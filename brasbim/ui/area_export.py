# SPDX-License-Identifier: GPL-3.0-or-later
"""Exportar e imprimir a área de seleção (``spec/ui/38-area-de-selecao.md`` §5).

A planta do pavimento ativo é desenhada pelo mesmo código da tela (``PlanView``, através
de ``paper._PlanPainter``), recortada pelo polígono da área:

- PDF e impressão: ``QPainter`` com o recorte pelo caminho da área;
- DXF: ``_DxfPainter`` faz o papel do ``QPainter`` e grava o que recebe (linhas, áreas
  cheias e textos) com ``ezdxf``, recortado pela área com ``shapely``. Fundos da cor do
  papel não vão (no DXF não há o que cobrir).

No ``_DxfPainter`` 1 unidade = 1 mm de papel nas espessuras (``unit`` = 25,4/96) e o
modelo fica a ``_S`` unidades por metro; ``_to_model`` desfaz essa escala.
"""

from __future__ import annotations

import math

import ezdxf
import shapely
from ezdxf.enums import TextEntityAlignment
from PySide6.QtCore import QMarginsF, QPointF, QRectF, QSizeF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFontMetricsF,
    QPageLayout,
    QPageSize,
    QPainter,
    QPainterPath,
    QPdfWriter,
    QPen,
    QTransform,
)
from shapely.geometry import LineString, Point, Polygon

from brasbim.ui.paper import _PAPER, _PlanPainter
from brasbim.ui.plan_view import C

MARGIN_MM = 10.0  # folha do PDF: a área mais esta margem em volta
_S = 1000.0  # unidades por metro do modelo no DXF
_UNIT_MM = 25.4 / 96  # ``unit`` que faz as espessuras saírem em mm de papel
# Espessuras do DXF (centésimos de mm)
_WEIGHTS = (0, 5, 9, 13, 15, 18, 20, 25, 30, 35, 40, 50, 53, 60, 70, 80, 90, 100, 106, 120,
            140, 158, 200, 211)
_LINETYPES = {Qt.DashLine: "DASHED", Qt.DashDotLine: "DASHDOT", Qt.DotLine: "DOT"}
LAYERS = {"lines": "LINHAS", "hatch": "HACHURAS", "fill": "PREENCHIMENTOS",
          "text": "TEXTOS"}


def _drawer(plan, view, pens_, scale: float, origin: QPointF, unit: float) -> _PlanPainter:
    """Pintor da planta com as opções de exibição da vista (etiquetas, espessuras…)."""
    drawer = _PlanPainter(None, plan, scale, origin, unit)
    for name, value in vars(view).items():
        if name.startswith("show_") and isinstance(value, bool):
            setattr(drawer, name, value)
    drawer.pens = pens_
    return drawer


def paper_size(area, den: int) -> tuple[float, float]:
    """Largura e altura da folha (mm): a área na escala mais a margem."""
    x0, y0, x1, y1 = area.bounds()
    return ((x1 - x0) * 1000.0 / den + 2 * MARGIN_MM,
            (y1 - y0) * 1000.0 / den + 2 * MARGIN_MM)


def render_area(painter: QPainter, plan, view, pens_, area, den: int, px_per_mm: float,
                top_left: QPointF, unit: float) -> None:
    """Desenha a planta recortada pela área, com o canto de cima da área a uma margem de
    ``top_left`` (pixels)."""
    x0, _, _, y1 = area.bounds()
    scale = px_per_mm * 1000.0 / den
    margin = MARGIN_MM * px_per_mm
    origin = QPointF(top_left.x() + margin - x0 * scale, top_left.y() + margin + y1 * scale)
    drawer = _drawer(plan, view, pens_, scale, origin, unit)
    old_background = C["background"]
    C["background"] = _PAPER
    try:
        painter.save()
        painter.setClipPath(drawer._path(area.points, True))
        drawer.paint(painter)
        painter.restore()
    finally:
        C["background"] = old_background


def export_pdf(path: str, plan, view, pens_, area, den: int, dpi: int = 600) -> None:
    """Uma página do tamanho da área na escala ``1:den``, mais a margem."""
    w, h = paper_size(area, den)
    writer = QPdfWriter(path)
    writer.setResolution(dpi)
    writer.setCreator("BrasBim")
    writer.setPageLayout(QPageLayout(QPageSize(QSizeF(w, h), QPageSize.Millimeter),
                                     QPageLayout.Portrait, QMarginsF(0, 0, 0, 0)))
    painter = QPainter(writer)
    try:
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(QRectF(0, 0, w * dpi / 25.4, h * dpi / 25.4), _PAPER)
        render_area(painter, plan, view, pens_, area, den, dpi / 25.4, QPointF(0, 0),
                    dpi / 96.0)
    finally:
        painter.end()


