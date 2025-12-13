"""GUI helper components for the translator app."""

from .add_language_dialog import AddLanguageDialog
from .batch_unused_dialog import BatchUnusedStringsDialog
from .placeholder_highlighter import PlaceholderHighlighter
from .themes import apply_app_theme, theme_stylesheet
from .unused_strings_dialog import UnusedStringsDialog

__all__ = [
    "AddLanguageDialog",
    "BatchUnusedStringsDialog",
    "PlaceholderHighlighter",
    "UnusedStringsDialog",
    "apply_app_theme",
    "theme_stylesheet",
]
