@echo off
setlocal

cd /d "%~dp0\Platform\web"

REM First-time install (safe to re-run)
npm install

REM Start dev server
npm run dev

endlocal
