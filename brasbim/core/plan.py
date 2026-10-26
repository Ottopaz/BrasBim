# SPDX-License-Identifier: LGPL-3.0-or-later
"""Planta de um pavimento como primitivas 2D, sem Qt (``spec/ui/01-janela-e-ferramentas.md``
§3, ``spec/ui/06-planta-por-camadas.md``, ``parede.md`` §7, ``porta.md`` §7).

O plano de corte é o do pavimento (``storeys.cut_height``), medido a partir da base de
cada parede. As coordenadas são as do pavimento, em metros. Nada disto é gravado no IFC.

Papéis (``Shape.role``): ``wall`` (parte cortada da parede: escolha, seleção e fantasma;
o preenchimento vem das regiões), ``wall_view`` (em vista: abaixo do plano, e as faces
no peitoril), ``wall_above`` (acima do plano: tracejado), ``below`` (parede do pavimento
de baixo), ``door_frame`` (marco, preenchido), ``door_leaf`` (folha), ``door_swing`` (arco
de giro, linha fina), ``door_arrow`` (seta de correr), ``door_hidden`` (tracejada) e
``door`` (contorno de porta de outra origem). A janela usa os mesmos papéis de porta
para o marco, a folha aberta, o arco e a seta, e mais ``window_sash`` (faces do perfil do
caixilho fechado) e ``window_glass`` (vidro), em linha fina (spec/ui 09 §6.2).

Estrutura (spec/ui 10 §6): ``slab``, ``column`` e ``beam`` (cortados pelo plano; o fundo
vem das regiões; na viga, também a faixa usada para escolher), ``slab_view``,
``column_view`` e ``beam_view`` (abaixo do plano, linha fina) e ``slab_above``,
``column_above`` e ``beam_above`` (acima, tracejados). A viga acima do plano aparece
sempre (viga.md §7), pelas duas faces. Os pilares cortados recortam as regiões e as
bordas das paredes. A laje mostra como furos os pilares que a atravessam e as aberturas;
cada abertura tem ``slab_opening`` (contorno, para escolher) e ``slab_opening_x`` (as
diagonais do X; spec/ui 12 §3.5).

Regiões (``Region``) e bordas (``Edge``) desenham as paredes cortadas: no detalhe
simplificado, uma mancha por tipo (paredes do mesmo tipo unidas, sem linha na junção);
no por camadas, uma por material, com a prioridade das camadas nas junções
(``layers.regions``), e o tipo só para paredes sem camadas.
"""

from __future__ import annotations

import dataclasses
import itertools
import logging
import math
from dataclasses import dataclass, field

import ifcopenshell.util.element
import ifcopenshell.util.placement
import numpy as np

from brasbim.core import clip, display_layers, geom2d, layers, materials, props, storeys
from brasbim.core.clip import Rings
from brasbim.core.document import Document, OpError
from brasbim.core.fillings import door_types, doors, geometry, params, window_types
from brasbim.core.geom2d import Point
from brasbim.core.structure import beams, columns, cuts, slab_openings, slabs
from brasbim.core.structure import types as st_types
from brasbim.core.walls import openings, rebuild, top
from brasbim.core.walls import types as wall_types
from brasbim.core.walls.wall import read_state as read_wall

log = logging.getLogger(__name__)

DETAILS = ("simple", "layers")  # Exibir > Detalhe da planta (spec/ui 06 §2)
_ARC_STEPS = 16


@dataclass(frozen=True)
class Shape:
    owner: str
    role: str
    points: tuple[Point, ...]
    closed: bool = True
    style: dict | None = field(default=None, hash=False, compare=False)
    """Representação do tipo (paredes cortadas; spec/ui 03 §6), ``None`` = padrão."""


@dataclass(frozen=True)
class Label:
    """Etiqueta no ponto ``at``: de esquadria (``kind`` ``filling``, spec/ui 05 §5: código
    e medidas do vão) ou de estrutura (``structure``, spec/ui 12 §5: nome e seção).
    ``angle`` em graus, anti-horário (a da viga acompanha a viga)."""

    owner: str
    at: Point
    code: str
    size: str
    kind: str = "filling"
    angle: float = 0.0
    height: float = 0.0  # m de modelo (tamanho no papel × escala, spec/ui 13 §2)
    size_ratio: float = 1.0  # altura da linha de medidas em relação à do código
    number: str = ""  # ambiente: número, mostrado com Exibir > Número dos ambientes


@dataclass(frozen=True)
class Region:
    """Mancha das paredes cortadas: ``key`` = GlobalId do tipo ou nome do material.
    ``fill``: ``pattern`` (none, solid, lines, cross), ``background``, ``angle``,
    ``spacing`` (m), ``line_color`` e ``source`` (``type`` ou ``material``). Anéis com a
    regra par-ímpar."""

    key: str
    rings: Rings = field(hash=False)
    fill: dict = field(hash=False)


@dataclass(frozen=True)
class Edge:
    """Contorno de uma região: espessura em metros de papel (NBR 8403), cor e categoria
    da tabela de penas (spec/ui 27)."""

    rings: Rings = field(hash=False)
    weight: float
    color: str
    pen: str = "cut"


@dataclass
class Plan:
    shapes: list[Shape] = field(default_factory=list)
    labels: list[Label] = field(default_factory=list)
    regions: list[Region] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    # Anotações (spec/ui 13): (GlobalId, primitivas) — traços, textos e preenchimentos.
    annotations: list = field(default_factory=list)
    views: set = field(default_factory=set)  # donos dos símbolos de corte e fachada
    # Elementos de camada bloqueada (spec/ui 18 §4): desenhados, mas fora da escolha.
    locked: set = field(default_factory=set)
    # Categoria da tabela de penas das anotações, por dono (spec/ui 27 §3).
    pens: dict = field(default_factory=dict)

    def owners(self, role_prefix: str | tuple[str, ...]) -> dict[str, list[Shape]]:
        out: dict[str, list[Shape]] = {}
        for s in self.shapes:
            if s.role.startswith(role_prefix):
                out.setdefault(s.owner, []).append(s)
        return out

    def bounds(self) -> tuple[float, float, float, float] | None:
        pts = [p for s in self.shapes for p in s.points]
        if not pts:
            return None
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        return min(xs), min(ys), max(xs), max(ys)

    def pick(self, p: Point, tol: float) -> str | None:
        """Elemento sob o ponto, nesta prioridade (spec/ui 10 §4.1): esquadria (caixa
        envolvente), pilar, viga, parede (as cortadas primeiro) e laje."""
        for owner, shapes in sorted(self.owners(("door", "window")).items()):
            if owner in self.locked:
                continue
            pts = [q for s in shapes for q in s.points]
            if (min(q[0] for q in pts) - tol <= p[0] <= max(q[0] for q in pts) + tol
                    and min(q[1] for q in pts) - tol <= p[1] <= max(q[1] for q in pts) + tol):
                return owner
        for roles in (("annotation",), _COLUMN_ROLES, _BEAM_ROLES, ("opening_box",),
                      ("wall",),
                      ("wall_view", "wall_above"), _OPENING_ROLES, ("object_box",),
                      ("space",), _SLAB_ROLES, _ROOF_ROLES):
            found = [s for s in self.shapes if s.role in roles and s.owner not in self.locked]
            for s in found:
                if s.closed and _inside(s.points, p):
                    return s.owner
            near = [(_distance_to_outline(s.points, p, s.closed), s.owner) for s in found]
            near = [n for n in near if n[0] <= tol]
            if near:
                return min(near)[1]
        return None


    def in_rect(self, a: Point, b: Point, crossing: bool = False) -> list[str]:
        """Elementos do pavimento na janela de cantos ``a`` e ``b`` (spec/ui 02 §3.1):
        inteiramente dentro, ou que tocam a janela (``crossing``)."""
        x0, x1 = sorted((a[0], b[0]))
        y0, y1 = sorted((a[1], b[1]))
        rect = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        return self._in_area(rect, lambda q: x0 <= q[0] <= x1 and y0 <= q[1] <= y1,
                             crossing)

    def in_polygon(self, points, crossing: bool = False) -> list[str]:
        """Elementos dentro do laço ``points`` (contorno fechado, spec/ui 28 §2), ou que
        tocam o laço (``crossing``)."""
        polygon = [tuple(p) for p in points]
        if len(polygon) < 3:
            return []
        return self._in_area(polygon, lambda q: _inside(polygon, q), crossing)

    def _in_area(self, rect, inside, crossing: bool) -> list[str]:
        out = []
        groups = {**self.owners("wall"),
                  **self.owners(("door", "window", "column", "beam", "slab", "space",
                                 "annotation", "roof")),
                  **self.owners("object_box")}
        for owner, shapes in sorted(groups.items()):
            shapes = [s for s in shapes if s.role != "below"]
            if not shapes or owner in self.locked:
                continue
            # A laje (e a abertura nela) só entra inteira, mesmo no cruzamento (spec/ui 10
            # §4.1).
            if not crossing or shapes[0].role.startswith(("slab", "space", "roof")):
                if all(inside(q) for s in shapes for q in s.points):
                    out.append(owner)
            elif any(_touches(s, rect, inside) for s in shapes):
                out.append(owner)
        return out


