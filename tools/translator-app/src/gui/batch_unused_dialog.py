#!/usr/bin/env python3
"""Dialog for batch cleanup of vanished translation strings across multiple files.

Qt's lupdate tool marks source strings that no longer exist in code as
"vanished". This dialog displays those strings across multiple .ts files
and lets users optionally save them before removal.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import xml.etree.ElementTree as ET

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)


class BatchUnusedStringsDialog(QDialog):
    """Dialog for cleaning up vanished strings across multiple translation files.

    Shows a tree view of files with their vanished strings (marked by lupdate
    as no longer existing in source code), allowing users to save them to a
    file and remove them from the .ts files.

    Attributes:
        unused_by_file: Dictionary mapping file paths to lists of (source, translation) tuples.
        save_requested: Whether user chose to save vanished strings to a file.
        saved_path: Path where vanished strings were saved, if any.
        files_cleaned: List of file paths that were cleaned.
    """

    def __init__(
        self,
        parent,
        unused_by_file: Dict[Path, List[Tuple[str, str]]],
        translations_dir: Path,
    ) -> None:
        """Initialize the batch cleanup dialog.

        Args:
            parent: Parent widget.
            unused_by_file: Mapping from .ts file paths to their vanished
                (source, translation) pairs.
            translations_dir: Base directory for translation files (used when
                suggesting a save location).
        """
        super().__init__(parent)
        self.unused_by_file = unused_by_file
        self.translations_dir = translations_dir
        self.save_requested = False
        self.saved_path: str = ""
        self.files_cleaned: List[Path] = []

        total_strings = sum(len(strings) for strings in unused_by_file.values())
        self.setWindowTitle(f"Vanished Strings Detected ({total_strings} total)")
        self.setMinimumSize(700, 500)
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the dialog layout with tree view and action buttons."""
        layout = QVBoxLayout(self)

        # Header message
        file_count = len(self.unused_by_file)
        total_strings = sum(len(strings) for strings in self.unused_by_file.values())
        header = QLabel(
            f"<b>{total_strings} vanished string{'s' if total_strings != 1 else ''} "
            f"found across {file_count} file{'s' if file_count != 1 else ''}.</b><br>"
            "These translations are marked as <code>type=\"vanished\"</code> by Qt's lupdate tool,<br>"
            "meaning the source strings no longer exist in the code. They can be safely removed."
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        # Tree view of files and strings
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["File / Source String", "Translation Preview"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setColumnWidth(0, 400)

        for file_path, strings in sorted(self.unused_by_file.items()):
            file_item = QTreeWidgetItem([file_path.name, f"{len(strings)} unused"])
            file_item.setToolTip(0, str(file_path))
            file_item.setExpanded(False)

            for source, translation in strings:
                source_preview = source[:60]
                if len(source) > 60:
                    source_preview += "..."
                trans_preview = translation[:40] if translation.strip() else "(empty)"
                if len(translation) > 40:
                    trans_preview += "..."

                string_item = QTreeWidgetItem([source_preview, trans_preview])
                string_item.setToolTip(0, source)
                string_item.setToolTip(1, translation or "(empty)")
                file_item.addChild(string_item)

            self.tree.addTopLevelItem(file_item)

        layout.addWidget(self.tree, 1)

        # Info label
        info_label = QLabel(
            "<i>You can save all unused strings to a text file for reference before removal.</i>"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Button row
        button_layout = QHBoxLayout()

        save_btn = QPushButton("Save to File && Clean All")
        save_btn.setToolTip(
            "Save all unused strings to a .txt file, then remove them from .ts files"
        )
        save_btn.clicked.connect(self._save_and_clean)
        button_layout.addWidget(save_btn)

        clean_btn = QPushButton("Clean All Without Saving")
        clean_btn.setToolTip("Remove all unused strings from .ts files without saving")
        clean_btn.clicked.connect(self._clean_only)
        button_layout.addWidget(clean_btn)

        skip_btn = QPushButton("Skip (Keep All)")
        skip_btn.setToolTip("Keep all strings, do not remove anything")
        skip_btn.clicked.connect(self.reject)
        button_layout.addWidget(skip_btn)

        layout.addLayout(button_layout)

    def _save_and_clean(self) -> None:
        """Prompt user for a file path, save vanished strings, then clean."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suggested_name = f"unused_strings_{timestamp}.txt"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Unused Strings",
            str(self.translations_dir / suggested_name),
            "Text Files (*.txt);;All Files (*)",
        )

        if not file_path:
            return  # User cancelled save dialog

        try:
            self._write_unused_strings(file_path)
            self.save_requested = True
            self.saved_path = file_path
            self._clean_files()
            self.accept()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Save Failed",
                f"Failed to save unused strings:\n{exc}",
            )

    def _clean_only(self) -> None:
        """Remove vanished strings from all files without saving."""
        self._clean_files()
        self.accept()

    def _write_unused_strings(self, file_path: str) -> None:
        """Write all vanished strings to a text file for archival.

        Args:
            file_path: Destination file path.
        """
        lines = [
            "# Unused Translation Strings Report",
            "# Generated by Translation Editor",
            f"# Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"# Total files: {len(self.unused_by_file)}",
            f"# Total strings: {sum(len(s) for s in self.unused_by_file.values())}",
            "",
            "=" * 70,
            "",
        ]

        for file_path_key, strings in sorted(self.unused_by_file.items()):
            lines.append(f"FILE: {file_path_key.name}")
            lines.append(f"Path: {file_path_key}")
            lines.append(f"Unused strings: {len(strings)}")
            lines.append("-" * 70)

            for i, (source, translation) in enumerate(strings, 1):
                lines.append(f"  [{i}] SOURCE:")
                # Indent multi-line sources
                for src_line in source.split("\n"):
                    lines.append(f"      {src_line}")
                lines.append("")
                lines.append("      TRANSLATION:")
                if translation.strip():
                    for trans_line in translation.split("\n"):
                        lines.append(f"      {trans_line}")
                else:
                    lines.append("      (empty)")
                lines.append("")

            lines.append("=" * 70)
            lines.append("")

        Path(file_path).write_text("\n".join(lines), encoding="utf-8")

    def _clean_files(self) -> None:
        """Remove vanished strings from each affected .ts file."""
        for file_path, unused_strings in self.unused_by_file.items():
            if not file_path.exists():
                continue

            try:
                self._remove_vanished_from_file(file_path)
                self.files_cleaned.append(file_path)
            except Exception:
                # Log error but continue with other files
                pass

    def _remove_vanished_from_file(self, file_path: Path) -> None:
        """Remove all vanished/obsolete strings from a .ts file.

        Strings that exist as active entries elsewhere (moved to another context)
        are preserved since they're not truly unused.

        Args:
            file_path: Path to the .ts file.
        """
        tree = ET.parse(file_path)
        root = tree.getroot()

        # First, collect all active (non-vanished/obsolete) source strings
        active_sources: set[str] = set()
        for message in root.iter("message"):
            translation_elem = message.find("translation")
            trans_type = translation_elem.get("type", "") if translation_elem is not None else ""
            if trans_type not in ("vanished", "obsolete"):
                source_elem = message.find("source")
                if source_elem is not None and source_elem.text:
                    active_sources.add(source_elem.text)

        # Find and remove messages marked as vanished or obsolete (but not moved)
        for context in root.findall("context"):
            messages_to_remove = []
            for message in context.findall("message"):
                translation_elem = message.find("translation")
                if translation_elem is not None:
                    trans_type = translation_elem.get("type", "")
                    if trans_type in ("vanished", "obsolete"):
                        source_elem = message.find("source")
                        source = source_elem.text if source_elem is not None and source_elem.text else ""
                        # Only remove if the string doesn't exist as an active entry
                        if source not in active_sources:
                            messages_to_remove.append(message)

            for message in messages_to_remove:
                context.remove(message)

            # Remove empty contexts
            remaining_messages = context.findall("message")
            if not remaining_messages:
                root.remove(context)

        # Write back with proper formatting
        ET.indent(tree, space="    ")
        tree.write(file_path, encoding="utf-8", xml_declaration=True)


__all__ = ["BatchUnusedStringsDialog"]
