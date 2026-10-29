# SPDX-License-Identifier: LGPL-3.0-or-later
"""Área de seleção (spec/ui 38): um polígono na planta, de um pavimento ou de todos, que
diz o que esticar, o que mostrar no 3D e o pedaço da planta a exportar. Não vai para o
IFC: é estado da sessão."""

from __future__ import annotations

import math
from dataclasses import dataclass

from brasbim.core import geom2d
from brasbim.core.geom2d import Point


@dataclass(frozen=True)
class Area:
    points: tuple[Point, ...]  # contorno fechado, sem repetir o primeiro ponto
    all_storeys: bool = False

    @staticmethod
    def rectangle(a: Point, b: Point, all_storeys: bool = False) -> Area:
        (x0, y0), (x1, y1) = a, b
        return Area(((x0, y0), (x1, y0), (x1, y1), (x0, y1)), all_storeys)

    def bounds(self) -> tuple[float, float, float, float]:
        xs, ys = [p[0] for p in self.points], [p[1] for p in self.points]
        return min(xs), min(ys), max(xs), max(ys)

    def contains(self, p: Point, eps: float = 1e-9) -> bool:
        """Ponto dentro ou sobre a borda."""
        pts = self.points
        n = len(pts)
        for i in range(n):  # na borda conta como dentro
            a, b = pts[i], pts[(i + 1) % n]
            if _seg_dist(p, a, b) <= eps:
                return True
        inside = False
        x, y = p
        for i in range(n):
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
            if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
                inside = not inside
        return inside

    def moved(self, vector: Point) -> Area:
        return Area(tuple((x + vector[0], y + vector[1]) for x, y in self.points),
                    self.all_storeys)


def valid(points) -> bool:
    """Polígono com área (três pontos ou mais, não alinhados)."""
    pts = list(points)
    if len(pts) < 3:
        return False
    a = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
            for i in range(len(pts)))
    return abs(a) > 1e-6


def stretch_fn(area: Area, vector: Point):
    """Leva os pontos de dentro da área pelo vetor; os de fora ficam."""
    move = geom2d.translation(tuple(vector))
    return lambda p: move(p) if area.contains(tuple(p)) else tuple(p)


def touched(plan, area: Area) -> list[str]:
    """Donos de formas da planta com algum ponto dentro da área (os que podem esticar)."""
    out: dict[str, None] = {}
    for s in plan.shapes:
        if s.owner and s.owner not in plan.locked and any(area.contains(q) for q in s.points):
            out[s.owner] = None
    for owner, prims in plan.annotations:
        if owner in plan.locked or owner in out:
            continue
        if any(area.contains(tuple(q)) for q in _prim_points(prims)):
            out[owner] = None
    return list(out)


def _prim_points(prims):
    """Pontos dos traços e âncoras dos textos (o desenho importado não estica)."""
    for s in prims.strokes:
        yield from s.points
    for t in prims.texts:
        yield t.at


def _seg_dist(p: Point, a: Point, b: Point) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = dx * dx + dy * dy
    t = 0.0 if n < 1e-18 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / n))
    return math.dist(p, (a[0] + t * dx, a[1] + t * dy))