_COLUMN_ROLES = ("column", "column_view", "column_above")
_BEAM_ROLES = ("beam", "beam_view", "beam_above")
_SLAB_ROLES = ("slab", "slab_view", "slab_above")
_OPENING_ROLES = ("slab_opening",)
_ROOF_ROLES = ("roof", "roof_edge")


def _segments(points, closed: bool):
    n = len(points)
    return [(points[i - 1], points[i]) for i in range(0 if closed else 1, n)]


def _cross(p, q, r, s) -> bool:
    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    d1, d2 = orient(r, s, p), orient(r, s, q)
    d3, d4 = orient(p, q, r), orient(p, q, s)
    return (d1 > 0) != (d2 > 0) and (d3 > 0) != (d4 > 0)


def outlines_in_area(outlines, area, crossing: bool = False) -> list[int]:
    """Índices dos contornos ``[(points, closed), ...]`` (um ou mais por item) dentro da
    janela ou do laço ``area``, ou que tocam nele (``crossing``): a mesma regra da planta
    (spec/ui 28 §2), para a prancha e a folha mestra (spec/ui 29 §2)."""
    polygon = [tuple(p) for p in area]
    if len(polygon) < 3:
        return []

    def inside(q):
        return _inside(polygon, q)

    out = []
    for i, parts in enumerate(outlines):
        shapes = [Shape("", "", tuple(tuple(q) for q in pts), closed)
                  for pts, closed in parts if pts]
        if not shapes:
            continue
        if crossing:
            if any(_touches(s, polygon, inside) for s in shapes):
                out.append(i)
        elif all(inside(q) for s in shapes for q in s.points):
            out.append(i)
    return out


def _touches(shape: Shape, rect, inside) -> bool:
    if any(inside(q) for q in shape.points):
        return True
    if shape.closed and _inside(shape.points, rect[0]):
        return True
    edges = _segments(rect, True)
    return any(_cross(p, q, r, s) for p, q in _segments(shape.points, shape.closed)
               for r, s in edges)


def _inside(points, p) -> bool:
    inside = False
    n = len(points)
    for i in range(n):
        (x0, y0), (x1, y1) = points[i - 1], points[i]
        if (y0 > p[1]) != (y1 > p[1]):
            x = x0 + (p[1] - y0) * (x1 - x0) / (y1 - y0)
            if x > p[0]:
                inside = not inside
    return inside


def distance_to_segment(p: Point, a: Point, b: Point) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy)
                                             / length2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def _distance_to_outline(points, p, closed: bool = True) -> float:
    return min(distance_to_segment(p, a, b) for a, b in _segments(points, closed))


# --- paredes -------------------------------------------------------------------------

_FAR = 1e3  # m: "infinito" dos recortes no sistema local da parede
_MARGIN = 10.0  # m: alcance das pontas além do caminho (junções)
VIEW_WEIGHT = 0.00025  # parede em vista: linha média (spec/ui 06 §3.2)
ABOVE_WEIGHT = 0.00018  # acima do plano: tracejado fino
LAYER_WEIGHT = 0.00018  # divisa entre materiais


def _slab(a: float, b: float, y0: float = -_FAR, y1: float = _FAR) -> list[Point]:
    a, b = max(a, -_FAR), min(b, _FAR)
    return [(a, y0), (b, y0), (b, y1), (a, y1)]


def _over(profile, c: float, length: float) -> list[tuple[float, float]]:
    """Trechos ``x`` em que o topo do perfil fica acima de ``c`` (pontas ao infinito)."""
    xs = sorted({-_MARGIN, length + _MARGIN, *(x for x, _ in profile)})
    out: list[list[float]] = []
    for a, b in itertools.pairwise(xs):
        ha, hb = top.at(profile, a) - c, top.at(profile, b) - c
        if ha <= 0 and hb <= 0:
            continue
        lo = a if ha > 0 else a + (b - a) * ha / (ha - hb)
        hi = b if hb > 0 else a + (b - a) * ha / (ha - hb)
        if out and abs(out[-1][1] - lo) < 1e-9:
            out[-1][1] = hi
        else:
            out.append([lo, hi])
    for piece in out:
        piece[0] = -_FAR if piece[0] <= -_MARGIN else piece[0]
        piece[1] = _FAR if piece[1] >= length + _MARGIN else piece[1]
    return [(a, b) for a, b in out if b - a > 1e-9]


@dataclass
class _Cut:
    """Uma parede do pavimento diante do plano de corte."""

    wall: object
    type_id: str
    style: dict
    shapes: list[Shape]
    pieces: Rings  # área cortada, coordenadas do pavimento
    crossed: set[str]  # aberturas atravessadas pelo plano


