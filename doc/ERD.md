# ERD (Entity Relationship Diagram)

> Spring LLM Sample Management 프로젝트 데이터베이스 설계

## 데이터베이스 정보

| 항목           | 값                          |
| -------------- | --------------------------- |
| DBMS           | MySQL 8.0                   |
| 데이터베이스명 | llm_db                      |
| 스키마 관리    | Hibernate DDL Auto (update) |
| 테스트 DB      | H2 In-Memory                |

---

## 테이블 관계도

```
┌──────────────┐       ┌──────────────────┐
│    users     │       │  medical_domain  │
│──────────────│       │──────────────────│
│ PK id        │       │ PK domain_id     │
│    username  │       │    domain_name   │
│    email     │       └────────┬─────────┘
└──────┬───────┘                │
       │                        │ domain (참조)
       │ user_id (FK)           │
       │                ┌───────┴──────────┐
┌──────┴───────────┐    │                  │
│   chat_history   │    │                  │
│──────────────────│    │                  │
│ PK id            │  ┌─┴────────────────┐ │
│ FK user_id ──────┤  │ medical_content  │ │
│    session_id    │  │──────────────────│ │
│    query         │  │ PK id            │ │
│    response      │  │    c_id          │ │
│    status        │  │    domain ───────┘ │
│    metadata      │  │    source          │
│    timestamp     │  │    source_spec     │
└──────────────────┘  │    creation_year   │
                      │    content         │
                      │    dataset         │
                      │    data_type       │
                      │    language        │
                      │    created_at      │
                      └────────────────────┘

                      ┌────────────────────┐
                      │    medical_qa      │
                      │────────────────────│
                      │ PK id             │
                      │    qa_id          │
                      │    domain ────────── (medical_domain 참조)
                      │    department     │
                      │    q_type        │
                      │    question      │
                      │    answer        │
                      │    dataset       │
                      │    data_type     │
                      │    created_at    │
                      └────────────────────┘
```

---

## 테이블 상세 정의

### 1. users (사용자)

| 컬럼명   | 타입         | 제약조건           | 설명           |
| -------- | ------------ | ------------------ | -------------- |
| id       | BIGINT       | PK, AUTO_INCREMENT | 사용자 고유 ID |
| username | VARCHAR(100) | NOT NULL           | 사용자명       |
| email    | VARCHAR(255) | NOT NULL           | 이메일 주소    |

### 2. chat_history (채팅 이력)

| 컬럼명     | 타입        | 제약조건                | 설명                                             |
| ---------- | ----------- | ----------------------- | ------------------------------------------------ |
| id         | BIGINT      | PK, AUTO_INCREMENT      | 채팅 이력 고유 ID                                |
| user_id    | BIGINT      | FK (users.id)           | 사용자 참조                                      |
| session_id | VARCHAR(64) |                         | 채팅 세션 식별자                                 |
| query      | TEXT        | NOT NULL                | 사용자 질의                                      |
| response   | TEXT        |                         | LLM 응답                                         |
| status     | VARCHAR(20) | NOT NULL                | 상태 (PENDING / COMPLETED / FAILED)              |
| metadata   | TEXT        |                         | JSON 메타데이터 (model, latency_ms, token_usage) |
| timestamp  | DATETIME    | NOT NULL, DEFAULT now() | 생성 시각                                        |

### 3. medical_domain (의료 도메인)

| 컬럼명      | 타입        | 제약조건 | 설명           |
| ----------- | ----------- | -------- | -------------- |
| domain_id   | INT         | PK       | 도메인 고유 ID |
| domain_name | VARCHAR(50) | NOT NULL | 도메인명       |

### 4. medical_content (의료 컨텐츠)

| 컬럼명        | 타입         | 제약조건           | 설명                              |
| ------------- | ------------ | ------------------ | --------------------------------- |
| id            | BIGINT       | PK, AUTO_INCREMENT | 컨텐츠 고유 ID                    |
| c_id          | VARCHAR(50)  | NOT NULL           | 컨텐츠 식별 코드                  |
| domain        | INT          | NOT NULL           | 의료 도메인 (medical_domain 참조) |
| source        | INT          |                    | 출처 코드                         |
| source_spec   | VARCHAR(255) |                    | 출처 상세                         |
| creation_year | VARCHAR(10)  |                    | 생성 연도                         |
| content       | LONGTEXT     | NOT NULL           | 컨텐츠 본문 (FULLTEXT INDEX)      |
| dataset       | VARCHAR(20)  | NOT NULL           | 데이터셋 구분                     |
| data_type     | VARCHAR(20)  | NOT NULL           | 데이터 유형                       |
| language      | VARCHAR(10)  | NOT NULL           | 언어 코드                         |
| created_at    | DATETIME     | NOT NULL           | 등록 일시                         |

### 5. medical_qa (의료 Q&A)

| 컬럼명     | 타입        | 제약조건           | 설명                              |
| ---------- | ----------- | ------------------ | --------------------------------- |
| id         | BIGINT      | PK, AUTO_INCREMENT | Q&A 고유 ID                       |
| qa_id      | INT         | NOT NULL           | Q&A 식별 번호                     |
| domain     | INT         | NOT NULL           | 의료 도메인 (medical_domain 참조) |
| department | VARCHAR(50) | NOT NULL           | 진료과                            |
| q_type     | INT         | NOT NULL           | 질문 유형 코드                    |
| question   | TEXT        | NOT NULL           | 질문 (FULLTEXT INDEX)             |
| answer     | TEXT        | NOT NULL           | 답변                              |
| dataset    | VARCHAR(20) | NOT NULL           | 데이터셋 구분                     |
| data_type  | VARCHAR(20) | NOT NULL           | 데이터 유형                       |
| created_at | DATETIME    | NOT NULL           | 등록 일시                         |

---

## 관계 정의

| 관계                             | 타입 | 설명                                                     |
| -------------------------------- | ---- | -------------------------------------------------------- |
| users → chat_history             | 1:N  | 한 사용자는 여러 채팅 이력을 가짐 (user_id FK)           |
| medical_domain → medical_content | 1:N  | 한 도메인에 여러 의료 컨텐츠가 속함 (domain 논리적 참조) |
| medical_domain → medical_qa      | 1:N  | 한 도메인에 여러 Q&A가 속함 (domain 논리적 참조)         |

> **참고:** `medical_content.domain`과 `medical_qa.domain`은 `medical_domain.domain_id`를 논리적으로 참조하지만, JPA 엔티티에서 `@ManyToOne` 매핑 없이 Integer 값으로 관리됩니다.

---

## 인덱스

| 테이블          | 인덱스   | 타입     | 대상 컬럼 |
| --------------- | -------- | -------- | --------- |
| medical_content | FULLTEXT | 전문검색 | content   |
| medical_qa      | FULLTEXT | 전문검색 | question  |

---

## 초기 데이터

| 테이블 | 조건                          | 데이터                                            |
| ------ | ----------------------------- | ------------------------------------------------- | --- | --- | --- | --- | --- | --- |
| users  | 사용자가 없을 때 (DataLoader) | username: "default", email: "default@example.com" |     |     |     |     |     |     | |
