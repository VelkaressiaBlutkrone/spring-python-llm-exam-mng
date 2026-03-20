"""
인메모리 추론 메트릭(프로세스 단위).

``record_request`` 호출 시마다 ``vector_search_total`` 은 증가하고,
컨텍스트가 비어 있지 않았을 때만 ``vector_search_hits`` 가 올라간다
(의학/규칙 엔드포인트에서 ``vector_hit=`` 로 전달).
"""

import threading
import time
from dataclasses import dataclass, field


@dataclass
class InferMetrics:
    """추론 메트릭 (스레드 안전)"""
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    total_requests: int = 0
    success_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0
    vector_search_hits: int = 0
    vector_search_total: int = 0

    def record_request(self, latency_ms: float, success: bool = True, vector_hit: bool = False):
        """요청 결과를 기록한다."""
        with self._lock:
            self.total_requests += 1
            self.total_latency_ms += latency_ms
            if success:
                self.success_count += 1
            else:
                self.error_count += 1
            self.vector_search_total += 1
            if vector_hit:
                self.vector_search_hits += 1

    @property
    def avg_latency_ms(self) -> float:
        with self._lock:
            if self.total_requests == 0:
                return 0.0
            return self.total_latency_ms / self.total_requests

    @property
    def success_rate(self) -> float:
        with self._lock:
            if self.total_requests == 0:
                return 0.0
            return self.success_count / self.total_requests

    @property
    def vector_hit_rate(self) -> float:
        with self._lock:
            if self.vector_search_total == 0:
                return 0.0
            return self.vector_search_hits / self.vector_search_total

    def to_dict(self) -> dict:
        with self._lock:
            avg_lat = self.total_latency_ms / self.total_requests if self.total_requests > 0 else 0.0
            suc_rate = self.success_count / self.total_requests if self.total_requests > 0 else 0.0
            vec_rate = self.vector_search_hits / self.vector_search_total if self.vector_search_total > 0 else 0.0
            return {
                "total_requests": self.total_requests,
                "success_count": self.success_count,
                "error_count": self.error_count,
                "avg_latency_ms": round(avg_lat, 1),
                "success_rate": round(suc_rate, 4),
                "vector_hit_rate": round(vec_rate, 4),
            }

    def reset(self):
        """메트릭 초기화"""
        with self._lock:
            self.total_requests = 0
            self.success_count = 0
            self.error_count = 0
            self.total_latency_ms = 0.0
            self.vector_search_hits = 0
            self.vector_search_total = 0


# 모듈 레벨 싱글톤
metrics = InferMetrics()
