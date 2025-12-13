"""LibreTranslate provider implementation.

LibreTranslate is a free, self-hostable translation API. Point
LIBRETRANSLATE_ENDPOINT at your instance; optionally set LIBRETRANSLATE_API_KEY
if your host requires authentication.
"""

from __future__ import annotations

import os
from typing import Optional

try:
    import requests
except ImportError:  # pragma: no cover - optional dependency
    requests = None  # type: ignore

from core import TranslationError, TranslationProvider


class LibreTranslationProvider(TranslationProvider):
    """LibreTranslate translation provider.

    Self-host LibreTranslate (e.g., via Docker) for free translations.
    Configure LIBRETRANSLATE_ENDPOINT and optionally LIBRETRANSLATE_API_KEY.

    Attributes:
        name: Display name shown in the provider dropdown.
    """

    name = "LibreTranslate"

    def __init__(self):
        """Initialize the provider with configured endpoint and API key."""
        self._endpoint = os.environ.get(
            "LIBRETRANSLATE_ENDPOINT", "http://127.0.0.1:5000/translate"
        )
        self._api_key = os.environ.get("LIBRETRANSLATE_API_KEY")

    def _map_language(self, code: Optional[str], *, is_target: bool) -> str:
        """Normalize a language code to LibreTranslate's expected format.

        Args:
            code: ISO language code.
            is_target: True if this is the target language.

        Returns:
            The normalized lowercase code, or 'auto'/'en' fallback.
        """
        if not code:
            return "auto" if not is_target else "en"
        return code.lower()

    def is_available(self) -> tuple[bool, str]:
        if requests is None:
            return False, "Install the 'requests' package to enable machine translation."
        return True, f"Endpoint: {self._endpoint}"

    def translate(self, text: str, target_lang: str, source_lang: Optional[str] = None) -> str:
        """Translate text using the LibreTranslate API.

        Args:
            text: Source text to translate.
            target_lang: Target language code.
            source_lang: Optional source language code.

        Returns:
            The translated string.

        Raises:
            TranslationError: On API errors or if requests is unavailable.
        """
        if not text.strip():
            return ""
        if requests is None:
            raise TranslationError("The 'requests' package is required for LibreTranslate.")

        mapped_target = self._map_language(target_lang, is_target=True)
        mapped_source = self._map_language(source_lang, is_target=False)

        payload = {
            "q": text,
            "source": mapped_source,
            "target": mapped_target,
            "format": "text",
        }
        if self._api_key:
            payload["api_key"] = self._api_key

        try:
            response = requests.post(self._endpoint, data=payload, timeout=15)
        except Exception as exc:
            raise TranslationError(f"LibreTranslate request failed: {exc}") from exc

        if response.status_code >= 400:
            raise TranslationError(f"LibreTranslate error {response.status_code}: {response.text}")

        try:
            data = response.json()
        except ValueError as exc:
            raise TranslationError("Failed to decode LibreTranslate response.") from exc

        if "error" in data:
            raise TranslationError(f"LibreTranslate error: {data['error']}")

        translated_text = data.get("translatedText", "")
        return translated_text


__all__ = ["LibreTranslationProvider"]
