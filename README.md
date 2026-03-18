# LLM 의료 상담 시스템

Spring Boot + Python + MySQL + Ollama 기반의 의료 상담 LLM 시스템입니다.
사용자 증상을 입력하면 의학 지식 데이터 기반으로 추천 진료과, 담당 의사, AI 상담 응답을 제공합니다.

## 기술 스택

| 구성 요소     | 기술                                  |
| ------------- | ------------------------------------- |
| 백엔드        | Spring Boot 4.0.3, Java 21            |
| 데이터베이스  | MySQL 8.0 (의학 데이터 + 챗 히스토리) |
| LLM 서버      | Python 3.10+, FastAPI, Uvicorn        |
| LLM 백엔드    | vLLM (qwen2.5-7b, AWQ 4bit) + Ollama (폴백) |
| LLM 전환      | LLM_BACKEND 환경변수로 vLLM/Ollama 즉시 전환 |
| RAG/벡터 검색 | ChromaDB + Ollama nomic-embed-text    |
| 비동기 호출   | Spring WebFlux (WebClient)            |
| 스트리밍      | SSE (Server-Sent Events)              |
| ORM           | Spring Data JPA / Hibernate           |
| 프론트엔드    | Vanilla HTML/CSS/JS (SPA)             |

## 프로젝트 구조

