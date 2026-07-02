#!/usr/bin/env python3
"""Resize panel."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from image_processor.core.image_engine import InterpolationMode


class ResizePanel(QWidget):
    """Panel for image scaling and export options."""

    request_resize = Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("缩放与导出")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        form_layout = QFormLayout()
        form_layout.setSpacing(8)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 10000)
        self.width_spin.setSpecialValueText("自动")
        self.width_spin.setValue(0)
        self.width_spin.setSuffix(" px")
        form_layout.addRow("宽度:", self.width_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 10000)
        self.height_spin.setSpecialValueText("自动")
        self.height_spin.setValue(0)
        self.height_spin.setSuffix(" px")
        form_layout.addRow("高度:", self.height_spin)

        self.percentage_spin = QSpinBox()
        self.percentage_spin.setRange(1, 500)
        self.percentage_spin.setValue(100)
        self.percentage_spin.setSuffix(" %")
        form_layout.addRow("百分比:", self.percentage_spin)

        self.interpolation_combo = QComboBox()
        self.interpolation_combo.addItems([mode.value for mode in InterpolationMode])
        self.interpolation_combo.setCurrentText(InterpolationMode.LANCZOS.value)
        form_layout.addRow("插值:", self.interpolation_combo)

        layout.addLayout(form_layout)
        layout.addStretch()

        self.run_button = QPushButton("应用缩放")
        self.run_button.setStyleSheet("background-color: #3B82F6; color: white; padding: 8px;")
        self.run_button.setMinimumHeight(40)
        layout.addWidget(self.run_button)

        self.run_button.clicked.connect(self._on_run)

    def _on_run(self) -> None:
        width = self.width_spin.value() if self.width_spin.value() > 0 else None
        height = self.height_spin.value() if self.height_spin.value() > 0 else None
        percentage = self.percentage_spin.value() if self.percentage_spin.value() != 100 else None
        options: dict[str, Any] = {
            "width": width,
            "height": height,
            "percentage": percentage,
            "interpolation": self.interpolation_combo.currentText(),
        }
        self.request_resize.emit(options)
