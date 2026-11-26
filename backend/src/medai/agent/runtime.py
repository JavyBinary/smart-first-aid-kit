"""MedAI Agent runtime with bounded tool-calling loop and streaming events."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Sequence

from medai.agent.errors import AgentIterationLimitError, InvalidLLMResponseError
from medai.agent.models import (
    AgentConfig,
    AgentResponse,
    AgentTextDelta,
    LLMResponse,
    LLMResultType,
    LLMTextDelta,
    Message,
    MessageRole,
    ToolCall,
    ToolError,
    ToolResult,
    UserRequest,
)
from medai.agent.providers.base import LLMProvider
from medai.agent.tools import ToolRegistry
from medai.observability import log_event, utc_now

__all__ = ["Agent", "AgentStreamEvent"]

logger = logging.getLogger(__name__)
AgentStreamEvent = AgentTextDelta | AgentResponse


class Agent:
    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_registry: ToolRegistry,
        config: AgentConfig,
    ) -> None:
        self._llm_provider = llm_provider
        self._tool_registry = tool_registry
        self._config = config

    async def run(
        self,
        history: Sequence[Message],
        request: UserRequest,
    ) -> AsyncIterator[AgentStreamEvent]:
        started_at = utc_now()
        started = time.monotonic()
        depth_instruction = (
            "Формат ответа: краткий (brief), 4-6 емких строк с главными фактами и [Dxx]."
            if request.response_depth == "brief"
            else "Формат ответа: подробный (detailed), с показаниями, дозировкой, противопоказаниями и [Dxx]."
        )
        context: list[Message] = [
            Message(role=MessageRole.SYSTEM, content=self._config.system_prompt),
            Message(role=MessageRole.SYSTEM, content=depth_instruction),
            *history,
            Message(role=MessageRole.USER, content=request.content),
        ]

        log_event(
            logger,
            logging.INFO,
            "agent.run.started",
            history_size=len(history),
            max_iterations=self._config.max_iterations,
        )

        try:
            for iteration in range(1, self._config.max_iterations + 1):
                llm_response: LLMResponse | None = None
                content_parts: list[str] = []

                async for event in self._llm_provider.stream(
                    tuple(context),
                    self._tool_registry.definitions,
                ):
                    if isinstance(event, LLMTextDelta):
                        if llm_response is not None:
                            raise InvalidLLMResponseError("Text delta received after LLMResponse.")
                        content_parts.append(event.content)
                        yield AgentTextDelta(content=event.content)
                    elif isinstance(event, LLMResponse):
                        if llm_response is not None:
                            raise InvalidLLMResponseError("Multiple LLMResponse objects in one turn.")
                        llm_response = event

                if llm_response is None:
                    raise InvalidLLMResponseError("Missing final LLMResponse.")

                result_type = self._result_type(llm_response)
                if result_type is LLMResultType.INVALID:
                    raise InvalidLLMResponseError("LLMResponse contained neither text nor tool calls.")

                if result_type is LLMResultType.FINAL:
                    final_text = llm_response.content or "".join(content_parts)
                    log_event(
                        logger,
                        logging.INFO,
                        "agent.run.completed",
                        iterations=iteration,
                        started_at=started_at,
                        duration_ms=round((time.monotonic() - started) * 1000, 3),
                    )
                    yield AgentResponse(content=final_text, used_llm=True)
                    return

                context.append(
                    Message(
                        role=MessageRole.ASSISTANT,
                        tool_calls=llm_response.tool_calls,
                        reasoning_content=llm_response.reasoning_content,
                    )
                )

                limit = self._config.max_tool_calls_per_response
                for pos, tc in enumerate(llm_response.tool_calls):
                    res = await self._execute_tool_call(tc, allowed=pos < limit)
                    context.append(
                        Message(
                            role=MessageRole.TOOL,
                            tool_call_id=tc.id,
                            tool_name=tc.name,
                            tool_result=res,
                        )
                    )

            raise AgentIterationLimitError(
                "Agent reached iteration limit without producing a final answer."
            )
        except asyncio.CancelledError:
            log_event(logger, logging.INFO, "agent.run.cancelled", started_at=started_at)
            raise
        except Exception as err:
            log_event(
                logger,
                logging.ERROR,
                "agent.run.failed",
                error_type=type(err).__name__,
                started_at=started_at,
                duration_ms=round((time.monotonic() - started) * 1000, 3),
            )
            raise

    async def _execute_tool_call(
        self, tool_call: ToolCall, *, allowed: bool
    ) -> ToolResult:
        if not allowed:
            return ToolResult(
                call_id=tool_call.id,
                name=tool_call.name,
                error=ToolError(
                    code="tool_call_limit_exceeded",
                    message="Tool call limit exceeded for this iteration.",
                ),
            )
        return await self._tool_registry.execute(tool_call)

    @staticmethod
    def _result_type(response: LLMResponse) -> LLMResultType:
        if response.tool_calls and response.content:
            return LLMResultType.INVALID
        if response.tool_calls:
            return LLMResultType.TOOL_CALLS
        if response.content is not None:
            return LLMResultType.FINAL
        return LLMResultType.INVALID
