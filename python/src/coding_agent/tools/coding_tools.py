"""Coding agent tools — bash, file read/write/edit/search, directory listing.

Each tool is a ``FunctionTool`` instance that can be passed to the agent loop.
All tools are async and return strings.
"""

from __future__ import annotations

import asyncio
import difflib
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_framework._tools import FunctionTool

logger = logging.getLogger(__name__)



@dataclass
class _ToolResult:
    """Structured result for tools that have exit codes / ok status."""
    type: str = "tool_result"
    result: str = ""
    exit_code: int | None = None
    ok: bool = True


_MAX_OUTPUT_CHARS = 100_000


def create_coding_tools() -> list[FunctionTool]:
    """Return the default set of coding tools."""
    from agent_framework._tools import FunctionTool

    # Import load_skill for the skill tool
    from coding_agent.skills import _load_skill

    _skill_dirs: list[str] = []

    async def load_skill_wrapper(skill_name: str) -> str:
        return await _load_skill(skill_name, _skill_dirs)

    return [
        FunctionTool(name="bash", description="Execute a shell command", func=_bash),
        FunctionTool(name="read", description="Read the contents of a file", func=_file_read),
        FunctionTool(
            name="write",
            description="Write content to a file (creates parent dirs)",
            func=_file_write,
        ),
        FunctionTool(
            name="edit",
            description=(
                "Edit a file using exact text replacements. "
                "Provide edits as [{oldText, newText}, ...]. "
                "Each oldText must match a unique, non-overlapping region."
            ),
            func=_edit,
        ),
        FunctionTool(
            name="search",
            description="Search file contents recursively with a regex pattern",
            func=_file_search,
        ),
        FunctionTool(
            name="list_dir",
            description="List files and directories at a path",
            func=_file_list,
        ),
        FunctionTool(
            name="load_skill",
            description="Load the full content of a skill by name",
            func=load_skill_wrapper,
        ),
    ]


# ── Bash ────────────────────────────────────────────────────────


async def _bash(command: str, timeout_seconds: float = 30.0) -> _ToolResult:
    """Execute a shell command and return stdout + stderr."""
    logger.info("bash: %s", command[:200])
    try:
        if sys.platform == "win32":
            proc = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    "pwsh", "-NoProfile", "-Command", command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=os.getcwd(),
                ),
                timeout=timeout_seconds,
            )
        else:
            proc = await asyncio.wait_for(
                asyncio.create_subprocess_shell(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=os.getcwd(),
                ),
                timeout=timeout_seconds,
            )
        stdout, _ = await proc.communicate()
        output = stdout.decode("utf-8", errors="replace") if stdout else ""
        if len(output) > _MAX_OUTPUT_CHARS:
            output = output[:_MAX_OUTPUT_CHARS] + f"\n… (truncated, {len(output)} total chars)"
        exit_code = proc.returncode or 0
        return _ToolResult(result=output, exit_code=exit_code, ok=exit_code == 0)
    except TimeoutError:
        return _ToolResult(result=f"Error: Command timed out after {timeout_seconds}s", exit_code=-1, ok=False)
    except Exception as exc:
        return _ToolResult(result=f"Error: {exc}", exit_code=-1, ok=False)


# ── File read ───────────────────────────────────────────────────


async def _file_read(path: str) -> str:
    """Read the contents of a file."""
    try:
        p = Path(path).resolve()
        if not p.exists():
            return f"Error: File not found: {path}"
        if not p.is_file():
            return f"Error: Not a file: {path}"
        content = p.read_text(encoding="utf-8", errors="replace")
        if len(content) > _MAX_OUTPUT_CHARS:
            content = content[:_MAX_OUTPUT_CHARS] + f"\n… (truncated, {len(content)} total chars)"
        return content
    except Exception as exc:
        return f"Error reading file: {exc}"


# ── File write ──────────────────────────────────────────────────


