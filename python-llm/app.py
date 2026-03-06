"""
LLM 추론 서버 - FastAPI 앱
PRD 기반: Spring Boot에서 HTTP 호출, RAG 없이 순수 LLM 추론
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import httpx

from config import get_settings
from llm_service import generate
from medical_context_service import build_medical_context, close_pool, get_pool
from schemas import InferRequest, InferResponse

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Python LLM Inference API",
    description="Spring Boot 연동용 LLM 추론 서버",
    version="0.1.0",
)

# CORS: Spring Boot 연동 시 필요
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 운영 시 특정 origin으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """앱 시작 시 DB 커넥션 풀 초기화"""
    await get_pool()
    logger.info("MySQL connection pool initialized")


@app.on_event("shutdown")
async def shutdown():
    """앱 종료 시 DB 커넥션 풀 정리"""
    await close_pool()
    logger.info("MySQL connection pool closed")


@app.get("/")
def root():
    """루트: 서버 상태 확인"""
    return {"status": "ok", "message": "LLM Inference API"}


@app.get("/health")
async def health():
    """헬스체크 엔드포인트"""
    settings = get_settings()
    result = {"status": "healthy", "llm_backend": settings.llm_backend}

    if settings.llm_backend == "ollama":
        from ollama_service import check_ollama_health

        result["ollama_connected"] = await check_ollama_health()

    return result


@app.exception_handler(TimeoutError)
def timeout_handler(request: Request, exc: TimeoutError):
    """추론 타임아웃 시 503 반환"""
    logger.warning("Request timeout: %s", exc)
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(MemoryError)
def memory_error_handler(request: Request, exc: MemoryError):
    """OOM 시 503 반환"""
    logger.error("Out of memory: %s", exc)
    return JSONResponse(status_code=503, content={"detail": "LLM 추론 중 메모리 부족"})


@app.exception_handler(RuntimeError)
def runtime_error_handler(request: Request, exc: RuntimeError):
    """모델/CUDA 오류 등 503 반환"""
    logger.error("Runtime error: %s", exc)
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(OSError)
def os_error_handler(request: Request, exc: OSError):
    """모델 로딩 실패(DLL 등) 503 반환"""
    logger.error("OS error: %s", exc)
    return JSONResponse(status_code=503, content={"detail": "LLM 모델 로딩 실패"})


@app.exception_handler(Exception)
def general_exception_handler(request: Request, exc: Exception):
    """기타 예외 500 반환"""
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "서버 내부 오류가 발생했습니다"})


@app.post("/infer", response_model=InferResponse)
async def infer(request: InferRequest) -> InferResponse:
    """
    LLM 추론: 쿼리 입력 → 생성 응답 반환
    Spring Boot /api/llm/query 에서 호출
    LLM_BACKEND=ollama 시 Ollama 서버, 아니면 Hugging Face 사용
    """
    query_preview = request.query[:50] + "..." if len(request.query) > 50 else request.query
    logger.info("Infer request: query=%s", repr(query_preview))

    settings = get_settings()

    try:
        if settings.llm_backend == "ollama":
            from ollama_service import generate_with_ollama

            generated_text = await generate_with_ollama(
                query=request.query,
                max_length=request.max_length,
                temperature=request.temperature,
                top_p=request.top_p or 1.0,
            )
        else:
            from llm_service import generate

            generated_text = generate(
                query=request.query,
                max_length=request.max_length,
                temperature=request.temperature,
                top_p=request.top_p or 1.0,
                num_return_sequences=request.num_return_sequences,
            )
    except Exception as exc:
        fallback = settings.llm_fallback_response
        if fallback:
            logger.warning("LLM failed: %s, using fallback response", exc)
            generated_text = fallback
        else:
            raise

    logger.info("Infer response: length=%d", len(generated_text))
    return InferResponse(generated_text=generated_text)


@app.post("/infer/medical", response_model=InferResponse)
async def infer_medical(request: InferRequest) -> InferResponse:
    """
    의학지식 데이터 기반 LLM 추론
    1. MySQL에서 관련 의학 데이터 실시간 조회
    2. 시스템 프롬프트 + 의학 컨텍스트 + 사용자 질문 조합
    3. Ollama Chat API 호출
    """
    query_preview = request.query[:50] + "..." if len(request.query) > 50 else request.query
    logger.info("Medical infer request: query=%s", repr(query_preview))

    settings = get_settings()

    # (1) 의학 컨텍스트 조회
    medical_context = await build_medical_context(request.query)
    logger.info("Medical context: %d chars", len(medical_context))

    # (2) 프롬프트 조합
    system_prompt = (
        "당신은 전문 의학 AI 어시스턴트입니다.\n"
        "아래 참고 자료를 기반으로 정확하고 신뢰할 수 있는 의학 정보를 제공하세요.\n"
        "참고 자료에 없는 내용은 일반 의학 지식으로 답변하되, "
        "확실하지 않은 경우 '전문의 상담을 권장합니다'라고 안내하세요.\n"
        "항상 한국어로 답변하세요."
    )

    messages = [{"role": "system", "content": system_prompt}]
    if medical_context:
        messages.append({"role": "system", "content": medical_context})
    messages.append({"role": "user", "content": request.query})

    # (3) Ollama Chat API 호출
    payload = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": request.temperature,
            "num_predict": request.max_length,
        },
    }

    async with httpx.AsyncClient(timeout=float(settings.llm_infer_timeout_sec)) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/chat",
            json=payload,
        )
        response.raise_for_status()
        result = response.json()
        generated_text = result.get("message", {}).get("content", "")

    logger.info("Medical infer response: length=%d", len(generated_text))
    return InferResponse(generated_text=generated_text)


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)
