#!/usr/bin/env python3
"""Dynamic tool options panel for canvas interaction tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image, ImageDraw

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from image_processor.utils.themes import gallery_hint_stylesheet

if TYPE_CHECKING:
    from image_processor.gui.canvas import ImageCanvas

INTERACTIVE_TOOLS = frozenset(
    {
        "move",
        "rect_select",
        "free_select",
        "clone_stamp",
        "eyedropper",
        "paint_bucket",
    }
)

_TOOL_TITLES = {
    "move": "移动",
    "rect_select": "矩形选择",
    "free_select": "自由选择",
    "clone_stamp": "仿制图章",
    "eyedropper": "吸管",
    "paint_bucket": "油漆桶",
}

_TOOL_HINTS = {
    "move": "拖拽图层以调整位置。可在「图层」面板中管理多个图层。",
    "rect_select": "拖拽绘制矩形选区，用于复制或裁剪内容。",
    "free_select": "按住并拖动绘制套索选区，用于复制不规则区域。",
    "clone_stamp": "按住 Ctrl 并点击设置取样点，然后在目标位置涂抹复制像素。",
    "eyedropper": "点击图片上的像素，将颜色应用到顶栏当前激活的前景色或背景色。",
    "paint_bucket": "点击区域进行填充，颜色取自顶栏当前激活的前景色。",
}


class InteractiveToolPanel(QWidget):
    """Panel for non-brush canvas tools with context-specific sections."""

    brush_size_changed = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self._active_tool = "move"
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        self.title_label = QLabel("工具")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.title_label)

        self.hint_label = QLabel()
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet(gallery_hint_stylesheet())
        layout.addWidget(self.hint_label)

        self._brush_size_section = self._build_brush_size_section()
        layout.addWidget(self._brush_size_section)

        self._selection_section = self._build_selection_section()
        layout.addWidget(self._selection_section)

        self._eyedropper_section = self._build_eyedropper_section()
        layout.addWidget(self._eyedropper_section)

        layout.addStretch()
        self.set_active_tool("move")

    def _section_frame(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(6)
        label = QLabel(title)
        label.setStyleSheet("font-weight: bold; font-size: 12px;")
        frame_layout.addWidget(label)
        return frame, frame_layout

    def _build_brush_size_section(self) -> QWidget:
        frame, frame_layout = self._section_frame("笔刷大小")
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(1, 100)
        self.size_slider.setValue(20)
        self.size_slider.valueChanged.connect(self._on_size_changed)
        frame_layout.addWidget(self.size_slider)
        return frame

    def _build_selection_section(self) -> QWidget:
        frame, frame_layout = self._section_frame("选区")
        self.selection_size_label = QLabel("选区: 未选择")
        frame_layout.addWidget(self.selection_size_label)
        shortcuts = QLabel("Ctrl+C 复制选区\nCtrl+V 粘贴为新图层")
        shortcuts.setStyleSheet(gallery_hint_stylesheet())
        frame_layout.addWidget(shortcuts)
        return frame

    def _build_eyedropper_section(self) -> QWidget:
        frame, frame_layout = self._section_frame("拾取颜色")
        swatch_layout = QHBoxLayout()
        self.picked_color_swatch = QPushButton()
        self.picked_color_swatch.setFixedSize(40, 24)
        self.picked_color_swatch.setEnabled(False)
        swatch_layout.addWidget(self.picked_color_swatch)
        self.picked_color_label = QLabel("尚未拾取")
        self.picked_color_label.setStyleSheet(gallery_hint_stylesheet())
        swatch_layout.addWidget(self.picked_color_label, 1)
        self._update_picked_color_swatch(None)
        frame_layout.addLayout(swatch_layout)
        return frame

    def _on_size_changed(self) -> None:
        self.brush_size_changed.emit(self.size_slider.value())

    def _update_picked_color_swatch(self, color: QColor | None) -> None:
        if color is None:
            self.picked_color_swatch.setStyleSheet(
                "background-color: #808080; border: 1px solid #9CA3AF; border-radius: 3px;"
            )
            self.picked_color_label.setText("尚未拾取")
            return
        self.picked_color_swatch.setStyleSheet(
            f"background-color: {color.name(QColor.HexArgb)}; "
            f"border: 1px solid #9CA3AF; border-radius: 3px;"
        )
        self.picked_color_label.setText(color.name(QColor.HexArgb).upper())

    def set_active_tool(self, tool_id: str) -> None:
        self._active_tool = tool_id if tool_id in INTERACTIVE_TOOLS else "move"
        self.title_label.setText(_TOOL_TITLES.get(self._active_tool, "工具"))
        self.hint_label.setText(_TOOL_HINTS.get(self._active_tool, ""))

        self._brush_size_section.setVisible(self._active_tool == "clone_stamp")
        self._selection_section.setVisible(self._active_tool in ("rect_select", "free_select"))
        self._eyedropper_section.setVisible(self._active_tool == "eyedropper")

    def set_brush_size(self, size: int) -> None:
        blocked = self.size_slider.blockSignals(True)
        self.size_slider.setValue(max(1, min(100, size)))
        self.size_slider.blockSignals(blocked)

    def refresh_selection(self, canvas: ImageCanvas) -> None:
        if self._active_tool not in ("rect_select", "free_select"):
            return
        layer = canvas.active_layer()
        if canvas.selection_rect is not None:
            left, top, right, bottom = canvas.selection_rect
            width = max(0, int(abs(right - left)))
            height = max(0, int(abs(bottom - top)))
            self.selection_size_label.setText(f"选区: {width} × {height} px")
            return
        if (
            layer is not None
            and canvas.selection_polygon is not None
            and len(canvas.selection_polygon) >= 3
        ):
            import numpy as np
            from PIL import ImageDraw

            poly = [(int(p.x() - layer.x), int(p.y() - layer.y)) for p in canvas.selection_polygon]
            mask = Image.new("L", layer.image.size, 0)
            ImageDraw.Draw(mask).polygon(poly, fill=255)
            pixels = int(np.asarray(mask).sum() // 255)
            self.selection_size_label.setText(f"选区: {pixels} px")
            return
        self.selection_size_label.setText("选区: 未选择")

    def set_picked_color(self, color: QColor) -> None:
        self._update_picked_color_swatch(color)

    def apply_theme_styles(self) -> None:
        self.hint_label.setStyleSheet(gallery_hint_stylesheet())
        for label in self.findChildren(QLabel):
            if label is self.title_label:
                continue
            text = label.text()
            if text.startswith("Ctrl+") or text == "尚未拾取":
                label.setStyleSheet(gallery_hint_stylesheet())
