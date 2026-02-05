@echo off
setlocal

cd /d "%~dp0"

REM Activate venv
call .\.venv_platform\Scripts\activate.bat

REM Run FastAPI backend
python -m uvicorn Platform.backend.app.main:app --reload --port 8000

endlocal
