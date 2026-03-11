# LLM 의료 상담 시스템

Spring Boot + Python + MySQL + Ollama 기반의 의료 상담 LLM 시스템입니다.
사용자 증상을 입력하면 의학 지식 데이터 기반으로 추천 진료과, 담당 의사, AI 상담 응답을 제공합니다.

## 기술 스택

| 구성 요소 | 기술 |
| --------- | ---- |
| 백엔드 | Spring Boot 4.0.3, Java 21 |
| 데이터베이스 | MySQL 8.0 (의학 데이터 + 챗 히스토리) |
| LLM 서버 | Python 3.10+, FastAPI, Uvicorn |
| LLM 백엔드 | Ollama (qwen2.5:7b, 로컬 LLM) |
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
│   │   ├── MedicalController.java       # 의료 상담 REST API (/api/medical/**)
│   │   └── ChatController.java          # 병원 규칙 Q&A REST API (/api/chat/**)
│   ├── dto/
│   │   ├── DoctorWithScheduleDto.java   # 의사+스케줄 응답 DTO
│   │   ├── MedicalLlmResponse.java      # 의료상담 통합 응답 DTO
│   │   ├── LlmRequest.java / LlmResponse.java
│   │   ├── ChatHistoryResponse.java
│   │   └── MedicalHistoryResponse.java
│   ├── entity/
│   │   ├── Staff.java / MedicalHistory.java / ChatHistory.java
│   │   ├── Doctor.java / DoctorSchedule.java
│   │   └── MedicalQa.java / MedicalContent.java
│   ├── service/
│   │   ├── MedicalService.java          # 의료 상담 LLM 호출 + 이력 관리
│   │   ├── ChatService.java             # 병원 규칙 Q&A LLM 호출 + 이력 저장
│   │   ├── DoctorService.java           # 의사+스케줄 조회
│   │   └── LlmResponseParser.java      # LLM 응답 파싱 (진료과 추출)
│   └── exception/                       # 전역 예외 처리
├── src/main/resources/
│   ├── application.yml
│   └── static/
│       ├── index.html                   # 메인 허브 페이지
│       ├── medical.html                 # 질병 Q&A 페이지
│       └── chat.html                    # 병원 규칙 Q&A 채팅 페이지
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
ollama pull qwen2.5:7b              # LLM 추론 모델
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
LLM_BACKEND=ollama OLLAMA_MODEL=qwen2.5:7b \
  uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

**Windows PowerShell**

```powershell
$env:LLM_BACKEND="ollama"; $env:OLLAMA_MODEL="qwen2.5:7b"; uvicorn app:app --host 0.0.0.0 --port 8000 --reload
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
| `OLLAMA_MODEL` | `qwen2.5:7b` | Ollama 추론 모델명 |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Ollama 임베딩 모델명 |
| `USE_VECTOR_SEARCH` | `True` | 벡터 검색 사용 여부 |
| `VECTOR_SEARCH_TOP_K` | `3` | 벡터 검색 상위 K건 |
| `CHROMA_PERSIST_DIR` | `./chroma_data` | ChromaDB 데이터 저장 경로 |
| `MEDICAL_CONTEXT_MAX_CHARS` | `1500` | 의학 컨텍스트 최대 문자 수 |
| `LLM_FALLBACK_MOCK` | `false` | Mock 모드 (torch 없이 테스트) |

## API 사용법

### 의료 상담 (추천 진료과 + 의사 목록)

**`POST /api/medical/query/consult`**

의학 지식 기반 LLM 상담 + 추천 진료과 + 해당 의사 목록을 통합 반환합니다.

```bash
curl -X POST http://localhost:8080/api/medical/query/consult \
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

**`POST /api/medical/query/stream`**

SSE(Server-Sent Events)로 토큰 단위 실시간 응답을 전송합니다.

```bash
curl -N -X POST http://localhost:8080/api/medical/query/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "두통이 심합니다"}'
```

### 기본 LLM 쿼리

**`POST /api/medical/query`**

일반 LLM 추론 요청. 쿼리와 응답은 자동으로 DB에 저장됩니다.

