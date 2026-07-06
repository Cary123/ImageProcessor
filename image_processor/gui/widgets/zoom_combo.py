#!/usr/bin/env python3
"""Editable zoom preset combo box."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox

ZOOM_PRESETS = (25, 50, 75, 100, 200, 500)
MIN_ZOOM_PERCENT = 10.0
MAX_ZOOM_PERCENT = 500.0


class ZoomComboBox(QComboBox):
    """Combo box for canvas zoom with presets and free-form percent input."""

    zoom_changed = Signal(float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setMinimumWidth(88)
        self.setToolTip("缩放比例")
        for percent in ZOOM_PRESETS:
            self.addItem(f"{percent}%")
        self.setCurrentText("50%")
        self.activated.connect(self._apply_from_text)
        line_edit = self.lineEdit()
        if line_edit is not None:
            line_edit.editingFinished.connect(self._apply_from_text)

    @staticmethod
    def parse_percent(text: str) -> float | None:
        cleaned = text.strip().rstrip("%").strip()
        if not cleaned:
            return None
        try:
            value = float(cleaned)
        except ValueError:
            return None
        return max(MIN_ZOOM_PERCENT, min(MAX_ZOOM_PERCENT, value))

    def _apply_from_text(self, *_args) -> None:
        percent = self.parse_percent(self.currentText())
        if percent is None:
            return
        self.set_zoom_scale(percent / 100.0)

    def set_zoom_scale(self, scale: float, *, emit: bool = True) -> None:
        clamped = max(MIN_ZOOM_PERCENT / 100.0, min(MAX_ZOOM_PERCENT / 100.0, scale))
        display = f"{int(round(clamped * 100))}%"
        self.blockSignals(True)
        self.setCurrentText(display)
        self.blockSignals(False)
        if emit:
            self.zoom_changed.emit(clamped)
