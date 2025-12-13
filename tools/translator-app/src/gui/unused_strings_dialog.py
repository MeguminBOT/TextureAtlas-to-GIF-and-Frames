#!/usr/bin/env python3
"""Dialog for displaying and handling vanished strings in a single .ts file.

Qt's lupdate tool marks source strings no longer found in code as "vanished".
This dialog shows those strings for a single file and offers save/remove options.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)


class UnusedStringsDialog(QDialog):
    """Dialog showing vanished strings with options to save and remove them.

    Displays translation strings marked as vanished (no longer in source code),
    allowing users to optionally save them for reference before removal.

    Attributes:
        unused_strings: List of (source, translation) tuples for vanished entries.
        save_requested: Whether user chose to save vanished strings to a file.
        saved_path: Path where vanished strings were saved, if any.
    """

    def __init__(
        self,
        parent,
        unused_strings: List[Tuple[str, str]],
        ts_filename: str,
    ) -> None:
        """Initialize the vanished-strings dialog.

        Args:
            parent: Parent widget.
            unused_strings: List of (source, translation) tuples for vanished entries.
            ts_filename: Name of the .ts file being processed.
        """
        super().__init__(parent)
        self.unused_strings = unused_strings
        self.ts_filename = ts_filename
        self.save_requested = False
        self.saved_path: str = ""

        self.setWindowTitle("Vanished Translation Strings Detected")
        self.setMinimumSize(600, 400)
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the dialog layout with list widget and action buttons."""
        layout = QVBoxLayout(self)

        # Header message
        count = len(self.unused_strings)
        header = QLabel(
            f"<b>{count} vanished translation string{'s' if count != 1 else ''} found.</b><br>"
            'These are marked <code>type="vanished"</code> by Qt\'s lupdate tool,<br>'
            "meaning the source strings no longer exist in the code."
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        # List of unused strings
        self.string_list = QListWidget()
        self.string_list.setAlternatingRowColors(True)
        for source, translation in self.unused_strings:
            # Show source with translation preview if available
            display = source[:80]
            if len(source) > 80:
                display += "..."
            if translation.strip():
                trans_preview = translation[:40]
                if len(translation) > 40:
                    trans_preview += "..."
                display += f"  →  {trans_preview}"
            item = QListWidgetItem(display)
            item.setToolTip(
                f"Source: {source}\n\nTranslation: {translation or '(empty)'}"
            )
            self.string_list.addItem(item)
        layout.addWidget(self.string_list, 1)

        # Info label
        info_label = QLabel(
            "<i>You can save these strings to a text file for reference before they are removed.</i>"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Button row
        button_layout = QHBoxLayout()

        save_btn = QPushButton("Save to File && Remove")
        save_btn.setToolTip(
            "Save vanished strings to a .txt file, then remove them from the editor"
        )
        save_btn.clicked.connect(self._save_and_accept)
        button_layout.addWidget(save_btn)

        remove_btn = QPushButton("Remove Without Saving")
        remove_btn.setToolTip("Remove vanished strings without saving them")
        remove_btn.clicked.connect(self.accept)
        button_layout.addWidget(remove_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setToolTip("Keep all strings (do not remove unused entries)")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _save_and_accept(self) -> None:
        """Prompt user for a save path, write the report, and accept."""
        base_name = Path(self.ts_filename).stem
        suggested_name = f"{base_name}_unused_strings.txt"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Unused Strings",
            suggested_name,
            "Text Files (*.txt);;All Files (*)",
        )

        if not file_path:
            return  # User cancelled save dialog

        try:
            self._write_unused_strings(file_path)
            self.save_requested = True
            self.saved_path = file_path
            self.accept()
        except Exception as exc:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self,
                "Save Failed",
                f"Failed to save unused strings:\n{exc}",
            )

    def _write_unused_strings(self, file_path: str) -> None:
        """Write the vanished strings report to a text file.

        Args:
            file_path: Destination file path.
        """
        lines = [
            f"# Unused Translation Strings from {self.ts_filename}",
            "# Generated by Translation Editor",
            f"# Total: {len(self.unused_strings)} entries",
            "",
            "=" * 60,
            "",
        ]

        for i, (source, translation) in enumerate(self.unused_strings, 1):
            lines.append(f"[{i}] SOURCE:")
            lines.append(source)
            lines.append("")
            lines.append("TRANSLATION:")
            lines.append(translation if translation.strip() else "(empty)")
            lines.append("")
            lines.append("-" * 60)
            lines.append("")

        Path(file_path).write_text("\n".join(lines), encoding="utf-8")


__all__ = ["UnusedStringsDialog"]
