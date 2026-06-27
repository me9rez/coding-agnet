"""Thinking level control — reasoning effort per provider."""

from __future__ import annotations

from typing import Literal

ThinkingLevel = Literal["off", "low", "medium", "high", "max"]

THINKING_LEVELS: tuple[ThinkingLevel, ...] = ("off", "low", "medium", "high", "max")
DEFAULT_THINKING_LEVEL: ThinkingLevel = "max"


def normalize_thinking_level(value: str | None) -> ThinkingLevel:
    if value is None:
        return DEFAULT_THINKING_LEVEL
    normalized = value.strip().lower()
    if normalized in THINKING_LEVELS:
        return normalized  # type: ignore[return-value]
    raise ValueError(f"Unknown thinking level: {value}. Options: {', '.join(THINKING_LEVELS)}")


def reasoning_effort_for_level(level: str | None) -> str | None:
    normalized = normalize_thinking_level(level)
    if normalized == "off":
        return None
    return normalized


def thinking_options_for_level(level: str | None) -> dict:
    """Return provider options dict for the given thinking level.

    For DeepSeek / OpenAI chat completions, this maps to
    ``reasoning_effort`` in the per-request options.
    """
    effort = reasoning_effort_for_level(level)
    if effort is None:
        return {}
    return {"reasoning_effort": effort}
