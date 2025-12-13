"""GUI helper components for the translator app."""

from .add_language_dialog import AddLanguageDialog
from .batch_unused_dialog import BatchUnusedStringsDialog
from .placeholder_highlighter import PlaceholderHighlighter
from .shortcuts_dialog import ShortcutsDialog, DEFAULT_SHORTCUTS, SHORTCUT_LABELS
from .themes import apply_app_theme, theme_stylesheet
from .unused_strings_dialog import UnusedStringsDialog

__all__ = [
    "AddLanguageDialog",
    "BatchUnusedStringsDialog",
    "DEFAULT_SHORTCUTS",
    "PlaceholderHighlighter",
    "SHORTCUT_LABELS",
    "ShortcutsDialog",
    "UnusedStringsDialog",
    "apply_app_theme",
    "theme_stylesheet",
]
