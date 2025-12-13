"""Google Cloud Translation API provider implementation.

Requires a Google Cloud project with billing enabled. Configure via the
GOOGLE_TRANSLATE_API_KEY environment variable.
"""

from __future__ import annotations

import html
import os
from typing import Optional, Sequence

try:
    import requests
except ImportError:  # pragma: no cover - optional dependency
    requests = None  # type: ignore

from core import TranslationError, TranslationProvider


class GoogleTranslationProvider(TranslationProvider):
    """Google Cloud Translation API provider.

    Requires GOOGLE_TRANSLATE_API_KEY. This uses the Cloud Translation
    Basic (v2) endpoint and bills per character.

    Attributes:
        name: Display name shown in the provider dropdown.
    """

    name = "Google Translate"
    _ENDPOINT = "https://translation.googleapis.com/language/translate/v2"

    def __init__(self):
        """Initialize the provider with supported language codes."""
        self._supported_codes = {
            "EN",
            "ES",
            "DE",
            "FR",
            "IT",
            "JA",
            "KO",
            "PL",
            "PT",
            "RU",
            "TR",
            "ZH",
        }

    @staticmethod
    def _api_key() -> Optional[str]:
        """Return the GOOGLE_TRANSLATE_API_KEY value from the environment."""
        return os.environ.get("GOOGLE_TRANSLATE_API_KEY")

    def is_available(self) -> tuple[bool, str]:
        if requests is None:
            return False, "Install the 'requests' package to enable machine translation."
        if not self._api_key():
            return False, "Set GOOGLE_TRANSLATE_API_KEY to enable Google Translate."
        return True, "Google Translate ready"

    def _map_language(self, code: Optional[str]) -> Optional[str]:
        """Normalize a language code to Google's expected lowercase format.

        Args:
            code: ISO language code.

        Returns:
            The normalized lowercase code, or None if code is empty.

        Raises:
            TranslationError: If the code is not in the supported set.
        """
        if not code:
            return None
        normalized = code.upper()
        if normalized not in self._supported_codes:
            raise TranslationError(f"Google Translate does not support '{code}'.")
        return normalized.lower()

    def translate(self, text: str, target_lang: str, source_lang: Optional[str] = None) -> str:
        """Translate text using the Google Cloud Translation API.

        Args:
            text: Source text to translate.
            target_lang: Target language code.
            source_lang: Optional source language code.

        Returns:
            The translated string.

        Raises:
            TranslationError: On API errors or misconfiguration.
        """
        if not text.strip():
            return ""
        api_key = self._api_key()
        if not api_key:
            raise TranslationError("GOOGLE_TRANSLATE_API_KEY is not configured.")
        if requests is None:
            raise TranslationError("The 'requests' package is required for Google Translate.")

        mapped_target = self._map_language(target_lang)
        mapped_source = self._map_language(source_lang)

        payload = {
            "q": text,
            "target": mapped_target,
            "format": "text",
        }
        if mapped_source:
            payload["source"] = mapped_source

        params = {"key": api_key}

        try:
            response = requests.post(self._ENDPOINT, params=params, json=payload, timeout=15)
        except Exception as exc:  # pragma: no cover - network issues surface to user
            raise TranslationError(f"Google Translate request failed: {exc}") from exc

        if response.status_code >= 400:
            raise TranslationError(
                f"Google Translate error {response.status_code}: {response.text}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise TranslationError("Failed to decode Google Translate response.") from exc

        translations = data.get("data", {}).get("translations") or []
        if not translations:
            raise TranslationError("Google Translate returned no translation result.")

        translated_text = translations[0].get("translatedText", "")
        return html.unescape(translated_text)

    def supported_codes(self) -> Optional[Sequence[str]]:
        """Return the list of language codes supported by this provider."""
        return sorted(self._supported_codes)


__all__ = ["GoogleTranslationProvider"]
