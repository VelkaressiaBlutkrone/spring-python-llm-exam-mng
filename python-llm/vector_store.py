"""
ChromaDB 벡터 저장소
Ollama 임베딩 + ChromaDB로 의학 문서 벡터 검색
"""

import logging

import chromadb

from config import get_settings

logger = logging.getLogger(__name__)

_client = None
_collection = None
_rule_collection = None


def get_chroma_client() -> chromadb.ClientAPI:
    """ChromaDB 클라이언트 싱글톤 (Docker HttpClient)"""
    global _client
    if _client is None:
        settings = get_settings()
        _client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
        logger.info("ChromaDB connected: %s:%d", settings.chroma_host, settings.chroma_port)
    return _client


def get_collection() -> chromadb.Collection:
    """의학 문서 컬렉션 조회/생성"""
    global _collection
    if _collection is None:
        settings = get_settings()
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "ChromaDB collection '%s': %d documents",
            settings.chroma_collection,
            _collection.count(),
        )
    return _collection


def get_rule_collection() -> chromadb.Collection:
    """병원규칙 전용 컬렉션 조회/생성"""
    global _rule_collection
    if _rule_collection is None:
        settings = get_settings()
        client = get_chroma_client()
        _rule_collection = client.get_or_create_collection(
            name=settings.chroma_rule_collection,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "ChromaDB rule collection '%s': %d documents",
            settings.chroma_rule_collection,
            _rule_collection.count(),
        )
    return _rule_collection


def add_documents(
    ids: list[str],
    documents: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict] | None = None,
):
    """
    벡터 저장소에 문서 추가

    Args:
        ids: 문서 ID 리스트
        documents: 원본 텍스트 리스트
        embeddings: 임베딩 벡터 리스트
        metadatas: 메타데이터 리스트 (선택)
    """
    collection = get_collection()
    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    logger.info("Added/updated %d documents to vector store", len(ids))


def search_similar(
    query_embedding: list[float],
    top_k: int = 3,
) -> list[dict]:
    """
    쿼리 임베딩과 유사한 문서 검색

    Args:
        query_embedding: 쿼리 임베딩 벡터
        top_k: 반환할 상위 결과 수

    Returns:
        검색 결과 리스트 [{document, metadata, distance}, ...]
    """
    collection = get_collection()

    if collection.count() == 0:
        logger.warning("Vector store is empty, skipping search")
        return []

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
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

    return items


def get_document_count() -> int:
    """저장된 문서 수 조회"""
    return get_collection().count()
