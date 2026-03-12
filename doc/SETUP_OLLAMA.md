# Ollama 로컬 LLM 서버 구축 가이드

> 참조: [PRD.md](./PRD.md), [TASK_PYTHON.md](./TASK_PYTHON.md)

OpenAI, Claude AI 등 외부 API 대신 **Ollama**를 활용하여 로컬 환경에서 LLM 서버를 운영하는 방법을 정의합니다.
비용 없이 프라이버시를 보장하며, 기존 Python FastAPI 서버와 연동하여 Spring Boot 아키텍처에 통합합니다.

---

## 1. Ollama 개요

| 항목            | 설명                                                                 |
| --------------- | -------------------------------------------------------------------- |
| **Ollama란**    | 로컬 환경에서 LLM을 간편하게 실행할 수 있는 오픈소스 도구            |
| **장점**        | API 비용 없음, 데이터 외부 전송 없음(프라이버시), 오프라인 사용 가능 |
| **단점**        | GPU 없으면 느림, 모델 크기에 따라 RAM/VRAM 요구량 높음               |
| **공식 사이트** | <https://ollama.com>                                                 |
| **GitHub**      | <https://github.com/ollama/ollama>                                   |

### 1.1 외부 API vs Ollama 비교

| 구분        | OpenAI / Claude API      | Ollama (로컬)                   |
| ----------- | ------------------------ | ------------------------------- |
| 비용        | 토큰 사용량 과금         | 무료 (하드웨어 비용만)          |
| 프라이버시  | 외부 서버 전송           | 로컬 처리, 데이터 유출 없음     |
| 응답 속도   | 네트워크 의존            | GPU 있으면 빠름, CPU만이면 느림 |
| 모델 품질   | GPT-4o, Claude 등 최상급 | 오픈소스 모델 (Llama, Gemma 등) |
| 인터넷 필요 | 필수                     | 모델 다운로드 후 불필요         |
| 설정 난이도 | API 키만 있으면 간단     | 로컬 설치 및 모델 다운로드 필요 |

---

## 2. Ollama 설치

### 2.1 Windows

```powershell
# 1. 공식 사이트에서 설치 파일 다운로드
# https://ollama.com/download/windows

# 2. 설치 후 확인
ollama --version

# 3. Ollama 서비스 시작 (설치 시 자동 시작됨)
ollama serve
```

### 2.2 macOS

```bash
# Homebrew로 설치
brew install ollama

# 또는 공식 사이트에서 다운로드
# https://ollama.com/download/mac

# 서비스 시작
ollama serve
```

### 2.3 Linux

```bash
# 공식 설치 스크립트
curl -fsSL https://ollama.com/install.sh | sh

# 서비스 시작
sudo systemctl start ollama
sudo systemctl enable ollama  # 부팅 시 자동 시작

# 확인
ollama --version
```

### 2.4 Docker

```bash
# GPU 지원 (NVIDIA)
docker run -d --gpus all -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama

# CPU 전용
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
```

---

## 3. 추천 모델

### 3.1 용도별 추천

| 용도             | 모델               | 크기   | 최소 RAM | 설명                             |
| ---------------- | ------------------ | ------ | -------- | -------------------------------- |
| **경량 테스트**  | `gemma3:4b`        | ~3GB   | 8GB      | Google Gemma 3, 빠른 응답        |
| **일반 대화/QA** | `llama3.1:8b`      | ~4.7GB | 8GB      | Meta Llama 3.1, 범용 성능 우수   |
| **한국어 특화**  | `gemma3:12b`       | ~8GB   | 16GB     | 한국어 성능 양호                 |
| **고품질 추론**  | `llama3.1:70b`     | ~40GB  | 64GB     | 대규모, 높은 품질 (GPU 권장)     |
| **코드 생성**    | `qwen2.5-coder:7b` | ~4.7GB | 8GB      | 코드 작성 특화                   |
| **경량 임베딩**  | `nomic-embed-text` | ~274MB | 4GB      | 텍스트 임베딩 (향후 RAG 확장 시) |

### 3.2 본 프로젝트 권장 모델

| 환경                       | 권장 모델         | 이유                        |
| -------------------------- | ----------------- | --------------------------- |
| **개발/테스트 (GPU 없음)** | `gemma3:4b`       | 가볍고 빠름, CPU에서도 동작 |
| **개발/테스트 (GPU 있음)** | `llama3.1:8b`     | 범용 성능 우수, 적절한 크기 |
| **프로덕션**               | `gemma3:12b` 이상 | 한국어 지원, 안정적 품질    |

