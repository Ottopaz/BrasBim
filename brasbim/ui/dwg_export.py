# SPDX-License-Identifier: GPL-3.0-or-later
"""Exportar DWG/DXF (``spec/ui/41-dwg-solidos-perfil-complexo.md`` §2).

O desenho é o mesmo da tela e do PDF: os pintores de ``paper`` (planta, corte, vista
salva) pintam num ``DxfPainter``, que faz o papel do ``QPainter`` e grava o que recebe
(linhas, áreas cheias e textos) com ``ezdxf``, recortado com ``shapely``.

- **Vista** (planta, corte ou fachada, vista salva): espaço do modelo em **centímetros**
  (resposta (a) do revisor), na posição do projeto (a planta no 0,0 do projeto; o corte
  nos eixos dele: ao longo da linha e a cota).
- **Prancha**: espaço do papel em milímetros, um layout com o nome da prancha; cada
  desenho posto vira um **bloco** com o desenho em centímetros, inserido na escala dele e
  recortado pelo limite; moldura, quadro e carimbo em linhas e textos.
- **Camadas do DWG = camadas do BrasBim**, na ordem delas: o desenho é feito uma vez por
  camada (``display_layers.only_layer``); o que não é de camada nenhuma vai para a
  ``0``. Cor da pena em cor verdadeira, com a cor do AutoCAD (ACI) mais próxima junto
  (o DWG 2000 só tem a ACI). Espessura da pena em cada objeto.
- **DWG**: o DXF (versão 2000) passa pelo ``dxf2dwg`` do GNU LibreDWG
  (``core.imports.libredwg``), que grava DWG 2000; sem o conversor, ``MissingWriter``.
"""

from __future__ import annotations

import contextlib
import math
import os
import re
import shutil
import tempfile
from pathlib import Path

import ezdxf
import shapely
from ezdxf.colors import DXF_DEFAULT_COLORS, int2rgb
from ezdxf.enums import TextEntityAlignment
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFontMetricsF, QPainterPath, QPen, QTransform
from shapely.geometry import LineString, Point, Polygon, box

from brasbim.core import display_layers
from brasbim.core.drawings import sheets
from brasbim.core.imports import libredwg
from brasbim.ui import paper
from brasbim.ui.plan_view import C

UNITS_PER_M = 100.0  # centímetros por metro: unidade das vistas no DWG
INSUNITS_CM, INSUNITS_MM = 5, 4
PX_PER_MM = 10.0  # resolução com que os pintores desenham (texto e hachura legíveis)
SHEET_LAYER = "Prancha"  # moldura, quadro e carimbo
FORMATS = ("dwg", "dxf")
# Espessuras do DXF (centésimos de mm)
_WEIGHTS = (0, 5, 9, 13, 15, 18, 20, 25, 30, 35, 40, 50, 53, 60, 70, 80, 90, 100, 106, 120,
            140, 158, 200, 211)
_LINETYPES = {Qt.DashLine: "DASHED", Qt.DashDotLine: "DASHDOT", Qt.DotLine: "DOT"}
_BAD_NAME = re.compile(r'[<>/\\":;?*|=`,]')  # proibidos em nomes de camada e de bloco


class MissingWriter(RuntimeError):
    """Não há ``dxf2dwg`` neste computador: só dá para gravar DXF (ou baixar o
    conversor)."""


def layer_name(text: str) -> str:
    return _BAD_NAME.sub("-", text).strip() or "0"


def file_name(text: str) -> str:
    """Nome de arquivo a partir do nome do item (sem os caracteres proibidos)."""
    return re.sub(r'[<>:"/\\|?*]', "-", text).strip(" .") or "desenho"


# --- cores e espessuras -----------------------------------------------------------------

_aci: dict[int, int] = {}


def nearest_aci(rgb: tuple[int, int, int]) -> int:
    """Cor do AutoCAD (1–255) mais próxima; preto e branco viram a 7 (que o CAD mostra
    preta no papel branco e branca no fundo escuro)."""
    key = (rgb[0] << 16) | (rgb[1] << 8) | rgb[2]
    if key not in _aci:
        if max(rgb) < 40 or min(rgb) > 235:
            _aci[key] = 7
        else:
            _aci[key] = min(range(1, 256), key=lambda i: sum(
                (a - b) ** 2 for a, b in zip(int2rgb(DXF_DEFAULT_COLORS[i]), rgb,
                                             strict=True)))
    return _aci[key]


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


