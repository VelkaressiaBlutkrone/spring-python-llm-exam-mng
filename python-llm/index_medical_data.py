"""
MySQL 의학 데이터 → ChromaDB 벡터 인덱싱 스크립트

사용법:
    python index_medical_data.py

Ollama 임베딩 모델이 필요합니다:
    ollama pull nomic-embed-text
"""

import asyncio
import logging

import pymysql

from config import get_settings
from embedding_service import get_embeddings_batch
from vector_store import add_documents, get_document_count

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

BATCH_SIZE = 20


def fetch_medical_qa(settings) -> list[dict]:
    """MySQL에서 의학 Q&A 데이터 조회"""
    conn = pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        db=settings.mysql_db,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, department, q_type, question, answer FROM medical_qa"
            )
            return cur.fetchall()
    finally:
        conn.close()


def fetch_medical_content(settings) -> list[dict]:
    """MySQL에서 의학 콘텐츠 데이터 조회"""
    conn = pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        db=settings.mysql_db,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT c_id, source_spec, content, language FROM medical_content "
                "WHERE language = 'ko'"
            )
            return cur.fetchall()
    finally:
        conn.close()


async def index_qa_data(qa_rows: list[dict]):
    """Q&A 데이터를 임베딩하여 ChromaDB에 저장"""
    logger.info("Indexing %d Q&A documents...", len(qa_rows))

    for i in range(0, len(qa_rows), BATCH_SIZE):
        batch = qa_rows[i : i + BATCH_SIZE]

        # 임베딩할 텍스트: 질문 + 답변 결합
        texts = []
        ids = []
        metadatas = []
        for row in batch:
            text = f"질문: {row['question']}\n답변: {row['answer'][:500]}"
            texts.append(text)
            ids.append(f"qa_{row['id']}")
            metadatas.append({
                "type": "qa",
                "department": row.get("department", ""),
                "q_type": row.get("q_type", ""),
                "question": row["question"][:200],
            })

        embeddings = await get_embeddings_batch(texts)
        add_documents(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)
        logger.info("  Indexed Q&A batch %d-%d", i + 1, i + len(batch))


async def index_content_data(content_rows: list[dict]):
    """의학 콘텐츠 데이터를 임베딩하여 ChromaDB에 저장"""
    logger.info("Indexing %d content documents...", len(content_rows))

    for i in range(0, len(content_rows), BATCH_SIZE):
        batch = content_rows[i : i + BATCH_SIZE]

        texts = []
        ids = []
        metadatas = []
        for row in batch:
            text = row["content"][:1000]
            texts.append(text)
            ids.append(f"content_{row['c_id']}")
            metadatas.append({
                "type": "content",
                "source": row.get("source_spec", ""),
            })

        embeddings = await get_embeddings_batch(texts)
        add_documents(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)
        logger.info("  Indexed content batch %d-%d", i + 1, i + len(batch))


async def main():
    settings = get_settings()
    logger.info("=== Medical Data Vector Indexing ===")
    logger.info("Ollama: %s, Embed model: %s", settings.ollama_base_url, settings.ollama_embed_model)
    logger.info("ChromaDB: %s / %s", settings.chroma_persist_dir, settings.chroma_collection)

    # MySQL에서 데이터 조회
    qa_rows = fetch_medical_qa(settings)
    content_rows = fetch_medical_content(settings)
    logger.info("Fetched: %d Q&A, %d content rows", len(qa_rows), len(content_rows))

    # ChromaDB에 인덱싱
    if qa_rows:
        await index_qa_data(qa_rows)
    if content_rows:
        await index_content_data(content_rows)

    total = get_document_count()
    logger.info("=== Indexing complete: %d total documents in vector store ===", total)


if __name__ == "__main__":
    asyncio.run(main())
