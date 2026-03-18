"""
의학지식 데이터 실시간 조회 -> LLM 컨텍스트 주입 서비스
MySQL FULLTEXT 검색(ngram)을 활용하여 사용자 질문과 관련된
의학 Q&A 및 원천 콘텐츠를 조회하고, LLM 프롬프트용 컨텍스트를 생성합니다.
"""

import asyncio
import logging
import re

import aiomysql

from config import get_settings

logger = logging.getLogger(__name__)

_pool = None
_pool_lock = asyncio.Lock()


async def get_pool() -> aiomysql.Pool:
    """MySQL 커넥션 풀 (싱글톤, asyncio.Lock으로 이중 초기화 방지)"""
    global _pool
    if _pool is not None:
        return _pool
    async with _pool_lock:
        if _pool is None:
            settings = get_settings()
            _pool = await aiomysql.create_pool(
                host=settings.mysql_host,
                port=settings.mysql_port,
                user=settings.mysql_user,
                password=settings.mysql_password,
                db=settings.mysql_db,
                charset="utf8mb4",
                minsize=0,
                maxsize=10,
                connect_timeout=10,
            )
    return _pool


async def close_pool():
    """앱 종료 시 커넥션 풀 정리"""
    global _pool
    if _pool is not None:
        _pool.close()
        await _pool.wait_closed()
        _pool = None


def extract_keywords(query: str) -> str:
    """
    질문에서 FULLTEXT 검색용 키워드 추출
    - 2글자 이상 한국어/영어 단어만 추출
    - Boolean Mode 형식으로 변환 (+word AND 검색)
    """
    words = re.findall(r"[가-힣a-zA-Z]{2,}", query)
    if not words:
        return ""
    # Boolean mode: 각 단어를 +로 연결 (AND 검색), 최대 8개
    return " ".join(f"+{w}" for w in words[:8])


async def search_medical_qa(query: str, limit: int = 5) -> list[dict]:
    """
    사용자 질문과 관련된 의학 Q&A 검색
    MySQL FULLTEXT 인덱스 활용 (ngram)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            keywords = extract_keywords(query)
            if keywords:
                await cur.execute(
                    """
                    SELECT department, q_type, question, answer,
                           MATCH(question) AGAINST(%s IN BOOLEAN MODE) AS relevance
                    FROM medical_qa
                    WHERE MATCH(question) AGAINST(%s IN BOOLEAN MODE)
                    ORDER BY relevance DESC
                    LIMIT %s
                    """,
                    (keywords, keywords, limit),
                )
            else:
                # 키워드 추출 실패 시 LIKE 검색
                search_term = query[:30]
                await cur.execute(
                    """
                    SELECT department, q_type, question, answer
                    FROM medical_qa
                    WHERE question LIKE %s
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (f"%{search_term}%", limit),
                )
            return await cur.fetchall()


