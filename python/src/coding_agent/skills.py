"""Skills system — progressive skill loading from SKILL.md files.

Uses the agent-framework ``SkillsProvider`` so that discovered skills are
advertised via the agent's context providers and loaded through the framework's
built-in ``load_skill`` tool.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from agent_framework._skills import SkillsProvider

logger = logging.getLogger(__name__)


DEFAULT_SKILL_DIRS: Sequence[str | Path] = [
    Path.cwd() / "skills",
    Path.home() / ".coding-agent" / "skills",
]


def create_skills_provider(
    skill_dirs: Sequence[str | Path] | None = None,
) -> SkillsProvider:
    """Create a ``SkillsProvider`` from the configured skill directories.

    Parameters
    ----------
    skill_dirs:
        Directories to scan for ``SKILL.md`` files. Defaults to the project-level
        ``./skills`` directory and the user-level ``~/.coding-agent/skills``.

    Returns
    -------
    A configured ``SkillsProvider`` that advertises skills and exposes the
    ``load_skill`` / ``read_skill_resource`` tools.
    """
    from agent_framework._skills import SkillsProvider

    dirs = skill_dirs if skill_dirs is not None else DEFAULT_SKILL_DIRS
    return SkillsProvider.from_paths(dirs)
