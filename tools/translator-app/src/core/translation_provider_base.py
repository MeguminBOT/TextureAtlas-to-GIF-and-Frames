"""Abstract base class and error type for machine translation providers.

This module defines the TranslationProvider interface that all provider
implementations (DeepL, Google, LibreTranslate) must satisfy, along with
the common exception type raised on translation failures.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence


class TranslationError(Exception):
    """Raised when a machine translation request fails.

    This may indicate network issues, invalid API keys, unsupported languages,
    or malformed responses from the translation service.
    """


class TranslationProvider(ABC):
    """Abstract interface for machine translation providers.

    Subclasses must implement is_available and translate methods. The optional
    supported_codes method enables filtering language dropdowns in the UI.

    Attributes:
        name: Human-readable provider name displayed in the UI.
    """

    name: str = "Translation Provider"

    @abstractmethod
    def is_available(self) -> tuple[bool, str]:
        """Check whether the provider is configured and ready to use.

        Returns:
            A tuple (available, message). If available is False, message
            describes what is missing (e.g., API key not set).
        """

    @abstractmethod
    def translate(self, text: str, target_lang: str, source_lang: Optional[str] = None) -> str:
        """Translate text to the target language.

        Args:
            text: Source text to translate.
            target_lang: Target language code (provider-specific format).
            source_lang: Optional source language code; auto-detect if omitted.

        Returns:
            The translated string.

        Raises:
            TranslationError: If the translation request fails.
        """

    def supported_codes(self) -> Optional[Sequence[str]]:
        """Return language codes this provider supports, or None for all.

        When not None, the UI will filter language dropdowns to show only
        the intersection of Qt's language list and this set.
        """
        return None


__all__ = ["TranslationError", "TranslationProvider"]
