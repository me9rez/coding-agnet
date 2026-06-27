"""Settings management — reads/writes ~/.coding-agent/settings.json.

Configuration now follows a provider/model layout similar to openclaw.json:

    {
      "selectedModel": "deepseek/deepseek-v4-flash",
      "providers": {
        "deepseek": {
          "api": "openai-completions",
          "baseUrl": "https://api.deepseek.com/v1",
          "apiKey": "...",
          "models": [
            {
              "id": "deepseek-v4-flash",
              "name": "DeepSeek V4 Flash",
              "contextWindow": 128000,
              "maxTokens": 8000,
              "reasoning": true,
              "thinking_level": ["high", "max"],
              "input": ["text"]
            }
          ]
        }
      },
      "max_turns": 25
    }

Legacy top-level ``model/base_url/api_key/thinking_level/max_*_tokens`` fields are
migrated automatically.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SETTINGS_DIR = Path.home() / ".coding-agent"
_SETTINGS_PATH = _SETTINGS_DIR / "settings.json"


def _default_providers() -> dict[str, Any]:
    return {
        "deepseek": {
            "api": "openai-completions",
            "baseUrl": "https://api.deepseek.com/v1",
            "apiKey": "",
            "models": [
                {
                    "id": "deepseek-v4-flash",
                    "name": "DeepSeek V4 Flash",
                    "contextWindow": 128_000,
                    "maxTokens": 8_000,
                    "reasoning": True,
                    "thinking_level": ["high", "max"],
                    "input": ["text"],
                },
                {
                    "id": "deepseek-v4",
                    "name": "DeepSeek V4",
                    "contextWindow": 128_000,
                    "maxTokens": 8_000,
                    "reasoning": True,
                    "thinking_level": ["high", "max"],
                    "input": ["text"],
                },
            ],
        }
    }


@dataclass
class Settings:
    selected_model: str = "deepseek/deepseek-v4-flash"
    providers: dict[str, Any] = field(default_factory=_default_providers)
    max_turns: int = 25


def _default_settings() -> Settings:
    return Settings()


def _infer_provider(base_url: str) -> str:
    url = base_url.lower()
    if "deepseek" in url:
        return "deepseek"
    if "openai" in url:
        return "openai"
    if "minimaxi" in url:
        return "minimax"
    return "custom"


def _split_selected_model(value: str) -> tuple[str, str]:
    if "/" in value:
        provider, model = value.split("/", 1)
        return provider, model
    return "deepseek", value


def load() -> Settings:
    """Load settings from ~/.coding-agent/settings.json."""
    if not _SETTINGS_PATH.exists():
        return _default_settings()
    try:
        data = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        s = _default_settings()
        migrated = False

        # New format
        if "selectedModel" in data:
            s.selected_model = data["selectedModel"]
        if "selected_model" in data:
            s.selected_model = data["selected_model"]
        if "providers" in data:
            s.providers = data["providers"]

        # Legacy format migration
        if "providers" not in data and any(k in data for k in ("model", "base_url", "api_key")):
            provider_id = _infer_provider(data.get("base_url", ""))
            model_id = data.get("model", _split_selected_model(s.selected_model)[1])
            old_thinking = data.get("thinking_level", "")
            thinking_levels: list[str] = []
            if old_thinking and old_thinking.lower() not in ("off", ""):
                thinking_levels.append(old_thinking.lower())
            if provider_id == "deepseek":
                for lvl in ("high", "max"):
                    if lvl not in thinking_levels:
                        thinking_levels.append(lvl)
            s.providers = {
                provider_id: {
                    "api": "openai-completions",
                    "baseUrl": data.get("base_url", "https://api.deepseek.com/v1"),
                    "apiKey": data.get("api_key", ""),
                    "models": [
                        {
                            "id": model_id,
                            "name": model_id,
                            "contextWindow": data.get("max_context_tokens", 128_000),
                            "maxTokens": data.get("max_output_tokens", 8_000),
                            "reasoning": bool(thinking_levels),
                            "thinking_level": thinking_levels or ["high", "max"],
                            "input": ["text"],
                        }
                    ],
                }
            }
            s.selected_model = f"{provider_id}/{model_id}"
            migrated = True

        if "max_turns" in data:
            s.max_turns = data["max_turns"]

        if migrated:
            save(s)
            logger.info("Migrated legacy settings to new provider/model format")

        return s
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load settings from %s: %s", _SETTINGS_PATH, exc)
        return _default_settings()


def save(s: Settings) -> None:
    """Save settings to ~/.coding-agent/settings.json."""
    _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "selectedModel": s.selected_model,
        "providers": s.providers,
        "max_turns": s.max_turns,
    }
    _SETTINGS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def resolve_api_key(settings: Settings) -> str:
    """Return the effective API key for the selected provider: provider > env."""
    provider_id, _ = _split_selected_model(settings.selected_model)
    provider = settings.providers.get(provider_id, {})
    return provider.get("apiKey") or os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""


def selected_model_config(settings: Settings) -> dict[str, Any] | None:
    """Return the config dict for the currently selected model."""
    provider_id, model_id = _split_selected_model(settings.selected_model)
    provider = settings.providers.get(provider_id, {})
    for model in provider.get("models", []):
        if model.get("id") == model_id:
            return model
    return None


def selected_thinking_level(settings: Settings) -> str | None:
    """Return the default thinking level for the selected model.

    Uses the last entry from the model's ``thinking_level`` array,
    which is assumed to be the strongest/highest level.
    """
    model_cfg = selected_model_config(settings)
    levels = model_cfg.get("thinking_level") if model_cfg else None
    if isinstance(levels, list) and levels:
        return levels[-1]
    return None
