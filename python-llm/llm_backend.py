"""LLM 백엔드 추상화 - Strategy 패턴

모든 LLM 백엔드(Ollama, vLLM)가 구현해야 하는 공통 인터페이스를 정의한다.
app.py에서 if/else 분기 없이 동일한 메서드를 호출할 수 있다.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator

import httpx


class LLMBackend(ABC):
    """LLM 백엔드 공통 인터페이스"""

    @abstractmethod
    async def generate(
        self,
        query: str,
        max_length: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.9,
        client: httpx.AsyncClient | None = None,
    ) -> str:
        """텍스트 생성 (단순 추론)"""
        ...

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_length: int = 256,
        stop: list[str] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> str:
        """채팅 형식 추론"""
        ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_length: int = 256,
        stop: list[str] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> AsyncIterator[dict]:
        """채팅 스트리밍"""
        ...

    @abstractmethod
    async def health_check(
        self, client: httpx.AsyncClient | None = None
    ) -> bool:
        """헬스체크"""
        ...