### 3.3 모델 설치 및 관리

```bash
# 모델 다운로드
ollama pull gemma3:4b
ollama pull llama3.1:8b

# 설치된 모델 목록
ollama list

# 모델 실행 (대화 테스트)
ollama run gemma3:4b

# 모델 삭제
ollama rm gemma3:4b

# 모델 정보 확인
ollama show gemma3:4b
```

---

## 4. Ollama API 사용법

Ollama는 기본적으로 `http://localhost:11434`에서 REST API를 제공합니다.

### 4.1 주요 API 엔드포인트

| 엔드포인트      | 메서드 | 설명                     |
| --------------- | ------ | ------------------------ |
| `/api/generate` | POST   | 텍스트 생성 (completion) |
| `/api/chat`     | POST   | 대화형 생성 (chat)       |
| `/api/tags`     | GET    | 설치된 모델 목록         |
| `/api/show`     | POST   | 모델 정보 조회           |
| `/api/pull`     | POST   | 모델 다운로드            |

### 4.2 API 호출 예시

```bash
# 텍스트 생성
curl http://localhost:11434/api/generate -d '{
  "model": "gemma3:4b",
  "prompt": "안녕하세요, 오늘 날씨는 어떤가요?",
  "stream": false
}'

# 대화형 생성
curl http://localhost:11434/api/chat -d '{
  "model": "gemma3:4b",
  "messages": [
    {"role": "user", "content": "안녕하세요, 오늘 날씨는?"}
  ],
  "stream": false
}'
```

### 4.3 응답 형식

```json
{
  "model": "gemma3:4b",
  "created_at": "2025-01-01T00:00:00Z",
  "response": "안녕하세요! 저는 AI 어시스턴트입니다...",
  "done": true,
  "total_duration": 1234567890,
  "eval_count": 42
}
```

---

## 5. Python 서버 연동

기존 Python FastAPI 서버(`python-llm/`)에서 Hugging Face transformers 대신 Ollama를 사용하도록 연동합니다.

### 5.1 아키텍처

```text
[클라이언트]
    ↓ (HTTP)
[Spring Boot 서버]
    ↓ (HTTP: WebClient)
[Python FastAPI 서버] (포트 8000)
    ↓ (HTTP: httpx)
[Ollama 서버] (포트 11434)
    - 로컬 LLM 모델 실행
```

### 5.2 의존성 추가

```bash
# requirements.txt에 추가
pip install httpx
```

`httpx`는 비동기 HTTP 클라이언트로, Python 서버에서 Ollama API를 호출하는 데 사용합니다.

### 5.3 Ollama 전용 LLM 서비스 구현

`python-llm/ollama_service.py` 파일을 생성합니다:

```python
"""
Ollama LLM 서비스
로컬 Ollama 서버를 통한 LLM 추론
"""

import logging
import httpx
from config import get_settings

logger = logging.getLogger(__name__)

# Ollama 기본 설정
OLLAMA_BASE_URL = "http://localhost:11434"


async def generate_with_ollama(
    query: str,
    model: str = "gemma3:4b",
    max_length: int = 100,
    temperature: float = 0.7,
    top_p: float = 1.0,
) -> str:
    """
    Ollama API를 통한 LLM 추론

    Args:
        query: 입력 텍스트
        model: Ollama 모델명
        max_length: 최대 생성 토큰 수
        temperature: 생성 다양성
        top_p: nucleus sampling

    Returns:
        생성된 텍스트
    """
    payload = {
        "model": model,
        "prompt": query,
        "stream": False,
        "options": {
            "num_predict": max_length,
            "temperature": temperature,
            "top_p": top_p,
        },
    }

    timeout = httpx.Timeout(
        connect=5.0,
        read=float(get_settings().llm_infer_timeout_sec),
        write=5.0,
        pool=5.0,
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except httpx.ConnectError:
            logger.error("Ollama 서버 연결 실패: %s", OLLAMA_BASE_URL)
            raise ConnectionError(
                "Ollama 서버에 연결할 수 없습니다. ollama serve 실행 여부를 확인하세요."
            )
        except httpx.ReadTimeout:
            logger.warning("Ollama 추론 타임아웃")
            raise TimeoutError("Ollama 추론 타임아웃")


async def chat_with_ollama(
    messages: list[dict],
    model: str = "gemma3:4b",
    temperature: float = 0.7,
) -> str:
    """
    Ollama Chat API를 통한 대화형 추론

    Args:
        messages: [{"role": "user", "content": "..."}] 형식의 메시지 리스트
        model: Ollama 모델명
        temperature: 생성 다양성

    Returns:
        생성된 응답 텍스트
    """
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }

    timeout = httpx.Timeout(
        connect=5.0,
        read=float(get_settings().llm_infer_timeout_sec),
        write=5.0,
        pool=5.0,
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
        )
        response.raise_for_status()
        result = response.json()
        return result.get("message", {}).get("content", "")


async def check_ollama_health() -> bool:
    """Ollama 서버 상태 확인"""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            return response.status_code == 200
    except Exception:
        return False


async def list_models() -> list[str]:
    """설치된 Ollama 모델 목록 조회"""
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
        response.raise_for_status()
        data = response.json()
        return [m["name"] for m in data.get("models", [])]
```

