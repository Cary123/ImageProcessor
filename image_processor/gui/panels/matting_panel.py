#!/usr/bin/env python3
"""Background removal panel."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from image_processor.core.image_engine import AVAILABLE_MODELS, DEFAULT_MODEL


class MattingPanel(QWidget):
    """Panel for AI background removal options."""

    request_matting = Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("智能抠图")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        form_layout = QFormLayout()
        form_layout.setSpacing(8)

        self.model_combo = QComboBox()
        self.model_combo.addItems(AVAILABLE_MODELS)
        self.model_combo.setCurrentText(DEFAULT_MODEL)
        form_layout.addRow("模型:", self.model_combo)

        self.trim_check = QCheckBox("裁剪透明边缘")
        form_layout.addRow(self.trim_check)

        self.trim_padding_spin = QSpinBox()
        self.trim_padding_spin.setRange(0, 50)
        self.trim_padding_spin.setValue(0)
        self.trim_padding_spin.setSuffix(" px")
        form_layout.addRow("保留边距:", self.trim_padding_spin)

        self.alpha_matting_check = QCheckBox("启用 Alpha Matting")
        form_layout.addRow(self.alpha_matting_check)

        layout.addLayout(form_layout)
        layout.addStretch()

        self.run_button = QPushButton("开始抠图")
        self.run_button.setStyleSheet("background-color: #3B82F6; color: white; padding: 8px;")
        self.run_button.setMinimumHeight(40)
        layout.addWidget(self.run_button)

        self.run_button.clicked.connect(self._on_run)

    def _on_run(self) -> None:
        options: dict[str, Any] = {
            "model": self.model_combo.currentText(),
            "trim": self.trim_check.isChecked(),
            "trim_padding": self.trim_padding_spin.value(),
            "alpha_matting": self.alpha_matting_check.isChecked(),
        }
        self.request_matting.emit(options)
