#!/usr/bin/env python3
"""Brush tool settings panel with multiple brush styles."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from image_processor.gui.brush_modes import BRUSH_STYLES, style_hint, uses_hardness, uses_opacity
from image_processor.utils.themes import gallery_hint_stylesheet


class BrushPanel(QWidget):
    """Dedicated panel for the paint brush tool."""

    brush_style_changed = Signal(str)
    brush_size_changed = Signal(int)
    brush_hardness_changed = Signal(int)
    brush_opacity_changed = Signal(int)
    apply_brush = Signal()
    cancel_brush = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("画笔")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        self.hint_label = QLabel(
            "在画布上涂抹以绘制前景色。完成后点击「应用」保留修改，或「取消」恢复原图。"
        )
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet(gallery_hint_stylesheet())
        layout.addWidget(self.hint_label)

        form_layout = QFormLayout()
        form_layout.setSpacing(8)

        self.style_combo = QComboBox()
        for style_id, label in BRUSH_STYLES.items():
            self.style_combo.addItem(label, style_id)
        self.style_combo.currentIndexChanged.connect(self._on_style_changed)
        form_layout.addRow("笔刷类型:", self.style_combo)

        self.style_hint_label = QLabel(style_hint("round"))
        self.style_hint_label.setWordWrap(True)
        self.style_hint_label.setStyleSheet(gallery_hint_stylesheet())
        form_layout.addRow(self.style_hint_label)

        layout.addLayout(form_layout)

        size_label = QLabel("笔刷大小")
        layout.addWidget(size_label)
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(1, 100)
        self.size_slider.setValue(20)
        self.size_slider.valueChanged.connect(self._on_size_changed)
        layout.addWidget(self.size_slider)

        self.hardness_label = QLabel("硬度")
        layout.addWidget(self.hardness_label)
        self.hardness_slider = QSlider(Qt.Horizontal)
        self.hardness_slider.setRange(0, 100)
        self.hardness_slider.setValue(100)
        self.hardness_slider.valueChanged.connect(self._on_hardness_changed)
        layout.addWidget(self.hardness_slider)

        self.opacity_label = QLabel("浓度")
        layout.addWidget(self.opacity_label)
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(5, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        layout.addWidget(self.opacity_slider)

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
        self._refresh_style_controls()

    def _current_style_id(self) -> str:
        return self.style_combo.currentData() or "round"

    def _on_style_changed(self) -> None:
        style_id = self._current_style_id()
        self.style_hint_label.setText(style_hint(style_id))
        self._refresh_style_controls()
        self.brush_style_changed.emit(style_id)

    def _refresh_style_controls(self) -> None:
        style_id = self._current_style_id()
        show_hardness = uses_hardness(style_id)
        show_opacity = uses_opacity(style_id)
        self.hardness_label.setVisible(show_hardness)
        self.hardness_slider.setVisible(show_hardness)
        self.opacity_label.setVisible(show_opacity)
        self.opacity_slider.setVisible(show_opacity)

    def _on_size_changed(self) -> None:
        self.brush_size_changed.emit(self.size_slider.value())

    def _on_hardness_changed(self) -> None:
        self.brush_hardness_changed.emit(self.hardness_slider.value())

    def _on_opacity_changed(self) -> None:
        self.brush_opacity_changed.emit(self.opacity_slider.value())

    def current_options(self) -> dict[str, Any]:
        return {
            "style": self._current_style_id(),
            "size": self.size_slider.value(),
            "hardness": self.hardness_slider.value(),
            "opacity": self.opacity_slider.value(),
        }

    def apply_theme_styles(self) -> None:
        self.hint_label.setStyleSheet(gallery_hint_stylesheet())
        self.style_hint_label.setStyleSheet(gallery_hint_stylesheet())
