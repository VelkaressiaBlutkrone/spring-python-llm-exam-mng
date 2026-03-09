"""
의학지식 데이터 실시간 조회 -> LLM 컨텍스트 주입 서비스
MySQL FULLTEXT 검색(ngram)을 활용하여 사용자 질문과 관련된
의학 Q&A 및 원천 콘텐츠를 조회하고, LLM 프롬프트용 컨텍스트를 생성합니다.
"""

import logging
import re

import aiomysql

from config import get_settings

logger = logging.getLogger(__name__)

_pool = None


async def get_pool() -> aiomysql.Pool:
    """MySQL 커넥션 풀 (싱글톤)"""
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = await aiomysql.create_pool(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            db=settings.mysql_db,
            charset="utf8mb4",
            minsize=2,
            maxsize=10,
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


async def build_medical_context(query: str) -> str:
    """
    사용자 질문에 대한 의학 컨텍스트 빌드
    Q&A + 원천데이터를 조합하여 LLM 프롬프트용 컨텍스트 생성
    """
    parts = []

    # 1. 관련 Q&A 검색
    qa_results = await search_medical_qa(query, limit=3)
    if qa_results:
        parts.append("[참고: 관련 의학 Q&A]")
        for qa in qa_results:
            parts.append(f"진료과: {qa['department']}")
            parts.append(f"Q: {qa['question'][:500]}")
            parts.append(f"A: {qa['answer'][:500]}")
            parts.append("")

    # 2. 관련 의학 콘텐츠 검색
    content_results = await search_medical_content(query, limit=2)
    if content_results:
        parts.append("[참고: 관련 의학 지식]")
        for c in content_results:
            source = c.get("source_spec", "")
            parts.append(f"출처: {source}")
            parts.append(f"{c['content'][:800]}")
            parts.append("")

    context = "\n".join(parts) if parts else ""

    # 컨텍스트 길이 제한 (프롬프트 최적화)
    settings = get_settings()
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
