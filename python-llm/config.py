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
    llm_backend: str = Field(default="vllm", description="LLM 백엔드 (huggingface | ollama | vllm)")
    llm_model: str = Field(default="Qwen/Qwen2.5-7B-Instruct", description="Hugging Face 모델명")
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
    medical_context_max_chars: int = Field(default=1500, ge=100, le=8000, description="의학 컨텍스트 최대 문자 수")

    # Ollama (폴백 + 임베딩용)
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama 서버 URL")
    ollama_model: str = Field(default="qwen2.5:7b", description="Ollama 모델명")
    ollama_embed_model: str = Field(default="nomic-embed-text", description="Ollama 임베딩 모델명")

    # vLLM (OpenAI 호환 API)
    vllm_base_url: str = Field(default="http://localhost:8000", description="vLLM 서버 URL")
    vllm_model: str = Field(default="qwen2.5-7b", description="vLLM 모델명")

    # ChromaDB (벡터 검색 - Docker HttpClient)
    chroma_host: str = Field(default="localhost", description="ChromaDB 서버 호스트")
    chroma_port: int = Field(default=8100, ge=1, le=65535, description="ChromaDB 서버 포트")
    chroma_collection: str = Field(default="medical_docs", description="ChromaDB 컬렉션명")
    chroma_rule_collection: str = Field(default="medical_rules", description="병원규칙 ChromaDB 컬렉션명")
    vector_search_top_k: int = Field(default=3, ge=1, le=20, description="벡터 검색 상위 K건")
    use_vector_search: bool = Field(default=True, description="벡터 검색 사용 여부")
    use_query_expansion: bool = Field(default=False, description="쿼리 확장 사용 여부")
    use_reranking: bool = Field(default=False, description="Re-ranking 사용 여부")

    # MySQL (의학데이터 조회)
    mysql_host: str = Field(default="127.0.0.1", description="MySQL 호스트")
    mysql_port: int = Field(default=3307, ge=1, le=65535, description="MySQL 포트")
    mysql_user: str = Field(default="root", description="MySQL 사용자")
    mysql_password: str = Field(default="", description="MySQL 비밀번호 (환경변수 MYSQL_PASSWORD 필수)")
    mysql_db: str = Field(default="llm_db", description="MySQL 데이터베이스명")

    # CORS
    cors_origins: str = Field(default="http://localhost:8080,http://127.0.0.1:8080", description="허용 CORS origins (콤마 구분)")

    # API 서버
    host: str = Field(default="0.0.0.0", description="서버 바인드 주소")
    port: int = Field(default=8000, ge=1, le=65535, description="서버 포트")


@lru_cache
def get_settings() -> Settings:
    """설정 싱글톤 (캐시)"""
    return Settings()