def _cut_wall(doc: Document, wall, cut: float, show_above: bool) -> _Cut | None:
    try:
        state = read_wall(doc, wall)
        band = rebuild.band(doc, state)
        segments = rebuild.profile(doc, wall, band)
    except (OpError, ValueError) as e:
        log.warning("parede %s fora da planta: %s", wall.GlobalId, e)
        return None
    gid, frame = wall.GlobalId, band.frame
    style = wall_types.plan_style(doc.get(state["type"], "IfcWallType"))
    out = _Cut(wall, state["type"], style, [], [], set())

    def emit(role: str, rings, closed=True):
        out.shapes += [Shape(gid, role, tuple(frame.to_global(p) for p in r), closed,
                             style if role == "wall" else None) for r in rings]

    local = [geom2d.polygon(segments)]
    c = cut - state["base_offset"]  # plano em relação à base da parede
    if c < 0:  # parede toda acima do plano
        if show_above:
            emit("wall_above", local)
        return out
    straight = isinstance(band.path, geom2d.LinePath)
    profile = state.get("top_profile")
    if profile and straight:
        over = _over(profile, c, band.path.length)
    else:
        over = [(-_FAR, _FAR)] if rebuild.height(doc, state) > c else []
    slabs = [_slab(a, b) for a, b in over]
    emit("wall_view", clip.difference(local, slabs))  # trechos com o topo abaixo do plano
    pieces = clip.intersection(local, slabs)
    if straight and pieces:
        holes = []
        for opening in openings.of_wall(wall, objects=True):
            try:
                o = openings.read_state(opening)
            except OpError:
                continue
            x0, x1 = o["distance"], o["distance"] + o["width"]
            if not any(a < x1 and x0 < b for a, b in over):
                continue  # trecho em vista: o vão não aparece
            if o["sill"] > c:
                if o["kind"] == "OPENING" and show_above:
                    emit("wall_above", [_slab(x0, x1, band.ymin, band.ymax)])
                continue
            if o["sill"] + o["height"] < c:
                continue  # vão todo abaixo do plano: a parede está cortada acima dele
            out.crossed.add(opening.GlobalId)
            if o["kind"] == "RECESS":
                depth = o["depth"] or 0.0
                y0, y1 = ((band.ymax - depth, _FAR) if o["side"] == "left"
                          else (-_FAR, band.ymin + depth))
                holes.append(_slab(x0, x1, y0, y1))
                continue
            holes.append(_slab(x0, x1))
            if o["sill"] > 1e-9:  # peitoril: as faces aparecem em vista
                emit("wall_view", [[(x0, y), (x1, y)] for y in (band.ymin, band.ymax)],
                     closed=False)
        pieces = clip.difference(pieces, holes)
    emit("wall", pieces)
    out.pieces = [[frame.to_global(p) for p in r] for r in pieces]
    return out


def wall_shapes(doc: Document, wall, role: str = "wall") -> list[Shape]:
    """Contorno da parede inteira (``role`` qualquer) ou, com ``wall``, a parte cortada
    no plano padrão."""
    if role == "wall":
        found = _cut_wall(doc, wall, storeys.DEFAULT_CUT_HEIGHT, True)
        return [s for s in found.shapes if s.role == "wall"] if found else []
    try:
        state = read_wall(doc, wall)
        band = rebuild.band(doc, state)
        segments = rebuild.profile(doc, wall, band)
    except (OpError, ValueError) as e:
        log.warning("parede %s fora da planta: %s", wall.GlobalId, e)
        return []
    return [Shape(wall.GlobalId, role,
                  tuple(band.frame.to_global(p) for p in geom2d.polygon(segments)))]


def _fill_of_type(style: dict) -> dict:
    pattern = {"none": "none", "solid": "solid", "hatch": "lines"}[style["fill"]]
    return {"pattern": pattern, "background": style["fill_color"] if pattern == "solid" else None,
            "angle": style["hatch_angle"], "spacing": style["hatch_spacing"],
            "line_color": style["fill_color"], "source": "type"}


def _type_regions(cuts: list[_Cut]) -> dict[str, Rings]:
    """União das peças de cada tipo; quem vem depois (a contínua em X) cobre os outros."""
    out: dict[str, Rings] = {}
    for w in cuts:
        if not w.pieces:
            continue
        for key, rings in out.items():
            if key != w.type_id:
                out[key] = clip.difference(rings, w.pieces)
        out[w.type_id] = clip.union(out.get(w.type_id, []), w.pieces)
    return {k: v for k, v in out.items() if v}


def _regions(doc: Document, plan: Plan, cuts: list[_Cut], detail: str) -> None:
    by_type = _type_regions(cuts)
    styles = {w.type_id: w.style for w in cuts}
    layered: set[str] = set()
    if detail == "layers":
        found = layers.regions(doc, [w.wall for w in cuts if w.pieces],
                               {w.wall.GlobalId: w.pieces for w in cuts if w.pieces})
        owners = {r.owner for r in found}
        layered = {w.type_id for w in cuts if w.wall.GlobalId in owners}
        for material, rings in sorted(layers.by_material(found).items(),
                                      key=lambda kv: kv[0] or ""):
            cut = materials.style(doc, material)["cut"]
            plan.regions.append(Region(material or "", rings, {**cut, "source": "material"}))
            plan.edges.append(Edge(rings, LAYER_WEIGHT, materials.LINE_COLOR, "layer"))
    for key, rings in by_type.items():
        if key not in layered:
            plan.regions.append(Region(key, rings, _fill_of_type(styles[key])))
    for key, rings in by_type.items():
        style = styles[key]
        plan.edges.append(Edge(rings, style["line_weight"], style["line_color"]))


# --- portas --------------------------------------------------------------------------


def _arc(center: Point, radius: float, a0: float, a1: float) -> list[Point]:
    return [(center[0] + radius * math.cos(a0 + (a1 - a0) * k / _ARC_STEPS),
             center[1] + radius * math.sin(a0 + (a1 - a0) * k / _ARC_STEPS))
            for k in range(_ARC_STEPS + 1)]


def _rect(x0, x1, y0, y1) -> list[Point]:
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def door_symbol(width: float, depth: float, operation: str, lining: dict,
                panels: list[dict]) -> list[tuple[str, list[Point], bool]]:
    """Símbolo da porta no sistema dela (x ao longo do vão, folha abrindo para +y; porta
    §2.2): lista de (papel, pontos, fechado)."""
    w, d = width, depth
    t = lining.get("thickness") or 0.0
    out: list[tuple[str, list[Point], bool]] = []
    if t > 0:
        out += [("door_frame", _rect(0, t, 0, d), True), ("door_frame", _rect(w - t, w, 0, d), True)]
    hand = params.hand_of(operation)
    x, clear = t, w - 2 * t
    for panel in panels:
        pw, pd = panel["width"] * clear, panel["depth"] or 0.035
        x0, x1 = x, x + pw
        x = x1
        position, op = panel["position"], panel["operation"]
        hinge_low = position == "LEFT" or (position == "MIDDLE" and hand != "right")
        if op in ("SWINGING", "DOUBLE_ACTING"):
            if hinge_low:
                out.append(("door_leaf", _rect(x0, x0 + pd, d, d + pw), True))
                out.append(("door_swing", _arc((x0, d), pw, 0, math.pi / 2), False))
                if op == "DOUBLE_ACTING":
                    out.append(("door_swing", _arc((x0, 0), pw, 0, -math.pi / 2), False))
            else:
                out.append(("door_leaf", _rect(x1 - pd, x1, d, d + pw), True))
                out.append(("door_swing", _arc((x1, d), pw, math.pi, math.pi / 2), False))
                if op == "DOUBLE_ACTING":
                    out.append(("door_swing", _arc((x1, 0), pw, math.pi, 1.5 * math.pi), False))
        elif op == "SLIDING":
            out.append(("door_leaf", _rect(x0, x1, d, d + pd), True))
            to_low = position == "LEFT" or (position == "MIDDLE" and hand == "left")
            y, mid, tip = d + pd + 0.05, (x0 + x1) / 2, (x0 if to_low else x1)
            head = 0.06 if to_low else -0.06
            out.append(("door_arrow", [(mid, y), (tip, y)], False))
            out.append(("door_arrow", [(tip + head, y + 0.03), (tip, y), (tip + head, y - 0.03)],
                        False))
        elif op == "FOLDING":
            steps = 4
            out.append(("door_leaf", [(x0 + pw * k / steps, d + (pw / steps if k % 2 else 0.0))
                                      for k in range(steps + 1)], False))
        elif op == "ROLLINGUP":
            out.append(("door_hidden", [(x0, d / 2), (x1, d / 2)], False))
        else:  # folha fixa
            out.append(("door_leaf", _rect(x0, x1, d - pd, d), True))
    return out


