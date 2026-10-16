# SPDX-License-Identifier: GPL-3.0-or-later
"""Aba de corte ou fachada (``spec/ui/14-cortes-e-fachadas.md`` §7): mostra o desenho de
``core/drawings/section.py``, com zoom, deslocamento e escolha do elemento pelo clique.

O desenho é refeito quando o modelo muda (``invalidate``); as cores e o preenchimento
das regiões cortadas são os da planta.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QFont, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from brasbim.core.document import OpError
from brasbim.core.drawings import section, views
from brasbim.ui.plan_view import C, PlanView

_MIN_SCALE, _MAX_SCALE = 2.0, 5000.0


class SectionView(QWidget):
    def __init__(self, session, view_gid: str, parent=None):
        super().__init__(parent)
        self.session = session
        self.view_gid = view_gid
        self.scale = 60.0
        self.origin = QPointF(200, 400)
        self.show_weights = True
        self._drawing: section.Drawing | None = None
        self._pan: QPointF | None = None
        self._fitted = False
        self.setMinimumSize(300, 200)
        self.setFocusPolicy(Qt.StrongFocus)

    # --- dados ---------------------------------------------------------------------------

    @property
    def view(self):
        return self.session.doc.find(self.view_gid)

    @property
    def title(self) -> str:
        view = self.view
        return views.read_state(view)["name"] if view is not None else "Vista"

    @property
    def drawing(self) -> section.Drawing:
        if self._drawing is None:
            view = self.view
            try:
                self._drawing = (section.draw(self.session.doc, view) if view is not None
                                 else section.Drawing())
            except OpError as e:
                self.session.message(f"não foi possível desenhar a vista: {e}", "aviso")
                self._drawing = section.Drawing()
        return self._drawing

    def invalidate(self) -> None:
        self._drawing = None
        self.update()

    # --- coordenadas ---------------------------------------------------------------------

    def to_screen(self, p) -> QPointF:
        return QPointF(self.origin.x() + p[0] * self.scale, self.origin.y() - p[1] * self.scale)

    def to_world(self, q: QPointF) -> tuple[float, float]:
        return ((q.x() - self.origin.x()) / self.scale, (self.origin.y() - q.y()) / self.scale)

    def _px(self, weight: float) -> float:
        return weight * 1000 * 96 / 25.4

    def _line_px(self, weight_mm: float) -> float:
        return max(1.0, self._px(weight_mm / 1000.0)) if self.show_weights else 1.0

    def fit(self) -> None:
        box = self.drawing.bounds()
        if box is None:
            return
        u0, v0, u1, v1 = box
        texts = [t.at for t in self.drawing.texts]
        if texts:
            v0 = min(v0, *(p[1] for p in texts))
            u1 = max(u1, *(p[0] for p in texts))
        w, h = max(u1 - u0, 1.0), max(v1 - v0, 1.0)
        self.scale = min(max(min(self.width() / w, self.height() / h) * 0.85, _MIN_SCALE),
                         _MAX_SCALE)
        cx, cy = (u0 + u1) / 2, (v0 + v1) / 2
        self.origin = QPointF(self.width() / 2 - cx * self.scale,
                              self.height() / 2 + cy * self.scale)
        self._fitted = True
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._fitted:
            self.fit()

    # --- desenho ---------------------------------------------------------------------------

    def _path(self, points, closed: bool) -> QPainterPath:
        path = QPainterPath()
        if points:
            path.addPolygon(QPolygonF([self.to_screen(p) for p in points]))
            if closed:
                path.closeSubpath()
        return path

    def _rings_path(self, rings) -> QPainterPath:
        path = QPainterPath()
        path.setFillRule(Qt.OddEvenFill)
        for ring in rings:
            path.addPolygon(QPolygonF([self.to_screen(p) for p in ring]))
            path.closeSubpath()
        return path

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), C["background"])
        selection = self.session.selection
        for item in self.drawing.items:
            selected = item.owner in selection
            ink = C["select"] if selected else C["wall_line"]
            if item.kind == "face":
                painter.setPen(QPen(C["background"], 0.6))
                painter.setBrush(QBrush(C["background"]))
                painter.drawPath(self._path(item.points, True))
            elif item.kind == "edge" or item.kind == "line":
                painter.setPen(QPen(ink, self._line_px(item.weight)))
                painter.setBrush(Qt.NoBrush)
                painter.drawPath(self._path(item.points, False))
            elif item.kind == "cut":
                path = self._rings_path(item.rings)
                if item.fill and item.fill.get("pattern") != "none":
                    PlanView._draw_region(self, painter, path, item.fill)
                elif not item.weight:
                    painter.fillPath(path, C["background"])
                if item.weight:
                    painter.setPen(QPen(ink, self._line_px(item.weight)))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawPath(path)
        painter.setPen(QPen(C["label"]))
        for text in self.drawing.texts:
            px = text.height * self.scale
            if px < 3:
                continue
            font = QFont(self.font().family())
            font.setPixelSize(max(1, round(px)))
            painter.save()
            painter.setFont(font)
            painter.translate(self.to_screen(text.at))
            painter.rotate(-text.angle)
            metrics = painter.fontMetrics()
            width, height = metrics.horizontalAdvance(text.text), metrics.height()
            x = {"left": 0.0, "center": -width / 2, "right": -width}[text.halign]
            y = -height if text.valign == "bottom" else -height / 2
            painter.drawText(QRectF(x, y, width + 2, height), Qt.AlignLeft | Qt.AlignBottom,
                             text.text)
            painter.restore()
        painter.end()

    # --- entrada -----------------------------------------------------------------------------

    def mousePressEvent(self, event):
        self.setFocus()
        if event.button() == Qt.MiddleButton:
            self._pan = event.position()
            return
        if event.button() == Qt.LeftButton:
            gid = self.drawing.pick(self.to_world(event.position()))
            add = bool(event.modifiers() & Qt.ControlModifier)
            if gid or not add:
                self.session.select([gid] if gid else [], add=add)

    def mouseMoveEvent(self, event):
        if self._pan is not None:
            delta = event.position() - self._pan
            self._pan = event.position()
            self.origin += delta
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._pan = None

    def wheelEvent(self, event):
        factor = 1.15 ** (event.angleDelta().y() / 120)
        new = min(max(self.scale * factor, _MIN_SCALE), _MAX_SCALE)
        at = event.position()
        world = self.to_world(at)
        self.scale = new
        self.origin = QPointF(at.x() - world[0] * new, at.y() + world[1] * new)
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Home:
            self.fit()
        else:
            super().keyPressEvent(event)
