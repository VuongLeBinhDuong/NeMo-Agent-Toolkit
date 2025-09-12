param(
  [string]$DataDir,
  [string]$MilvusUri
)
$ErrorActionPreference = 'Stop'

# Resolve repo root and env path
$bundleRoot = Split-Path $PSScriptRoot -Parent
$repoRoot = Split-Path $bundleRoot -Parent
$envPath = Join-Path $bundleRoot '.env'

# Helper to read key from .env
function Get-DotEnvValue {
  param([string]$Path, [string]$Key)
  if (-not (Test-Path $Path)) { return $null }
  $line = Get-Content $Path | Select-String ("^$Key=") | Select-Object -First 1
  if (-not $line) { return $null }
  $val = $line.ToString().Substring($Key.Length + 1)
  return $val.Trim()
}

# Read defaults from .env if present
if (Test-Path $envPath) {
  if (-not $DataDir) { $DataDir = Get-DotEnvValue -Path $envPath -Key 'DATA_DIR' }
  if (-not $MilvusUri) { $MilvusUri = Get-DotEnvValue -Path $envPath -Key 'MILVUS_URI' }
  $nvKey = Get-DotEnvValue -Path $envPath -Key 'NVIDIA_API_KEY'
  if ($nvKey) { $env:NVIDIA_API_KEY = $nvKey }
}

if (-not $DataDir) { $DataDir = Join-Path $bundleRoot 'data' }
if (-not $MilvusUri) { $MilvusUri = 'http://localhost:19530' }

$ingestScript = Join-Path (Join-Path $bundleRoot 'scripts') 'ingest_documents_to_mydocs.py'

if (-not (Test-Path $ingestScript)) { throw "Ingest script not found: $ingestScript" }
if (-not (Test-Path $DataDir)) { New-Item -ItemType Directory -Path $DataDir | Out-Null }

# Ingest documents in order: DOCX, Excel, then others to manage schema conflicts
$files = @()
$files += Get-ChildItem -Path $DataDir -Filter *.docx -Recurse -ErrorAction SilentlyContinue
$files += Get-ChildItem -Path $DataDir -Filter *.xlsx -Recurse -ErrorAction SilentlyContinue
$files += Get-ChildItem -Path $DataDir -Filter *.csv -Recurse -ErrorAction SilentlyContinue
$files += Get-ChildItem -Path $DataDir -Filter *.pdf -Recurse -ErrorAction SilentlyContinue

if (-not $files) {
  Write-Warning "No PDF, DOCX, XLSX, or CSV files found in '$DataDir'. Add document files to this folder and re-run."
  exit 0
}

foreach ($f in $files) {
  Write-Host "Ingesting $($f.FullName) -> Milvus $MilvusUri (collection: my_docs)" -ForegroundColor Cyan
  & python $ingestScript $f.FullName --uri $MilvusUri --collection my_docs | Out-Host
}
