"""Session persistence for the coding agent.

Saves conversation history as JSONL files (one JSON object per message line).
A session index file tracks available sessions.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Data types ──────────────────────────────────────────────────


@dataclass
class SessionInfo:
    """Metadata about a saved session."""

    id: str
    created_at: str
    updated_at: str
    message_count: int
    title: str = ""


@dataclass
class SessionData:
    """A serialisable session containing messages and metadata."""

    id: str
    messages: list[dict] = field(default_factory=list)
    title: str = ""
    created_at: str = ""
    updated_at: str = ""


# ── Session store ───────────────────────────────────────────────


_SESSIONS_DIR = Path.home() / ".coding-agent" / "sessions"
_INDEX_FILE = "index.json"


def _session_dir() -> Path:
    return _SESSIONS_DIR


def _session_path(session_id: str) -> Path:
    return _session_dir() / f"{session_id}.jsonl"


def _index_path() -> Path:
    return _session_dir() / _INDEX_FILE


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _load_index() -> dict[str, SessionInfo]:
    """Load the session index from disk."""
    path = _index_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {sid: SessionInfo(**info) for sid, info in data.items()}
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("Failed to load session index: %s", exc)
        return {}


def _save_index(index: dict[str, SessionInfo]) -> None:
    """Save the session index to disk."""
    _session_dir().mkdir(parents=True, exist_ok=True)
    data = {
        sid: {
            "id": info.id,
            "created_at": info.created_at,
            "updated_at": info.updated_at,
            "message_count": info.message_count,
            "title": info.title,
        }
        for sid, info in index.items()
    }
    _index_path().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def list_sessions() -> list[SessionInfo]:
    """Return all saved sessions, newest first."""
    index = _load_index()
    sessions = sorted(index.values(), key=lambda s: s.updated_at, reverse=True)
    return sessions


def create_session(title: str = "") -> SessionData:
    """Create a new empty session."""
    now = _now()
    return SessionData(id=uuid.uuid4().hex[:12], title=title, created_at=now, updated_at=now)


def save_session(session: SessionData) -> None:
    """Save a session's messages to disk and update the index."""
    _session_dir().mkdir(parents=True, exist_ok=True)
    path = _session_path(session.id)

    # Write messages as JSONL
    with path.open("w", encoding="utf-8") as f:
        for msg in session.messages:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    # Update index
    session.updated_at = _now()
    index = _load_index()
    index[session.id] = SessionInfo(
        id=session.id,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=len(session.messages),
        title=session.title,
    )
    _save_index(index)


def load_session(session_id: str) -> SessionData | None:
    """Load a session from disk by ID."""
    path = _session_path(session_id)
    if not path.exists():
        return None

    index = _load_index()
    info = index.get(session_id)
    if info is None:
        return None

    messages: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    return SessionData(
        id=session_id,
        messages=messages,
        title=info.title,
        created_at=info.created_at,
        updated_at=info.updated_at,
    )


def delete_session(session_id: str) -> bool:
    """Delete a session by ID. Returns True if deleted."""
    path = _session_path(session_id)
    if not path.exists():
        return False
    path.unlink()
    index = _load_index()
    index.pop(session_id, None)
    _save_index(index)
    return True


# ── Serialisation helpers ───────────────────────────────────────


def message_to_dict(msg: object) -> dict:
    """Convert an agent-framework Message to a JSON-serialisable dict."""
    contents = []
    for c in getattr(msg, "contents", None) or []:
        ctype = c.type
        # Thinking/reasoning content blocks are persisted via additional_properties
        # so they are not replayed to the model API on the next turn.
        if ctype in ("thinking", "reasoning", "text_reasoning"):
            continue
        entry = {"type": ctype}
        if ctype == "text":
            entry["text"] = c.text
        elif ctype == "function_call":
            entry["call_id"] = c.call_id
            entry["name"] = c.name
            entry["arguments"] = c.arguments
        elif ctype == "function_result":
            entry["call_id"] = c.call_id
            entry["name"] = c.name
            entry["result"] = c.result
        contents.append(entry)
    result = {"role": getattr(msg, "role", "user"), "contents": contents}
    thinking = getattr(msg, "additional_properties", {}).get("thinking")
    if thinking:
        result["thinking"] = thinking
    return result


def dict_to_message(d: dict) -> object:
    """Reconstruct an agent-framework Message from a dict."""
    from agent_framework._types import Content, Message

    contents = []
    for c in d.get("contents", []):
        t = c.get("type", "text")
        if t == "text":
            contents.append(Content(type="text", text=c.get("text", "")))
        elif t == "function_call":
            contents.append(
                Content(
                    type="function_call",
                    call_id=c.get("call_id", ""),
                    name=c.get("name", ""),
                    arguments=c.get("arguments", ""),
                )
            )
        elif t == "function_result":
            contents.append(
                Content(
                    type="function_result",
                    call_id=c.get("call_id", ""),
                    name=c.get("name", ""),
                    result=c.get("result", ""),
                )
            )
    additional_properties = {}
    thinking = d.get("thinking")
    if thinking:
        additional_properties["thinking"] = thinking
    return Message(
        role=d.get("role", "user"),
        contents=contents,
        additional_properties=additional_properties if additional_properties else None,
    )
