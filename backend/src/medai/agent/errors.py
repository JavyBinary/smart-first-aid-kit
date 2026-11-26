"""Domain exceptions for MedAI Agent runtime and LLM providers."""

from __future__ import annotations

__all__ = [
    "AgentError",
    "AgentIterationLimitError",
    "DuplicateToolError",
    "InvalidLLMResponseError",
    "LLMProviderError",
]


class AgentError(Exception):
    """Base error for agent execution."""


class DuplicateToolError(AgentError):
    """Raised when registering two tools with the same name."""


class LLMProviderError(AgentError):
    """Safe provider error hiding API keys and upstream exception details."""


class InvalidLLMResponseError(AgentError):
    """Raised when LLM returns malformed tool calls or inconsistent chunks."""


class AgentIterationLimitError(AgentError):
    """Raised when the agent exceeds max tool-calling iterations."""
