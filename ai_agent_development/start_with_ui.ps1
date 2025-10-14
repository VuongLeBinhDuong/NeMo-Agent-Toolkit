# SPDX-FileCopyrightText: Copyright (c) 2024-2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# PowerShell script to start NeMo Agent Toolkit with UI and custom file upload

param(
    [string]$Port = "8000",
    [string]$Host = "localhost"
)

$ErrorActionPreference = 'Stop'

Write-Host "🚀 Starting NeMo Agent Toolkit with Custom File Upload" -ForegroundColor Green
Write-Host "📁 Files will be saved to: ai_agent_development/data/uploaded" -ForegroundColor Cyan
Write-Host "🌐 Server will be available at: http://$Host`:$Port" -ForegroundColor Cyan
Write-Host "🎨 UI will be available at: http://$Host`:$Port/ui" -ForegroundColor Cyan

# Check if we're in the right directory
if (-not (Test-Path "ai_agent_development")) {
    Write-Error "Please run this script from the project root directory"
    exit 1
}

# Set environment variables
if (-not $env:NVIDIA_API_KEY -or $env:NVIDIA_API_KEY -eq "your-api-key-here") {
    Write-Host "⚠️  NVIDIA_API_KEY not set or using default value" -ForegroundColor Yellow
    Write-Host "Please set your API key first:" -ForegroundColor Red
    Write-Host "  .\ai_agent_development\setup_api_key.ps1 -ApiKey 'your-actual-api-key'" -ForegroundColor Cyan
    Write-Host "Or set it manually: `$env:NVIDIA_API_KEY = 'your-api-key'" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Continuing with default key (may cause ingest failures)..." -ForegroundColor Yellow
}

$env:NVIDIA_API_KEY = if ($env:NVIDIA_API_KEY) { $env:NVIDIA_API_KEY } else { "your-api-key-here" }

# Create uploaded directory
$uploadDir = "ai_agent_development/data"
if (-not (Test-Path $uploadDir)) {
    New-Item -ItemType Directory -Path $uploadDir -Force | Out-Null
    Write-Host "✅ Created upload directory: $uploadDir" -ForegroundColor Green
}

# Start the server with RAG workflow
try {
    Write-Host "Starting NeMo Agent Toolkit server with RAG workflow..." -ForegroundColor Yellow
    nat serve --config_file ai_agent_development/workflow.yaml
}
catch {
    Write-Error "Failed to start server: $_"
    exit 1
}
