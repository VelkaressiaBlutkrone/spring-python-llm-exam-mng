"""프롬프트 파일 로더"""
import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"

ALLOWED_PROMPTS = {"medical_system", "rule_system"}


@lru_cache
def load_prompt(name: str) -> str:
    """프롬프트 파일을 읽어 반환한다. 결과는 캐시된다."""
    if name not in ALLOWED_PROMPTS:
        raise ValueError(f"Invalid prompt name: {name}")
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        logger.error("Prompt file not found: %s", path)
        raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {path}")
    text = path.read_text(encoding="utf-8")
    logger.info("Loaded prompt '%s' (%d chars)", name, len(text))
    return text


def reload_prompt(name: str) -> str:
    """캐시를 무효화하고 프롬프트를 다시 로드한다."""
    load_prompt.cache_clear()
    return load_prompt(name)
