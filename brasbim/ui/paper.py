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
import json
from types import SimpleNamespace

from PySide6.QtCore import QMarginsF, QPointF, QRectF, QSizeF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QPageLayout,
    QPageSize,
    QPainter,
    QPdfWriter,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import QMenu, QWidget

from brasbim.core import pens
from brasbim.core import plan as plan_mod
from brasbim.core.document import OpError
from brasbim.core.drawings import saved_views, section, sheets
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
        self.show_tag_size = self.show_space_numbers = self.show_object_tags = False
        self.show_view_symbols = True
        self.pens = pens.DEFAULT

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
        self.pens = pens.DEFAULT

    def font(self) -> QFont:
        return theme.font()

    def paint(self, painter: QPainter) -> None:
        self.paint_drawing(painter, ())


class _ImagePainter:
    """Vista 3D salva na prancha: a imagem do 3D no retângulo dela (spec/ui 25 §5)."""

    def __init__(self, image, rect: QRectF):
        self.image, self.rect = image, rect

    def paint(self, painter: QPainter) -> None:
        if self.image is None:
            painter.setPen(QPen(QColor(theme.INK_SOFT), 1, Qt.DashLine))
            painter.drawRect(self.rect)
            painter.drawText(self.rect, Qt.AlignCenter, "Vista 3D (sem OpenGL)")
            return
        painter.drawImage(self.rect, self.image)
        painter.setPen(QPen(QColor(theme.INK), 0))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(self.rect)


MAX_3D_PX = 4096  # lado maior da imagem do 3D na prancha
DPI_3D = 300  # resolução da imagem do 3D no PDF


_images: dict[tuple, object] = {}  # imagens do 3D já feitas (refeitas quando o modelo muda)


def invalidate_images() -> None:
    _images.clear()


def _image_3d(doc, state: dict, rect: QRectF, px_per_mm: float):
    from brasbim.ui import saved_views_ui

    w, h = rect.width(), rect.height()
    k = min(1.0, DPI_3D / 25.4 / max(px_per_mm, 1e-9), MAX_3D_PX / max(w, h, 1.0))
    size = (round(w * k), round(h * k))
    key = (id(doc), json.dumps(state, sort_keys=True), size)
    if key not in _images:
        if len(_images) > 16:
            _images.clear()
        _images[key] = saved_views_ui.render_3d(doc, state, *size)
    return _images[key]


def _item_painter(doc, item: dict, center: QPointF, px_per_mm: float, unit: float):
    """Pintor da vista centrada em ``center`` (pixels do papel), ou ``None``; com a tabela
    de penas da vista salva ou a da janela (spec/ui 27 §4)."""
    drawer = _item_drawer(doc, item, center, px_per_mm, unit)
    if drawer is not None and hasattr(drawer, "pens"):
        saved = sheets.saved_state(doc, item) if item["kind"] == "saved" else None
        drawer.pens = pens.resolve(doc, saved.get("pens") if saved else None, paper=True)
    return drawer


def _item_drawer(doc, item: dict, center: QPointF, px_per_mm: float, unit: float):
    saved = sheets.saved_state(doc, item) if item["kind"] == "saved" else None
    if item["kind"] == "saved" and saved is None:
        return None
    if saved is not None and saved["kind"] == "3d":
        w, h = sheets.view_size(doc, item)
        rect = QRectF(center.x() - w * px_per_mm / 2, center.y() - h * px_per_mm / 2,
                      w * px_per_mm, h * px_per_mm)
        return _ImagePainter(_image_3d(doc, saved, rect, px_per_mm), rect)
    scale = px_per_mm * 1000.0 / sheets.scale_of(doc, item)
    box = sheets.view_bounds(doc, item)
    if box is None:
        return None
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    origin = QPointF(center.x() - cx * scale, center.y() + cy * scale)
    with sheets.item_display(doc, item):  # camadas e escala da vista (spec/ui 18 §6.2, 25)
        if saved is not None and saved["kind"] == "plan":
            painter = _PlanPainter(None, saved_views.plan_of(doc, saved), scale, origin, unit)
            for name, value in saved_views.options(saved).items():
                if name.startswith("show_") and name != "show_above":
                    setattr(painter, name, value)
            return painter
        if saved is not None:
            drawer = _SectionPainter(section.draw(doc, doc.find(saved["view"]),
                                                  saved["scale"]), scale, origin, unit)
            drawer.show_weights = saved_views.options(saved)["show_weights"]
            return drawer
        if item["kind"] == "plan":
            storey = doc.find(item["storey"])
            return _PlanPainter(None, plan_mod.storey_plan(doc, storey), scale, origin, unit)
        return _SectionPainter(section.draw(doc, doc.find(item["view"])), scale, origin, unit)


