# SPDX-License-Identifier: LGPL-3.0-or-later
"""Contorno de um cômodo fechado por paredes, para a laje pelo cômodo (spec/ui 12 §4).

O cômodo é o furo da união das plantas das paredes do pavimento (as faixas inteiras, sem
o plano de corte; portas e janelas não abrem o cômodo) que contém o ponto. O contorno
pode ficar na face interna (o próprio furo), no eixo das paredes ou na face externa: cada
lado do furo é afastado pela metade ou pela espessura toda da parede que o forma, e os
cantos são refeitos pelo cruzamento dos lados vizinhos.
"""

from __future__ import annotations

import itertools
import math

import ifcopenshell.util.element

from brasbim.core import clip, geom2d
from brasbim.core.document import Document, OpError
from brasbim.core.walls import rebuild as wall_rebuild
from brasbim.core.walls.wall import read_state as read_wall

BOUNDARIES = ("inner", "axis", "outer")
NOT_A_ROOM = "o ponto não está num cômodo fechado por paredes"
_ON = 1e-5  # m: ponto sobre a face de uma parede


def walls_of(doc: Document, storey) -> list[tuple[list, float]]:
    """(planta, espessura) de cada parede do pavimento."""
    return [(ring, thickness) for ring, thickness, _ in wall_rings(doc, storey)]


def wall_rings(doc: Document, storey) -> list[tuple[list, float, object]]:
    """(planta, espessura, parede) de cada parede do pavimento."""
    out = []
    for wall in ifcopenshell.util.element.get_decomposition(storey):
        if not wall.is_a("IfcWall"):
            continue
        try:
            state = read_wall(doc, wall)
            band = wall_rebuild.band(doc, state)
            segments = wall_rebuild.profile(doc, wall, band)
        except (OpError, ValueError):
            continue
        ring = [band.frame.to_global(p) for p in geom2d.polygon(segments, arc_steps=16)]
        out.append((ring, band.thickness, wall))
    return out


def _inside(ring, p) -> bool:
    inside = False
    n = len(ring)
    for i in range(n):
        (x0, y0), (x1, y1) = ring[i - 1], ring[i]
        if (y0 > p[1]) != (y1 > p[1]):
            x = x0 + (p[1] - y0) * (x1 - x0) / (y1 - y0)
            if x > p[0]:
                inside = not inside
    return inside


def _dist_to_segment(p, a, b) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    n2 = dx * dx + dy * dy
    t = 0.0 if n2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / n2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def _on_ring(p, ring) -> bool:
    return any(_dist_to_segment(p, ring[i - 1], ring[i]) <= _ON for i in range(len(ring)))


def room_ring(doc: Document, storey, point, walls=None) -> tuple[list, list]:
    """(furo anti-horário que contém o ponto, paredes do pavimento). Recusa se não há.
    ``walls``: o ``walls_of`` do pavimento, se já calculado."""
    walls = walls_of(doc, storey) if walls is None else walls
    if not walls:
        raise OpError(NOT_A_ROOM)
    union = clip.union([list(r) for r, _ in walls])
    outer = math.copysign(1.0, clip.signed_area(max(union, key=lambda r: abs(
        clip.signed_area(r)))))
    # Furos: anéis com o sentido oposto ao dos contornos externos.
    holes = [r for r in union if clip.signed_area(r) * outer < 0 and _inside(r, point)]
    if not holes or any(_inside(r, point) for r, _ in walls):
        raise OpError(NOT_A_ROOM)
    ring = list(min(holes, key=lambda r: abs(clip.signed_area(r))))
    if clip.signed_area(ring) < 0:
        ring.reverse()
    return ring, walls


def _thickness(a, b, walls) -> float:
    """Espessura da parede em cuja face está o trecho ``a``–``b`` (0 se nenhuma)."""
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    found = [t for ring, t in walls if _on_ring(mid, ring)]
    return max(found) if found else 0.0


