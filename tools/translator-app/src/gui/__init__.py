"""GUI helper components for the translator app."""

from .add_language_dialog import AddLanguageDialog
from .placeholder_highlighter import PlaceholderHighlighter
from .themes import apply_app_theme, theme_stylesheet

__all__ = [
    "AddLanguageDialog",
    "PlaceholderHighlighter",
    "apply_app_theme",
    "theme_stylesheet",
]
