"""Circuit breaker utilities for external calls (Holistic AI + Valyu)."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class SimpleCircuitBreaker:
    def __init__(self, fail_max: int = 3, reset_timeout: int = 30):
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure = 0.0
        self.state = "closed"

    def call(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        if self.state == "open" and not self._can_reset():
            raise RuntimeError("Circuit breaker open")

        try:
            result = func(*args, **kwargs)
        except Exception:
            self._record_failure()
            raise
        else:
            self._reset()
            return result

    def _record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure = time.time()
        if self.failure_count >= self.fail_max:
            self.state = "open"
            logger.warning("Circuit breaker tripped (failures=%s)", self.failure_count)

    def _reset(self) -> None:
        self.failure_count = 0
        self.state = "closed"

    def _can_reset(self) -> bool:
        if time.time() - self.last_failure >= self.reset_timeout:
            self.state = "half-open"
            self.failure_count = 0
            return True
        return False


holistic_ai_breaker = SimpleCircuitBreaker()
valyu_breaker = SimpleCircuitBreaker()
fetcher_breaker = SimpleCircuitBreaker()


def wrap_with_breaker(breaker: SimpleCircuitBreaker, func: Callable[..., Any], *args, **kwargs) -> Any:
    return breaker.call(func, *args, **kwargs)
