"""
LLM 모델 로딩 및 추론 서비스
Hugging Face Transformers pipeline 사용
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from config import get_settings

logger = logging.getLogger(__name__)

# 싱글톤: 앱 시작 시 1회 로딩
_generator = None


def load_model():
    """모델 로딩 (1회만 실행)"""
    global _generator
    if _generator is not None:
        return _generator

    settings = get_settings()
    try:
        from transformers import pipeline

        logger.info("Loading LLM model: %s", settings.llm_model)
        _generator = pipeline(
            "text-generation",
            model=settings.llm_model,
            trust_remote_code=True,
        )
        logger.info("Model loaded successfully")
        return _generator
    except OSError as e:
        # Windows torch DLL 오류 등: llm_fallback_mock 시 mock 사용
        logger.warning("Model load failed (OSError): %s", e)
        if settings.llm_fallback_mock:
            _generator = _MockGenerator()
            logger.warning("Using mock generator (llm_fallback_mock=True)")
            return _generator
        raise
    except Exception as e:
        logger.exception("Failed to load model: %s", e)
        raise


class _MockGenerator:
    """개발용 mock: torch 미지원 환경에서 동작"""

    def __init__(self):
        self.tokenizer = type("Token", (), {"eos_token_id": 0})()

    def __call__(self, query, **kwargs):
        return [{"generated_text": f"[Mock] {query} (LLM 모델 로딩 실패 시 mock 응답)"}]


def get_generator():
    """로딩된 generator 반환 (없으면 로딩)"""
    global _generator
    if _generator is None:
        _generator = load_model()
    return _generator


def _preprocess_query(query: str) -> str:
    """
    입력 텍스트 전처리
    - 앞뒤 공백 제거
    - 길이 제한 (과도한 입력 방지)
    - 연속 공백 정규화
    """
    if not query or not isinstance(query, str):
        return ""
    text = query.strip()
    text = re.sub(r"\s+", " ", text)
    max_len = get_settings().llm_input_max_length
    if len(text) > max_len:
        text = text[:max_len] + "..."
        logger.debug("Input truncated to %d chars", max_len)
    return text


def _postprocess_output(text: str) -> str:
    """
    출력 후처리
    - 연속 공백/탭 정규화
    - 연속 줄바꿈 2개로 제한
    - 앞뒤 공백 제거
    """
    if not text:
        return ""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _generate_internal(
    query: str,
    max_length: int,
    temperature: float,
    top_p: float,
    num_return_sequences: int,
) -> str:
    """내부 추론 로직 (타임아웃 없이)"""
    gen = get_generator()
    result = gen(
        query,
        max_length=max_length,
        temperature=temperature,
        top_p=top_p if top_p else 1.0,
        num_return_sequences=num_return_sequences,
        pad_token_id=gen.tokenizer.eos_token_id,
        do_sample=temperature > 0,
    )
    return result[0]["generated_text"]


def generate(
    query: str,
    max_length: int = 100,
    temperature: float = 0.7,
    top_p: float = 1.0,
    num_return_sequences: int = 1,
) -> str:
    """
    LLM 추론 수행 (전처리 → 추론 → 후처리, 타임아웃 적용)

    Args:
        query: 입력 텍스트
        max_length: 생성 최대 토큰 수
        temperature: 샘플링 온도
        top_p: nucleus sampling
        num_return_sequences: 생성 시퀀스 수

    Returns:
        생성된 텍스트 (첫 번째 시퀀스)

    Raises:
        TimeoutError: 추론이 LLM_INFER_TIMEOUT_SEC 초과 시
    """
    processed_query = _preprocess_query(query)
    if not processed_query:
        return ""

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            _generate_internal,
            processed_query,
            max_length,
            temperature,
            top_p,
            num_return_sequences,
        )
        timeout_sec = get_settings().llm_infer_timeout_sec
        try:
            raw_text = future.result(timeout=timeout_sec)
        except FuturesTimeoutError:
            logger.warning("Inference timeout after %d sec", timeout_sec)
            raise TimeoutError(f"LLM 추론 타임아웃 ({timeout_sec}초)")

    return _postprocess_output(raw_text)
