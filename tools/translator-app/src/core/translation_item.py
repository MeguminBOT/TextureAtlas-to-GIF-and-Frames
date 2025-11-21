from __future__ import annotations

import re
from typing import Dict, List, Tuple


class TranslationItem:
    """Represents a single translation entry or group of identical entries."""

    def __init__(
        self,
        source: str,
        translation: str = "",
        context: str = "",
        filename: str = "",
        line: int = 0,
    ) -> None:
        self.source = source
        self.translation = translation or ""
        self.contexts = [context] if context else []
        self.locations: List[Tuple[str, int]] = [(filename, line)] if filename else []
        self.is_translated = bool(self.translation.strip())

    def add_context(self, context: str, filename: str = "", line: int = 0) -> None:
        """Track another context that reuses this string."""
        if context and context not in self.contexts:
            self.contexts.append(context)
        if filename and (filename, line) not in self.locations:
            self.locations.append((filename, line))

    def get_context_display(self) -> str:
        """Return a short label for list views."""
        if len(self.contexts) == 1:
            return self.contexts[0]
        if len(self.contexts) > 1:
            return f"{self.contexts[0]} (+{len(self.contexts) - 1} more)"
        return "Unknown"

    def get_all_contexts_info(self) -> str:
        """Return an expanded list of contexts/locations."""
        info_lines = []
        for i, context in enumerate(self.contexts):
            if i < len(self.locations):
                filename, line = self.locations[i]
                info_lines.append(f"Context: {context}\nFile: {filename}:{line}")
            else:
                info_lines.append(f"Context: {context}")
        return "\n\n".join(info_lines)

    @property
    def context(self) -> str:
        return self.contexts[0] if self.contexts else ""

    @property
    def filename(self) -> str:
        return self.locations[0][0] if self.locations else ""

    @property
    def line(self) -> int:
        return self.locations[0][1] if self.locations else 0

    def has_placeholders(self) -> bool:
        return bool(re.search(r"\{[^}]*\}", self.source))

    def get_placeholders(self) -> List[str]:
        return re.findall(r"\{[^}]*\}", self.source)

    def preview_with_placeholders(self, placeholder_values: Dict[str, str]) -> str:
        if not self.translation:
            return ""

        preview = self.translation
        placeholders = self.get_placeholders()

        for placeholder in placeholders:
            key = placeholder.strip("{}")
            if key in placeholder_values:
                preview = preview.replace(placeholder, placeholder_values[key])
            elif placeholder in placeholder_values:
                preview = preview.replace(placeholder, placeholder_values[placeholder])
            else:
                preview = preview.replace(placeholder, f"[{key}]")

        return preview

    def validate_translation(self) -> tuple[bool, str]:
        if not self.translation.strip():
            return True, ""

        source_placeholders = set(self.get_placeholders())
        translation_placeholders = set(re.findall(r"\{[^}]*\}", self.translation))

        missing_placeholders = source_placeholders - translation_placeholders
        extra_placeholders = translation_placeholders - source_placeholders

        errors = []
        if missing_placeholders:
            errors.append(f"Missing placeholders: {', '.join(missing_placeholders)}")
        if extra_placeholders:
            errors.append(f"Extra placeholders: {', '.join(extra_placeholders)}")

        if errors:
            return False, "; ".join(errors)
        return True, ""


__all__ = ["TranslationItem"]