_EVERYWHERE = box(-1e12, -1e12, 1e12, 1e12)


class DxfPainter:
    """Faz o papel do ``QPainter`` para os pintores de ``paper`` e grava em ``target``
    (espaço do modelo, do papel ou um bloco do DXF).

    ``out`` leva os pixels do pintor às unidades do DXF (com o y para cima); ``mm_per_px``
    dá a espessura em mm de papel; ``clip`` (unidades do DXF) recorta tudo. ``layer`` é a
    camada do que for desenhado; ``seen`` guarda o que já foi gravado na camada ``0``,
    para não repetir nas passadas das camadas."""

    def __init__(self, target, out: QTransform, mm_per_px: float, clip=None):
        self.target = target
        self.out = out
        self.mm_per_px = mm_per_px
        self.area = clip if clip is not None else _EVERYWHERE
        self.clip = self.area
        shapely.prepare(self.clip)
        self.t = QTransform()
        self.pen = QPen()
        self.brush = QBrush()
        self.font = None
        self._stack = []
        self.layer = "0"
        self.ltscale: float | None = None  # escala do tipo de linha em cada objeto
        self.seen: set | None = None  # ``set`` = gravando a camada 0; ``frozenset`` = pular
        self.count = 0  # objetos gravados

    # --- estado ---------------------------------------------------------------------

    def save(self) -> None:
        self._stack.append((QTransform(self.t), QPen(self.pen), QBrush(self.brush),
                            self.font, self.clip))

    def restore(self) -> None:
        self.t, self.pen, self.brush, self.font, self.clip = self._stack.pop()

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

    def setClipRect(self, rect: QRectF, op=Qt.ReplaceClip) -> None:
        path = QPainterPath()
        path.addRect(rect)
        self.setClipPath(path, op)

    # --- desenho --------------------------------------------------------------------

    def _map(self, p: QPointF) -> tuple[float, float]:
        q = self.out.map(self.t.map(p))
        return q.x(), q.y()

    def _rings(self, path: QPainterPath) -> list[list[tuple[float, float]]]:
        out = self.t * self.out
        return [[(q.x(), q.y()) for q in out.map(poly)]
                for poly in path.toSubpathPolygons()]

    def _shape(self, path: QPainterPath):
        """Área do caminho, par‑ímpar entre os anéis."""
        found = Polygon()
        for ring in self._rings(path):
            if len(ring) >= 3:
                found = found.symmetric_difference(Polygon(ring).buffer(0))
        return found

    def _new(self, key) -> bool:
        """``False`` se o objeto já foi para a camada 0 (não repete); senão anota."""
        if self.seen is None:
            return True
        if isinstance(self.seen, frozenset):
            return key not in self.seen
        self.seen.add(key)
        return True

    @staticmethod
    def _key(kind: str, points, *extra) -> tuple:
        return (kind, tuple((round(x, 4), round(y, 4)) for x, y in points), *extra)

    def _attribs(self, color: QColor) -> dict:
        rgb = (color.red(), color.green(), color.blue())
        return {"layer": self.layer, "color": nearest_aci(rgb),
                "true_color": ezdxf.rgb2int(rgb)}

    def _stroke(self, ring) -> None:
        if self.pen.style() == Qt.NoPen or len(ring) < 2:
            return
        color = self.pen.color()
        if color.alpha() == 0 or color.rgb() == C["background"].rgb():
            return  # da cor do papel (faces escondidas do corte): no DXF não cobre nada
        attribs = self._attribs(color)
        width = self.pen.widthF() * math.sqrt(abs(self.t.determinant())) * self.mm_per_px
        attribs["lineweight"] = _lineweight(width)
        linetype = _LINETYPES.get(self.pen.style())
        if linetype:
            attribs["linetype"] = linetype
            if self.ltscale:
                attribs["ltscale"] = self.ltscale
        if not self._new(self._key("line", ring, attribs["true_color"],
                                   attribs["lineweight"], linetype)):
            return
        closed = len(ring) > 2 and math.dist(ring[0], ring[-1]) < 1e-9
        line = LineString(ring)
        if self.clip.contains(line):
            self.target.add_lwpolyline(ring[:-1] if closed else ring, close=closed,
                                       dxfattribs=attribs)
            self.count += 1
            return
        for piece in _lines(line.intersection(self.clip)):
            self.target.add_lwpolyline(list(piece.coords), dxfattribs=attribs)
            self.count += 1

    def _fill(self, path: QPainterPath, color: QColor) -> None:
        if color.alpha() == 0 or color.rgb() == C["background"].rgb():
            return  # fundo da cor do papel: no DXF não cobre nada
        found = _polygons(self._shape(path).intersection(self.clip))
        if not found:
            return
        rgb = (color.red(), color.green(), color.blue())
        if not self._new(self._key("fill", [p for poly in found
                                            for p in poly.exterior.coords], rgb)):
            return
        hatch = self.target.add_hatch(dxfattribs=self._attribs(color))
        hatch.set_solid_fill(color=nearest_aci(rgb), rgb=rgb)
        if color.alpha() < 255 and self.target.doc.dxfversion >= "AC1018":
            hatch.transparency = 1.0 - color.alpha() / 255.0
        for poly in found:
            hatch.paths.add_polyline_path(list(poly.exterior.coords)[:-1], is_closed=True,
                                          flags=ezdxf.const.BOUNDARY_PATH_EXTERNAL)
            for hole in poly.interiors:
                hatch.paths.add_polyline_path(list(hole.coords)[:-1], is_closed=True)
        self.count += 1

    def drawPath(self, path: QPainterPath) -> None:
        if self.brush.style() != Qt.NoBrush:
            self._fill(path, self.brush.color())
        for ring in self._rings(path):
            self._stroke(ring)

    def fillPath(self, path: QPainterPath, brush) -> None:
        self._fill(path, QBrush(brush).color())

    def fillRect(self, rect: QRectF, brush) -> None:
        path = QPainterPath()
        path.addRect(QRectF(rect))
        self.fillPath(path, brush)

    def drawRect(self, rect: QRectF) -> None:
        path = QPainterPath()
        path.addRect(QRectF(rect))
        self.drawPath(path)

    def drawPolygon(self, polygon) -> None:
        path = QPainterPath()
        path.addPolygon(polygon)
        path.closeSubpath()
        self.drawPath(path)

    def drawPolyline(self, polygon) -> None:
        self._stroke([self._map(q) for q in polygon])

    def drawLine(self, a: QPointF, b: QPointF) -> None:
        self._stroke([self._map(a), self._map(b)])

    def drawImage(self, rect: QRectF, _image) -> None:
        """Vista 3D na prancha: no DWG fica só o retângulo dela (a imagem vai no PDF)."""

    def drawText(self, *args) -> None:
        """``(QRectF, alinhamento, texto)`` ou ``(QPointF, texto)`` (linha de base)."""
        metrics = QFontMetricsF(self.font)
        if len(args) == 3:
            rect, flags, text = args
            if flags & Qt.AlignHCenter:  # centrado: a linha de base calculada aqui
                at = QPointF(rect.center().x() - metrics.horizontalAdvance(text) / 2,
                             rect.center().y() + metrics.capHeight() / 2)
            else:
                at = QPointF(rect.left(), rect.bottom() - metrics.descent())
        else:
            at, text = args
        # Sempre à esquerda na linha de base: o ``dxf2dwg`` perde o segundo ponto de
        # alinhamento dos textos centrados (o CAD os poria no 0,0).
        align = TextEntityAlignment.LEFT
        p = self._map(at)
        if not text or not self.clip.contains(Point(p)):
            return
        whole = self.t * self.out
        k = math.sqrt(abs(whole.determinant()))
        o, x = whole.map(QPointF(0, 0)), whole.map(QPointF(1, 0))
        angle = math.degrees(math.atan2(x.y() - o.y(), x.x() - o.x()))
        attribs = self._attribs(self.pen.color())
        attribs["rotation"] = angle
        if not self._new(self._key("text", [p], text, round(angle, 3))):
            return
        self.target.add_text(text, height=metrics.capHeight() * k,
                             dxfattribs=attribs).set_placement(p, align=align)
        self.count += 1


