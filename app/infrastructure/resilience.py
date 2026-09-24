from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable, TypeVar


class CircuitBreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


T = TypeVar("T")


@dataclass(slots=True)
class CircuitBreaker:
    failure_threshold: int = 5
    reset_after_seconds: float = 30.0
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failures: int = 0
    opened_at: float | None = None

    async def call(self, operation: Callable[[], Awaitable[T]]) -> T:
        if self.state == CircuitBreakerState.OPEN:
            if self.opened_at and time.monotonic() - self.opened_at >= self.reset_after_seconds:
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise RuntimeError("circuit breaker is open")

        try:
            result = await operation()
        except Exception:
            self.failures += 1
            if self.failures >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                self.opened_at = time.monotonic()
            raise

        self.failures = 0
        self.state = CircuitBreakerState.CLOSED
        self.opened_at = None
        return result


async def retry_async(operation: Callable[[], Awaitable[T]], attempts: int = 3, base_delay: float = 0.25) -> T:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return await operation()
        except Exception as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
            await asyncio.sleep(base_delay * (2 ** attempt))
    raise last_error if last_error else RuntimeError("operation failed")