def window_symbol(width: float, height: float, state: dict, cut_z: float | None = None
                  ) -> list[tuple[str, list[Point], bool]]:
    """Símbolo da janela no sistema dela (x ao longo do vão, y na profundidade do marco,
    abrindo para +y; spec/ui 09 §6.2). ``cut_z``: altura do plano de corte a partir do
    peitoril, que escolhe o caixilho desenhado na divisão um sobre o outro (sem ela, o de
    baixo)."""
    w, d = width, state["lining"]["depth"]
    out: list[tuple[str, list[Point], bool]] = []
    parts = geometry.window_parts(width, height, state)
    # Peças verticais do marco e montantes: as que vão de baixo a cima.
    for x0, x1, y0, y1, z0, z1 in (b for b, role in parts if role == "lining"):
        if z1 - z0 > height / 2 and x1 - x0 < w - 1e-6:
            out.append(("door_frame", _rect(x0, x1, y0, y1), True))
    vertical = params.is_vertical(state["partitioning"])
    glass = [b for b, role in parts if role == "glazing"]
    cells = list(zip(state["panels"], glass))
    if not vertical and cells:
        z = cut_z if cut_z is not None else -1.0
        row = [c for c in cells if c[1][4] - 0.05 <= z <= c[1][5] + 0.05]
        cells = row[:1] or [cells[-1]]
    t = state["lining"]["thickness"] or 0.0
    for panel, (gx0, gx1, gy0, gy1, _, _) in cells:
        op, ft, fd = panel["operation"], panel["frame_thickness"] or 0.0, panel["frame_depth"]
        x0, x1 = (gx0 - ft, gx1 + ft) if vertical else (t, w - t)
        yc = (gy0 + gy1) / 2
        y0, y1 = yc - fd / 2, yc + fd / 2
        if op in params.WINDOW_SWINGS:
            pw = x1 - x0
            if params.panel_hand(op) == "left":
                out.append(("door_leaf", _rect(x0, x0 + fd, d, d + pw), True))
                out.append(("door_swing", _arc((x0, d), pw, 0, math.pi / 2), False))
            else:
                out.append(("door_leaf", _rect(x1 - fd, x1, d, d + pw), True))
                out.append(("door_swing", _arc((x1, d), pw, math.pi, math.pi / 2), False))
            continue
        out.append(("window_sash", [(x0, y0), (x1, y0)], False))
        out.append(("window_sash", [(x0, y1), (x1, y1)], False))
        out.append(("window_glass", [(x0, yc), (x1, yc)], False))
        if op == "SLIDINGHORIZONTAL" and panel["position"] in ("LEFT", "RIGHT"):
            to_high = panel["position"] == "LEFT"  # corre para o meio do vão
            mid = (x0 + x1) / 2
            tip = mid + (0.15 if to_high else -0.15)
            head = -0.05 if to_high else 0.05
            y = d + 0.06
            out.append(("door_arrow", [(mid, y), (tip, y)], False))
            out.append(("door_arrow", [(tip + head, y + 0.025), (tip, y),
                                       (tip + head, y - 0.025)], False))
    return out


def window_elevation(width: float, height: float, state: dict
                     ) -> list[tuple[str, list[Point], bool]]:
    """Desenho do tipo de janela visto de frente (spec/ui 09 §5.1), em (x, z): peças do
    marco (``lining``), perfis (``framing``), vidros (``glass``) e o símbolo de abertura
    de cada caixilho (``symbol``: triângulo com a ponta no lado do eixo de giro, seta no
    de correr, linha tracejada no pivotante)."""
    out: list[tuple[str, list[Point], bool]] = []
    parts = geometry.window_parts(width, height, state)
    for (x0, x1, _, _, z0, z1), role in parts:
        out.append(("glass" if role == "glazing" else role, _rect(x0, x1, z0, z1), True))
    glass = [b for b, role in parts if role == "glazing"]
    for panel, (x0, x1, _, _, z0, z1) in zip(state["panels"], glass):
        op = panel["operation"]
        xm, zm = (x0 + x1) / 2, (z0 + z1) / 2
        hand = params.panel_hand(op)
        if hand is not None:  # de abrir e oscilobatente: ponta no lado das dobradiças
            hinge, free = (x0, x1) if hand == "left" else (x1, x0)
            out.append(("symbol", [(free, z0), (hinge, zm), (free, z1)], False))
        if op in ("TOPHUNG", "TILTANDTURNLEFTHAND", "TILTANDTURNRIGHTHAND", "BOTTOMHUNG"):
            apex = z1 if op == "TOPHUNG" else z0
            base = z0 if op == "TOPHUNG" else z1
            out.append(("symbol", [(x0, base), (xm, apex), (x1, base)], False))
        elif op == "PIVOTHORIZONTAL":
            out.append(("axis", [(x0, zm), (x1, zm)], False))
        elif op == "PIVOTVERTICAL":
            out.append(("axis", [(xm, z0), (xm, z1)], False))
        elif op in params.WINDOW_SLIDES:
            if op == "SLIDINGHORIZONTAL":
                to_high = panel["position"] != "RIGHT"
                a, b = ((x0 + 0.25 * (x1 - x0), zm), (x1 - 0.25 * (x1 - x0), zm))
                tip, tail = (b, a) if to_high else (a, b)
                k = 0.06 if to_high else -0.06
                head = [(tip[0] - k, tip[1] + 0.04), tip, (tip[0] - k, tip[1] - 0.04)]
            else:
                a, b = (xm, z0 + 0.25 * (z1 - z0)), (xm, z1 - 0.25 * (z1 - z0))
                tip, tail = b, a
                head = [(tip[0] - 0.04, tip[1] - 0.06), tip, (tip[0] + 0.04, tip[1] - 0.06)]
            out.append(("symbol", [tail, tip], False))
            out.append(("symbol", head, False))
    return out


def _door_to_storey(door, storey):
    m = np.linalg.inv(ifcopenshell.util.placement.get_local_placement(storey.ObjectPlacement)) \
        @ ifcopenshell.util.placement.get_local_placement(door.ObjectPlacement)
    return lambda p: tuple(float(v) for v in (m @ (p[0], p[1], 0.0, 1.0))[:2])


def door_shapes(doc: Document, door, storey, cut_z: float | None = None) -> list[Shape]:
    """Símbolo da porta ou da janela no pavimento. ``cut_z``: plano de corte a partir da
    base do vão (só a janela usa)."""
    if door.ObjectPlacement is None or not door.OverallWidth:
        return []
    to_storey = _door_to_storey(door, storey)
    opening = door.FillsVoids[0].RelatingOpeningElement if door.FillsVoids else None
    wall = openings.host(opening) if opening else None
    thickness = 0.1
    if wall is not None:
        try:
            thickness = rebuild.band(doc, read_wall(doc, wall)).thickness
        except OpError:
            pass
    if doors.is_parametric(door) and door.is_a("IfcWindow"):
        state = doors.read_state(door)
        tstate = window_types.read(doc.get(state["type"], "IfcWindowType"))
        symbol = window_symbol(float(door.OverallWidth), float(door.OverallHeight or 0.0),
                               tstate, cut_z)
    elif doors.is_parametric(door):
        state = doors.read_state(door)
        tstate = door_types.read(doc.get(state["type"], "IfcDoorType"))
        depth = tstate["lining"]["depth"] or thickness
        symbol = door_symbol(float(door.OverallWidth), depth, tstate["operation_type"],
                             tstate["lining"], tstate["panels"])
    else:
        symbol = [("door", _rect(0, float(door.OverallWidth), 0, thickness), True)]
    return [Shape(door.GlobalId, role, tuple(to_storey(p) for p in pts), closed)
            for role, pts, closed in symbol]


