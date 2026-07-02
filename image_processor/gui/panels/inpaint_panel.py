#!/usr/bin/env python3
"""Content-aware inpainting panel."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class InpaintPanel(QWidget):
    """Panel for content-aware inpainting using a mask image."""

    request_inpaint = Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self._mask_path: Path | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("内容感知擦除")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        hint = QLabel("使用外部工具绘制白色遮罩，白色区域将被智能擦除。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray; font-size: 12px;")
        layout.addWidget(hint)

        mask_layout = QHBoxLayout()
        self.mask_edit = QLineEdit()
        self.mask_edit.setPlaceholderText("选择遮罩图片")
        self.mask_edit.setReadOnly(True)
        mask_layout.addWidget(self.mask_edit)
        self.mask_button = QPushButton("浏览...")
        self.mask_button.clicked.connect(self._browse_mask)
        mask_layout.addWidget(self.mask_button)
        layout.addLayout(mask_layout)

        form_layout = QFormLayout()
        form_layout.setSpacing(8)

        self.method_combo = QComboBox()
        self.method_combo.addItems(["NS", "TELEA"])
        self.method_combo.setCurrentText("NS")
        form_layout.addRow("算法:", self.method_combo)

        self.radius_spin = QSpinBox()
        self.radius_spin.setRange(1, 50)
        self.radius_spin.setValue(5)
        form_layout.addRow("半径:", self.radius_spin)

        layout.addLayout(form_layout)
        layout.addStretch()

        self.run_button = QPushButton("开始擦除")
        self.run_button.setStyleSheet("background-color: #3B82F6; color: white; padding: 8px;")
        self.run_button.setMinimumHeight(40)
        layout.addWidget(self.run_button)

        self.run_button.clicked.connect(self._on_run)

    def _browse_mask(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择遮罩图片", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self._mask_path = Path(path)
            self.mask_edit.setText(path)

    def _on_run(self) -> None:
        if self._mask_path is None:
            self._browse_mask()
            if self._mask_path is None:
                return

        options: dict[str, Any] = {
            "mask_path": str(self._mask_path),
            "method": self.method_combo.currentText(),
            "radius": self.radius_spin.value(),
        }
        self.request_inpaint.emit(options)
