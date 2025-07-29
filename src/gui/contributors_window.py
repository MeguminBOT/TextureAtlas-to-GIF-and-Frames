#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import webbrowser
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QWidget,
    QPushButton,
    QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class ContributorsWindow(QDialog):
    """
    This class provides a dedicated window to thank contributors to the project
    and allows users to visit their social media profiles or GitHub pages.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Contributors"))
        self.setGeometry(200, 200, 600, 500)
        self.setup_ui()

    def tr(self, text):
        """Translation helper method."""
        from PySide6.QtCore import QCoreApplication

        return QCoreApplication.translate(self.__class__.__name__, text)

    def setup_ui(self):
        """Sets up the UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel(self.tr("TextureAtlas Toolbox\nContributors"))
        title_font = QFont("Arial", 16, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Scrollable area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)

        # Add contributors
        self.add_contributors(content_layout)

        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

        # Close button
        close_btn = QPushButton(self.tr("Close"))
        close_btn.clicked.connect(self.close)
        close_btn.setMaximumWidth(100)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def add_contributors(self, layout):
        """Add contributor information to the layout."""
        contributors_data = [
            {
                "name": "AutisticLulu",
                "role": "Project starter",
                "links": [
                    ("GitHub", "https://github.com/MeguminBOT"),
                    (
                        "Project Repository",
                        "https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames",
                    ),
                ],
            },
            {
                "name": "Jsfasdf250",
                "role": "Major contributor",
                "links": [
                    ("GitHub", "https://github.com/Jsfasdf250"),
                ],
            },
            {
                "name": "Julnz",
                "role": "App icon",
                "links": [
                    ("Website", "https://julnz.com"),
                ],
            },
        ]

        for contributor in contributors_data:
            self.add_contributor_card(layout, contributor)

    def add_contributor_card(self, layout, contributor_data):
        """Add a contributor card to the layout."""
        # Create frame for contributor
        card_frame = QFrame()
        card_frame.setFrameStyle(QFrame.Shape.Box)
        card_frame.setLineWidth(1)
        card_layout = QVBoxLayout(card_frame)
        card_layout.setSpacing(10)
        card_layout.setContentsMargins(15, 15, 15, 15)

        # Name
        name_label = QLabel(contributor_data["name"])
        name_font = QFont("Arial", 12, QFont.Weight.Bold)
        name_label.setFont(name_font)
        card_layout.addWidget(name_label)

        # Role
        if "role" in contributor_data:
            role_label = QLabel(contributor_data["role"])
            role_label.setStyleSheet("color: #666666;")
            card_layout.addWidget(role_label)

        # Description (if any)
        if "description" in contributor_data:
            desc_label = QLabel(contributor_data["description"])
            desc_label.setWordWrap(True)
            card_layout.addWidget(desc_label)

        # Links
        if "links" in contributor_data:
            links_layout = QHBoxLayout()
            for link_text, link_url in contributor_data["links"]:
                link_btn = QPushButton(link_text)
                link_btn.clicked.connect(lambda checked, url=link_url: self.open_link(url))
                link_btn.setMaximumWidth(150)
                links_layout.addWidget(link_btn)
            links_layout.addStretch()
            card_layout.addLayout(links_layout)

        layout.addWidget(card_frame)

    def open_link(self, url):
        """Opens a URL in the default web browser."""
        webbrowser.open(url)

    @staticmethod
    def show_contributors(parent=None):
        """Static method to show the contributors window."""
        window = ContributorsWindow(parent)
        window.exec()
