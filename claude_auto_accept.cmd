@echo off
REM ============================================================
REM  Claude Code Auto-Accept Plugin
REM  Launches a background monitor that auto-accepts
REM  "Do you want to proceed?" prompts from Claude Code CLI.
REM ============================================================

where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [claude_auto_accept] Python not found in PATH - plugin disabled.
    goto :eof
)

start /b python "%CMDER_ROOT%\bin\claude_auto_accept.py" >nul 2>&1
