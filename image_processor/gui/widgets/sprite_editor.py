#!/usr/bin/env python3
"""Manual sprite sheet editor with fixed grid canvas and drag-drop layout."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from PySide6.QtCore import Qt, QMimeData, Signal
from PySide6.QtGui import QCloseEvent, QDrag, QDragEnterEvent, QDropEvent, QImage, QPixmap, QWheelEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from image_processor.gui.widgets.zoom_combo import ZoomComboBox


class SourceListWidget(QListWidget):
    """Gallery list that drags the sprite index as mime data."""

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


class SpriteGridCanvas(QGraphicsView):
    """Fixed-size canvas with a grid of drop targets."""

    cell_filled = Signal(int, int)
    zoom_changed = Signal(float)

    def __init__(self) -> None:
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setAlignment(Qt.AlignCenter)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setAcceptDrops(True)
        self.setMinimumSize(400, 400)

        self._canvas_width = 768
        self._canvas_height = 768
        self._rows = 4
        self._cols = 4
        self._zoom_scale = 0.5
        self._images: list[Image.Image] = []
        self._cells: list[QGraphicsPixmapItem | None] = [None] * (self._rows * self._cols)
        self._grid_lines: list[QGraphicsLineItem] = []
        self._center_dots: list[QGraphicsEllipseItem] = []
        self._background: QGraphicsRectItem | None = None
        self._guides_visible = True

        self._build_scene()
        self._apply_zoom()

    def _build_scene(self) -> None:
        self.scene.clear()
        self._grid_lines.clear()
        self._center_dots.clear()
        self._cells = [None] * (self._rows * self._cols)

        self.scene.setSceneRect(0, 0, self._canvas_width, self._canvas_height)

        self._background = QGraphicsRectItem(0, 0, self._canvas_width, self._canvas_height)
        self._background.setBrush(Qt.white)
        self._background.setPen(Qt.NoPen)
        self._background.setZValue(-1)
        self.scene.addItem(self._background)

        cell_w = self._canvas_width / self._cols
        cell_h = self._canvas_height / self._rows

        for row in range(self._rows + 1):
            y = row * cell_h
            line = QGraphicsLineItem(0, y, self._canvas_width, y)
            pen = line.pen()
            pen.setColor(Qt.gray)
            pen.setWidth(1)
            line.setPen(pen)
            line.setZValue(0)
            self.scene.addItem(line)
            self._grid_lines.append(line)

        for col in range(self._cols + 1):
            x = col * cell_w
            line = QGraphicsLineItem(x, 0, x, self._canvas_height)
            pen = line.pen()
            pen.setColor(Qt.gray)
            pen.setWidth(1)
            line.setPen(pen)
            line.setZValue(0)
            self.scene.addItem(line)
            self._grid_lines.append(line)

        for index in range(self._rows * self._cols):
            row, col = divmod(index, self._cols)
            cx = col * cell_w + cell_w / 2
            cy = row * cell_h + cell_h / 2
            dot = QGraphicsEllipseItem(cx - 2, cy - 2, 4, 4)
            dot.setBrush(Qt.red)
            dot.setZValue(2)
            dot.setVisible(self._guides_visible)
            self.scene.addItem(dot)
            self._center_dots.append(dot)

    def set_grid(self, width: int, height: int, rows: int, cols: int) -> None:
        self._canvas_width = max(1, width)
        self._canvas_height = max(1, height)
        self._rows = max(1, rows)
        self._cols = max(1, cols)
        self._build_scene()
        self._apply_zoom()

    def zoom_scale(self) -> float:
        return self._zoom_scale

    def set_zoom_scale(self, scale: float, *, emit: bool = True) -> None:
        self._zoom_scale = max(0.1, min(5.0, scale))
        self._apply_zoom()
        if emit:
            self.zoom_changed.emit(self._zoom_scale)

    def _apply_zoom(self) -> None:
        self.resetTransform()
        self.scale(self._zoom_scale, self._zoom_scale)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.1 if event.angleDelta().y() > 0 else 0.9
            self.set_zoom_scale(self._zoom_scale * factor)
            return
        super().wheelEvent(event)

    def set_guides_visible(self, visible: bool) -> None:
        self._guides_visible = visible
        for dot in self._center_dots:
            dot.setVisible(visible)

    def _cell_index_at(self, scene_pos: Any) -> int | None:
        cell_w = self._canvas_width / self._cols
        cell_h = self._canvas_height / self._rows
        col = int(scene_pos.x() // cell_w)
        row = int(scene_pos.y() // cell_h)
        if 0 <= col < self._cols and 0 <= row < self._rows:
            return row * self._cols + col
        return None

    def _cell_rect(self, index: int) -> tuple[float, float, float, float]:
        row, col = divmod(index, self._cols)
        cell_w = self._canvas_width / self._cols
        cell_h = self._canvas_height / self._rows
        return col * cell_w, row * cell_h, cell_w, cell_h

    def set_images(self, images: list[Image.Image]) -> None:
        self._images = images

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        text = event.mimeData().text()
        try:
            source_index = int(text)
        except ValueError:
            return
        if not (0 <= source_index < len(self._images)):
            return
        scene_pos = self.mapToScene(event.pos())
        cell_index = self._cell_index_at(scene_pos)
        if cell_index is None:
            return
        self._fill_cell(cell_index, source_index)
        event.acceptProposedAction()

    def _fill_cell(self, cell_index: int, source_index: int) -> None:
        image = self._images[source_index].copy()
        x, y, cell_w, cell_h = self._cell_rect(cell_index)
        # Scale down to fit inside the cell while keeping aspect ratio.
        scaled = image.copy()
        if scaled.width > cell_w or scaled.height > cell_h:
            scaled.thumbnail((int(cell_w), int(cell_h)), Image.Resampling.LANCZOS)
        pixmap = self._pil_to_pixmap(scaled)

        if self._cells[cell_index] is not None:
            self.scene.removeItem(self._cells[cell_index])

        item = QGraphicsPixmapItem(pixmap)
        offset_x = x + (cell_w - pixmap.width()) / 2
        offset_y = y + (cell_h - pixmap.height()) / 2
        item.setOffset(offset_x, offset_y)
        item.setZValue(1)
        item.setFlag(QGraphicsItem.ItemIsMovable, True)
        item.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.scene.addItem(item)
        self._cells[cell_index] = item
        self.cell_filled.emit(cell_index, source_index)

    def clear_cell(self, cell_index: int) -> None:
        if 0 <= cell_index < len(self._cells) and self._cells[cell_index] is not None:
            self.scene.removeItem(self._cells[cell_index])
            self._cells[cell_index] = None

    def clear_all_cells(self) -> None:
        for index, item in enumerate(self._cells):
            if item is not None:
                self.scene.removeItem(item)
                self._cells[index] = None

    def center_all_cells(self) -> None:
        for index, item in enumerate(self._cells):
            if item is None:
                continue
            x, y, cell_w, cell_h = self._cell_rect(index)
            pixmap = item.pixmap()
            offset_x = x + (cell_w - pixmap.width()) / 2
            offset_y = y + (cell_h - pixmap.height()) / 2
            item.setOffset(offset_x, offset_y)

    def export_image(self) -> Image.Image:
        canvas = Image.new("RGBA", (self._canvas_width, self._canvas_height), (0, 0, 0, 0))
        for index, item in enumerate(self._cells):
            if item is None:
                continue
            x = int(item.offset().x())
            y = int(item.offset().y())
            image = self._pil_from_pixmap(item.pixmap())
            canvas.paste(image, (x, y), image)
        return canvas

    def _pil_to_pixmap(self, image: Image.Image) -> QPixmap:
        data = np.array(image.convert("RGBA"))
        height, width, _ = data.shape
        bytes_per_line = width * 4
        q_image = QImage(data.data, width, height, bytes_per_line, QImage.Format_RGBA8888)
        return QPixmap.fromImage(q_image)

    def _pil_from_pixmap(self, pixmap: QPixmap) -> Image.Image:
        image = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
        width = image.width()
        height = image.height()
        ptr = image.bits()
        data = np.frombuffer(ptr, dtype=np.uint8).reshape(height, width, 4).copy()
        return Image.fromarray(data, "RGBA")


class SpriteEditor(QWidget):
    """Widget for manually arranging sprites on a fixed grid canvas."""

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

        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 4096)
        self.width_spin.setValue(768)
        self.width_spin.setSuffix(" px")

        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 4096)
        self.height_spin.setValue(768)
        self.height_spin.setSuffix(" px")

        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 64)
        self.rows_spin.setValue(4)

        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 64)
        self.cols_spin.setValue(4)

        size_form = QFormLayout()
        size_form.setSpacing(4)
        size_form.addRow("画布宽:", self.width_spin)
        size_form.addRow("画布高:", self.height_spin)

        grid_form = QFormLayout()
        grid_form.setSpacing(4)
        grid_form.addRow("行数:", self.rows_spin)
        grid_form.addRow("列数:", self.cols_spin)

        forms_layout = QHBoxLayout()
        forms_layout.setSpacing(16)
        forms_layout.addLayout(size_form)
        forms_layout.addLayout(grid_form)
        controls.addLayout(forms_layout)

        controls.addSpacing(16)

        self.upload_button = QPushButton("上传图片...")
        self.upload_button.setStyleSheet("background-color: #3B82F6; color: white; padding: 6px;")
        self.upload_button.clicked.connect(self._upload_images)
        controls.addWidget(self.upload_button)

        self.clear_button = QPushButton("清空网格")
        self.clear_button.clicked.connect(self._clear_grid)
        controls.addWidget(self.clear_button)

        self.center_button = QPushButton("居中所有精灵")
        self.center_button.clicked.connect(self._center_all)
        controls.addWidget(self.center_button)

        self.guides_button = QPushButton("隐藏辅助线")
        self.guides_button.setCheckable(True)
        self.guides_button.clicked.connect(self._toggle_guides)
        controls.addWidget(self.guides_button)

        controls.addSpacing(8)
        controls.addWidget(QLabel("缩放:"))
        self.zoom_combo = ZoomComboBox()
        self.zoom_combo.zoom_changed.connect(self._on_zoom_combo_changed)
        controls.addWidget(self.zoom_combo)

        self.export_button = QPushButton("导出精灵图")
        self.export_button.setStyleSheet("background-color: #10B981; color: white; padding: 6px;")
        self.export_button.clicked.connect(self._export_sprite)
        controls.addWidget(self.export_button)

        controls.addStretch()
        layout.addLayout(controls)

        self.grid_canvas = SpriteGridCanvas()
        layout.addWidget(self.grid_canvas, 1)

        self.source_list = SourceListWidget()
        self.source_list.setFlow(QListWidget.LeftToRight)
        self.source_list.setWrapping(False)
        self.source_list.setDragEnabled(True)
        self.source_list.setMinimumHeight(100)
        self.source_list.setMaximumHeight(140)
        layout.addWidget(self.source_list)

        self.width_spin.valueChanged.connect(self._on_grid_changed)
        self.height_spin.valueChanged.connect(self._on_grid_changed)
        self.rows_spin.valueChanged.connect(self._on_grid_changed)
        self.cols_spin.valueChanged.connect(self._on_grid_changed)
        self.grid_canvas.zoom_changed.connect(self.zoom_combo.set_zoom_scale)

    def _on_zoom_combo_changed(self, scale: float) -> None:
        self.grid_canvas.set_zoom_scale(scale, emit=False)

    def _on_grid_changed(self) -> None:
        self.grid_canvas.set_grid(
            self.width_spin.value(),
            self.height_spin.value(),
            self.rows_spin.value(),
            self.cols_spin.value(),
        )
        self.grid_canvas.set_images([Image.open(p).convert("RGBA") for p in self._image_paths])

    def _upload_images(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择精灵图片",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)",
        )
        if not paths:
            return
        self.set_images([Path(p) for p in paths])

    def set_images(self, paths: list[Path]) -> None:
        self._image_paths = paths
        self.source_list.clear()
        images = []
        for index, path in enumerate(paths):
            try:
                image = Image.open(path).convert("RGBA")
                images.append(image)
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
        self.grid_canvas.set_images(images)

    def _clear_grid(self) -> None:
        self.grid_canvas.clear_all_cells()

    def _center_all(self) -> None:
        self.grid_canvas.center_all_cells()

    def _toggle_guides(self) -> None:
        visible = not self.guides_button.isChecked()
        self.grid_canvas.set_guides_visible(visible)
        self.guides_button.setText("隐藏辅助线" if visible else "显示辅助线")

    def _export_sprite(self) -> None:
        output_path, _ = QFileDialog.getSaveFileName(self, "保存精灵图", "sprite.png", "PNG (*.png)")
        if not output_path:
            return
        try:
            image = self.grid_canvas.export_image()
            image.save(output_path)
            QMessageBox.information(self, "导出成功", f"精灵图已保存: {output_path}")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))


class SpriteEditorWindow(QMainWindow):
    """Standalone window for the sprite sheet editor."""

    closed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("精灵图编辑器")
        self.setMinimumSize(900, 700)
        self._editor = SpriteEditor()
        self.setCentralWidget(self._editor)

    def set_images(self, paths: list[Path]) -> None:
        self._editor.set_images(paths)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.closed.emit()
        event.accept()
