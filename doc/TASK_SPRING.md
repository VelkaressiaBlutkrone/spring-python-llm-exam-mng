# Spring Boot 백엔드 작업 목록

> 참조: [PRD.md](./PRD.md), [RULE_SPRING.md](./RULE_SPRING.md)

Spring Boot 백엔드는 REST API를 제공하고, MySQL에 데이터를 저장하며, Python LLM 서버를 HTTP로 호출합니다.

---

## 작업 단계 (총 10단계)

### Step 1. Spring Boot 프로젝트 생성
- **요구사항**: Spring Initializr로 Java 17, Spring Boot 3.x 기반 프로젝트를 생성합니다.
- **의존성**: `Spring Web`, `Spring WebFlux`(비동기 `WebClient`용), `Spring Data JPA`, `MySQL Driver`, `Lombok`.

**Workflow**:
1.  `start.spring.io` 또는 IDE의 Spring Initializr 기능을 사용합니다.
2.  프로젝트 메타데이터를 설정합니다 (e.g., Group: `com.sample`, Artifact: `llm-api`).
3.  **의존성 목록에서 `Spring Web`, `Spring WebFlux`, `Spring Data JPA`, `MySQL Driver`, `Lombok`을 선택**합니다.
4.  프로젝트를 생성하고 IDE로 가져옵니다.

**산출물**: `build.gradle`, 기본 패키지 구조.

---

### Step 2. application.yml 설정
- **요구사항**: MySQL 데이터소스, JPA, LLM 서비스 URL 등 핵심 설정을 구성합니다.

**Workflow**:
1.  `src/main/resources/application.yml` 파일을 생성합니다.
2.  `RULE_SPRING.md`를 참조하여 **데이터베이스 연결 정보**를 추가합니다.
    ```yaml
    spring:
      datasource:
        url: jdbc:mysql://localhost:3306/llm_db?useSSL=false&serverTimezone=UTC
        username: root
        password: password # 실제 비밀번호는 환경변수로 관리 권장
        driver-class-name: com.mysql.cj.jdbc.Driver
    ```
3.  **JPA 및 하이버네이트 설정**을 추가합니다. (`ddl-auto: update`는 개발용)
    ```yaml
      jpa:
        hibernate:
          ddl-auto: update
        properties:
          hibernate:
            format_sql: true
    ```
4.  **Python LLM 서버 URL**을 환경변수 또는 설정 파일에 추가합니다.
    ```yaml
    llm:
      service:
        url: "http://localhost:8000"
    ```
5.  서버 포트 및 로깅 레벨을 설정합니다.

**산출물**: `src/main/resources/application.yml`

---

### Step 3. User 엔티티 및 Repository
- **요구사항**: 사용자 정보를 저장할 `User` 엔티티와 `UserRepository`를 생성합니다.

**Workflow**:
1.  `com.sample.llm.entity` 패키지에 `User.java` 엔티티를 생성합니다.
2.  `PRD.md`의 데이터 모델에 따라 `id`, `username`, `email` 필드를 추가하고 `@Entity`, `@Id`, `@GeneratedValue` 어노테이션을 설정합니다.
3.  `com.sample.llm.repository` 패키지에 `UserRepository` 인터페이스를 생성하고 `JpaRepository<User, Long>`를 상속받도록 합니다.

**산출물**: `User.java`, `UserRepository.java`

---

### Step 4. ChatHistory 엔티티 및 Repository
- **요구사항**: `PRD.md`에 명시된 모든 컬럼을 포함하는 `ChatHistory` 엔티티와 `ChatHistoryRepository`를 생성합니다.

