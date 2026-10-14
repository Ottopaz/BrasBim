# SPDX-License-Identifier: LGPL-3.0-or-later
"""Atração a pontos (*snap*) e parede sob o cursor, sem Qt
(``spec/ui/01-janela-e-ferramentas.md`` §3.2 e §5.5).

Coordenadas do pavimento, em metros. ``tol`` é a distância de atração em metros (quem
chama converte os pixels da tela pela escala da vista).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import ifcopenshell.util.element

from brasbim.core import geom2d
from brasbim.core.document import Document, OpError
from brasbim.core.geom2d import Point
from brasbim.core.walls import rebuild
from brasbim.core.walls.wall import read_state as read_wall

# Nomes curtos mostrados junto ao marcador (spec/ui §3.2).
KIND_LABEL = {"end": "extremidade", "mid": "meio", "path": "na parede", "grid": "grade",
              "free": ""}


@dataclass(frozen=True)
class WallPath:
    """Caminho e faixa de espessura de uma parede, em coordenadas do pavimento."""

    gid: str
    path: geom2d.Path
    ymin: float
    ymax: float

    @property
    def frame(self) -> geom2d.Frame:
        return geom2d.frame(self.path)

    @property
    def straight(self) -> bool:
        return isinstance(self.path, geom2d.LinePath)

    def ends(self) -> list[Point]:
        return [self.path.start, self.path.end]

    def middle(self) -> Point:
        return self.frame.to_global(self.path.point(0.0, self.path.t_end / 2))

    def param(self, p: Point) -> float:
        """Parâmetro local do ponto (abscissa ou ângulo), sem limitar ao caminho."""
        local = self.frame.to_local(p)
        return geom2d.unwrap(self.path, self.path.param(local), self.path.t_end / 2)

    def project(self, p: Point) -> tuple[Point, float, float]:
        """(ponto mais próximo no caminho, distância ao longo dele, afastamento à esquerda)."""
        path, frame = self.path, self.frame
        t = min(max(self.param(p), 0.0), path.t_end)
        return (frame.to_global(path.point(0.0, t)), path.arc_length(t),
                path.offset(frame.to_local(p)))


@dataclass(frozen=True)
class Snap:
    point: Point
    kind: str  # chave de KIND_LABEL
    wall: str | None = None


def wall_paths(doc: Document, storey) -> list[WallPath]:
    out = []
    for wall in ifcopenshell.util.element.get_decomposition(storey):
        if not wall.is_a("IfcWall"):
            continue
        try:
            band = rebuild.band(doc, read_wall(doc, wall))
        except (OpError, ValueError):
            continue
        out.append(WallPath(wall.GlobalId, band.path, band.ymin, band.ymax))
    return sorted(out, key=lambda w: w.gid)


def snap(walls: list[WallPath], p: Point, tol: float, grid: float | None = 0.1,
         extra: list[Point] = ()) -> Snap:
    """Ponto atraído, por prioridade: extremidades (e ``extra``), meio, caminho, grade."""
    best = None
    for w in walls:
        for q in w.ends():
            d = math.dist(p, q)
            if d <= tol and (best is None or d < best[0]):
                best = (d, Snap(q, "end", w.gid))
    for q in extra:
        d = math.dist(p, q)
        if d <= tol and (best is None or d < best[0]):
            best = (d, Snap(tuple(q), "end"))
    if best:
        return best[1]
    for w in walls:
        q = w.middle()
        d = math.dist(p, q)
        if d <= tol and (best is None or d < best[0]):
            best = (d, Snap(q, "mid", w.gid))
    if best:
        return best[1]
    for w in walls:
        q, _, _ = w.project(p)
        d = math.dist(p, q)
        if d <= tol and (best is None or d < best[0]):
            best = (d, Snap(q, "path", w.gid))
    if best:
        return best[1]
    if grid:
        return Snap((round(p[0] / grid) * grid, round(p[1] / grid) * grid), "grid")
    return Snap(tuple(p), "free")


@dataclass(frozen=True)
class WallHit:
    wall: WallPath
    along: float  # distância ao longo do caminho até o ponto projetado
    left: bool  # o ponto está do lado esquerdo do meio da espessura


def wall_at(walls: list[WallPath], p: Point, tol: float) -> WallHit | None:
    """Parede cuja espessura (com folga ``tol``) contém o ponto; a mais próxima do meio."""
    found = []
    for w in walls:
        t = w.param(p)
        slack = tol if w.straight else tol / max(w.path.radius, 1e-9)
        if not -slack <= t <= w.path.t_end + slack:
            continue
        _, along, offset = w.project(p)
        if w.ymin - tol <= offset <= w.ymax + tol:
            center = (w.ymin + w.ymax) / 2
            found.append((abs(offset - center), w.gid, WallHit(w, along, offset > center)))
    return min(found)[2] if found else None


def constrain(origin: Point, p: Point, step_deg: float = 45.0) -> Point:
    """Ponto na direção múltipla de ``step_deg`` mais próxima, à mesma distância (Shift)."""
    dx, dy = p[0] - origin[0], p[1] - origin[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return p
    step = math.radians(step_deg)
    angle = round(math.atan2(dy, dx) / step) * step
    return (origin[0] + length * math.cos(angle), origin[1] + length * math.sin(angle))
