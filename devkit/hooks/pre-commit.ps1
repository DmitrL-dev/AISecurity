# SENTINEL DevKit Pre-commit Hook (PowerShell)
# Enforces TDD Iron Law and basic quality checks

$ErrorActionPreference = "Continue"

Write-Host "🔍 SENTINEL DevKit Pre-commit Check..." -ForegroundColor Cyan

$Errors = 0

# === Check 1: TDD Iron Law ===
Write-Host ""
Write-Host "📋 Check 1: TDD Iron Law" -ForegroundColor White

$StagedFiles = git diff --cached --name-only
$StagedSrc = $StagedFiles | Where-Object { $_ -match "^src/" }
$StagedTests = $StagedFiles | Where-Object { $_ -match "test_|_test\.py|tests/" }

if ($StagedSrc -and -not $StagedTests) {
    Write-Host "❌ TDD Iron Law Violation!" -ForegroundColor Red
    Write-Host "   Production code changed without test changes."
    Write-Host "   Changed src files:"
    $StagedSrc | ForEach-Object { Write-Host "   - $_" }
    Write-Host ""
    Write-Host "   Add tests before committing or use --no-verify to bypass (NOT RECOMMENDED)"
    $Errors++
} else {
    Write-Host "✅ TDD Iron Law: OK" -ForegroundColor Green
}

# === Check 2: No Debug Code ===
Write-Host ""
Write-Host "📋 Check 2: Debug Code Check" -ForegroundColor White

$DebugPatterns = "console\.log|print\(|debugger|import pdb|breakpoint\(\)"
$DebugFiles = @()

foreach ($file in $StagedFiles) {
    if (Test-Path $file) {
        $content = Get-Content $file -Raw -ErrorAction SilentlyContinue
        if ($content -match $DebugPatterns) {
            $DebugFiles += $file
        }
    }
}

if ($DebugFiles.Count -gt 0) {
    Write-Host "⚠️ Warning: Debug code detected" -ForegroundColor Yellow
    $DebugFiles | ForEach-Object { Write-Host "   - $_" }
    Write-Host "   Consider removing before commit."
    # Warning only, not blocking
} else {
    Write-Host "✅ Debug Code: OK" -ForegroundColor Green
}

# === Check 3: No Hardcoded Secrets ===
Write-Host ""
Write-Host "📋 Check 3: Secrets Check" -ForegroundColor White

$SecretPatterns = "password\s*=|api_key\s*=|secret\s*=|token\s*="
$SecretsFound = $false

$Diff = git diff --cached -U0
$AddedLines = $Diff | Where-Object { $_ -match "^\+" }

foreach ($line in $AddedLines) {
    if ($line -match $SecretPatterns) {
        if (-not $SecretsFound) {
            Write-Host "❌ Potential hardcoded secrets detected!" -ForegroundColor Red
            $SecretsFound = $true
        }
        Write-Host "   $line"
    }
}

if ($SecretsFound) {
    Write-Host "   Review and remove before committing."
    $Errors++
} else {
    Write-Host "✅ Secrets Check: OK" -ForegroundColor Green
}

# === Check 4: Python Syntax ===
Write-Host ""
Write-Host "📋 Check 4: Python Syntax" -ForegroundColor White

$PythonFiles = $StagedFiles | Where-Object { $_ -match "\.py$" }
$SyntaxErrors = 0

foreach ($file in $PythonFiles) {
    if (Test-Path $file) {
        $result = python -m py_compile $file 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Syntax error in $file" -ForegroundColor Red
            $SyntaxErrors++
        }
    }
}

if ($SyntaxErrors -eq 0) {
    Write-Host "✅ Python Syntax: OK" -ForegroundColor Green
} else {
    $Errors += $SyntaxErrors
}

# === Summary ===
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

if ($Errors -gt 0) {
    Write-Host "❌ Pre-commit failed with $Errors error(s)" -ForegroundColor Red
    Write-Host "   Fix issues or use 'git commit --no-verify' to bypass"
    exit 1
} else {
    Write-Host "✅ All checks passed!" -ForegroundColor Green
    exit 0
}
