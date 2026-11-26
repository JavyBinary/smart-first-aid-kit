"""Redis-backed auth rate limiter with graceful in-memory interface compatibility."""

from __future__ import annotations

from redis.asyncio import Redis
from redis.exceptions import RedisError

from medai.auth.models import TooManyAttemptsError
from medai.auth.rate_limiter import InMemoryRateLimiter, RateLimiter
from medai.config import AuthRateLimitConfig

__all__ = ["RedisRateLimiter"]

KEY_PREFIX = "auth:ratelimit:"


class RedisRateLimiter(RateLimiter):
    """Fixed-window Redis counters matching InMemoryRateLimiter semantics."""

    def __init__(self, redis: Redis, config: AuthRateLimitConfig) -> None:
        self._redis = redis
        self._config = config
        self._fallback = InMemoryRateLimiter(config)

    async def _increment(self, key: str, window_seconds: int) -> int:
        full_key = KEY_PREFIX + key
        try:
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.incr(full_key)
                pipe.expire(full_key, window_seconds, nx=True)
                count, _ = await pipe.execute()
            return int(count)
        except (RedisError, OSError, TimeoutError):
            return -1

    async def _get_count(self, key: str) -> int:
        try:
            val = await self._redis.get(KEY_PREFIX + key)
            return int(val) if val is not None else 0
        except (RedisError, OSError, TimeoutError):
            return -1

    async def check_login_ip(self, ip: str) -> None:
        count = await self._increment(
            f"login_ip:{ip}", self._config.login_per_ip_window_seconds
        )
        if count == -1:
            await self._fallback.check_login_ip(ip)
            return
        if count > self._config.login_per_ip:
            raise TooManyAttemptsError(
                "login_per_ip", self._config.login_per_ip_window_seconds
            )

    async def check_login_failures(self, email: str) -> None:
        count = await self._get_count(f"fail:{email.lower()}")
        if count == -1:
            await self._fallback.check_login_failures(email)
            return
        if count >= self._config.login_failures:
            raise TooManyAttemptsError(
                "login_failures", self._config.login_failure_window_seconds
            )

    async def record_login_failure(self, email: str) -> None:
        count = await self._increment(
            f"fail:{email.lower()}", self._config.login_failure_window_seconds
        )
        if count == -1:
            await self._fallback.record_login_failure(email)

    async def reset_login_failures(self, email: str) -> None:
        try:
            await self._redis.delete(KEY_PREFIX + f"fail:{email.lower()}")
        except (RedisError, OSError, TimeoutError):
            await self._fallback.reset_login_failures(email)

    async def check_register_ip(self, ip: str) -> None:
        count = await self._increment(
            f"reg_ip:{ip}", self._config.register_per_ip_window_seconds
        )
        if count == -1:
            await self._fallback.check_register_ip(ip)
            return
        if count > self._config.register_per_ip:
            raise TooManyAttemptsError(
                "register_per_ip", self._config.register_per_ip_window_seconds
            )