# --- documento e camadas ----------------------------------------------------------------


def new_document(fmt: str):
    """DXF novo: 2018 para o DXF; 2000 para virar DWG 2000 (o que o ``dxf2dwg`` grava)."""
    doc = ezdxf.new("R2000" if fmt == "dwg" else "R2018", setup=True)
    doc.header["$MEASUREMENT"] = 1
    return doc


def _passes(doc) -> list[tuple[str, str | None]]:
    """(camada do DXF, camada do BrasBim) na ordem do BrasBim, só as visíveis e com
    elementos; antes, ``("0", "")``: o que não é de camada nenhuma. Sem camadas no
    projeto, uma passada só."""
    config = display_layers.read_config(doc)
    if config is None:
        return [("0", None)]
    out = [("0", "")]
    for lay in [*config["layers"], {"id": display_layers.NONE,
                                    "name": display_layers.NONE_NAME}]:
        if lay["id"] in doc.display.hidden or not display_layers.members(doc, lay["id"]):
            continue
        out.append((layer_name(lay["name"]), lay["id"]))
    return out


def _paint_layers(dxf, doc, painter: DxfPainter, make) -> None:
    """Desenha camada por camada: ``make()`` dá o pintor da vista (refeito em cada
    passada, com a planta ou o corte só daquela camada)."""
    base: set = set()
    for name, layer_id in _passes(doc):
        if name not in dxf.layers:
            dxf.layers.add(name)
        painter.layer = name
        painter.seen = base if layer_id == "" else frozenset(base)
        context = display_layers.only_layer(doc, layer_id) if layer_id is not None \
            else contextlib.nullcontext()
        with context:
            drawer = make()
            if drawer is not None:
                drawer.paint(painter)
    painter.seen = None


