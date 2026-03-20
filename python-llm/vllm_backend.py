"""vLLM LLM 백엔드 구현"""

from typing import AsyncIterator

import httpx

from llm_backend import LLMBackend
from vllm_service import (
    check_vllm_health,
    chat_with_vllm,
    chat_with_vllm_stream,
    generate_with_vllm,
)


class VllmBackend(LLMBackend):
    """vLLM API 기반 LLM 백엔드"""

    async def generate(
        self, query, max_length=256, temperature=0.7, top_p=0.9, client=None
    ) -> str:
        return await generate_with_vllm(
            query,
            max_length=max_length,
            temperature=temperature,
            top_p=top_p,
            client=client,
        )

    async def chat(
        self, messages, temperature=0.7, max_length=256, stop=None, client=None
    ) -> str:
        return await chat_with_vllm(
            messages,
            temperature=temperature,
            max_length=max_length,
            stop=stop,
            client=client,
        )

    async def chat_stream(
        self, messages, temperature=0.7, max_length=256, stop=None, client=None
    ) -> AsyncIterator[dict]:
        async for chunk in chat_with_vllm_stream(
            messages,
            temperature=temperature,
            max_length=max_length,
            stop=stop,
            client=client,
        ):
            yield chunk

    async def health_check(self, client=None) -> bool:
        return await check_vllm_health(client=client)
