# SPDX-License-Identifier: GPL-3.0-or-later
"""Prévia e miniaturas de objetos paramétricos (``spec/elementos/objeto-parametrico.md``
§4.2 e §5.3).

Desenho rápido sem OpenGL: a planta mostra o símbolo 2D; o 3D projeta os triângulos de
``core.objects.mesh`` (pintor, do mais longe para o mais perto) com um sombreamento simples.
"""

from __future__ import annotations

import json
import logging
import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QWidget

from brasbim.core import materials
from brasbim.core.objects import definition as od
from brasbim.core.objects import mesh as object_mesh
from brasbim.core.objects import plan as object_plan
from brasbim.ui import theme

_LIGHT = (0.35, -0.55, 0.76)
log = logging.getLogger(__name__)


class _Built:
    """O que ``objects.plan.local_symbol`` precisa, sem gravar nada."""

    def __init__(self, defn: dict, values: dict):
        self.definition = defn
        self.values = values
        self.solids = od.solids(defn, values)
        self.strokes = od.symbol_items(defn, values)
        self.box = od.bounds(self.solids)


def _color(name: str | None) -> QColor:
    return QColor(materials.default_style(name or "")["color"]) if name else QColor(
        theme.INK_SOFT)


def _project(p, azimuth: float, elevation: float):
    a, e = math.radians(azimuth), math.radians(elevation)
    x, y, z = p
    # gira em torno de z, depois inclina: u para a direita, v para cima, w para o olho
    xr = x * math.cos(a) - y * math.sin(a)
    yr = x * math.sin(a) + y * math.cos(a)
    u = xr
    v = z * math.cos(e) + yr * math.sin(e)
    w = -yr * math.cos(e) + z * math.sin(e)
    return u, v, w


def _normal(tri):
    (x0, y0, z0), (x1, y1, z1), (x2, y2, z2) = tri
    ux, uy, uz = x1 - x0, y1 - y0, z1 - z0
    vx, vy, vz = x2 - x0, y2 - y0, z2 - z0
    n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
    length = math.sqrt(sum(c * c for c in n)) or 1.0
    return tuple(c / length for c in n)


def paint_3d(painter: QPainter, rect: QRectF, tris, azimuth: float = -35.0,
             elevation: float = 30.0, zoom: float = 1.0) -> None:
    if not tris:
        return
    projected = []
    for tri, material, part in tris:
        pts = [_project(p, azimuth, elevation) for p in tri]
        projected.append((pts, tri, material, part))
    us = [p[0] for item in projected for p in item[0]]
    vs = [p[1] for item in projected for p in item[0]]
    width, height = max(us) - min(us), max(vs) - min(vs)
    scale = zoom * 0.86 * min(rect.width() / max(width, 1e-6), rect.height() / max(height, 1e-6))
    cu, cv = (max(us) + min(us)) / 2, (max(vs) + min(vs)) / 2
    center = rect.center()

    def screen(p):
        return QPointF(center.x() + (p[0] - cu) * scale, center.y() - (p[1] - cv) * scale)

    a, e = math.radians(azimuth), math.radians(elevation)
    eye = (-math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))
    # pintor por peça: as peças mais longe primeiro; dentro da peça, só as faces de frente
    parts: dict[int, list] = {}
    for item in projected:
        parts.setdefault(item[3], []).append(item)
    order = sorted(parts.values(), key=lambda items: sum(
        p[2] for it in items for p in it[0]) / (3 * len(items)))
    for items in order:
        for pts, tri, material, _ in sorted(items, key=lambda it: sum(p[2] for p in it[0])):
            n = _normal(tri)
            if sum(n[i] * eye[i] for i in range(3)) < -1e-9:
                continue
            light = max(0.0, sum(n[i] * _LIGHT[i] for i in range(3)))
            base = _color(material)
            k = 0.58 + 0.42 * light
            color = QColor(int(base.red() * k), int(base.green() * k), int(base.blue() * k))
            painter.setPen(QPen(color, 0.8))
            painter.setBrush(QBrush(color))
            painter.drawPolygon(QPolygonF([screen(p) for p in pts]))


def paint_plan(painter: QPainter, rect: QRectF, symbol, zoom: float = 1.0) -> None:
    pts = [q for points, _, _ in symbol for q in points]
    if not pts:
        return
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    width, height = max(xs) - min(xs), max(ys) - min(ys)
    scale = zoom * 0.86 * min(rect.width() / max(width, 1e-6), rect.height() / max(height, 1e-6))
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    center = rect.center()

    def screen(p):
        return QPointF(center.x() + (p[0] - cx) * scale, center.y() - (p[1] - cy) * scale)

    for points, closed, fill in symbol:
        path = QPainterPath()
        path.moveTo(screen(points[0]))
        for p in points[1:]:
            path.lineTo(screen(p))
        if closed:
            path.closeSubpath()
        if fill and closed:
            painter.fillPath(path, QColor(theme.PAPER))
        painter.setPen(QPen(QColor(theme.INK), 1.0))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)