### 5.4 기존 `/infer` 엔드포인트에 Ollama 연동

`app.py`에서 Ollama 모드를 추가하는 예시:

```python
from ollama_service import generate_with_ollama, check_ollama_health

# 환경변수로 LLM 백엔드 선택
# LLM_BACKEND=ollama  → Ollama 사용
# LLM_BACKEND=huggingface  → 기존 Hugging Face 사용

@app.post("/infer", response_model=InferResponse)
async def infer(request: InferRequest) -> InferResponse:
    settings = get_settings()

    if settings.llm_backend == "ollama":
        generated_text = await generate_with_ollama(
            query=request.query,
            model=settings.ollama_model,
            max_length=request.max_length,
            temperature=request.temperature,
            top_p=request.top_p or 1.0,
        )
    else:
        generated_text = generate(
            query=request.query,
            max_length=request.max_length,
            temperature=request.temperature,
            top_p=request.top_p or 1.0,
            num_return_sequences=request.num_return_sequences,
        )

    return InferResponse(generated_text=generated_text)
```

### 5.5 설정 추가 (`config.py`)

```python
# 기존 Settings 클래스에 추가
class Settings(BaseSettings):
    # ... 기존 설정 ...

    # Ollama 설정
    llm_backend: str = Field(
        default="huggingface",
        description="LLM 백엔드 (huggingface | ollama)"
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama 서버 URL"
    )
    ollama_model: str = Field(
        default="gemma3:4b",
        description="Ollama 모델명"
    )
```

### 5.6 `.env` 설정 예시

```env
# Ollama 모드로 전환
LLM_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:4b

# 기존 Hugging Face 모드 (기본값)
# LLM_BACKEND=huggingface
# LLM_MODEL=gpt2
```

---

## 6. Spring Boot 연동

Spring Boot에서는 기존과 동일하게 Python FastAPI 서버의 `/infer` 엔드포인트를 호출합니다.
Python 서버 내부에서 Ollama를 사용하므로 Spring Boot 코드 변경은 불필요합니다.

```text
Spring Boot (WebClient)
    → POST http://localhost:8000/infer  (Python FastAPI)
        → POST http://localhost:11434/api/generate  (Ollama)
```

### 6.1 Spring Boot에서 직접 Ollama 호출 (대안)

Python 서버를 거치지 않고 Spring Boot에서 직접 Ollama API를 호출할 수도 있습니다:

```java
@Service
public class OllamaService {
    private final WebClient webClient;

    public OllamaService(WebClient.Builder builder) {
        this.webClient = builder.baseUrl("http://localhost:11434").build();
    }

    public Mono<String> generate(String prompt, String model) {
        Map<String, Object> body = Map.of(
            "model", model,
            "prompt", prompt,
            "stream", false
        );

        return webClient.post()
            .uri("/api/generate")
            .bodyValue(body)
            .retrieve()
            .bodyToMono(Map.class)
            .map(result -> (String) result.get("response"));
    }
}
```

### 6.2 Spring AI + Ollama (대안)

Spring AI 프레임워크를 사용하면 더 간결하게 연동 가능합니다:

```xml
<!-- pom.xml -->
<dependency>
    <groupId>org.springframework.ai</groupId>
    <artifactId>spring-ai-ollama-spring-boot-starter</artifactId>
</dependency>
```

```yaml
# application.yml
spring:
  ai:
    ollama:
      base-url: http://localhost:11434
      chat:
        model: gemma3:4b
```

