# llm_db 재설치 후 데이터 복원 가이드

llm_db(MySQL) 컨테이너를 새로 설치한 후 `llm_data` 데이터를 다시 적재하는 방법입니다.

---

## 사전 준비: llm_data 폴더 구조

```
llm_data/
├── 08.전문 의학지식 데이터.zip    ← 의학 Q&A/콘텐츠 (필수)
├── 09.필수의료 의학지식 데이터.zip ← 의학 Q&A/콘텐츠 (필수)
└── medical_rules.json             ← 병원 규칙 (프로젝트에 포함됨)
```

> **ZIP 파일 출처**: 의학지식 데이터는 별도로 확보해야 합니다.
> 프로젝트에 `medical_rules.json`만 포함되어 있으며, `08.*.zip`, `09.*.zip`은 데이터 제공처에서 다운로드 후 `llm_data/`에 배치하세요.

---

## 1단계: MySQL 테이블 생성

MySQL 컨테이너가 healthy 상태가 된 후 실행합니다.

```powershell
# 프로젝트 루트에서

# PowerShell (Windows): < 리다이렉션 미지원 → Get-Content 사용
Get-Content scripts/medical-tables.sql -Raw | docker exec -i llm-db mysql -uroot -prootpassword --default-character-set=utf8mb4 llm_db

# CMD 또는 Bash
# docker exec -i llm-db mysql -uroot -prootpassword --default-character-set=utf8mb4 llm_db < scripts/medical-tables.sql
```

- `medical_domain`, `medical_content`, `medical_qa`, `medical_rule` 테이블 생성

---

## 2단계: 의학지식 ZIP 데이터 → MySQL 적재

```powershell
cd python-llm
.venv\Scripts\activate   # 가상환경 활성화

# Windows: localhost:3307로 Docker MySQL 접속
$env:MYSQL_HOST="127.0.0.1"
$env:MYSQL_PORT="3307"
python import_medical_data.py
```

**환경변수 (선택)**

- `MYSQL_HOST`: 기본값 `localhost` (Windows에서는 `127.0.0.1` 권장)
- `MYSQL_PORT`: 기본값 `3307`
- `MYSQL_USER`: 기본값 `root`
- `MYSQL_PASSWORD`: 기본값 `rootpassword`
- `MYSQL_DB`: 기본값 `llm_db`

---

## 3단계: 병원 규칙 → MySQL + ChromaDB 적재

```powershell
# Ollama 실행 중이어야 함 (ollama pull nomic-embed-text, ollama serve)
python index_rule_data.py
```

- `llm_data/medical_rules.json` → MySQL `medical_rule` + ChromaDB `medical_rules` 컬렉션

---

## 4단계: 의학 데이터 → ChromaDB 벡터 인덱싱

```powershell
python index_medical_data.py --full
```

- MySQL `medical_content`, `medical_qa` → ChromaDB `medical_docs` 컬렉션
- `--full`: 전체 재인덱싱 (초기 적재 시 권장)

---

## 전체 실행 순서 요약

```powershell
# 1. Docker 기동 (MySQL, ChromaDB)
docker compose up -d

# 2. MySQL healthy 대기 후 테이블 생성 (PowerShell)
Get-Content scripts/medical-tables.sql -Raw | docker exec -i llm-db mysql -uroot -prootpassword --default-character-set=utf8mb4 llm_db

# 3. Python 환경
cd python-llm
.venv\Scripts\activate

# 4. 의학지식 ZIP → MySQL
$env:MYSQL_HOST="127.0.0.1"; python import_medical_data.py

# 5. 병원 규칙 → MySQL + ChromaDB (Ollama 필요)
python index_rule_data.py

# 6. 의학 데이터 → ChromaDB 벡터 인덱싱 (Ollama 필요)
python index_medical_data.py --full
```

---

## ZIP 파일이 없을 때

`08.*.zip`, `09.*.zip`이 없으면 `import_medical_data.py`는 건너뛰고, `medical_rules.json`만 사용할 수 있습니다.

- `index_rule_data.py` → 병원 규칙 Q&A만 동작
- 의료 상담은 `medical_content`, `medical_qa`가 비어 있어 FULLTEXT/벡터 검색 결과가 없을 수 있음
- 의료 상담은 `medical_content`, `medical_qa`가 비어 있어 FULLTEXT/벡터 검색 결과가 없을 수 있음
