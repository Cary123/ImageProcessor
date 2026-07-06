#!/usr/bin/env python3
"""Foreground / background color selector with swatches."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QButtonGroup, QColorDialog, QFrame, QHBoxLayout, QPushButton, QWidget

from image_processor.gui.widgets.icons import get_svg_icon
from image_processor.gui.widgets.tool_button import ToolIconButton
from image_processor.gui.widgets.zoom_combo import ZoomComboBox
from image_processor.utils.themes import (
    DARK_BG_ELEVATED,
    DARK_BORDER_SUBTLE,
    color_bar_divider_stylesheet,
    color_button_border,
    color_swatch_border,
    is_dark_mode,
)


DEFAULT_SWATCHES = [
    "#000000",
    "#FFFFFF",
    "#EF4444",
    "#F97316",
    "#F59E0B",
    "#84CC16",
    "#10B981",
    "#06B6D4",
    "#3B82F6",
    "#6366F1",
    "#8B5CF6",
    "#D946EF",
    "#F43F5E",
    "#9CA3AF",
]


class _ColorButton(QPushButton):
    """Square button showing the current color and its selection state."""

    def __init__(self, label: str, color: QColor, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(40, 40)
        self.setToolTip(label)
        self._color = color
        self._selected = False
        self._update_style()

    @property
    def color(self) -> QColor:
        return self._color

    def set_color(self, color: QColor) -> None:
        self._color = color
        self._update_style()

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._update_style()

    def _update_style(self) -> None:
        border_color = color_button_border(self._selected)
        self.setStyleSheet(
            f"background-color: {self._color.name()}; border: 3px solid {border_color}; border-radius: 4px;"
        )


class ColorBar(QWidget):
    """Top bar for foreground/background colors and swatches."""

    foreground_changed = Signal(QColor)
    background_changed = Signal(QColor)
    tool_selected = Signal(str)
    zoom_changed = Signal(float)

    def __init__(self) -> None:
        super().__init__()
        self._active_role = "foreground"
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 10, 8, 10)
        self.setMinimumHeight(60)

        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        top_tools = [
            ("rect_select", "矩形选择"),
            ("free_select", "自由选择"),
            ("eyedropper", "吸管"),
            ("paint_bucket", "油漆桶"),
        ]
        for tool_id, tooltip in top_tools:
            button = ToolIconButton()
            button.setProperty("tool_id", tool_id)
            button.setFixedSize(44, 44)
            button.set_tool_icon(get_svg_icon(tool_id, size=28), 28)
            button.setToolTip(tooltip)
            self.tool_group.addButton(button)
            layout.addWidget(button)
            button.clicked.connect(lambda _checked, tid=tool_id: self.tool_selected.emit(tid))

        self.zoom_combo = ZoomComboBox()
        self.zoom_combo.zoom_changed.connect(self.zoom_changed.emit)
        layout.addWidget(self.zoom_combo)

        divider = QFrame()
        divider.setFrameShape(QFrame.VLine)
        divider.setFixedSize(2, 44)
        divider.setStyleSheet(color_bar_divider_stylesheet())
        self.divider = divider
        layout.addWidget(divider)

        self.foreground_button = _ColorButton("前景色", QColor("#000000"))
        self.background_button = _ColorButton("背景色", QColor("#FFFFFF"))
        self.foreground_button.clicked.connect(self._select_foreground)
        self.background_button.clicked.connect(self._select_background)
        self.foreground_button.set_selected(True)

        layout.addWidget(self.foreground_button)
        layout.addWidget(self.background_button)

        layout.addSpacing(8)

        self._swatches: list[QPushButton] = []
        for hex_color in DEFAULT_SWATCHES:
            swatch = QPushButton()
            swatch.setFixedSize(22, 22)
            swatch.setStyleSheet(
                f"background-color: {hex_color}; border: 1px solid {color_swatch_border()}; border-radius: 3px;"
            )
            swatch.setToolTip(hex_color)
            swatch.clicked.connect(lambda _checked, c=hex_color: self._set_active_color_hex(c))
            self._swatches.append(swatch)
            layout.addWidget(swatch)

        palette_button = QPushButton()
        palette_button.setFixedSize(22, 22)
        palette_button.setIcon(get_svg_icon("palette", size=18))
        palette_button.setToolTip("调色盘")
        palette_button.setStyleSheet("border: none; background-color: transparent;")
        palette_button.clicked.connect(self._pick_active_color)
        self.palette_button = palette_button
        layout.addWidget(palette_button)

        layout.addStretch()

    def _select_foreground(self) -> None:
        self._active_role = "foreground"
        self.foreground_button.set_selected(True)
        self.background_button.set_selected(False)

    def _select_background(self) -> None:
        self._active_role = "background"
        self.foreground_button.set_selected(False)
        self.background_button.set_selected(True)

    def _pick_active_color(self) -> None:
        if self._active_role == "foreground":
            dialog = QColorDialog(self.foreground_button.color, self)
            if dialog.exec():
                color = dialog.selectedColor()
                self.foreground_button.set_color(color)
                self.foreground_changed.emit(color)
        else:
            dialog = QColorDialog(self.background_button.color, self)
            if dialog.exec():
                color = dialog.selectedColor()
                self.background_button.set_color(color)
                self.background_changed.emit(color)

    def _set_active_color_hex(self, hex_color: str) -> None:
        color = QColor(hex_color)
        if self._active_role == "foreground":
            self.foreground_button.set_color(color)
            self.foreground_changed.emit(color)
        else:
            self.background_button.set_color(color)
            self.background_changed.emit(color)

    def foreground_color(self) -> QColor:
        return self.foreground_button.color

    def background_color(self) -> QColor:
        return self.background_button.color

    def set_foreground_color(self, color: QColor) -> None:
        self.foreground_button.set_color(color)
        self.foreground_changed.emit(color)

    def set_background_color(self, color: QColor) -> None:
        self.background_button.set_color(color)
        self.background_changed.emit(color)

    def active_role(self) -> str:
        return self._active_role

    def set_active_color(self, color: QColor) -> None:
        if self._active_role == "foreground":
            self.foreground_button.set_color(color)
            self.foreground_changed.emit(color)
        else:
            self.background_button.set_color(color)
            self.background_changed.emit(color)

    def set_zoom_scale(self, scale: float) -> None:
        self.zoom_combo.set_zoom_scale(scale, emit=False)

    def set_tool_checked(self, tool_id: str | None) -> None:
        for button in self.tool_group.buttons():
            if button.property("tool_id") == tool_id:
                button.setChecked(True)
                return
        for button in self.tool_group.buttons():
            button.setChecked(False)

    def refresh_theme(self) -> None:
        """Refresh icons and theme-dependent styles."""
        if is_dark_mode():
            self.setStyleSheet(
                f"background-color: {DARK_BG_ELEVATED}; "
                f"border-bottom: 1px solid {DARK_BORDER_SUBTLE};"
            )
        else:
            self.setStyleSheet("background-color: #FFFFFF; border-bottom: 1px solid #E5E7EB;")
        for button in self.tool_group.buttons():
            tool_id = button.property("tool_id")
            if tool_id:
                button.set_tool_icon(get_svg_icon(tool_id, size=28), 28)
        self.palette_button.setIcon(get_svg_icon("palette", size=18))
        self.divider.setStyleSheet(color_bar_divider_stylesheet())
        self.foreground_button._update_style()
        self.background_button._update_style()
        swatch_border = color_swatch_border()
        for swatch, hex_color in zip(self._swatches, DEFAULT_SWATCHES):
            swatch.setStyleSheet(
                f"background-color: {hex_color}; border: 1px solid {swatch_border}; border-radius: 3px;"
            )
