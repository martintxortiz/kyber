# Valorant VCT Predictor

Phase 1 builds the smallest reliable foundation for future VCT research work:

- one config-driven pipeline entrypoint
- resumable raw VLR.gg acquisition
- explicit state, manifests, and logs
- VM-first execution on `kyber`

## Scope

Phase 1 stops at raw acquisition and indexing. It does not include training, feature engineering, or dataset modeling beyond minimal metadata extraction.

## Repository Layout

```text
.
├── AGENTS.md
├── README.md
├── configs/
├── docs/
├── guidelines.md
├── memory.md
├── scripts/
├── src/
└── tests/
```

Runtime data lives under `data/` and is intentionally ignored by git.

## Install

```powershell
python -m pip install --user -r requirements.txt
```

## Main Command

```powershell
python -m src.main --config configs/pipeline.yaml
```

Use local execution only for:

- config validation
- tests
- tiny dry runs
- fixture-based smoke checks

Use `kyber` for:

- real downloads
- real scraping
- refresh jobs
- backfills
- dataset creation
- training

## Local Validation

```powershell
python -m unittest discover -s tests -v
```

## VM Workflow

PowerShell wrappers are provided because local `bash` is not currently usable on this machine.

```powershell
.\scripts\sync_to_kyber.ps1
.\scripts\run_on_kyber.ps1
.\scripts\fetch_logs_from_kyber.ps1
```

Matching `.sh` scripts are included for compatibility with Linux shells and future automation.

## Canonical Data Rule

- Local machine is authoritative for code, docs, configs, and tests.
- `kyber` is authoritative for raw HTML, derived JSON metadata, logs, manifests, and resume state.
- `sync_to_kyber` never pushes local `data/` to the VM.
- `fetch_logs_from_kyber` only pulls logs and manifests by default.

## Output Artifacts

The pipeline writes:

- raw HTML under `data/raw/html/`
- minimal JSON metadata under `data/raw/json/`
- append-only JSONL indexes under `data/raw/indexes/`
- one run manifest under `data/raw/manifests/`
- run state under `data/state/`
- logs under `data/logs/`

# kyber
