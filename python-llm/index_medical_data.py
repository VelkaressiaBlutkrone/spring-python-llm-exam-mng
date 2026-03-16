"""
MySQL 의학 데이터 → ChromaDB 벡터 인덱싱 스크립트

사용법:
    python index_medical_data.py          # 증분 인덱싱 (기본)
    python index_medical_data.py --full   # 전체 재인덱싱

Ollama 임베딩 모델이 필요합니다:
    ollama pull nomic-embed-text
"""

import asyncio
import json
import logging
from pathlib import Path

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

INDEX_META_FILE = Path(__file__).parent / ".index_meta.json"


def load_index_meta() -> dict:
    """마지막 인덱싱 타임스탬프 로드"""
    if INDEX_META_FILE.exists():
        return json.loads(INDEX_META_FILE.read_text(encoding="utf-8"))
    return {}


def save_index_meta(meta: dict):
    """인덱싱 메타데이터 저장"""
    INDEX_META_FILE.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def fetch_medical_qa(settings, since: str | None = None) -> list[dict]:
    """MySQL에서 의학 Q&A 데이터 조회 (증분 지원)"""
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
            if since:
                cur.execute(
                    "SELECT id, department, q_type, question, answer FROM medical_qa "
                    "WHERE updated_at > %s OR created_at > %s",
                    (since, since),
                )
            else:
                cur.execute(
                    "SELECT id, department, q_type, question, answer FROM medical_qa"
                )
            return cur.fetchall()
    finally:
        conn.close()


def fetch_medical_content(settings, since: str | None = None) -> list[dict]:
    """MySQL에서 의학 콘텐츠 데이터 조회 (증분 지원)"""
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
            if since:
                cur.execute(
                    "SELECT id, c_id, source_spec, content, language FROM medical_content "
                    "WHERE language = 'ko' AND (updated_at > %s OR created_at > %s)",
                    (since, since),
                )
            else:
                cur.execute(
                    "SELECT id, c_id, source_spec, content, language FROM medical_content "
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
    """의학 콘텐츠 데이터를 청킹+임베딩하여 ChromaDB에 저장"""
    from chunker import chunk_text

    logger.info("Indexing %d content documents (with chunking)...", len(content_rows))

    # 모든 콘텐츠를 청크로 분할
    all_chunks = []
    for row in content_rows:
        content = row.get("content", "")
        if not content:
            continue
        chunks = chunk_text(content, chunk_size=800, overlap=200)
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "id": f"content_{row['id']}_chunk_{i}",
                "text": chunk,
                "metadata": {
                    "type": "content",
                    "source": row.get("source_spec", ""),
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "c_id": row.get("c_id", ""),
                },
            })

    logger.info("Content chunked: %d rows → %d chunks", len(content_rows), len(all_chunks))

    # 배치 임베딩 + 저장
    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch = all_chunks[i : i + BATCH_SIZE]
        texts = [c["text"] for c in batch]
        ids = [c["id"] for c in batch]
        metadatas = [c["metadata"] for c in batch]

        embeddings = await get_embeddings_batch(texts)
        add_documents(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)
        logger.info("  Indexed content chunk batch %d-%d", i + 1, i + len(batch))


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Medical data vector indexing")
    parser.add_argument("--full", action="store_true", help="Full re-index (ignore timestamps)")
    args = parser.parse_args()

    settings = get_settings()
    meta = load_index_meta()

    since = None
    if not args.full and meta.get("last_indexed_at"):
        since = meta["last_indexed_at"]
        logger.info("Incremental indexing since %s", since)
    else:
        logger.info("Full indexing mode")

    logger.info("=== Medical Data Vector Indexing ===")
    logger.info("Ollama: %s, Embed model: %s", settings.ollama_base_url, settings.ollama_embed_model)
    logger.info("ChromaDB: %s:%d / %s", settings.chroma_host, settings.chroma_port, settings.chroma_collection)

    # Fetch with optional since filter
    qa_rows = fetch_medical_qa(settings, since=since)
    content_rows = fetch_medical_content(settings, since=since)
    logger.info("Fetched: %d Q&A, %d content rows", len(qa_rows), len(content_rows))

    if not qa_rows and not content_rows:
        logger.info("No new data to index")
        return

    if qa_rows:
        await index_qa_data(qa_rows)
    if content_rows:
        await index_content_data(content_rows)

    # Save timestamp
    from datetime import datetime
    meta["last_indexed_at"] = datetime.now().isoformat()
    meta["last_qa_count"] = len(qa_rows)
    meta["last_content_count"] = len(content_rows)
    save_index_meta(meta)

    total = get_document_count()
    logger.info("=== Indexing complete: %d total documents ===", total)


if __name__ == "__main__":
    asyncio.run(main())
