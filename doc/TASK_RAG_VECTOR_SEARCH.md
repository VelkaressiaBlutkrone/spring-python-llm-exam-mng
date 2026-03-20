# RAG/벡터 검색 구현 (Ollama Embedding + ChromaDB)

## 1. 개요

### 배경

기존 의학 질의응답 시스템은 MySQL FULLTEXT 검색(ngram)만으로 사용자 질문과 관련된 의학 데이터를 조회하고 LLM 컨텍스트로 주입하였다.
FULLTEXT 검색은 키워드 기반이므로 **의미적 유사도**를 반영하지 못하는 한계가 있었다.

### 목적

- **의미 기반 검색** 도입으로 키워드가 정확히 일치하지 않아도 관련 문서를 찾을 수 있도록 개선
- **하이브리드 검색** (벡터 + FULLTEXT) 적용으로 검색 품질 향상
- 기존 FULLTEXT 검색을 제거하지 않고 폴백으로 유지하여 안정성 확보

### 선택한 방식

| 항목        | 선택                        | 이유                                     |
| ----------- | --------------------------- | ---------------------------------------- |
| 임베딩 모델 | Ollama `nomic-embed-text`   | Ollama 인프라 재활용, 외부 API 비용 없음 |
| 벡터 DB     | ChromaDB (PersistentClient) | 경량, 설치 간편, Python 네이티브         |
| 유사도 측정 | Cosine Similarity           | 텍스트 임베딩에 가장 보편적              |

---

## 2. 아키텍처

```
[사용자 질문]
    │
    ▼
[오타 교정] ─── typo_corrector.py
    │
    ├─────────────────────────────────┐
    ▼                                 ▼
[ChromaDB 벡터 검색]          [MySQL FULLTEXT 검색]
 (의미 유사도 기반)             (키워드 기반, 폴백)
    │                                 │
    └──────────┬──────────────────────┘
               ▼
      [컨텍스트 병합 + 길이 제한]
               │
               ▼
      [시스템 프롬프트 + 컨텍스트 + 사용자 질문]
               │
               ▼
        [Ollama Chat API 호출]
               │
               ▼
          [LLM 응답 반환]
```

### 데이터 인덱싱 흐름

```
[MySQL medical_qa / medical_content]
    │
    ▼
[index_medical_data.py] ── pymysql로 조회
    │
    ▼
[Ollama /api/embed] ── nomic-embed-text 모델로 임베딩
    │
    ▼
[ChromaDB] ── 벡터 + 원본 텍스트 + 메타데이터 저장
```

---

## 3. 코드 변경사항

### 3.1 신규 파일

| 파일                               | 역할                             |
| ---------------------------------- | -------------------------------- |
| `python-llm/embedding_service.py`  | Ollama 임베딩 API 클라이언트     |
| `python-llm/vector_store.py`       | ChromaDB 벡터 저장소 래퍼        |
| `python-llm/index_medical_data.py` | MySQL → ChromaDB 인덱싱 스크립트 |

### 3.2 수정 파일

| 파일                                    | 변경 내용                           |
| --------------------------------------- | ----------------------------------- |
| `python-llm/config.py`                  | ChromaDB/임베딩 관련 설정 추가      |
| `python-llm/medical_context_service.py` | 하이브리드 검색 로직 추가           |
| `python-llm/app.py`                     | 서버 시작 시 ChromaDB 초기화        |
| `python-llm/requirements.txt`           | `chromadb>=0.5.0` 의존성 추가       |
| `.gitignore`                            | `chroma_data/`, `__pycache__/` 제외 |

---

## 4. 상세 구현

### 4.1 embedding_service.py

Ollama `/api/embed` API를 사용하여 텍스트를 벡터로 변환한다.

- `get_embedding(text)` — 단건 텍스트 임베딩 (질의 시 사용)
- `get_embeddings_batch(texts)` — 배치 임베딩 (인덱싱 시 사용)

```python
# 단건 임베딩 요청
POST {ollama_base_url}/api/embed
{
    "model": "nomic-embed-text",
    "input": "두통이 심합니다"
}
# 응답: {"embeddings": [[0.1, -0.3, ...]]}
```

### 4.2 vector_store.py

ChromaDB PersistentClient를 래핑하여 벡터 CRUD를 제공한다.

| 함수                   | 설명                                            |
| ---------------------- | ----------------------------------------------- |
| `get_chroma_client()`  | ChromaDB 클라이언트 싱글톤                      |
| `get_collection()`     | `medical_docs` 컬렉션 조회/생성 (cosine 유사도) |
| `add_documents()`      | upsert 방식으로 문서 추가 (중복 방지)           |
| `search_similar()`     | 쿼리 벡터와 가장 유사한 문서 검색               |
| `get_document_count()` | 인덱싱된 문서 수 조회                           |

**ChromaDB 설정:**

- 저장 경로: `./chroma_data` (PersistentClient, 서버 재시작 후에도 유지)
- 컬렉션: `medical_docs`
- 유사도: `cosine` (HNSW 인덱스)

### 4.3 index_medical_data.py

MySQL의 의학 데이터를 읽어 Ollama로 임베딩한 뒤 ChromaDB에 저장하는 CLI 스크립트이다.

**인덱싱 대상:**

| 테이블            | ID 형식          | 임베딩 텍스트                            | 메타데이터                         |
| ----------------- | ---------------- | ---------------------------------------- | ---------------------------------- |
| `medical_qa`      | `qa_{id}`        | `질문: {question}\n답변: {answer[:500]}` | type, department, q_type, question |
| `medical_content` | `content_{c_id}` | `content[:1000]`                         | type, source                       |

**배치 처리:** 20건씩 묶어 Ollama 배치 임베딩 → ChromaDB upsert

