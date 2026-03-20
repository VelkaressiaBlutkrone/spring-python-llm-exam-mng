# 추가 기능: 의사 정보 및 스케줄 관리

> 참조: [ERD.md](./ERD.md), [TASK_SPRING.md](./TASK_SPRING.md), [PRD.md](./PRD.md)

LLM 의료 상담 응답에 **추천 진료과의 의사 목록**을 함께 제공하여, 사용자가 바로 진료 예약을 검토할 수 있도록 합니다.

---

## 목표

- 의사 정보(doctor)와 의사 스케줄(doctor_schedule) 테이블 신규 생성
- 기존 `medical_domain` 테이블과 연동하여 진료과별 의사 조회
- LLM 응답 시 추천 진료과 + 해당 진료과 의사 목록을 함께 반환
- 프론트엔드에서 진료과 추천 이유 및 의사 목록 표시

---

## 신규 테이블 설계

### 1. doctor (의사 정보)

| 컬럼명     | 타입         | 제약조건                      | 설명                                    |
| ---------- | ------------ | ----------------------------- | --------------------------------------- |
| id         | BIGINT       | PK, AUTO_INCREMENT            | 의사 고유 ID                            |
| name       | VARCHAR(50)  | NOT NULL                      | 의사 이름                               |
| department | VARCHAR(50)  | NOT NULL                      | 진료과 (예: 정형외과, 신경과)           |
| domain_id  | INT          | FK (medical_domain.domain_id) | 의료 도메인 참조                        |
| specialty  | VARCHAR(100) |                               | 세부 전문 분야 (예: 척추외과, 관절외과) |
| hospital   | VARCHAR(100) | NOT NULL                      | 소속 병원명                             |
| phone      | VARCHAR(20)  |                               | 연락처                                  |
| email      | VARCHAR(255) |                               | 이메일                                  |
| bio        | TEXT         |                               | 의사 소개 / 약력                        |
| is_active  | BOOLEAN      | NOT NULL, DEFAULT TRUE        | 활동 상태                               |
| created_at | DATETIME     | NOT NULL                      | 등록 일시                               |

### 2. doctor_schedule (의사 스케줄)

| 컬럼명       | 타입         | 제약조건                 | 설명                               |
| ------------ | ------------ | ------------------------ | ---------------------------------- |
| id           | BIGINT       | PK, AUTO_INCREMENT       | 스케줄 고유 ID                     |
| doctor_id    | BIGINT       | FK (doctor.id), NOT NULL | 의사 참조                          |
| day_of_week  | VARCHAR(10)  | NOT NULL                 | 요일 (MON/TUE/WED/THU/FRI/SAT/SUN) |
| start_time   | TIME         | NOT NULL                 | 진료 시작 시간                     |
| end_time     | TIME         | NOT NULL                 | 진료 종료 시간                     |
| max_patients | INT          | DEFAULT 20               | 시간대별 최대 예약 수              |
| is_available | BOOLEAN      | NOT NULL, DEFAULT TRUE   | 진료 가능 여부                     |
| note         | VARCHAR(255) |                          | 비고 (예: 격주 진료, 오전만 등)    |

---

## 테이블 관계도 (기존 + 신규)

```
┌──────────────────┐
│  medical_domain  │
│──────────────────│
│ PK domain_id     │
│    domain_name   │
└────────┬─────────┘
         │
         │ domain_id (FK)
         │
┌────────┴─────────┐         ┌─────────────────────┐
│     doctor       │         │   doctor_schedule    │
│──────────────────│         │─────────────────────│
│ PK id            │────────→│ PK id               │
│ FK domain_id     │  1:N    │ FK doctor_id         │
│    name          │         │    day_of_week       │
│    department    │         │    start_time        │
│    specialty     │         │    end_time          │
│    hospital      │         │    max_patients      │
│    phone         │         │    is_available      │
│    email         │         │    note              │
│    bio           │         └─────────────────────┘
│    is_active     │
│    created_at    │
└──────────────────┘
```

---

## 작업 단계 (총 8단계)

