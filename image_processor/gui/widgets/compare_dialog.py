#!/usr/bin/env python3
"""Before/after comparison dialog."""

from __future__ import annotations

import numpy as np
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)


class CompareDialog(QDialog):
    """Dialog showing before/after comparison side by side."""

    def __init__(self, before: Image.Image, after: Image.Image, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("原图 vs 处理后")
        self.setMinimumSize(900, 500)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Horizontal)

        before_label = QLabel("原图")
        before_label.setAlignment(Qt.AlignCenter)
        before_label.setStyleSheet("font-weight: bold;")
        before_pixmap = self._pil_to_pixmap(before)
        before_image = QLabel()
        before_image.setPixmap(before_pixmap)
        before_image.setAlignment(Qt.AlignCenter)
        before_widget = QWidget()
        before_layout = QVBoxLayout(before_widget)
        before_layout.addWidget(before_label)
        before_layout.addWidget(before_image, 1)
        splitter.addWidget(before_widget)

        after_label = QLabel("处理后")
        after_label.setAlignment(Qt.AlignCenter)
        after_label.setStyleSheet("font-weight: bold;")
        after_pixmap = self._pil_to_pixmap(after)
        after_image = QLabel()
        after_image.setPixmap(after_pixmap)
        after_image.setAlignment(Qt.AlignCenter)
        after_widget = QWidget()
        after_layout = QVBoxLayout(after_widget)
        after_layout.addWidget(after_label)
        after_layout.addWidget(after_image, 1)
        splitter.addWidget(after_widget)

        splitter.setSizes([450, 450])
        layout.addWidget(splitter, 1)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

    def _pil_to_pixmap(self, image: Image.Image) -> QPixmap:
        data = np.array(image.convert("RGBA"))
        height, width, _ = data.shape
        bytes_per_line = width * 4
        q_image = QImage(data.data, width, height, bytes_per_line, QImage.Format_RGBA8888)
        return QPixmap.fromImage(q_image)
