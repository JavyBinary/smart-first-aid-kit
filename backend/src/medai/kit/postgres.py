"""PostgreSQL implementation of KitStore using SQLAlchemy 2.0 Core."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from medai.db.tables import user_kits
from medai.kit.models import CreateKitItemRequest, KitItem, UpdateKitItemRequest
from medai.kit.stores import KitItemNotFoundError, KitStore

__all__ = ["PostgresKitStore"]


def _to_uuid(item_id: str) -> UUID:
    try:
        return UUID(item_id)
    except ValueError:
        return uuid4()


class PostgresKitStore(KitStore):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def list_items(self, user_id: UUID) -> list[KitItem]:
        stmt = (
            select(
                user_kits.c.id,
                user_kits.c.medicine_name,
                user_kits.c.dosage,
                user_kits.c.form,
                user_kits.c.category,
                user_kits.c.tags,
                user_kits.c.quantity,
                user_kits.c.expiry_date,
                user_kits.c.status,
            )
            .where(user_kits.c.user_id == user_id)
            .order_by(user_kits.c.created_at.desc())
        )
        async with self._engine.connect() as conn:
            res = await conn.execute(stmt)
            rows = res.all()

        items: list[KitItem] = []
        for r in rows:
            exp_str = (
                r.expiry_date.isoformat() if r.expiry_date else "2027-12-31"
            )
            items.append(
                KitItem.create(
                    id=str(r.id),
                    name=r.medicine_name,
                    dosage=r.dosage,
                    form=r.form,
                    category=r.category,
                    tags=r.tags if isinstance(r.tags, list) else [],
                    quantity=r.quantity,
                    expiry=exp_str,
                    status=r.status,
                )
            )
        return items

    async def add_item(self, user_id: UUID, req: CreateKitItemRequest) -> KitItem:
        item_uuid = uuid4()
        now = datetime.now(UTC)
        try:
            exp_date = date.fromisoformat(req.expiry)
        except ValueError:
            exp_date = date(2027, 12, 31)

        stmt = (
            insert(user_kits)
            .values(
                id=item_uuid,
                user_id=user_id,
                medicine_name=req.name,
                dosage=req.dosage,
                form=req.form,
                category=req.category,
                tags=req.tags,
                quantity=req.quantity,
                expiry_date=exp_date,
                status=req.status,
                created_at=now,
                updated_at=now,
            )
            .returning(user_kits.c.id)
        )
        async with self._engine.begin() as conn:
            await conn.execute(stmt)

        return KitItem.create(
            id=str(item_uuid),
            name=req.name,
            dosage=req.dosage,
            form=req.form,
            category=req.category,
            tags=req.tags,
            quantity=req.quantity,
            expiry=exp_date.isoformat(),
            status=req.status,
        )

    async def update_item(
        self, user_id: UUID, item_id: str, req: UpdateKitItemRequest
    ) -> KitItem:
        target_uuid = _to_uuid(item_id)
        updates: dict = {"updated_at": datetime.now(UTC)}

        if req.name is not None:
            updates["medicine_name"] = req.name
        if req.dosage is not None:
            updates["dosage"] = req.dosage
        if req.form is not None:
            updates["form"] = req.form
        if req.category is not None:
            updates["category"] = req.category
        if req.tags is not None:
            updates["tags"] = req.tags
        if req.quantity is not None:
            updates["quantity"] = req.quantity
        if req.status is not None:
            updates["status"] = req.status
        if req.expiry is not None:
            try:
                updates["expiry_date"] = date.fromisoformat(req.expiry)
            except ValueError:
                pass

        stmt = (
            update(user_kits)
            .where(user_kits.c.id == target_uuid, user_kits.c.user_id == user_id)
            .values(**updates)
            .returning(
                user_kits.c.id,
                user_kits.c.medicine_name,
                user_kits.c.dosage,
                user_kits.c.form,
                user_kits.c.category,
                user_kits.c.tags,
                user_kits.c.quantity,
                user_kits.c.expiry_date,
                user_kits.c.status,
            )
        )
        async with self._engine.begin() as conn:
            res = await conn.execute(stmt)
            r = res.first()

        if r is None:
            raise KitItemNotFoundError(item_id)

        exp_str = r.expiry_date.isoformat() if r.expiry_date else "2027-12-31"
        return KitItem.create(
            id=str(r.id),
            name=r.medicine_name,
            dosage=r.dosage,
            form=r.form,
            category=r.category,
            tags=r.tags if isinstance(r.tags, list) else [],
            quantity=r.quantity,
            expiry=exp_str,
            status=r.status,
        )

    async def delete_item(self, user_id: UUID, item_id: str) -> bool:
        target_uuid = _to_uuid(item_id)
        stmt = (
            delete(user_kits)
            .where(user_kits.c.id == target_uuid, user_kits.c.user_id == user_id)
            .returning(user_kits.c.id)
        )
        async with self._engine.begin() as conn:
            res = await conn.execute(stmt)
            return res.first() is not None
