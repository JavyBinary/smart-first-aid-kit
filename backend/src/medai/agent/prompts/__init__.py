"""Versioned prompt package loader."""

from __future__ import annotations

from importlib.resources import files

__all__ = ["load_system_prompt"]


def load_system_prompt() -> str:
    """Load the versioned production system prompt from package resources."""
    return files("medai.agent.prompts").joinpath("system.md").read_text(encoding="utf-8")
