# LLM 의료 상담 시스템

Spring Boot + Python + MySQL + Ollama 기반의 의료 상담 LLM 시스템입니다.
사용자 증상을 입력하면 의학 지식 데이터 기반으로 추천 진료과, 담당 의사, AI 상담 응답을 제공합니다.

## 기술 스택

| 구성 요소 | 기술 |
| --------- | ---- |
| 백엔드 | Spring Boot 4.0.3, Java 21 |
| 데이터베이스 | MySQL 8.0 (의학 데이터 + 챗 히스토리) |
| LLM 서버 | Python 3.10+, FastAPI, Uvicorn |
| LLM 백엔드 | Ollama (gemma3:4b, 로컬 LLM) |
| RAG/벡터 검색 | ChromaDB + Ollama nomic-embed-text |
| 비동기 호출 | Spring WebFlux (WebClient) |
| 스트리밍 | SSE (Server-Sent Events) |
| ORM | Spring Data JPA / Hibernate |
| 프론트엔드 | Vanilla HTML/CSS/JS (SPA) |

## 프로젝트 구조

```
spring_llm_sample_mng/
├── src/main/java/com/sample/llm/
│   ├── config/
│   │   ├── DataLoader.java              # 초기 시드 데이터 로딩
│   │   └── WebClientConfig.java         # WebClient Bean 설정
│   ├── controller/
│   │   └── LlmController.java           # REST API (쿼리, 의료상담, 스트리밍)
│   ├── dto/
│   │   ├── DoctorWithScheduleDto.java   # 의사+스케줄 응답 DTO
│   │   ├── MedicalLlmResponse.java      # 의료상담 통합 응답 DTO
│   │   ├── LlmRequest.java / LlmResponse.java
│   │   └── ChatHistoryResponse.java
│   ├── entity/
│   │   ├── ChatHistory.java / User.java
│   │   ├── Doctor.java / DoctorSchedule.java
│   │   └── MedicalQa.java / MedicalContent.java
│   ├── service/
│   │   ├── LlmService.java             # LLM 호출 (동기/스트리밍)
│   │   ├── DoctorService.java           # 의사+스케줄 조회
│   │   └── LlmResponseParser.java      # LLM 응답 파싱 (진료과 추출)
│   └── exception/                       # 전역 예외 처리
├── src/main/resources/
│   ├── application.yml
│   └── static/index.html               # 프론트엔드 SPA
├── python-llm/                          # Python LLM 서버
│   ├── app.py                           # FastAPI 앱 (의료상담 + SSE 스트리밍)
│   ├── ollama_service.py                # Ollama API 클라이언트
│   ├── medical_context_service.py       # 하이브리드 검색 (벡터 + FULLTEXT)
│   ├── embedding_service.py             # Ollama 임베딩 API 클라이언트
│   ├── vector_store.py                  # ChromaDB 벡터 저장소
│   ├── index_medical_data.py            # MySQL → ChromaDB 인덱싱 스크립트
│   ├── response_cleaner.py              # LLM 응답 후처리 (CJK 필터링)
│   ├── typo_corrector.py                # 오타 교정
│   ├── config.py                        # 설정 관리 (Pydantic Settings)
│   └── tests/                           # pytest 테스트
├── doc/                                 # 프로젝트 문서
│   ├── TASK_RAG_VECTOR_SEARCH.md        # RAG/벡터 검색 구현 가이드
│   ├── TROUBLESHOOTING.md               # 트러블슈팅 가이드 (11건)
│   ├── SETUP_OLLAMA.md                  # Ollama 설치/연동 가이드
│   └── PRD.md / ERD.md / RULE_*.md
├── docker-compose.yml                   # MySQL 컨테이너 설정
├── .env.example                         # 환경변수 템플릿
└── build.gradle
```

## 실행 순서

**반드시 아래 순서대로 실행해야 합니다.**

### 1. MySQL 컨테이너 실행

```bash
docker-compose up -d
```

MySQL이 포트 `3307`에서 실행됩니다. (기본 계정: `llm_admin` / `llm_password`)

### 2. Ollama 서버 실행

Ollama를 설치하고 필요한 모델을 다운로드합니다.
자세한 설정은 [Ollama 설치 가이드](doc/SETUP_OLLAMA.md)를 참고하세요.

```bash
# Ollama 설치 후 모델 다운로드
ollama pull gemma3:4b              # LLM 추론 모델
ollama pull nomic-embed-text       # 임베딩 모델 (RAG 벡터 검색용)

# Ollama 서버 실행 (기본 포트 11434)
ollama serve
```

### 3. Python LLM 서버 실행 (포트 8000)

```bash
cd python-llm
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
# source .venv/bin/activate

pip install -r requirements.txt
```

### 4. (선택) RAG 벡터 인덱싱

