"""Dialog history domain models, persistence abstraction, and in-memory store."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "DialogMessage",
    "DialogNotFoundError",
    "DialogSummary",
    "DialogTranscript",
    "HistoryStore",
    "InMemoryHistoryStore",
    "make_title",
]


def make_title(text: str, max_length: int = 80) -> str:
    """Format dialog title from initial user message text."""
    collapsed = " ".join(text.strip().split())
    if not collapsed:
        return "Новый диалог"
    if len(collapsed) <= max_length:
        return collapsed
    return collapsed[: max_length - 1].rstrip() + "…"


class DialogNotFoundError(Exception):
    def __init__(self, dialog_id: UUID) -> None:
        super().__init__(f"Dialog {dialog_id} not found.")
        self.dialog_id = dialog_id


class DialogSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dialog_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class DialogMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: int
    position: int
    role: Literal["user", "assistant", "system"]
    content: str
    rag_payload: dict[str, Any] | None = None
    created_at: datetime


class DialogTranscript(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dialog_id: UUID
    title: str
    messages: list[DialogMessage] = Field(default_factory=list)


class HistoryStore(ABC):
    @abstractmethod
    async def create_dialog(self, owner_id: UUID) -> UUID:
        """Create a new empty dialog for owner."""

    @abstractmethod
    async def list_dialogs(
        self, owner_id: UUID, limit: int = 50
    ) -> list[DialogSummary]:
        """List owner's dialogs ordered by updated_at descending."""

    @abstractmethod
    async def get_transcript(self, owner_id: UUID, dialog_id: UUID) -> DialogTranscript:
        """Retrieve full transcript of messages for owner's dialog."""

    @abstractmethod
    async def delete_dialog(self, owner_id: UUID, dialog_id: UUID) -> bool:
        """Delete dialog belonging to owner."""

    @abstractmethod
    async def append_exchange(
        self,
        owner_id: UUID,
        dialog_id: UUID,
        user_content: str,
        assistant_content: str,
        rag_payload: dict[str, Any] | None = None,
        title: str | None = None,
    ) -> tuple[DialogMessage, DialogMessage]:
        """Atomically append a user-assistant message exchange."""


class InMemoryHistoryStore(HistoryStore):
    """In-memory history store implementation for rapid unit and contract testing."""

    def __init__(self) -> None:
        self._dialogs: dict[UUID, dict[str, Any]] = {}
        self._messages: dict[UUID, list[DialogMessage]] = {}
        self._msg_id_counter = 1

    async def create_dialog(self, owner_id: UUID) -> UUID:
        now = datetime.now(UTC)
        dialog_id = uuid4()
        self._dialogs[dialog_id] = {
            "id": dialog_id,
            "owner_id": owner_id,
            "title": "Новый диалог",
            "created_at": now,
            "updated_at": now,
        }
        self._messages[dialog_id] = []
        return dialog_id

    async def list_dialogs(
        self, owner_id: UUID, limit: int = 50
    ) -> list[DialogSummary]:
        user_dialogs = [
            DialogSummary(
                dialog_id=d["id"],
                title=d["title"],
                created_at=d["created_at"],
                updated_at=d["updated_at"],
            )
            for d in self._dialogs.values()
            if d["owner_id"] == owner_id
        ]
        user_dialogs.sort(key=lambda d: d.updated_at, reverse=True)
        return user_dialogs[:limit]

    async def get_transcript(self, owner_id: UUID, dialog_id: UUID) -> DialogTranscript:
        dialog = self._dialogs.get(dialog_id)
        if dialog is None or dialog["owner_id"] != owner_id:
            raise DialogNotFoundError(dialog_id)
        return DialogTranscript(
            dialog_id=dialog_id,
            title=dialog["title"],
            messages=list(self._messages.get(dialog_id, [])),
        )

    async def delete_dialog(self, owner_id: UUID, dialog_id: UUID) -> bool:
        dialog = self._dialogs.get(dialog_id)
        if dialog is None or dialog["owner_id"] != owner_id:
            return False
        del self._dialogs[dialog_id]
        self._messages.pop(dialog_id, None)
        return True

    async def append_exchange(
        self,
        owner_id: UUID,
        dialog_id: UUID,
        user_content: str,
        assistant_content: str,
        rag_payload: dict[str, Any] | None = None,
        title: str | None = None,
    ) -> tuple[DialogMessage, DialogMessage]:
        dialog = self._dialogs.get(dialog_id)
        if dialog is None or dialog["owner_id"] != owner_id:
            raise DialogNotFoundError(dialog_id)

        now = datetime.now(UTC)
        msgs = self._messages.setdefault(dialog_id, [])
        pos = len(msgs)

        if title and dialog["title"] in ("Новый диалог", "", None):
            dialog["title"] = title
        dialog["updated_at"] = now

        user_msg = DialogMessage(
            id=self._msg_id_counter,
            position=pos + 1,
            role="user",
            content=user_content,
            rag_payload=None,
            created_at=now,
        )
        self._msg_id_counter += 1

        assistant_msg = DialogMessage(
            id=self._msg_id_counter,
            position=pos + 2,
            role="assistant",
            content=assistant_content,
            rag_payload=rag_payload,
            created_at=now,
        )
        self._msg_id_counter += 1

        msgs.extend([user_msg, assistant_msg])
        return user_msg, assistant_msg
