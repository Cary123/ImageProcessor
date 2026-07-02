#!/usr/bin/env python3
"""Brush and eraser settings panel."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class BrushPanel(QWidget):
    """Panel for configuring brush/eraser tool."""

    brush_size_changed = Signal(int)
    brush_hardness_changed = Signal(int)
    brush_mode_changed = Signal(str)
    apply_brush = Signal()
    cancel_brush = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("橡皮擦 / 画笔")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        hint = QLabel("在画布上涂抹以擦除或恢复区域。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray; font-size: 12px;")
        layout.addWidget(hint)

        mode_layout = QHBoxLayout()
        self.mode_group = QButtonGroup(self)
        self.eraser_radio = QRadioButton("橡皮擦")
        self.brush_radio = QRadioButton("画笔")
        self.eraser_radio.setChecked(True)
        self.mode_group.addButton(self.eraser_radio)
        self.mode_group.addButton(self.brush_radio)
        mode_layout.addWidget(self.eraser_radio)
        mode_layout.addWidget(self.brush_radio)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        self.mode_group.buttonClicked.connect(self._on_mode_changed)

        size_label = QLabel("笔刷大小")
        layout.addWidget(size_label)
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(1, 100)
        self.size_slider.setValue(20)
        self.size_slider.valueChanged.connect(self._on_size_changed)
        layout.addWidget(self.size_slider)

        hardness_label = QLabel("硬度")
        layout.addWidget(hardness_label)
        self.hardness_slider = QSlider(Qt.Horizontal)
        self.hardness_slider.setRange(0, 100)
        self.hardness_slider.setValue(100)
        self.hardness_slider.valueChanged.connect(self._on_hardness_changed)
        layout.addWidget(self.hardness_slider)

        layout.addStretch()

        button_layout = QHBoxLayout()
        self.apply_button = QPushButton("应用")
        self.apply_button.setStyleSheet("background-color: #3B82F6; color: white; padding: 6px;")
        self.cancel_button = QPushButton("取消")
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.apply_button.clicked.connect(self.apply_brush)
        self.cancel_button.clicked.connect(self.cancel_brush)

    def _on_mode_changed(self) -> None:
        mode = "brush" if self.brush_radio.isChecked() else "eraser"
        self.brush_mode_changed.emit(mode)

    def _on_size_changed(self) -> None:
        self.brush_size_changed.emit(self.size_slider.value())

    def _on_hardness_changed(self) -> None:
        self.brush_hardness_changed.emit(self.hardness_slider.value())

    def current_mode(self) -> str:
        return "brush" if self.brush_radio.isChecked() else "eraser"

    def current_options(self) -> dict[str, Any]:
        return {
            "mode": self.current_mode(),
            "size": self.size_slider.value(),
            "hardness": self.hardness_slider.value(),
        }
