#!/usr/bin/env python3
"""Color adjustment panel."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class AdjustPanel(QWidget):
    """Panel for brightness, contrast, saturation and filters."""

    adjustment_preview = Signal(dict)
    adjustment_applied = Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("色彩调整")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        form_layout = QFormLayout()
        form_layout.setSpacing(8)

        self.brightness_slider = self._create_slider()
        form_layout.addRow("亮度:", self.brightness_slider)

        self.contrast_slider = self._create_slider()
        form_layout.addRow("对比度:", self.contrast_slider)

        self.saturation_slider = self._create_slider()
        form_layout.addRow("饱和度:", self.saturation_slider)

        self.grayscale_check = QCheckBox("黑白")
        form_layout.addRow(self.grayscale_check)

        self.invert_check = QCheckBox("反色")
        form_layout.addRow(self.invert_check)

        layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        self.apply_button = QPushButton("应用")
        self.apply_button.setStyleSheet("background-color: #3B82F6; color: white; padding: 6px;")
        self.reset_button = QPushButton("重置")
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.reset_button)
        layout.addLayout(button_layout)
        layout.addStretch()

        self.brightness_slider.valueChanged.connect(self._on_preview)
        self.contrast_slider.valueChanged.connect(self._on_preview)
        self.saturation_slider.valueChanged.connect(self._on_preview)
        self.grayscale_check.stateChanged.connect(self._on_preview)
        self.invert_check.stateChanged.connect(self._on_preview)

        self.apply_button.clicked.connect(self._on_apply)
        self.reset_button.clicked.connect(self._on_reset)

    def _create_slider(self) -> QSlider:
        slider = QSlider(Qt.Horizontal)
        slider.setRange(-100, 100)
        slider.setValue(0)
        slider.setTickInterval(10)
        slider.setTickPosition(QSlider.TicksBelow)
        return slider

    def _options(self) -> dict[str, Any]:
        return {
            "brightness": self.brightness_slider.value(),
            "contrast": self.contrast_slider.value(),
            "saturation": self.saturation_slider.value(),
            "grayscale": self.grayscale_check.isChecked(),
            "invert": self.invert_check.isChecked(),
        }

    def _on_preview(self) -> None:
        self.adjustment_preview.emit(self._options())

    def _on_apply(self) -> None:
        self.adjustment_applied.emit(self._options())

    def _on_reset(self) -> None:
        self.brightness_slider.setValue(0)
        self.contrast_slider.setValue(0)
        self.saturation_slider.setValue(0)
        self.grayscale_check.setChecked(False)
        self.invert_check.setChecked(False)
        self._on_preview()
