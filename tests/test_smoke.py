from __future__ import annotations

import logging
import tempfile
import unittest
from pathlib import Path

from src.config import load_config
from src.downloader import Downloader
from src.state import StateStore


CONFIG_TEMPLATE = """\
region: emea
tier: vct
date_start: 2026-04-01
date_end: 2026-04-30
output_root: {output_root}
max_requests_per_minute: 30
retry_count: 1
retry_backoff_seconds: 0
resume_enabled: true
refresh_existing: {refresh_existing}
log_level: INFO
run_name: {run_name}
"""


class FakeClient:
    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def fetch(self, url: str, timeout_seconds: int = 30) -> str:
        self.calls.append(url)
        if url not in self.responses:
            raise RuntimeError(f"Missing fake response for {url}")
        return self.responses[url]


def load_fixture(name: str) -> str:
    fixture_path = Path(__file__).parent / "fixtures" / name
    return fixture_path.read_text(encoding="utf-8")


def make_logger() -> logging.Logger:
    logger = logging.getLogger("vlr_pipeline_test")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.NullHandler())
    return logger


class SmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.responses = {
            "https://www.vlr.gg/events/?region=27&tier=60": load_fixture("listing_emea_vct.html"),
            "https://www.vlr.gg/event/2863/vct-2026-emea-stage-1": load_fixture("event_overview_2863.html"),
            "https://www.vlr.gg/event/1999/old-event": load_fixture("event_overview_1999.html"),
            "https://www.vlr.gg/event/matches/2863/vct-2026-emea-stage-1": load_fixture("event_matches_2863.html"),
            "https://www.vlr.gg/500001/team-a-vs-team-b-vct-2026-emea-stage-1-w1": load_fixture("match_500001.html"),
            "https://www.vlr.gg/500002/team-c-vs-team-d-vct-2026-emea-stage-1-w1": load_fixture("match_500002.html"),
        }

    def test_smoke_flow_writes_expected_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir) / "data"
            config_path = Path(temp_dir) / "pipeline.yaml"
            config_path.write_text(
                CONFIG_TEMPLATE.format(
                    output_root=output_root.as_posix(),
                    refresh_existing="false",
                    run_name="smoke_run",
                ),
                encoding="utf-8",
            )

            config = load_config(config_path)
            state = StateStore(config.output_root)
            client = FakeClient(self.responses)
            downloader = Downloader(config, make_logger(), state, client)
            manifest = downloader.run()

            self.assertEqual(manifest["counts"]["events_discovered"], 2)
            self.assertEqual(manifest["counts"]["events_in_scope"], 1)
            self.assertEqual(manifest["counts"]["events_out_of_scope"], 1)
            self.assertEqual(manifest["counts"]["matches_discovered"], 2)
            self.assertTrue((output_root / "raw" / "manifests" / "smoke_run.json").exists())
            self.assertTrue((output_root / "raw" / "indexes" / "events.jsonl").exists())
            self.assertTrue((output_root / "raw" / "indexes" / "matches.jsonl").exists())
            self.assertTrue((output_root / "state" / "completed_items.json").exists())

    def test_cached_pages_are_reused_when_refresh_is_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir) / "data"
            config_path = Path(temp_dir) / "pipeline.yaml"
            config_path.write_text(
                CONFIG_TEMPLATE.format(
                    output_root=output_root.as_posix(),
                    refresh_existing="false",
                    run_name="cache_run",
                ),
                encoding="utf-8",
            )

            config = load_config(config_path)
            state = StateStore(config.output_root)
            first_client = FakeClient(self.responses)
            Downloader(config, make_logger(), state, first_client).run()
            self.assertGreater(len(first_client.calls), 0)

            second_client = FakeClient(self.responses)
            Downloader(config, make_logger(), StateStore(config.output_root), second_client).run()
            self.assertEqual(second_client.calls, [])

    def test_refresh_existing_triggers_redownload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir) / "data"
            config_path = Path(temp_dir) / "pipeline.yaml"
            config_path.write_text(
                CONFIG_TEMPLATE.format(
                    output_root=output_root.as_posix(),
                    refresh_existing="false",
                    run_name="refresh_seed",
                ),
                encoding="utf-8",
            )
            config = load_config(config_path)
            Downloader(config, make_logger(), StateStore(config.output_root), FakeClient(self.responses)).run()

            refresh_config_path = Path(temp_dir) / "refresh.yaml"
            refresh_config_path.write_text(
                CONFIG_TEMPLATE.format(
                    output_root=output_root.as_posix(),
                    refresh_existing="true",
                    run_name="refresh_run",
                ),
                encoding="utf-8",
            )
            refresh_config = load_config(refresh_config_path)
            refresh_client = FakeClient(self.responses)
            Downloader(refresh_config, make_logger(), StateStore(refresh_config.output_root), refresh_client).run()

            self.assertGreater(len(refresh_client.calls), 0)


if __name__ == "__main__":
    unittest.main()
