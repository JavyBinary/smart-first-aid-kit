"""PostgreSQL implementation of HistoryStore (dialogs, messages, feedback, reports)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from medai.db.tables import dialogs, message_feedback, message_reports, messages
from medai.dialogs.history import (
    DialogMessage,
    DialogNotFoundError,
    DialogSummary,
    DialogTranscript,
    HistoryStore,
    MessageNotFoundError,
    ReportExistsError,
    ReportNewsItem,
)

__all__ = ["PostgresHistoryStore"]


class PostgresHistoryStore(HistoryStore):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def create_dialog(self, owner_id: UUID) -> UUID:
        dialog_id = uuid4()
        now = datetime.now(UTC)
        stmt = insert(dialogs).values(
            id=dialog_id,
            user_id=owner_id,
            title="Новый диалог",
            created_at=now,
            updated_at=now,
        )
        async with self._engine.begin() as conn:
            await conn.execute(stmt)
        return dialog_id

    async def list_dialogs(
        self, owner_id: UUID, limit: int = 50
    ) -> list[DialogSummary]:
        stmt = (
            select(
                dialogs.c.id,
                dialogs.c.title,
                dialogs.c.created_at,
                dialogs.c.updated_at,
            )
            .where(dialogs.c.user_id == owner_id)
            .order_by(dialogs.c.updated_at.desc())
            .limit(limit)
        )
        async with self._engine.connect() as conn:
            res = await conn.execute(stmt)
            rows = res.all()

        return [
            DialogSummary(
                dialog_id=row.id,
                title=row.title or "Новый диалог",
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    async def get_transcript(self, owner_id: UUID, dialog_id: UUID) -> DialogTranscript:
        dialog_stmt = select(dialogs.c.title).where(
            dialogs.c.id == dialog_id,
            dialogs.c.user_id == owner_id,
        )
        msg_stmt = (
            select(
                messages.c.id,
                messages.c.position,
                messages.c.role,
                messages.c.content,
                messages.c.rag_payload,
                messages.c.created_at,
                message_feedback.c.score.label("feedback"),
                message_reports.c.id.label("report_id"),
            )
            .select_from(
                messages.outerjoin(
                    message_feedback, messages.c.id == message_feedback.c.message_id
                ).outerjoin(
                    message_reports, messages.c.id == message_reports.c.message_id
                )
            )
            .where(messages.c.dialog_id == dialog_id)
            .order_by(messages.c.position.asc())
        )
        async with self._engine.connect() as conn:
            d_res = await conn.execute(dialog_stmt)
            d_row = d_res.first()
            if d_row is None:
                raise DialogNotFoundError(dialog_id)
            m_res = await conn.execute(msg_stmt)
            m_rows = m_res.all()

        return DialogTranscript(
            dialog_id=dialog_id,
            title=d_row.title or "Новый диалог",
            messages=[
                DialogMessage(
                    id=row.id,
                    position=row.position,
                    role=row.role,
                    content=row.content,
                    rag_payload=row.rag_payload,
                    feedback=row.feedback,
                    reported=row.report_id is not None,
                    created_at=row.created_at,
                )
                for row in m_rows
            ],
        )

    async def delete_dialog(self, owner_id: UUID, dialog_id: UUID) -> bool:
        async with self._engine.begin() as conn:
            await conn.execute(
                update(message_reports)
                .where(message_reports.c.dialog_id == dialog_id)
                .values(dialog_deleted=1)
            )
            stmt = (
                delete(dialogs)
                .where(dialogs.c.id == dialog_id, dialogs.c.user_id == owner_id)
                .returning(dialogs.c.id)
            )
            res = await conn.execute(stmt)
            return res.first() is not None

    async def append_exchange(
        self,
        owner_id: UUID,
        dialog_id: UUID,
        user_content: str,
        assistant_content: str,
        rag_payload: dict[str, Any] | None = None,
        title: str | None = None,
    ) -> tuple[DialogMessage, DialogMessage]:
        async with self._engine.begin() as conn:
            d_stmt = select(dialogs.c.title).where(
                dialogs.c.id == dialog_id,
                dialogs.c.user_id == owner_id,
            )
            d_row = (await conn.execute(d_stmt)).first()
            if d_row is None:
                raise DialogNotFoundError(dialog_id)

            now = datetime.now(UTC)
            pos_stmt = select(func.coalesce(func.max(messages.c.position), 0)).where(
                messages.c.dialog_id == dialog_id
            )
            cur_pos = (await conn.execute(pos_stmt)).scalar() or 0

            update_vals: dict[str, Any] = {"updated_at": now}
            if title and d_row.title in ("Новый диалог", "", None):
                update_vals["title"] = title
            await conn.execute(
                update(dialogs).where(dialogs.c.id == dialog_id).values(**update_vals)
            )

            user_stmt = (
                insert(messages)
                .values(
                    dialog_id=dialog_id,
                    position=cur_pos + 1,
                    role="user",
                    content=user_content,
                    rag_payload=None,
                    created_at=now,
                )
                .returning(messages.c.id, messages.c.created_at)
            )
            user_row = (await conn.execute(user_stmt)).one()

            asst_stmt = (
                insert(messages)
                .values(
                    dialog_id=dialog_id,
                    position=cur_pos + 2,
                    role="assistant",
                    content=assistant_content,
                    rag_payload=rag_payload,
                    created_at=now,
                )
                .returning(messages.c.id, messages.c.created_at)
            )
            asst_row = (await conn.execute(asst_stmt)).one()

            return (
                DialogMessage(
                    id=user_row.id,
                    position=cur_pos + 1,
                    role="user",
                    content=user_content,
                    rag_payload=None,
                    created_at=user_row.created_at,
                ),
                DialogMessage(
                    id=asst_row.id,
                    position=cur_pos + 2,
                    role="assistant",
                    content=assistant_content,
                    rag_payload=rag_payload,
                    created_at=asst_row.created_at,
                ),
            )

    async def _verify_assistant_message(
        self, conn: Any, owner_id: UUID, dialog_id: UUID, message_id: int
    ) -> tuple[str, str, int]:
        d_row = (
            await conn.execute(
                select(dialogs.c.title).where(
                    dialogs.c.id == dialog_id,
                    dialogs.c.user_id == owner_id,
                )
            )
        ).first()
        if d_row is None:
            raise DialogNotFoundError(dialog_id)

        m_row = (
            await conn.execute(
                select(messages.c.content, messages.c.position).where(
                    messages.c.id == message_id,
                    messages.c.dialog_id == dialog_id,
                    messages.c.role == "assistant",
                )
            )
        ).first()
        if m_row is None:
            raise MessageNotFoundError(message_id)
        return d_row.title or "Диалог", m_row.content, int(m_row.position)

    async def set_feedback(
        self, owner_id: UUID, dialog_id: UUID, message_id: int, score: int
    ) -> None:
        now = datetime.now(UTC)
        async with self._engine.begin() as conn:
            await self._verify_assistant_message(conn, owner_id, dialog_id, message_id)
            if conn.dialect.name == "postgresql":
                stmt = (
                    pg_insert(message_feedback)
                    .values(
                        message_id=message_id,
                        user_id=owner_id,
                        score=score,
                        created_at=now,
                        updated_at=now,
                    )
                    .on_conflict_do_update(
                        index_elements=["message_id"],
                        set_={"score": score, "updated_at": now},
                    )
                )
                await conn.execute(stmt)
            else:
                await conn.execute(
                    delete(message_feedback).where(
                        message_feedback.c.message_id == message_id
                    )
                )
                await conn.execute(
                    insert(message_feedback).values(
                        message_id=message_id,
                        user_id=owner_id,
                        score=score,
                        created_at=now,
                        updated_at=now,
                    )
                )

    async def clear_feedback(
        self, owner_id: UUID, dialog_id: UUID, message_id: int
    ) -> None:
        async with self._engine.begin() as conn:
            await self._verify_assistant_message(conn, owner_id, dialog_id, message_id)
            await conn.execute(
                delete(message_feedback).where(
                    message_feedback.c.message_id == message_id
                )
            )

    async def create_report(
        self,
        owner_id: UUID,
        dialog_id: UUID,
        message_id: int,
        reason: str,
        comment: str | None,
    ) -> int:
        now = datetime.now(UTC)
        async with self._engine.begin() as conn:
            d_title, answer_text, pos = await self._verify_assistant_message(
                conn, owner_id, dialog_id, message_id
            )
            req_row = (
                await conn.execute(
                    select(messages.c.content)
                    .where(
                        messages.c.dialog_id == dialog_id,
                        messages.c.position < pos,
                        messages.c.role == "user",
                    )
                    .order_by(messages.c.position.desc())
                    .limit(1)
                )
            ).first()
            request_text = req_row.content if req_row else ""

            try:
                rep_id = (
                    await conn.execute(
                        insert(message_reports)
                        .values(
                            message_id=message_id,
                            dialog_id=dialog_id,
                            user_id=owner_id,
                            dialog_title=d_title,
                            reason=reason,
                            comment=comment,
                            request_text=request_text,
                            answer_text=answer_text,
                            status="new",
                            created_at=now,
                        )
                        .returning(message_reports.c.id)
                    )
                ).scalar_one()
                return int(rep_id)
            except IntegrityError as err:
                raise ReportExistsError(message_id) from err

    async def list_report_news(self, owner_id: UUID) -> list[ReportNewsItem]:
        stmt = (
            select(
                message_reports.c.id,
                message_reports.c.dialog_id,
                message_reports.c.dialog_title,
            )
            .where(
                message_reports.c.user_id == owner_id,
                message_reports.c.status.in_(("resolved", "dismissed")),
                message_reports.c.seen_at.is_(None),
            )
            .order_by(message_reports.c.resolved_at.desc())
        )
        async with self._engine.connect() as conn:
            rows = (await conn.execute(stmt)).all()
        return [
            ReportNewsItem(
                report_id=r.id,
                dialog_id=r.dialog_id,
                dialog_title=r.dialog_title or "Диалог",
            )
            for r in rows
        ]

    async def mark_report_news_seen(
        self, owner_id: UUID, report_ids: list[int]
    ) -> None:
        if not report_ids:
            return
        async with self._engine.begin() as conn:
            await conn.execute(
                update(message_reports)
                .where(
                    message_reports.c.user_id == owner_id,
                    message_reports.c.id.in_(report_ids),
                )
                .values(seen_at=datetime.now(UTC))
            )