**Workflow**:
1.  `com.sample.llm.entity` 패키지에 `ChatHistory.java` 엔티티를 생성합니다.
2.  `RULE_SPRING.md`의 데이터 모델 규칙에 따라 **`id`, `userId`, `sessionId`, `query`, `response`, `status`, `metadata`, `timestamp`** 필드를 모두 추가합니다.
3.  `@Column(columnDefinition = "TEXT")` (query, response), `@Column(columnDefinition = "JSON")` (metadata) 등 상세 설정을 적용합니다.
4.  `com.sample.llm.repository` 패키지에 `ChatHistoryRepository` 인터페이스를 생성하고 `JpaRepository<ChatHistory, Long>`를 상속받도록 합니다.

**산출물**: `ChatHistory.java`, `ChatHistoryRepository.java`

---

### Step 5. WebClient 및 LLM 서비스 설정
- **요구사항**: `RestTemplate` 대신 **`WebClient`**를 사용하여 Python LLM 서버를 비동기 호출하는 서비스를 구현합니다.

**Workflow**:
1.  `com.sample.llm.config` 패키지에 `WebClientConfig.java`를 생성하여 `WebClient.Builder`를 Bean으로 등록합니다.
2.  LLM 서버 URL을 `@Value("${llm.service.url}")`로 주입받아 기본 URL로 설정하고, 타임아웃(e.g., 30초)을 설정합니다.
3.  `com.sample.llm.service` 패키지에 `LlmService.java`를 생성합니다.
4.  `WebClient`를 주입받아 `callLlmApi(String query)` 메서드를 구현합니다.
5.  Python 서버의 `/infer` API 명세에 맞춰 **`{"query": "..."}` 형식의 JSON으로 요청**하고, `Mono<String>` 형태로 응답을 받아 처리합니다.

**산출물**: `WebClientConfig.java`, `LlmService.java`

---

### Step 6. LlmController 기본 구현
- **요구사항**: `POST /api/llm/query` 엔드포인트를 구현하여 LLM 호출 및 상태 저장을 비동기 파이프라인으로 처리합니다.

**Workflow**:
1.  `com.sample.llm.controller` 패키지에 `LlmController.java`를 생성합니다.
2.  `LlmService`와 `ChatHistoryRepository`를 의존성으로 주입받습니다.
3.  `@PostMapping("/query")` 엔드포인트를 구현합니다.
4.  **비동기 처리 파이프라인**:
    a.  **(DB 저장 1)** `ChatHistory` 객체를 생성하여 `query`와 `status='PENDING'`을 설정하고 DB에 저장합니다.
    b.  **(API 호출)** `llmService.callLlmApi()`를 호출하여 `Mono` 스트림을 시작합니다.
    c.  **(DB 저장 2)** `doOnNext`를 사용하여 LLM 응답을 받으면 `ChatHistory` 객체의 `response`와 `status='COMPLETED'`를 설정하고 DB를 업데이트합니다.
5.  최종적으로 LLM 응답을 클라이언트에 반환합니다.

**산출물**: `LlmController.java`, `/api/llm/query` 동작 확인

---

### Step 7. ChatHistory 저장 연동
- **요구사항**: `LlmController`의 비동기 파이프라인 내에서 `ChatHistory`의 상태(PENDING → COMPLETED/FAILED)를 정확하게 업데이트합니다.

**Workflow**:
1.  (Step 6에서 이어짐) `LlmService`의 LLM 호출 및 DB 업데이트 로직을 `@Transactional`이 적용된 별도 서비스 메서드로 분리하여 트랜잭션 원자성을 보장합니다.
2.  `llmService.callLlmApi`의 `Mono` 스트림에 `doOnError`를 추가하여, API 호출 실패 시 `ChatHistory`의 `status`를 **`FAILED`**로 업데이트하는 로직을 구현합니다.
3.  (선택) 사용자 식별이 필요할 경우, `SecurityContextHolder`나 요청 헤더에서 `userId`를 추출하여 `ChatHistory`에 저장합니다.

**산출물**: LLM 호출 결과에 따라 `chat_history` 테이블의 `status`가 정확히 변경됨

---

### Step 8. 에러 핸들링 및 Fallback
- **요구사항**: `@ControllerAdvice`를 사용하여 Python 서버 연동 실패 시 `RULE_SPRING.md`에 정의된 HTTP 상태와 메시지를 반환합니다.

