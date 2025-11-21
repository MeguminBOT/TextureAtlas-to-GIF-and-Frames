from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
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
from language_registry import LANGUAGE_REGISTRY, save_language_registry
from translation_tasks import LocalizationOperations, OperationResult
from utils import BackgroundTaskWorker


class ManageTab(QWidget):
    """UI Tab for managing translation files"""

    def __init__(
        self,
        *,
        parent: QWidget,
        localization_ops: LocalizationOperations,
        thread_pool: QThreadPool,
        status_bar: Optional[QStatusBar] = None,
    ) -> None:
        super().__init__(parent)
        self.localization_ops = localization_ops
        self.thread_pool = thread_pool
        self.status_bar = status_bar

        self.language_list_widget: Optional[QListWidget] = None
        self.manage_status_label: Optional[QLabel] = None
        self.manage_log_view: Optional[QPlainTextEdit] = None
        self.manage_table: Optional[QTableWidget] = None
        self.manage_action_buttons: List[QPushButton] = []
        self.manage_task_running = False

        self._build_ui()
        self.populate_language_list(preserve_selection=False)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        description = QLabel(
            "Run pyside6 translation maintenance commands without leaving the app."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        top_layout = QHBoxLayout()

        language_group = QGroupBox("Languages")
        language_layout = QVBoxLayout(language_group)
        self.language_list_widget = QListWidget()
        self.language_list_widget.setSelectionMode(QListWidget.MultiSelection)
        language_layout.addWidget(self.language_list_widget)

        selector_row = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all_languages)
        selector_row.addWidget(select_all_btn)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_language_selection)
        selector_row.addWidget(clear_btn)
        add_btn = QPushButton("Add Language...")
        add_btn.clicked.connect(self.prompt_add_language)
        selector_row.addWidget(add_btn)
        selector_row.addStretch(1)
        language_layout.addLayout(selector_row)
        top_layout.addWidget(language_group, 2)

        actions_group = QGroupBox("Actions")
        actions_layout = QGridLayout(actions_group)
        buttons = [
            ("Extract TS", "extract"),
            ("Compile QM", "compile"),
            ("Create Resource", "resource"),
            ("Status", "status"),
            ("Add Disclaimers", "disclaimer"),
            ("Run All", "all"),
        ]
        self.manage_action_buttons = []
        for index, (label, action) in enumerate(buttons):
            button = QPushButton(label)
            button.clicked.connect(lambda _=False, op=action: self.run_manage_operation(op))
            row = index // 2
            col = index % 2
            actions_layout.addWidget(button, row, col)
            self.manage_action_buttons.append(button)
        top_layout.addWidget(actions_group, 3)

        layout.addLayout(top_layout)

        self.manage_status_label = QLabel("Idle")
        layout.addWidget(self.manage_status_label)

        self.manage_table = QTableWidget(0, 5)
        self.manage_table.setHorizontalHeaderLabels(["Lang", ".ts", ".qm", "Progress", "Quality"])
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
            item = QListWidgetItem(f"{code.upper()} - {display_name}{indicator}")
            item.setData(Qt.UserRole, code)
            self.language_list_widget.addItem(item)
            if code in selected_codes:
                item.setSelected(True)

    def select_all_languages(self) -> None:
        if self.language_list_widget:
            self.language_list_widget.selectAll()

    def clear_language_selection(self) -> None:
        if self.language_list_widget:
            self.language_list_widget.clearSelection()

    def prompt_add_language(self) -> None:
        dialog = AddLanguageDialog(self)
        if dialog.exec() != dialog.Accepted:
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

    def get_selected_languages(self) -> List[str]:
        if not self.language_list_widget:
            return []
        return [
            item.data(Qt.UserRole)
            for item in self.language_list_widget.selectedItems()
            if item.data(Qt.UserRole)
        ]

    def run_manage_operation(self, op_name: str) -> None:
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
        for result in results:
            if not isinstance(result, OperationResult):
                continue
            self.append_manage_log(result)
            if result.name == "status":
                entries = result.details.get("entries", []) if result.details else []
                if isinstance(entries, list):
                    self._update_status_table(entries)
            if not result.success:
                overall_success = False
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
        for button in self.manage_action_buttons:
            button.setEnabled(enabled)

    def append_manage_log(self, result: OperationResult) -> None:
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
        if not self.manage_table:
            return
        self.manage_table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            lang_item = QTableWidgetItem(entry.get("language", "").upper())
            ts_item = QTableWidgetItem("✅" if entry.get("ts_exists") else "❌")
            qm_item = QTableWidgetItem("✅" if entry.get("qm_exists") else "❌")
            total = entry.get("total_messages", 0)
            finished = entry.get("finished_messages", 0)
            progress = f"{finished}/{total}" if total else "0/0"
            if total:
                progress += f" ({finished / total * 100:.0f}%)"
            progress_item = QTableWidgetItem(progress)
            quality_item = QTableWidgetItem(entry.get("quality", ""))
            for item in (lang_item, ts_item, qm_item, progress_item, quality_item):
                item.setTextAlignment(Qt.AlignCenter)
            self.manage_table.setItem(row, 0, lang_item)
            self.manage_table.setItem(row, 1, ts_item)
            self.manage_table.setItem(row, 2, qm_item)
            self.manage_table.setItem(row, 3, progress_item)
            self.manage_table.setItem(row, 4, quality_item)

    def refresh_language_list(self) -> None:
        self.populate_language_list(preserve_selection=True)


__all__ = ["ManageTab"]
