"""PostgreSQL implementation of HistoryStore using SQLAlchemy 2.0 Core."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from medai.db.tables import dialogs, messages
from medai.dialogs.history import (
    DialogMessage,
    DialogNotFoundError,
    DialogSummary,
    DialogTranscript,
    HistoryStore,
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
                    created_at=row.created_at,
                )
                for row in m_rows
            ],
        )

    async def delete_dialog(self, owner_id: UUID, dialog_id: UUID) -> bool:
        stmt = (
            delete(dialogs)
            .where(dialogs.c.id == dialog_id, dialogs.c.user_id == owner_id)
            .returning(dialogs.c.id)
        )
        async with self._engine.begin() as conn:
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