**Workflow**:
1.  `com.sample.llm.exception` 패키지에 `GlobalExceptionHandler.java`를 생성하고 `@ControllerAdvice`를 붙입니다.
2.  `WebClientResponseException`을 처리하는 `@ExceptionHandler`를 추가합니다.
    -   `getRawStatusCode() == 503`이면 "LLM 서버 사용 불가" 메시지와 함께 503 상태를 반환합니다.
    -   `getRawStatusCode() == 504`이면 "LLM 응답 시간 초과" 메시지와 함께 504 상태를 반환합니다.
3.  `LlmService`의 API 호출 부분에 `.onErrorResume()`을 사용하여, 예외 발생 시 `Mono.error()`를 통해 처리하거나 Fallback 응답(`Mono.just("대체 응답")`)을 반환합니다.

**산출물**: `GlobalExceptionHandler.java`, 안정적인 에러 응답

---

### Step 9. (선택) 챗 히스토리 조회 API
- **요구사항**: 특정 사용자의 챗 히스토리를 조회하는 `GET /api/llm/history/{userId}` API를 구현합니다.

**Workflow**:
1.  `LlmController`에 `@GetMapping("/history/{userId}")` 엔드포인트를 추가합니다.
2.  `ChatHistoryRepository`에 `findByUserIdOrderByTimestampDesc(Long userId)` 메서드를 정의합니다.
3.  컨트롤러에서 이 메서드를 호출하여 조회된 `List<ChatHistory>`를 DTO 리스트로 변환 후 반환합니다.
4.  (심화) `Pageable` 파라미터를 추가하여 페이징 기능을 구현할 수 있습니다.

**산출물**: `LlmController`에 히스토리 조회 엔드포인트 추가

---

### Step 10. 테스트 및 문서화
- **요구사항**: `WebMvcTest`와 `@MockBean`을 사용하여 실제 Python 서버 호출 없이 컨트롤러를 단위 테스트하고, `README.md`를 업데이트합니다.

**Workflow**:
1.  `src/test/java`에 `LlmControllerTest.java`를 `@WebMvcTest(LlmController.class)`로 생성합니다.
2.  `@MockBean`을 사용하여 `LlmService`와 `ChatHistoryRepository`를 가짜 객체로 만듭니다.
3.  `when(llmService.callLlmApi(anyString())).thenReturn(Mono.just("Mock 응답"))`과 같이 Mock 객체의 동작을 정의합니다.
4.  `mockMvc.perform(post("/api/llm/query")...)`를 사용하여 API를 호출하고, 상태 코드와 응답 본문을 검증합니다.
5.  `README.md`에 **실행 순서(MySQL → Python → Spring)**, API 사용법, `curl` 예제를 명확히 문서화합니다.

**산출물**: `LlmControllerTest.java`, 업데이트된 `README.md`

---

## 데이터베이스 스키마

| 테이블 | 주요 컬럼 |
| ------ | --------- |
| users | id, username, email |
| chat_history | id, user_id, session_id, query, response, status, metadata, timestamp |

---

## API 스펙 (Spring Boot)

| 엔드포인트 | 메서드 | 설명 |
| ---------- | ------ | ---- |
| `/api/llm/query` | POST | 쿼리 전송 → LLM 응답 반환, DB 저장 |
| `/api/llm/history/{userId}` | GET | (선택) 특정 사용자의 챗 히스토리 조회 |

**요청 예시** (`POST /api/llm/query`):

```json
{
  "query": "안녕하세요, 오늘 날씨는?"
}
```

**응답**: LLM 생성 텍스트 (plain text 또는 JSON)

---

## 실행 순서

1.  **MySQL** 컨테이너 실행 (`docker run ...`)
2.  **Python LLM 서버** 실행 (`uvicorn app:app --port 8000`)
3.  **Spring Boot 애플리케이션** 실행
