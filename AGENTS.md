# AGENTS

## Mission

Build a small, explicit, reproducible Valorant VCT research codebase. Phase 1 is only about repository standards, project memory, VM protocol, and resumable raw VLR.gg acquisition.

## Principles

- Always work from first principles.
- Always try to delete and simplify.
- Prefer fewer files, fewer abstractions, and fewer dependencies.
- Keep behavior explicit.
- Preserve raw source material.
- Fail loudly, record why, and resume safely.

## Agent Rules

- Read the current repo state before editing.
- Keep changes narrow and explain real decisions in code and docs.
- Do not add frameworks, background workers, async layers, or generic scraping infrastructure.
- Do not add new runtime modes unless the existing single pipeline entrypoint cannot support the need.
- Append a new structured entry to `memory.md` after every meaningful run or handoff.
- Never overwrite another agent's work without understanding it first.

## File Ownership

- Root docs define project rules and must stay concise.
- `src/` owns runtime behavior only.
- `tests/` stays small and protects core behavior.
- `data/` is runtime state and stays out of git.
- If two agents need the same file, one agent should land the shared interface first and the other should build against it.

## Run Procedure

1. Make code and doc changes locally.
2. Run local validation only: config checks, unit tests, fixture-based smoke tests.
3. Sync code to `kyber`.
4. Run real downloads on `kyber`.
5. Pull logs and manifests back if needed.
6. Append the outcome to `memory.md`.

## VM Rules

- The only approved VM is `kyber`.
- Do not run real scraping locally.
- Do not assume `git` exists on `kyber`.
- Use `gcloud compute scp` and `gcloud compute ssh`.
- Preserve remote `data/` so resume state and cached raw pages survive syncs.

## Sync Protocol

- Sync only code, docs, configs, scripts, and tests.
- Never sync `data/` from local to remote.
- Treat `/home/Lowgo/valorant-vct-predictor` on `kyber` as the remote project root.
- Logs, manifests, and state are expected to accumulate on the VM.

## Handoff Procedure

Every handoff must include:

- current objective
- files created or modified
- important decisions
- assumptions
- blockers
- exact next steps

Put this in `memory.md` as a new timestamped entry.

## Definition of Done

Phase 1 work is done when:

- the single pipeline entrypoint works
- caching and resume are explicit
- runs leave behind logs, state, and manifests
- remote execution on `kyber` is the standard path for real downloads
- the repo stays small and understandable