```text
spring_llm_sample_mng/
├── src/main/java/com/sample/llm/
│   ├── SpringLlmSampleMngApplication.java
│   ├── config/
│   │   ├── DataLoader.java              # 초기 시드 데이터 로딩
│   │   └── WebClientConfig.java         # WebClient Bean 설정
│   ├── controller/
│   │   ├── MedicalController.java       # 의료 상담 REST API (/api/medical/**)
│   │   └── ChatController.java          # 병원 규칙 Q&A REST API (/api/chat/**)
│   ├── dto/
│   │   ├── DoctorDto.java, DoctorScheduleDto.java, DoctorWithScheduleDto.java
│   │   ├── MedicalLlmResponse.java      # 의료상담 통합 응답 DTO
│   │   ├── LlmRequest.java, LlmResponse.java
│   │   ├── ChatHistoryResponse.java, MedicalHistoryResponse.java
│   │   └── ErrorResponse.java
│   ├── entity/
│   │   ├── Staff.java                   # 직원 (의사/간호사)
│   │   ├── Doctor.java, DoctorSchedule.java
│   │   ├── MedicalHistory.java          # 의료 상담 이력
│   │   ├── ChatHistory.java             # 병원 규칙 Q&A 이력
│   │   ├── MedicalQa.java, MedicalContent.java
│   │   ├── MedicalDomain.java, MedicalRule.java
│   ├── repository/                      # JPA Repository
│   │   ├── MedicalHistoryRepository, ChatHistoryRepository
│   │   ├── DoctorRepository, DoctorScheduleRepository
│   │   ├── MedicalQaRepository, MedicalContentRepository
│   │   ├── MedicalRuleRepository, StaffRepository, MedicalDomainRepository
│   ├── service/
│   │   ├── MedicalService.java          # 의료 상담 LLM 호출 + 이력 관리
│   │   ├── ChatService.java             # 병원 규칙 Q&A LLM 호출 + 이력 저장
│   │   ├── DoctorService.java           # 의사+스케줄 조회
│   │   └── LlmResponseParser.java       # LLM 응답 파싱 (진료과 추출)
│   └── exception/
│       ├── GlobalExceptionHandler.java
│       ├── LlmTimeoutException.java
│       └── LlmServiceUnavailableException.java
├── src/main/resources/
│   ├── application.yml
│   └── static/
│       ├── index.html                   # 메인 허브 페이지
│       ├── medical.html                 # 질병 Q&A 페이지
│       └── chat.html                    # 병원 규칙 Q&A 채팅 페이지
├── python-llm/                          # Python LLM 추론 서버
│   ├── app.py                           # FastAPI 앱 (엔드포인트 + 미들웨어)
│   ├── ollama_service.py                # Ollama API 클라이언트 (generate/chat/stream)
│   ├── vllm_service.py                # vLLM OpenAI 호환 API 클라이언트 (generate/chat/stream)
│   ├── medical_context_service.py       # 하이브리드 검색 (벡터 + FULLTEXT, asyncio.gather 병렬)
│   ├── rule_context_service.py          # 병원 규칙 RAG (벡터 + MySQL 폴백)
│   ├── embedding_service.py             # Ollama 임베딩 + OrderedDict 캐시
│   ├── vector_store.py                  # ChromaDB 벡터 저장소 (medical + rule 컬렉션)
│   ├── import_medical_data.py            # llm_data ZIP → MySQL 적재
│   ├── index_medical_data.py            # MySQL → ChromaDB 인덱싱 (증분 지원)
│   ├── index_rule_data.py               # 병원 규칙 JSON → MySQL + ChromaDB 적재
│   ├── config.py                        # 설정 관리 (Pydantic Settings)
│   ├── schemas.py                       # 요청/응답 스키마 (Pydantic)
│   ├── circuit_breaker.py               # Circuit Breaker 패턴 (장애 격리)
│   ├── metrics.py                       # 추론 메트릭 수집 (지연시간, 성공률)
│   ├── reranker.py                      # 검색 결과 Re-ranking (LLM 기반)
│   ├── query_expander.py                # 쿼리 확장 (의학 용어 보강)
│   ├── chunker.py                       # 텍스트 청킹 (오버랩 분할)
│   ├── prompt_loader.py                 # 프롬프트 외부 파일 로더 (@lru_cache)
│   ├── response_cleaner.py              # LLM 응답 후처리 (CJK 필터링)
│   ├── typo_corrector.py                # 의료 용어 오타 교정 (DB + 내장 사전)
│   ├── llm_service.py                   # Hugging Face 백엔드 (폴백)
│   ├── prompts/
│   │   ├── medical_system.txt            # 의료 상담 시스템 프롬프트
│   │   └── rule_system.txt              # 병원 규칙 시스템 프롬프트
│   ├── sql/
│   │   ├── typo_dictionary.sql          # 오타 사전 테이블
│   │   └── feedback_schema.sql          # 피드백 테이블
│   ├── tests/                           # pytest 단위 테스트
│   ├── run.bat, run.sh                  # 실행 스크립트
│   ├── requirements.txt, requirements-dev.txt
│   ├── pyproject.toml
│   └── Dockerfile
├── llm_data/                            # 데이터 소스
│   ├── medical_rules.json               # 병원 규칙 (200+건)
│   ├── 08.전문 의학지식 데이터.zip      # 의학 Q&A/콘텐츠 (별도 확보)
│   └── 09.필수의료 의학지식 데이터.zip
├── scripts/                             # DB 마이그레이션·초기화
│   ├── medical-tables.sql               # medical_domain, medical_content, medical_qa, medical_rule
│   ├── init-mysql.sql                   # DB 초기 설정
│   ├── erd-alignment-migration.sql
│   ├── medical-chat-history-migration.sql
│   ├── run-mysql-init.ps1
│   └── check-mysql-password.ps1
├── doc/                                 # 프로젝트 문서
│   ├── PRD.md                           # 제품 요구사항
│   ├── ERD.md                           # 데이터베이스 설계
│   ├── DATA_RESTORE_GUIDE.md            # llm_db 재설치 후 데이터 복원 가이드
│   ├── TROUBLESHOOTING.md               # 트러블슈팅 가이드
│   ├── SETUP_OLLAMA.md                  # Ollama 설치/연동 가이드
│   ├── RULE_SPRING.md, RULE_PYTHON.md  # 개발 규칙
│   ├── IMPROVEMENT_PYTHON_LLM.md        # Python LLM 개선 제안서
│   ├── TASK_IMPROVEMENT_WORKFLOW.md     # 개선 작업 실행 계획
│   ├── TASK_RAG_VECTOR_SEARCH.md        # RAG 벡터 검색 가이드
│   ├── TASK_MEDICAL_RULE_RAG.md         # 병원 규칙 RAG
│   ├── TASK_*.md                        # 기능별 작업 문서
│   ├── ERD_ALIGNMENT.md, ERD_NON_STANDARD_TABLES.md
│   ├── MVP_FEATURES.md
│   ├── TASK_VLLM_MIGRATION.md         # Ollama→vLLM 전환 기획서
│   ├── CODE_REVIEW_PYTHON_LLM.md      # Python LLM 코드 리뷰 리포트
│   ├── VLLM-QWEN2.5-7B-WSL2-GUIDE.md # vLLM WSL2 설치 가이드
├── .claude/                             # Claude 스킬 규칙
│   ├── rules/common-rule.md
│   └── skills/
├── docker-compose.yml                   # MySQL + ChromaDB (+ python-llm, spring-app)
├── Dockerfile                           # Spring Boot Docker 이미지
├── build.gradle
├── .env.example, .env
└── .gitignore
```

