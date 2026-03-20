# Python LLM 모듈 작업 목록

> 참조: [PRD.md](./PRD.md), [SETUP_OLLAMA.md](./SETUP_OLLAMA.md)

Python LLM 모듈은 FastAPI 기반 추론 서버로, Spring Boot에서 HTTP 호출하여 LLM 응답을 생성합니다. RAG 없이 순수 LLM 추론만 수행합니다.

**LLM 백엔드**: 기본적으로 **Ollama**(로컬 LLM)를 사용하며, Hugging Face Transformers를 대안으로 지원합니다.

**사전 요구사항** (Ollama 모드): [SETUP_OLLAMA.md](./SETUP_OLLAMA.md) 참조하여 Ollama 설치 후 `ollama serve` 실행, 모델 다운로드 (`ollama pull gemma3:4b` 등)

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
  - `httpx` (Ollama REST API 호출용)
  - `transformers`, `torch` (Hugging Face 백엔드 선택 시, 선택적)
- `requirements.txt` 고정

**산출물**: `requirements.txt`, 활성화된 가상환경

---

### Step 3. FastAPI 앱 기본 구조 작성

- `app.py` 또는 `main.py` 생성
- FastAPI 인스턴스 생성
- `/` 루트, `/health` 헬스체크 엔드포인트 추가 (Ollama 모드 시 `ollama_connected` 포함)
- CORS 설정 (Spring Boot 연동 시 필요)

**산출물**: `app.py`, 기본 서버 구동 확인

---

### Step 4. 요청/응답 스키마 정의

- Pydantic 모델 정의:
  - `InferRequest`: `query` (str), `max_length`, `temperature`, `top_p`, `num_return_sequences` 등
  - `InferResponse`: `generated_text` (str)
- Spring Boot와 JSON 형식 협의

**산출물**: `schemas.py` 또는 `models.py`

---

### Step 5. LLM 서비스 모듈 구현

**Ollama 모드 (권장)**:

- `ollama_service.py` 생성: Ollama REST API 클라이언트
- `httpx`로 `http://localhost:11434/api/generate` 또는 `/api/chat` 호출
- 환경변수: `OLLAMA_BASE_URL`, `OLLAMA_MODEL` (e.g., `gemma3:4b`, `qwen2.5:7b`)
- 모델 로딩 없음 (Ollama 서버가 별도 실행)

**Hugging Face 모드 (선택)**:

- `llm_service.py`: `pipeline` 또는 `AutoModelForCausalLM` 사용
- 환경변수: `LLM_MODEL` (e.g., `gpt2`)

**산출물**: `ollama_service.py`, `llm_service.py` (선택)

---

### Step 6. `/infer` 엔드포인트 구현

- `POST /infer` 라우트 추가
- 요청 본문에서 `query` 추출
- `LLM_BACKEND`에 따라 `ollama_service.generate_with_ollama()` 또는 `llm_service.generate()` 호출
- 기본 파라미터: `max_length=100`, `temperature=0.7`, `top_p=1.0`

**산출물**: `/infer` API 동작 확인

---

### Step 7. 추론 로직 및 파라미터화

- `max_length`, `temperature`, `top_p` 등 파라미터 지원
- Ollama: `options.num_predict`, `options.temperature`, `options.top_p`로 전달
- 입력 텍스트 전처리 (길이 제한, 특수문자 등)
- `httpx.Timeout`으로 추론 타임아웃 설정 (`LLM_INFER_TIMEOUT_SEC`)

**산출물**: 안정적인 추론 파이프라인

---

### Step 8. 에러 핸들링 및 로깅

- Ollama 연결 실패: `httpx.ConnectError` → `ConnectionError` (ollama serve 확인 안내)
- 추론 타임아웃: `httpx.ReadTimeout` → `TimeoutError` → HTTP 503
- `logging` 모듈로 요청/응답 로깅
- `LLM_FALLBACK_RESPONSE` 설정 시 fallback 응답 반환

**산출물**: 견고한 에러 처리, 로그 출력

---

### Step 9. 설정 관리 (환경변수)

- Pydantic `Settings` (`pydantic-settings`) 사용
- 설정 항목:
  - `LLM_BACKEND`: `ollama` | `huggingface`
  - `OLLAMA_BASE_URL`: Ollama 서버 URL (기본 `http://localhost:11434`)
  - `OLLAMA_MODEL`: Ollama 모델명 (기본 `gemma3:4b`, 한국어 권장 `qwen2.5:7b`)
  - `LLM_INFER_TIMEOUT_SEC`, `LLM_FALLBACK_RESPONSE` 등
- `.env.example` 제공, [SETUP_OLLAMA.md](./SETUP_OLLAMA.md) 참조

**산출물**: `config.py`, `.env.example`

---

### Step 10. 테스트 및 실행 스크립트

- `pytest`로 `/infer` 엔드포인트 테스트 (mock 또는 실제 Ollama)
- Ollama 모드 실행: `LLM_BACKEND=ollama uvicorn app:app --host 0.0.0.0 --port 8000`
- `README.md`에 실행 방법 문서화 (Ollama 선실행 안내)
- (선택) Dockerfile 작성

**산출물**: `tests/test_infer.py`, 실행 스크립트

---

## 의존성 요약

| 패키지                      | 용도                          |
| --------------------------- | ----------------------------- |
| fastapi                     | REST API 프레임워크           |
| uvicorn                     | ASGI 서버                     |
| httpx                       | Ollama REST API 호출 (비동기) |
| pydantic, pydantic-settings | 요청/응답 검증, 설정 관리     |
| python-dotenv               | 환경변수 로드                 |
| transformers, torch         | Hugging Face 백엔드 (선택)    |
| pytest, httpx               | 테스트                        |

---

## API 스펙 (Python 서버)

| 엔드포인트       | 메서드 | 설명                                               |
| ---------------- | ------ | -------------------------------------------------- |
| `/`              | GET    | 서버 상태 확인                                     |
| `/health`        | GET    | 헬스체크 (Ollama 연결 여부 포함)                   |
| `/infer`         | POST   | 쿼리 입력 → LLM 응답 반환 (Ollama `/api/generate`) |
| `/infer/medical` | POST   | 의학지식 DB 기반 추론 (Ollama `/api/chat`)         |

**요청 예시** (Spring Boot에서 호출):

```json
{
  "query": "안녕하세요, 오늘 날씨는?",
  "max_length": 100,
  "temperature": 0.7,
  "top_p": 1.0
}
```

**응답 예시**:

```json
{
  "generated_text": "안녕하세요! 오늘 날씨에 대해..."
}
```

**실행 예시** (Ollama 모드):

````bash
# Ollama 서버 선실행 필요: ollama serve
LLM_BACKEND=ollama OLLAMA_MODEL=qwen2.5:7b uvicorn app:app --host 0.0.0.0 --port 8000
```llama 서버 선실행 필요: ollama serve
LLM_BACKEND=ollama OLLAMA_MODEL=qwen2.5:7b uvicorn app:app --host 0.0.0.0 --port 8000
````
