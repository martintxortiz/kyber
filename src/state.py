from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    temp_path.replace(path)


def atomic_write_json(path: Path, payload: Any) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, sort_keys=True, ensure_ascii=True))
        handle.write("\n")


class StateStore:
    def __init__(self, output_root: Path) -> None:
        self.root = output_root / "state"
        self.root.mkdir(parents=True, exist_ok=True)
        self.run_state_path = self.root / "run_state.json"
        self.completed_path = self.root / "completed_items.json"
        self.failed_path = self.root / "failed_items.json"

        self.completed = self._load_bucketed(self.completed_path)
        self.failed = self._load_bucketed(self.failed_path)

    def _load_bucketed(self, path: Path) -> dict[str, dict[str, Any]]:
        loaded = load_json(path, {})
        if not isinstance(loaded, dict):
            loaded = {}
        for item_type in ("listings", "events", "matches"):
            loaded.setdefault(item_type, {})
        return loaded

    def _write_completed(self) -> None:
        atomic_write_json(self.completed_path, self.completed)

    def _write_failed(self) -> None:
        atomic_write_json(self.failed_path, self.failed)

    def update_run_state(self, status: str, **extra: Any) -> None:
        payload = {
            "status": status,
            "updated_at": utc_now(),
        }
        payload.update(extra)
        atomic_write_json(self.run_state_path, payload)

    def is_completed(self, item_type: str, key: str) -> bool:
        return key in self.completed.setdefault(item_type, {})

    def mark_completed(self, item_type: str, key: str, record: dict[str, Any]) -> None:
        bucket = self.completed.setdefault(item_type, {})
        enriched = dict(record)
        enriched["completed_at"] = utc_now()
        bucket[key] = enriched
        self.failed.setdefault(item_type, {}).pop(key, None)
        self._write_completed()
        self._write_failed()

    def mark_failed(self, item_type: str, key: str, error: str, **record: Any) -> None:
        bucket = self.failed.setdefault(item_type, {})
        previous = bucket.get(key, {})
        attempt_count = int(previous.get("attempt_count", 0)) + 1
        enriched = dict(record)
        enriched["attempt_count"] = attempt_count
        enriched["last_error"] = error
        enriched["last_updated"] = utc_now()
        bucket[key] = enriched
        self._write_failed()

    def get_failed(self, item_type: str, key: str) -> dict[str, Any] | None:
        return self.failed.setdefault(item_type, {}).get(key)
