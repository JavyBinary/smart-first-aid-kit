"""Tests for cache blacklist, CSRF middleware, password change, feedback, reports, admin, and speech."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from medai.admin import (
    ActivityPoint,
    AdminStore,
    AdminUserSummary,
    FeedbackSummary,
    MessageReportItem,
    ReportStatus,
    StatsPeriod,
    UserStats,
)
from medai.auth import (
    Argon2PasswordHasher,
    AuthService,
    InMemoryRateLimiter,
    TokenCodec,
)
from medai.auth.models import RefreshSession, Role, User, UserWithPassword
from medai.auth.router import get_current_user
from medai.cache import InMemoryTokenBlacklist
from medai.config import AuthConfig, AuthRateLimitConfig
from medai.dialogs import DialogService, InMemoryDialogEventBroker, InMemoryHistoryStore
from medai.main import create_app
from medai.rag.analyzer import MorphAnalyzer
from medai.rag.index import load_package_from_yaml


class _MemUserStore:
    def __init__(self) -> None:
        self.by_id: dict[UUID, UserWithPassword] = {}
        self.by_email: dict[str, UserWithPassword] = {}

    async def get_by_email(self, email: str) -> UserWithPassword | None:
        return self.by_email.get(email.strip().lower())

    async def get_by_id(self, user_id: UUID) -> User | None:
        entry = self.by_id.get(user_id)
        return entry.user if entry else None

    async def list_all(self) -> list[User]:
        return [e.user for e in self.by_id.values()]

    async def create(
        self, id: UUID, email: str, name: str, password_hash: str, role: Role, avatar_color: str, now: datetime
    ) -> User:
        u = User(id=id, email=email.lower(), name=name, role=role, avatar_color=avatar_color)
        entry = UserWithPassword(user=u, password_hash=password_hash)
        self.by_id[id] = entry
        self.by_email[u.email] = entry
        return u

    async def update_password(self, user_id: UUID, password_hash: str, now: datetime) -> None:
        entry = self.by_id[user_id]
        updated = UserWithPassword(user=entry.user, password_hash=password_hash)
        self.by_id[user_id] = updated
        self.by_email[entry.user.email] = updated

    async def update_role(self, user_id: UUID, role: Role, now: datetime) -> User | None:
        entry = self.by_id.get(user_id)
        if entry is None:
            return None
        new_u = User(
            id=entry.user.id,
            email=entry.user.email,
            name=entry.user.name,
            role=role,
            avatar_color=entry.user.avatar_color,
        )
        updated = UserWithPassword(user=new_u, password_hash=entry.password_hash)
        self.by_id[user_id] = updated
        self.by_email[new_u.email] = updated
        return new_u


class _MemSessionStore:
    def __init__(self) -> None:
        self.sessions: dict[bytes, RefreshSession] = {}

    async def create_session(self, session: RefreshSession) -> None:
        self.sessions[session.token_hash] = session

    async def get_session_by_token_hash(self, token_hash: bytes) -> RefreshSession | None:
        return self.sessions.get(token_hash)

    async def replace_session(self, old_id: UUID, new_session: RefreshSession, now: datetime) -> None:
        self.sessions[new_session.token_hash] = new_session

    async def revoke_session(self, session_id: UUID, now: datetime) -> None:
        for h, s in list(self.sessions.items()):
            if s.id == session_id:
                self.sessions[h] = RefreshSession(
                    id=s.id,
                    user_id=s.user_id,
                    family_id=s.family_id,
                    token_hash=s.token_hash,
                    created_at=s.created_at,
                    expires_at=s.expires_at,
                    revoked_at=now,
                )

    async def revoke_family(self, family_id: UUID, now: datetime) -> None:
        pass

    async def revoke_all_user_sessions(self, user_id: UUID, now: datetime) -> None:
        for h, s in list(self.sessions.items()):
            if s.user_id == user_id:
                self.sessions[h] = RefreshSession(
                    id=s.id,
                    user_id=s.user_id,
                    family_id=s.family_id,
                    token_hash=s.token_hash,
                    created_at=s.created_at,
                    expires_at=s.expires_at,
                    revoked_at=now,
                )


class _FakeAdminStore(AdminStore):
    def __init__(self) -> None:
        self.reports = [
            MessageReportItem(
                id=1,
                reason="inaccurate",
                comment="Проверить дозу",
                request_text="Болит голова",
                answer_text="Примите Ибупрофен",
                status=ReportStatus.NEW,
                created_at=datetime.now(UTC),
            )
        ]

    async def get_stats(self, period: StatsPeriod, *, fallback_medicines_count: int = 0) -> UserStats:
        return UserStats(
            period=period,
            users_total=3,
            active_users=2,
            new_users=1,
            recent_users=[
                AdminUserSummary(
                    id=uuid4(),
                    email="u@medai.local",
                    name="Тест",
                    role="user",
                    registered_at=datetime.now(UTC),
                    dialogs=2,
                    kit_count=4,
                    medcard_filled=True,
                )
            ],
            feedback=FeedbackSummary(answers_total=5, rated_answers=2, counts=[0, 0, 0, 1, 1]),
            reports_new=1,
            dialogs=2,
            messages=6,
            medicines_count=fallback_medicines_count,
            activity=[ActivityPoint(start=datetime.now(UTC), dialogs=2)],
        )

    async def list_reports(self, status: ReportStatus | None = None) -> list[MessageReportItem]:
        if status is None:
            return self.reports
        return [r for r in self.reports if r.status == status]

    async def set_report_status(self, report_id: int, status: ReportStatus, admin_id: UUID) -> None:
        for idx, r in enumerate(self.reports):
            if r.id == report_id:
                self.reports[idx] = MessageReportItem(
                    id=r.id,
                    reason=r.reason,
                    comment=r.comment,
                    request_text=r.request_text,
                    answer_text=r.answer_text,
                    status=status,
                    created_at=r.created_at,
                    resolved_at=datetime.now(UTC),
                )
                return


@pytest.mark.asyncio
async def test_blacklist_and_change_password_and_csrf() -> None:
    blacklist = InMemoryTokenBlacklist()
    await blacklist.revoke("jti-1", 60)
    assert await blacklist.is_revoked("jti-1") is True
    assert await blacklist.is_revoked("jti-2") is False

    cfg = AuthConfig(rate_limit=AuthRateLimitConfig(login_per_ip=50))
    users = _MemUserStore()
    sessions = _MemSessionStore()
    auth_svc = AuthService(
        config=cfg,
        users=users,
        sessions=sessions,
        hasher=Argon2PasswordHasher(),
        tokens=TokenCodec(cfg),
        limiter=InMemoryRateLimiter(cfg.rate_limit),
        blacklist=blacklist,
    )
    app = create_app(auth_service=auth_svc, admin_store=_FakeAdminStore())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # CSRF check blocks Sec-Fetch-Site: cross-site on unsafe POST
        csrf_res = await client.post(
            "/api/v1/auth/register",
            json={"email": "csrf@medai.local", "password": "Password123!", "name": "Test"},
            headers={"Sec-Fetch-Site": "cross-site"},
        )
        assert csrf_res.status_code == 403

        # Register -> change password -> old token rejected
        reg = await client.post(
            "/api/v1/auth/register",
            json={"email": "pwuser@medai.local", "password": "Password123!", "name": "Иван"},
        )
        assert reg.status_code == 200
        old_access = reg.cookies.get("access_token")

        cp = await client.post(
            "/api/v1/auth/change-password",
            json={"old_password": "Password123!", "new_password": "NewPassword456!"},
        )
        assert cp.status_code == 200

        # Old JWT must now be rejected by Redis/InMemory blacklist
        me_after = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {old_access}"},
        )
        assert me_after.status_code == 401


@pytest.mark.asyncio
async def test_feedback_reports_admin_and_speech_endpoints() -> None:
    pkg_path = Path(__file__).resolve().parents[2] / "data" / "medicines" / "package.yaml"
    analyzer = MorphAnalyzer()
    bm25 = load_package_from_yaml(pkg_path, analyzer)
    history = InMemoryHistoryStore()
    d_svc = DialogService(
        history_store=history,
        event_broker=InMemoryDialogEventBroker(),
        bm25_index=bm25,
        analyzer=analyzer,
    )
    app = create_app(dialog_service=d_svc, admin_store=_FakeAdminStore())

    admin_user = User(
        id=uuid4(),
        email="admin@medai.local",
        name="Админ",
        role=Role.ADMIN,
        avatar_color="#00B074",
    )
    app.dependency_overrides[get_current_user] = lambda: admin_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        d_res = await client.post("/api/v1/dialogs")
        d_id = d_res.json()["dialog_id"]
        await client.post(f"/api/v1/dialogs/{d_id}/messages", json={"content": "Болит голова"})
        task = d_svc._dialog_chains.get(UUID(d_id))
        if task:
            await task

        msgs = (await client.get(f"/api/v1/dialogs/{d_id}/messages")).json()["messages"]
        asst_id = msgs[1]["id"]

        # Feedback 1..5
        fb_res = await client.put(
            f"/api/v1/dialogs/{d_id}/messages/{asst_id}/feedback", json={"score": 5}
        )
        assert fb_res.status_code == 204
        msgs_after = (await client.get(f"/api/v1/dialogs/{d_id}/messages")).json()["messages"]
        assert msgs_after[1]["feedback"] == 5

        # Report message
        rep_res = await client.post(
            f"/api/v1/dialogs/{d_id}/messages/{asst_id}/report",
            json={"reason": "inaccurate", "comment": "Тестовая жалоба"},
        )
        assert rep_res.status_code == 201

        # Speech router returns 503 fallback signal when Silero model not mounted
        sp_res = await client.post(
            f"/api/v1/dialogs/{d_id}/messages/{asst_id}/audio",
            json={"voice": "baya"},
        )
        assert sp_res.status_code == 503

        # Admin stats, reports, and live benchmark
        st_res = await client.get("/api/v1/admin/stats?period=30")
        assert st_res.status_code == 200
        assert st_res.json()["users_total"] == 3

        reps = await client.get("/api/v1/admin/reports?status_filter=new")
        assert reps.status_code == 200
        assert len(reps.json()["reports"]) == 1

        patch_rep = await client.patch(
            "/api/v1/admin/reports/1", json={"status": "resolved"}
        )
        assert patch_rep.status_code == 204

        bm_res = await client.get("/api/v1/admin/benchmark?dataset=base")
        assert bm_res.status_code == 200
        assert len(bm_res.json()["rows"]) == 3
