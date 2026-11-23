"""Dialog streaming events and consumer subscription protocol."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

__all__ = [
    "DialogEvent",
    "DialogEventType",
    "DialogSubscription",
]


class DialogEventType(StrEnum):
    MESSAGE_START = "message_start"
    MESSAGE_DELTA = "message_delta"
    MESSAGE_END = "message_end"
    MESSAGE_ERROR = "message_error"


class DialogEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: DialogEventType
    delta: str | None = None
    code: str | None = None
    message: str | None = None
    message_id: int | None = None
    emergency_mode: bool | None = None
    sources: list[dict[str, Any]] | None = None


class DialogSubscription(Protocol):
    @property
    def dialog_id(self) -> UUID: ...

    @property
    def closed(self) -> bool: ...

    async def receive(self) -> DialogEvent | None: ...
