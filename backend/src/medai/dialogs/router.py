"""FastAPI router for dialog management, SSE streaming, and chat queries."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from medai.auth.models import User
from medai.auth.router import get_current_user
from medai.dialogs.events import DialogEventType
from medai.dialogs.history import DialogNotFoundError
from medai.dialogs.service import DialogService

__all__ = ["create_dialogs_router"]


class StartDialogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dialog_id: UUID


class DialogSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dialog_id: UUID
    title: str
    created_at: str
    updated_at: str


class DialogListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dialogs: list[DialogSummaryResponse]


class DialogMessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: int
    position: int
    role: str
    content: str
    rag_payload: dict[str, Any] | None = None
    created_at: str


class DialogTranscriptResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dialog_id: UUID
    title: str
    messages: list[DialogMessageResponse]


class SubmitMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content: str = Field(min_length=1)


class ChatQueryRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    query: str = Field(min_length=1)
    include_kit_context: bool = True
    user_kit_names: list[str] = Field(default_factory=list)
    selected_pills: list[str] = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    medicine_name: str
    in_user_kit: bool
    dosage: str
    contraindications: str
    warnings: str


class ChatQueryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: str
    emergency_mode: bool
    message: str | None = None
    first_aid_steps: list[str] | None = None
    recommendation: RecommendationResponse | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)
    disclaimer: str


def _format_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat()


def create_dialogs_router(dialog_service: DialogService) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["dialogs"])

    @router.post(
        "/dialogs",
        status_code=status.HTTP_201_CREATED,
        response_model=StartDialogResponse,
    )
    async def start_dialog(
        response: Response,
        user: User = Depends(get_current_user),
    ) -> StartDialogResponse:
        dialog_id = await dialog_service.start_dialog(user.id)
        response.headers["Location"] = f"/api/v1/dialogs/{dialog_id}"
        return StartDialogResponse(dialog_id=dialog_id)

    @router.get("/dialogs", response_model=DialogListResponse)
    async def list_dialogs(
        user: User = Depends(get_current_user),
    ) -> DialogListResponse:
        dialogs = await dialog_service.list_dialogs(user.id)
        return DialogListResponse(
            dialogs=[
                DialogSummaryResponse(
                    dialog_id=d.dialog_id,
                    title=d.title,
                    created_at=_format_iso(d.created_at),
                    updated_at=_format_iso(d.updated_at),
                )
                for d in dialogs
            ]
        )

    @router.get(
        "/dialogs/{dialog_id}/messages",
        response_model=DialogTranscriptResponse,
    )
    async def get_dialog_messages(
        dialog_id: UUID,
        user: User = Depends(get_current_user),
    ) -> DialogTranscriptResponse:
        try:
            transcript = await dialog_service.get_transcript(user.id, dialog_id)
        except DialogNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dialog not found",
            )
        return DialogTranscriptResponse(
            dialog_id=transcript.dialog_id,
            title=transcript.title,
            messages=[
                DialogMessageResponse(
                    id=m.id,
                    position=m.position,
                    role=m.role,
                    content=m.content,
                    rag_payload=m.rag_payload,
                    created_at=_format_iso(m.created_at),
                )
                for m in transcript.messages
            ],
        )

    @router.delete(
        "/dialogs/{dialog_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    async def delete_dialog(
        dialog_id: UUID,
        user: User = Depends(get_current_user),
    ) -> Response:
        try:
            await dialog_service.delete_dialog(user.id, dialog_id)
        except DialogNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dialog not found",
            )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.post(
        "/dialogs/{dialog_id}/messages",
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def submit_message(
        dialog_id: UUID,
        body: SubmitMessageRequest,
        user: User = Depends(get_current_user),
    ) -> Response:
        try:
            await dialog_service.submit_message(
                owner_id=user.id,
                dialog_id=dialog_id,
                content=body.content,
            )
        except DialogNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dialog not found",
            )
        return Response(status_code=status.HTTP_202_ACCEPTED)

    @router.get("/dialogs/{dialog_id}/events")
    async def stream_dialog_events(
        dialog_id: UUID,
        user: User = Depends(get_current_user),
    ) -> StreamingResponse:
        try:
            subscription = await dialog_service.subscribe(user.id, dialog_id)
        except DialogNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dialog not found",
            )

        async def generate_events() -> AsyncIterator[str]:
            try:
                ready_payload = json.dumps({"dialog_id": str(dialog_id)})
                yield f"event: ready\ndata: {ready_payload}\n\n"

                while True:
                    try:
                        event = await asyncio.wait_for(
                            subscription.receive(), timeout=10.0
                        )
                    except TimeoutError:
                        yield ": keep-alive\n\n"
                        continue

                    if event is None:
                        break

                    data_json = json.dumps(
                        event.model_dump(exclude_none=True),
                        ensure_ascii=False,
                    )
                    yield f"event: {event.type.value}\ndata: {data_json}\n\n"

                    if event.type in (
                        DialogEventType.MESSAGE_END,
                        DialogEventType.MESSAGE_ERROR,
                    ):
                        break
            finally:
                await dialog_service.unsubscribe(subscription)

        return StreamingResponse(
            generate_events(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    @router.post("/chat/query", response_model=ChatQueryResponse)
    async def chat_query(body: ChatQueryRequest) -> ChatQueryResponse:
        kit_names = list(body.user_kit_names) + list(body.selected_pills)
        res = dialog_service.process_query_sync(
            query=body.query, user_kit_names=kit_names
        )
        return ChatQueryResponse.model_validate(res)

    return router
