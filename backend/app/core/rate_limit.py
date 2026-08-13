"""In-process fixed-window rate limiter for login and generation routes (§15).

Deliberately dependency free and injectable-clock friendly so it can be unit
tested. A multi-process deployment needs a shared store (Redis); that is called
out in the README's production notes.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass

_UNITS = {
    "second": 1,
    "seconds": 1,
    "minute": 60,
    "minutes": 60,
    "hour": 3600,
    "hours": 3600,
    "day": 86400,
    "days": 86400,
}


@dataclass(frozen=True)
class RateLimitPolicy:
    limit: int
    window_seconds: int

    @classmethod
    def parse(cls, expression: str) -> RateLimitPolicy:
        """Parse expressions such as ``20/hour`` or ``10/minute``."""
        try:
            raw_limit, raw_unit = expression.split("/", 1)
            unit = raw_unit.strip().lower()
            if unit not in _UNITS:
                raise KeyError(unit)
            return cls(limit=int(raw_limit.strip()), window_seconds=_UNITS[unit])
        except (ValueError, KeyError) as exc:
            raise ValueError(f"Invalid rate limit expression: {expression!r}") from exc


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after_seconds: int


class RateLimiter:
    """Fixed-window counter keyed by ``(bucket, identity)``."""

    def __init__(self, clock=time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._hits: dict[tuple[str, str], list[float]] = defaultdict(list)

    def check(self, bucket: str, identity: str, policy: RateLimitPolicy) -> RateLimitResult:
        now = self._clock()
        window_start = now - policy.window_seconds
        key = (bucket, identity)

        with self._lock:
            hits = [hit for hit in self._hits[key] if hit > window_start]
            if len(hits) >= policy.limit:
                oldest = min(hits)
                retry_after = max(1, int(policy.window_seconds - (now - oldest)) + 1)
                self._hits[key] = hits
                return RateLimitResult(False, 0, retry_after)
            hits.append(now)
            self._hits[key] = hits
            return RateLimitResult(True, policy.limit - len(hits), 0)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


rate_limiter = RateLimiter()
