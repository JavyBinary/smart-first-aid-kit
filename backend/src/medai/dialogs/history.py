"""Dialog history domain models, persistence abstraction, feedback, reports, and in-memory store."""

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
    "MessageNotFoundError",
    "ReportExistsError",
    "ReportNewsItem",
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


class MessageNotFoundError(Exception):
    def __init__(self, message_id: int) -> None:
        super().__init__(f"Message {message_id} not found.")
        self.message_id = message_id


class ReportExistsError(Exception):
    def __init__(self, message_id: int) -> None:
        super().__init__(f"Report already exists for message {message_id}.")
        self.message_id = message_id


class ReportNewsItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    report_id: int
    dialog_id: UUID | None = None
    dialog_title: str


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
    feedback: int | None = None
    reported: bool = False
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

    async def set_feedback(
        self, owner_id: UUID, dialog_id: UUID, message_id: int, score: int
    ) -> None:
        raise NotImplementedError

    async def clear_feedback(
        self, owner_id: UUID, dialog_id: UUID, message_id: int
    ) -> None:
        raise NotImplementedError

    async def create_report(
        self,
        owner_id: UUID,
        dialog_id: UUID,
        message_id: int,
        reason: str,
        comment: str | None,
    ) -> int:
        raise NotImplementedError

    async def list_report_news(self, owner_id: UUID) -> list[ReportNewsItem]:
        return []

    async def mark_report_news_seen(
        self, owner_id: UUID, report_ids: list[int]
    ) -> None:
        return None


class InMemoryHistoryStore(HistoryStore):
    """In-memory history store implementation for rapid unit and contract testing."""

    def __init__(self) -> None:
        self._dialogs: dict[UUID, dict[str, Any]] = {}
        self._messages: dict[UUID, list[DialogMessage]] = {}
        self._feedback: dict[int, int] = {}
        self._reports: dict[int, dict[str, Any]] = {}
        self._report_id_counter = 1
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
        msgs = [
            DialogMessage(
                id=m.id,
                position=m.position,
                role=m.role,
                content=m.content,
                rag_payload=m.rag_payload,
                feedback=self._feedback.get(m.id),
                reported=m.id in self._reports,
                created_at=m.created_at,
            )
            for m in self._messages.get(dialog_id, [])
        ]
        return DialogTranscript(
            dialog_id=dialog_id,
            title=dialog["title"],
            messages=msgs,
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

    def _find_assistant_message(
        self, owner_id: UUID, dialog_id: UUID, message_id: int
    ) -> tuple[DialogMessage, DialogMessage | None]:
        dialog = self._dialogs.get(dialog_id)
        if dialog is None or dialog["owner_id"] != owner_id:
            raise DialogNotFoundError(dialog_id)
        msgs = self._messages.get(dialog_id, [])
        for idx, msg in enumerate(msgs):
            if msg.id == message_id and msg.role == "assistant":
                prev_msg = msgs[idx - 1] if idx > 0 else None
                return msg, prev_msg
        raise MessageNotFoundError(message_id)

    async def set_feedback(
        self, owner_id: UUID, dialog_id: UUID, message_id: int, score: int
    ) -> None:
        self._find_assistant_message(owner_id, dialog_id, message_id)
        self._feedback[message_id] = score

    async def clear_feedback(
        self, owner_id: UUID, dialog_id: UUID, message_id: int
    ) -> None:
        self._find_assistant_message(owner_id, dialog_id, message_id)
        self._feedback.pop(message_id, None)

    async def create_report(
        self,
        owner_id: UUID,
        dialog_id: UUID,
        message_id: int,
        reason: str,
        comment: str | None,
    ) -> int:
        msg, prev_msg = self._find_assistant_message(owner_id, dialog_id, message_id)
        if message_id in self._reports:
            raise ReportExistsError(message_id)
        report_id = self._report_id_counter
        self._report_id_counter += 1
        self._reports[message_id] = {
            "id": report_id,
            "dialog_id": dialog_id,
            "user_id": owner_id,
            "dialog_title": self._dialogs[dialog_id]["title"],
            "reason": reason,
            "comment": comment,
            "request_text": prev_msg.content if prev_msg else "",
            "answer_text": msg.content,
            "status": "new",
            "seen_at": None,
        }
        return report_id
