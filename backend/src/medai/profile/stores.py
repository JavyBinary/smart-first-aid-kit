"""Health profile store abstraction and in-memory test store."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from medai.profile.models import HealthProfile, UpdateHealthProfileRequest

__all__ = ["InMemoryProfileStore", "ProfileStore"]


class ProfileStore(ABC):
    @abstractmethod
    async def get_profile(self, user_id: UUID) -> HealthProfile:
        """Get or initialize health profile for user."""

    @abstractmethod
    async def update_profile(
        self, user_id: UUID, req: UpdateHealthProfileRequest
    ) -> HealthProfile:
        """Update health profile for user."""


class InMemoryProfileStore(ProfileStore):
    def __init__(self) -> None:
        self._profiles: dict[UUID, HealthProfile] = {}

    async def get_profile(self, user_id: UUID) -> HealthProfile:
        profile = self._profiles.get(user_id)
        if profile is None:
            profile = HealthProfile()
            self._profiles[user_id] = profile
        return profile

    async def update_profile(
        self, user_id: UUID, req: UpdateHealthProfileRequest
    ) -> HealthProfile:
        current = await self.get_profile(user_id)
        updated = HealthProfile(
            age=req.age if req.age is not None else current.age,
            weight_kg=req.weight_kg if req.weight_kg is not None else current.weight_kg,
            chronic_diseases=(
                req.chronic_diseases
                if req.chronic_diseases is not None
                else current.chronic_diseases
            ),
            allergies=(
                req.allergies if req.allergies is not None else current.allergies
            ),
            special_notes=(
                req.special_notes
                if req.special_notes is not None
                else current.special_notes
            ),
        )
        self._profiles[user_id] = updated
        return updated
