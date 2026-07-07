#!/usr/bin/env python3
"""Crop and rotate panel."""

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


class CropPanel(QWidget):
    """Panel for crop, rotate and flip operations."""

    request_crop = Signal(dict)
    request_rotate = Signal(dict)
    request_flip = Signal(dict)
    crop_values_changed = Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("裁剪与旋转")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        crop_group = QLabel("裁剪区域")
        layout.addWidget(crop_group)

        crop_form = QFormLayout()
        crop_form.setSpacing(8)

        self.left_spin = QSpinBox()
        self.left_spin.setRange(0, 99999)
        self.left_spin.setSuffix(" px")
        crop_form.addRow("Left:", self.left_spin)

        self.top_spin = QSpinBox()
        self.top_spin.setRange(0, 99999)
        self.top_spin.setSuffix(" px")
        crop_form.addRow("Top:", self.top_spin)

        self.right_spin = QSpinBox()
        self.right_spin.setRange(0, 99999)
        self.right_spin.setSuffix(" px")
        crop_form.addRow("Right:", self.right_spin)

        self.bottom_spin = QSpinBox()
        self.bottom_spin.setRange(0, 99999)
        self.bottom_spin.setSuffix(" px")
        crop_form.addRow("Bottom:", self.bottom_spin)

        self.aspect_combo = QComboBox()
        self.aspect_combo.addItems(["自由", "1:1", "16:9", "4:3", "3:2"])
        self.aspect_combo.currentIndexChanged.connect(self._on_aspect_changed)
        crop_form.addRow("比例:", self.aspect_combo)

        for spin in (self.left_spin, self.top_spin, self.right_spin, self.bottom_spin):
            spin.valueChanged.connect(self._on_values_changed)

        layout.addLayout(crop_form)

        self.crop_button = QPushButton("应用裁剪")
        self.crop_button.setStyleSheet("background-color: #3B82F6; color: white; padding: 6px;")
        layout.addWidget(self.crop_button)
        self.crop_button.clicked.connect(self._on_crop)

        layout.addSpacing(16)
        rotate_label = QLabel("旋转")
        layout.addWidget(rotate_label)

        rotate_layout = QHBoxLayout()
        self.rotate_left_button = QPushButton("左转 90°")
        self.rotate_right_button = QPushButton("右转 90°")
        self.rotate_180_button = QPushButton("180°")
        rotate_layout.addWidget(self.rotate_left_button)
        rotate_layout.addWidget(self.rotate_right_button)
        rotate_layout.addWidget(self.rotate_180_button)
        layout.addLayout(rotate_layout)

        self.rotate_left_button.clicked.connect(lambda: self.request_rotate.emit({"angle": 90}))
        self.rotate_right_button.clicked.connect(lambda: self.request_rotate.emit({"angle": -90}))
        self.rotate_180_button.clicked.connect(lambda: self.request_rotate.emit({"angle": 180}))

        flip_layout = QHBoxLayout()
        self.flip_h_button = QPushButton("水平翻转")
        self.flip_v_button = QPushButton("垂直翻转")
        flip_layout.addWidget(self.flip_h_button)
        flip_layout.addWidget(self.flip_v_button)
        layout.addLayout(flip_layout)

        self.flip_h_button.clicked.connect(lambda: self.request_flip.emit({"horizontal": True, "vertical": False}))
        self.flip_v_button.clicked.connect(lambda: self.request_flip.emit({"horizontal": False, "vertical": True}))

        layout.addStretch()

    def set_image_size(self, width: int, height: int) -> None:
        self.left_spin.setRange(0, width)
        self.top_spin.setRange(0, height)
        self.right_spin.setRange(0, width)
        self.bottom_spin.setRange(0, height)
        self.right_spin.setValue(width)
        self.bottom_spin.setValue(height)

    def _on_values_changed(self) -> None:
        self.crop_values_changed.emit({
            "box": (
                self.left_spin.value(),
                self.top_spin.value(),
                self.right_spin.value(),
                self.bottom_spin.value(),
            ),
        })

    def _on_aspect_changed(self, index: int) -> None:
        width = self.right_spin.value() - self.left_spin.value()
        height = self.bottom_spin.value() - self.top_spin.value()
        if width <= 0 or height <= 0:
            return

        ratios = {
            0: None,
            1: 1.0,
            2: 16 / 9,
            3: 4 / 3,
            4: 3 / 2,
        }
        ratio = ratios.get(index)
        if ratio is None:
            return

        width = self.right_spin.value() - self.left_spin.value()
        height = self.bottom_spin.value() - self.top_spin.value()
        if width / height > ratio:
            new_height = int(width / ratio)
            self.bottom_spin.setValue(min(self.top_spin.value() + new_height, self.bottom_spin.maximum()))
        else:
            new_width = int(height * ratio)
            self.right_spin.setValue(min(self.left_spin.value() + new_width, self.right_spin.maximum()))

    def _on_crop(self) -> None:
        options: dict[str, Any] = {
            "box": (
                self.left_spin.value(),
                self.top_spin.value(),
                self.right_spin.value(),
                self.bottom_spin.value(),
            ),
        }
        self.request_crop.emit(options)
