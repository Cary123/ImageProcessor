#!/usr/bin/env python3
"""Main application window."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image
from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QAction, QCloseEvent, QDragEnterEvent, QDropEvent, QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from image_processor.core.image_engine import EngineError, export_image
from image_processor.core.project_manager import ProjectError, ProjectManager
from image_processor.gui.canvas import ImageCanvas
from image_processor.gui.panels.adjust_panel import AdjustPanel
from image_processor.gui.panels.brush_panel import BrushPanel
from image_processor.gui.panels.crop_panel import CropPanel
from image_processor.gui.panels.grid_panel import GridPanel
from image_processor.gui.panels.inpaint_panel import InpaintPanel
from image_processor.gui.panels.layers_panel import LayersPanel
from image_processor.gui.panels.matting_panel import MattingPanel
from image_processor.gui.panels.resize_panel import ResizePanel
from image_processor.gui.toolbar import ToolBar
from image_processor.gui.widgets.batch_dialog import BatchDialog
from image_processor.gui.widgets.color_bar import ColorBar
from image_processor.gui.widgets.compare_dialog import CompareDialog
from image_processor.gui.widgets.image_gallery import ImageGallery
from image_processor.gui.widgets.matting_worker import MattingWorker
from image_processor.gui.widgets.slider_compare import SliderCompareDialog
from image_processor.gui.widgets.sprite_editor import SpriteEditor
from image_processor.gui.widgets.toast import Toast
from image_processor.models.image_item import ImageItem
from image_processor.utils.helpers import collect_images, is_matting_model_available
from image_processor.utils.recent_files import RecentFilesManager
from image_processor.utils.themes import apply_theme, gallery_frame_stylesheet, gallery_hint_stylesheet
from image_processor.gui.widgets.icons import get_icon


class MainWindow(QMainWindow):
    """Primary application window for ImageProcessor."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ImageProcessor")
        self.setMinimumSize(1024, 768)
        self.setAcceptDrops(True)

        self.thread_pool = QThreadPool.globalInstance()
        self.images: list[ImageItem] = []
        self.current_index = -1
        self.recent_files = RecentFilesManager()
        self._matting_item: ImageItem | None = None

        self._build_ui()
        self._connect_signals()
        self._apply_editor_theme_styles()
        self._update_status()
        self.canvas.setFocus()

    def _build_ui(self) -> None:
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        self.image_editor = self._build_image_editor()
        self.sprite_editor = SpriteEditor()

        self.tab_widget.addTab(self.image_editor, "图片编辑")
        self.tab_widget.addTab(self.sprite_editor, "精灵图")

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)

        self.status_zoom_label = QLabel("50%")
        self.status_zoom_label.setMinimumWidth(60)
        self.status_coord_label = QLabel("--, -- px")
        self.status_coord_label.setMinimumWidth(90)

        self.status_bar = QStatusBar()
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.status_bar.addPermanentWidget(self.status_zoom_label)
        self.status_bar.addPermanentWidget(self.status_coord_label)
        self.setStatusBar(self.status_bar)

        self._build_menu()

    def _build_image_editor(self) -> QWidget:
        editor = QWidget()
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)

        self.color_bar = ColorBar()
        editor_layout.addWidget(self.color_bar)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self.toolbar = ToolBar()
        content_layout.addWidget(self.toolbar)

        self.content_splitter = QSplitter(Qt.Horizontal)
        content_layout.addWidget(self.content_splitter, 1)

        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setSpacing(0)
        center_layout.setContentsMargins(0, 0, 0, 0)

        self.canvas = ImageCanvas()
        center_layout.addWidget(self.canvas, 1)

        gallery_layout = QHBoxLayout()
        gallery_layout.setSpacing(6)
        gallery_layout.setContentsMargins(6, 4, 6, 4)

        self.prev_button = QPushButton()
        self.prev_button.setFixedSize(36, 64)
        self.prev_button.setIcon(get_icon("prev", size=20))
        self.prev_button.setToolTip("上一张")
        self.prev_button.setEnabled(False)
        self.prev_button.clicked.connect(self._previous_image)
        gallery_layout.addWidget(self.prev_button)

        self.gallery_frame = QFrame()
        self.gallery_frame.setFrameShape(QFrame.StyledPanel)
        gallery_frame_layout = QVBoxLayout(self.gallery_frame)
        gallery_frame_layout.setSpacing(4)
        gallery_frame_layout.setContentsMargins(4, 4, 4, 4)

        self.gallery = ImageGallery()
        gallery_frame_layout.addWidget(self.gallery, 1)

        self.gallery_hint = QLabel("拖拽图片到这里显示")
        self.gallery_hint.setAlignment(Qt.AlignCenter)
        self.gallery_hint.setWordWrap(True)
        gallery_frame_layout.addWidget(self.gallery_hint)

        gallery_layout.addWidget(self.gallery_frame, 1)

        self.next_button = QPushButton()
        self.next_button.setFixedSize(36, 64)
        self.next_button.setIcon(get_icon("next", size=20))
        self.next_button.setToolTip("下一张")
        self.next_button.setEnabled(False)
        self.next_button.clicked.connect(self._next_image)
        gallery_layout.addWidget(self.next_button)

        center_layout.addLayout(gallery_layout)

        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(8, 4, 8, 4)
        info_layout.setSpacing(12)
        self.crop_size_label = QLabel("裁剪尺寸: --")
        self.crop_size_label.setMinimumWidth(120)
        info_layout.addWidget(self.crop_size_label)
        info_layout.addStretch()
        self.zoom_label = QLabel("50%")
        self.zoom_label.setMinimumWidth(60)
        self.coord_label = QLabel("坐标: --, --")
        self.coord_label.setMinimumWidth(120)
        info_layout.addWidget(self.zoom_label)
        info_layout.addWidget(self.coord_label)
        center_layout.addLayout(info_layout)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(0)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.panel_stack = QStackedWidget()
        self.panel_stack.setMinimumWidth(260)
        self.panel_stack.setMaximumWidth(360)

        self.matting_panel = MattingPanel()
        self.resize_panel = ResizePanel()
        self.crop_panel = CropPanel()
        self.inpaint_panel = InpaintPanel()
        self.brush_panel = BrushPanel()
        self.grid_panel = GridPanel()
        self.adjust_panel = AdjustPanel()

        self.panel_stack.addWidget(self.matting_panel)
        self.panel_stack.addWidget(self.resize_panel)
        self.panel_stack.addWidget(self.crop_panel)
        self.panel_stack.addWidget(self.inpaint_panel)
        self.panel_stack.addWidget(self.brush_panel)
        self.panel_stack.addWidget(self.grid_panel)
        self.panel_stack.addWidget(self.adjust_panel)

        self.layers_panel = LayersPanel()
        self.layers_panel.setMinimumWidth(260)
        self.layers_panel.setMaximumWidth(360)

        right_layout.addWidget(self.panel_stack, 2)
        right_layout.addWidget(self.layers_panel, 1)

        self.content_splitter.addWidget(center_widget)
        self.content_splitter.addWidget(right_panel)
        self.content_splitter.setSizes([700, 260])

        editor_layout.addLayout(content_layout, 1)
        return editor

    def _build_menu(self) -> None:
        menu = self.menuBar()
        file_menu = menu.addMenu("文件")

        open_action = QAction("打开图片...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_images)
        file_menu.addAction(open_action)

        open_dir_action = QAction("打开文件夹...", self)
        open_dir_action.triggered.connect(self._open_directory)
        file_menu.addAction(open_dir_action)

        export_action = QAction("导出...", self)
        export_action.setShortcut("Ctrl+S")
        export_action.triggered.connect(self._export_current)
        file_menu.addAction(export_action)

        batch_action = QAction("批量处理...", self)
        batch_action.setShortcut("Ctrl+B")
        batch_action.triggered.connect(self._open_batch_dialog)
        file_menu.addAction(batch_action)

        file_menu.addSeparator()

        save_project_action = QAction("保存项目...", self)
        save_project_action.setShortcut("Ctrl+Shift+S")
        save_project_action.triggered.connect(self._save_project)
        file_menu.addAction(save_project_action)

        open_project_action = QAction("打开项目...", self)
        open_project_action.setShortcut("Ctrl+Shift+O")
        open_project_action.triggered.connect(self._open_project)
        file_menu.addAction(open_project_action)

        file_menu.addSeparator()

        quit_action = QAction("退出", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        self.recent_menu = menu.addMenu("最近文件")
        self._update_recent_menu()

        edit_menu = menu.addMenu("编辑")

        undo_action = QAction("撤销", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self._undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("重做", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self._redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        copy_action = QAction("复制", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self._copy_selection)
        edit_menu.addAction(copy_action)

        paste_action = QAction("粘贴", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self._paste_selection)
        edit_menu.addAction(paste_action)

        view_menu = menu.addMenu("查看")

        prev_action = QAction("上一张", self)
        prev_action.setShortcut("Ctrl+Left")
        prev_action.triggered.connect(self._previous_image)
        view_menu.addAction(prev_action)

        next_action = QAction("下一张", self)
        next_action.setShortcut("Ctrl+Right")
        next_action.triggered.connect(self._next_image)
        view_menu.addAction(next_action)

        view_menu.addSeparator()

        compare_action = QAction("对比原图/处理后", self)
        compare_action.setShortcut("Ctrl+D")
        compare_action.triggered.connect(self._compare_current)
        view_menu.addAction(compare_action)

        slider_compare_action = QAction("滑动对比", self)
        slider_compare_action.setShortcut("Ctrl+Shift+D")
        slider_compare_action.triggered.connect(self._slider_compare_current)
        view_menu.addAction(slider_compare_action)

        view_menu.addSeparator()

        self.dark_theme_action = QAction("深色模式", self)
        self.dark_theme_action.setCheckable(True)
        self.dark_theme_action.setChecked(True)
        self.dark_theme_action.triggered.connect(self._toggle_theme)
        view_menu.addAction(self.dark_theme_action)

    def _connect_signals(self) -> None:
        self.toolbar.tool_selected.connect(self._on_tool_selected)
        self.color_bar.tool_selected.connect(self._on_tool_selected)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        self.canvas.color_picked.connect(self.color_bar.set_active_color)

        self.color_bar.foreground_changed.connect(self.canvas.set_foreground_color)
        self.color_bar.background_changed.connect(self.canvas.set_background_color)
        self.color_bar.zoom_changed.connect(self._on_color_bar_zoom_changed)
        self.canvas.zoom_changed.connect(self.color_bar.set_zoom_scale)

        self.layers_panel.layer_selected.connect(self._on_layer_selected)
        self.layers_panel.layer_visibility_changed.connect(self._on_layer_visibility_changed)
        self.layers_panel.layer_deleted.connect(self._on_layer_deleted)
        self.layers_panel.layer_renamed.connect(self._on_layer_renamed)
        self.layers_panel.new_layer_requested.connect(self._on_new_layer)
        self.layers_panel.opacity_changed.connect(self._on_layer_opacity_changed)
        self.layers_panel.layers_reordered.connect(self._on_layers_reordered)
        self.canvas.layers_changed.connect(self._on_canvas_layers_changed)

        self.matting_panel.request_matting.connect(self._run_matting)
        self.resize_panel.request_resize.connect(self._run_resize)
        self.crop_panel.request_crop.connect(self._run_crop)
        self.crop_panel.request_rotate.connect(self._run_rotate)
        self.crop_panel.request_flip.connect(self._run_flip)
        self.inpaint_panel.request_inpaint.connect(self._run_inpaint)
        self.brush_panel.brush_mode_changed.connect(self._on_brush_mode_changed)
        self.brush_panel.brush_size_changed.connect(self.canvas.set_brush_size)
        self.brush_panel.brush_hardness_changed.connect(self.canvas.set_brush_hardness)
        self.brush_panel.apply_brush.connect(self.canvas.apply_brush)
        self.brush_panel.cancel_brush.connect(self.canvas.cancel_brush)
        self.canvas.brush_applied.connect(self._on_brush_applied)
        self.canvas.image_changed.connect(self._on_canvas_image_changed)
        self.adjust_panel.adjustment_preview.connect(self._preview_adjust)
        self.adjust_panel.adjustment_applied.connect(self._apply_adjust)
        self.grid_panel.grid_changed.connect(self.canvas.set_grid_options)
        self.canvas.zoom_changed.connect(self._on_zoom_changed)
        self.canvas.cursor_moved.connect(self._on_cursor_moved)
        self.canvas.crop_rect_changed.connect(self._on_crop_rect_changed)
        self.crop_panel.crop_values_changed.connect(self._on_crop_values_changed)
        self.gallery.item_clicked.connect(self._on_thumbnail_clicked)

    def _on_tab_changed(self, index: int) -> None:
        if index == 1:
            self.sprite_editor.set_images([item.source_path for item in self.images])

    def _panel_row_to_canvas(self, row: int) -> int:
        layer_count = len(self.canvas.layers())
        return layer_count - 1 - row

    def _on_layer_selected(self, row: int) -> None:
        self.canvas.set_active_layer(self._panel_row_to_canvas(row))

    def _on_layer_visibility_changed(self, row: int) -> None:
        self.canvas.toggle_layer_visibility(self._panel_row_to_canvas(row))

    def _on_layer_deleted(self, row: int) -> None:
        self.canvas.delete_layer(self._panel_row_to_canvas(row))

    def _on_layer_renamed(self, row: int, name: str) -> None:
        self.canvas.rename_layer(self._panel_row_to_canvas(row), name)

    def _on_new_layer(self) -> None:
        self.canvas.add_new_layer()

    def _on_layer_opacity_changed(self, opacity: int) -> None:
        self.canvas.set_all_visible_layers_opacity(opacity)

    def _on_layers_reordered(self, new_panel_order: list[int]) -> None:
        self.canvas.reorder_image_layers(list(reversed(new_panel_order)))

    def _on_canvas_layers_changed(self) -> None:
        layers = self.canvas.layers()
        names = [layer.name for layer in layers]
        visibilities = [layer.visible for layer in layers]
        active = self.canvas.active_layer()
        canvas_index = layers.index(active) if active is not None and active in layers else 0
        selected_row = len(layers) - 1 - canvas_index
        self.layers_panel.set_layers(names, visibilities, selected_row)

    def _on_canvas_image_changed(self, image: Image.Image) -> None:
        if not self.images or self.current_index < 0:
            return
        item = self.images[self.current_index]
        if item.image.tobytes() != image.tobytes():
            item.replace(image, description="编辑")

    def _on_brush_mode_changed(self, mode: str) -> None:
        self.canvas.set_brush_mode(mode)
        self.toolbar.set_tool_checked(mode)

    def _on_tool_selected(self, tool: str) -> None:
        if tool == "sprite":
            self.tab_widget.setCurrentIndex(1)
            return
        self.tab_widget.setCurrentIndex(0)

        mapping = {
            "matting": 0,
            "resize": 1,
            "crop": 2,
            "inpaint": 3,
            "brush": 4,
            "eraser": 4,
            "rect_select": 4,
            "free_select": 4,
            "clone_stamp": 4,
            "move": 4,
            "eyedropper": 4,
            "paint_bucket": 4,
            "grid": 5,
            "adjust": 6,
        }
        self.panel_stack.setCurrentIndex(mapping.get(tool, 0))
        if tool in ("brush", "eraser"):
            self.brush_panel.set_mode("brush" if tool == "brush" else "eraser")
            self.canvas.set_brush_mode("brush" if tool == "brush" else "eraser")
        else:
            self.canvas.set_brush_mode(None)
        if tool in ("rect_select", "free_select", "crop", "clone_stamp", "move", "eyedropper", "paint_bucket"):
            self.canvas.set_tool(tool)
        elif tool == "navigator":
            self.canvas.set_tool("navigator")

        self.toolbar.set_tool_checked(tool)
        self.color_bar.set_tool_checked(tool)
        if tool == "grid" and 0 <= self.current_index < len(self.images):
            self.canvas.set_grid_options(self.grid_panel.current_options())
        if tool == "crop" and 0 <= self.current_index < len(self.images):
            item = self.images[self.current_index]
            self.crop_panel.set_image_size(item.width, item.height)
            self.canvas.set_tool("crop")
            self.canvas.crop_rect = (
                self.crop_panel.left_spin.value() - item.width // 2,
                self.crop_panel.top_spin.value() - item.height // 2,
                self.crop_panel.right_spin.value() - item.width // 2,
                self.crop_panel.bottom_spin.value() - item.height // 2,
            )
            self.canvas.refresh_crop_tool()
        if tool == "brush" and 0 <= self.current_index < len(self.images):
            item = self.images[self.current_index]
            original = item.history._stack[0].image if item.history._stack else item.image
            self.canvas.start_brush_session(item.image, original)

    def _update_recent_menu(self) -> None:
        self.recent_menu.clear()
        paths = self.recent_files.get_all()
        if not paths:
            no_action = QAction("无最近文件", self)
            no_action.setEnabled(False)
            self.recent_menu.addAction(no_action)
            return

        for path_str in paths:
            action = QAction(Path(path_str).name, self)
            action.setToolTip(path_str)
            action.triggered.connect(lambda _checked, p=path_str: self._open_recent_file(p))
            self.recent_menu.addAction(action)

        self.recent_menu.addSeparator()
        clear_action = QAction("清空最近文件", self)
        clear_action.triggered.connect(self._clear_recent_files)
        self.recent_menu.addAction(clear_action)

    def _open_recent_file(self, path_str: str) -> None:
        path = Path(path_str)
        if path.is_file():
            self._load_image_items([path])
        elif path.is_dir():
            self._load_image_items(collect_images(path))
        else:
            QMessageBox.warning(self, "文件不存在", f"无法找到文件: {path_str}")

    def _clear_recent_files(self) -> None:
        self.recent_files.clear()
        self._update_recent_menu()

    def _save_project(self) -> None:
        if not self.images:
            QMessageBox.information(self, "提示", "没有可保存的内容")
            return

        directory = QFileDialog.getExistingDirectory(self, "选择项目保存位置")
        if not directory:
            return

        try:
            manager = ProjectManager()
            project = manager.project_from_items(self.images, self.current_index)
            manager.save(project, Path(directory))
            self._show_toast(f"项目已保存: {directory}")
            self.status_bar.showMessage(f"项目已保存: {directory}", 5000)
        except ProjectError as exc:
            QMessageBox.critical(self, "保存失败", str(exc))

    def _open_project(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择项目文件夹")
        if not directory:
            return

        try:
            manager = ProjectManager()
            project = manager.load(Path(directory))
            self._clear_images()
            for data in project.images:
                self.images.append(data.to_item())
            self.current_index = project.current_index
            if self.current_index < 0 or self.current_index >= len(self.images):
                self.current_index = 0 if self.images else -1
            self._show_current_image()
            self._update_status()
            self._update_navigation_buttons()
            self._update_recent_menu()
            self._show_toast(f"项目已打开: {directory}")
            self.status_bar.showMessage(f"项目已打开: {directory}", 5000)
        except ProjectError as exc:
            QMessageBox.critical(self, "打开失败", str(exc))

    def _clear_images(self) -> None:
        self.images.clear()
        self.current_index = -1
        self.canvas.clear()
        self._update_gallery()

    def _load_image_items(self, paths: list[Path]) -> None:
        new_items: list[ImageItem] = []
        for path in paths:
            try:
                image = Image.open(path).convert("RGBA")
                new_items.append(ImageItem(source_path=path, image=image))
                self.recent_files.add(path)
            except Exception as exc:
                self.status_bar.showMessage(f"无法打开 {path.name}: {exc}", 5000)

        if not new_items:
            QMessageBox.warning(self, "打开失败", "未成功加载任何图片")
            return

        self.images.extend(new_items)
        self.current_index = len(self.images) - len(new_items)
        self._show_current_image()
        self._update_status()
        self._update_navigation_buttons()
        self._update_recent_menu()
        self._update_gallery()

    def _show_current_image(self) -> None:
        if 0 <= self.current_index < len(self.images):
            self.canvas.set_image(self.images[self.current_index].image)
            self.gallery.setCurrentRow(self.current_index)
        else:
            self.canvas.clear()

    def _previous_image(self) -> None:
        if self.current_index > 0:
            self.current_index -= 1
            self._show_current_image()
            self._update_status()

    def _next_image(self) -> None:
        if self.current_index < len(self.images) - 1:
            self.current_index += 1
            self._show_current_image()
            self._update_status()

    def _on_thumbnail_clicked(self, index: int) -> None:
        if 0 <= index < len(self.images):
            self.current_index = index
            self._show_current_image()
            self._update_status()

    def _update_gallery(self) -> None:
        images = [item.image for item in self.images]
        names = [item.name for item in self.images]
        self.gallery.set_images(images, names, self.current_index)
        if self.images:
            self.gallery_hint.setText(f"已加载 {len(self.images)} 张图片")
        else:
            self.gallery_hint.setText("拖拽图片到这里显示")
        self._update_navigation_buttons()

    def _undo(self) -> None:
        if not self.images or self.current_index < 0:
            return
        item = self.images[self.current_index]
        if item.undo():
            self.canvas.set_image(item.image)
            self._show_toast(f"已撤销: {item.history.current_description}")
        else:
            self._show_toast("没有可撤销的操作")

    def _redo(self) -> None:
        if not self.images or self.current_index < 0:
            return
        item = self.images[self.current_index]
        if item.redo():
            self.canvas.set_image(item.image)
            self._show_toast(f"已重做: {item.history.current_description}")
        else:
            self._show_toast("没有可重做的操作")

    def _update_status(self) -> None:
        total = len(self.images)
        if total == 0:
            self.status_bar.showMessage("就绪 | 0 张图片")
        else:
            current = self.current_index + 1 if self.current_index >= 0 else 0
            self.status_bar.showMessage(f"就绪 | {current}/{total} 张图片")

    def _on_crop_rect_changed(self, rect: tuple[float, float, float, float]) -> None:
        layer = self.canvas.active_layer()
        if layer is None:
            return
        left = int(rect[0] - layer.x)
        top = int(rect[1] - layer.y)
        right = int(rect[2] - layer.x)
        bottom = int(rect[3] - layer.y)
        self.crop_panel.left_spin.blockSignals(True)
        self.crop_panel.top_spin.blockSignals(True)
        self.crop_panel.right_spin.blockSignals(True)
        self.crop_panel.bottom_spin.blockSignals(True)
        self.crop_panel.left_spin.setValue(max(0, left))
        self.crop_panel.top_spin.setValue(max(0, top))
        self.crop_panel.right_spin.setValue(max(0, right))
        self.crop_panel.bottom_spin.setValue(max(0, bottom))
        self.crop_panel.left_spin.blockSignals(False)
        self.crop_panel.top_spin.blockSignals(False)
        self.crop_panel.right_spin.blockSignals(False)
        self.crop_panel.bottom_spin.blockSignals(False)
        self._update_crop_size_label()

    def _on_crop_values_changed(self, options: dict[str, Any]) -> None:
        layer = self.canvas.active_layer()
        if layer is None:
            return
        box = options.get("box")
        if box is not None:
            left, top, right, bottom = box
            self.canvas.crop_rect = (left + layer.x, top + layer.y, right + layer.x, bottom + layer.y)
            self.canvas.refresh_crop_tool()

    def _update_crop_size_label(self) -> None:
        if self.canvas.crop_rect is None:
            self.crop_size_label.setText("裁剪尺寸: --")
            return
        left, top, right, bottom = self.canvas.crop_rect
        width = int(right - left)
        height = int(bottom - top)
        self.crop_size_label.setText(f"裁剪尺寸: {width}x{height}")

    def _on_cursor_moved(self, x: int, y: int) -> None:
        if x < 0 or y < 0:
            self.coord_label.setText("坐标: --, --")
            self.status_coord_label.setText("--, -- px")
        else:
            self.coord_label.setText(f"坐标: {x}, {y}")
            self.status_coord_label.setText(f"{x}, {y} px")

    def _copy_selection(self) -> None:
        self.canvas.copy_selection()
        self._show_toast("已复制选区")

    def _paste_selection(self) -> None:
        pasted = self.canvas.paste_selection()
        if pasted is not None:
            self._show_toast(f"已粘贴图层: {pasted.width}x{pasted.height}")
            self._on_canvas_image_changed(self.canvas.export_image())
            self.canvas.set_tool("move")
            self.toolbar.set_tool_checked("move")
        else:
            self._show_toast("剪贴板为空")

    def _update_navigation_buttons(self) -> None:
        total = len(self.images)
        self.prev_button.setEnabled(self.current_index > 0)
        self.next_button.setEnabled(self.current_index < total - 1)

    def _on_color_bar_zoom_changed(self, scale: float) -> None:
        self.canvas.set_zoom_scale(scale, emit=False)
        self._on_zoom_changed(scale)

    def _on_zoom_changed(self, scale: float) -> None:
        self.zoom_label.setText(f"{int(scale * 100)}%")
        self.status_zoom_label.setText(f"{int(scale * 100)}%")
        self._update_status()

    def _show_toast(self, message: str) -> None:
        toast = Toast(self, message, duration_ms=3000)
        x = self.width() - toast.width() - 20
        y = self.height() - toast.height() - 80
        toast.show_at(max(x, 20), max(y, 20))

    def _compare_current(self) -> None:
        if not self.images or self.current_index < 0:
            QMessageBox.information(self, "提示", "请先打开一张图片")
            return

        item = self.images[self.current_index]
        if not item.history._stack:
            QMessageBox.information(self, "提示", "没有原图可用于对比")
            return

        before = item.history._stack[0].image
        after = item.image
        dialog = CompareDialog(before, after, self)
        dialog.exec()

    def _slider_compare_current(self) -> None:
        if not self.images or self.current_index < 0:
            QMessageBox.information(self, "提示", "请先打开一张图片")
            return

        item = self.images[self.current_index]
        if not item.history._stack:
            QMessageBox.information(self, "提示", "没有原图可用于对比")
            return

        before = item.history._stack[0].image
        after = item.image
        dialog = SliderCompareDialog(before, after, self)
        dialog.exec()

    def _apply_editor_theme_styles(self) -> None:
        self.gallery_frame.setStyleSheet(gallery_frame_stylesheet())
        self.gallery_hint.setStyleSheet(gallery_hint_stylesheet())
        self.gallery.apply_theme_styles()
        self.color_bar.refresh_theme()
        self.toolbar.refresh_icons()
        self.prev_button.setIcon(get_icon("prev", size=20))
        self.next_button.setIcon(get_icon("next", size=20))
        self.canvas.apply_theme_styles()
        self._on_canvas_layers_changed()

    def _toggle_theme(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        apply_theme(app, self.dark_theme_action.isChecked())
        self._apply_editor_theme_styles()

    def _open_images(self) -> None:
        dialog = QFileDialog(self, "打开图片")
        dialog.setFileMode(QFileDialog.ExistingFiles)
        dialog.setNameFilter("Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)")
        if dialog.exec():
            paths = [Path(url) for url in dialog.selectedFiles()]
            self._load_image_items(paths)

    def _open_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
        if directory:
            paths = collect_images(Path(directory))
            self._load_image_items(paths)

    def _open_batch_dialog(self) -> None:
        dialog = BatchDialog(self)
        dialog.exec()

    def _export_current(self) -> None:
        if not self.images or self.current_index < 0:
            QMessageBox.information(self, "提示", "没有可导出的图片")
            return

        item = self.images[self.current_index]
        merged = self.canvas.export_image()
        if self.canvas.active_layer() is None:
            merged = item.image

        path_str, selected_filter = QFileDialog.getSaveFileName(
            self,
            "导出图片",
            str(item.source_path.with_suffix(".png")),
            "PNG (*.png);;JPEG (*.jpg);;WebP (*.webp)",
        )
        if not path_str:
            return

        try:
            fmt = "PNG" if "PNG" in selected_filter else "JPEG" if "JPEG" in selected_filter else "WEBP"
            quality = 95 if fmt in {"JPEG", "WEBP"} else -1
            export_image(merged, Path(path_str), format=fmt, quality=quality)
            self._show_toast(f"已导出: {path_str}")
            self.status_bar.showMessage(f"已导出: {path_str}", 5000)
        except EngineError as exc:
            QMessageBox.critical(self, "导出失败", str(exc))

    def _run_matting(self, options: dict[str, Any]) -> None:
        if not self.images or self.current_index < 0:
            QMessageBox.information(self, "提示", "请先打开一张图片")
            return

        model = options.get("model", "isnet-general-use")
        if not is_matting_model_available(model):
            QMessageBox.information(
                self,
                "首次下载模型",
                f"模型 {model} 首次使用，需要从网络下载。\n下载过程中界面可能无响应，请耐心等待。",
            )

        item = self.images[self.current_index]
        self._matting_item = item
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.status_bar.showMessage("正在抠图...")

        worker = MattingWorker(item.image, options)
        worker.signals.progress.connect(self.progress_bar.setValue, type=Qt.QueuedConnection)
        worker.signals.finished.connect(self._on_matting_finished, type=Qt.QueuedConnection)
        worker.signals.error.connect(self._on_matting_error, type=Qt.QueuedConnection)
        self.thread_pool.start(worker)

    def _on_matting_finished(self, result: object) -> None:
        if self._matting_item is None:
            self.progress_bar.setVisible(False)
            return
        self._matting_item.replace(result, description="抠图")
        self.canvas.set_image(result)
        self._show_toast("抠图完成")
        self.status_bar.showMessage("抠图完成", 5000)
        self.progress_bar.setVisible(False)
        self._matting_item = None

    def _on_matting_error(self, message: str) -> None:
        QMessageBox.critical(self, "抠图失败", message)
        self.progress_bar.setVisible(False)

    def _run_resize(self, options: dict[str, Any]) -> None:
        if not self.images or self.current_index < 0:
            QMessageBox.information(self, "提示", "请先打开一张图片")
            return

        from image_processor.core.image_engine import resize_image

        item = self.images[self.current_index]
        try:
            result = resize_image(
                item.image,
                width=options.get("width") or None,
                height=options.get("height") or None,
                percentage=options.get("percentage") or None,
                interpolation=options.get("interpolation", "LANCZOS"),
            )
            item.replace(result, description="缩放")
            self.canvas.set_image(result)
            self._show_toast(f"缩放完成: {result.width}x{result.height}")
            self.status_bar.showMessage(f"缩放完成: {result.width}x{result.height}", 5000)
        except EngineError as exc:
            QMessageBox.critical(self, "缩放失败", str(exc))

    def _preview_adjust(self, options: dict[str, Any]) -> None:
        if not self.images or self.current_index < 0:
            return
        image = self._apply_adjust_to_image(self.images[self.current_index].image, options)
        self.canvas.set_image(image)

    def _apply_adjust(self, options: dict[str, Any]) -> None:
        if not self.images or self.current_index < 0:
            return
        item = self.images[self.current_index]
        image = self._apply_adjust_to_image(item.image, options)
        item.replace(image, description="色彩调整")
        self.canvas.set_image(image)
        self._show_toast("色彩调整已应用")
        self.status_bar.showMessage("色彩调整已应用", 3000)

    def _apply_adjust_to_image(self, image: Image.Image, options: dict[str, Any]) -> Image.Image:
        brightness = options.get("brightness", 0)
        contrast = options.get("contrast", 0)
        saturation = options.get("saturation", 0)
        grayscale = options.get("grayscale", False)
        invert = options.get("invert", False)

        if grayscale:
            image = image.convert("L").convert("RGBA")
        elif brightness or contrast or saturation:
            from PIL import ImageEnhance

            if brightness:
                factor = 1 + (brightness / 100)
                image = ImageEnhance.Brightness(image).enhance(factor)
            if contrast:
                factor = 1 + (contrast / 100)
                image = ImageEnhance.Contrast(image).enhance(factor)
            if saturation:
                factor = 1 + (saturation / 100)
                image = ImageEnhance.Color(image).enhance(factor)

        if invert:
            from PIL import ImageOps

            image = ImageOps.invert(image.convert("RGB")).convert("RGBA")

        return image

    def _run_crop(self, options: dict[str, Any]) -> None:
        if not self.images or self.current_index < 0:
            QMessageBox.information(self, "提示", "请先打开一张图片")
            return

        from image_processor.core.image_engine import crop_image

        item = self.images[self.current_index]
        box = options.get("box") or self.canvas.get_crop_box()
        if box is None:
            QMessageBox.information(self, "提示", "请先在画布上拖拽选择裁剪区域")
            return
        try:
            result = crop_image(item.image, box=box)
            item.replace(result, description="裁剪")
            self.canvas.set_image(result)
            self.crop_panel.set_image_size(result.width, result.height)
            self._show_toast(f"裁剪完成: {result.width}x{result.height}")
            self.status_bar.showMessage(f"裁剪完成: {result.width}x{result.height}", 5000)
        except EngineError as exc:
            QMessageBox.critical(self, "裁剪失败", str(exc))

    def _run_rotate(self, options: dict[str, Any]) -> None:
        if not self.images or self.current_index < 0:
            QMessageBox.information(self, "提示", "请先打开一张图片")
            return

        from image_processor.core.image_engine import rotate_image

        item = self.images[self.current_index]
        try:
            result = rotate_image(item.image, angle=options["angle"], expand=True)
            item.replace(result, description="旋转")
            self.canvas.set_image(result)
            self.crop_panel.set_image_size(result.width, result.height)
            self._show_toast(f"旋转完成: {result.width}x{result.height}")
            self.status_bar.showMessage(f"旋转完成: {result.width}x{result.height}", 5000)
        except EngineError as exc:
            QMessageBox.critical(self, "旋转失败", str(exc))

    def _run_flip(self, options: dict[str, Any]) -> None:
        if not self.images or self.current_index < 0:
            QMessageBox.information(self, "提示", "请先打开一张图片")
            return

        from image_processor.core.image_engine import flip_image

        item = self.images[self.current_index]
        try:
            result = flip_image(item.image, horizontal=options.get("horizontal", False), vertical=options.get("vertical", False))
            item.replace(result, description="翻转")
            self.canvas.set_image(result)
            self._show_toast("翻转完成")
            self.status_bar.showMessage("翻转完成", 5000)
        except EngineError as exc:
            QMessageBox.critical(self, "翻转失败", str(exc))

    def _on_brush_applied(self, result: object) -> None:
        if not self.images or self.current_index < 0:
            return
        item = self.images[self.current_index]
        if item.image.tobytes() != result.tobytes():
            item.replace(result, description="画笔修复")
        original = item.history._stack[0].image if item.history._stack else item.image
        self.canvas.start_brush_session(item.image, original)
        self._show_toast("画笔修复已应用")
        self.status_bar.showMessage("画笔修复已应用", 5000)

    def _run_inpaint(self, options: dict[str, Any]) -> None:
        if not self.images or self.current_index < 0:
            QMessageBox.information(self, "提示", "请先打开一张图片")
            return

        from image_processor.core.image_engine import inpaint_image

        item = self.images[self.current_index]
        mask_path = Path(options["mask_path"])
        try:
            result = inpaint_image(
                item.image,
                mask_path,
                radius=options.get("radius", 5),
                method=options.get("method", "NS"),
            )
            item.replace(result, description="内容感知擦除")
            self.canvas.set_image(result)
            self._show_toast("内容感知擦除完成")
            self.status_bar.showMessage("内容感知擦除完成", 5000)
        except EngineError as exc:
            QMessageBox.critical(self, "擦除失败", str(exc))

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        paths: list[Path] = []
        for url in urls:
            path = Path(url.toLocalFile())
            if path.is_file():
                paths.append(path)
            elif path.is_dir():
                paths.extend(collect_images(path))
        if paths:
            self._load_image_items(paths)

    def closeEvent(self, event: QCloseEvent) -> None:
        event.accept()
