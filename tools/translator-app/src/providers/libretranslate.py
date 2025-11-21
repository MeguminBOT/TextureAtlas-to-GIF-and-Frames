from __future__ import annotations

import os
from typing import Optional

try:
    import requests
except ImportError:  # pragma: no cover - optional dependency
    requests = None  # type: ignore

from core import TranslationError, TranslationProvider


class LibreTranslationProvider(TranslationProvider):
    """LibreTranslate provider; self-host for free or point LIBRETRANSLATE_ENDPOINT at a hosted node with an optional LIBRETRANSLATE_API_KEY."""

    name = "LibreTranslate"

    def __init__(self):
        self._endpoint = os.environ.get(
            "LIBRETRANSLATE_ENDPOINT", "http://127.0.0.1:5000/translate"
        )
        self._api_key = os.environ.get("LIBRETRANSLATE_API_KEY")

    def _map_language(self, code: Optional[str], *, is_target: bool) -> str:
        if not code:
            return "auto" if not is_target else "en"
        return code.lower()

    def is_available(self) -> tuple[bool, str]:
        if requests is None:
            return False, "Install the 'requests' package to enable machine translation."
        return True, f"Endpoint: {self._endpoint}"

    def translate(self, text: str, target_lang: str, source_lang: Optional[str] = None) -> str:
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
