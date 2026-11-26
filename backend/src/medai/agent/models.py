"""Immutable Pydantic v2 domain models for MedAI Agent runtime."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "AgentConfig",
    "AgentResponse",
    "AgentTextDelta",
    "LLMResponse",
    "LLMResultType",
    "LLMTextDelta",
    "Message",
    "MessageRole",
    "ToolCall",
    "ToolDefinition",
    "ToolError",
    "ToolResult",
    "UserRequest",
]


class MessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class LLMResultType(StrEnum):
    FINAL = "final"
    TOOL_CALLS = "tool_calls"
    INVALID = "invalid"


class ToolDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    description: str
    parameters: dict[str, Any]


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    message: str


class ToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    call_id: str
    name: str
    output: Any = None
    error: ToolError | None = None


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    role: MessageRole
    content: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_result: ToolResult | None = None
    reasoning_content: str | None = None


class LLMTextDelta(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content: str


class LLMResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    reasoning_content: str | None = None
    usage: dict[str, int] | None = None


class AgentTextDelta(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content: str


class AgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    recommendation: dict[str, Any] | None = None
    safety_warnings: list[str] = Field(default_factory=list)
    used_llm: bool = False


class AgentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    system_prompt: str
    max_iterations: int = Field(default=4, ge=1, le=10)
    max_tool_calls_per_response: int = Field(default=4, ge=1, le=10)


class UserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content: str = Field(min_length=1)
    response_depth: Literal["brief", "detailed"] = "detailed"
    selected_pills: list[str] = Field(default_factory=list)
    user_kit_names: list[str] = Field(default_factory=list)
    health_profile: dict[str, Any] | None = None
