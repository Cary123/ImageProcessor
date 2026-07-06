#!/usr/bin/env python3
"""Vertical icon toolbar for tool selection."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from image_processor.gui.widgets.edge_shadow import EdgeShadow
from image_processor.gui.widgets.icons import get_svg_icon
from image_processor.gui.widgets.tool_button import ToolIconButton
from image_processor.utils.themes import DARK_BG_SECONDARY, is_dark_mode


class ToolBar(QWidget):
    """Toolbar that emits a selected tool identifier using generated icons."""

    tool_selected = Signal(str)

    def __init__(self) -> None:
        super().__init__()

        outer = QHBoxLayout(self)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 0)

        self._panel = QWidget()
        self._panel.setMaximumWidth(52)
        layout = QVBoxLayout(self._panel)
        layout.setSpacing(4)
        layout.setContentsMargins(6, 6, 4, 6)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)

        tools = [
            ("move", "移动"),
            ("crop", "裁剪"),
            ("matting", "抠图"),
            ("resize", "缩放"),
            ("inpaint", "擦除"),
            ("brush", "画笔"),
            ("eraser", "橡皮"),
            ("clone_stamp", "仿制图章"),
            ("grid", "网格"),
            ("adjust", "调色"),
        ]

        for tool_id, label in tools:
            button = ToolIconButton()
            button.setProperty("tool_id", tool_id)
            button.setFixedSize(36, 36)
            button.set_tool_icon(get_svg_icon(tool_id), 20)
            button.setToolTip(label)
            self.group.addButton(button)
            layout.addWidget(button)
            button.clicked.connect(lambda _checked, tid=tool_id: self.tool_selected.emit(tid))

        if self.group.buttons():
            self.group.buttons()[0].setChecked(True)

        layout.addStretch()

        outer.addWidget(self._panel)
        self._right_shadow = EdgeShadow(EdgeShadow.RIGHT)
        outer.addWidget(self._right_shadow)

    def set_tool_checked(self, tool_id: str | None) -> None:
        for button in self.group.buttons():
            if button.property("tool_id") == tool_id:
                button.setChecked(True)
                return
        for button in self.group.buttons():
            button.setChecked(False)

    def refresh_icons(self) -> None:
        if is_dark_mode():
            self._panel.setStyleSheet(f"background-color: {DARK_BG_SECONDARY};")
        else:
            self._panel.setStyleSheet("background-color: #F3F4F6;")
        self._right_shadow.update()
        for button in self.group.buttons():
            tool_id = button.property("tool_id")
            if tool_id:
                button.set_tool_icon(get_svg_icon(tool_id), 20)
