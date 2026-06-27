"""WebSocket gateway server — replaces stdin/stdout transport.

Usage:
    python -m coding_agent.main --ws-port 8765
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any

from websockets.asyncio.server import ServerConnection, serve

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

logger = logging.getLogger(__name__)


def _serialize_event(event: AgentEvent) -> dict[str, Any]:
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
                "type": "tool_execution_end", "callId": rid, "name": n,
                "ok": ok, "exitCode": ec, "error": err, "result": r,
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

class WsGatewayServer:
    """WebSocket gateway — one connection, dispatches to agent loop."""

    def __init__(
        self,
        client: Any,
        tools: list[Any] | None = None,
        settings: object | None = None,
        *,
        host: str = "127.0.0.1",
        port: int = 8765,
    ) -> None:
        self._client = client
        self._tools = tools or []
        self._settings = settings
        self._host = host
        self._port = port
        self._current_task: asyncio.Task[None] | None = None
        self._session: Any = None
        self._ws: ServerConnection | None = None
        self._emit_tasks: list[asyncio.Task[None]] = []

    def _emit(self, event: AgentEvent) -> None:
        obj = _serialize_event(event)
        if obj.get("type") not in ("text_delta", "thinking_delta", "tool_execution_delta"):
            fields = _summarize_event(obj)
            print(f"→ {obj.get('type', '?')} {fields}", file=sys.stderr, flush=True)
        if self._ws is None:
            return
        try:
            task = asyncio.create_task(self._ws.send(json.dumps(obj, ensure_ascii=False)))
            self._emit_tasks.append(task)
            task.add_done_callback(self._emit_tasks.remove)
        except Exception:
            pass

    async def _handle_ws(self, ws: ServerConnection) -> None:
        self._ws = ws
        logger.info("TUI connected from %s", ws.remote_address)
        await ws.send(json.dumps({"type": "ready"}))

        async for raw in ws:
            try:
                request = json.loads(raw)
            except json.JSONDecodeError as exc:
                logger.warning("Invalid JSON: %s", exc)
                continue

            method = request.get("method")
            params = request.get("params", {})
            if method == "prompt":
                text = params.get("text", "")
                session_id = params.get("sessionId", "")
                logger.info("← prompt (session=%s, text=%.80s)", session_id, text)
                if self._current_task and not self._current_task.done():
                    self._current_task.cancel()
                self._current_task = asyncio.create_task(self._handle_prompt(text, session_id))
            elif method == "cancel":
                if self._current_task and not self._current_task.done():
                    self._current_task.cancel()

        self._ws = None

    async def _handle_prompt(self, text: str, session_id: str = "") -> None:
        from agent_framework._types import Content, Message

        from coding_agent.loop import run_coding_agent
        from coding_agent.session import (
            create_session,
            dict_to_message,
            load_session,
            message_to_dict,
            save_session,
        )
        from coding_agent.skills import discover_skills, format_skills_for_prompt
        from coding_agent.system_prompt import (
            BuildSystemPromptOptions,
            build_system_prompt,
            discover_project_context,
        )

        # Resolve session
        existing = load_session(session_id) if session_id else None
        if existing:
            session = existing
        elif self._session is None:
            session = create_session()
        else:
            session = self._session
        self._session = session

        # Build messages
        messages: list[object] = [dict_to_message(m) for m in session.messages]
        messages.append(Message(role="user", contents=[Content(type="text", text=text)]))
        skills = discover_skills()
        skills_prompt = format_skills_for_prompt(skills)
        ctx = discover_project_context()
        sys_prompt = build_system_prompt(
            BuildSystemPromptOptions(project_context=ctx, skills_prompt=skills_prompt)
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
            has_sys = messages and hasattr(messages[0], "role") and getattr(messages[0], "role", "") == "system"
            session.messages = [message_to_dict(m) for m in (messages[1:] if has_sys else messages)]
            save_session(session)

    async def run_forever(self) -> None:
        async with serve(self._handle_ws, self._host, self._port):
            logger.info("WS gateway on ws://%s:%d", self._host, self._port)
            print(f"WS READY ws://{self._host}:{self._port}", file=sys.stderr, flush=True)
            await asyncio.get_running_loop().create_future()
