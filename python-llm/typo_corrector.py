"""
의료 용어 오타 교정 모듈
- DB에서 오타 사전 로드 (DB 사용 불가 시 내장 사전 폴백)
- 주기적 리로드 지원
"""

import logging
import re
import time

logger = logging.getLogger(__name__)

# 내장 폴백 사전 (DB 불가 시 사용)
_BUILTIN_TYPO_MAP: dict[str, str] = {
    # ㅂ/ㅍ 혼동, 받침 탈락
    "무릅": "무릎",
    "무릊": "무릎",
    "무르": "무릎",
    "무릅이": "무릎이",
    "무르이": "무릎이",
    # ㄹ/ㄴ 혼동
    "의뇨": "의료",
    # 겹받침 탈락
    "앉목": "안목",
    "삶키다": "삼키다",
    # 사이시옷/된소리 오류
    "잇목": "잇몸",
    "이몸": "잇몸",
    "있몸": "잇몸",
    # 흔한 의료 용어 오타
    "어게": "어깨",
    "골졀": "골절",
    "골저": "골절",
    "관졀": "관절",
    "관저": "관절",
    "괸절": "관절",
    "두퉁": "두통",
    "복퉁": "복통",
    "요퉁": "요통",
    "소화불냥": "소화불량",
    "편두퉁": "편두통",
    "당뇨벙": "당뇨병",
    "고혈앞": "고혈압",
    "고헐압": "고혈압",
    "저헐압": "저혈압",
    "듸스크": "디스크",
    "허리듸스크": "허리디스크",
    "인데": "인대",
    # 검사 약어
    "엠알아이": "MRI",
    "시티": "CT",
    "씨티": "CT",
    "엑스레이": "X-ray",
    "엑스래이": "X-ray",
    # 질병명 오타
    "앨러지": "알레르기",
    "알러지": "알레르기",
    "아퇴피": "아토피",
    "류머티즘": "류마티즘",
    "류마티스": "류마티즘",
    "페렴": "폐렴",
    "뇌졸증": "뇌졸중",
    "심금경색": "심근경색",
    "협심즘": "협심증",
    "위궤얌": "위궤양",
    "축능증": "축농증",
    "비렴": "비염",
    "결막렴": "결막염",
    "방광렴": "방광염",
    "요로감렴": "요로감염",
    # 신체 부위 오타
    "발몪": "발목",
    "손몪": "손목",
    "가스미": "가슴이",
    "목뻐": "목뼈",
    "갈비뻐": "갈비뼈",
    "발바닦": "발바닥",
    # 진료과 오타
    "정형외괴": "정형외과",
    "신경외괴": "신경외과",
    "이비인후괴": "이비인후과",
    "피부괴": "피부과",
    "안괴": "안과",
    "내괴": "내과",
    "외괴": "외과",
    "비뇨기괴": "비뇨기과",
    "산부인괴": "산부인과",
    "소아괴": "소아과",
    "치괴": "치과",
    # 병원 규칙 관련 오타
    "위행": "위생",
    "위셍": "위생",
    "위쌩": "위생",
    "당즉": "당직",
    "당짂": "당직",
    "물푸": "물품",
    "물픔": "물품",
    "비품": "비품",
    "비푼": "비품",
    "감렴": "감염",
    "감연": "감염",
    "격리해제": "격리 해제",
    "응급처치": "응급 처치",
    "소독규칙": "소독 규칙",
}

# 방어적 필터: key == value인 항목 제거
_BUILTIN_TYPO_MAP = {k: v for k, v in _BUILTIN_TYPO_MAP.items() if k != v}

# 활성 사전 (DB 로드 성공 시 DB 데이터, 실패 시 내장 사전)
_active_map: dict[str, str] = dict(_BUILTIN_TYPO_MAP)
_last_reload: float = 0.0
_RELOAD_INTERVAL: float = 600.0  # 10분


async def load_typo_dict_from_db() -> dict[str, str]:
    """DB에서 오타 사전을 로드한다."""
    try:
        from medical_context_service import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT typo, correct_term FROM typo_dictionary")
                rows = await cur.fetchall()
                result = {row[0]: row[1] for row in rows if row[0] != row[1]}
                logger.info("Loaded %d typo entries from DB", len(result))
                return result
    except Exception as exc:
        logger.warning("Failed to load typo dict from DB, using builtin: %s", exc)
        return {}


async def reload_typo_dict():
    """DB에서 사전을 리로드한다."""
    global _active_map, _last_reload
    db_map = await load_typo_dict_from_db()
    if db_map:
        _active_map = db_map
    else:
        _active_map = dict(_BUILTIN_TYPO_MAP)
    _last_reload = time.monotonic()
    logger.info("Typo dictionary reloaded: %d entries", len(_active_map))


async def _maybe_reload():
    """리로드 간격이 지났으면 백그라운드에서 리로드"""
    global _last_reload
    if time.monotonic() - _last_reload > _RELOAD_INTERVAL:
        await reload_typo_dict()



def correct_typos(text: str) -> str:
    """
    의료 용어 오타를 사전 기반으로 교정한다.
    긴 키워드부터 먼저 매칭하여 부분 치환 충돌을 방지한다.
    """
    if not text:
        return text

    corrected = text
    corrections = []

    sorted_typos = sorted(_active_map.keys(), key=len, reverse=True)

    for typo in sorted_typos:
        if typo in corrected:
            correct = _active_map[typo]
            corrected = corrected.replace(typo, correct)
            corrections.append(f"'{typo}'→'{correct}'")

    if corrections:
        logger.info("Typo corrected: %s", ", ".join(corrections))

    return corrected
