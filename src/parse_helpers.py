from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup


BASE_URL = "https://www.vlr.gg"
EVENT_URL_RE = re.compile(r"/event/(?P<event_id>\d+)/(?P<slug>[^/?#]+)")
MATCH_URL_RE = re.compile(r"/(?P<match_id>\d+)/(?P<slug>[^/?#]+)$")


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "get_text"):
        text = value.get_text(" ", strip=True)
    else:
        text = str(value)
    return re.sub(r"\s+", " ", text).strip()


def normalize_url(path_or_url: str) -> str:
    return urljoin(BASE_URL, path_or_url)


def sanitize_slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "unknown"


def split_match_title(title: str) -> list[str]:
    parts = re.split(r"\s+vs\.?\s+", title.strip(), maxsplit=1)
    if len(parts) == 2:
        return [parts[0].strip(), parts[1].strip()]
    return []


def extract_event_id_slug(url: str) -> dict[str, str] | None:
    match = EVENT_URL_RE.search(urlparse(url).path)
    if not match:
        return None
    return {
        "event_id": match.group("event_id"),
        "slug": match.group("slug"),
    }


def extract_match_id_slug(url: str) -> dict[str, str] | None:
    parsed = urlparse(url)
    if "/event/" in parsed.path:
        return None
    match = MATCH_URL_RE.search(parsed.path)
    if not match:
        return None
    return {
        "match_id": match.group("match_id"),
        "slug": match.group("slug"),
    }


def listing_key_from_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    region = query.get("region", ["all"])[0]
    tier = query.get("tier", ["all"])[0]
    page = query.get("page", ["1"])[0]
    return f"region_{region}__tier_{tier}__page_{page}"


def parse_date_range(text: str) -> tuple[str | None, str | None]:
    cleaned = clean_text(text)
    if not cleaned:
        return None, None

    if " - " in cleaned:
        start_raw, end_raw = cleaned.split(" - ", 1)
    else:
        return None, None

    return _parse_single_date(start_raw), _parse_single_date(end_raw)


def _parse_single_date(text: str) -> str | None:
    cleaned = clean_text(text)
    if not cleaned or cleaned.upper() == "TBD":
        return None

    formats = (
        "%b %d, %Y",
        "%B %d, %Y",
        "%b %d %Y",
        "%B %d %Y",
    )
    for date_format in formats:
        try:
            return datetime.strptime(cleaned, date_format).date().isoformat()
        except ValueError:
            continue
    return None


def event_overlaps_window(
    event_start: str | None,
    event_end: str | None,
    window_start: datetime.date,
    window_end: datetime.date,
) -> bool:
    if event_start is None and event_end is None:
        return True

    start = datetime.fromisoformat(event_start).date() if event_start else None
    end = datetime.fromisoformat(event_end).date() if event_end else None

    if start is None:
        start = end
    if end is None:
        end = start
    if start is None or end is None:
        return True
    return start <= window_end and end >= window_start


