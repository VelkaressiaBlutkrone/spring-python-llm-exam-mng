"""
텍스트 청킹 모듈
긴 텍스트를 오버랩하는 청크로 분할하여 벡터 검색 품질을 높인다.
"""

import logging

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 200, min_chunk_size: int = 100) -> list[str]:
    """
    텍스트를 겹치는 청크로 분할한다.

    Args:
        text: 원본 텍스트
        chunk_size: 청크 최대 크기 (문자 수)
        overlap: 청크 간 겹치는 문자 수
        min_chunk_size: 최소 청크 크기 (이보다 짧으면 이전 청크에 합침)

    Returns:
        청크 리스트
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end >= len(text):
            # 마지막 청크
            chunk = text[start:]
            if chunks and len(chunk) < min_chunk_size:
                # 너무 짧으면 이전 청크에 합침 (오버랩은 start 계산에서 이미 반영됨)
                chunks[-1] = chunks[-1] + chunk
            else:
                chunks.append(chunk)
            break

        chunk = text[start:end]

        # 문장 경계에서 자르기 (마침표, 줄바꿈)
        for sep in ["\n\n", "\n", ". ", "。"]:
            last_sep = chunk.rfind(sep)
            if last_sep > chunk_size * 0.5:
                chunk = chunk[:last_sep + len(sep)]
                end = start + last_sep + len(sep)
                break

        chunks.append(chunk)
        start = end - overlap

    logger.debug("Chunked %d chars → %d chunks (size=%d, overlap=%d)", len(text), len(chunks), chunk_size, overlap)
    return chunks
