"""
병원규칙 RAG 벡터 검색 -> LLM 컨텍스트 주입 서비스
medical_rules 전용 컬렉션 사용
"""

import logging

from config import get_settings

logger = logging.getLogger(__name__)


def _get_collection():
    """병원규칙 전용 컬렉션 사용"""
    from vector_store import get_rule_collection
    return get_rule_collection()


def get_rule_document_count() -> int:
    """병원규칙 벡터 저장소 문서 수 조회"""
    try:
        col = _get_collection()
        return col.count()
    except Exception:
        return 0


def add_rule_documents(
    ids: list[str],
    documents: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict] | None = None,
):
    """병원규칙을 전용 컬렉션에 추가"""
    col = _get_collection()
    col.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
    logger.info("Added/updated %d rule documents to rule collection", len(ids))


async def search_rule_vector_store(query: str, top_k: int = 3) -> list[dict]:
    """ChromaDB 벡터 검색으로 관련 병원규칙 조회 (type=rule 필터)"""
    settings = get_settings()
    if not settings.use_vector_search:
        return []

    try:
        from embedding_service import get_embedding

        col = _get_collection()
        if col.count() == 0:
            return []

        query_embedding = await get_embedding(query)
        results = col.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, col.count()),
        )

        items = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                item = {
                    "document": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                }
                items.append(item)

        logger.info("Rule vector search: %d results (query: %s...)", len(items), query[:30])
        return items
    except Exception as exc:
        logger.warning("Rule vector search failed: %s: %s", type(exc).__name__, exc)
        return []


async def build_rule_context(query: str) -> str:
    """
    사용자 질문에 대한 병원규칙 컨텍스트 빌드
    실패 시 빈 문자열 반환 (일반 지식으로 답변)
    """
    try:
        settings = get_settings()
        parts = []

        results = await search_rule_vector_store(query, top_k=settings.vector_search_top_k)
        if results:
            parts.append("[참고: 병원 규칙 검색 결과]")
            for item in results:
                meta = item.get("metadata", {})
                category = meta.get("category", "")
                title = meta.get("title", "")
                target = meta.get("target", "")
                if category:
                    parts.append(f"카테고리: {category}")
                if title:
                    parts.append(f"규칙명: {title}")
                if target:
                    parts.append(f"적용 대상: {target}")
                parts.append(item["document"][:800])
                parts.append("")

        context = "\n".join(parts) if parts else ""

        max_chars = settings.medical_context_max_chars
        if len(context) > max_chars:
            truncated = context[:max_chars]
            last_newline = truncated.rfind("\n")
            if last_newline > 0:
                context = truncated[:last_newline]
            else:
                context = truncated

        return context
    except Exception as exc:
        logger.warning("build_rule_context failed: %s: %s", type(exc).__name__, exc)
        return ""
