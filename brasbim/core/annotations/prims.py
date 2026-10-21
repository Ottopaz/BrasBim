# SPDX-License-Identifier: LGPL-3.0-or-later
"""Primitivas 2D das anotações (traço, texto, preenchimento), em coordenadas do pavimento
e em metros de modelo; e a gravação delas no IFC (spec/ui 13 §4.1, §6).

A planta desenha as mesmas primitivas que vão para o arquivo: um ``IfcGeometricCurveSet``
com os traços, ``IfcTextLiteralWithExtent`` para os textos e ``IfcAnnotationFillArea``
para os preenchimentos, cada grupo com o seu ``IfcStyledItem`` [IFC-ANNOT].
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import ifcopenshell.util.element

from brasbim.core import materials
from brasbim.core.document import Document

DASHES = ("solid", "dashed", "dashdot")
# Padrões de traço em mm de papel (visível, invisível, …) (CG).
DASH_PATTERNS = {"dashed": (3.0, 1.5), "dashdot": (6.0, 1.5, 0.5, 1.5)}
HALIGN = ("left", "center", "right")
INK = materials.LINE_COLOR


@dataclass(frozen=True)
class Stroke:
    points: tuple[tuple[float, float], ...]
    closed: bool = False
    weight: float = 0.25  # mm de papel
    dash: str = "solid"


@dataclass(frozen=True)
class Text:
    at: tuple[float, float]  # âncora: meio da base (center), ou ponta esquerda/direita
    text: str
    height: float  # m de modelo
    angle: float = 0.0  # graus, anti-horário
    halign: str = "center"
    valign: str = "bottom"  # bottom ou middle


@dataclass(frozen=True)
class Fill:
    rings: tuple = field(hash=False)
    fill: dict = field(hash=False)  # como Region.fill da planta (spacing em m)


@dataclass
class Prims:
    strokes: list[Stroke] = field(default_factory=list)
    texts: list[Text] = field(default_factory=list)
    fills: list[Fill] = field(default_factory=list)

    def extend(self, other: Prims) -> None:
        self.strokes += other.strokes
        self.texts += other.texts
        self.fills += other.fills

    def points(self) -> list[tuple[float, float]]:
        """Pontos de tudo (escolha, seleção, enquadramento)."""
        out = [p for s in self.strokes for p in s.points]
        out += [p for f in self.fills for r in f.rings for p in r]
        for t in self.texts:
            out += text_box(t)
        return out


def readable(angle: float) -> float:
    """Ângulo de texto legível: de baixo para cima ou da esquerda para a direita."""
    a = (angle + 180.0) % 360.0 - 180.0
    if a > 90.0 + 1e-9:
        a -= 180.0
    elif a <= -90.0 + 1e-9:
        a += 180.0
    return a


def text_box(t: Text) -> list[tuple[float, float]]:
    """Retângulo aproximado do texto (largura ≈ 0,6 da altura por letra)."""
    lines = t.text.split("\n")
    w = max(len(line) for line in lines) * 0.6 * t.height
    h = len(lines) * 1.4 * t.height
    x0 = {"left": 0.0, "center": -w / 2, "right": -w}[t.halign]
    y0 = 0.0 if t.valign == "bottom" else -h / 2
    c, s = math.cos(math.radians(t.angle)), math.sin(math.radians(t.angle))
    return [(t.at[0] + c * x - s * y, t.at[1] + s * x + c * y)
            for x, y in ((x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h))]


# --- IFC ---------------------------------------------------------------------------------


def _point(ifc, p):
    return ifc.createIfcCartesianPoint((float(p[0]), float(p[1])))


def _colour(ifc, color: str):
    r, g, b = materials.rgb(color)
    return ifc.createIfcColourRgb(None, r, g, b)


def _curve_style(ifc, weight: float, dash: str):
    font = None
    if dash != "solid":
        pattern = DASH_PATTERNS[dash]
        font = ifc.createIfcCurveStyleFont(dash, [
            ifc.createIfcCurveStyleFontPattern(float(pattern[i]) / 1000.0,
                                               float(pattern[i + 1]) / 1000.0)
            for i in range(0, len(pattern), 2)])
    return ifc.createIfcCurveStyle(None, font,
                                   ifc.createIfcPositiveLengthMeasure(float(weight) / 1000.0),
                                   _colour(ifc, INK), False)


def _fill_style(ifc, fill: dict):
    fills = []
    if fill.get("background") or fill["pattern"] == "solid":
        fills.append(_colour(ifc, fill.get("background") or INK))
    for extra in ((0.0,) if fill["pattern"] == "lines" else
                  (0.0, 90.0) if fill["pattern"] == "cross" else ()):
        curve = ifc.createIfcCurveStyle(None, None,
                                        ifc.createIfcPositiveLengthMeasure(0.00013),
                                        _colour(ifc, fill.get("line_color") or INK), False)
        fills.append(ifc.createIfcFillAreaStyleHatching(
            curve, ifc.createIfcPositiveLengthMeasure(float(fill["spacing"])), None, None,
            math.radians(float(fill["angle"]) + extra)))
    return ifc.createIfcFillAreaStyle(None, fills, False)


def _text_item(ifc, t: Text):
    c, s = math.cos(math.radians(t.angle)), math.sin(math.radians(t.angle))
    placement = ifc.createIfcAxis2Placement2D(_point(ifc, t.at), ifc.createIfcDirection((c, s)))
    lines = t.text.split("\n")
    w = max(len(line) for line in lines) * 0.6 * t.height
    extent = ifc.createIfcPlanarExtent(float(w), float(len(lines) * 1.4 * t.height))
    box = {"bottom": "bottom", "middle": "center"}[t.valign]
    box = f"{box}-{'middle' if t.halign == 'center' else t.halign}" if box == "bottom" \
        else ("center" if t.halign == "center" else f"center-{t.halign}")
    return ifc.createIfcTextLiteralWithExtent(t.text, placement, "RIGHT", extent, box)


def _indexed(ifc, s: Stroke):
    """Linha numa entidade só: ``IfcIndexedPolyCurve`` sobre ``IfcCartesianPointList2D``."""
    coords = [(float(p[0]), float(p[1])) for p in s.points]
    segments = None
    if s.closed:
        index = [*range(1, len(coords) + 1), 1]
        segments = [ifc.createIfcLineIndex(index)]
    return ifc.createIfcIndexedPolyCurve(ifc.createIfcCartesianPointList2D(coords), segments,
                                         False)


def write(doc: Document, element, prims: Prims, compact: bool = False) -> None:
    """Representação ``Annotation`` (contexto ``Plan``) com as primitivas e os estilos;
    ``compact``: linhas como ``IfcIndexedPolyCurve`` (desenho importado)."""
    ifc = doc.ifc
    items = []
    by_style: dict[tuple, list] = {}
    for s in prims.strokes:
        if compact:
            curve = _indexed(ifc, s)
        else:
            pts = [_point(ifc, p) for p in s.points]
            curve = ifc.createIfcPolyline([*pts, pts[0]] if s.closed else pts)
        by_style.setdefault((s.weight, s.dash), []).append(curve)
    for (weight, dash), curves in sorted(by_style.items()):
        item = ifc.createIfcGeometricCurveSet(curves)
        ifc.createIfcStyledItem(item, [_curve_style(ifc, weight, dash)], None)
        items.append(item)
    for t in prims.texts:
        item = _text_item(ifc, t)
        font = ifc.createIfcTextStyleFontModel(
            "BrasBim", ["sans-serif"], None, None, None,
            ifc.createIfcLengthMeasure(float(t.height)))
        style = ifc.createIfcTextStyle(None, ifc.createIfcTextStyleForDefinedFont(
            _colour(ifc, INK), None), None, font, False)
        ifc.createIfcStyledItem(item, [style], None)
        items.append(item)
    for f in prims.fills:
        rings = [list(r) for r in f.rings if len(r) >= 3]
        if not rings:
            continue
        curves = [ifc.createIfcPolyline([*(pts := [_point(ifc, p) for p in r]), pts[0]])
                  for r in rings]
        item = ifc.createIfcAnnotationFillArea(curves[0], curves[1:] or None)
        ifc.createIfcStyledItem(item, [_fill_style(ifc, f.fill)], None)
        items.append(item)
    if not items:
        _drop(doc, element)
        return
    rep = ifc.createIfcShapeRepresentation(doc.annotation_context, "Annotation",
                                           "Annotation2D", items)
    _replace(doc, element, rep)


def _replace(doc: Document, element, rep) -> None:
    """Troca a representação ``Annotation``, apagando a antiga com os estilos dela."""
    _drop(doc, element)
    shape = element.Representation
    if shape is None:
        element.Representation = doc.ifc.createIfcProductDefinitionShape(None, None, [rep])
    else:
        shape.Representations = [*shape.Representations, rep]


def _drop(doc: Document, element) -> None:
    """Apaga a representação ``Annotation`` com os itens e os estilos de cada item (os
    estilos são da anotação, não compartilhados)."""
    shape = element.Representation
    if shape is None:
        return
    old = [r for r in shape.Representations if r.RepresentationIdentifier == "Annotation"]
    if not old:
        return
    keep = [r for r in shape.Representations if r not in old]
    if keep:
        shape.Representations = keep
    else:
        element.Representation = None
        doc.ifc.remove(shape)
    for rep in old:
        items = list(rep.Items)
        doc.ifc.remove(rep)
        for item in items:
            styles = []
            for styled in list(item.StyledByItem or ()):
                styles += list(styled.Styles or ())
                doc.ifc.remove(styled)
            for style in styles:
                ifcopenshell.util.element.remove_deep2(doc.ifc, style)
            ifcopenshell.util.element.remove_deep2(doc.ifc, item)