MySQL 의학 데이터를 ChromaDB에 벡터 인덱싱합니다.
이 단계를 건너뛰면 FULLTEXT 검색만 사용됩니다.

```bash
cd python-llm
python index_medical_data.py
```

성공 시 `=== Indexing complete: N total documents in vector store ===` 출력.
상세 내용: [RAG 벡터 검색 가이드](doc/TASK_RAG_VECTOR_SEARCH.md)

### 5. Python LLM 서버 시작

**Linux / Mac (bash)**

```bash
LLM_BACKEND=ollama OLLAMA_MODEL=gemma3:4b \
  uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

**Windows PowerShell**

```powershell
$env:LLM_BACKEND="ollama"; $env:OLLAMA_MODEL="gemma3:4b"; uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

서버 시작 로그에서 `ChromaDB ready: N documents indexed` 확인.

### 6. Spring Boot 애플리케이션 실행

```bash
# 환경변수 설정 (.env.example 참고)
cp .env.example .env

# 실행
./gradlew bootRun
```

Spring Boot가 포트 `8080`에서 실행됩니다.

## 환경변수

`.env.example` 파일을 `.env`로 복사하여 설정합니다.

**Spring Boot** (`.env`):

| 변수 | 기본값 | 설명 |
| ---- | ------ | ---- |
| `MYSQL_USERNAME` | `root` | MySQL 사용자명 |
| `MYSQL_PASSWORD` | `rootpassword` | MySQL 비밀번호 |
| `LLM_SERVICE_URL` | `http://localhost:8000` | Python LLM 서버 URL |
| `SERVER_PORT` | `8080` | Spring Boot 서버 포트 |

**Python LLM 서버** (`python-llm/.env`):

| 변수 | 기본값 | 설명 |
| ---- | ------ | ---- |
| `LLM_BACKEND` | `huggingface` | LLM 백엔드 (`huggingface` / `ollama`) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 서버 URL |
| `OLLAMA_MODEL` | `gemma3:4b` | Ollama 추론 모델명 |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Ollama 임베딩 모델명 |
| `USE_VECTOR_SEARCH` | `True` | 벡터 검색 사용 여부 |
| `VECTOR_SEARCH_TOP_K` | `3` | 벡터 검색 상위 K건 |
| `CHROMA_PERSIST_DIR` | `./chroma_data` | ChromaDB 데이터 저장 경로 |
| `MEDICAL_CONTEXT_MAX_CHARS` | `1500` | 의학 컨텍스트 최대 문자 수 |
| `LLM_FALLBACK_MOCK` | `false` | Mock 모드 (torch 없이 테스트) |

## API 사용법

### 의료 상담 (추천 진료과 + 의사 목록)

**`POST /api/llm/query/medical`**

의학 지식 기반 LLM 상담 + 추천 진료과 + 해당 의사 목록을 통합 반환합니다.

```bash
curl -X POST http://localhost:8080/api/llm/query/medical \
  -H "Content-Type: application/json" \
  -d '{"query": "무릎이 아프고 걸을 때 통증이 심해요"}'
```

**응답 예시:**

```json
{
  "generatedText": "추천 진료과: 정형외과\n무릎 통증은...",
  "recommendedDepartment": "정형외과",
  "recommendationReason": "무릎 관절 통증 및 보행 시 악화 증상",
  "doctors": [
    {
      "name": "이정형",
      "specialty": "관절외과",
      "hospital": "서울대학교병원",
      "schedules": [
        {"dayOfWeek": "MON", "startTime": "09:00", "endTime": "17:00", "available": true}
      ]
    }
  ]
}
```

### 의료 상담 스트리밍 (SSE)

**`POST /api/llm/query/medical/stream`**

SSE(Server-Sent Events)로 토큰 단위 실시간 응답을 전송합니다.

```bash
curl -N -X POST http://localhost:8080/api/llm/query/medical/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "두통이 심합니다"}'
```

### 기본 LLM 쿼리

**`POST /api/llm/query`**

일반 LLM 추론 요청. 쿼리와 응답은 자동으로 DB에 저장됩니다.

```bash
curl -X POST http://localhost:8080/api/llm/query \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{"query": "안녕하세요"}'
```

### 챗 히스토리 조회

**`GET /api/llm/history/{staffId}`**

특정 직원(Staff)의 챗봇 대화 이력을 페이징으로 조회합니다. (ERD v4.0 CHATBOT_HISTORY 정합)

```bash
# 기본 조회 (최신순 20건)
curl http://localhost:8080/api/llm/history/1

# 페이징 파라미터 지정
curl "http://localhost:8080/api/llm/history/1?page=0&size=10"
```

**응답 예시:**

