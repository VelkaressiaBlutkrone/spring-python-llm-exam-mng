# Ollama → vLLM 전환 기획서 — Task / Step / Workflow

> 작성일: 2026-03-18
> 기반 문서: vLLM 접속 테스트 결과 + 현행 코드 분석
> 총 4개 Task, 10개 검증 항목

---

## 개요

| 항목          | 내용                                                                    |
| ------------- | ----------------------------------------------------------------------- |
| 목적          | LLM 추론 백엔드를 Ollama에서 vLLM으로 전환하여 추론 성능 및 처리량 향상 |
| 대상 서버     | `192.168.0.22:8000` (WSL2 환경)                                         |
| vLLM 버전     | 0.17.1                                                                  |
| 모델          | `qwen2.5-7b` (Qwen/Qwen2.5-7B-Instruct-AWQ, 4bit 양자화)              |
| max_model_len | 4096                                                                    |

### 접속 테스트 결과

| 테스트        | 엔드포인트                           | 결과                         |
| ------------- | ------------------------------------ | ---------------------------- |
| 모델 목록     | `GET /v1/models`                     | ✅ 성공 — `qwen2.5-7b` 확인  |
| 버전 확인     | `GET /version`                       | ✅ 성공 — `0.17.1`           |
| Chat 추론     | `POST /v1/chat/completions`          | ✅ 성공 — 정상 응답          |
| Chat 스트리밍 | `POST /v1/chat/completions` (stream) | ✅ 성공 — SSE 토큰 단위 수신 |
| Text 생성     | `POST /v1/completions`               | ✅ 성공 — 정상 응답          |
| 헬스체크      | `GET /health`                        | ✅ 성공 — 200 OK             |

### API 매핑 (Ollama → vLLM)

| 기능        | Ollama API              | vLLM API (OpenAI 호환)              |
| ----------- | ----------------------- | ----------------------------------- |
| 텍스트 생성 | `POST /api/generate`    | `POST /v1/completions`              |
| 대화형 생성 | `POST /api/chat`        | `POST /v1/chat/completions`         |
| 스트리밍    | NDJSON (`stream: true`) | SSE (`stream: true`)                |
| 헬스체크    | `GET /api/tags`         | `GET /health` 또는 `GET /v1/models` |
| 모델 목록   | `GET /api/tags`         | `GET /v1/models`                    |

### 요청/응답 형식 변환

**요청**: `options.num_predict` → `max_tokens` (최상위), `options` 평탄화
**응답**: `result.message.content` → `result.choices[0].message.content`
**스트리밍**: NDJSON → SSE (`data:` 접두사, `[DONE]` 종료)

### 변경 범위

```
[Spring Boot] → /infer/* → [Python-LLM] → /v1/chat/completions → [vLLM]
                (변경 없음)   (내부 전환)                           (신규)
```

- **Spring Boot**: 변경 없음 (Python-LLM의 `/infer/*` 인터페이스 유지)
- **Python-LLM**: `vllm_service.py` 신규 + `config.py`/`app.py` 수정
- **임베딩**: Ollama 임베딩(`nomic-embed-text`) 유지 (추론만 vLLM 전환)

---

## Task 1: vLLM 서비스 모듈 작성

> 난이도: 높음 | 영향 파일: 신규 `python-llm/vllm_service.py`

**목표**: Ollama 서비스와 동일한 인터페이스로 vLLM OpenAI 호환 API를 호출하는 모듈을 작성한다.

### Step 1: vllm_service.py 핵심 함수 작성

- [x] `generate_with_vllm()` — `POST /v1/completions` 호출
  - Ollama `options.num_predict` → vLLM `max_tokens`
  - 응답: `result["choices"][0]["text"]`
- [x] `chat_with_vllm()` — `POST /v1/chat/completions` 호출
  - 파라미터 평탄화 (temperature, max_tokens, top_p, stop 최상위)
  - 응답: `result["choices"][0]["message"]["content"]`
- [x] `chat_with_vllm_stream()` — SSE 스트리밍 파싱
  - `data: ` 접두사 제거 → JSON 파싱
  - `choices[0].delta.content` 에서 토큰 추출
  - `[DONE]` 또는 `finish_reason != null` 시 종료
- [x] Circuit Breaker 기존 `_breaker` 인스턴스 재사용

### Step 2: 유틸리티 함수 작성

- [x] `check_vllm_health()` — `GET /health` → bool 반환
- [x] `list_models()` — `GET /v1/models` → 모델명 리스트 반환

### Step 3: 단위 검증

- [x] `chat_with_vllm()` 직접 호출 → 정상 응답 확인
- [x] `chat_with_vllm_stream()` 호출 → 토큰 단위 수신 확인
- [x] `check_vllm_health()` → True 반환 확인

**Workflow**:

```
핵심 함수(Step1) → 유틸리티(Step2) → 검증(Step3)
```

---

## Task 2: config.py 설정 확장

> 난이도: 낮음 | 영향 파일: `python-llm/config.py`

**목표**: vLLM 관련 설정을 추가하고, `llm_backend` 기본값을 `vllm`으로 변경한다.

### Step 1: vLLM 설정 필드 추가

