# Python-LLM 코드 리뷰 리포트

> 리뷰 일시: 2026-03-18
> 대상: `python-llm/` 전체 (28개 파일, 약 3,949 LOC)
> 검사 항목: RULE_PYTHON.md 준수, 버그, 보안, 코드 일관성, 테스트 커버리지
> 수정 상태 갱신: 2026-03-20

---

## 요약

| 심각도   | 건수 | 수정 완료 | 주요 항목                                            |
| -------- | ---- | --------- | ---------------------------------------------------- |
| CRITICAL | 1    | 1         | metrics.py 데드락                                    |
| HIGH     | 7    | 7         | 입력 전처리 누락, 하드코딩 비밀번호, CORS, 경쟁 상태 |
| MEDIUM   | 12   | 10        | 예외 삼킴, 데이터 손실, 미사용 기능, 보안 노출       |
| LOW      | 8    | 7         | 미사용 설정, import 비일관, 테스트 커버리지 부족     |

---

## CRITICAL

### 1. ~~`metrics.py:56-65` — `to_dict()` 데드락~~ ✅ 수정 완료

> **수정됨**: `to_dict()` (현재 `metrics.py:59-71`)에서 프로퍼티 호출 대신 인라인 계산으로 변경하여 데드락 해소.

~~`to_dict()`가 `self._lock`을 잡은 상태에서 `self.avg_latency_ms`, `self.success_rate` 프로퍼티를 호출하는데, 이 프로퍼티들도 동일한 non-reentrant `threading.Lock`을 다시 잡으려 함.~~

---

## HIGH

### 2. ~~`medical_context_service.py:20-36` — `get_pool()` 이중 초기화 경쟁 상태~~ ✅ 수정 완료

> **수정됨**: `asyncio.Lock` (`_pool_lock`) + double-check locking 패턴 적용 (현재 `medical_context_service.py:19,27-28`).

### 3. ~~`schemas.py:12` — `query` max_length=2048 (RULE_PYTHON.md 위반)~~ ✅ 수정 완료

> **수정됨**: `max_length=4096`으로 변경 완료 (현재 `schemas.py:13`).

### 4. ~~`app.py:240-270` + `ollama_service.py` + `vllm_service.py` — 입력 전처리 누락~~ ✅ 수정 완료

> **수정됨**: `typo_corrector.correct_typos()`가 공통 전처리로 적용되고, `InferRequest` Pydantic 모델이 길이 제한(`max_length=4096`)을 검증함.

### 5. ~~`config.py:60` + `import_medical_data.py:28` — 하드코딩 비밀번호~~ ✅ 수정 완료

> **수정됨**: `config.py:63` — `mysql_password` 기본값이 `""` (빈 문자열)로 변경. `import_medical_data.py:33` — `os.getenv("MYSQL_PASSWORD", "")` 로 변경.

### 6. ~~`app.py:83-89` — CORS 과도한 허용~~ ✅ 수정 완료

> **수정됨**: 환경변수 기반 origin 설정 + `allow_methods=["GET", "POST"]`, `allow_headers=["Content-Type", "Authorization", "X-Session-Id"]`로 제한 (현재 `app.py:119-125`).

### 7. ~~`ollama_service.py:209-225` — 스트리밍 에러 핸들링 누락~~ ✅ 수정 완료

> **수정됨**: `_stream()` 내부에 `ConnectError`/`ReadTimeout` 핸들링 + Circuit Breaker 실패 기록 추가 (현재 `ollama_service.py:230-239`).

### 8. ~~`config.py:43` — 하드코딩 사설 IP 기본값~~ ✅ 수정 완료

> **수정됨**: `vllm_base_url` 기본값이 `"http://localhost:8000"`으로 변경 (현재 `config.py:46`).

---

## MEDIUM

### 9. `app.py:511-513, 534-537` — 피드백 엔드포인트 예외 삼킴

`/feedback`와 `/feedback/stats`에서 DB 예외 시 HTTP 200 + `status="error"` 반환. Spring Boot 클라이언트가 상태 코드로 실패 감지 불가.

**수정**: `raise HTTPException(status_code=500)` 또는 적절한 에러 응답.

### 10. ~~`chunker.py:36-39` — 마지막 청크 병합 시 데이터 손실~~ ✅ 수정 완료

> **수정됨**: 오버랩 슬라이싱 제거. 현재 `chunker.py:39` — `chunks[-1] = chunks[-1] + chunk`.

### 11. ~~`typo_corrector.py:158-207` — `_flush_hit_counts()` 미호출~~ ✅ 수정 완료

> **수정됨**: `_flush_hit_counts()` 기능이 제거됨. 현재 typo_corrector는 DB 사전 리로드 + 내장 폴백 사전 패턴으로 단순화됨.

### 12. ~~`app.py:192-204` — `OSError` 핸들러가 `ConnectionError` 핸들러를 섀도잉~~ ✅ 수정 완료

> **수정됨**: `OSError` 핸들러 내에서 `isinstance(exc, ConnectionError)` 분기 추가 (현재 `app.py:247-249`).

### 13. ~~`query_expander.py:30` — 백엔드 무관하게 Ollama 고정 사용~~ ✅ 수정 완료

