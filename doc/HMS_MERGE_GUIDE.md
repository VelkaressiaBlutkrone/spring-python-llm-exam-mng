# HMS 프로젝트 병합 가이드

> spring_llm_sample_mng를 [proejct-team-alpha/hms](https://github.com/proejct-team-alpha/hms) dev 브랜치 구조에 맞춰 병합할 때 필요한 수정사항 정리
>
> 최종 업데이트: 2026-03-19

**참고**: Python LLM 서버(python-llm/)는 별도 모듈로 유지하며, Spring Boot 쪽만 HMS 패키지 구조에 맞게 재구성한다.

---

## 1. 프로젝트 비교 요약

| 구분            | spring_llm_sample_mng                                                          | HMS (dev)                                                                 |
| --------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| **패키지**      | `com.sample.llm`                                                               | `com.smartclinic.hms`                                                     |
| **엔트리**      | `SpringLlmSampleMngApplication`                                                | `HmsApplication`                                                          |
| **레이어 구조** | config, controller, dto, entity, repository, service, exception                | config, common, domain, admin, staff, doctor, nurse, reservation, **llm** |
| **Entity 위치** | `entity/`                                                                      | `domain/`                                                                 |
| **LLM 백엔드**  | Python FastAPI (Ollama/vLLM) + WebClient                                       | Claude API (RestClient)                                                   |
| **DB**          | MySQL only                                                                     | H2 (dev) / MySQL (prod)                                                   |
| **Security**    | 없음                                                                           | Spring Security (4 ROLE)                                                  |
| **View**        | Vanilla SPA (static/, 다크 테마)                                               | Mustache SSR (templates/)                                                 |
| **설정**        | application.yml                                                                | application.properties + application-dev.properties                       |
| **스트리밍**    | SSE (WebFlux Flux) — `/api/chat/query/stream`, `/api/medical/stream`           | 없음                                                                      |
| **예약 시스템** | `Reservation` Entity + REST API (`/api/reservation`)                           | `Reservation` Entity + SSR Controller                                     |

---

## 2. 패키지 구조 매핑

### 2.1 목표 구조 (HMS 기준)

```
com.smartclinic.hms
├── config/                    # Security, MVC, Claude API + WebClient
├── common/
│   ├── interceptor/
│   ├── exception/             # GlobalExceptionHandler, LlmTimeoutException 등
│   ├── util/
│   └── service/
├── domain/                    # JPA Entity + Repository
├── admin/
├── staff/
├── doctor/
├── nurse/
├── reservation/
├── llm/                       # ★ 병합 대상
│   ├── dto/
│   ├── controller/            # MedicalController, ChatController
│   ├── service/                # MedicalService, ChatService, DoctorService
│   └── repository/             # (domain에 두거나 llm 하위)
└── HmsApplication.java
```

### 2.2 spring_llm_sample_mng → HMS 매핑

| 현재 (spring_llm_sample_mng)              | 병합 후 (HMS)                                          | 비고                           |
| ----------------------------------------- | ------------------------------------------------------ | ------------------------------ |
| `com.sample.llm.config.*`                 | `com.smartclinic.hms.config.*`                         | WebClientConfig 등             |
| `com.sample.llm.controller.Chat*`         | `com.smartclinic.hms.llm.controller.*`                 | 병원규칙 Q&A                   |
| `com.sample.llm.controller.Medical*`      | `com.smartclinic.hms.llm.controller.*`                 | 의료 상담                      |
| `com.sample.llm.controller.Reservation*`  | `com.smartclinic.hms.reservation.controller.*`         | HMS 기존 reservation과 통합    |
| `com.sample.llm.dto.*`                    | `com.smartclinic.hms.llm.dto.*`                        | LLM 관련 DTO                   |
| `com.sample.llm.dto.Reservation*`         | `com.smartclinic.hms.reservation.dto.*`                | HMS 기존 DTO와 통합            |
| `com.sample.llm.entity.*`                 | `com.smartclinic.hms.domain.*`                         | JPA Entity                     |
| `com.sample.llm.entity.Reservation`       | `com.smartclinic.hms.domain.Reservation`               | HMS 기존 Entity와 스키마 비교  |
| `com.sample.llm.repository.*`             | `com.smartclinic.hms.domain.*` (또는 llm.repository)   | LLM 관련 Repository            |
| `com.sample.llm.repository.Reservation*`  | `com.smartclinic.hms.reservation.repository.*`         | HMS 기존 Repository와 통합     |
| `com.sample.llm.service.*`                | `com.smartclinic.hms.llm.service.*`                    | LLM 관련 Service               |
| `com.sample.llm.service.Reservation*`     | `com.smartclinic.hms.reservation.service.*`            | HMS 기존 Service와 통합        |
| `com.sample.llm.exception.*`              | `com.smartclinic.hms.common.exception.*`               | 공통 예외                      |

---

## 3. Entity / 도메인 정합성

### 3.1 중복·유사 Entity

| spring_llm_sample_mng           | HMS domain                     | 조치                                                                                       |
| ------------------------------- | ------------------------------ | ------------------------------------------------------------------------------------------ |
| `ChatHistory` (chatbot_history) | `ChatbotHistory`               | **HMS 것 사용** — 구조 동일, `ChatbotHistory.create()` 팩토리 활용                         |
| `MedicalRule` (medical_rule)    | `HospitalRule` (hospital_rule) | **테이블·스키마 정합 필요** — medical_rule vs hospital_rule, category 타입(String vs enum) |
| `Staff`                         | `Staff`                        | **HMS 것 사용** — StaffRole enum 등 HMS 스키마 준수                                        |
| `Doctor`                        | `Doctor`                       | **HMS 것 사용** — Department 연관 등 HMS 스키마 준수                                       |

### 3.2 spring_llm_sample_mng 전용 Entity (domain에 추가)

| Entity           | 테이블           | 비고                                     |
| ---------------- | ---------------- | ---------------------------------------- |
| `MedicalHistory` | medical_history  | 의료 상담 이력                           |
| `MedicalContent` | medical_content  | 의학 콘텐츠                              |
| `MedicalQa`      | medical_qa       | 의학 Q&A                                 |
| `MedicalDomain`  | medical_domain   | 진료 도메인 (의학 지식용)                |
| `DoctorSchedule` | doctor_schedules | HMS Doctor와 연관 여부 확인 후 통합 검토 |
| `Reservation`    | reservation_tb   | HMS 기존 Reservation과 스키마 비교 필요  |

### 3.4 Reservation 통합

- **spring_llm**: `reservation_tb` — doctor_id(FK), staff_id(FK nullable), reservation_date, start_time, end_time, status(String)
- **HMS**: `reservation` — 기존 예약 스키마 확인 필요

**조치**

1. HMS `Reservation` Entity 스키마를 기준으로 통합
2. spring_llm의 `start_time`, `end_time` 시간 슬롯 기반 예약 로직을 HMS에 반영
3. `DoctorSchedule` 기반 가용 슬롯 조회 로직(`getAvailableSlots`) 이식

### 3.3 MedicalRule vs HospitalRule

- **spring_llm**: `medical_rule` — category(String), title, content, target, start_date, end_date
- **HMS**: `hospital_rule` — category(enum HospitalRuleCategory), title, content, is_active, created_at, updated_at

**옵션**

1. **HospitalRule 확장**: target, start_date, end_date 컬럼 추가 후 medical_rules.json 적재 로직 수정
2. **medical_rule 유지**: 별도 테이블로 두고 Python RAG는 medical_rule 사용, HMS 관리 화면은 hospital_rule 사용 (이중화)
3. **마이그레이션**: medical_rule → hospital_rule 스키마 통합 + HospitalRuleCategory 매핑

---

## 4. build.gradle 의존성

### 4.1 HMS에 추가할 의존성 (LLM 연동용)

```groovy
// spring_llm_sample_mng에서 사용 중
implementation 'org.springframework.boot:spring-boot-starter-webflux'   // WebClient + Flux (SSE 스트리밍)
runtimeOnly 'com.mysql:mysql-connector-j'                               // prod 프로필용
developmentOnly 'me.paulschwarz:springboot3-dotenv:5.1.0'              // .env 로드 (선택)
```

> **주의**: `spring-boot-starter-webflux`는 WebClient뿐 아니라 SSE 스트리밍(`Flux<String>`) 응답에도 필수적이다.

### 4.2 HMS 기존 vs spring_llm_sample_mng

| 항목            | HMS                     | spring_llm_sample_mng |
| --------------- | ----------------------- | --------------------- |
| webflux         | ❌                      | ✅                    |
| mysql-connector | ❌ (prod에서 추가 예정) | ✅                    |
| mustache        | ✅                      | ❌                    |
| security        | ✅                      | ❌                    |
| webmvc-test     | ✅                      | ✅                    |

---

## 5. 설정 파일

### 5.1 application.properties / application-\*.properties

HMS는 `application.properties` + `application-dev.properties` 사용.
LLM 관련 설정은 `application-dev.properties` 또는 `application-prod.properties`에 추가:

```properties
# application-dev.properties (또는 공통)
llm.service.url=${LLM_SERVICE_URL:http://localhost:8000}
llm.service.timeout.connect=5000
llm.service.timeout.read=120000

# MySQL (prod 프로필용, HMS에 이미 있을 수 있음)
spring.datasource.url=jdbc:mysql://localhost:3307/llm_db
spring.datasource.username=${MYSQL_USER:llm_admin}
spring.datasource.password=${MYSQL_PASSWORD:llm_password}
```

### 5.2 SecurityConfig

- `/api/medical/**`, `/api/chat/**` 등 LLM API 경로에 대한 접근 제어 정책 반영
- HMS: 비회원 증상 분석(`/llm/symptom/analyze`) 허용, 챗봇(`/llm/chatbot/ask`)은 인증 필요
- spring_llm: `X-Staff-Id` 헤더로 직원 식별 → HMS Security와 연동 시 `Staff` principal 사용

---

## 6. API 경로 및 컨트롤러

### 6.1 경로 정렬 옵션

| 현재 (spring_llm)                    | HMS 스타일 제안                                          | 비고                            |
| ------------------------------------ | -------------------------------------------------------- | ------------------------------- |
| `POST /api/medical/query`            | `POST /llm/medical/query` 또는 `POST /api/medical/query` | 프론트 연동 경로 유지 여부 결정 |
| `POST /api/medical/medical-query`    | 동일 또는 `/llm/medical/query`로 통합                    |                                 |
| `GET /api/medical/stream/...`        | `GET /llm/medical/stream/...`                            | SSE 스트리밍 (의학)             |
| `POST /api/chat/query`              | `POST /llm/chatbot/ask` (HMS 기존)                       | ChatbotController와 통합        |
| `POST /api/chat/query/stream`       | `POST /llm/chatbot/ask/stream`                           | SSE 스트리밍 (병원규칙)         |
| `GET /api/chat/history/{staffId}`    | `GET /llm/chatbot/history/{staffId}`                     |                                 |
| `POST /api/reservation`             | HMS 기존 reservation 경로와 통합                         | 예약 생성                       |
| `GET /api/reservation/slots/{docId}` | HMS 기존 reservation 경로와 통합                         | 가용 슬롯 조회                  |

### 6.2 HMS 기존 llm vs spring_llm_sample_mng

| HMS llm (Claude)            | spring_llm (Ollama/Python)             |
| --------------------------- | -------------------------------------- |
| `POST /llm/symptom/analyze` | `POST /api/medical/query` (의료 상담)  |
| `POST /llm/chatbot/ask`     | `POST /api/chat/query` (병원 규칙 Q&A) |

**통합 전략**

- LlmService를 Python WebClient 호출로 교체하거나,
- MedicalService/ChatService를 LlmService 내부에서 호출하는 방식으로 래핑

---

## 7. 리소스 (정적 파일, 템플릿)

### 7.1 spring_llm_sample_mng static

```
src/main/resources/static/
├── index.html       ← 메인 허브 (다크 테마, 서버 상태 표시)
├── medical.html     ← 질병 Q&A (다크 테마, SSE 스트리밍)
└── chat.html        ← 병원규칙 Q&A (다크 테마, SSE 스트리밍 + 퀵칩)
```

**현재 상태**: 다크 테마 UI로 리디자인 완료. SSE 스트리밍 우선 + 폴백 렌더링 구현됨.

**옵션**

1. `static/`에 그대로 두고 `/` 등에서 서빙 (현재와 동일)
2. Mustache 템플릿으로 변환 후 `templates/doctor/`, `templates/nurse/` 등에 배치
3. doctor/nurse 화면에 iframe 또는 링크로 medical, chat 페이지 연결

HMS는 Mustache SSR이므로, 장기적으로는 2번을 권장. 단기에는 1번으로 병합 후 점진 이전 가능.

### 7.2 Mustache 변환 시 고려사항

- SSE 스트리밍 JS 로직은 `<script>` 태그로 유지하거나 별도 JS 파일로 분리
- 다크 테마 CSS 변수를 HMS 공통 스타일과 통합 여부 결정
- `chat.html`의 퀵칩 UI, 스트리밍 버블 렌더링 로직 보존 필요

---

## 8. Python LLM 서버 (python-llm/)

- **위치**: 프로젝트 루트 `python-llm/` 유지
- **변경**: 없음 (Spring만 HMS 구조로 맞춤)
- **실행**: `docker-compose` 또는 `python-llm/run.sh` 등 기존 방식 유지
- **연동**: Spring `llm.service.url`로 Python 서버 URL 지정

---

## 9. 체크리스트 (병합 시)

### 9.1 패키지·파일 이동

- [ ] `com.sample.llm` → `com.smartclinic.hms` 패키지 변경
- [ ] `entity/` → `domain/` 이동
- [ ] `controller/` → `llm/controller/` 이동
- [ ] `service/` → `llm/service/` 이동
- [ ] `dto/` → `llm/dto/` 이동
- [ ] `repository/` → `domain/` 또는 `llm/repository/` 이동
- [ ] `exception/` → `common/exception/` 이동
- [ ] `config/WebClientConfig` → `config/` 이동
- [ ] `config/DataLoader` → domain 시드용으로 config 또는 별도 초기화 로직에 통합

### 9.2 의존성

- [ ] `build.gradle`에 `spring-boot-starter-webflux`, `mysql-connector-j` 추가
- [ ] (선택) `springboot3-dotenv` 추가

### 9.3 설정

- [ ] `llm.service.*` 설정 추가
- [ ] `SecurityConfig`에 LLM API 경로 허용/인증 규칙 추가

### 9.4 Entity·테이블

- [ ] `ChatHistory` → `ChatbotHistory` 사용 (import 등 참조 수정)
- [ ] `MedicalRule` vs `HospitalRule` 전략 결정 및 마이그레이션
- [ ] `MedicalHistory`, `MedicalContent`, `MedicalQa`, `MedicalDomain` domain에 추가
- [ ] `Doctor`, `Staff`는 HMS domain 사용
- [ ] `Reservation` — HMS 기존 Entity와 스키마 비교 후 통합 전략 결정
- [ ] `DoctorSchedule` — HMS Doctor 연관 확인 후 통합 or 추가
- [ ] `reservation_tb` DDL을 HMS 마이그레이션에 반영

### 9.5 API·컨트롤러

- [ ] 경로 `/api/*` vs `/llm/*` 정책 확정
- [ ] ChatbotController와 ChatController 통합 또는 공존 방식 결정
- [ ] LlmService와 MedicalService/ChatService 역할 분리
- [ ] SSE 스트리밍 엔드포인트 (`/query/stream`) 이식 여부 결정
- [ ] ReservationApiController → HMS reservation 패키지 통합

### 9.6 프론트엔드

- [ ] static 파일 경로 유지 또는 Mustache 이전
- [ ] doctor/nurse 화면에서 medical, chat 페이지 링크 연결
- [ ] SSE 스트리밍 JS 로직 보존 (스트리밍 버블, 퀵칩 UI)
- [ ] 다크 테마 CSS 변수 통합 여부 결정

### 9.7 Python LLM 서버

- [ ] `python-llm/` 디렉토리 HMS 루트에 복사
- [ ] `/infer/rule/stream` SSE 스트리밍 엔드포인트 정상 동작 확인
- [ ] vLLM/Ollama 백엔드 전환 설정 (`LLM_BACKEND` 환경변수) 문서화
- [ ] `docker-compose.yml`에 python-llm, chromadb 서비스 추가

---

## 10. 참고 링크

- [HMS dev 브랜치](https://github.com/proejct-team-alpha/hms/tree/dev)
- [HMS PACKAGE_STRUCTURE.md](https://github.com/proejct-team-alpha/hms/blob/dev/src/main/java/com/smartclinic/hms/PACKAGE_STRUCTURE.md)
- [HMS llm FILES.md](https://github.com/proejct-team-alpha/hms/blob/dev/src/main/java/com/smartclinic/hms/llm/FILES.md)
- [spring_llm_sample_mng README](../README.md)
- [TASK_HMS_MERGE.md](./TASK_HMS_MERGE.md) — 병합 실행 Task/Step/Workflow