def _pieces(ring, walls) -> list[tuple[tuple, tuple, float]]:
    """Lados do furo, divididos onde muda a parede, com a espessura de cada trecho."""
    corners = [p for r, _ in walls for p in r]
    out = []
    n = len(ring)
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        length = math.dist(a, b)
        if length <= 1e-9:
            continue
        ts = sorted({0.0, 1.0, *(
            ((q[0] - a[0]) * (b[0] - a[0]) + (q[1] - a[1]) * (b[1] - a[1])) / length ** 2
            for q in corners if _dist_to_segment(q, a, b) <= _ON)})
        ts = [t for t in ts if 0.0 <= t <= 1.0]
        for t0, t1 in itertools.pairwise(ts):
            if (t1 - t0) * length <= 1e-6:
                continue
            p = (a[0] + t0 * (b[0] - a[0]), a[1] + t0 * (b[1] - a[1]))
            q = (a[0] + t1 * (b[0] - a[0]), a[1] + t1 * (b[1] - a[1]))
            out.append((p, q, _thickness(p, q, walls)))
    return out


def _meet(p, d, q, e):
    det = d[0] * e[1] - d[1] * e[0]
    if abs(det) < 1e-12:
        return None
    t = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / det
    return (p[0] + t * d[0], p[1] + t * d[1])


def room_outline(doc: Document, storey, point, boundary: str = "outer",
                 walls=None) -> list:
    """Contorno do cômodo até a face interna, o eixo ou a face externa das paredes."""
    if boundary not in BOUNDARIES:
        raise OpError(f"contorno inválido: {boundary!r}")
    ring, walls = room_ring(doc, storey, point, walls)
    if boundary == "inner":
        return [list(p) for p in ring]
    k = 0.5 if boundary == "axis" else 1.0
    lines = []
    for a, b, t in _pieces(ring, walls):
        d = (b[0] - a[0], b[1] - a[1])
        n = math.hypot(*d)
        out = (d[1] / n, -d[0] / n)  # anti-horário: para fora fica à direita
        lines.append(((a[0] + out[0] * t * k, a[1] + out[1] * t * k), d,
                      (b[0] + out[0] * t * k, b[1] + out[1] * t * k)))
    points = []
    for i, (p, d, end) in enumerate(lines):
        prev_p, prev_d, prev_end = lines[i - 1]
        corner = _meet(prev_p, prev_d, p, d)
        if corner is None:  # lados alinhados com espessuras diferentes: degrau
            points += [prev_end, p]
        else:
            points.append(corner)
    return [list(p) for p in points]


def building_rings(doc: Document, storey, rings=None) -> list:
    """Contornos externos (face externa das paredes) de todas as edificações do
    pavimento, sem os furos dos cômodos; vazio sem paredes. ``rings``: a planta das
    paredes, já lida."""
    if rings is None:
        rings = [r for r, _ in walls_of(doc, storey)]
    if not rings:
        return []
    union = clip.union([list(r) for r in rings])
    outer = math.copysign(1.0, clip.signed_area(max(union, key=lambda r: abs(
        clip.signed_area(r)))))
    return [r for r in union if clip.signed_area(r) * outer > 0]


def building_outline(doc: Document, storey, point=None) -> list:
    """Contorno externo das paredes em volta de ``point`` (a face externa da edificação,
    para a cobertura pelas paredes, cobertura.md §4); sem ``point``, o da maior
    edificação do pavimento. Anti-horário."""
    rings = building_rings(doc, storey)
    if not rings:
        raise OpError("não há paredes no pavimento")
    if point is not None:
        rings = [r for r in rings if _inside(r, point)]
        if not rings:
            raise OpError("o ponto não está dentro de uma edificação fechada por paredes")
    ring = list(min(rings, key=lambda r: abs(clip.signed_area(r))) if point is not None
                else max(rings, key=lambda r: abs(clip.signed_area(r))))
    if clip.signed_area(ring) < 0:
        ring.reverse()
    return [list(p) for p in ring]
