# SPDX-License-Identifier: LGPL-3.0-or-later
"""Junções de paredes (spec §6.2): detecção e recorte do perfil, sem IFC.

Uma parede é vista aqui como uma faixa (``Band``): o caminho da linha de referência e o
intervalo ``ymin..ymax`` ocupado pela espessura no sistema local do caminho. Tudo é
calculado em coordenadas do pavimento.

Recorte (decisão do projeto, aprovada em 2026-10-14):

- L com espessuras iguais: as duas paredes são cortadas pela reta que liga os dois cantos
  (interseções das faces correspondentes). Entre retas, é a meia-esquadria (bissetriz).
- L com espessuras diferentes: a mais espessa vai até a face externa da mais fina, e a
  mais fina para na face interna da mais espessa.
- L colinear (faces paralelas): corte perpendicular ao caminho no nó.
- T: a parede que chega é cortada pela face da contínua voltada para ela.
- X: sem recorte.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from brasbim.core import geom2d
from brasbim.core.geom2d import Curve, Path, Point

TOL = 0.001  # tolerância de detecção (spec §6.2)
ENDS = ("ATSTART", "ATEND")
_PARALLEL = 1e-3  # seno do ângulo abaixo do qual as faces são tratadas como paralelas


def _cross(a: Point, b: Point) -> float:
    return a[0] * b[1] - a[1] * b[0]


def _dot(a: Point, b: Point) -> float:
    return a[0] * b[0] + a[1] * b[1]


@dataclass(frozen=True)
class Band:
    path: Path
    ymin: float
    ymax: float

    @property
    def frame(self) -> geom2d.Frame:
        return geom2d.frame(self.path)

    @property
    def thickness(self) -> float:
        return self.ymax - self.ymin

    def face(self, y: float) -> Curve:
        return self.frame.curve_to_global(self.path.face(y))

    def node(self, end: str) -> Point:
        return self.path.start if end == "ATSTART" else self.path.end

    def away(self, end: str) -> Point:
        """Direção, no nó, que aponta para dentro da parede."""
        if end == "ATSTART":
            return self.frame.vector_to_global(self.path.tangent(0.0))
        tx, ty = self.frame.vector_to_global(self.path.tangent(self.path.t_end))
        return (-tx, -ty)

    def away_faces(self, end: str) -> tuple[float, float]:
        """(face esquerda, face direita) para quem sai do nó entrando na parede."""
        return (self.ymax, self.ymin) if end == "ATSTART" else (self.ymin, self.ymax)

    def offset(self, p: Point) -> float:
        return self.path.offset(self.frame.to_local(p))


def _normal_cut(band: Band, end: str) -> Curve:
    d = band.away(end)
    return geom2d.StraightLine(band.node(end), (-d[1], d[0]))


def l_cuts(a: Band, ea: str, b: Band, eb: str) -> tuple[Curve | None, Curve | None]:
    """Cortes das paredes ``a`` e ``b`` numa junção L (coordenadas do pavimento)."""
    da, db = a.away(ea), b.away(eb)
    turn = _cross(da, db)
    if abs(turn) < _PARALLEL:
        if _dot(da, db) > 0:  # dobram uma sobre a outra: sem recorte
            return None, None
        return _normal_cut(a, ea), _normal_cut(b, eb)
    la, ra = a.away_faces(ea)
    lb, rb = b.away_faces(eb)
    node = a.node(ea)
    if abs(a.thickness - b.thickness) < 1e-6:
        p1 = geom2d.nearest(geom2d.intersect(a.face(la), b.face(rb)), node)
        p2 = geom2d.nearest(geom2d.intersect(a.face(ra), b.face(lb)), node)
        if p1 is None or p2 is None or math.dist(p1, p2) < 1e-9:
            return None, None
        cut = geom2d.line_through(p1, p2)
        return cut, cut
    # b à esquerda de a: lado interno de a é a esquerda e o de b, a direita.
    a_in, a_out = (la, ra) if turn > 0 else (ra, la)
    b_in, b_out = (rb, lb) if turn > 0 else (lb, rb)
    if a.thickness > b.thickness:
        return b.face(b_out), a.face(a_in)
    return b.face(b_in), a.face(a_out)


def t_cut(arriving: Band, end: str, through: Band) -> Curve:
    """Corte da parede que chega (``arriving``) na face da parede contínua."""
    node = arriving.node(end)
    d = arriving.away(end)
    probe = (node[0] + d[0] * 1e-3, node[1] + d[1] * 1e-3)
    side = through.offset(probe) - through.offset(node)
    return through.face(through.ymax if side > 0 else through.ymin)


# --- detecção --------------------------------------------------------------------


def _locate(path: Path, p: Point) -> tuple[float, float]:
    """(posição ao longo do caminho, distância) do ponto mais próximo na curva do caminho."""
    local = geom2d.frame(path).to_local(p)
    t = path.param(local)
    if isinstance(path, geom2d.ArcPath):
        t %= 2 * math.pi
    return path.arc_length(t), abs(path.offset(local))


def _interior(path: Path, p: Point) -> bool:
    s, dist = _locate(path, p)
    return dist <= TOL < s < path.length - TOL


def _endpoint(path: Path, end: str) -> Point:
    return path.start if end == "ATSTART" else path.end


def _curve(path: Path) -> Curve:
    return geom2d.frame(path).curve_to_global(path.face(0.0))


def detect(a: Path, b: Path) -> list[tuple[str, str]]:
    """Junções entre os caminhos ``a`` e ``b``: lista de (tipo em a, tipo em b).

    Tipos: ``ATSTART``/``ATEND`` (extremidade) e ``ATPATH`` (meio do caminho).
    """
    found = []
    ends_a, ends_b = set(), set()
    for ea in ENDS:
        for eb in ENDS:
            if math.dist(_endpoint(a, ea), _endpoint(b, eb)) <= TOL:
                found.append((ea, eb))
                ends_a.add(ea)
                ends_b.add(eb)
    for ea in ENDS:
        if ea not in ends_a and _interior(b, _endpoint(a, ea)):
            found.append((ea, "ATPATH"))
    for eb in ENDS:
        if eb not in ends_b and _interior(a, _endpoint(b, eb)):
            found.append(("ATPATH", eb))
    ends = [_endpoint(a, e) for e in ENDS] + [_endpoint(b, e) for e in ENDS]
    for p in geom2d.intersect(_curve(a), _curve(b)):
        if (_interior(a, p) and _interior(b, p)
                and all(math.dist(p, q) > TOL for q in ends)):
            found.append(("ATPATH", "ATPATH"))
            break
    return found
