#!/usr/bin/env python3
"""Main application window."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QAction, QCloseEvent, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from image_processor.core.image_engine import EngineError, export_image
from image_processor.core.project_manager import ProjectError, ProjectManager
from image_processor.gui.canvas import ImageCanvas
from image_processor.gui.panels.adjust_panel import AdjustPanel
from image_processor.gui.panels.brush_panel import BrushPanel
from image_processor.gui.panels.crop_panel import CropPanel
from image_processor.gui.panels.inpaint_panel import InpaintPanel
from image_processor.gui.panels.matting_panel import MattingPanel
from image_processor.gui.panels.resize_panel import ResizePanel
from image_processor.gui.panels.sprite_panel import SpritePanel
from image_processor.gui.toolbar import ToolBar
from image_processor.gui.widgets.batch_dialog import BatchDialog
from image_processor.gui.widgets.compare_dialog import CompareDialog
from image_processor.gui.widgets.matting_worker import MattingWorker
from image_processor.gui.widgets.slider_compare import SliderCompareDialog
from image_processor.gui.widgets.toast import Toast
from image_processor.models.image_item import ImageItem
from image_processor.utils.helpers import collect_images, is_matting_model_available
from image_processor.utils.recent_files import RecentFilesManager
from image_processor.utils.themes import apply_theme


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

        self._build_ui()
        self._connect_signals()
        self._update_status()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(0)

        self.toolbar = ToolBar()
        content_layout.addWidget(self.toolbar)

        self.splitter = QSplitter(Qt.Horizontal)
        content_layout.addWidget(self.splitter, 1)

        self.canvas = ImageCanvas()
        self.splitter.addWidget(self.canvas)

        self.panel_stack = QStackedWidget()
        self.panel_stack.setMinimumWidth(260)
        self.panel_stack.setMaximumWidth(360)

        self.matting_panel = MattingPanel()
        self.resize_panel = ResizePanel()
        self.crop_panel = CropPanel()
        self.inpaint_panel = InpaintPanel()
        self.brush_panel = BrushPanel()
        self.sprite_panel = SpritePanel()
        self.adjust_panel = AdjustPanel()

        self.panel_stack.addWidget(self.matting_panel)
        self.panel_stack.addWidget(self.resize_panel)
        self.panel_stack.addWidget(self.crop_panel)
        self.panel_stack.addWidget(self.inpaint_panel)
        self.panel_stack.addWidget(self.brush_panel)
        self.panel_stack.addWidget(self.sprite_panel)
        self.panel_stack.addWidget(self.adjust_panel)

        self.splitter.addWidget(self.panel_stack)
        self.splitter.setSizes([700, 260])

        main_layout.addLayout(content_layout, 1)

        bottom_panel = QWidget()
        bottom_panel.setMaximumHeight(120)
        bottom_layout = QHBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(8, 4, 8, 4)
        bottom_layout.setSpacing(8)

        self.prev_button = QPushButton("< 上一张")
        self.prev_button.setEnabled(False)
        self.prev_button.clicked.connect(self._previous_image)
        bottom_layout.addWidget(self.prev_button)

        self.next_button = QPushButton("下一张 >")
        self.next_button.setEnabled(False)
        self.next_button.clicked.connect(self._next_image)
        bottom_layout.addWidget(self.next_button)

        self.thumbnail_list = QListWidget()
        self.thumbnail_list.setFlow(QListWidget.LeftToRight)
        self.thumbnail_list.setWrapping(False)
        self.thumbnail_list.itemClicked.connect(self._on_thumbnail_clicked)
        bottom_layout.addWidget(self.thumbnail_list, 1)

        self.zoom_reset_button = QPushButton("适应窗口")
        self.zoom_reset_button.clicked.connect(self.canvas.reset_zoom)
        bottom_layout.addWidget(self.zoom_reset_button)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(50)
        bottom_layout.addWidget(self.zoom_label)

        main_layout.addWidget(bottom_panel)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)

        self.status_bar = QStatusBar()
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.setStatusBar(self.status_bar)

        self._build_menu()

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
        self.dark_theme_action.setChecked(False)
        self.dark_theme_action.triggered.connect(self._toggle_theme)
        view_menu.addAction(self.dark_theme_action)

    def _connect_signals(self) -> None:
        self.toolbar.tool_selected.connect(self._on_tool_selected)
        self.matting_panel.request_matting.connect(self._run_matting)
        self.resize_panel.request_resize.connect(self._run_resize)
        self.crop_panel.request_crop.connect(self._run_crop)
        self.crop_panel.request_rotate.connect(self._run_rotate)
        self.crop_panel.request_flip.connect(self._run_flip)
        self.inpaint_panel.request_inpaint.connect(self._run_inpaint)
        self.brush_panel.brush_mode_changed.connect(self.canvas.set_brush_mode)
        self.brush_panel.brush_size_changed.connect(self.canvas.set_brush_size)
        self.brush_panel.brush_hardness_changed.connect(self.canvas.set_brush_hardness)
        self.brush_panel.apply_brush.connect(self.canvas.apply_brush)
        self.brush_panel.cancel_brush.connect(self.canvas.cancel_brush)
        self.canvas.brush_applied.connect(self._on_brush_applied)
        self.sprite_panel.request_sprite.connect(self._run_sprite)
        self.adjust_panel.adjustment_preview.connect(self._preview_adjust)
        self.adjust_panel.adjustment_applied.connect(self._apply_adjust)
        self.canvas.zoom_changed.connect(self._on_zoom_changed)

    def _on_tool_selected(self, tool: str) -> None:
        mapping = {
            "matting": 0,
            "resize": 1,
            "crop": 2,
            "inpaint": 3,
            "brush": 4,
            "sprite": 5,
            "adjust": 6,
        }
        self.panel_stack.setCurrentIndex(mapping.get(tool, 0))
        if tool == "sprite":
            self.sprite_panel.set_images([item.source_path for item in self.images])
        if tool == "crop" and 0 <= self.current_index < len(self.images):
            item = self.images[self.current_index]
            self.crop_panel.set_image_size(item.width, item.height)
        if tool == "brush" and 0 <= self.current_index < len(self.images):
            item = self.images[self.current_index]
            original = item.history._stack[0].image if item.history._stack else item.image
            self.canvas.start_brush_session(item.image, original)
            self.canvas.set_brush_mode(self.brush_panel.current_mode())
        else:
            self.canvas.set_brush_mode(None)

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
                self.thumbnail_list.addItem(data.source_path.name)
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
        self.thumbnail_list.clear()
        self.current_index = -1
        self.canvas.clear()

    def _load_image_items(self, paths: list[Path]) -> None:
        new_items: list[ImageItem] = []
        for path in paths:
            try:
                from PIL import Image

                image = Image.open(path).convert("RGBA")
                new_items.append(ImageItem(source_path=path, image=image))
                self.recent_files.add(path)
            except Exception as exc:
                self.status_bar.showMessage(f"无法打开 {path.name}: {exc}", 5000)

        if not new_items:
            QMessageBox.warning(self, "打开失败", "未成功加载任何图片")
            return

        self.images.extend(new_items)
        for item in new_items:
            self.thumbnail_list.addItem(item.name)
        self.current_index = len(self.images) - len(new_items)
        self._show_current_image()
        self._update_status()
        self._update_navigation_buttons()
        self._update_recent_menu()

    def _show_current_image(self) -> None:
        if 0 <= self.current_index < len(self.images):
            self.canvas.set_image(self.images[self.current_index].image)
            self.thumbnail_list.setCurrentRow(self.current_index)
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

    def _on_thumbnail_clicked(self) -> None:
        row = self.thumbnail_list.currentRow()
        if 0 <= row < len(self.images):
            self.current_index = row
            self._show_current_image()
            self._update_status()

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
            self.status_bar.showMessage(f"就绪 | {current}/{total} 张图片 | 缩放 {int(self.canvas.transform().m11() * 100)}%")

    def _update_navigation_buttons(self) -> None:
        total = len(self.images)
        self.prev_button.setEnabled(self.current_index > 0)
        self.next_button.setEnabled(self.current_index < total - 1)

    def _on_zoom_changed(self, scale: float) -> None:
        self.zoom_label.setText(f"{int(scale * 100)}%")
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

    def _toggle_theme(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        apply_theme(app, self.dark_theme_action.isChecked())

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
            export_image(item.image, Path(path_str), format=fmt, quality=quality)
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
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.status_bar.showMessage("正在抠图...")

        worker = MattingWorker(item.image, options)
        worker.signals.progress.connect(self.progress_bar.setValue)
        worker.signals.finished.connect(lambda result: self._on_matting_finished(item, result))
        worker.signals.error.connect(lambda message: self._on_matting_error(message))
        self.thread_pool.start(worker)

    def _on_matting_finished(self, item: ImageItem, result: object) -> None:
        item.replace(result, description="抠图")
        self.canvas.set_image(result)
        self._show_toast("抠图完成")
        self.status_bar.showMessage("抠图完成", 5000)
        self.progress_bar.setVisible(False)

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

    def _run_sprite(self, options: dict[str, Any]) -> None:
        from image_processor.core.image_engine import create_sprite_sheet, export_image

        paths = [Path(p) for p in options.get("paths", [])]
        if not paths:
            QMessageBox.information(self, "提示", "请选择图片文件夹")
            return

        try:
            sprite, frames = create_sprite_sheet(
                paths,
                cols=options.get("cols") or None,
                spacing=options.get("spacing", 0),
                padding=options.get("padding", 0),
                sort_by="name",
            )
            output_path = Path(options["output_path"])
            export_image(sprite, output_path, format="PNG")
            if options.get("json_path"):
                json_path = Path(options["json_path"])
                json_path.parent.mkdir(parents=True, exist_ok=True)
                import json

                metadata = {
                    "frames": frames,
                    "meta": {
                        "version": "1.0",
                        "size": {"w": sprite.width, "h": sprite.height},
                        "image": output_path.name,
                    },
                }
                json_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            self.canvas.set_image(sprite)
            self._show_toast(f"精灵图已生成: {output_path}")
            self.status_bar.showMessage(f"精灵图已生成: {output_path}", 5000)
        except EngineError as exc:
            QMessageBox.critical(self, "精灵图生成失败", str(exc))

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
        try:
            result = crop_image(item.image, box=options["box"])
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
        item.replace(result, description="画笔修复")
        self.canvas.set_image(result)
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
