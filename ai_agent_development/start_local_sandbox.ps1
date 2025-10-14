# Copyright (c) 2024-2025, NVIDIA CORPORATION.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Usage: .\start_local_sandbox.ps1 [SANDBOX_NAME] [OUTPUT_DATA_PATH]
# NOTE: can run from ai_agent_development directory!

param(
    [string]$SANDBOX_NAME = 'local-sandbox',
    [string]$OUTPUT_DATA_PATH = $null,
    [string]$DOCKER_COMMAND = 'docker'
)

$NUM_THREADS = 10

# Get the output_data directory path for mounting
# Priority: command line argument > environment variable > default path (current directory)
if ($null -eq $OUTPUT_DATA_PATH -or $OUTPUT_DATA_PATH -eq "") {
    if ($env:OUTPUT_DATA_PATH) {
        $OUTPUT_DATA_PATH = $env:OUTPUT_DATA_PATH
    } else {
        $OUTPUT_DATA_PATH = Get-Location
    }
}

Write-Host "Starting sandbox with container name: $SANDBOX_NAME"
Write-Host "Mounting output_data directory: $OUTPUT_DATA_PATH"

# Verify the path exists before mounting, create if it doesn't
if (-not (Test-Path $OUTPUT_DATA_PATH)) {
    Write-Host "Output data directory does not exist, creating: $OUTPUT_DATA_PATH"
    New-Item -ItemType Directory -Path $OUTPUT_DATA_PATH -Force | Out-Null
}

# Check if the Docker image already exists
$imageExists = & $DOCKER_COMMAND images $SANDBOX_NAME 2>$null | Select-String $SANDBOX_NAME

if (-not $imageExists) {
    Write-Host "Docker image not found locally. Building $SANDBOX_NAME..."
    
    # Check if Dockerfile.sandbox exists in current directory
    if (-not (Test-Path "Dockerfile.sandbox")) {
        Write-Error "Dockerfile.sandbox not found in current directory. Please ensure you're running from the correct location."
        exit 1
    }
    
    $buildArgs = @(
        "build",
        "--tag=$SANDBOX_NAME",
        "--build-arg=UWSGI_PROCESSES=$($NUM_THREADS * 10)",
        "--build-arg=UWSGI_CHEAPER=$NUM_THREADS",
        "-f", "Dockerfile.sandbox",
        "."
    )
    & $DOCKER_COMMAND $buildArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to build Docker image"
        exit 1
    }
} else {
    Write-Host "Using existing Docker image: $SANDBOX_NAME"
}

# Stop and remove existing container if it exists
$existingContainer = & $DOCKER_COMMAND ps -a --filter "name=local-sandbox" --format "{{.Names}}" 2>$null
if ($existingContainer -eq "local-sandbox") {
    Write-Host "Stopping existing container..."
    & $DOCKER_COMMAND stop local-sandbox 2>$null
    & $DOCKER_COMMAND rm local-sandbox 2>$null
}

# Convert Windows path to Docker-compatible path
$dockerPath = $OUTPUT_DATA_PATH -replace '\\', '/'
if ($dockerPath -match '^[A-Za-z]:') {
    $driveLetter = $dockerPath.Substring(0,1).ToLower()
    $dockerPath = "/$driveLetter" + $dockerPath.Substring(2)
}

# Mount the output_data directory directly so files created in container appear in the local directory
$runArgs = @(
    "run", "--rm", "--name=local-sandbox",
    "-p", "6000:6000",
    "-v", "${dockerPath}:/workspace",
    "-w", "/workspace",
    $SANDBOX_NAME
)

Write-Host "Starting Docker container with command: $DOCKER_COMMAND $($runArgs -join ' ')"
& $DOCKER_COMMAND $runArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to start sandbox container"
    exit 1
}