```java
@RestController
public class LlmController {
    private final ChatClient chatClient;

    public LlmController(ChatClient.Builder builder) {
        this.chatClient = builder.build();
    }

    @PostMapping("/api/llm/query")
    public String query(@RequestBody String prompt) {
        return chatClient.prompt(prompt).call().content();
    }
}
```

---

## 7. 하드웨어 요구사항

| 모델 크기 | RAM   | GPU VRAM | CPU 추론 속도     | GPU 추론 속도    |
| --------- | ----- | -------- | ----------------- | ---------------- |
| 1B~4B     | 8GB   | 4GB      | 보통 (5~15 tok/s) | 빠름 (30+ tok/s) |
| 7B~8B     | 16GB  | 8GB      | 느림 (2~8 tok/s)  | 빠름 (20+ tok/s) |
| 12B~14B   | 32GB  | 12GB     | 매우 느림         | 보통 (15+ tok/s) |
| 70B       | 64GB+ | 40GB+    | 사용 불가 수준    | 보통             |

### 7.1 GPU 지원

| GPU 종류      | 지원 여부 | 비고                            |
| ------------- | --------- | ------------------------------- |
| NVIDIA (CUDA) | 지원      | 가장 안정적, 6GB VRAM 이상 권장 |
| AMD (ROCm)    | 부분 지원 | Linux에서 ROCm 설치 필요        |
| Apple Silicon | 지원      | Metal 가속, M1 이상             |
| CPU 전용      | 가능      | 소형 모델(4B 이하) 권장         |

---

## 8. 운영 팁

### 8.1 Ollama 환경변수

```bash
# 모델 저장 경로 변경 (기본: ~/.ollama)
OLLAMA_MODELS=/path/to/models

# 바인드 주소 변경 (외부 접근 허용)
OLLAMA_HOST=0.0.0.0:11434

# GPU 메모리 제한
OLLAMA_GPU_MEMORY=6g
```

### 8.2 성능 최적화

| 항목               | 방법                                                |
| ------------------ | --------------------------------------------------- |
| 모델 미리 로딩     | `ollama run <model>` 후 종료하면 메모리에 캐시 유지 |
| 양자화 모델 사용   | `q4_0`, `q4_K_M` 등 양자화 버전으로 메모리 절약     |
| 컨텍스트 길이 조절 | `num_ctx` 옵션으로 컨텍스트 윈도우 조절             |
| Keep-alive 설정    | 모델 언로드 시간 조절 (`keep_alive` 파라미터)       |

### 8.3 Modelfile로 커스텀 모델 생성

```dockerfile
# Modelfile
FROM gemma3:4b

# 시스템 프롬프트 설정
SYSTEM """당신은 병원 예약 시스템의 AI 어시스턴트입니다.
환자의 증상을 분석하고 적절한 진료과를 추천합니다.
항상 한국어로 응답합니다."""

# 파라미터 설정
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_predict 256
```

```bash
# 커스텀 모델 빌드
ollama create hospital-assistant -f Modelfile

# 실행
ollama run hospital-assistant
```

---

## 9. 트러블슈팅

| 문제                   | 원인                 | 해결                               |
| ---------------------- | -------------------- | ---------------------------------- |
| `connection refused`   | Ollama 서버 미실행   | `ollama serve` 실행                |
| 모델 다운로드 실패     | 네트워크/디스크 공간 | 인터넷 연결 및 디스크 용량 확인    |
| OOM (Out of Memory)    | 모델이 RAM/VRAM 초과 | 더 작은 모델 또는 양자화 버전 사용 |
| 추론 속도 너무 느림    | CPU 전용 + 대형 모델 | GPU 사용 또는 소형 모델로 변경     |
| Windows에서 GPU 미인식 | CUDA 드라이버 미설치 | NVIDIA 드라이버 최신 버전 설치     |

---

## 10. RDB(MySQL) 데이터를 활용한 LLM 학습 방법

Ollama 로컬 LLM에 RDB 데이터를 활용하는 방법은 크게 3가지입니다.
모델 자체를 재학습(Fine-tuning)하는 방법과, 모델 변경 없이 데이터를 프롬프트로 주입하는 방법이 있습니다.

### 10.1 학습 방법 비교

