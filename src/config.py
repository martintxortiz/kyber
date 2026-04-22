from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml


REGION_CODES = {
    "all": "all",
    "americas": "26",
    "emea": "27",
    "pacific": "28",
    "china": "24",
}

TIER_CODES = {
    "all": "all",
    "vct": "60",
    "vcl": "61",
    "t3": "62",
    "gc": "63",
    "collegiate": "64",
    "offseason": "67",
}

LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
REQUIRED_KEYS = {
    "region",
    "tier",
    "date_start",
    "date_end",
    "output_root",
    "max_requests_per_minute",
    "retry_count",
    "retry_backoff_seconds",
    "resume_enabled",
    "refresh_existing",
    "log_level",
    "run_name",
}


class ConfigError(ValueError):
    """Raised when the pipeline config is invalid."""


def _parse_date(value: str, field_name: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ConfigError(f"{field_name} must use YYYY-MM-DD format") from exc


def _require_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{field_name} must be a boolean")
    return value


@dataclass(frozen=True)
class PipelineConfig:
    region: str
    tier: str
    date_start: date
    date_end: date
    output_root: Path
    max_requests_per_minute: int
    retry_count: int
    retry_backoff_seconds: int
    resume_enabled: bool
    refresh_existing: bool
    log_level: str
    run_name: str

    @property
    def region_code(self) -> str:
        return REGION_CODES[self.region]

    @property
    def tier_code(self) -> str:
        return TIER_CODES[self.tier]

    @property
    def listing_url(self) -> str:
        return f"https://www.vlr.gg/events/?region={self.region_code}&tier={self.tier_code}"

    def to_manifest_dict(self) -> dict[str, Any]:
        return {
            "region": self.region,
            "region_code": self.region_code,
            "tier": self.tier,
            "tier_code": self.tier_code,
            "date_start": self.date_start.isoformat(),
            "date_end": self.date_end.isoformat(),
            "output_root": str(self.output_root),
            "max_requests_per_minute": self.max_requests_per_minute,
            "retry_count": self.retry_count,
            "retry_backoff_seconds": self.retry_backoff_seconds,
            "resume_enabled": self.resume_enabled,
            "refresh_existing": self.refresh_existing,
            "log_level": self.log_level,
            "run_name": self.run_name,
        }


def load_config(path: str | Path) -> PipelineConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    if not isinstance(raw, dict):
        raise ConfigError("Config must be a YAML mapping")

    missing = sorted(REQUIRED_KEYS - set(raw))
    if missing:
        raise ConfigError(f"Config is missing required keys: {', '.join(missing)}")

    region = str(raw["region"]).strip().lower()
    tier = str(raw["tier"]).strip().lower()
    if region not in REGION_CODES:
        raise ConfigError(f"Unsupported region: {region}")
    if tier not in TIER_CODES:
        raise ConfigError(f"Unsupported tier: {tier}")

    date_start = _parse_date(str(raw["date_start"]).strip(), "date_start")
    date_end = _parse_date(str(raw["date_end"]).strip(), "date_end")
    if date_start > date_end:
        raise ConfigError("date_start must be less than or equal to date_end")

    try:
        max_requests_per_minute = int(raw["max_requests_per_minute"])
        retry_count = int(raw["retry_count"])
        retry_backoff_seconds = int(raw["retry_backoff_seconds"])
    except (TypeError, ValueError) as exc:
        raise ConfigError("Rate limit and retry settings must be integers") from exc

    if max_requests_per_minute <= 0:
        raise ConfigError("max_requests_per_minute must be greater than 0")
    if retry_count < 0:
        raise ConfigError("retry_count must be greater than or equal to 0")
    if retry_backoff_seconds < 0:
        raise ConfigError("retry_backoff_seconds must be greater than or equal to 0")

    resume_enabled = _require_bool(raw["resume_enabled"], "resume_enabled")
    refresh_existing = _require_bool(raw["refresh_existing"], "refresh_existing")

    log_level = str(raw["log_level"]).strip().upper()
    if log_level not in LOG_LEVELS:
        raise ConfigError(f"Unsupported log level: {log_level}")

    run_name = str(raw["run_name"]).strip()
    if not run_name:
        raise ConfigError("run_name must not be empty")

    output_root = Path(str(raw["output_root"]).strip())
    if not output_root:
        raise ConfigError("output_root must not be empty")

    return PipelineConfig(
        region=region,
        tier=tier,
        date_start=date_start,
        date_end=date_end,
        output_root=output_root,
        max_requests_per_minute=max_requests_per_minute,
        retry_count=retry_count,
        retry_backoff_seconds=retry_backoff_seconds,
        resume_enabled=resume_enabled,
        refresh_existing=refresh_existing,
        log_level=log_level,
        run_name=run_name,
    )
