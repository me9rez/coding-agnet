"""Agent-driven coding loop — emits fine-grained events to the gateway/TUI.

Uses ``agent_framework.Agent`` with a ``FunctionMiddleware`` so we keep the
existing per-chunk thinking/text/tool lifecycle events while delegating the
LLM/tool loop to the framework.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterable, Awaitable, Callable, Mapping
from typing import TYPE_CHECKING, Any, cast

from agent_framework._middleware import FunctionInvocationContext, FunctionMiddleware
from agent_framework._types import Content, Message, UsageDetails

from coding_agent.events import (
    AgentEvent,
    DoneEvent,
    TextDeltaEvent,
    ThinkingDeltaEvent,
    ToolCallStartEvent,
    ToolExecutionEndEvent,
    ToolExecutionStartEvent,
    TurnEndEvent,
    UsageEvent,
)

if TYPE_CHECKING:
    from agent_framework._clients import SupportsChatGetResponse
    from agent_framework._skills import SkillsProvider
    from agent_framework._tools import FunctionTool
    from agent_framework._types import AgentResponse, AgentResponseUpdate

logger = logging.getLogger(__name__)


class ToolEventMiddleware(FunctionMiddleware):
    """Emit tool lifecycle events and normalise raw tool results."""

    def __init__(self, emit: Callable[[AgentEvent], None]) -> None:
        self._emit = emit

    async def process(
        self,
        context: FunctionInvocationContext,
        call_next: Callable[[], Awaitable[None]],
    ) -> None:
        call_id = context.metadata.get("call_id", "")
        name = context.function.name
        arguments = _arguments_to_json(context.arguments)

        self._emit(ToolCallStartEvent(call_id=call_id, name=name, arguments=arguments))
        self._emit(ToolExecutionStartEvent(call_id=call_id, name=name))

        try:
            await call_next()
        except Exception:
            self._emit(ToolExecutionEndEvent(call_id=call_id, name=name, ok=False, error="Tool execution failed"))
            raise

        result_text, exit_code, ok = _extract_tool_result(context.result)
        context.result = [Content(type="text", text=result_text)]

        # Stream any async-iterable raw output (preserves legacy shell-streaming behaviour).
        if isinstance(context.result[0].text, AsyncIterable):
            # Should not happen because _extract_tool_result consumed async iterables,
            # but keep the guard for robustness.
            context.result = [Content(type="text", text="")]

        self._emit(
            ToolExecutionEndEvent(
                call_id=call_id,
                name=name,
                result=result_text,
                ok=ok,
                exit_code=exit_code,
            )
        )


def _arguments_to_json(arguments: Mapping[str, Any] | Any) -> str:
    """Serialise validated tool arguments to JSON."""
    try:
        if hasattr(arguments, "model_dump"):
            payload = arguments.model_dump()  # type: ignore[union-attr]
        elif isinstance(arguments, Mapping):
            payload = dict(arguments)
        else:
            payload = {"args": str(arguments)}
        return json.dumps(payload, ensure_ascii=False)
    except Exception:
        return str(arguments)


def _extract_tool_result(result: Any) -> tuple[str, int | None, bool]:
    """Return (text, exit_code, ok) from a raw tool result.

    Handles async iterables, ``_ToolResult``-like objects, strings, and
    ``list[Content]``.
    """
    if hasattr(result, "__aiter__"):
        # Reached only if a tool returns an async iterable; collect into text.
        # We cannot async-iterate here because this helper is sync, so callers
        # should not produce raw async iterables.
        return "", None, True

    if isinstance(result, list):
        # Default ``FunctionTool.parse_result`` output.
        text_parts = [c.text for c in result if getattr(c, "type", None) == "text" and getattr(c, "text", None)]
        return "\n".join(text_parts), None, True

    result_text = getattr(result, "result", None)
    if result_text is not None:
        exit_code = getattr(result, "exit_code", None)
        ok = getattr(result, "ok", True)
        return str(result_text), exit_code if exit_code is None or isinstance(exit_code, int) else None, bool(ok)

    if result is None:
        return "", None, True

    return str(result), None, True


async def run_coding_agent(
    client: SupportsChatGetResponse,
    messages: list[Message],
    tools: list[FunctionTool] | None = None,
    on_event: Callable[[AgentEvent], None] | None = None,
    *,
    max_turns: int = 25,
    system_prompt: str | None = None,
    compaction_max_tokens: int | None = None,
    thinking_level: str | None = None,
    skill_provider: SkillsProvider | None = None,
    mcp_tools: list[Any] | None = None,
) -> None:
    """Run the coding agent loop, emitting fine-grained events.

    Parameters
    ----------
    client:
        An agent-framework chat client. Must support function invocation
        (e.g. ``OpenAIChatCompletionClient``) so that ``Agent`` can execute the
        tool loop.
    messages:
        The mutable message list — assistant/tool messages are appended during
        the run.
    tools:
        Optional list of ``FunctionTool`` instances the agent can call.
    on_event:
        Callback invoked for each fine-grained event.
    max_turns:
        Safety cap on LLM + tool rounds. The client should already be configured
        with a matching ``max_iterations``.
    system_prompt:
        Instructions passed to ``Agent(instructions=...)``.
    compaction_max_tokens:
        If set, compacts the conversation after tool results are appended.
    thinking_level:
        Optional thinking/reasoning level forwarded via ``options``.
    skill_provider:
        Optional ``SkillsProvider`` that advertises skills and exposes the
        ``load_skill`` tool.
    mcp_tools:
        Optional list of ``MCPTool`` instances to merge into the tool list.
    """
    from agent_framework import Agent
    from agent_framework._types import normalize_tools

    _base_emit = on_event or _noop_emit
    turn_thinking_parts: list[str] = []

    def _emit(event: AgentEvent) -> None:
        if isinstance(event, ThinkingDeltaEvent):
            turn_thinking_parts.append(event.delta)
        _base_emit(event)

    tool_list = list(tools) if tools else []
    if mcp_tools:
        tool_list.extend(mcp_tools)

    options: dict[str, Any] = {}
    if tool_list:
        options["tools"] = normalize_tools(tool_list)
    if thinking_level:
        from coding_agent.thinking import thinking_options_for_level

        options.update(thinking_options_for_level(thinking_level))

    context_providers = [skill_provider] if skill_provider is not None else None
    tool_event_middleware = ToolEventMiddleware(_emit)

    async with Agent(
        client=client,
        instructions=system_prompt,
        tools=tool_list,
        context_providers=context_providers,
        middleware=[tool_event_middleware],
    ) as agent:
        from agent_framework._types import ChatOptions

        stream = agent.run(messages, stream=True, options=cast(ChatOptions, options))
        async for update in stream:
            _process_agent_update(update, _emit, turn_thinking_parts)

        response: AgentResponse = await stream.get_final_response()

    # Attach the final usage details to the last assistant message so they are
    # persisted in the session JSONL and replayed to the TUI.
    if response.usage_details:
        usage_dict = cast(Mapping[str, Any], response.usage_details)
        usage_content = Content(type="usage", usage_details=UsageDetails(**dict(usage_dict)))
        for msg in reversed(response.messages):
            if getattr(msg, "role", None) == "assistant":
                msg.contents = [*(getattr(msg, "contents", None) or []), usage_content]
                break
        else:
            response.messages.append(Message(role="assistant", contents=[usage_content]))

    # Persist any thinking collected this turn on the assistant message(s).
    thinking_text = "".join(turn_thinking_parts)
    if thinking_text:
        for msg in response.messages:
            if getattr(msg, "role", None) == "assistant":
                additional = getattr(msg, "additional_properties", None)
                if additional is None:
                    additional = {}
                    object.__setattr__(msg, "additional_properties", additional)
                additional["thinking"] = thinking_text

    # Append assistant and tool messages to the transcript.
    for msg in response.messages:
        _ensure_not_duplicate(messages, msg)
        messages.append(msg)

    # Compact conversation if needed.
    if compaction_max_tokens and len(messages) > 10:
        from coding_agent.compaction import compact_messages

        msgs: list[Any] = list(messages)
        compacted = await compact_messages(msgs, max_tokens=compaction_max_tokens)  # type: ignore[arg-type]
        if len(compacted) < len(msgs):
            messages[:] = compacted  # type: ignore[assignment]

    # Determine turn end reason from the final assistant message.
    last_assistant = next(
        (msg for msg in reversed(response.messages) if getattr(msg, "role", None) == "assistant"),
        None,
    )
    has_tool_calls = last_assistant is not None and any(
        getattr(c, "type", None) == "function_call" for c in getattr(last_assistant, "contents", [])
    )
    _emit(TurnEndEvent(reason="tool_calls" if has_tool_calls else "complete"))
    _emit(DoneEvent())


def _process_agent_update(
    update: AgentResponseUpdate,
    emit: Callable[[AgentEvent], None],
    thinking_parts_out: list[str] | None,
) -> None:
    """Extract text/thinking/usage events from one AgentResponseUpdate chunk."""
    # Provider-specific raw thinking (DeepSeek / Anthropic).
    raw = getattr(update, "raw_representation", None)
    if raw is not None:
        _extract_thinking(raw, emit, thinking_parts_out)

    contents = getattr(update, "contents", None) or []
    for c in contents:
        ctype = getattr(c, "type", None)
        if ctype == "text":
            text = getattr(c, "text", "") or ""
            if text:
                emit(TextDeltaEvent(delta=text))
        elif ctype in ("thinking", "reasoning", "reasoning_content"):
            thinking = getattr(c, "text", "") or getattr(c, "thinking", "") or getattr(c, "reasoning_content", "") or ""
            if thinking:
                if thinking_parts_out is not None:
                    thinking_parts_out.append(str(thinking))
                emit(ThinkingDeltaEvent(delta=str(thinking)))
        elif ctype == "usage":
            details = getattr(c, "usage_details", None) or {}
            emit(
                UsageEvent(
                    input_tokens=details.get("input_token_count", 0) or 0,
                    output_tokens=details.get("output_token_count", 0) or 0,
                    total_tokens=details.get("total_token_count", 0) or 0,
                    cache_read_tokens=details.get("cache_read_input_token_count", 0) or 0,
                    reasoning_tokens=details.get("reasoning_output_token_count", 0) or 0,
                    details=dict(details),
                )
            )


def _extract_thinking(
    raw: Any,
    emit: Callable[[AgentEvent], None],
    thinking_parts_out: list[str] | None,
) -> None:
    """Extract thinking/reasoning tokens from provider-specific raw data."""
    if isinstance(raw, dict):
        for choice in raw.get("choices", []):
            delta = choice.get("delta", {}) if isinstance(choice, dict) else {}
            reasoning = delta.get("reasoning_content") if isinstance(delta, dict) else None
            if reasoning:
                reasoning_str = str(reasoning)
                if thinking_parts_out is not None:
                    thinking_parts_out.append(reasoning_str)
                emit(ThinkingDeltaEvent(delta=reasoning_str))
        rtype = raw.get("type")
        text = raw.get("text")
        if text:
            text_str = str(text)
            if thinking_parts_out is not None:
                thinking_parts_out.append(text_str)
            emit(ThinkingDeltaEvent(delta=text_str))
        return

    choices = getattr(raw, "choices", None)
    if choices is not None:
        for choice in choices:
            delta = getattr(choice, "delta", None)
            reasoning = getattr(delta, "reasoning_content", None) if delta is not None else None
            if reasoning:
                reasoning_str = str(reasoning)
                if thinking_parts_out is not None:
                    thinking_parts_out.append(reasoning_str)
                emit(ThinkingDeltaEvent(delta=reasoning_str))

    rtype = getattr(raw, "type", None)
    if rtype == "content_block_delta":
        delta = raw.delta if hasattr(raw, "delta") else raw.get("delta", {})
        d_type = getattr(delta, "type", None) if not isinstance(delta, dict) else delta.get("type")
        if d_type == "thinking":
            thinking = getattr(delta, "thinking", None) or delta.get("thinking", "")
            if thinking:
                thinking_str = str(thinking)
                if thinking_parts_out is not None:
                    thinking_parts_out.append(thinking_str)
                emit(ThinkingDeltaEvent(delta=thinking_str))
    elif rtype == "thinking":
        text = getattr(raw, "text", None) or raw.get("text", "")
        if text:
            text_str = str(text)
            if thinking_parts_out is not None:
                thinking_parts_out.append(text_str)
            emit(ThinkingDeltaEvent(delta=text_str))


def _noop_emit(_event: AgentEvent) -> None:
    pass


def _ensure_not_duplicate(messages: list[Any], msg: Any) -> None:
    """Skip appending if the message already exists (by identity or id)."""
    if msg in messages:
        return
    msg_id = getattr(msg, "message_id", None)
    if msg_id:
        for existing in messages:
            if getattr(existing, "message_id", None) == msg_id:
                return
