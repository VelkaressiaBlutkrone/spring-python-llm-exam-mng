# Python-LLM 코드 리뷰 리포트

> 리뷰 일시: 2026-03-18
> 대상: `python-llm/` 전체 (28개 파일, 약 3,949 LOC)
> 검사 항목: RULE_PYTHON.md 준수, 버그, 보안, 코드 일관성, 테스트 커버리지

---

## 요약

| 심각도   | 건수 | 주요 항목                                            |
| -------- | ---- | ---------------------------------------------------- |
| CRITICAL | 1    | metrics.py 데드락                                    |
| HIGH     | 7    | 입력 전처리 누락, 하드코딩 비밀번호, CORS, 경쟁 상태 |
| MEDIUM   | 12   | 예외 삼킴, 데이터 손실, 미사용 기능, 보안 노출       |
| LOW      | 8    | 미사용 설정, import 비일관, 테스트 커버리지 부족     |

---

## CRITICAL

### 1. `metrics.py:56-65` — `to_dict()` 데드락

`to_dict()`가 `self._lock`을 잡은 상태에서 `self.avg_latency_ms`, `self.success_rate` 프로퍼티를 호출하는데, 이 프로퍼티들도 동일한 non-reentrant `threading.Lock`을 다시 잡으려 함. **`/metrics` 엔드포인트 호출 시 영구 블락**.

```python
def to_dict(self) -> dict:
    with self._lock:                          # lock 획득
        return {
            "avg_latency_ms": self.avg_latency_ms,  # 내부에서 같은 lock 재획득 시도 → 데드락
        }
```

**수정**: `to_dict()` 내에서 `_lock` 없이 직접 `self._total_latency_ms / self._total_requests` 계산하거나, `Lock`을 `RLock`으로 교체.

---

## HIGH

### 2. `medical_context_service.py:20-36` — `get_pool()` 이중 초기화 경쟁 상태

`async def get_pool()`에서 `if _pool is None` 체크 후 `await create_pool()` 하는 사이에 다른 코루틴이 동일 체크를 통과 가능. 두 번째 pool이 첫 번째를 덮어쓰며, 첫 번째 pool은 누수됨.

**수정**: `asyncio.Lock`으로 보호하거나 lazy init 패턴을 개선.

### 3. `schemas.py:12` — `query` max_length=2048 (RULE_PYTHON.md 위반)

RULE_PYTHON.md는 "1~4096자"를 명시하지만 스키마는 2048자로 제한. 2049~4096자 입력이 422 에러로 거부됨.

**수정**: `max_length=4096`으로 변경.

### 4. `app.py:240-270` + `ollama_service.py` + `vllm_service.py` — 입력 전처리 누락

`/infer`의 vLLM/Ollama 경로, `/infer/medical`, `/infer/rule` 모두 `_preprocess_query()` (길이 제한 + 공백 정규화)를 적용하지 않음. HuggingFace 경로만 적용됨.

**수정**: 모든 엔드포인트 진입부에서 공통 전처리 적용.

### 5. `config.py:60` + `import_medical_data.py:28` — 하드코딩 비밀번호

`mysql_password` 기본값 `"rootpassword"`, `import_medical_data.py`의 `os.getenv("MYSQL_PASSWORD", "rootpassword")`. 환경변수 미설정 시 약한 기본 비밀번호로 DB 접속.

**수정**: 기본값 제거, 필수 환경변수로 전환.

### 6. `app.py:83-89` — CORS 과도한 허용

`allow_credentials=True` + `allow_methods=["*"]` + `allow_headers=["*"]` 조합. CSRF 및 교차 출처 데이터 유출 위험 증가.

**수정**: `allow_methods=["GET", "POST"]`, `allow_headers=["Content-Type"]`로 제한.

### 7. `ollama_service.py:209-225` — 스트리밍 에러 핸들링 누락

`chat_with_ollama_stream`의 `_stream()` 내부에 `try/except` 없음. 연결 끊김 시 Circuit Breaker 실패 기록 없이 raw 예외 전파. `vllm_service.py`는 정상 처리됨.

