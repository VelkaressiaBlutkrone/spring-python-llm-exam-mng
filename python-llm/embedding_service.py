"""
Ollama 임베딩 서비스
Ollama /api/embed API를 사용하여 텍스트를 벡터로 변환
"""

import logging

import httpx

from config import get_settings

logger = logging.getLogger(__name__)


async def get_embedding(text: str) -> list[float]:
    """
    Ollama 임베딩 API로 텍스트를 벡터로 변환

    Args:
        text: 임베딩할 텍스트

    Returns:
        임베딩 벡터 (float 리스트)
    """
    settings = get_settings()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
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


async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """
    여러 텍스트를 한 번에 임베딩

    Args:
        texts: 임베딩할 텍스트 리스트

    Returns:
        임베딩 벡터 리스트
    """
    settings = get_settings()

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/embed",
            json={
                "model": settings.ollama_embed_model,
                "input": texts,
            },
        )
        response.raise_for_status()
        result = response.json()
        return result.get("embeddings", [])
