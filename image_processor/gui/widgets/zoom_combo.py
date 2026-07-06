#!/usr/bin/env python3
"""Editable zoom preset combo box."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap, QPolygon
from PySide6.QtWidgets import QComboBox, QStyle, QStyleOptionComboBox

from image_processor.utils.themes import DARK_TEXT_MUTED, is_dark_mode, zoom_combo_stylesheet

ZOOM_PRESETS = (25, 50, 75, 100, 200, 500)
MIN_ZOOM_PERCENT = 10.0
MAX_ZOOM_PERCENT = 500.0


def _down_arrow_icon(color: QColor, width: int = 10, height: int = 6) -> QIcon:
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawPolygon(
        QPolygon(
            [
                QPoint(0, 0),
                QPoint(width, 0),
                QPoint(width // 2, height),
            ]
        )
    )
    painter.end()
    return QIcon(pixmap)


class ZoomComboBox(QComboBox):
    """Combo box for canvas zoom with presets and free-form percent input."""

    zoom_changed = Signal(float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setMinimumWidth(72)
        self.setMaximumHeight(28)
        self.setToolTip("缩放比例")
        self._arrow_icon = _down_arrow_icon(QColor(DARK_TEXT_MUTED))
        self.apply_theme_styles()
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

    def apply_theme_styles(self) -> None:
        arrow_color = QColor(DARK_TEXT_MUTED if is_dark_mode() else "#6B7280")
        self._arrow_icon = _down_arrow_icon(arrow_color)
        self.setStyleSheet(zoom_combo_stylesheet())
        line_edit = self.lineEdit()
        if line_edit is not None:
            line_edit.setStyleSheet("background: transparent; border: none; padding: 0px; margin: 0px;")
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        arrow_rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_ComboBox,
            option,
            QStyle.SubControl.SC_ComboBoxArrow,
            self,
        )
        if not arrow_rect.isValid():
            arrow_rect = self.rect().adjusted(self.width() - 18, 0, 0, 0)
        painter = QPainter(self)
        self._arrow_icon.paint(painter, arrow_rect, Qt.AlignmentFlag.AlignCenter)
        painter.end()
