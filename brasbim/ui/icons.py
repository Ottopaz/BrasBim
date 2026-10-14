# SPDX-License-Identifier: GPL-3.0-or-later
"""Ícones próprios do BrasBim (``spec/ui/03-barras-e-icones.md`` §3).

Os SVG de ``icons/`` usam ``currentColor``; aqui a cor é trocada pela do texto do tema
(e pela de destaque no estado marcado) antes de desenhar.
"""

from __future__ import annotations

import math
from functools import cache
from pathlib import Path

from PySide6.QtCore import QByteArray, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QIcon,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
)
from PySide6.QtSvg import QSvgRenderer

ICON_DIR = Path(__file__).parent / "icons"
_SIZES = (16, 24, 32, 48)


def names() -> list[str]:
    return sorted(p.stem for p in ICON_DIR.glob("*.svg"))


def _pixmap(svg: str, color: str, size: int) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(svg.replace("currentColor", color).encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return pixmap


@cache
def icon(name: str) -> QIcon:
    svg = (ICON_DIR / f"{name}.svg").read_text(encoding="utf-8")
    palette = QGuiApplication.palette()
    normal = palette.color(QPalette.WindowText).name()
    accent = palette.color(QPalette.Highlight).name()
    disabled = palette.color(QPalette.Disabled, QPalette.WindowText).name()
    result = QIcon()
    for size in _SIZES:
        result.addPixmap(_pixmap(svg, normal, size), QIcon.Normal, QIcon.Off)
        result.addPixmap(_pixmap(svg, accent, size), QIcon.Normal, QIcon.On)
        result.addPixmap(_pixmap(svg, disabled, size), QIcon.Disabled, QIcon.Off)
    return result


def swatch(style: dict, width: int = 36, height: int = 14) -> QPixmap:
    """Amostra da representação de um tipo de parede (spec/ui 03 §6): faixa com o
    preenchimento e a linha de contorno."""
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    rect = QRectF(1, 2, width - 2, height - 4)
    path = QPainterPath()
    path.addRect(rect)
    if style["fill"] == "solid":
        painter.fillPath(path, QColor(style["fill_color"]))
    elif style["fill"] == "hatch":
        painter.save()
        painter.setClipPath(path)
        painter.setPen(QPen(QColor(style["fill_color"]).darker(130), 1))
        angle = -math.radians(style["hatch_angle"])
        d = QPointF(math.cos(angle), math.sin(angle))
        n = QPointF(-d.y(), d.x())
        for k in range(-12, 13):
            o = rect.center() + n * (k * 4)
            painter.drawLine(o - d * width, o + d * width)
        painter.restore()
    painter.setPen(QPen(QColor(style["line_color"]),
                        max(1.0, style["line_weight"] * 1000 * 96 / 25.4)))
    painter.drawRect(rect)
    painter.end()
    return pixmap


def icon_from(pixmap: QPixmap) -> QIcon:
    return QIcon(pixmap)
