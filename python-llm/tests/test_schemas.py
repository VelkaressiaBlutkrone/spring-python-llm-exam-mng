"""schemas 유효성 검증 테스트"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from pydantic import ValidationError
from schemas import InferRequest


class TestInferRequest:
    def test_valid_request(self):
        req = InferRequest(query="무릎이 아파요")
        assert req.query == "무릎이 아파요"
        assert req.max_length == 512
        assert req.temperature == 0.7

    def test_empty_query_rejected(self):
        with pytest.raises(ValidationError):
            InferRequest(query="")

    def test_temperature_too_high(self):
        with pytest.raises(ValidationError):
            InferRequest(query="test", temperature=3.0)

    def test_temperature_negative(self):
        with pytest.raises(ValidationError):
            InferRequest(query="test", temperature=-0.1)

    def test_max_length_bounds(self):
        with pytest.raises(ValidationError):
            InferRequest(query="test", max_length=0)
        with pytest.raises(ValidationError):
            InferRequest(query="test", max_length=3000)

    def test_default_values(self):
        req = InferRequest(query="test")
        assert req.top_p == 1.0
        assert req.num_return_sequences == 1
