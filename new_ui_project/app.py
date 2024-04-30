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

from user_interface import Ui_MainWindow
from update_interface import Ui_update_window
from file_handler import FileHandler

class AppWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        
        self.filehandler = FileHandler(self.input_dir, self.spritelist_ui_box, self.animationlist_ui_box)
        self.input_ui_button.clicked.connect(self.filehandler.select_directory)

        self.spritelist_ui_box.selectionModel().selectionChanged.connect(self.filehandler.on_select_png)
        self.animationlist_ui_box.selectionModel().selectionChanged.connect(self.filehandler.on_animation_selected)
        

class UpdateWindow(QWidget, Ui_update_window):
    def __init__(self, current_version, latest_version):
        super().__init__()
        self.setupUi(self)
        self.setWindowModality(Qt.ApplicationModal)

        self.update_ui_choice.clicked.connect(self.update_buttons)
        self.update_ui_info.setText(QCoreApplication.translate("update_window", u"An update is available\n" "Do you want to download it now?", None))
        self.update_ui_version.setText(QCoreApplication.translate("update_window", u"Latest Version: '{}'\n""Your Version: '{}'".format(latest_version, current_version), None))

    def update_buttons(self, button):
        if self.update_ui_choice.standardButton(button) == QDialogButtonBox.Yes:
            QDesktopServices.openUrl(QUrl("https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/releases/latest"))
            self.close()

        if self.update_ui_choice.standardButton(button) == QDialogButtonBox.No:
            self.close()