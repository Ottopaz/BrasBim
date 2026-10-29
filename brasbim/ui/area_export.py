# SPDX-License-Identifier: GPL-3.0-or-later
"""Exportar e imprimir a área de seleção (``spec/ui/38-area-de-selecao.md`` §5).

A planta do pavimento ativo é desenhada pelo mesmo código da tela (``PlanView``, através
de ``paper._PlanPainter``), recortada pelo polígono da área:

- PDF e impressão: ``QPainter`` com o recorte pelo caminho da área;
- DXF e DWG: ``dwg_export.DxfPainter`` faz o papel do ``QPainter`` e grava o que recebe
  (linhas, áreas cheias e textos), recortado pela área, em centímetros e com as camadas
  do BrasBim (spec/ui 41 §2). Fundos da cor do papel não vão (no DXF não há o que
  cobrir).

O pintor desenha com 1 pixel = 1 mm de papel nas espessuras (``unit`` = 25,4/96) e o
modelo a ``_S`` pixels por metro.
"""

from __future__ import annotations

from PySide6.QtCore import QMarginsF, QPointF, QRectF, QSizeF
from PySide6.QtGui import QPageLayout, QPageSize, QPainter, QPdfWriter, QTransform
from shapely.geometry import Polygon

from brasbim.ui import dwg_export
from brasbim.ui.paper import _PAPER, _PlanPainter
from brasbim.ui.plan_view import C

MARGIN_MM = 10.0  # folha do PDF: a área mais esta margem em volta
_S = 1000.0  # pixels por metro do modelo no desenho para o DXF
_UNIT_MM = 25.4 / 96  # ``unit`` que faz as espessuras saírem em mm de papel


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


# --- DXF e DWG ------------------------------------------------------------------------


def export_dxf(path: str, doc, make_plan, view, pens_, area, den: int,
               fmt: str = "dxf") -> str:
    """A planta recortada pela área, em centímetros, nas coordenadas do pavimento, com as
    camadas do BrasBim (spec/ui 41 §2). ``make_plan()`` refaz a planta da janela (uma vez
    por camada). ``fmt``: ``dxf`` ou ``dwg``."""
    dxf = dwg_export.new_document(fmt)
    dxf.header["$INSUNITS"] = dwg_export.INSUNITS_CM
    dxf.header["$LTSCALE"] = 0.6 * den  # traço de ~8 mm no papel na escala da vista
    k = dwg_export.UNITS_PER_M / _S
    clip = Polygon([(x * dwg_export.UNITS_PER_M, y * dwg_export.UNITS_PER_M)
                    for x, y in area.points])
    painter = dwg_export.DxfPainter(dxf.modelspace(), QTransform(k, 0, 0, -k, 0, 0), 1.0,
                                    clip)
    with dwg_export._paper_background():
        dwg_export._paint_layers(dxf, doc, painter, lambda: _drawer(
            make_plan(), view, pens_, _S, QPointF(0, 0), _UNIT_MM))
    return dwg_export.save(dxf, path, fmt)
