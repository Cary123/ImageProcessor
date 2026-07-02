#!/usr/bin/env python3
"""Vertical toolbar for tool selection."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QPushButton, QVBoxLayout, QWidget


class ToolBar(QWidget):
    """Toolbar that emits a selected tool identifier."""

    tool_selected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setMaximumWidth(80)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)

        tools = [
            ("matting", "抠图"),
            ("resize", "缩放"),
            ("crop", "裁剪"),
            ("inpaint", "擦除"),
            ("brush", "画笔"),
            ("sprite", "精灵图"),
            ("adjust", "调色"),
        ]

        for tool_id, label in tools:
            button = QPushButton(label)
            button.setCheckable(True)
            button.setProperty("tool_id", tool_id)
            button.setMinimumHeight(48)
            self.group.addButton(button)
            layout.addWidget(button)
            button.clicked.connect(lambda _checked, tid=tool_id: self.tool_selected.emit(tid))

        if self.group.buttons():
            self.group.buttons()[0].setChecked(True)

        layout.addStretch()

        self.group.buttonClicked.connect(self._on_button_clicked)

    def _on_button_clicked(self, button: QPushButton) -> None:
        tool_id = button.property("tool_id")
        if tool_id:
            self.tool_selected.emit(tool_id)