```json
{
  "content": [
    {
      "id": 1,
      "sessionId": "abc-123",
      "question": "안녕하세요, 오늘 날씨는?",
      "answer": "안녕하세요! 오늘 날씨에 대해...",
      "status": "COMPLETED",
      "metadata": "{\"model\":\"gpt2\",\"latency_ms\":1250}",
      "createdAt": "2025-03-01T12:00:00"
    }
  ],
  "totalElements": 1,
  "totalPages": 1,
  "size": 20,
  "number": 0
}
```

## 에러 응답

| HTTP 상태 | 상황 | 응답 메시지 |
| --------- | ---- | ----------- |
| 503 | Python LLM 서버 연결 실패 | LLM 서버를 사용할 수 없습니다 |
| 504 | LLM 응답 시간 초과 | LLM 응답 시간 초과 |
| 500 | 서버 내부 오류 | 서버 내부 오류가 발생했습니다 |

## 데이터베이스 스키마

### users

| 컬럼 | 타입 | 설명 |
| ---- | ---- | ---- |
| id | BIGINT (PK) | 사용자 고유 식별자 |
| username | VARCHAR(100) | 사용자명 |
| email | VARCHAR(255) | 이메일 주소 |

### chat_history

| 컬럼 | 타입 | 설명 |
| ---- | ---- | ---- |
| id | BIGINT (PK) | 히스토리 고유 식별자 |
| user_id | BIGINT (FK) | 사용자 ID (선택) |
| session_id | VARCHAR(64) | 세션/대화 그룹 ID |
| query | TEXT | 사용자 쿼리 |
| response | TEXT | LLM 응답 |
| status | VARCHAR(20) | PENDING / COMPLETED / FAILED |
| metadata | TEXT (JSON) | 모델명, latency_ms 등 성능 분석용 |
| timestamp | DATETIME | 생성 시각 |

## 테스트

### Spring Boot

```bash
./gradlew test
```

`@WebMvcTest`와 `@MockBean`을 사용하여 실제 Python LLM 서버 없이 컨트롤러 단위 테스트를 실행합니다.

### Python LLM 서버

```bash
cd python-llm
.venv/Scripts/python -m pytest tests/ -v
```

`sys.modules` mock으로 torch/transformers import 없이 테스트합니다.

## 아키텍처

```text
[프론트엔드 SPA]
    ↓ SSE 스트리밍 + REST API
[Spring Boot :8080]
    ├── LlmController (쿼리/의료상담/스트리밍)
    ├── DoctorService (의사+스케줄 조회)
    └── LlmResponseParser (진료과 추출)
    ↓ WebClient
[Python FastAPI :8000]
    ├── /infer/medical         → 의학 컨텍스트 + Ollama Chat (동기)
    ├── /infer/medical/stream  → 의학 컨텍스트 + Ollama Chat (SSE 스트리밍)
    ├── medical_context_service → 하이브리드 검색
    │   ├── ChromaDB 벡터 검색 (의미 유사도, 우선)
    │   └── MySQL FULLTEXT 검색 (키워드, 폴백)
    └── response_cleaner → CJK 필터링 + 후처리
    ↓
[Ollama :11434]
    ├── gemma3:4b          → LLM 추론
    └── nomic-embed-text   → 임베딩 (RAG 벡터 검색)

[MySQL :3307]
    ├── medical_qa / medical_content → 의학 지식 데이터
    ├── doctors / doctor_schedules   → 의사 + 진료 스케줄
    └── chat_history / users         → 상담 이력
```

## 주요 기능

| 기능 | 설명 |
| ---- | ---- |
| 의료 상담 | 증상 입력 → 추천 진료과 + 담당 의사 + AI 상담 응답 |
| SSE 스트리밍 | 토큰 단위 실시간 응답으로 체감 속도 개선 |
| RAG 벡터 검색 | ChromaDB + Ollama 임베딩으로 의미 기반 문서 검색 |
| 하이브리드 검색 | 벡터 검색 우선 → MySQL FULLTEXT 폴백 |
| 중국어 필터링 | 시스템 프롬프트 강화 + CJK 패턴 실시간 제거 |
| 오타 교정 | 의학 용어 오타 자동 보정 |
| 챗 히스토리 | 상담 이력 자동 저장 (PENDING → COMPLETED/FAILED) |
| 프론트엔드 | 병렬 API 호출, 스트리밍 우선 + 폴백 렌더링 |

## 참고 문서

- [PRD (제품 요구사항)](doc/PRD.md)
- [RAG 벡터 검색 가이드](doc/TASK_RAG_VECTOR_SEARCH.md)
- [트러블슈팅 가이드](doc/TROUBLESHOOTING.md)
- [Spring Boot 개발 규칙](doc/RULE_SPRING.md)
- [Ollama 설치/연동 가이드](doc/SETUP_OLLAMA.md)
- [Python LLM 모듈 README](python-llm/README.md)
