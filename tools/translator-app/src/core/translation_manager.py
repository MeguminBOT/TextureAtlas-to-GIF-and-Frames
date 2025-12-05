"""Helper utilities for coordinating translation providers in the GUI and CLI."""

from __future__ import annotations

import re
import uuid
from typing import Dict, List, Optional, Tuple

from localization import QT_LANGUAGE_CHOICES
from .translation_provider_base import TranslationError, TranslationProvider
from providers import (
    DeepLTranslationProvider,
    GoogleTranslationProvider,
    LibreTranslationProvider,
)


class TranslationManager:
    """Coordinate translation providers and placeholder helpers."""

    def __init__(self) -> None:
        self.providers: Dict[str, TranslationProvider] = {
            "deepl": DeepLTranslationProvider(),
            "google": GoogleTranslationProvider(),
            "libretranslate": LibreTranslationProvider(),
        }

    def get_provider_language_choices(self, provider_key: Optional[str]) -> List[Tuple[str, str]]:
        """Return Qt language tuples limited to what the provider reports."""

        choices = QT_LANGUAGE_CHOICES
        if not provider_key:
            return choices

        provider = self.providers.get(provider_key)
        if not provider:
            return choices

        supported = provider.supported_codes()
        if not supported:
            return choices

        allowed = {code.upper() for code in supported}
        filtered = [entry for entry in choices if entry[0] in allowed]
        return filtered or choices

    def get_provider_name(self, key: Optional[str]) -> str:
        """Return a human-friendly name for a provider key."""
        if not key:
            return "Manual"
        provider = self.providers.get(key)
        return provider.name if provider else "Unknown"

    def is_provider_available(self, key: Optional[str]) -> tuple[bool, str]:
        """Report whether the requested provider can be used right now."""
        if not key:
            return False, "Machine translation disabled."
        provider = self.providers.get(key)
        if not provider:
            return False, "Selected provider is not available."
        return provider.is_available()

    def translate(
        self,
        provider_key: str,
        text: str,
        target_lang: str,
        source_lang: Optional[str] = None,
    ) -> str:
        """Delegate translation work to the provider after availability checks."""
        provider = self.providers.get(provider_key)
        if not provider:
            raise TranslationError("Selected translation provider is not supported.")
        available, reason = provider.is_available()
        if not available:
            raise TranslationError(reason)
        return provider.translate(text, target_lang, source_lang)

    @staticmethod
    def protect_placeholders(text: str) -> tuple[str, Dict[str, str]]:
        """Swap placeholders for temporary tokens providers will leave intact."""
        mapping: Dict[str, str] = {}

        def repl(match):
            token = f"PH{len(mapping)}{uuid.uuid4().hex[:8].upper()}"
            mapping[token] = match.group(0)
            return token

        protected_text = re.sub(r"\{[^}]*\}", repl, text)
        return protected_text, mapping

    @staticmethod
    def restore_placeholders(text: str, mapping: Dict[str, str]) -> str:
        """Swap placeholder tokens back to their original brace-wrapped text."""
        restored = text
        for token, original in mapping.items():
            restored = restored.replace(token, original)
        return restored


__all__ = ["TranslationManager"]
