#!/usr/bin/env python3
"""Application bootstrap."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from image_processor.gui.main_window import MainWindow


def create_application(argv: list[str] | None = None) -> QApplication:
    if argv is None:
        argv = sys.argv
    app = QApplication(argv)
    app.setApplicationName("ImageProcessor")
    app.setApplicationDisplayName("ImageProcessor")
    app.setOrganizationName("ImageProcessor")
    return app


def run() -> int:
    app = create_application()
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
