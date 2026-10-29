# SPDX-License-Identifier: LGPL-3.0-or-later
"""Linhas-guia (spec/ui 37): retas temporárias que saem dos pontos de referência e do
ponto anterior a 0°, 45°, 90° e 135°; o cursor perto de uma delas se prende a ela, e o
cruzamento de duas guias, ou de uma guia com uma aresta, prende mais forte."""

from __future__ import annotations

import math
from dataclasses import dataclass

Point = tuple[float, float]

ANGLES = (0.0, 45.0, 90.0, 135.0)
MAX_REFS = 3  # pontos de referência ao mesmo tempo; o mais antigo sai (§2)
CROSS = 1.5  # cruzamento atrai até 1,5 × a distância de atração (§3)


@dataclass(frozen=True)
class Guide:
    source: Point
    angle: float  # graus, em [0, 180)
    from_ref: bool  # True: ponto de referência; False: ponto anterior da ferramenta

    @property
    def dir(self) -> Point:
        a = math.radians(self.angle)
        return (math.cos(a), math.sin(a))

    def distance(self, p: Point) -> float:
        ux, uy = self.dir
        return abs((p[0] - self.source[0]) * uy - (p[1] - self.source[1]) * ux)

    def project(self, p: Point) -> Point:
        ux, uy = self.dir
        t = (p[0] - self.source[0]) * ux + (p[1] - self.source[1]) * uy
        return (self.source[0] + t * ux, self.source[1] + t * uy)


@dataclass(frozen=True)
class Tracked:
    point: Point
    guides: tuple[Guide, ...]
    crossing: bool = False  # cruzamento de duas guias ou de uma guia com uma aresta

    def reference(self) -> Guide | None:
        """A guia que sai de um ponto de referência (a que mede a distância)."""
        return next((g for g in self.guides if g.from_ref), None)


def guides_from(refs, origin: Point | None, angles=ANGLES) -> list[Guide]:
    out = [Guide(tuple(r), a, True) for r in refs for a in angles]
    if origin is not None and all(math.dist(origin, r) > 1e-9 for r in refs):
        out += [Guide(tuple(origin), a, False) for a in angles]
    return out


def _cross(g: Guide, h: Guide) -> Point | None:
    (ux, uy), (vx, vy) = g.dir, h.dir
    den = ux * vy - uy * vx
    if abs(den) < 1e-9:
        return None
    dx, dy = h.source[0] - g.source[0], h.source[1] - g.source[1]
    t = (dx * vy - dy * vx) / den
    return (g.source[0] + t * ux, g.source[1] + t * uy)


def _cross_segment(g: Guide, a: Point, b: Point) -> Point | None:
    ux, uy = g.dir
    ex, ey = b[0] - a[0], b[1] - a[1]
    den = ux * ey - uy * ex
    if abs(den) < 1e-12:
        return None
    dx, dy = a[0] - g.source[0], a[1] - g.source[1]
    s = (dx * uy - dy * ux) / den  # posição na aresta, de 0 (a) a 1 (b)
    if not -1e-9 <= s <= 1 + 1e-9:
        return None
    return (a[0] + s * ex, a[1] + s * ey)


def track(p: Point, guides: list[Guide], tol: float, segments=()) -> Tracked | None:
    """Ponto da guia mais próxima de ``p`` (até ``tol``), ou None. Cruzamento de duas
    guias, ou de uma guia com uma das ``segments`` (pares de pontos), vence a guia só."""
    near = [(g.distance(p), g) for g in guides
            if g.distance(p) <= tol and math.dist(p, g.source) > tol]
    if not near:
        return None
    near.sort(key=lambda n: n[0])
    best = None
    for i, (_, g) in enumerate(near):
        for _, h in near[i + 1:]:
            if math.dist(g.source, h.source) < 1e-9:
                continue
            x = _cross(g, h)
            if x is not None and math.dist(x, p) <= CROSS * tol and (
                    best is None or math.dist(x, p) < math.dist(best.point, p)):
                best = Tracked(x, (g, h), True)
    if best is not None:
        return best
    g = near[0][1]
    for a, b in segments:
        x = _cross_segment(g, a, b)
        if x is not None and math.dist(x, p) <= CROSS * tol and (
                best is None or math.dist(x, p) < math.dist(best.point, p)):
            best = Tracked(x, (g,), True)
    return best or Tracked(g.project(p), (g,))


def round_along(t: Tracked, step: float) -> Tracked:
    """Guia só: a distância à origem da guia vai ao múltiplo de ``step`` mais próximo
    (sobre a guia, a grade continua valendo)."""
    g = t.guides[0]
    (ux, uy), (sx, sy) = g.dir, g.source
    d = (t.point[0] - sx) * ux + (t.point[1] - sy) * uy
    d = round(d / step) * step
    return Tracked((sx + d * ux, sy + d * uy), t.guides)


def through(q: Point, guides: list[Guide], eps: float) -> Tracked | None:
    """Guias que passam por ``q`` (ponto atraído que já está alinhado): só para mostrar."""
    on = tuple(g for g in guides if g.distance(q) <= eps and math.dist(q, g.source) > eps)
    return Tracked(q, on[:2]) if on else None
