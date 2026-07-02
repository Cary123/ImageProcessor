#!/usr/bin/env python3
"""Non-blocking toast notification widget."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class Toast(QWidget):
    """A simple toast that auto-hides after a timeout."""

    def __init__(self, parent: QWidget, message: str, duration_ms: int = 3000) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            "background-color: #1F2937; color: white; border-radius: 6px; padding: 4px;"
        )
        self.setMinimumHeight(36)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 8, 4)
        layout.setSpacing(8)

        self.label = QLabel(message)
        self.label.setStyleSheet("color: white;")
        layout.addWidget(self.label)

        close_button = QPushButton("×")
        close_button.setFixedSize(20, 20)
        close_button.setStyleSheet(
            "background-color: transparent; color: white; border: none; font-weight: bold;"
        )
        close_button.clicked.connect(self.hide)
        layout.addWidget(close_button)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        self._timer.start(duration_ms)

    def show_at(self, x: int, y: int) -> None:
        self.adjustSize()
        self.move(x, y)
        self.show()
