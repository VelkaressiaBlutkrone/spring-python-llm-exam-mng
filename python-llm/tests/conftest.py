"""
pytest 설정: mock 모드로 테스트 (torch 불필요)
"""

import os

import pytest


@pytest.fixture(autouse=True)
def mock_llm_env(monkeypatch):
    """모든 테스트에서 LLM_FALLBACK_MOCK=1 사용"""
    monkeypatch.setenv("LLM_FALLBACK_MOCK", "1")


@pytest.fixture
def client():
    """FastAPI TestClient"""
    from fastapi.testclient import TestClient

    from app import app

    return TestClient(app)
