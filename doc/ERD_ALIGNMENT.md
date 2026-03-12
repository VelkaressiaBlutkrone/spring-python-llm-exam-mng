# ERD 문서 정합 계획

> **기준 문서:** [proejct-team-alpha/documents](https://github.com/proejct-team-alpha/documents) ERD v4.0
> **작성일:** 2026-03-10

## 1. ERD 문서와 매핑

| 현재 테이블    | ERD 테이블        | 변경 내용                       |
| -------------- | ----------------- | ------------------------------- |
| `users`        | `staff`           | 테이블명 변경 (STAFF)           |
| `chat_history` | `chatbot_history` | 테이블명 변경 (CHATBOT_HISTORY) |

### 1.1 users → staff

| 현재 컬럼 | ERD 컬럼        | 비고                           |
| --------- | --------------- | ------------------------------ |
| id        | id              | 유지                           |
| username  | username        | 유지                           |
| email     | —               | ERD에 없음, 확장 컬럼으로 유지 |
| —         | employee_number | nullable 추가 (ERD 필수)       |

### 1.2 chat_history → chatbot_history

| 현재 컬럼  | ERD 컬럼   | 비고                            |
| ---------- | ---------- | ------------------------------- |
| id         | id         | 유지                            |
| user_id    | staff_id   | FK 명칭 변경                    |
| session_id | session_id | 유지                            |
| query      | question   | ERD 명칭                        |
| response   | answer     | ERD 명칭                        |
| status     | —          | 확장 (PENDING/COMPLETED/FAILED) |
| metadata   | —          | 확장 (JSON)                     |
| timestamp  | created_at | ERD 명칭                        |

---

## 2. 마이그레이션 순서

**기존 DB가 있는 경우** (users, chat_history 테이블 존재):

1. 애플리케이션 중지
2. `scripts/erd-alignment-migration.sql` 실행
3. 애플리케이션 재시작

**신규 DB인 경우:** Hibernate `ddl-auto: update`로 자동 생성됨

**API 변경:** `GET /api/llm/history/{userId}` → `GET /api/llm/history/{staffId}` (경로 동일, 파라미터 의미 변경)

---

## 3. ERD에 없는 테이블

→ [ERD_NON_STANDARD_TABLES.md](./ERD_NON_STANDARD_TABLES.md) 참조
