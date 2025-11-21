from __future__ import annotations

import os
from typing import Optional, Sequence

try:
    import requests
except ImportError:  # pragma: no cover - optional dependency
    requests = None  # type: ignore

from core import TranslationError, TranslationProvider


class DeepLTranslationProvider(TranslationProvider):
    """DeepL Translation API provider; works with free (500k chars/month cap) or Pro plans via the DEEPL_API_KEY secret and optional custom endpoint."""

    name = "DeepL"
    _SUPPORTED_CODES = {
        "BG",
        "CS",
        "DA",
        "DE",
        "EL",
        "EN",
        "ES",
        "ET",
        "FI",
        "FR",
        "HU",
        "ID",
        "IT",
        "JA",
        "KO",
        "LT",
        "LV",
        "NB",
        "NL",
        "PL",
        "PT",
        "RO",
        "RU",
        "SK",
        "SL",
        "SV",
        "TR",
        "UK",
        "ZH",
    }

    def __init__(self):
        self._endpoint = os.environ.get(
            "DEEPL_API_ENDPOINT", "https://api-free.deepl.com/v2/translate"
        )

    @staticmethod
    def _api_key() -> Optional[str]:
        return os.environ.get("DEEPL_API_KEY")

    def is_available(self) -> tuple[bool, str]:
        if requests is None:
            return False, "Install the 'requests' package to enable machine translation."
        if not self._api_key():
            return False, "Set the DEEPL_API_KEY environment variable to enable DeepL."
        return True, "DeepL ready"

    def _map_language(self, code: Optional[str], *, is_target: bool) -> Optional[str]:
        if not code:
            return None
        normalized = code.upper()

        if normalized not in self._SUPPORTED_CODES and normalized not in {
            "EN-US",
            "EN-GB",
            "PT-BR",
            "PT-PT",
        }:
            raise TranslationError(f"DeepL does not support the language code '{code}'.")

        if normalized == "EN" and is_target:
            return os.environ.get("DEEPL_TARGET_EN_VARIANT", "EN-US").upper()
        if normalized == "PT" and is_target:
            return os.environ.get("DEEPL_TARGET_PT_VARIANT", "PT-BR").upper()
        if normalized == "EN" and not is_target:
            return "EN"
        if normalized == "PT" and not is_target:
            return "PT"
        return normalized

    def translate(self, text: str, target_lang: str, source_lang: Optional[str] = None) -> str:
        if not text.strip():
            return ""
        api_key = self._api_key()
        if not api_key:
            raise TranslationError("DEEPL_API_KEY is not configured.")
        if requests is None:
            raise TranslationError("The 'requests' package is required for DeepL translations.")

        mapped_target = self._map_language(target_lang, is_target=True)
        mapped_source = self._map_language(source_lang, is_target=False)

        payload = {"text": text, "target_lang": mapped_target}
        if mapped_source:
            payload["source_lang"] = mapped_source

        headers = {"Authorization": f"DeepL-Auth-Key {api_key}"}

        try:
            response = requests.post(self._endpoint, data=payload, headers=headers, timeout=15)
        except Exception as exc:  # pragma: no cover - network error surface to user
            raise TranslationError(f"DeepL request failed: {exc}") from exc

        if response.status_code >= 400:
            raise TranslationError(f"DeepL error {response.status_code}: {response.text}")

        try:
            data = response.json()
        except ValueError as exc:
            raise TranslationError("Failed to decode DeepL response.") from exc

        translations = data.get("translations") or []
        if not translations:
            raise TranslationError("DeepL returned no translation result.")

        return translations[0].get("text", "")

    def supported_codes(self) -> Optional[Sequence[str]]:
        return sorted(self._SUPPORTED_CODES)


__all__ = ["DeepLTranslationProvider"]