- [x] `vllm_base_url: str = "http://192.168.0.22:8000"` 추가 (이후 기본값 `localhost:8000`으로 변경, 환경변수로 주입)
- [x] `vllm_model: str = "qwen2.5-7b"` 추가
- [x] `llm_backend` 기본값을 `"vllm"`으로 변경, 설명에 `"huggingface | ollama | vllm"` 명시

### Step 2: 기존 설정 유지 확인

- [x] Ollama 설정(`ollama_base_url`, `ollama_model`, `ollama_embed_model`) 그대로 유지 (폴백 + 임베딩용)
- [x] `llm_backend` 필드 description 업데이트

### Step 3: 검증

- [x] `LLM_BACKEND=vllm` 환경변수 → `settings.llm_backend == "vllm"` 확인
- [x] `LLM_BACKEND=ollama` 환경변수 → 기존 Ollama 설정 정상 로드 확인

**Workflow**:

```
필드 추가(Step1) → 기존 유지(Step2) → 검증(Step3)
```

---

## Task 3: app.py 라우팅 전환

> 난이도: 중간 | 영향 파일: `python-llm/app.py`
> 선행: Task 1, Task 2

**목표**: `llm_backend` 설정에 따라 vLLM 또는 Ollama를 선택적으로 호출하도록 분기를 추가한다.

### Step 1: /infer 엔드포인트 분기

- [x] `infer()` — `llm_backend == "vllm"` 시 `generate_with_vllm()` 호출
- [x] 기존 `ollama` / `huggingface` 분기 유지

### Step 2: /infer/medical 엔드포인트 분기

- [x] `infer_medical()` — `llm_backend == "vllm"` 시 `chat_with_vllm()` 호출
- [x] 기존 Ollama Chat 호출 분기 유지

### Step 3: /infer/medical/stream 엔드포인트 분기

- [x] `infer_medical_stream()` — `llm_backend == "vllm"` 시 `chat_with_vllm_stream()` 호출
- [x] SSE 생성 로직에서 vLLM 스트리밍 형식 처리
  - vLLM: `item["token"]` (vllm_service에서 통일된 형식으로 반환)

### Step 4: /infer/rule 엔드포인트 분기

- [x] `infer_rule()` — `llm_backend == "vllm"` 시 `chat_with_vllm()` 호출

### Step 5: /health 헬스체크 수정

- [x] `llm_backend == "vllm"` 시 `check_vllm_health()` 호출
- [x] Circuit Breaker 상태는 `vllm_service._breaker` 참조

### Step 6: 통합 검증

- [x] `LLM_BACKEND=vllm` 상태에서 4개 엔드포인트 모두 정상 동작
- [ ] `LLM_BACKEND=ollama`로 변경 → 기존과 동일하게 동작 (롤백 확인)

**Workflow**:

```
/infer(Step1) → /infer/medical(Step2) → /stream(Step3) → /rule(Step4) → /health(Step5) → 통합 검증(Step6)
```

---

## Task 4: docker-compose.yml 환경변수 업데이트

> 난이도: 낮음 | 영향 파일: `docker-compose.yml`
> 선행: Task 1~3

**목표**: Docker 환경에서 vLLM 백엔드를 사용하도록 환경변수를 업데이트한다.

### Step 1: python-llm 서비스 환경변수 수정

- [x] `LLM_BACKEND=vllm` 으로 변경
- [x] `VLLM_BASE_URL=http://192.168.0.22:8000` 추가
- [x] `VLLM_MODEL=qwen2.5-7b` 추가
- [x] 기존 `OLLAMA_BASE_URL` 유지 (임베딩 + 폴백용)

### Step 2: 검증

- [ ] Docker Compose 환경에서 전체 스택 기동 확인
- [ ] python-llm 컨테이너에서 vLLM 서버 접근 가능 확인

**Workflow**:

```
환경변수 수정(Step1) → 검증(Step2)
```

---

## 의존 관계

```
Task 1 (vllm_service.py) ─┐
Task 2 (config.py)        ├→ Task 3 (app.py 라우팅) → Task 4 (docker-compose)
                          ┘
```

- Task 1, 2는 병렬 작업 가능
- Task 3은 Task 1, 2 완료 후 진행
- Task 4는 Task 3 완료 후 진행

---

## 롤백 전략

`LLM_BACKEND` 환경변수로 즉시 전환:

```bash
LLM_BACKEND=ollama   # vLLM 장애 시 Ollama로 롤백
LLM_BACKEND=vllm     # 정상 시 vLLM 사용
```

`ollama_service.py` 삭제하지 않고 유지 → 언제든 롤백 가능

---

## 주의사항

- **네트워크**: Docker 컨테이너에서 `192.168.0.22:8000` 접근 가능 여부 확인
- **max_model_len**: 4096 토큰 제한 — 시스템 프롬프트 + 컨텍스트 + 이력 + 질문 범위 내 확인
- **모델명**: Ollama `qwen2.5:7b` ≠ vLLM `qwen2.5-7b` (설정으로 분리)
- **임베딩**: Ollama `nomic-embed-text` 유지 (vLLM 전환 대상 아님)