LABEL_GAP = 0.30  # etiqueta a 0,30 m da face, do lado oposto ao da folha (spec/ui 05 §5)


def _fmt(v: float) -> str:
    return f"{v:.2f}".replace(".", ",")


def door_label(doc: Document, door, storey) -> Label | None:
    if door.ObjectPlacement is None or not door.OverallWidth:
        return None
    common = ifcopenshell.util.element.get_pset(door, doors.kind_of(door)[2]) or {}
    code = common.get("Reference") or door.Name
    if not code:
        return None
    width, height = float(door.OverallWidth), float(door.OverallHeight or 0.0)
    sill = None
    opening = door.FillsVoids[0].RelatingOpeningElement if door.FillsVoids else None
    if opening is not None:
        try:
            o = openings.read_state(opening)
            width, height, sill = o["width"], o["height"], o["sill"]
        except OpError:
            pass
    at = _door_to_storey(door, storey)((float(door.OverallWidth) / 2, -LABEL_GAP))
    size = f"{_fmt(width)} × {_fmt(height)}"
    if door.is_a("IfcWindow") and sill is not None:
        size += f" / {_fmt(sill)}"  # peitoril (spec/ui 09 §6.3)
    return Label(door.GlobalId, at, str(code), size)


def _cut_in_opening(doc: Document, opening, cut: float) -> float | None:
    """Plano de corte medido da base do vão (``None`` se não dá para saber)."""
    if opening is None:
        return None
    try:
        o = openings.read_state(opening)
        wall = openings.host(opening)
        return cut - read_wall(doc, wall)["base_offset"] - o["sill"]
    except (OpError, TypeError, AttributeError):
        return None


def _hidden_window(doc: Document, window, storey) -> list[Shape]:
    """Contorno do marco tracejado (janela acima do plano de corte)."""
    if window.ObjectPlacement is None or not window.OverallWidth:
        return []
    depth = 0.05
    if doors.is_parametric(window):
        state = doors.read_state(window)
        depth = window_types.read(doc.get(state["type"], "IfcWindowType"))["lining"]["depth"]
    to_storey = _door_to_storey(window, storey)
    pts = _rect(0, float(window.OverallWidth), 0, depth)
    return [Shape(window.GlobalId, "door_hidden", tuple(to_storey(p) for p in pts), True)]


def _continuous_last(walls) -> list:
    """Em X, a parede contínua (``RelatingElement``) é desenhada depois da outra."""
    def rank(wall):
        return any(r.is_a("IfcRelConnectsPathElements")
                   and r.RelatingConnectionType == "ATPATH"
                   and r.RelatedConnectionType == "ATPATH" for r in wall.ConnectedTo)
    return sorted(walls, key=lambda w: (rank(w), w.GlobalId))


# --- pilar, viga e laje (spec/ui 10 §6) ------------------------------------------------

CUT_WEIGHT = 0.0005  # contorno grosso de corte (NBR 8403)
SLAB_WEIGHT = 0.00018  # contorno fino da laje (laje.md §7)


@dataclass
class _Element:
    """Pilar, viga ou laje diante do plano de corte."""

    element: object
    kind: str  # column, beam, slab
    ring: list[Point]  # contorno no pavimento
    lines: list[list[Point]]  # o que se desenha em vista ou acima (viga: as faces)
    z: tuple[float, float]  # cotas do fundo e do topo, a partir do pavimento
    fill: dict
    edge_weight: float


def _material_fill(doc: Document, element_type) -> dict:
    """Fundo do material do perfil, ou o da representação do tipo, se houver."""
    if wall_types.read_plan_style(element_type) is not None:
        return _fill_of_type(wall_types.plan_style(element_type))
    material = st_types.material_profile(element_type).Material
    cut = materials.style(doc, material.Name if material else None)["cut"]
    return {**cut, "source": "material"}


def _slab_fill(element_type) -> dict:
    """Laje: só o fundo que o tipo pedir (padrão: sem fundo, laje.md §3.2)."""
    style = wall_types.read_plan_style(element_type)
    return _fill_of_type(style) if style else {"pattern": "none", "source": "type"}


def _foreign_element(element, storey, kind: str) -> _Element | None:
    """Elemento de outra origem: contorno convexo do corpo, visto de cima."""
    import ifcopenshell.geom

    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    try:
        shape = props.body_shape(settings, element)
    except RuntimeError:
        return None
    verts = np.array(shape.geometry.verts, dtype=float).reshape(-1, 3)
    m = np.linalg.inv(ifcopenshell.util.placement.get_local_placement(storey.ObjectPlacement))
    local = (m @ np.c_[verts, np.ones(len(verts))].T).T[:, :3]
    ring = geom2d.convex_hull([(float(x), float(y)) for x, y, _ in local])
    if len(ring) < 3:
        return None
    z = (float(local[:, 2].min()), float(local[:, 2].max()))
    return _Element(element, kind, ring, [ring], z, {"pattern": "none", "source": "type"},
                    CUT_WEIGHT)


def _structure_element(doc: Document, element, storey) -> _Element | None:
    kind = {"IfcColumn": "column", "IfcBeam": "beam", "IfcSlab": "slab"}[element.is_a()]
    module = {"column": columns, "beam": beams, "slab": slabs}[kind]
    try:
        state = module.read_state(doc, element)
        if state["foreign"] is not None:
            return _foreign_element(element, storey, kind)
        element_type = doc.get(state["type"])
        if kind == "column":
            ring = columns.outline(doc, state)
            z0 = state["base_offset"]
            return _Element(element, kind, ring, [ring], (z0, z0 + columns.height(doc, state)),
                            _material_fill(doc, element_type), CUT_WEIGHT)
        if kind == "beam":
            ring = beams.outline(doc, state)
            z1 = beams.top_z(doc, state)
            faces = [[ring[0], ring[1]], [ring[3], ring[2]]]
            return _Element(element, kind, ring, faces,
                            (z1 - beams.section(doc, state)["h"], z1),
                            _material_fill(doc, element_type), CUT_WEIGHT)
        ring = [tuple(p) for p in state["outline"]]
        z1 = state["top_offset"]
        style = wall_types.read_plan_style(element_type)
        holes = [list(c.cutter.ring) for c in cuts.cuts_of(doc, element)
                 if c.mode == "through"]
        holes += [list(map(tuple, slab_openings.read_state(o)["outline"]))
                  for o in slab_openings.of_slab(element)]
        lines = clip.difference([list(ring)], holes) if holes else [ring]
        return _Element(element, kind, ring, lines, (z1 - slabs.thickness(doc, state), z1),
                        _slab_fill(element_type),
                        style["line_weight"] if style else SLAB_WEIGHT)
    except (OpError, ValueError, KeyError, TypeError) as e:
        log.warning("%s %s fora da planta: %s", element.is_a(), element.GlobalId, e)
        return None


