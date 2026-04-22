#!/usr/bin/env bash
set -euo pipefail

VM_NAME="${VM_NAME:-kyber}"
ZONE="${ZONE:-us-central1-f}"
REMOTE_ROOT="${REMOTE_ROOT:-/home/Lowgo/valorant-vct-predictor}"

remote_cmd="
set -euo pipefail
cd '$REMOTE_ROOT'
mkdir -p data/raw/html/listings data/raw/html/events data/raw/html/matches
mkdir -p data/raw/json/listings data/raw/json/events data/raw/json/matches
mkdir -p data/raw/indexes data/raw/manifests data/state data/logs
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m src.main --config configs/pipeline.yaml
"

gcloud compute ssh "$VM_NAME" --zone "$ZONE" --command "$remote_cmd"
