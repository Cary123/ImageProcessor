#!/usr/bin/env python3
"""Sprite sheet generator panel."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from image_processor.utils.helpers import collect_images


class SpritePanel(QWidget):
    """Panel for configuring sprite sheet generation."""

    request_sprite = Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self._image_paths: list[Path] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("精灵图生成")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        form_layout = QFormLayout()
        form_layout.setSpacing(8)

        self.dir_edit = QLineEdit()
        self.dir_edit.setPlaceholderText("选择图片文件夹")
        self.dir_edit.setReadOnly(True)
        form_layout.addRow("文件夹:", self.dir_edit)

        self.browse_button = QPushButton("浏览...")
        self.browse_button.clicked.connect(self._browse_directory)
        layout.addWidget(self.browse_button)

        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(0, 100)
        self.cols_spin.setSpecialValueText("自动")
        self.cols_spin.setValue(0)
        form_layout.addRow("列数:", self.cols_spin)

        self.spacing_spin = QSpinBox()
        self.spacing_spin.setRange(0, 100)
        self.spacing_spin.setValue(0)
        self.spacing_spin.setSuffix(" px")
        form_layout.addRow("间距:", self.spacing_spin)

        self.padding_spin = QSpinBox()
        self.padding_spin.setRange(0, 100)
        self.padding_spin.setValue(0)
        self.padding_spin.setSuffix(" px")
        form_layout.addRow("内边距:", self.padding_spin)

        layout.addLayout(form_layout)
        layout.addStretch()

        self.generate_button = QPushButton("生成精灵图")
        self.generate_button.setStyleSheet("background-color: #3B82F6; color: white; padding: 8px;")
        self.generate_button.setMinimumHeight(40)
        layout.addWidget(self.generate_button)

        self.generate_button.clicked.connect(self._on_generate)

    def set_images(self, paths: list[Path]) -> None:
        self._image_paths = paths
        self.dir_edit.setText(f"已加载 {len(paths)} 张图片")

    def _browse_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
        if directory:
            self._image_paths = collect_images(Path(directory))
            self.dir_edit.setText(f"{directory} ({len(self._image_paths)} 张)")

    def _on_generate(self) -> None:
        if not self._image_paths:
            self._browse_directory()
            if not self._image_paths:
                return

        output_path, _ = QFileDialog.getSaveFileName(
            self, "保存精灵图", "sprite.png", "PNG (*.png)"
        )
        if not output_path:
            return

        json_path = str(Path(output_path).with_suffix(".json"))
        options: dict[str, Any] = {
            "paths": [str(p) for p in self._image_paths],
            "cols": self.cols_spin.value() or None,
            "spacing": self.spacing_spin.value(),
            "padding": self.padding_spin.value(),
            "output_path": output_path,
            "json_path": json_path,
        }
        self.request_sprite.emit(options)
