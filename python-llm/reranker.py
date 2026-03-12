"""
검색 결과 Re-ranking 모듈
Ollama LLM을 활용한 경량 관련성 재정렬
"""

import logging
import re

from config import get_settings

logger = logging.getLogger(__name__)


async def rerank_results(
    query: str,
    results: list[dict],
    top_k: int = 3,
    client=None,
) -> list[dict]:
    """
    검색 결과를 쿼리 관련성 기준으로 재정렬한다.

    Ollama를 사용하여 각 결과의 관련성 점수(0-10)를 평가하고
    상위 top_k개만 반환한다.

    Args:
        query: 사용자 질문
        results: 검색 결과 리스트 (각각 "document" 키 필수)
        top_k: 반환할 상위 결과 수
        client: 공유 httpx 클라이언트

    Returns:
        관련성 점수 기준 정렬된 상위 결과 리스트
    """
    settings = get_settings()

    if not results or len(results) <= 1:
        return results[:top_k]

    # Re-ranking이 비활성화되면 원본 그대로 반환
    if not getattr(settings, 'use_reranking', False):
        return results[:top_k]

    try:
        from ollama_service import generate_with_ollama

        scored = []
        for item in results:
            doc_text = item.get("document", "")[:300]
            prompt = (
                f"질문: {query}\n"
                f"문서: {doc_text}\n"
                "이 문서가 질문에 얼마나 관련 있는지 0~10 점수만 숫자로 답하세요:"
            )
            try:
                score_text = await generate_with_ollama(
                    query=prompt,
                    max_length=5,
                    temperature=0.1,
                    client=client,
                )
                # 숫자만 추출
                match = re.search(r"(\d+)", score_text.strip())
                score = int(match.group(1)) if match else 5
                score = min(max(score, 0), 10)
            except Exception:
                score = 5  # 평가 실패 시 중간 점수

            scored.append({**item, "_rerank_score": score})

        # 점수 내림차순 정렬
        scored.sort(key=lambda x: x["_rerank_score"], reverse=True)
        logger.info(
            "Reranked %d results for query '%s...' (top scores: %s)",
            len(scored), query[:30],
            [s["_rerank_score"] for s in scored[:top_k]]
        )
        return scored[:top_k]

    except Exception as exc:
        logger.warning("Reranking failed (using original order): %s", exc)
        return results[:top_k]