### 4.4 medical_context_service.py — 하이브리드 검색

`build_medical_context()` 함수가 벡터 검색과 FULLTEXT 검색을 조합한다.

```
1. ChromaDB 벡터 검색 (top_k=3, 의미 유사도)
   └─ 결과 < 2건 → MySQL FULLTEXT Q&A 검색 보완
   └─ 결과 < 1건 → MySQL FULLTEXT 콘텐츠 검색 보완
2. 컨텍스트 병합 + 최대 1500자 제한
```

**폴백 전략:**

- 벡터 검색 실패 시(예: ChromaDB 미초기화, 임베딩 오류) 자동으로 FULLTEXT만 사용
- `use_vector_search=False` 설정으로 벡터 검색 비활성화 가능

### 4.5 config.py — 추가 설정

| 환경변수                    | 기본값             | 설명                      |
| --------------------------- | ------------------ | ------------------------- |
| `OLLAMA_EMBED_MODEL`        | `nomic-embed-text` | Ollama 임베딩 모델        |
| `CHROMA_PERSIST_DIR`        | `./chroma_data`    | ChromaDB 데이터 저장 경로 |
| `CHROMA_COLLECTION`         | `medical_docs`     | ChromaDB 컬렉션명         |
| `VECTOR_SEARCH_TOP_K`       | `3`                | 벡터 검색 상위 K건        |
| `USE_VECTOR_SEARCH`         | `True`             | 벡터 검색 사용 여부       |
| `MEDICAL_CONTEXT_MAX_CHARS` | `1500`             | 컨텍스트 최대 문자 수     |

### 4.6 app.py — 서버 시작 시 초기화

서버 startup 이벤트에서 `use_vector_search=True`일 때 ChromaDB 컬렉션을 미리 로드하여 첫 요청 지연을 방지한다. 초기화 실패 시 경고 로그만 남기고 FULLTEXT 검색으로 자동 폴백된다.

---

## 5. 사용법

### 5.1 사전 준비

```bash
# 1. Ollama 임베딩 모델 다운로드
ollama pull nomic-embed-text

# 2. Python 의존성 설치
cd python-llm
pip install -r requirements.txt
```

### 5.2 데이터 인덱싱

```bash
# MySQL 의학 데이터를 ChromaDB에 벡터 인덱싱
cd python-llm
python index_medical_data.py
```

출력 예시:

```
=== Medical Data Vector Indexing ===
Ollama: http://localhost:11434, Embed model: nomic-embed-text
ChromaDB: ./chroma_data / medical_docs
Fetched: 150 Q&A, 80 content rows
Indexing 150 Q&A documents...
  Indexed Q&A batch 1-20
  ...
Indexing 80 content documents...
  Indexed content batch 1-20
  ...
=== Indexing complete: 230 total documents in vector store ===
```

### 5.3 서버 실행

```bash
cd python-llm
uvicorn app:app --host 0.0.0.0 --port 8000
```

서버 시작 로그에서 ChromaDB 초기화 확인:

```
ChromaDB ready: 230 documents indexed
```

### 5.4 벡터 검색 비활성화

FULLTEXT 검색만 사용하려면:

```bash
USE_VECTOR_SEARCH=False uvicorn app:app --port 8000
```

---

## 6. 반영 이유 및 기대 효과

### 기존 FULLTEXT 검색의 한계

| 문제           | 예시                                         |
| -------------- | -------------------------------------------- |
| 동의어 미인식  | "머리가 아파요" → "두통" 관련 문서 검색 실패 |
| 표현 변형 불가 | "배가 살살 아파" → "복통" 매칭 어려움        |
| 짧은 질문 불리 | 2글자 미만 키워드 추출 불가                  |

### 벡터 검색 도입 효과

| 개선점          | 설명                                                       |
| --------------- | ---------------------------------------------------------- |
| 의미 기반 매칭  | 단어가 다르더라도 의미가 유사하면 검색 가능                |
| 하이브리드 보완 | 벡터 결과 부족 시 FULLTEXT로 자동 보완                     |
| 점진적 적용     | `use_vector_search` 플래그로 즉시 롤백 가능                |
| 비용 없음       | Ollama 로컬 실행으로 외부 API 비용 미발생                  |
| 지속성          | ChromaDB PersistentClient로 서버 재시작 후에도 인덱스 유지 |

---

## 7. 향후 개선 방향

1. **인덱싱 자동화** — 의학 데이터 변경 시 자동 재인덱싱 (이벤트 기반 or 주기적 배치)
2. **임베딩 모델 교체** — 한국어 특화 임베딩 모델 적용 시 검색 품질 추가 향상 가능
3. **Re-ranking** — 벡터 검색 결과를 Cross-Encoder로 재순위화하여 정밀도 향상
4. **청크 분할** — 긴 콘텐츠를 적절한 크기로 분할하여 임베딩 품질 개선
5. **메타데이터 필터링** — 진료과 등 메타데이터 기반 사전 필터링으로 검색 범위 축소

---

## 7. 향후 개선 방향

1. **인덱싱 자동화** — 의학 데이터 변경 시 자동 재인덱싱 (이벤트 기반 or 주기적 배치)
2. **임베딩 모델 교체** — 한국어 특화 임베딩 모델 적용 시 검색 품질 추가 향상 가능
3. **Re-ranking** — 벡터 검색 결과를 Cross-Encoder로 재순위화하여 정밀도 향상
4. **청크 분할** — 긴 콘텐츠를 적절한 크기로 분할하여 임베딩 품질 개선
5. **메타데이터 필터링** — 진료과 등 메타데이터 기반 사전 필터링으로 검색 범위 축소
6. **메타데이터 필터링** — 진료과 등 메타데이터 기반 사전 필터링으로 검색 범위 축소
