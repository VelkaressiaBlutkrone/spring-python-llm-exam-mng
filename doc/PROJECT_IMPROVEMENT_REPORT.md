# 전체 프로젝트 개선 리포트

> 분석일: 2026-03-20
> 분석 대상: Spring Boot + Python FastAPI + MySQL + ChromaDB 의료 상담 LLM 시스템
> 분석 Agent Team: Spring Architect, Python Architect, Security Reviewer, Infra Architect, Frontend Architect

---

## 목차

1. [프로젝트 현황 요약](#1-프로젝트-현황-요약)
2. [Critical 이슈 (즉시 수정)](#2-critical-이슈-즉시-수정)
3. [High 이슈 (1주 내 수정)](#3-high-이슈-1주-내-수정)
4. [Medium 이슈 (1개월 내 수정)](#4-medium-이슈-1개월-내-수정)
5. [Low 이슈 (백로그)](#5-low-이슈-백로그)
6. [통합 개선 로드맵](#6-통합-개선-로드맵)
7. [Agent Team 분석 요약](#7-agent-team-분석-요약)

---

## 1. 프로젝트 현황 요약

### 아키텍처 구조

```
[Client (HTML/JS)] → [Spring Boot 8081] → [Python FastAPI 8000] → [Ollama/vLLM]
                            ↕                       ↕
                      [MySQL 3306]            [ChromaDB 8000]
```

### 전체 이슈 현황

| 심각도   | 건수 | 주요 영역                                                                            |
| -------- | ---- | ------------------------------------------------------------------------------------ |
| CRITICAL | 8    | 보안(인증 부재, 비밀번호 하드코딩), Spring(Reactive+트랜잭션, N+1 쿼리)              |
| HIGH     | 14   | 보안(IDOR, Prompt Injection), Python(백엔드 추상화, 에러 처리), 인프라(DB 포트 노출) |
| MEDIUM   | 19   | 코드 품질, RAG 파이프라인, 인프라, 프론트엔드                                        |
| LOW      | 12   | 컨벤션 위반, 테스트 커버리지, 접근성                                                 |

### 현재 강점

- **하이브리드 검색**: 벡터(ChromaDB) + FULLTEXT(MySQL) 조합으로 검색 커버리지 우수
- **SSE 스트리밍**: 실시간 토큰 전송 + non-streaming 폴백 패턴 잘 설계
- **한국어 도메인 특화**: 오타 교정, CJK 응답 후처리, 의료 용어 전처리
- **WebClient 에러 처리**: 커스텀 예외 + GlobalExceptionHandler 매핑 체계적
- **DTO 분리**: Entity를 Controller에 직접 반환하지 않는 원칙 준수
- **Docker 멀티 스테이지 빌드**: Spring Boot Dockerfile 최적화 양호

---

## 2. Critical 이슈 (즉시 수정)

### C1. [보안] 비밀번호 하드코딩 + Git 커밋

- **위치**: `docker-compose.yml:6,9,60,82`, `scripts/init-mysql.sql:9,15`
- **문제**: `rootpassword`, `llm_password`, `llm_user_1234` 등 평문 비밀번호가 버전 관리에 포함
- **영향**: 저장소 접근 가능한 누구든 전체 DB 접근 가능
- **수정**: `.env` 파일로 외부화, `.gitignore` 추가, 기존 비밀번호 즉시 교체

### C2. [보안] 전체 엔드포인트 인증/인가 부재

- **위치**: 모든 Spring Controller, 모든 Python FastAPI 엔드포인트
- **문제**: Spring Security 미적용, 인증 없이 모든 API 호출 가능
- **영향**: 의료 상담 데이터 무단 접근, 예약 위조, 시스템 남용
- **수정**: Spring Security 도입, Python 관리 엔드포인트에 API Key 인증

### C3. [보안] IDOR - 채팅/의료 이력 무단 열람

- **위치**: `ChatController.java:62`, `MedicalController.java:130`
- **문제**: `staffId` 경로 변수로 아무 사용자의 히스토리 조회 가능
- **영향**: 전체 상담 기록 유출 (의료 개인정보 침해)
- **수정**: 인증된 세션에서 사용자 ID 추출, 경로 변수 직접 사용 금지

### C4. [보안] Python LLM 서비스 root 권한 + MySQL root 접속

- **위치**: `docker-compose.yml:59-60`, `python-llm/Dockerfile`
- **문제**: 컨테이너 root 실행 + DB root 계정 사용
- **영향**: RCE 취약점 발생 시 전체 시스템 장악 가능
- **수정**: non-root USER 추가, 최소 권한 DB 계정 분리

### C5. [Spring] Reactive 체인 내 @Transactional 동기 메서드 호출

- **위치**: `MedicalController.java:51-53`, `ChatController.java:44-46`
- **문제**: `doOnNext()` 콜백은 Reactor 스레드에서 실행되어 `@Transactional` 미보장
- **영향**: 트랜잭션 무결성 손실 (PENDING → COMPLETED 전환 실패 가능)
- **수정**: `Mono.block()` 동기화 또는 `Schedulers.boundedElastic()` + `fromCallable` 패턴

### C6. [Spring] ReservationService N+1 루프 쿼리

- **위치**: `ReservationService.java:79-80`
- **문제**: 슬롯마다 `countBy` 개별 쿼리 → 최대 112회 DB 호출
- **영향**: 동시 접속 시 DB 커넥션 풀 고갈
- **수정**: 기간별 예약 한 번에 조회 후 메모리 필터링

### C7. [Spring] DoctorService N+1 쿼리

- **위치**: `DoctorService.java:50-55`
- **문제**: 의사마다 스케줄 개별 조회
- **영향**: 의사 N명 → N+1회 쿼리
- **수정**: `findByDoctorIdInAndIsAvailableTrue()` IN 쿼리 또는 `@EntityGraph`

### C8. [Python] metrics.py 데드락 가능성

- **위치**: `metrics.py:56-65`
- **문제**: `to_dict()` 내에서 `self._lock` 재획득 시도 가능
- **영향**: `/metrics` 호출 시 영구 블락
- **수정**: `Lock` → `RLock` 전환 또는 인라인 계산

---

## 3. High 이슈 (1주 내 수정)

### 보안

| #   | 이슈                                  | 위치                       | 수정 방향                                     |
| --- | ------------------------------------- | -------------------------- | --------------------------------------------- |
| H1  | SSE 스트림에서 내부 예외 메시지 노출  | `app.py:440-443`           | 일반 에러 메시지만 반환, 상세는 로그에만      |
| H2  | ConnectionError 핸들러 내부 정보 유출 | `app.py:219-224`           | `str(exc)` 대신 일반 메시지 반환              |
| H3  | LLM Prompt Injection 방어 없음        | `app.py:340-351`           | history 검증 강화, 패턴 필터링                |
| H4  | Spring LlmRequest 입력 검증 없음      | `LlmRequest.java`          | `@NotBlank`, `@Size(max=4096)`, `@Valid` 추가 |
| H5  | DB 포트 전체 인터페이스 바인딩        | `docker-compose.yml:10-11` | `127.0.0.1:3307:3306` 또는 포트 매핑 제거     |
| H6  | `trust_remote_code=True` 모델 로딩    | `llm_service.py:35`        | 모델 허용 목록(allowlist) 적용                |

### Spring Boot

| #   | 이슈                                           | 위치                                                  | 수정 방향                     |
| --- | ---------------------------------------------- | ----------------------------------------------------- | ----------------------------- |
| H7  | `callLlmApi`/`callMedicalLlmApi` 완전 중복     | `MedicalService.java:37-77`                           | 하나의 private 헬퍼로 통합    |
| H8  | Controller에서 Repository 직접 주입            | `ChatController.java:30`, `MedicalController.java:35` | Service 레이어로 이동         |
| H9  | `updateMedicalCompleted` ifPresent 조용한 실패 | `MedicalService.java:117`                             | `orElseThrow`로 변경          |
| H10 | `@ManyToOne` LAZY 누락                         | `Doctor.java:34`, `DoctorSchedule.java:28`            | `fetch = FetchType.LAZY` 추가 |

### Python LLM

| #   | 이슈                                     | 위치                         | 수정 방향                        |
| --- | ---------------------------------------- | ---------------------------- | -------------------------------- |
| H11 | LLM 백엔드 if/else 분기 5곳 중복         | `app.py:272,356,415,499,582` | Strategy/Protocol 패턴 추출      |
| H12 | HuggingFace 동기 호출이 이벤트 루프 차단 | `app.py:296`                 | `asyncio.to_thread()` 래핑       |
| H13 | 에러 메트릭 미기록 (success=False 없음)  | `app.py:303-312`             | 모든 엔드포인트에 에러 기록 추가 |
| H14 | import_medical_data.py 비멱등 INSERT     | `import_medical_data.py:164` | `INSERT IGNORE` 또는 중복 체크   |

### 프론트엔드

| #   | 이슈                                      | 위치                                | 수정 방향                              |
| --- | ----------------------------------------- | ----------------------------------- | -------------------------------------- |
| H15 | 중복 ID 충돌 (streamBubble, slotSection)  | `medical.html:476,646`              | 고유 ID 생성 (timestamp 접미사)        |
| H16 | 헬스체크가 실제 쿼리 API 호출 (DB 부작용) | `index.html:182-187`                | 전용 `GET /api/health` 엔드포인트 생성 |
| H17 | SSE 에러 무시 (silent catch)              | `chat.html:400`, `medical.html:562` | 사용자에게 에러 표시                   |

---

## 4. Medium 이슈 (1개월 내 수정)

### 아키텍처/코드 품질

| #   | 이슈                                               | 영역   | 수정 방향                                   |
| --- | -------------------------------------------------- | ------ | ------------------------------------------- |
| M1  | Spring 패키지 구조: 레이어 → 도메인 기반 전환      | Spring | chat/medical/doctor/reservation/\_core 분리 |
| M2  | PK 타입 Long/Integer 혼재                          | Spring | `Integer` + `IDENTITY`로 통일 (컨벤션)      |
| M3  | status 필드 String → Enum                          | Spring | `@Enumerated(EnumType.STRING)` 적용         |
| M4  | `Resp<T>` 래퍼 부재                                | Spring | `_core/utils/Resp.java` 생성                |
| M5  | GlobalExceptionHandler에 비즈니스 예외 핸들러 없음 | Spring | `IllegalArgumentException`(400) 등 추가     |
| M6  | Reranker가 N회 직렬 LLM 호출                       | Python | Cross-encoder 또는 BM25+vector RRF 도입     |
| M7  | Medical 벡터 검색에 distance threshold 없음        | Python | `rule_context_service.py`와 동일 패턴 적용  |
| M8  | 인덱싱 스크립트 배치 체크포인트 없음               | Python | 마지막 성공 ID 저장으로 재시도 지원         |

### 인프라

| #   | 이슈                                      | 영역   | 수정 방향                                      |
| --- | ----------------------------------------- | ------ | ---------------------------------------------- |
| M9  | CI/CD 파이프라인 완전 부재                | DevOps | GitHub Actions: lint + test + build + scan     |
| M10 | 구조화 로깅 없음                          | DevOps | Python: structlog/JSON, Spring: Logback JSON   |
| M11 | Spring Boot Actuator 미적용               | Spring | starter-actuator 추가, /actuator/health 활성화 |
| M12 | python-llm 헬스체크 없음 (docker-compose) | DevOps | healthcheck 추가 + spring-app 의존성 수정      |
| M13 | restart 정책 없음                         | DevOps | 모든 서비스에 `restart: unless-stopped`        |
| M14 | Docker 네트워크 미격리                    | DevOps | frontend/backend 네트워크 분리                 |
| M15 | requirements-lock.txt 미사용 (Dockerfile) | DevOps | lock 파일로 빌드, 재현 가능한 이미지           |
| M16 | TLS/HTTPS 전무                            | 보안   | 역방향 프록시(Nginx/Traefik) + Let's Encrypt   |
| M17 | ChromaDB 인증 없음                        | 보안   | `CHROMA_SERVER_AUTHN_PROVIDER` 활성화          |

### 프론트엔드

| #   | 이슈                                    | 영역 | 수정 방향                                |
| --- | --------------------------------------- | ---- | ---------------------------------------- |
| M18 | SSE 스트리밍 타임아웃/취소 없음         | UX   | `AbortSignal.timeout(60000)` + 중지 버튼 |
| M19 | 반응형 미적용 (chat.html, medical.html) | UX   | `@media (max-width: 640px)` 추가         |

---

## 5. Low 이슈 (백로그)

| #   | 이슈                                                                      | 영역     |
| --- | ------------------------------------------------------------------------- | -------- |
| L1  | 어노테이션 순서 컨벤션 불일치                                             | Spring   |
| L2  | 테이블명 `_tb` 접미사 9개 누락                                            | Spring   |
| L3  | `@CreationTimestamp` 미사용                                               | Spring   |
| L4  | CSS/JS 인라인 중복 (~300줄 x 3페이지)                                     | Frontend |
| L5  | 접근성(A11y) 전무 (ARIA, role, tabindex 없음)                             | Frontend |
| L6  | `scrollToBottom()` 스트리밍 중 O(n^2) 렌더링                              | Frontend |
| L7  | Quick Chips 영구 숨김 (복원 안 됨)                                        | Frontend |
| L8  | .env.example 동기화 안 됨 (백엔드 불일치)                                 | DevOps   |
| L9  | Dockerfile EXPOSE 포트 불일치 (8080 vs 8081)                              | DevOps   |
| L10 | Spring Rate Limiting 부재                                                 | 보안     |
| L11 | 보안 헤더(CSP, HSTS, X-Frame-Options) 미설정                              | 보안     |
| L12 | 테스트 커버리지 부족 (Spring: Reservation 0%, Python: 핵심 모듈 미테스트) | 품질     |

---

## 6. 통합 개선 로드맵

### Phase 1 - 긴급 수정 (1~3일)

> 목표: 보안 위협 차단 + 데이터 무결성 확보

| 순서 | 작업                                                  | 노력 | 효과                  |
| ---- | ----------------------------------------------------- | ---- | --------------------- |
| 1    | 비밀번호 외부화 (.env) + 기존 크리덴셜 교체           | 소   | 보안 CRITICAL 해소    |
| 2    | DB 포트 localhost 바인딩 (`127.0.0.1`)                | 소   | DB 직접 접근 차단     |
| 3    | Python non-root USER + 최소 권한 DB 계정              | 소   | 컨테이너 보안 강화    |
| 4    | SSE/에러 핸들러 내부 정보 유출 차단                   | 소   | 내부 토폴로지 보호    |
| 5    | Reactive 체인 트랜잭션 수정 (block 또는 fromCallable) | 중   | 트랜잭션 무결성       |
| 6    | ReservationService + DoctorService N+1 제거           | 소   | DB 쿼리 112회→1회     |
| 7    | 프론트엔드 중복 ID 충돌 수정                          | 소   | 멀티턴 대화 버그 해소 |

### Phase 2 - 단기 개선 (1~2주)

> 목표: 인증 체계 구축 + 코드 품질 향상

| 순서 | 작업                                           | 노력 | 효과                 |
| ---- | ---------------------------------------------- | ---- | -------------------- |
| 8    | Spring Security 도입 (세션 기반 인증)          | 중   | IDOR 해소, 접근 제어 |
| 9    | Python 관리 엔드포인트 API Key 인증            | 소   | 관리 기능 보호       |
| 10   | LlmRequest @Valid + @Size 검증                 | 소   | 입력 검증 강화       |
| 11   | callLlmApi 중복 제거 + Controller→Service 정리 | 소   | 유지보수성 향상      |
| 12   | ifPresent → orElseThrow 변경                   | 소   | 버그 탐지력 향상     |
| 13   | @ManyToOne LAZY 추가                           | 소   | 불필요한 JOIN 방지   |
| 14   | python-llm 헬스체크 + restart 정책 추가        | 소   | 운영 안정성          |
| 15   | 에러 메트릭 기록 추가                          | 소   | 실제 실패율 파악     |
| 16   | SSE 스트리밍 타임아웃 + 취소 버튼              | 중   | 사용자 경험 개선     |

### Phase 3 - 중기 고도화 (3~4주)

> 목표: 아키텍처 정비 + DevOps 체계화

| 순서 | 작업                                     | 노력 | 효과                   |
| ---- | ---------------------------------------- | ---- | ---------------------- |
| 17   | LLM Backend Strategy/Protocol 패턴 추출  | 높   | 5곳 코드 중복 제거     |
| 18   | Spring 패키지 도메인 기반 전환           | 중   | 도메인 경계 명확화     |
| 19   | PK 타입 통일 + Resp 래퍼 도입            | 중   | 컨벤션 준수            |
| 20   | GitHub Actions CI/CD 파이프라인          | 중   | 품질 게이트 자동화     |
| 21   | 구조화 로깅 (structlog + Logback JSON)   | 중   | 운영 가시성 확보       |
| 22   | Spring Boot Actuator + Prometheus 메트릭 | 중   | 모니터링 체계 구축     |
| 23   | Reranker Cross-encoder 전환              | 중   | RAG 성능 3x 향상       |
| 24   | 반응형 디자인 + 접근성 개선              | 중   | 모바일/스크린리더 지원 |
| 25   | 테스트 커버리지 강화                     | 중   | 안정성 향상            |

### Phase 4 - 장기 (1~2개월)

> 목표: 프로덕션 준비 + 규정 준수

| 순서 | 작업                                     | 노력 | 효과             |
| ---- | ---------------------------------------- | ---- | ---------------- |
| 26   | TLS 역방향 프록시 배포                   | 중   | 통신 암호화      |
| 27   | Docker 네트워크 격리 + ChromaDB 인증     | 중   | 인프라 보안      |
| 28   | Prompt Injection 방어 체계               | 높   | LLM 보안 강화    |
| 29   | 의료 데이터 감사 로깅                    | 높   | 규정 준수 (PIPA) |
| 30   | 대화 이력(Multi-turn) + 응답 피드백 루프 | 높   | 사용자 경험/품질 |

---

## 7. Agent Team 분석 요약

### Spring Architect

**핵심 발견:**

- Reactive 체인 내 `@Transactional` 미보장이 가장 심각한 아키텍처 결함
- MVC + WebClient 혼합 구조에서 `Mono.block()` 동기화가 현실적 해법
- 패키지 구조가 레이어 기반 → 도메인 기반 전환 필요
- 컨벤션(CLAUDE.md)과 실제 코드 괴리가 큼 (테이블명, PK 타입, 어노테이션 순서)

**권장 전략:** SSE 스트리밍 엔드포인트는 Flux 유지, 일반 엔드포인트는 block() 동기화. R2DBC 전환은 과도한 투자.

### Python Architect

**핵심 발견:**

- LLM 백엔드 추상화 부재로 5곳에 동일한 if/else 분기 중복
- Reranker가 검색 결과당 1회 LLM 호출 → 3x 레이턴시 추가
- Medical RAG에 distance threshold 없음 (Rule RAG는 있음)
- HuggingFace 백엔드 동기 호출이 async 이벤트 루프 차단
- 에러 메트릭이 전혀 기록되지 않음

**권장 전략:** `LLMBackend` Protocol 추출이 최우선. Cross-encoder 기반 reranker로 전환.

### Security Reviewer

**핵심 발견:**

- CRITICAL 4건: 비밀번호 하드코딩, 인증 전무, IDOR, root 권한 컨테이너
- HIGH 6건: 정보 유출, Prompt Injection, 입력 검증, DB 포트 노출, trust_remote_code
- 의료 데이터 관련 PIPA 규정 준수 미흡 (암호화, 감사 로깅, 접근 제어 없음)
- SQL Injection은 안전 (파라미터화 쿼리 사용 확인)

**권장 전략:** 비밀번호 즉시 교체 → 인증 체계 구축 → TLS 배포 → 감사 로깅 순서.

### Infra Architect

**핵심 발견:**

- docker-compose에 자격 증명 불일치 (Python=root, Spring=llm_admin)
- CI/CD 완전 부재, 모니터링 인프라 부재
- requirements.txt와 lock 파일 괴리, chromadb 클라이언트/서버 버전 불일치
- vLLM 모드에서 불필요한 torch 포함 (이미지 ~2GB 과대)
- Spring Boot Actuator 미적용

**권장 전략:** 비밀번호 외부화 → 헬스체크/restart 추가 → CI/CD 구축 → 모니터링 순서.

### Frontend Architect

**핵심 발견:**

- 3개 HTML 파일에 CSS/JS ~300줄씩 중복
- `medical.html`의 중복 ID 충돌로 멀티턴 대화 시 슬롯/스트림 버그
- 헬스체크가 실제 쿼리 API 호출 (30초마다 MedicalHistory PENDING 생성)
- SSE 에러 무시 (catch에서 삼킴), 타임아웃/취소 기능 없음
- 접근성(A11y) 전무: ARIA 속성, role, tabindex 없음
- 반응형 미적용 (index.html에만 1개 미디어 쿼리)
- `scrollToBottom()` + `innerHTML` 재할당이 O(n^2) 성능 문제

**권장 전략:** 중복 ID/헬스체크 버그 즉시 수정 → 타임아웃/취소 추가 → CSS/JS 분리.

---

## 부록: 이슈 전체 목록 (심각도별)

### Critical (8건)

1. C1 - 비밀번호 하드코딩 (보안)
2. C2 - 인증/인가 전무 (보안)
3. C3 - IDOR 취약점 (보안)
4. C4 - root 권한 컨테이너 (보안)
5. C5 - Reactive+@Transactional 충돌 (Spring)
6. C6 - ReservationService N+1 (Spring)
7. C7 - DoctorService N+1 (Spring)
8. C8 - metrics.py 데드락 (Python)

### High (17건)

1. H1 - SSE 내부 정보 유출 (보안)
2. H2 - ConnectionError 정보 유출 (보안)
3. H3 - Prompt Injection 방어 없음 (보안)
4. H4 - LlmRequest 입력 검증 없음 (보안)
5. H5 - DB 포트 전 인터페이스 바인딩 (보안)
6. H6 - trust_remote_code=True (보안)
7. H7 - callLlmApi 중복 (Spring)
8. H8 - Controller→Repository 직접 주입 (Spring)
9. H9 - ifPresent 조용한 실패 (Spring)
10. H10 - @ManyToOne LAZY 누락 (Spring)
11. H11 - LLM 백엔드 5곳 중복 (Python)
12. H12 - HuggingFace 이벤트 루프 차단 (Python)
13. H13 - 에러 메트릭 미기록 (Python)
14. H14 - 비멱등 INSERT (Python)
15. H15 - 중복 ID 충돌 (Frontend)
16. H16 - 헬스체크 DB 부작용 (Frontend)
17. H17 - SSE 에러 무시 (Frontend)

### Medium (19건)

26~44: 패키지 구조, PK 통일, Enum 전환, Resp 래퍼, GlobalExceptionHandler, Reranker, 벡터 threshold, 인덱싱 체크포인트, CI/CD, 구조화 로깅, Actuator, docker 헬스체크, restart, 네트워크 격리, lock 파일, TLS, ChromaDB 인증, SSE 타임아웃, 반응형

### Low (12건)

lmApi 중복 (Spring) 8. H8 - Controller→Repository 직접 주입 (Spring) 9. H9 - ifPresent 조용한 실패 (Spring) 10. H10 - @ManyToOne LAZY 누락 (Spring) 11. H11 - LLM 백엔드 5곳 중복 (Python) 12. H12 - HuggingFace 이벤트 루프 차단 (Python) 13. H13 - 에러 메트릭 미기록 (Python) 14. H14 - 비멱등 INSERT (Python) 15. H15 - 중복 ID 충돌 (Frontend) 16. H16 - 헬스체크 DB 부작용 (Frontend) 16. H16 - 헬스체크 DB 부작용 (Frontend) 17. H17 - SSE 에러 무시 (Frontend)

### Medium (19건)

26~44: 패키지 구조, PK 통일, Enum 전환, Resp 래퍼, GlobalExceptionHandler, Reranker, 벡터 threshold, 인덱싱 체크포인트, CI/CD, 구조화 로깅, Actuator, docker 헬스체크, restart, 네트워크 격리, lock 파일, TLS, ChromaDB 인증, SSE 타임아웃, 반응형

### Low (12건)

45~56: 어노테이션 순서, 테이블명, CreationTimestamp, CSS/JS 중복, 접근성, 스트리밍 렌더링, Quick Chips, .env 동기화, EXPOSE 포트, Rate Limiting, 보안 헤더, 테스트 커버리지
