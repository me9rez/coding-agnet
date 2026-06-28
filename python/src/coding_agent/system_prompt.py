"""System prompt assembly for the coding agent.

Builds a system prompt that tells the model its identity, capabilities,
tool interfaces, and project context.
"""

from __future__ import annotations

import logging
import os
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)

# ── Data types ──────────────────────────────────────────────────


@dataclass(frozen=True)
class ProjectContext:
    """Summary of the project the agent is working in."""

    cwd: str = ""
    git_root: str | None = None
    language_hints: Sequence[str] = field(default_factory=tuple)
    ignore_patterns: Sequence[str] = field(default_factory=tuple)
    os_name: str = ""
    shell: str = ""


@dataclass(frozen=True)
class BuildSystemPromptOptions:
    """Options used to assemble the system prompt."""

    instructions: str | None = None
    extra_guidelines: Sequence[str] = field(default_factory=tuple)
    project_context: ProjectContext | None = None
    skills_prompt: str = ""
    mcp_tools_prompt: str = ""


# ── Builder ─────────────────────────────────────────────────────


_DEFAULT_INSTRUCTIONS = """\
You are a helpful coding assistant running in a terminal. You have access to tools
that let you execute shell commands, read and write files, edit existing files with
exact text replacements, search file contents, and list directories.

## Guidelines

- Read files before editing them. Use the `read` tool to inspect a file, then use `edit`
  to make precise changes.
- When making multiple related edits to the same file, prefer a single `edit` call with
  multiple entries in the `edits` array instead of several separate calls.
- Each `edit` entry's `oldText` must match **exactly** and appear **exactly once** in the
  file. Keep `oldText` as small as possible while still being unique.
- After running bash commands, check the exit code. Non-zero exit codes mean the command
  likely failed.
- Working directory is the project root.
- When you have completed the task, present a clear summary of what you did.
"""


def build_system_prompt(options: BuildSystemPromptOptions) -> str:
    """Build the system prompt string."""
    parts: list[str] = []

    # Core instructions
    parts.append(options.instructions or _DEFAULT_INSTRUCTIONS)

    # Extra guidelines
    if options.extra_guidelines:
        parts.append("## Additional Guidelines\n" + "\n".join(f"- {g}" for g in options.extra_guidelines))

    # Skills
    if options.skills_prompt:
        parts.append(options.skills_prompt)

    # MCP tools
    if options.mcp_tools_prompt:
        parts.append(options.mcp_tools_prompt)

    # Project context
    ctx = options.project_context
    if ctx and ctx.cwd:
        ctx_lines = [f"- Working directory: `{ctx.cwd}`"]
        if ctx.git_root:
            ctx_lines.append(f"- Git root: `{ctx.git_root}`")
        if ctx.language_hints:
            ctx_lines.append(f"- Languages detected: {', '.join(ctx.language_hints)}")
        if ctx.ignore_patterns:
            ctx_lines.append("- Ignored patterns: " + ", ".join(ctx.ignore_patterns[:5]))
        if ctx.os_name:
            ctx_lines.append(f"- OS: {ctx.os_name}")
        if ctx.shell:
            ctx_lines.append(f"- Shell: {ctx.shell}")
        parts.append("## Project Context\n" + "\n".join(ctx_lines))

    # OS-specific shell guidance
    if ctx and ctx.os_name and "Windows" in ctx.os_name:
        parts.append(
            "## Windows Shell Guidance\n"
            "- Prefer PowerShell commands. The `bash` tool runs via `pwsh -NoProfile -Command <cmd>`.\n"
            "- Avoid Unix-only syntax (e.g. `ls`, `grep`, `cat`, `sed`, single quotes for paths).\n"
            "- Use Windows-compatible paths and commands when possible."
        )

    return "\n\n".join(parts)


def _detect_shell() -> str:
    """Return a human-readable shell name for the current OS."""
    if sys.platform == "win32":
        return "PowerShell (pwsh)"
    shell = os.environ.get("SHELL", "")
    if shell:
        return Path(shell).name
    return "bash"


def discover_project_context(cwd: str | None = None) -> ProjectContext:
    """Gather project context from the current working directory."""
    root = Path(cwd or Path.cwd()).resolve()

    git_root = None
    git_dir = root
    for _ in range(10):
        if (git_dir / ".git").exists():
            git_root = str(git_dir)
            break
        parent = git_dir.parent
        if parent == git_dir:
            break
        git_dir = parent

    # Detect language hints from common config files
    hints: list[str] = []
    for marker, lang in [
        ("pyproject.toml", "Python"),
        ("package.json", "JavaScript/TypeScript"),
        ("Cargo.toml", "Rust"),
        ("go.mod", "Go"),
        ("Gemfile", "Ruby"),
        ("Makefile", "Make"),
        ("CMakeLists.txt", "CMake"),
        ("pom.xml", "Java"),
        ("build.gradle", "Gradle"),
    ]:
        if (root / marker).exists():
            hints.append(lang)

    # Gitignore patterns
    ignore: list[str] = []
    gitignore_path = (git_dir or root) / ".gitignore"
    if gitignore_path.exists():
        for line in gitignore_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                ignore.append(line)

    os_name = f"{platform.system()} {platform.release()}".strip()
    shell = _detect_shell()
    logger.info("Detected OS: %s, shell: %s", os_name, shell)
    return ProjectContext(
        cwd=str(root),
        git_root=git_root,
        language_hints=hints,
        ignore_patterns=ignore[:20],
        os_name=os_name,
        shell=shell,
    )
