"""Pydantic models for Admin 2.0 statistics, report moderation, and corpus management."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ActivityPoint",
    "AdminUserSummary",
    "FeedbackSummary",
    "MessageReportItem",
    "ReportStatus",
    "ReportStatusUpdate",
    "StatsPeriod",
    "UserStats",
]


class StatsPeriod(StrEnum):
    DAYS_7 = "7"
    DAYS_30 = "30"
    DAYS_90 = "90"


class ReportStatus(StrEnum):
    NEW = "new"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class ReportStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: ReportStatus


class AdminUserSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    email: str
    name: str
    role: str
    registered_at: datetime
    last_active_at: datetime | None = None
    dialogs: int = 0
    kit_count: int = 0
    medcard_filled: bool = False


class FeedbackSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    answers_total: int = 0
    rated_answers: int = 0
    counts: list[int] = Field(default_factory=lambda: [0, 0, 0, 0, 0])


class ActivityPoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    start: datetime
    dialogs: int = 0


class UserStats(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    period: StatsPeriod
    users_total: int
    active_users: int
    new_users: int
    recent_users: list[AdminUserSummary]
    feedback: FeedbackSummary
    reports_new: int
    dialogs: int
    messages: int
    medicines_count: int = 0
    activity: list[ActivityPoint]


class MessageReportItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: int
    reason: str
    comment: str | None = None
    request_text: str
    answer_text: str
    status: ReportStatus
    created_at: datetime
    resolved_at: datetime | None = None
    dialog_deleted: bool = False
