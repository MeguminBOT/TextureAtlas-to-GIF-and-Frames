# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'update_interface.ui'
##
## Created by: Qt User Interface Compiler version 6.7.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialogButtonBox, QFrame,
    QLabel, QSizePolicy, QWidget)

class Ui_update_window(object):
    def setupUi(self, update_window):
        if not update_window.objectName():
            update_window.setObjectName(u"update_window")
        update_window.resize(401, 127)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(update_window.sizePolicy().hasHeightForWidth())
        update_window.setSizePolicy(sizePolicy)
        update_window.setMinimumSize(QSize(401, 127))
        update_window.setMaximumSize(QSize(401, 127))
        update_window.setBaseSize(QSize(401, 127))
        font = QFont()
        font.setFamilies([u"Roboto"])
        update_window.setFont(font)
        update_window.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        update_window.setAutoFillBackground(False)
        update_window.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
        self.update_ui_info = QLabel(update_window)
        self.update_ui_info.setObjectName(u"update_ui_info")
        self.update_ui_info.setGeometry(QRect(0, 10, 399, 36))
        font1 = QFont()
        font1.setFamilies([u"Roboto"])
        font1.setPointSize(11)
        self.update_ui_info.setFont(font1)
        self.update_ui_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_ui_info.setOpenExternalLinks(False)
        self.update_ui_version = QLabel(update_window)
        self.update_ui_version.setObjectName(u"update_ui_version")
        self.update_ui_version.setGeometry(QRect(0, 54, 399, 28))
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.update_ui_version.sizePolicy().hasHeightForWidth())
        self.update_ui_version.setSizePolicy(sizePolicy1)
        font2 = QFont()
        font2.setFamilies([u"Roboto"])
        font2.setPointSize(9)
        self.update_ui_version.setFont(font2)
        self.update_ui_version.setFrameShape(QFrame.Shape.NoFrame)
        self.update_ui_version.setTextFormat(Qt.TextFormat.AutoText)
        self.update_ui_version.setScaledContents(False)
        self.update_ui_version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_ui_choice = QDialogButtonBox(update_window)
        self.update_ui_choice.setObjectName(u"update_ui_choice")
        self.update_ui_choice.setGeometry(QRect(0, 90, 399, 29))
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.update_ui_choice.sizePolicy().hasHeightForWidth())
        self.update_ui_choice.setSizePolicy(sizePolicy2)
        self.update_ui_choice.setOrientation(Qt.Orientation.Horizontal)
        self.update_ui_choice.setStandardButtons(QDialogButtonBox.StandardButton.No|QDialogButtonBox.StandardButton.Yes)
        self.update_ui_choice.setCenterButtons(True)

        self.retranslateUi(update_window)

        QMetaObject.connectSlotsByName(update_window)
    # setupUi

    def retranslateUi(self, update_window):
        update_window.setWindowTitle(QCoreApplication.translate("update_window", u"TextureAtlas to GIF and Frames", None))
        self.update_ui_info.setText(QCoreApplication.translate("update_window", u"An update is available\n"
"Do you want to download it now?", None))
        self.update_ui_version.setText(QCoreApplication.translate("update_window", u"Latest Version: 'latest'\n"
"Your Version: 'current'", None))
    # retranslateUi

