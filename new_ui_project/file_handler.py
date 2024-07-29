from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt, QStringListModel)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform, QDesktopServices, QStandardItem, QStandardItemModel)

from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialogButtonBox, QFrame,
    QGridLayout, QLabel, QLayout, QSizePolicy, QMainWindow, QWidget, QFileDialog)

import os
import re
import xml.etree.ElementTree as ET

class FileHandler:
    def __init__(self, input_ui_group, input_dir, spritelist_ui_box, animationlist_ui_box, user_settings, override_settings_ui_group, fps_ui_stepper_override, delay_ui_stepper_override, alpha_ui_stepper_override):
        self.input_dir = input_dir
        self.input_ui_location = input_ui_group
        
        self.spritelist_ui_box = spritelist_ui_box
        self.animationlist_ui_box = animationlist_ui_box
        
        self.user_settings = user_settings
       
        self.override_settings_ui_group = override_settings_ui_group
        self.override_settings = {}  # This dictionary will remember which entries have the checkbox ticked for override
        
        self.fps_ui_stepper_override = fps_ui_stepper_override
        self.delay_ui_stepper_override = delay_ui_stepper_override
        self.alpha_ui_stepper_override = alpha_ui_stepper_override

        self.model = QStandardItemModel()
        self.spritelist_ui_box.setModel(self.model)
        self.animationlist_ui_box.setModel(QStandardItemModel())

    def select_directory(self):
        directory = QFileDialog.getExistingDirectory()
        if directory:
            self.input_dir = directory
            png_files = []
            for filename in os.listdir(directory):
                if filename.endswith('.png'):
                    png_files.append(filename)

            self.model.clear()
            for filename in png_files:
                item = QStandardItem(filename)
                self.model.appendRow(item)

    def on_select_png(self, selected):
        png_filename = selected.indexes()[0].data()
        xml_filename = os.path.splitext(png_filename)[0] + '.xml'

        tree = ET.parse(os.path.join(self.input_dir, xml_filename))
        root = tree.getroot()
        names = set()
        for subtexture in root.findall(".//SubTexture"):
            name = subtexture.get('name')
            name = re.sub(r'\d{1,4}(?:\.png)?$', '', name).rstrip()
            names.add(name)

        model = self.animationlist_ui_box.model()
        model.clear()
        for name in names:
            item = QStandardItem(name)
            if name in self.override_settings:
                item.setData(self.override_settings[name], Qt.UserRole)
            model.appendRow(item)

    def on_animation_selected(self, selected):
        animation_name = selected.indexes()[0].data()
        print(f"Selected animation: {animation_name}")  # Debug print

        if animation_name in self.override_settings:
            print(f"Setting checkbox to True for {animation_name}")  # Debug print
            self.override_settings_ui_group.setChecked(True)
            fps, delay, alpha = self.override_settings[animation_name]
            self.fps_ui_stepper_override.setValue(fps)
            self.delay_ui_stepper_override.setValue(delay)
            self.alpha_ui_stepper_override.setValue(alpha)
        else:
            print(f"Setting checkbox to False for {animation_name}")  # Debug print
            self.override_settings_ui_group.setChecked(False)

    def on_override_settings_changed(self):
        animation_name = self.animationlist_ui_box.currentIndex().data(Qt.DisplayRole)
        if self.override_settings_ui_group.isChecked():
            fps = self.fps_ui_stepper_override.value()
            delay = self.delay_ui_stepper_override.value()
            alpha = self.alpha_ui_stepper_override.value()
            self.override_settings[animation_name] = (fps, delay, alpha)
            item = self.animationlist_ui_box.model().item(self.animationlist_ui_box.currentIndex().row())
            item.setData((fps, delay, alpha), Qt.UserRole)
    
        elif not self.override_settings_ui_group.isChecked() and animation_name in self.override_settings:
            self.override_settings.pop(animation_name, None)
            item = self.animationlist_ui_box.model().item(self.animationlist_ui_box.currentIndex().row())
            item.setData(None, Qt.UserRole)
