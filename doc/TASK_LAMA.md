# WSL2 Ollama 실제 동작 테스트 기록

> 테스트 일자: 2026-03-06
> 환경: Windows 11 Pro + WSL2 Ollama, Python 3.12.10
> 참조: [SETUP_OLLAMA.md](./SETUP_OLLAMA.md)

---

## 1. 환경 구성

### 1.1 시스템 환경

| 항목        | 값                                     |
| ----------- | -------------------------------------- |
| OS          | Windows 11 Pro 10.0.26200              |
| Ollama 위치 | WSL2 (localhost:11434)                 |
| Python      | 3.12.10 (venv: `python-llm/.venv`)     |
| torch       | 2.6.0+cpu (CPU 전용)                   |
| 설치 모델   | `llama3:8b`, `gemma3:4b`, `qwen2.5:7b` |

### 1.2 Ollama 접근 방식

WSL2에서 실행 중인 Ollama 서버에 Windows 호스트에서 `localhost:11434`로 접근합니다.
WSL2의 네트워크 미러링 또는 포트 포워딩이 설정되어 있어야 합니다.

```text
[Windows Host]
    ↓ curl http://localhost:11434
[WSL2 - Ollama 서버]
    └── llama3:8b (Q4_0, 8.0B params, ~4.3GB)
```

---

## 2. API 테스트 결과

### 2.1 모델 목록 조회 (`GET /api/tags`)

```bash
curl -s http://localhost:11434/api/tags
```

**응답:**

```json
{
  "models": [
    {
      "name": "llama3:8b",
      "model": "llama3:8b",
      "size": 4661224676,
      "details": {
        "format": "gguf",
        "family": "llama",
        "parameter_size": "8.0B",
        "quantization_level": "Q4_0"
      }
    }
  ]
}
```

**결과: 정상** — llama3:8b 모델 확인

---

### 2.2 텍스트 생성 (`POST /api/generate`)

#### 테스트 1: 기본 영문 생성

```bash
curl -s http://localhost:11434/api/generate \
  -d '{"model":"llama3:8b","prompt":"Hello, respond in one sentence.","stream":false}'
```

**응답:**

| 항목               | 값                                       |
| ------------------ | ---------------------------------------- |
| response           | `"I'm excited to be chatting with you!"` |
| total_duration     | 3,083ms (모델 로딩 2,929ms 포함)         |
| prompt_eval_count  | 17 tokens                                |
| eval_count         | 10 tokens                                |
| eval_duration      | 121ms                                    |
| **토큰 생성 속도** | **~82 tok/s**                            |

**결과: 정상** — 영문 생성 우수, 첫 요청 시 모델 로딩 ~3초 소요

#### 테스트 2: 옵션 지정 (temperature, num_predict)

```bash
curl -s http://localhost:11434/api/generate \
  -d '{"model":"llama3:8b","prompt":"What is the capital of South Korea? Answer in one sentence.","stream":false,"options":{"temperature":0.3,"num_predict":50}}'
```

**응답:**

| 항목               | 값                                       |
| ------------------ | ---------------------------------------- |
| response           | `"The capital of South Korea is Seoul."` |
| total_duration     | 291ms                                    |
| prompt_eval_count  | 23 tokens                                |
| eval_count         | 9 tokens                                 |
| eval_duration      | 155ms                                    |
| **토큰 생성 속도** | **~58 tok/s**                            |

**결과: 정상** — 모델 캐시 상태에서 빠른 응답 (291ms)

---

### 2.3 대화형 생성 (`POST /api/chat`)

#### 테스트 3: 한국어 입력 (시스템 프롬프트 없음)

```bash
curl -s http://localhost:11434/api/chat \
  -d '{"model":"llama3:8b","messages":[{"role":"user","content":"안녕하세요, 한국어로 한 문장만 답변해주세요."}],"stream":false}'
```

**응답:**

| 항목               | 값                            |
| ------------------ | ----------------------------- |
| content            | 영문으로 응답 (한국어 미인식) |
| total_duration     | 1,427ms                       |
| eval_count         | 101 tokens                    |
| **토큰 생성 속도** | **~78 tok/s**                 |

**결과: 한국어 미지원** — llama3:8b는 한국어 입력을 이해하지 못하고 영문으로 응답

#### 테스트 4: 한국어 시스템 프롬프트 지정