### Step 1. Doctor 엔티티 및 Repository 생성 (Spring Boot)

**요구사항**: 의사 정보를 저장할 `Doctor` 엔티티와 `DoctorRepository`를 생성합니다.

**Workflow**:

1. `com.sample.llm.entity` 패키지에 `Doctor.java` 엔티티를 생성합니다.
2. `@ManyToOne`으로 `MedicalDomain`과 연관관계를 설정합니다.
3. `com.sample.llm.repository` 패키지에 `DoctorRepository` 인터페이스를 생성합니다.
4. 커스텀 쿼리 메서드를 추가합니다:
   - `findByDepartmentAndIsActiveTrue(String department)` — 진료과별 활동 중인 의사 조회
   - `findByDomainIdAndIsActiveTrue(Integer domainId)` — 도메인별 의사 조회

**산출물**: `Doctor.java`, `DoctorRepository.java`

---

### Step 2. DoctorSchedule 엔티티 및 Repository 생성 (Spring Boot)

**요구사항**: 의사 스케줄을 저장할 `DoctorSchedule` 엔티티와 `DoctorScheduleRepository`를 생성합니다.

**Workflow**:

1. `com.sample.llm.entity` 패키지에 `DoctorSchedule.java` 엔티티를 생성합니다.
2. `@ManyToOne`으로 `Doctor`와 연관관계를 설정합니다.
3. `DoctorScheduleRepository` 인터페이스를 생성합니다.
4. 커스텀 쿼리 메서드를 추가합니다:
   - `findByDoctorIdAndIsAvailableTrue(Long doctorId)` — 특정 의사의 진료 가능 스케줄 조회
   - `findByDoctorDepartmentAndDayOfWeekAndIsAvailableTrue(String department, String dayOfWeek)` — 진료과 + 요일별 가능 스케줄 조회

**산출물**: `DoctorSchedule.java`, `DoctorScheduleRepository.java`

---

### Step 3. DTO 설계 (Spring Boot)

**요구사항**: 의사 정보 및 LLM 통합 응답을 위한 DTO를 생성합니다.

**Workflow**:

1. `DoctorDto.java` — 의사 기본 정보 (id, name, department, specialty, hospital)
2. `DoctorScheduleDto.java` — 스케줄 정보 (dayOfWeek, startTime, endTime, isAvailable)
3. `DoctorWithScheduleDto.java` — 의사 정보 + 스케줄 목록 (의사 상세 조회용)
4. `MedicalLlmResponse.java` — LLM 통합 응답 DTO:
   ```java
   public record MedicalLlmResponse(
       String generatedText,           // LLM 응답 원문
       String recommendedDepartment,   // 추천 진료과
       String recommendationReason,    // 추천 이유 (LLM 응답에서 파싱)
       List<DoctorDto> doctors         // 해당 진료과 의사 목록
   ) {}
   ```

**산출물**: `DoctorDto.java`, `DoctorScheduleDto.java`, `DoctorWithScheduleDto.java`, `MedicalLlmResponse.java`

---

### Step 4. DoctorService 구현 (Spring Boot)

**요구사항**: 진료과 기반 의사 조회 서비스를 구현합니다.

**Workflow**:

1. `com.sample.llm.service` 패키지에 `DoctorService.java`를 생성합니다.
2. 구현 메서드:
   - `findDoctorsByDepartment(String department)` — 진료과명으로 활동 중인 의사 목록 반환
   - `findDoctorsWithSchedule(String department)` — 의사 목록 + 스케줄 포함 조회
3. 진료과명 정규화 처리 (예: "정형외과", "정형 외과" 통일)

**산출물**: `DoctorService.java`

---

### Step 5. LLM 응답 파싱 로직 구현 (Spring Boot)

**요구사항**: LLM 응답 텍스트에서 추천 진료과명을 추출하는 파서를 구현합니다.

**Workflow**:

1. `com.sample.llm.service` 패키지에 `LlmResponseParser.java`를 생성합니다.
2. LLM 응답에서 진료과명을 추출하는 로직 구현:
   - 시스템 프롬프트 규칙에 따라 "**추천 진료과**:" 다음의 진료과명 파싱
   - 정규표현식 패턴: `추천 진료과.*?[:：]\s*(.+?)[\n\r]`
   - 추출 실패 시 null 반환 (의사 목록 없이 LLM 응답만 전달)
3. 추출된 진료과명으로 `DoctorService`를 호출하여 의사 목록 조회

**산출물**: `LlmResponseParser.java`

---

### Step 6. MedicalController 의료 상담 API 확장 (Spring Boot)

**요구사항**: 기존 LLM 쿼리 API를 확장하여 의사 정보를 함께 반환하는 엔드포인트를 추가합니다.

**Workflow**:

1. `MedicalController`에 새 엔드포인트 추가:
   - `POST /api/llm/query/medical` — 의료 상담 + 의사 추천 통합 API
2. 처리 흐름:
   ```
   사용자 쿼리 수신
   → Python /infer/medical 호출 (LLM 응답 수신)
   → LlmResponseParser로 추천 진료과 추출
   → DoctorService로 해당 진료과 의사 목록 조회
   → MedicalLlmResponse DTO로 통합 반환
   ```
3. 기존 `POST /api/llm/query`는 하위 호환성을 위해 유지

**산출물**: `MedicalController.java` 업데이트, 새 엔드포인트 동작 확인

**API 응답 예시** (`POST /api/llm/query/medical`):

```json
{
  "generatedText": "추천 진료과: 정형외과\n\n무릎 통증이 걸을 때 심해지는 증상은...",
  "recommendedDepartment": "정형외과",
  "recommendationReason": "무릎 통증이 걸을 때 심해지는 증상은 관절 문제를 의심할 수 있습니다.",
  "doctors": [
    {
      "id": 1,
      "name": "김정형",
      "department": "정형외과",
      "specialty": "관절외과",
      "hospital": "서울대학교병원"
    },
    {
      "id": 2,
      "name": "이관절",
      "department": "정형외과",
      "specialty": "척추외과",
      "hospital": "세브란스병원"
    }
  ]
}
```

---

### Step 7. 초기 데이터 및 테스트 (Spring Boot)

**요구사항**: DataLoader에 샘플 의사/스케줄 데이터를 추가하고 단위 테스트를 작성합니다.

**Workflow**:

1. `DataLoader.java`에 샘플 의사 데이터 추가:
   - 주요 진료과(정형외과, 신경과, 내과, 피부과 등) 각 2~3명
   - 각 의사당 주간 스케줄 3~5건
2. 테스트 작성:
   - `DoctorServiceTest.java` — 진료과별 의사 조회 테스트
   - `LlmResponseParserTest.java` — LLM 응답 파싱 테스트
   - `MedicalIntegrationTest.java` — `/api/llm/query/medical` 통합 테스트

**산출물**: 샘플 데이터, 테스트 코드

---

### Step 8. 프론트엔드 화면 구현

**요구사항**: LLM 상담 응답 화면에 추천 진료과 이유 및 의사 목록을 표시합니다.

**Workflow**:

1. 상담 결과 화면 구성:
   ```
   ┌─────────────────────────────────────────┐
   │ 💬 상담 결과                              │
   ├─────────────────────────────────────────┤
   │                                         │
   │ 추천 진료과: 정형외과                      │
   │                                         │
   │ 추천 이유:                                │
   │ 무릎 통증이 걸을 때 심해지는 증상은          │
   │ 관절 문제를 의심할 수 있으며, 정형외과에서     │
   │ 정밀 검사를 받으시는 것을 권장합니다.         │
   │                                         │
   ├─────────────────────────────────────────┤
   │ 📋 정형외과 의사 목록                       │
   ├──────┬──────────┬────────┬──────────────┤
   │ 이름 │ 전문분야   │ 병원    │ 진료 스케줄    │
   ├──────┼──────────┼────────┼──────────────┤
   │김정형│ 관절외과   │서울대병원│월,수,금 09-17 │
   │이관절│ 척추외과   │세브란스 │화,목 09-12   │
   └──────┴──────────┴────────┴──────────────┘
   ```
