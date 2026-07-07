#!/usr/bin/env python3
"""Grid overlay settings panel."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class GridPanel(QWidget):
    """Panel for configuring the non-destructive grid overlay."""

    grid_changed = Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self._image_size = (0, 0)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("网格辅助线")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        hint = QLabel("仅在画布上显示辅助网格，不会修改图片内容。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray; font-size: 12px;")
        layout.addWidget(hint)

        form_layout = QFormLayout()
        form_layout.setSpacing(8)

        self.visible_check = QCheckBox("显示网格")
        self.visible_check.setChecked(False)
        form_layout.addRow("显示:", self.visible_check)

        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 64)
        self.rows_spin.setValue(4)
        form_layout.addRow("行数:", self.rows_spin)

        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 64)
        self.cols_spin.setValue(4)
        form_layout.addRow("列数:", self.cols_spin)

        layout.addLayout(form_layout)
        layout.addStretch()

        self.visible_check.stateChanged.connect(self._on_changed)
        self.rows_spin.valueChanged.connect(self._on_changed)
        self.cols_spin.valueChanged.connect(self._on_changed)

    def _on_changed(self) -> None:
        self.grid_changed.emit(self.current_options())

    def current_options(self) -> dict[str, Any]:
        return {
            "visible": self.visible_check.isChecked(),
            "rows": self.rows_spin.value(),
            "cols": self.cols_spin.value(),
        }

    def set_image_size(self, width: int, height: int) -> None:
        """Reserved for syncing grid bounds with the active image size."""
        self._image_size = (max(1, width), max(1, height))
