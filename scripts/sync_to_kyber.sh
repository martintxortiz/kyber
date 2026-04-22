#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VM_NAME="${VM_NAME:-kyber}"
ZONE="${ZONE:-us-central1-f}"
REMOTE_ROOT="${REMOTE_ROOT:-/home/Lowgo/valorant-vct-predictor}"

items=(
  "README.md"
  "AGENTS.md"
  "guidelines.md"
  "memory.md"
  ".gitignore"
  "requirements.txt"
  "configs"
  "docs"
  "scripts"
  "src"
  "tests"
)

cd "$ROOT_DIR"
gcloud compute ssh "$VM_NAME" --zone "$ZONE" --command "mkdir -p '$REMOTE_ROOT'"

for item in "${items[@]}"; do
  gcloud compute scp --recurse --zone "$ZONE" "$item" "${VM_NAME}:${REMOTE_ROOT}/"
done
