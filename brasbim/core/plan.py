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
``door`` (contorno de porta de outra origem).

Regiões (``Region``) e bordas (``Edge``) desenham as paredes cortadas: no detalhe
simplificado, uma mancha por tipo (paredes do mesmo tipo unidas, sem linha na junção);
no por camadas, uma por material, com a prioridade das camadas nas junções
(``layers.regions``), e o tipo só para paredes sem camadas.
"""

from __future__ import annotations

import itertools
import logging
import math
from dataclasses import dataclass, field

import ifcopenshell.util.element
import ifcopenshell.util.placement
import numpy as np

from brasbim.core import clip, geom2d, layers, materials, storeys
from brasbim.core.clip import Rings
from brasbim.core.document import Document, OpError
from brasbim.core.fillings import door_types, doors, params
from brasbim.core.geom2d import Point
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
    """Etiqueta de porta (spec/ui 05 §5): código e medidas do vão, no ponto ``at``."""

    owner: str
    at: Point
    code: str
    size: str


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
    """Contorno de uma região: espessura em metros de papel (NBR 8403) e cor."""

    rings: Rings = field(hash=False)
    weight: float
    color: str


@dataclass
class Plan:
    shapes: list[Shape] = field(default_factory=list)
    labels: list[Label] = field(default_factory=list)
    regions: list[Region] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)

    def owners(self, role_prefix: str) -> dict[str, list[Shape]]:
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
        """Elemento sob o ponto: porta (caixa envolvente) antes de parede (polígono)."""
        for owner, shapes in sorted(self.owners("door").items()):
            pts = [q for s in shapes for q in s.points]
            if (min(q[0] for q in pts) - tol <= p[0] <= max(q[0] for q in pts) + tol
                    and min(q[1] for q in pts) - tol <= p[1] <= max(q[1] for q in pts) + tol):
                return owner
        for roles in (("wall",), ("wall_view", "wall_above")):  # cortadas primeiro
            walls = [s for s in self.shapes if s.role in roles]
            for s in walls:
                if s.closed and _inside(s.points, p):
                    return s.owner
            near = [(_distance_to_outline(s.points, p, s.closed), s.owner) for s in walls]
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

        def inside(q):
            return x0 <= q[0] <= x1 and y0 <= q[1] <= y1

        out = []
        groups = {**self.owners("wall"), **self.owners("door")}
        for owner, shapes in sorted(groups.items()):
            shapes = [s for s in shapes if s.role != "below"]
            if not shapes:
                continue
            if not crossing:
                if all(inside(q) for s in shapes for q in s.points):
                    out.append(owner)
            elif any(_touches(s, rect, inside) for s in shapes):
                out.append(owner)
        return out


def _segments(points, closed: bool):
    n = len(points)
    return [(points[i - 1], points[i]) for i in range(0 if closed else 1, n)]


def _cross(p, q, r, s) -> bool:
    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    d1, d2 = orient(r, s, p), orient(r, s, q)
    d3, d4 = orient(p, q, r), orient(p, q, s)
    return (d1 > 0) != (d2 > 0) and (d3 > 0) != (d4 > 0)


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
        for opening in openings.of_wall(wall):
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
            plan.edges.append(Edge(rings, LAYER_WEIGHT, materials.LINE_COLOR))
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


def _door_to_storey(door, storey):
    m = np.linalg.inv(ifcopenshell.util.placement.get_local_placement(storey.ObjectPlacement)) \
        @ ifcopenshell.util.placement.get_local_placement(door.ObjectPlacement)
    return lambda p: tuple(float(v) for v in (m @ (p[0], p[1], 0.0, 1.0))[:2])


def door_shapes(doc: Document, door, storey) -> list[Shape]:
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
    if doors.is_parametric(door):
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
    common = ifcopenshell.util.element.get_pset(door, doors.COMMON_PSET) or {}
    code = common.get("Reference") or door.Name
    if not code:
        return None
    width, height = float(door.OverallWidth), float(door.OverallHeight or 0.0)
    opening = door.FillsVoids[0].RelatingOpeningElement if door.FillsVoids else None
    if opening is not None:
        try:
            o = openings.read_state(opening)
            width, height = o["width"], o["height"]
        except OpError:
            pass
    at = _door_to_storey(door, storey)((float(door.OverallWidth) / 2, -LABEL_GAP))
    return Label(door.GlobalId, at, str(code), f"{_fmt(width)} × {_fmt(height)}")


def _continuous_last(walls) -> list:
    """Em X, a parede contínua (``RelatingElement``) é desenhada depois da outra."""
    def rank(wall):
        return any(r.is_a("IfcRelConnectsPathElements")
                   and r.RelatingConnectionType == "ATPATH"
                   and r.RelatedConnectionType == "ATPATH" for r in wall.ConnectedTo)
    return sorted(walls, key=lambda w: (rank(w), w.GlobalId))


# --- pavimento ----------------------------------------------------------------------


def _contained(storey, ifc_class: str) -> list:
    return sorted((e for e in ifcopenshell.util.element.get_decomposition(storey)
                   if e.is_a(ifc_class)), key=lambda e: e.GlobalId)


def storey_plan(doc: Document, storey, show_below: bool = True, detail: str = "simple",
                show_above: bool = True) -> Plan:
    """Planta do pavimento. ``detail``: ``simple`` ou ``layers`` (spec/ui 06 §2);
    ``show_above``: paredes e vãos acima do plano em tracejado (§3.2)."""
    plan = Plan()
    if show_below:
        storeys_ = doc.storeys()
        i = storeys_.index(storey)
        if i > 0:
            for wall in _contained(storeys_[i - 1], "IfcWall"):
                plan.shapes += wall_shapes(doc, wall, role="below")
    cut = storeys.cut_height(storey)
    cuts = [c for c in (_cut_wall(doc, wall, cut, show_above)
                        for wall in _continuous_last(_contained(storey, "IfcWall")))
            if c is not None]
    order = {"wall_above": 0, "wall_view": 1}  # acima, abaixo, cortadas (§3.2)
    plan.shapes += sorted((s for c in cuts for s in c.shapes), key=lambda s: order.get(s.role, 2))
    _regions(doc, plan, cuts, detail)
    crossed = {o for c in cuts for o in c.crossed}
    for door in _contained(storey, "IfcDoor"):
        opening = door.FillsVoids[0].RelatingOpeningElement if door.FillsVoids else None
        if opening is not None and opening.GlobalId not in crossed:
            continue  # vão fora do plano de corte: sem símbolo (spec/ui 06 §3.3)
        plan.shapes += door_shapes(doc, door, storey)
        label = door_label(doc, door, storey)
        if label is not None:
            plan.labels.append(label)
    return plan
