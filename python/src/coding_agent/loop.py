"""Custom agent loop — emits fine-grained events to the gateway/TUI.

Uses ``BaseChatClient.get_response(stream=True)`` directly (without
``FunctionInvocationLayer``) so we can emit per-chunk thinking, text,
tool call lifecycle events that the TUI renders in real time.

Agent-framework building blocks used:
    - ``SupportsChatGetResponse`` / ``BaseChatClient`` — streaming model calls
    - ``FunctionTool`` — tool definition, schema, and execution
    - ``Message``, ``Content``, ``ChatResponseUpdate`` — core types
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from agent_framework._types import Content, Message, UsageDetails

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
    UsageEvent,
)

if TYPE_CHECKING:
    from agent_framework._clients import SupportsChatGetResponse
    from agent_framework._tools import FunctionTool
    from agent_framework._types import ChatResponse

logger = logging.getLogger(__name__)


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
) -> None:
    """Run the coding agent loop, emitting fine-grained events.

    Parameters
    ----------
    client:
        An agent-framework ``BaseChatClient`` (e.g. ``RawOpenAIChatClient``
        or ``OpenAIChatClient``).  If a client with ``FunctionInvocationLayer``
        is passed, tool calls will be handled twice; prefer a raw client.
    messages:
        The mutable message list — new messages (assistant responses, tool
        results) are appended during the run.
    tools:
        Optional list of ``FunctionTool`` instances the agent can call.
    on_event:
        Callback invoked for each fine-grained event.
    max_turns:
        Safety cap on LLM + tool rounds.
    """
    _base_emit = on_event or _noop_emit
    turn_thinking_parts: list[str] = []

    def _emit(event: AgentEvent) -> None:
        if isinstance(event, ThinkingDeltaEvent):
            turn_thinking_parts.append(event.delta)
        _base_emit(event)

    tool_list = list(tools) if tools else []
    tool_map: dict[str, FunctionTool] = {t.name: t for t in tool_list}
    options: dict[str, Any] = {}
    if tool_list:
        from agent_framework._types import normalize_tools

        options["tools"] = normalize_tools(tool_list)
    # Thinking level → provider options
    if thinking_level:
        from coding_agent.thinking import thinking_options_for_level

        options.update(thinking_options_for_level(thinking_level))

    turn = 0

    while turn < max_turns:
        turn += 1
        logger.debug("Turn %d/%d", turn, max_turns)
        turn_thinking_parts.clear()
        turn_usage_details: list[dict[str, Any]] = []

        # ── 1. Call LLM with streaming ──────────────────────────────
        stream_result = client.get_response(
            messages,
            stream=True,
            options=options,  # type: ignore[arg-type]
        )
        # stream_result is a ResponseStream — await to initialise, then iterate
        if hasattr(stream_result, "__await__"):
            stream = await stream_result
        else:
            stream = stream_result

        async for update in stream:
            _process_update(update, _emit, turn_usage_details)

        # ── 2. Get final response ────────────────────────────────────
        response: ChatResponse = await stream.get_final_response()

        # Attach the full usage details to the assistant message so they are
        # persisted in the session JSONL and replayed to the TUI.
        if turn_usage_details:
            usage_content = Content(type="usage", usage_details=UsageDetails(**turn_usage_details[-1]))
            for msg in reversed(response.messages):
                if getattr(msg, "role", None) == "assistant":
                    msg.contents = [*(getattr(msg, "contents", None) or []), usage_content]
                    break
            else:
                response.messages.append(Message(role="assistant", contents=[usage_content]))

        # Collect thinking from content blocks (e.g., Claude) in addition to streamed deltas.
        content_thinking_parts: list[str] = []
        for msg in response.messages:
            if getattr(msg, "role", None) != "assistant":
                continue
            for c in getattr(msg, "contents", None) or []:
                ctype = getattr(c, "type", None)
                if ctype in ("thinking", "reasoning", "text_reasoning"):
                    text = getattr(c, "text", None) or getattr(c, "thinking", None) or ""
                    if text:
                        content_thinking_parts.append(str(text))

        # Prefer streamed deltas; fall back to content-block thinking to avoid duplication.
        thinking_text = "".join(turn_thinking_parts)
        if not thinking_text:
            thinking_text = "".join(content_thinking_parts)

        # Persist any thinking collected this turn on the assistant message(s)
        if thinking_text:
            for msg in response.messages:
                if getattr(msg, "role", None) == "assistant":
                    additional = getattr(msg, "additional_properties", None)
                    if additional is None:
                        additional = {}
                        object.__setattr__(msg, "additional_properties", additional)
                    additional["thinking"] = thinking_text

        # Append assistant message(s) to the transcript
        for msg in response.messages:
            _ensure_not_duplicate(messages, msg)
            messages.append(msg)

        # ── 3. Extract tool calls from the final response ────────────
        pending_calls = _extract_tool_calls(response)
        logger.info("Extracted %d tool call(s): %s", len(pending_calls), _tool_call_preview(pending_calls))

        if not pending_calls:
            _emit(TurnEndEvent(reason="complete"))
            _emit(DoneEvent())
            return

        # ── 3b. Compact conversation if needed ───────────────────────
        if compaction_max_tokens and len(messages) > 10:
            from coding_agent.compaction import compact_messages

            msgs = messages[:]
            compacted = await compact_messages(msgs, max_tokens=compaction_max_tokens)  # type: ignore[arg-type]
            if len(compacted) < len(msgs):
                messages[:] = compacted  # type: ignore[assignment]

        # ── 4. Execute tool calls ────────────────────────────────────
        _emit(TurnEndEvent(reason="tool_calls"))

        tool_results: list[Message] = []
        for tc in pending_calls:
            call_id = tc.call_id or ""
            name = tc.name or ""
            raw_args = tc.arguments or "{}"
            if isinstance(raw_args, str):
                try:
                    parsed = json.loads(raw_args)
                except json.JSONDecodeError:
                    parsed = {}
            else:
                parsed = raw_args
            _emit(ToolCallStartEvent(call_id=call_id, name=name, arguments=json.dumps(parsed)))
            _emit(ToolExecutionStartEvent(call_id=call_id, name=name))
            tool = tool_map.get(name)
            if tool is None:
                _emit(ToolExecutionEndEvent(call_id=call_id, name=name, ok=False, error=f"Unknown tool: {name}"))
                tool_results.append(_tool_result_message(call_id, name, f"Error: unknown tool '{name}'", ok=False))
                continue

            try:
                logger.info("→ tool %s(%s)", name, json.dumps(parsed)[:200])
                result = await tool.invoke(arguments=parsed, skip_parsing=True)

                # Streaming output from tool (e.g. shell stdout lines)
                if hasattr(result, "__aiter__"):
                    async for line in result:  # type: ignore[union-attr]
                        _emit(ToolExecutionDeltaEvent(call_id=call_id, line=str(line)))

                result_text = ""
                if hasattr(result, "type") and hasattr(result, "result"):
                    result_text = result.result or str(result)  # type: ignore[union-attr]
                else:
                    result_text = str(result) if result is not None else ""
                exit_code = getattr(result, "exit_code", None)
                ok = getattr(result, "ok", True) if not isinstance(result, str) else True

                logger.info("← tool %s: exit_code=%s, ok=%s, result_len=%d", name, exit_code, ok, len(result_text))
                _emit(ToolExecutionEndEvent(call_id=call_id, name=name, result=result_text, ok=ok, exit_code=exit_code))
                tool_results.append(_tool_result_message(call_id, name, result_text, ok=ok))

            except Exception as exc:
                logger.exception("Tool %s failed", name)
                _emit(ToolExecutionEndEvent(call_id=call_id, name=name, ok=False, error=str(exc)))
                tool_results.append(_tool_result_message(call_id, name, f"Error: {exc}", ok=False))

        # Append tool results to transcript
        messages.extend(tool_results)

    # ── 5. Max turns exhausted ──────────────────────────────────────
    _emit(ErrorEvent(message=f"Max turns ({max_turns}) reached", recoverable=False))
    _emit(TurnEndEvent(reason="complete"))
    _emit(DoneEvent())


# ── Helpers ──────────────────────────────────────────────────────


def _tool_call_preview(calls: list[Any]) -> list[tuple[str, str]]:
    """Return (name, truncated_args) for logging."""
    result: list[tuple[str, str]] = []
    for c in calls:
        args = (c.arguments or "{}")[:120]
        result.append((c.name or "", args))
    return result


def _noop_emit(_event: AgentEvent) -> None:
    pass


def _process_update(
    update: Any,
    emit: Callable[[AgentEvent], None],
    usage_details_out: list[dict[str, Any]] | None = None,
) -> None:
    """Extract text/thinking/usage events from one ChatResponseUpdate chunk."""
    # 1. Check raw_representation for thinking deltas (Anthropic / DeepSeek)
    raw = getattr(update, "raw_representation", None)
    if raw is not None:
        _extract_thinking(raw, emit)

    # 2. Check contents for text, reasoning and usage
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
                emit(ThinkingDeltaEvent(delta=thinking))
        elif ctype == "usage":
            details = getattr(c, "usage_details", None) or {}
            if usage_details_out is not None:
                usage_details_out.append(dict(details))
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


def _extract_tool_calls(response: ChatResponse) -> list[Content]:
    """Extract tool call content items from the final response messages."""
    calls: list[Content] = []
    for msg in response.messages:
        for c in msg.contents:
            if c.type == "function_call":
                calls.append(c)
    return calls


def _extract_thinking(raw: Any, emit: Callable[[AgentEvent], None]) -> None:
    """Extract thinking/reasoning tokens from provider-specific raw data."""
    if isinstance(raw, dict):
        # DeepSeek / OpenAI-style raw chunk: choices[0].delta.reasoning_content
        for choice in raw.get("choices", []):
            delta = choice.get("delta", {}) if isinstance(choice, dict) else {}
            reasoning = delta.get("reasoning_content") if isinstance(delta, dict) else None
            if reasoning:
                emit(ThinkingDeltaEvent(delta=str(reasoning)))
        rtype = raw.get("type")
        text = raw.get("text")
        if text:
            emit(ThinkingDeltaEvent(delta=str(text)))
        return

    # Handle Pydantic/ChatCompletionChunk-like objects (e.g. from agent-framework)
    choices = getattr(raw, "choices", None)
    if choices is not None:
        for choice in choices:
            delta = getattr(choice, "delta", None)
            reasoning = getattr(delta, "reasoning_content", None) if delta is not None else None
            if reasoning:
                emit(ThinkingDeltaEvent(delta=str(reasoning)))

    rtype = getattr(raw, "type", None)
    if rtype == "content_block_delta":
        delta = raw.delta if hasattr(raw, "delta") else raw.get("delta", {})  # type: ignore[union-attr]
        d_type = getattr(delta, "type", None) if not isinstance(delta, dict) else delta.get("type")
        if d_type == "thinking":
            thinking = getattr(delta, "thinking", None) or delta.get("thinking", "")
            if thinking:
                emit(ThinkingDeltaEvent(delta=thinking))
    elif rtype == "thinking":
        text = getattr(raw, "text", None) or raw.get("text", "")
        if text:
            emit(ThinkingDeltaEvent(delta=text))


def _ensure_not_duplicate(messages: list[Any], msg: Any) -> None:
    """Skip appending if the message already exists (by identity or id)."""
    if msg in messages:
        return
    msg_id = getattr(msg, "message_id", None)
    if msg_id:
        for existing in messages:
            if getattr(existing, "message_id", None) == msg_id:
                return


def _tool_result_message(
    call_id: str,
    name: str,
    content: str,
    *,
    ok: bool = True,
) -> Any:
    """Create a tool result Message for chat completion APIs."""
    from agent_framework._types import Content, Message

    return Message(
        role="tool",
        contents=[Content(type="function_result", call_id=call_id, name=name, result=content)],
    )
