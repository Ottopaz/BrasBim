# SPDX-License-Identifier: GPL-3.0-or-later
"""Prancha no papel (``spec/ui/15-pranchas-e-pdf.md``): desenho da folha com o quadro, o
carimbo, as marcas de dobra e as vistas na escala delas; a aba da prancha na tela e a
exportação em PDF vetorial (``QPdfWriter``).

As plantas e os cortes são desenhados pelo mesmo código da tela (``PlanView`` e
``SectionView``), por objetos "pintores" que têm só o que esse código usa, com a escala
em pixels do papel e ``unit`` = dpi / 96 nas espessuras.
"""

from __future__ import annotations

import datetime
from types import SimpleNamespace

from PySide6.QtCore import QMarginsF, QPointF, QRectF, QSizeF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QPageLayout,
    QPageSize,
    QPainter,
    QPdfWriter,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import QMenu, QWidget

from brasbim.core import plan as plan_mod
from brasbim.core.document import OpError
from brasbim.core.drawings import section, sheets
from brasbim.ui import theme
from brasbim.ui.plan_view import C, PlanView
from brasbim.ui.section_view import SectionView

_PAPER = QColor(theme.FIELD)  # papel branco


def today() -> str:
    return datetime.date.today().strftime("%d/%m/%Y")


class _PlanPainter:
    """O necessário para usar o desenho de ``PlanView`` fora da tela."""

    to_screen = PlanView.to_screen
    _polygon = PlanView._polygon
    _path = PlanView._path
    _rings_path = PlanView._rings_path
    _px = PlanView._px
    _draw_plan = PlanView._draw_plan
    _draw_region = PlanView._draw_region
    _draw_annotations = PlanView._draw_annotations
    _draw_tags = PlanView._draw_tags
    _font = PlanView._font
    _line_px = PlanView._line_px

    def __init__(self, session, plan, scale: float, origin: QPointF, unit: float):
        self.ctx = SimpleNamespace(plan=plan, session=SimpleNamespace(selection=set()))
        self.scale, self.origin, self.unit = scale, origin, unit
        self.show_tags = self.show_structure_tags = self.show_weights = True
        self.show_tag_size = self.show_space_numbers = False
        self.show_view_symbols = True

    def font(self) -> QFont:
        return theme.font()

    def paint(self, painter: QPainter) -> None:
        self._draw_plan(painter)
        self._draw_annotations(painter)
        self._draw_tags(painter)


class _SectionPainter:
    to_screen = SectionView.to_screen
    _path = SectionView._path
    _rings_path = SectionView._rings_path
    _px = SectionView._px
    _line_px = SectionView._line_px
    _draw_region = PlanView._draw_region
    paint_drawing = SectionView.paint

    def __init__(self, drawing, scale: float, origin: QPointF, unit: float):
        self.drawing, self.scale, self.origin, self.unit = drawing, scale, origin, unit
        self.show_weights = True

    def font(self) -> QFont:
        return theme.font()

    def paint(self, painter: QPainter) -> None:
        self.paint_drawing(painter, ())


def _item_painter(doc, item: dict, center: QPointF, px_per_mm: float, unit: float):
    """Pintor da vista centrada em ``center`` (pixels do papel), ou ``None``."""
    scale = px_per_mm * 1000.0 / sheets.scale_of(doc, item)
    box = sheets.view_bounds(doc, item)
    if box is None:
        return None
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    origin = QPointF(center.x() - cx * scale, center.y() + cy * scale)
    with sheets.item_display(doc, item):  # combinação de camadas da vista (spec/ui 18 §6.2)
        if item["kind"] == "plan":
            storey = doc.find(item["storey"])
            return _PlanPainter(None, plan_mod.storey_plan(doc, storey), scale, origin, unit)
        return _SectionPainter(section.draw(doc, doc.find(item["view"])), scale, origin, unit)


def render_sheet(painter: QPainter, doc, sheet, px_per_mm: float, top_left: QPointF,
                 unit: float, date: str) -> list[QRectF]:
    """Desenha a prancha; devolve o retângulo (pixels) de cada vista, na ordem dela."""
    state = sheets.read_state(sheet)
    w, h = sheets.paper(state)

    def at(p) -> QPointF:  # mm do papel (y para cima) → pixels
        return QPointF(top_left.x() + p[0] * px_per_mm, top_left.y() + (h - p[1]) * px_per_mm)

    old_background = C["background"]
    C["background"] = _PAPER  # o que cobre o desenho de baixo é o papel
    try:
        painter.fillRect(QRectF(at((0, h)), at((w, 0))), _PAPER)
        rects = []
        for item in state["views"]:
            center = at(item["at"])
            vw, vh = sheets.view_size(doc, item)
            rects.append(QRectF(center.x() - vw * px_per_mm / 2, center.y() - vh * px_per_mm / 2,
                                vw * px_per_mm, vh * px_per_mm))
            try:
                drawer = _item_painter(doc, item, center, px_per_mm, unit)
            except (OpError, RuntimeError):
                drawer = None
            if drawer is not None:
                painter.save()
                drawer.paint(painter)
                painter.restore()
        strokes, texts = sheets.title_items(doc, sheet, date)
        for stroke in strokes:
            painter.setPen(QPen(QColor(theme.INK), max(unit * 0.5,
                                                       stroke.weight * px_per_mm)))
            painter.setBrush(Qt.NoBrush)
            poly = QPolygonF([at(p) for p in stroke.points])
            if stroke.closed:
                painter.drawPolygon(poly)
            else:
                painter.drawPolyline(poly)
        painter.setPen(QPen(QColor(theme.INK)))
        for text in texts:
            font = theme.font()
            font.setPixelSize(max(1, round(text.height * px_per_mm)))
            painter.setFont(font)
            p = at(text.at)
            painter.drawText(p, text.text)
    finally:
        C["background"] = old_background
    return rects


