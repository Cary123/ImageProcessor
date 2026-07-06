#!/usr/bin/env python3
"""Checkable tool icon button with inset selection border."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QPushButton

from image_processor.utils.themes import DARK_ACCENT, DARK_SELECTION_BG, is_dark_mode


class ToolIconButton(QPushButton):
    """Icon tool button that paints selection chrome inside its bounds."""

    BORDER = 2
    RADIUS = 5

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setProperty("toolButton", True)
        self.setCursor(Qt.ArrowCursor)
        self.setStyleSheet("background: transparent; border: none; padding: 0; margin: 0;")

    def set_tool_icon(self, icon, size: int) -> None:
        self.setIcon(icon)
        self.setIconSize(QSize(size, size))

    def paintEvent(self, event) -> None:
        if self.isChecked():
            inset = self.BORDER
            rect = self.rect().adjusted(inset, inset, -inset, -inset)
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            fill = QColor(DARK_SELECTION_BG if is_dark_mode() else "#DBEAFE")
            painter.setPen(Qt.NoPen)
            painter.setBrush(fill)
            painter.drawRoundedRect(rect, self.RADIUS, self.RADIUS)
            painter.setPen(QPen(QColor(DARK_ACCENT), self.BORDER))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, self.RADIUS, self.RADIUS)
            painter.end()
        super().paintEvent(event)
