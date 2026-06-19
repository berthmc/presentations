# Start Windows Ollama (if needed) and the pptx Docker stack.
# Usage: .\scripts\start-pptx-stack.ps1 [-Detached] [-Profile gpu]

param(
    [switch]$Detached,
    [string]$Profile = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $RepoRoot "docker\docker-compose.yml"

function Test-OllamaReady {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 3
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Start-OllamaIfNeeded {
    if (Test-OllamaReady) {
        Write-Host "Ollama is already running on http://localhost:11434"
        return
    }

    Write-Host "Starting Ollama (Windows client)..."
    $ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($ollamaCmd) {
        Start-Process -FilePath $ollamaCmd.Source -ArgumentList "serve" -WindowStyle Hidden
    } else {
        $appPath = Join-Path $env:LOCALAPPDATA "Programs\Ollama\Ollama.exe"
        if (-not (Test-Path $appPath)) {
            throw "Ollama not found. Install the Windows client from https://ollama.com or add ollama to PATH."
        }
        Start-Process -FilePath $appPath
    }

    for ($attempt = 1; $attempt -le 30; $attempt++) {
        Start-Sleep -Seconds 2
        if (Test-OllamaReady) {
            Write-Host "Ollama is ready."
            return
        }
    }

    throw "Ollama did not respond on http://localhost:11434 within 60 seconds."
}

Start-OllamaIfNeeded

$composeArgs = @("-f", $ComposeFile)
if ($Profile) {
    $composeArgs += @("--profile", $Profile)
}
if ($Detached) {
    $composeArgs += "up", "-d", "--build"
} else {
    $composeArgs += "up", "--build"
}

Write-Host "Starting Docker stack..."
Push-Location $RepoRoot
try {
    & docker compose @composeArgs
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}
