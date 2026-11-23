"""Unit and integration tests for MedAI authentication, sessions, and rate limiting."""

import io
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
import pytest

from medai.auth.models import (
    InvalidCredentialsError,
    LoginTakenError,
    RefreshSession,
    Role,
    TooManyAttemptsError,
    UnauthorizedError,
    User,
    UserWithPassword,
)
from medai.auth.passwords import Argon2PasswordHasher
from medai.auth.rate_limiter import InMemoryRateLimiter
from medai.auth.service import AuthService
from medai.auth.stores import SessionStore, UserStore
from medai.auth.tokens import TokenCodec
from medai.config import AuthConfig, AuthRateLimitConfig
from medai.create_admin import run as run_create_admin
from medai.main import create_app


class InMemoryUserStore(UserStore):
    def __init__(self) -> None:
        self.users_by_email: dict[str, UserWithPassword] = {}
        self.users_by_id: dict[UUID, User] = {}

    async def get_by_email(self, email: str) -> UserWithPassword | None:
        return self.users_by_email.get(email.strip().lower())

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self.users_by_id.get(user_id)

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
        key = email.strip().lower()
        if key in self.users_by_email:
            raise LoginTakenError()
        user = User(id=id, email=key, name=name, role=role, avatar_color=avatar_color)
        self.users_by_email[key] = UserWithPassword(
            user=user, password_hash=password_hash
        )
        self.users_by_id[id] = user
        return user

    async def update_password(
        self, user_id: UUID, password_hash: str, now: datetime
    ) -> None:
        user = self.users_by_id.get(user_id)
        if user:
            self.users_by_email[user.email] = UserWithPassword(
                user=user, password_hash=password_hash
            )


class InMemorySessionStore(SessionStore):
    def __init__(self) -> None:
        self.sessions_by_hash: dict[bytes, RefreshSession] = {}
        self.sessions_by_id: dict[UUID, RefreshSession] = {}

    async def create_session(self, session: RefreshSession) -> None:
        self.sessions_by_hash[session.token_hash] = session
        self.sessions_by_id[session.id] = session

    async def get_session_by_token_hash(
        self, token_hash: bytes
    ) -> RefreshSession | None:
        return self.sessions_by_hash.get(token_hash)

    async def replace_session(
        self, old_session_id: UUID, new_session: RefreshSession, now: datetime
    ) -> None:
        old = self.sessions_by_id.get(old_session_id)
        if old:
            updated_old = RefreshSession(
                id=old.id,
                user_id=old.user_id,
                family_id=old.family_id,
                token_hash=old.token_hash,
                created_at=old.created_at,
                expires_at=old.expires_at,
                revoked_at=now,
                replaced_by=new_session.id,
            )
            self.sessions_by_id[old.id] = updated_old
            self.sessions_by_hash[old.token_hash] = updated_old

        self.sessions_by_id[new_session.id] = new_session
        self.sessions_by_hash[new_session.token_hash] = new_session

    async def revoke_session(self, session_id: UUID, now: datetime) -> None:
        s = self.sessions_by_id.get(session_id)
        if s:
            revoked = RefreshSession(
                id=s.id,
                user_id=s.user_id,
                family_id=s.family_id,
                token_hash=s.token_hash,
                created_at=s.created_at,
                expires_at=s.expires_at,
                revoked_at=now,
                replaced_by=s.replaced_by,
            )
            self.sessions_by_id[s.id] = revoked
            self.sessions_by_hash[s.token_hash] = revoked

    async def revoke_family(self, family_id: UUID, now: datetime) -> None:
        for s in list(self.sessions_by_id.values()):
            if s.family_id == family_id and s.revoked_at is None:
                await self.revoke_session(s.id, now)

    async def revoke_all_user_sessions(self, user_id: UUID, now: datetime) -> None:
        for s in list(self.sessions_by_id.values()):
            if s.user_id == user_id and s.revoked_at is None:
                await self.revoke_session(s.id, now)


@pytest.mark.asyncio
async def test_argon2_password_hasher() -> None:
    hasher = Argon2PasswordHasher()
    hashed = await hasher.hash("secure_password_123")
    assert hashed.startswith("$argon2id$")
    assert await hasher.verify(hashed, "secure_password_123") is True
    assert await hasher.verify(hashed, "wrong_password") is False
    assert await hasher.verify(hasher.dummy_hash, "any_password") is False


def test_token_codec_lifecycle() -> None:
    config = AuthConfig(
        jwt_secret="test_secret_key_at_least_32_characters_long",
        access_ttl_seconds=300,
    )
    codec = TokenCodec(config)
    now = datetime.now(UTC)
    user_id = uuid4()
    session_id = uuid4()
    family_id = uuid4()

    token, claims = codec.encode_access(user_id, Role.ADMIN, session_id, family_id, now)
    assert isinstance(token, str)

    decoded = codec.decode_access(token, now)
    assert decoded.user_id == user_id
    assert decoded.role == Role.ADMIN
    assert decoded.session_id == session_id
    assert decoded.family_id == family_id

    # Expired token raises UnauthorizedError
    future = now + timedelta(seconds=301)
    with pytest.raises(UnauthorizedError):
        codec.decode_access(token, future, verify_expiry=True)