def symbol_of(defn: dict, values: dict, resolver=None, depth: int = 0):
    """Símbolo 2D no sistema local, com os aninhados (``resolver`` como na malha)."""
    out = object_plan.local_symbol(_Built(defn, values))
    if resolver is None or depth >= od.MAX_NESTING:
        return out
    for n in od.nested(defn, values):
        state = resolver(n.type_name)
        if state is None:
            continue
        try:
            inner = od.evaluate(state["definition"], state["values"],
                                {**state["defaults"], **n.values})
            parts = symbol_of(state["definition"], inner, resolver, depth + 1)
        except Exception as e:  # noqa: BLE001 - aninhado que não se calcula fica de fora
            log.debug("prévia sem o aninhado %s: %s", n.type_name, e)
            continue
        a = math.radians(n.rotation)
        c, sn = math.cos(a), math.sin(a)
        k = -1.0 if n.mirror else 1.0
        for points, closed, fill in parts:
            out.append(([(n.origin[0] + c * k * x - sn * y, n.origin[1] + sn * k * x + c * y)
                         for x, y in points], closed, fill))
    return out


_CACHE: dict = {}


def thumbnail(state: dict, size: int = 64, mode: str = "3d", resolver=None) -> QPixmap:
    """Miniatura de um tipo (estado de ``types.read`` ou da biblioteca)."""
    key = (state["definition"]["object_id"], state["definition"].get("version"),
           state.get("name"), json.dumps(state.get("values"), sort_keys=True), size, mode)
    if key in _CACHE:
        return _CACHE[key]
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(theme.PAPER))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    rect = QRectF(2, 2, size - 4, size - 4)
    try:
        values = od.evaluate(state["definition"], state.get("values") or {},
                             state.get("defaults") or {})
        if mode == "plan":
            paint_plan(painter, rect, symbol_of(state["definition"], values, resolver))
        else:
            paint_3d(painter, rect, object_mesh.object_mesh(state["definition"], values,
                                                            resolver))
    except Exception:  # noqa: BLE001 - definição que não se calcula fica sem miniatura
        painter.setPen(QPen(QColor(theme.ERROR), 1.2))
        painter.drawLine(rect.topLeft(), rect.bottomRight())
    painter.end()
    _CACHE[key] = pixmap
    if len(_CACHE) > 600:
        _CACHE.pop(next(iter(_CACHE)))
    return pixmap


def icon(state: dict, size: int = 48, mode: str = "3d", resolver=None) -> QIcon:
    return QIcon(thumbnail(state, size, mode, resolver))


class PreviewWidget(QWidget):
    """Prévia do editor: planta ou 3D, arrastar gira, roda aproxima."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mode = "3d"
        self.azimuth, self.elevation, self.zoom = -35.0, 28.0, 1.0
        self.tris: list = []
        self.symbol: list = []
        self.error: str | None = None
        self._drag = None
        self.setMinimumSize(QSize(260, 240))
        self.setMouseTracking(False)

    def set_content(self, tris, symbol, error: str | None = None) -> None:
        self.tris, self.symbol, self.error = tris, symbol, error
        self.update()

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(theme.PAPER))
        rect = QRectF(self.rect()).adjusted(12, 12, -12, -12)
        if self.error:
            painter.setPen(QColor(theme.ERROR))
            painter.drawText(rect, Qt.AlignCenter | Qt.TextWordWrap, self.error)
        elif self.mode == "plan":
            paint_plan(painter, rect, self.symbol, self.zoom)
        else:
            paint_3d(painter, rect, self.tris, self.azimuth, self.elevation, self.zoom)
        painter.setPen(QPen(QColor(theme.RULE), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5))
        painter.end()

    def mousePressEvent(self, event):
        self._drag = event.position()

    def mouseMoveEvent(self, event):
        if self._drag is None or self.mode != "3d":
            return
        d = event.position() - self._drag
        self._drag = event.position()
        self.azimuth = (self.azimuth - d.x() * 0.6) % 360.0
        self.elevation = max(-5.0, min(89.0, self.elevation + d.y() * 0.4))
        self.update()

    def mouseReleaseEvent(self, event):
        self._drag = None

    def wheelEvent(self, event):
        self.zoom = max(0.3, min(6.0, self.zoom * (1.12 if event.angleDelta().y() > 0
                                                   else 1 / 1.12)))
        self.update()
