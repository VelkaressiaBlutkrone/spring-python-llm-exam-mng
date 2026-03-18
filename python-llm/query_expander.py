"""
쿼리 확장 모듈
짧은 구어체 질문을 의학 용어로 확장하여 벡터/FULLTEXT 검색 재현율을 높인다.
"""

import logging

from config import get_settings

logger = logging.getLogger(__name__)


async def expand_query(original: str, client=None) -> str:
    """
    LLM으로 검색 키워드를 확장한다 (저비용 호출)

    Args:
        original: 원본 사용자 질문
        client: 공유 httpx 클라이언트 (선택)

    Returns:
        확장된 쿼리 문자열 (원본 + 관련 키워드)
    """
    settings = get_settings()

    if not settings.use_query_expansion:
        return original

    try:
        prompt = (
            f"사용자 질문: {original}\n"
            "이 질문과 관련된 의학 용어, 진료과, 증상, 질병명을 5개 나열하세요. "
            "콤마로 구분, 설명 없이 키워드만:"
        )

        if settings.llm_backend == "vllm":
            from vllm_service import generate_with_vllm
            keywords = await generate_with_vllm(
                query=prompt,
                max_length=50,
                temperature=0.3,
                client=client,
            )
        else:
            from ollama_service import generate_with_ollama
            keywords = await generate_with_ollama(
                query=prompt,
                max_length=50,
                temperature=0.3,
                client=client,
            )

        expanded = f"{original} {keywords.strip()}"
        logger.info("Query expanded: '%s' → '%s'", original[:30], expanded[:80])
        return expanded
    except Exception as exc:
        logger.warning("Query expansion failed (using original): %s", exc)
        return original