## 실행 순서

**반드시 아래 순서대로 실행해야 합니다.**

### 1. Docker 컨테이너 실행

```bash
docker-compose up -d
```

MySQL(포트 3307)과 ChromaDB(포트 8100)가 실행됩니다.

### 2. LLM 백엔드 실행 (vLLM 또는 Ollama)

#### vLLM 사용 시 (권장)
별도 서버(192.168.0.22 등)에 vLLM이 구축되어 있다면 환경변수만 설정:
```bash
VLLM_BASE_URL=http://192.168.0.22:8000
LLM_BACKEND=vllm
```
자세한 설정은 [vLLM WSL2 가이드](doc/VLLM-QWEN2.5-7B-WSL2-GUIDE.md)를 참고하세요.

#### Ollama 사용 시 (폴백)
Ollama를 설치하고 필요한 모델을 다운로드합니다.
자세한 설정은 [Ollama 설치 가이드](doc/SETUP_OLLAMA.md)를 참고하세요.

```bash
# Ollama 설치 후 모델 다운로드
ollama pull qwen2.5:7b              # LLM 추론 모델
ollama pull nomic-embed-text       # 임베딩 모델 (RAG 벡터 검색용)

# Ollama 서버 실행 (기본 포트 11434)
ollama serve
```

### 3. Python LLM 서버 설치 (포트 8000)

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

# 전체 인덱싱
python index_medical_data.py

# 증분 인덱싱 (이전 실행 이후 변경분만)
python index_medical_data.py
# --full 플래그로 강제 전체 재인덱싱 가능
python index_medical_data.py --full

# 병원 규칙 인덱싱
python index_rule_data.py
```

성공 시 `=== Indexing complete: N total documents ===` 출력.
상세 내용: [RAG 벡터 검색 가이드](doc/TASK_RAG_VECTOR_SEARCH.md)

### 5. Python LLM 서버 시작

**Linux / Mac (bash) — vLLM 기본**

```bash
LLM_BACKEND=vllm VLLM_BASE_URL=http://192.168.0.22:8000 \
  uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

**Linux / Mac (bash) — Ollama 폴백**

```bash
LLM_BACKEND=ollama OLLAMA_MODEL=qwen2.5:7b \
  uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

**Windows PowerShell — vLLM 기본**

```powershell
$env:LLM_BACKEND="vllm"; $env:VLLM_BASE_URL="http://192.168.0.22:8000"; uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

**Windows PowerShell — Ollama 폴백**

```powershell
$env:LLM_BACKEND="ollama"; $env:OLLAMA_MODEL="qwen2.5:7b"; uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

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

| 변수              | 기본값                  | 설명                  |
| ----------------- | ----------------------- | --------------------- |
| `MYSQL_USERNAME`  | `root`                  | MySQL 사용자명        |
| `MYSQL_PASSWORD`  | `rootpassword`          | MySQL 비밀번호        |
| `LLM_SERVICE_URL` | `http://localhost:8000` | Python LLM 서버 URL   |
| `SERVER_PORT`     | `8080`                  | Spring Boot 서버 포트 |

**Python LLM 서버** (`python-llm/.env`):

