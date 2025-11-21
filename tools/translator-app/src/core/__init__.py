"""Core classes and base abstractions for the translator app."""

from .translation_item import TranslationItem
from .translation_provider_base import TranslationError, TranslationProvider

__all__ = [
    "TranslationError",
    "TranslationProvider",
    "TranslationItem",
]
