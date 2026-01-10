@echo off
setlocal
cd /d "%~dp0"

start "BotTrader Backend" cmd /k call "%~dp0run_backend.cmd"
start "BotTrader Web"     cmd /k call "%~dp0run_web.cmd"

endlocal
