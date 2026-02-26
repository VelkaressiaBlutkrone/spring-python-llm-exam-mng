@echo off
REM Python LLM 서버 실행
REM 사용법: run.bat [--reload]

cd /d "%~dp0"

if not exist ".venv" (
    echo 가상환경이 없습니다. python -m venv .venv ^&^& pip install -r requirements.txt
    exit /b 1
)

call .venv\Scripts\activate.bat

if "%1"=="--reload" (
    uvicorn app:app --host 0.0.0.0 --port 8000 --reload
) else (
    uvicorn app:app --host 0.0.0.0 --port 8000
)
