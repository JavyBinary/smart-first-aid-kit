"""Rate limiting implementation for authentication endpoints."""

from __future__ import annotations

import time
from typing import Protocol

from medai.auth.models import TooManyAttemptsError
from medai.config import AuthRateLimitConfig

__all__ = ["InMemoryRateLimiter", "RateLimiter"]


class RateLimiter(Protocol):
    async def check_login_ip(self, ip: str) -> None: ...
    async def check_login_failures(self, email: str) -> None: ...
    async def record_login_failure(self, email: str) -> None: ...
    async def reset_login_failures(self, email: str) -> None: ...
    async def check_register_ip(self, ip: str) -> None: ...


class InMemoryRateLimiter(RateLimiter):
    """In-memory rate limiter suitable for unit tests and single-worker dev."""

    def __init__(self, config: AuthRateLimitConfig) -> None:
        self._config = config
        self._attempts: dict[str, list[float]] = {}

    def _cleanup_and_count(self, key: str, window_seconds: int) -> int:
        now = time.monotonic()
        cutoff = now - window_seconds
        current = [t for t in self._attempts.get(key, []) if t > cutoff]
        self._attempts[key] = current
        return len(current)

    def _record(self, key: str) -> None:
        self._attempts.setdefault(key, []).append(time.monotonic())

    async def check_login_ip(self, ip: str) -> None:
        count = self._cleanup_and_count(
            f"login_ip:{ip}", self._config.login_per_ip_window_seconds
        )
        if count >= self._config.login_per_ip:
            raise TooManyAttemptsError(
                "login_per_ip", self._config.login_per_ip_window_seconds
            )
        self._record(f"login_ip:{ip}")

    async def check_login_failures(self, email: str) -> None:
        count = self._cleanup_and_count(
            f"fail:{email.lower()}", self._config.login_failure_window_seconds
        )
        if count >= self._config.login_failures:
            raise TooManyAttemptsError(
                "login_failures", self._config.login_failure_window_seconds
            )

    async def record_login_failure(self, email: str) -> None:
        self._record(f"fail:{email.lower()}")

    async def reset_login_failures(self, email: str) -> None:
        self._attempts.pop(f"fail:{email.lower()}", None)

    async def check_register_ip(self, ip: str) -> None:
        count = self._cleanup_and_count(
            f"reg_ip:{ip}", self._config.register_per_ip_window_seconds
        )
        if count >= self._config.register_per_ip:
            raise TooManyAttemptsError(
                "register_per_ip", self._config.register_per_ip_window_seconds
            )
        self._record(f"reg_ip:{ip}")
