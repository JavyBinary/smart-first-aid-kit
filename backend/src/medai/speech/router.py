"""Voice narration API router (neural multi-voice edge-tts MP3 + 503 fallback signal when disabled)."""

from __future__ import annotations

import os
import re
from collections import OrderedDict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field

from medai.auth.models import User
from medai.auth.router import get_current_user
from medai.dialogs.history import DialogNotFoundError
from medai.dialogs.service import DialogService

__all__ = ["ALLOWED_VOICES", "VOICE_PROFILES", "create_speech_router"]

ALLOWED_VOICES = ("baya", "aidar", "kseniya", "xenia", "eugene")

# Каждому голосу задан отдельный нейросетный диктор (жен./муж.) и тембр (pitch/rate)
VOICE_PROFILES: dict[str, tuple[str, str, str]] = {
    "baya": ("ru-RU-SvetlanaNeural", "+0%", "+0Hz"),
    "kseniya": ("ru-RU-SvetlanaNeural", "+6%", "+22Hz"),
    "xenia": ("ru-RU-SvetlanaNeural", "-6%", "-18Hz"),
    "aidar": ("ru-RU-DmitryNeural", "+0%", "+0Hz"),
    "eugene": ("ru-RU-DmitryNeural", "-6%", "-22Hz"),
}


class AudioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    voice: str = "baya"


class SynthesizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(min_length=1, max_length=12000)
    voice: str = "baya"


def _clean_for_tts(raw_text: str) -> str:
    cleaned = re.sub(r"\[D\d{2,3}\]", "", raw_text)
    cleaned = re.sub(r"[*#_`~>|]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:4000]


async def _render_mp3(text: str, voice_id: str) -> bytes:
    import asyncio

    import edge_tts

    clean_text = _clean_for_tts(text)
    if not clean_text:
        clean_text = "Рекомендация сформирована."
    neural_voice, rate, pitch = VOICE_PROFILES[voice_id]
    kwargs: dict[str, str] = {}
    if rate != "+0%":
        kwargs["rate"] = rate
    if pitch != "+0Hz":
        kwargs["pitch"] = pitch

    last_err: Exception | None = None
    for attempt in range(2):
        try:
            comm = edge_tts.Communicate(clean_text, voice=neural_voice, **kwargs)
            chunks: list[bytes] = []
            async for chunk in comm.stream():
                if chunk.get("type") == "audio":
                    chunks.append(bytes(chunk["data"]))
            audio = b"".join(chunks)
            if audio:
                return audio
        except Exception as err:
            last_err = err
        if attempt == 0:
            await asyncio.sleep(0.35)

    raise RuntimeError("Empty audio stream returned by TTS engine") from last_err


def create_speech_router(dialog_service: DialogService) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["speech"])
    speech_enabled = os.getenv("SPEECH_ENABLED", "false").lower() in ("true", "1", "yes")
    audio_cache: OrderedDict[tuple[str, int, str], bytes] = OrderedDict()
    max_cache_items = 64

    def _cache_put(key: tuple[str, int, str], data: bytes) -> None:
        audio_cache[key] = data
        audio_cache.move_to_end(key)
        while len(audio_cache) > max_cache_items:
            audio_cache.popitem(last=False)

    @router.post("/speech/synthesize")
    async def synthesize_stateless(body: SynthesizeRequest) -> Response:
        if body.voice not in ALLOWED_VOICES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unknown voice identifier",
            )
        if not speech_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Server TTS disabled; use browser synthesis fallback.",
            )
        try:
            mp3_bytes = await _render_mp3(body.text, body.voice)
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"TTS synthesis unavailable: {type(err).__name__}",
            ) from err
        return Response(content=mp3_bytes, media_type="audio/mpeg")

    @router.post(
        "/dialogs/{dialog_id}/messages/{message_id}/audio",
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def request_audio(
        dialog_id: UUID,
        message_id: int,
        body: AudioRequest = AudioRequest(),
        user: User = Depends(get_current_user),
    ) -> dict[str, str]:
        if body.voice not in ALLOWED_VOICES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unknown voice identifier",
            )
        try:
            transcript = await dialog_service.get_transcript(user.id, dialog_id)
        except DialogNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        target_msg = next(
            (m for m in transcript.messages if m.id == message_id and m.role == "assistant"),
            None,
        )
        if target_msg is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

        if not speech_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Server TTS disabled; use client speech synthesis fallback.",
            )

        cache_key = (str(dialog_id), message_id, body.voice)
        if cache_key not in audio_cache:
            try:
                mp3_bytes = await _render_mp3(target_msg.content, body.voice)
                _cache_put(cache_key, mp3_bytes)
            except Exception as err:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"TTS synthesis unavailable: {type(err).__name__}",
                ) from err

        return {
            "status": "ready",
            "voice": body.voice,
            "audio_url": f"/api/v1/dialogs/{dialog_id}/messages/{message_id}/audio?voice={body.voice}",
        }

    @router.get("/dialogs/{dialog_id}/messages/{message_id}/audio")
    async def get_audio(
        dialog_id: UUID,
        message_id: int,
        voice: str = Query("baya"),
        user: User = Depends(get_current_user),
    ) -> Response:
        if voice not in ALLOWED_VOICES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unknown voice identifier",
            )
        if not speech_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Server TTS disabled",
            )
        try:
            transcript = await dialog_service.get_transcript(user.id, dialog_id)
        except DialogNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        target_msg = next(
            (m for m in transcript.messages if m.id == message_id and m.role == "assistant"),
            None,
        )
        if target_msg is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

        cache_key = (str(dialog_id), message_id, voice)
        mp3_bytes = audio_cache.get(cache_key)
        if mp3_bytes is None:
            mp3_bytes = await _render_mp3(target_msg.content, voice)
            _cache_put(cache_key, mp3_bytes)
        return Response(content=mp3_bytes, media_type="audio/mpeg")

    return router
