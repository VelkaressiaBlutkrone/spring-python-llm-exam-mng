"""
LLM 응답 후처리 모듈
- 특수 토큰 제거 (<|im_start|>, <|im_end|> 등)
- 비한국어/비영어 문자 혼입 제거
- 응답 잘림 정리
"""

import logging
import re

logger = logging.getLogger(__name__)

# LLM 특수 토큰 패턴
SPECIAL_TOKEN_PATTERN = re.compile(
    r"<\|[a-z_]+\|>|<\|im_start\|>|<\|im_end\|>|<\|endoftext\|>"
)

# 한국어/영어/숫자/기본 문장부호가 아닌 CJK 문자 (중국어, 일본어)
# 한국어 범위: AC00-D7AF(완성형), 3131-318E(자모), 1100-11FF(자모)
# 허용: 한국어, 영어, 숫자, 공백, 일반 문장부호
NON_KOREAN_CJK_PATTERN = re.compile(
    r"[\u4e00-\u9fff"   # CJK 통합 한자 (중국어)
    r"\u3040-\u309f"    # 히라가나 (일본어)
    r"\u30a0-\u30ff"    # 가타카나 (일본어)
    r"\u31f0-\u31ff"    # 가타카나 확장
    r"\uff66-\uff9f"    # 반각 가타카나
    r"\u3000-\u303f"    # CJK 기호 및 구두점 (。、「」등)
    r"\uff01-\uff60"    # 전각 영숫자/구두점 (，．！？등)
    r"]+"
)


def clean_llm_response(text: str) -> str:
    """
    LLM 응답에서 특수 토큰, 깨진 글자, 비한국어 문자를 정리한다.

    Args:
        text: LLM 원본 응답

    Returns:
        정리된 응답 텍스트
    """
    if not text:
        return text

    original_len = len(text)
    cleaned = text

    # (1) 특수 토큰 제거
    cleaned = SPECIAL_TOKEN_PATTERN.sub("", cleaned)

    # (2) 중국어/일본어 구두점 반복 패턴 제거 (，。，。，。 등)
    cleaned = re.sub(r"[，。、；：！？]{2,}", "", cleaned)

    # (3) 중국어/일본어 문자 제거 (한국어 의료 서비스이므로)
    cleaned = NON_KOREAN_CJK_PATTERN.sub("", cleaned)

    # (4) 전각 구두점을 반각으로 변환
    cleaned = cleaned.replace("。", ".").replace("，", ",").replace("：", ":").replace("；", ";")

    # (5) CJK 제거 후 남은 고아 구두점 정리 (예: ",,.", "...")
    cleaned = re.sub(r"[.,;:]{2,}", "", cleaned)

    # (6) 연속 공백 정규화
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    # 빈 줄만 남은 라인 제거
    cleaned = re.sub(r"\n +\n", "\n\n", cleaned)

    # (7) 문장이 중간에 잘린 경우 마지막 불완전 문장 제거
    cleaned = _trim_incomplete_ending(cleaned)

    cleaned = cleaned.strip()

    if len(cleaned) != original_len:
        logger.info(
            "Response cleaned: %d → %d chars (removed %d)",
            original_len,
            len(cleaned),
            original_len - len(cleaned),
        )

    return cleaned


def _trim_incomplete_ending(text: str) -> str:
    """
    응답 끝이 불완전하게 잘린 경우 마지막 완전한 문장까지만 남긴다.
    마침표/물음표/느낌표/닫는 괄호 뒤에서 자른다.
    """
    text = text.rstrip()
    if not text:
        return text

    # 이미 완전한 문장으로 끝나면 그대로 반환
    if text[-1] in ".!?)\n다요음니":
        return text

    # 마지막 문장 종결 위치 찾기 (한국어 종결어미 포함)
    last_end = -1
    for i in range(len(text) - 1, -1, -1):
        if text[i] in ".!?)\n":
            last_end = i
            break
        # 한국어 종결어미 (다, 요, 음, 니 등) 뒤에 공백이나 줄바꿈이 오면 문장 종결
        if text[i] in "다요음니" and i + 1 < len(text) and text[i + 1] in " \n":
            last_end = i
            break

    # 종결 문자가 있고, 전체 길이의 50% 이상이면 잘라냄
    if last_end > 0 and last_end >= len(text) * 0.5:
        return text[: last_end + 1]

    # 짧은 응답이거나 종결 문자가 없으면 그대로 반환
    return text
