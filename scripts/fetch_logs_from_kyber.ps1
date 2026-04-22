$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$vmName = if ($env:VM_NAME) { $env:VM_NAME } else { "kyber" }
$zone = if ($env:ZONE) { $env:ZONE } else { "us-central1-f" }
$remoteRoot = if ($env:REMOTE_ROOT) { $env:REMOTE_ROOT } else { "/home/Lowgo/valorant-vct-predictor" }

New-Item -ItemType Directory -Force -Path (Join-Path $projectRoot "data/logs") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $projectRoot "data/raw/manifests") | Out-Null

Push-Location $projectRoot
try {
  gcloud compute scp --recurse --zone $zone ("{0}:{1}/data/logs" -f $vmName, $remoteRoot) "data/"
  gcloud compute scp --recurse --zone $zone ("{0}:{1}/data/raw/manifests" -f $vmName, $remoteRoot) "data/raw/"
}
finally {
  Pop-Location
}