| 방법                                    | 난이도 | GPU 필요 | 모델 변경   | 적합한 상황                               |
| --------------------------------------- | ------ | -------- | ----------- | ----------------------------------------- |
| **프롬프트 주입 (In-Context Learning)** | 낮음   | 불필요   | 없음        | DB 데이터를 참조하여 응답 생성, 빠른 적용 |
| **시스템 프롬프트 + Modelfile**         | 낮음   | 불필요   | 프롬프트만  | 도메인 지식을 시스템 프롬프트로 고정      |
| **Fine-tuning (GGUF 변환)**             | 높음   | 필수     | 모델 가중치 | 대량 데이터로 모델 자체를 특화            |

---

### 10.2 방법 1: 프롬프트 주입 (In-Context Learning)

MySQL에서 관련 데이터를 조회하여 LLM 프롬프트에 컨텍스트로 포함시키는 방식입니다.
모델 수정 없이 즉시 적용 가능하며, 가장 실용적인 방법입니다.

#### 아키텍처

```text
[사용자 질문]
    ↓
[Python FastAPI]
    ↓ (1) MySQL에서 관련 데이터 조회
[MySQL] → 조회 결과
    ↓ (2) 프롬프트 = 시스템 지시 + DB 데이터 + 사용자 질문
[Ollama] → LLM 응답
    ↓
[사용자에게 반환]
```

#### Python 구현 예시

```python
"""
RDB 데이터를 활용한 프롬프트 주입 서비스
python-llm/rdb_context_service.py
"""

import logging
import aiomysql
import httpx

logger = logging.getLogger(__name__)

# MySQL 연결 설정
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "password",
    "db": "llm_db",
}

OLLAMA_BASE_URL = "http://localhost:11434"


async def get_db_pool():
    """MySQL 커넥션 풀 생성"""
    return await aiomysql.create_pool(**DB_CONFIG, minsize=1, maxsize=5)


async def fetch_context_from_db(query: str, pool) -> str:
    """
    사용자 질문과 관련된 데이터를 MySQL에서 조회하여
    LLM 컨텍스트로 변환

    예: chat_history에서 유사한 과거 대화 검색
    """
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 과거 대화 이력에서 키워드 매칭
            await cur.execute(
                """
                SELECT query, response
                FROM chat_history
                WHERE status = 'COMPLETED'
                  AND query LIKE %s
                ORDER BY timestamp DESC
                LIMIT 5
                """,
                (f"%{query[:20]}%",),
            )
            rows = await cur.fetchall()

    if not rows:
        return ""

    context_lines = ["[참고: 과거 대화 이력]"]
    for row in rows:
        context_lines.append(f"Q: {row['query']}")
        context_lines.append(f"A: {row['response']}")
        context_lines.append("")

    return "\n".join(context_lines)


async def generate_with_rdb_context(
    query: str,
    pool,
    model: str = "gemma3:4b",
    temperature: float = 0.7,
) -> str:
    """
    MySQL 데이터를 컨텍스트로 포함하여 Ollama 추론 수행

    1. MySQL에서 관련 데이터 조회
    2. 시스템 프롬프트 + DB 컨텍스트 + 사용자 질문 조합
    3. Ollama API 호출
    """
    # (1) DB에서 컨텍스트 조회
    db_context = await fetch_context_from_db(query, pool)

    # (2) 프롬프트 조합
    system_prompt = (
        "당신은 병원 예약 시스템의 AI 어시스턴트입니다.\n"
        "아래 참고 데이터를 활용하여 정확하게 응답하세요.\n"
        "참고 데이터에 없는 내용은 일반 지식으로 답변하세요."
    )

    messages = [
        {"role": "system", "content": system_prompt},
    ]

    if db_context:
        messages.append({"role": "system", "content": db_context})

    messages.append({"role": "user", "content": query})

    # (3) Ollama Chat API 호출
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
        )
        response.raise_for_status()
        result = response.json()
        return result.get("message", {}).get("content", "")
```

#### FastAPI 엔드포인트 추가

```python
# app.py에 추가
from rdb_context_service import get_db_pool, generate_with_rdb_context

db_pool = None

@app.on_event("startup")
async def startup():
    global db_pool
    db_pool = await get_db_pool()

@app.on_event("shutdown")
async def shutdown():
    if db_pool:
        db_pool.close()
        await db_pool.wait_closed()

@app.post("/infer/with-context", response_model=InferResponse)
async def infer_with_context(request: InferRequest) -> InferResponse:
    """RDB 데이터를 컨텍스트로 활용한 LLM 추론"""
    generated_text = await generate_with_rdb_context(
        query=request.query,
        pool=db_pool,
        model=get_settings().ollama_model,
        temperature=request.temperature,
    )
    return InferResponse(generated_text=generated_text)
```

