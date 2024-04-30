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
    def __init__(self, input_ui_group, input_dir, spritelist_ui_box, animationlist_ui_box):
        self.input_dir = input_dir
        self.input_ui_location = input_ui_group
        self.spritelist_ui_box = spritelist_ui_box
        self.animationlist_ui_box = animationlist_ui_box

    def select_directory(self):
        directory = QFileDialog.getExistingDirectory()
        if directory:
            self.input_dir = directory

            self.spritelist_ui_box.setModel(None)
            self.animationlist_ui_box.setModel(None)

            png_files = []
            for filename in os.listdir(directory):
                if filename.endswith('.png'):
                    png_files.append(filename)

            model = QStringListModel()
            model.setStringList(png_files)
            self.spritelist_ui_box.setModel(model)

    def on_select_png(self, selected, deselected):
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

        model = QStringListModel()
        model.setStringList(list(names))
        self.animationlist_ui_box.setModel(model)
                    
    def on_animation_selected(self, selected, deselected):
        if self.override_settings_ui_group.isChecked():
    
            animation_name = selected.indexes()[0].data()
            if animation_name in user_settings:
                fps, delay, alpha = user_settings[animation_name]

                self.fps_ui_stepper_override.setValue(fps)
                self.delay_ui_stepper_override.setValue(delay)
                self.alpha_ui_stepper_override.setValue(alpha)