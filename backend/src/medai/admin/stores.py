"""PostgreSQL & InMemory stores for Admin dashboard stats and report moderation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from medai.admin.models import (
    ActivityPoint,
    AdminUserSummary,
    FeedbackSummary,
    MessageReportItem,
    ReportStatus,
    StatsPeriod,
    UserStats,
)
from medai.db.tables import (
    dialogs,
    health_profiles,
    message_feedback,
    message_reports,
    messages,
    rag_medicines,
    refresh_sessions,
    user_kits,
    users,
)

__all__ = ["AdminStore", "PostgresAdminStore", "ReportNotFoundError"]


class ReportNotFoundError(Exception):
    def __init__(self, report_id: int) -> None:
        super().__init__(f"Report {report_id} not found.")
        self.report_id = report_id


class AdminStore:
    async def get_stats(
        self, period: StatsPeriod, *, fallback_medicines_count: int = 0
    ) -> UserStats:
        raise NotImplementedError

    async def list_reports(
        self, status: ReportStatus | None = None
    ) -> list[MessageReportItem]:
        return []

    async def set_report_status(
        self, report_id: int, status: ReportStatus, admin_id: UUID
    ) -> None:
        raise ReportNotFoundError(report_id)


class PostgresAdminStore(AdminStore):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def get_stats(
        self, period: StatsPeriod, *, fallback_medicines_count: int = 0
    ) -> UserStats:
        days = int(period.value)
        now = datetime.now(UTC)
        since = now - timedelta(days=days)
        bucket_count = 7 if days == 7 else (10 if days == 30 else 9)
        bucket_delta = timedelta(days=days) / bucket_count

        async with self._engine.connect() as conn:
            users_total = int(
                (await conn.execute(select(func.count()).select_from(users))).scalar()
                or 0
            )
            new_users = int(
                (
                    await conn.execute(
                        select(func.count())
                        .select_from(users)
                        .where(users.c.created_at >= since)
                    )
                ).scalar()
                or 0
            )
            active_users = int(
                (
                    await conn.execute(
                        select(func.count(func.distinct(refresh_sessions.c.user_id)))
                        .where(refresh_sessions.c.created_at >= since)
                    )
                ).scalar()
                or 0
            )
            med_db_count = int(
                (
                    await conn.execute(
                        select(func.count()).select_from(rag_medicines)
                    )
                ).scalar()
                or 0
            )

            # Non-empty dialogs created in window
            non_empty_dialog_ids = (
                select(messages.c.dialog_id).distinct().scalar_subquery()
            )
            dialogs_in_window = int(
                (
                    await conn.execute(
                        select(func.count())
                        .select_from(dialogs)
                        .where(
                            dialogs.c.created_at >= since,
                            dialogs.c.id.in_(non_empty_dialog_ids),
                        )
                    )
                ).scalar()
                or 0
            )
            messages_in_window = int(
                (
                    await conn.execute(
                        select(func.count())
                        .select_from(messages)
                        .where(messages.c.created_at >= since)
                    )
                ).scalar()
                or 0
            )

            answers_total = int(
                (
                    await conn.execute(
                        select(func.count())
                        .select_from(messages)
                        .where(
                            messages.c.role == "assistant",
                            messages.c.created_at >= since,
                        )
                    )
                ).scalar()
                or 0
            )

            fb_rows = (
                await conn.execute(
                    select(message_feedback.c.score, func.count())
                    .select_from(
                        message_feedback.join(
                            messages, message_feedback.c.message_id == messages.c.id
                        )
                    )
                    .where(messages.c.created_at >= since)
                    .group_by(message_feedback.c.score)
                )
            ).all()
            counts = [0, 0, 0, 0, 0]
            for score, cnt in fb_rows:
                if 1 <= int(score) <= 5:
                    counts[int(score) - 1] = int(cnt)

            reports_new = int(
                (
                    await conn.execute(
                        select(func.count())
                        .select_from(message_reports)
                        .where(message_reports.c.status == "new")
                    )
                ).scalar()
                or 0
            )

            # Activity buckets
            dlg_times = (
                await conn.execute(
                    select(dialogs.c.created_at).where(
                        dialogs.c.created_at >= since,
                        dialogs.c.id.in_(non_empty_dialog_ids),
                    )
                )
            ).scalars().all()
            buckets = [0] * bucket_count
            for ts in dlg_times:
                ts_utc = ts if ts.tzinfo else ts.replace(tzinfo=UTC)
                idx = int((ts_utc - since) / bucket_delta)
                if 0 <= idx < bucket_count:
                    buckets[idx] += 1
                elif idx >= bucket_count:
                    buckets[bucket_count - 1] += 1
            activity = [
                ActivityPoint(start=since + bucket_delta * i, dialogs=buckets[i])
                for i in range(bucket_count)
            ]

            # Users overview
            u_rows = (
                await conn.execute(
                    select(users).order_by(users.c.created_at.desc()).limit(25)
                )
            ).all()

            recent_users: list[AdminUserSummary] = []
            for u in u_rows:
                u_dialogs = int(
                    (
                        await conn.execute(
                            select(func.count())
                            .select_from(dialogs)
                            .where(
                                dialogs.c.user_id == u.id,
                                dialogs.c.id.in_(non_empty_dialog_ids),
                            )
                        )
                    ).scalar()
                    or 0
                )
                u_kit = int(
                    (
                        await conn.execute(
                            select(func.count())
                            .select_from(user_kits)
                            .where(user_kits.c.user_id == u.id)
                        )
                    ).scalar()
                    or 0
                )
                prof_row = (
                    await conn.execute(
                        select(
                            health_profiles.c.allergies,
                            health_profiles.c.chronic_diseases,
                        ).where(health_profiles.c.user_id == u.id)
                    )
                ).first()
                medcard_filled = False
                if prof_row:
                    medcard_filled = bool(prof_row.allergies or prof_row.chronic_diseases)

                last_sess = (
                    await conn.execute(
                        select(func.max(refresh_sessions.c.created_at)).where(
                            refresh_sessions.c.user_id == u.id
                        )
                    )
                ).scalar()

                recent_users.append(
                    AdminUserSummary(
                        id=u.id,
                        email=u.email,
                        name=u.name,
                        role=u.role,
                        registered_at=u.created_at,
                        last_active_at=last_sess,
                        dialogs=u_dialogs,
                        kit_count=u_kit,
                        medcard_filled=medcard_filled,
                    )
                )

        return UserStats(
            period=period,
            users_total=users_total,
            active_users=active_users,
            new_users=new_users,
            recent_users=recent_users,
            feedback=FeedbackSummary(
                answers_total=answers_total,
                rated_answers=sum(counts),
                counts=counts,
            ),
            reports_new=reports_new,
            dialogs=dialogs_in_window,
            messages=messages_in_window,
            medicines_count=med_db_count or fallback_medicines_count,
            activity=activity,
        )

    async def list_reports(
        self, status: ReportStatus | None = None
    ) -> list[MessageReportItem]:
        stmt = select(message_reports).order_by(message_reports.c.created_at.desc()).limit(50)
        if status is not None:
            stmt = stmt.where(message_reports.c.status == status.value)
        async with self._engine.connect() as conn:
            rows = (await conn.execute(stmt)).all()
        return [
            MessageReportItem(
                id=r.id,
                reason=r.reason,
                comment=r.comment,
                request_text=r.request_text,
                answer_text=r.answer_text,
                status=ReportStatus(r.status),
                created_at=r.created_at,
                resolved_at=r.resolved_at,
                dialog_deleted=bool(r.dialog_deleted),
            )
            for r in rows
        ]

    async def set_report_status(
        self, report_id: int, status: ReportStatus, admin_id: UUID
    ) -> None:
        now = datetime.now(UTC)
        resolved_at = None if status is ReportStatus.NEW else now
        resolved_by = None if status is ReportStatus.NEW else admin_id
        stmt = (
            update(message_reports)
            .where(message_reports.c.id == report_id)
            .values(
                status=status.value,
                resolved_at=resolved_at,
                resolved_by=resolved_by,
            )
            .returning(message_reports.c.id)
        )
        async with self._engine.begin() as conn:
            row = (await conn.execute(stmt)).first()
        if row is None:
            raise ReportNotFoundError(report_id)
