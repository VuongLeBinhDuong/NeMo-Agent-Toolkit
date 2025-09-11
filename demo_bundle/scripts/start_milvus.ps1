param()
$ErrorActionPreference = 'Stop'

# Start Milvus using demo_milvus.yml inside demo_bundle
$bundleRoot = Split-Path $PSScriptRoot -Parent
Push-Location $bundleRoot
Write-Host "Starting Milvus using demo_milvus.yml in $bundleRoot" -ForegroundColor Cyan
# Ensure 'milvus' docker network exists (compose expects an external network)
$netExists = docker network ls --format '{{.Name}}' | Select-String -SimpleMatch 'milvus'
if (-not $netExists) {
    Write-Host "Creating docker network 'milvus'" -ForegroundColor Yellow
    & docker network create milvus | Out-Host
}
# Stop and remove any existing containers defined in compose to avoid name conflicts
& docker compose -f .\demo_milvus.yml down --remove-orphans | Out-Host

# Force remove any lingering containers with conflicting names from previous runs
$containersToClean = @('milvus-etcd','milvus-minio','milvus-standalone')
foreach ($name in $containersToClean) {
    $exists = docker ps -a --format '{{.Names}}' | Select-String -SimpleMatch $name
    if ($exists) {
        Write-Host "Removing existing container $name" -ForegroundColor Yellow
        & docker rm -f $name | Out-Host
    }
}

# Bring services up
& docker compose -f .\demo_milvus.yml up -d | Out-Host

# Wait for Milvus to become healthy
Write-Host "Waiting for Milvus health endpoint..." -ForegroundColor Cyan
$deadline = (Get-Date).AddMinutes(3)
do {
    try {
        $resp = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:9091/healthz' -TimeoutSec 5
        if ($resp.StatusCode -eq 200) { break }
    } catch { Start-Sleep -Seconds 2 }
} while ((Get-Date) -lt $deadline)

try {
    $resp = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:9091/healthz' -TimeoutSec 5
    if ($resp.StatusCode -eq 200) {
        Write-Host "Milvus is healthy" -ForegroundColor Green
    } else {
        throw "Milvus health check failed"
    }
} catch {
    Write-Warning "Milvus did not report healthy within timeout. You may need to check logs: docker compose -f .\demo_milvus.yml logs --no-color | cat"
}

