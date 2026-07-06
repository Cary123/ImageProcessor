#!/usr/bin/env python3
"""Layer list panel with visibility, deletion, drag reorder, and opacity controls."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QRect, Qt, Signal, QSize
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QStyledItemDelegate,
    QStyle,
    QVBoxLayout,
    QWidget,
    QLabel,
)

from image_processor.gui.widgets.icons import get_svg_icon


class DeleteIconDelegate(QStyledItemDelegate):
    """Delegate that paints a delete icon on the right when an item is hovered."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._delete = get_svg_icon("delete", 18)

    def paint(self, painter, option, index) -> None:
        super().paint(painter, option, index)
        if option.state & QStyle.State_MouseOver:
            rect = option.rect
            delete_rect = QRect(rect.right() - 24, rect.y() + (rect.height() - 18) // 2, 18, 18)
            self._delete.paint(painter, delete_rect)

    def sizeHint(self, option, index) -> QSize:
        return QSize(max(1, option.rect.width()), 36)


class LayersPanel(QWidget):
    """Panel for managing image layers."""

    layer_selected = Signal(int)
    layer_visibility_changed = Signal(int)
    layer_deleted = Signal(int)
    layer_renamed = Signal(int, str)
    layers_reordered = Signal(list)
    new_layer_requested = Signal()
    opacity_changed = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self._updating = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(6)
        top_bar.addStretch()
        self.new_button = QPushButton()
        self.new_button.setFixedSize(32, 32)
        self.new_button.setIcon(get_svg_icon("new_layer", 18))
        self.new_button.setToolTip("新建图层")
        self.new_button.clicked.connect(self.new_layer_requested.emit)
        top_bar.addWidget(self.new_button)
        layout.addLayout(top_bar)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.list_widget.setMouseTracking(True)
        self.list_widget.viewport().setMouseTracking(True)
        self.list_widget.viewport().installEventFilter(self)
        self.list_widget.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.list_widget.setIconSize(QSize(18, 18))
        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        self.list_widget.model().rowsMoved.connect(self._on_rows_moved)
        self.list_widget.itemChanged.connect(self._on_item_changed)
        self._delegate = DeleteIconDelegate(self.list_widget)
        self.list_widget.setItemDelegate(self._delegate)
        layout.addWidget(self.list_widget, 1)

        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("不透明度"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_layout.addWidget(self.opacity_slider)
        layout.addLayout(opacity_layout)

    def set_layers(self, names: list[str], visibilities: list[bool], selected_row: int) -> None:
        self._updating = True
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        # Display topmost layer first. Canvas order is bottom-to-top, so reverse here.
        for panel_row, canvas_index in enumerate(range(len(names) - 1, -1, -1)):
            name = names[canvas_index]
            visible = visibilities[canvas_index]
            item = QListWidgetItem(name)
            item.setFlags(
                item.flags()
                | Qt.ItemIsEnabled
                | Qt.ItemIsSelectable
                | Qt.ItemIsDragEnabled
                | Qt.ItemIsEditable
            )
            item.setData(Qt.UserRole, canvas_index)
            item.setData(Qt.UserRole + 1, visible)
            item.setData(Qt.UserRole + 2, name)
            item.setIcon(get_svg_icon("eye-fill" if visible else "eye-close", 18))
            self.list_widget.addItem(item)
        if 0 <= selected_row < self.list_widget.count():
            self.list_widget.setCurrentRow(selected_row)
        self.list_widget.blockSignals(False)
        self._updating = False

    def eventFilter(self, obj: QWidget, event: QEvent) -> bool:
        if obj is self.list_widget.viewport() and event.type() == QEvent.MouseButtonRelease:
            pos = self.list_widget.mapFromGlobal(event.globalPos())
            item = self.list_widget.itemAt(pos)
            if item is not None and item.flags() != Qt.NoItemFlags:
                row = self.list_widget.row(item)
                rect = self.list_widget.visualItemRect(item)
                x = pos.x()
                if x < rect.x() + 28:
                    self.layer_visibility_changed.emit(row)
                    return True
                if (x > rect.right() - 28) and (item is self.list_widget.itemAt(pos)):
                    self.layer_deleted.emit(row)
                    return True
        return super().eventFilter(obj, event)

    def _on_row_changed(self, row: int) -> None:
        if row >= 0 and not self._updating:
            self.layer_selected.emit(row)

    def _on_rows_moved(self, parent, start, end, destination, row) -> None:
        if self._updating:
            return
        model = self.list_widget.model()
        new_panel_order = []
        for r in range(model.rowCount()):
            idx = model.index(r, 0)
            canvas_index = idx.data(Qt.UserRole)
            if canvas_index is not None:
                new_panel_order.append(canvas_index)
        if new_panel_order:
            self.layers_reordered.emit(new_panel_order)

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        if self._updating:
            return
        old_name = item.data(Qt.UserRole + 2)
        new_name = item.text()
        if new_name != old_name:
            item.setData(Qt.UserRole + 2, new_name)
            row = self.list_widget.row(item)
            self.layer_renamed.emit(row, new_name)

    def _on_opacity_changed(self, value: int) -> None:
        self.opacity_changed.emit(value)

    def update_opacity(self, value: int) -> None:
        self.opacity_slider.blockSignals(True)
        self.opacity_slider.setValue(value)
        self.opacity_slider.blockSignals(False)
