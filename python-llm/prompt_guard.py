"""Prompt Injection 기본 방어 모듈

사용자 입력(query)과 대화 이력(history)에서 알려진 프롬프트 인젝션 패턴을 감지하고
정제하여 LLM 시스템 프롬프트 우회를 방지한다.
"""

import logging
import re

logger = logging.getLogger(__name__)

# 알려진 프롬프트 인젝션 패턴 (대소문자 무시)
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?above\s+instructions",
    r"disregard\s+(all\s+)?previous",
    r"forget\s+(all\s+)?previous",
    r"you\s+are\s+now\s+a",
    r"new\s+instructions?\s*:",
    r"system\s*:\s*",
    r"<\|im_start\|>system",
    r"\[INST\]",
    r"\[\/INST\]",
    r"<\|system\|>",
    r"###\s*instruction",
    r"do\s+not\s+follow\s+(the\s+)?previous",
    r"override\s+(all\s+)?previous",
    r"이전\s*지시를?\s*무시",
    r"이전\s*명령을?\s*무시",
    r"시스템\s*프롬프트를?\s*무시",
    r"너는?\s*이제\s*부터",
]

_compiled_patterns = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def detect_injection(text: str) -> bool:
    """텍스트에서 프롬프트 인젝션 패턴을 감지한다."""
    for pattern in _compiled_patterns:
        if pattern.search(text):
            logger.warning(
                "Prompt injection detected: pattern=%s, text_preview=%s",
                pattern.pattern,
                text[:100],
            )
            return True
    return False


def sanitize_history(
    history: list[dict] | None,
    max_turns: int = 6,
    max_content_length: int = 2000,
) -> list[dict]:
    """대화 이력을 검증하고 정제한다.

    - role을 user/assistant로 제한
    - content 길이 제한
    - 인젝션 패턴이 포함된 메시지 제거
    - 최근 N턴만 유지
    """
    if not history:
        return []

    ALLOWED_ROLES = {"user", "assistant"}
    sanitized = []

    recent = history[-max_turns:]
    for msg in recent:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role not in ALLOWED_ROLES:
            logger.warning("Invalid role in history: %s", role)
            continue

        if not content or not isinstance(content, str):
            continue

        # 길이 제한
        content = content[:max_content_length]

        # 인젝션 감지
        if detect_injection(content):
            logger.warning("Prompt injection in history removed: role=%s", role)
            continue

        sanitized.append({"role": role, "content": content})

    return sanitized


def sanitize_query(query: str) -> tuple[str, bool]:
    """사용자 쿼리를 검증한다.

    Returns:
        (query, is_suspicious): 인젝션 감지 시 is_suspicious=True
    """
    is_suspicious = detect_injection(query)
    if is_suspicious:
        logger.warning("Prompt injection in query detected: %s", query[:100])
    return query, is_suspicious
