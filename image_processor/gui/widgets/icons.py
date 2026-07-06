#!/usr/bin/env python3
"""Self-drawn tool icons used throughout the GUI."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from image_processor.utils.themes import icon_color, is_dark_mode


ASSETS_DIR = Path(__file__).resolve().parents[3] / "assets"

# Always load from bundled SVG assets (never hand-drawn fallbacks).
NATIVE_SVG_ICONS = frozenset({"eyedropper", "paint_bucket"})


ICON_SIZE = 24


def _palette_color() -> QColor:
    app = QApplication.instance()
    if app is None:
        return QColor("#333333")
    return QColor(app.palette().text().color())


def _base_pixmap(size: int, color: QColor) -> tuple[QPixmap, QPainter]:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(color)
    pen.setWidth(2)
    pen.setJoinStyle(Qt.RoundJoin)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    return pixmap, painter


def _icon_from_painter(name: str, size: int, color: QColor) -> QIcon:
    pixmap, painter = _base_pixmap(size, color)
    painter.setBrush(Qt.NoBrush)
    margin = size * 0.1
    rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)

    if name == "matting":
        painter.drawEllipse(rect)
        painter.drawLine(int(size * 0.75), int(size * 0.25), int(size * 0.9), int(size * 0.1))
        painter.drawLine(int(size * 0.75), int(size * 0.1), int(size * 0.9), int(size * 0.1))
        painter.drawLine(int(size * 0.9), int(size * 0.1), int(size * 0.9), int(size * 0.25))

    elif name == "resize":
        painter.drawRect(rect)
        painter.drawLine(int(size * 0.35), int(size * 0.65), int(size * 0.15), int(size * 0.85))
        painter.drawLine(int(size * 0.65), int(size * 0.35), int(size * 0.85), int(size * 0.15))

    elif name == "crop":
        lw = 2
        m = margin + 1
        painter.drawLine(int(m), int(m), int(size * 0.35), int(m))
        painter.drawLine(int(m), int(m), int(m), int(size * 0.35))
        painter.drawLine(int(size - m), int(size - m), int(size * 0.65), int(size - m))
        painter.drawLine(int(size - m), int(size - m), int(size - m), int(size * 0.65))

    elif name == "inpaint":
        painter.drawEllipse(rect)
        painter.drawLine(int(size * 0.5), int(size * 0.3), int(size * 0.5), int(size * 0.7))
        painter.drawLine(int(size * 0.3), int(size * 0.5), int(size * 0.7), int(size * 0.5))

    elif name == "brush":
        painter.drawLine(int(size * 0.2), int(size * 0.85), int(size * 0.75), int(size * 0.3))
        painter.setBrush(color)
        painter.drawEllipse(int(size * 0.75), int(size * 0.25), int(size * 0.2), int(size * 0.2))

    elif name == "eraser":
        painter.drawRect(rect.adjusted(2, -2, -2, 2))
        painter.drawLine(int(size * 0.25), int(size * 0.75), int(size * 0.75), int(size * 0.25))

    elif name == "rect_select":
        pen = painter.pen()
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.drawRect(rect)

    elif name == "free_select":
        polygon = [
            QPointF(size * 0.2, size * 0.3),
            QPointF(size * 0.5, size * 0.15),
            QPointF(size * 0.8, size * 0.3),
            QPointF(size * 0.75, size * 0.7),
            QPointF(size * 0.4, size * 0.85),
            QPointF(size * 0.25, size * 0.6),
        ]
        pen = painter.pen()
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.drawPolygon(polygon)

    elif name == "clone_stamp":
        painter.drawRect(rect)
        painter.drawLine(int(size * 0.2), int(size * 0.8), int(size * 0.8), int(size * 0.2))
        painter.drawEllipse(int(size * 0.6), int(size * 0.6), int(size * 0.2), int(size * 0.2))

    elif name == "move":
        cx = size * 0.5
        cy = size * 0.5
        painter.drawLine(int(cx), int(size * 0.15), int(cx), int(size * 0.85))
        painter.drawLine(int(size * 0.15), int(cy), int(size * 0.85), int(cy))
        painter.drawLine(int(cx), int(size * 0.15), int(cx - 2), int(size * 0.22))
        painter.drawLine(int(cx), int(size * 0.15), int(cx + 2), int(size * 0.22))
        painter.drawLine(int(cx), int(size * 0.85), int(cx - 2), int(size * 0.78))
        painter.drawLine(int(cx), int(size * 0.85), int(cx + 2), int(size * 0.78))
        painter.drawLine(int(size * 0.15), int(cy), int(size * 0.22), int(cy - 2))
        painter.drawLine(int(size * 0.15), int(cy), int(size * 0.22), int(cy + 2))
        painter.drawLine(int(size * 0.85), int(cy), int(size * 0.78), int(cy - 2))
        painter.drawLine(int(size * 0.85), int(cy), int(size * 0.78), int(cy + 2))

    elif name == "grid":
        for i in range(1, 4):
            x = margin + i * (size - 2 * margin) / 4
            y = margin + i * (size - 2 * margin) / 4
            painter.drawLine(int(x), int(margin), int(x), int(size - margin))
            painter.drawLine(int(margin), int(y), int(size - margin), int(y))

    elif name == "sprite":
        w = (size - 2 * margin) / 2
        h = (size - 2 * margin) / 2
        for r in range(2):
            for c in range(2):
                painter.drawRect(
                    QRectF(
                        margin + c * w,
                        margin + r * h,
                        w - 1,
                        h - 1,
                    )
                )

    elif name == "adjust":
        painter.drawLine(int(size * 0.25), int(size * 0.35), int(size * 0.25), int(size * 0.65))
        painter.drawLine(int(size * 0.5), int(size * 0.25), int(size * 0.5), int(size * 0.75))
        painter.drawLine(int(size * 0.75), int(size * 0.4), int(size * 0.75), int(size * 0.6))
        painter.setBrush(color)
        painter.drawEllipse(int(size * 0.22), int(size * 0.35), int(size * 0.06), int(size * 0.06))
        painter.drawEllipse(int(size * 0.47), int(size * 0.65), int(size * 0.06), int(size * 0.06))
        painter.drawEllipse(int(size * 0.72), int(size * 0.45), int(size * 0.06), int(size * 0.06))

    elif name == "prev":
        painter.drawLine(int(size * 0.7), int(size * 0.2), int(size * 0.3), int(size * 0.5))
        painter.drawLine(int(size * 0.3), int(size * 0.5), int(size * 0.7), int(size * 0.8))

    elif name == "next":
        painter.drawLine(int(size * 0.3), int(size * 0.2), int(size * 0.7), int(size * 0.5))
        painter.drawLine(int(size * 0.7), int(size * 0.5), int(size * 0.3), int(size * 0.8))

    elif name == "new_layer":
        painter.drawRect(rect)
        painter.drawLine(int(size * 0.5), int(margin + 3), int(size * 0.5), int(size - margin - 3))
        painter.drawLine(int(margin + 3), int(size * 0.5), int(size - margin - 3), int(size * 0.5))

    elif name == "delete_layer":
        painter.drawLine(int(size * 0.25), int(size * 0.25), int(size * 0.75), int(size * 0.75))
        painter.drawLine(int(size * 0.75), int(size * 0.25), int(size * 0.25), int(size * 0.75))

    elif name == "visibility":
        painter.drawEllipse(int(size * 0.35), int(size * 0.4), int(size * 0.3), int(size * 0.2))
        painter.drawArc(rect, int(-30 * 16), int(240 * 16))

    elif name == "layer":
        painter.drawRect(rect)
        painter.drawRect(rect.adjusted(3, -3, -3, 3))

    elif name == "swap":
        painter.drawLine(int(size * 0.2), int(size * 0.8), int(size * 0.5), int(size * 0.5))
        painter.drawLine(int(size * 0.5), int(size * 0.5), int(size * 0.8), int(size * 0.8))
        painter.drawLine(int(size * 0.5), int(size * 0.5), int(size * 0.3), int(size * 0.45))
        painter.drawLine(int(size * 0.5), int(size * 0.5), int(size * 0.55), int(size * 0.3))
        painter.drawLine(int(size * 0.5), int(size * 0.5), int(size * 0.7), int(size * 0.55))
        painter.drawLine(int(size * 0.5), int(size * 0.5), int(size * 0.45), int(size * 0.7))

    else:
        painter.drawRect(rect)

    painter.end()
    return QIcon(pixmap)


def _tint_pixmap(pixmap: QPixmap, color: QColor) -> QPixmap:
    tinted = QPixmap(pixmap.size())
    tinted.fill(Qt.transparent)
    painter = QPainter(tinted)
    painter.drawPixmap(0, 0, pixmap)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(), color)
    painter.end()
    return tinted


def get_icon(name: str, size: int = ICON_SIZE, color: QColor | None = None) -> QIcon:
    """Return a generated icon for the requested tool/action."""
    if name in NATIVE_SVG_ICONS and (ASSETS_DIR / f"{name}.svg").is_file():
        return get_svg_icon(name, size=size)
    if color is None:
        color = _palette_color()
    return _icon_from_painter(name, size, color)


def get_svg_icon(name: str, size: int = ICON_SIZE) -> QIcon:
    """Return an SVG icon from the assets folder, falling back to a generated icon."""
    path = ASSETS_DIR / f"{name}.svg"
    if not path.is_file():
        return _icon_from_painter(name, size, _palette_color())
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer = QSvgRenderer(str(path))
    if not renderer.isValid():
        painter.end()
        return _icon_from_painter(name, size, _palette_color())
    renderer.setAspectRatioMode(Qt.KeepAspectRatio)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    if is_dark_mode():
        pixmap = _tint_pixmap(pixmap, QColor(icon_color()))
    return QIcon(pixmap)
