"""PostgreSQL implementation of ProfileStore using SQLAlchemy 2.0 Core."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from medai.db.tables import health_profiles
from medai.profile.models import HealthProfile, UpdateHealthProfileRequest
from medai.profile.stores import ProfileStore

__all__ = ["PostgresProfileStore"]


class PostgresProfileStore(ProfileStore):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def get_profile(self, user_id: UUID) -> HealthProfile:
        stmt = select(
            health_profiles.c.age,
            health_profiles.c.weight_kg,
            health_profiles.c.chronic_diseases,
            health_profiles.c.allergies,
            health_profiles.c.special_notes,
        ).where(health_profiles.c.user_id == user_id)

        async with self._engine.connect() as conn:
            res = await conn.execute(stmt)
            r = res.first()

        if r is not None:
            return HealthProfile(
                age=r.age,
                weight_kg=r.weight_kg,
                chronic_diseases=(
                    r.chronic_diseases if isinstance(r.chronic_diseases, list) else []
                ),
                allergies=(
                    r.allergies if isinstance(r.allergies, list) else []
                ),
                special_notes=r.special_notes,
            )

        # Initialize default profile in database
        now = datetime.now(UTC)
        default_profile = HealthProfile()
        ins_stmt = insert(health_profiles).values(
            id=uuid4(),
            user_id=user_id,
            age=default_profile.age,
            weight_kg=default_profile.weight_kg,
            chronic_diseases=default_profile.chronic_diseases,
            allergies=default_profile.allergies,
            special_notes=default_profile.special_notes,
            created_at=now,
            updated_at=now,
        )
        async with self._engine.begin() as conn:
            await conn.execute(ins_stmt)

        return default_profile

    async def update_profile(
        self, user_id: UUID, req: UpdateHealthProfileRequest
    ) -> HealthProfile:
        # Ensure row exists
        await self.get_profile(user_id)

        updates: dict = {"updated_at": datetime.now(UTC)}
        if req.age is not None:
            updates["age"] = req.age
        if req.weight_kg is not None:
            updates["weight_kg"] = req.weight_kg
        if req.chronic_diseases is not None:
            updates["chronic_diseases"] = req.chronic_diseases
        if req.allergies is not None:
            updates["allergies"] = req.allergies
        if req.special_notes is not None:
            updates["special_notes"] = req.special_notes

        stmt = (
            update(health_profiles)
            .where(health_profiles.c.user_id == user_id)
            .values(**updates)
            .returning(
                health_profiles.c.age,
                health_profiles.c.weight_kg,
                health_profiles.c.chronic_diseases,
                health_profiles.c.allergies,
                health_profiles.c.special_notes,
            )
        )
        async with self._engine.begin() as conn:
            res = await conn.execute(stmt)
            r = res.one()

        return HealthProfile(
            age=r.age,
            weight_kg=r.weight_kg,
            chronic_diseases=(
                r.chronic_diseases if isinstance(r.chronic_diseases, list) else []
            ),
            allergies=(
                r.allergies if isinstance(r.allergies, list) else []
            ),
            special_notes=r.special_notes,
        )
