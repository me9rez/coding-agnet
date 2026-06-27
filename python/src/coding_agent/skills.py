"""Skills system — progressive skill loading from SKILL.md files.

Skills follow the agent-skills specification:
1. Advertise — skill names and descriptions in the system prompt
2. Load — the full SKILL.md body returned via the ``load_skill`` tool
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Skill:
    """A skill loaded from a SKILL.md file."""

    name: str
    path: Path
    description: str = ""
    content: str = ""


def discover_skills(skill_dirs: Sequence[str | Path] | None = None) -> list[Skill]:
    """Scan directories for ``SKILL.md`` files and return discovered skills."""
    if skill_dirs is None:
        user_skills = Path.home() / ".coding-agent" / "skills"
        skill_dirs = [Path.cwd() / "skills", user_skills]

    skills: dict[str, Skill] = {}
    for directory in skill_dirs:
        base = Path(directory).resolve()
        if not base.is_dir():
            continue
        for md_file in sorted(base.rglob("SKILL.md")):
            name = md_file.parent.name
            try:
                content = md_file.read_text(encoding="utf-8")
            except Exception as exc:
                logger.warning("Failed to read skill %s: %s", md_file, exc)
                continue

            # Extract description from first heading or first line
            description = ""
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("#"):
                    description = stripped.lstrip("#").strip()
                    break
            if not description:
                description = name

            skills[name] = Skill(name=name, path=md_file, description=description, content=content)

    return sorted(skills.values(), key=lambda s: s.name)


def format_skills_for_prompt(skills: Sequence[Skill]) -> str:
    """Format skills for inclusion in the system prompt (advertise only)."""
    if not skills:
        return ""

    lines = [
        "## Available Skills",
        "",
        "The following skills are available. Use the ``load_skill`` tool to load a skill's full content.",
        "",
    ]
    for skill in skills:
        lines.append(f"- **{skill.name}**: {skill.description}")

    return "\n".join(lines)


async def _load_skill(skill_name: str, skill_dirs: list[str] | None = None) -> str:
    """Tool function: load and return the full content of a skill by name."""
    skills = discover_skills(skill_dirs)
    for skill in skills:
        if skill.name == skill_name:
            return f"# Skill: {skill.name}\n\n{skill.content}"
    return f"Error: Skill '{skill_name}' not found. Available: {', '.join(s.name for s in skills)}"
