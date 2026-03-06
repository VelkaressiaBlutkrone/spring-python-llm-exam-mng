# Ollama 로컬 LLM 서버 구축 가이드

> 참조: [PRD.md](./PRD.md), [TASK_PYTHON.md](./TASK_PYTHON.md)

OpenAI, Claude AI 등 외부 API 대신 **Ollama**를 활용하여 로컬 환경에서 LLM 서버를 운영하는 방법을 정의합니다.
비용 없이 프라이버시를 보장하며, 기존 Python FastAPI 서버와 연동하여 Spring Boot 아키텍처에 통합합니다.

---

## 1. Ollama 개요

| 항목 | 설명 |
| ---- | ---- |
| **Ollama란** | 로컬 환경에서 LLM을 간편하게 실행할 수 있는 오픈소스 도구 |
| **장점** | API 비용 없음, 데이터 외부 전송 없음(프라이버시), 오프라인 사용 가능 |
| **단점** | GPU 없으면 느림, 모델 크기에 따라 RAM/VRAM 요구량 높음 |
| **공식 사이트** | <https://ollama.com> |
| **GitHub** | <https://github.com/ollama/ollama> |

### 1.1 외부 API vs Ollama 비교

| 구분 | OpenAI / Claude API | Ollama (로컬) |
| ---- | ------------------- | ------------- |
| 비용 | 토큰 사용량 과금 | 무료 (하드웨어 비용만) |
| 프라이버시 | 외부 서버 전송 | 로컬 처리, 데이터 유출 없음 |
| 응답 속도 | 네트워크 의존 | GPU 있으면 빠름, CPU만이면 느림 |
| 모델 품질 | GPT-4o, Claude 등 최상급 | 오픈소스 모델 (Llama, Gemma 등) |
| 인터넷 필요 | 필수 | 모델 다운로드 후 불필요 |
| 설정 난이도 | API 키만 있으면 간단 | 로컬 설치 및 모델 다운로드 필요 |

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

| 용도 | 모델 | 크기 | 최소 RAM | 설명 |
| ---- | ---- | ---- | -------- | ---- |
| **경량 테스트** | `gemma3:4b` | ~3GB | 8GB | Google Gemma 3, 빠른 응답 |
| **일반 대화/QA** | `llama3.1:8b` | ~4.7GB | 8GB | Meta Llama 3.1, 범용 성능 우수 |
| **한국어 특화** | `gemma3:12b` | ~8GB | 16GB | 한국어 성능 양호 |
| **고품질 추론** | `llama3.1:70b` | ~40GB | 64GB | 대규모, 높은 품질 (GPU 권장) |
| **코드 생성** | `qwen2.5-coder:7b` | ~4.7GB | 8GB | 코드 작성 특화 |
| **경량 임베딩** | `nomic-embed-text` | ~274MB | 4GB | 텍스트 임베딩 (향후 RAG 확장 시) |

### 3.2 본 프로젝트 권장 모델

| 환경 | 권장 모델 | 이유 |
| ---- | --------- | ---- |
| **개발/테스트 (GPU 없음)** | `gemma3:4b` | 가볍고 빠름, CPU에서도 동작 |
| **개발/테스트 (GPU 있음)** | `llama3.1:8b` | 범용 성능 우수, 적절한 크기 |
| **프로덕션** | `gemma3:12b` 이상 | 한국어 지원, 안정적 품질 |

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

| 엔드포인트 | 메서드 | 설명 |
| ---------- | ------ | ---- |
| `/api/generate` | POST | 텍스트 생성 (completion) |
| `/api/chat` | POST | 대화형 생성 (chat) |
| `/api/tags` | GET | 설치된 모델 목록 |
| `/api/show` | POST | 모델 정보 조회 |
| `/api/pull` | POST | 모델 다운로드 |

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

| 모델 크기 | RAM | GPU VRAM | CPU 추론 속도 | GPU 추론 속도 |
| --------- | --- | -------- | ------------- | ------------- |
| 1B~4B | 8GB | 4GB | 보통 (5~15 tok/s) | 빠름 (30+ tok/s) |
| 7B~8B | 16GB | 8GB | 느림 (2~8 tok/s) | 빠름 (20+ tok/s) |
| 12B~14B | 32GB | 12GB | 매우 느림 | 보통 (15+ tok/s) |
| 70B | 64GB+ | 40GB+ | 사용 불가 수준 | 보통 |

### 7.1 GPU 지원

| GPU 종류 | 지원 여부 | 비고 |
| -------- | --------- | ---- |
| NVIDIA (CUDA) | 지원 | 가장 안정적, 6GB VRAM 이상 권장 |
| AMD (ROCm) | 부분 지원 | Linux에서 ROCm 설치 필요 |
| Apple Silicon | 지원 | Metal 가속, M1 이상 |
| CPU 전용 | 가능 | 소형 모델(4B 이하) 권장 |

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

| 항목 | 방법 |
| ---- | ---- |
| 모델 미리 로딩 | `ollama run <model>` 후 종료하면 메모리에 캐시 유지 |
| 양자화 모델 사용 | `q4_0`, `q4_K_M` 등 양자화 버전으로 메모리 절약 |
| 컨텍스트 길이 조절 | `num_ctx` 옵션으로 컨텍스트 윈도우 조절 |
| Keep-alive 설정 | 모델 언로드 시간 조절 (`keep_alive` 파라미터) |

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

| 문제 | 원인 | 해결 |
| ---- | ---- | ---- |
| `connection refused` | Ollama 서버 미실행 | `ollama serve` 실행 |
| 모델 다운로드 실패 | 네트워크/디스크 공간 | 인터넷 연결 및 디스크 용량 확인 |
| OOM (Out of Memory) | 모델이 RAM/VRAM 초과 | 더 작은 모델 또는 양자화 버전 사용 |
| 추론 속도 너무 느림 | CPU 전용 + 대형 모델 | GPU 사용 또는 소형 모델로 변경 |
| Windows에서 GPU 미인식 | CUDA 드라이버 미설치 | NVIDIA 드라이버 최신 버전 설치 |

---

## 10. 작업 체크리스트

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

---

## 11. 문서 이력

| 버전 | 날짜 | 작성자 | 변경 내용 |
| ---- | ---- | ------ | ---------- |
| 1.0 | 2025-03-06 | - | 최초 작성: Ollama 설치, 추천 모델, Python/Spring Boot 연동 가이드 |
