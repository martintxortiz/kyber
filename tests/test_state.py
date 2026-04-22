from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.state import StateStore, atomic_write_json, load_json


class StateTests(unittest.TestCase):
    def test_atomic_write_json_creates_expected_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            atomic_write_json(path, {"hello": "world"})

            self.assertTrue(path.exists())
            self.assertFalse(path.with_suffix(".json.tmp").exists())
            self.assertEqual(load_json(path, {}), {"hello": "world"})

    def test_state_resume_and_failures_persist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state = StateStore(Path(temp_dir))
            state.mark_completed("matches", "500001", {"url": "https://example.com/500001"})
            state.mark_failed("matches", "500002", "network", url="https://example.com/500002")
            state.mark_failed("matches", "500002", "network", url="https://example.com/500002")

            reloaded = StateStore(Path(temp_dir))

            self.assertTrue(reloaded.is_completed("matches", "500001"))
            failure = reloaded.get_failed("matches", "500002")
            self.assertIsNotNone(failure)
            self.assertEqual(failure["attempt_count"], 2)
            self.assertEqual(failure["last_error"], "network")


if __name__ == "__main__":
    unittest.main()
