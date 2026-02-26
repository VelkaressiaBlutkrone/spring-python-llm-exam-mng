# Python LLM 추론 서버
# 빌드: docker build -t python-llm .
# 실행: docker run -p 8000:8000 -e LLM_FALLBACK_MOCK=1 python-llm

FROM python:3.11-slim

WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 복사
COPY app.py config.py llm_service.py schemas.py ./

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
