"""In-memory event broker for multi-subscriber dialog streaming."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from uuid import UUID

from medai.dialogs.events import DialogEvent, DialogSubscription
from medai.observability import log_event

__all__ = [
    "DialogEventBroker",
    "InMemoryDialogEventBroker",
]

_CLOSED = object()
logger = logging.getLogger(__name__)


class DialogEventBroker(ABC):
    @abstractmethod
    async def subscribe(self, dialog_id: UUID) -> DialogSubscription:
        """Open a subscription for future events of one dialog."""

    @abstractmethod
    async def unsubscribe(self, subscription: DialogSubscription) -> None:
        """Close a subscription and release its resources."""

    @abstractmethod
    async def publish(self, dialog_id: UUID, event: DialogEvent) -> None:
        """Publish an event to active subscribers of one dialog."""

    @abstractmethod
    async def close_dialog(self, dialog_id: UUID) -> None:
        """Close all subscriptions of one dialog after delivering queued events."""

    @abstractmethod
    async def shutdown(self) -> None:
        """Close the broker and all active subscriptions."""


class _InMemoryDialogSubscription:
    def __init__(self, dialog_id: UUID, queue_size: int) -> None:
        self._dialog_id = dialog_id
        self._queue: asyncio.Queue[DialogEvent | object] = asyncio.Queue(queue_size)
        self._closed = False

    @property
    def dialog_id(self) -> UUID:
        return self._dialog_id

    @property
    def closed(self) -> bool:
        return self._closed

    async def receive(self) -> DialogEvent | None:
        item = await self._queue.get()
        if item is _CLOSED:
            return None
        assert isinstance(item, DialogEvent)
        return item

    def offer(self, event: DialogEvent) -> bool:
        if self._closed:
            return False
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            # Drop slow subscriber without blocking publisher
            self.close()
            return False
        return True

    def close(self, *, discard_pending: bool = True) -> None:
        if self._closed:
            return
        self._closed = True
        if discard_pending:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        elif self._queue.full():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        self._queue.put_nowait(_CLOSED)


class InMemoryDialogEventBroker(DialogEventBroker):
    def __init__(self, *, queue_size: int = 64) -> None:
        if queue_size <= 0:
            raise ValueError("queue_size must be positive")
        self._queue_size = queue_size
        self._subscribers: dict[UUID, set[_InMemoryDialogSubscription]] = {}
        self._lock = asyncio.Lock()
        self._closed = False

    async def subscribe(self, dialog_id: UUID) -> DialogSubscription:
        async with self._lock:
            if self._closed:
                raise RuntimeError("Dialog event broker is closed.")
            subscription = _InMemoryDialogSubscription(dialog_id, self._queue_size)
            self._subscribers.setdefault(dialog_id, set()).add(subscription)
            log_event(
                logger,
                logging.DEBUG,
                "dialog_events.subscribed",
                dialog_id=str(dialog_id),
            )
            return subscription

    async def unsubscribe(self, subscription: DialogSubscription) -> None:
        async with self._lock:
            subscribers = self._subscribers.get(subscription.dialog_id)
            if subscribers is None:
                return
            matched = next(
                (s for s in subscribers if s is subscription),
                None,
            )
            if matched is not None:
                subscribers.discard(matched)
                matched.close()
            if not subscribers:
                self._subscribers.pop(subscription.dialog_id, None)

    async def publish(self, dialog_id: UUID, event: DialogEvent) -> None:
        async with self._lock:
            subscribers = self._subscribers.get(dialog_id)
            if not subscribers:
                return
            to_remove: list[_InMemoryDialogSubscription] = []
            for sub in subscribers:
                if not sub.offer(event):
                    to_remove.append(sub)
            for sub in to_remove:
                subscribers.discard(sub)
            if not subscribers:
                self._subscribers.pop(dialog_id, None)

    async def close_dialog(self, dialog_id: UUID) -> None:
        async with self._lock:
            subscribers = self._subscribers.pop(dialog_id, None)
            if subscribers is not None:
                for sub in subscribers:
                    sub.close(discard_pending=False)

    async def shutdown(self) -> None:
        async with self._lock:
            if self._closed:
                return
            self._closed = True
            for subscribers in self._subscribers.values():
                for sub in subscribers:
                    sub.close()
            self._subscribers.clear()
