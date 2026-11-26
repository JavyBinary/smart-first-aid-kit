"""Dialogs module exporting models, stores, services, and routers."""

from medai.dialogs.event_broker import DialogEventBroker, InMemoryDialogEventBroker
from medai.dialogs.events import DialogEvent, DialogEventType, DialogSubscription
from medai.dialogs.history import (
    DialogMessage,
    DialogNotFoundError,
    DialogSummary,
    DialogTranscript,
    HistoryStore,
    InMemoryHistoryStore,
    MessageNotFoundError,
    ReportExistsError,
    ReportNewsItem,
    make_title,
)
from medai.dialogs.postgres import PostgresHistoryStore
from medai.dialogs.router import create_dialogs_router
from medai.dialogs.service import DialogService

__all__ = [
    "DialogEvent",
    "DialogEventBroker",
    "DialogEventType",
    "DialogMessage",
    "DialogNotFoundError",
    "DialogService",
    "DialogSubscription",
    "DialogSummary",
    "DialogTranscript",
    "HistoryStore",
    "InMemoryDialogEventBroker",
    "InMemoryHistoryStore",
    "MessageNotFoundError",
    "PostgresHistoryStore",
    "ReportExistsError",
    "ReportNewsItem",
    "create_dialogs_router",
    "make_title",
]