def _structure(doc: Document, storey, cut: float, show_above: bool
               ) -> tuple[list[_Element], list[Shape], Rings]:
    """Elementos da estrutura do pavimento, as formas deles e a área dos pilares
    cortados (que recorta as paredes)."""
    found = [e for e in (_structure_element(doc, x, storey)
                         for cls in ("IfcSlab", "IfcColumn", "IfcBeam")
                         for x in _contained(storey, cls, doc)) if e is not None]
    shapes: list[Shape] = []
    cut_columns: Rings = []
    for e in found:
        gid = e.element.GlobalId
        z0, z1 = e.z
        closed = e.kind != "beam"
        if z0 < cut < z1:
            shapes.append(Shape(gid, e.kind, tuple(e.ring), True))
            if e.kind == "column":
                cut_columns.append(list(e.ring))
            continue
        if z1 <= cut:
            role = f"{e.kind}_view"
        elif show_above or e.kind == "beam":
            role = f"{e.kind}_above"
        else:
            continue
        shapes += [Shape(gid, role, tuple(line), closed) for line in e.lines]
        if e.kind == "beam":  # escolha e seleção pela faixa inteira
            shapes.append(Shape(gid, "beam", tuple(e.ring), True))
        if e.kind == "slab":
            shapes += _opening_shapes(e.element)
    if cut_columns:  # o tracejado da viga não entra no pilar cortado (spec/ui 10 §6.2)
        outside = clip.difference([_slab(-_FAR, _FAR)], cut_columns)
        trimmed = []
        for s in shapes:
            if s.role in ("beam_above", "beam_view"):
                trimmed += [Shape(s.owner, s.role, tuple(q), False)
                            for q in clip.clip_lines([list(s.points)], outside)]
            else:
                trimmed.append(s)
        shapes = trimmed
    return found, shapes, cut_columns


LABEL_OFFSET = 0.20  # m: etiqueta de pilar e viga afastada do contorno (spec/ui 12 §5)


def _section_text(element_type) -> str:
    """"20×40", "Ø30" (seção do tipo), ou vazio."""
    try:
        section = st_types.section(element_type)
    except (OpError, AttributeError):
        return ""
    from brasbim.core.structure import profiles

    return profiles.label(section).replace(" × ", "×").replace("Ø ", "Ø")


def structure_labels(found: list[_Element]) -> list[Label]:
    """Etiquetas de pilar ("P1" e, abaixo, "20×40", junto ao canto de cima à direita) e de
    viga ("V1 14×40" no meio dela, girada com ela, de leitura da esquerda para a direita
    ou de baixo para cima; spec/ui 12 §5)."""
    out = []
    for e in found:
        element = e.element
        if e.kind not in ("column", "beam") or not element.Name:
            continue
        size = _section_text(ifcopenshell.util.element.get_type(element))
        if e.kind == "column":
            xs, ys = [p[0] for p in e.ring], [p[1] for p in e.ring]
            out.append(Label(element.GlobalId, (max(xs) + LABEL_OFFSET, max(ys) + LABEL_OFFSET),
                             element.Name, size, "structure"))
            continue
        a, b, c, d = e.ring  # faixa: direita (a→b) e esquerda (d→c)
        dx, dy = b[0] - a[0], b[1] - a[1]
        angle = math.degrees(math.atan2(dy, dx))
        if angle > 90.0 + 1e-9 or angle <= -90.0 + 1e-9:  # sempre legível
            angle = angle - 180.0 if angle > 0 else angle + 180.0
        n = math.hypot(dx, dy)
        left = (-dy / n, dx / n)
        mid = ((c[0] + d[0]) / 2 + left[0] * LABEL_OFFSET,
               (c[1] + d[1]) / 2 + left[1] * LABEL_OFFSET)
        text = f"{element.Name} {size}".strip()
        out.append(Label(element.GlobalId, mid, text, "", "structure", angle))
    return out


def _opening_shapes(slab) -> list[Shape]:
    """Contorno e X de cada abertura da laje (spec/ui 12 §3.5)."""
    out = []
    for opening in slab_openings.of_slab(slab):
        ring = [tuple(p) for p in slab_openings.read_state(opening)["outline"]]
        out.append(Shape(opening.GlobalId, "slab_opening", tuple(ring), True))
        xs, ys = [p[0] for p in ring], [p[1] for p in ring]
        diagonals = [[(min(xs), min(ys)), (max(xs), max(ys))],
                     [(min(xs), max(ys)), (max(xs), min(ys))]]
        out += [Shape(opening.GlobalId, "slab_opening_x", tuple(q), False)
                for q in clip.clip_lines(diagonals, [list(ring)])]
    return out


def _structure_regions(plan: Plan, found: list[_Element], cut: float, kinds) -> None:
    for e in found:
        if e.kind not in kinds:
            continue
        z0, z1 = e.z
        ring = [list(r) for r in e.lines] if e.kind == "slab" else [list(e.ring)]
        if z0 < cut < z1:
            plan.regions.append(Region(e.element.GlobalId, ring, e.fill))
            plan.edges.append(Edge(ring, e.edge_weight, materials.LINE_COLOR))
        elif e.kind == "slab" and z1 <= cut and e.fill["pattern"] != "none":
            plan.regions.append(Region(e.element.GlobalId, ring, e.fill))


def _carve(plan: Plan, first_region: int, first_edge: int, holes: Rings) -> None:
    """Tira das regiões e das bordas das paredes (a partir dos índices dados) a área dos
    pilares cortados (pilar.md §6)."""
    if not holes:
        return
    plan.regions[first_region:] = [Region(r.key, clip.difference(r.rings, holes), r.fill)
                                   for r in plan.regions[first_region:]]
    plan.edges[first_edge:] = [Edge(clip.difference(e.rings, holes), e.weight, e.color, e.pen)
                               for e in plan.edges[first_edge:]]


# --- pavimento ----------------------------------------------------------------------


def _contained(storey, ifc_class: str, doc: Document) -> list:
    """Elementos da classe no pavimento; as águas da cobertura ficam de fora (quem aparece
    é a cobertura, ``_roofs``), e os das camadas ocultas também (spec/ui 18 §4)."""
    from brasbim.core.structure import roofs

    hidden = display_layers.hidden_ids(doc)
    return sorted((e for e in ifcopenshell.util.element.get_decomposition(storey)
                   if e.is_a(ifc_class) and not roofs.is_part(e) and e.GlobalId not in hidden),
                  key=lambda e: e.GlobalId)