async def _file_write(path: str, content: str) -> str:
    """Write content to a file, creating parent directories if needed."""
    try:
        p = Path(path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as exc:
        return f"Error writing file: {exc}"


# ── Edit (exact text replacement) ──────────────────────────────


async def _edit(path: str, edits: list[dict[str, str]]) -> str:
    """Apply exact text replacements to a file.

    Each edit item: ``{"oldText": "...", "newText": "..."}``.
    Every ``oldText`` must appear exactly once; edits must not overlap.
    All replacements are validated before any write occurs.
    """
    try:
        p = Path(path).resolve()
        if not p.exists():
            return f"Error: File not found: {path}"
        if not p.is_file():
            return f"Error: Not a file: {path}"

        raw = p.read_text(encoding="utf-8")
        content = raw.replace("\r\n", "\n").replace("\r", "\n")

        # Validate and collect edit spans
        spans: list[tuple[int, int, str]] = []
        for i, edit in enumerate(edits):
            old = edit.get("oldText", "")
            new = edit.get("newText", "")
            if not old:
                return f"Error: edits[{i}].oldText is empty"
            old_norm = old.replace("\r\n", "\n").replace("\r", "\n")
            count = content.count(old_norm)
            if count == 0:
                return (
                    f"Error: edits[{i}].oldText not found in {path}. "
                    "oldText must match a unique region of the file content."
                )
            if count > 1:
                return (
                    f"Error: edits[{i}].oldText found {count} times in {path}. Each oldText must appear exactly once."
                )
            start = content.index(old_norm)
            spans.append((start, start + len(old_norm), new))

        # Validate no overlaps
        spans.sort(key=lambda s: s[0])
        for i in range(1, len(spans)):
            if spans[i][0] < spans[i - 1][1]:
                return f"Error: edits[{i}] overlaps with edits[{i - 1}]. Edit spans must not overlap."

        # Apply in reverse order (preserves positions)
        new_content = content
        for start, end, new_text in reversed(spans):
            new_content = new_content[:start] + new_text + new_content[end:]

        if new_content == content:
            return f"Warning: No changes made to {path} (oldText matched newText)"

        p.write_text(new_content, encoding="utf-8")

        # Generate unified diff
        old_lines = content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        diff = "".join(difflib.unified_diff(old_lines, new_lines, str(path), str(path)))

        return f"Applied {len(edits)} edit(s) to {path}.\n\n{diff}"

    except Exception as exc:
        return f"Error editing file: {exc}"


# ── File search ─────────────────────────────────────────────────


async def _file_search(pattern: str, path: str = ".") -> str:
    """Search file contents recursively using a regex pattern."""
    try:
        root = Path(path).resolve()
        if not root.is_dir():
            return f"Error: Not a directory: {path}"
        compiled = re.compile(pattern, re.IGNORECASE)
        results: list[str] = []
        max_results = 50
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix in (".pyc", ".exe", ".dll", ".so", ".dylib", ".bin", ".png", ".jpg", ".gif"):
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
                for lineno, line in enumerate(text.splitlines(), 1):
                    if compiled.search(line):
                        rel = p.relative_to(root)
                        results.append(f"{rel}:{lineno}: {line.strip()[:200]}")
                        if len(results) >= max_results:
                            break
                if len(results) >= max_results:
                    break
            except Exception:
                continue
        if not results:
            return f"No matches for pattern: {pattern}"
        return "\n".join(results) + (f"\n… (showing {len(results)} of many)" if len(results) >= max_results else "")
    except re.error as exc:
        return f"Invalid regex pattern: {exc}"
    except Exception as exc:
        return f"Error searching files: {exc}"


# ── File list ───────────────────────────────────────────────────


async def _file_list(path: str = ".") -> str:
    """List files and directories at the given path."""
    try:
        p = Path(path).resolve()
        if not p.is_dir():
            return f"Error: Not a directory: {path}"
        entries = [f"📁 {p}/"]
        for entry in sorted(p.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            entries.append(f"  {entry.name}{'/' if entry.is_dir() else ''}")
        return "\n".join(entries) if entries else "(empty)"
    except Exception as exc:
        return f"Error listing directory: {exc}"
