# Phase 1 Standards

## Naming

- Use lowercase snake_case for Python modules, config keys, JSON keys, and filenames where practical.
- Name raw event and match files as `<id>_<slug>.*`.
- Name listing files from normalized scope: region, tier, and page.

## Directories

- `src/` contains runtime code only.
- `tests/` contains small unit and smoke tests only.
- `data/raw/html/` stores raw source pages.
- `data/raw/json/` stores minimal derived metadata.
- `data/raw/indexes/` stores append-only JSONL indexes.
- `data/raw/manifests/` stores one manifest per run.
- `data/state/` stores resume state.
- `data/logs/` stores per-run logs.

## Config

- Use one YAML config file per run.
- Keep config user-facing and simple.
- Normalize friendly values like `emea` and `vct` in code, not in the YAML.

## Logging

- Log to console and file.
- Use readable key=value lines.
- Log run start, scope, per-item progress, cache skips, retries, failures, and final summary.

## State And Resume

- State files must be plain JSON and safe to inspect manually.
- Writes to JSON state and manifests must use temp-file-plus-rename.
- Existing raw HTML is reusable cache unless `refresh_existing` is true.
- Failed items must record attempt count, last error, and last update time.

## Raw Data

- Preserve raw HTML before any deeper parsing.
- Parse metadata from saved HTML so later reprocessing uses the same source artifact.
- Index records must include run name, IDs, URLs, and local file paths.

## Sync

- Sync code to `kyber` with `gcloud compute scp`.
- Run real pipeline work with `gcloud compute ssh`.
- Do not overwrite or delete remote `data/` during sync.

## Agent Handoff

- Append every meaningful run to `memory.md`.
- Keep handoffs short, factual, and decision-oriented.
- If a change increases complexity, justify it in the handoff entry.
