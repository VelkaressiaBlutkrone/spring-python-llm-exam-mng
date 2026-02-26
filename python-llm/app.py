"""
LLM 추론 서버 - FastAPI 앱
PRD 기반: Spring Boot에서 HTTP 호출, RAG 없이 순수 LLM 추론
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings
from llm_service import generate
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


@app.get("/")
def root():
    """루트: 서버 상태 확인"""
    return {"status": "ok", "message": "LLM Inference API"}


@app.get("/health")
def health():
    """헬스체크 엔드포인트"""
    return {"status": "healthy"}


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
def infer(request: InferRequest) -> InferResponse:
    """
    LLM 추론: 쿼리 입력 → 생성 응답 반환
    Spring Boot /api/llm/query 에서 호출
    """
    query_preview = request.query[:50] + "..." if len(request.query) > 50 else request.query
    logger.info("Infer request: query=%s", repr(query_preview))

    try:
        generated_text = generate(
            query=request.query,
            max_length=request.max_length,
            temperature=request.temperature,
            top_p=request.top_p or 1.0,
            num_return_sequences=request.num_return_sequences,
        )
    except Exception as exc:
        fallback = get_settings().llm_fallback_response
        if fallback:
            logger.warning("LLM failed: %s, using fallback response", exc)
            generated_text = fallback
        else:
            raise

    logger.info("Infer response: length=%d", len(generated_text))
    return InferResponse(generated_text=generated_text)


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)
