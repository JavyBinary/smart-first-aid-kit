"""Production async streaming LLM adapter using LiteLLM."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import litellm as litellm_sdk

from medai.agent.errors import LLMProviderError
from medai.agent.models import (
    LLMResponse,
    LLMTextDelta,
    Message,
    MessageRole,
    ToolCall,
    ToolDefinition,
)
from medai.agent.providers.base import LLMProvider, LLMStreamEvent
from medai.config import LiteLLMProviderConfig
from medai.observability import bind_context, log_event, utc_now

__all__ = ["LiteLLMProvider"]

logger = logging.getLogger(__name__)


@dataclass
class _ToolCallParts:
    id: str = ""
    name: str = ""
    arguments: str = ""


def _build_tool_calls(parts_by_index: dict[int, _ToolCallParts]) -> tuple[ToolCall, ...]:
    tool_calls: list[ToolCall] = []
    for index in sorted(parts_by_index):
        parts = parts_by_index[index]
        if not parts.id.strip() or not parts.name.strip():
            raise TypeError("Tool call must have an id and name.")
        arguments = json.loads(parts.arguments or "{}")
        if not isinstance(arguments, dict):
            raise TypeError("Tool call arguments must be a JSON object.")
        tool_calls.append(ToolCall(id=parts.id, name=parts.name, arguments=arguments))
    return tuple(tool_calls)


class LiteLLMProvider(LLMProvider):
    """Streaming LiteLLM adapter with observability and secret-safe error mapping."""

    def __init__(self, config: LiteLLMProviderConfig) -> None:
        self._config = config

    @property
    def is_configured(self) -> bool:
        model = (self._config.model or "").strip()
        if not model:
            return False
        # Require API key unless targeting a local endpoint via base_url (e.g. Ollama/vLLM)
        has_key = bool((self._config.api_key or "").strip())
        has_local_base = bool((self._config.base_url or "").strip())
        return has_key or has_local_base

    def _build_request(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolDefinition],
        max_tokens: int | None,
    ) -> dict[str, Any]:
        formatted_msgs: list[dict[str, Any]] = []
        for m in messages:
            if m.role is MessageRole.TOOL:
                payload = (
                    m.tool_result.output
                    if m.tool_result and m.tool_result.error is None
                    else {
                        "error": (
                            m.tool_result.error.model_dump()
                            if m.tool_result and m.tool_result.error
                            else "tool_error"
                        )
                    }
                )
                formatted_msgs.append(
                    {
                        "role": "tool",
                        "tool_call_id": m.tool_call_id,
                        "name": m.tool_name,
                        "content": json.dumps(payload, ensure_ascii=False),
                    }
                )
            elif m.role is MessageRole.ASSISTANT and m.tool_calls:
                msg_dict: dict[str, Any] = {
                    "role": "assistant",
                    "content": m.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                            },
                        }
                        for tc in m.tool_calls
                    ],
                }
                if m.reasoning_content:
                    msg_dict["reasoning_content"] = m.reasoning_content
                formatted_msgs.append(msg_dict)
            else:
                formatted_msgs.append({"role": m.role.value, "content": m.content or ""})

        req: dict[str, Any] = {
            "model": self._config.model,
            "messages": formatted_msgs,
            "stream": True,
            "timeout": self._config.timeout_seconds,
            "num_retries": self._config.num_retries,
            "temperature": self._config.temperature,
        }
        if self._config.api_key:
            req["api_key"] = self._config.api_key
        if self._config.base_url:
            req["api_base"] = self._config.base_url
        if tools:
            req["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]
        if max_tokens is not None:
            req["max_tokens"] = max_tokens + (3000 if self._config.thinking else 0)
        return req

    async def stream(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolDefinition],
        max_tokens: int | None = None,
    ) -> AsyncIterator[LLMStreamEvent]:
        started_at = utc_now()
        started = time.monotonic()
        call_id = str(uuid4())
        first_token_ms: float | None = None
        usage: dict[str, int] | None = None

        with bind_context(call_id=call_id):
            log_event(
                logger,
                logging.INFO,
                "llm.request.started",
                model=self._config.model,
                message_count=len(messages),
                tool_count=len(tools),
            )
            try:
                request = self._build_request(messages, tools, max_tokens)
                response_stream = await litellm_sdk.acompletion(**request)

                content_parts: list[str] = []
                reasoning_parts: list[str] = []
                tool_call_parts: dict[int, _ToolCallParts] = {}
                saw_choice = False

                async for chunk in response_stream:
                    chunk_usage = getattr(chunk, "usage", None)
                    if chunk_usage is not None:
                        usage = {
                            "input_tokens": int(getattr(chunk_usage, "prompt_tokens", 0) or 0),
                            "output_tokens": int(
                                getattr(chunk_usage, "completion_tokens", 0) or 0
                            ),
                            "total_tokens": int(getattr(chunk_usage, "total_tokens", 0) or 0),
                        }
                    choices = getattr(chunk, "choices", None)
                    if not choices:
                        continue
                    saw_choice = True
                    delta = choices[0].delta
                    content = getattr(delta, "content", None)
                    external_tool_calls = getattr(delta, "tool_calls", None) or ()
                    reasoning = getattr(delta, "reasoning_content", None)

                    if reasoning:
                        reasoning_parts.append(reasoning)

                    if content:
                        if first_token_ms is None:
                            first_token_ms = round((time.monotonic() - started) * 1000, 3)
                        content_parts.append(content)
                        yield LLMTextDelta(content=content)

                    for ext_call in external_tool_calls:
                        index = ext_call.index
                        parts = tool_call_parts.setdefault(index, _ToolCallParts())
                        if ext_call.id is not None:
                            parts.id += ext_call.id
                        func = ext_call.function
                        if func.name is not None:
                            parts.name += func.name
                        if func.arguments is not None:
                            parts.arguments += func.arguments

                if not saw_choice:
                    raise TypeError("LLM stream returned zero choices.")

                if tool_call_parts:
                    result = LLMResponse(
                        tool_calls=_build_tool_calls(tool_call_parts),
                        reasoning_content="".join(reasoning_parts) or None,
                        usage=usage,
                    )
                else:
                    result = LLMResponse(
                        content="".join(content_parts),
                        usage=usage,
                    )
            except asyncio.CancelledError:
                log_event(
                    logger,
                    logging.INFO,
                    "llm.request.cancelled",
                    model=self._config.model,
                    started_at=started_at,
                    duration_ms=round((time.monotonic() - started) * 1000, 3),
                )
                raise
            except Exception as error:
                log_event(
                    logger,
                    logging.ERROR,
                    "llm.request.failed",
                    model=self._config.model,
                    error_type=type(error).__name__,
                    started_at=started_at,
                    duration_ms=round((time.monotonic() - started) * 1000, 3),
                )
                raise LLMProviderError("LLM provider request failed.") from error

            log_event(
                logger,
                logging.INFO,
                "llm.request.completed",
                model=self._config.model,
                started_at=started_at,
                duration_ms=round((time.monotonic() - started) * 1000, 3),
                time_to_first_token_ms=first_token_ms,
                total_tokens=usage["total_tokens"] if usage else None,
            )
            yield result
