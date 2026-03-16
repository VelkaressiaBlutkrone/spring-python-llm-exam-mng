"""
병원규칙 RAG 벡터 검색 -> LLM 컨텍스트 주입 서비스
medical_rules 전용 컬렉션 사용
벡터 검색 실패/미인덱싱 시 MySQL medical_rule 테이블로 폴백
"""

import logging
import re

import aiomysql

from config import get_settings

logger = logging.getLogger(__name__)


def _extract_keywords(query: str) -> list[str]:
    """질문에서 2글자 이상 한국어/영어 키워드 추출 (최대 8개)"""
    words = re.findall(r"[가-힣a-zA-Z]{2,}", query)
    return words[:8] if words else []


async def _get_pool() -> aiomysql.Pool:
    """MySQL 커넥션 풀 (medical_context_service와 동일)"""
    from medical_context_service import get_pool
    return await get_pool()


async def search_medical_rule_mysql(query: str, limit: int = 5) -> list[dict]:
    """
    MySQL medical_rule 테이블에서 병원규칙 검색 (벡터 검색 폴백)
    FULLTEXT 인덱스 없으면 LIKE 검색 사용
    """
    try:
        pool = await _get_pool()
        keywords = _extract_keywords(query)

        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                if keywords:
                    # LIKE 검색: content 또는 title에 키워드 포함
                    conditions = []
                    params = []
                    for kw in keywords:
                        like_val = f"%{kw}%"
                        conditions.append("(content LIKE %s OR title LIKE %s OR category LIKE %s)")
                        params.extend([like_val, like_val, like_val])
                    params.append(limit)
                    sql = f"""
                        SELECT id, category, title, content, target
                        FROM medical_rule
                        WHERE {" OR ".join(conditions)}
                        ORDER BY id DESC
                        LIMIT %s
                    """
                    await cur.execute(sql, params)
                else:
                    # 키워드 없으면 최근 규칙 조회
                    search_term = query[:30] if query else ""
                    if search_term:
                        await cur.execute(
                            """
                            SELECT id, category, title, content, target
                            FROM medical_rule
                            WHERE content LIKE %s OR title LIKE %s
                            ORDER BY id DESC
                            LIMIT %s
                            """,
                            (f"%{search_term}%", f"%{search_term}%", limit),
                        )
                    else:
                        await cur.execute(
                            """
                            SELECT id, category, title, content, target
                            FROM medical_rule
                            ORDER BY id DESC
                            LIMIT %s
                            """,
                            (limit,),
                        )
                rows = await cur.fetchall()

        if rows:
            logger.info("Rule MySQL fallback: %d results (query: %s...)", len(rows), query[:30])
        return rows
    except Exception as exc:
        logger.warning("Rule MySQL search failed: %s: %s", type(exc).__name__, exc)
        return []


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


def _format_rule_item(item: dict, is_vector: bool) -> list[str]:
    """벡터/MySQL 검색 결과를 컨텍스트 형식으로 변환"""
    parts = []
    if is_vector:
        meta = item.get("metadata", {})
        category = meta.get("category", "")
        title = meta.get("title", "")
        target = meta.get("target", "")
        doc = item.get("document", "")[:800]
    else:
        category = item.get("category", "")
        title = item.get("title", "")
        target = item.get("target", "")
        content = item.get("content", "")
        doc = f"카테고리: {category}\n규칙명: {title}\n내용: {content}"[:800]
    if category:
        parts.append(f"카테고리: {category}")
    if title:
        parts.append(f"규칙명: {title}")
    if target:
        parts.append(f"적용 대상: {target}")
    parts.append(doc)
    parts.append("")
    return parts


async def build_rule_context(query: str) -> str:
    """
    사용자 질문에 대한 병원규칙 컨텍스트 빌드
    하이브리드: ChromaDB 벡터 검색 우선 → MySQL 폴백
    실패 시 빈 문자열 반환
    """
    try:
        settings = get_settings()
        parts = []

        # 1. ChromaDB 벡터 검색 시도
        results = await search_rule_vector_store(query, top_k=settings.vector_search_top_k)

        # 2. 벡터 결과 없으면 MySQL 폴백 (index_rule_data 미실행 또는 ChromaDB 장애 시)
        if not results:
            mysql_rows = await search_medical_rule_mysql(query, limit=settings.vector_search_top_k)
            if mysql_rows:
                for row in mysql_rows:
                    parts.extend(_format_rule_item(row, is_vector=False))
        else:
            for item in results:
                parts.extend(_format_rule_item(item, is_vector=True))

        if parts:
            parts.insert(0, "[참고: 병원 규칙 검색 결과]")
            parts.insert(1, "")

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