| 변수                        | 기본값                   | 설명                                  |
| --------------------------- | ------------------------ | ------------------------------------- |
| `LLM_BACKEND`               | `vllm`                   | LLM 백엔드 (`huggingface` / `ollama` / `vllm`) |
| `VLLM_BASE_URL`             | `http://localhost:8000`  | vLLM 서버 URL                         |
| `VLLM_MODEL`                | `qwen2.5-7b`             | vLLM 모델명                           |
| `OLLAMA_BASE_URL`           | `http://localhost:11434` | Ollama 서버 URL                       |
| `OLLAMA_MODEL`              | `qwen2.5:7b`             | Ollama 추론 모델명                    |
| `OLLAMA_EMBED_MODEL`        | `nomic-embed-text`       | Ollama 임베딩 모델명                  |
| `USE_VECTOR_SEARCH`         | `True`                   | 벡터 검색 사용 여부                   |
| `VECTOR_SEARCH_TOP_K`       | `3`                      | 벡터 검색 상위 K건                    |
| `USE_QUERY_EXPANSION`       | `False`                  | 쿼리 확장 사용 여부                   |
| `USE_RERANKING`             | `False`                  | Re-ranking 사용 여부                  |
| `CHROMA_HOST`               | `localhost`              | ChromaDB 서버 호스트                  |
| `CHROMA_PORT`               | `8100`                   | ChromaDB 서버 포트                    |
| `CORS_ORIGINS`              | `http://localhost:8080`  | 허용 CORS origins (콤마 구분)         |
| `MEDICAL_CONTEXT_MAX_CHARS` | `1500`                   | 의학 컨텍스트 최대 문자 수            |
| `LLM_INFER_TIMEOUT_SEC`     | `60`                     | 추론 타임아웃 (초)                    |
| `LLM_FALLBACK_MOCK`         | `false`                  | Mock 모드 (torch 없이 테스트)         |

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
        {
          "dayOfWeek": "MON",
          "startTime": "09:00",
          "endTime": "17:00",
          "available": true
        }
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

의사/간호사가 병원 내부 규칙(당직, 물품, 위생 등)에 대해 질의합니다. `X-Staff-Id` 헤더 필수.

```bash
curl -X POST http://localhost:8080/api/chat/query \
  -H "Content-Type: application/json" \
  -H "X-Staff-Id: 1" \
  -d '{"query": "당직 근무 규정이 어떻게 되나요?"}'
```

### Python LLM 서버 직접 API

| 엔드포인트             | 메서드 | 설명                         | Rate Limit |
| ---------------------- | ------ | ---------------------------- | ---------- |
| `/infer`               | POST   | 기본 LLM 추론                | 20/min     |
| `/infer/medical`       | POST   | 의학 컨텍스트 + Chat API     | 10/min     |
| `/infer/medical/stream`| POST   | 의학 컨텍스트 + SSE 스트리밍 | 10/min     |
| `/infer/rule`          | POST   | 병원 규칙 RAG + Chat API     | 10/min     |
| `/feedback`            | POST   | LLM 응답 품질 피드백 저장    | 10/min     |
| `/feedback/stats`      | GET    | 피드백 통계 조회             | -          |
| `/metrics`             | GET    | 추론 메트릭 조회             | 30/min     |
| `/health`              | GET    | 헬스체크 (Ollama/MySQL/ChromaDB) | -      |
| `/typo/reload`         | POST   | 오타 사전 DB 리로드          | 2/min      |

### 히스토리 조회

**`GET /api/medical/history/{staffId}`** — 의학/질병 관련 질의응답 이력

**`GET /api/chat/history/{staffId}`** — 병원 규칙 Q&A 이력

```bash
# 의학 이력 조회
curl http://localhost:8080/api/medical/history/1

# 규칙 Q&A 이력 조회
curl http://localhost:8080/api/chat/history/1
```

## 에러 응답

| HTTP 상태 | 상황                      | 응답 메시지                   |
| --------- | ------------------------- | ----------------------------- |
| 429       | Rate Limit 초과           | Rate limit exceeded           |
| 503       | Python LLM 서버 연결 실패 | LLM 서버를 사용할 수 없습니다 |
| 503       | Circuit Breaker OPEN      | 서비스 일시 중단 (Retry-After: 30) |
| 504       | LLM 응답 시간 초과        | LLM 응답 시간 초과            |
| 500       | 서버 내부 오류            | 서버 내부 오류가 발생했습니다 |

## 데이터베이스 스키마

### staff

| 컬럼            | 타입         | 설명             |
| --------------- | ------------ | ---------------- |
| id              | BIGINT (PK)  | 직원 고유 식별자 |
| username        | VARCHAR(100) | 로그인 ID        |
| employee_number | VARCHAR(20)  | 사번             |
| email           | VARCHAR(255) | 이메일 주소      |