#### 의존성 추가

```bash
pip install aiomysql
```

---

### 10.3 방법 2: 시스템 프롬프트 + Modelfile (도메인 특화)

MySQL에서 도메인 데이터를 추출하여 Modelfile의 시스템 프롬프트에 포함시키는 방식입니다.
모델 자체는 변경하지 않지만, 항상 특정 도메인 지식을 갖고 응답합니다.

#### Step 1: MySQL에서 학습 데이터 추출

```sql
-- 진료과 정보 추출
SELECT department_name, description, symptoms
FROM departments
ORDER BY department_name;

-- 의사 정보 추출
SELECT d.name, d.specialty, dept.department_name
FROM doctors d
JOIN departments dept ON d.department_id = dept.id;

-- 자주 묻는 질문 추출
SELECT query, response
FROM chat_history
WHERE status = 'COMPLETED'
ORDER BY timestamp DESC
LIMIT 100;
```

#### Step 2: 추출 스크립트 작성

```python
"""
MySQL 데이터를 Modelfile용 시스템 프롬프트로 변환
python-llm/export_modelfile_data.py
"""

import pymysql


def export_domain_data() -> str:
    """MySQL에서 도메인 데이터를 추출하여 시스템 프롬프트 생성"""
    conn = pymysql.connect(
        host="localhost",
        user="root",
        password="password",
        db="llm_db",
        charset="utf8mb4",
    )

    prompt_parts = [
        "당신은 병원 예약 시스템의 AI 어시스턴트입니다.",
        "아래는 시스템에 등록된 정보입니다. 이 정보를 기반으로 정확하게 답변하세요.",
        "",
    ]

    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        # 진료과 정보
        cur.execute("SELECT department_name, description FROM departments")
        departments = cur.fetchall()
        if departments:
            prompt_parts.append("[진료과 목록]")
            for dept in departments:
                prompt_parts.append(
                    f"- {dept['department_name']}: {dept['description']}"
                )
            prompt_parts.append("")

        # FAQ 데이터
        cur.execute(
            """
            SELECT query, response FROM chat_history
            WHERE status = 'COMPLETED'
            ORDER BY timestamp DESC LIMIT 50
            """
        )
        faqs = cur.fetchall()
        if faqs:
            prompt_parts.append("[자주 묻는 질문]")
            for faq in faqs:
                prompt_parts.append(f"Q: {faq['query']}")
                prompt_parts.append(f"A: {faq['response']}")
                prompt_parts.append("")

    conn.close()
    return "\n".join(prompt_parts)


def generate_modelfile(output_path: str = "Modelfile"):
    """Modelfile 생성"""
    domain_data = export_domain_data()

    modelfile_content = f'''FROM gemma3:4b

SYSTEM """{domain_data}"""

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_predict 512
'''

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(modelfile_content)

    print(f"Modelfile 생성 완료: {output_path}")


if __name__ == "__main__":
    generate_modelfile()
```

#### Step 3: 커스텀 모델 빌드 및 실행

```bash
# 데이터 추출 및 Modelfile 생성
python export_modelfile_data.py

# Ollama 커스텀 모델 빌드
ollama create hospital-assistant -f Modelfile

# 테스트
ollama run hospital-assistant "내과 진료 예약하려면 어떻게 하나요?"
```

#### 데이터 갱신 자동화

DB 데이터가 변경될 때마다 모델을 재빌드하는 스크립트:

```bash
#!/bin/bash
# rebuild_model.sh - 주기적으로 실행 (cron 등록 권장)

cd /path/to/python-llm

# 1. MySQL에서 최신 데이터 추출 → Modelfile 생성
python export_modelfile_data.py

# 2. 기존 모델 삭제 후 재빌드
ollama rm hospital-assistant 2>/dev/null
ollama create hospital-assistant -f Modelfile

echo "모델 재빌드 완료: $(date)"
```

---

### 10.4 방법 3: Fine-tuning (모델 재학습)

RDB 데이터로 모델 가중치를 직접 학습시키는 방법입니다.
가장 높은 품질을 달성할 수 있지만, GPU와 학습 환경이 필요합니다.

#### 전체 흐름

