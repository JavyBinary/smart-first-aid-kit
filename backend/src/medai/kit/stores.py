"""Kit store abstraction and in-memory test store."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID, uuid4

from medai.kit.models import CreateKitItemRequest, KitItem, UpdateKitItemRequest

__all__ = ["InMemoryKitStore", "KitItemNotFoundError", "KitStore"]


class KitItemNotFoundError(Exception):
    def __init__(self, item_id: str) -> None:
        super().__init__(f"Kit item {item_id} not found.")
        self.item_id = item_id


class KitStore(ABC):
    @abstractmethod
    async def list_items(self, user_id: UUID) -> list[KitItem]:
        """List all medicines in user's first aid kit."""

    @abstractmethod
    async def add_item(self, user_id: UUID, req: CreateKitItemRequest) -> KitItem:
        """Add medicine item to user's first aid kit."""

    @abstractmethod
    async def update_item(
        self, user_id: UUID, item_id: str, req: UpdateKitItemRequest
    ) -> KitItem:
        """Update existing medicine item."""

    @abstractmethod
    async def delete_item(self, user_id: UUID, item_id: str) -> bool:
        """Delete medicine item from user's first aid kit."""


class InMemoryKitStore(KitStore):
    def __init__(self) -> None:
        # user_id -> dict of item_id -> KitItem
        self._items: dict[UUID, dict[str, KitItem]] = {}

    async def list_items(self, user_id: UUID) -> list[KitItem]:
        return list(self._items.get(user_id, {}).values())

    async def add_item(self, user_id: UUID, req: CreateKitItemRequest) -> KitItem:
        user_kit = self._items.setdefault(user_id, {})
        item_id = req.id or f"kit_{uuid4().hex[:8]}"
        item = KitItem.create(
            id=item_id,
            name=req.name,
            dosage=req.dosage,
            form=req.form,
            category=req.category,
            tags=req.tags,
            quantity=req.quantity,
            expiry=req.expiry,
            status=req.status,
        )
        user_kit[item_id] = item
        return item

    async def update_item(
        self, user_id: UUID, item_id: str, req: UpdateKitItemRequest
    ) -> KitItem:
        user_kit = self._items.get(user_id)
        if not user_kit or item_id not in user_kit:
            raise KitItemNotFoundError(item_id)
        current = user_kit[item_id]
        updated = KitItem.create(
            id=current.id,
            name=current.name,
            dosage=req.dosage if req.dosage is not None else current.dosage,
            form=current.form,
            category=current.category,
            tags=current.tags,
            quantity=req.quantity if req.quantity is not None else current.quantity,
            expiry=req.expiry if req.expiry is not None else current.expiry,
            status=req.status if req.status is not None else current.status,
        )
        user_kit[item_id] = updated
        return updated

    async def delete_item(self, user_id: UUID, item_id: str) -> bool:
        user_kit = self._items.get(user_id)
        if not user_kit or item_id not in user_kit:
            return False
        del user_kit[item_id]
        return True
