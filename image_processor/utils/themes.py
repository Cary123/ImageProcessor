#!/usr/bin/env python3
"""Theme stylesheets for the application."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

LIGHT_STYLE = """
QMainWindow, QDialog {
    background-color: #F9FAFB;
    color: #111827;
}
QPushButton {
    background-color: #E5E7EB;
    color: #111827;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    padding: 6px 12px;
}
QPushButton:hover {
    background-color: #D1D5DB;
}
QLineEdit, QSpinBox, QComboBox, QTextEdit {
    background-color: #FFFFFF;
    color: #111827;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    padding: 4px;
}
QListWidget {
    background-color: #FFFFFF;
    color: #111827;
    border: 1px solid #D1D5DB;
}
QMenuBar, QMenu {
    background-color: #FFFFFF;
    color: #111827;
}
QStatusBar {
    background-color: #F3F4F6;
    color: #111827;
}
QLabel {
    color: #111827;
}
"""

DARK_STYLE = """
QMainWindow, QDialog {
    background-color: #1F2937;
    color: #F9FAFB;
}
QPushButton {
    background-color: #374151;
    color: #F9FAFB;
    border: 1px solid #4B5563;
    border-radius: 4px;
    padding: 6px 12px;
}
QPushButton:hover {
    background-color: #4B5563;
}
QLineEdit, QSpinBox, QComboBox, QTextEdit {
    background-color: #111827;
    color: #F9FAFB;
    border: 1px solid #4B5563;
    border-radius: 4px;
    padding: 4px;
}
QListWidget {
    background-color: #111827;
    color: #F9FAFB;
    border: 1px solid #4B5563;
}
QMenuBar, QMenu {
    background-color: #1F2937;
    color: #F9FAFB;
}
QStatusBar {
    background-color: #111827;
    color: #F9FAFB;
}
QLabel {
    color: #F9FAFB;
}
"""


def apply_theme(app: QApplication, dark: bool) -> None:
    """Apply a light or dark stylesheet to the application."""
    app.setStyleSheet(DARK_STYLE if dark else LIGHT_STYLE)
