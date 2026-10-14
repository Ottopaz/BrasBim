# SPDX-License-Identifier: LGPL-3.0-or-later
"""Planta de um pavimento como primitivas 2D, sem Qt (``spec/ui/01-janela-e-ferramentas.md``
§3, ``parede.md`` §7, ``porta.md`` §7).

Versão simplificada: tudo o que é do pavimento aparece cortado; os vãos que o plano de
corte atravessa interrompem a parede; portas com folha aberta a 90° e arco de giro. As
coordenadas são as do pavimento, em metros. Nada disto é gravado no IFC.

Papéis (``Shape.role``): ``wall`` (preenchida), ``below`` (parede do pavimento de baixo),
``door_frame`` (marco, preenchido), ``door_leaf`` (folha), ``door_swing`` (arco de giro,
linha fina), ``door_arrow`` (seta de correr), ``door_hidden`` (tracejada) e ``door``
(contorno de porta de outra origem).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

import ifcopenshell.util.element
import ifcopenshell.util.placement
import numpy as np

from brasbim.core import geom2d
from brasbim.core.document import Document, OpError
from brasbim.core.fillings import door_types, doors, params
from brasbim.core.geom2d import Point
from brasbim.core.walls import openings, rebuild
from brasbim.core.walls import types as wall_types
from brasbim.core.walls.wall import read_state as read_wall

log = logging.getLogger(__name__)

CUT_HEIGHT = 1.50  # plano de corte acima do piso do pavimento (parede §7, a confirmar)
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


@dataclass
class Plan:
    shapes: list[Shape] = field(default_factory=list)
    labels: list[Label] = field(default_factory=list)

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
        walls = [s for s in self.shapes if s.role == "wall"]
        for s in walls:
            if _inside(s.points, p):
                return s.owner
        near = [(_distance_to_outline(s.points, p), s.owner) for s in walls]
        near = [n for n in near if n[0] <= tol]
        return min(near)[1] if near else None


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


def _distance_to_outline(points, p) -> float:
    return min(distance_to_segment(p, points[i - 1], points[i]) for i in range(len(points)))


# --- paredes -------------------------------------------------------------------------


def _cut_intervals(wall, length: float) -> list[tuple[float, float]]:
    """Trechos da parede reta que não estão em vão atravessado pelo plano de corte."""
    gaps = []
    for opening in openings.of_wall(wall):
        try:
            o = openings.read_state(opening)
        except OpError:
            continue
        if o["kind"] == "OPENING" and o["sill"] <= CUT_HEIGHT <= o["sill"] + o["height"]:
            gaps.append((o["distance"], o["distance"] + o["width"]))
    out, x = [], -math.inf
    for a, b in sorted(gaps):
        if a > x:
            out.append((x, a))
        x = max(x, b)
    out.append((x, math.inf))
    return [(a, b) for a, b in out if b - a > 1e-6 and a < length + 1 and b > -1]


def wall_shapes(doc: Document, wall, role: str = "wall") -> list[Shape]:
    try:
        state = read_wall(doc, wall)
        band = rebuild.band(doc, state)
        segments = rebuild.profile(doc, wall, band)
    except (OpError, ValueError) as e:
        log.warning("parede %s fora da planta: %s", wall.GlobalId, e)
        return []
    local = geom2d.polygon(segments)
    pieces = [local]
    if role == "wall" and isinstance(band.path, geom2d.LinePath):
        pieces = [geom2d.clip_rect(local, a, b, -math.inf, math.inf)
                  for a, b in _cut_intervals(wall, band.path.length)]
    frame = band.frame
    style = (wall_types.plan_style(doc.get(state["type"], "IfcWallType"))
             if role == "wall" else None)
    return [Shape(wall.GlobalId, role, tuple(frame.to_global(p) for p in piece), True, style)
            for piece in pieces if piece]


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


def storey_plan(doc: Document, storey, show_below: bool = True) -> Plan:
    plan = Plan()
    if show_below:
        storeys = doc.storeys()
        i = storeys.index(storey)
        if i > 0:
            for wall in _contained(storeys[i - 1], "IfcWall"):
                plan.shapes += wall_shapes(doc, wall, role="below")
    for wall in _continuous_last(_contained(storey, "IfcWall")):
        plan.shapes += wall_shapes(doc, wall)
    for door in _contained(storey, "IfcDoor"):
        plan.shapes += door_shapes(doc, door, storey)
        label = door_label(doc, door, storey)
        if label is not None:
            plan.labels.append(label)
    return plan
