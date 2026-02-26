# Python LLM 모듈

Spring Boot에서 HTTP로 호출하는 LLM 추론 서버입니다. RAG 없이 순수 LLM 추론만 수행합니다.

- **참조**: [PRD](../doc/PRD.md), [TASK_PYTHON](../doc/TASK_PYTHON.md)
- **Python**: 3.10+

## 설치

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows PowerShell
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

## 가상환경 활성화 (개발 시)

```powershell
# Windows
.venv\Scripts\Activate.ps1
```

```bash
# Linux/Mac
source .venv/bin/activate
```

## 설정

`config.py`에서 Pydantic Settings로 환경변수 관리. `.env` 또는 `.env.example` 참고.

**주요 항목**:

- `LLM_MODEL`: Hugging Face 모델명 (기본: gpt2)
- `LLM_FALLBACK_MOCK`: 1로 설정 시 torch 미지원 환경에서 mock 응답 사용
- `LLM_INFER_TIMEOUT_SEC`: 추론 타임아웃 초 (기본: 60)
- `LLM_INPUT_MAX_LENGTH`: 입력 최대 문자 수 (기본: 2048)
- `LLM_FALLBACK_RESPONSE`: LLM 실패 시 반환할 기본 응답 (설정 시)
- `HOST`, `PORT`: 서버 바인드 주소/포트 (기본: 0.0.0.0, 8000)
- `OPENAI_API_KEY`: OpenAI API 키 (향후 확장용)

## 실행

```bash
# 직접 실행
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# 또는 스크립트 사용
./run.sh          # Linux/Mac
run.bat           # Windows
./run.sh --reload # 개발 모드 (자동 리로드)
```

- `GET /` : 서버 상태
- `GET /health` : 헬스체크
- `POST /infer` : LLM 추론

## 테스트

```bash
# LLM_FALLBACK_MOCK=1 권장 (torch 불필요)
$env:LLM_FALLBACK_MOCK="1"  # PowerShell
pytest tests/ -v
```

## Docker (선택)

```bash
docker build -t python-llm .
docker run -p 8000:8000 -e LLM_FALLBACK_MOCK=1 python-llm
```

## API 스키마 (Spring Boot 연동)

`schemas.py`에 정의된 요청/응답 형식:

**POST /infer 요청** (JSON):

```json
{
  "query": "안녕하세요, 오늘 날씨는?",
  "max_length": 100,
  "temperature": 0.7
}
```

**응답**:

```json
{
  "generated_text": "안녕하세요! 오늘 날씨에 대해..."
}
```
