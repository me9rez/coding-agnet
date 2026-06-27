"""Settings management — reads/writes ~/.coding-agent/settings.json.

All configuration (model, base_url, thinking level, token budgets, API key)
lives in one JSON file.  Environment variables and CLI flags override file values.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_SETTINGS_DIR = Path.home() / ".coding-agent"
_SETTINGS_PATH = _SETTINGS_DIR / "settings.json"


@dataclass
class Settings:
    model: str = "deepseek-v4-flash"
    base_url: str = "https://api.deepseek.com/v1"
    api_key: str = ""
    thinking_level: str = ""  # off / low / medium / high
    max_context_tokens: int = 128_000
    max_output_tokens: int = 8_000
    keep_recent_tokens: int = 8_000
    max_turns: int = 25


def _default_settings() -> Settings:
    return Settings()


def load() -> Settings:
    """Load settings from ~/.coding-agent/settings.json."""
    if not _SETTINGS_PATH.exists():
        return _default_settings()
    try:
        data = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        s = _default_settings()
        for key in (
            "model",
            "base_url",
            "api_key",
            "thinking_level",
            "max_context_tokens",
            "max_output_tokens",
            "keep_recent_tokens",
            "max_turns",
        ):
            if key in data:
                setattr(s, key, data[key])
        return s
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load settings from %s: %s", _SETTINGS_PATH, exc)
        return _default_settings()


def save(s: Settings) -> None:
    """Save settings to ~/.coding-agent/settings.json."""
    _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "model": s.model,
        "base_url": s.base_url,
        "api_key": s.api_key,
        "thinking_level": s.thinking_level,
        "max_context_tokens": s.max_context_tokens,
        "max_output_tokens": s.max_output_tokens,
        "keep_recent_tokens": s.keep_recent_tokens,
        "max_turns": s.max_turns,
    }
    _SETTINGS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def resolve_api_key(settings: Settings) -> str:
    """Return the effective API key: settings > env."""
    return settings.api_key or os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