async def search_medical_content(
    query: str, language: str = "ko", limit: int = 3
) -> list[dict]:
    """
    사용자 질문과 관련된 의학 원천 콘텐츠 검색
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            keywords = extract_keywords(query)
            if keywords:
                await cur.execute(
                    """
                    SELECT c_id, source_spec, content,
                           MATCH(content) AGAINST(%s IN BOOLEAN MODE) AS relevance
                    FROM medical_content
                    WHERE language = %s
                      AND MATCH(content) AGAINST(%s IN BOOLEAN MODE)
                    ORDER BY relevance DESC
                    LIMIT %s
                    """,
                    (keywords, language, keywords, limit),
                )
            else:
                await cur.execute(
                    """
                    SELECT c_id, source_spec, content
                    FROM medical_content
                    WHERE language = %s
                    ORDER BY RAND()
                    LIMIT %s
                    """,
                    (language, limit),
                )
            return await cur.fetchall()


async def search_vector_store(query: str, top_k: int = 3) -> list[dict]:
    """
    ChromaDB 벡터 검색으로 의미적으로 유사한 문서 조회

    Args:
        query: 사용자 질문
        top_k: 상위 결과 수

    Returns:
        검색 결과 리스트
    """
    settings = get_settings()
    if not settings.use_vector_search:
        return []

    try:
        from embedding_service import get_embedding
        from vector_store import get_document_count, search_similar

        doc_count = get_document_count()
        if doc_count == 0:
            logger.warning(
                "Vector store is empty. Run 'python index_medical_data.py' to index data. "
                "Also ensure 'ollama pull %s' has been executed.",
                settings.ollama_embed_model,
            )
            return []

        query_embedding = await get_embedding(query)
        results = search_similar(query_embedding, top_k=top_k)
        logger.info("Vector search: %d results from %d docs (query: %s...)", len(results), doc_count, query[:30])
        return results
    except ImportError as exc:
        logger.warning("Vector search dependencies not available: %s", exc)
        return []
    except Exception as exc:
        logger.warning("Vector search failed (falling back to FULLTEXT): %s: %s", type(exc).__name__, exc)
        return []


async def build_medical_context(query: str, client=None) -> str:
    """
    사용자 질문에 대한 의학 컨텍스트 빌드
    하이브리드 검색: MySQL FULLTEXT + ChromaDB 벡터 검색 결합
    3개 검색을 asyncio.gather로 병렬 실행
    """
    settings = get_settings()

    # 쿼리 확장 (활성화된 경우)
    from query_expander import expand_query
    search_query = await expand_query(query, client=client)

    # 3개 검색을 병렬로 동시 실행
    vector_results, qa_results, content_results = await asyncio.gather(
        search_vector_store(search_query, top_k=settings.vector_search_top_k),
        search_medical_qa(search_query, limit=3),
        search_medical_content(search_query, limit=2),
        return_exceptions=True,
    )

    # 예외 발생 시 빈 리스트로 대체
    if isinstance(vector_results, Exception):
        logger.warning("Vector search failed in gather: %s", vector_results)
        vector_results = []
    if isinstance(qa_results, Exception):
        logger.warning("QA search failed in gather: %s", qa_results)
        qa_results = []
    if isinstance(content_results, Exception):
        logger.warning("Content search failed in gather: %s", content_results)
        content_results = []

    # Re-ranking: 벡터 검색 결과 재정렬
    if settings.use_reranking and vector_results and len(vector_results) > 1:
        from reranker import rerank_results
        vector_results = await rerank_results(
            query=search_query,
            results=vector_results,
            top_k=settings.vector_search_top_k,
            client=client,
        )

    parts = []

    # 1. 벡터 검색 결과 (의미 기반)
    if vector_results:
        parts.append("[참고: 벡터 검색 결과 (의미 유사도)]")
        for item in vector_results:
            meta = item.get("metadata", {})
            doc_type = meta.get("type", "")
            if doc_type == "qa":
                dept = meta.get("department", "")
                if dept:
                    parts.append(f"진료과: {dept}")
            elif doc_type == "content":
                source = meta.get("source", "")
                if source:
                    parts.append(f"출처: {source}")
            parts.append(item["document"][:500])
            parts.append("")

    # 2. 벡터 결과 부족 시 FULLTEXT Q&A 보완
    if len(vector_results) < 2 and qa_results:
        parts.append("[참고: 관련 의학 Q&A]")
        for qa in qa_results:
            parts.append(f"진료과: {qa['department']}")
            parts.append(f"Q: {qa['question'][:500]}")
            parts.append(f"A: {qa['answer'][:500]}")
            parts.append("")

    # 3. 벡터 결과 없으면 콘텐츠도 보완
    if len(vector_results) < 1 and content_results:
        parts.append("[참고: 관련 의학 지식]")
        for c in content_results:
            source = c.get("source_spec", "")
            parts.append(f"출처: {source}")
            parts.append(f"{c['content'][:800]}")
            parts.append("")

    context = "\n".join(parts) if parts else ""

    # 컨텍스트 길이 제한 (프롬프트 최적화)
    max_chars = settings.medical_context_max_chars
    if len(context) > max_chars:
        # 마지막 완전한 줄 기준으로 자르기
        truncated = context[:max_chars]
        last_newline = truncated.rfind("\n")
        if last_newline > 0:
            context = truncated[:last_newline]
        else:
            context = truncated
        logger.info("Medical context truncated: %d → %d chars", len("\n".join(parts)), len(context))

    return context
