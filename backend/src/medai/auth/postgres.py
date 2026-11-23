"""PostgreSQL implementations of user and session storage via SQLAlchemy Core."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from medai.auth.models import (
    LoginTakenError,
    RefreshSession,
    Role,
    User,
    UserWithPassword,
)
from medai.auth.stores import SessionStore, UserStore
from medai.db.tables import refresh_sessions, users

__all__ = ["PostgresSessionStore", "PostgresUserStore"]


class PostgresUserStore(UserStore):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def get_by_email(self, email: str) -> UserWithPassword | None:
        stmt = select(users).where(func.lower(users.c.email) == email.strip().lower())
        async with self._engine.connect() as conn:
            result = await conn.execute(stmt)
            row = result.mappings().first()
            if not row:
                return None
            return UserWithPassword(
                user=User(
                    id=row["id"],
                    email=row["email"],
                    name=row["name"],
                    role=Role(row["role"]),
                    avatar_color=row["avatar_color"],
                ),
                password_hash=row["password_hash"],
            )

    async def get_by_id(self, user_id: UUID) -> User | None:
        stmt = select(users).where(users.c.id == user_id)
        async with self._engine.connect() as conn:
            result = await conn.execute(stmt)
            row = result.mappings().first()
            if not row:
                return None
            return User(
                id=row["id"],
                email=row["email"],
                name=row["name"],
                role=Role(row["role"]),
                avatar_color=row["avatar_color"],
            )

    async def create(
        self,
        id: UUID,
        email: str,
        name: str,
        password_hash: str,
        role: Role,
        avatar_color: str,
        now: datetime,
    ) -> User:
        stmt = (
            insert(users)
            .values(
                id=id,
                email=email.strip().lower(),
                name=name.strip(),
                password_hash=password_hash,
                role=role.value,
                avatar_color=avatar_color,
                created_at=now,
                updated_at=now,
            )
            .returning(users)
        )
        try:
            async with self._engine.begin() as conn:
                result = await conn.execute(stmt)
                row = result.mappings().one()
                return User(
                    id=row["id"],
                    email=row["email"],
                    name=row["name"],
                    role=Role(row["role"]),
                    avatar_color=row["avatar_color"],
                )
        except IntegrityError as err:
            raise LoginTakenError() from err

    async def update_password(
        self,
        user_id: UUID,
        password_hash: str,
        now: datetime,
    ) -> None:
        stmt = (
            update(users)
            .where(users.c.id == user_id)
            .values(password_hash=password_hash, updated_at=now)
        )
        async with self._engine.begin() as conn:
            await conn.execute(stmt)


class PostgresSessionStore(SessionStore):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def create_session(self, session: RefreshSession) -> None:
        stmt = insert(refresh_sessions).values(
            id=session.id,
            user_id=session.user_id,
            family_id=session.family_id,
            token_hash=session.token_hash,
            created_at=session.created_at,
            expires_at=session.expires_at,
            revoked_at=session.revoked_at,
            replaced_by=session.replaced_by,
        )
        async with self._engine.begin() as conn:
            await conn.execute(stmt)

    async def get_session_by_token_hash(
        self, token_hash: bytes
    ) -> RefreshSession | None:
        stmt = select(refresh_sessions).where(
            refresh_sessions.c.token_hash == token_hash
        )
        async with self._engine.connect() as conn:
            result = await conn.execute(stmt)
            row = result.mappings().first()
            if not row:
                return None
            return RefreshSession(
                id=row["id"],
                user_id=row["user_id"],
                family_id=row["family_id"],
                token_hash=row["token_hash"],
                created_at=row["created_at"],
                expires_at=row["expires_at"],
                revoked_at=row["revoked_at"],
                replaced_by=row["replaced_by"],
            )

    async def replace_session(
        self,
        old_session_id: UUID,
        new_session: RefreshSession,
        now: datetime,
    ) -> None:
        async with self._engine.begin() as conn:
            # 1. Update old session
            await conn.execute(
                update(refresh_sessions)
                .where(refresh_sessions.c.id == old_session_id)
                .values(replaced_by=new_session.id, revoked_at=now)
            )
            # 2. Insert new session
            await conn.execute(
                insert(refresh_sessions).values(
                    id=new_session.id,
                    user_id=new_session.user_id,
                    family_id=new_session.family_id,
                    token_hash=new_session.token_hash,
                    created_at=new_session.created_at,
                    expires_at=new_session.expires_at,
                    revoked_at=new_session.revoked_at,
                    replaced_by=new_session.replaced_by,
                )
            )

    async def revoke_session(self, session_id: UUID, now: datetime) -> None:
        stmt = (
            update(refresh_sessions)
            .where(refresh_sessions.c.id == session_id)
            .values(revoked_at=now)
        )
        async with self._engine.begin() as conn:
            await conn.execute(stmt)

    async def revoke_family(self, family_id: UUID, now: datetime) -> None:
        stmt = (
            update(refresh_sessions)
            .where(
                refresh_sessions.c.family_id == family_id,
                refresh_sessions.c.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        async with self._engine.begin() as conn:
            await conn.execute(stmt)

    async def revoke_all_user_sessions(self, user_id: UUID, now: datetime) -> None:
        stmt = (
            update(refresh_sessions)
            .where(
                refresh_sessions.c.user_id == user_id,
                refresh_sessions.c.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        async with self._engine.begin() as conn:
            await conn.execute(stmt)
