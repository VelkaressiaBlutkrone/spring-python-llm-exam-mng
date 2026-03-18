"""
Circuit Breaker 패턴 구현
Ollama 서버 장애 시 빠른 실패를 통해 사용자 대기 시간을 줄인다.

상태: CLOSED(정상) → OPEN(차단) → HALF_OPEN(시험)
"""

import logging
import threading
import time

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """스레드 안전 Circuit Breaker"""

    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._failures = 0
        self._last_failure_time = 0.0
        self._state = "CLOSED"
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == "OPEN":
                if time.time() - self._last_failure_time > self.reset_timeout:
                    self._state = "HALF_OPEN"
            return self._state

    def can_execute(self) -> bool:
        """요청 실행 가능 여부 확인
        HALF_OPEN 진입 시 단일 프로브만 허용:
        - timeout 경과한 OPEN → OPEN 유지(추가 차단) + True 반환(프로브 1개)
        - 이미 HALF_OPEN → OPEN으로 전환(추가 차단) + True 반환
        - CLOSED → True
        프로브 성공 시 record_success()가 CLOSED로 복귀시킨다.
        """
        with self._lock:
            if self._state == "OPEN":
                if time.time() - self._last_failure_time > self.reset_timeout:
                    # 프로브 1개 통과, 상태는 OPEN 유지하여 동시 추가 요청 차단
                    # (record_success 호출 시 CLOSED로 복귀)
                    return True
                return False
            if self._state == "HALF_OPEN":
                # 동시 요청이 HALF_OPEN을 보고 들어오는 경우 차단
                self._state = "OPEN"
                return True
            return True

    def record_success(self):
        """성공 기록 — CLOSED로 복귀"""
        with self._lock:
            self._failures = 0
            self._state = "CLOSED"

    def record_failure(self):
        """실패 기록 — threshold 초과 시 OPEN으로 전환"""
        with self._lock:
            self._failures += 1
            self._last_failure_time = time.time()
            if self._failures >= self.failure_threshold:
                self._state = "OPEN"
                logger.warning(
                    "Circuit breaker OPEN: %d consecutive failures (threshold: %d)",
                    self._failures, self.failure_threshold,
                )

    def reset(self):
        """수동 리셋"""
        with self._lock:
            self._failures = 0
            self._state = "CLOSED"
            logger.info("Circuit breaker manually reset to CLOSED")


class ServiceUnavailableError(Exception):
    """Circuit Breaker가 OPEN 상태일 때 발생"""
    pass
