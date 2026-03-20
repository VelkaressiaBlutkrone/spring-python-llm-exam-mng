"""
LLM 추론 서버 — FastAPI 애플리케이션.

역할:
    Spring Boot 등 백엔드가 HTTP로 호출하는 LLM 게이트웨이. 백엔드는
    ``LLM_BACKEND``(vllm | ollama)에 따라 원격 추론 서버로 위임하거나,
    로컬 Hugging Face 파이프라인(``llm_service``)을 사용한다.

주요 라우트:
    ``GET /`` — 서버 가동 확인
    ``GET /health`` — LLM·MySQL·ChromaDB·서킷 브레이커 상태
    ``GET /metrics`` — 추론 지연·성공률·벡터 적중 등 집계
    ``POST /infer`` — 순수 생성 (RAG 없음)
    ``POST /infer/medical`` · ``POST /infer/medical/stream`` — 의학 컨텍스트(RAG) + 채팅
    ``POST /infer/rule`` · ``POST /infer/rule/stream`` — 병원 규칙 RAG + 채팅
    ``POST /feedback`` · ``GET /feedback/stats`` — 응답 품질 피드백(MySQL)
    ``POST /typo/reload`` — 오타 사전 DB 리로드

공통 처리:
    slowapi 요청 제한, CORS, 공유 ``httpx.AsyncClient``, 예외 시 일관된 JSON 오류 응답.
"""

import logging
import time as _time
from contextlib import asynccontextmanager

import json

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import APIKeyHeader

import httpx

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from circuit_breaker import ServiceUnavailableError
from metrics import metrics
from config import get_settings
from medical_context_service import build_medical_context, close_pool, get_pool
from prompt_guard import sanitize_history, sanitize_query
from prompt_loader import load_prompt
from response_cleaner import NON_KOREAN_CJK_PATTERN, SPECIAL_TOKEN_PATTERN, clean_llm_response
import aiomysql
from schemas import InferRequest, InferResponse, FeedbackRequest, FeedbackResponse
from typo_corrector import correct_typos