### medical_history (의학/질병 관련)

| 컬럼       | 타입        | 설명                       |
| ---------- | ----------- | -------------------------- |
| id         | BIGINT (PK) | 고유 ID                    |
| staff_id   | BIGINT (FK) | 직원 ID                    |
| question   | TEXT        | 질문                       |
| answer     | TEXT        | LLM 응답                   |
| status     | VARCHAR(20) | PENDING, COMPLETED, FAILED |
| metadata   | TEXT        | JSON (latency_ms 등)       |
| created_at | DATETIME    | 생성 시각                  |

### chatbot_history (병원 규칙 Q&A)

| 컬럼       | 타입         | 설명      |
| ---------- | ------------ | --------- |
| id         | BIGINT (PK)  | 고유 ID   |
| staff_id   | BIGINT (FK)  | 직원 ID   |
| session_id | VARCHAR(100) | 세션 ID   |
| question   | TEXT         | 질문      |
| answer     | TEXT         | LLM 응답  |
| created_at | DATETIME     | 생성 시각 |

### typo_dictionary (오타 교정 사전)

| 컬럼         | 타입        | 설명               |
| ------------ | ----------- | ------------------ |
| id           | INT (PK)    | 고유 ID            |
| typo         | VARCHAR(50) | 오타 표기 (UNIQUE) |
| correct_term | VARCHAR(50) | 올바른 표기        |
| category     | VARCHAR(30) | 카테고리           |
| hit_count    | INT         | 교정 사용 횟수     |

### llm_feedback (LLM 응답 피드백)

| 컬럼       | 타입         | 설명                    |
| ---------- | ------------ | ----------------------- |
| id         | INT (PK)     | 고유 ID                 |
| session_id | VARCHAR(100) | 세션 ID                 |
| query      | TEXT         | 사용자 질문             |
| response   | TEXT         | LLM 응답               |
| score      | INT          | 만족도 (1-5)            |
| comment    | TEXT         | 피드백 코멘트           |
| endpoint   | VARCHAR(50)  | 사용 엔드포인트         |

## 테스트

### Spring Boot

```bash
./gradlew test
```

`@WebMvcTest`와 `@MockBean`을 사용하여 실제 Python LLM 서버 없이 컨트롤러 단위 테스트를 실행합니다.

### Python LLM 서버

```bash
cd python-llm

# 프로덕션 의존성만 설치된 환경
pip install -r requirements.txt
python -m pytest tests/ -v

# 개발 환경 (ruff, mypy 등 포함)
pip install -r requirements-dev.txt
python -m pytest tests/ -v --cov
```

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
    ├── /infer/medical         → 의학 컨텍스트 + LLM Chat (동기)
    ├── /infer/medical/stream  → 의학 컨텍스트 + LLM Chat (SSE 스트리밍)
    ├── /infer/rule            → 병원 규칙 RAG + LLM Chat
    ├── /feedback              → LLM 응답 피드백 수집
    ├── /metrics               → 추론 메트릭 모니터링
    ├── vllm_service         → vLLM OpenAI 호환 API (기본)
    ├── ollama_service       → Ollama API (폴백)
    ├── Circuit Breaker        → LLM 장애 격리 (5회 실패 → 30초 차단)
    ├── Rate Limiting          → slowapi (10~20/min)
    ├── medical_context_service → 하이브리드 검색 (asyncio.gather 병렬)
    │   ├── ChromaDB 벡터 검색 (의미 유사도, 우선)
    │   ├── MySQL FULLTEXT 검색 (키워드, 폴백)
    │   ├── Re-ranking (LLM 기반 관련성 재정렬, 선택)
    │   └── 쿼리 확장 (의학 용어 보강, 선택)
    ├── prompt_loader    → 시스템 프롬프트 외부 파일 관리
    ├── response_cleaner → CJK 필터링 + 후처리
    └── typo_corrector   → 의료 용어 오타 교정 (DB + 내장 사전)
    ↓
[vLLM :8000 (외부)]
    └── qwen2.5-7b (AWQ 4bit) → LLM 추론 (기본)