**수정**: `vllm_service.py`와 동일하게 `ConnectError`/`ReadTimeout` 핸들링 추가.

### 8. `config.py:43` — 하드코딩 사설 IP 기본값

`vllm_base_url` 기본값이 `"http://192.168.0.22:8000"` (특정 개발 환경 IP). 다른 환경 배포 시 의도치 않게 잘못된 서버 연결.

**수정**: 기본값을 `"http://localhost:8000"`으로 변경하거나 필수값으로 전환.

---

## MEDIUM

### 9. `app.py:511-513, 534-537` — 피드백 엔드포인트 예외 삼킴

`/feedback`와 `/feedback/stats`에서 DB 예외 시 HTTP 200 + `status="error"` 반환. Spring Boot 클라이언트가 상태 코드로 실패 감지 불가.

**수정**: `raise HTTPException(status_code=500)` 또는 적절한 에러 응답.

### 10. `chunker.py:36-39` — 마지막 청크 병합 시 데이터 손실

`chunks[-1] = chunks[-1] + chunk[overlap:]`에서 `overlap` 바이트가 이중 제거됨. `start = end - overlap`으로 이미 오버랩을 반영했는데 `chunk[overlap:]`로 다시 건너뜀.

**수정**: `chunk[overlap:]` → `chunk` (슬라이싱 제거).

### 11. `typo_corrector.py:158-207` — `_flush_hit_counts()` 미호출

`correct_typos()`가 `_hit_queue`에 적중 데이터를 쌓지만, `_flush_hit_counts()`를 호출하는 코드가 어디에도 없음. hit_count DB 업데이트 불가, 큐 무한 증가.

**수정**: 백그라운드 태스크로 스케줄링하거나 기능 제거.

### 12. `app.py:192-204` — `OSError` 핸들러가 `ConnectionError` 핸들러를 섀도잉

Python 3에서 `ConnectionError`는 `OSError`의 하위 클래스. Starlette의 핸들러 등록 순서에 따라 `ConnectionError` 발생 시 `OSError` 핸들러가 먼저 매칭될 수 있음 → 잘못된 에러 메시지 반환.

**수정**: `OSError` 핸들러 내에서 `isinstance(exc, ConnectionError)` 분기 추가, 또는 등록 순서 조정.

### 13. `query_expander.py:30` — 백엔드 무관하게 Ollama 고정 사용

`llm_backend=vllm` 설정이어도 쿼리 확장은 항상 `from ollama_service import generate_with_ollama` 호출. 백엔드 혼용 발생.

**수정**: `llm_backend` 설정에 따라 vLLM/Ollama 분기.

### 14. `app.py:322-339, 380-383, 463-480` — `huggingface` 백엔드 분기 누락

`/infer/medical`, `/infer/medical/stream`, `/infer/rule`에 `vllm`/`else(ollama)` 분기만 있음. `llm_backend=huggingface` 시 Ollama 호출 시도.

### 15. `app.py:175, 189, 537` — 내부 예외 메시지 클라이언트 노출

`str(exc)` 직접 반환으로 MySQL 쿼리 구조, 서버 URL, 모델 경로 등 내부 정보 유출.

**수정**: 로그에는 전체 예외 기록, 클라이언트에는 일반 메시지만 반환.

### 16. `app.py:98, 104-109` — 관리 엔드포인트 Rate Limiting/인증 없음

`GET /metrics`, `POST /typo/reload`, `GET /feedback/stats`에 Rate Limiting 없음. `/typo/reload` 반복 호출로 DB 부하 유발 가능.

### 17. `circuit_breaker.py:26-39` — HALF_OPEN 상태에서 다수 요청 동시 통과

`state` 프로퍼티와 `can_execute()` 간 TOCTOU 경쟁. HALF_OPEN에서 단일 프로브만 허용해야 하지만 동시 요청 모두 통과.

### 18. `index_rule_data.py:62-66` — 기존 규칙도 "inserted"로 처리

이미 존재하는 규칙이 `inserted` 리스트에 포함되어 매 실행마다 전체 임베딩 재계산.

