"""
의학 컨텍스트 서비스 테스트
- extract_keywords 단위 테스트
- /infer/medical 엔드포인트 테스트 (Ollama mock)
"""

import pytest
from unittest.mock import AsyncMock, patch


def test_extract_keywords_korean():
    """한글 키워드 추출"""
    from medical_context_service import extract_keywords

    result = extract_keywords("두통이 심하고 어지러운데 어느 과로 가야 하나요?")
    assert "+두통이" in result
    assert "+심하고" in result


def test_extract_keywords_english():
    """영문 키워드 추출"""
    from medical_context_service import extract_keywords

    result = extract_keywords("headache and dizziness symptoms")
    assert "+headache" in result
    assert "+dizziness" in result


def test_extract_keywords_single_char():
    """1글자는 필터링되어 빈 문자열 반환"""
    from medical_context_service import extract_keywords

    result = extract_keywords("가 나 다")
    assert result == ""


def test_extract_keywords_empty():
    """빈 문자열 입력"""
    from medical_context_service import extract_keywords

    result = extract_keywords("")
    assert result == ""


def test_extract_keywords_max_limit():
    """최대 8개 키워드만 추출"""
    from medical_context_service import extract_keywords

    result = extract_keywords("하나 둘이 셋이 넷이 다섯 여섯 일곱 여덟 아홉 열이")
    words = result.split()
    assert len(words) <= 8


def test_infer_medical_endpoint_exists(client):
    """POST /infer/medical 엔드포인트 존재 확인 (422 = 라우트 존재, body 누락)"""
    response = client.post("/infer/medical", json={})
    # query 누락 → 422 (엔드포인트 존재 확인)
    assert response.status_code == 422


def test_infer_medical_empty_query_rejected(client):
    """빈 query는 스키마 검증 실패 (422)"""
    response = client.post("/infer/medical", json={"query": ""})
    assert response.status_code == 422
