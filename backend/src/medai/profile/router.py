"""FastAPI router for user health profile (medical card)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from medai.auth.models import User
from medai.auth.router import get_current_user
from medai.profile.models import HealthProfile, UpdateHealthProfileRequest
from medai.profile.stores import ProfileStore

__all__ = ["create_profile_router"]


def create_profile_router(profile_store: ProfileStore) -> APIRouter:
    router = APIRouter(prefix="/api/v1/profile", tags=["profile"])

    @router.get("", response_model=HealthProfile)
    async def get_health_profile(
        user: User = Depends(get_current_user),
    ) -> HealthProfile:
        return await profile_store.get_profile(user.id)

    @router.put("", response_model=HealthProfile)
    async def update_health_profile(
        body: UpdateHealthProfileRequest,
        user: User = Depends(get_current_user),
    ) -> HealthProfile:
        return await profile_store.update_profile(user.id, body)

    return router
