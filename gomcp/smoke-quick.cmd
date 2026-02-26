@echo off
REM GoMCP v2 Quick Smoke Test (batch version)
REM Sends initialize + health via stdin pipe
REM Usage: smoke-quick.cmd

setlocal
set GOMCP=%~dp0gomcp.exe
set RLMDIR=%~dp0..\.rlm

echo === GoMCP v2 Quick Smoke Test ===
echo Binary: %GOMCP%
echo RLM dir: %RLMDIR%
echo.

REM Create temp file with JSON-RPC messages
set TMPFILE=%TEMP%\gomcp-smoke-%RANDOM%.txt

REM Message 1: initialize
set MSG1={"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"1.0"}}}

REM Message 2: initialized notification
set MSG2={"jsonrpc":"2.0","method":"notifications/initialized"}

REM Message 3: health
set MSG3={"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"health","arguments":{}}}

REM Message 4: version
set MSG4={"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"version","arguments":{}}}

REM Message 5: fact_stats
set MSG5={"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"fact_stats","arguments":{}}}

echo Writing test messages...
(
    call :write_msg "%MSG1%"
    call :write_msg "%MSG2%"
    call :write_msg "%MSG3%"
    call :write_msg "%MSG4%"
    call :write_msg "%MSG5%"
) > %TMPFILE%

echo Sending to gomcp...
echo.
type %TMPFILE% | "%GOMCP%" -rlm-dir "%RLMDIR%" 2>%TEMP%\gomcp-stderr.txt

echo.
echo === Server Logs ===
type %TEMP%\gomcp-stderr.txt
echo.
echo === Done ===

del %TMPFILE% 2>nul
del %TEMP%\gomcp-stderr.txt 2>nul
goto :eof

:write_msg
setlocal
set MSG=%~1
REM Calculate content length (approximate for ASCII)
set /a LEN=0
call :strlen LEN "%MSG%"
echo Content-Length: %LEN%
echo.
echo %MSG%
endlocal
goto :eof

:strlen
setlocal enabledelayedexpansion
set STR=%~2
set /a CNT=0
:loop
if "!STR:~%CNT%,1!" neq "" (set /a CNT+=1 & goto loop)
endlocal & set %1=%CNT%
goto :eof
