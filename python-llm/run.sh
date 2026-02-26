#!/bin/bash
# Python LLM 서버 실행
# 사용법: ./run.sh [--reload]

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "가상환경이 없습니다. python -m venv .venv && pip install -r requirements.txt"
    exit 1
fi

source .venv/bin/activate

if [ "$1" = "--reload" ]; then
    uvicorn app:app --host 0.0.0.0 --port 8000 --reload
else
    uvicorn app:app --host 0.0.0.0 --port 8000
fi
