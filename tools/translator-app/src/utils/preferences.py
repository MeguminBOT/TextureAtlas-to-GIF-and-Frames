from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

_PREFERENCES_PATH = Path.home() / ".textureatlastoolbox_translator.json"


def load_preferences() -> Dict[str, Any]:
    """Return stored user preferences or defaults when unavailable."""

    if not _PREFERENCES_PATH.exists():
        return {}
    try:
        raw = _PREFERENCES_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_preferences(preferences: Dict[str, Any]) -> None:
    """Persist user preferences to disk."""

    try:
        _PREFERENCES_PATH.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(preferences, indent=2, sort_keys=True)
        _PREFERENCES_PATH.write_text(serialized, encoding="utf-8")
    except OSError:
        pass


__all__ = ["load_preferences", "save_preferences"]
