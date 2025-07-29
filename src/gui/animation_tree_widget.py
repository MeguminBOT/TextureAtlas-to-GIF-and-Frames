#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
from PySide6.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QMessageBox,
    QInputDialog,
    QMenu,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QAction


class AnimationTreeWidget(QTreeWidget):
    """Custom tree widget for managing animation groups and frame ordering."""

    # Signals
    animation_added = Signal(str)  # animation_name
    animation_removed = Signal(str)  # animation_name
    frame_order_changed = Signal()  # general signal for any frame order change

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_tree()

    def tr(self, text):
        """Translation helper method."""
        from PySide6.QtCore import QCoreApplication

        return QCoreApplication.translate(self.__class__.__name__, text)

    def setup_tree(self):
        """Set up the tree widget properties."""
        self.setHeaderLabel(self.tr("Animations & Frames"))
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

        # Enable context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # Connect item changes
        self.itemChanged.connect(self.on_item_changed)

    def add_animation_group(self, animation_name=None):
        """Add a new animation group."""
        if animation_name is None:
            animation_name = self.tr("New animation")

        # Check if animation name already exists
        if self.find_animation_group(animation_name):
            counter = 1
            while self.find_animation_group(f"{animation_name} {counter}"):
                counter += 1
            animation_name = f"{animation_name} {counter}"

        # Create the group item
        group_item = QTreeWidgetItem(self)
        group_item.setText(0, animation_name)
        group_item.setFlags(group_item.flags() | Qt.ItemFlag.ItemIsEditable)

        # Make it bold to distinguish from frame items
        font = QFont()
        font.setBold(True)
        group_item.setFont(0, font)

        # Store metadata
        group_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "animation_group"})

        # Expand the group
        group_item.setExpanded(True)

        # Select the new group
        self.setCurrentItem(group_item)

        # Emit signal
        self.animation_added.emit(animation_name)

        return group_item

    def add_frame_to_animation(self, animation_name, frame_path):
        """Add a frame to an animation group."""
        group_item = self.find_animation_group(animation_name)
        if not group_item:
            group_item = self.add_animation_group(animation_name)

        # Create frame item
        frame_item = QTreeWidgetItem(group_item)
        frame_item.setText(0, Path(frame_path).name)
        frame_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "frame", "path": frame_path})

        # Make it selectable but not editable
        frame_item.setFlags(frame_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

        # Update frame numbering
        self.update_frame_numbering(group_item)

        return frame_item

    def remove_animation_group(self, animation_name):
        """Remove an animation group and all its frames."""
        group_item = self.find_animation_group(animation_name)
        if group_item:
            # Remove from tree
            root = self.invisibleRootItem()
            root.removeChild(group_item)

            # Emit signal
            self.animation_removed.emit(animation_name)

            return True
        return False

    def remove_frame_from_animation(self, frame_item):
        """Remove a frame from its animation group."""
        if frame_item:
            parent = frame_item.parent()
            if parent:
                parent.removeChild(frame_item)
                # Update frame numbering
                self.update_frame_numbering(parent)
                self.frame_order_changed.emit()
                return True
        return False

    def find_animation_group(self, animation_name):
        """Find an animation group by name."""
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.text(0) == animation_name:
                data = item.data(0, Qt.ItemDataRole.UserRole)
                if data and data.get("type") == "animation_group":
                    return item
        return None

    def get_animation_groups(self):
        """Get all animation groups and their frames."""
        animations = {}
        root = self.invisibleRootItem()

        for i in range(root.childCount()):
            group_item = root.child(i)
            data = group_item.data(0, Qt.ItemDataRole.UserRole)

            if data and data.get("type") == "animation_group":
                animation_name = group_item.text(0)
                frames = []

                # Get all frames in order
                for j in range(group_item.childCount()):
                    frame_item = group_item.child(j)
                    frame_data = frame_item.data(0, Qt.ItemDataRole.UserRole)

                    if frame_data and frame_data.get("type") == "frame":
                        frames.append(
                            {"path": frame_data["path"], "name": frame_item.text(0), "order": j}
                        )

                animations[animation_name] = frames

        return animations

    def update_frame_numbering(self, group_item):
        """Update the display names of frames to show proper numbering."""
        if not group_item:
            return

        animation_name = group_item.text(0)

        for i in range(group_item.childCount()):
            frame_item = group_item.child(i)
            frame_data = frame_item.data(0, Qt.ItemDataRole.UserRole)

            if frame_data and frame_data.get("type") == "frame":
                # Get original filename
                original_path = frame_data["path"]
                original_name = Path(original_path).name

                # Create new display name with frame number
                frame_number = f"{i:04d}"  # 0000, 0001, 0002, etc.
                display_name = f"{original_name} → {animation_name}{frame_number}"

                frame_item.setText(0, display_name)

    def clear_all_animations(self):
        """Clear all animation groups and frames."""
        self.clear()

    def get_frame_paths_for_animation(self, animation_name):
        """Get ordered list of frame paths for a specific animation."""
        group_item = self.find_animation_group(animation_name)
        if not group_item:
            return []

        frame_paths = []
        for i in range(group_item.childCount()):
            frame_item = group_item.child(i)
            frame_data = frame_item.data(0, Qt.ItemDataRole.UserRole)

            if frame_data and frame_data.get("type") == "frame":
                frame_paths.append(frame_data["path"])

        return frame_paths

    def show_context_menu(self, position):
        """Show context menu for tree items."""
        item = self.itemAt(position)
        if not item:
            # Right-click on empty space
            menu = QMenu(self)

            add_action = QAction(self.tr("Add animation group"), self)
            add_action.triggered.connect(self.add_animation_group)
            menu.addAction(add_action)

            menu.exec(self.mapToGlobal(position))
            return

        # Get item data
        data = item.data(0, Qt.ItemDataRole.UserRole)

        if data and data.get("type") == "animation_group":
            # Context menu for animation group
            menu = QMenu(self)

            rename_action = QAction(self.tr("Rename animation"), self)
            rename_action.triggered.connect(lambda: self.rename_animation_group(item))
            menu.addAction(rename_action)

            menu.addSeparator()

            delete_action = QAction(self.tr("Delete animation"), self)
            delete_action.triggered.connect(lambda: self.delete_animation_group(item))
            menu.addAction(delete_action)

            menu.exec(self.mapToGlobal(position))

        elif data and data.get("type") == "frame":
            # Context menu for frame
            menu = QMenu(self)

            remove_action = QAction(self.tr("Remove frame"), self)
            remove_action.triggered.connect(lambda: self.remove_frame_from_animation(item))
            menu.addAction(remove_action)

            menu.exec(self.mapToGlobal(position))

    def rename_animation_group(self, group_item):
        """Rename an animation group."""
        old_name = group_item.text(0)
        new_name, ok = QInputDialog.getText(
            self, self.tr("Rename animation"), self.tr("Enter new animation name:"), text=old_name
        )

        if ok and new_name and new_name != old_name:
            # Check if name already exists
            if self.find_animation_group(new_name):
                QMessageBox.warning(
                    self,
                    self.tr("Name conflict"),
                    self.tr("An animation named '{0}' already exists.").format(new_name),
                )
                return

            # Update the group name
            group_item.setText(0, new_name)

            # Update frame numbering to reflect new name
            self.update_frame_numbering(group_item)

            # Emit signals
            self.animation_removed.emit(old_name)
            self.animation_added.emit(new_name)

    def delete_animation_group(self, group_item):
        """Delete an animation group after confirmation."""
        animation_name = group_item.text(0)

        reply = QMessageBox.question(
            self,
            self.tr("Delete animation"),
            self.tr(
                "Are you sure you want to delete the animation '{0}' and all its frames?"
            ).format(animation_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.remove_animation_group(animation_name)

    def on_item_changed(self, item, column):
        """Handle item name changes."""
        if column == 0:  # Name column
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") == "animation_group":
                # Animation group was renamed
                # Update frame numbering
                self.update_frame_numbering(item)

                # Note: We don't emit signals here to avoid double emission
                # The rename_animation_group method handles signal emission

    def dropEvent(self, event):
        """Handle drop events to maintain proper frame ordering."""
        super().dropEvent(event)

        # After drop, update frame numbering for all affected groups
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            group_item = root.child(i)
            data = group_item.data(0, Qt.ItemDataRole.UserRole)

            if data and data.get("type") == "animation_group":
                self.update_frame_numbering(group_item)

        # Emit frame order changed signal
        self.frame_order_changed.emit()

    def get_total_frame_count(self):
        """Get the total number of frames across all animations."""
        total = 0
        root = self.invisibleRootItem()

        for i in range(root.childCount()):
            group_item = root.child(i)
            data = group_item.data(0, Qt.ItemDataRole.UserRole)

            if data and data.get("type") == "animation_group":
                total += group_item.childCount()

        return total

    def get_animation_count(self):
        """Get the number of animation groups."""
        count = 0
        root = self.invisibleRootItem()

        for i in range(root.childCount()):
            group_item = root.child(i)
            data = group_item.data(0, Qt.ItemDataRole.UserRole)

            if data and data.get("type") == "animation_group":
                count += 1

        return count