def storey_plan(doc: Document, storey, show_below: bool = True, detail: str = "simple",
                show_above: bool = True) -> Plan:
    """Planta do pavimento. ``detail``: ``simple`` ou ``layers`` (spec/ui 06 §2);
    ``show_above``: paredes e vãos acima do plano em tracejado (§3.2)."""
    plan = Plan(locked=display_layers.locked_ids(doc))
    if show_below:
        storeys_ = doc.storeys()
        i = storeys_.index(storey)
        if i > 0:
            for wall in _contained(storeys_[i - 1], "IfcWall", doc):
                plan.shapes += wall_shapes(doc, wall, role="below")
    cut = storeys.cut_height(storey)
    found, structure, cut_columns = _structure(doc, storey, cut, show_above)
    # Lajes sob as paredes; pilares e vigas por cima (spec/ui 10 §6.1).
    plan.shapes += [s for s in structure if s.role.startswith("slab")]
    _structure_regions(plan, found, cut, ("slab",))
    cuts = [c for c in (_cut_wall(doc, wall, cut, show_above)
                        for wall in _continuous_last(_contained(storey, "IfcWall", doc)))
            if c is not None]
    order = {"wall_above": 0, "wall_view": 1}  # acima, abaixo, cortadas (§3.2)
    plan.shapes += sorted((s for c in cuts for s in c.shapes), key=lambda s: order.get(s.role, 2))
    first_region, first_edge = len(plan.regions), len(plan.edges)
    _regions(doc, plan, cuts, detail)
    _carve(plan, first_region, first_edge, cut_columns)
    plan.shapes += [s for s in structure if not s.role.startswith("slab")]
    _structure_regions(plan, found, cut, ("column", "beam"))
    plan.labels += structure_labels(found)
    crossed = {o for c in cuts for o in c.crossed}
    # A esquadria segue a própria camada (spec/ui 18 §4): o vão de parede oculta também conta.
    hidden = display_layers.hidden_ids(doc)
    for wall in ifcopenshell.util.element.get_decomposition(storey):
        if wall.GlobalId in hidden and wall.is_a("IfcWall"):
            c = _cut_wall(doc, wall, cut, show_above)
            crossed |= set(c.crossed) if c is not None else set()
    from brasbim.core.structure import skylights

    fillings = sorted((e for e in _contained(storey, "IfcDoor", doc)
                       + _contained(storey, "IfcWindow", doc) if not skylights.is_skylight(e)),
                      key=lambda e: e.GlobalId)
    for door in fillings:
        opening = door.FillsVoids[0].RelatingOpeningElement if door.FillsVoids else None
        cut_z = _cut_in_opening(doc, opening, cut)
        if opening is not None and opening.GlobalId not in crossed:
            # Vão fora do plano de corte: sem símbolo (spec/ui 06 §3.3); a janela acima
            # do plano aparece tracejada (spec/ui 09 §6.1).
            if door.is_a("IfcWindow") and show_above and cut_z is not None and cut_z < 0:
                plan.shapes += _hidden_window(doc, door, storey)
            continue
        plan.shapes += door_shapes(doc, door, storey, cut_z)
        label = door_label(doc, door, storey)
        if label is not None:
            plan.labels.append(label)
    _wall_openings(doc, storey, plan)
    _skylights(doc, storey, plan)
    _stairs_and_railings(doc, storey, plan, cut)
    _objects(doc, storey, plan, cut)
    _roofs(doc, storey, plan, cut, show_above)
    _documentation(doc, storey, plan)
    from brasbim.core import pens

    plan.pens = {gid: pens.annotation_category(doc, doc.find(gid))
                 for gid in {owner for owner, _ in plan.annotations}}
    return plan


def _stairs_and_railings(doc: Document, storey, plan: Plan, cut: float) -> None:
    """Escadas, guarda-corpos soltos e, no pavimento mais baixo, o terreno
    (escada-terreno.md §2.3, §3, §4): desenhados como anotações."""
    from brasbim.core import terrain
    from brasbim.core.structure import railings, stairs

    hidden = display_layers.hidden_ids(doc)
    for stair in _contained(storey, "IfcStair", doc):
        if not stairs.is_stair(stair):
            continue
        try:
            state = stairs.read_state(stair)
            prims = stairs.plan_prims(doc, state, cut)
            rings = stairs.footprint(doc, state)
        except (OpError, ValueError, ZeroDivisionError):
            continue
        plan.annotations.append((stair.GlobalId, prims))
        plan.shapes += [Shape(stair.GlobalId, "annotation", tuple(r), True) for r in rings]
    for railing in _contained(storey, "IfcRailing", doc):
        if not railings.is_railing(railing):
            continue
        from brasbim.core.annotations.prims import Prims, Stroke

        pts = tuple(railings.plan_points(railings.read_state(railing)))
        plan.annotations.append((railing.GlobalId, Prims(strokes=[Stroke(pts, False, 0.25)])))
        plan.shapes.append(Shape(railing.GlobalId, "annotation", pts, False))
    lowest = doc.storeys()[0] if doc.storeys() else None
    if lowest is not None and lowest.GlobalId == storey.GlobalId:
        for t in terrain.all_terrains(doc):
            if t.GlobalId in hidden:
                continue
            state = terrain.read_state(t)
            prims = terrain.plan_prims(state, storey)
            plan.annotations.insert(0, (t.GlobalId, prims))
            plan.shapes.append(Shape(t.GlobalId, "annotation",
                                     tuple(terrain.hull(state["points"])), False))


def _skylights(doc: Document, storey, plan: Plan) -> None:
    """Claraboias (spec/ui 20 §4): caixilho e vidro em projeção, escolha pela caixa."""
    from brasbim.core.structure import skylights

    for window in _contained(storey, "IfcWindow", doc):
        if not skylights.is_skylight(window):
            continue
        state = skylights.read_state(window)
        ring = skylights.outline(state)
        inner = skylights.outline({**state, "width": state["width"] - 2 * state["frame"],
                                   "length": state["length"] - 2 * state["frame"]})
        plan.shapes.append(Shape(window.GlobalId, "window_skylight", tuple(ring), True))
        plan.shapes.append(Shape(window.GlobalId, "window_glass", tuple(inner), True))


def _wall_openings(doc: Document, storey, plan: Plan) -> None:
    """Vãos e nichos sem esquadria (spec/ui 20 §3): a caixa do vão, para escolher."""
    from brasbim.core.walls import commands as wall_cmd

    for wall in _contained(storey, "IfcWall", doc):
        try:
            state = read_wall(doc, wall)
            band = rebuild.band(doc, state)
        except (OpError, ValueError):
            continue
        if not isinstance(band.path, geom2d.LinePath):
            continue
        frame = geom2d.frame(band.path)
        for opening in openings.of_wall(wall):
            if not wall_cmd.is_wall_opening(opening):
                continue
            o = openings.read_state(opening)
            if o["kind"] == "RECESS":
                y0, y1 = ((band.ymax - o["depth"], band.ymax) if o["side"] == "left"
                          else (band.ymin, band.ymin + o["depth"]))
            else:
                y0, y1 = band.ymin, band.ymax
            x0, x1 = o["distance"], o["distance"] + o["width"]
            ring = tuple(frame.to_global(q) for q in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)))
            plan.shapes.append(Shape(opening.GlobalId, "opening_box", ring, True))


def _objects(doc: Document, storey, plan: Plan, cut: float) -> None:
    """Objetos paramétricos (objeto-parametrico.md §7): símbolo, caixa e etiqueta."""
    from brasbim.core.objects import elements as objects
    from brasbim.core.objects import plan as object_plan

    found = sorted((e for cls in objects.OCCURRENCE_CLASSES
                    for e in _contained(storey, cls, doc) if objects.is_object(e)),
                   key=lambda e: e.GlobalId)
    for element in found:
        plan.shapes += object_plan.shapes(doc, element, storey, cut)
        try:
            label = object_plan.label(doc, element, storey, 0.0)
        except OpError:
            label = None
        if label is not None:
            plan.labels.append(label)


# --- cobertura (cobertura.md §7) -----------------------------------------------------------

ROOF_ARROW_MM, ROOF_HEAD_MM = 10.0, 2.0  # seta da água, no papel (CG)
ROOF_VIEW_MM, ROOF_ABOVE_MM = 0.18, 0.18  # espessura das linhas (spec/ui 13 §8)


def _percent(value: float) -> str:
    text = f"{value:.1f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


