# HMS 프로젝트 병합 가이드

> spring_llm_sample_mng를 [proejct-team-alpha/hms](https://github.com/proejct-team-alpha/hms) dev 브랜치 구조에 맞춰 병합할 때 필요한 수정사항 정리

**참고**: Python LLM 서버(python-llm/)는 별도 모듈로 유지하며, Spring Boot 쪽만 HMS 패키지 구조에 맞게 재구성한다.

---

## 1. 프로젝트 비교 요약

| 구분 | spring_llm_sample_mng | HMS (dev) |
|------|------------------------|-----------|
| **패키지** | `com.sample.llm` | `com.smartclinic.hms` |
| **엔트리** | `SpringLlmSampleMngApplication` | `HmsApplication` |
| **레이어 구조** | config, controller, dto, entity, repository, service, exception | config, common, domain, admin, staff, doctor, nurse, reservation, **llm** |
| **Entity 위치** | `entity/` | `domain/` |
| **LLM 백엔드** | Python FastAPI (Ollama) + WebClient | Claude API (RestClient) |
| **DB** | MySQL only | H2 (dev) / MySQL (prod) |
| **Security** | 없음 | Spring Security (4 ROLE) |
| **View** | Vanilla SPA (static/) | Mustache SSR (templates/) |
| **설정** | application.yml | application.properties + application-dev.properties |

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

| 현재 (spring_llm_sample_mng) | 병합 후 (HMS) |
|------------------------------|---------------|
| `com.sample.llm.config.*` | `com.smartclinic.hms.config.*` |
| `com.sample.llm.controller.*` | `com.smartclinic.hms.llm.controller.*` |
| `com.sample.llm.dto.*` | `com.smartclinic.hms.llm.dto.*` |
| `com.sample.llm.entity.*` | `com.smartclinic.hms.domain.*` |
| `com.sample.llm.repository.*` | `com.smartclinic.hms.domain.*` (또는 llm.repository) |
| `com.sample.llm.service.*` | `com.smartclinic.hms.llm.service.*` |
| `com.sample.llm.exception.*` | `com.smartclinic.hms.common.exception.*` |

---

## 3. Entity / 도메인 정합성

### 3.1 중복·유사 Entity

| spring_llm_sample_mng | HMS domain | 조치 |
|-----------------------|------------|------|
| `ChatHistory` (chatbot_history) | `ChatbotHistory` | **HMS 것 사용** — 구조 동일, `ChatbotHistory.create()` 팩토리 활용 |
| `MedicalRule` (medical_rule) | `HospitalRule` (hospital_rule) | **테이블·스키마 정합 필요** — medical_rule vs hospital_rule, category 타입(String vs enum) |
| `Staff` | `Staff` | **HMS 것 사용** — StaffRole enum 등 HMS 스키마 준수 |
| `Doctor` | `Doctor` | **HMS 것 사용** — Department 연관 등 HMS 스키마 준수 |

### 3.2 spring_llm_sample_mng 전용 Entity (domain에 추가)

| Entity | 테이블 | 비고 |
|--------|--------|------|
| `MedicalHistory` | medical_history | 의료 상담 이력 |
| `MedicalContent` | medical_content | 의학 콘텐츠 |
| `MedicalQa` | medical_qa | 의학 Q&A |
| `MedicalDomain` | medical_domain | 진료 도메인 (의학 지식용) |
| `DoctorSchedule` | doctor_schedules | HMS Doctor와 연관 여부 확인 후 통합 검토 |

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
implementation 'org.springframework.boot:spring-boot-starter-webflux'   // WebClient
runtimeOnly 'com.mysql:mysql-connector-j'                               // prod 프로필용
developmentOnly 'me.paulschwarz:springboot3-dotenv:5.1.0'              // .env 로드 (선택)
```

### 4.2 HMS 기존 vs spring_llm_sample_mng

| 항목 | HMS | spring_llm_sample_mng |
|------|-----|------------------------|
| webflux | ❌ | ✅ |
| mysql-connector | ❌ (prod에서 추가 예정) | ✅ |
| mustache | ✅ | ❌ |
| security | ✅ | ❌ |
| webmvc-test | ✅ | ✅ |

---

## 5. 설정 파일

### 5.1 application.properties / application-*.properties

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

| 현재 (spring_llm) | HMS 스타일 제안 | 비고 |
|-------------------|-----------------|------|
| `POST /api/medical/query` | `POST /llm/medical/query` 또는 `POST /api/medical/query` | 프론트 연동 경로 유지 여부 결정 |
| `POST /api/medical/medical-query` | 동일 또는 `/llm/medical/query`로 통합 | |
| `GET /api/medical/stream/...` | `GET /llm/medical/stream/...` | SSE 스트리밍 |
| `POST /api/chat/query` | `POST /llm/chatbot/ask` (HMS 기존) | ChatbotController와 통합 |
| `GET /api/chat/history/{staffId}` | `GET /llm/chatbot/history/{staffId}` | |

### 6.2 HMS 기존 llm vs spring_llm_sample_mng

| HMS llm (Claude) | spring_llm (Ollama/Python) |
|------------------|----------------------------|
| `POST /llm/symptom/analyze` | `POST /api/medical/query` (의료 상담) |
| `POST /llm/chatbot/ask` | `POST /api/chat/query` (병원 규칙 Q&A) |

**통합 전략**  
- LlmService를 Python WebClient 호출로 교체하거나,  
- MedicalService/ChatService를 LlmService 내부에서 호출하는 방식으로 래핑

---

## 7. 리소스 (정적 파일, 템플릿)

### 7.1 spring_llm_sample_mng static

```
src/main/resources/static/
├── index.html
├── medical.html
├── chat.html
└── (관련 JS/CSS)
```

**옵션**  
1. `static/`에 그대로 두고 `/` 등에서 서빙 (현재와 동일)  
2. Mustache 템플릿으로 변환 후 `templates/doctor/`, `templates/nurse/` 등에 배치  
3. doctor/nurse 화면에 iframe 또는 링크로 medical, chat 페이지 연결

HMS는 Mustache SSR이므로, 장기적으로는 2번을 권장. 단기에는 1번으로 병합 후 점진 이전 가능.

---

## 8. Python LLM 서버 (python-llm/)

- **위치**: 프로젝트 루트 `python-llm/` 유지
- **변경**: 없음 (Spring만 HMS 구조로 맞춤)
- **실행**: `docker-compose` 또는 `python-llm/run.bat` 등 기존 방식 유지
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

### 9.5 API·컨트롤러

- [ ] 경로 `/api/*` vs `/llm/*` 정책 확정
- [ ] ChatbotController와 ChatController 통합 또는 공존 방식 결정
- [ ] LlmService와 MedicalService/ChatService 역할 분리

### 9.6 프론트엔드

- [ ] static 파일 경로 유지 또는 Mustache 이전
- [ ] doctor/nurse 화면에서 medical, chat 페이지 링크 연결

---

## 10. 참고 링크

- [HMS dev 브랜치](https://github.com/proejct-team-alpha/hms/tree/dev)
- [HMS PACKAGE_STRUCTURE.md](https://github.com/proejct-team-alpha/hms/blob/dev/src/main/java/com/smartclinic/hms/PACKAGE_STRUCTURE.md)
- [HMS llm FILES.md](https://github.com/proejct-team-alpha/hms/blob/dev/src/main/java/com/smartclinic/hms/llm/FILES.md)
- [spring_llm_sample_mng README](../README.md)
