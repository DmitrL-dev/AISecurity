# Pre-Exec Guard Hook

<#
.SYNOPSIS
    Security guard for command execution in AI agents

.DESCRIPTION
    Validates commands before execution, blocks dangerous patterns,
    and enforces financial transaction limits.

.PARAMETER Command
    The command to validate

.PARAMETER Context
    Optional context (user, session, etc.)

.EXAMPLE
    ./pre-exec-guard.ps1 -Command "npm install lodash"
    # Returns: exit 0 (allowed)

.EXAMPLE
    ./pre-exec-guard.ps1 -Command ":(){ :|:& };:"
    # Returns: exit 1 (blocked - fork bomb)
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$Command,
    
    [Parameter(Mandatory=$false)]
    [string]$Context = "default"
)

# ============================================
# CONFIGURATION
# ============================================

$Config = @{
    MaxTransactionAmount = 50  # USD
    RequireApprovalForFinancial = $true
    LogPath = "$env:USERPROFILE\.sentinel\exec-guard.log"
    BlockedPatterns = @()
    FinancialPatterns = @()
}

# ============================================
# BLOCKED PATTERNS (CRITICAL)
# ============================================

$Config.BlockedPatterns = @(
    # A01: Fork bombs
    @{ Pattern = ":\(\)\s*\{.*\|.*&\s*\}\s*;"; Name = "Fork bomb (bash)" }
    @{ Pattern = "%0\|%0"; Name = "Fork bomb (Windows)" }
    
    # A02: Reverse shells
    @{ Pattern = "bash\s+-i\s+>&\s+/dev/tcp"; Name = "Reverse shell (bash)" }
    @{ Pattern = "nc\s+-e\s+/bin/(ba)?sh"; Name = "Reverse shell (netcat)" }
    @{ Pattern = "python.*socket.*connect.*dup2"; Name = "Reverse shell (Python)" }
    @{ Pattern = "New-Object\s+Net\.Sockets\.TCPClient"; Name = "Reverse shell (PowerShell)" }
    
    # A03: Credential exfiltration
    @{ Pattern = "curl.*\.ssh/id_rsa"; Name = "SSH key exfil" }
    @{ Pattern = "curl.*\.aws"; Name = "AWS creds exfil" }
    @{ Pattern = "curl.*\.gnupg"; Name = "GPG key exfil" }
    
    # A04: Destructive commands
    @{ Pattern = "rm\s+-rf\s+/(?!tmp)"; Name = "Recursive delete root" }
    @{ Pattern = "format\s+c:"; Name = "Format drive" }
    @{ Pattern = "dd\s+if=.*of=/dev/[sh]d"; Name = "Disk overwrite" }
    
    # A05: Eval/exec piping
    @{ Pattern = "curl.*\|\s*(ba)?sh"; Name = "curl | sh" }
    @{ Pattern = "wget.*\|\s*(ba)?sh"; Name = "wget | sh" }
    @{ Pattern = "iex\s*\(.*DownloadString"; Name = "PowerShell download+exec" }
    
    # A06: Cron/task persistence
    @{ Pattern = "crontab\s+-"; Name = "Crontab modification" }
    @{ Pattern = "schtasks\s+/create"; Name = "Scheduled task creation" }
)

# ============================================
# FINANCIAL PATTERNS (REQUIRE APPROVAL)
# ============================================

$Config.FinancialPatterns = @(
    @{ Pattern = "stripe"; Name = "Stripe payment" }
    @{ Pattern = "paypal"; Name = "PayPal payment" }
    @{ Pattern = "checkout"; Name = "Checkout process" }
    @{ Pattern = "purchase"; Name = "Purchase operation" }
    @{ Pattern = "subscribe"; Name = "Subscription" }
    @{ Pattern = "mastermind"; Name = "Mastermind program" }  # The $7000 lesson!
    @{ Pattern = "buy|order"; Name = "Buy/Order operation" }
    @{ Pattern = "credit.?card"; Name = "Credit card operation" }
)

# ============================================
# LOGGING
# ============================================

function Write-ExecLog {
    param(
        [string]$Level,
        [string]$Message,
        [string]$Command
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logDir = Split-Path $Config.LogPath -Parent
    
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    
    $logEntry = "$timestamp [$Level] Command: $Command | $Message"
    Add-Content -Path $Config.LogPath -Value $logEntry
    
    # RLM Integration (if available)
    # rlm_add_hierarchical_fact -content $logEntry -level 1 -domain "clawdbot-blocked"
}

# ============================================
# VALIDATION
# ============================================

function Test-BlockedPattern {
    param([string]$Command)
    
    foreach ($pattern in $Config.BlockedPatterns) {
        if ($Command -match $pattern.Pattern) {
            return @{
                Blocked = $true
                Name = $pattern.Name
                Pattern = $pattern.Pattern
            }
        }
    }
    
    return @{ Blocked = $false }
}

function Test-FinancialPattern {
    param([string]$Command)
    
    foreach ($pattern in $Config.FinancialPatterns) {
        if ($Command -match $pattern.Pattern) {
            return @{
                IsFinancial = $true
                Name = $pattern.Name
            }
        }
    }
    
    return @{ IsFinancial = $false }
}

function Request-Approval {
    param(
        [string]$Operation,
        [string]$Reason
    )
    
    Write-Host ""
    Write-Host "⚠️  APPROVAL REQUIRED" -ForegroundColor Yellow
    Write-Host "Operation: $Operation" -ForegroundColor Cyan
    Write-Host "Reason: $Reason" -ForegroundColor Gray
    Write-Host ""
    
    $response = Read-Host "Approve? (yes/no)"
    
    return $response -eq "yes" -or $response -eq "y"
}

# ============================================
# MAIN EXECUTION
# ============================================

# 1. Check blocked patterns
$blockResult = Test-BlockedPattern -Command $Command

if ($blockResult.Blocked) {
    Write-Host ""
    Write-Host "❌ BLOCKED: $($blockResult.Name)" -ForegroundColor Red
    Write-Host "Pattern: $($blockResult.Pattern)" -ForegroundColor Gray
    Write-Host "Command: $Command" -ForegroundColor Gray
    Write-Host ""
    
    Write-ExecLog -Level "BLOCKED" -Message $blockResult.Name -Command $Command
    exit 1
}

# 2. Check financial patterns
$financialResult = Test-FinancialPattern -Command $Command

if ($financialResult.IsFinancial -and $Config.RequireApprovalForFinancial) {
    Write-ExecLog -Level "FINANCIAL" -Message $financialResult.Name -Command $Command
    
    $approved = Request-Approval -Operation $financialResult.Name -Reason "Financial operation detected"
    
    if (-not $approved) {
        Write-Host "❌ Financial operation NOT approved" -ForegroundColor Red
        Write-ExecLog -Level "REJECTED" -Message "User rejected financial op" -Command $Command
        exit 1
    }
    
    Write-ExecLog -Level "APPROVED" -Message "User approved financial op" -Command $Command
}

# 3. Command allowed
Write-Host "✅ Command allowed" -ForegroundColor Green
Write-ExecLog -Level "ALLOWED" -Message "Passed all checks" -Command $Command
exit 0
