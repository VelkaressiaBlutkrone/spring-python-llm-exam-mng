# ERD 문서에 없는 테이블 정리

> **기준 문서:** [proejct-team-alpha/documents](https://github.com/proejct-team-alpha/documents) ERD v4.0
> **작성일:** 2026-03-10

본 프로젝트(spring_llm_sample_mng)는 LLM 샘플 + 의학지식 관리 시스템으로, HMS(병원 예약 & 내부 업무 시스템) ERD 문서와 **부분적으로** 정합됩니다.

## 테이블 역할 구분

| 테이블            | 용도                                             | ERD 대응        |
| ----------------- | ------------------------------------------------ | --------------- |
| `medical_history` | 의학/질병 관련 질의응답 (증상 추천, 진료과 추천) | —               |
| `chatbot_history` | 병원 규칙 Q&A (당직, 물품, 위생 등)              | CHATBOT_HISTORY |

---

## 1. medical_domain — 의학 도메인 코드

| 컬럼명        | 타입        | 제약             | 설명                                         |
| ------------- | ----------- | ---------------- | -------------------------------------------- |
| `domain_id`   | INT         | PK               | 도메인 고유 ID                               |
| `domain_name` | VARCHAR(50) | NOT NULL, UNIQUE | 진료과/도메인명 (예: 영상의학과, 내과, 외과) |

**용도:** 의학지식 데이터(medical_content, medical_qa)의 도메인 분류 및 Doctor 엔티티의 진료과 매핑.

**ERD와의 차이:** ERD의 `DEPARTMENT`는 병원 내 진료과 정보(id, name, is_active)이며, `medical_domain`은 **의학 분류 코드**로 목적이 다릅니다.

**초기 데이터:** 영상의학과, 내과, 외과, 마취통증의학과, 비뇨의학과, 안과, 신경과, 신경외과, 종양내과, 병리과, 산부인과, 이비인후과, 정신건강의학과, 피부과, 예방의학, 의료법규, 소아청소년과, 응급의학과

---

## 2. medical_content — 의학 지식 원문

| 컬럼명          | 타입         | 제약                         | 설명                                   |
| --------------- | ------------ | ---------------------------- | -------------------------------------- |
| `id`            | BIGINT       | PK, AUTO_INCREMENT           | 고유 ID                                |
| `c_id`          | VARCHAR(50)  | NOT NULL                     | 원본 콘텐츠 ID                         |
| `domain`        | INT          | NOT NULL                     | 도메인 번호 (medical_domain.domain_id) |
| `source`        | INT          | NULL                         | 소스 유형 번호                         |
| `source_spec`   | VARCHAR(255) | NULL                         | 소스 상세 (학회명, 교과서명 등)        |
| `creation_year` | VARCHAR(10)  | NULL                         | 생성 연도                              |
| `content`       | LONGTEXT     | NOT NULL                     | 의학 지식 원문                         |
| `dataset`       | VARCHAR(20)  | NOT NULL                     | 데이터셋 구분 (08*전문 / 09*필수의료)  |
| `data_type`     | VARCHAR(20)  | NOT NULL, DEFAULT 'training' | training / validation                  |
| `language`      | VARCHAR(10)  | NOT NULL, DEFAULT 'ko'       | 언어 (ko / en)                         |
| `created_at`    | DATETIME     | NOT NULL, DEFAULT NOW()      | 등록 일시                              |

**용도:** RAG/LLM 학습용 의학 지식 원문 저장. Python LLM 서버에서 MySQL 컨텍스트로 활용.

**ERD와의 관계:** ERD에 해당 테이블 없음. 의학지식 LLM 전용.

---

## 3. medical_qa — 의학 Q&A 라벨링 데이터

| 컬럼명       | 타입        | 제약                         | 설명                                     |
| ------------ | ----------- | ---------------------------- | ---------------------------------------- |
| `id`         | BIGINT      | PK, AUTO_INCREMENT           | 고유 ID                                  |
| `qa_id`      | INT         | NOT NULL                     | 원본 Q&A ID                              |
| `domain`     | INT         | NOT NULL                     | 도메인 번호                              |
| `department` | VARCHAR(50) | NOT NULL                     | 진료과명 (내과, 외과 등)                 |
| `q_type`     | INT         | NOT NULL                     | 질문 유형 (1:객관식, 2:단답형, 3:서술형) |
| `question`   | TEXT        | NOT NULL                     | 질문                                     |
| `answer`     | TEXT        | NOT NULL                     | 답변                                     |
| `dataset`    | VARCHAR(20) | NOT NULL                     | 데이터셋 구분 (08*전문 / 09*필수의료)    |
| `data_type`  | VARCHAR(20) | NOT NULL, DEFAULT 'training' | training / validation                    |
| `created_at` | DATETIME    | NOT NULL, DEFAULT NOW()      | 등록 일시                                |

**용도:** 의학 Q&A 학습/검증 데이터. LLM 추론 시 참조 또는 RAG 확장 시 활용.

**ERD와의 관계:** ERD에 해당 테이블 없음.

---

## 4. doctor — 의사 정보 (ERD와 구조 상이)

| 컬럼명       | 타입         | 제약                   | 설명                |
| ------------ | ------------ | ---------------------- | ------------------- |
| `id`         | BIGINT       | PK, AUTO_INCREMENT     | 의사 고유 ID        |
| `name`       | VARCHAR(50)  | NOT NULL               | 의사명              |
| `department` | VARCHAR(50)  | NOT NULL               | 진료과명            |
| `domain_id`  | INT          | FK, NULL               | medical_domain 참조 |
| `specialty`  | VARCHAR(100) | NULL                   | 전문 분야           |
| `hospital`   | VARCHAR(100) | NOT NULL               | 소속 병원           |
| `phone`      | VARCHAR(20)  | NULL                   | 연락처              |
| `email`      | VARCHAR(255) | NULL                   | 이메일              |
| `bio`        | TEXT         | NULL                   | 소개                |
| `is_active`  | BOOLEAN      | NOT NULL, DEFAULT TRUE | 활성 여부           |
| `created_at` | DATETIME     | NOT NULL               | 등록 일시           |

**ERD와의 차이:** ERD의 `DOCTOR`는 `STAFF`와 1:1 관계이며 `staff_id`, `department_id`, `available_days`, `specialty`만 가짐. 본 프로젝트의 `doctor`는 **독립 의사 정보**로, STAFF 없이 진료과·병원·스케줄만 관리합니다.

**용도:** LLM 증상 추천 시 진료과별 의사 목록 제공.

---

## 5. doctor_schedule — 의사 진료 스케줄

| 컬럼명         | 타입         | 제약                   | 설명               |
| -------------- | ------------ | ---------------------- | ------------------ |
| `id`           | BIGINT       | PK, AUTO_INCREMENT     | 고유 ID            |
| `doctor_id`    | BIGINT       | FK, NOT NULL           | doctor 참조        |
| `day_of_week`  | VARCHAR(10)  | NOT NULL               | 요일 (MON, TUE, …) |
| `start_time`   | TIME         | NOT NULL               | 시작 시간          |
| `end_time`     | TIME         | NOT NULL               | 종료 시간          |
| `max_patients` | INT          | NULL, DEFAULT 20       | 최대 환자 수       |
| `is_available` | BOOLEAN      | NOT NULL, DEFAULT TRUE | 진료 가능 여부     |
| `note`         | VARCHAR(255) | NULL                   | 비고               |

**ERD와의 차이:** ERD의 `DOCTOR.available_days`는 VARCHAR(20)으로 `"MON,WED,FRI"` 형태의 쉼표 구분 문자열입니다. 본 프로젝트는 **별도 스케줄 테이블**로 요일·시간대를 세분화하여 관리합니다.

**용도:** LLM 증상 추천 시 진료 가능 요일·시간대 필터링.

---

## 요약

| 테이블            | ERD 존재     | 용도                                    |
| ----------------- | ------------ | --------------------------------------- |
| `medical_domain`  | ❌           | 의학 도메인 코드, Doctor 매핑           |
| `medical_content` | ❌           | 의학 지식 원문 (RAG/LLM)                |
| `medical_qa`      | ❌           | 의학 Q&A 라벨링 데이터                  |
| `doctor`          | ⚠️ 구조 상이 | 독립 의사 정보 (ERD DOCTOR는 STAFF 1:1) |
| `doctor_schedule` | ❌           | 의사 진료 스케줄 (ERD는 available_days) |

---

_ERD 문서: https://github.com/proejct-team-alpha/documents (02*ERD*문서)_)\*)\*)\*)\*)\*)\*)\*)*
