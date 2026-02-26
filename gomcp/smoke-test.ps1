# GoMCP v2 Smoke Test
# Sends JSON-RPC messages via stdin to gomcp.exe and reads responses from stdout.
# Usage: powershell -File smoke-test.ps1

$ErrorActionPreference = "Stop"
$gomcp = "$PSScriptRoot\gomcp.exe"
$rlmDir = "$PSScriptRoot\..\..\.rlm"  # Adjust if needed

if (-not (Test-Path $gomcp)) {
    Write-Error "gomcp.exe not found. Run: go build -o gomcp.exe ./cmd/gomcp/"
    exit 1
}

# JSON-RPC messages to send (each must be on one line, separated by Content-Length header)
$messages = @(
    # 1. Initialize
    @{
        jsonrpc = "2.0"
        id = 1
        method = "initialize"
        params = @{
            protocolVersion = "2024-11-05"
            capabilities = @{}
            clientInfo = @{ name = "smoke-test"; version = "1.0" }
        }
    },
    # 2. Initialized notification
    @{
        jsonrpc = "2.0"
        method = "notifications/initialized"
    },
    # 3. List tools
    @{
        jsonrpc = "2.0"
        id = 2
        method = "tools/list"
    },
    # 4. Health check
    @{
        jsonrpc = "2.0"
        id = 3
        method = "tools/call"
        params = @{
            name = "health"
            arguments = @{}
        }
    },
    # 5. Version
    @{
        jsonrpc = "2.0"
        id = 4
        method = "tools/call"
        params = @{
            name = "version"
            arguments = @{}
        }
    },
    # 6. Fact stats
    @{
        jsonrpc = "2.0"
        id = 5
        method = "tools/call"
        params = @{
            name = "fact_stats"
            arguments = @{}
        }
    },
    # 7. Get L0 facts
    @{
        jsonrpc = "2.0"
        id = 6
        method = "tools/call"
        params = @{
            name = "get_l0_facts"
            arguments = @{}
        }
    },
    # 8. Search facts
    @{
        jsonrpc = "2.0"
        id = 7
        method = "tools/call"
        params = @{
            name = "search_facts"
            arguments = @{ query = "architecture"; limit = 5 }
        }
    },
    # 9. List domains
    @{
        jsonrpc = "2.0"
        id = 8
        method = "tools/call"
        params = @{
            name = "list_domains"
            arguments = @{}
        }
    },
    # 10. Add a test fact
    @{
        jsonrpc = "2.0"
        id = 9
        method = "tools/call"
        params = @{
            name = "add_fact"
            arguments = @{
                content = "GoMCP v2 smoke test passed successfully"
                level = 3
                domain = "testing"
                module = "smoke-test"
            }
        }
    },
    # 11. Dashboard
    @{
        jsonrpc = "2.0"
        id = 10
        method = "tools/call"
        params = @{
            name = "dashboard"
            arguments = @{}
        }
    }
)

Write-Host "=== GoMCP v2 Smoke Test ===" -ForegroundColor Cyan
Write-Host "Binary: $gomcp"
Write-Host "RLM dir: $rlmDir"
Write-Host ""

# Start gomcp process
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $gomcp
$psi.Arguments = "-rlm-dir `"$rlmDir`""
$psi.UseShellExecute = $false
$psi.RedirectStandardInput = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.CreateNoWindow = $true

$process = [System.Diagnostics.Process]::Start($psi)

# Give it a moment to start
Start-Sleep -Milliseconds 500

$passed = 0
$failed = 0

foreach ($msg in $messages) {
    $json = $msg | ConvertTo-Json -Depth 10 -Compress
    $header = "Content-Length: $($json.Length)`r`n`r`n"
    
    $isNotification = -not $msg.ContainsKey("id")
    $label = if ($isNotification) { $msg.method } else { "id=$($msg.id) $($msg.method)" }
    
    Write-Host ">> Sending: $label" -ForegroundColor Yellow
    
    try {
        $process.StandardInput.Write($header)
        $process.StandardInput.Write($json)
        $process.StandardInput.Flush()
        
        if ($isNotification) {
            Write-Host "   (notification, no response expected)" -ForegroundColor DarkGray
            Start-Sleep -Milliseconds 200
            continue
        }
        
        # Read response: Content-Length header + body
        $headerLine = ""
        $contentLength = 0
        
        # Read until we get Content-Length
        while ($true) {
            $line = $process.StandardOutput.ReadLine()
            if ($null -eq $line) { break }
            if ($line -match "Content-Length:\s*(\d+)") {
                $contentLength = [int]$Matches[1]
            }
            if ($line -eq "") { break }
        }
        
        if ($contentLength -gt 0) {
            $buffer = New-Object char[] $contentLength
            $read = $process.StandardOutput.Read($buffer, 0, $contentLength)
            $response = [string]::new($buffer, 0, $read)
            
            $parsed = $response | ConvertFrom-Json
            
            if ($parsed.error) {
                Write-Host "   FAIL: $($parsed.error.message)" -ForegroundColor Red
                $failed++
            } else {
                # Truncate long results for display
                $resultText = ($parsed.result | ConvertTo-Json -Depth 5 -Compress)
                if ($resultText.Length -gt 200) {
                    $resultText = $resultText.Substring(0, 200) + "..."
                }
                Write-Host "   OK: $resultText" -ForegroundColor Green
                $passed++
            }
        } else {
            Write-Host "   FAIL: no response" -ForegroundColor Red
            $failed++
        }
    }
    catch {
        Write-Host "   FAIL: $($_.Exception.Message)" -ForegroundColor Red
        $failed++
    }
    
    Start-Sleep -Milliseconds 100
}

# Cleanup
try {
    $process.StandardInput.Close()
    $process.WaitForExit(3000)
    if (-not $process.HasExited) { $process.Kill() }
} catch {}

# Print stderr (server logs)
$stderr = $process.StandardError.ReadToEnd()
if ($stderr) {
    Write-Host ""
    Write-Host "=== Server Logs ===" -ForegroundColor Cyan
    $stderr -split "`n" | ForEach-Object { Write-Host "   $_" -ForegroundColor DarkGray }
}

Write-Host ""
Write-Host "=== Results ===" -ForegroundColor Cyan
Write-Host "Passed: $passed" -ForegroundColor Green
Write-Host "Failed: $failed" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })

if ($failed -gt 0) { exit 1 }
