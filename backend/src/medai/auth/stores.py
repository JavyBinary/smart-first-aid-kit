"""Protocols for user and session persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from medai.auth.models import RefreshSession, Role, User, UserWithPassword

__all__ = ["SessionStore", "UserStore"]


class UserStore(Protocol):
    async def get_by_email(self, email: str) -> UserWithPassword | None: ...

    async def get_by_id(self, user_id: UUID) -> User | None: ...

    async def create(
        self,
        id: UUID,
        email: str,
        name: str,
        password_hash: str,
        role: Role,
        avatar_color: str,
        now: datetime,
    ) -> User: ...

    async def update_password(
        self,
        user_id: UUID,
        password_hash: str,
        now: datetime,
    ) -> None: ...


class SessionStore(Protocol):
    async def create_session(self, session: RefreshSession) -> None: ...

    async def get_session_by_token_hash(
        self, token_hash: bytes
    ) -> RefreshSession | None: ...

    async def replace_session(
        self,
        old_session_id: UUID,
        new_session: RefreshSession,
        now: datetime,
    ) -> None: ...

    async def revoke_session(self, session_id: UUID, now: datetime) -> None: ...

    async def revoke_family(self, family_id: UUID, now: datetime) -> None: ...

    async def revoke_all_user_sessions(self, user_id: UUID, now: datetime) -> None: ...
