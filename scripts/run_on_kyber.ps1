$ErrorActionPreference = "Stop"

$vmName = if ($env:VM_NAME) { $env:VM_NAME } else { "kyber" }
$zone = if ($env:ZONE) { $env:ZONE } else { "us-central1-f" }
$remoteRoot = if ($env:REMOTE_ROOT) { $env:REMOTE_ROOT } else { "/home/Lowgo/valorant-vct-predictor" }

$remoteCommand = @"
set -euo pipefail
cd '$remoteRoot'
mkdir -p data/raw/html/listings data/raw/html/events data/raw/html/matches
mkdir -p data/raw/json/listings data/raw/json/events data/raw/json/matches
mkdir -p data/raw/indexes data/raw/manifests data/state data/logs
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m src.main --config configs/pipeline.yaml
"@

gcloud compute ssh $vmName --zone $zone --command $remoteCommand
