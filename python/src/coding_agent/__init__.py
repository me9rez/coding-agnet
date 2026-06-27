"""Coding Agent — fine-grained agent loop + gateway for Vue TUI."""

from coding_agent.events import (
    AgentEvent,
    DoneEvent,
    ErrorEvent,
    TextDeltaEvent,
    ThinkingDeltaEvent,
    ToolCallStartEvent,
    ToolExecutionDeltaEvent,
    ToolExecutionEndEvent,
    ToolExecutionStartEvent,
    TurnEndEvent,
)
from coding_agent.loop import run_coding_agent

__all__ = [
    "AgentEvent",
    "DoneEvent",
    "ErrorEvent",
    "TextDeltaEvent",
    "ThinkingDeltaEvent",
    "ToolCallStartEvent",
    "ToolExecutionDeltaEvent",
    "ToolExecutionEndEvent",
    "ToolExecutionStartEvent",
    "TurnEndEvent",
    "run_coding_agent",
]