> **수정됨**: `llm_backend` 설정에 따라 vLLM/Ollama 분기 적용 (현재 `query_expander.py:38-39`).

### 14. `app.py:322-339, 380-383, 463-480` — `huggingface` 백엔드 분기 누락

`/infer/medical`, `/infer/medical/stream`, `/infer/rule`에 `vllm`/`else(ollama)` 분기만 있음. `llm_backend=huggingface` 시 Ollama 호출 시도.

### 15. ~~`app.py:175, 189, 537` — 내부 예외 메시지 클라이언트 노출~~ ✅ 수정 완료

> **수정됨**: 모든 예외 핸들러가 일반 메시지 반환으로 변경 (현재 `app.py:214-249`). `str(exc)`는 로그에만 기록.

### 16. ~~`app.py:98, 104-109` — 관리 엔드포인트 Rate Limiting/인증 없음~~ ✅ 수정 완료

> **수정됨**: `slowapi` Rate Limiting 적용 + `verify_admin_api_key` API Key 인증 추가 (현재 `app.py:113-115,134-136,141-142`).

### 17. ~~`circuit_breaker.py:26-39` — HALF_OPEN 상태에서 다수 요청 동시 통과~~ ✅ 수정 완료

> **수정됨**: `can_execute()` 내에서 `threading.Lock`으로 원자적 상태 전환. HALF_OPEN → OPEN 전환으로 동시 프로브 차단 (현재 `circuit_breaker.py:43-54`).

### 18. `index_rule_data.py:62-66` — 기존 규칙도 "inserted"로 처리

이미 존재하는 규칙이 `inserted` 리스트에 포함되어 매 실행마다 전체 임베딩 재계산.

### 19. ~~`schemas.py:18` — `history` 필드 크기 제한 없음~~ ✅ 수정 완료

> **수정됨**: `max_length=20` 제한 추가 (현재 `schemas.py:19`).

### 20. ~~`prompt_loader.py:12-20` — 경로 순회 위험~~ ✅ 수정 완료

> **수정됨**: `ALLOWED_PROMPTS` 화이트리스트 적용 (현재 `prompt_loader.py:15,21-22`).

---

## LOW

### 21. ~~`config.py:22` — `llm_model` 기본값이 Ollama 포맷~~ ✅ 수정 완료

> **수정됨**: 기본값이 `"Qwen/Qwen2.5-7B-Instruct"` (HuggingFace 포맷)으로 변경 (현재 `config.py:25`).

### 22. ~~`config.py:71` — `openai_api_key` 미사용~~ ✅ 수정 완료

> **수정됨**: 필드 제거됨. 현재 `config.py`에 `openai_api_key` 없음.

### 23. ~~`config.py:54` — `use_reranking` 설정 무시~~ ✅ 수정 완료

> **수정됨**: `medical_context_service.py:212`에서 `settings.use_reranking` 체크 후 reranker 호출. `reranker.py:44`에서도 이중 체크.

### 24. ~~`app.py:25` — 미사용 top-level import~~ ✅ 수정 완료

> **수정됨**: `from llm_service import generate` 모듈 레벨 import 제거됨.

### 25. `app.py:225-280` — `/infer` 엔드포인트 metrics 미기록

`/infer/medical`과 `/infer/rule`은 `metrics.record_request()` 호출하지만, `/infer`는 호출하지 않음.

### 26. ~~`schemas.py:40` — `FeedbackRequest.endpoint` 패턴 부정확~~ ✅ 수정 완료

> **수정됨**: 패턴이 `"^(medical|rule|infer|infer/medical|infer/rule)$"`로 확장 (현재 `schemas.py:41`).

### 27. ~~`ollama_service.py:190` — 함수 내 `import json` (비일관)~~ ✅ 수정 완료

> **수정됨**: 모듈 레벨 `import json`으로 통일 (현재 `ollama_service.py:8`).

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

| 순서 | 항목                                          | 심각도   | 상태        |
| ---- | --------------------------------------------- | -------- | ----------- |
| 1    | `metrics.py` 데드락 수정 (Lock → RLock)       | CRITICAL | ✅ 수정 완료 |
| 2    | `get_pool()` 경쟁 상태 수정                   | HIGH     | ✅ 수정 완료 |
| 3    | 전 엔드포인트 입력 전처리 적용                | HIGH     | ✅ 수정 완료 |
| 4    | 하드코딩 비밀번호 제거                        | HIGH     | ✅ 수정 완료 |
| 5    | CORS 설정 제한                                | HIGH     | ✅ 수정 완료 |
| 6    | `vllm_base_url` 기본값 변경                   | HIGH     | ✅ 수정 완료 |
| 7    | `ollama_service.py` 스트리밍 에러 핸들링 추가 | HIGH     | ✅ 수정 완료 |
| 8    | 피드백 엔드포인트 에러 응답 수정              | MEDIUM   | ⬜ 미수정    |
| 9    | `chunker.py` 데이터 손실 수정                 | MEDIUM   | ✅ 수정 완료 |
| 10   | 예외 메시지 클라이언트 노출 제거              | MEDIUM   | ✅ 수정 완료 |