# ---------------------------------------------------------------------------
# 로깅
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 관리 엔드포인트 API Key 인증
# ---------------------------------------------------------------------------
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_admin_api_key(api_key: str = Security(api_key_header)):
    """관리 엔드포인트용 API Key 검증. admin_api_key가 설정되지 않으면 인증을 건너뜁니다."""
    settings = get_settings()
    if not settings.admin_api_key:
        return  # API Key 미설정 시 인증 비활성화 (개발 편의)
    if api_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 리소스 관리 (lazy initialization)"""
    # startup — MySQL과 ChromaDB 모두 lazy init (첫 요청 시 연결)
    settings = get_settings()
    logger.info("Server starting (MySQL: %s:%d, ChromaDB: %s:%d, vector_search: %s)",
                settings.mysql_host, settings.mysql_port,
                settings.chroma_host, settings.chroma_port,
                settings.use_vector_search)

    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=5.0,
            read=float(settings.llm_infer_timeout_sec),
            write=5.0,
            pool=5.0,
        ),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )
    logger.info("Shared httpx client created")

    # LLM 백엔드 초기화 (Strategy 패턴)
    if settings.llm_backend == "vllm":
        from vllm_backend import VllmBackend
        app.state.llm = VllmBackend()
        logger.info("LLM backend initialized: vLLM")
    else:
        from ollama_backend import OllamaBackend
        app.state.llm = OllamaBackend()
        logger.info("LLM backend initialized: Ollama")

    yield

    # shutdown
    await app.state.http_client.aclose()
    await close_pool()
    logger.info("Resources cleaned up")


app = FastAPI(
    title="Python LLM Inference API",
    description="Spring Boot 연동용 LLM 추론 서버",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Rate limiting (IP 기준, slowapi)
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS: Spring Boot 연동 시 허용 origin 제한 (환경변수 CORS_ORIGINS으로 재정의 가능)
_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-Session-Id"],
)


@app.get("/")
def root():
    """루트: 서버 상태 확인"""
    return {"status": "ok", "message": "LLM Inference API"}


@app.get("/metrics", dependencies=[Depends(verify_admin_api_key)])
@limiter.limit("30/minute")
def get_metrics(request: Request):
    """추론 메트릭 조회"""
    return metrics.to_dict()


@app.post("/typo/reload", dependencies=[Depends(verify_admin_api_key)])
@limiter.limit("2/minute")
async def typo_reload(request: Request):
    """오타 사전 DB에서 리로드"""
    from typo_corrector import reload_typo_dict
    await reload_typo_dict()
    return {"status": "ok", "message": "Typo dictionary reloaded"}


async def _check_mysql_health() -> bool:
    """MySQL 연결 상태 확인"""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                return True
    except Exception:
        return False


def _check_chromadb_health() -> bool:
    """ChromaDB 연결 상태 확인"""
    try:
        from vector_store import get_chroma_client
        client = get_chroma_client()
        client.heartbeat()
        return True
    except Exception:
        return False


@app.get("/health")
async def health():
    """헬스체크 엔드포인트 — LLM 백엔드, MySQL, ChromaDB 상태 확인"""
    settings = get_settings()

    checks = {}

    # LLM 백엔드 체크
    llm = request.app.state.llm
    checks["llm"] = await llm.health_check(client=request.app.state.http_client)

    # MySQL 체크
    checks["mysql"] = await _check_mysql_health()

    # ChromaDB 체크
    checks["chromadb"] = _check_chromadb_health()

    all_healthy = all(checks.values())

    # Circuit Breaker 상태
    if settings.llm_backend == "vllm":
        from vllm_service import _breaker  # noqa: circuit breaker는 모듈별 싱글턴
    else:
        from ollama_service import _breaker  # noqa
    return {
        "status": "healthy" if all_healthy else "degraded",
        "llm_backend": settings.llm_backend,
        "checks": checks,
        "circuit_breaker": _breaker.state,
    }


# ---------------------------------------------------------------------------
# 예외 → JSON 응답 (클라이언트·로드밸런서가 일관되게 처리하도록)
# ---------------------------------------------------------------------------


@app.exception_handler(TimeoutError)
def timeout_handler(request: Request, exc: TimeoutError):
    """추론 타임아웃 시 503 반환"""
    logger.warning("Request timeout: %s", exc)
    return JSONResponse(status_code=503, content={"detail": "요청 처리 시간이 초과되었습니다"})


@app.exception_handler(MemoryError)
def memory_error_handler(request: Request, exc: MemoryError):
    """OOM 시 503 반환"""
    logger.error("Out of memory: %s", exc)
    return JSONResponse(status_code=503, content={"detail": "LLM 추론 중 메모리 부족"})


@app.exception_handler(RuntimeError)
def runtime_error_handler(request: Request, exc: RuntimeError):
    """모델/CUDA 오류 등 503 반환"""
    logger.error("Runtime error: %s", exc)
    return JSONResponse(status_code=503, content={"detail": "LLM 런타임 오류가 발생했습니다"})


@app.exception_handler(ConnectionError)
def connection_error_handler(request: Request, exc: ConnectionError):
    """Ollama/외부 서버 연결 실패 시 503 반환"""
    logger.error("Connection error: %s", exc)
    detail = "LLM 서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요."
    return JSONResponse(status_code=503, content={"detail": detail})


@app.exception_handler(OSError)
def os_error_handler(request: Request, exc: OSError):
    """모델 로딩 실패(DLL 등) 503 반환"""
    logger.error("OS error: %s", exc)
    if isinstance(exc, ConnectionError):
        detail = "LLM 서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요."
        return JSONResponse(status_code=503, content={"detail": detail})
    return JSONResponse(status_code=503, content={"detail": "서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."})


@app.exception_handler(ServiceUnavailableError)
def circuit_breaker_handler(request: Request, exc: ServiceUnavailableError):
    """Circuit Breaker OPEN 시 503 반환"""
    logger.warning("Circuit breaker rejected request: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc)},
        headers={"Retry-After": "30"},
    )


@app.exception_handler(Exception)
def general_exception_handler(request: Request, exc: Exception):
    """기타 예외 500 반환"""
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "서버 내부 오류가 발생했습니다"})


@app.post("/infer", response_model=InferResponse)
@limiter.limit("20/minute")
async def infer(request: Request, body: InferRequest) -> InferResponse:
    """
    LLM 추론: 쿼리 입력 → 생성 응답 반환
    Spring Boot /api/llm/query 에서 호출
    LLM_BACKEND=ollama 시 Ollama 서버, 아니면 Hugging Face 사용
    """
    _start = _time.time()
    query_preview = body.query[:50] + "..." if len(body.query) > 50 else body.query
    logger.info("Infer request: query=%s", repr(query_preview))

    settings = get_settings()

    corrected = correct_typos(body.query)

    try:
        llm = request.app.state.llm
        generated_text = await llm.generate(
            query=corrected,
            max_length=body.max_length,
            temperature=body.temperature,
            top_p=body.top_p or 1.0,
            client=request.app.state.http_client,
        )
    except Exception as exc:
        fallback = settings.llm_fallback_response
        if fallback:
            logger.warning("LLM failed: %s, using fallback response", exc)
            generated_text = fallback
        else:
            _elapsed = (_time.time() - _start) * 1000
            metrics.record_request(latency_ms=_elapsed, success=False)
            raise

    _elapsed = (_time.time() - _start) * 1000
    metrics.record_request(latency_ms=_elapsed, success=True)
    logger.info("Infer response: length=%d", len(generated_text))
    return InferResponse(generated_text=generated_text)


@app.post("/infer/medical", response_model=InferResponse)
@limiter.limit("10/minute")
async def infer_medical(request: Request, body: InferRequest) -> InferResponse:
    """
    의학지식 데이터 기반 LLM 추론
    1. MySQL에서 관련 의학 데이터 실시간 조회
    2. 시스템 프롬프트 + 의학 컨텍스트 + 사용자 질문 조합
    3. Ollama Chat API 호출
    """
    _start = _time.time()
    query_preview = body.query[:50] + "..." if len(body.query) > 50 else body.query
    logger.info("Medical infer request: query=%s", repr(query_preview))

    settings = get_settings()

    # (0) 오타 교정 + 인젝션 감지
    corrected_query = correct_typos(body.query)
    _, is_suspicious = sanitize_query(body.query)

    # (1) 의학 컨텍스트 조회
    medical_context = await build_medical_context(corrected_query)
    logger.info("Medical context: %d chars", len(medical_context))

    # (2) 프롬프트 조합
    messages = [{"role": "system", "content": load_prompt("medical_system")}]
    if medical_context:
        messages.append({"role": "system", "content": medical_context})

    # 대화 이력 포함 (검증 + 인젝션 방어)
    for msg in sanitize_history(body.history):
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": corrected_query})

    # (3) LLM Chat API 호출 (vLLM 또는 Ollama)
    stop_tokens = ["<|im_start|>", "<|im_end|>", "<|endoftext|>", "，。，", "。，。"]

    try:
        llm = request.app.state.llm
        raw_text = await llm.chat(
            messages=messages,
            temperature=body.temperature,
            max_length=body.max_length,
            stop=stop_tokens,
            client=request.app.state.http_client,
        )
    except Exception:
        _elapsed = (_time.time() - _start) * 1000
        metrics.record_request(latency_ms=_elapsed, success=False, vector_hit=len(medical_context) > 0)
        raise

    generated_text = clean_llm_response(raw_text)

    _elapsed = (_time.time() - _start) * 1000
    metrics.record_request(latency_ms=_elapsed, success=True, vector_hit=len(medical_context) > 0)
    logger.info("Medical infer response: length=%d", len(generated_text))
    return InferResponse(generated_text=generated_text)


@app.post("/infer/medical/stream")
@limiter.limit("10/minute")
async def infer_medical_stream(request: Request, body: InferRequest):
    """
    의학지식 기반 LLM 스트리밍 추론 (SSE)
    Ollama stream:true → Server-Sent Events로 토큰 단위 전송
    """
    query_preview = body.query[:50] + "..." if len(body.query) > 50 else body.query
    logger.info("Medical stream request: query=%s", repr(query_preview))

    settings = get_settings()

    corrected_query = correct_typos(body.query)
    medical_context = await build_medical_context(corrected_query)
    logger.info("Medical context (stream): %d chars", len(medical_context))

    messages = [{"role": "system", "content": load_prompt("medical_system")}]
    if medical_context:
        messages.append({"role": "system", "content": medical_context})

    # 대화 이력 포함 (검증 + 인젝션 방어)
    for msg in sanitize_history(body.history):
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": corrected_query})

    stop_tokens = ["<|im_start|>", "<|im_end|>", "<|endoftext|>", "，。，", "。，。"]
    http_client = request.app.state.http_client

    llm = request.app.state.llm

    async def generate_sse():
        try:
            async for item in llm.chat_stream(
                messages=messages,
                temperature=body.temperature,
                max_length=body.max_length,
                stop=stop_tokens,
                client=http_client,
            ):
                if "token" in item:
                    raw_token = item["token"]
                    # 특수 토큰 + 중국어/일본어 문자 실시간 제거
                    token = SPECIAL_TOKEN_PATTERN.sub("", raw_token)
                    token = NON_KOREAN_CJK_PATTERN.sub("", token)
                    if token:
                        data = json.dumps({"token": token}, ensure_ascii=False)
                        yield f"data: {data}\n\n"
                if item.get("done"):
                    yield "data: [DONE]\n\n"
        except Exception as exc:
            logger.error("Stream error: %s", exc, exc_info=True)
            error_data = json.dumps({"error": "응답 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/infer/rule", response_model=InferResponse)
@limiter.limit("10/minute")
async def infer_rule(request: Request, body: InferRequest) -> InferResponse:
    """
    병원 규칙 Q&A LLM 추론
    의사·간호사가 병원 내부 규칙(당직, 물품, 위생 등)에 대해 질의할 때 사용
    """
    _start = _time.time()
    query_preview = body.query[:50] + "..." if len(body.query) > 50 else body.query
    logger.info("Rule infer request: query=%s", repr(query_preview))

    settings = get_settings()
    corrected_query = correct_typos(body.query)
    if corrected_query != body.query:
        logger.info("Rule query typo corrected: '%s' -> '%s'", body.query, corrected_query)

    # RAG: ChromaDB + MySQL 하이브리드 검색으로 병원규칙 컨텍스트 주입
    rule_context = ""
    try:
        from rule_context_service import build_rule_context
        rule_context = await build_rule_context(corrected_query)
    except Exception as exc:
        logger.warning("Rule context build skipped: %s", exc)
    logger.info("Rule context: %d chars", len(rule_context))

    # 검색 결과가 없으면 LLM 호출 없이 안내 메시지 반환
    if not rule_context:
        no_result_msg = "해당 내용이 등록되어 있지 않습니다. 관리자에게 문의 바랍니다."
        # 오타 교정이 있었으면 교정 결과도 안내
        if corrected_query != body.query:
            no_result_msg = (
                f"'{body.query}'을(를) '{corrected_query}'(으)로 검색했으나, "
                "해당 내용이 등록되어 있지 않습니다. 관리자에게 문의 바랍니다."
            )
        logger.info("Rule infer: no context found, returning fallback message")
        return InferResponse(generated_text=no_result_msg)

    messages = [{"role": "system", "content": load_prompt("rule_system")}]
    messages.append({"role": "system", "content": rule_context})
    messages.append({"role": "user", "content": corrected_query})

    stop_tokens = ["<|im_start|>", "<|im_end|>", "<|endoftext|>", "，。，", "。，。"]

    try:
        llm = request.app.state.llm
        raw_text = await llm.chat(
            messages=messages,
            temperature=body.temperature,
            max_length=body.max_length,
            stop=stop_tokens,
            client=request.app.state.http_client,
        )
    except Exception:
        _elapsed = (_time.time() - _start) * 1000
        metrics.record_request(latency_ms=_elapsed, success=False, vector_hit=len(rule_context) > 0)
        raise

    generated_text = clean_llm_response(raw_text)

    _elapsed = (_time.time() - _start) * 1000
    metrics.record_request(latency_ms=_elapsed, success=True, vector_hit=len(rule_context) > 0)
    logger.info("Rule infer response: length=%d", len(generated_text))
    return InferResponse(generated_text=generated_text)


@app.post("/infer/rule/stream")
@limiter.limit("10/minute")
async def infer_rule_stream(request: Request, body: InferRequest):
    """
    병원 규칙 Q&A 스트리밍 추론 (SSE)
    /infer/rule과 동일한 로직, stream:true로 토큰 단위 전송
    """
    query_preview = body.query[:50] + "..." if len(body.query) > 50 else body.query
    logger.info("Rule stream request: query=%s", repr(query_preview))

    settings = get_settings()
    corrected_query = correct_typos(body.query)

    # RAG: 병원규칙 컨텍스트 주입
    rule_context = ""
    try:
        from rule_context_service import build_rule_context
        rule_context = await build_rule_context(corrected_query)
    except Exception as exc:
        logger.warning("Rule context build skipped (stream): %s", exc)
    logger.info("Rule context (stream): %d chars", len(rule_context))

    # 검색 결과가 없으면 안내 메시지 스트리밍 반환
    if not rule_context:
        no_result_msg = "해당 내용이 등록되어 있지 않습니다. 관리자에게 문의 바랍니다."
        if corrected_query != body.query:
            no_result_msg = (
                f"'{body.query}'을(를) '{corrected_query}'(으)로 검색했으나, "
                "해당 내용이 등록되어 있지 않습니다. 관리자에게 문의 바랍니다."
            )

        async def no_result_sse():
            data = json.dumps({"token": no_result_msg}, ensure_ascii=False)
            yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            no_result_sse(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    messages = [{"role": "system", "content": load_prompt("rule_system")}]
    messages.append({"role": "system", "content": rule_context})

    # 대화 이력 포함 (검증 + 인젝션 방어)
    for msg in sanitize_history(body.history):
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": corrected_query})

    stop_tokens = ["<|im_start|>", "<|im_end|>", "<|endoftext|>", "，。，", "。，。"]
    http_client = request.app.state.http_client

    llm = request.app.state.llm

    async def generate_sse():
        try:
            async for item in llm.chat_stream(
                messages=messages,
                temperature=body.temperature,
                max_length=body.max_length,
                stop=stop_tokens,
                client=http_client,
            ):
                if "token" in item:
                    raw_token = item["token"]
                    token = SPECIAL_TOKEN_PATTERN.sub("", raw_token)
                    token = NON_KOREAN_CJK_PATTERN.sub("", token)
                    if token:
                        data = json.dumps({"token": token}, ensure_ascii=False)
                        yield f"data: {data}\n\n"
                if item.get("done"):
                    yield "data: [DONE]\n\n"
        except Exception as exc:
            logger.error("Rule stream error: %s", exc, exc_info=True)
            error_data = json.dumps({"error": "응답 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/feedback", response_model=FeedbackResponse)
@limiter.limit("10/minute")
async def submit_feedback(request: Request, body: FeedbackRequest) -> FeedbackResponse:
    """
    LLM 응답 품질 피드백 저장
    """
    logger.info("Feedback received: score=%d, endpoint=%s", body.score, body.endpoint)

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO llm_feedback (session_id, query, response, score, comment, endpoint)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (body.session_id, body.query, body.response,
                     body.score, body.comment, body.endpoint),
                )
            await conn.commit()
        return FeedbackResponse()
    except Exception as exc:
        logger.error("Feedback error: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "피드백 처리 중 오류가 발생했습니다."}
        )


@app.get("/feedback/stats", dependencies=[Depends(verify_admin_api_key)])
async def feedback_stats():
    """피드백 통계 조회"""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT
                        endpoint,
                        COUNT(*) as total,
                        ROUND(AVG(score), 2) as avg_score,
                        SUM(CASE WHEN score <= 2 THEN 1 ELSE 0 END) as low_count,
                        SUM(CASE WHEN score >= 4 THEN 1 ELSE 0 END) as high_count
                    FROM llm_feedback
                    GROUP BY endpoint
                """)
                stats = await cur.fetchall()
        return {"status": "ok", "stats": stats}
    except Exception as exc:
        logger.error("Feedback error: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "피드백 처리 중 오류가 발생했습니다."}
        )


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)