def print_area(printer, plan, view, pens_, area, den: int) -> bool:
    """Imprime na escala, centrado na folha da impressora; se não couber, reduz até caber.
    Devolve ``True`` se saiu na escala."""
    dpi = printer.resolution()
    page = printer.pageLayout().paintRectPixels(dpi)
    px_per_mm = dpi / 25.4
    w, h = paper_size(area, den)
    fit = min(1.0, page.width() / (w * px_per_mm), page.height() / (h * px_per_mm))
    painter = QPainter(printer)
    try:
        painter.setRenderHint(QPainter.Antialiasing)
        k = px_per_mm * fit
        left = (page.width() - w * k) / 2
        top = (page.height() - h * k) / 2
        render_area(painter, plan, view, pens_, area, den, k, QPointF(left, top),
                    dpi / 96.0 * fit)
    finally:
        painter.end()
    return fit >= 1.0


# --- DXF ------------------------------------------------------------------------------


def _to_model(p: QPointF) -> tuple[float, float]:
    return p.x() / _S, -p.y() / _S


def _lineweight(mm: float) -> int:
    target = mm * 100
    return min(_WEIGHTS[1:], key=lambda w: abs(w - target))


def _lines(found):
    """As linhas de um resultado do ``shapely`` (ignora pontos)."""
    if isinstance(found, LineString):
        return [found] if not found.is_empty else []
    return [g for g in getattr(found, "geoms", ()) if isinstance(g, LineString)
            and not g.is_empty]


def _polygons(found):
    if isinstance(found, Polygon):
        return [found] if not found.is_empty else []
    out = []
    for g in getattr(found, "geoms", ()):
        out.extend(_polygons(g))
    return out


