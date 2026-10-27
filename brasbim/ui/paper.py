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
import math
from types import SimpleNamespace

from PySide6.QtCore import QMarginsF, QPointF, QRectF, QSizeF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QIcon,
    QPageLayout,
    QPageSize,
    QPainter,
    QPdfWriter,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QMenu,
    QWidget,
)

from brasbim.core import pens
from brasbim.core import plan as plan_mod
from brasbim.core.annotations.prims import DASH_PATTERNS
from brasbim.core.document import OpError
from brasbim.core.drawings import saved_views, section, sheets
from brasbim.ui import theme
from brasbim.ui.measure_box import pick_cursor
from brasbim.ui.paper_select import DRAG_PX, PaperSelection, draw_overlay
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
    tint = PlanView.tint
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


def frame_pen(doc, frame: dict, px_per_mm: float, unit: float) -> QPen:
    """Caneta da moldura: cor e espessura da pena e o tipo de linha (spec/ui 29 §4)."""
    pen_ = pens.resolve(doc, None, paper=True).number(frame["pen"])
    width = max(unit * 0.5, pen_.weight * px_per_mm)
    pen = QPen(QColor(pen_.color), width)
    pen.setCapStyle(Qt.FlatCap)
    pattern = DASH_PATTERNS.get(frame["dash"])
    if pattern:  # traços em mm de papel, na unidade da caneta (a espessura)
        pen.setDashPattern([v * px_per_mm / width for v in pattern])
    return pen


