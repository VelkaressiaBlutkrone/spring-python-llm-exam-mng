"""
vLLM LLM 서비스
OpenAI 호환 API를 통한 LLM 추론 (vLLM 서버)
"""

import json
import logging

import httpx

from circuit_breaker import CircuitBreaker, ServiceUnavailableError
from config import get_settings

_breaker = CircuitBreaker(failure_threshold=5, reset_timeout=30.0)

logger = logging.getLogger(__name__)


async def generate_with_vllm(
    query: str,
    model: str | None = None,
    max_length: int = 100,
    temperature: float = 0.7,
    top_p: float = 1.0,
    client: httpx.AsyncClient | None = None,
) -> str:
    """
    vLLM /v1/completions API를 통한 텍스트 생성

    Args:
        query: 입력 텍스트
        model: vLLM 모델명 (None이면 설정값 사용)
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
    model = model or settings.vllm_model

    payload = {
        "model": model,
        "prompt": query,
        "max_tokens": max_length,
        "temperature": temperature,
        "top_p": top_p,
    }

    async def _call(c: httpx.AsyncClient) -> str:
        try:
            response = await c.post(
                f"{settings.vllm_base_url}/v1/completions",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            _breaker.record_success()
            choices = result.get("choices", [])
            if choices:
                return choices[0].get("text", "")
            return ""
        except httpx.ConnectError:
            logger.error("vLLM 서버 연결 실패: %s", settings.vllm_base_url)
            _breaker.record_failure()
            raise ConnectionError(
                "vLLM 서버에 연결할 수 없습니다. vLLM 서버 실행 여부를 확인하세요."
            )
        except httpx.ReadTimeout:
            logger.warning("vLLM 추론 타임아웃")
            _breaker.record_failure()
            raise TimeoutError("vLLM 추론 타임아웃")

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


async def chat_with_vllm(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    max_length: int = 256,
    stop: list[str] | None = None,
    client: httpx.AsyncClient | None = None,
) -> str:
    """
    vLLM /v1/chat/completions API를 통한 대화형 생성

    Args:
        messages: [{"role": "user", "content": "..."}] 형식의 메시지 리스트
        model: vLLM 모델명
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
    model = model or settings.vllm_model

    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_length,
    }
    if stop:
        payload["stop"] = stop

    async def _call(c: httpx.AsyncClient) -> str:
        try:
            response = await c.post(
                f"{settings.vllm_base_url}/v1/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            _breaker.record_success()
            choices = result.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""
        except httpx.ConnectError:
            logger.error("vLLM 서버 연결 실패: %s", settings.vllm_base_url)
            _breaker.record_failure()
            raise ConnectionError(
                "vLLM 서버에 연결할 수 없습니다. vLLM 서버 실행 여부를 확인하세요."
            )
        except httpx.ReadTimeout:
            logger.warning("vLLM Chat 추론 타임아웃")
            _breaker.record_failure()
            raise TimeoutError("vLLM Chat 추론 타임아웃")

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


async def chat_with_vllm_stream(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    max_length: int = 256,
    stop: list[str] | None = None,
    client: httpx.AsyncClient | None = None,
):
    """
    vLLM /v1/chat/completions 스트리밍 — 토큰 단위 AsyncGenerator

    vLLM은 OpenAI SSE 형식을 사용:
      data: {"choices":[{"delta":{"content":"토큰"}}]}
      data: [DONE]

    Yields:
        dict — {"token": str} 또는 {"done": True}
    """
    if not _breaker.can_execute():
        raise ServiceUnavailableError("LLM 서비스가 일시적으로 중단되었습니다. 잠시 후 다시 시도해 주세요.")

    settings = get_settings()
    model = model or settings.vllm_model

    payload: dict = {
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": temperature,
        "max_tokens": max_length,
    }
    if stop:
        payload["stop"] = stop

    async def _stream(c: httpx.AsyncClient):
        try:
            async with c.stream(
                "POST",
                f"{settings.vllm_base_url}/v1/chat/completions",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    # SSE 형식: "data: {...}" 또는 "data: [DONE]"
                    if line.startswith("data: "):
                        data_str = line[6:]  # "data: " 제거
                        if data_str == "[DONE]":
                            _breaker.record_success()
                            yield {"done": True}
                            return
                        chunk = json.loads(data_str)
                        choices = chunk.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            token = delta.get("content", "")
                            finish_reason = choices[0].get("finish_reason")
                            if token:
                                yield {"token": token}
                            if finish_reason is not None:
                                _breaker.record_success()
                                yield {"done": True}
                                return
        except httpx.ConnectError:
            logger.error("vLLM 서버 연결 실패: %s", settings.vllm_base_url)
            _breaker.record_failure()
            raise ConnectionError(
                "vLLM 서버에 연결할 수 없습니다. vLLM 서버 실행 여부를 확인하세요."
            )
        except httpx.ReadTimeout:
            logger.warning("vLLM Stream 추론 타임아웃")
            _breaker.record_failure()
            raise TimeoutError("vLLM Stream 추론 타임아웃")

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


async def check_vllm_health(client: httpx.AsyncClient | None = None) -> bool:
    """vLLM 서버 상태 확인"""
    settings = get_settings()
    try:
        if client is not None:
            response = await client.get(f"{settings.vllm_base_url}/health")
            return response.status_code == 200
        async with httpx.AsyncClient(timeout=3.0) as _client:
            response = await _client.get(f"{settings.vllm_base_url}/health")
            return response.status_code == 200
    except Exception:
        return False


async def list_models(client: httpx.AsyncClient | None = None) -> list[str]:
    """vLLM 서버 모델 목록 조회"""
    settings = get_settings()
    try:
        if client is not None:
            response = await client.get(f"{settings.vllm_base_url}/v1/models")
            response.raise_for_status()
            data = response.json()
        else:
            async with httpx.AsyncClient(timeout=5.0) as _client:
                response = await _client.get(f"{settings.vllm_base_url}/v1/models")
                response.raise_for_status()
                data = response.json()
        return [m["id"] for m in data.get("data", [])]
    except Exception:
        return []
