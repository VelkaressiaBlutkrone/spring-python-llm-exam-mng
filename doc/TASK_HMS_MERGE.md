# HMS 프로젝트 병합 실행 계획서 — Task / Step / Workflow

> 작성일: 2026-03-19
> 기반 문서: `doc/HMS_MERGE_GUIDE.md`
> 총 8개 Task, 3개 Phase

---

## 목차

- [Phase 1 — 기반 준비 (Task 1~3)](#phase-1--기반-준비-task-13)
- [Phase 2 — 핵심 병합 (Task 4~6)](#phase-2--핵심-병합-task-46)
- [Phase 3 — 통합 및 검증 (Task 7~8)](#phase-3--통합-및-검증-task-78)
- [의존 관계 다이어그램](#의존-관계-다이어그램)

---

## Phase 1 — 기반 준비 (Task 1~3)

---

### Task 1: HMS 프로젝트 패키지 구조 확인 및 브랜치 준비

> 난이도: 낮음 | 영향 파일: HMS 프로젝트 전체

**목표**: HMS dev 브랜치의 현재 패키지 구조, Entity 스키마, API 경로를 확인하고 병합 작업 브랜치를 생성한다.

#### Step 1: HMS dev 브랜치 클론 및 구조 확인

- [ ] HMS dev 브랜치 최신 pull
- [ ] `com.smartclinic.hms` 패키지 트리 확인 (config, common, domain, admin, staff, doctor, nurse, reservation, llm)
- [ ] HMS `Reservation` Entity 스키마 확인 (컬럼, 관계, 테이블명)
- [ ] HMS `ChatbotHistory` Entity 스키마 확인
- [ ] HMS `HospitalRule` Entity 스키마 확인 (category 타입, 컬럼 차이)

#### Step 2: 병합 브랜치 생성

- [ ] `feat/llm-merge` 브랜치를 HMS dev 기준으로 생성
- [ ] spring_llm_sample_mng 원본은 별도 워크트리로 참조 가능하도록 유지

#### Step 3: Entity 스키마 비교표 작성

- [ ] `Reservation`: spring_llm(`reservation_tb`) vs HMS(`reservation`) 컬럼 매핑표
- [ ] `ChatHistory` vs `ChatbotHistory` 컬럼 매핑표
- [ ] `MedicalRule` vs `HospitalRule` 컬럼 매핑표 + 통합 전략 결정
- [ ] `Doctor`, `Staff`, `DoctorSchedule` 호환성 확인

**Workflow**:

```
HMS 구조 확인(Step1) → 브랜치 생성(Step2) → 스키마 비교(Step3)
```

---

### Task 2: build.gradle 의존성 및 설정 파일 병합

> 난이도: 낮음 | 영향 파일: `build.gradle`, `application*.properties`
> 선행: Task 1

**목표**: HMS build.gradle에 LLM 연동용 의존성을 추가하고, 설정 파일에 LLM 서비스 접속 정보를 추가한다.

#### Step 1: build.gradle 의존성 추가

- [ ] `spring-boot-starter-webflux` 추가 (WebClient + SSE Flux)
- [ ] `mysql-connector-j` runtimeOnly 확인 (prod 프로필)
- [ ] (선택) `springboot3-dotenv` 추가

#### Step 2: application-dev.properties에 LLM 설정 추가

- [ ] `llm.service.url=${LLM_SERVICE_URL:http://localhost:8000}` 추가
- [ ] `llm.service.timeout.connect=5000` 추가
- [ ] `llm.service.timeout.read=120000` 추가

#### Step 3: WebClientConfig 이식

- [ ] `com.sample.llm.config.WebClientConfig` → `com.smartclinic.hms.config.WebClientConfig` 복사
- [ ] 패키지 선언 및 import 수정
- [ ] Bean 이름 충돌 여부 확인

#### Step 4: 검증

- [ ] HMS 프로젝트 빌드 성공 (`./gradlew build`)
- [ ] WebClient Bean 정상 로드 확인 (애플리케이션 기동)

**Workflow**:

```
의존성(Step1) → 설정(Step2) → WebClient(Step3) → 빌드 검증(Step4)
```

---

### Task 3: 공통 예외 및 유틸리티 이식

> 난이도: 낮음 | 영향 파일: `common/exception/`
> 선행: Task 1

**목표**: spring_llm_sample_mng의 예외 클래스와 공통 유틸리티를 HMS common 패키지로 이식한다.

#### Step 1: 예외 클래스 이식

- [ ] `LlmServiceUnavailableException` → `com.smartclinic.hms.common.exception.` 이식
- [ ] `LlmTimeoutException` → `com.smartclinic.hms.common.exception.` 이식
- [ ] 패키지 선언 수정

#### Step 2: GlobalExceptionHandler 통합

- [ ] HMS 기존 `GlobalExceptionHandler` 확인
- [ ] LLM 관련 예외 핸들러 추가 (503 Service Unavailable, 504 Gateway Timeout)
- [ ] 기존 핸들러와 충돌 없는지 확인

#### Step 3: 검증

- [ ] 빌드 성공 확인
- [ ] 예외 클래스 import 정상 확인

**Workflow**:

```
예외 이식(Step1) → 핸들러 통합(Step2) → 검증(Step3)
```

---

## Phase 2 — 핵심 병합 (Task 4~6)

---

### Task 4: Entity 및 Repository 이식

> 난이도: 높음 | 영향 파일: `domain/`, `llm/repository/`
> 선행: Task 1 (스키마 비교 완료), Task 3

**목표**: spring_llm_sample_mng의 Entity와 Repository를 HMS domain 패키지에 이식하고, 중복 Entity는 HMS 것을 사용하도록 통합한다.

#### Step 1: HMS 기존 Entity 사용 (중복 제거)

- [ ] `ChatHistory` → HMS `ChatbotHistory` 사용으로 전환
  - 참조하는 Service/Controller에서 import 변경
  - `ChatbotHistory.create()` 팩토리 메서드 활용
- [ ] `Doctor` → HMS `Doctor` 사용
- [ ] `Staff` → HMS `Staff` 사용 (StaffRole enum 등 HMS 스키마 준수)

#### Step 2: LLM 전용 Entity 추가

- [ ] `MedicalHistory` → `com.smartclinic.hms.domain.MedicalHistory` 추가
- [ ] `MedicalContent` → `com.smartclinic.hms.domain.MedicalContent` 추가
- [ ] `MedicalQa` → `com.smartclinic.hms.domain.MedicalQa` 추가
- [ ] `MedicalDomain` → `com.smartclinic.hms.domain.MedicalDomain` 추가
- [ ] `MedicalRule` → HMS `HospitalRule`과 통합 전략 적용 (Task 1에서 결정)
- [ ] `DoctorSchedule` → HMS Doctor 연관 확인 후 domain에 추가
- [ ] 모든 Entity 패키지 선언 `com.smartclinic.hms.domain` 으로 수정

#### Step 3: Reservation 통합

- [ ] HMS 기존 `Reservation` Entity 스키마 기준으로 통합
- [ ] spring_llm의 `start_time`, `end_time` 필드가 없으면 ALTER TABLE 또는 Entity 확장
- [ ] FK 관계 (`Doctor`, `Staff`) HMS domain 기준으로 재설정
- [ ] `reservation_tb` → HMS 테이블명 기준으로 통일

#### Step 4: Repository 이식

- [ ] `MedicalHistoryRepository` → `com.smartclinic.hms.domain.` 또는 `llm.repository.`
- [ ] `MedicalContentRepository` → 동일
- [ ] `MedicalQaRepository` → 동일
- [ ] `MedicalDomainRepository` → 동일
- [ ] `DoctorScheduleRepository` → 동일
- [ ] `ChatHistoryRepository` → HMS `ChatbotHistoryRepository` 사용
- [ ] `ReservationRepository` → HMS 기존 Repository에 메서드 추가
  - `countByDoctorIdAndReservationDateAndStartTime()` 추가

#### Step 5: 검증

- [ ] 빌드 성공
- [ ] JPA Entity 스캔 정상 (중복 테이블 매핑 없음)
- [ ] DDL auto 모드에서 테이블 생성 확인

**Workflow**:

```
중복 제거(Step1) → LLM Entity 추가(Step2) → Reservation 통합(Step3) → Repository(Step4) → 검증(Step5)
```

---

### Task 5: Service 이식

> 난이도: 높음 | 영향 파일: `llm/service/`, `reservation/service/`
> 선행: Task 4

**목표**: LLM 관련 Service를 HMS llm 패키지로 이식하고, Reservation Service는 HMS 기존 서비스와 통합한다.

#### Step 1: LLM Service 이식

- [ ] `ChatService` → `com.smartclinic.hms.llm.service.ChatService`
  - WebClient 주입 유지
  - `ChatHistory` → `ChatbotHistory` 참조 수정
  - `StaffRepository` → HMS Staff 관련 Repository 참조
  - SSE 스트리밍 메서드 (`callRuleLlmApiStream`) 포함
- [ ] `MedicalService` → `com.smartclinic.hms.llm.service.MedicalService`
  - `MedicalHistory` 저장 로직 유지
  - 스트리밍 SSE 메서드 포함
- [ ] `DoctorService` → `com.smartclinic.hms.llm.service.DoctorService`
  - HMS Doctor/DoctorSchedule 연관 확인
- [ ] `LlmResponseParser` → `com.smartclinic.hms.llm.service.LlmResponseParser`

#### Step 2: Reservation Service 통합

- [ ] HMS 기존 `ReservationService` 확인
- [ ] spring_llm의 `createReservation()` 로직 통합
  - 중복 예약 검증 (`countByDoctorIdAndReservationDateAndStartTime`)
  - `DoctorSchedule` 기반 가용 슬롯 조회 (`getAvailableSlots`)
- [ ] 시간 슬롯 계산 로직 (`toEnglishDayCode`, 30분 단위 분할) 이식

#### Step 3: HMS LlmService와 역할 분리

- [ ] HMS 기존 `LlmService` (Claude API) 확인
- [ ] spring_llm의 `ChatService`/`MedicalService` (Python WebClient)와 공존 방식 결정
  - 옵션 A: LlmService 내부에서 Python 호출로 래핑
  - 옵션 B: 별도 Service로 유지하고 Controller에서 선택 호출
- [ ] 공존 시 Bean 이름 충돌 해결

#### Step 4: 검증

- [ ] 빌드 성공
- [ ] Service Bean 정상 생성 (순환 참조 없음)
- [ ] 의존성 주입 정상 확인

**Workflow**:

```
LLM Service(Step1) → Reservation 통합(Step2) → 역할 분리(Step3) → 검증(Step4)
```

---

### Task 6: Controller 및 DTO 이식

> 난이도: 중간 | 영향 파일: `llm/controller/`, `llm/dto/`, `reservation/controller/`
> 선행: Task 5

**목표**: Controller와 DTO를 HMS 패키지로 이식하고, API 경로를 HMS 정책에 맞게 조정한다.

#### Step 1: DTO 이식

- [ ] `LlmRequest`, `LlmResponse` → `com.smartclinic.hms.llm.dto.`
- [ ] `MedicalLlmResponse`, `MedicalHistoryResponse` → `com.smartclinic.hms.llm.dto.`
- [ ] `ChatHistoryResponse` → HMS `ChatbotHistory` 기반으로 수정
- [ ] `DoctorDto`, `DoctorScheduleDto`, `DoctorWithScheduleDto` → `com.smartclinic.hms.llm.dto.`
- [ ] `ErrorResponse` → HMS 공통 에러 응답과 통합
- [ ] `ReservationRequest`, `ReservationResponse` → HMS 기존 DTO와 통합

#### Step 2: LLM Controller 이식

- [ ] `ChatController` → `com.smartclinic.hms.llm.controller.ChatController`
  - `@RequestMapping` 경로 조정: `/api/chat` → `/llm/chatbot` (HMS 정책 확정 후)
  - SSE 스트리밍 엔드포인트 (`/query/stream`) 포함
  - `X-Staff-Id` 헤더 → HMS Security principal 전환
- [ ] `MedicalController` → `com.smartclinic.hms.llm.controller.MedicalController`
  - `@RequestMapping` 경로 조정
  - SSE 스트리밍 엔드포인트 포함

#### Step 3: Reservation Controller 통합

- [ ] HMS 기존 `ReservationController` 확인
- [ ] spring_llm의 `ReservationApiController` 엔드포인트 통합
  - `POST /api/reservation` → HMS 경로 기준
  - `GET /api/reservation/slots/{doctorId}` → HMS 경로 기준
- [ ] HMS Mustache SSR Controller와 REST API Controller 분리 유지

#### Step 4: SecurityConfig 업데이트

- [ ] LLM API 경로 접근 제어 추가
  - 비회원 허용: 증상 분석 (`/llm/medical/**`)
  - 인증 필요: 챗봇 (`/llm/chatbot/**`)
  - 예약: 직원 이상 (`/api/reservation/**`)
- [ ] CORS 설정에 LLM 프론트엔드 경로 추가

#### Step 5: 검증

- [ ] 빌드 성공
- [ ] 컨트롤러 Bean 매핑 충돌 없음 확인
- [ ] API 경로 중복 없음 확인 (`/llm/*` vs 기존 경로)

**Workflow**:

```
DTO(Step1) → LLM Controller(Step2) → Reservation 통합(Step3) → Security(Step4) → 검증(Step5)
```

---

## Phase 3 — 통합 및 검증 (Task 7~8)

---

### Task 7: 프론트엔드 및 Python LLM 서버 이식

> 난이도: 중간 | 영향 파일: `static/` 또는 `templates/`, `python-llm/`, `docker-compose.yml`
> 선행: Task 6

**목표**: 프론트엔드 파일과 Python LLM 서버를 HMS 프로젝트에 이식하고, Docker 환경을 구성한다.

#### Step 1: 프론트엔드 이식 전략 결정 및 실행

- [ ] **단기**: `static/` 폴더 그대로 복사 (index.html, medical.html, chat.html)
  - API 경로가 변경된 경우 fetch URL 수정
  - SSE 스트리밍 URL 수정 (`STREAM_URL`, `FALLBACK_URL`)
- [ ] **장기 (선택)**: Mustache 템플릿 변환
  - `templates/llm/medical.mustache` 생성
  - `templates/llm/chat.mustache` 생성
  - SSR Controller 추가

#### Step 2: Python LLM 서버 이식

- [ ] `python-llm/` 디렉토리를 HMS 프로젝트 루트에 복사
- [ ] `.env.example` 업데이트 (HMS 환경에 맞게)
- [ ] `prompts/`, `sql/`, `tests/` 포함 확인
- [ ] `/infer/rule/stream` SSE 스트리밍 엔드포인트 포함 확인

#### Step 3: docker-compose.yml 업데이트

- [ ] `chromadb` 서비스 추가 (포트 8100)
- [ ] `python-llm` 서비스 추가 (포트 8000)
  - `LLM_BACKEND`, `VLLM_BASE_URL`, `OLLAMA_BASE_URL` 환경변수
  - depends_on: mysql, chromadb
- [ ] spring-app 서비스에 `LLM_SERVICE_URL` 환경변수 추가
- [ ] 의학 데이터 볼륨 마운트 설정 (`llm_data/`)

#### Step 4: 검증

- [ ] Docker Compose 전체 스택 기동 (`docker-compose up -d`)
- [ ] python-llm 헬스체크 통과 (`/health`)
- [ ] 프론트엔드 페이지 정상 렌더링

**Workflow**:

```
프론트엔드(Step1) → Python 서버(Step2) → Docker(Step3) → 검증(Step4)
```

---

### Task 8: 통합 테스트 및 최종 검증

> 난이도: 중간 | 영향 파일: 전체
> 선행: Task 7

**목표**: 병합된 HMS 프로젝트에서 모든 LLM 기능이 정상 동작하는지 End-to-End 검증한다.

#### Step 1: 기본 기동 테스트

- [ ] HMS 프로젝트 단독 빌드 (`./gradlew build`)
- [ ] 애플리케이션 기동 → 에러 없이 Started 로그 확인
- [ ] WebClient Bean, JPA Entity 스캔 정상 확인

#### Step 2: LLM API 기능 테스트

- [ ] `POST /llm/medical/query` — 의료 상담 정상 응답
- [ ] `GET /llm/medical/stream/{sessionId}` — SSE 스트리밍 정상 수신
- [ ] `POST /llm/chatbot/ask` — 병원규칙 Q&A 정상 응답
- [ ] `POST /llm/chatbot/ask/stream` — SSE 스트리밍 정상 수신
- [ ] `GET /llm/chatbot/history/{staffId}` — 히스토리 조회

#### Step 3: Reservation 기능 테스트

- [ ] 예약 생성 → 정상 응답
- [ ] 가용 슬롯 조회 → DoctorSchedule 기반 슬롯 반환
- [ ] 중복 예약 → 에러 응답 (IllegalStateException)

#### Step 4: Security 통합 테스트

- [ ] 비인증 상태에서 의료 상담 API → 접근 가능
- [ ] 비인증 상태에서 챗봇 API → 401 Unauthorized
- [ ] 직원 로그인 후 챗봇 API → 정상 응답
- [ ] `X-Staff-Id` 헤더 → Security principal 매핑 확인

#### Step 5: 프론트엔드 E2E 테스트

- [ ] index.html — 서버 상태 표시 (green dot)
- [ ] medical.html — 증상 입력 → SSE 스트리밍 응답 렌더링
- [ ] chat.html — 퀵칩 클릭 → SSE 스트리밍 → 폴백 정상 동작
- [ ] 다크 테마 UI 정상 렌더링

#### Step 6: 기존 HMS 기능 회귀 테스트

- [ ] HMS 기존 로그인/로그아웃 정상 동작
- [ ] HMS 기존 admin/staff/doctor/nurse 페이지 정상 동작
- [ ] HMS 기존 예약 기능 정상 동작 (spring_llm 통합 후에도)

**Workflow**:

```
기동(Step1) → LLM API(Step2) → Reservation(Step3) → Security(Step4) → 프론트엔드(Step5) → 회귀(Step6)
```

---

## 의존 관계 다이어그램

```
Phase 1 (기반 준비)
  Task 1 (HMS 구조 확인) ──┬→ Task 2 (의존성·설정)
                           └→ Task 3 (예외·유틸)

Phase 2 (핵심 병합)
  Task 2 ─┐
  Task 3 ─┴→ Task 4 (Entity·Repository) → Task 5 (Service) → Task 6 (Controller·DTO)

Phase 3 (통합 검증)
  Task 6 → Task 7 (프론트·Python·Docker) → Task 8 (통합 테스트)
```

### 병렬 실행 가능 그룹

| 그룹      | Task           | 비고                     |
| --------- | -------------- | ------------------------ |
| Phase 1-A | Task 2, Task 3 | Task 1 완료 후 병렬 가능 |
| Phase 2   | Task 4 → 5 → 6 | 순차 (레이어 의존)       |
| Phase 3   | Task 7 → 8     | 순차 (이식 후 검증)      |

---

## 롤백 전략

- **브랜치 기반**: `feat/llm-merge` 브랜치에서 작업 → 문제 시 브랜치 삭제로 원복
- **Python LLM**: 별도 디렉토리이므로 삭제만으로 원복 가능
- **LLM 백엔드 전환**: `LLM_BACKEND` 환경변수로 Ollama/vLLM 즉시 전환

---

## 주의사항

- **패키지명 일괄 변경**: `com.sample.llm` → `com.smartclinic.hms` 변경 시 IDE 리팩토링 기능 활용 권장
- **Entity 중복**: 같은 테이블에 두 Entity가 매핑되면 JPA 오류 발생 — 반드시 중복 제거 선행
- **WebFlux 혼용**: Spring MVC + WebFlux 공존 시 `spring.main.web-application-type` 설정 확인
- **Security 경로**: LLM API 경로를 SecurityConfig에 누락하면 403 발생
- **Docker 네트워크**: python-llm 컨테이너에서 vLLM 서버(`192.168.0.22:8000`) 접근 가능 여부 확인
- **데이터 마이그레이션**: `medical_rule` → `hospital_rule` 전환 시 기존 데이터 유실 주의
