"""
설정 관리 - Pydantic Settings
환경변수 또는 .env 파일에서 로드
"""

from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 설정"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    llm_model: str = Field(default="gpt2", description="Hugging Face 모델명")
    llm_fallback_mock: bool = Field(default=False, description="torch 미지원 시 mock 사용")

    @field_validator("llm_fallback_mock", mode="before")
    @classmethod
    def parse_fallback_mock(cls, v):
        if isinstance(v, str) and v.lower() in ("1", "true", "yes", "on"):
            return True
        return v

    llm_infer_timeout_sec: int = Field(default=60, ge=1, le=600, description="추론 타임아웃(초)")
    llm_input_max_length: int = Field(default=2048, ge=1, le=32768, description="입력 최대 문자 수")
    llm_fallback_response: str = Field(default="", description="LLM 실패 시 반환할 기본 응답")

    # API 서버
    host: str = Field(default="0.0.0.0", description="서버 바인드 주소")
    port: int = Field(default=8000, ge=1, le=65535, description="서버 포트")

    # OpenAI (선택, 향후 확장용)
    openai_api_key: str = Field(default="", description="OpenAI API 키")


@lru_cache
def get_settings() -> Settings:
    """설정 싱글톤 (캐시)"""
    return Settings()