[Ollama :11434]
    ├── qwen2.5:7b          → LLM 추론 (폴백)
    └── nomic-embed-text   → 임베딩 (RAG 벡터 검색)

[MySQL :3307]
    ├── medical_qa / medical_content → 의학 지식 데이터
    ├── doctors / doctor_schedules   → 의사 + 진료 스케줄
    ├── medical_history              → 의료 상담 이력
    ├── chatbot_history              → 병원 규칙 Q&A 이력
    ├── medical_rules                → 병원 규칙 데이터
    ├── typo_dictionary              → 오타 교정 사전
    ├── llm_feedback                 → LLM 응답 피드백
    └── staff                        → 직원 정보

[ChromaDB :8100]
    ├── medical_docs    → 의학 문서 벡터 컬렉션
    └── medical_rules   → 병원 규칙 벡터 컬렉션
```

## 주요 기능

| 기능              | 설명                                               |
| ----------------- | -------------------------------------------------- |
| 의료 상담         | 증상 입력 → 추천 진료과 + 담당 의사 + AI 상담 응답 |
| SSE 스트리밍      | 토큰 단위 실시간 응답으로 체감 속도 개선           |
| RAG 벡터 검색     | ChromaDB + Ollama 임베딩으로 의미 기반 문서 검색   |
| 하이브리드 검색   | 벡터 검색 우선 → MySQL FULLTEXT 폴백 (병렬 실행)   |
| Re-ranking        | LLM 기반 검색 결과 관련성 재정렬 (선택적 활성화)   |
| 쿼리 확장         | 짧은 질문을 의학 용어로 확장하여 검색 재현율 향상  |
| 텍스트 청킹       | 긴 문서를 오버랩 청크로 분할하여 벡터 검색 품질 향상 |
| Circuit Breaker   | Ollama 장애 시 자동 격리 (5회 실패 → 30초 차단)    |
| Rate Limiting     | slowapi 기반 API 호출 제한 (10~20/min)             |
| 오타 교정         | 의학 용어 오타 자동 보정 (DB + 내장 사전, hit 추적) |
| 중국어 필터링     | 시스템 프롬프트 강화 + CJK 패턴 실시간 제거        |
| Multi-turn 대화   | 최근 3턴 대화 이력을 컨텍스트에 포함               |
| 피드백 수집       | LLM 응답 만족도 (1-5) 피드백 저장 + 통계 조회      |
| 추론 메트릭       | 지연시간, 성공률, 벡터 히트율 실시간 모니터링      |
| 증분 인덱싱       | 타임스탬프 기반 변경분만 재인덱싱 (--full로 전체)  |
| 챗 히스토리       | 상담 이력 자동 저장 (PENDING → COMPLETED/FAILED)   |
| 프론트엔드        | 병렬 API 호출, 스트리밍 우선 + 폴백 렌더링         |

## 참고 문서

- [PRD (제품 요구사항)](doc/PRD.md)
- [ERD (데이터베이스 설계)](doc/ERD.md)
- [데이터 복원 가이드](doc/DATA_RESTORE_GUIDE.md) — llm_db 재설치 후 데이터 복원
- [HMS 병합 가이드](doc/HMS_MERGE_GUIDE.md) — proejct-team-alpha/hms 프로젝트에 합칠 때 수정사항
- [RAG 벡터 검색 가이드](doc/TASK_RAG_VECTOR_SEARCH.md)
- [Python LLM 개선 제안서](doc/IMPROVEMENT_PYTHON_LLM.md)
- [개선 작업 실행 계획](doc/TASK_IMPROVEMENT_WORKFLOW.md)
- [트러블슈팅 가이드](doc/TROUBLESHOOTING.md)
- [Spring Boot 개발 규칙](doc/RULE_SPRING.md)
- [Python 개발 규칙](doc/RULE_PYTHON.md)
- [Ollama 설치/연동 가이드](doc/SETUP_OLLAMA.md)
- [vLLM 전환 기획서](doc/TASK_VLLM_MIGRATION.md)
- [vLLM WSL2 설치 가이드](doc/VLLM-QWEN2.5-7B-WSL2-GUIDE.md)
- [Python LLM 코드 리뷰](doc/CODE_REVIEW_PYTHON_LLM.md)
- [Python LLM 모듈 README](python-llm/README.md)