def export_pdf(path: str, doc, sheet_list, date: str | None = None, dpi: int = 600) -> int:
    """Uma página por prancha, no tamanho do formato; devolve o número de páginas."""
    date = date or today()
    writer = QPdfWriter(path)
    writer.setResolution(dpi)
    writer.setCreator("BrasBim")
    painter = None
    pages = 0
    try:
        for sheet in sheet_list:
            w, h = sheets.paper(sheets.read_state(sheet))
            layout = QPageLayout(QPageSize(QSizeF(w, h), QPageSize.Millimeter),
                                 QPageLayout.Portrait, QMarginsF(0, 0, 0, 0))
            writer.setPageLayout(layout)
            if painter is None:
                painter = QPainter(writer)
                painter.setRenderHint(QPainter.Antialiasing)
            else:
                writer.newPage()
            render_sheet(painter, doc, sheet, dpi / 25.4, QPointF(0, 0), dpi / 96.0, date)
            pages += 1
    finally:
        if painter is not None:
            painter.end()
    return pages


class SheetView(QWidget):
    """Aba da prancha (spec/ui 15 §5): o papel na tela, arrastar as vistas, tirar da
    prancha pelo botão direito."""

    changed = Signal()

    def __init__(self, session, sheet_gid: str, parent=None):
        super().__init__(parent)
        self.session = session
        self.sheet_gid = sheet_gid
        self.zoom = 1.5  # pixels por mm
        self.top_left = QPointF(20, 20)
        self.rects: list[QRectF] = []
        self._drag: dict | None = None
        self._pan: QPointF | None = None
        self._fitted = False
        self.setMinimumSize(300, 200)
        self.setMouseTracking(True)

    @property
    def sheet(self):
        return self.session.doc.find(self.sheet_gid)

    @property
    def title(self) -> str:
        sheet = self.sheet
        return f"Prancha {sheets.read_state(sheet)['number']}" if sheet is not None \
            else "Prancha"

    def fit(self) -> None:
        sheet = self.sheet
        if sheet is None:
            return
        w, h = sheets.paper(sheets.read_state(sheet))
        self.zoom = max(0.2, min((self.width() - 40) / w, (self.height() - 40) / h))
        self.top_left = QPointF((self.width() - w * self.zoom) / 2,
                                (self.height() - h * self.zoom) / 2)
        self._fitted = True
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._fitted:
            self.fit()

    def invalidate(self) -> None:
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(theme.FRAME))
        sheet = self.sheet
        if sheet is not None:
            self.rects = render_sheet(painter, self.session.doc, sheet, self.zoom,
                                      self.top_left, 1.0, today())
            if self._drag is not None and self._drag.get("moved"):
                r = self.rects[self._drag["index"]].translated(self._drag["delta"])
                painter.setPen(QPen(QColor(theme.ACCENT), 1, Qt.DashLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(r)
        painter.end()

    def _index_at(self, pos: QPointF) -> int | None:
        for i in reversed(range(len(self.rects))):
            if self.rects[i].contains(pos):
                return i
        return None

    def mousePressEvent(self, event):
        pos = event.position()
        if event.button() == Qt.MiddleButton:
            self._pan = pos
            return
        index = self._index_at(pos)
        if event.button() == Qt.RightButton and index is not None:
            menu = QMenu(self)
            menu.addAction("Tirar da prancha", lambda: self.session.run(
                lambda: sheets.remove_from_sheet(self.session.doc, self.sheet_gid, index)))
            menu.exec(event.globalPosition().toPoint())
            return
        if event.button() == Qt.LeftButton and index is not None:
            self._drag = {"index": index, "start": pos, "delta": QPointF(0, 0),
                          "moved": False}

    def mouseMoveEvent(self, event):
        pos = event.position()
        if self._pan is not None:
            self.top_left += pos - self._pan
            self._pan = pos
            self.update()
            return
        if self._drag is not None:
            self._drag["delta"] = pos - self._drag["start"]
            self._drag["moved"] = True
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._pan = None
            return
        drag, self._drag = self._drag, None
        if drag is None or not drag["moved"]:
            return
        state = sheets.read_state(self.sheet)
        x, y = state["views"][drag["index"]]["at"]
        d = drag["delta"]
        new = (x + d.x() / self.zoom, y - d.y() / self.zoom)
        self.session.run(lambda: sheets.move_on_sheet(self.session.doc, self.sheet_gid,
                                                      drag["index"], new))

    def wheelEvent(self, event):
        factor = 1.15 ** (event.angleDelta().y() / 120)
        at = event.position()
        mm = (at - self.top_left) / self.zoom
        self.zoom = min(max(self.zoom * factor, 0.1), 50.0)
        self.top_left = at - mm * self.zoom
        self.update()