```text
[MySQL] → (1) 학습 데이터 추출 (JSONL)
    ↓
[Python] → (2) Unsloth/LoRA로 Fine-tuning
    ↓
[GGUF 파일] → (3) Ollama에 등록
    ↓
[Ollama 서버] → (4) Fine-tuned 모델로 추론
```

#### Step 1: MySQL에서 학습 데이터 추출 (JSONL 형식)

```python
"""
MySQL 데이터를 Fine-tuning용 JSONL로 변환
python-llm/export_training_data.py
"""

import json
import pymysql


def export_to_jsonl(output_path: str = "training_data.jsonl"):
    """
    chat_history 테이블에서 학습 데이터 추출
    형식: ChatML (Ollama/Unsloth 호환)
    """
    conn = pymysql.connect(
        host="localhost",
        user="root",
        password="password",
        db="llm_db",
        charset="utf8mb4",
    )

    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute(
            """
            SELECT query, response
            FROM chat_history
            WHERE status = 'COMPLETED'
              AND response IS NOT NULL
              AND LENGTH(response) > 10
            ORDER BY timestamp
            """
        )
        rows = cur.fetchall()

    conn.close()

    with open(output_path, "w", encoding="utf-8") as f:
        for row in rows:
            # ChatML 형식
            entry = {
                "messages": [
                    {
                        "role": "system",
                        "content": "당신은 병원 예약 시스템의 AI 어시스턴트입니다.",
                    },
                    {"role": "user", "content": row["query"]},
                    {"role": "assistant", "content": row["response"]},
                ]
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"학습 데이터 {len(rows)}건 추출 완료: {output_path}")


if __name__ == "__main__":
    export_to_jsonl()
```

생성되는 `training_data.jsonl` 예시:

```jsonl
{"messages":[{"role":"system","content":"당신은 병원 예약 시스템의 AI 어시스턴트입니다."},{"role":"user","content":"두통이 심한데 어느 과로 가야 하나요?"},{"role":"assistant","content":"두통 증상은 신경과 또는 내과 진료를 추천드립니다."}]}
{"messages":[{"role":"system","content":"당신은 병원 예약 시스템의 AI 어시스턴트입니다."},{"role":"user","content":"예약 취소 방법"},{"role":"assistant","content":"마이페이지 > 예약 관리에서 취소할 수 있습니다."}]}
```

#### Step 2: Unsloth + LoRA로 Fine-tuning

```bash
# Fine-tuning 환경 설치 (GPU 필요, CUDA 11.8+)
pip install unsloth[colab-new]
pip install trl datasets
```

```python
"""
Unsloth LoRA Fine-tuning 스크립트
python-llm/finetune_ollama.py

요구사항: NVIDIA GPU (VRAM 8GB+), CUDA 11.8+
"""

from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments
from datasets import load_dataset

# (1) 베이스 모델 로딩 (4bit 양자화)
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/gemma-2-2b-it-bnb-4bit",  # 또는 llama-3.1-8b
    max_seq_length=2048,
    load_in_4bit=True,
)

# (2) LoRA 어댑터 설정
model = FastLanguageModel.get_peft_model(
    model,
    r=16,               # LoRA rank
    lora_alpha=16,
    lora_dropout=0,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
)

# (3) 학습 데이터 로딩
dataset = load_dataset("json", data_files="training_data.jsonl", split="train")

# (4) 학습 실행
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    args=TrainingArguments(
        output_dir="./finetuned_model",
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        num_train_epochs=3,
        learning_rate=2e-4,
        fp16=True,
        logging_steps=10,
        save_steps=100,
    ),
)

trainer.train()

# (5) GGUF로 변환 (Ollama 호환 형식)
model.save_pretrained_gguf(
    "hospital-model-gguf",
    tokenizer,
    quantization_method="q4_k_m",  # 4bit 양자화
)

print("Fine-tuning 및 GGUF 변환 완료!")
```

#### Step 3: Fine-tuned 모델을 Ollama에 등록

```dockerfile
# Modelfile.finetuned
FROM ./hospital-model-gguf/unsloth.Q4_K_M.gguf

SYSTEM """당신은 병원 예약 시스템의 AI 어시스턴트입니다.
환자의 증상을 분석하고 적절한 진료과를 추천합니다."""

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_predict 512
```

```bash
# Ollama에 등록
ollama create hospital-finetuned -f Modelfile.finetuned

# 테스트
ollama run hospital-finetuned "허리가 아프고 다리가 저린데 어디로 가야 하나요?"
```

