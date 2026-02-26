# Spring Boot 백엔드 작업 목록

> 참조: [PRD.md](./PRD.md)

Spring Boot 백엔드는 REST API를 제공하고, MySQL에 데이터를 저장하며, Python LLM 서버를 HTTP로 호출합니다.

---

## 작업 단계 (총 10단계)

### Step 1. Spring Boot 프로젝트 생성

- Spring Initializr (start.spring.io) 또는 IDE로 프로젝트 생성
- Java 17+, Spring Boot 3.x
- 의존성 선택: Spring Web, Spring Data JPA, MySQL Driver, Lombok(선택)

**산출물**: `pom.xml` 또는 `build.gradle`, 기본 패키지 구조

---

### Step 2. application.yml 설정

- `spring.datasource`: MySQL URL, username, password
- `spring.jpa.hibernate.ddl-auto`: `update` (개발) 또는 `validate` (운영)
- Python LLM 서버 URL 설정 (e.g., `llm.service.url: http://localhost:8000`)
- 포트, 로깅 레벨 설정

**산출물**: `src/main/resources/application.yml`

---

### Step 3. User 엔티티 및 Repository

- `User` 엔티티: `id`, `username`, `email`
- `@Entity`, `@Table` 어노테이션
- `UserRepository` 인터페이스 (JpaRepository 상속)
- (선택) 초기 사용자 시드 데이터

**산출물**: `User.java`, `UserRepository.java`

---

### Step 4. ChatHistory 엔티티 및 Repository

- `ChatHistory` 엔티티: `id`, `userId`, `query`, `response`, `timestamp`
- `User`와 `@ManyToOne` 관계 (선택)
- `ChatHistoryRepository` 인터페이스
- `findByUserIdOrderByTimestampDesc` 등 조회 메서드 (확장용)

**산출물**: `ChatHistory.java`, `ChatHistoryRepository.java`

---

### Step 5. RestTemplate 및 LLM 서비스 설정

- `RestTemplate` Bean 등록 (또는 `WebClient` 비동기 대안)
- Python 서버 URL, 타임아웃 설정
- `LlmService` 또는 `LlmClient` 클래스 생성
- `callInfer(String query)` 메서드: Python `/infer` 호출 후 응답 반환

**산출물**: `RestTemplateConfig.java`, `LlmService.java`

---

### Step 6. LlmController 기본 구현

- `@RestController`, `@RequestMapping("/api/llm")`
- `POST /api/llm/query` 엔드포인트
- 요청 본문에서 쿼리 텍스트 수신 (`@RequestBody String query` 또는 DTO)
- `LlmService` 호출 → 응답 반환

**산출물**: `LlmController.java`, `/api/llm/query` 동작 확인

---

### Step 7. ChatHistory 저장 연동

- `POST /api/llm/query` 처리 시 LLM 응답 수신 후
- `ChatHistory` 엔티티 생성 및 `ChatHistoryRepository.save()` 호출
- `userId` 처리: 익명 요청 시 null 또는 기본 사용자 ID (요구사항에 따라)
- 트랜잭션 처리

**산출물**: 쿼리/응답이 MySQL `chat_history` 테이블에 저장됨

---

### Step 8. 에러 핸들링 및 Fallback

- `@ControllerAdvice` 또는 `@ExceptionHandler`로 전역 예외 처리
- Python 서버 연결 실패, 타임아웃 시 적절한 HTTP 상태 코드 반환
- Fallback: LLM 호출 실패 시 기본 응답 반환 (선택)
- 로깅

**산출물**: `GlobalExceptionHandler.java`, 안정적인 에러 응답

---

### Step 9. (선택) 챗 히스토리 조회 API

- `GET /api/llm/history` 또는 `GET /api/llm/history/{userId}`
- `ChatHistoryRepository`로 조회 후 반환
- 페이징 지원 (Pageable)

**산출물**: `LlmController`에 히스토리 조회 엔드포인트 추가

---

### Step 10. 테스트 및 문서화

- `LlmController`에 대한 `@WebMvcTest` 또는 `@SpringBootTest` 테스트
- Mock `LlmService`로 LLM 호출 없이 컨트롤러 테스트
- `ChatHistoryRepository` 테스트 (JPA)
- `README.md`에 실행 방법, API 사용법 문서화
- (선택) Spring Security 설정으로 API 보호

**산출물**: `LlmControllerTest.java`, `LlmServiceTest.java`, README

---

## 데이터베이스 스키마

| 테이블 | 주요 컬럼 |
| ------ | --------- |
| users | id, username, email |
| chat_history | id, user_id, query, response, timestamp |

---

## API 스펙 (Spring Boot)

| 엔드포인트 | 메서드 | 설명 |
| ---------- | ------ | ---- |
| `/api/llm/query` | POST | 쿼리 전송 → LLM 응답 반환, DB 저장 |
| `/api/llm/history` | GET | (선택) 챗 히스토리 조회 |

**요청 예시** (`POST /api/llm/query`):

```json
"안녕하세요, 오늘 날씨는?"
```

또는

```json
{
  "query": "안녕하세요, 오늘 날씨는?"
}
```

**응답**: LLM 생성 텍스트 (plain text 또는 JSON)

---

## 실행 순서

1. MySQL 컨테이너 실행
2. Python LLM 서버 실행 (`uvicorn app:app --port 8000`)
3. Spring Boot 애플리케이션 실행
