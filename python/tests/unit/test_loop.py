"""Unit tests for the Agent-driven event loop."""

from __future__ import annotations

import pytest
from agent_framework._middleware import FunctionInvocationContext
from agent_framework._tools import SKIP_PARSING, FunctionTool
from agent_framework._types import AgentResponseUpdate, Content, UsageDetails

from coding_agent.events import (
    TextDeltaEvent,
    ThinkingDeltaEvent,
    ToolCallStartEvent,
    ToolExecutionEndEvent,
    ToolExecutionStartEvent,
    UsageEvent,
)
from coding_agent.loop import ToolEventMiddleware, _extract_tool_result, _process_agent_update
from coding_agent.tools.coding_tools import _ToolResult


class TestProcessAgentUpdate:
    def test_text_delta(self) -> None:
        events: list[object] = []
        update = AgentResponseUpdate(contents=[Content(type="text", text="hello")])
        _process_agent_update(update, events.append, None)
        assert len(events) == 1
        assert isinstance(events[0], TextDeltaEvent)
        assert events[0].delta == "hello"

    def test_thinking_delta(self) -> None:
        events: list[object] = []
        update = AgentResponseUpdate(contents=[Content(type="thinking", text="thinking...")])  # type: ignore[arg-type]
        _process_agent_update(update, events.append, None)
        assert len(events) == 1
        assert isinstance(events[0], ThinkingDeltaEvent)
        assert events[0].delta == "thinking..."

    def test_usage_event(self) -> None:
        events: list[object] = []
        usage = UsageDetails(
            input_token_count=10,
            output_token_count=5,
            total_token_count=15,
        )
        update = AgentResponseUpdate(contents=[Content(type="usage", usage_details=usage)])
        _process_agent_update(update, events.append, None)
        assert len(events) == 1
        assert isinstance(events[0], UsageEvent)
        assert events[0].input_tokens == 10
        assert events[0].output_tokens == 5


class TestExtractToolResult:
    def test_tool_result_object(self) -> None:
        text, exit_code, ok = _extract_tool_result(_ToolResult(result="output", exit_code=1, ok=False))
        assert text == "output"
        assert exit_code == 1
        assert ok is False

    def test_plain_string(self) -> None:
        text, exit_code, ok = _extract_tool_result("plain result")
        assert text == "plain result"
        assert exit_code is None
        assert ok is True

    def test_content_list(self) -> None:
        text, exit_code, ok = _extract_tool_result([Content(type="text", text="content result")])
        assert text == "content result"
        assert exit_code is None
        assert ok is True

    def test_none_result(self) -> None:
        text, exit_code, ok = _extract_tool_result(None)
        assert text == ""
        assert exit_code is None
        assert ok is True


class TestToolEventMiddleware:
    @pytest.mark.asyncio
    async def test_emits_tool_events(self) -> None:
        events: list[object] = []
        middleware = ToolEventMiddleware(events.append)

        async def dummy_tool() -> str:
            return "result"

        tool = FunctionTool(name="dummy", description="", func=dummy_tool, result_parser=SKIP_PARSING)
        context = FunctionInvocationContext(
            function=tool,
            arguments={"x": 1},
            metadata={"call_id": "call-123"},
        )

        async def call_next() -> None:
            context.result = await tool.invoke(arguments={"x": 1})

        await middleware.process(context, call_next)

        assert len(events) == 3
        assert isinstance(events[0], ToolCallStartEvent)
        assert events[0].call_id == "call-123"
        assert events[0].name == "dummy"
        assert isinstance(events[1], ToolExecutionStartEvent)
        assert isinstance(events[2], ToolExecutionEndEvent)
        assert events[2].result == "result"
        assert events[2].ok is True

    @pytest.mark.asyncio
    async def test_emits_error_event_on_failure(self) -> None:
        events: list[object] = []
        middleware = ToolEventMiddleware(events.append)

        async def failing_tool() -> str:
            raise RuntimeError("boom")

        tool = FunctionTool(name="fail", description="", func=failing_tool, result_parser=SKIP_PARSING)
        context = FunctionInvocationContext(
            function=tool,
            arguments={},
            metadata={"call_id": "call-456"},
        )

        async def call_next() -> None:
            context.result = await tool.invoke(arguments={})

        with pytest.raises(RuntimeError, match="boom"):
            await middleware.process(context, call_next)

        assert any(isinstance(e, ToolExecutionEndEvent) and not e.ok for e in events)
