from __future__ import annotations

from pathlib import Path
from typing import Any

from src.config import load_config
from src.downloader import Downloader
from src.logging_utils import configure_logging, log_event
from src.state import StateStore
from src.vlr_client import VLRClient


def run_pipeline(config_path: str | Path) -> dict[str, Any]:
    config = load_config(config_path)
    logger, log_path = configure_logging(config.output_root, config.run_name, config.log_level)

    log_event(
        logger,
        "pipeline_start",
        config_path=str(config_path),
        region=config.region,
        tier=config.tier,
        date_start=config.date_start.isoformat(),
        date_end=config.date_end.isoformat(),
        run_name=config.run_name,
        output_root=str(config.output_root),
    )

    state = StateStore(config.output_root)
    client = VLRClient(
        max_requests_per_minute=config.max_requests_per_minute,
        retry_count=config.retry_count,
        retry_backoff_seconds=config.retry_backoff_seconds,
    )
    downloader = Downloader(config, logger, state, client)

    try:
        manifest = downloader.run()
        log_event(
            logger,
            "pipeline_complete",
            run_name=config.run_name,
            manifest_path=str(downloader.manifest_path),
            log_path=str(log_path),
            pages_downloaded=manifest["counts"]["pages_downloaded"],
            pages_skipped=manifest["counts"]["pages_skipped"],
            pages_failed=manifest["counts"]["pages_failed"],
        )
        return manifest
    except Exception as exc:
        state.update_run_state(
            "failed",
            run_name=config.run_name,
            error=str(exc),
            manifest_path=str(downloader.manifest_path),
        )
        log_event(
            logger,
            "pipeline_failed",
            run_name=config.run_name,
            error=str(exc),
        )
        raise
