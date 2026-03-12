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
        """요청 실행 가능 여부 확인"""
        current_state = self.state
        if current_state == "OPEN":
            return False
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
