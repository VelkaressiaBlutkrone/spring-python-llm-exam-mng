# LLM 샘플 관리 시스템 - MVP 필수 기능

> 참조: [PRD.md](./PRD.md), [TASK_SPRING.md](./TASK_SPRING.md), [TASK_PYTHON.md](./TASK_PYTHON.md)

---

## MVP 필수 기능 목록

| 기능 | 설명 | 우선순위 |
| ---- | ---- | -------- |
| **LLM 쿼리 API** | `POST /api/llm/query` - 사용자 쿼리 수신 → LLM 응답 반환 | P0 (필수) |
| **LLM 추론 엔드포인트** | Python `POST /infer` - 쿼리 입력 시 LLM이 텍스트 생성 후 `generated_text` 반환 | P0 (필수) |
| **ChatHistory DB 저장** | 쿼리/응답을 `chat_history` 테이블에 저장, status(PENDING/COMPLETED/FAILED) 관리 | P0 (필수) |
| **WebClient 비동기 호출** | Spring Boot에서 Python LLM 서버를 WebClient로 비동기 HTTP 호출 | P0 (필수) |
| **에러 핸들링** | Python 서버 연결 실패(503), 타임아웃(504) 시 적절한 HTTP 상태 및 메시지 반환 | P0 (필수) |
| **입력 전처리** | LLM 입력 길이 제한(예: 2048자), 공백 정규화 | P0 (필수) |
| **헬스체크** | Python `/` 또는 `/health` - 서버 상태 확인 | P1 (권장) |
| **User/ChatHistory 엔티티** | users, chat_history 테이블 및 JPA 엔티티/Repository | P1 (권장) |
| **환경 설정** | application.yml, .env - DB, LLM URL, 타임아웃 등 | P1 (권장) |
| **ChatHistory 실패 시 FAILED** | LLM API 호출 실패 시 status를 FAILED로 업데이트 | P1 (권장) |
| **Fallback 응답** | LLM 호출 실패 시 기본 응답 반환 (선택) | P2 (선택) |
| **챗 히스토리 조회 API** | `GET /api/llm/history/{userId}` - 사용자별 히스토리 조회 | P2 (선택) |
| **단위 테스트** | LlmController, LlmService Mock 테스트 | P2 (선택) |
| **README 문서화** | 실행 순서(MySQL → Python → Spring), API 사용법 | P2 (선택) |

---

## 우선순위 정의

| 등급 | 의미 |
| ---- | ---- |
| **P0 (필수)** | MVP의 핵심 가치, 없으면 시스템이 동작하지 않음 |
| **P1 (권장)** | 안정적 운영에 필요, MVP 완성도 향상 |
| **P2 (선택)** | 확장·유지보수 편의, 나중에 추가 가능 |

---

## MVP 최소 실행 흐름

1. 클라이언트 → `POST /api/llm/query` (쿼리 전송)
2. Spring Boot → ChatHistory PENDING 저장 → WebClient로 Python `/infer` 호출
3. Python → LLM 추론 → `generated_text` 반환
4. Spring Boot → ChatHistory COMPLETED 업데이트 → 클라이언트에 응답 반환
