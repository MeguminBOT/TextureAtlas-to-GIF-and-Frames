"""Shared helpers for reading and persisting the translator language registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

RegistryDict = Dict[str, Dict[str, str]]

_REGISTRY_PATH = Path(__file__).resolve().parent / "language_registry.json"
_FALLBACK_REGISTRY: RegistryDict = {
    "en": {"name": "English", "english_name": "English", "quality": "native"}
}

LANGUAGE_REGISTRY: RegistryDict = {}


def get_registry_path() -> Path:
    """Return the on-disk path for the registry file."""

    return _REGISTRY_PATH


def _sanitize_registry(raw: RegistryDict) -> RegistryDict:
    sanitized: RegistryDict = {}
    for code, meta in sorted(raw.items(), key=lambda item: item[0]):
        if not isinstance(code, str):
            continue
        normalized_code = code.strip()
        if not normalized_code:
            continue
        if not isinstance(meta, dict):
            continue
        name = str(meta.get("name", normalized_code))
        english_name = str(meta.get("english_name", name))
        quality = str(meta.get("quality", "unknown"))
        sanitized[normalized_code] = {
            "name": name,
            "english_name": english_name,
            "quality": quality,
        }
    return sanitized


def _write_registry_file(registry: RegistryDict) -> None:
    _REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REGISTRY_PATH.write_text(
        json.dumps(registry, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )


def _read_registry_from_disk() -> RegistryDict:
    if _REGISTRY_PATH.exists():
        try:
            raw = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                sanitized = _sanitize_registry(raw) or _sanitize_registry(_FALLBACK_REGISTRY)
                return sanitized
        except Exception:
            pass
    fallback = _sanitize_registry(_FALLBACK_REGISTRY)
    _write_registry_file(fallback)
    return fallback


def load_language_registry(force_reload: bool = False) -> RegistryDict:
    """Load the registry from disk and optionally force a reload."""

    if LANGUAGE_REGISTRY and not force_reload:
        return LANGUAGE_REGISTRY

    LANGUAGE_REGISTRY.clear()
    LANGUAGE_REGISTRY.update(_read_registry_from_disk())
    return LANGUAGE_REGISTRY


def reload_language_registry() -> RegistryDict:
    """Force a reload of the registry file from disk."""

    return load_language_registry(force_reload=True)


def save_language_registry(registry: RegistryDict | None = None) -> RegistryDict:
    """Persist the provided registry (or the global one) back to disk."""

    target = registry if registry is not None else LANGUAGE_REGISTRY
    sanitized = _sanitize_registry(target)
    LANGUAGE_REGISTRY.clear()
    LANGUAGE_REGISTRY.update(sanitized)
    _write_registry_file(LANGUAGE_REGISTRY)
    return LANGUAGE_REGISTRY


# Load registry immediately so other modules can import LANGUAGE_REGISTRY directly.
load_language_registry()
