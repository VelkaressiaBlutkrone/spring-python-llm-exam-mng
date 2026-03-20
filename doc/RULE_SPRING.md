# Spring Boot 백엔드 개발 규칙

> 참조: [PRD.md](./PRD.md), [TASK_SPRING.md](./TASK_SPRING.md)

---

## 1. 아키텍처 규칙

| 규칙                | 설명                                                           |
| ------------------- | -------------------------------------------------------------- |
| **WebClient 사용**  | Python LLM 호출 시 RestTemplate 대신 **WebClient** 비동기 호출 |
| **상태값 관리**     | chat_history에 `status` (PENDING, COMPLETED, FAILED) 저장      |
| **Spring Boot 3.x** | Java 17+                                                       |
| **의존성**          | Spring Web, WebFlux, Spring Data JPA, MySQL Driver             |

---

## 2. 데이터 모델 규칙

### 2.1 chat_history 엔티티 필수 컬럼

| 컬럼       | 타입          | 필수                            |
| ---------- | ------------- | ------------------------------- |
| id         | Long (PK)     | O                               |
| user_id    | Long (FK)     | 선택                            |
| session_id | String(64)    | 세션 그룹화용                   |
| query      | String (TEXT) | O                               |
| response   | String (TEXT) | O                               |
| status     | String(20)    | O (PENDING/COMPLETED/FAILED)    |
| metadata   | JSON          | 모델명, latency_ms, token_usage |
| timestamp  | LocalDateTime | O                               |

### 2.2 users 엔티티

| 컬럼     | 타입      |
| -------- | --------- |
| id       | Long (PK) |
| username | String    |
| email    | String    |

---

## 3. API 규칙

### 3.1 엔드포인트

| 경로               | 메서드 | 설명                          |
| ------------------ | ------ | ----------------------------- |
| `/api/llm/query`   | POST   | 쿼리 전송 → LLM 응답, DB 저장 |
| `/api/llm/history` | GET    | (선택) 챗 히스토리 조회       |

### 3.2 Python 호출 형식

**요청** (POST `<http://localhost:8000/infer>`):

```json
{
  "query": "사용자 쿼리 텍스트"
}
```

**응답**:

```json
{
  "generated_text": "LLM 생성 텍스트"
}
```

---

## 4. Exception Handling 규칙

Python 서버 장애 시 반환할 HTTP 응답:

| 상황                  | HTTP                    | 응답                                          |
| --------------------- | ----------------------- | --------------------------------------------- |
| Python 서버 연결 실패 | 503 Service Unavailable | `{"detail": "LLM 서버를 사용할 수 없습니다"}` |
| Python 타임아웃       | 504 Gateway Timeout     | `{"detail": "LLM 응답 시간 초과"}`            |
| Python 5xx 에러       | 503                     | Python 에러 메시지 전달                       |

| 규칙                  | 설명                              |
| --------------------- | --------------------------------- |
| **@ControllerAdvice** | 전역 예외 처리                    |
| **로깅**              | 예외 발생 시 로그 출력            |
| **Fallback**          | (선택) LLM 실패 시 기본 응답 반환 |

---

## 5. 설정 규칙

| 항목                | 설명                                         |
| ------------------- | -------------------------------------------- |
| **application.yml** | `llm.service.url` 등 Python 서버 URL 설정    |
| **타임아웃**        | WebClient 타임아웃 설정 (LLM 추론 시간 고려) |
| **ddl-auto**        | 개발: `update`, 운영: `validate`             |

---

## 6. 트랜잭션 규칙

| 규칙                    | 설명                           |
| ----------------------- | ------------------------------ |
| **ChatHistory 저장**    | `@Transactional` 적용          |
| **PENDING → COMPLETED** | 비동기 완료 시 status 업데이트 |

---

## 7. 테스트 규칙

| 규칙                | 설명                                  |
| ------------------- | ------------------------------------- |
| **Mock LlmService** | 실제 Python 호출 없이 컨트롤러 테스트 |
| **@WebMvcTest**     | 컨트롤러 단위 테스트                  |
| **@SpringBootTest** | 통합 테스트 (선택)                    |
| **JUnit 5**         | 테스트 프레임워크                     |

---

## 8. 보안 규칙

| 규칙                | 설명                                    |
| ------------------- | --------------------------------------- |
| **Spring Security** | (선택) API 보호                         |
| **API 키/JWT**      | Python 서버 호출 시 인증 헤더           |
| **비밀정보**        | application.yml 대신 환경변수 사용 권장 |

---

## 9. 실행 순서

1. MySQL 컨테이너 실행
2. Python LLM 서버 실행 (포트 8000)
3. Spring Boot 애플리케이션 실행

---

## 10. 금지 사항

- RestTemplate으로 Python 동기 호출 (장시간 대기 시 부적합)
- chat_history에 status 없이 저장
- Python 에러 시 200 OK 반환
- 트랜잭션 없이 DB 저장