def draw_paper_text(painter: QPainter, text, p: QPointF, px_per_mm: float) -> None:
    """Texto do carimbo: âncora na base, à esquerda, no meio ou à direita (spec/ui 26)."""
    font = theme.font()
    font.setPixelSize(max(1, round(text.height * px_per_mm)))
    font.setBold(bool(getattr(text, "bold", False)))
    painter.setFont(font)
    width = QFontMetricsF(font).horizontalAdvance(text.text)
    dx = {"center": -width / 2, "right": -width}.get(text.halign, 0.0)
    painter.drawText(QPointF(p.x() + dx, p.y()), text.text)


def render_sheet(painter: QPainter, doc, sheet, px_per_mm: float, top_left: QPointF,
                 unit: float, date: str) -> list[QRectF]:
    """Desenha a prancha; devolve o retângulo (pixels) de cada vista, na ordem dela."""
    state = sheets.read_state(sheet)
    w, h = sheets.paper_of(doc, state)

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
                saved = sheets.saved_state(doc, item) if item["kind"] == "saved" else None
                if saved is not None and saved.get("crop"):
                    painter.setClipRect(rects[-1])  # recorte da vista salva (spec/ui 25 §2)
                with sheets.item_display(doc, item):
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
            draw_paper_text(painter, text, at(text.at), px_per_mm)
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
            w, h = sheets.paper_of(doc, sheets.read_state(sheet))
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
        self.setAcceptDrops(True)  # vistas salvas arrastadas do painel (spec/ui 25 §5)

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
        w, h = sheets.paper_of(self.session.doc, sheets.read_state(sheet))
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

    def to_paper(self, pos: QPointF) -> tuple[float, float]:
        """Pixels da aba → mm do papel (y para cima)."""
        _, h = sheets.paper_of(self.session.doc, sheets.read_state(self.sheet))
        return ((pos.x() - self.top_left.x()) / self.zoom,
                h - (pos.y() - self.top_left.y()) / self.zoom)

    def context_menu(self, pos: QPointF, index: int | None) -> QMenu:
        """Botão direito: na vista, tirar (e a largura da vista 3D); no papel, pôr uma vista
        salva no ponto clicado (spec/ui 25 §5)."""
        from brasbim.core.drawings import saved_views as sv

        doc = self.session.doc
        menu = QMenu(self)
        if index is not None:
            item = sheets.read_state(self.sheet)["views"][index]
            saved = sheets.saved_state(doc, item) if item["kind"] == "saved" else None
            if saved is not None and saved["kind"] == "3d":
                menu.addAction("Largura no papel…", lambda: self.ask_width(index))
            menu.addAction("Tirar da prancha", lambda: self.session.run(
                lambda: sheets.remove_from_sheet(doc, self.sheet_gid, index)))
            return menu
        at = self.to_paper(pos)
        sub = menu.addMenu("Pôr vista salva")
        entities = sv.all_saved_views(doc)
        for entity in entities:
            sub.addAction(sv.read_state(entity)["name"],
                          lambda g=entity.GlobalId: self.put_saved(g, at))
        if not entities:
            sub.addAction("(nenhuma vista salva)").setEnabled(False)
        return menu

    def put_saved(self, gid: str, at) -> bool:
        return self.session.run(lambda: sheets.add_to_sheet(
            self.session.doc, self.sheet_gid, {"kind": "saved", "saved": gid}, at=at))

    def ask_width(self, index: int) -> None:
        from PySide6.QtWidgets import QInputDialog

        item = sheets.read_state(self.sheet)["views"][index]
        width, ok = QInputDialog.getDouble(self, "Largura no papel", "Largura (mm)",
                                           sheets.view_size(self.session.doc, item)[0], 10,
                                           2000, 1)
        if ok:
            self.session.run(lambda: sheets.set_item_width(self.session.doc, self.sheet_gid,
                                                           index, width))

    def dragEnterEvent(self, event):
        from brasbim.ui.saved_views_ui import MIME

        if event.mimeData().hasFormat(MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dropEvent(self, event):
        from brasbim.ui.saved_views_ui import MIME

        data = event.mimeData()
        if data.hasFormat(MIME):
            gid = bytes(data.data(MIME)).decode()
            if self.put_saved(gid, self.to_paper(event.position())):
                event.acceptProposedAction()

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
        if event.button() == Qt.RightButton:
            self.context_menu(pos, index).exec(event.globalPosition().toPoint())
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

