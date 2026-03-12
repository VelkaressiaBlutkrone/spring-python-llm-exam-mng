# Python LLM 개선 실행 계획서 — Task / Step / Workflow

> 작성일: 2026-03-12
> 기반 문서: `doc/IMPROVEMENT_PYTHON_LLM.md`
> 총 22개 Task, 4개 Phase

---

## 목차

- [Phase 1 — 즉시 적용 (Task 1~6)](#phase-1--즉시-적용-task-16)
- [Phase 2 — 단기 개선 (Task 7~13)](#phase-2--단기-개선-task-713)
- [Phase 3 — 중기 고도화 (Task 14~19)](#phase-3--중기-고도화-task-1419)
- [Phase 4 — 장기 (Task 20~22)](#phase-4--장기-task-2022)
- [의존 관계 다이어그램](#의존-관계-다이어그램)

---

## Phase 1 — 즉시 적용 (Task 1~6)

---

### Task 1: httpx 공유 클라이언트 전환

> 개선항목: 1.1 | 난이도: 낮음 | 영향 파일: `app.py`, `ollama_service.py`

**목표**: 매 요청마다 httpx.AsyncClient를 생성하는 대신, 앱 수명 주기에 바인딩된 공유 클라이언트를 사용한다.

#### Step 1: 현행 코드 내 httpx 클라이언트 생성 위치 파악
- [ ] `app.py` — `infer_medical()`, `infer_medical_stream()`, `infer_rule()` 내 `async with httpx.AsyncClient`
- [ ] `ollama_service.py` — `generate_with_ollama()`, `chat_with_ollama()`, `check_ollama_health()`, `list_models()`
- [ ] `embedding_service.py` — `get_embedding()`, `get_embeddings_batch()`

#### Step 2: 공유 클라이언트 생성
- [ ] `app.py`의 `lifespan()`에서 `httpx.AsyncClient` 생성 → `app.state.http_client`에 저장
- [ ] `httpx.Timeout(connect=5.0, read=60.0, write=5.0, pool=5.0)` 설정
- [ ] `httpx.Limits(max_connections=20, max_keepalive_connections=10)` 설정
- [ ] `lifespan()` yield 후 `await app.state.http_client.aclose()` 추가

#### Step 3: 각 모듈에서 공유 클라이언트 사용
- [ ] `ollama_service.py` 함수에 `client: httpx.AsyncClient | None = None` 파라미터 추가
- [ ] `embedding_service.py` 동일하게 클라이언트 주입 가능하도록 수정
- [ ] `app.py` 엔드포인트에서 `request.app.state.http_client`를 전달

#### Step 4: 검증
- [ ] `/health` 엔드포인트 호출 → Ollama 연결 정상 확인
- [ ] `/infer/medical` 연속 5회 호출 → 오류 없이 응답 확인
- [ ] 서버 종료 시 `aclose()` 로그 확인

**Workflow**:
```
파악(Step1) → 구현(Step2) → 적용(Step3) → 검증(Step4)
```

---

### Task 2: Ollama 호출 로직 중복 제거

> 개선항목: 1.2 | 난이도: 낮음 | 영향 파일: `app.py`, `ollama_service.py`
> 선행: Task 1 (공유 클라이언트)

**목표**: `app.py`에 분산된 Ollama Chat API 호출 코드를 `ollama_service.py`의 `chat_with_ollama()`로 통합한다.

#### Step 1: 중복 코드 식별
- [ ] `app.py:infer_medical()` — payload 구성 + httpx 호출 + 응답 파싱 (L231~L253)
- [ ] `app.py:infer_rule()` — 거의 동일한 코드 (L357~L379)
- [ ] `app.py:infer_medical_stream()` — 스트리밍 버전 (L276~L323)

#### Step 2: ollama_service.py 확장
- [ ] `chat_with_ollama()`에 `stop: list[str] | None` 파라미터 추가
- [ ] `chat_with_ollama()`에 `client: httpx.AsyncClient | None` 파라미터 추가
- [ ] 응답 텍스트에 `clean_llm_response()` 적용 옵션 추가
- [ ] 스트리밍 전용 `chat_with_ollama_stream()` 함수 신규 생성
  - `AsyncGenerator[str, None]` 반환
  - 토큰 단위 특수문자 제거 포함

#### Step 3: app.py 엔드포인트 리팩토링
- [ ] `infer_medical()`: 메시지 구성 → `chat_with_ollama()` 호출로 교체
- [ ] `infer_rule()`: 동일하게 교체
- [ ] `infer_medical_stream()`: `chat_with_ollama_stream()` 호출로 교체

#### Step 4: 검증
- [ ] 기존 3개 엔드포인트 기능 동작 확인 (일반/의학/규칙)
- [ ] 스트리밍 SSE 토큰 전송 정상 확인
- [ ] 응답 내용이 기존과 동일한지 비교 테스트

**Workflow**:
```
식별(Step1) → 서비스 확장(Step2) → 엔드포인트 리팩토링(Step3) → 검증(Step4)
```

---

### Task 3: 벡터/FULLTEXT 병렬 검색

> 개선항목: 2.2 | 난이도: 낮음 | 영향 파일: `medical_context_service.py`

**목표**: `build_medical_context()`에서 벡터 검색, Q&A FULLTEXT, 콘텐츠 FULLTEXT를 `asyncio.gather`로 동시 실행한다.

#### Step 1: 현행 순차 흐름 확인
- [ ] `search_vector_store()` → 결과 수 판단 → `search_medical_qa()` → `search_medical_content()` (순차)

#### Step 2: asyncio.gather 병렬화
- [ ] 3개 검색 함수를 `asyncio.gather()`로 동시 실행
- [ ] 각 함수에 `return_exceptions=True` 적용하여 개별 실패 허용
- [ ] 결과 합산 로직에서 기존 조건문(벡터 결과 부족 시 FULLTEXT 보완) 유지

#### Step 3: 포맷팅 함수 분리
- [ ] `_format_vector_results(results)` 추출
- [ ] `_format_qa_results(results)` 추출
- [ ] `_format_content_results(results)` 추출

#### Step 4: 검증
- [ ] `/infer/medical` 호출 → 컨텍스트 정상 구성 확인 (로그)
- [ ] 벡터 검색 실패 시 FULLTEXT 결과만으로 컨텍스트 구성되는지 확인
- [ ] 응답 시간 비교 (변경 전/후 로그 기반)

**Workflow**:
```
현행 확인(Step1) → 병렬화(Step2) → 리팩토링(Step3) → 검증(Step4)
```

---

### Task 4: response_cleaner.py 주석 번호 수정

> 개선항목: 5.1 | 난이도: 매우 낮음 | 영향 파일: `response_cleaner.py`

**목표**: `clean_llm_response()` 내 중복된 단계 번호를 (1)~(7)로 순차 정리한다.

#### Step 1: 수정
- [ ] 현재 주석 번호 확인: (1), (2), (3), (4)전각변환, (5)고아구두점, (5)공백, (4)잘림
- [ ] 순차 재번호: (1)특수토큰 → (2)CJK구두점 → (3)CJK문자 → (4)전각변환 → (5)고아구두점 → (6)공백정규화 → (7)불완전문장

#### Step 2: 검증
- [ ] 기존 테스트 실행 (있는 경우)
- [ ] 함수 동작은 변경 없음을 확인

**Workflow**:
```
수정(Step1) → 검증(Step2)
```

---

### Task 5: typo_corrector.py 정상→정상 매핑 제거

> 개선항목: 5.2 | 난이도: 매우 낮음 | 영향 파일: `typo_corrector.py`

**목표**: `MEDICAL_TYPO_MAP` 초기 사전에서 `key == value`인 불필요 항목을 제거한다.

#### Step 1: 불필요 항목 식별
- [ ] `"어깨": "어깨"`, `"골절": "골절"`, `"두통": "두통"` 등 정상→정상 매핑 목록 추출
- [ ] 총 항목 수 확인 (현재 131항목 중 오타만 남기면 약 60~70항목)

#### Step 2: 사전 정리
- [ ] 정상→정상 항목 삭제
- [ ] 맨 아래 필터 코드 `{k: v for k, v in ... if k != v}` 는 안전장치로 유지하되, 주석에 "방어적 필터" 표기

#### Step 3: 검증
- [ ] `correct_typos("무릅이 아파요")` → `"무릎이 아파요"` 확인
- [ ] `correct_typos("정형외과 가고 싶어요")` → 변경 없음 확인

**Workflow**:
```
식별(Step1) → 정리(Step2) → 검증(Step3)
```

---

### Task 6: Health Check 강화

> 개선항목: 6.4 | 난이도: 낮음 | 영향 파일: `app.py`, `medical_context_service.py`, `vector_store.py`

**목표**: `/health` 엔드포인트에서 Ollama, MySQL, ChromaDB 세 가지 의존성 상태를 모두 확인한다.

#### Step 1: 개별 헬스체크 함수 작성
- [ ] `check_mysql_health()` — `get_pool()` → `SELECT 1` 실행 → bool 반환
- [ ] `check_chromadb_health()` — `get_chroma_client().heartbeat()` → bool 반환
- [ ] 기존 `check_ollama_health()` 재사용

#### Step 2: /health 엔드포인트 수정
- [ ] 3개 체크를 `asyncio.gather()`로 병렬 실행
- [ ] 응답 형식: `{ status: "healthy"|"degraded", checks: { ollama, mysql, chromadb } }`
- [ ] 하나라도 false면 `status: "degraded"` + HTTP 200 (503 대신 — Docker 헬스체크 호환)

#### Step 3: 검증
- [ ] 정상 상태에서 `/health` → 모두 true
- [ ] MySQL 중지 후 `/health` → mysql: false, status: "degraded"

**Workflow**:
```
함수 작성(Step1) → 엔드포인트 수정(Step2) → 검증(Step3)
```

---

## Phase 2 — 단기 개선 (Task 7~13)

---

### Task 7: 임베딩 캐시 도입

> 개선항목: 2.1 | 난이도: 낮음 | 영향 파일: `embedding_service.py`

**목표**: 동일 쿼리 임베딩을 메모리 캐시하여 Ollama 호출을 줄인다.

#### Step 1: 캐시 구조 설계
- [ ] 해시 키: `hashlib.sha256(text.encode()).hexdigest()`
- [ ] 저장: `OrderedDict` (FIFO 삭제 용이)
- [ ] 최대 크기: `MAX_CACHE_SIZE = 500` (환경변수로 설정 가능)

#### Step 2: get_embedding() 수정
- [ ] 캐시 조회 → hit 시 즉시 반환 (로그: "Embedding cache hit")
- [ ] miss 시 Ollama 호출 → 캐시 저장
- [ ] 캐시 초과 시 가장 오래된 항목 제거

#### Step 3: 캐시 관리 API (선택)
- [ ] `GET /cache/stats` — 캐시 크기, hit/miss 비율
- [ ] `DELETE /cache` — 캐시 초기화

#### Step 4: 검증
- [ ] 동일 쿼리 2회 요청 → 2번째 응답 시간 측정 (임베딩 호출 생략 확인)
- [ ] 500개 초과 시 FIFO 동작 확인

**Workflow**:
```
설계(Step1) → 구현(Step2) → API(Step3, 선택) → 검증(Step4)
```

---

### Task 8: ChromaDB 컬렉션 분리

> 개선항목: 2.3 | 난이도: 중간 | 영향 파일: `rule_context_service.py`, `index_rule_data.py`, `vector_store.py`

**목표**: 병원 규칙을 `medical_rules` 별도 컬렉션으로 분리하여 검색 정확도를 높인다.

#### Step 1: vector_store.py 확장
- [ ] `get_rule_collection()` 함수 추가 — `settings.chroma_rule_collection` 사용
- [ ] 기존 `get_collection()`은 의학 문서 전용으로 유지

#### Step 2: rule_context_service.py 수정
- [ ] `_get_collection()` → `get_rule_collection()` 으로 변경
- [ ] `where={"type": "rule"}` 필터 제거 (별도 컬렉션이므로 불필요)

#### Step 3: index_rule_data.py 수정
- [ ] 인덱싱 대상을 `get_rule_collection()` 으로 변경
- [ ] 기존 `medical_docs` 컬렉션의 rule 문서 정리 마이그레이션 스크립트 작성

#### Step 4: 마이그레이션
- [ ] 기존 `medical_docs`에서 `type=rule` 문서 삭제
- [ ] `index_rule_data.py` 재실행 → `medical_rules` 컬렉션에 저장
- [ ] 문서 수 확인

#### Step 5: 검증
- [ ] `/infer/rule` 호출 → 규칙 검색 정상 동작
- [ ] `/infer/medical` 호출 → 의학 검색에 규칙 문서 미포함 확인

**Workflow**:
```
확장(Step1) → 서비스 수정(Step2) → 인덱서 수정(Step3) → 마이그레이션(Step4) → 검증(Step5)
```

---

### Task 9: 프롬프트 관리 외부화

> 개선항목: 1.3 | 난이도: 낮음 | 영향 파일: `app.py`, 신규 `prompts/`, `prompt_loader.py`

**목표**: 시스템 프롬프트를 외부 텍스트 파일로 분리한다.

#### Step 1: 프롬프트 파일 생성
- [ ] `python-llm/prompts/medical_system.txt` — 현재 `MEDICAL_SYSTEM_PROMPT` 내용
- [ ] `python-llm/prompts/rule_system.txt` — 현재 `RULE_SYSTEM_PROMPT` 내용

#### Step 2: prompt_loader.py 작성
- [ ] `load_prompt(name: str) -> str` — 파일 읽기 + `@lru_cache`
- [ ] `reload_prompt(name: str)` — 캐시 무효화 (런타임 리로드용)
- [ ] 파일 미존재 시 `FileNotFoundError` + 로그

#### Step 3: app.py 수정
- [ ] `MEDICAL_SYSTEM_PROMPT` 상수 삭제 → `load_prompt("medical_system")` 호출로 교체
- [ ] `RULE_SYSTEM_PROMPT` 동일하게 교체

#### Step 4: 검증
- [ ] 서버 기동 → `/infer/medical` 정상 응답
- [ ] 프롬프트 파일 수정 → 서버 재시작 → 변경 반영 확인

**Workflow**:
```
파일 생성(Step1) → 로더 작성(Step2) → app.py 수정(Step3) → 검증(Step4)
```

---

### Task 10: Few-shot 예시 추가

> 개선항목: 4.1 | 난이도: 낮음 | 영향 파일: `prompts/medical_system.txt` (Task 9 이후)
> 선행: Task 9 (프롬프트 외부화)

**목표**: 의학 상담 시스템 프롬프트에 1~2개의 응답 예시를 추가하여 형식 일관성을 높인다.

#### Step 1: 예시 설계
- [ ] 예시 1: 근골격계 증상 (무릎 통증 → 정형외과)
- [ ] 예시 2: 내과 증상 (복통 + 소화불량 → 소화기내과)
- [ ] 각 예시에 포함할 섹션: 추천 진료과, 추천 이유, 응급 판단

#### Step 2: 프롬프트 파일 수정
- [ ] `prompts/medical_system.txt` 하단에 `\n\n--- 예시 ---\n` 구분자 추가
- [ ] 예시 Q&A 2쌍 추가

#### Step 3: 검증
- [ ] 다양한 증상 5개로 테스트 → 응답 형식 일관성 비교
- [ ] 토큰 사용량 확인 (few-shot 추가로 인한 추가 비용 측정)

**Workflow**:
```
예시 설계(Step1) → 프롬프트 수정(Step2) → 검증(Step3)
```

---

### Task 11: Circuit Breaker 도입

> 개선항목: 6.1 | 난이도: 중간 | 영향 파일: 신규 `circuit_breaker.py`, `ollama_service.py`, `app.py`

**목표**: Ollama 서버 장애 시 빠르게 실패하여 사용자 대기 시간을 줄인다.

#### Step 1: CircuitBreaker 클래스 구현
- [ ] `circuit_breaker.py` 신규 파일 생성
- [ ] 상태: CLOSED(정상) → OPEN(차단) → HALF_OPEN(시험)
- [ ] 설정: `failure_threshold=5`, `reset_timeout=30초`
- [ ] 스레드 안전: `threading.Lock` 사용

#### Step 2: ollama_service.py 통합
- [ ] 모듈 레벨 `_breaker = CircuitBreaker()` 인스턴스 생성
- [ ] `chat_with_ollama()` 진입 시 `_breaker.can_execute()` 확인
  - False → 즉시 `ServiceUnavailableError` 발생
- [ ] 성공 시 `_breaker.record_success()`
- [ ] 실패 시 `_breaker.record_failure()`

#### Step 3: app.py 에러 핸들링
- [ ] `ServiceUnavailableError` 예외 핸들러 추가 → 503 + "서비스 일시 중단" 메시지
- [ ] 응답에 `Retry-After` 헤더 포함 (reset_timeout 값)

#### Step 4: 상태 확인 API
- [ ] `GET /health`에 circuit_breaker 상태 포함: `{ breaker: "CLOSED" | "OPEN" | "HALF_OPEN" }`

#### Step 5: 검증
- [ ] Ollama 정지 → 5회 요청 → 6번째 요청부터 즉시 503
- [ ] 30초 후 Ollama 재시작 → HALF_OPEN → 성공 시 CLOSED 복귀

**Workflow**:
```
클래스 구현(Step1) → 서비스 통합(Step2) → 에러 처리(Step3) → 상태 API(Step4) → 검증(Step5)
```

---

### Task 12: 테스트 커버리지 강화

> 개선항목: 5.4 | 난이도: 중간 | 영향 파일: `tests/` 디렉토리

**목표**: 순수 함수 중심으로 단위 테스트를 작성하여 리팩토링 안전망을 구축한다.

#### Step 1: 테스트 대상 식별 (순수 함수 우선)
- [ ] `response_cleaner.py` — `clean_llm_response()`, `_trim_incomplete_ending()`
- [ ] `typo_corrector.py` — `correct_typos()`
- [ ] `medical_context_service.py` — `extract_keywords()`
- [ ] `schemas.py` — `InferRequest` 유효성 검증

#### Step 2: test_response_cleaner.py
- [ ] 특수 토큰 제거 테스트
- [ ] 중국어/일본어 문자 제거 테스트
- [ ] 전각 구두점 변환 테스트
- [ ] 불완전 문장 잘림 테스트
- [ ] 빈 문자열/None 입력 테스트

#### Step 3: test_typo_corrector.py
- [ ] 기본 오타 교정 테스트 ("무릅" → "무릎")
- [ ] 진료과 오타 테스트 ("정형외괴" → "정형외과")
- [ ] 변경 없는 입력 테스트
- [ ] 여러 오타 동시 교정 테스트

#### Step 4: test_extract_keywords.py
- [ ] 한국어 키워드 추출 테스트
- [ ] 영문 키워드 추출 테스트
- [ ] 1글자 단어 제외 테스트
- [ ] 최대 8개 제한 테스트

#### Step 5: test_schemas.py
- [ ] 정상 요청 유효성 통과
- [ ] query 빈 문자열 거부
- [ ] temperature 범위 초과 거부

#### Step 6: CI 연동 (선택)
- [ ] `pytest.ini` 또는 `pyproject.toml`에 테스트 설정 추가
- [ ] `pytest --cov=. --cov-report=term-missing` 커버리지 확인

**Workflow**:
```
대상 식별(Step1) → 테스트 작성(Step2~5) → CI 연동(Step6, 선택)
```

---

### Task 13: 보안 일괄 개선 (입력 길이 / CORS / Rate Limit)

> 개선항목: 7.1, 7.2, 7.3 | 난이도: 낮음 | 영향 파일: `config.py`, `schemas.py`, `app.py`

**목표**: 입력 검증, CORS, Rate Limiting 세 가지 보안 이슈를 한 번에 해결한다.

#### Step 1: 입력 길이 통일 (7.1)
- [ ] `config.py`의 `llm_input_max_length=2048`을 기준으로 통일
- [ ] `schemas.py`의 `InferRequest.query` max_length를 2048로 변경
- [ ] 또는 `schemas.py`에서 설정값을 동적 참조

#### Step 2: CORS 환경변수화 (7.2)
- [ ] `config.py`에 `cors_origins: str = Field(default="http://localhost:8080")` 추가
- [ ] 콤마 구분 문자열 → 리스트 변환 validator 추가
- [ ] `app.py`에서 `settings.cors_origins` 사용

#### Step 3: Rate Limiting (7.3)
- [ ] `requirements.txt`에 `slowapi>=0.1.9` 추가
- [ ] `app.py`에 Limiter 초기화
- [ ] `/infer/*` 엔드포인트에 `@limiter.limit("10/minute")` 적용
- [ ] 429 응답 핸들러 추가

#### Step 4: 검증
- [ ] 4097자 쿼리 전송 → 422 에러 확인
- [ ] 환경변수 `CORS_ORIGINS` 설정 후 기동 → 반영 확인
- [ ] 11번째 요청 → 429 Too Many Requests

**Workflow**:
```
입력(Step1) → CORS(Step2) → Rate Limit(Step3) → 검증(Step4)
```

---

## Phase 3 — 중기 고도화 (Task 14~19)

---

### Task 14: Re-ranking 도입

> 개선항목: 3.1 | 난이도: 높음 | 영향 파일: 신규 `reranker.py`, `medical_context_service.py`

**목표**: 벡터 검색 결과를 LLM 기반으로 재정렬하여 컨텍스트 품질을 높인다.

#### Step 1: 경량 Re-ranker 설계
- [ ] 전략 선택: Ollama 프롬프트 기반 (별도 모델 불필요)
- [ ] 프롬프트: "다음 문서들 중 질문 '{query}'에 가장 관련 있는 3개를 번호로 선택"
- [ ] 입력: Top-10 검색 결과, 출력: 순위 번호 리스트

#### Step 2: reranker.py 구현
- [ ] `async def rerank(query: str, documents: list[dict], top_n: int = 3) -> list[dict]`
- [ ] Ollama generate 호출 (저온도 0.1, 짧은 max_length 50)
- [ ] 응답 파싱: 번호 추출 → 해당 문서 반환
- [ ] 파싱 실패 시 원래 순서 유지 (fallback)

#### Step 3: medical_context_service.py 통합
- [ ] `search_vector_store()` top_k를 10으로 상향
- [ ] 결과에 `rerank()` 적용 → top_3 반환
- [ ] 설정: `USE_RERANKING=true` 환경변수로 on/off

#### Step 4: 검증
- [ ] 동일 질문에 대해 re-ranking 전/후 컨텍스트 비교
- [ ] 응답 품질 비교 (수동 평가 5개 질문)
- [ ] 추가 지연 시간 측정 (re-ranking 호출 비용)

**Workflow**:
```
설계(Step1) → 구현(Step2) → 통합(Step3) → 검증(Step4)
```

---

### Task 15: 쿼리 확장 (Query Expansion)

> 개선항목: 3.2 | 난이도: 중간 | 영향 파일: 신규 `query_expander.py`, `medical_context_service.py`

**목표**: 짧은 구어체 질문을 의학 용어로 확장하여 검색 재현율을 높인다.

#### Step 1: query_expander.py 구현
- [ ] `async def expand_query(original: str) -> str`
- [ ] Ollama 호출 (저비용: max_length=50, temperature=0.3)
- [ ] 프롬프트: 관련 의학 용어/진료과/증상 5개 키워드 나열
- [ ] 결과: `"{original} {expanded_keywords}"`

#### Step 2: medical_context_service.py 통합
- [ ] `build_medical_context()` 진입 시 `expand_query()` 호출
- [ ] 확장된 쿼리로 벡터 검색 + FULLTEXT 검색 수행
- [ ] 설정: `USE_QUERY_EXPANSION=true` 환경변수로 on/off

#### Step 3: 검증
- [ ] "머리 아파요" → 확장 후 "두통 편두통 긴장성두통 신경과 뇌압" 등 포함 확인
- [ ] 검색 결과 수 비교 (확장 전/후)
- [ ] 추가 지연 시간 측정

**Workflow**:
```
구현(Step1) → 통합(Step2) → 검증(Step3)
```

---

### Task 16: Chunk 전략 개선

> 개선항목: 3.4 | 난이도: 중간 | 영향 파일: `index_medical_data.py`, 신규 `chunker.py`

**목표**: 긴 의학 콘텐츠를 오버랩 청킹하여 정보 손실을 방지한다.

#### Step 1: chunker.py 구현
- [ ] `chunk_text(text, chunk_size=800, overlap=200) -> list[str]`
- [ ] 문장 경계 인식: 마침표, 줄바꿈 위치에서 자르기
- [ ] 최소 청크 길이 설정 (너무 짧은 잔여 청크 방지)

#### Step 2: index_medical_data.py 수정
- [ ] 콘텐츠 인덱싱 시 `chunk_text()` 적용
- [ ] 청크 ID: `content_{c_id}_chunk_{i}` 형식
- [ ] 메타데이터에 `chunk_index`, `total_chunks` 추가
- [ ] Q&A는 기존 방식 유지 (질문+답변 조합이 이미 적절한 크기)

#### Step 3: 검색 결과 중복 제거
- [ ] 동일 원문(`c_id`)에서 여러 청크가 검색될 경우 가장 높은 유사도 1개만 사용
- [ ] `medical_context_service.py`에 중복 제거 로직 추가

#### Step 4: 마이그레이션 및 검증
- [ ] ChromaDB 컬렉션 리셋 → 재인덱싱
- [ ] 인덱싱된 문서 수 확인 (기존 대비 증가)
- [ ] 긴 콘텐츠 후반부 내용으로 질문 → 검색 성공 확인

**Workflow**:
```
chunker 구현(Step1) → 인덱서 수정(Step2) → 중복 제거(Step3) → 마이그레이션(Step4)
```

---

### Task 17: 대화 이력 (Multi-turn) 지원

> 개선항목: 4.2 | 난이도: 높음 | 영향 파일: `schemas.py`, `app.py`, Spring Boot `MedicalService.java`, `MedicalController.java`

**목표**: 연속 대화를 지원하여 사용자가 이전 문맥을 참조할 수 있게 한다.

#### Step 1: Python 스키마 확장
- [ ] `InferRequest`에 `session_id: str | None = None` 추가
- [ ] `InferRequest`에 `history: list[dict] | None = None` 추가
- [ ] history 형식: `[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]`

#### Step 2: app.py 엔드포인트 수정
- [ ] `infer_medical()`: history가 있으면 messages에 system 프롬프트 → history → 현재 질문 순서로 구성
- [ ] 최근 N턴 제한 (기본 3턴 = 6 메시지) — 토큰 초과 방지
- [ ] `infer_medical_stream()` 동일하게 수정

#### Step 3: Spring Boot 수정
- [ ] `LlmRequest`에 `sessionId`, `history` 필드 추가
- [ ] `MedicalService`에서 `MedicalHistory` 테이블의 최근 3건 조회
- [ ] 조회 결과를 `history` 리스트로 변환하여 Python 서버에 전달
- [ ] `MedicalController`에서 session ID 관리 (X-Session-Id 헤더 또는 자동 생성)

#### Step 4: 검증
- [ ] "무릎이 아파요" → "아까 말한 병원에서 뭘 검사하나요?" 연속 질문
- [ ] 2번째 응답에서 "정형외과" 문맥 유지 확인
- [ ] session_id 없는 요청 → 기존과 동일하게 동작 (하위 호환)

**Workflow**:
```
스키마(Step1) → Python(Step2) → Spring Boot(Step3) → 검증(Step4)
```

---

### Task 18: 구조화 로깅 + 메트릭 수집

> 개선항목: 6.2, 6.3 | 난이도: 중간 | 영향 파일: 전체 Python 모듈

**목표**: JSON 로깅과 기본 메트릭 수집을 도입한다.

#### Step 1: 로깅 전환
- [ ] `requirements.txt`에 `structlog>=24.0.0` 추가
- [ ] `logging_config.py` 신규 — structlog + JSON formatter 설정
- [ ] 기존 `logging.getLogger` → `structlog.get_logger()` 전환
- [ ] 주요 로그에 구조화 필드 추가 (query_length, latency_ms, vector_hits 등)

#### Step 2: Metrics 클래스 구현
- [ ] `metrics.py` 신규 — dataclass 기반 카운터
- [ ] 수집 항목: total_requests, success_count, error_count, avg_latency_ms, vector_hit_rate
- [ ] 스레드 안전: `threading.Lock` 사용

#### Step 3: 미들웨어 적용
- [ ] FastAPI 미들웨어로 요청/응답 시간 자동 측정
- [ ] 각 엔드포인트에서 `metrics.record()` 호출

#### Step 4: /metrics 엔드포인트
- [ ] `GET /metrics` — 현재 메트릭 JSON 반환
- [ ] (선택) Prometheus exposition format

#### Step 5: 검증
- [ ] 서버 로그 출력 → JSON 형식 확인
- [ ] 10회 요청 후 `/metrics` → 수치 정확성 확인

**Workflow**:
```
로깅(Step1) → 메트릭 클래스(Step2) → 미들웨어(Step3) → API(Step4) → 검증(Step5)
```

---

### Task 19: 증분 인덱싱

> 개선항목: 2.4 | 난이도: 중간 | 영향 파일: `index_medical_data.py`

**목표**: 전체 재인덱싱 대신 변경분만 처리한다.

#### Step 1: 타임스탬프 관리
- [ ] 인덱싱 메타 파일 `python-llm/.index_meta.json` 저장
  - `{ "last_indexed_at": "2026-03-12T10:00:00", "total_docs": 150 }`
- [ ] 인덱싱 완료 시 자동 갱신

#### Step 2: 증분 조회 함수 구현
- [ ] `fetch_medical_qa_since(settings, since: datetime)` — `WHERE created_at > %s`
- [ ] `fetch_medical_content_since(settings, since: datetime)` — 동일
- [ ] Entity에 `updated_at` 컬럼이 없다면 `created_at`만 사용

#### Step 3: main() 수정
- [ ] `--full` 옵션: 전체 재인덱싱 (기존 동작)
- [ ] 기본: 증분 인덱싱 (`.index_meta.json` 기준)
- [ ] `--full` 없이 메타파일 없으면 자동으로 전체 수행

#### Step 4: 검증
- [ ] 전체 인덱싱 1회 실행 → 메타파일 생성 확인
- [ ] 새 데이터 INSERT → 증분 실행 → 추가분만 인덱싱 확인
- [ ] `--full` 옵션 → 전체 재인덱싱 확인

**Workflow**:
```
메타 관리(Step1) → 증분 조회(Step2) → CLI 수정(Step3) → 검증(Step4)
```

---

## Phase 4 — 장기 (Task 20~22)

---

### Task 20: 오타 사전 DB화 + 자동 확장

> 개선항목: 4.3 | 난이도: 높음 | 영향 파일: `typo_corrector.py`, Spring Boot Entity/Repository, DB 스키마

**목표**: 오타 교정 사전을 DB에서 관리하고, 사용 빈도를 추적한다.

#### Step 1: DB 스키마
- [ ] `typo_dictionary` 테이블 생성 (id, typo, correct_term, category, hit_count, created_at)
- [ ] 초기 데이터: 현재 `MEDICAL_TYPO_MAP`의 오타 항목을 INSERT
- [ ] `medical_qa`에서 updated_at 컬럼이 없는 경우 ALTER TABLE 추가

#### Step 2: Python 측 수정
- [ ] `typo_corrector.py` — 기동 시 DB에서 사전 로드 → 메모리 캐시
- [ ] 주기적 리로드 (10분 간격) 또는 `/typo/reload` API
- [ ] 교정 발생 시 `hit_count` 비동기 업데이트

#### Step 3: Spring Boot 관리 API (선택)
- [ ] `TypoDictionary` Entity + Repository
- [ ] CRUD API: `GET/POST/PUT/DELETE /api/admin/typos`
- [ ] 관리 페이지 (Mustache 템플릿)

#### Step 4: 자동 발견 배치 (선택)
- [ ] 사용자 질문 로그에서 벡터 검색 miss + 오타 패턴 후보 추출
- [ ] 관리자 승인 후 사전 등록

#### Step 5: 검증
- [ ] DB에서 로드한 사전으로 기존 오타 교정 동작 확인
- [ ] 새 오타 DB 등록 → 리로드 → 교정 동작 확인
- [ ] hit_count 증가 확인

**Workflow**:
```
스키마(Step1) → Python(Step2) → Spring Boot(Step3, 선택) → 배치(Step4, 선택) → 검증(Step5)
```

---

### Task 21: 응답 품질 피드백 루프

> 개선항목: 4.4 | 난이도: 높음 | 영향 파일: Python `app.py`, Spring Boot Entity/Controller, 프론트엔드

**목표**: 사용자가 LLM 응답에 대한 피드백을 제출하고, 이를 품질 개선에 활용한다.

#### Step 1: DB 스키마 확장
- [ ] `medical_history` 테이블에 `feedback_score INT NULL`, `feedback_comment TEXT NULL` 추가
- [ ] 마이그레이션 SQL 작성

#### Step 2: Python 피드백 API
- [ ] `POST /feedback` — `{ history_id, score (1-5), comment }`
- [ ] score 유효성 검증
- [ ] DB 업데이트 (aiomysql)

#### Step 3: Spring Boot 피드백 전달
- [ ] `POST /api/medical/feedback` — 프론트엔드 → Spring Boot → Python
- [ ] 또는 Spring Boot에서 직접 DB 업데이트

#### Step 4: 프론트엔드 UI
- [ ] `medical.html` 응답 하단에 좋아요/나빠요 버튼 추가
- [ ] 선택 시 fetch로 피드백 API 호출
- [ ] 제출 후 "감사합니다" 피드백

#### Step 5: 분석 대시보드 (선택)
- [ ] 낮은 점수(1-2) 응답 목록 조회 API
- [ ] 주기적 리포트: 평균 점수, 낮은 점수 비율, 자주 실패하는 질문 패턴

#### Step 6: 검증
- [ ] 상담 후 피드백 제출 → DB 저장 확인
- [ ] 피드백 조회 API → 데이터 정확성 확인

**Workflow**:
```
스키마(Step1) → Python API(Step2) → Spring Boot(Step3) → 프론트엔드(Step4) → 대시보드(Step5, 선택) → 검증(Step6)
```

---

### Task 22: 의존성 핀닝 + CI

> 개선항목: 5.3 | 난이도: 중간 | 영향 파일: `requirements.txt`, 신규 `requirements-lock.txt`

**목표**: 재현 가능한 빌드 환경을 구축한다.

#### Step 1: 현재 버전 확인
- [ ] `.venv` 환경에서 `pip freeze` 실행
- [ ] 주요 패키지 실제 설치 버전 확인 (fastapi, chromadb, torch 등)

#### Step 2: requirements.txt 호환 릴리즈로 전환
- [ ] `>=` → `~=` (호환 릴리즈) 또는 `>=X.Y,<X.Z` (상한 지정)
- [ ] chromadb 버전을 Docker 이미지(1.5.4)와 맞춤: `chromadb~=1.5.0`

#### Step 3: Lock 파일 생성
- [ ] `pip freeze > requirements-lock.txt` (정확한 버전)
- [ ] `.gitignore`에 `.venv/` 확인 (이미 있을 것)
- [ ] Dockerfile에서 `requirements-lock.txt` 사용하도록 수정

#### Step 4: CI 설정 (선택)
- [ ] GitHub Actions 워크플로우 또는 스크립트
- [ ] `pip install -r requirements-lock.txt` → `pytest` 실행

#### Step 5: 검증
- [ ] 깨끗한 venv에서 `pip install -r requirements-lock.txt` → 설치 성공
- [ ] Docker 빌드 → 서버 정상 기동

**Workflow**:
```
버전 확인(Step1) → 핀닝(Step2) → Lock(Step3) → CI(Step4, 선택) → 검증(Step5)
```

---

## 의존 관계 다이어그램

```
Phase 1 (독립 실행 가능)
  Task 1 ──→ Task 2 (공유 클라이언트 → 중복 제거)
  Task 3 (독립)
  Task 4 (독립)
  Task 5 (독립)
  Task 6 (독립)

Phase 2
  Task 1 ──→ Task 7 (공유 클라이언트 → 임베딩 캐시에서도 활용)
  Task 8 (독립, but 인덱싱 재실행 필요)
  Task 9 ──→ Task 10 (프롬프트 외부화 → Few-shot 추가)
  Task 11 ──→ Task 1 (Circuit Breaker는 공유 클라이언트에 적용)
  Task 12 (독립)
  Task 13 (독립)

Phase 3
  Task 7 ──→ Task 14 (캐시 → Re-ranking에서 임베딩 재사용)
  Task 15 ──→ Task 14 (쿼리 확장 후 Re-ranking 적용)
  Task 16 ──→ Task 8 (청킹 → 컬렉션 분리 후 재인덱싱)
  Task 17 (독립, 단 Spring Boot 동시 수정 필요)
  Task 18 (독립)
  Task 19 ──→ Task 16 (증분 인덱싱은 청킹 전략 이후 적용)

Phase 4
  Task 20 (독립, DB 스키마 변경)
  Task 21 ──→ Task 17 (피드백은 세션 기반 대화 이후가 자연스러움)
  Task 22 (독립)
```

### 병렬 실행 가능 그룹

| 그룹 | Task | 비고 |
|------|------|------|
| Phase 1-A | Task 3, 4, 5, 6 | 서로 독립, 동시 작업 가능 |
| Phase 1-B | Task 1 → Task 2 | 순차 |
| Phase 2-A | Task 7, 12, 13 | 서로 독립 |
| Phase 2-B | Task 9 → Task 10 | 순차 |
| Phase 2-C | Task 8, 11 | 서로 독립 |
| Phase 3-A | Task 15, 17, 18 | 서로 독립 |
| Phase 3-B | Task 16 → Task 19 | 순차 |
| Phase 4 | Task 20, 21, 22 | 서로 독립 (21은 17 선행 권장) |