```bash
curl -X POST http://localhost:8080/api/medical/query \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{"query": "안녕하세요"}'
```

### 병원 규칙 Q&A

**`POST /api/chat/query`**

의사·간호사가 병원 내부 규칙(당직, 물품, 위생 등)에 대해 질의합니다. `X-Staff-Id` 헤더 필수.

```bash
curl -X POST http://localhost:8080/api/chat/query \
  -H "Content-Type: application/json" \
  -H "X-Staff-Id: 1" \
  -d '{"query": "당직 근무 규정이 어떻게 되나요?"}'
```

### 히스토리 조회

**`GET /api/medical/history/{staffId}`** — 의학/질병 관련 질의응답 이력

**`GET /api/chat/history/{staffId}`** — 병원 규칙 Q&A 이력

```bash
# 의학 이력 조회
curl http://localhost:8080/api/medical/history/1

# 규칙 Q&A 이력 조회
curl http://localhost:8080/api/chat/history/1
```

**의학 이력 응답 예시:**

```json
{
  "content": [
    {
      "id": 1,
      "sessionId": "abc-123",
      "question": "두통이 심한데 어느 과로 가야 하나요?",
      "answer": "신경과 진료를 추천드립니다.",
      "status": "COMPLETED",
      "metadata": "{\"model\":\"qwen2.5:7b\",\"latency_ms\":1250}",
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

### staff

| 컬럼 | 타입 | 설명 |
| ---- | ---- | ---- |
| id | BIGINT (PK) | 직원 고유 식별자 |
| username | VARCHAR(100) | 로그인 ID |
| employee_number | VARCHAR(20) | 사번 |
| email | VARCHAR(255) | 이메일 주소 |

### medical_history (의학/질병 관련)

| 컬럼 | 타입 | 설명 |
| ---- | ---- | ---- |
| id | BIGINT (PK) | 고유 ID |
| staff_id | BIGINT (FK) | 직원 ID |
| question | TEXT | 질문 |
| answer | TEXT | LLM 응답 |
| status | VARCHAR(20) | PENDING, COMPLETED, FAILED |
| metadata | TEXT | JSON (latency_ms 등) |
| created_at | DATETIME | 생성 시각 |

### chatbot_history (병원 규칙 Q&A)

| 컬럼 | 타입 | 설명 |
| ---- | ---- | ---- |
| id | BIGINT (PK) | 고유 ID |
| staff_id | BIGINT (FK) | 직원 ID |
| session_id | VARCHAR(100) | 세션 ID |
| question | TEXT | 질문 |
| answer | TEXT | LLM 응답 |
| created_at | DATETIME | 생성 시각 |

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
    ├── MedicalController (/api/medical/** — 의료상담/스트리밍)
    ├── ChatController (/api/chat/** — 병원규칙 Q&A)
    ├── MedicalService / ChatService (LLM 호출 + 이력)
    ├── DoctorService (의사+스케줄 조회)
    └── LlmResponseParser (진료과 추출)
    ↓ WebClient
[Python FastAPI :8000]
    ├── /infer/medical         → 의학 컨텍스트 + Ollama Chat (동기)
    ├── /infer/medical/stream  → 의학 컨텍스트 + Ollama Chat (SSE 스트리밍)
    ├── /infer/rule            → 병원 규칙 RAG + Ollama Chat
    ├── medical_context_service → 하이브리드 검색
    │   ├── ChromaDB 벡터 검색 (의미 유사도, 우선)
    │   └── MySQL FULLTEXT 검색 (키워드, 폴백)
    └── response_cleaner → CJK 필터링 + 후처리
    ↓
[Ollama :11434]
    ├── qwen2.5:7b          → LLM 추론
    └── nomic-embed-text   → 임베딩 (RAG 벡터 검색)

[MySQL :3307]
    ├── medical_qa / medical_content → 의학 지식 데이터
    ├── doctors / doctor_schedules   → 의사 + 진료 스케줄
    ├── medical_history              → 의료 상담 이력
    ├── chatbot_history              → 병원 규칙 Q&A 이력
    └── staff                        → 직원 정보
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
