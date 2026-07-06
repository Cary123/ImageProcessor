#!/usr/bin/env python3
"""Thumbnail gallery for the image editor bottom strip."""

from __future__ import annotations

from typing import Any

import numpy as np
from PIL import Image
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QWidget

from image_processor.utils.themes import gallery_placeholder_stylesheet, image_gallery_stylesheet

THUMB_SIZE = 64
ITEM_BORDER = 2
ITEM_MARGIN = 4
CELL_SIZE = THUMB_SIZE + 2 * ITEM_BORDER + 2 * ITEM_MARGIN
LIST_PADDING = 8


class ImageGallery(QListWidget):
    """Horizontal thumbnail gallery with uniform centered square thumbnails."""

    item_clicked = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setViewMode(QListWidget.IconMode)
        self.setFlow(QListWidget.LeftToRight)
        self.setWrapping(False)
        self.setUniformItemSizes(True)
        self.setIconSize(QSize(THUMB_SIZE, THUMB_SIZE))
        self.setGridSize(QSize(CELL_SIZE, CELL_SIZE))
        self.setSpacing(0)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        gallery_height = CELL_SIZE + LIST_PADDING
        self.setMinimumHeight(gallery_height)
        self.setMaximumHeight(gallery_height)
        self._placeholder_label: QLabel | None = None
        self.apply_theme_styles()
        self.itemClicked.connect(self._on_item_clicked)
        self._items: list[Any] = []
        self._placeholder_item: QListWidgetItem | None = None

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        if item is self._placeholder_item:
            return
        row = self.row(item)
        if 0 <= row < len(self._items):
            self.item_clicked.emit(row)

    def _add_placeholder(self) -> None:
        self._placeholder_item = QListWidgetItem()
        self._placeholder_item.setFlags(Qt.NoItemFlags)
        self.addItem(self._placeholder_item)

        size = self.viewport().size() - QSize(20, 20)
        label = QLabel("拖拽图片到这里显示")
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        label.setFixedSize(size)
        label.setStyleSheet(gallery_placeholder_stylesheet())
        self._placeholder_label = label
        self.setItemWidget(self._placeholder_item, label)
        self._placeholder_item.setSizeHint(size)

    def _make_thumbnail(self, image: Image.Image) -> QPixmap:
        size = THUMB_SIZE
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        x = (size - image.width) // 2
        y = (size - image.height) // 2
        canvas.paste(image, (x, y), image)
        data = np.array(canvas.convert("RGBA"))
        height, width, _ = data.shape
        bytes_per_line = width * 4
        q_image = QImage(data.data, width, height, bytes_per_line, QImage.Format_RGBA8888)
        return QPixmap.fromImage(q_image)

    def set_images(self, images: list[Image.Image], names: list[str], current_index: int) -> None:
        self.clear()
        self._placeholder_item = None
        self._items = list(images)

        if not images:
            self._add_placeholder()
            return

        for index, (image, name) in enumerate(zip(images, names)):
            pixmap = self._make_thumbnail(image.copy())
            item = QListWidgetItem(QIcon(pixmap), "")
            item.setToolTip(f"{name}\n{image.width}x{image.height}")
            self.addItem(item)
        if 0 <= current_index < self.count():
            self.setCurrentRow(current_index)

    def apply_theme_styles(self) -> None:
        self.setStyleSheet(image_gallery_stylesheet())
        if self._placeholder_label is not None:
            self._placeholder_label.setStyleSheet(gallery_placeholder_stylesheet())
