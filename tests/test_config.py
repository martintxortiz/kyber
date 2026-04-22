from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.config import ConfigError, load_config


VALID_CONFIG = """\
region: emea
tier: vct
date_start: 2026-04-01
date_end: 2026-04-30
output_root: data
max_requests_per_minute: 30
retry_count: 2
retry_backoff_seconds: 2
resume_enabled: true
refresh_existing: false
log_level: INFO
run_name: test_run
"""


class ConfigTests(unittest.TestCase):
    def test_load_config_normalizes_region_and_tier(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "pipeline.yaml"
            config_path.write_text(VALID_CONFIG, encoding="utf-8")
            config = load_config(config_path)

        self.assertEqual(config.region, "emea")
        self.assertEqual(config.region_code, "27")
        self.assertEqual(config.tier, "vct")
        self.assertEqual(config.tier_code, "60")

    def test_invalid_date_raises(self) -> None:
        bad_config = VALID_CONFIG.replace("2026-04-30", "2026/04/30", 1)
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "pipeline.yaml"
            config_path.write_text(bad_config, encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(config_path)

    def test_missing_key_raises(self) -> None:
        bad_config = VALID_CONFIG.replace("run_name: test_run\n", "")
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "pipeline.yaml"
            config_path.write_text(bad_config, encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(config_path)


if __name__ == "__main__":
    unittest.main()
