from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt, QStringListModel)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform, QDesktopServices)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialogButtonBox, QFrame,
    QGridLayout, QLabel, QLayout, QSizePolicy, QMainWindow, QWidget, QFileDialog)

import os
import re
import xml.etree.ElementTree as ET

class FileHandler:
    def __init__(self, input_ui_group, input_dir, spritelist_ui_box, animationlist_ui_box, user_settings, override_settings_ui_group):
        self.input_dir = input_dir
        self.input_ui_location = input_ui_group
        self.spritelist_ui_box = spritelist_ui_box
        self.animationlist_ui_box = animationlist_ui_box
        self.user_settings = user_settings
        self.override_settings_ui_group = override_settings_ui_group
        self.override_settings = {}  # This dictionary will remember which entries have the checkbox ticked for override

        # Initialize models
        self.model = QStringListModel()
        self.spritelist_ui_box.setModel(QStringListModel())
        self.animationlist_ui_box.setModel(QStringListModel())

    def select_directory(self):
        directory = QFileDialog.getExistingDirectory()
        if directory:
            self.input_dir = directory
            png_files = []
            for filename in os.listdir(directory):
                if filename.endswith('.png'):
                    png_files.append(filename)

            model = self.spritelist_ui_box.model()
            model.setStringList(png_files)

    def on_select_png(self, selected):
        self.animationlist_ui_box.setModel(None)

        png_filename = selected.indexes()[0].data()
        xml_filename = os.path.splitext(png_filename)[0] + '.xml'

        tree = ET.parse(os.path.join(self.input_dir, xml_filename))
        root = tree.getroot()
        names = set()
        for subtexture in root.findall(".//SubTexture"):
            name = subtexture.get('name')
            name = re.sub(r'\d{1,4}(?:\.png)?$', '', name).rstrip()
            names.add(name)

        model = QStringListModel(list(names))
        self.animationlist_ui_box.setModel(model)
                    
    def on_animation_selected(self, selected):
        animation_name = selected.indexes()[0].data(Qt.DisplayRole)

        if animation_name in self.override_settings:
            fps, delay, alpha = self.override_settings[animation_name]
            self.override_settings_ui_group.setChecked(True)
        elif animation_name in self.user_settings:
            fps, delay, alpha = self.user_settings[animation_name]
            self.override_settings_ui_group.setChecked(False)
        else:
            fps = delay = alpha = 0
            self.override_settings_ui_group.setChecked(False)

        self.fps_ui_stepper_override.setValue(fps)
        self.delay_ui_stepper_override.setValue(delay)
        self.alpha_ui_stepper_override.setValue(alpha)
        
        self.override_settings_ui_group.setChecked(animation_name in self.override_settings)
        self.on_override_settings_changed(self.override_settings_ui_group.isChecked())



    def on_override_settings_changed(self, state):
        animation_name = self.animationlist_ui_box.currentIndex().data(Qt.DisplayRole)
        if state == Qt.Checked:
            fps = self.fps_ui_stepper_override.value()
            delay = self.delay_ui_stepper_override.value()
            alpha = self.alpha_ui_stepper_override.value()
            self.override_settings[animation_name] = (fps, delay, alpha)
        elif state == Qt.Unchecked and animation_name in self.override_settings:
            del self.override_settings[animation_name]
        self.save_override_settings()
        
    def save_override_settings(self):
        for animation_name, settings in self.override_settings.items():
            self.user_settings[animation_name] = settings