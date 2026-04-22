$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$vmName = if ($env:VM_NAME) { $env:VM_NAME } else { "kyber" }
$zone = if ($env:ZONE) { $env:ZONE } else { "us-central1-f" }
$remoteRoot = if ($env:REMOTE_ROOT) { $env:REMOTE_ROOT } else { "/home/Lowgo/valorant-vct-predictor" }

$items = @(
  "README.md",
  "AGENTS.md",
  "guidelines.md",
  "memory.md",
  ".gitignore",
  "requirements.txt",
  "configs",
  "docs",
  "scripts",
  "src",
  "tests"
)

Push-Location $projectRoot
try {
  gcloud compute ssh $vmName --zone $zone --command "mkdir -p '$remoteRoot'"
  foreach ($item in $items) {
    gcloud compute scp --recurse --zone $zone $item ("{0}:{1}/" -f $vmName, $remoteRoot)
  }
}
finally {
  Pop-Location
}
