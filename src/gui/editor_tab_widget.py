#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Interactive alignment editor tab for animations and spritesheets."""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QPoint, QPointF, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

try:
    from PIL import Image, ImageSequence

    PIL_AVAILABLE = True
except ImportError:  # pragma: no cover - pillow is expected to be installed with the app
    Image = None  # type: ignore
    ImageSequence = None  # type: ignore
    PIL_AVAILABLE = False

ANIMATION_ID_ROLE = Qt.ItemDataRole.UserRole + 1
FRAME_INDEX_ROLE = Qt.ItemDataRole.UserRole + 2


@dataclass
class AlignmentFrame:
    """Container representing a single frame that can be aligned."""

    name: str
    original_key: str
    pixmap: QPixmap
    duration_ms: int = 100
    offset_x: int = 0
    offset_y: int = 0
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class AlignmentAnimation:
    """Holds state for an animation currently loaded in the editor."""

    display_name: str
    frames: List[AlignmentFrame]
    canvas_width: int
    canvas_height: int
    source: str = "manual"  # either "manual" or "extract"
    spritesheet_name: Optional[str] = None
    animation_name: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)
    default_offset: Tuple[int, int] = (0, 0)

    def ensure_canvas_bounds(self):
        """Ensure the canvas matches the frame bounds plus padding."""
        if not self.frames:
            return
        max_w = max(frame.pixmap.width() for frame in self.frames)
        max_h = max(frame.pixmap.height() for frame in self.frames)
        # Add 50% padding around the bounding box (e.g., 512px -> 768px)
        padding_ratio = 0.5
        pad_w = int(round(max_w * padding_ratio))
        pad_h = int(round(max_h * padding_ratio))
        padded_w = min(4096, max_w + pad_w)
        padded_h = min(4096, max_h + pad_h)
        self.canvas_width = max(self.canvas_width, padded_w)
        self.canvas_height = max(self.canvas_height, padded_h)


class AlignmentCanvas(QWidget):
    """Simple canvas that renders the active frame and allows drag alignment."""

    offsetChanged = Signal(int, int)
    zoomChanged = Signal(float)

    def __init__(self):
        super().__init__()
        self._pixmap: Optional[QPixmap] = None
        self._canvas_width = 512
        self._canvas_height = 512
        self._display_padding = 80
        self._offset_x = 0
        self._offset_y = 0
        self._dragging = False
        self._drag_origin = QPoint()
        self._start_offset = (0, 0)
        self._zoom = 1.0
        self._min_zoom = 0.25
        self._max_zoom = 5.0
        self._ghost_pixmap: Optional[QPixmap] = None
        self._ghost_opacity = 0.35
        self._ghost_offset_x = 0
        self._ghost_offset_y = 0
        self._snapping_enabled = False
        self._snap_step = 1
        self._view_translation = QPointF(0.0, 0.0)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(self.sizeHint())

    def sizeHint(self) -> QSize:  # noqa: D401 - Qt API
        return QSize(
            max(self._canvas_width + self._display_padding, 240),
            max(self._canvas_height + self._display_padding, 240),
        )

    def minimumSizeHint(self) -> QSize:  # noqa: D401 - Qt API
        return self.sizeHint()

    def set_pixmap(self, pixmap: Optional[QPixmap]):
        self._pixmap = pixmap
        self.update()

    def set_canvas_size(self, width: int, height: int):
        width = max(8, int(width))
        height = max(8, int(height))
        if (width, height) != (self._canvas_width, self._canvas_height):
            self._canvas_width = width
            self._canvas_height = height
            self.recenter_view()
            hint = self.sizeHint()
            self.setMinimumSize(hint)
            self.updateGeometry()
            self.update()

    def set_offsets(self, offset_x: int, offset_y: int, notify: bool = False):
        offset_x = self._apply_snapping(int(offset_x))
        offset_y = self._apply_snapping(int(offset_y))
        changed = (offset_x, offset_y) != (self._offset_x, self._offset_y)
        self._offset_x = offset_x
        self._offset_y = offset_y
        if changed and notify:
            self.offsetChanged.emit(self._offset_x, self._offset_y)
        if changed:
            self.update()

    def offsets(self) -> Tuple[int, int]:
        return self._offset_x, self._offset_y

    def set_ghost_pixmap(
        self,
        pixmap: Optional[QPixmap],
        opacity: float = 0.35,
        offset_x: int = 0,
        offset_y: int = 0,
    ):
        self._ghost_pixmap = pixmap
        self._ghost_opacity = max(0.05, min(0.95, opacity))
        self._ghost_offset_x = int(offset_x)
        self._ghost_offset_y = int(offset_y)
        self.update()

    def configure_snapping(self, enabled: bool, snap_step: int):
        self._snapping_enabled = enabled
        self._snap_step = max(1, int(snap_step))
        # Re-apply snapping to current offsets to keep UI consistent
        self.set_offsets(self._offset_x, self._offset_y)

    def reset_zoom(self):
        self.recenter_view()
        self.set_zoom(1.0)

    def set_zoom(self, zoom: float, anchor: Optional[QPointF] = None):
        zoom = max(self._min_zoom, min(self._max_zoom, zoom))
        if abs(zoom - self._zoom) < 0.001:
            return
        old_zoom = self._zoom
        self._zoom = zoom
        if anchor is not None and old_zoom > 0:
            self._apply_zoom_anchor(anchor, old_zoom, zoom)
        self.zoomChanged.emit(self._zoom)
        self.update()

    def zoom(self) -> float:
        return self._zoom

    def paintEvent(self, event):  # noqa: D401 - Qt API
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(28, 28, 28))

        painter.save()
        painter.translate(self._view_translation)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(self._zoom, self._zoom)
        painter.translate(-self.width() / 2, -self.height() / 2)

        canvas_rect = self._canvas_rect()
        self._paint_checkerboard(painter, canvas_rect)
        self._paint_crosshair(painter, canvas_rect)

        if self._ghost_pixmap and not self._ghost_pixmap.isNull():
            ghost_rect = self._ghost_pixmap.rect()
            ghost_x = canvas_rect.center().x() - ghost_rect.width() // 2 + self._ghost_offset_x
            ghost_y = canvas_rect.center().y() - ghost_rect.height() // 2 + self._ghost_offset_y
            painter.setOpacity(self._ghost_opacity)
            painter.drawPixmap(ghost_x, ghost_y, self._ghost_pixmap)
            painter.setOpacity(1.0)

        if self._pixmap and not self._pixmap.isNull():
            pixmap_rect = self._pixmap.rect()
            target_x = canvas_rect.center().x() - pixmap_rect.width() // 2 + self._offset_x
            target_y = canvas_rect.center().y() - pixmap_rect.height() // 2 + self._offset_y
            painter.drawPixmap(target_x, target_y, self._pixmap)

        painter.restore()

    def _canvas_rect(self) -> QRect:
        left = (self.width() - self._canvas_width) // 2
        top = (self.height() - self._canvas_height) // 2
        return QRect(left, top, self._canvas_width, self._canvas_height)

    def _paint_checkerboard(self, painter: QPainter, rect):
        square = 16
        dark = QColor(60, 60, 60)
        light = QColor(80, 80, 80)
        for x in range(rect.left(), rect.right() + square, square):
            for y in range(rect.top(), rect.bottom() + square, square):
                color = dark if ((x // square + y // square) % 2 == 0) else light
                painter.fillRect(x, y, square, square, color)

    def _paint_crosshair(self, painter: QPainter, rect):
        painter.setPen(QColor(0, 196, 255, 140))
        painter.drawLine(rect.center().x(), rect.top(), rect.center().x(), rect.bottom())
        painter.drawLine(rect.left(), rect.center().y(), rect.right(), rect.center().y())

    def mousePressEvent(self, event):  # noqa: D401 - Qt API
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_origin = event.position().toPoint()
            self._start_offset = (self._offset_x, self._offset_y)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # noqa: D401 - Qt API
        if self._dragging:
            delta = event.position().toPoint() - self._drag_origin
            self.set_offsets(self._start_offset[0] + delta.x(), self._start_offset[1] + delta.y(), notify=True)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):  # noqa: D401 - Qt API
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):  # noqa: D401 - Qt API
        step = 5 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
        handled = True
        if event.key() == Qt.Key.Key_Left:
            self.set_offsets(self._offset_x - step, self._offset_y, notify=True)
        elif event.key() == Qt.Key.Key_Right:
            self.set_offsets(self._offset_x + step, self._offset_y, notify=True)
        elif event.key() == Qt.Key.Key_Up:
            self.set_offsets(self._offset_x, self._offset_y - step, notify=True)
        elif event.key() == Qt.Key.Key_Down:
            self.set_offsets(self._offset_x, self._offset_y + step, notify=True)
        else:
            handled = False
        if not handled:
            super().keyPressEvent(event)

    def wheelEvent(self, event):  # noqa: D401 - Qt API
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta == 0:
                return
            factor = 1.1 if delta > 0 else 0.9
            self.set_zoom(self._zoom * factor, anchor=event.position())
            event.accept()
        else:
            event.ignore()

    def _apply_snapping(self, value: int) -> int:
        if not self._snapping_enabled or self._snap_step <= 1:
            return value
        snapped = int(round(value / self._snap_step) * self._snap_step)
        return snapped

    def recenter_view(self):
        self._view_translation = QPointF(0.0, 0.0)
        self.update()

    def fit_canvas_to_viewport(self, viewport_size: QSize):
        if viewport_size.width() <= 0 or viewport_size.height() <= 0:
            return
        padded_width = self._canvas_width + self._display_padding
        padded_height = self._canvas_height + self._display_padding
        scale_x = viewport_size.width() / max(1, padded_width)
        scale_y = viewport_size.height() / max(1, padded_height)
        target_zoom = min(scale_x, scale_y)
        target_zoom = max(self._min_zoom, min(self._max_zoom, target_zoom))
        self.recenter_view()
        self.set_zoom(target_zoom)

    def _apply_zoom_anchor(self, anchor: QPointF, old_zoom: float, new_zoom: float):
        if old_zoom <= 0:
            return
        ratio = new_zoom / old_zoom
        center = QPointF(self.width() / 2, self.height() / 2)
        delta = anchor - center
        self._view_translation = QPointF(
            (1 - ratio) * delta.x() + ratio * self._view_translation.x(),
            (1 - ratio) * delta.y() + ratio * self._view_translation.y(),
        )


