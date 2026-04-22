from __future__ import annotations

import socket
from collections import deque
from pathlib import Path
from typing import Any

from src.config import PipelineConfig
from src.logging_utils import log_event
from src.parse_helpers import (
    event_overlaps_window,
    extract_event_id_slug,
    listing_key_from_url,
    parse_event_matches_page,
    parse_event_overview_page,
    parse_listing_page,
    parse_match_page,
    sanitize_slug,
)
from src.state import StateStore, append_jsonl, atomic_write_json, atomic_write_text, utc_now
from src.vlr_client import VLRClient


class Downloader:
    def __init__(self, config: PipelineConfig, logger: Any, state: StateStore, client: VLRClient) -> None:
        self.config = config
        self.logger = logger
        self.state = state
        self.client = client
        self.hostname = socket.gethostname()
        self.started_at = utc_now()

        self.output_root = config.output_root
        self.html_root = self.output_root / "raw" / "html"
        self.json_root = self.output_root / "raw" / "json"
        self.index_root = self.output_root / "raw" / "indexes"
        self.manifest_root = self.output_root / "raw" / "manifests"

        for path in (
            self.html_root / "listings",
            self.html_root / "events",
            self.html_root / "matches",
            self.json_root / "listings",
            self.json_root / "events",
            self.json_root / "matches",
            self.index_root,
            self.manifest_root,
        ):
            path.mkdir(parents=True, exist_ok=True)

        self.events_index_path = self.index_root / "events.jsonl"
        self.matches_index_path = self.index_root / "matches.jsonl"
        self.manifest_path = self.manifest_root / f"{self.config.run_name}.json"

        self.counts: dict[str, int] = {
            "listing_pages_processed": 0,
            "events_discovered": 0,
            "events_in_scope": 0,
            "events_out_of_scope": 0,
            "matches_discovered": 0,
            "pages_downloaded": 0,
            "pages_skipped": 0,
            "pages_failed": 0,
        }
        self._seen_match_ids: set[str] = set()

    def run(self) -> dict[str, Any]:
        self._sync_status("running")
        discovered_events = self._collect_listing_pages()
        self.counts["events_discovered"] = len(discovered_events)
        self._sync_status("running")

        for event_summary in discovered_events.values():
            event_metadata = self._process_event_overview(event_summary)
            if event_metadata is None:
                continue
            self._process_event_matches(event_metadata)

        finished_at = utc_now()
        manifest = self._manifest_payload("completed", finished_at)
        atomic_write_json(self.manifest_path, manifest)
        self.state.update_run_state(
            "completed",
            run_name=self.config.run_name,
            started_at=self.started_at,
            finished_at=finished_at,
            manifest_path=str(self.manifest_path),
            counts=self.counts,
        )
        return manifest

    def _manifest_payload(self, status: str, finished_at: str | None = None) -> dict[str, Any]:
        return {
            "run_name": self.config.run_name,
            "status": status,
            "machine_name": self.hostname,
            "started_at": self.started_at,
            "finished_at": finished_at,
            "region": self.config.region,
            "tier": self.config.tier,
            "config": self.config.to_manifest_dict(),
            "counts": dict(self.counts),
            "output_paths": {
                "html_root": str(self.html_root),
                "json_root": str(self.json_root),
                "events_index": str(self.events_index_path),
                "matches_index": str(self.matches_index_path),
                "manifest": str(self.manifest_path),
                "state_root": str(self.output_root / "state"),
                "log_root": str(self.output_root / "logs"),
            },
        }

    def _sync_status(self, status: str, current_item: dict[str, Any] | None = None) -> None:
        atomic_write_json(self.manifest_path, self._manifest_payload(status))
        self.state.update_run_state(
            status,
            run_name=self.config.run_name,
            started_at=self.started_at,
            current_item=current_item or {},
            manifest_path=str(self.manifest_path),
            counts=self.counts,
        )

    def _collect_listing_pages(self) -> dict[str, dict[str, Any]]:
        queue: deque[str] = deque([self.config.listing_url])
        visited: set[str] = set()
        discovered_events: dict[str, dict[str, Any]] = {}

        while queue:
            listing_url = queue.popleft()
            if listing_url in visited:
                continue
            visited.add(listing_url)
            self.counts["listing_pages_processed"] = len(visited)
            self._sync_status("running", {"item_type": "listings", "url": listing_url})

            listing_key = listing_key_from_url(listing_url)
            html_path = self.html_root / "listings" / f"{listing_key}.html"
            json_path = self.json_root / "listings" / f"{listing_key}.json"
            html = self._get_or_fetch_html("listings", listing_key, listing_url, html_path)
            if html is None:
                continue

            try:
                parsed = parse_listing_page(html, listing_url)
                listing_record = {
                    "listing_key": listing_key,
                    "page_url": listing_url,
                    "fetched_at": utc_now(),
                    "pagination_urls": parsed["pagination_urls"],
                    "events": parsed["events"],
                }
                atomic_write_json(json_path, listing_record)
                self.state.mark_completed(
                    "listings",
                    listing_key,
                    {
                        "url": listing_url,
                        "html_path": str(html_path),
                        "json_path": str(json_path),
                        "run_name": self.config.run_name,
                    },
                )
                for event_summary in parsed["events"]:
                    event_id = event_summary["event_id"]
                    discovered_events.setdefault(event_id, event_summary)
                for page_url in parsed["pagination_urls"]:
                    if page_url not in visited:
                        queue.append(page_url)
            except Exception as exc:
                self.counts["pages_failed"] += 1
                self.state.mark_failed(
                    "listings",
                    listing_key,
                    str(exc),
                    url=listing_url,
                    run_name=self.config.run_name,
                )
                log_event(
                    self.logger,
                    "listing_parse_failed",
                    listing_key=listing_key,
                    url=listing_url,
                    error=str(exc),
                )
                self._sync_status("running", {"item_type": "listings", "url": listing_url})

        return discovered_events

    def _process_event_overview(self, event_summary: dict[str, Any]) -> dict[str, Any] | None:
        event_id = event_summary["event_id"]
        slug = sanitize_slug(event_summary["slug"])
        html_path = self.html_root / "events" / f"{event_id}_{slug}.html"
        json_path = self.json_root / "events" / f"{event_id}_{slug}.json"
        key = f"overview:{event_id}"

        self._sync_status("running", {"item_type": "events", "event_id": event_id, "url": event_summary["url"]})
        html = self._get_or_fetch_html("events", key, event_summary["url"], html_path)
        if html is None:
            return None

        try:
            overview = parse_event_overview_page(html, event_summary["url"])
            metadata = {
                **event_summary,
                **overview,
                "region": self.config.region,
                "tier": self.config.tier,
                "source_listing_url": event_summary["source_listing_url"],
                "fetched_at": utc_now(),
            }
            if not event_overlaps_window(
                metadata["date_start"],
                metadata["date_end"],
                self.config.date_start,
                self.config.date_end,
            ):
                self.counts["events_out_of_scope"] += 1
                log_event(
                    self.logger,
                    "event_out_of_scope",
                    event_id=event_id,
                    title=metadata["title"],
                    date_start=metadata["date_start"],
                    date_end=metadata["date_end"],
                )
                return None

            self.counts["events_in_scope"] += 1
            atomic_write_json(json_path, metadata)
            append_jsonl(
                self.events_index_path,
                {
                    "run_name": self.config.run_name,
                    "event_id": metadata["event_id"],
                    "slug": metadata["slug"],
                    "url": metadata["url"],
                    "source_page": metadata["source_listing_url"],
                    "date_start": metadata["date_start"],
                    "date_end": metadata["date_end"],
                    "html_path": str(html_path),
                    "json_path": str(json_path),
                    "fetched_at": metadata["fetched_at"],
                },
            )
            self.state.mark_completed(
                "events",
                key,
                {
                    "url": metadata["url"],
                    "html_path": str(html_path),
                    "json_path": str(json_path),
                    "run_name": self.config.run_name,
                },
            )
            return metadata
        except Exception as exc:
            self.counts["pages_failed"] += 1
            self.state.mark_failed(
                "events",
                key,
                str(exc),
                url=event_summary["url"],
                run_name=self.config.run_name,
            )
            log_event(
                self.logger,
                "event_parse_failed",
                event_id=event_id,
                url=event_summary["url"],
                error=str(exc),
            )
            self._sync_status("running", {"item_type": "events", "event_id": event_id})
            return None

    def _process_event_matches(self, event_metadata: dict[str, Any]) -> None:
        event_id = event_metadata["event_id"]
        slug = sanitize_slug(event_metadata["slug"])
        html_path = self.html_root / "events" / f"{event_id}_{slug}_matches.html"
        json_path = self.json_root / "events" / f"{event_id}_{slug}_matches.json"
        key = f"matches:{event_id}"
        matches_url = event_metadata["matches_url"]

        self._sync_status("running", {"item_type": "events", "event_id": event_id, "url": matches_url})
        html = self._get_or_fetch_html("events", key, matches_url, html_path)
        if html is None:
            return

        try:
            parsed = parse_event_matches_page(html, matches_url, event_id, event_metadata["title"])
            metadata = {
                "event_id": event_id,
                "event_title": event_metadata["title"],
                "matches_url": matches_url,
                "match_count": len(parsed["matches"]),
                "matches": parsed["matches"],
                "fetched_at": utc_now(),
            }
            atomic_write_json(json_path, metadata)
            self.state.mark_completed(
                "events",
                key,
                {
                    "url": matches_url,
                    "html_path": str(html_path),
                    "json_path": str(json_path),
                    "run_name": self.config.run_name,
                },
            )
            for match_summary in parsed["matches"]:
                match_id = match_summary["match_id"]
                if match_id not in self._seen_match_ids:
                    self._seen_match_ids.add(match_id)
                    self.counts["matches_discovered"] += 1
                self._process_match(match_summary, matches_url)
        except Exception as exc:
            self.counts["pages_failed"] += 1
            self.state.mark_failed(
                "events",
                key,
                str(exc),
                url=matches_url,
                run_name=self.config.run_name,
            )
            log_event(
                self.logger,
                "event_matches_parse_failed",
                event_id=event_id,
                url=matches_url,
                error=str(exc),
            )
            self._sync_status("running", {"item_type": "events", "event_id": event_id})

    def _process_match(self, match_summary: dict[str, Any], source_page: str) -> None:
        match_id = match_summary["match_id"]
        slug = sanitize_slug(match_summary["slug"])
        html_path = self.html_root / "matches" / f"{match_id}_{slug}.html"
        json_path = self.json_root / "matches" / f"{match_id}_{slug}.json"

        self._sync_status("running", {"item_type": "matches", "match_id": match_id, "url": match_summary["url"]})
        html = self._get_or_fetch_html("matches", match_id, match_summary["url"], html_path)
        if html is None:
            return

        try:
            parsed = parse_match_page(
                html,
                match_summary["url"],
                match_summary["event_id"],
                match_summary["event_title"],
            )
            metadata = {
                **match_summary,
                **parsed,
                "region": self.config.region,
                "tier": self.config.tier,
                "source_page": source_page,
                "fetched_at": utc_now(),
            }
            atomic_write_json(json_path, metadata)
            append_jsonl(
                self.matches_index_path,
                {
                    "run_name": self.config.run_name,
                    "match_id": metadata["match_id"],
                    "slug": metadata["slug"],
                    "event_id": metadata["event_id"],
                    "url": metadata["url"],
                    "source_page": source_page,
                    "scheduled_at_text": metadata["scheduled_at_text"],
                    "html_path": str(html_path),
                    "json_path": str(json_path),
                    "fetched_at": metadata["fetched_at"],
                },
            )
            self.state.mark_completed(
                "matches",
                match_id,
                {
                    "url": metadata["url"],
                    "html_path": str(html_path),
                    "json_path": str(json_path),
                    "run_name": self.config.run_name,
                },
            )
        except Exception as exc:
            self.counts["pages_failed"] += 1
            self.state.mark_failed(
                "matches",
                match_id,
                str(exc),
                url=match_summary["url"],
                run_name=self.config.run_name,
            )
            log_event(
                self.logger,
                "match_parse_failed",
                match_id=match_id,
                url=match_summary["url"],
                error=str(exc),
            )
            self._sync_status("running", {"item_type": "matches", "match_id": match_id})

    def _get_or_fetch_html(self, item_type: str, key: str, url: str, path: Path) -> str | None:
        if path.exists() and not self.config.refresh_existing:
            self.counts["pages_skipped"] += 1
            log_event(
                self.logger,
                "cache_hit",
                item_type=item_type,
                key=key,
                url=url,
                path=str(path),
            )
            return path.read_text(encoding="utf-8")

        try:
            html = self.client.fetch(url)
            atomic_write_text(path, html)
            self.counts["pages_downloaded"] += 1
            log_event(
                self.logger,
                "download_success",
                item_type=item_type,
                key=key,
                url=url,
                path=str(path),
            )
            return html
        except Exception as exc:
            self.counts["pages_failed"] += 1
            self.state.mark_failed(
                item_type,
                key,
                str(exc),
                url=url,
                run_name=self.config.run_name,
            )
            log_event(
                self.logger,
                "download_failed",
                item_type=item_type,
                key=key,
                url=url,
                error=str(exc),
            )
            self._sync_status("running", {"item_type": item_type, "key": key, "url": url})
            return None
