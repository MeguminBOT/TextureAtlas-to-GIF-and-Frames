"""Manage tab widget for translation file operations.

Provides a UI for running Qt localization commands (lupdate, lrelease),
managing the language registry, checking translation progress, and cleaning
up vanished strings across multiple .ts files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
import xml.etree.ElementTree as ET

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QFileDialog,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QVBoxLayout,
    QWidget,
)

from .add_language_dialog import AddLanguageDialog
from .batch_unused_dialog import BatchUnusedStringsDialog
from localization import (
    LANGUAGE_REGISTRY,
    LocalizationOperations,
    OperationResult,
    save_language_registry,
)
from utils import BackgroundTaskWorker


class ManageTab(QWidget):
    """Widget tab for managing translation files and running localization tasks.

    Provides controls to select languages, run lupdate/lrelease, regenerate
    resource files, and view translation progress in a status table.

    Attributes:
        localization_ops: Backend helper for running translation commands.
        thread_pool: Qt thread pool for background task execution.
        language_list_widget: List widget displaying registered languages.
        manage_table: Table showing translation progress per language.
        manage_log_view: Text area displaying command output.
    """

    def __init__(
        self,
        *,
        parent: QWidget,
        localization_ops: LocalizationOperations,
        thread_pool: QThreadPool,
        status_bar: Optional[QStatusBar] = None,
        on_translations_dir_changed: Optional[Callable[[Path], None]] = None,
        open_ts_callback: Optional[Callable[[Path], None]] = None,
    ) -> None:
        """Initialize the manage tab.

        Args:
            parent: Parent widget.
            localization_ops: Backend for running translation commands.
            thread_pool: Pool for background task execution.
            status_bar: Optional status bar for messages.
            on_translations_dir_changed: Callback when translations folder changes.
            open_ts_callback: Callback to open a .ts file in the editor tab.
        """
        super().__init__(parent)
        self.localization_ops = localization_ops
        self.thread_pool = thread_pool
        self.status_bar = status_bar
        self._translations_dir_changed = on_translations_dir_changed
        self._open_ts_callback = open_ts_callback

        self.language_list_widget: Optional[QListWidget] = None
        self.manage_status_label: Optional[QLabel] = None
        self.manage_log_view: Optional[QPlainTextEdit] = None
        self.manage_table: Optional[QTableWidget] = None
        self.manage_action_buttons: List[QPushButton] = []
        self.manage_task_running = False
        self.translations_path_label: Optional[QLabel] = None
        self._pending_extract_languages: List[str] = []

        self._build_ui()
        self.populate_language_list(preserve_selection=False)
        self._refresh_status_table()

    def _build_ui(self) -> None:
        """Construct the tab layout with language list, action buttons, and status table."""
        layout = QVBoxLayout(self)

        path_row = QHBoxLayout()
        path_caption = QLabel("Translations Folder:")
        path_caption.setMinimumWidth(140)
        path_row.addWidget(path_caption)
        self.translations_path_label = QLabel()
        self.translations_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        path_row.addWidget(self.translations_path_label, 1)
        change_btn = QPushButton("Change Folder...")
        change_btn.clicked.connect(self.prompt_translations_folder)
        path_row.addWidget(change_btn)
        layout.addLayout(path_row)
        self._update_translations_path_label()

        top_layout = QHBoxLayout()

        language_group = QGroupBox("Languages")
        language_layout = QVBoxLayout(language_group)
        self.language_list_widget = QListWidget()
        self.language_list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.language_list_widget.setToolTip(
            "Click to select one language. Hold Shift for ranges or Ctrl for individual toggles."
        )
        self.language_list_widget.itemDoubleClicked.connect(self._handle_language_double_click)
        language_layout.addWidget(self.language_list_widget)

        selector_row = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.setToolTip("Highlight every language in the list.")
        select_all_btn.clicked.connect(self.select_all_languages)
        selector_row.addWidget(select_all_btn)
        clear_btn = QPushButton("Clear Selection")
        clear_btn.setToolTip("Remove the current selection.")
        clear_btn.clicked.connect(self.clear_language_selection)
        selector_row.addWidget(clear_btn)
        edit_btn = QPushButton("Edit Details...")
        edit_btn.setToolTip("Update the display names or quality flag for the selected language.")
        edit_btn.clicked.connect(self.prompt_edit_language)
        selector_row.addWidget(edit_btn)
        add_btn = QPushButton("Add Language...")
        add_btn.setToolTip("Register a brand new language entry.")
        add_btn.clicked.connect(self.prompt_add_language)
        selector_row.addWidget(add_btn)
        delete_btn = QPushButton("Remove Selected...")
        delete_btn.setToolTip(
            "Delete the highlighted languages from the registry (optionally removing files)."
        )
        delete_btn.clicked.connect(self.prompt_delete_languages)
        selector_row.addWidget(delete_btn)
        selector_row.addStretch(1)
        language_layout.addLayout(selector_row)
        top_layout.addWidget(language_group, 2)

        actions_group = QGroupBox("Actions")
        actions_layout = QGridLayout(actions_group)
        buttons = [
            ("Update Source Files", "extract", "Run lupdate to refresh every .ts file."),
            (
                "Build Compiled Files",
                "compile",
                "Run lrelease to build .qm files for the selection.",
            ),
            (
                "Regenerate Resource",
                "resource",
                "Write translations.qrc referencing the current .qm files.",
            ),
            (
                "Add MT Disclaimers",
                "disclaimer",
                "Inject the machine translation notice for auto-translated languages.",
            ),
            (
                "Run Full Pipeline",
                "all",
                "Execute update, compile, resource, and status in sequence.",
            ),
        ]
        self.manage_action_buttons = []
        for index, (label, action, tooltip) in enumerate(buttons):
            button = QPushButton(label)
            button.setToolTip(tooltip)
            button.clicked.connect(lambda _=False, op=action: self.run_manage_operation(op))
            row = index // 2
            col = index % 2
            actions_layout.addWidget(button, row, col)
            self.manage_action_buttons.append(button)
        top_layout.addWidget(actions_group, 3)

        layout.addLayout(top_layout)

        self.manage_status_label = QLabel("Idle")
        layout.addWidget(self.manage_status_label)

        self.manage_table = QTableWidget(0, 6)
        self.manage_table.setHorizontalHeaderLabels(
            ["Locale", ".ts", ".qm", "Progress", "Needs Update", "Quality"]
        )
        self.manage_table.verticalHeader().setVisible(False)
        self.manage_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.manage_table.setSelectionMode(QTableWidget.NoSelection)
        header = self.manage_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.manage_table)

        self.manage_log_view = QPlainTextEdit()
        self.manage_log_view.setReadOnly(True)
        self.manage_log_view.setPlaceholderText("Run an action to see logs here...")
        layout.addWidget(self.manage_log_view)

    def populate_language_list(
        self,
        *,
        preserve_selection: bool = True,
        ensure_selected: Optional[Sequence[str]] = None,
    ) -> None:
        """Refresh the language list widget from the registry.

        Args:
            preserve_selection: Keep previously selected items selected.
            ensure_selected: If provided, select these language codes.
        """
        if not self.language_list_widget:
            return
        if preserve_selection and ensure_selected is None:
            selected_codes = set(self.get_selected_languages())
        else:
            selected_codes = {code.lower() for code in ensure_selected or []}
        self.language_list_widget.clear()
        for code in sorted(LANGUAGE_REGISTRY.keys()):
            meta = LANGUAGE_REGISTRY[code]
            display_name = meta.get("name", code)
            english = meta.get("english_name")
            if english and english != display_name:
                display_name = f"{display_name} ({english})"
            indicator = (
                " 🤖"
                if meta.get("quality") == "machine"
                else " ✋"
                if meta.get("quality") == "native"
                else ""
            )
            locale_label = self._format_locale_label(code)
            item = QListWidgetItem(f"{display_name} ({locale_label}){indicator}")
            item.setData(Qt.UserRole, code)
            self.language_list_widget.addItem(item)
            if code in selected_codes:
                item.setSelected(True)

    def select_all_languages(self) -> None:
        """Select all languages in the list widget."""
        if self.language_list_widget:
            self.language_list_widget.selectAll()

    def clear_language_selection(self) -> None:
        """Clear the current language selection."""
        if self.language_list_widget:
            self.language_list_widget.clearSelection()

    def _handle_language_double_click(self, item: QListWidgetItem) -> None:
        """Open the corresponding .ts file when a language is double-clicked."""
        if not item:
            return
        code = item.data(Qt.UserRole)
        if not code:
            return
        ts_path = self.localization_ops.paths.translations_dir / f"app_{code}.ts"
        if not ts_path.exists():
            QMessageBox.information(
                self,
                "File Not Found",
                f"No translation file found for {code.upper()} in {self.localization_ops.paths.translations_dir}.",
            )
            return
        if self._open_ts_callback:
            self._open_ts_callback(ts_path)
        elif hasattr(self.parent(), "load_ts_file"):
            try:
                self.parent().load_ts_file(str(ts_path))  # type: ignore[attr-defined]
            except Exception:
                pass

    def prompt_add_language(self) -> None:
        """Show dialog to register a new language in the registry."""
        dialog = AddLanguageDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        data = dialog.get_data()
        if not data:
            return
        code = data["code"].lower()
        native_name = data["native_name"]
        english_name = data["english_name"]
        quality = data["quality"]
        if code in LANGUAGE_REGISTRY:
            overwrite = QMessageBox.question(
                self,
                "Language Exists",
                f"{code.upper()} already exists. Update its metadata?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if overwrite != QMessageBox.Yes:
                return
        LANGUAGE_REGISTRY[code] = {
            "name": native_name,
            "english_name": english_name,
            "quality": quality,
        }
        save_language_registry(LANGUAGE_REGISTRY)
        self.populate_language_list(preserve_selection=False, ensure_selected=[code])
        if self.status_bar:
            self.status_bar.showMessage(f"Added {code.upper()} to the language list.")
        if self.manage_task_running:
            QMessageBox.information(
                self,
                "Language Added",
                "Language added. Wait for the current task to finish before creating files.",
            )
            return
        should_create = QMessageBox.question(
            self,
            "Create Translation File",
            f"Do you want to run Extract now to generate app_{code}.ts?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if should_create == QMessageBox.Yes:
            self._enqueue_operation(self.localization_ops.extract, [code])

    def prompt_delete_languages(self) -> None:
        """Prompt to delete selected languages from the registry."""
        if self.manage_task_running:
            QMessageBox.information(
                self,
                "Task Running",
                "Please wait for the current operation to finish before deleting languages.",
            )
            return
        languages = self.get_selected_languages()
        if not languages:
            QMessageBox.information(
                self,
                "Delete Languages",
                "Select at least one language to delete.",
            )
            return
        protected = {code for code in languages if code.lower() == "en"}
        deletable = [code for code in languages if code.lower() != "en"]
        if protected:
            QMessageBox.warning(
                self,
                "Protected Languages",
                "English (EN) is required and cannot be deleted.",
            )
            if not deletable:
                return
        codes_preview = ", ".join(code.upper() for code in deletable)
        prompt = QMessageBox(self)
        prompt.setIcon(QMessageBox.Warning)
        prompt.setWindowTitle("Delete Languages")
        prompt.setText(
            f"Remove the selected languages from the registry?\n\nLanguages: {codes_preview}"
        )
        prompt.setInformativeText(
            "Deleting also removes metadata. Choose whether to delete the corresponding"
            " .ts/.qm files."
        )
        delete_files_btn = prompt.addButton("Delete and Remove Files", QMessageBox.DestructiveRole)
        prompt.addButton("Delete (Keep Files)", QMessageBox.ActionRole)
        cancel_btn = prompt.addButton(QMessageBox.Cancel)
        prompt.setDefaultButton(cancel_btn)
        prompt.exec()
        clicked = prompt.clickedButton()
        if clicked == cancel_btn:
            return
        delete_files = clicked == delete_files_btn
        self._delete_languages(deletable, delete_files)

    def prompt_translations_folder(self) -> None:
        """Prompt user to select a different translations directory."""
        if self.manage_task_running:
            QMessageBox.information(
                self,
                "Task Running",
                "Please wait for the current operation to finish before changing folders.",
            )
            return
        current_dir = str(self.localization_ops.paths.translations_dir)
        new_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Translations Folder",
            current_dir,
        )
        if not new_dir:
            return
        try:
            self.localization_ops.set_translations_dir(Path(new_dir))
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid Folder", str(exc))
            return
        self._update_translations_path_label()
        if self._translations_dir_changed:
            self._translations_dir_changed(self.localization_ops.paths.translations_dir)
        if self.status_bar:
            self.status_bar.showMessage(f"Translations folder set to {new_dir}")
        self.refresh_language_list()
        self._refresh_status_table()

    def prompt_edit_language(self) -> None:
        """Show dialog to edit metadata for the selected language."""
        languages = self.get_selected_languages()
        if len(languages) != 1:
            QMessageBox.information(
                self,
                "Edit Metadata",
                "Select exactly one language to edit.",
            )
            return
        code = languages[0]
        meta = LANGUAGE_REGISTRY.get(code)
        if not meta:
            QMessageBox.warning(
                self,
                "Missing Metadata",
                f"No metadata found for {code.upper()}.",
            )
            return
        dialog = AddLanguageDialog(
            self,
            initial_data={
                "code": code,
                "native_name": meta.get("name", code),
                "english_name": meta.get("english_name", meta.get("name", code)),
                "quality": meta.get("quality", "unknown"),
            },
            code_editable=False,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        data = dialog.get_data()
        if not data:
            return
        LANGUAGE_REGISTRY[code] = {
            "name": data["native_name"],
            "english_name": data["english_name"],
            "quality": data["quality"],
        }
        save_language_registry(LANGUAGE_REGISTRY)
        self.populate_language_list(preserve_selection=False, ensure_selected=[code])
        if self.status_bar:
            self.status_bar.showMessage(f"Updated metadata for {code.upper()}.")

    def get_selected_languages(self) -> List[str]:
        """Retrieve language codes for the currently selected list items.

        Returns:
            A list of lowercase language codes for each selected item.
        """
        if not self.language_list_widget:
            return []
        return [
            item.data(Qt.UserRole)
            for item in self.language_list_widget.selectedItems()
            if item.data(Qt.UserRole)
        ]

    def run_manage_operation(self, op_name: str) -> None:
        """Dispatch a localization operation by name (extract, compile, etc.).

        Args:
            op_name: Operation key such as 'extract', 'compile', 'resource', 'all'.
        """
        if self.manage_task_running:
            QMessageBox.information(
                self, "Task Running", "Please wait for the current operation to finish."
            )
            return
        languages = self.get_selected_languages()
        language_required_ops = {"extract", "compile", "status", "disclaimer", "all"}
        needs_languages = op_name in language_required_ops
        if needs_languages and not languages:
            QMessageBox.information(
                self,
                "Select Languages",
                "Select at least one language before running this action.",
            )
            return
        if self.status_bar:
            if needs_languages:
                self.status_bar.showMessage(
                    f"Running {op_name} task for {len(languages)} language(s)..."
                )
            else:
                self.status_bar.showMessage(f"Running {op_name} task...")
        if op_name == "extract":
            self._pending_extract_languages = languages.copy()
            self._enqueue_operation(self.localization_ops.extract, languages)
        elif op_name == "compile":
            self._enqueue_operation(self.localization_ops.compile, languages)
        elif op_name == "resource":
            self._enqueue_operation(self.localization_ops.create_resource_file)
        elif op_name == "status":
            self._enqueue_operation(self.localization_ops.status_report, languages)
        elif op_name == "disclaimer":
            self._enqueue_operation(self.localization_ops.inject_disclaimers, languages)
        elif op_name == "all":
            self._pending_extract_languages = languages.copy()
            self._enqueue_operation(self._run_full_workflow, languages)
        else:
            QMessageBox.warning(self, "Unknown Operation", f"Unsupported action: {op_name}")

    def _run_full_workflow(self, languages: List[str]) -> List[OperationResult]:
        results = [
            self.localization_ops.extract(languages),
            self.localization_ops.compile(languages),
            self.localization_ops.create_resource_file(),
        ]
        results.append(self.localization_ops.status_report(languages))
        return results

    def _enqueue_operation(self, fn: Callable[..., Any], *args: object) -> None:
        self.manage_task_running = True
        self.set_manage_buttons_enabled(False)
        if self.manage_status_label:
            self.manage_status_label.setText("Running...")
        worker = BackgroundTaskWorker(fn, *args)
        worker.signals.completed.connect(self._handle_operation_completed)
        worker.signals.failed.connect(self._handle_operation_failed)
        self.thread_pool.start(worker)

    def _handle_operation_completed(self, payload: object) -> None:
        results: List[OperationResult]
        if isinstance(payload, list):
            results = payload
        else:
            results = [payload]
        overall_success = True
        has_extract = False
        for result in results:
            if not isinstance(result, OperationResult):
                continue
            self.append_manage_log(result)
            if result.name == "status":
                entries = result.details.get("entries", []) if result.details else []
                if isinstance(entries, list):
                    self._update_status_table(entries)
            if result.name == "extract" and result.success:
                has_extract = True
            if not result.success:
                overall_success = False

        # Check for unused strings after successful extract
        if has_extract and self._pending_extract_languages:
            self._check_for_unused_strings(self._pending_extract_languages)
            self._pending_extract_languages = []

        # Refresh the status table after any operation completes
        # (unless status was already run as part of the operation)
        has_status = any(
            isinstance(r, OperationResult) and r.name == "status" for r in results
        )
        if not has_status:
            self._refresh_status_table()

        status_text = "Completed" if overall_success else "Completed with issues"
        if self.manage_status_label:
            self.manage_status_label.setText(status_text)
        if self.status_bar:
            self.status_bar.showMessage(f"Localization task {status_text.lower()}.")
        self.set_manage_buttons_enabled(True)
        self.manage_task_running = False

    def _handle_operation_failed(self, message: str) -> None:
        if self.manage_log_view:
            self.manage_log_view.appendPlainText(f"[ERROR] {message}\n")
        if self.status_bar:
            self.status_bar.showMessage(f"Localization task failed: {message}")
        if self.manage_status_label:
            self.manage_status_label.setText("Failed")
        self.set_manage_buttons_enabled(True)
        self.manage_task_running = False

    def set_manage_buttons_enabled(self, enabled: bool) -> None:
        """Enable or disable the action buttons.

        Args:
            enabled: True to enable buttons, False to disable.
        """
        for button in self.manage_action_buttons:
            button.setEnabled(enabled)

    def _update_translations_path_label(self) -> None:
        if not self.translations_path_label:
            return
        current_path = self.localization_ops.paths.translations_dir
        display = self._format_path(current_path)
        self.translations_path_label.setText(display)
        self.translations_path_label.setToolTip(str(current_path))

    @staticmethod
    def _format_locale_label(code: str) -> str:
        """Format a language code as a locale label.

        Args:
            code: A language code like "en" or "pt-BR".

        Returns:
            The lowercased, underscore-separated locale string (e.g., "pt_br").
        """
        return code.lower().replace("-", "_") if code else ""

    @staticmethod
    def _format_path(path: Path) -> str:
        """Truncate a path for display if too long.

        Args:
            path: The filesystem path to format.

        Returns:
            A string representation of the path, truncated with "..." if needed.
        """
        text = str(path)
        if len(text) <= 60:
            return text
        return "..." + text[-57:]

    def _delete_languages(self, languages: List[str], delete_files: bool) -> None:
        """Remove languages from the registry and optionally delete files.

        Args:
            languages: List of language codes to remove.
            delete_files: If True, also delete .ts and .qm files.
        """
        removed: List[str] = []
        for code in languages:
            if code in LANGUAGE_REGISTRY:
                removed.append(code)
                LANGUAGE_REGISTRY.pop(code, None)
        if not removed:
            QMessageBox.information(
                self,
                "Delete Languages",
                "Selected languages were not found in the registry.",
            )
            return

        save_language_registry(LANGUAGE_REGISTRY)

        deleted_files: List[str] = []
        failed_files: List[str] = []
        translations_dir: Path = self.localization_ops.paths.translations_dir
        if delete_files:
            translations_dir.mkdir(parents=True, exist_ok=True)
            for code in removed:
                for suffix in (".ts", ".qm"):
                    candidate = translations_dir / f"app_{code}{suffix}"
                    if not candidate.exists():
                        continue
                    try:
                        candidate.unlink()
                        deleted_files.append(candidate.name)
                    except OSError as exc:
                        failed_files.append(f"{candidate.name}: {exc}")

        self.populate_language_list(preserve_selection=False)
        if self.status_bar:
            self.status_bar.showMessage(
                f"Deleted {len(removed)} language(s){' and files' if delete_files else ''}."
            )

        if self.manage_log_view:
            header = "[DELETE] Removed languages: " + ", ".join(code.upper() for code in removed)
            self.manage_log_view.appendPlainText(header + "\n")
            if deleted_files:
                self.manage_log_view.appendPlainText(
                    "    Deleted files: " + ", ".join(deleted_files) + "\n"
                )
        if failed_files:
            QMessageBox.warning(
                self,
                "File Removal Issues",
                "Some translation files could not be removed:\n" + "\n".join(failed_files),
            )

    def append_manage_log(self, result: OperationResult) -> None:
        """Append an operation result to the log view.

        Args:
            result: The OperationResult to display in the log.
        """
        if not self.manage_log_view:
            return
        header = f"[{result.name.upper()}] {'OK' if result.success else 'FAILED'}"
        lines = [header]
        lines.extend(result.logs)
        if result.errors:
            lines.append("Errors:")
            lines.extend(f"  - {msg}" for msg in result.errors)
        self.manage_log_view.appendPlainText("\n".join(lines) + "\n")

    def _update_status_table(self, entries: List[Dict[str, Any]]) -> None:
        """Populate the status table with translation progress entries.

        Args:
            entries: List of dictionaries containing language status details.
        """
        if not self.manage_table:
            return
        self.manage_table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            lang_item = QTableWidgetItem(self._format_locale_label(entry.get("language", "")))
            ts_item = QTableWidgetItem("✅" if entry.get("ts_exists") else "❌")
            qm_item = QTableWidgetItem("✅" if entry.get("qm_exists") else "❌")
            total = entry.get("total_messages", 0)
            finished = entry.get("finished_messages", 0)
            progress = f"{finished}/{total}" if total else "0/0"
            if total:
                progress += f" ({finished / total * 100:.0f}%)"
            progress_item = QTableWidgetItem(progress)
            needs_update = entry.get("needs_update", False)
            needs_item = QTableWidgetItem("Yes" if needs_update else "No")
            unfinished = entry.get("unfinished_messages")
            if unfinished is not None:
                needs_item.setToolTip(f"Unfinished strings: {unfinished}")
            quality_item = QTableWidgetItem(entry.get("quality", ""))
            for item in (lang_item, ts_item, qm_item, progress_item, needs_item, quality_item):
                item.setTextAlignment(Qt.AlignCenter)
            self.manage_table.setItem(row, 0, lang_item)
            self.manage_table.setItem(row, 1, ts_item)
            self.manage_table.setItem(row, 2, qm_item)
            self.manage_table.setItem(row, 3, progress_item)
            self.manage_table.setItem(row, 4, needs_item)
            self.manage_table.setItem(row, 5, quality_item)

    def refresh_language_list(self) -> None:
        self.populate_language_list(preserve_selection=True)

    def _refresh_status_table(self) -> None:
        """Refresh the status table with current translation progress for all languages."""
        result = self.localization_ops.status_report()
        if result.success:
            entries = result.details.get("entries", []) if result.details else []
            if isinstance(entries, list):
                self._update_status_table(entries)

    def _check_for_unused_strings(self, languages: List[str]) -> None:
        """Check extracted .ts files for vanished (obsolete) strings and prompt for cleanup.

        Qt's lupdate marks strings that no longer exist in source code with
        type="vanished". This method finds those strings and offers to remove them.

        Args:
            languages: List of language codes that were just extracted.
        """
        translations_dir = self.localization_ops.paths.translations_dir
        unused_by_file: Dict[Path, List[Tuple[str, str]]] = {}

        for lang in languages:
            ts_file = translations_dir / f"app_{lang}.ts"
            if not ts_file.exists():
                continue

            vanished = self._extract_vanished_strings(ts_file)
            if vanished:
                unused_by_file[ts_file] = vanished

        if not unused_by_file:
            return

        # Show batch cleanup dialog
        dialog = BatchUnusedStringsDialog(
            self,
            unused_by_file,
            translations_dir,
        )
        result = dialog.exec()

        if result == QDialog.Accepted:
            cleaned_count = len(dialog.files_cleaned)
            total_removed = sum(len(strings) for strings in unused_by_file.values())
            msg = f"Removed {total_removed} vanished string(s) from {cleaned_count} file(s)"
            if dialog.save_requested and dialog.saved_path:
                msg += f" (saved to {Path(dialog.saved_path).name})"
            if self.manage_log_view:
                self.manage_log_view.appendPlainText(f"[CLEANUP] {msg}\n")
            if self.status_bar:
                self.status_bar.showMessage(msg, 5000)

    def _extract_vanished_strings(self, file_path: Path) -> List[Tuple[str, str]]:
        """Extract vanished/obsolete strings from a .ts file.

        Qt's lupdate marks strings that no longer exist in the source code
        with type="vanished" (newer Qt) or type="obsolete" (older Qt).
        Strings that exist as active entries elsewhere (moved to another context)
        are excluded since they're not truly unused.

        Args:
            file_path: Path to the .ts file.

        Returns:
            List of (source, translation) tuples for vanished/obsolete strings.
        """
        vanished: List[Tuple[str, str]] = []
        try:
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

            # Now collect vanished/obsolete strings that don't exist elsewhere
            for message in root.iter("message"):
                translation_elem = message.find("translation")
                if translation_elem is not None:
                    trans_type = translation_elem.get("type", "")
                    if trans_type in ("vanished", "obsolete"):
                        source_elem = message.find("source")
                        source = source_elem.text if source_elem is not None and source_elem.text else ""
                        # Skip if this string exists as an active entry (was moved)
                        if source and source not in active_sources:
                            translation = translation_elem.text if translation_elem.text else ""
                            vanished.append((source, translation))
        except Exception:
            pass
        return vanished


__all__ = ["ManageTab"]
