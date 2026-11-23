"""FastAPI router for user first aid kit items."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from medai.auth.models import User
from medai.auth.router import get_current_user
from medai.kit.models import (
    CreateKitItemRequest,
    KitItem,
    KitListResponse,
    UpdateKitItemRequest,
)
from medai.kit.stores import KitItemNotFoundError, KitStore

__all__ = ["create_kit_router"]


def create_kit_router(kit_store: KitStore) -> APIRouter:
    router = APIRouter(prefix="/api/v1/kit", tags=["kit"])

    @router.get("", response_model=KitListResponse)
    async def get_kit(
        user: User = Depends(get_current_user),
    ) -> KitListResponse:
        items = await kit_store.list_items(user.id)
        return KitListResponse(items=items, total=len(items))

    @router.post(
        "/items",
        status_code=status.HTTP_201_CREATED,
        response_model=dict[str, Any],
    )
    async def add_kit_item(
        body: CreateKitItemRequest,
        user: User = Depends(get_current_user),
    ) -> dict[str, Any]:
        item = await kit_store.add_item(user.id, body)
        return {
            "id": item.id,
            "status": "created",
            "item": item.model_dump(),
        }

    @router.put("/items/{item_id}", response_model=KitItem)
    async def update_kit_item(
        item_id: str,
        body: UpdateKitItemRequest,
        user: User = Depends(get_current_user),
    ) -> KitItem:
        try:
            return await kit_store.update_item(user.id, item_id, body)
        except KitItemNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Medicine item {item_id} not found in kit",
            )

    @router.delete("/items/{item_id}", response_model=dict[str, str])
    async def delete_kit_item(
        item_id: str,
        user: User = Depends(get_current_user),
    ) -> dict[str, str]:
        deleted = await kit_store.delete_item(user.id, item_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Medicine item {item_id} not found in kit",
            )
        return {"status": "deleted"}

    return router
