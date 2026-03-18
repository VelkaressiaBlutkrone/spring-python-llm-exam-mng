"""
병원규칙 JSON -> MySQL + ChromaDB 벡터 인덱싱 스크립트

사용법:
    python index_rule_data.py

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
from rule_context_service import add_rule_documents, get_rule_document_count

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

JSON_PATH = Path(__file__).parent.parent / "llm_data" / "medical_rules.json"
BATCH_SIZE = 10


def load_json_rules() -> list[dict]:
    """JSON 파일에서 병원규칙 데이터 로드"""
    with open(JSON_PATH, encoding="utf-8") as f:
        return json.load(f)


def import_to_mysql(rules: list[dict], settings) -> list[dict]:
    """
    MySQL medical_rule 테이블에 데이터 import
    중복 체크: title 기준으로 이미 존재하면 skip
    반환: 실제 insert된 규칙 리스트 (with id)
    """
    conn = pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        db=settings.mysql_db,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    inserted = []
    skipped = 0
    try:
        with conn.cursor() as cur:
            for rule in rules:
                # 중복 체크
                cur.execute(
                    "SELECT id FROM medical_rule WHERE title = %s",
                    (rule["title"],),
                )
                existing = cur.fetchone()
                if existing:
                    logger.info("Skip duplicate: %s (id=%d)", rule["title"], existing["id"])
                    skipped += 1
                    continue

                cur.execute(
                    """
                    INSERT INTO medical_rule (category, title, content, target, start_date, end_date, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (
                        rule["category"],
                        rule["title"],
                        rule["content"],
                        rule.get("target", ""),
                        rule.get("start_date"),
                        rule.get("end_date"),
                    ),
                )
                rule["id"] = cur.lastrowid
                inserted.append(rule)
                logger.info("Inserted: %s (id=%d)", rule["title"], rule["id"])

            conn.commit()
    finally:
        conn.close()

    logger.info("MySQL import: %d new, %d existing", len(inserted), skipped)
    return inserted


async def index_to_chromadb(rules: list[dict]):
    """병원규칙 데이터를 임베딩하여 ChromaDB에 저장"""
    logger.info("Indexing %d rule documents to ChromaDB...", len(rules))

    for i in range(0, len(rules), BATCH_SIZE):
        batch = rules[i : i + BATCH_SIZE]

        texts = []
        ids = []
        metadatas = []
        for rule in batch:
            text = (
                f"카테고리: {rule['category']}\n"
                f"규칙명: {rule['title']}\n"
                f"내용: {rule['content']}"
            )
            texts.append(text)
            ids.append(f"rule_{rule['id']}")
            metadatas.append({
                "type": "rule",
                "category": rule["category"],
                "title": rule["title"],
                "target": rule.get("target", ""),
                "start_date": rule.get("start_date", ""),
                "end_date": rule.get("end_date", ""),
            })

        embeddings = await get_embeddings_batch(texts)
        add_rule_documents(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)
        logger.info("  Indexed rule batch %d-%d", i + 1, i + len(batch))


async def main():
    settings = get_settings()
    logger.info("=== Medical Rule Data Import & Indexing ===")
    logger.info("JSON source: %s", JSON_PATH)
    logger.info("Ollama: %s, Embed model: %s", settings.ollama_base_url, settings.ollama_embed_model)
    logger.info("ChromaDB: %s:%d / %s (rules: %s)", settings.chroma_host, settings.chroma_port, settings.chroma_collection, settings.chroma_rule_collection)

    # 1. JSON 로드
    rules = load_json_rules()
    logger.info("Loaded %d rules from JSON", len(rules))

    # 2. MySQL import
    rules_with_ids = import_to_mysql(rules, settings)
    logger.info("MySQL import complete: %d rules", len(rules_with_ids))

    # 3. ChromaDB 인덱싱
    if rules_with_ids:
        await index_to_chromadb(rules_with_ids)

    total = get_rule_document_count()
    logger.info("=== Indexing complete: %d total rule documents in vector store ===", total)


if __name__ == "__main__":
    asyncio.run(main())
