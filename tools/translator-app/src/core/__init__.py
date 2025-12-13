"""Core classes and base abstractions for the translator app."""

from .translation_item import TranslationItem, TranslationMarker, MARKER_LABELS
from .translation_provider_base import TranslationError, TranslationProvider

__all__ = [
    "MARKER_LABELS",
    "TranslationError",
    "TranslationItem",
    "TranslationMarker",
    "TranslationProvider",
]