@contextlib.contextmanager
def _paper_background():
    """O que cobre o desenho de baixo é o papel (como na prancha e no PDF)."""
    old = C["background"]
    C["background"] = paper._PAPER
    try:
        yield
    finally:
        C["background"] = old


# --- vistas -----------------------------------------------------------------------------


def item_of(kind: str, gid: str) -> dict:
    """Item (como o da prancha) da planta (``plan``, GlobalId do pavimento), do corte ou
    fachada (``view``) ou da vista salva (``saved``)."""
    key = {"plan": "storey", "view": "view", "saved": "saved"}[kind]
    return {"kind": kind, key: gid}


def _drawer_at_origin(doc, item: dict):
    """Pintor da vista com o 0,0 do projeto (ou da vista) no 0,0 dos pixels."""
    drawer = paper._item_painter(doc, item, QPointF(0, 0), PX_PER_MM, PX_PER_MM * 25.4 / 96)
    if drawer is None or not hasattr(drawer, "origin"):
        return None
    drawer.origin = QPointF(0, 0)
    return drawer


def write_view(dxf, doc, item: dict) -> int:
    """A vista no espaço do modelo, em centímetros. Devolve o número de objetos."""
    den = sheets.scale_of(doc, item)
    if den is None:
        raise ValueError("a vista 3D não vai para o DWG (exporte a imagem ou o PDF)")
    k = UNITS_PER_M / (PX_PER_MM * 1000.0 / den)  # cm por pixel
    painter = DxfPainter(dxf.modelspace(), QTransform(k, 0, 0, -k, 0, 0), 1 / PX_PER_MM)
    dxf.header["$INSUNITS"] = INSUNITS_CM
    dxf.header["$LTSCALE"] = 0.6 * den  # traço de ~8 mm no papel, na escala da vista
    with _paper_background(), sheets.item_display(doc, item):
        _paint_layers(dxf, doc, painter, lambda: _drawer_at_origin(doc, item))
    return painter.count


# --- pranchas ---------------------------------------------------------------------------


def sheet_title(state: dict) -> str:
    number = state["number"] or ""
    return f"{number} {state['title']}".strip() if state["title"] \
        else f"Prancha {number}".strip()


