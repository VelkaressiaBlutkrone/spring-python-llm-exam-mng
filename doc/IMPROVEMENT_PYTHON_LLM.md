# Python LLM 서비스 개선 제안서

> 2026-03-18 기준: 22개 Task 전체 구현 완료

> 작성일: 2026-03-12
> 대상: `python-llm/` 모듈 전체 및 Spring Boot LLM 연동 레이어

---

## 목차

1. [아키텍처 개선](#1-아키텍처-개선)
2. [성능 최적화](#2-성능-최적화)
3. [RAG 파이프라인 고도화](#3-rag-파이프라인-고도화)
4. [LLM 추론 품질 향상](#4-llm-추론-품질-향상)
5. [코드 품질 및 유지보수성](#5-코드-품질-및-유지보수성)
6. [운영 안정성](#6-운영-안정성)
7. [보안](#7-보안)
8. [우선순위 로드맵](#8-우선순위-로드맵)

---

## 1. 아키텍처 개선

### 1.1 httpx.AsyncClient 매 요청마다 생성 → 공유 클라이언트로 전환

**현재 문제**
`app.py`의 `/infer/medical`, `/infer/rule` 등에서 매 요청마다 `async with httpx.AsyncClient(...)` 로 새 클라이언트를 생성한다. `ollama_service.py`의 `generate_with_ollama`, `chat_with_ollama` 도 마찬가지다.

```python
# 현재 — 매 요청마다 TCP 커넥션 풀 생성/해제
async with httpx.AsyncClient(timeout=...) as client:
    response = await client.post(...)
```

**문제점**

- 요청마다 TCP 핸드셰이크 + TLS(있는 경우) 발생 → 불필요한 지연
- 동시 요청 다수 시 커넥션 폭발 가능

**개선안**
앱 lifespan에서 공유 `httpx.AsyncClient`를 생성하고 종료 시 close한다.

```python
# app.py lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=5.0, read=60.0, write=5.0, pool=5.0),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )
    yield
    await app.state.http_client.aclose()
```

**효과**: Ollama 호출 레이턴시 감소, 리소스 사용 안정화

---

### 1.2 Ollama 호출 로직 중복 제거

**현재 문제**
`app.py`의 `/infer/medical`과 `/infer/rule`에서 Ollama Chat API 호출 코드가 거의 동일하게 반복된다 (payload 구성 → httpx 호출 → 응답 파싱 → clean). `ollama_service.py`의 `chat_with_ollama`는 이미 존재하지만 사용하지 않는다.

**개선안**
`ollama_service.py`의 `chat_with_ollama`를 확장하여 `stop` 토큰, `options` 등을 파라미터로 받고, `app.py`에서는 이를 호출만 한다.

```python
# ollama_service.py
async def chat_with_ollama(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    max_length: int = 256,
    stop: list[str] | None = None,    # 추가
    client: httpx.AsyncClient = None,  # 공유 클라이언트
) -> str:
    ...
```

**효과**: 유지보수 용이, 버그 수정 시 한 곳만 변경

---

### 1.3 프롬프트 관리 외부화

**현재 문제**
`MEDICAL_SYSTEM_PROMPT`, `RULE_SYSTEM_PROMPT`가 `app.py` 상단에 하드코딩되어 있다. 프롬프트 변경 시 코드 수정 + 서버 재시작 필요.

**개선안**
프롬프트를 외부 파일(YAML/JSON) 또는 DB 테이블로 분리한다.

```
python-llm/
  prompts/
    medical_system.txt
    rule_system.txt
```

```python
# prompt_loader.py
from pathlib import Path
from functools import lru_cache

PROMPTS_DIR = Path(__file__).parent / "prompts"

@lru_cache
def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8")
```

**효과**: 프롬프트 엔지니어링 이터레이션 속도 향상, 비개발자도 수정 가능

---

## 2. 성능 최적화

### 2.1 임베딩 캐시 도입

**현재 문제**
`embedding_service.py`에서 동일한 쿼리도 매번 Ollama `/api/embed` API를 호출한다.

**개선안**
LRU 캐시로 최근 N개 쿼리의 임베딩을 메모리에 보관한다.

```python
from functools import lru_cache
import hashlib

_embedding_cache: dict[str, list[float]] = {}
MAX_CACHE = 500

async def get_embedding(text: str) -> list[float]:
    key = hashlib.md5(text.encode()).hexdigest()
    if key in _embedding_cache:
        return _embedding_cache[key]

    embedding = await _call_ollama_embed(text)

    if len(_embedding_cache) >= MAX_CACHE:
        # 가장 오래된 항목 제거 (FIFO)
        oldest = next(iter(_embedding_cache))
        del _embedding_cache[oldest]
    _embedding_cache[key] = embedding
    return embedding
```

**효과**: 반복 질문 시 Ollama 호출 제거 → 응답 속도 ~200ms 단축

---

### 2.2 벡터 검색과 FULLTEXT 검색 병렬 실행

**현재 문제**
`build_medical_context()`에서 벡터 검색 → 결과 부족 시 FULLTEXT 검색을 **순차 실행**한다.

```python
# 현재 — 순차 실행
vector_results = await search_vector_store(query)
if len(vector_results) < 2:
    qa_results = await search_medical_qa(query)  # 여기서 대기
```

**개선안**
`asyncio.gather`로 병렬 실행 후 결과를 합산한다.

```python
import asyncio

async def build_medical_context(query: str) -> str:
    vector_task = search_vector_store(query, top_k=settings.vector_search_top_k)
    qa_task = search_medical_qa(query, limit=3)
    content_task = search_medical_content(query, limit=2)

    vector_results, qa_results, content_results = await asyncio.gather(
        vector_task, qa_task, content_task
    )

    # 벡터 결과가 충분하면 FULLTEXT 결과는 사용하지 않음
    parts = []
    if vector_results:
        parts.extend(_format_vector_results(vector_results))
    if len(vector_results) < 2 and qa_results:
        parts.extend(_format_qa_results(qa_results))
    if len(vector_results) < 1 and content_results:
        parts.extend(_format_content_results(content_results))
    ...
```

**효과**: 컨텍스트 빌드 시간 ~40-60% 단축 (가장 느린 쿼리 기준)

---

### 2.3 ChromaDB 컬렉션 분리

**현재 문제**
의학 문서(`type=qa/content`)와 병원 규칙(`type=rule`)이 동일한 `medical_docs` 컬렉션에 혼재한다. `rule_context_service.py`에서 `where={"type": "rule"}` 필터로 구분하지만, HNSW 인덱스 전체를 탐색한 후 필터링하므로 비효율적이다.

**개선안**
`config.py`에 이미 `chroma_rule_collection` 설정이 있으나 사용하지 않고 있다. 이를 활성화하여 별도 컬렉션으로 분리한다.

```python
# rule_context_service.py
def _get_rule_collection():
    settings = get_settings()
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=settings.chroma_rule_collection,  # "medical_rules"
        metadata={"hnsw:space": "cosine"},
    )
```

**효과**: 규칙 검색 정확도 향상, 불필요한 의학 문서 노이즈 제거

---

### 2.4 인덱싱 스크립트 증분 업데이트

**현재 문제**
`index_medical_data.py`는 전체 데이터를 매번 다시 임베딩하고 upsert한다. 데이터가 많아지면 시간과 비용 낭비.

**개선안**
마지막 인덱싱 시점(`last_indexed_at`) 이후 변경된 레코드만 처리한다.

```python
def fetch_medical_qa_incremental(settings, since: datetime) -> list[dict]:
    """마지막 인덱싱 이후 추가/수정된 Q&A만 조회"""
    conn = pymysql.connect(...)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, department, q_type, question, answer FROM medical_qa "
            "WHERE created_at > %s OR updated_at > %s",
            (since, since),
        )
        return cur.fetchall()
```

**효과**: 인덱싱 시간 대폭 단축, 정기 배치 실행 시 부담 감소

---

## 3. RAG 파이프라인 고도화

### 3.1 Re-ranking 단계 추가

**현재 문제**
벡터 검색 결과를 cosine distance 순서대로 그대로 사용한다. 의미적 유사도만으로는 실제 질문에 대한 적합도가 보장되지 않는다.

**개선안**
검색 결과에 대해 Cross-Encoder 기반 Re-ranking을 수행한다.

```
Query → ChromaDB Top-K(10) → Re-ranker → Top-3 → LLM Context
```

구현 옵션:

- **경량**: Ollama에게 "다음 중 질문과 가장 관련 있는 문서 3개를 선택하세요" 프롬프트
- **정밀**: `sentence-transformers/ms-marco-MiniLM-L-12-v2` 같은 Cross-Encoder 모델 로컬 실행

**효과**: 컨텍스트 품질 향상 → LLM 응답 정확도 향상

---

### 3.2 쿼리 확장 (Query Expansion)

**현재 문제**
사용자가 "머리 아파요"라고 하면 이 짧은 문장만으로 검색한다. "두통", "편두통", "긴장성 두통" 등 관련 용어를 놓칠 수 있다.

**개선안**
LLM을 활용한 쿼리 확장 단계를 추가한다.

```python
async def expand_query(original: str) -> str:
    """LLM으로 검색 키워드를 확장한다 (저비용 호출)"""
    prompt = (
        f"사용자 질문: {original}\n"
        "이 질문과 관련된 의학 용어, 진료과, 증상을 5개 나열하세요. "
        "콤마로 구분, 설명 없이 키워드만:"
    )
    keywords = await generate_with_ollama(query=prompt, max_length=50, temperature=0.3)
    return f"{original} {keywords}"
```

**효과**: 검색 재현율(recall) 향상, 특히 구어체 질문 대응력 개선

---

### 3.3 컨텍스트 관련도 점수 포함

**현재 문제**
벡터 검색 결과의 distance(유사도 점수)를 LLM에 전달하지 않는다. LLM은 모든 참고 자료를 동등하게 취급한다.

**개선안**
컨텍스트에 관련도 점수를 포함하여 LLM이 우선순위를 판단할 수 있게 한다.

```python
# 현재
parts.append(f"진료과: {dept}")
parts.append(item["document"][:500])

# 개선
similarity = 1 - item["distance"]  # cosine distance → similarity
parts.append(f"[관련도: {similarity:.0%}] 진료과: {dept}")
parts.append(item["document"][:500])
```

---

### 3.4 Chunk 전략 개선

**현재 문제**
`index_medical_data.py`에서 Q&A는 `질문+답변[:500]`, 콘텐츠는 `content[:1000]`으로 단순 잘라서 임베딩한다. 긴 콘텐츠의 후반부 정보가 손실된다.

**개선안**
오버랩 청킹(overlapping chunk)을 적용한다.

```python
def chunk_text(text: str, chunk_size: int = 800, overlap: int = 200) -> list[str]:
    """텍스트를 겹치는 청크로 분할"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        # 문장 경계에서 자르기
        if end < len(text):
            last_period = chunk.rfind(".")
            if last_period > chunk_size * 0.5:
                chunk = chunk[:last_period + 1]
                end = start + last_period + 1
        chunks.append(chunk)
        start = end - overlap
    return chunks
```

**효과**: 긴 의학 콘텐츠 검색 누락 방지

---

## 4. LLM 추론 품질 향상

### 4.1 Few-shot 예시 추가

**현재 문제**
시스템 프롬프트에 형식 규칙만 있고, 실제 응답 예시가 없다. LLM이 원하는 형식을 정확히 따르지 않을 수 있다.

**개선안**
시스템 프롬프트에 1~2개의 few-shot 예시를 추가한다.

```
예시 질문: "무릎이 아프고 계단 내려갈 때 시큰합니다"
예시 답변:
추천 진료과: 정형외과

무릎 통증이 계단 하행 시 악화되는 것은 슬개골연골연화증(무릎연골 손상)이나
퇴행성 관절염의 전형적인 증상입니다.

진료과 추천 이유: 무릎 관절의 구조적 문제(연골, 인대, 반월판)를 평가하기 위해
정형외과 전문의의 진찰이 필요합니다.

응급 판단: 현재 증상은 응급 상황은 아니나, 부종이 심하거나 무릎이 잠기는 현상이
있으면 조기 진료를 권장합니다.
```

**효과**: 응답 형식 일관성 향상, 진료과 추천 정확도 개선

---

### 4.2 대화 이력(Multi-turn) 지원

**현재 문제**
매 요청이 독립적이다. 사용자가 "아까 말한 정형외과에서 어떤 검사를 받나요?"라고 해도 이전 문맥을 모른다.

**개선안**
`InferRequest`에 `session_id`와 `history` 필드를 추가하고, 최근 N턴의 대화를 messages에 포함한다.

```python
class InferRequest(BaseModel):
    query: str
    session_id: str | None = None
    history: list[dict] | None = None  # [{"role":"user","content":"..."}, ...]
    max_length: int = 512
    temperature: float = 0.7
```

Spring Boot 측에서 `MedicalHistory` 테이블의 최근 대화를 함께 전송한다.

**효과**: 연속 상담 품질 대폭 향상, 사용자 만족도 증가

---

### 4.3 오타 교정 사전 자동 확장

**현재 문제**
`typo_corrector.py`의 오타 사전(131항목)이 수동 관리된다. 새로운 오타 패턴을 발견해도 코드 수정 필요.

**개선안**

- DB 테이블(`typo_dictionary`)로 오타 사전 이동, 관리 UI 제공
- 사용자 질문 로그에서 오타 패턴 자동 발견 배치 구현

```sql
CREATE TABLE typo_dictionary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    typo VARCHAR(50) NOT NULL UNIQUE,
    correct_term VARCHAR(50) NOT NULL,
    category VARCHAR(20) DEFAULT 'medical',
    hit_count INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**효과**: 오타 교정 커버리지 지속 확장, 운영 편의성 향상

---

### 4.4 응답 품질 평가 루프

**현재 문제**
LLM 응답의 품질(정확성, 적절한 진료과 추천 등)을 측정하는 메커니즘이 없다.

**개선안**

- 사용자 피드백(좋아요/나빠요) 수집 API 추가
- `medical_history` 테이블에 `feedback_score` 컬럼 추가
- 주기적으로 낮은 점수 응답을 분석하여 프롬프트/RAG 개선

```python
@app.post("/feedback")
async def submit_feedback(history_id: int, score: int, comment: str = ""):
    """사용자 응답 품질 피드백 수집"""
    ...
```

---

## 5. 코드 품질 및 유지보수성

### 5.1 response_cleaner.py 단계 번호 중복

**현재 문제**
`clean_llm_response()` 함수 내 주석에서 (5)가 두 번, (4)도 두 번 등장한다. 실행 순서가 불명확하다.

```python
# (5) CJK 제거 후 남은 고아 구두점 정리    ← 첫 번째 (5)
# (5) 연속 공백 정규화                     ← 두 번째 (5)
# (4) 문장이 중간에 잘린 경우              ← (4)가 이미 위에서 사용됨
```

**개선안**: 주석 번호를 (1)~(7)로 순차 정리

---

### 5.2 typo_corrector.py 정상→정상 매핑 잔존

**현재 문제**
`MEDICAL_TYPO_MAP`에 `"어깨": "어깨"`, `"골절": "골절"` 같은 정상→정상 매핑이 다수 있다. 마지막 줄에서 필터링하지만, 사전 정의 자체가 혼란스럽다.

```python
"어깨": "어깨",    # 정상 → 정상 (불필요)
"골절": "골절",    # 정상 → 정상 (불필요)
```

**개선안**: 초기 사전에서 정상→정상 항목을 제거하여 코드 가독성 향상

---

### 5.3 의존성 버전 핀닝 미흡

**현재 문제**
`requirements.txt`에서 `>=` 만 사용하여 최소 버전만 지정한다. 재현 불가능한 빌드 위험.

```
fastapi>=0.109.0
torch>=2.1.0
chromadb>=0.5.0   # 현재 Docker는 1.5.4
```

특히 `chromadb>=0.5.0`인데 Docker 이미지는 `chromadb/chroma:1.5.4`이다. API 호환성 문제 가능성이 있다.

**개선안**
`requirements.txt`에서 호환 릴리즈(`~=`) 또는 상한 버전을 지정한다. 또는 `pip freeze > requirements-lock.txt`로 잠금 파일 생성.

```
fastapi~=0.115.0
chromadb~=1.5.0
torch~=2.4.0
```

---

### 5.4 테스트 커버리지 강화

**현재 문제**
`python-llm/tests/` 디렉토리가 존재하나 테스트가 최소한이다. 핵심 모듈(`medical_context_service`, `response_cleaner`, `typo_corrector`)에 대한 단위 테스트 부족.

**개선안**
우선 순수 함수부터 테스트를 작성한다.

```python
# tests/test_response_cleaner.py
def test_removes_special_tokens():
    assert clean_llm_response("<|im_start|>안녕하세요<|im_end|>") == "안녕하세요"

def test_removes_chinese_characters():
    assert clean_llm_response("정형외과를 推薦합니다") == "정형외과를 합니다"

def test_trims_incomplete_ending():
    result = clean_llm_response("진료과: 내과. 증상은 복통이며 치료")
    assert result.endswith("내과.")  # 불완전 문장 제거
```

---

## 6. 운영 안정성

### 6.1 Ollama 연결 실패 시 Circuit Breaker

**현재 문제**
Ollama 서버 다운 시 모든 요청이 타임아웃(60초)까지 대기한다. 빠른 실패가 안 된다.

**개선안**
Circuit Breaker 패턴을 적용한다. 연속 N회 실패 시 즉시 503 반환.

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, reset_timeout=30):
        self.failures = 0
        self.threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def can_execute(self) -> bool:
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        return True

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.threshold:
            self.state = "OPEN"

    def record_success(self):
        self.failures = 0
        self.state = "CLOSED"
```

**효과**: 장애 전파 방지, 빠른 사용자 피드백

---

### 6.2 구조화된 로깅 (Structured Logging)

**현재 문제**
`logging.basicConfig` + 포맷 문자열 기반 로깅. 로그 파싱, 모니터링 도구 연동이 어렵다.

**개선안**
`structlog` 또는 JSON 로깅으로 전환한다.

```python
import structlog

logger = structlog.get_logger()

# 사용
logger.info("medical_infer",
    query=query_preview,
    context_chars=len(medical_context),
    vector_results=len(vector_results),
    latency_ms=elapsed,
)
```

출력:

```json
{
  "event": "medical_infer",
  "query": "무릎이...",
  "context_chars": 1200,
  "vector_results": 3,
  "latency_ms": 1450,
  "timestamp": "2026-03-12T10:30:00Z"
}
```

**효과**: 로그 검색/분석 용이, Grafana/ELK 연동 가능

---

### 6.3 추론 메트릭 수집

**현재 문제**
응답 시간, 성공률, 컨텍스트 적중률 등을 측정하지 않는다.

**개선안**
`/metrics` 엔드포인트 또는 Prometheus 연동을 추가한다.

```python
from dataclasses import dataclass, field
import time

@dataclass
class Metrics:
    total_requests: int = 0
    success_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0
    vector_hit_rate: float = 0  # 벡터 검색 결과가 있었던 비율

metrics = Metrics()

@app.get("/metrics")
def get_metrics():
    return {
        "total_requests": metrics.total_requests,
        "success_rate": metrics.success_count / max(metrics.total_requests, 1),
        "avg_latency_ms": metrics.avg_latency_ms,
        "vector_hit_rate": metrics.vector_hit_rate,
    }
```

---

### 6.4 Health Check 강화

**현재 문제**
`/health`에서 Ollama 연결만 확인한다. MySQL, ChromaDB 상태는 확인하지 않는다.

**개선안**

```python
@app.get("/health")
async def health():
    checks = {
        "ollama": await check_ollama_health(),
        "mysql": await check_mysql_health(),
        "chromadb": check_chromadb_health(),
    }
    all_healthy = all(checks.values())
    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
    }
```

---

## 7. 보안

### 7.1 입력 길이 제한 일관성

**현재 문제**
`schemas.py`에서 `max_length=4096`이지만, `config.py`에서 `llm_input_max_length=2048`이다. 두 값이 불일치하며 `llm_input_max_length`를 실제로 검증에 사용하지 않는다.

**개선안**
`InferRequest` 검증에서 설정값을 참조하거나, 하나로 통일한다.

---

### 7.2 CORS 설정 확장 필요

**현재 문제**

```python
allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"]
```

Docker 환경에서는 `spring-app` 컨테이너에서 호출하므로 이 origin이 적용되지 않는다. 백엔드 간 통신이므로 CORS가 불필요하거나, 환경별 설정이 필요하다.

**개선안**
환경변수로 CORS origin을 설정한다.

```python
# config.py
cors_origins: list[str] = Field(
    default=["http://localhost:8080"],
    description="허용 CORS origins"
)
```

---

### 7.3 Rate Limiting 부재

**현재 문제**
LLM 추론은 비용이 큰 작업인데, 요청 횟수 제한이 없다.

**개선안**
`slowapi` 또는 미들웨어로 rate limiting을 추가한다.

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/infer/medical")
@limiter.limit("10/minute")
async def infer_medical(request: Request, body: InferRequest):
    ...
```

---

## 8. 우선순위 로드맵

### Phase 1 — 즉시 적용 (코드 수정만으로 해결, 1-2일)

| #   | 항목                             | 효과          | 난이도    |
| --- | -------------------------------- | ------------- | --------- |
| 1   | httpx 공유 클라이언트 전환 (1.1) | 레이턴시 감소 | 낮음      |
| 2   | Ollama 호출 중복 제거 (1.2)      | 유지보수성    | 낮음      |
| 3   | 벡터/FULLTEXT 병렬 검색 (2.2)    | 응답속도 40%↑ | 낮음      |
| 4   | response_cleaner 주석 수정 (5.1) | 가독성        | 매우 낮음 |
| 5   | typo_corrector 정리 (5.2)        | 가독성        | 매우 낮음 |
| 6   | Health Check 강화 (6.4)          | 운영 안정성   | 낮음      |

### Phase 2 — 단기 개선 (1-2주)

| #   | 항목                            | 효과            | 난이도 |
| --- | ------------------------------- | --------------- | ------ |
| 7   | 임베딩 캐시 도입 (2.1)          | 반복 쿼리 속도↑ | 낮음   |
| 8   | ChromaDB 컬렉션 분리 (2.3)      | 검색 정확도↑    | 중간   |
| 9   | 프롬프트 외부화 (1.3)           | 이터레이션↑     | 낮음   |
| 10  | Few-shot 예시 추가 (4.1)        | 응답 품질↑      | 낮음   |
| 11  | Circuit Breaker (6.1)           | 장애 대응↑      | 중간   |
| 12  | 테스트 커버리지 강화 (5.4)      | 안정성↑         | 중간   |
| 13  | 입력 길이/CORS/Rate Limit (7.x) | 보안↑           | 낮음   |

### Phase 3 — 중기 고도화 (3-4주)

| #   | 항목                            | 효과          | 난이도 |
| --- | ------------------------------- | ------------- | ------ |
| 14  | Re-ranking 도입 (3.1)           | RAG 품질↑↑    | 높음   |
| 15  | 쿼리 확장 (3.2)                 | 검색 재현율↑  | 중간   |
| 16  | Chunk 전략 개선 (3.4)           | 긴 문서 검색↑ | 중간   |
| 17  | 대화 이력 지원 (4.2)            | 사용자 경험↑↑ | 높음   |
| 18  | 구조화 로깅 + 메트릭 (6.2, 6.3) | 운영 가시성↑  | 중간   |
| 19  | 증분 인덱싱 (2.4)               | 운영 효율↑    | 중간   |

### Phase 4 — 장기 (1-2개월)

| #   | 항목                             | 효과        | 난이도 |
| --- | -------------------------------- | ----------- | ------ |
| 20  | 오타 사전 DB화 + 자동 확장 (4.3) | 커버리지↑   | 높음   |
| 21  | 응답 품질 피드백 루프 (4.4)      | 지속 개선   | 높음   |
| 22  | 의존성 핀닝 + CI (5.3)           | 빌드 안정성 | 중간   |

---

## 참고: 현재 아키텍처의 강점

개선 사항과 별개로, 현재 구현에서 잘 설계된 부분도 기록한다:

- **하이브리드 검색**: 벡터 + FULLTEXT 조합으로 단일 방식 대비 검색 커버리지 우수
- **오타 교정 전처리**: 한국어 의료 도메인 특화 전처리로 실용적
- **응답 후처리**: CJK 필터링 + 불완전 문장 제거로 한국어 품질 확보
- **Lazy 초기화**: MySQL/ChromaDB 연결을 첫 요청 시 생성하여 기동 속도 확보
- **SSE 스트리밍**: 실시간 토큰 전송으로 사용자 체감 응답 시간 단축
- **환경 분리**: Pydantic Settings + .env로 환경별 설정 관리
- **Fallback 전략**: LLM 실패 시 기본 응답, 벡터 검색 실패 시 FULLTEXT 대체

- **하이브리드 검색**: 벡터 + FULLTEXT 조합으로 단일 방식 대비 검색 커버리지 우수
- **오타 교정 전처리**: 한국어 의료 도메인 특화 전처리로 실용적
- **응답 후처리**: CJK 필터링 + 불완전 문장 제거로 한국어 품질 확보
- **Lazy 초기화**: MySQL/ChromaDB 연결을 첫 요청 시 생성하여 기동 속도 확보
- **SSE 스트리밍**: 실시간 토큰 전송으로 사용자 체감 응답 시간 단축
- **환경 분리**: Pydantic Settings + .env로 환경별 설정 관리
- **Fallback 전략**: LLM 실패 시 기본 응답, 벡터 검색 실패 시 FULLTEXT 대체