```bash
curl -s http://localhost:11434/api/chat \
  -d '{"model":"llama3:8b","messages":[{"role":"system","content":"You are a helpful assistant. Always respond in Korean."},{"role":"user","content":"두통이 심한데 어느 진료과를 가야 하나요?"}],"stream":false}'
```

**응답:**

| 항목           | 값                                    |
| -------------- | ------------------------------------- |
| content        | 깨진 문자 출력 (유니코드 인코딩 오류) |
| total_duration | 710ms                                 |
| eval_count     | 21 tokens                             |

**결과: 실패** — llama3:8b는 한국어 생성 능력 부재, 깨진 문자 출력

---

## 3. 성능 요약

### 3.1 llama3:8b (Q4_0) on WSL2 CPU

| 측정 항목           | 값                     |
| ------------------- | ---------------------- |
| 모델 크기           | 4.3GB (Q4_0 양자화)    |
| 첫 요청 로딩 시간   | ~3초                   |
| 캐시 상태 응답 시간 | 150~300ms (짧은 응답)  |
| 토큰 생성 속도      | 58~82 tok/s            |
| 프롬프트 평가 속도  | ~600 tok/s             |
| 한국어 지원         | **미지원** (영문 전용) |

### 3.2 응답 시간 분석

```text
[첫 요청]
  모델 로딩: ~2,900ms  ← 디스크→메모리 로드
  프롬프트 평가: ~27ms
  토큰 생성: ~122ms
  ─────────────────
  합계: ~3,083ms

[후속 요청 (캐시)]
  모델 로딩: ~80ms     ← 메모리 캐시 히트
  프롬프트 평가: ~26ms
  토큰 생성: ~155ms
  ─────────────────
  합계: ~291ms
```

---

## 4. 한국어 지원 테스트

### 4.1 모델별 한국어 능력 비교

| 모델             | 한국어 입력 이해 | 한국어 출력       | 비고                  |
| ---------------- | ---------------- | ----------------- | --------------------- |
| `llama3:8b`      | 미인식           | 깨진 문자         | 영문 전용             |
| `gemma3:4b`      | 미인식           | 영문/깨진 문자    | 한국어 토큰 부족      |
| **`qwen2.5:7b`** | **정상**         | **정상 (한국어)** | **한국어 우수, 권장** |

### 4.2 qwen2.5:7b 한국어 테스트 결과

```text
# 입력
"두통이 심한데 어느 진료과를 가야 하나요?"

# 응답 (1,590ms)
"두통이 심한 경우에는 다음과 같은 방법을 추천드립니다:
1. 먼저 가정의학과나 내과를 방문해보세요.
   일반적인 두통은 이곳에서 진단받을 수 있습니다.
2. 만약 두통이 갑작스럽게 시작하거나 매우 심하거나,
   다른 증상(예: 발열, 복시, 균형 문제 등)과 함께 발생한다면,
   즉시 신경과를 방문하거나 응급실을 이용하세요.
3. 장기간 지속되거나 반복되는 두통이 있다면, 신경과 전..."
```

| 측정 항목   | 값                          |
| ----------- | --------------------------- |
| Eval tokens | 88                          |
| Duration    | 1,590ms                     |
| 한국어 품질 | 우수 (자연스러운 의학 안내) |

### 4.3 권장 모델

의학 Q&A 서비스에서 한국어 응답이 필수이므로 `qwen2.5:7b`를 권장합니다:

```bash
# 설치
ollama pull qwen2.5:7b

# .env 설정
LLM_BACKEND=ollama
OLLAMA_MODEL=qwen2.5:7b
```

---

## 5. Python 서버 Ollama 연동 (E2E 테스트 완료)

### 5.1 구현 현황

| 구성 요소                    | 상태                     | 파일                           |
| ---------------------------- | ------------------------ | ------------------------------ |
| Ollama 서버 (WSL2)           | 정상 동작                | —                              |
| qwen2.5:7b 모델              | 한국어 정상              | —                              |
| `ollama_service.py`          | **구현 완료**            | `python-llm/ollama_service.py` |
| `config.py` llm_backend      | **추가 완료**            | `python-llm/config.py`         |
| `/infer` Ollama 연동         | **구현 완료**            | `python-llm/app.py`            |
| `/health` Ollama 상태        | **구현 완료**            | `python-llm/app.py`            |
| `medical_context_service.py` | 미구현 (MySQL 연동 필요) | —                              |

### 5.2 E2E 테스트 결과

#### GET /health (Ollama 모드)

```json
{ "status": "healthy", "llm_backend": "ollama", "ollama_connected": true }
```