@pytest.mark.asyncio
async def test_rate_limiter() -> None:
    config = AuthRateLimitConfig(
        login_failures=2,
        login_failure_window_seconds=60,
        login_per_ip=3,
        login_per_ip_window_seconds=60,
        register_per_ip=2,
        register_per_ip_window_seconds=60,
    )
    limiter = InMemoryRateLimiter(config)

    # IP limit
    await limiter.check_login_ip("192.168.1.1")
    await limiter.check_login_ip("192.168.1.1")
    await limiter.check_login_ip("192.168.1.1")
    with pytest.raises(TooManyAttemptsError):
        await limiter.check_login_ip("192.168.1.1")

    # Failure limit
    await limiter.check_login_failures("user@test.ru")
    await limiter.record_login_failure("user@test.ru")
    await limiter.record_login_failure("user@test.ru")
    with pytest.raises(TooManyAttemptsError):
        await limiter.check_login_failures("user@test.ru")
    await limiter.reset_login_failures("user@test.ru")
    await limiter.check_login_failures("user@test.ru")


@pytest.mark.asyncio
async def test_auth_service_full_flow() -> None:
    config = AuthConfig(
        jwt_secret="test_secret_key_at_least_32_characters_long",
        access_ttl_seconds=300,
        refresh_ttl_seconds=3600,
    )
    users = InMemoryUserStore()
    sessions = InMemorySessionStore()
    hasher = Argon2PasswordHasher()
    tokens = TokenCodec(config)
    limiter = InMemoryRateLimiter(config.rate_limit)

    service = AuthService(
        config=config,
        users=users,
        sessions=sessions,
        hasher=hasher,
        tokens=tokens,
        limiter=limiter,
    )

    # 1. Register
    reg_res = await service.register(
        email="luka@medai.ru",
        password="password123",
        name="Лука",
        ip="127.0.0.1",
    )
    assert reg_res.user.email == "luka@medai.ru"
    assert reg_res.user.role == Role.USER

    # 2. Duplicate registration fails
    with pytest.raises(LoginTakenError):
        await service.register(
            email="luka@medai.ru",
            password="password456",
            name="Лука 2",
            ip="127.0.0.1",
        )

    # 3. Login with wrong password
    with pytest.raises(InvalidCredentialsError):
        await service.login(
            email="luka@medai.ru",
            password="wrong_password",
            ip="127.0.0.1",
        )

    # 4. Successful Login
    login_res = await service.login(
        email="luka@medai.ru",
        password="password123",
        ip="127.0.0.1",
    )
    assert login_res.user.id == reg_res.user.id

    # 5. Authenticate via access token
    auth_user, _ = await service.authenticate(login_res.tokens.access_token)
    assert auth_user.id == reg_res.user.id

    # 6. Refresh token rotation
    ref_res = await service.refresh(refresh_token=login_res.tokens.refresh_token)
    assert ref_res.user.id == reg_res.user.id
    assert ref_res.tokens.refresh_token != login_res.tokens.refresh_token

    # 7. Reuse of old refresh token triggers theft detection (revokes entire family)
    with pytest.raises(UnauthorizedError):
        await service.refresh(refresh_token=login_res.tokens.refresh_token)

    # Now the rotated new token is also revoked because the whole family was revoked
    with pytest.raises(UnauthorizedError):
        await service.refresh(refresh_token=ref_res.tokens.refresh_token)


@pytest.mark.asyncio
async def test_auth_api_endpoints() -> None:
    config = AuthConfig(
        jwt_secret="test_secret_key_at_least_32_characters_long",
        access_ttl_seconds=300,
        refresh_ttl_seconds=3600,
    )
    users = InMemoryUserStore()
    sessions = InMemorySessionStore()
    hasher = Argon2PasswordHasher()
    tokens = TokenCodec(config)
    limiter = InMemoryRateLimiter(config.rate_limit)

    service = AuthService(
        config=config,
        users=users,
        sessions=sessions,
        hasher=hasher,
        tokens=tokens,
        limiter=limiter,
    )

    app = create_app(auth_service=service)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Register
        reg_resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "doctor@medai.ru",
                "password": "doctor_pass_123",
                "name": "Доктор",
            },
        )
        assert reg_resp.status_code == 200
        assert "access_token" in reg_resp.cookies
        assert "refresh_token" in reg_resp.cookies
        assert reg_resp.json()["email"] == "doctor@medai.ru"

        # 2. Get Current User /me
        me_resp = await client.get("/api/v1/auth/me")
        assert me_resp.status_code == 200
        assert me_resp.json()["name"] == "Доктор"

        # 3. Refresh session
        ref_resp = await client.post("/api/v1/auth/refresh")
        assert ref_resp.status_code == 200
        assert "access_token" in ref_resp.cookies

        # 4. Logout
        logout_resp = await client.post("/api/v1/auth/logout")
        assert logout_resp.status_code == 200

        # After logout, /me fails without cookies
        client.cookies.clear()
        me_fail = await client.get("/api/v1/auth/me")
        assert me_fail.status_code == 401


@pytest.mark.asyncio
async def test_create_admin_cli() -> None:
    users = InMemoryUserStore()
    hasher = Argon2PasswordHasher()
    out = io.StringIO()

    # Passwords mismatch
    res = await run_create_admin(
        ["--email", "admin@medai.ru"],
        users=users,
        hasher=hasher,
        read_password=lambda prompt: "pass1" if "Введите" in prompt else "pass2",
        output=out,
    )
    assert res == 1
    assert "не совпадают" in out.getvalue()

    # Successful creation
    out = io.StringIO()
    res = await run_create_admin(
        ["--email", "admin@medai.ru", "--role", "superadmin", "--name", "СуперАдмин"],
        users=users,
        hasher=hasher,
        read_password=lambda prompt: "admin_secret_123",
        output=out,
    )
    assert res == 0
    assert "успешно создан" in out.getvalue()

    created = await users.get_by_email("admin@medai.ru")
    assert created is not None
    assert created.user.role == Role.SUPERADMIN
    assert created.user.name == "СуперАдмин"
