# SPDX-License-Identifier: GPL-3.0-or-later
"""Vista de planta (``spec/ui/01-janela-e-ferramentas.md`` §3): desenha o pavimento ativo,
navega (roda, botão do meio, espaço) e repassa mouse e teclado à ferramenta ativa."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
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

from brasbim.core import pens
from brasbim.core.plan import ABOVE_WEIGHT, VIEW_WEIGHT
from brasbim.core.snap import KIND_LABEL
from brasbim.ui import theme
from brasbim.ui.measure_box import ToolInput
from brasbim.ui.selection_bar import ZOOM_PAUSE_MS
from brasbim.ui.tools import Mods, PlanContext, ToolBox

SNAP_PX = 10  # distância de atração na tela (§3.2)
HANDLE_PX = 4  # metade do lado da alça na tela (0.2 §4)
BELOW_WEIGHT = 0.00013  # m de papel: pavimento de baixo (spec/ui 27)
_MIN_SCALE, _MAX_SCALE = 2.0, 5000.0
_FRAME_MAX_SCALE = 200.0  # enquadrar a seleção não aproxima mais que isto (spec/ui 07 §4)
_FRAME_MARGIN = 0.2

_OBJECT_ROLES = ("object", "object_fill", "object_above")

# Cores da planta (spec/ui 11 §2).
C = {
    "background": QColor(theme.PAPER),
    "grid": QColor(theme.GRID),
    "grid_major": QColor(theme.GRID_MAJOR),
    "wall_fill": QColor("#9c9a93"),
    "wall_line": QColor(theme.INK),
    "below": QColor("#bdbab2"),
    "door": QColor(theme.INK),
    "object": QColor(theme.INK_SOFT),
    "swing": QColor(theme.INK_SOFT),
    "select": QColor(theme.ACCENT),
    "preview": QColor(theme.ACCENT),
    "invalid": QColor(theme.ERROR),
    "crossing": QColor(theme.OK),
    "label_bg": QColor(247, 248, 246, 225),
    "label": QColor(theme.INK),
}



def snap_marker(painter: QPainter, q: QPointF, kind: str, color) -> None:
    """Marcador próprio de cada tipo de atração (spec/ui 23 §2.4), 8 px."""
    x, y, r = q.x(), q.y(), 4.0
    painter.setPen(QPen(color, 1.5))
    painter.setBrush(Qt.NoBrush)
    if kind == "end":
        painter.setBrush(QBrush(color))
        painter.drawRect(QRectF(x - 3, y - 3, 6, 6))
    elif kind == "inter":
        painter.drawLine(QPointF(x - r - 1, y), QPointF(x + r + 1, y))
        painter.drawLine(QPointF(x, y - r - 1), QPointF(x, y + r + 1))
    elif kind == "mid":
        painter.drawPolygon(QPolygonF([QPointF(x, y - r - 1), QPointF(x + r + 1, y),
                                       QPointF(x, y + r + 1), QPointF(x - r - 1, y)]))
    elif kind == "center":
        painter.drawEllipse(q, r + 1, r + 1)
        painter.drawEllipse(q, 1.5, 1.5)
    elif kind == "perp":
        painter.drawLine(QPointF(x - r, y + r), QPointF(x + r, y + r))
        painter.drawLine(QPointF(x, y + r), QPointF(x, y - r))
    elif kind == "tan":
        painter.drawEllipse(q, r, r)
        painter.drawLine(QPointF(x - r - 2, y - r), QPointF(x + r + 2, y - r))
    elif kind in ("near", "path"):
        painter.drawLine(QPointF(x - r - 1, y + r - 1), QPointF(x + r + 1, y - r + 1))
        painter.drawEllipse(q, 1.5, 1.5)
    else:  # grade
        painter.drawEllipse(q, 1.5, 1.5)

class PlanView(QWidget, ToolInput):
    cursor_moved = Signal(float, float)
    hint_changed = Signal(str)
    tool_finished = Signal()
    tool_options_changed = Signal()
    tool_requested = Signal(str)  # Enter repete a última ferramenta (spec/ui 23 §3.2)
    context_requested = Signal(object, object)  # (GlobalId ou None, posição global)
    object_dropped = Signal(str, float, float)  # objeto arrastado da biblioteca, ponto

    def __init__(self, toolbox: ToolBox, parent=None):
        super().__init__(parent)
        self.toolbox = toolbox
        self.ctx: PlanContext = toolbox.ctx
        self.setAcceptDrops(True)  # objeto da biblioteca
        self.scale = 60.0  # pixels por metro
        self.origin = QPointF(200, 400)  # posição na tela do ponto (0, 0) do pavimento
        self._pan: QPointF | None = None
        self._zooming = QTimer(self, singleShot=True, interval=ZOOM_PAUSE_MS)
        self._zooming.timeout.connect(self.update)  # a mini-barra volta ao parar o zoom
        self.selection_bar = None  # mini-barra (spec/ui 03 §5), posta pela janela
        self.show_tags = True  # etiquetas de porta (spec/ui 05 §5)
        self.show_tag_size = False
        self.show_structure_tags = True  # etiquetas de pilar e viga (spec/ui 12 §5)
        self.show_object_tags = False  # código dos objetos (objeto-parametrico.md §7)
        self.show_space_numbers = False  # número antes do nome do ambiente (spec/ui 13 §3.4)
        self.show_weights = True  # espessuras de linha do papel (spec/ui 13 §8)
        self.show_view_symbols = True  # símbolos de corte e fachada (spec/ui 14 §7)
        self.pens = pens.DEFAULT  # tabela de penas da janela (spec/ui 27)
        # Unidades do desenho por pixel de tela: 1 na tela; dpi/96 no papel (spec/ui 15).
        self.unit = 1.0
        self._space = False
        self._fitted = False
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(300, 200)
        self._init_tool_input()

    # --- coordenadas -----------------------------------------------------------------

    def anchor_screen(self, p) -> QPointF:
        return self.to_screen(p)

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

    @property
    def navigating(self) -> bool:
        """Deslocamento ou zoom em curso (a mini-barra some até parar)."""
        return self._pan is not None or self._zooming.isActive()

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
        """Grade de 1 m; a de 0,10 m aparece aos poucos com o zoom, para não competir
        com o desenho (spec/ui 11 §4.1)."""
        metre = self.scale
        if metre >= 8:
            major, minor = 1.0, 0.1
        elif metre * 10 >= 8:
            major, minor = 10.0, 1.0
        else:
            return
        fade = min(1.0, max(0.0, (minor * self.scale - 7) / 17))
        faint = QColor(C["grid"])
        faint.setAlphaF(fade)
        x0, y1 = self.to_world(QPointF(0, 0))
        x1, y0 = self.to_world(QPointF(self.width(), self.height()))
        ratio = round(major / minor)
        for axis in (0, 1):
            lo, hi = (x0, x1) if axis == 0 else (y0, y1)
            k = math.floor(lo / minor)
            while k * minor <= hi:
                is_major = k % ratio == 0
                if is_major or fade > 0:
                    painter.setPen(QPen(C["grid_major"] if is_major else faint, 1))
                    v = k * minor
                    if axis == 0:
                        x = self.to_screen((v, 0)).x()
                        painter.drawLine(QPointF(x, 0), QPointF(x, self.height()))
                    else:
                        y = self.to_screen((0, v)).y()
                        painter.drawLine(QPointF(0, y), QPointF(self.width(), y))
                k += 1

    def _px(self, weight: float) -> float:
        """Espessura de linha em metros de papel (NBR 8403) para pixels (spec/ui 03 §6.1)."""
        return weight * 1000 * 96 / 25.4 * self.unit

    def tint(self, owner) -> QColor | None:
        """Cor da situação do dono (spec/ui 31 §3); nunca em Imprimir em preto."""
        if self.pens.black:
            return None
        found = self.ctx.plan.colors.get(owner)
        return QColor(found) if found else None

    def _rings_path(self, rings) -> QPainterPath:
        path = QPainterPath()
        path.setFillRule(Qt.OddEvenFill)
        for ring in rings:
            path.addPolygon(self._polygon(ring))
            path.closeSubpath()
        return path

    def _draw_plan(self, painter: QPainter) -> None:
        """Ordem (spec/ui 06 §3.2): pavimento de baixo, acima do plano, em vista, cortadas
        (regiões e bordas), destaque da seleção e portas."""
        selection = self.ctx.session.selection
        plan = self.ctx.plan
        # Laje em vista é opaca: cobre a grade, mas fica sob todo o resto (inclusive o
        # pavimento de baixo); os furos (anéis do mesmo dono e aberturas) ficam vazados.
        floors: dict[str, list] = {}
        holes = QPainterPath()
        for shape in plan.shapes:
            if shape.role == "slab_view" and shape.closed:
                floors.setdefault(shape.owner, []).append(shape.points)
            elif shape.role == "slab_opening" and shape.closed:
                holes.addPolygon(self._polygon(shape.points))
                holes.closeSubpath()
        for rings in floors.values():
            painter.fillPath(self._rings_path(rings).subtracted(holes), C["background"])
        rest = []
        for shape in plan.shapes:
            role = shape.role
            if role in _OBJECT_ROLES:  # mobiliário e equipamentos: sob as paredes cortadas
                self._draw_object(painter, shape, shape.owner in selection)
                continue
            if role not in ("below", "wall_above", "wall_view", "slab_view", "slab_above",
                            "slab_opening", "slab_opening_x"):
                rest.append(shape)
                continue
            selected = shape.owner in selection
            pens_ = self.pens
            tint = self.tint(shape.owner)
            if role == "below":
                pen = QPen(QColor(pens_.color("below")),
                           max(self.unit, self._px(pens_.weight("below", BELOW_WEIGHT))),
                           Qt.DashLine)
            elif role in ("wall_above", "slab_above"):
                pen = QPen(C["select"] if selected else tint or QColor(pens_.color("above")),
                           max(self.unit, self._px(pens_.weight("above", ABOVE_WEIGHT))),
                           Qt.DashLine)
            else:
                pen = QPen(C["select"] if selected else tint or QColor(pens_.color("view")),
                           2 * self.unit if selected else max(
                               self.unit, self._px(pens_.weight("view", VIEW_WEIGHT))))
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(self._path(shape.points, shape.closed))
        black = self.pens.black
        for region in plan.regions:
            fill = region.fill
            if region.tint and not black:  # situação (spec/ui 31 §3)
                fill = {**fill, "line_color": region.tint,
                        "background": region.tint if fill.get("background") else None}
            self._draw_region(painter, self._rings_path(region.rings), fill)
        painter.setBrush(Qt.NoBrush)
        for edge in plan.edges:
            color = edge.color if edge.color.upper() not in pens.NEUTRAL \
                else self.pens.color(edge.pen)
            if edge.tint and not black:
                color = edge.tint
            painter.setPen(QPen(QColor(color), max(self.unit, self._px(
                self.pens.weight(edge.pen, edge.weight)))))
            painter.drawPath(self._rings_path(edge.rings))
        for shape in rest:
            selected = shape.owner in selection
            path = self._path(shape.points, shape.closed)
            role = shape.role
            if role in ("annotation", "roof_edge", "object_box"):
                continue  # desenhada por ``_draw_annotations`` (a caixa não aparece)
            if role == "opening_box":  # o vão aparece na parede; aqui só o destaque
                if selected:
                    fill = QColor(C["select"])
                    fill.setAlpha(60)
                    painter.setPen(QPen(C["select"], 1.6 * self.unit))
                    painter.setBrush(QBrush(fill))
                    painter.drawPath(path)
                continue
            if role in ("plant", "plant_fill"):  # vegetação: por cima das paredes
                self._draw_object(painter, shape, selected)
                continue
            if role in ("wall", "column", "beam", "slab", "space", "roof"):
                # O desenho vem das regiões (cortados) ou das linhas da vista: aqui só o
                # destaque da seleção.
                if not selected:
                    continue
                painter.setPen(QPen(C["select"], 2 * self.unit))
                fill = QColor(C["select"])
                fill.setAlpha(40 if role in ("slab", "space", "roof") else 110)
                painter.setBrush(QBrush(fill))
            elif role in ("column_view", "beam_view", "column_above", "beam_above"):
                above = role.endswith("above")
                category = "above" if above else "view"
                painter.setPen(QPen(
                    C["select"] if selected else self.tint(shape.owner)
                    or QColor(self.pens.color(category)),
                    2 * self.unit if selected else max(self.unit, self._px(self.pens.weight(
                        category, ABOVE_WEIGHT if above else VIEW_WEIGHT))),
                    Qt.DashLine if above else Qt.SolidLine))
                painter.setBrush(Qt.NoBrush)
            else:
                thin = role in ("door_swing", "window_sash", "window_glass")
                category = "swing" if role == "door_swing" else "opening"
                color = C["select"] if selected else self.tint(shape.owner) \
                    or QColor(self.pens.color(category))
                style = Qt.DashLine if role == "door_hidden" else Qt.SolidLine
                painter.setPen(QPen(color, (0.8 if thin else 1.3) * self.unit
                                    * self.pens.scale(category), style))
                painter.setBrush(QBrush(color) if role == "door_frame" else Qt.NoBrush)
            painter.drawPath(path)

    def _draw_object(self, painter: QPainter, shape, selected: bool) -> None:
        """Símbolo do objeto paramétrico (objeto-parametrico.md §7): linha fina; o contorno
        com fundo cobre o que fica por baixo; acima do plano de corte, tracejado."""
        path = self._path(shape.points, shape.closed)
        color = C["select"] if selected else self.tint(shape.owner) \
            or QColor(self.pens.color("object"))
        width = 1.6 * self.unit if selected else max(
            self.unit, self._px(self.pens.weight("object", ABOVE_WEIGHT)))
        style = Qt.DashLine if shape.role == "object_above" else Qt.SolidLine
        if shape.role in ("object_fill", "plant_fill") and shape.closed:
            painter.fillPath(path, C["background"])
        painter.setPen(QPen(color, width, style))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

    def _draw_region(self, painter: QPainter, path: QPainterPath, fill: dict) -> None:
        """Mancha de tipo ou de material; a hachura parte da origem do pavimento, para
        continuar de uma parede para a outra (spec/ui 06 §2.2)."""
        painter.fillPath(path, C["background"])  # cobre o que estiver por baixo
        pattern = fill["pattern"]
        if fill.get("background"):
            painter.fillPath(path, QColor(fill["background"]))
        if pattern not in ("lines", "cross"):
            return
        spacing = fill["spacing"] * self.scale
        color = QColor(fill["line_color"])
        if fill.get("source") == "type":
            color = color.darker(130)
            if spacing < 3:  # longe demais para ver as linhas: tom chapado (spec/ui 03)
                color.setAlpha(120)
                painter.fillPath(path, color)
                return
        elif spacing < 1:  # menos de 1 px: só o fundo (spec/ui 06 §4.1)
            return
        painter.save()
        painter.setClipPath(path)
        painter.setPen(QPen(color, self.unit))
        rect = path.boundingRect()
        corners = [rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()]
        anchor = self.to_screen((0.0, 0.0))
        angles = [fill["angle"]] + ([fill["angle"] + 90.0] if pattern == "cross" else [])
        for degrees in angles:
            a = -math.radians(degrees)  # y da tela para baixo
            d = QPointF(math.cos(a), math.sin(a))
            n = QPointF(-d.y(), d.x())
            ss = [QPointF.dotProduct(c - anchor, n) for c in corners]
            ts = [QPointF.dotProduct(c - anchor, d) for c in corners]
            for k in range(math.floor(min(ss) / spacing), math.ceil(max(ss) / spacing) + 1):
                o = anchor + n * (k * spacing)
                painter.drawLine(o + d * (min(ts) - 1), o + d * (max(ts) + 1))
        painter.restore()

    def _font(self, height_m: float) -> QFont | None:
        """Fonte com a altura de modelo na tela (texto que segue a escala, spec/ui 13 §2);
        ``None`` se ficaria pequena demais para ler."""
        px = height_m * self.scale
        if px < 3:
            return None
        font = QFont(self.font().family())
        font.setPixelSize(max(1, round(px)))
        return font

    def _draw_tags(self, painter: QPainter) -> None:
        selection = self.ctx.session.selection
        for label in self.ctx.plan.labels:
            if label.kind == "structure":
                if not self.show_structure_tags:
                    continue
                lines = [label.code] + ([label.size] if label.size else [])
            elif label.kind == "object":
                if not self.show_object_tags:
                    continue
                lines = [label.code]
            elif label.kind == "space":
                code = (f"{label.number} · {label.code}" if self.show_space_numbers
                        and label.number else label.code)
                lines = [code, label.size]
            elif not self.show_tags:
                continue
            else:
                lines = [label.code] + ([label.size] if self.show_tag_size else [])
            q = self.to_screen(label.at)
            painter.setPen(QPen(C["select"] if label.owner in selection
                                else QColor(self.pens.color("text"))))
            painter.save()
            painter.translate(q)
            painter.rotate(-label.angle)  # y da tela para baixo
            heights = [label.height] + [label.height * label.size_ratio] * (len(lines) - 1)
            fonts = [self._font(h) if label.height else QFont(self.font().family(), 9)
                     for h in heights]
            if any(f is None for f in fonts):
                painter.restore()
                continue
            rows = []
            for text, font in zip(lines, fonts, strict=True):
                painter.setFont(font)
                rows.append((text, font, painter.fontMetrics().height()))
            y = -sum(h for _, _, h in rows) / 2
            for text, font, h in rows:
                painter.setFont(font)
                width = painter.fontMetrics().horizontalAdvance(text)
                painter.drawText(QRectF(-width / 2 - 2, y, width + 4, h), Qt.AlignCenter, text)
                y += h
            painter.restore()

    def _line_px(self, weight_mm: float) -> float:
        return max(self.unit, self._px(weight_mm / 1000.0)) if self.show_weights else self.unit

    def _draw_annotations(self, painter: QPainter) -> None:
        """Traços e textos das anotações (as hachuras vêm nas regiões), spec/ui 13."""
        selection = self.ctx.session.selection
        dashes = {"solid": Qt.SolidLine, "dashed": Qt.DashLine, "dashdot": Qt.DashDotLine}
        for owner, prims in self.ctx.plan.annotations:
            if owner in self.ctx.plan.views and not self.show_view_symbols:
                continue
            category = self.ctx.plan.pens.get(owner, "drawing")  # spec/ui 27
            ink = self.tint(owner) or QColor(self.pens.color(category))
            color = C["select"] if owner in selection else ink
            painter.setBrush(Qt.NoBrush)
            for stroke in prims.strokes:
                painter.setPen(QPen(color, self._line_px(self.pens.weight(category,
                                                                          stroke.weight)),
                                    dashes.get(stroke.dash, Qt.SolidLine)))
                painter.drawPath(self._path(stroke.points, stroke.closed))
            painter.setPen(QPen(C["select"] if owner in selection else ink))
            for text in prims.texts:
                font = self._font(text.height)
                if font is None:
                    continue
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

    def _draw_hover(self, painter: QPainter) -> None:
        """Destaque do elemento sob o cursor, antes do clique (spec/ui 28 §2)."""
        owner = self.ctx.hover
        if owner is None or owner in self.ctx.session.selection                 or self.toolbox.active.name != "select":
            return
        color = QColor(C["select"])
        color.setAlpha(140)
        painter.setPen(QPen(color, 2.5 * self.unit))
        painter.setBrush(Qt.NoBrush)
        for shape in self.ctx.plan.shapes:
            if shape.owner == owner and shape.role != "below":
                painter.drawPath(self._path(shape.points, shape.closed))

    def leaveEvent(self, event):
        if self.ctx.hover is not None:
            self.ctx.hover = None
            self.update()
        super().leaveEvent(event)

    def _draw_tool(self, painter: QPainter) -> None:
        tool = self.toolbox.active
        for mark in tool.preview():
            if mark.style == "gap":
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(C["background"]))
            elif mark.style in ("guide", "reference"):
                painter.setPen(QPen(C["preview"], 1.6 if mark.style == "reference" else 1,
                                    Qt.SolidLine if mark.style == "reference"
                                    else Qt.DashLine))
                painter.setBrush(Qt.NoBrush)
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
            painter.setBrush(QBrush(C["select"] if hot else C["background"]))
            painter.drawRect(QRectF(q.x() - r, q.y() - r, 2 * r, 2 * r))
        for mark in self.ctx.axis_marks():
            painter.setPen(QPen(C["preview"], 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(self._path(mark.points, False))
        snapped = tool.snapped
        if snapped is not None and snapped.kind not in ("free",):
            q = self.to_screen(snapped.source or snapped.point)
            if snapped.source is not None:  # projeção na trava de eixo (spec/ui 23 §3.1)
                painter.setPen(QPen(C["preview"], 1, Qt.DotLine))
                painter.drawLine(q, self.to_screen(snapped.point))
            painter.setPen(QPen(C["preview"], 1.5))
            painter.setBrush(Qt.NoBrush)
            snap_marker(painter, q, snapped.kind, C["preview"])
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
        painter.setPen(QPen(C["label"]))
        painter.drawText(rect, Qt.AlignCenter, text)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), C["background"])
        self._draw_grid(painter)
        self._draw_plan(painter)
        self._draw_annotations(painter)
        self._draw_tags(painter)
        self._draw_hover(painter)
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
            if button == "left":  # ponto anterior da coordenada relativa (spec/ui 24 §4)
                near = tool.snapped is not None and                     math.dist(tool.snapped.point, p) <= 2 * self.ctx.tol
                self.ctx.last_point = tool.snapped.point if near else p
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
        self.restart_dwell()
        self._refresh_hint()

    def mouseReleaseEvent(self, event):
        if self._pan is not None and event.button() in (Qt.MiddleButton, Qt.LeftButton):
            self._pan = None
            self.update()  # a mini-barra volta junto à seleção
            return
        if event.button() == Qt.LeftButton:
            self.toolbox.active.release(self.to_world(event.position()), self._mods(event))
            self._refresh_hint()

    # --- arrastar da biblioteca (pente fino, 2026-10-27) -----------------------------

    def dragEnterEvent(self, event):
        from brasbim.ui.library_panel import MIME

        if event.mimeData().hasFormat(MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dropEvent(self, event):
        from brasbim.ui.library_panel import MIME

        if not event.mimeData().hasFormat(MIME):
            return
        event.acceptProposedAction()
        x, y = self.to_world(event.position())
        key = bytes(event.mimeData().data(MIME)).decode("utf-8")
        self.object_dropped.emit(key, x, y)

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
        self._zooming.start()
        self.update()

    def event(self, event):
        if self.tool_event(event):
            return True
        return super().event(event)

    def keyPressEvent(self, event):
        if self.tool_key(event):
            return
        if event.key() != Qt.Key_Space and self.forward_text(event):
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
            self.apply_cursor()
        super().keyReleaseEvent(event)