def parse_listing_page(html: str, source_url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    events: list[dict[str, Any]] = []
    seen_event_ids: set[str] = set()

    for anchor in soup.select("a.event-item[href*='/event/']"):
        url = normalize_url(anchor.get("href", ""))
        identity = extract_event_id_slug(url)
        if identity is None:
            continue
        event_id = identity["event_id"]
        if event_id in seen_event_ids:
            continue
        seen_event_ids.add(event_id)

        events.append(
            {
                "event_id": event_id,
                "slug": identity["slug"],
                "url": url,
                "title": clean_text(anchor.select_one(".event-item-title")),
                "status_text": clean_text(anchor.select_one(".event-item-desc-item-status")),
                "listing_dates_text": clean_text(anchor.select_one(".event-item-desc-item.mod-dates")),
                "source_listing_url": source_url,
            }
        )

    pagination_urls: list[str] = []
    for anchor in soup.select(".action-container-pages a.btn.mod-page[href]"):
        page_url = normalize_url(anchor.get("href", ""))
        if page_url and page_url not in pagination_urls:
            pagination_urls.append(page_url)

    return {
        "page_url": source_url,
        "events": events,
        "pagination_urls": pagination_urls,
    }


def _extract_labeled_value(soup: BeautifulSoup, label_text: str) -> str:
    for item in soup.select(".event-desc-item"):
        label = clean_text(item.select_one(".event-desc-item-label")).lower()
        if label == label_text.lower():
            value_node = item.select_one(".event-desc-item-value")
            if value_node is not None:
                return clean_text(value_node)
            text = clean_text(item)
            return text.replace(label_text, "", 1).strip()
    return ""


def parse_event_overview_page(html: str, source_url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    identity = extract_event_id_slug(source_url)
    if identity is None:
        raise ValueError(f"Could not parse event identity from {source_url}")

    title = clean_text(soup.select_one(".wf-title"))
    if not title:
        title = clean_text(soup.title).split("|")[0].strip()

    date_text = _extract_labeled_value(soup, "Dates")
    date_start, date_end = parse_date_range(date_text)

    return {
        "event_id": identity["event_id"],
        "slug": identity["slug"],
        "title": title,
        "url": normalize_url(source_url),
        "matches_url": f"{BASE_URL}/event/matches/{identity['event_id']}/{identity['slug']}",
        "date_start": date_start,
        "date_end": date_end,
        "dates_text": date_text,
        "prize_text": _extract_labeled_value(soup, "Prize"),
        "location_text": _extract_labeled_value(soup, "Location"),
    }


def parse_event_matches_page(html: str, source_url: str, event_id: str, event_title: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    matches: list[dict[str, Any]] = []
    seen_match_ids: set[str] = set()

    for anchor in soup.select("a.match-item[href]"):
        url = normalize_url(anchor.get("href", ""))
        identity = extract_match_id_slug(url)
        if identity is None:
            continue
        match_id = identity["match_id"]
        if match_id in seen_match_ids:
            continue
        seen_match_ids.add(match_id)

        teams = [
            clean_text(node)
            for node in anchor.select(".match-item-vs-team-name .text-of")
            if clean_text(node)
        ]
        matches.append(
            {
                "match_id": match_id,
                "slug": identity["slug"],
                "url": url,
                "event_id": event_id,
                "event_title": event_title,
                "teams": teams,
                "scheduled_at_text": clean_text(anchor.select_one(".match-item-time")),
                "status_text": clean_text(anchor.select_one(".ml-status")),
                "stage_text": clean_text(anchor.select_one(".match-item-event")),
            }
        )

    return {
        "event_id": event_id,
        "event_title": event_title,
        "matches_url": normalize_url(source_url),
        "matches": matches,
    }


def parse_match_page(html: str, source_url: str, event_id: str, event_title: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    identity = extract_match_id_slug(source_url)
    if identity is None:
        raise ValueError(f"Could not parse match identity from {source_url}")

    title_text = clean_text(soup.title)
    title_parts = [part.strip() for part in title_text.split("|") if part.strip()]
    match_title = title_parts[0] if title_parts else clean_text(source_url)
    teams = split_match_title(match_title)

    event_url = ""
    for anchor in soup.select("a[href*='/event/']"):
        maybe_url = normalize_url(anchor.get("href", ""))
        if extract_event_id_slug(maybe_url) is not None:
            event_url = maybe_url
            if not event_title:
                event_title = clean_text(anchor)
            break

    scheduled_at_text = clean_text(soup.select_one(".match-header-date"))
    note_text = clean_text(soup.select_one(".match-header-vs-note"))
    patch_match = re.search(r"Patch\s+\d+\.\d+", clean_text(soup))
    best_of_match = re.search(r"\bBo\d\b", note_text or clean_text(soup))

    parsed_event_id = event_id
    if event_url:
        parsed_identity = extract_event_id_slug(event_url)
        if parsed_identity is not None:
            parsed_event_id = parsed_identity["event_id"]

    stage_text = title_parts[2] if len(title_parts) >= 3 else ""

    return {
        "match_id": identity["match_id"],
        "slug": identity["slug"],
        "url": normalize_url(source_url),
        "event_id": parsed_event_id,
        "event_title": event_title or (title_parts[1] if len(title_parts) >= 2 else ""),
        "event_url": event_url,
        "match_title": match_title,
        "teams": teams,
        "scheduled_at_text": scheduled_at_text,
        "status_text": note_text or clean_text(soup.select_one(".ml-status")),
        "best_of": best_of_match.group(0) if best_of_match else "",
        "stage_text": stage_text,
        "patch_text": patch_match.group(0) if patch_match else "",
    }
