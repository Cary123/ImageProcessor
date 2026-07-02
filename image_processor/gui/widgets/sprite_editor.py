#!/usr/bin/env python3
"""Visual sprite sheet editor with drag-drop layout and guides."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from PySide6.QtCore import Qt, QMimeData, Signal
from PySide6.QtGui import QDrag, QDragEnterEvent, QDropEvent, QImage, QPixmap
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from image_processor.utils.helpers import collect_images


class SourceListWidget(QListWidget):
    """List widget that drags the item index as mime data."""

    def startDrag(self, supportedActions) -> None:
        item = self.currentItem()
        if item is None:
            return
        index = item.data(Qt.UserRole)
        if index is None:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(str(index))
        drag.setMimeData(mime)
        drag.exec(supportedActions)


class SpriteGridView(QGraphicsView):
    """Graphics view for arranging sprite cells."""

    sprite_moved = Signal(int, float, float)
    order_changed = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setAlignment(Qt.AlignCenter)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setAcceptDrops(True)
        self.setMinimumHeight(300)

        self._cols = 4
        self._spacing = 0
        self._padding = 0
        self._cells: list[QGraphicsPixmapItem] = []
        self._guides: list[QGraphicsLineItem] = []
        self._center_dots: list[QGraphicsEllipseItem] = []
        self._cell_size = 64
        self._sprite_size = 64
        self._dragging_index: int | None = None
        self._drag_start_pos: Any = None
        self._order: list[int] = []

    def set_grid(self, cols: int, spacing: int, padding: int) -> None:
        self._cols = max(1, cols)
        self._spacing = max(0, spacing)
        self._padding = max(0, padding)
        self._layout_cells()

    def _clear(self) -> None:
        for cell in self._cells:
            self.scene.removeItem(cell)
        for guide in self._guides:
            self.scene.removeItem(guide)
        for dot in self._center_dots:
            self.scene.removeItem(dot)
        self._cells.clear()
        self._guides.clear()
        self._center_dots.clear()

    def _cell_rect(self, index: int) -> tuple[float, float, float, float]:
        row, col = divmod(index, self._cols)
        x = col * (self._cell_size + self._spacing) + self._padding
        y = row * (self._cell_size + self._spacing) + self._padding
        return x, y, self._cell_size, self._cell_size

    def _layout_cells(self) -> None:
        for index, cell in enumerate(self._cells):
            x, y, w, h = self._cell_rect(index)
            cell.setOffset(x + (w - cell.pixmap().width()) / 2, y + (h - cell.pixmap().height()) / 2)
        for index, (guide, dot) in enumerate(zip(self._guides, self._center_dots)):
            x, y, w, h = self._cell_rect(index)
            cx = x + w / 2
            cy = y + h / 2
            guide.setLine(x + 2, cy, x + w - 2, cy)
            dot.setRect(cx - 2, cy - 2, 4, 4)

    def update_guides(self, visible: bool) -> None:
        for guide in self._guides:
            guide.setVisible(visible)
        for dot in self._center_dots:
            dot.setVisible(visible)

    def set_images(self, images: list[Image.Image]) -> None:
        self._clear()
        self._order = list(range(len(images)))
        if not images:
            self.scene.setSceneRect(0, 0, 320, 240)
            return
        max_width = max(img.width for img in images)
        max_height = max(img.height for img in images)
        self._cell_size = max(max_width, max_height) + self._padding * 2
        self._sprite_size = max(max_width, max_height)
        rows = math.ceil(len(images) / self._cols)
        scene_width = self._cols * (self._cell_size + self._spacing) + self._padding * 2
        scene_height = rows * (self._cell_size + self._spacing) + self._padding * 2
        self.scene.setSceneRect(0, 0, scene_width, scene_height)

        for display_index, image_index in enumerate(self._order):
            image = images[image_index]
            x, y, w, h = self._cell_rect(display_index)
            cell = QGraphicsPixmapItem(self._pil_to_pixmap(image))
            cell.setOffset(x + (w - image.width) / 2, y + (h - image.height) / 2)
            cell.setZValue(1)
            cell.setFlag(QGraphicsItem.ItemIsMovable, True)
            cell.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
            self.scene.addItem(cell)
            self._cells.append(cell)

            cx = x + w / 2
            cy = y + h / 2
            guide = QGraphicsLineItem(x + 2, cy, x + w - 2, cy)
            pen = guide.pen()
            pen.setColor(Qt.red)
            pen.setWidth(1)
            pen.setStyle(Qt.DashLine)
            guide.setPen(pen)
            guide.setZValue(2)
            self.scene.addItem(guide)
            self._guides.append(guide)

            dot = QGraphicsEllipseItem(cx - 2, cy - 2, 4, 4)
            dot.setBrush(Qt.red)
            dot.setZValue(3)
            self.scene.addItem(dot)
            self._center_dots.append(dot)

        self.update_guides(True)

    def _pil_to_pixmap(self, image: Image.Image) -> QPixmap:
        data = np.array(image.convert("RGBA"))
        height, width, _ = data.shape
        bytes_per_line = width * 4
        q_image = QImage(data.data, width, height, bytes_per_line, QImage.Format_RGBA8888)
        return QPixmap.fromImage(q_image)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        text = event.mimeData().text()
        if not text:
            return
        try:
            index = int(text)
        except ValueError:
            return
        if 0 <= index < len(self._cells):
            scene_pos = self.mapToScene(event.pos())
            target_cell = self._cell_at(scene_pos)
            if target_cell is not None and target_cell != index:
                self._swap_cells(index, target_cell)
            event.acceptProposedAction()

    def _cell_at(self, scene_pos: Any) -> int | None:
        for index, cell in enumerate(self._cells):
            offset = cell.offset()
            rect = cell.boundingRect()
            if offset.x() <= scene_pos.x() <= offset.x() + rect.width():
                if offset.y() <= scene_pos.y() <= offset.y() + rect.height():
                    return index
        return None

    def _swap_cells(self, a: int, b: int) -> None:
        self._cells[a], self._cells[b] = self._cells[b], self._cells[a]
        self._order[a], self._order[b] = self._order[b], self._order[a]
        self._layout_cells()
        self.sprite_moved.emit(a, 0, 0)
        self.order_changed.emit(self._order[:])

    def center_sprite(self, index: int) -> None:
        if 0 <= index < len(self._cells):
            x, y, w, h = self._cell_rect(index)
            cell = self._cells[index]
            cell.setOffset(x + (w - cell.pixmap().width()) / 2, y + (h - cell.pixmap().height()) / 2)

    def get_layout(self) -> list[tuple[int, int]]:
        """Return current sprite offsets relative to their cell centers."""
        result = []
        for index, cell in enumerate(self._cells):
            x, y, w, h = self._cell_rect(index)
            cx = x + w / 2 - cell.pixmap().width() / 2
            cy = y + h / 2 - cell.pixmap().height() / 2
            result.append((int(cell.offset().x() - cx), int(cell.offset().y() - cy)))
        return result

    def get_order(self) -> list[int]:
        return self._order[:]


class SpriteEditor(QWidget):
    """Widget for visually editing sprite sheet layouts."""

    request_sprite = Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self._image_paths: list[Path] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("列数:"))
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 20)
        self.cols_spin.setValue(4)
        controls.addWidget(self.cols_spin)
        controls.addWidget(QLabel("间距:"))
        self.spacing_spin = QSpinBox()
        self.spacing_spin.setRange(0, 100)
        self.spacing_spin.setValue(0)
        controls.addWidget(self.spacing_spin)
        controls.addWidget(QLabel("内边距:"))
        self.padding_spin = QSpinBox()
        self.padding_spin.setRange(0, 100)
        self.padding_spin.setValue(0)
        controls.addWidget(self.padding_spin)
        controls.addStretch()

        self.guides_button = QPushButton("隐藏辅助线")
        self.guides_button.setCheckable(True)
        self.guides_button.clicked.connect(self._toggle_guides)
        controls.addWidget(self.guides_button)

        self.center_button = QPushButton("居中所有精灵")
        self.center_button.clicked.connect(self._center_all)
        controls.addWidget(self.center_button)

        self.generate_button = QPushButton("生成精灵图")
        self.generate_button.setStyleSheet("background-color: #3B82F6; color: white; padding: 6px;")
        self.generate_button.clicked.connect(self._on_generate)
        controls.addWidget(self.generate_button)
        layout.addLayout(controls)

        self.grid_view = SpriteGridView()
        self.grid_view.order_changed.connect(self._on_order_changed)
        layout.addWidget(self.grid_view, 1)

        self.source_list = SourceListWidget()
        self.source_list.setFlow(QListWidget.LeftToRight)
        self.source_list.setWrapping(False)
        self.source_list.setDragEnabled(True)
        self.source_list.setMinimumHeight(80)
        self.source_list.setMaximumHeight(120)
        layout.addWidget(self.source_list)

        self.cols_spin.valueChanged.connect(self._update_grid)
        self.spacing_spin.valueChanged.connect(self._update_grid)
        self.padding_spin.valueChanged.connect(self._update_grid)

    def _toggle_guides(self) -> None:
        visible = not self.guides_button.isChecked()
        self.grid_view.update_guides(visible)
        self.guides_button.setText("隐藏辅助线" if visible else "显示辅助线")

    def _center_all(self) -> None:
        for index in range(len(self.grid_view._cells)):
            self.grid_view.center_sprite(index)

    def _update_grid(self) -> None:
        self.grid_view.set_grid(
            self.cols_spin.value(),
            self.spacing_spin.value(),
            self.padding_spin.value(),
        )
        if self._image_paths:
            self.grid_view.set_images([Image.open(p).convert("RGBA") for p in self._image_paths])

    def _on_order_changed(self, order: list[int]) -> None:
        if order and max(order) < len(self._image_paths):
            self._image_paths = [self._image_paths[i] for i in order]
            self._refresh_source_list()

    def _refresh_source_list(self) -> None:
        self.source_list.clear()
        for index, path in enumerate(self._image_paths):
            try:
                image = Image.open(path).convert("RGBA")
                data = np.array(image.convert("RGBA"))
                height, width, _ = data.shape
                bytes_per_line = width * 4
                q_image = QImage(data.data, width, height, bytes_per_line, QImage.Format_RGBA8888)
                pixmap = QPixmap.fromImage(q_image).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                item = QListWidgetItem(pixmap, path.name)
                item.setData(Qt.UserRole, index)
                item.setToolTip(str(path))
                self.source_list.addItem(item)
            except Exception as exc:
                QMessageBox.warning(self, "加载失败", f"无法加载 {path}: {exc}")

    def set_images(self, paths: list[Path]) -> None:
        self._image_paths = paths
        self._refresh_source_list()
        self._update_grid()

    def _on_generate(self) -> None:
        if not self._image_paths:
            QMessageBox.information(self, "提示", "请先加载图片")
            return
        output_path, _ = QFileDialog.getSaveFileName(self, "保存精灵图", "sprite.png", "PNG (*.png)")
        if not output_path:
            return
        json_path = str(Path(output_path).with_suffix(".json"))
        options: dict[str, Any] = {
            "paths": [str(p) for p in self._image_paths],
            "cols": self.cols_spin.value(),
            "spacing": self.spacing_spin.value(),
            "padding": self.padding_spin.value(),
            "output_path": output_path,
            "json_path": json_path,
        }
        self.request_sprite.emit(options)
