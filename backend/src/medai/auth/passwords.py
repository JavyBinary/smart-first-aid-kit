"""Argon2id password hashing with timing-attack defense and threadpool bounding."""

from __future__ import annotations

import asyncio

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

__all__ = ["Argon2PasswordHasher"]


class Argon2PasswordHasher:
    """Argon2id hashing executed outside the event loop thread."""

    def __init__(
        self,
        *,
        time_cost: int = 3,
        memory_cost: int = 64 * 1024,
        parallelism: int = 4,
        max_concurrency: int = 4,
    ) -> None:
        self._hasher = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
        )
        self._semaphore = asyncio.Semaphore(max_concurrency)
        # Precomputed hash verified for non-existent users to equalize timing
        self.dummy_hash = self._hasher.hash("medai-dummy-password-for-timing")

    async def hash(self, password: str) -> str:
        async with self._semaphore:
            return await asyncio.to_thread(self._hasher.hash, password)

    async def verify(self, password_hash: str, password: str) -> bool:
        def _verify() -> bool:
            try:
                return self._hasher.verify(password_hash, password)
            except (VerificationError, InvalidHashError):
                return False

        async with self._semaphore:
            return await asyncio.to_thread(_verify)
