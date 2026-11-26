"""Abstract LLM provider contract and FakeLLMProvider for tests."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence

from medai.agent.models import (
    LLMResponse,
    LLMTextDelta,
    Message,
    ToolDefinition,
)

__all__ = ["FakeLLMProvider", "LLMProvider", "LLMStreamEvent"]

LLMStreamEvent = LLMTextDelta | LLMResponse


class LLMProvider(ABC):
    @abstractmethod
    async def stream(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolDefinition],
        max_tokens: int | None = None,
    ) -> AsyncIterator[LLMStreamEvent]:
        """Stream LLM text deltas followed by one final LLMResponse."""
        if False:
            yield LLMResponse()


class FakeLLMProvider(LLMProvider):
    """Deterministic fake provider for offline tests."""

    def __init__(self, script: Sequence[Sequence[LLMStreamEvent]] | None = None) -> None:
        self._script = list(script) if script else []
        self._cursor = 0

    async def stream(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolDefinition],
        max_tokens: int | None = None,
    ) -> AsyncIterator[LLMStreamEvent]:
        if self._cursor < len(self._script):
            events = self._script[self._cursor]
            self._cursor += 1
            for ev in events:
                yield ev
            return
        yield LLMResponse(content="")
