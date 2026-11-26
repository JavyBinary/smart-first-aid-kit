"""Voice narration API router (Silero TTS when installed, clean 503 fallback signal otherwise)."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict

from medai.auth.models import User
from medai.auth.router import get_current_user
from medai.dialogs.history import DialogNotFoundError
from medai.dialogs.service import DialogService

__all__ = ["create_speech_router"]

ALLOWED_VOICES = ("baya", "aidar", "kseniya", "xenia", "eugene")


class AudioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    voice: str = "baya"


def create_speech_router(dialog_service: DialogService) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["speech"])
    model_path = Path(os.getenv("SPEECH_MODEL_PATH", "/models/silero/v5_ru.pt"))
    speech_enabled = (
        os.getenv("SPEECH_ENABLED", "false").lower() in ("true", "1", "yes")
        and model_path.exists()
    )

    @router.post(
        "/dialogs/{dialog_id}/messages/{message_id}/audio",
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def request_audio(
        dialog_id: UUID,
        message_id: int,
        body: AudioRequest = AudioRequest(),
        user: User = Depends(get_current_user),
    ) -> Response:
        if body.voice not in ALLOWED_VOICES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unknown voice identifier",
            )
        try:
            transcript = await dialog_service.get_transcript(user.id, dialog_id)
        except DialogNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        if not any(m.id == message_id and m.role == "assistant" for m in transcript.messages):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

        if not speech_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Server Silero TTS model is not mounted; use client speech synthesis fallback.",
            )
        return Response(status_code=status.HTTP_202_ACCEPTED)

    return router
