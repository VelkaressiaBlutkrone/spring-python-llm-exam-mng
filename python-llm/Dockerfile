# Python LLM 추론 서버
# 빌드: docker compose build python-llm
# 단독: docker build -t python-llm .

FROM python:3.11-slim

WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 복사
COPY *.py ./
COPY prompts/ ./prompts/

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
