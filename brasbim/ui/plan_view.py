# SPDX-License-Identifier: GPL-3.0-or-later
"""Vista de planta (``spec/ui/01-janela-e-ferramentas.md`` §3): desenha o pavimento ativo,
navega (roda, botão do meio, espaço) e repassa mouse e teclado à ferramenta ativa."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import QWidget

from brasbim.core.snap import KIND_LABEL
from brasbim.ui.measure_box import ToolInput
from brasbim.ui.tools import Mods, PlanContext, ToolBox

SNAP_PX = 10  # distância de atração na tela (§3.2)
HANDLE_PX = 4  # metade do lado da alça na tela (0.2 §4)
_MIN_SCALE, _MAX_SCALE = 2.0, 5000.0
_FRAME_MAX_SCALE = 200.0  # enquadrar a seleção não aproxima mais que isto (spec/ui 07 §4)
_FRAME_MARGIN = 0.2

# Cores da planta (próprias).
C = {
    "background": QColor("#f6f5f1"),
    "grid": QColor("#e4e2da"),
    "grid_major": QColor("#cfccc1"),
    "wall_fill": QColor("#9c9a93"),
    "wall_line": QColor("#2b2a27"),
    "below": QColor("#bdbab2"),
    "door": QColor("#2b2a27"),
    "swing": QColor("#6d6a62"),
    "select": QColor("#1d6fd6"),
    "preview": QColor("#1d6fd6"),
    "invalid": QColor("#d43a2f"),
    "crossing": QColor("#2f8f4e"),
    "label_bg": QColor(255, 255, 255, 225),
}


class PlanView(QWidget, ToolInput):
    cursor_moved = Signal(float, float)
    hint_changed = Signal(str)
    tool_finished = Signal()
    tool_options_changed = Signal()
    context_requested = Signal(object, object)  # (GlobalId ou None, posição global)

    def __init__(self, toolbox: ToolBox, parent=None):
        super().__init__(parent)
        self.toolbox = toolbox
        self.ctx: PlanContext = toolbox.ctx
        self.scale = 60.0  # pixels por metro
        self.origin = QPointF(200, 400)  # posição na tela do ponto (0, 0) do pavimento
        self._pan: QPointF | None = None
        self.selection_bar = None  # mini-barra (spec/ui 03 §5), posta pela janela
        self.show_tags = True  # etiquetas de porta (spec/ui 05 §5)
        self.show_tag_size = False
        self._space = False
        self._fitted = False
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(300, 200)
        self._init_tool_input()

    # --- coordenadas -----------------------------------------------------------------

    def to_screen(self, p) -> QPointF:
        return QPointF(self.origin.x() + p[0] * self.scale, self.origin.y() - p[1] * self.scale)

    def to_world(self, q: QPointF) -> tuple[float, float]:
        return ((q.x() - self.origin.x()) / self.scale, (self.origin.y() - q.y()) / self.scale)

    def selection_rect(self) -> tuple[float, float, float, float] | None:
        """Retângulo da seleção na tela (x0, y0, x1, y1), ou None se não está na planta."""
        selection = self.ctx.session.selection
        pts = [self.to_screen(p) for s in self.ctx.plan.shapes
               if s.owner in selection and s.role != "below" for p in s.points]
        if not pts:
            return None
        xs, ys = [q.x() for q in pts], [q.y() for q in pts]
        return min(xs), min(ys), max(xs), max(ys)

    def _sync_tol(self) -> None:
        self.ctx.tol = SNAP_PX / self.scale

    def fit(self) -> None:
        bounds = self.ctx.plan.bounds()
        if bounds is None:
            self.scale = 60.0
            self.origin = QPointF(self.width() / 2, self.height() / 2)
        else:
            x0, y0, x1, y1 = bounds
            w, h = max(x1 - x0, 1.0), max(y1 - y0, 1.0)
            self.scale = min(max(min(self.width() / w, self.height() / h) * 0.85, _MIN_SCALE),
                             _MAX_SCALE)
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            self.origin = QPointF(self.width() / 2 - cx * self.scale,
                                  self.height() / 2 + cy * self.scale)
        self._sync_tol()
        self.update()

    def frame_selection(self) -> bool:
        """Enquadra a seleção do pavimento ativo com margem (spec/ui 07 §4)."""
        selection = self.ctx.session.selection
        pts = [p for s in self.ctx.plan.shapes if s.owner in selection and s.role != "below"
               for p in s.points]
        if not pts:
            return False
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        w = max(x1 - x0, 0.01) * (1 + 2 * _FRAME_MARGIN)
        h = max(y1 - y0, 0.01) * (1 + 2 * _FRAME_MARGIN)
        self.scale = min(max(min(self.width() / w, self.height() / h), _MIN_SCALE),
                         _FRAME_MAX_SCALE)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        self.origin = QPointF(self.width() / 2 - cx * self.scale,
                              self.height() / 2 + cy * self.scale)
        self._sync_tol()
        self.update()
        return True

    def showEvent(self, event):
        super().showEvent(event)
        if not self._fitted:
            self._fitted = True
            self.fit()

    # --- desenho ---------------------------------------------------------------------

    def _polygon(self, points) -> QPolygonF:
        return QPolygonF([self.to_screen(p) for p in points])

    def _path(self, points, closed) -> QPainterPath:
        path = QPainterPath()
        path.addPolygon(self._polygon(points))
        if closed:
            path.closeSubpath()
        return path

    def _draw_grid(self, painter: QPainter) -> None:
        step = 0.1 if self.scale * 0.1 >= 8 else 1.0 if self.scale >= 8 else None
        if step is None:
            return
        x0, y1 = self.to_world(QPointF(0, 0))
        x1, y0 = self.to_world(QPointF(self.width(), self.height()))
        for axis in (0, 1):
            lo, hi = (x0, x1) if axis == 0 else (y0, y1)
            k = math.floor(lo / step)
            while k * step <= hi:
                v = k * step
                major = step == 1.0 or k % 10 == 0
                painter.setPen(QPen(C["grid_major"] if major else C["grid"], 1))
                if axis == 0:
                    x = self.to_screen((v, 0)).x()
                    painter.drawLine(QPointF(x, 0), QPointF(x, self.height()))
                else:
                    y = self.to_screen((0, v)).y()
                    painter.drawLine(QPointF(0, y), QPointF(self.width(), y))
                k += 1

    def _draw_plan(self, painter: QPainter) -> None:
        selection = self.ctx.session.selection
        for shape in self.ctx.plan.shapes:
            selected = shape.owner in selection
            path = self._path(shape.points, shape.closed)
            role = shape.role
            if role == "below":
                painter.setPen(QPen(C["below"], 1, Qt.DashLine))
                painter.setBrush(Qt.NoBrush)
            elif role == "wall":
                if not selected and shape.style is not None:
                    self._draw_styled(painter, path, shape.style)
                    continue
                painter.setPen(QPen(C["select"] if selected else C["wall_line"],
                                    2 if selected else 1.4))
                fill = QColor(C["select"]) if selected else C["wall_fill"]
                if selected:
                    fill.setAlpha(110)
                painter.setBrush(QBrush(fill))
            else:
                color = C["select"] if selected else (C["swing"] if role == "door_swing"
                                                      else C["door"])
                style = Qt.DashLine if role == "door_hidden" else Qt.SolidLine
                painter.setPen(QPen(color, 0.8 if role == "door_swing" else 1.3, style))
                painter.setBrush(QBrush(color) if role == "door_frame" else Qt.NoBrush)
            painter.drawPath(path)

    def _draw_styled(self, painter: QPainter, path: QPainterPath, style: dict) -> None:
        """Parede cortada com a representação do tipo (spec/ui 03 §6.1)."""
        fill = style["fill"]
        painter.fillPath(path, C["background"])  # cobre o que estiver por baixo (X)
        if fill == "solid":
            painter.fillPath(path, QColor(style["fill_color"]))
        elif fill == "hatch":
            spacing = style["hatch_spacing"] * self.scale
            color = QColor(style["fill_color"])
            if spacing < 3:  # longe demais para ver as linhas: tom chapado
                color.setAlpha(120)
                painter.fillPath(path, color)
            else:
                painter.save()
                painter.setClipPath(path)
                painter.setPen(QPen(color.darker(130), 1))
                rect = path.boundingRect()
                center = rect.center()
                angle = -math.radians(style["hatch_angle"])  # y da tela para baixo
                d = QPointF(math.cos(angle), math.sin(angle))
                n = QPointF(-d.y(), d.x())
                reach = math.hypot(rect.width(), rect.height()) / 2 + 1
                for k in range(-int(reach / spacing) - 1, int(reach / spacing) + 2):
                    o = center + n * (k * spacing)
                    painter.drawLine(o - d * reach, o + d * reach)
                painter.restore()
        width = max(1.0, style["line_weight"] * 1000 * 96 / 25.4)
        painter.setPen(QPen(QColor(style["line_color"]), width))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

    def _draw_tags(self, painter: QPainter) -> None:
        if not self.show_tags:
            return
        painter.setFont(QFont(self.font().family(), 9))
        metrics = painter.fontMetrics()
        selection = self.ctx.session.selection
        for label in self.ctx.plan.labels:
            lines = [label.code] + ([label.size] if self.show_tag_size else [])
            q = self.to_screen(label.at)
            height = metrics.height()
            painter.setPen(QPen(C["select"] if label.owner in selection else QColor("#222")))
            for i, text in enumerate(lines):
                width = metrics.horizontalAdvance(text)
                y = q.y() - len(lines) * height / 2 + i * height
                painter.drawText(QRectF(q.x() - width / 2 - 2, y, width + 4, height),
                                 Qt.AlignCenter, text)

    def _draw_tool(self, painter: QPainter) -> None:
        tool = self.toolbox.active
        for mark in tool.preview():
            if mark.style == "gap":
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(C["background"]))
            elif mark.style in ("window", "crossing"):
                color = C["preview"] if mark.style == "window" else C["crossing"]
                fill = QColor(color)
                fill.setAlpha(25)
                painter.setPen(QPen(color, 1, Qt.SolidLine if mark.style == "window"
                                    else Qt.DashLine))
                painter.setBrush(QBrush(fill))
            else:
                color = C["invalid"] if mark.style == "invalid" else C["preview"]
                fill = QColor(color)
                fill.setAlpha(45)
                painter.setPen(QPen(color, 1.4, Qt.DashLine))
                painter.setBrush(QBrush(fill) if mark.closed else Qt.NoBrush)
            painter.drawPath(self._path(mark.points, mark.closed))
        for point, hot in tool.handles():
            q, r = self.to_screen(point), HANDLE_PX
            painter.setPen(QPen(C["select"], 1.2))
            painter.setBrush(QBrush(C["select"] if hot else QColor("white")))
            painter.drawRect(QRectF(q.x() - r, q.y() - r, 2 * r, 2 * r))
        snapped = tool.snapped
        if snapped is not None and snapped.kind not in ("free",):
            q = self.to_screen(snapped.point)
            painter.setPen(QPen(C["preview"], 1.5))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(QRectF(q.x() - 4, q.y() - 4, 8, 8))
            label = KIND_LABEL.get(snapped.kind, "")
            if label and snapped.kind != "grid":
                self._label(painter, QPointF(q.x() + 8, q.y() + 16), label)
        for point, text in tool.labels():
            q = self.to_screen(point)
            self._label(painter, QPointF(q.x() + 10, q.y() - 10), text)

    def _label(self, painter: QPainter, at: QPointF, text: str) -> None:
        painter.setFont(QFont(self.font().family(), 9))
        rect = painter.fontMetrics().boundingRect(text).adjusted(-4, -2, 4, 2)
        rect.moveTopLeft(at.toPoint())
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(C["label_bg"]))
        painter.drawRoundedRect(rect, 3, 3)
        painter.setPen(QPen(QColor("#222")))
        painter.drawText(rect, Qt.AlignCenter, text)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), C["background"])
        self._draw_grid(painter)
        self._draw_plan(painter)
        self._draw_tags(painter)
        self._draw_tool(painter)
        painter.end()
        if self.selection_bar is not None:
            self.selection_bar.place()

    # --- entrada ---------------------------------------------------------------------

    @staticmethod
    def _mods(event) -> Mods:
        m = event.modifiers()
        return Mods(bool(m & Qt.ShiftModifier), bool(m & Qt.AltModifier),
                    bool(m & Qt.ControlModifier))

    def _refresh_hint(self) -> None:
        self.after_tool_input()

    def _take_input(self) -> None:
        """A planta passa a ser a vista das ferramentas (tolerância pela escala)."""
        self.ctx.input_view = self
        self._sync_tol()

    def mousePressEvent(self, event):
        self.before_press()
        self.setFocus()
        self._take_input()
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and self._space):
            self._pan = event.position()
            return
        tool = self.toolbox.active
        p = self.to_world(event.position())
        if event.button() == Qt.RightButton and tool.name == "select" and not tool.drag:
            gid = self.ctx.plan.pick(p, self.ctx.tol)
            session = self.ctx.session
            if gid and gid not in session.selection:  # spec/ui 07 §4
                session.select([gid], add=bool(event.modifiers() & Qt.ControlModifier))
            self.context_requested.emit(gid, event.globalPosition().toPoint())
            return
        button = {Qt.LeftButton: "left", Qt.RightButton: "right"}.get(event.button())
        if button:
            tool.press(p, self._mods(event), button)
            self._refresh_hint()

    def mouseMoveEvent(self, event):
        if self._pan is not None:
            delta = event.position() - self._pan
            self._pan = event.position()
            self.origin += delta
            self.update()
            return
        self._take_input()
        self.mouse_pos = event.position()
        p = self.to_world(event.position())
        self.cursor_moved.emit(*p)
        self.toolbox.active.move(p, self._mods(event))
        self._refresh_hint()

    def mouseReleaseEvent(self, event):
        if self._pan is not None and event.button() in (Qt.MiddleButton, Qt.LeftButton):
            self._pan = None
            return
        if event.button() == Qt.LeftButton:
            self.toolbox.active.release(self.to_world(event.position()), self._mods(event))
            self._refresh_hint()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toolbox.active.double(self.to_world(event.position()), self._mods(event))
            self._refresh_hint()

    def wheelEvent(self, event):
        factor = 1.15 ** (event.angleDelta().y() / 120)
        new = min(max(self.scale * factor, _MIN_SCALE), _MAX_SCALE)
        at = event.position()
        world = self.to_world(at)
        self.scale = new
        self.origin = QPointF(at.x() - world[0] * new, at.y() + world[1] * new)
        self._sync_tol()
        self.update()

    def event(self, event):
        if self.tool_event(event):
            return True
        return super().event(event)

    def keyPressEvent(self, event):
        if self.tool_key(event):
            return
        key = event.key()
        if key == Qt.Key_Home:
            self.fit()
        elif key == Qt.Key_Space and not event.isAutoRepeat():
            self._space = True
            self.setCursor(Qt.OpenHandCursor)
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self._space = False
            self.unsetCursor()
        super().keyReleaseEvent(event)
