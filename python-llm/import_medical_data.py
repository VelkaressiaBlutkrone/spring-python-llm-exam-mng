"""
llm_data/*.zip -> MySQL 적재 스크립트
중첩 ZIP 구조: outer.zip > inner.zip > *.json

실행:
    cd python-llm
    pip install pymysql
    python import_medical_data.py
"""

import json
import logging
import os
import re
import sys
import zipfile
from io import BytesIO

import pymysql

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3307")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "db": os.getenv("MYSQL_DB", "llm_db"),
    "charset": "utf8mb4",
}

# 파일명에서 진료과명 추출 (TL_진료과명.zip -> 진료과명)
DEPT_PATTERN = re.compile(r"^[TV]L_(.+)\.zip$")

# 파일명에서 언어 추출 (TS_국문_*.zip -> ko, TS_영문_*.zip -> en)
LANG_PATTERN = re.compile(r"^TS_(국문|영문)_")

# 배치 INSERT 크기
BATCH_SIZE = 500


def detect_language(filename: str) -> str:
    """파일명에서 언어 감지"""
    match = LANG_PATTERN.search(filename)
    if match:
        return "ko" if match.group(1) == "국문" else "en"
    return "ko"


def detect_department(filename: str) -> str:
    """파일명에서 진료과명 추출"""
    match = DEPT_PATTERN.search(filename)
    return match.group(1) if match else "기타"


def detect_data_type(path: str) -> str:
    """경로에서 training/validation 구분"""
    if "Validation" in path:
        return "validation"
    return "training"


def detect_dataset(outer_zip_name: str) -> str:
    """외부 ZIP 파일명에서 데이터셋 구분"""
    if "08" in outer_zip_name:
        return "08_전문"
    elif "09" in outer_zip_name:
        return "09_필수의료"
    return "unknown"


def decode_filename(raw_name: str) -> str:
    """ZIP 내 한글 파일명 디코딩"""
    try:
        return raw_name.encode("cp437").decode("euc-kr")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return raw_name


def process_outer_zip(zip_path: str, conn):
    """외부 ZIP 파일 처리"""
    dataset = detect_dataset(os.path.basename(zip_path))
    logger.info("Processing: %s (dataset=%s)", zip_path, dataset)

    content_count = 0
    qa_count = 0

    with zipfile.ZipFile(zip_path, "r") as outer:
        for entry in outer.infolist():
            if entry.file_size == 0:
                continue

            decoded_path = decode_filename(entry.filename)
            fname = decoded_path.split("/")[-1]
            data_type = detect_data_type(decoded_path)

            # 내부 ZIP 읽기
            raw_data = outer.read(entry.filename)
            try:
                inner = zipfile.ZipFile(BytesIO(raw_data))
            except zipfile.BadZipFile:
                continue

            if fname.startswith("TS_"):
                lang = detect_language(fname)
                cnt = import_content(inner, conn, dataset, data_type, lang)
                content_count += cnt
                logger.info("  %s: %d content records", fname, cnt)
            elif fname.startswith("TL_") or fname.startswith("VL_"):
                dept = detect_department(fname)
                cnt = import_qa(inner, conn, dataset, data_type, dept)
                qa_count += cnt
                logger.info("  %s: %d qa records (dept=%s)", fname, cnt, dept)

    logger.info("Completed %s: content=%d, qa=%d", zip_path, content_count, qa_count)
    return content_count, qa_count


def import_content(inner_zip, conn, dataset, data_type, language) -> int:
    """원천데이터 JSON -> medical_content 테이블 (배치 INSERT)"""
    batch = []
    count = 0

    for name in inner_zip.namelist():
        if not name.endswith(".json"):
            continue
        try:
            raw = inner_zip.read(name)
            obj = json.loads(raw.decode("utf-8-sig"))
            batch.append((
                obj.get("c_id", ""),
                obj.get("domain", 0),
                obj.get("source"),
                str(obj.get("source_spec", "")),
                obj.get("creation_year", ""),
                obj.get("content", ""),
                dataset,
                data_type,
                language,
            ))
            count += 1

            if len(batch) >= BATCH_SIZE:
                _flush_content(conn, batch)
                batch.clear()
        except Exception as e:
            logger.warning("Skip content %s: %s", name, e)

    if batch:
        _flush_content(conn, batch)

    return count


def _flush_content(conn, batch):
    """medical_content 배치 INSERT 실행"""
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO medical_content
                (c_id, domain, source, source_spec, creation_year,
                 content, dataset, data_type, language)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            batch,
        )
    conn.commit()


def import_qa(inner_zip, conn, dataset, data_type, department) -> int:
    """라벨링데이터 JSON -> medical_qa 테이블 (배치 INSERT)"""
    batch = []
    count = 0

    for name in inner_zip.namelist():
        if not name.endswith(".json"):
            continue
        try:
            raw = inner_zip.read(name)
            obj = json.loads(raw.decode("utf-8-sig"))
            batch.append((
                obj.get("qa_id", 0),
                obj.get("domain", 0),
                department,
                obj.get("q_type", 0),
                obj.get("question", ""),
                obj.get("answer", ""),
                dataset,
                data_type,
            ))
            count += 1

            if len(batch) >= BATCH_SIZE:
                _flush_qa(conn, batch)
                batch.clear()
        except Exception as e:
            logger.warning("Skip qa %s: %s", name, e)

    if batch:
        _flush_qa(conn, batch)

    return count


def _flush_qa(conn, batch):
    """medical_qa 배치 INSERT 실행"""
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO medical_qa
                (qa_id, domain, department, q_type, question, answer,
                 dataset, data_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            batch,
        )
    conn.commit()


def main():
    llm_data_dir = os.path.join(os.path.dirname(__file__), "..", "llm_data")
    llm_data_dir = os.path.abspath(llm_data_dir)

    if not os.path.isdir(llm_data_dir):
        logger.error("llm_data 폴더가 없습니다: %s", llm_data_dir)
        logger.error("프로젝트 루트에 llm_data/ 폴더를 생성하고 ZIP 파일을 배치하세요.")
        sys.exit(1)

    zip_files = [
        os.path.join(llm_data_dir, "08.전문 의학지식 데이터.zip"),
        os.path.join(llm_data_dir, "09.필수의료 의학지식 데이터.zip"),
    ]

    found = [zf for zf in zip_files if os.path.exists(zf)]
    if not found:
        logger.error("ZIP 파일을 찾을 수 없습니다.")
        for zf in zip_files:
            logger.error("  필요: %s", zf)
        sys.exit(1)

    logger.info("DB 연결: %s:%d/%s", DB_CONFIG["host"], DB_CONFIG["port"], DB_CONFIG["db"])
    conn = pymysql.connect(**DB_CONFIG)

    total_content = 0
    total_qa = 0

    try:
        for zf in found:
            cc, qc = process_outer_zip(zf, conn)
            total_content += cc
            total_qa += qc

        # 적재 결과 확인
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM medical_content")
            content_total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM medical_qa")
            qa_total = cur.fetchone()[0]

            logger.info("=== Import Summary ===")
            logger.info("이번 적재: content=%d, qa=%d", total_content, total_qa)
            logger.info("전체 누적: medical_content=%d rows, medical_qa=%d rows",
                        content_total, qa_total)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
