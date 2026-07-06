#!/usr/bin/env python3
"""Directional edge shadow strips for elevated toolbars."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import QWidget

from image_processor.utils.themes import is_dark_mode

SHADOW_SIZE = 8


class EdgeShadow(QWidget):
    """Thin gradient strip that simulates a drop shadow on one edge."""

    BOTTOM = "bottom"
    RIGHT = "right"

    def __init__(self, direction: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._direction = direction
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAutoFillBackground(False)
        if direction == self.BOTTOM:
            self.setFixedHeight(SHADOW_SIZE)
        else:
            self.setFixedWidth(SHADOW_SIZE)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        start_alpha = 72 if is_dark_mode() else 48
        end_alpha = 0
        shadow_color = QColor(0, 0, 0)

        if self._direction == self.BOTTOM:
            gradient = QLinearGradient(0, 0, 0, self.height())
        else:
            gradient = QLinearGradient(0, 0, self.width(), 0)

        gradient.setColorAt(0.0, QColor(shadow_color.red(), shadow_color.green(), shadow_color.blue(), start_alpha))
        gradient.setColorAt(1.0, QColor(shadow_color.red(), shadow_color.green(), shadow_color.blue(), end_alpha))
        painter.fillRect(self.rect(), gradient)
