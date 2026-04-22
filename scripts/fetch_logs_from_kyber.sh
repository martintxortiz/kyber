#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VM_NAME="${VM_NAME:-kyber}"
ZONE="${ZONE:-us-central1-f}"
REMOTE_ROOT="${REMOTE_ROOT:-/home/Lowgo/valorant-vct-predictor}"

mkdir -p "$ROOT_DIR/data/logs" "$ROOT_DIR/data/raw/manifests"

gcloud compute scp --recurse --zone "$ZONE" "${VM_NAME}:${REMOTE_ROOT}/data/logs" "$ROOT_DIR/data/"
gcloud compute scp --recurse --zone "$ZONE" "${VM_NAME}:${REMOTE_ROOT}/data/raw/manifests" "$ROOT_DIR/data/raw/"