2. `POST /api/llm/query/medical` API를 호출하고 `MedicalLlmResponse`를 파싱하여 화면에 렌더링
3. 의사 목록이 없는 경우 (진료과 추출 실패 시) LLM 응답만 표시

**산출물**: 상담 결과 화면 (진료과 추천 + 의사 목록)

---

## API 스펙 (신규)

| 엔드포인트                       | 메서드 | 설명                                        |
| -------------------------------- | ------ | ------------------------------------------- |
| `/api/llm/query/medical`         | POST   | 의료 상담 + 추천 진료과 의사 목록 통합 반환 |
| `/api/doctors?department={dept}` | GET    | 진료과별 의사 목록 조회                     |
| `/api/doctors/{id}`              | GET    | 의사 상세 정보 + 스케줄 조회                |
| `/api/doctors/{id}/schedules`    | GET    | 특정 의사의 스케줄 목록 조회                |

---

## 우선순위

| 단계     | 우선순위  | 설명                                       |
| -------- | --------- | ------------------------------------------ |
| Step 1~2 | P0 (필수) | 테이블/엔티티 생성 — 이후 모든 작업의 기반 |
| Step 3~4 | P0 (필수) | DTO 및 서비스 — API 핵심 로직              |
| Step 5~6 | P0 (필수) | LLM 연동 및 API — 핵심 기능 완성           |
| Step 7   | P1 (권장) | 테스트 및 샘플 데이터                      |
| Step 8   | P1 (권장) | 프론트엔드 화면                            |

---

## 기존 테이블 연동 관계

```
medical_domain ──1:N──→ doctor ──1:N──→ doctor_schedule
                          │
medical_qa.department ←── doctor.department (논리적 매칭)
```

- `doctor.domain_id`로 `medical_domain`과 FK 연관 (진료 분야 분류)
- `doctor.department`와 `medical_qa.department`를 논리적으로 매칭하여 진료과 기반 검색
- LLM 응답에서 추출한 진료과명으로 `doctor` 테이블을 조회하여 의사 목록 제공

---

## 기존 테이블 연동 관계

```
medical_domain ──1:N──→ doctor ──1:N──→ doctor_schedule
                          │
medical_qa.department ←── doctor.department (논리적 매칭)
```

- `doctor.domain_id`로 `medical_domain`과 FK 연관 (진료 분야 분류)
- `doctor.department`와 `medical_qa.department`를 논리적으로 매칭하여 진료과 기반 검색
- LLM 응답에서 추출한 진료과명으로 `doctor` 테이블을 조회하여 의사 목록 제공매칭)

````

- `doctor.domain_id`로 `medical_domain`과 FK 연관 (진료 분야 분류)
- `doctor.department`와 `medical_qa.department`를 논리적으로 매칭하여 진료과 기반 검색
- LLM 응답에서 추출한 진료과명으로 `doctor` 테이블을 조회하여 의사 목록 제공
```매칭)

````

- `doctor.domain_id`로 `medical_domain`과 FK 연관 (진료 분야 분류)
- `doctor.department`와 `medical_qa.department`를 논리적으로 매칭하여 진료과 기반 검색
- LLM 응답에서 추출한 진료과명으로 `doctor` 테이블을 조회하여 의사 목록 제공

```

- `doctor.domain_id`로 `medical_domain`과 FK 연관 (진료 분야 분류)
- `doctor.department`와 `medical_qa.department`를 논리적으로 매칭하여 진료과 기반 검색
- LLM 응답에서 추출한 진료과명으로 `doctor` 테이블을 조회하여 의사 목록 제공
```

```

- `doctor.domain_id`로 `medical_domain`과 FK 연관 (진료 분야 분류)
- `doctor.department`와 `medical_qa.department`를 논리적으로 매칭하여 진료과 기반 검색
- LLM 응답에서 추출한 진료과명으로 `doctor` 테이블을 조회하여 의사 목록 제공
