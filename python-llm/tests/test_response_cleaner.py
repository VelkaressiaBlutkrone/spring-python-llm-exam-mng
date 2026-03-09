"""LLM 응답 후처리 모듈 테스트"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from response_cleaner import clean_llm_response


class TestCleanLlmResponse:
    """clean_llm_response 함수 테스트"""

    def test_remove_special_tokens(self):
        text = "안녕하세요<|im_start|>user\n질문<|im_end|>"
        result = clean_llm_response(text)
        assert "<|im_start|>" not in result
        assert "<|im_end|>" not in result

    def test_remove_chinese_chars(self):
        text = "무릎이ocaly动 아파요"
        result = clean_llm_response(text)
        assert "动" not in result

    def test_remove_japanese_chars(self):
        text = "통증がある입니다"
        result = clean_llm_response(text)
        assert "がある" not in result

    def test_preserve_korean(self):
        text = "정형외과를 방문하세요."
        assert clean_llm_response(text) == text

    def test_preserve_english(self):
        text = "MRI 검사를 권장합니다."
        assert clean_llm_response(text) == text

    def test_normalize_whitespace(self):
        text = "통증이   심합니다.    정형외과를 방문하세요."
        result = clean_llm_response(text)
        assert "   " not in result

    def test_empty_string(self):
        assert clean_llm_response("") == ""

    def test_none_input(self):
        assert clean_llm_response(None) is None

    def test_trim_incomplete_ending(self):
        # 70% 이상 완성된 텍스트에서 불완전 문장 제거
        text = "정형외과를 방문하세요. 무릎 통증은 관절 문제일 수 있습니다. 추가로 검"
        result = clean_llm_response(text)
        assert result.endswith("있습니다.")

    def test_keep_short_incomplete(self):
        # 짧은 응답은 잘라내지 않음
        text = "정형외과"
        assert clean_llm_response(text) == text

    def test_mixed_garbled_response(self):
        """실제 발생한 깨진 응답 패턴"""
        text = (
            "**추천 진료과**: 정형외과\n\n"
            "무릎 통증이ocaly动\n"
            "<|im_start|><|im_start|><|im_start|>user\n"
            "무릎 너무 아파요"
        )
        result = clean_llm_response(text)
        assert "정형외과" in result
        assert "<|im_start|>" not in result
        assert "动" not in result
