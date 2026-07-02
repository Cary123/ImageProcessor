#!/usr/bin/env python3
"""Batch processing dialog with progress and cancel."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from image_processor.core.batch_processor import BatchProcessor, BatchResult
from image_processor.core.image_engine import InterpolationMode
from image_processor.utils.helpers import collect_images


class WorkerSignals(QObject):
    """Signals for batch worker."""

    progress = Signal(int, int)
    log = Signal(str)
    finished = Signal(list)


class BatchWorker(QRunnable):
    """Runs batch processing in a thread pool."""

    def __init__(
        self,
        paths: list[Path],
        output_dir: Path,
        *,
        matting: bool,
        percentage: int,
        quality: int,
    ) -> None:
        super().__init__()
        self.paths = paths
        self.output_dir = output_dir
        self.matting = matting
        self.percentage = percentage
        self.quality = quality
        self.signals = WorkerSignals()
        self._processor = BatchProcessor()

    def run(self) -> None:
        def progress_callback(current: int, total: int) -> None:
            self.signals.progress.emit(current, total)

        if self.matting:
            results = self._processor.process_matting(
                self.paths, self.output_dir, progress_callback=progress_callback
            )
        else:
            results = self._processor.process_resize(
                self.paths,
                self.output_dir,
                percentage=self.percentage,
                quality=self.quality,
                interpolation=InterpolationMode.LANCZOS,
                progress_callback=progress_callback,
            )
        self.signals.finished.emit(results)

    def cancel(self) -> None:
        self._processor.cancel()


class BatchDialog(QDialog):
    """Dialog for batch matting or resize operations."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("批量处理")
        self.setMinimumSize(500, 400)

        self._worker: BatchWorker | None = None
        self._cancelled = False

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        input_layout = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("选择输入文件夹")
        self.input_edit.setReadOnly(True)
        input_layout.addWidget(self.input_edit)
        self.input_button = QPushButton("浏览...")
        self.input_button.clicked.connect(self._browse_input)
        input_layout.addWidget(self.input_button)
        layout.addLayout(input_layout)

        output_layout = QHBoxLayout()
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("选择输出文件夹")
        self.output_edit.setReadOnly(True)
        output_layout.addWidget(self.output_edit)
        self.output_button = QPushButton("浏览...")
        self.output_button.clicked.connect(self._browse_output)
        output_layout.addWidget(self.output_button)
        layout.addLayout(output_layout)

        operation_layout = QHBoxLayout()
        self.matting_radio = QRadioButton("批量抠图")
        self.resize_radio = QRadioButton("批量缩放")
        self.matting_radio.setChecked(True)
        operation_layout.addWidget(self.matting_radio)
        operation_layout.addWidget(self.resize_radio)
        operation_layout.addStretch()
        layout.addLayout(operation_layout)

        resize_layout = QHBoxLayout()
        self.resize_percentage_spin = QSpinBox()
        self.resize_percentage_spin.setRange(1, 500)
        self.resize_percentage_spin.setValue(50)
        self.resize_percentage_spin.setSuffix(" %")
        resize_layout.addWidget(QLabel("百分比:"))
        resize_layout.addWidget(self.resize_percentage_spin)

        self.resize_quality_spin = QSpinBox()
        self.resize_quality_spin.setRange(1, 100)
        self.resize_quality_spin.setValue(95)
        self.resize_quality_spin.setSuffix(" %")
        resize_layout.addWidget(QLabel("质量:"))
        resize_layout.addWidget(self.resize_quality_spin)
        resize_layout.addStretch()
        layout.addLayout(resize_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("处理日志...")
        layout.addWidget(self.log_text, 1)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.run_button = QPushButton("开始")
        self.run_button.setStyleSheet("background-color: #3B82F6; color: white; padding: 6px;")
        self.run_button.setMinimumWidth(80)
        self.run_button.clicked.connect(self._run)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self._cancel)
        self.cancel_button.setEnabled(False)
        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.reject)
        button_layout.addWidget(self.run_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)

    def _browse_input(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择输入文件夹")
        if directory:
            self.input_edit.setText(directory)
            if not self.output_edit.text():
                self.output_edit.setText(str(Path(directory) / "output"))

    def _browse_output(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if directory:
            self.output_edit.setText(directory)

    @Slot(str)
    def _log(self, message: str) -> None:
        self.log_text.append(message)

    @Slot(int, int)
    def _on_progress(self, current: int, total: int) -> None:
        if total > 0:
            self.progress_bar.setValue(int(current * 100 / total))

    @Slot(list)
    def _on_finished(self, results: list[BatchResult]) -> None:
        success_count = sum(1 for r in results if r.success)
        self._log(f"完成：成功 {success_count}/{len(results)}")
        for result in results:
            if result.success:
                self._log(f"  ✓ {result.source.name} -> {result.output}")
            else:
                self._log(f"  ✗ {result.source.name}: {result.message}")
        self.progress_bar.setValue(100 if not self._cancelled else 0)
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def _run(self) -> None:
        input_dir = Path(self.input_edit.text()) if self.input_edit.text() else None
        output_dir = Path(self.output_edit.text()) if self.output_edit.text() else None

        if not input_dir or not input_dir.is_dir():
            self._log("错误：请选择有效的输入文件夹")
            return
        if not output_dir:
            self._log("错误：请选择输出文件夹")
            return

        paths = collect_images(input_dir)
        if not paths:
            self._log("错误：输入文件夹中没有支持的图片")
            return

        self._cancelled = False
        self.run_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self._log(f"开始处理 {len(paths)} 张图片...")

        self._worker = BatchWorker(
            paths,
            output_dir,
            matting=self.matting_radio.isChecked(),
            percentage=self.resize_percentage_spin.value(),
            quality=self.resize_quality_spin.value(),
        )
        self._worker.signals.progress.connect(self._on_progress)
        self._worker.signals.log.connect(self._log)
        self._worker.signals.finished.connect(self._on_finished)
        QThreadPool.globalInstance().start(self._worker)

    def _cancel(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self._cancelled = True
            self._log("已请求取消...")