---

### 10.5 방법별 권장 시나리오

| 시나리오                 | 권장 방법              | 이유                                              |
| ------------------------ | ---------------------- | ------------------------------------------------- |
| **빠른 프로토타입**      | 방법 1 (프롬프트 주입) | 모델 변경 없이 즉시 적용                          |
| **고정된 도메인 지식**   | 방법 2 (Modelfile)     | 매번 DB 조회 불필요, 응답 속도 빠름               |
| **대량 데이터 + 고품질** | 방법 3 (Fine-tuning)   | 모델이 도메인 지식을 내재화                       |
| **데이터가 자주 변경**   | 방법 1 + 방법 2 조합   | 실시간 데이터는 프롬프트, 고정 데이터는 Modelfile |

### 10.6 학습 데이터 품질 관리

| 항목              | 설명                                                            |
| ----------------- | --------------------------------------------------------------- |
| **데이터 정제**   | `status='COMPLETED'`인 정상 응답만 사용, 빈 응답·에러 응답 제외 |
| **최소 데이터량** | Fine-tuning: 최소 100건 이상, 권장 1,000건 이상                 |
| **데이터 다양성** | 다양한 질문 유형 포함 (증상 문의, 예약, FAQ 등)                 |
| **라벨 검증**     | 추출된 Q&A 쌍의 정확성을 사람이 검수                            |
| **개인정보 제거** | 환자명, 연락처 등 PII 마스킹 후 학습 데이터로 사용              |

### 10.7 전체 파이프라인 요약

```text
[MySQL (RDB)]
    │
    ├─→ 방법 1: 실시간 조회 → 프롬프트 주입 → Ollama /api/chat
    │                        (aiomysql + httpx)
    │
    ├─→ 방법 2: 데이터 추출 → Modelfile 시스템 프롬프트 → ollama create
    │                        (export_modelfile_data.py)
    │
    └─→ 방법 3: JSONL 추출 → Unsloth LoRA 학습 → GGUF 변환 → ollama create
                             (export_training_data.py → finetune_ollama.py)
```

---

## 11. 작업 체크리스트

### Ollama 서버 구축

- [ ] Ollama 설치 및 `ollama --version` 확인
- [ ] 추천 모델 다운로드 (`ollama pull gemma3:4b`)
- [ ] Ollama 서버 시작 및 API 테스트 (`curl localhost:11434/api/tags`)
- [ ] `python-llm/ollama_service.py` 구현
- [ ] `config.py`에 Ollama 설정 추가 (`LLM_BACKEND`, `OLLAMA_MODEL` 등)
- [ ] `.env`에 Ollama 설정 반영
- [ ] `/infer` 엔드포인트에서 Ollama 백엔드 연동 확인
- [ ] Spring Boot에서 Python 서버 경유 Ollama 추론 테스트
- [ ] (선택) Modelfile로 프로젝트 전용 커스텀 모델 생성
- [ ] (선택) Spring AI + Ollama 직접 연동 검토

### RDB 데이터 학습

- [ ] 방법 1: `rdb_context_service.py` 구현 (프롬프트 주입)
- [ ] 방법 1: `/infer/with-context` 엔드포인트 추가 및 테스트
- [ ] 방법 1: `aiomysql` 의존성 추가
- [ ] 방법 2: `export_modelfile_data.py` 작성 (Modelfile 생성기)
- [ ] 방법 2: 커스텀 모델 빌드 (`ollama create hospital-assistant`)
- [ ] (선택) 방법 3: `export_training_data.py` 작성 (JSONL 추출)
- [ ] (선택) 방법 3: Unsloth + LoRA Fine-tuning 실행
- [ ] (선택) 방법 3: GGUF 변환 후 Ollama 등록
- [ ] 학습 데이터 품질 검증 (PII 제거, 정확성 검수)

---

## 12. 문서 이력

| 버전 | 날짜       | 작성자 | 변경 내용                                                                     |
| ---- | ---------- | ------ | ----------------------------------------------------------------------------- |
| 1.0  | 2025-03-06 | -      | 최초 작성: Ollama 설치, 추천 모델, Python/Spring Boot 연동 가이드             |
| 1.1  | 2025-03-06 | -      | RDB(MySQL) 데이터 활용 학습 방법 추가 (프롬프트 주입, Modelfile, Fine-tuning) |
