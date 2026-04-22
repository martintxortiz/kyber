from __future__ import annotations

import argparse
import sys

from src.pipeline import run_pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Phase 1 VLR.gg raw-data pipeline.")
    parser.add_argument("--config", required=True, help="Path to the pipeline YAML config.")
    args = parser.parse_args(argv)

    run_pipeline(args.config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
