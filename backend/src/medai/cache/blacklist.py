"""Access-token JTI blacklist (Redis and in-memory implementations)."""

from __future__ import annotations

import time
from typing import Protocol

from redis.asyncio import Redis
from redis.exceptions import RedisError

__all__ = ["InMemoryTokenBlacklist", "RedisTokenBlacklist", "TokenBlacklist"]

BLACKLIST_PREFIX = "auth:blacklist:"


class TokenBlacklist(Protocol):
    async def revoke(self, jti: str, ttl_seconds: int) -> None: ...

    async def is_revoked(self, jti: str) -> bool: ...


class InMemoryTokenBlacklist:
    """In-memory JTI blacklist for unit tests and dev without Redis."""

    def __init__(self) -> None:
        self._revoked: dict[str, float] = {}

    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        if ttl_seconds > 0:
            self._revoked[jti] = time.monotonic() + ttl_seconds

    async def is_revoked(self, jti: str) -> bool:
        exp = self._revoked.get(jti)
        if exp is None:
            return False
        if time.monotonic() >= exp:
            self._revoked.pop(jti, None)
            return False
        return True


class RedisTokenBlacklist:
    """Redis-backed JTI blacklist with TTL expiration."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        try:
            await self._redis.set(BLACKLIST_PREFIX + jti, "1", ex=ttl_seconds)
        except (RedisError, OSError, TimeoutError):
            pass

    async def is_revoked(self, jti: str) -> bool:
        try:
            res = await self._redis.exists(BLACKLIST_PREFIX + jti)
            return bool(res)
        except (RedisError, OSError, TimeoutError):
            return False
