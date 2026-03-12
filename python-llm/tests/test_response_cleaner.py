"""LLM 응답 후처리 모듈 테스트"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from response_cleaner import clean_llm_response, _trim_incomplete_ending


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

    def test_removes_endoftext(self):
        result = clean_llm_response("답변입니다<|endoftext|>추가")
        assert "<|endoftext|>" not in result

    def test_converts_fullwidth_punctuation(self):
        result = clean_llm_response("내용。다음，항목")
        assert "。" not in result
        assert "，" not in result

    def test_removes_repeated_cjk_punctuation(self):
        result = clean_llm_response("내용，。，。계속")
        assert "，。" not in result

    def test_normalizes_newlines(self):
        result = clean_llm_response("줄1\n\n\n\n줄2")
        assert "\n\n\n" not in result

    def test_clean_text_unchanged(self):
        text = "정상적인 한국어 텍스트입니다."
        assert clean_llm_response(text) == text

    def test_mixed_content(self):
        text = "<|im_start|>추천 진료과: 정형외과。推薦<|im_end|>"
        result = clean_llm_response(text)
        assert "정형외과" in result
        assert "<|" not in result
        assert "推薦" not in result


class TestTrimIncompleteEnding:
    def test_complete_sentence_korean(self):
        text = "진료과: 정형외과입니다"
        result = _trim_incomplete_ending(text)
        assert result == text

    def test_complete_with_period(self):
        text = "진료를 받으세요."
        assert _trim_incomplete_ending(text) == text

    def test_complete_with_question_mark(self):
        text = "어디가 아프신가요?"
        assert _trim_incomplete_ending(text) == text

    def test_empty_string(self):
        assert _trim_incomplete_ending("") == ""
