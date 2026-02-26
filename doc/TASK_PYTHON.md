# Python LLM 모듈 작업 목록

> 참조: [PRD.md](./PRD.md)

Python LLM 모듈은 FastAPI 기반 추론 서버로, Spring Boot에서 HTTP 호출하여 LLM 응답을 생성합니다. RAG 없이 순수 LLM 추론만 수행합니다.

---

## 작업 단계 (총 10단계)

### Step 1. Python 프로젝트 초기화

- 프로젝트 디렉터리 생성 (e.g., `python-llm/`)
- `pyproject.toml` 또는 `requirements.txt` 생성
- Python 3.10+ 권장

**산출물**: 프로젝트 루트, 의존성 관리 파일

---

### Step 2. 가상환경 및 의존성 설치

- `venv` 또는 `poetry`로 가상환경 생성
- 핵심 패키지 설치:
  - `fastapi`, `uvicorn` (API 서버)
  - `transformers`, `torch` (Hugging Face 모델) 또는 `openai` (OpenAI API)
- `requirements.txt` 고정

**산출물**: `requirements.txt`, 활성화된 가상환경

---

### Step 3. FastAPI 앱 기본 구조 작성

- `app.py` 또는 `main.py` 생성
- FastAPI 인스턴스 생성
- `/health` 또는 `/` 헬스체크 엔드포인트 추가
- CORS 설정 (Spring Boot 연동 시 필요)

**산출물**: `app.py`, 기본 서버 구동 확인

---

### Step 4. 요청/응답 스키마 정의

- Pydantic 모델 정의:
  - `InferRequest`: `query` (str), 선택적 `max_length`, `temperature` 등
  - `InferResponse`: `generated_text` (str)
- Spring Boot와 JSON 형식 협의

**산출물**: `schemas.py` 또는 `models.py`

---

### Step 5. LLM 모델 로딩 모듈 구현

- 모델 로딩 전용 모듈 생성 (e.g., `llm_service.py`)
- Hugging Face `pipeline` 또는 `AutoModelForCausalLM` 사용
- 모델명 환경변수로 설정 (e.g., `gpt2`, `meta-llama/Llama-2-7b`)
- 앱 시작 시 1회 로딩 (lazy load 대안 가능)

**산출물**: `llm_service.py`, 모델 로딩 로직

---

### Step 6. `/infer` 엔드포인트 구현

- `POST /infer` 라우트 추가
- 요청 본문에서 `query` 추출
- LLM 서비스 호출 → `generated_text` 반환
- 기본 파라미터: `max_length=100`, `num_return_sequences=1`

**산출물**: `/infer` API 동작 확인

---

### Step 7. 추론 로직 및 파라미터화

- `max_length`, `temperature`, `top_p` 등 파라미터 지원
- 입력 텍스트 전처리 (길이 제한, 특수문자 등)
- 출력 후처리 (불필요한 반복 제거 등)
- 타임아웃 설정

**산출물**: 안정적인 추론 파이프라인

---

### Step 8. 에러 핸들링 및 로깅

- LLM 호출 실패 시 예외 처리 (모델 로딩 실패, OOM 등)
- HTTP 500/503 적절히 반환
- `logging` 모듈로 요청/응답 로깅
- Fallback 응답 옵션 (선택)

**산출물**: 견고한 에러 처리, 로그 출력

---

### Step 9. 설정 관리 (환경변수)

- `python-dotenv` 또는 Pydantic `Settings` 사용
- 설정 항목: 모델명, 포트, 타임아웃, API 키(OpenAI 사용 시)
- `.env.example` 제공

**산출물**: `config.py`, `.env.example`

---

### Step 10. 테스트 및 실행 스크립트

- `pytest`로 `/infer` 엔드포인트 테스트 (mock 모델 또는 소형 모델)
- `uvicorn app:app --host 0.0.0.0 --port 8000` 실행 스크립트
- `README.md`에 실행 방법 문서화
- (선택) Dockerfile 작성

**산출물**: `tests/test_infer.py`, `run.sh` 또는 `docker-compose.yml`

---

## 의존성 요약

| 패키지 | 용도 |
| ------ | ---- |
| fastapi | REST API 프레임워크 |
| uvicorn | ASGI 서버 |
| transformers | Hugging Face LLM |
| torch | PyTorch (transformers 백엔드) |
| pydantic | 요청/응답 검증 |
| python-dotenv | 환경변수 로드 |
| pytest, httpx | 테스트 |

---

## API 스펙 (Python 서버)

| 엔드포인트 | 메서드 | 설명 |
| ---------- | ------ | ---- |
| `/` | GET | 헬스체크 |
| `/infer` | POST | 쿼리 입력 → LLM 응답 반환 |

**요청 예시** (Spring Boot에서 호출):

```json
{
  "query": "안녕하세요, 오늘 날씨는?"
}
```

**응답 예시**:

```json
{
  "generated_text": "안녕하세요! 오늘 날씨에 대해..."
}
```
