from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _serialize(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True)


class KeyValueFormatter(logging.Formatter):
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        return datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()

    def format(self, record: logging.LogRecord) -> str:
        fields = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra_fields = getattr(record, "kv_fields", {})
        fields.update(extra_fields)
        return " ".join(f"{key}={_serialize(value)}" for key, value in fields.items())


def configure_logging(output_root: Path, run_name: str, log_level: str) -> tuple[logging.Logger, Path]:
    log_dir = output_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{run_name}.log"

    logger = logging.getLogger("vlr_pipeline")
    logger.handlers.clear()
    logger.setLevel(getattr(logging, log_level))
    logger.propagate = False

    formatter = KeyValueFormatter()
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger, log_path


def log_event(logger: logging.Logger, message: str, **fields: Any) -> None:
    logger.info(message, extra={"kv_fields": fields})