class CanvasDetachWindow(QDialog):
    """Simple dialog used to host the canvas when detached from the main tab."""

    closed = Signal()

    def closeEvent(self, event):  # noqa: D401 - Qt API
        self.closed.emit()
        super().closeEvent(event)


class EditorTabWidget(QWidget):
    """Widget backing the new Editor tab."""

    def __init__(self, parent_app):
        super().__init__(parent_app)
        self.parent_app = parent_app
        self._animations: Dict[str, AlignmentAnimation] = {}
        self._current_animation_id: Optional[str] = None
        self._current_frame_index: int = -1
        self._root_alignment_mode: bool = False
        self._updating_controls = False
        self._detached_window: Optional[CanvasDetachWindow] = None
        self._animation_items: Dict[str, QTreeWidgetItem] = {}
        self._build_ui()
        self._connect_signals()
        self._update_zoom_label(self.canvas.zoom())

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter, 1)

        # Left column: animation + frame lists
        lists_widget = QWidget()
        lists_widget.setMinimumWidth(280)
        lists_widget.setMaximumWidth(420)
        lists_widget.setSizePolicy(QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding))
        lists_layout = QVBoxLayout(lists_widget)
        lists_layout.setSpacing(8)

        anim_label = QLabel(self.tr("Animations & Frames"))
        lists_layout.addWidget(anim_label)

        self.animation_tree = QTreeWidget()
        self.animation_tree.setHeaderHidden(True)
        self.animation_tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.animation_tree.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
        lists_layout.addWidget(self.animation_tree, 1)

        button_row = QHBoxLayout()
        self.load_files_button = QPushButton(self.tr("Load Animation Files"))
        self.load_files_button.setToolTip(self.tr("Load GIF/WebP/APNG/PNG files into the editor"))
        button_row.addWidget(self.load_files_button)
        self.remove_animation_button = QPushButton(self.tr("Remove"))
        button_row.addWidget(self.remove_animation_button)
        self.combine_button = QPushButton(self.tr("Combine Selected"))
        self.combine_button.setToolTip(
            self.tr("Create a composite entry from all selected animations for group alignment")
        )
        self.combine_button.setEnabled(False)
        button_row.addWidget(self.combine_button)
        lists_layout.addLayout(button_row)

        splitter.addWidget(lists_widget)

        # Right column: canvas + controls
        editor_splitter = QSplitter(Qt.Orientation.Horizontal)
        editor_splitter.setChildrenCollapsible(False)

        canvas_panel = QWidget()
        canvas_panel.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
        canvas_column = QVBoxLayout(canvas_panel)
        canvas_column.setSpacing(8)
        canvas_column.setContentsMargins(0, 0, 0, 0)
        self.canvas = AlignmentCanvas()
        self.canvas_scroll = QScrollArea()
        self.canvas_scroll.setWidget(self.canvas)
        self.canvas_scroll.setWidgetResizable(True)
        self.canvas_scroll.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
        self.canvas_holder = QWidget()
        self.canvas_holder.setLayout(QVBoxLayout())
        self.canvas_holder.layout().setContentsMargins(0, 0, 0, 0)
        self.canvas_holder.layout().addWidget(self.canvas_scroll)
        self.canvas_holder.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
        canvas_column.addWidget(self.canvas_holder, 1)

        canvas_toolbar = QHBoxLayout()
        self.zoom_out_button = QPushButton("-")
        self.zoom_out_button.setToolTip(self.tr("Zoom out"))
        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.setToolTip(self.tr("Zoom in"))
        self.reset_zoom_button = QPushButton(self.tr("Reset Zoom"))
        self.zoom_100_button = QPushButton("100%")
        self.zoom_100_button.setToolTip(self.tr("Set zoom to 100%"))
        self.zoom_50_button = QPushButton("50%")
        self.zoom_50_button.setToolTip(self.tr("Set zoom to 50%"))
        self.center_view_button = QPushButton(self.tr("Center View"))
        self.center_view_button.setToolTip(self.tr("Re-center the viewport"))
        self.fit_canvas_button = QPushButton(self.tr("Fit Canvas"))
        self.fit_canvas_button.setToolTip(self.tr("Fit the entire canvas inside the view"))
        self.zoom_label = QLabel("100%")
        self.detach_canvas_button = QPushButton(self.tr("Detach Canvas"))
        canvas_toolbar.addWidget(self.zoom_out_button)
        canvas_toolbar.addWidget(self.zoom_in_button)
        canvas_toolbar.addWidget(self.reset_zoom_button)
        canvas_toolbar.addWidget(self.zoom_100_button)
        canvas_toolbar.addWidget(self.zoom_50_button)
        canvas_toolbar.addWidget(self.center_view_button)
        canvas_toolbar.addWidget(self.fit_canvas_button)
        canvas_toolbar.addWidget(self.zoom_label)
        canvas_toolbar.addStretch()
        canvas_toolbar.addWidget(self.detach_canvas_button)
        canvas_column.addLayout(canvas_toolbar)

        controls_group = QGroupBox(self.tr("Alignment Controls"))
        controls_layout = QFormLayout(controls_group)

        self.offset_x_spin = QSpinBox()
        self.offset_x_spin.setRange(-4096, 4096)
        controls_layout.addRow(self.tr("Frame offset X"), self.offset_x_spin)

        self.offset_y_spin = QSpinBox()
        self.offset_y_spin.setRange(-4096, 4096)
        controls_layout.addRow(self.tr("Frame offset Y"), self.offset_y_spin)

        control_buttons = QHBoxLayout()
        self.reset_offset_button = QPushButton(self.tr("Reset to Default"))
        control_buttons.addWidget(self.reset_offset_button)
        self.apply_all_button = QPushButton(self.tr("Apply to All Frames"))
        control_buttons.addWidget(self.apply_all_button)
        controls_layout.addRow(control_buttons)

        self.canvas_width_spin = QSpinBox()
        self.canvas_width_spin.setRange(8, 4096)
        controls_layout.addRow(self.tr("Canvas width"), self.canvas_width_spin)

        self.canvas_height_spin = QSpinBox()
        self.canvas_height_spin.setRange(8, 4096)
        controls_layout.addRow(self.tr("Canvas height"), self.canvas_height_spin)

        self.save_overrides_button = QPushButton(self.tr("Save Alignment to Extract Tab"))
        self.save_overrides_button.setEnabled(False)
        controls_layout.addRow(self.save_overrides_button)

        self.export_composite_button = QPushButton(self.tr("Export Composite to Sprites"))
        self.export_composite_button.setEnabled(False)
        controls_layout.addRow(self.export_composite_button)

        display_group = QGroupBox(self.tr("Display & snapping"))
        display_layout = QFormLayout(display_group)

        ghost_widget = QWidget()
        ghost_row = QHBoxLayout(ghost_widget)
        ghost_row.setContentsMargins(0, 0, 0, 0)
        self.ghost_checkbox = QCheckBox(self.tr("Enable"))
        self.ghost_frame_combo = QComboBox()
        self.ghost_frame_combo.setEnabled(False)
        ghost_row.addWidget(self.ghost_checkbox)
        ghost_row.addWidget(self.ghost_frame_combo, 1)
        display_layout.addRow(self.tr("Ghost frame"), ghost_widget)

        snap_widget = QWidget()
        snap_row = QHBoxLayout(snap_widget)
        snap_row.setContentsMargins(0, 0, 0, 0)
        self.snap_checkbox = QCheckBox(self.tr("Enable"))
        self.snap_step_spin = QSpinBox()
        self.snap_step_spin.setRange(1, 256)
        self.snap_step_spin.setValue(1)
        self.snap_step_spin.setEnabled(False)
        snap_row.addWidget(self.snap_checkbox)
        snap_row.addWidget(QLabel(self.tr("px")))
        snap_row.addWidget(self.snap_step_spin)
        display_layout.addRow(self.tr("Snapping"), snap_widget)

        self._default_status_text = self.tr(
            "Drag the frame, use arrow keys for fine adjustments, or type offsets manually."
        )
        self.status_label = QLabel(self._default_status_text)
        canvas_column.addWidget(self.status_label)

        controls_panel = QWidget()
        controls_panel.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding))
        controls_panel.setMinimumWidth(280)
        controls_panel.setMaximumWidth(320)
        controls_panel_layout = QVBoxLayout(controls_panel)
        controls_panel_layout.setContentsMargins(0, 0, 0, 0)
        controls_panel_layout.setSpacing(8)
        controls_panel_layout.addWidget(controls_group)
        controls_panel_layout.addWidget(display_group)
        controls_panel_layout.addStretch()
        editor_splitter.addWidget(canvas_panel)
        editor_splitter.addWidget(controls_panel)
        editor_splitter.setStretchFactor(0, 1)
        editor_splitter.setStretchFactor(1, 0)
        editor_splitter.setSizes([960, 320])

        splitter.addWidget(editor_splitter)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([360, 960])

    def _connect_signals(self):
        self.animation_tree.currentItemChanged.connect(self._on_tree_current_changed)
        self.animation_tree.itemSelectionChanged.connect(self._update_combine_button_state)
        self.load_files_button.clicked.connect(self._load_manual_files)
        self.remove_animation_button.clicked.connect(self._remove_selected_animation)
        self.combine_button.clicked.connect(self._combine_selected_animations)
        self.offset_x_spin.valueChanged.connect(self._on_manual_offset_changed)
        self.offset_y_spin.valueChanged.connect(self._on_manual_offset_changed)
        self.apply_all_button.clicked.connect(self._apply_offsets_to_all_frames)
        self.reset_offset_button.clicked.connect(self._reset_frame_offset)
        self.canvas_width_spin.valueChanged.connect(self._on_canvas_size_changed)
        self.canvas_height_spin.valueChanged.connect(self._on_canvas_size_changed)
        self.save_overrides_button.clicked.connect(self._save_alignment_to_settings)
        self.export_composite_button.clicked.connect(self._export_composite_to_sprites)
        self.canvas.offsetChanged.connect(self._on_canvas_dragged)
        self.canvas.zoomChanged.connect(self._update_zoom_label)
        self.zoom_in_button.clicked.connect(lambda: self.canvas.set_zoom(self.canvas.zoom() * 1.1))
        self.zoom_out_button.clicked.connect(lambda: self.canvas.set_zoom(self.canvas.zoom() * 0.9))
        self.reset_zoom_button.clicked.connect(self.canvas.reset_zoom)
        self.zoom_100_button.clicked.connect(lambda: self.canvas.set_zoom(1.0))
        self.zoom_50_button.clicked.connect(lambda: self.canvas.set_zoom(0.5))
        self.center_view_button.clicked.connect(self._center_canvas_view)
        self.fit_canvas_button.clicked.connect(self._fit_canvas_to_viewport)
        self.ghost_checkbox.toggled.connect(self._on_ghost_toggled)
        self.ghost_frame_combo.currentIndexChanged.connect(self._on_ghost_frame_changed)
        self.snap_checkbox.toggled.connect(self._on_snap_toggled)
        self.snap_step_spin.valueChanged.connect(self._on_snap_step_changed)
        self.detach_canvas_button.clicked.connect(self._toggle_canvas_detach)

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------
    def _update_combine_button_state(self):
        selected_top_levels = [item for item in self.animation_tree.selectedItems() if item.parent() is None]
        self.combine_button.setEnabled(len(selected_top_levels) >= 2)

    def _update_zoom_label(self, zoom: float):
        percent = int(round(zoom * 100))
        self.zoom_label.setText(self.tr("Zoom: {value}%").format(value=percent))

    def _refresh_ghost_options(self):
        current_data = self.ghost_frame_combo.currentData()
        self.ghost_frame_combo.blockSignals(True)
        self.ghost_frame_combo.clear()
        for animation_id, animation in self._animations.items():
            for idx, frame in enumerate(animation.frames):
                label = f"{animation.display_name} - {frame.name} ({frame.pixmap.width()}x{frame.pixmap.height()})"
                self.ghost_frame_combo.addItem(label, (animation_id, idx))
        if current_data is not None:
            for i in range(self.ghost_frame_combo.count()):
                if self.ghost_frame_combo.itemData(i) == current_data:
                    self.ghost_frame_combo.setCurrentIndex(i)
                    break
        self.ghost_frame_combo.blockSignals(False)

        has_frames = self.ghost_frame_combo.count() > 0
        self.ghost_checkbox.blockSignals(True)
        if not has_frames:
            self.ghost_checkbox.setChecked(False)
        self.ghost_checkbox.setEnabled(has_frames)
        self.ghost_checkbox.blockSignals(False)
        self.ghost_frame_combo.setEnabled(has_frames and self.ghost_checkbox.isChecked())
        if has_frames and self.ghost_checkbox.isChecked():
            self._apply_ghost_overlay()
        else:
            self.canvas.set_ghost_pixmap(None)

    def _apply_ghost_overlay(self):
        if not self.ghost_checkbox.isChecked():
            self.canvas.set_ghost_pixmap(None)
            return
        data = self.ghost_frame_combo.currentData()
        if data is None:
            self.canvas.set_ghost_pixmap(None)
            return
        try:
            animation_id, index = data
        except (TypeError, ValueError):
            self.canvas.set_ghost_pixmap(None)
            return
        animation = self._animations.get(animation_id)
        if animation is None or index < 0 or index >= len(animation.frames):
            self.canvas.set_ghost_pixmap(None)
            return
        ghost_frame = animation.frames[index]
        self.canvas.set_ghost_pixmap(
            ghost_frame.pixmap,
            offset_x=ghost_frame.offset_x,
            offset_y=ghost_frame.offset_y,
        )

    def _refresh_ghost_if_frame_changed(self, frame_index: int):
        if not self.ghost_checkbox.isChecked():
            return
        data = self.ghost_frame_combo.currentData()
        if data is None:
            return
        try:
            animation_id, selected_index = data
        except (TypeError, ValueError):
            return
        if animation_id == self._current_animation_id and selected_index == frame_index:
            self._apply_ghost_overlay()

    def _on_ghost_toggled(self, checked: bool):
        self.ghost_frame_combo.setEnabled(checked and self.ghost_frame_combo.count() > 0)
        self._apply_ghost_overlay()

    def _on_ghost_frame_changed(self):
        if self.ghost_checkbox.isChecked():
            self._apply_ghost_overlay()

    def _on_snap_toggled(self, checked: bool):
        self.snap_step_spin.setEnabled(checked)
        self.canvas.configure_snapping(checked, self.snap_step_spin.value())

    def _on_snap_step_changed(self, value: int):
        self.canvas.configure_snapping(self.snap_checkbox.isChecked(), value)

    def _center_canvas_view(self):
        self.canvas.recenter_view()
        self.canvas.update()

    def _fit_canvas_to_viewport(self):
        viewport_size = self.canvas_scroll.viewport().size()
        self.canvas.fit_canvas_to_viewport(viewport_size)

    def _toggle_canvas_detach(self):
        if self._detached_window:
            self._detached_window.close()
            return

        self._detached_window = CanvasDetachWindow(self)
        self._detached_window.setWindowTitle(self.tr("Alignment Canvas"))
        dialog_layout = QVBoxLayout(self._detached_window)
        dialog_layout.setContentsMargins(6, 6, 6, 6)
        if self.canvas_holder.layout():
            self.canvas_holder.layout().removeWidget(self.canvas_scroll)
        self.canvas_scroll.setParent(self._detached_window)
        dialog_layout.addWidget(self.canvas_scroll)
        self._detached_window.closed.connect(self._reattach_canvas)
        self._detached_window.resize(self.canvas.sizeHint().width() + 120, self.canvas.sizeHint().height() + 120)
        self._detached_window.show()
        self.detach_canvas_button.setText(self.tr("Reattach Canvas"))

    def _reattach_canvas(self):
        if not self._detached_window:
            return
        dialog = self._detached_window
        self._detached_window = None
        if dialog.layout():
            dialog.layout().removeWidget(self.canvas_scroll)
        self.canvas_scroll.setParent(self.canvas_holder)
        holder_layout = self.canvas_holder.layout()
        if holder_layout is not None:
            holder_layout.addWidget(self.canvas_scroll)
        self.canvas_scroll.show()
        if dialog:
            dialog.deleteLater()
        self.detach_canvas_button.setText(self.tr("Detach Canvas"))

    # ------------------------------------------------------------------
    # Animation loading helpers
    # ------------------------------------------------------------------
    def _load_manual_files(self):
        if not PIL_AVAILABLE:
            QMessageBox.warning(self, self.tr("Missing dependency"), self.tr("Pillow is required to load animations."))
            return

        paths, _ = QFileDialog.getOpenFileNames(
            self,
            self.tr("Select animation files"),
            "",
            self.tr("Animation files (*.gif *.apng *.png *.webp);;All files (*.*)"),
        )
        for path in paths:
            animation = self._build_animation_from_file(path)
            if animation:
                self._register_animation(animation)

    def _build_animation_from_file(self, file_path: str) -> Optional[AlignmentAnimation]:
        if not file_path:
            return None

        try:
            with Image.open(file_path) as img:
                frames: List[AlignmentFrame] = []
                duration = int(img.info.get("duration", 100))
                for idx, frame in enumerate(ImageSequence.Iterator(img)):
                    frame = frame.convert("RGBA")
                    pixmap = self._pil_to_pixmap(frame)
                    frame_name = f"{os.path.basename(file_path)}#frame_{idx:04d}"
                    frames.append(
                        AlignmentFrame(
                            name=self.tr("Frame {index}").format(index=idx + 1),
                            original_key=frame_name,
                            pixmap=pixmap,
                            duration_ms=duration,
                        )
                    )

            if not frames:
                QMessageBox.warning(
                    self,
                    self.tr("Load failed"),
                    self.tr("{file} did not contain any frames.").format(file=os.path.basename(file_path)),
                )
                return None

            max_w = max(frame.pixmap.width() for frame in frames)
            max_h = max(frame.pixmap.height() for frame in frames)
            animation = AlignmentAnimation(
                display_name=os.path.basename(file_path),
                frames=frames,
                canvas_width=max_w,
                canvas_height=max_h,
                source="manual",
                metadata={"path": file_path},
            )
            animation.ensure_canvas_bounds()
            return animation
        except Exception as exc:
            QMessageBox.warning(
                self,
                self.tr("Load failed"),
                self.tr("Could not load {file}: {error}").format(file=os.path.basename(file_path), error=str(exc)),
            )
            return None

    def add_animation_from_extractor(
        self,
        spritesheet_name: str,
        animation_name: str,
        spritesheet_path: str,
        metadata_path: Optional[str],
        spritemap_info: Optional[dict] = None,
        spritemap_target: Optional[dict] = None,
    ):
        """Public entry point used by the extract tab to open an animation."""
        animation = self._build_animation_from_spritesheet(
            spritesheet_name,
            animation_name,
            spritesheet_path,
            metadata_path,
            spritemap_info,
            spritemap_target,
        )
        if animation:
            self._register_animation(animation)
            self.status_label.setText(
                self.tr("Loaded {animation} from {sheet}.").format(
                    animation=animation_name, sheet=spritesheet_name
                )
            )
            self._focus_latest_animation()
        else:
            QMessageBox.warning(
                self,
                self.tr("Editor"),
                self.tr("Could not load animation '{animation}' from '{sheet}'.").format(
                    animation=animation_name, sheet=spritesheet_name
                ),
            )

    def _build_animation_from_spritesheet(
        self,
        spritesheet_name: str,
        animation_name: str,
        spritesheet_path: str,
        metadata_path: Optional[str],
        spritemap_info: Optional[dict],
        spritemap_target: Optional[dict],
    ) -> Optional[AlignmentAnimation]:
        try:
            frames: List[AlignmentFrame] = []
            fps = 24
            if hasattr(self.parent_app, "settings_manager"):
                settings = self.parent_app.settings_manager.get_settings(
                    spritesheet_name, f"{spritesheet_name}/{animation_name}"
                )
                fps = settings.get("fps", fps)
            frame_duration = int(round(1000 / max(1, fps)))

            if spritemap_info:
                from core.spritemap import AdobeSpritemapRenderer

                target = spritemap_target or animation_name
                animation_json = spritemap_info.get("animation_json")
                spritemap_json = spritemap_info.get("spritemap_json")
                if not (animation_json and spritemap_json):
                    raise ValueError("Spritemap metadata is incomplete.")
                renderer = AdobeSpritemapRenderer(
                    animation_json,
                    spritemap_json,
                    spritesheet_path,
                    filter_single_frame=True,
                )
                raw_frames = renderer.render_animation(target)
            else:
                if not metadata_path:
                    raise ValueError("The selected spritesheet does not have metadata.")
                from core.atlas_processor import AtlasProcessor
                from core.sprite_processor import SpriteProcessor

                atlas_processor = AtlasProcessor(spritesheet_path, metadata_path)
                if metadata_path.endswith(".xml"):
                    animation_sprites = atlas_processor.parse_xml_for_preview(animation_name)
                elif metadata_path.endswith(".txt"):
                    animation_sprites = atlas_processor.parse_txt_for_preview(animation_name)
                else:
                    animation_sprites = []

                if not animation_sprites:
                    return None

                sprite_processor = SpriteProcessor(atlas_processor.atlas, animation_sprites)
                processed = sprite_processor.process_specific_animation(animation_name)
                raw_frames = processed.get(animation_name, [])

            if not raw_frames:
                return None

            for idx, frame_entry in enumerate(raw_frames):
                frame_name, pil_image, _meta = frame_entry
                pixmap = self._pil_to_pixmap(pil_image)
                frames.append(
                    AlignmentFrame(
                        name=frame_name,
                        original_key=frame_name,
                        pixmap=pixmap,
                        duration_ms=frame_duration,
                    )
                )

            max_w = max(frame.pixmap.width() for frame in frames)
            max_h = max(frame.pixmap.height() for frame in frames)
            animation = AlignmentAnimation(
                display_name=f"{spritesheet_name}/{animation_name}",
                frames=frames,
                canvas_width=max_w,
                canvas_height=max_h,
                source="extract",
                spritesheet_name=spritesheet_name,
                animation_name=animation_name,
                metadata={
                    "spritesheet_path": spritesheet_path,
                    "metadata_path": metadata_path or "",
                },
            )
            animation.ensure_canvas_bounds()

            overrides = {}
            if hasattr(self.parent_app, "settings_manager"):
                settings = self.parent_app.settings_manager.get_settings(
                    spritesheet_name, f"{spritesheet_name}/{animation_name}"
                )
                overrides = settings.get("alignment_overrides", {})
            if overrides:
                self._apply_alignment_overrides(animation, overrides)

            return animation
        except Exception as exc:
            print(f"[EditorTabWidget] Failed to build animation {animation_name}: {exc}")
            return None

    # ------------------------------------------------------------------
    # Animation registration / selection
    # ------------------------------------------------------------------
    def _register_animation(self, animation: AlignmentAnimation) -> str:
        animation_id = uuid.uuid4().hex
        self._animations[animation_id] = animation
        item = QTreeWidgetItem([animation.display_name])
        item.setData(0, ANIMATION_ID_ROLE, animation_id)
        item.setExpanded(True)
        self.animation_tree.addTopLevelItem(item)
        self._animation_items[animation_id] = item
        self._populate_frame_items(item, animation_id, animation)
        target = item.child(0) if item.childCount() > 0 else item
        self.animation_tree.setCurrentItem(target)
        self.animation_tree.scrollToItem(item)
        self._update_combine_button_state()
        self._refresh_ghost_options()
        return animation_id

    def _populate_frame_items(
        self, animation_item: QTreeWidgetItem, animation_id: str, animation: AlignmentAnimation
    ):
        while animation_item.childCount():
            animation_item.removeChild(animation_item.child(0))
        for idx, frame in enumerate(animation.frames):
            label = f"{frame.name}  ({frame.pixmap.width()}x{frame.pixmap.height()})"
            child = QTreeWidgetItem([label])
            child.setData(0, ANIMATION_ID_ROLE, animation_id)
            child.setData(0, FRAME_INDEX_ROLE, idx)
            animation_item.addChild(child)

    def _focus_latest_animation(self):
        count = self.animation_tree.topLevelItemCount()
        if count <= 0:
            return
        item = self.animation_tree.topLevelItem(count - 1)
        target = item.child(0) if item.childCount() > 0 else item
        self.animation_tree.setCurrentItem(target)
        self.animation_tree.scrollToItem(item)

    def _remove_selected_animation(self):
        current_item = self.animation_tree.currentItem()
        if not current_item:
            return
        animation_item = current_item if current_item.parent() is None else current_item.parent()
        animation_id = animation_item.data(0, ANIMATION_ID_ROLE)
        if animation_id in self._animations:
            del self._animations[animation_id]
        self._animation_items.pop(animation_id, None)
        index = self.animation_tree.indexOfTopLevelItem(animation_item)
        if index >= 0:
            self.animation_tree.takeTopLevelItem(index)
        self._current_animation_id = None
        self._current_frame_index = -1
        self.canvas.set_pixmap(None)
        self.save_overrides_button.setEnabled(False)
        self._update_combine_button_state()
        self._refresh_ghost_options()
        self.export_composite_button.setEnabled(False)

    def _combine_selected_animations(self):
        selected_items = [item for item in self.animation_tree.selectedItems() if item.parent() is None]
        if len(selected_items) < 2:
            QMessageBox.information(
                self,
                self.tr("Need more animations"),
                self.tr("Select at least two animations to build a composite entry."),
            )
            return

        combined_frames: List[AlignmentFrame] = []
        composite_sources: List[str] = []
        source_animation_ids: List[str] = []
        max_frame_width = 0
        max_frame_height = 0

        for item in selected_items:
            animation_id = item.data(0, ANIMATION_ID_ROLE)
            animation = self._animations.get(animation_id)
            if not animation:
                continue
            composite_sources.append(animation.display_name)
            if animation_id not in source_animation_ids:
                source_animation_ids.append(animation_id)
            for index, frame in enumerate(animation.frames):
                max_frame_width = max(max_frame_width, frame.pixmap.width())
                max_frame_height = max(max_frame_height, frame.pixmap.height())
                combined_frames.append(
                    AlignmentFrame(
                        name=f"{animation.display_name} - {frame.name}",
                        original_key=frame.original_key,
                        pixmap=frame.pixmap,
                        duration_ms=frame.duration_ms,
                        offset_x=frame.offset_x,
                        offset_y=frame.offset_y,
                        metadata={
                            "source_animation_id": animation_id,
                            "source_frame_index": str(index),
                        },
                    )
                )

        if len(composite_sources) < 2 or not combined_frames:
            QMessageBox.warning(
                self,
                self.tr("Combine failed"),
                self.tr("Could not build the composite entry. Ensure the selected animations have frames."),
            )
            return

        if len(composite_sources) > 3:
            display_name = self.tr("Composite ({count} animations)").format(count=len(composite_sources))
        else:
            display_name = self.tr("Composite: {names}").format(names=", ".join(composite_sources))

        canvas_width = min(4096, max(8, (max_frame_width or 256) * 2))
        canvas_height = min(4096, max(8, (max_frame_height or 256) * 2))

        composite_animation = AlignmentAnimation(
            display_name=display_name,
            frames=combined_frames,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
            source="manual",
            metadata={
                "composite_of": ",".join(composite_sources),
                "source_animation_ids": ",".join(source_animation_ids),
            },
            default_offset=(0, 0),
        )
        composite_animation.ensure_canvas_bounds()
        self._register_animation(composite_animation)
        self.status_label.setText(
            self.tr("Composite entry created with {count} frames.").format(count=len(combined_frames))
        )

    # ------------------------------------------------------------------
    # Selection handlers
    # ------------------------------------------------------------------
    def _on_tree_current_changed(self, current: Optional[QTreeWidgetItem], previous: Optional[QTreeWidgetItem]):
        if not current:
            self._current_animation_id = None
            self._current_frame_index = -1
            self._root_alignment_mode = False
            self.canvas.set_pixmap(None)
            self.save_overrides_button.setEnabled(False)
            self.export_composite_button.setEnabled(False)
            self._refresh_ghost_options()
            return

        animation_id = current.data(0, ANIMATION_ID_ROLE)
        if not animation_id:
            return

        animation = self._animations.get(animation_id)
        if animation is None:
            return

        frame_index = current.data(0, FRAME_INDEX_ROLE)
        animation_changed = animation_id != self._current_animation_id
        self._current_animation_id = animation_id

        if frame_index is None:
            self._enter_root_alignment_mode(animation, animation_changed)
            return

        self._root_alignment_mode = False
        self._current_frame_index = int(frame_index)
        frame = animation.frames[self._current_frame_index]
        self.canvas.set_pixmap(frame.pixmap)
        self.canvas.set_canvas_size(animation.canvas_width, animation.canvas_height)
        self._updating_controls = True
        self.offset_x_spin.setValue(frame.offset_x)
        self.offset_y_spin.setValue(frame.offset_y)
        self._updating_controls = False
        self.canvas.set_offsets(frame.offset_x, frame.offset_y)
        self.canvas_width_spin.setValue(animation.canvas_width)
        self.canvas_height_spin.setValue(animation.canvas_height)
        self.save_overrides_button.setEnabled(animation.source == "extract")
        self.export_composite_button.setEnabled(bool(animation.metadata.get("source_animation_ids")))
        if animation_changed:
            self._refresh_ghost_options()
        self.status_label.setText(self._default_status_text)

    def focus_animation_by_id(self, animation_id: str) -> bool:
        item = self._animation_items.get(animation_id)
        if item is None:
            return False
        target = item.child(0) if item.childCount() > 0 else item
        self.animation_tree.setCurrentItem(target)
        self.animation_tree.scrollToItem(item)
        return True

    def _determine_root_display_offsets(self, animation: AlignmentAnimation) -> Tuple[int, int]:
        if not animation.frames:
            return animation.default_offset
        offsets = {(frame.offset_x, frame.offset_y) for frame in animation.frames}
        if len(offsets) == 1:
            return offsets.pop()
        return animation.default_offset

    def _enter_root_alignment_mode(self, animation: AlignmentAnimation, animation_changed: bool):
        self._root_alignment_mode = True
        preview_index = 0
        if 0 <= self._current_frame_index < len(animation.frames):
            preview_index = self._current_frame_index
        preview_index = max(0, min(preview_index, len(animation.frames) - 1)) if animation.frames else -1
        self._current_frame_index = preview_index

        if preview_index >= 0:
            frame = animation.frames[preview_index]
            self.canvas.set_pixmap(frame.pixmap)
            self.canvas.set_canvas_size(animation.canvas_width, animation.canvas_height)
            offset_x, offset_y = self._determine_root_display_offsets(animation)
            self._updating_controls = True
            self.offset_x_spin.setValue(offset_x)
            self.offset_y_spin.setValue(offset_y)
            self._updating_controls = False
            self.canvas.set_offsets(offset_x, offset_y)
        else:
            self.canvas.set_pixmap(None)
            offset_x, offset_y = animation.default_offset
            self._updating_controls = True
            self.offset_x_spin.setValue(offset_x)
            self.offset_y_spin.setValue(offset_y)
            self._updating_controls = False
            self.canvas.set_offsets(offset_x, offset_y)

        self.canvas_width_spin.setValue(animation.canvas_width)
        self.canvas_height_spin.setValue(animation.canvas_height)
        self.save_overrides_button.setEnabled(animation.source == "extract")
        self.export_composite_button.setEnabled(bool(animation.metadata.get("source_animation_ids")))
        if animation_changed:
            self._refresh_ghost_options()
        self.status_label.setText(
            self.tr("Root selected: offset changes now apply to every frame in this animation.")
        )

    # ------------------------------------------------------------------
    # Offset handling
    # ------------------------------------------------------------------
    def _apply_offsets_to_animation(
        self,
        animation: AlignmentAnimation,
        offset_x: int,
        offset_y: int,
        update_default: bool = False,
    ):
        for frame in animation.frames:
            frame.offset_x = offset_x
            frame.offset_y = offset_y
            self._propagate_frame_offset(frame)
        if update_default:
            animation.default_offset = (offset_x, offset_y)
        if self.ghost_checkbox.isChecked():
            self._apply_ghost_overlay()

    def _on_manual_offset_changed(self):
        if self._updating_controls or self._current_animation_id is None:
            return
        animation = self._animations.get(self._current_animation_id)
        if animation is None or (self._current_frame_index < 0 and not self._root_alignment_mode):
            return
        offset_x = self.offset_x_spin.value()
        offset_y = self.offset_y_spin.value()
        self.canvas.set_offsets(offset_x, offset_y)
        if self._root_alignment_mode:
            self._apply_offsets_to_animation(animation, offset_x, offset_y, update_default=True)
            return
        frame = animation.frames[self._current_frame_index]
        frame.offset_x = offset_x
        frame.offset_y = offset_y
        self._propagate_frame_offset(frame)
        self._refresh_ghost_if_frame_changed(self._current_frame_index)

    def _on_canvas_dragged(self, offset_x: int, offset_y: int):
        if self._updating_controls or self._current_animation_id is None:
            return
        animation = self._animations.get(self._current_animation_id)
        if animation is None or (self._current_frame_index < 0 and not self._root_alignment_mode):
            return
        self._updating_controls = True
        self.offset_x_spin.setValue(offset_x)
        self.offset_y_spin.setValue(offset_y)
        self._updating_controls = False
        if self._root_alignment_mode:
            self._apply_offsets_to_animation(animation, offset_x, offset_y, update_default=True)
            return
        frame = animation.frames[self._current_frame_index]
        frame.offset_x = offset_x
        frame.offset_y = offset_y
        self._propagate_frame_offset(frame)
        self._refresh_ghost_if_frame_changed(self._current_frame_index)

    def _propagate_frame_offset(self, frame: AlignmentFrame):
        source_animation_id = frame.metadata.get("source_animation_id")
        if not source_animation_id:
            return
        source_index_value = frame.metadata.get("source_frame_index")
        if source_index_value is None:
            return
        try:
            source_index = int(source_index_value)
        except (TypeError, ValueError):
            return
        target_animation = self._animations.get(source_animation_id)
        if not target_animation or not (0 <= source_index < len(target_animation.frames)):
            return
        target_frame = target_animation.frames[source_index]
        target_frame.offset_x = frame.offset_x
        target_frame.offset_y = frame.offset_y

    def _apply_offsets_to_all_frames(self):
        if self._current_animation_id is None:
            return
        animation = self._animations.get(self._current_animation_id)
        if animation is None or self._current_frame_index < 0:
            return
        frame = animation.frames[self._current_frame_index]
        offset_x = frame.offset_x
        offset_y = frame.offset_y
        self._apply_offsets_to_animation(animation, offset_x, offset_y, update_default=True)
        self._refresh_ghost_if_frame_changed(self._current_frame_index)
        self.status_label.setText(
            self.tr("Applied ({x}, {y}) to every frame.").format(
                x=offset_x, y=offset_y
            )
        )
        self.canvas.set_offsets(offset_x, offset_y)
        if self._root_alignment_mode:
            self._updating_controls = True
            self.offset_x_spin.setValue(offset_x)
            self.offset_y_spin.setValue(offset_y)
            self._updating_controls = False

    def _reset_frame_offset(self):
        if self._current_animation_id is None:
            return
        animation = self._animations.get(self._current_animation_id)
        if animation is None:
            return
        default_x, default_y = animation.default_offset
        if self._root_alignment_mode:
            self._apply_offsets_to_animation(animation, default_x, default_y, update_default=False)
            self._updating_controls = True
            self.offset_x_spin.setValue(default_x)
            self.offset_y_spin.setValue(default_y)
            self._updating_controls = False
            self.canvas.set_offsets(default_x, default_y)
            return
        if self._current_frame_index < 0:
            return
        frame = animation.frames[self._current_frame_index]
        frame.offset_x = default_x
        frame.offset_y = default_y
        self._updating_controls = True
        self.offset_x_spin.setValue(default_x)
        self.offset_y_spin.setValue(default_y)
        self._updating_controls = False
        self.canvas.set_offsets(default_x, default_y)
        self._propagate_frame_offset(frame)
        self._refresh_ghost_if_frame_changed(self._current_frame_index)

    def _on_canvas_size_changed(self):
        if self._current_animation_id is None:
            return
        animation = self._animations.get(self._current_animation_id)
        if animation is None:
            return
        animation.canvas_width = self.canvas_width_spin.value()
        animation.canvas_height = self.canvas_height_spin.value()
        self.canvas.set_canvas_size(animation.canvas_width, animation.canvas_height)

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _save_alignment_to_settings(self):
        if self._current_animation_id is None:
            return
        animation = self._animations.get(self._current_animation_id)
        if animation is None or animation.source != "extract":
            return

        payload = self._build_alignment_payload(animation)
        full_name = f"{animation.spritesheet_name}/{animation.animation_name}"
        settings = self.parent_app.settings_manager.animation_settings.setdefault(full_name, {})
        settings["alignment_overrides"] = payload
        QMessageBox.information(
            self,
            self.tr("Alignment saved"),
            self.tr("Offsets stored for '{name}'. They will be used on the next extraction run.").format(
                name=full_name
            ),
        )

    def _export_composite_to_sprites(self):
        if self._current_animation_id is None:
            return
        animation = self._animations.get(self._current_animation_id)
        if animation is None:
            return
        source_ids_value = animation.metadata.get("source_animation_ids")
        if not source_ids_value:
            QMessageBox.information(
                self,
                self.tr("Export composite"),
                self.tr("Select a composite entry generated from multiple animations."),
            )
            return

        source_ids = [item for item in source_ids_value.split(",") if item]
        if not source_ids:
            QMessageBox.warning(
                self,
                self.tr("Export composite"),
                self.tr("Could not determine the source animations for this composite."),
            )
            return

        source_animations: List[AlignmentAnimation] = []
        for source_id in source_ids:
            item = self._animations.get(source_id)
            if item:
                source_animations.append(item)

        if not source_animations:
            QMessageBox.warning(
                self,
                self.tr("Export composite"),
                self.tr("Source animations are no longer available in the session."),
            )
            return

        if any(anim.source != "extract" for anim in source_animations):
            QMessageBox.warning(
                self,
                self.tr("Export composite"),
                self.tr("Composite export currently supports animations loaded from the extractor only."),
            )
            return

        base_spritesheet = source_animations[0].spritesheet_name
        base_metadata = dict(source_animations[0].metadata or {})
        spritesheet_path = base_metadata.get("spritesheet_path")
        metadata_path = base_metadata.get("metadata_path")
        if not base_spritesheet:
            QMessageBox.warning(
                self,
                self.tr("Export composite"),
                self.tr("Composite export requires animations that originated from the extractor."),
            )
            return

        different_sheet = any(anim.spritesheet_name != base_spritesheet for anim in source_animations)
        if different_sheet:
            QMessageBox.warning(
                self,
                self.tr("Export composite"),
                self.tr("All combined animations must belong to the same spritesheet."),
            )
            return

        default_name = self.tr("Composite_{count}").format(count=len(source_animations))
        animation_name, accepted = QInputDialog.getText(
            self,
            self.tr("Composite name"),
            self.tr("Enter a name for the exported animation"),
            text=default_name,
        )
        if not accepted or not animation_name.strip():
            return
        animation_name = animation_name.strip()

        new_frames: List[AlignmentFrame] = []
        for frame in animation.frames:
            new_frames.append(
                AlignmentFrame(
                    name=frame.name,
                    original_key=frame.original_key,
                    pixmap=frame.pixmap,
                    duration_ms=frame.duration_ms,
                    offset_x=frame.offset_x,
                    offset_y=frame.offset_y,
                )
            )

        export_metadata = {
            "spritesheet_path": spritesheet_path,
            "metadata_path": metadata_path,
            "exported_from": animation.display_name,
            "composite_sources": animation.metadata.get("composite_of", ""),
        }

        exported_animation = AlignmentAnimation(
            display_name=f"{base_spritesheet}/{animation_name}",
            frames=new_frames,
            canvas_width=animation.canvas_width,
            canvas_height=animation.canvas_height,
            source="extract",
            spritesheet_name=base_spritesheet,
            animation_name=animation_name,
            metadata=export_metadata,
            default_offset=animation.default_offset,
        )
        exported_animation.ensure_canvas_bounds()
        new_animation_id = self._register_animation(exported_animation)
        self.status_label.setText(
            self.tr("Exported composite to {name}.").format(name=exported_animation.display_name)
        )
        if hasattr(self.parent_app, "extract_tab_widget") and getattr(self.parent_app, "extract_tab_widget"):
            try:
                self.parent_app.extract_tab_widget.register_editor_composite(
                    base_spritesheet,
                    animation_name,
                    new_animation_id,
                )
            except Exception as exc:
                print(f"[EditorTabWidget] Failed to register composite in Extract tab: {exc}")

    def _build_alignment_payload(self, animation: AlignmentAnimation) -> dict:
        frames_payload = {}
        for frame in animation.frames:
            frames_payload[frame.original_key] = {"x": frame.offset_x, "y": frame.offset_y}
        return {
            "canvas": [animation.canvas_width, animation.canvas_height],
            "default": {"x": animation.default_offset[0], "y": animation.default_offset[1]},
            "frames": frames_payload,
        }

    def _apply_alignment_overrides(self, animation: AlignmentAnimation, overrides: dict):
        canvas = overrides.get("canvas")
        if canvas and len(canvas) == 2:
            animation.canvas_width = int(canvas[0])
            animation.canvas_height = int(canvas[1])
        default_values = overrides.get("default", {})
        animation.default_offset = (
            int(default_values.get("x", 0)),
            int(default_values.get("y", 0)),
        )
        frame_map = overrides.get("frames", {})
        for frame in animation.frames:
            data = frame_map.get(frame.original_key)
            if data is None:
                frame.offset_x = animation.default_offset[0]
                frame.offset_y = animation.default_offset[1]
                continue
            frame.offset_x = int(data.get("x", animation.default_offset[0]))
            frame.offset_y = int(data.get("y", animation.default_offset[1]))

    def closeEvent(self, event):  # noqa: D401 - Qt API
        if self._detached_window:
            self._detached_window.close()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _pil_to_pixmap(image) -> QPixmap:
        image = image.convert("RGBA")
        data = image.tobytes("raw", "RGBA")
        bytes_per_line = image.width * 4
        qimage = QImage(
            data,
            image.width,
            image.height,
            bytes_per_line,
            QImage.Format.Format_RGBA8888,
        )
        return QPixmap.fromImage(qimage.copy())
