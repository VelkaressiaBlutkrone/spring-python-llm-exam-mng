"""
Ollama 임베딩 서비스
Ollama /api/embed API를 사용하여 텍스트를 벡터로 변환
"""

import hashlib
import logging
from collections import OrderedDict

import httpx

from config import get_settings

logger = logging.getLogger(__name__)

_embedding_cache: OrderedDict[str, list[float]] = OrderedDict()
MAX_CACHE_SIZE = 500


async def get_embedding(text: str, client: httpx.AsyncClient | None = None) -> list[float]:
    """
    Ollama 임베딩 API로 텍스트를 벡터로 변환

    Args:
        text: 임베딩할 텍스트
        client: 공유 httpx 클라이언트 (None이면 자체 생성)

    Returns:
        임베딩 벡터 (float 리스트)
    """
    cache_key = hashlib.sha256(text.encode()).hexdigest()
    if cache_key in _embedding_cache:
        logger.debug("Embedding cache hit")
        return _embedding_cache[cache_key]

    settings = get_settings()

    async def _call(c: httpx.AsyncClient) -> list[float]:
        response = await c.post(
            f"{settings.ollama_base_url}/api/embed",
            json={
                "model": settings.ollama_embed_model,
                "input": text,
            },
        )
        response.raise_for_status()
        result = response.json()
        embeddings = result.get("embeddings", [])
        if embeddings:
            return embeddings[0]
        raise ValueError("임베딩 결과가 비어있습니다")

    if client is not None:
        embedding = await _call(client)
    else:
        async with httpx.AsyncClient(timeout=30.0) as _client:
            embedding = await _call(_client)

    if len(_embedding_cache) >= MAX_CACHE_SIZE:
        _embedding_cache.popitem(last=False)
    _embedding_cache[cache_key] = embedding
    return embedding


async def get_embeddings_batch(texts: list[str], client: httpx.AsyncClient | None = None) -> list[list[float]]:
    """
    여러 텍스트를 한 번에 임베딩

    Args:
        texts: 임베딩할 텍스트 리스트
        client: 공유 httpx 클라이언트 (None이면 자체 생성)

    Returns:
        임베딩 벡터 리스트
    """
    settings = get_settings()

    async def _call(c: httpx.AsyncClient) -> list[list[float]]:
        response = await c.post(
            f"{settings.ollama_base_url}/api/embed",
            json={
                "model": settings.ollama_embed_model,
                "input": texts,
            },
        )
        response.raise_for_status()
        result = response.json()
        return result.get("embeddings", [])

    if client is not None:
        return await _call(client)
    async with httpx.AsyncClient(timeout=60.0) as _client:
        return await _call(_client)
