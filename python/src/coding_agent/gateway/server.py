"""Gateway server — reads JSON-RPC from stdin, runs agent loop, emits events to stdout.

The TUI spawns ``python -m coding_agent.main`` as a subprocess.  The gateway
reads newline-delimited JSON-RPC requests from stdin (``prompt``, ``cancel``)
and writes newline-delimited JSON events to stdout.

Event flow:
    TUI → ``{"method":"prompt","params":{"text":"..."}}``
        → GatewayServer dispatches ``run_coding_agent()``
        → loop emits ``TextDeltaEvent``, ``ThinkingDeltaEvent`` etc.
        → gateway serialises each event as ``{"type":"text_delta","delta":"..."}``
        → TUI reads, renders

References:
    hermes tui_gateway/server.py — dispatch pattern
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any

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
from coding_agent.gateway.transport import StdioTransport
from coding_agent.loop import run_coding_agent

logger = logging.getLogger(__name__)


def _serialize_event(event: AgentEvent) -> dict[str, Any]:
    """Convert an AgentEvent to a JSON-serialisable dict."""
    match event:
        case ThinkingDeltaEvent(delta=d):
            return {"type": "thinking_delta", "delta": d}
        case TextDeltaEvent(delta=d):
            return {"type": "text_delta", "delta": d}
        case ToolCallStartEvent(call_id=rid, name=n, arguments=a):
            return {"type": "tool_call_start", "callId": rid, "name": n, "arguments": a}
        case ToolExecutionStartEvent(call_id=rid, name=n):
            return {"type": "tool_execution_start", "callId": rid, "name": n}
        case ToolExecutionDeltaEvent(call_id=rid, line=l):
            return {"type": "tool_execution_delta", "callId": rid, "line": l}
        case ToolExecutionEndEvent(call_id=rid, name=n, ok=ok, exit_code=ec, error=err, result=r):
            return {
                "type": "tool_execution_end",
                "callId": rid,
                "name": n,
                "ok": ok,
                "exitCode": ec,
                "error": err,
                "result": r,
            }
        case TurnEndEvent(reason=r):
            return {"type": "turn_end", "reason": r}
        case DoneEvent():
            return {"type": "done"}
        case ErrorEvent(message=m, recoverable=r):
            return {"type": "error", "message": m, "recoverable": r}
    return {"type": "unknown", "raw": str(event)}


def _summarize_event(obj: dict[str, Any]) -> str:
    """Return a one-line summary of key fields for logging."""
    t = obj.get("type", "")
    parts: list[str] = []
    if call_id := obj.get("callId"):
        parts.append(f"id={call_id}")
    if name := obj.get("name"):
        parts.append(f"name={name}")
    if t == "tool_call_start":
        args = obj.get("arguments", "")[:80]
        parts.append(f"args={args}")
    elif t == "tool_execution_end":
        ok = obj.get("ok", "?")
        ec = obj.get("exitCode")
        err = obj.get("error")
        r = obj.get("result", "")
        parts.append(f"ok={ok}")
        if ec is not None:
            parts.append(f"exit={ec}")
        if r:
            parts.append(f"result={len(r)}B")
        if err:
            parts.append(f"error={err[:100]}")
    elif t == "turn_end":
        parts.append(f"reason={obj.get('reason', '?')}")
    elif t == "error":
        parts.append(f"msg={obj.get('message', '?')[:120]}")
    return " ".join(parts)


class GatewayServer:
    """Read stdin JSON-RPC, dispatch to agent loop, emit events to transport.

    Usage::

        server = GatewayServer(client=my_client, transport=StdioTransport())
        await server.run()
    """

    def __init__(
        self,
        client: Any,
        tools: list[Any] | None = None,
        transport: StdioTransport | None = None,
        settings: object | None = None,
        skill_provider: Any | None = None,
        mcp_tools: list[Any] | None = None,
    ) -> None:
        self._client = client
        self._tools = tools or []
        self.transport = transport or StdioTransport()
        self._cancel_event = asyncio.Event()
        self._running = False
        self._current_task: asyncio.Task[None] | None = None
        self._session: object | None = None
        self._settings = settings
        self._skill_provider = skill_provider
        self._mcp_tools = mcp_tools or []

    def _emit(self, event: AgentEvent) -> None:
        """Serialize and write one event to the transport."""
        obj = _serialize_event(event)
        if obj.get("type") not in ("text_delta", "thinking_delta", "tool_execution_delta"):
            fields = _summarize_event(obj)
            print(f"→ {obj.get('type', '?')} {fields}", file=sys.stderr, flush=True)
        self.transport.write(obj)

    async def run(self) -> None:
        """Read JSON-RPC lines from stdin (threaded) and dispatch them."""
        self._running = True
        loop = asyncio.get_running_loop()

        # Signal ready to TUI
        self.transport.write({"type": "ready"})
        logger.info("Gateway ready, waiting for requests on stdin")

        while self._running:
            try:
                line = await loop.run_in_executor(None, sys.stdin.readline)
            except OSError:
                break

            if not line:
                logger.info("stdin EOF, shutting down")
                break

            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning("Invalid JSON from stdin: %s", exc)
                continue

            method = request.get("method")
            params = request.get("params", {})
            if method == "prompt":
                text = params.get("text", "")
                session_id = params.get("sessionId", "")
                logger.info("← prompt (session=%s, text=%.80s)", session_id, text)
                if text:
                    if self._current_task and not self._current_task.done():
                        self._current_task.cancel()
                    self._current_task = asyncio.create_task(self._handle_prompt(text, session_id))
            else:
                logger.warning("Unknown method: %s", method)

        # Wait for current task to finish
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            try:
                await self._current_task
            except asyncio.CancelledError, Exception:
                pass

    async def _handle_prompt(self, text: str, session_id: str = "") -> None:
        """Run a single prompt, auto-saving session."""
        from agent_framework._types import Content, Message

        from coding_agent.mcp import format_mcp_tools_for_prompt
        from coding_agent.session import (
            SessionData,
            create_session,
            dict_to_message,
            load_session,
            message_to_dict,
            save_session,
        )
        from coding_agent.system_prompt import (
            BuildSystemPromptOptions,
            build_system_prompt,
            discover_project_context,
        )

        # Resolve/create session
        session: SessionData
        existing = load_session(session_id) if session_id else None
        if existing:
            session = existing
        elif self._session is None:
            session = create_session()
        else:
            session = self._session  # type: ignore[assignment]
        self._session = session
        messages: list[object] = [dict_to_message(m) for m in session.messages]
        messages.append(Message(role="user", contents=[Content(type="text", text=text)]))

        # Build system prompt (skills are advertised via SkillsProvider).
        ctx = discover_project_context()
        mcp_tools_prompt = format_mcp_tools_for_prompt(self._mcp_tools)
        sys_prompt = build_system_prompt(
            BuildSystemPromptOptions(
                project_context=ctx,
                mcp_tools_prompt=mcp_tools_prompt,
            )
        )
        try:
            thinking = getattr(self._settings, "thinking_level", "") if self._settings else ""
            max_tok = getattr(self._settings, "max_context_tokens", None) if self._settings else None
            await run_coding_agent(
                client=self._client,
                messages=messages,  # type: ignore[arg-type]
                tools=self._tools,
                on_event=self._emit,
                system_prompt=sys_prompt,
                thinking_level=thinking or None,
                compaction_max_tokens=max_tok,
                skill_provider=self._skill_provider,
                mcp_tools=self._mcp_tools,
            )
        except asyncio.CancelledError:
            logger.info("Agent run cancelled")
            self._emit(ErrorEvent(message="Agent run cancelled", recoverable=True))
            self._emit(DoneEvent())
        except Exception as exc:
            logger.exception("Agent loop failed")
            self._emit(ErrorEvent(message=str(exc), recoverable=False))
            self._emit(DoneEvent())
        finally:
            # Save messages (skip system prompt message at index 0)
            has_sys = messages and getattr(messages[0], "role", "") == "system"
            session.messages = [message_to_dict(m) for m in (messages[1:] if has_sys else messages)]
            save_session(session)
