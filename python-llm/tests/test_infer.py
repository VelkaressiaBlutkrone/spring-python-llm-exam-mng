"""
/infer 엔드포인트 테스트
LLM_FALLBACK_MOCK=1로 mock 응답 사용 (conftest.py)
"""

import pytest


def test_infer_success(client):
    """정상 요청 시 200, generated_text 반환"""
    response = client.post("/infer", json={"query": "Hello"})
    assert response.status_code == 200
    data = response.json()
    assert "generated_text" in data
    assert len(data["generated_text"]) > 0


def test_infer_with_params(client):
    """max_length, temperature 파라미터 전달"""
    response = client.post(
        "/infer",
        json={
            "query": "안녕하세요",
            "max_length": 50,
            "temperature": 0.5,
        },
    )
    assert response.status_code == 200
    assert "generated_text" in response.json()


def test_infer_empty_query_rejected(client):
    """빈 query는 스키마 검증 실패 (422)"""
    response = client.post("/infer", json={"query": ""})
    assert response.status_code == 422


def test_infer_missing_query(client):
    """query 누락 시 422"""
    response = client.post("/infer", json={})
    assert response.status_code == 422


def test_root(client):
    """GET / 서버 상태"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health(client):
    """GET /health 헬스체크"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