def draw_frame(painter: QPainter, doc, item: dict, rect: QRectF, px_per_mm: float,
               unit: float) -> None:
    frame = item.get("frame")
    if not frame or not frame["show"] or rect.isEmpty():
        return
    painter.setPen(frame_pen(doc, frame, px_per_mm, unit))
    painter.setBrush(Qt.NoBrush)
    painter.drawRect(rect)


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
                if (saved is not None and saved.get("crop")) or item.get("limit"):
                    # recorte da vista salva (spec/ui 25 §2) ou pela alça (spec/ui 29 §3)
                    painter.setClipRect(rects[-1])
                with sheets.item_display(doc, item):
                    drawer.paint(painter)
                painter.restore()
            draw_frame(painter, doc, item, rects[-1], px_per_mm, unit)
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
    """Aba da prancha (spec/ui 15 §5): o papel na tela; seleção pelo cursor como na
    planta, arrastar os desenhos, alças do limite, moldura e botão direito (spec/ui 29)."""

    changed = Signal()

    def __init__(self, session, sheet_gid: str, parent=None):
        super().__init__(parent)
        self.session = session
        self.sheet_gid = sheet_gid
        self.zoom = 1.5  # pixels por mm
        self.top_left = QPointF(20, 20)
        self.rects: list[QRectF] = []
        self.accumulate = lambda: True  # Editar > Modo de seleção (posto pela janela)
        self.show_limits = lambda: True  # Exibir > Limites dos desenhos (idem)
        self.selection = PaperSelection(self._pick, self._outlines,
                                        lambda: self.accumulate())
        self._handle: dict | None = None  # alça do limite sendo levada
        self._pan: QPointF | None = None
        self._fitted = False
        self.setMinimumSize(300, 200)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(pick_cursor())
        self.setAcceptDrops(True)  # vistas salvas arrastadas do painel (spec/ui 25 §5)

    @property
    def sheet(self):
        return self.session.doc.find(self.sheet_gid)

    @property
    def items(self) -> list[dict]:
        sheet = self.sheet
        return sheets.read_state(sheet)["views"] if sheet is not None else []

    @property
    def selected(self) -> set[int]:
        return self.selection.selected

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
        self.selection.prune(len(self.items))
        self.update()

    # itens no papel (mm)

    def _rects_mm(self) -> list[tuple[float, float, float, float]]:
        doc = self.session.doc
        out = []
        for item in self.items:
            try:
                out.append(sheets.item_rect(doc, item))
            except (OpError, RuntimeError):
                out.append((*item["at"], *item["at"]))
        return out

    def _outlines(self):
        return [[([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], True)]
                for x0, y0, x1, y1 in self._rects_mm()]

    def _pick(self, p) -> int | None:
        reach = 3.0 / self.zoom
        rects = self._rects_mm()
        for i in reversed(range(len(rects))):
            x0, y0, x1, y1 = rects[i]
            if x0 - reach <= p[0] <= x1 + reach and y0 - reach <= p[1] <= y1 + reach:
                return i
        return None

    def _handles(self) -> dict[str, tuple[float, float]]:
        """Alças do limite do desenho selecionado sozinho (spec/ui 29 §3)."""
        if len(self.selected) != 1:
            return {}
        index = next(iter(self.selected))
        items = self.items
        if index >= len(items):
            return {}
        try:
            return sheets.handle_points(self.session.doc, items[index])
        except (OpError, RuntimeError):
            return {}

    def _handle_at(self, p) -> str | None:
        reach = 6.0 / self.zoom
        found = [(math.dist(p, q), k) for k, q in self._handles().items()
                 if math.dist(p, q) <= reach]
        return min(found)[1] if found else None

    # pintura

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(theme.FRAME))
        sheet = self.sheet
        if sheet is not None:
            self.rects = render_sheet(painter, self.session.doc, sheet, self.zoom,
                                      self.top_left, 1.0, today())
            self._paint_marks(painter)
        painter.end()

    def at(self, p) -> QPointF:
        """mm do papel (y para cima) → pixels da aba."""
        _, h = sheets.paper_of(self.session.doc, sheets.read_state(self.sheet))
        return QPointF(self.top_left.x() + p[0] * self.zoom,
                       self.top_left.y() + (h - p[1]) * self.zoom)

    def _paint_marks(self, painter: QPainter) -> None:
        """Limites tracejados (só na tela), seleção, alças, arrasto e janela/laço."""
        offset = self.selection.offset()
        handle = self._handle
        for i, (x0, y0, x1, y1) in enumerate(self._rects_mm()):
            chosen = i in self.selected
            if handle is not None and handle["index"] == i:
                x0, y0, x1, y1 = handle["rect"]
            if not chosen and not self.show_limits():
                continue
            color = QColor(theme.ACCENT if chosen else theme.INK_SOFT)
            painter.setPen(QPen(color, 1.5 if chosen else 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(QRectF(self.at((x0, y1)), self.at((x1, y0))))
            if chosen and offset is not None:
                dx, dy = offset
                painter.setPen(QPen(QColor(theme.ACCENT), 1, Qt.DashLine))
                painter.drawRect(QRectF(self.at((x0 + dx, y1 + dy)),
                                        self.at((x1 + dx, y0 + dy))))
        if offset is None and handle is None:
            for q in self._handles().values():
                c = self.at(q)
                painter.setPen(QPen(QColor(theme.ACCENT), 1))
                painter.setBrush(QColor(theme.FIELD))
                painter.drawRect(QRectF(c.x() - 4, c.y() - 4, 8, 8))
        draw_overlay(painter, self.selection, self.at)

    def to_paper(self, pos: QPointF) -> tuple[float, float]:
        """Pixels da aba → mm do papel (y para cima)."""
        _, h = sheets.paper_of(self.session.doc, sheets.read_state(self.sheet))
        return ((pos.x() - self.top_left.x()) / self.zoom,
                h - (pos.y() - self.top_left.y()) / self.zoom)

    # ações

    def context_menu(self, pos: QPointF, index: int | None) -> QMenu:
        """Botão direito: no desenho, moldura, limite e tirar (vale para a seleção); no
        papel, pôr uma vista salva no ponto clicado (spec/ui 25 §5, 29 §4)."""
        from brasbim.core.drawings import saved_views as sv

        doc = self.session.doc
        menu = QMenu(self)
        if index is not None:
            if index not in self.selected:
                self.selection.selected = {index}
                self.update()
            chosen = sorted(self.selected)
            items = self.items
            if len(chosen) == 1 and sheets.is_3d(doc, items[index]):
                menu.addAction("Largura no papel…", lambda: self.ask_width(index))
            menu.addAction("Moldura…", lambda: self.ask_frame(chosen))
            fit = menu.addAction("Ajustar o limite ao desenho",
                                 lambda: self.reset_limits(chosen))
            fit.setEnabled(any(items[i].get("limit") for i in chosen))
            menu.addSeparator()
            menu.addAction("Tirar da prancha", lambda: self.delete_selected())
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

    def delete_selected(self) -> bool:
        """Delete: tira da prancha os desenhos selecionados (spec/ui 29 §2)."""
        chosen = sorted(self.selected)
        if not chosen:
            return False
        done = self.session.run(lambda: sheets.remove_many_from_sheet(
            self.session.doc, self.sheet_gid, chosen))
        if done:
            self.selection.selected = set()
        return done

    def move_selected(self, delta) -> bool:
        chosen = sorted(self.selected)
        return bool(chosen) and self.session.run(lambda: sheets.move_many_on_sheet(
            self.session.doc, self.sheet_gid, chosen, delta))

    def reset_limits(self, indices) -> bool:
        doc = self.session.doc
        done = False
        for i in indices:
            if self.items[i].get("limit"):
                done = self.session.run(
                    lambda i=i: sheets.set_item_limit(doc, self.sheet_gid, i, None)) or done
        return done

    def set_frame(self, indices, show: bool, dash: str, pen: int) -> bool:
        return self.session.run(lambda: sheets.set_item_frame(
            self.session.doc, self.sheet_gid, indices, show, dash, pen))

    def ask_frame(self, indices) -> bool:
        dialog = FrameDialog(self.session.doc, self.items[indices[0]].get("frame"), self)
        if dialog.exec() != QDialog.Accepted:
            return False
        return self.set_frame(indices, *dialog.values())

    def ask_width(self, index: int) -> None:
        from PySide6.QtWidgets import QInputDialog

        item = self.items[index]
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

    # mouse e teclado (p em mm do papel)

    def press(self, p, shift: bool = False, ctrl: bool = False) -> None:
        handle = None if shift or ctrl or self.selection.drag else self._handle_at(p)
        if handle is not None:
            index = next(iter(self.selected))
            self._handle = {"index": index, "which": handle,
                            "rect": sheets.item_rect(self.session.doc, self.items[index])}
            return
        self.selection.press(p, shift, ctrl)
        self.update()

    def move(self, p) -> None:
        h = self._handle
        if h is not None:
            item = self.items[h["index"]]
            limit, at = sheets.limit_from_handle(self.session.doc, item, h["which"], p)
            w, hh = sheets.view_size(self.session.doc, {**item, "limit": limit})
            h["rect"] = (at[0] - w / 2, at[1] - hh / 2, at[0] + w / 2, at[1] + hh / 2)
            h["moved"] = True
        else:
            self.selection.move(p, DRAG_PX / self.zoom)
        self.update()

    def release(self, p, shift: bool = False) -> None:
        h, self._handle = self._handle, None
        if h is not None:
            if h.get("moved"):
                doc = self.session.doc
                limit, at = sheets.limit_from_handle(doc, self.items[h["index"]],
                                                     h["which"], p)
                self.session.run(lambda: sheets.set_item_limit(doc, self.sheet_gid,
                                                               h["index"], limit, at))
            self.update()
            return
        delta = self.selection.release(p, shift)
        if delta is not None and math.hypot(*delta) > 1e-9:
            self.move_selected(delta)
        self.update()

    def escape(self) -> bool:
        if self._handle is not None:
            self._handle = None
            self.update()
            return True
        done = self.selection.escape()
        self.update()
        return done

    def mousePressEvent(self, event):
        pos = event.position()
        self.setFocus()
        if event.button() == Qt.MiddleButton:
            self._pan = pos
            return
        if event.button() == Qt.RightButton:
            self.context_menu(pos, self._pick(self.to_paper(pos))).exec(
                event.globalPosition().toPoint())
            return
        if event.button() == Qt.LeftButton:
            mods = event.modifiers()
            self.press(self.to_paper(pos), bool(mods & Qt.ShiftModifier),
                       bool(mods & Qt.ControlModifier))

    def mouseMoveEvent(self, event):
        pos = event.position()
        if self._pan is not None:
            self.top_left += pos - self._pan
            self._pan = pos
            self.update()
            return
        self.move(self.to_paper(pos))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._pan = None
            return
        if event.button() == Qt.LeftButton:
            self.release(self.to_paper(event.position()),
                         bool(event.modifiers() & Qt.ShiftModifier))

    def leaveEvent(self, event):
        if self.selection.hover is not None:
            self.selection.hover = None
            self.update()
        super().leaveEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.escape()
        elif event.key() == Qt.Key_Delete:
            self.delete_selected()
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, event):
        factor = 1.15 ** (event.angleDelta().y() / 120)
        at = event.position()
        mm = (at - self.top_left) / self.zoom
        self.zoom = min(max(self.zoom * factor, 0.1), 50.0)
        self.top_left = at - mm * self.zoom
        self.update()


class FrameDialog(QDialog):
    """Moldura do desenho na prancha (spec/ui 29 §4): mostrar, tipo de linha e pena."""

    DASH_NAMES = (("Contínua", "solid"), ("Tracejada", "dashed"), ("Traço-ponto", "dashdot"))

    def __init__(self, doc, frame: dict | None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Moldura do desenho")
        frame = frame or {"show": True, "dash": "solid", "pen": 3}
        form = QFormLayout(self)
        self.show_frame = QCheckBox("Mostrar moldura")
        self.show_frame.setChecked(bool(frame["show"]))
        form.addRow(self.show_frame)
        self.dash = QComboBox()
        for text, key in self.DASH_NAMES:
            self.dash.addItem(text, key)
        self.dash.setCurrentIndex(max(0, self.dash.findData(frame["dash"])))
        form.addRow("Tipo de linha", self.dash)
        self.pen = QComboBox()
        table = pens.resolve(doc).table
        for number in sorted(table["pens"], key=int):
            data = table["pens"][number]
            swatch = QPixmap(14, 14)
            swatch.fill(QColor(data["color"]))
            border = QPainter(swatch)  # borda clara: a pena escura aparece no tema escuro
            border.setPen(QColor(theme.INK_SOFT))
            border.drawRect(0, 0, 13, 13)
            border.end()
            weight = f"{data['weight']:g}".replace(".", ",")
            note = f" — {data['note']}" if data.get("note") else ""
            self.pen.addItem(QIcon(swatch), f"Pena {number}: {weight} mm{note}", int(number))
        self.pen.setCurrentIndex(max(0, self.pen.findData(frame["pen"])))
        form.addRow("Pena", self.pen)
        for widget in (self.dash, self.pen):
            widget.setEnabled(self.show_frame.isChecked())
            self.show_frame.toggled.connect(widget.setEnabled)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self) -> tuple[bool, str, int]:
        return self.show_frame.isChecked(), self.dash.currentData(), self.pen.currentData()
