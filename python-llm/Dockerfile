# Python LLM 추론 서버
# 빌드: docker compose build python-llm
# 단독: docker build -t python-llm .

FROM python:3.11-slim

WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# non-root 사용자 생성
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 소스 복사
COPY *.py ./
COPY prompts/ ./prompts/

# 소유권 변경 및 non-root 전환
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