### 19. `schemas.py:18` — `history` 필드 크기 제한 없음

`list[dict]`에 길이/항목 크기 제한 없음. 대량 히스토리 전송으로 메모리 과다 사용 가능.

**수정**: `max_length=20` + 개별 메시지 `content` 길이 제한 추가.

### 20. `prompt_loader.py:12-20` — 경로 순회 위험

`name` 파라미터 검증 없이 `Path(f"{name}.txt")` 생성. 현재는 하드코딩 호출만 있지만 향후 사용자 입력 연결 시 파일 읽기 취약점.

**수정**: 허용 프롬프트명 화이트리스트 추가.

---

## LOW

### 21. `config.py:22` — `llm_model` 기본값이 Ollama 포맷

`llm_model` 설명은 "Hugging Face 모델명"이지만 기본값 `"qwen2.5:7b"`는 Ollama 포맷. HuggingFace 사용 시 모델 로딩 실패.

### 22. `config.py:71` — `openai_api_key` 미사용

코드베이스 어디에서도 참조하지 않는 설정 필드.

### 23. `config.py:54` — `use_reranking` 설정 무시

`medical_context_service.py`에서 `use_reranking` 체크 없이 reranker 호출.

### 24. `app.py:25` — 미사용 top-level import

`from llm_service import generate`가 모듈 레벨에서 import되지만, 실제 사용은 함수 내부 lazy import.

### 25. `app.py:225-280` — `/infer` 엔드포인트 metrics 미기록

`/infer/medical`과 `/infer/rule`은 `metrics.record_request()` 호출하지만, `/infer`는 호출하지 않음.

### 26. `schemas.py:40` — `FeedbackRequest.endpoint` 패턴 부정확

`"^(medical|rule|infer)$"` 패턴은 `"infer/medical"` 같은 실제 경로명을 거부함.

### 27. `ollama_service.py:190` — 함수 내 `import json` (비일관)

`vllm_service.py`는 모듈 레벨 import, `ollama_service.py`는 함수 내 import.

### 28. 테스트 커버리지 부족

`vllm_service.py`, `ollama_service.py`, `circuit_breaker.py`, `rule_context_service.py`, `metrics.py` 등 핵심 모듈에 테스트 없음. 9개 엔드포인트 중 3개만 테스트됨.

---

## 테스트 커버리지 현황

| 모듈                      | 테스트 유무 | 우선순위 |
| ------------------------- | ----------- | -------- |
| `vllm_service.py`         | 없음        | P0       |
| `circuit_breaker.py`      | 없음        | P0       |
| `metrics.py`              | 없음        | P1       |
| `ollama_service.py`       | 없음        | P1       |
| `rule_context_service.py` | 없음        | P1       |
| `embedding_service.py`    | 없음        | P2       |
| `config.py`               | 없음        | P2       |
| `response_cleaner.py`     | 있음 (양호) | —        |
| `typo_corrector.py`       | 있음 (양호) | —        |
| `schemas.py`              | 있음 (부분) | P2       |

---

## 우선 수정 권장 순서

| 순서 | 항목                                          | 심각도   |
| ---- | --------------------------------------------- | -------- |
| 1    | `metrics.py` 데드락 수정 (Lock → RLock)       | CRITICAL |
| 2    | `get_pool()` 경쟁 상태 수정                   | HIGH     |
| 3    | 전 엔드포인트 입력 전처리 적용                | HIGH     |
| 4    | 하드코딩 비밀번호 제거                        | HIGH     |
| 5    | CORS 설정 제한                                | HIGH     |
| 6    | `vllm_base_url` 기본값 변경                   | HIGH     |
| 7    | `ollama_service.py` 스트리밍 에러 핸들링 추가 | HIGH     |
| 8    | 피드백 엔드포인트 에러 응답 수정              | MEDIUM   |
| 9    | `chunker.py` 데이터 손실 수정                 | MEDIUM   |
| 10   | 예외 메시지 클라이언트 노출 제거              | MEDIUM   |
