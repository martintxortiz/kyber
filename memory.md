# Memory

Use this file as persistent project memory. Append a new entry after every meaningful run, handoff, or milestone.

## Entry Template

```text
## YYYY-MM-DDTHH:MM:SSZ | agent=<name> | role=<role>
- objective:
- files created:
- files modified:
- decisions:
- assumptions:
- blockers:
- status:
- next steps:
```

## 2026-04-22T00:00:00Z | agent=codex | role=implementation
- objective: Build Phase 1 repository standards, memory system, VM protocol, and resumable VLR.gg raw-data pipeline.
- files created: Planned full Phase 1 skeleton in the current project root.
- files modified: None yet at initialization time.
- decisions: Use `C:\Users\Lowgo\Code\kyber` as the project root, keep one pipeline entrypoint, use `PyYAML` and `beautifulsoup4`, and make `kyber` the canonical machine for raw data and state.
- assumptions: Remote root on `kyber` is `/home/Lowgo/valorant-vct-predictor`. Local `bash` remains unavailable, so PowerShell wrappers are required.
- blockers: None at initialization.
- status: in_progress
- next steps: Create docs, config, runtime code, tests, then run local verification.

## 2026-04-22T20:27:00Z | agent=codex | role=implementation
- objective: Finish Phase 1, validate locally, sync to `kyber`, and leave the downloader running remotely in the background.
- files created: Repository skeleton, governance docs, config files, scripts, runtime modules, fixtures, and tests.
- files modified: `README.md`, `memory.md`.
- decisions: Initialized git in the project root, pushed the full Phase 1 repo rather than only `README.md`, synced code to `/home/Lowgo/valorant-vct-predictor`, and kept only the detached `nohup` pipeline process on `kyber`.
- assumptions: Remote cached raw data and state on `kyber` are canonical and may already contain prior pages from earlier attempts.
- blockers: Git push still depends on local credentials and remote repository access succeeding from this machine.
- status: running_on_kyber
- next steps: Commit and push the repo, then pull logs and manifests from `kyber` as needed while the background downloader continues.
