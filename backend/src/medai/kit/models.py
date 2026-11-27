"""Domain models and schemas for user first aid kit items."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "CreateKitItemRequest",
    "KitItem",
    "KitListResponse",
    "UpdateKitItemRequest",
]


class KitItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    name: str
    dosage: str
    form: str
    category: str
    tags: list[str] = Field(default_factory=list)
    quantity: int = 1
    expiry: str
    status: Literal["otc", "rx"] = "otc"
    is_expired: bool = False

    @classmethod
    def create(
        cls,
        id: str,
        name: str,
        dosage: str,
        form: str,
        category: str,
        tags: list[str] | None = None,
        quantity: int = 1,
        expiry: str = "2027-12-31",
        status: Literal["otc", "rx"] = "otc",
    ) -> KitItem:
        is_expired = False
        try:
            exp_date = date.fromisoformat(expiry)
            if exp_date < date.today():
                is_expired = True
        except ValueError:
            pass

        return cls(
            id=id,
            name=name,
            dosage=dosage,
            form=form,
            category=category,
            tags=list(tags) if tags else [],
            quantity=quantity,
            expiry=expiry,
            status=status,
            is_expired=is_expired,
        )


class CreateKitItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str | None = None
    name: str = Field(min_length=1)
    dosage: str = Field(default="По инструкции", min_length=1)
    form: str = Field(default="таблетки")
    category: str = Field(default="Общее")
    tags: list[str] = Field(default_factory=list)
    quantity: int = Field(default=1, ge=1)
    expiry: str = Field(default="2027-12-31")
    status: Literal["otc", "rx"] = Field(default="otc")


class UpdateKitItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str | None = Field(default=None, min_length=1)
    dosage: str | None = None
    form: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    quantity: int | None = Field(default=None, ge=1)
    expiry: str | None = None
    status: Literal["otc", "rx"] | None = None


class KitListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    items: list[KitItem]
    total: int