def write_sheet(dxf, doc, sheet, date: str | None = None) -> int:
    """A prancha no espaço do papel, em mm; cada desenho num bloco. Devolve o número de
    objetos."""
    date = date or paper.today()
    state = sheets.read_state(sheet)
    w, h = sheets.paper_of(doc, state)
    name = layer_name(sheet_title(state))
    layout = dxf.layouts.get("Layout1") if "Layout1" in dxf.layouts else None
    if layout is not None:
        dxf.layouts.rename("Layout1", name)
    else:
        layout = dxf.layouts.new(name)
    layout.page_setup(size=(w, h), margins=(0, 0, 0, 0), units="mm")
    dxf.header["$INSUNITS"] = INSUNITS_MM
    dxf.header["$LTSCALE"] = 6.0
    p = PX_PER_MM
    unit = p * 25.4 / 96
    on_paper = DxfPainter(layout, QTransform(1 / p, 0, 0, -1 / p, 0, h), 1 / p)
    count = 0
    for name_ in (SHEET_LAYER,):
        if name_ not in dxf.layers:
            dxf.layers.add(name_)
    with _paper_background():
        for i, item in enumerate(state["views"]):
            center = QPointF(item["at"][0] * p, (h - item["at"][1]) * p)
            vw, vh = sheets.view_size(doc, item)
            rect = QRectF(center.x() - vw * p / 2, center.y() - vh * p / 2, vw * p, vh * p)
            count += _write_placed(dxf, doc, layout, state, i, item, center, rect)
            on_paper.layer = SHEET_LAYER
            paper.draw_frame(on_paper, doc, item, rect, p, unit)
        strokes, texts = sheets.title_items(doc, sheet, date)
        on_paper.layer = SHEET_LAYER
        for stroke in strokes:
            on_paper.setPen(QPen(QColor(paper.theme.INK), max(unit * 0.5, stroke.weight * p)))
            on_paper.setBrush(Qt.NoBrush)
            pts = [QPointF(x * p, (h - y) * p) for x, y in stroke.points]
            on_paper.drawPolyline(pts + pts[:1] if stroke.closed else pts)
        on_paper.setPen(QPen(QColor(paper.theme.INK)))
        for text in texts:
            paper.draw_paper_text(on_paper, text, QPointF(text.at[0] * p, (h - text.at[1]) * p),
                                  p)
    return count + on_paper.count


def _write_placed(dxf, doc, layout, state, index: int, item: dict, center: QPointF,
                  rect: QRectF) -> int:
    """Desenho posto: um bloco em cm (na posição do projeto) inserido na escala dele."""
    p = PX_PER_MM
    unit = p * 25.4 / 96
    try:
        first = paper._item_painter(doc, item, center, p, unit)
    except (RuntimeError, ValueError):
        first = None
    if first is None or not hasattr(first, "origin"):
        return 0  # vista 3D (imagem) ou origem que não existe mais: fica a moldura
    den = sheets.scale_of(doc, item)
    k = UNITS_PER_M / first.scale  # cm por pixel
    out = QTransform(k, 0, 0, -k, -first.origin.x() * k, first.origin.y() * k)
    base = out.map(center)
    block = dxf.blocks.new(layer_name(f"{sheet_title(state)} - desenho {index + 1}"),
                           base_point=(base.x(), base.y()))
    saved = sheets.saved_state(doc, item) if item["kind"] == "saved" else None
    clip = None
    if (saved is not None and saved.get("crop")) or item.get("limit"):
        clip = Polygon([out.map(q).toTuple() for q in
                        (rect.topLeft(), rect.topRight(), rect.bottomRight(),
                         rect.bottomLeft())])
    painter = DxfPainter(block, out, 1 / p, clip)
    painter.ltscale = 0.1 * den

    def make():
        drawer = paper._item_painter(doc, item, center, p, unit)
        if drawer is not None:
            drawer.origin = first.origin  # a passada de uma camada só não muda o lugar
        return drawer

    with sheets.item_display(doc, item):
        _paint_layers(dxf, doc, painter, make)
    scale = 10.0 / den  # 1 cm do modelo em mm de papel
    layout.add_blockref(block.name, (item["at"][0], item["at"][1]),
                        dxfattribs={"xscale": scale, "yscale": scale})
    return painter.count


# --- gravar -----------------------------------------------------------------------------


def find_writer() -> str | None:
    return libredwg.find_writer() or shutil.which("dxf2dwg")


def save(dxf, path: str, fmt: str) -> str:
    """Grava ``dxf`` em ``path`` como DXF ou DWG. Levanta ``MissingWriter`` sem o
    conversor e ``RuntimeError`` se ele falhar."""
    if fmt == "dxf":
        dxf.saveas(path)
        return path
    exe = find_writer()
    if exe is None:
        raise MissingWriter("falta o conversor de DWG (GNU LibreDWG)")
    handle, temp = tempfile.mkstemp(suffix=".dxf", prefix="brasbim-")
    os.close(handle)
    try:
        dxf.saveas(temp)
        libredwg.write_dwg(exe, temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)
    return path


def export_item(doc, kind: str, gid: str, path: str, fmt: str = "dwg") -> int:
    """Uma planta, corte ou fachada, vista salva (``kind`` de ``item_of``) ou prancha
    (``sheet``) num arquivo. Devolve o número de objetos gravados."""
    dxf = new_document(fmt)
    if kind == "sheet":
        count = write_sheet(dxf, doc, doc.find(gid))
    else:
        count = write_view(dxf, doc, item_of(kind, gid))
    save(dxf, path, fmt)
    return count