class _DxfPainter:
    """Faz o papel do ``QPainter`` para o desenho da planta e grava no ``msp`` do DXF."""

    def __init__(self, msp, clip):
        self.msp = msp
        self.area = clip
        self.clip = clip
        shapely.prepare(self.clip)
        self.t = QTransform()
        self.pen = QPen()
        self.brush = QBrush()
        self.font = None
        self._stack = []
        self.in_hatch = False  # linhas desenhadas sob recorte de região: hachura

    # --- estado ---------------------------------------------------------------------

    def save(self) -> None:
        self._stack.append((QTransform(self.t), QPen(self.pen), QBrush(self.brush),
                            self.font, self.clip, self.in_hatch))

    def restore(self) -> None:
        self.t, self.pen, self.brush, self.font, self.clip, self.in_hatch = self._stack.pop()

    def setPen(self, pen) -> None:  # mesma interface do QPainter
        self.pen = QPen(pen)

    def setBrush(self, brush) -> None:
        self.brush = QBrush(brush)

    def setFont(self, font) -> None:
        self.font = font

    def fontMetrics(self) -> QFontMetricsF:
        return QFontMetricsF(self.font)

    def setRenderHint(self, *args) -> None:
        pass

    def setTransform(self, t: QTransform, combine: bool = False) -> None:
        self.t = t * self.t if combine else QTransform(t)

    def translate(self, *args) -> None:
        p = args[0] if len(args) == 1 else QPointF(*args)
        self.t = QTransform.fromTranslate(p.x(), p.y()) * self.t

    def rotate(self, degrees: float) -> None:
        self.t = QTransform().rotate(degrees) * self.t

    def setClipPath(self, path: QPainterPath, op=Qt.ReplaceClip) -> None:
        shape = self._shape(path)
        base = self.clip if op == Qt.IntersectClip else self.area
        self.clip = base.intersection(shape)
        shapely.prepare(self.clip)
        self.in_hatch = True

    # --- desenho --------------------------------------------------------------------

    def _rings(self, path: QPainterPath) -> list[list[tuple[float, float]]]:
        return [[_to_model(q) for q in poly] for poly in path.toSubpathPolygons(self.t)]

    def _shape(self, path: QPainterPath):
        """Área do caminho, par‑ímpar entre os anéis."""
        found = Polygon()
        for ring in self._rings(path):
            if len(ring) >= 3:
                found = found.symmetric_difference(Polygon(ring).buffer(0))
        return found

    def _attribs(self, layer: str, color: QColor) -> dict:
        return {"layer": LAYERS[layer], "true_color": ezdxf.rgb2int(
            (color.red(), color.green(), color.blue()))}

    def _stroke(self, ring) -> None:
        if self.pen.style() == Qt.NoPen or len(ring) < 2:
            return
        attribs = self._attribs("hatch" if self.in_hatch else "lines", self.pen.color())
        width = self.pen.widthF() * math.sqrt(abs(self.t.determinant()))
        attribs["lineweight"] = _lineweight(width)
        linetype = _LINETYPES.get(self.pen.style())
        if linetype:
            attribs["linetype"] = linetype
        closed = len(ring) > 2 and math.dist(ring[0], ring[-1]) < 1e-9
        line = LineString(ring)
        if self.clip.contains(line):
            self.msp.add_lwpolyline(ring[:-1] if closed else ring, close=closed,
                                    dxfattribs=attribs)
            return
        for piece in _lines(line.intersection(self.clip)):
            self.msp.add_lwpolyline(list(piece.coords), dxfattribs=attribs)

    def _fill(self, path: QPainterPath, color: QColor) -> None:
        if color.alpha() == 0 or color.rgb() == C["background"].rgb():
            return  # fundo da cor do papel: no DXF não cobre nada
        found = _polygons(self._shape(path).intersection(self.clip))
        if not found:
            return
        hatch = self.msp.add_hatch(dxfattribs={"layer": LAYERS["fill"]})
        hatch.set_solid_fill(rgb=(color.red(), color.green(), color.blue()))
        if color.alpha() < 255:
            hatch.transparency = 1.0 - color.alpha() / 255.0
        for poly in found:
            hatch.paths.add_polyline_path(list(poly.exterior.coords)[:-1], is_closed=True,
                                          flags=ezdxf.const.BOUNDARY_PATH_EXTERNAL)
            for hole in poly.interiors:
                hatch.paths.add_polyline_path(list(hole.coords)[:-1], is_closed=True)

    def drawPath(self, path: QPainterPath) -> None:
        if self.brush.style() != Qt.NoBrush:
            self._fill(path, self.brush.color())
        for ring in self._rings(path):
            self._stroke(ring)

    def fillPath(self, path: QPainterPath, brush) -> None:
        self._fill(path, QBrush(brush).color())

    def drawLine(self, a: QPointF, b: QPointF) -> None:
        self._stroke([_to_model(self.t.map(a)), _to_model(self.t.map(b))])

    def drawText(self, *args) -> None:
        """``(QRectF, alinhamento, texto)`` ou ``(QPointF, texto)`` (linha de base)."""
        metrics = QFontMetricsF(self.font)
        if len(args) == 3:
            rect, flags, text = args
            if flags & Qt.AlignHCenter:
                at, align = rect.center(), TextEntityAlignment.MIDDLE_CENTER
            else:
                at = QPointF(rect.left(), rect.bottom() - metrics.descent())
                align = TextEntityAlignment.LEFT
        else:
            at, text = args
            align = TextEntityAlignment.LEFT
        p = _to_model(self.t.map(at))
        if not text or not self.clip.contains(Point(p)):
            return
        k = math.sqrt(abs(self.t.determinant()))
        o, x = self.t.map(QPointF(0, 0)), self.t.map(QPointF(1, 0))
        angle = math.degrees(math.atan2(-(x.y() - o.y()), x.x() - o.x()))
        attribs = self._attribs("text", self.pen.color())
        attribs["rotation"] = angle
        self.msp.add_text(text, height=metrics.capHeight() * k / _S,
                          dxfattribs=attribs).set_placement(p, align=align)


def export_dxf(path: str, plan, view, pens_, area, den: int) -> None:
    """A planta recortada pela área, em metros, nas coordenadas do pavimento."""
    doc = ezdxf.new("R2018", setup=True)
    doc.header["$INSUNITS"] = 6  # metros
    doc.header["$MEASUREMENT"] = 1
    doc.header["$LTSCALE"] = 0.006 * den  # traço de ~3 mm no papel na escala da vista
    for name in LAYERS.values():
        doc.layers.add(name)
    painter = _DxfPainter(doc.modelspace(), Polygon(area.points))
    drawer = _drawer(plan, view, pens_, _S, QPointF(0, 0), _UNIT_MM)
    old_background = C["background"]
    C["background"] = _PAPER
    try:
        drawer.paint(painter)
    finally:
        C["background"] = old_background
    doc.saveas(path)
