"""의료 용어 오타 교정 모듈 테스트"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typo_corrector import correct_typos, _BUILTIN_TYPO_MAP


class TestCorrectTypos:
    """correct_typos 함수 테스트"""

    def test_single_typo(self):
        assert correct_typos("무릅이 아파요") == "무릎이 아파요"

    def test_multiple_typos(self):
        result = correct_typos("무릅 골졀 의심됩니다")
        assert "무릎" in result
        assert "골절" in result

    def test_no_typo(self):
        original = "무릎이 아파요"
        assert correct_typos(original) == original

    def test_empty_string(self):
        assert correct_typos("") == ""

    def test_none_input(self):
        assert correct_typos(None) is None

    def test_department_typo(self):
        assert correct_typos("정형외괴 가야하나요") == "정형외과 가야하나요"

    def test_disease_typo(self):
        assert correct_typos("고헐압 약 먹고 있어요") == "고혈압 약 먹고 있어요"

    def test_body_part_typo(self):
        assert correct_typos("어게가 아파요") == "어깨가 아파요"

    def test_mixed_normal_and_typo(self):
        result = correct_typos("무릅 관절이 아프고 두퉁도 있어요")
        assert "무릎" in result
        assert "관절" in result
        assert "두통" in result

    def test_long_compound_typo(self):
        assert correct_typos("허리듸스크 증상") == "허리디스크 증상"

    def test_typo_map_has_no_identity(self):
        """사전에 정상→정상 매핑이 없는지 확인"""
        for k, v in _BUILTIN_TYPO_MAP.items():
            assert k != v, f"Identity mapping found: '{k}'→'{v}'"

    def test_brain_disease_typo(self):
        assert correct_typos("뇌졸증 증상이에요") == "뇌졸중 증상이에요"

    def test_allergy_typo(self):
        assert correct_typos("알러지 있어요") == "알레르기 있어요"

    def test_abbreviation_conversion(self):
        assert "MRI" in correct_typos("엠알아이 찍어야 하나요")

    def test_ct_conversion(self):
        assert "CT" in correct_typos("씨티 촬영하고 싶어요")