def roof_prims(doc: Document, state: dict, storey, view: bool):
    """Desenho da cobertura: só o contorno do beiral tracejado (acima do plano) ou a
    planta de cobertura (``view``): beiral, cumeeira e espigões, e uma seta em cada água
    apontando para baixo com a inclinação."""
    from brasbim.core.annotations.prims import Prims, Stroke, Text
    from brasbim.core.structure import roofs

    eave = tuple(tuple(p) for p in roofs.eave_outline(state))
    if not view:
        return Prims([Stroke(eave, True, ROOF_ABOVE_MM, "dashed")])
    out = Prims([Stroke(eave, True, ROOF_VIEW_MM)])
    out.strokes += [Stroke(tuple(line), False, ROOF_VIEW_MM)
                    for line in roofs.ridge_lines(state)]
    if state["shape"] == "flat":
        return out
    length = storeys.paper(storey, ROOF_ARROW_MM)
    head = storeys.paper(storey, ROOF_HEAD_MM)
    height = storeys.paper(storey, LABEL_MM)
    label = f"i = {_percent(state['slope'])}%"
    for face in roofs.faces(state):
        ring = face.ring
        cx = sum(p[0] for p in ring) / len(ring)
        cy = sum(p[1] for p in ring) / len(ring)
        dx, dy = -face.inward[0], -face.inward[1]  # morro abaixo
        a = (cx - dx * length / 2, cy - dy * length / 2)
        b = (cx + dx * length / 2, cy + dy * length / 2)
        left = (b[0] - dx * head - dy * head / 2, b[1] - dy * head + dx * head / 2)
        right = (b[0] - dx * head + dy * head / 2, b[1] - dy * head - dx * head / 2)
        out.strokes += [Stroke((a, b), False, ROOF_VIEW_MM),
                        Stroke((left, b, right), False, ROOF_VIEW_MM)]
        angle = math.degrees(math.atan2(dy, dx))
        from brasbim.core.annotations.prims import readable

        side = (-dy * height * 0.6, dx * height * 0.6)
        out.texts.append(Text((cx + side[0], cy + side[1]), label, height,
                              readable(angle)))
    return out


def _roofs(doc: Document, storey, plan: Plan, cut: float, show_above: bool) -> None:
    """Coberturas do pavimento (§7) e, tracejado, o beiral das coberturas do pavimento de
    cima (projeção da cobertura)."""
    from brasbim.core.structure import roofs

    for roof in _contained(storey, "IfcRoof", doc):
        if not roofs.is_roof(roof):
            continue
        try:
            state = roofs.read_state(doc, roof)
            low = min(roofs.bottom_z(state, f, p) for f in roofs.faces(state) for p in f.ring)
        except (OpError, ValueError, KeyError, TypeError) as e:
            log.warning("cobertura %s fora da planta: %s", roof.GlobalId, e)
            continue
        view = low < cut
        if not view and not show_above:
            continue
        prims = roof_prims(doc, state, storey, view)
        plan.annotations.append((roof.GlobalId, prims))
        eave = tuple(tuple(p) for p in roofs.eave_outline(state))
        if view:  # escolha por dentro, como a laje
            plan.shapes.append(Shape(roof.GlobalId, "roof", eave, True))
        else:  # acima do plano: só perto do contorno
            plan.shapes.append(Shape(roof.GlobalId, "roof_edge", (*eave, eave[0]), False))
    if not show_above:
        return
    storeys_ = doc.storeys()
    i = storeys_.index(storey) if storey in storeys_ else -1
    if i < 0 or i + 1 >= len(storeys_):
        return
    from brasbim.core.annotations.prims import Prims, Stroke

    for roof in _contained(storeys_[i + 1], "IfcRoof", doc):
        if not roofs.is_roof(roof):
            continue
        try:
            eave = tuple(tuple(p) for p in roofs.eave_outline(roofs.read_state(doc, roof)))
        except (OpError, ValueError, KeyError, TypeError):
            continue
        plan.annotations.append((roof.GlobalId, Prims([Stroke(eave, True, ROOF_ABOVE_MM,
                                                               "dashed")])))


# --- documentação (spec/ui 13) ------------------------------------------------------------

LABEL_MM = 2.5  # altura das etiquetas no papel (spec/ui 13 §2)
SPACE_NAME_MM, SPACE_AREA_MM = 3.0, 2.5  # §3.4


def _documentation(doc: Document, storey, plan: Plan) -> None:
    """Ambientes (forma de escolha e etiqueta), anotações (primitivas, hachuras como
    regiões sob tudo) e a altura das etiquetas pela escala do pavimento."""
    from brasbim.core.annotations import base, spaces
    from brasbim.core.annotations.prims import text_box

    height = storeys.paper(storey, LABEL_MM)
    plan.labels = [dataclasses.replace(lb, height=height) for lb in plan.labels]
    hatches = []
    hidden = display_layers.hidden_ids(doc)
    for e in ifcopenshell.util.element.get_decomposition(storey):
        if e.GlobalId in hidden:
            continue
        if e.is_a("IfcSpace"):
            try:
                state = spaces.read_state(e)
            except (OpError, AttributeError):
                continue
            if not state["outline"]:
                continue
            ring = tuple(tuple(p) for p in state["outline"])
            plan.shapes.append(Shape(e.GlobalId, "space", ring, True))
            q = ifcopenshell.util.element.get_pset(e, spaces.QTO) or {}
            area = q.get("NetFloorArea", spaces.area(state["outline"]))
            plan.labels.append(Label(
                e.GlobalId, spaces.label_point(state), state["name"] or "",
                f"{area:.2f}".replace(".", ",") + " m²", "space", 0.0,
                storeys.paper(storey, SPACE_NAME_MM), SPACE_AREA_MM / SPACE_NAME_MM,
                state["number"] or ""))
        elif e.is_a("IfcAnnotation") and base.kind_of(e) is not None:
            try:
                prims = base.build(doc, e)
            except (OpError, ValueError, KeyError):
                continue
            plan.annotations.append((e.GlobalId, prims))
            for f in prims.fills:
                hatches.append(Region(e.GlobalId, [list(r) for r in f.rings], f.fill))
                plan.shapes += [Shape(e.GlobalId, "annotation", tuple(r), True)
                                for r in f.rings]
            plan.shapes += [Shape(e.GlobalId, "annotation", st.points, st.closed)
                            for st in prims.strokes]
            plan.shapes += [Shape(e.GlobalId, "annotation", tuple(text_box(t)), True)
                            for t in prims.texts]
    plan.regions[:0] = hatches  # as hachuras ficam sob as paredes
    from brasbim.core import grids  # eixos de projeto (spec/ui 20 §2): em todo pavimento

    for grid in grids.all_grids(doc):
        if grid.GlobalId in hidden:
            continue
        try:
            prims = grids.prims(grids.read_state(grid), storey)
        except OpError:
            continue
        plan.annotations.append((grid.GlobalId, prims))
        plan.shapes += [Shape(grid.GlobalId, "annotation", st.points, st.closed)
                        for st in prims.strokes]
    from brasbim.core.drawings import views  # símbolos de corte e fachada (spec/ui 14 §6)

    for view in views.all_views(doc):
        try:
            state = views.read_state(view)
        except OpError:
            continue
        if not views.shown_on(state, storey) or view.GlobalId in hidden:
            continue
        prims = views.symbol(state)
        plan.annotations.append((view.GlobalId, prims))
        plan.views.add(view.GlobalId)
        plan.shapes += [Shape(view.GlobalId, "annotation", st.points, st.closed)
                        for st in prims.strokes]