#### POST /infer (Ollama 모드, qwen2.5:7b)

```text
# 요청
POST http://localhost:8000/infer
{"query": "두통이 심한데 어느 진료과를 가야 하나요?", "max_length": 128, "temperature": 0.3}

# 응답 (HTTP 200)
{
  "generated_text": "두통이 심한 경우에는 다음과 같은 방법을 추천드립니다:\n\n
    1. 먼저 가정의학과나 내과를 방문해보세요.
       일반적인 두통은 이곳에서 진단받을 수 있습니다.\n\n
    2. 만약 두통이 갑작스럽게 시작하거나 매우 심하거나,
       다른 증상(예: 발열, 복시, 균형 문제 등)과 함께 발생한다면,
       즉시 신경과를 방문하거나 응급실을 이용하세요.\n\n
    3. 장기간 지속되거나 반복되는 두통이 있다면, 신경과 전..."
}
```

**결과: E2E 정상 동작 확인**

- Windows Host → Python FastAPI (localhost:8000) → Ollama WSL2 (localhost:11434) → qwen2.5:7b

### 5.3 서버 실행 방법

```bash
cd python-llm

# Ollama 모드로 실행
LLM_BACKEND=ollama OLLAMA_MODEL=qwen2.5:7b \
  .venv/Scripts/python -m uvicorn app:app --port 8000 --reload

# 또는 .env 파일에 설정 후 실행
.venv/Scripts/python -m uvicorn app:app --port 8000 --reload
```

### 5.4 다음 단계

1. **의학 컨텍스트 서비스 구현** — `medical_context_service.py` (MySQL FULLTEXT 검색)
2. **`/infer/medical` 엔드포인트 추가** — 의학 DB 컨텍스트 + Ollama 추론
3. **Spring Boot 경유 E2E** — Spring Boot → Python FastAPI → Ollama 전 구간 테스트

---

## 6. pytest 테스트 현황

### 6.1 수정 사항

`tests/conftest.py`에서 `sys.modules["llm_service"]`를 mock으로 교체하여
torch import 없이 테스트가 동작하도록 수정했습니다.

**원인**: torch 2.10.0이 Windows에서 DLL access violation 발생 (fatal crash, try/except 불가)
**해결**: torch 2.6.0+cpu 재설치 + conftest에서 llm_service 모듈 레벨 mock

### 6.2 테스트 결과

```text
$ cd python-llm && .venv/Scripts/python -m pytest tests/ -v

tests/test_infer.py::test_infer_success         PASSED
tests/test_infer.py::test_infer_with_params      PASSED
tests/test_infer.py::test_infer_empty_query_rejected PASSED
tests/test_infer.py::test_infer_missing_query    PASSED
tests/test_infer.py::test_root                   PASSED
tests/test_infer.py::test_health                 PASSED

============================== 6 passed in 0.30s ==============================
```

---

## 7. 이슈 및 해결 기록

| #   | 이슈                          | 원인                                             | 해결                                   |
| --- | ----------------------------- | ------------------------------------------------ | -------------------------------------- |
| 1   | pytest collected 0 items      | 프로젝트 루트에서 실행 (python-llm/ 아님)        | `cd python-llm` 후 실행                |
| 2   | torch DLL access violation    | torch 2.10.0 Windows DLL 호환 문제               | torch 2.6.0+cpu로 다운그레이드         |
| 3   | pytest import error (fastapi) | 시스템 Python 사용 (venv 미활성)                 | `.venv/Scripts/python -m pytest` 사용  |
| 4   | conftest mock 불충분          | `LLM_FALLBACK_MOCK=1`로는 torch import 차단 불가 | `sys.modules["llm_service"]` mock 교체 |
| 5   | llama3:8b 한국어 깨짐         | 한국어 학습 데이터 부재                          | gemma3 또는 qwen2.5 모델 권장          |

---

## 8. 문서 이력

| 버전 | 날짜       | 변경 내용                                                                   |
| ---- | ---------- | --------------------------------------------------------------------------- |
| 1.0  | 2026-03-06 | 최초 작성: WSL2 Ollama 실제 동작 테스트 (llama3:8b), pytest 수정 기록       |
| 1.1  | 2026-03-06 | 한국어 모델 비교 (qwen2.5:7b 채택), ollama_service.py 구현, E2E 테스트 완료 |
| 1.1  | 2026-03-06 | 한국어 모델 비교 (qwen2.5:7b 채택), ollama_service.py 구현, E2E 테스트 완료 |
