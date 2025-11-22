"""Localization datasets and operations used across the translator app."""

from __future__ import annotations

from .operations import (
    CommandResult,
    CommandRunner,
    LocalizationOperations,
    OperationResult,
    TranslationPaths,
    normalize_languages,
    resolve_language_code,
)
from .qt_languages import QT_LANGUAGE_CHOICES
from .registry import (
    LANGUAGE_REGISTRY,
    RegistryDict,
    get_registry_path,
    load_language_registry,
    reload_language_registry,
    save_language_registry,
)

__all__ = [
    "CommandResult",
    "CommandRunner",
    "LocalizationOperations",
    "OperationResult",
    "TranslationPaths",
    "QT_LANGUAGE_CHOICES",
    "LANGUAGE_REGISTRY",
    "RegistryDict",
    "get_registry_path",
    "load_language_registry",
    "reload_language_registry",
    "save_language_registry",
    "normalize_languages",
    "resolve_language_code",
]
