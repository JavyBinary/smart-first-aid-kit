"""High-level authentication and session service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from medai.auth.models import (
    AccessClaims,
    AuthResult,
    InvalidCredentialsError,
    IssuedTokens,
    RefreshSession,
    Role,
    UnauthorizedError,
    User,
)
from medai.auth.passwords import Argon2PasswordHasher
from medai.auth.rate_limiter import RateLimiter
from medai.auth.stores import SessionStore, UserStore
from medai.auth.tokens import TokenCodec, hash_refresh_token, new_refresh_token
from medai.cache.blacklist import InMemoryTokenBlacklist, TokenBlacklist
from medai.config import AuthConfig

__all__ = ["AuthService"]


class AuthService:
    def __init__(
        self,
        *,
        config: AuthConfig,
        users: UserStore,
        sessions: SessionStore,
        hasher: Argon2PasswordHasher,
        tokens: TokenCodec,
        limiter: RateLimiter,
        blacklist: TokenBlacklist | None = None,
    ) -> None:
        self._config = config
        self._users = users
        self._sessions = sessions
        self._hasher = hasher
        self._tokens = tokens
        self._limiter = limiter
        self._blacklist: TokenBlacklist = blacklist or InMemoryTokenBlacklist()
        self._refresh_ttl = timedelta(seconds=config.refresh_ttl_seconds)

    async def register(
        self,
        *,
        email: str,
        password: str,
        name: str,
        ip: str,
        role: Role = Role.USER,
        avatar_color: str = "#2563EB",
        now: datetime | None = None,
    ) -> AuthResult:
        current_time = datetime.now(UTC) if now is None else now
        await self._limiter.check_register_ip(ip)

        password_hash = await self._hasher.hash(password)
        user_id = uuid4()
        user = await self._users.create(
            id=user_id,
            email=email,
            name=name,
            password_hash=password_hash,
            role=role,
            avatar_color=avatar_color,
            now=current_time,
        )

        tokens = await self._issue_session(user=user, now=current_time)
        return AuthResult(user=user, tokens=tokens)

    async def login(
        self,
        *,
        email: str,
        password: str,
        ip: str,
        now: datetime | None = None,
    ) -> AuthResult:
        current_time = datetime.now(UTC) if now is None else now
        await self._limiter.check_login_ip(ip)
        await self._limiter.check_login_failures(email)

        user_with_pw = await self._users.get_by_email(email)
        if user_with_pw is None:
            # Timing attack mitigation: verify against precomputed dummy hash
            await self._hasher.verify(self._hasher.dummy_hash, password)
            await self._limiter.record_login_failure(email)
            raise InvalidCredentialsError()

        valid = await self._hasher.verify(user_with_pw.password_hash, password)
        if not valid:
            await self._limiter.record_login_failure(email)
            raise InvalidCredentialsError()

        await self._limiter.reset_login_failures(email)
        tokens = await self._issue_session(user=user_with_pw.user, now=current_time)
        return AuthResult(user=user_with_pw.user, tokens=tokens)

    async def refresh(
        self,
        *,
        refresh_token: str,
        now: datetime | None = None,
    ) -> AuthResult:
        current_time = datetime.now(UTC) if now is None else now
        token_hash = hash_refresh_token(refresh_token)
        session = await self._sessions.get_session_by_token_hash(token_hash)

        if session is None or session.expires_at <= current_time:
            raise UnauthorizedError()

        # If already replaced or revoked, token was compromised! Revoke entire family.
        if session.revoked_at is not None or session.replaced_by is not None:
            await self._sessions.revoke_family(session.family_id, current_time)
            raise UnauthorizedError()

        user = await self._users.get_by_id(session.user_id)
        if user is None:
            raise UnauthorizedError()

        # Rotate session
        new_session_id = uuid4()
        new_raw_refresh = new_refresh_token()
        new_refresh_hash = hash_refresh_token(new_raw_refresh)
        new_refresh_expires = current_time + self._refresh_ttl

        new_session = RefreshSession(
            id=new_session_id,
            user_id=user.id,
            family_id=session.family_id,
            token_hash=new_refresh_hash,
            created_at=current_time,
            expires_at=new_refresh_expires,
        )

        await self._sessions.replace_session(session.id, new_session, current_time)
        access_token, access_claims = self._tokens.encode_access(
            user.id, user.role, new_session_id, session.family_id, current_time
        )

        return AuthResult(
            user=user,
            tokens=IssuedTokens(
                access_token=access_token,
                access_expires_at=access_claims.expires_at,
                refresh_token=new_raw_refresh,
                refresh_expires_at=new_refresh_expires,
            ),
        )

    async def logout(
        self,
        *,
        refresh_token: str | None,
        access_token: str | None = None,
        now: datetime | None = None,
    ) -> None:
        current_time = datetime.now(UTC) if now is None else now
        if access_token:
            try:
                claims = self._tokens.decode_access(access_token, current_time)
                ttl = int((claims.expires_at - current_time).total_seconds())
                if ttl > 0:
                    await self._blacklist.revoke(claims.jti, ttl)
            except UnauthorizedError:
                pass
        if not refresh_token:
            return
        token_hash = hash_refresh_token(refresh_token)
        session = await self._sessions.get_session_by_token_hash(token_hash)
        if session and session.revoked_at is None:
            await self._sessions.revoke_session(session.id, current_time)

    async def authenticate(
        self,
        access_token: str,
        now: datetime | None = None,
    ) -> tuple[User, AccessClaims]:
        current_time = datetime.now(UTC) if now is None else now
        claims = self._tokens.decode_access(access_token, current_time)
        if await self._blacklist.is_revoked(claims.jti):
            raise UnauthorizedError("Token has been revoked.")
        user = await self._users.get_by_id(claims.user_id)
        if user is None:
            raise UnauthorizedError()
        return user, claims

    async def change_password(
        self,
        *,
        user_id: UUID,
        old_password: str,
        new_password: str,
        access_jti: str | None = None,
        access_ttl_seconds: int = 900,
        now: datetime | None = None,
    ) -> None:
        current_time = datetime.now(UTC) if now is None else now
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError()
        user_with_pw = await self._users.get_by_email(user.email)
        if user_with_pw is None:
            raise UnauthorizedError()
        valid = await self._hasher.verify(user_with_pw.password_hash, old_password)
        if not valid:
            raise InvalidCredentialsError()
        new_hash = await self._hasher.hash(new_password)
        await self._users.update_password(user.id, new_hash, current_time)
        await self._sessions.revoke_all_user_sessions(user.id, current_time)
        if access_jti:
            await self._blacklist.revoke(access_jti, access_ttl_seconds)

    async def update_user_role(
        self,
        *,
        target_user_id: UUID,
        new_role: Role,
        now: datetime | None = None,
    ) -> User | None:
        if hasattr(self._users, "update_role"):
            current_time = datetime.now(UTC) if now is None else now
            return await self._users.update_role(target_user_id, new_role, current_time)
        return None

    async def list_users(self) -> list[User]:
        if hasattr(self._users, "list_all"):
            return await self._users.list_all()
        return []

    async def _issue_session(self, *, user: User, now: datetime) -> IssuedTokens:
        session_id = uuid4()
        family_id = uuid4()
        raw_refresh = new_refresh_token()
        refresh_hash = hash_refresh_token(raw_refresh)
        refresh_expires = now + self._refresh_ttl

        session = RefreshSession(
            id=session_id,
            user_id=user.id,
            family_id=family_id,
            token_hash=refresh_hash,
            created_at=now,
            expires_at=refresh_expires,
        )
        await self._sessions.create_session(session)

        access_token, access_claims = self._tokens.encode_access(
            user.id, user.role, session_id, family_id, now
        )

        return IssuedTokens(
            access_token=access_token,
            access_expires_at=access_claims.expires_at,
            refresh_token=raw_refresh,
            refresh_expires_at=refresh_expires,
        )
