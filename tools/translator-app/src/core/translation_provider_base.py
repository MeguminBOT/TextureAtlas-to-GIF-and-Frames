from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence


class TranslationError(Exception):
    """Raised when a machine translation request fails."""


class TranslationProvider(ABC):
    """Base class for translation providers. Serves as an abstract interface."""

    name: str = "Translation Provider"

    @abstractmethod
    def is_available(self) -> tuple[bool, str]:
        """Return availability flag and status message."""

    @abstractmethod
    def translate(self, text: str, target_lang: str, source_lang: Optional[str] = None) -> str:
        """Translate text and return the translated string."""

    def supported_codes(self) -> Optional[Sequence[str]]:
        """Return a list of supported language codes for UI filtering."""

        return None


__all__ = ["TranslationError", "TranslationProvider"]
