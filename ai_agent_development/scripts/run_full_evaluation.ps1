param(
    [string]$ConfigFile = "ai_agent_development\eval_config.yml",
    [switch]$SkipIngestion,
    [switch]$GenerateReport
)

$ErrorActionPreference = 'Stop'

Write-Host "🔍 Demo Bundle Full Evaluation Pipeline" -ForegroundColor Cyan
Write-Host "=" * 50

# Step 1: Verify Milvus is running
Write-Host "`n1️⃣ Checking Milvus service..." -ForegroundColor Yellow
try {
    $resp = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:9091/healthz' -TimeoutSec 5
    if ($resp.StatusCode -eq 200) {
        Write-Host "✅ Milvus is healthy" -ForegroundColor Green
    } else {
        throw "Milvus health check failed"
    }
} catch {
    Write-Host "❌ Milvus not available. Starting Milvus..." -ForegroundColor Red
    & PowerShell -NoProfile -ExecutionPolicy Bypass -File ai_agent_development\scripts\start_milvus.ps1
}

# Step 2: Ensure documents are ingested (unless skipped)
if (-not $SkipIngestion) {
    Write-Host "`n2️⃣ Checking document ingestion..." -ForegroundColor Yellow
    
    # Check if collection has documents
    try {
        $pythonCheck = @"
import pymilvus
from pymilvus import connections, Collection

try:
    connections.connect(host='localhost', port='19530')
    collection = Collection('my_docs')
    count = collection.num_entities
    print(f'Documents in collection: {count}')
    if count == 0:
        exit(1)
except Exception as e:
    print(f'Error: {e}')
    exit(1)
"@
        
        $result = python -c $pythonCheck
        Write-Host "✅ $result" -ForegroundColor Green
        
    } catch {
        Write-Host "⚠️ No documents found. Running ingestion..." -ForegroundColor Yellow
        & PowerShell -NoProfile -ExecutionPolicy Bypass -File ai_agent_development\scripts\demo_ingest.ps1
    }
} else {
    Write-Host "`n2️⃣ Skipping document ingestion (--SkipIngestion)" -ForegroundColor Gray
}

# Step 3: Check NVIDIA API key
Write-Host "`n3️⃣ Verifying NVIDIA API key..." -ForegroundColor Yellow
if (-not $env:NVIDIA_API_KEY) {
    Write-Host "❌ NVIDIA_API_KEY not set!" -ForegroundColor Red
    Write-Host "Please set your API key: `$env:NVIDIA_API_KEY='your_key_here'" -ForegroundColor Yellow
    exit 1
} else {
    $keyPrefix = $env:NVIDIA_API_KEY.Substring(0, [Math]::Min(8, $env:NVIDIA_API_KEY.Length))
    Write-Host "✅ API key configured ($keyPrefix...)" -ForegroundColor Green
}

# Step 4: Create output directory
Write-Host "`n4️⃣ Preparing evaluation environment..." -ForegroundColor Yellow
$outputDir = "ai_agent_development\eval\output"
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    Write-Host "✅ Created output directory: $outputDir" -ForegroundColor Green
} else {
    Write-Host "✅ Output directory ready: $outputDir" -ForegroundColor Green
}

# Step 5: Run evaluation
Write-Host "`n5️⃣ Running NAT evaluation..." -ForegroundColor Yellow
Write-Host "Config: $ConfigFile" -ForegroundColor Gray
Write-Host "This may take several minutes..." -ForegroundColor Gray

try {
    & nat eval --config_file=$ConfigFile
    Write-Host "✅ Evaluation completed successfully!" -ForegroundColor Green
} catch {
    Write-Host "❌ Evaluation failed!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Step 6: Generate detailed report (if requested)
if ($GenerateReport) {
    Write-Host "`n6️⃣ Generating detailed analysis report..." -ForegroundColor Yellow
    try {
        & python ai_agent_development\eval\run_evaluation.py --output_dir $outputDir
        Write-Host "✅ Analysis report generated!" -ForegroundColor Green
    } catch {
        Write-Host "⚠️ Report generation failed, but evaluation data is available in $outputDir" -ForegroundColor Yellow
    }
} else {
    Write-Host "`n6️⃣ Skipping detailed report (use --GenerateReport to enable)" -ForegroundColor Gray
}

# Step 7: Display summary
Write-Host "`n🎯 EVALUATION COMPLETE!" -ForegroundColor Cyan
Write-Host "=" * 50
Write-Host "📁 Results location: $outputDir" -ForegroundColor White
Write-Host "📊 View detailed scores in the output JSON files" -ForegroundColor White

if ($GenerateReport) {
    $reportFiles = Get-ChildItem -Path $outputDir -Filter "evaluation_report_*.md" | Sort-Object LastWriteTime -Descending
    if ($reportFiles) {
        $latestReport = $reportFiles[0]
        Write-Host "📄 Latest report: $($latestReport.FullName)" -ForegroundColor White
    }
}

Write-Host "`n💡 Tips:" -ForegroundColor Yellow
Write-Host "  - Review questions.jsonl to add more test cases" -ForegroundColor Gray
Write-Host "  - Adjust eval_config.yml for different metrics" -ForegroundColor Gray  
Write-Host "  - Use --GenerateReport for detailed analysis" -ForegroundColor Gray
Write-Host "  - Monitor scores over time for quality regression" -ForegroundColor Gray
