# LLM Sample Management System

Spring Boot + Python + MySQL 기반의 LLM 추론 샘플 시스템입니다.
사용자 쿼리를 받아 Python LLM 서버로 추론을 수행하고, 챗 히스토리를 MySQL에 저장합니다.

## 기술 스택

| 구성 요소 | 기술 |
| --------- | ---- |
| 백엔드 | Spring Boot 4.0.3, Java 21 |
| 데이터베이스 | MySQL 8.0 |
| LLM 서버 | Python 3.10+, FastAPI, Uvicorn |
| 비동기 호출 | Spring WebFlux (WebClient) |
| ORM | Spring Data JPA / Hibernate |

## 프로젝트 구조

```
spring_llm_sample_mng/
├── src/main/java/com/sample/llm/
│   ├── SpringLlmSampleMngApplication.java
│   ├── config/
│   │   ├── DataLoader.java          # 초기 데이터 로딩
│   │   └── WebClientConfig.java     # WebClient Bean 설정
│   ├── controller/
│   │   └── LlmController.java       # REST API 엔드포인트
│   ├── dto/
│   │   ├── ChatHistoryResponse.java # 히스토리 응답 DTO
│   │   ├── ErrorResponse.java       # 에러 응답 DTO
│   │   ├── LlmRequest.java          # LLM 요청 DTO
│   │   └── LlmResponse.java         # LLM 응답 DTO
│   ├── entity/
│   │   ├── ChatHistory.java          # 챗 히스토리 엔티티
│   │   └── User.java                 # 사용자 엔티티
│   ├── exception/
│   │   ├── GlobalExceptionHandler.java         # 전역 예외 처리
│   │   ├── LlmServiceUnavailableException.java # 503 예외
│   │   └── LlmTimeoutException.java            # 504 예외
│   ├── repository/
│   │   ├── ChatHistoryRepository.java
│   │   └── UserRepository.java
│   └── service/
│       └── LlmService.java          # LLM 호출 및 DB 상태 관리
├── src/main/resources/
│   └── application.yml               # 애플리케이션 설정
├── src/test/java/
│   └── com/sample/llm/controller/
│       └── LlmControllerTest.java    # 컨트롤러 단위 테스트
├── python-llm/                        # Python LLM 서버
├── docker-compose.yml                 # MySQL 컨테이너 설정
├── .env.example                       # 환경변수 템플릿
└── build.gradle
```

## 실행 순서

**반드시 아래 순서대로 실행해야 합니다.**

### 1. MySQL 컨테이너 실행

```bash
docker-compose up -d
```

MySQL이 포트 `3307`에서 실행됩니다. (기본 계정: `llm_admin` / `llm_password`)

### 2. Python LLM 서버 실행 (포트 8000)

```bash
cd python-llm
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

> Mock 모드(GPU 없이 테스트): 환경변수 `LLM_FALLBACK_MOCK=1` 설정 후 실행

### 3. Spring Boot 애플리케이션 실행

```bash
# 환경변수 설정 (.env.example 참고)
cp .env.example .env

# 실행
./gradlew bootRun
```

Spring Boot가 포트 `8080`에서 실행됩니다.

## 환경변수

`.env.example` 파일을 `.env`로 복사하여 설정합니다.

| 변수 | 기본값 | 설명 |
| ---- | ------ | ---- |
| `MYSQL_USERNAME` | `root` | MySQL 사용자명 |
| `MYSQL_PASSWORD` | `rootpassword` | MySQL 비밀번호 |
| `LLM_SERVICE_URL` | `http://localhost:8000` | Python LLM 서버 URL |
| `SERVER_PORT` | `8080` | Spring Boot 서버 포트 |

## API 사용법

### LLM 쿼리 전송

**`POST /api/llm/query`**

LLM에 쿼리를 전송하고 응답을 받습니다. 쿼리와 응답은 자동으로 DB에 저장됩니다.

```bash
curl -X POST http://localhost:8080/api/llm/query \
  -H "Content-Type: application/json" \
  -d '{"query": "안녕하세요, 오늘 날씨는?"}'
```

사용자 ID를 지정하여 히스토리를 사용자와 연결할 수 있습니다:

```bash
curl -X POST http://localhost:8080/api/llm/query \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{"query": "안녕하세요, 오늘 날씨는?"}'
```

**요청 본문:**

```json
{
  "query": "안녕하세요, 오늘 날씨는?"
}
```

**응답:** LLM이 생성한 텍스트 (plain text)

### 챗 히스토리 조회

**`GET /api/llm/history/{userId}`**

특정 사용자의 챗 히스토리를 페이징으로 조회합니다.

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
      "query": "안녕하세요, 오늘 날씨는?",
      "response": "안녕하세요! 오늘 날씨에 대해...",
      "status": "COMPLETED",
      "metadata": "{\"model\":\"gpt2\",\"latency_ms\":1250}",
      "timestamp": "2025-03-01T12:00:00"
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

```bash
./gradlew test
```

`@WebMvcTest`와 `@MockBean`을 사용하여 실제 Python LLM 서버 없이 컨트롤러 단위 테스트를 실행합니다.

## 참고 문서

- [PRD (제품 요구사항)](doc/PRD.md)
- [Spring Boot 개발 규칙](doc/RULE_SPRING.md)
- [Spring Boot 작업 목록](doc/TASK_SPRING.md)
- [Python LLM 모듈 README](python-llm/README.md)
