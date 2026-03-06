"""
pytest 설정: mock 모드로 테스트 (torch 불필요)
llm_service.generate를 직접 mock하여 torch import를 완전히 회피
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
