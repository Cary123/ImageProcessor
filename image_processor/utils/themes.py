#!/usr/bin/env python3
"""Theme stylesheets for the application."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

# Shared palette tokens
DARK_BG = "#2B2B2B"
DARK_BG_SECONDARY = "#333333"
DARK_BG_ELEVATED = "#3D3D3D"
DARK_BORDER = "#555555"
DARK_BORDER_SUBTLE = "#484848"
DARK_TEXT = "#E8E8E8"
DARK_TEXT_MUTED = "#A0A0A0"
DARK_ACCENT = "#3B82F6"
DARK_SELECTION_BG = "#404040"
DARK_HOVER = "#4A4A4A"

LIGHT_BG = "#F9FAFB"
LIGHT_TEXT = "#111827"

_dark_mode = True


def is_dark_mode() -> bool:
    """Return whether the dark theme is currently active."""
    return _dark_mode


def icon_color() -> str:
    """Return the preferred monochrome icon tint for the active theme."""
    return DARK_TEXT if _dark_mode else "#333333"


LIGHT_STYLE = """
QMainWindow, QDialog, QWidget {
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
QPushButton[toolButton="true"] {
    background-color: transparent;
    border: none;
    padding: 0px;
    margin: 0px;
}
QPushButton[toolButton="true"]:hover {
    background-color: rgba(0, 0, 0, 0.06);
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
QListWidget::item:selected {
    background-color: #DBEAFE;
    color: #111827;
}
QMenuBar, QMenu {
    background-color: #FFFFFF;
    color: #111827;
}
QMenu::item:selected {
    background-color: #E5E7EB;
}
QStatusBar {
    background-color: #F3F4F6;
    color: #111827;
}
QLabel {
    color: #111827;
}
QTabWidget::pane {
    border: none;
    background-color: #F9FAFB;
}
QTabBar::tab {
    background-color: #E5E7EB;
    color: #374151;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #F9FAFB;
    color: #111827;
}
QSplitter::handle {
    background-color: #D1D5DB;
}
QScrollBar:vertical {
    background: #F3F4F6;
    width: 10px;
}
QScrollBar::handle:vertical {
    background: #9CA3AF;
    border-radius: 4px;
    min-height: 24px;
}
QSlider::groove:horizontal {
    background: #D1D5DB;
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #3B82F6;
    width: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QProgressBar {
    background-color: #E5E7EB;
    border: none;
    border-radius: 4px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #3B82F6;
    border-radius: 4px;
}
"""

DARK_STYLE = f"""
QMainWindow, QDialog, QWidget {{
    background-color: {DARK_BG};
    color: {DARK_TEXT};
}}
QPushButton {{
    background-color: {DARK_BG_ELEVATED};
    color: {DARK_TEXT};
    border: 1px solid {DARK_BORDER};
    border-radius: 4px;
    padding: 6px 12px;
}}
QPushButton:hover {{
    background-color: {DARK_HOVER};
}}
QPushButton:disabled {{
    background-color: {DARK_BG_SECONDARY};
    color: {DARK_TEXT_MUTED};
    border-color: {DARK_BORDER_SUBTLE};
}}
QPushButton[toolButton="true"] {{
    background-color: transparent;
    border: none;
    padding: 0px;
    margin: 0px;
}}
QPushButton[toolButton="true"]:hover {{
    background-color: rgba(255, 255, 255, 0.08);
}}
QLineEdit, QSpinBox, QComboBox, QTextEdit {{
    background-color: {DARK_BG_SECONDARY};
    color: {DARK_TEXT};
    border: 1px solid {DARK_BORDER};
    border-radius: 4px;
    padding: 4px;
    selection-background-color: {DARK_ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    background: {DARK_BG_ELEVATED};
}}
QComboBox QAbstractItemView {{
    background-color: {DARK_BG_ELEVATED};
    color: {DARK_TEXT};
    border: 1px solid {DARK_BORDER};
    selection-background-color: {DARK_ACCENT};
}}
QListWidget {{
    background-color: {DARK_BG_SECONDARY};
    color: {DARK_TEXT};
    border: 1px solid {DARK_BORDER};
    outline: none;
}}
QListWidget::item {{
    padding: 4px;
    border-radius: 4px;
}}
QListWidget::item:selected {{
    background-color: {DARK_SELECTION_BG};
    color: {DARK_TEXT};
    border: 1px solid {DARK_ACCENT};
}}
QListWidget::item:hover {{
    background-color: {DARK_HOVER};
}}
QMenuBar {{
    background-color: {DARK_BG};
    color: {DARK_TEXT};
    border-bottom: 1px solid {DARK_BORDER_SUBTLE};
}}
QMenuBar::item:selected {{
    background-color: {DARK_BG_ELEVATED};
}}
QMenu {{
    background-color: {DARK_BG_ELEVATED};
    color: {DARK_TEXT};
    border: 1px solid {DARK_BORDER};
}}
QMenu::item:selected {{
    background-color: {DARK_ACCENT};
    color: white;
}}
QStatusBar {{
    background-color: {DARK_BG_SECONDARY};
    color: {DARK_TEXT_MUTED};
    border-top: 1px solid {DARK_BORDER_SUBTLE};
}}
QLabel {{
    color: {DARK_TEXT};
}}
QTabWidget::pane {{
    border: none;
    background-color: {DARK_BG};
}}
QTabBar::tab {{
    background-color: {DARK_BG_SECONDARY};
    color: {DARK_TEXT_MUTED};
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background-color: {DARK_BG_ELEVATED};
    color: {DARK_TEXT};
}}
QTabBar::tab:hover {{
    background-color: {DARK_HOVER};
}}
QSplitter::handle {{
    background-color: {DARK_BORDER_SUBTLE};
}}
QScrollBar:vertical {{
    background: {DARK_BG_SECONDARY};
    width: 10px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {DARK_BORDER};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar:horizontal {{
    background: {DARK_BG_SECONDARY};
    height: 10px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: {DARK_BORDER};
    border-radius: 4px;
    min-width: 24px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0px;
    height: 0px;
}}
QSlider::groove:horizontal {{
    background: {DARK_BORDER};
    height: 4px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {DARK_ACCENT};
    width: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QProgressBar {{
    background-color: {DARK_BG_SECONDARY};
    color: {DARK_TEXT};
    border: none;
    border-radius: 4px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {DARK_ACCENT};
    border-radius: 4px;
}}
QCheckBox {{
    color: {DARK_TEXT};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {DARK_BORDER};
    border-radius: 3px;
    background: {DARK_BG_SECONDARY};
}}
QCheckBox::indicator:checked {{
    background: {DARK_ACCENT};
    border-color: {DARK_ACCENT};
}}
QGroupBox {{
    color: {DARK_TEXT};
    border: 1px solid {DARK_BORDER};
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 8px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}}
"""


def gallery_frame_stylesheet() -> str:
    """Stylesheet for the bottom thumbnail gallery frame."""
    if _dark_mode:
        return (
            f"QFrame {{ border: 1px solid {DARK_BORDER}; "
            f"border-radius: 6px; background: {DARK_BG_SECONDARY}; }}"
        )
    return "QFrame { border: 1px solid #D1D5DB; border-radius: 6px; background: transparent; }"


def gallery_hint_stylesheet() -> str:
    """Stylesheet for gallery hint label."""
    if _dark_mode:
        return f"color: {DARK_TEXT_MUTED}; font-size: 12px;"
    return "color: #6B7280; font-size: 12px;"


def image_gallery_stylesheet() -> str:
    """Stylesheet for the horizontal thumbnail gallery."""
    if _dark_mode:
        return f"""
            QListWidget {{
                background: transparent;
                border: none;
                padding: 10px;
            }}
            QListWidget::item {{
                margin: 0px;
                padding: 0px;
                border: 1px solid {DARK_BORDER};
                border-radius: 4px;
                background: transparent;
            }}
            QListWidget::item:selected {{
                border: 2px solid {DARK_ACCENT};
                background: {DARK_SELECTION_BG};
            }}
        """
    return """
        QListWidget {
            background: transparent;
            border: 1px solid #D1D5DB;
            border-radius: 6px;
            padding: 10px;
        }
        QListWidget::item {
            margin: 0px;
            padding: 0px;
            border: 1px solid #D1D5DB;
            border-radius: 4px;
            background: transparent;
        }
        QListWidget::item:selected {
            border: 2px solid #3B82F6;
            background: #E0F2FE;
        }
    """


def gallery_placeholder_stylesheet() -> str:
    """Stylesheet for empty gallery placeholder."""
    if _dark_mode:
        return f"""
            QLabel {{
                border: 2px dashed {DARK_BORDER};
                border-radius: 8px;
                color: {DARK_TEXT_MUTED};
                font-size: 14px;
                font-weight: bold;
                padding: 12px;
                margin: 8px;
                background: transparent;
            }}
        """
    return """
        QLabel {
            border: 2px dashed #9CA3AF;
            border-radius: 8px;
            color: #4B5563;
            font-size: 14px;
            font-weight: bold;
            padding: 12px;
            margin: 8px;
            background: transparent;
        }
    """


def color_bar_divider_stylesheet() -> str:
    """Stylesheet for the color bar vertical divider."""
    color = DARK_BORDER if _dark_mode else "#E5E7EB"
    return f"QFrame {{ background-color: {color}; border: none; }}"


def color_swatch_border() -> str:
    """Border color for color swatches."""
    return DARK_BORDER if _dark_mode else "#9CA3AF"


def color_button_border(selected: bool) -> str:
    """Border color for foreground/background color buttons."""
    if selected:
        return DARK_ACCENT
    return DARK_BORDER if _dark_mode else "#9CA3AF"


def apply_theme(app: QApplication, dark: bool) -> None:
    """Apply a light or dark stylesheet to the application."""
    global _dark_mode
    _dark_mode = dark
    app.setStyleSheet(DARK_STYLE if dark else LIGHT_STYLE)
