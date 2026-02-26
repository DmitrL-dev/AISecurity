# SENTINEL AI Security Platform — PowerShell Installer
# Usage: irm https://raw.githubusercontent.com/DmitrL-dev/AISecurity/main/install.ps1 | iex

param(
    [switch]$Lite,
    [switch]$Full,
    [switch]$Dev,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

function Write-Banner {
    Write-Host ""
    Write-Host "  SENTINEL AI Security Platform" -ForegroundColor Cyan
    Write-Host "  209 Detection Engines | Strange Math" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Help {
    Write-Host "SENTINEL AI Security Platform - Installer" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage: .\install.ps1 [-Lite] [-Full] [-Dev] [-Help]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Lite   Python only (pip install)"
    Write-Host "  -Full   Docker stack (default)"
    Write-Host "  -Dev    Development mode"
    Write-Host "  -Help   Show this help"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\install.ps1 -Lite"
    Write-Host "  .\install.ps1 -Full"
}

function Install-Lite {
    Write-Host "[STEP] Installing SENTINEL Lite (Python only)..." -ForegroundColor Blue
    
    # Check Python
    try {
        $pythonVersion = python --version 2>&1
        Write-Host "[INFO] $pythonVersion" -ForegroundColor Green
    }
    catch {
        Write-Host "[ERROR] Python not found. Install from https://python.org" -ForegroundColor Red
        exit 1
    }
    
    $installDir = "$env:USERPROFILE\sentinel"
    
    # Create venv
    Write-Host "[INFO] Creating virtual environment..." -ForegroundColor Green
    python -m venv "$installDir\venv"
    
    # Activate and install
    & "$installDir\venv\Scripts\Activate.ps1"
    pip install --upgrade pip
    pip install sentinel-llm-security
    
    # Download signatures
    Write-Host "[INFO] Downloading signatures..." -ForegroundColor Green
    New-Item -ItemType Directory -Force -Path "$installDir\signatures" | Out-Null
    Invoke-WebRequest -Uri "https://cdn.jsdelivr.net/gh/DmitrL-dev/AISecurity@main/sentinel-community/signatures/jailbreaks-manifest.json" -OutFile "$installDir\signatures\manifest.json"
    
    Write-Host ""
    Write-Host "SENTINEL Lite installed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Quick start:" -ForegroundColor Yellow
    Write-Host "  $installDir\venv\Scripts\Activate.ps1"
    Write-Host "  python -c `"from sentinel import analyze; print(analyze('test'))`""
}

function Install-Full {
    Write-Host "[STEP] Installing SENTINEL Full (Docker)..." -ForegroundColor Blue
    
    # Check Docker
    try {
        docker --version | Out-Null
        Write-Host "[INFO] Docker found" -ForegroundColor Green
    }
    catch {
        Write-Host "[ERROR] Docker not found. Install Docker Desktop" -ForegroundColor Red
        exit 1
    }
    
    $installDir = "$env:USERPROFILE\sentinel"
    
    # Clone
    Write-Host "[INFO] Cloning repository..." -ForegroundColor Green
    git clone --depth 1 https://github.com/DmitrL-dev/AISecurity.git $installDir
    
    # Start
    Set-Location "$installDir\sentinel-community"
    docker compose -f docker-compose.full.yml up -d
    
    Write-Host ""
    Write-Host "SENTINEL installed!" -ForegroundColor Green
    Write-Host "   Dashboard: http://localhost:3000"
    Write-Host "   API: http://localhost:8080"
}

function Install-Dev {
    Write-Host "[INFO] Development mode - clone and pip install" -ForegroundColor Green
    $installDir = "$env:USERPROFILE\sentinel"
    git clone --depth 1 https://github.com/DmitrL-dev/AISecurity.git $installDir
    Set-Location "$installDir\sentinel-community"
    pip install -r requirements.txt
    Write-Host "Dev environment ready!" -ForegroundColor Green
}

# Main
Write-Banner

if ($Help) {
    Write-Help
    exit 0
}

if ($Lite) {
    Install-Lite
}
elseif ($Dev) {
    Install-Dev
}
else {
    Install-Full
}
