@echo off
setlocal

REM Run signals-only Opening Tool (no trade execution)
cd /d "%~dp0.."

python scripts\run_opening_tool.py --once

endlocal
