"""WebSocket gateway server — replaces stdin/stdout transport.

Usage:
    python -m coding_agent.main --ws-port 8765
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
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
    UsageEvent,
)
from coding_agent.session import (
    create_session,
    delete_session,
    end_session_run,
    list_sessions,
    load_session,
    save_session,
    start_session_run,
    update_session,
)
from coding_agent.settings import Settings, _split_selected_model, build_client, model_config, thinking_level
from coding_agent.settings import load as load_settings
from coding_agent.settings import save as save_settings
from coding_agent.thinking import thinking_options_for_model

logger = logging.getLogger(__name__)


def _session_info_to_dict(info: Any) -> dict[str, Any]:
    return {
        "id": info.id,
        "createdAt": info.created_at,
        "updatedAt": info.updated_at,
        "messageCount": info.message_count,
        "title": info.title,
        "model": info.model,
        "modelProvider": info.model_provider,
        "status": info.status,
        "sessionStartedAt": info.session_started_at,
        "lastInteractionAt": info.last_interaction_at,
        "startedAt": info.started_at,
        "endedAt": info.ended_at,
        "runtimeMs": info.runtime_ms,
        "inputTokens": info.input_tokens,
        "outputTokens": info.output_tokens,
        "totalTokens": info.total_tokens,
        "cacheReadTokens": info.cache_read_tokens,
        "reasoningTokens": info.reasoning_tokens,
        "estimatedCostUsd": info.estimated_cost_usd,
    }


def _session_data_to_dict(session: Any) -> dict[str, Any]:
    return {
        "id": session.id,
        "title": session.title,
        "model": session.model,
        "modelProvider": session.model_provider,
        "createdAt": session.created_at,
        "updatedAt": session.updated_at,
        "messages": session.messages,
        "status": session.status,
        "sessionStartedAt": session.session_started_at,
        "lastInteractionAt": session.last_interaction_at,
        "startedAt": session.started_at,
        "endedAt": session.ended_at,
        "runtimeMs": session.runtime_ms,
        "inputTokens": session.input_tokens,
        "outputTokens": session.output_tokens,
        "totalTokens": session.total_tokens,
        "cacheReadTokens": session.cache_read_tokens,
        "reasoningTokens": session.reasoning_tokens,
        "estimatedCostUsd": session.estimated_cost_usd,
    }


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
        case UsageEvent(
            input_tokens=i, output_tokens=o, total_tokens=t,
            cache_read_tokens=c, reasoning_tokens=r, details=d,
        ):
            return {
                "type": "usage",
                "inputTokens": i,
                "outputTokens": o,
                "totalTokens": t,
                "cacheReadTokens": c,
                "reasoningTokens": r,
                "details": d,
            }
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
        tools: list[Any] | None = None,
        settings: Settings | None = None,
        *,
        host: str = "127.0.0.1",
        port: int = 8765,
    ) -> None:
        self._tools = tools or []
        self._settings = settings
        self._host = host
        self._port = port
        self._current_task: asyncio.Task[None] | None = None
        self._session: Any = None
        self._ws: ServerConnection | None = None
        self._emit_tasks: list[asyncio.Task[None]] = []
        self._clients: dict[str, Any] = {}
        self._workspace = self._detect_workspace()

    def _client_for(self, model: str) -> Any:
        if self._settings is None:
            raise RuntimeError("Settings not available")
        if model not in self._clients:
            self._clients[model] = build_client(self._settings, model)
        return self._clients[model]

    def _detect_workspace(self) -> dict[str, str]:
        from coding_agent.system_prompt import discover_project_context

        ctx = discover_project_context()
        path = ctx.cwd or str(Path.cwd().resolve())
        return {"name": Path(path).name, "path": path}

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

    def _send_rpc_response(self, request_id: str, result: Any) -> None:
        if self._ws is None:
            return
        obj = {"type": "rpc_response", "id": request_id, "result": result}
        try:
            task = asyncio.create_task(self._ws.send(json.dumps(obj, ensure_ascii=False)))
            self._emit_tasks.append(task)
            task.add_done_callback(self._emit_tasks.remove)
        except Exception:
            pass

    def _send_rpc_error(self, request_id: str, message: str) -> None:
        if self._ws is None:
            return
        obj = {"type": "rpc_response", "id": request_id, "error": {"message": message}}
        try:
            task = asyncio.create_task(self._ws.send(json.dumps(obj, ensure_ascii=False)))
            self._emit_tasks.append(task)
            task.add_done_callback(self._emit_tasks.remove)
        except Exception:
            pass

    async def _handle_ws(self, ws: ServerConnection) -> None:
        self._ws = ws
        logger.info("Client connected from %s", ws.remote_address)
        await ws.send(json.dumps({"type": "ready", "workspace": self._workspace}))

        async for raw in ws:
            try:
                request = json.loads(raw)
            except json.JSONDecodeError as exc:
                logger.warning("Invalid JSON: %s", exc)
                continue

            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")
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
            elif method == "listSessions":
                try:
                    sessions = list_sessions()
                    self._send_rpc_response(request_id, [_session_info_to_dict(s) for s in sessions])
                except Exception as exc:
                    logger.exception("listSessions failed")
                    self._send_rpc_error(request_id, str(exc))
            elif method == "createSession":
                try:
                    title = params.get("title", "")
                    model = params.get("model", "")
                    session = create_session(title=title, model=model)
                    save_session(session)
                    self._send_rpc_response(request_id, _session_data_to_dict(session))
                except Exception as exc:
                    logger.exception("createSession failed")
                    self._send_rpc_error(request_id, str(exc))
            elif method == "loadSession":
                try:
                    session_id = params.get("sessionId", "")
                    session = load_session(session_id)
                    if session is None:
                        self._send_rpc_error(request_id, f"Session not found: {session_id}")
                    else:
                        self._send_rpc_response(request_id, _session_data_to_dict(session))
                except Exception as exc:
                    logger.exception("loadSession failed")
                    self._send_rpc_error(request_id, str(exc))
            elif method == "deleteSession":
                try:
                    session_id = params.get("sessionId", "")
                    ok = delete_session(session_id)
                    self._send_rpc_response(request_id, {"ok": ok})
                except Exception as exc:
                    logger.exception("deleteSession failed")
                    self._send_rpc_error(request_id, str(exc))
            elif method == "updateSession":
                try:
                    session_id = params.get("sessionId", "")
                    title = params.get("title")
                    model = params.get("model")
                    session = update_session(session_id, title=title, model=model)
                    if session is None:
                        self._send_rpc_error(request_id, f"Session not found: {session_id}")
                    else:
                        self._send_rpc_response(request_id, _session_data_to_dict(session))
                except Exception as exc:
                    logger.exception("updateSession failed")
                    self._send_rpc_error(request_id, str(exc))
            elif method == "getSettings":
                try:
                    s = load_settings()
                    self._send_rpc_response(
                        request_id,
                        {
                            "primaryModel": s.primary_model,
                            "providers": s.providers,
                            "max_turns": s.max_turns,
                        },
                    )
                except Exception as exc:
                    logger.exception("getSettings failed")
                    self._send_rpc_error(request_id, str(exc))
            elif method == "updateSettings":
                try:
                    s = load_settings()
                    if "primaryModel" in params:
                        s.primary_model = params["primaryModel"]
                    if "selectedModel" in params:
                        s.primary_model = params["selectedModel"]
                    if "providers" in params:
                        s.providers = params["providers"]
                    if "max_turns" in params:
                        s.max_turns = params["max_turns"]
                    save_settings(s)
                    self._send_rpc_response(
                        request_id,
                        {
                            "primaryModel": s.primary_model,
                            "providers": s.providers,
                            "max_turns": s.max_turns,
                        },
                    )
                except Exception as exc:
                    logger.exception("updateSettings failed")
                    self._send_rpc_error(request_id, str(exc))

        self._ws = None

    async def _handle_prompt(self, text: str, session_id: str = "") -> None:
        from agent_framework._types import Content, Message

        from coding_agent.loop import run_coding_agent
        from coding_agent.session import dict_to_message, message_to_dict
        from coding_agent.skills import discover_skills, format_skills_for_prompt
        from coding_agent.system_prompt import (
            BuildSystemPromptOptions,
            build_system_prompt,
            discover_project_context,
        )

        # Resolve session and model
        settings = self._settings if isinstance(self._settings, Settings) else None
        primary_model = getattr(settings, "primary_model", "") if settings else ""
        existing = load_session(session_id) if session_id else None
        if existing:
            session = existing
        elif self._session is None:
            session = create_session(model=primary_model)
        else:
            session = self._session
        self._session = session
        session_model = session.model or primary_model
        if not session_id:
            save_session(session)
        session = start_session_run(session.id) or session
        self._session = session

        # Build messages
        messages: list[object] = [dict_to_message(m) for m in session.messages]
        messages.append(Message(role="user", contents=[Content(type="text", text=text)]))
        skills = discover_skills()
        skills_prompt = format_skills_for_prompt(skills)
        ctx = discover_project_context()
        sys_prompt = build_system_prompt(BuildSystemPromptOptions(project_context=ctx, skills_prompt=skills_prompt))

        error_occurred = False

        def _on_event(event: AgentEvent) -> None:
            if isinstance(event, UsageEvent):
                session.input_tokens += event.input_tokens
                session.output_tokens += event.output_tokens
                session.total_tokens += event.total_tokens
                session.cache_read_tokens += event.cache_read_tokens
                session.reasoning_tokens += event.reasoning_tokens
            self._emit(event)

        try:
            provider_id, model_id = _split_selected_model(session_model)
            cfg = model_config(settings, session_model) if settings else None
            max_tok = cfg.get("contextWindow") if cfg else None
            lvl = thinking_level(settings, session_model) if settings else None
            options = thinking_options_for_model(lvl, provider_id, model_id)
            client = self._client_for(session_model)
            await run_coding_agent(
                client=client,
                messages=messages,  # type: ignore[arg-type]
                tools=self._tools,
                on_event=_on_event,
                system_prompt=sys_prompt,
                thinking_level=options.get("reasoning_effort") if options else None,
                compaction_max_tokens=max_tok,
            )
        except asyncio.CancelledError:
            logger.info("Agent run cancelled")
            self._emit(ErrorEvent(message="Agent run cancelled", recoverable=True))
            self._emit(DoneEvent())
        except Exception as exc:
            error_occurred = True
            logger.exception("Agent loop failed")
            self._emit(ErrorEvent(message=str(exc), recoverable=False))
            self._emit(DoneEvent())
        finally:
            has_sys = messages and hasattr(messages[0], "role") and getattr(messages[0], "role", "") == "system"
            session.messages = [message_to_dict(m) for m in (messages[1:] if has_sys else messages)]
            session = end_session_run(session.id, error=error_occurred) or session
            self._session = session
            save_session(session)

    async def run_forever(self) -> None:
        from coding_agent.system_prompt import discover_project_context

        ctx = discover_project_context()
        logger.info("WS gateway starting — OS: %s, shell: %s", ctx.os_name, ctx.shell)
        async with serve(self._handle_ws, self._host, self._port):
            logger.info("WS gateway on ws://%s:%d", self._host, self._port)
            print(f"WS READY ws://{self._host}:{self._port}", file=sys.stderr, flush=True)
            await asyncio.get_running_loop().create_future()
