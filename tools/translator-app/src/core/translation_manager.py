"""Coordinate machine translation providers and placeholder preservation.

This module provides the TranslationManager class, which acts as the central
hub for interacting with translation providers (DeepL, Google, LibreTranslate).
It also supplies placeholder-protection helpers to ensure brace-wrapped tokens
survive round-trips through external APIs.
"""

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
    """Coordinate translation providers and protect placeholders during translation.

    This class manages registered translation providers, checks their availability,
    and offers static helpers to shield brace-delimited placeholders from being
    corrupted by external machine translation APIs.

    Attributes:
        providers: Mapping of provider keys ("deepl", "google", "libretranslate")
            to their corresponding TranslationProvider instances.
    """

    def __init__(self) -> None:
        self.providers: Dict[str, TranslationProvider] = {
            "deepl": DeepLTranslationProvider(),
            "google": GoogleTranslationProvider(),
            "libretranslate": LibreTranslationProvider(),
        }

    def get_provider_language_choices(
        self, provider_key: Optional[str]
    ) -> List[Tuple[str, str]]:
        """Return Qt language tuples limited to what the provider reports.

        Args:
            provider_key: Key identifying the provider (e.g., "deepl"), or None
                to return all Qt language choices.

        Returns:
            A list of (code, display_name) tuples for the provider's languages.
        """

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
        """Return a human-friendly name for a provider key.

        Args:
            key: Provider key such as "deepl" or "google", or None.

        Returns:
            The provider's display name, "Manual" if key is None, or "Unknown".
        """
        if not key:
            return "Manual"
        provider = self.providers.get(key)
        return provider.name if provider else "Unknown"

    def is_provider_available(self, key: Optional[str]) -> tuple[bool, str]:
        """Report whether the requested provider can be used right now.

        Args:
            key: Provider key such as "deepl" or "google", or None.

        Returns:
            A tuple (available, message) indicating readiness and reason.
        """
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
        """Translate text using the specified provider.

        Args:
            provider_key: Key identifying the provider ("deepl", "google", etc.).
            text: Source text to translate.
            target_lang: Target language code.
            source_lang: Optional source language code; auto-detected if omitted.

        Returns:
            The translated text.

        Raises:
            TranslationError: If the provider is unavailable or the request fails.
        """
        provider = self.providers.get(provider_key)
        if not provider:
            raise TranslationError("Selected translation provider is not supported.")
        available, reason = provider.is_available()
        if not available:
            raise TranslationError(reason)
        return provider.translate(text, target_lang, source_lang)

    @staticmethod
    def protect_placeholders(text: str) -> tuple[str, Dict[str, str]]:
        """Replace brace-delimited placeholders with unique tokens.

        Machine translation APIs may corrupt placeholders like ``{value}``.
        This method replaces them with alphanumeric tokens that survive
        translation, returning a mapping to restore them afterward.

        Args:
            text: The source string containing placeholders.

        Returns:
            A tuple of (protected_text, mapping) where mapping maps tokens
            back to their original placeholder strings.
        """
        mapping: Dict[str, str] = {}

        def repl(match):
            token = f"PH{len(mapping)}{uuid.uuid4().hex[:8].upper()}"
            mapping[token] = match.group(0)
            return token

        protected_text = re.sub(r"\{[^}]*\}", repl, text)
        return protected_text, mapping

    @staticmethod
    def restore_placeholders(text: str, mapping: Dict[str, str]) -> str:
        """Replace tokens back to their original brace-wrapped placeholders.

        Args:
            text: Translated text containing placeholder tokens.
            mapping: Token-to-placeholder mapping produced by protect_placeholders.

        Returns:
            The text with tokens replaced by their original placeholders.
        """
        restored = text
        for token, original in mapping.items():
            restored = restored.replace(token, original)
        return restored


__all__ = ["TranslationManager"]
