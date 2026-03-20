"""
pytest 공통 픽스처.

- ``LLM_FALLBACK_MOCK=1`` 로 두어 HF 경로 테스트 시 GPU/torch 없이 동작하게 한다.
- ``sys.modules["llm_service"]`` 를 MagicMock 으로 밀어 넣어 ``app`` import 시
  ``transformers`` 로딩을 아예 하지 않는다.
"""

import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def mock_llm_env(monkeypatch):
    """모든 테스트에서 LLM_FALLBACK_MOCK=1 사용"""
    monkeypatch.setenv("LLM_FALLBACK_MOCK", "1")


def _mock_generate(query: str, **kwargs) -> str:
    """torch 없이 동작하는 mock generate"""
    return f"[Mock] {query}"


# llm_service 모듈을 mock으로 교체하여 transformers/torch import 방지
_mock_llm_service = MagicMock()
_mock_llm_service.generate = _mock_generate
sys.modules["llm_service"] = _mock_llm_service


@pytest.fixture
def client():
    """FastAPI TestClient"""
    from fastapi.testclient import TestClient

    from app import app

    return TestClient(app)
