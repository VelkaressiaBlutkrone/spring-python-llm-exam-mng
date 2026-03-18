"""
Ollama LLM 서비스
로컬 Ollama 서버를 통한 LLM 추론
"""

import json
import logging

import httpx

from circuit_breaker import CircuitBreaker, ServiceUnavailableError
from config import get_settings

_breaker = CircuitBreaker(failure_threshold=5, reset_timeout=30.0)

logger = logging.getLogger(__name__)


async def generate_with_ollama(
    query: str,
    model: str | None = None,
    max_length: int = 100,
    temperature: float = 0.7,
    top_p: float = 1.0,
    client: httpx.AsyncClient | None = None,
) -> str:
    """
    Ollama /api/generate API를 통한 텍스트 생성

    Args:
        query: 입력 텍스트
        model: Ollama 모델명 (None이면 설정값 사용)
        max_length: 최대 생성 토큰 수
        temperature: 생성 다양성
        top_p: nucleus sampling
        client: 공유 httpx 클라이언트 (None이면 자체 생성)

    Returns:
        생성된 텍스트
    """
    if not _breaker.can_execute():
        raise ServiceUnavailableError("LLM 서비스가 일시적으로 중단되었습니다. 잠시 후 다시 시도해 주세요.")
    settings = get_settings()
    model = model or settings.ollama_model

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

    async def _call(c: httpx.AsyncClient) -> str:
        try:
            response = await c.post(
                f"{settings.ollama_base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            _breaker.record_success()
            return result.get("response", "")
        except httpx.ConnectError:
            logger.error("Ollama 서버 연결 실패: %s", settings.ollama_base_url)
            _breaker.record_failure()
            raise ConnectionError(
                "Ollama 서버에 연결할 수 없습니다. ollama serve 실행 여부를 확인하세요."
            )
        except httpx.ReadTimeout:
            logger.warning("Ollama 추론 타임아웃")
            _breaker.record_failure()
            raise TimeoutError("Ollama 추론 타임아웃")

    if client is not None:
        return await _call(client)

    timeout = httpx.Timeout(
        connect=5.0,
        read=float(settings.llm_infer_timeout_sec),
        write=5.0,
        pool=5.0,
    )
    async with httpx.AsyncClient(timeout=timeout) as _client:
        return await _call(_client)


async def chat_with_ollama(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    max_length: int = 256,
    stop: list[str] | None = None,
    client: httpx.AsyncClient | None = None,
) -> str:
    """
    Ollama /api/chat API를 통한 대화형 생성

    Args:
        messages: [{"role": "user", "content": "..."}] 형식의 메시지 리스트
        model: Ollama 모델명
        temperature: 생성 다양성
        max_length: 최대 생성 토큰 수
        stop: 생성 중단 토큰 리스트
        client: 공유 httpx 클라이언트 (None이면 자체 생성)

    Returns:
        생성된 응답 텍스트
    """
    if not _breaker.can_execute():
        raise ServiceUnavailableError("LLM 서비스가 일시적으로 중단되었습니다. 잠시 후 다시 시도해 주세요.")
    settings = get_settings()
    model = model or settings.ollama_model

    options: dict = {
        "temperature": temperature,
        "num_predict": max_length,
    }
    if stop:
        options["stop"] = stop

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": options,
    }

    async def _call(c: httpx.AsyncClient) -> str:
        try:
            response = await c.post(
                f"{settings.ollama_base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            _breaker.record_success()
            return result.get("message", {}).get("content", "")
        except httpx.ConnectError:
            logger.error("Ollama 서버 연결 실패: %s", settings.ollama_base_url)
            _breaker.record_failure()
            raise ConnectionError(
                "Ollama 서버에 연결할 수 없습니다. ollama serve 실행 여부를 확인하세요."
            )
        except httpx.ReadTimeout:
            logger.warning("Ollama Chat 추론 타임아웃")
            _breaker.record_failure()
            raise TimeoutError("Ollama Chat 추론 타임아웃")

    if client is not None:
        return await _call(client)

    timeout = httpx.Timeout(
        connect=5.0,
        read=float(settings.llm_infer_timeout_sec),
        write=5.0,
        pool=5.0,
    )
    async with httpx.AsyncClient(timeout=timeout) as _client:
        return await _call(_client)


async def chat_with_ollama_stream(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    max_length: int = 256,
    stop: list[str] | None = None,
    client: httpx.AsyncClient | None = None,
):
    """
    Ollama /api/chat 스트리밍 — 토큰 단위 AsyncGenerator

    Args:
        messages: 메시지 리스트
        model: Ollama 모델명
        temperature: 생성 다양성
        max_length: 최대 생성 토큰 수
        stop: 생성 중단 토큰 리스트
        client: 공유 httpx 클라이언트 (None이면 자체 생성)

    Yields:
        dict — {"token": str} 또는 {"done": True}
    """
    if not _breaker.can_execute():
        raise ServiceUnavailableError("LLM 서비스가 일시적으로 중단되었습니다. 잠시 후 다시 시도해 주세요.")

    settings = get_settings()
    model = model or settings.ollama_model

    options: dict = {
        "temperature": temperature,
        "num_predict": max_length,
    }
    if stop:
        options["stop"] = stop

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": options,
    }

    async def _stream(c: httpx.AsyncClient):
        try:
            async with c.stream(
                "POST",
                f"{settings.ollama_base_url}/api/chat",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    done = chunk.get("done", False)
                    if token:
                        yield {"token": token}
                    if done:
                        _breaker.record_success()
                        yield {"done": True}
        except httpx.ConnectError:
            logger.error("Ollama 서버 연결 실패: %s", settings.ollama_base_url)
            _breaker.record_failure()
            raise ConnectionError(
                "Ollama 서버에 연결할 수 없습니다. ollama serve 실행 여부를 확인하세요."
            )
        except httpx.ReadTimeout:
            logger.warning("Ollama Stream 추론 타임아웃")
            _breaker.record_failure()
            raise TimeoutError("Ollama Stream 추론 타임아웃")

    if client is not None:
        async for item in _stream(client):
            yield item
    else:
        timeout = httpx.Timeout(
            connect=5.0,
            read=float(settings.llm_infer_timeout_sec),
            write=5.0,
            pool=5.0,
        )
        async with httpx.AsyncClient(timeout=timeout) as _client:
            async for item in _stream(_client):
                yield item


async def check_ollama_health(client: httpx.AsyncClient | None = None) -> bool:
    """Ollama 서버 상태 확인"""
    settings = get_settings()
    try:
        if client is not None:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            return response.status_code == 200
        async with httpx.AsyncClient(timeout=3.0) as _client:
            response = await _client.get(f"{settings.ollama_base_url}/api/tags")
            return response.status_code == 200
    except Exception:
        return False


async def list_models(client: httpx.AsyncClient | None = None) -> list[str]:
    """설치된 Ollama 모델 목록 조회"""
    settings = get_settings()
    if client is not None:
        response = await client.get(f"{settings.ollama_base_url}/api/tags")
        response.raise_for_status()
        data = response.json()
        return [m["name"] for m in data.get("models", [])]
    async with httpx.AsyncClient(timeout=5.0) as _client:
        response = await _client.get(f"{settings.ollama_base_url}/api/tags")
        response.raise_for_status()
        data = response.json()
        return [m["name"] for m in data.get("models", [])]
