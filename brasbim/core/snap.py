# SPDX-License-Identifier: LGPL-3.0-or-later
"""Atração a pontos (*snap*) e parede sob o cursor, sem Qt
(``spec/ui/01-janela-e-ferramentas.md`` §3.2 e §5.5; ``spec/ui/23-precisao.md`` §2).

Coordenadas do pavimento, em metros. ``tol`` é a distância de atração em metros (quem
chama converte os pixels da tela pela escala da vista).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import ifcopenshell.util.element
import numpy as np

from brasbim.core import geom2d
from brasbim.core.document import Document, OpError
from brasbim.core.geom2d import Point
from brasbim.core.walls import rebuild
from brasbim.core.walls.wall import read_state as read_wall

# Nomes curtos mostrados junto ao marcador (spec/ui 01 §3.2, 23 §2.2).
KIND_LABEL = {"end": "extremidade", "inter": "interseção", "mid": "meio", "center": "centro",
              "perp": "perpendicular", "tan": "tangente", "path": "na parede",
              "near": "na borda", "grid": "grade", "guide": "", "free": ""}
# Tipos que o usuário liga e desliga (Exibir > Atração); "path" segue "near".
KINDS = ("end", "inter", "mid", "center", "perp", "tan", "near", "grid")
# Prioridade (spec/ui 23 §2.2): dentro de um nível ganha o mais próximo do cursor.
_TIERS = (("end", "inter"), ("mid",), ("center",), ("perp",), ("tan",), ("path", "near"))
CORNER_DEG = 12.0  # vértice com desvio menor é de curva aproximada: não é extremidade
_CELL = 2.0  # m: lado do balde do índice
_BIG = 400  # aresta que cobre mais baldes que isto fica na lista das sempre consultadas


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
    # Ponto atraído quando ``point`` é a projeção dele numa trava de eixo (§3.1).
    source: Point | None = None


@dataclass(frozen=True)
class Segment:
    a: Point
    b: Point
    owner: str
    straight: bool = True  # aresta de verdade (False: trecho de curva aproximada)


@dataclass(frozen=True)
class CircleRef:
    """Círculo (``span`` None) ou arco de ``span[0]`` a ``span[1]`` graus, anti-horário."""

    center: Point
    radius: float
    owner: str
    span: tuple[float, float] | None = None

    def contains(self, q: Point) -> bool:
        if self.span is None:
            return True
        a = math.degrees(math.atan2(q[1] - self.center[1], q[0] - self.center[0]))
        a0, a1 = self.span
        return (a - a0) % 360.0 <= (a1 - a0) % 360.0 + 1e-6


class SnapIndex:
    """Arestas, pontos e círculos do pavimento para a atração (spec/ui 23 §2.1)."""

    def __init__(self, segments=(), circles=(), corners=(), bulk=()):
        self.segments = list(segments)
        self.circles = list(circles)
        self.corners = list(corners)  # (ponto, dono)
        # Desenho importado: (dono, ``linework.Lines``), consultado com arrays (spec/ui 22
        # §7), sem um ``Segment`` por linha.
        self.bulk = list(bulk)
        self._cells: dict[tuple[int, int], list[int]] = {}
        self._big: list[int] = []
        self._points: dict[tuple[int, int], list[int]] = {}
        for i, s in enumerate(self.segments):
            x0, x1 = sorted((s.a[0], s.b[0]))
            y0, y1 = sorted((s.a[1], s.b[1]))
            cx0, cx1, cy0, cy1 = (math.floor(x0 / _CELL), math.floor(x1 / _CELL),
                                  math.floor(y0 / _CELL), math.floor(y1 / _CELL))
            if (cx1 - cx0 + 1) * (cy1 - cy0 + 1) > _BIG:
                self._big.append(i)
                continue
            for cx in range(cx0, cx1 + 1):
                for cy in range(cy0, cy1 + 1):
                    self._cells.setdefault((cx, cy), []).append(i)
        for i, (q, _) in enumerate(self.corners):
            self._points.setdefault(_cell(q), []).append(i)

    def _around(self, table, p: Point, r: float):
        cx0, cx1 = math.floor((p[0] - r) / _CELL), math.floor((p[0] + r) / _CELL)
        cy0, cy1 = math.floor((p[1] - r) / _CELL), math.floor((p[1] + r) / _CELL)
        seen = set()
        for cx in range(cx0, cx1 + 1):
            for cy in range(cy0, cy1 + 1):
                for i in table.get((cx, cy), ()):
                    if i not in seen:
                        seen.add(i)
                        yield i

    def segments_near(self, p: Point, r: float) -> list[Segment]:
        found = set(self._around(self._cells, p, r)) | set(self._big)
        out = [self.segments[i] for i in sorted(found)]
        out = [s for s in out if _seg_dist(p, s.a, s.b) <= r]
        for owner, lines in self.bulk:
            k, _ = lines.near(p, r)
            if len(k):
                a, b, _, straight = lines.segments()
                out += [Segment(tuple(a[i].tolist()), tuple(b[i].tolist()), owner,
                                bool(straight[i])) for i in k.tolist()]
        return out

    def corners_near(self, p: Point, r: float) -> list[tuple[Point, str]]:
        out = [self.corners[i] for i in self._around(self._points, p, r)
               if math.dist(p, self.corners[i][0]) <= r]
        for owner, lines in self.bulk:
            pts = lines.corners()[0]
            if not len(pts):
                continue
            d = np.hypot(pts[:, 0] - p[0], pts[:, 1] - p[1])
            out += [(tuple(q), owner) for q in pts[d <= r].tolist()]
        return out

    def circles_near(self, p: Point, r: float) -> list[CircleRef]:
        return [c for c in self.circles if abs(math.dist(p, c.center) - c.radius) <= r]

    def add_polyline(self, points, closed: bool, owner: str) -> None:
        """Acrescenta uma polilinha (antes de consultar; refaz as tabelas)."""
        segs, corners = polyline_parts(points, closed, owner)
        self.__init__(self.segments + segs, self.circles, self.corners + corners, self.bulk)


def _cell(q: Point) -> tuple[int, int]:
    return math.floor(q[0] / _CELL), math.floor(q[1] / _CELL)


def _seg_dist(p: Point, a: Point, b: Point) -> float:
    return math.dist(p, _foot(p, a, b, clamp=True))


def _foot(p: Point, a: Point, b: Point, clamp: bool) -> Point:
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = dx * dx + dy * dy
    if n < 1e-18:
        return a
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / n
    if clamp:
        t = min(max(t, 0.0), 1.0)
    return (a[0] + t * dx, a[1] + t * dy)


def _turn(prev: Point, q: Point, nxt: Point) -> float:
    a1 = math.atan2(q[1] - prev[1], q[0] - prev[0])
    a2 = math.atan2(nxt[1] - q[1], nxt[0] - q[0])
    return abs(math.degrees((a2 - a1 + math.pi) % (2 * math.pi) - math.pi))


def polyline_parts(points, closed: bool, owner: str) -> tuple[list[Segment], list]:
    """Arestas e extremidades de uma polilinha. Vértices com desvio menor que
    ``CORNER_DEG`` são de curva aproximada (arco, círculo, curva livre): não atraem como
    extremidade, e os trechos ao lado deles não têm meio."""
    pts = [tuple(map(float, q)) for q in points]
    if closed and len(pts) > 2 and math.dist(pts[0], pts[-1]) < 1e-9:
        pts = pts[:-1]
    n = len(pts)
    if n < 2:
        return [], []
    corner = []
    for i in range(n):
        if not closed and i in (0, n - 1):
            corner.append(True)
        else:
            corner.append(_turn(pts[i - 1], pts[i], pts[(i + 1) % n]) >= CORNER_DEG)
    pairs = [(i, i + 1) for i in range(n - 1)] + ([(n - 1, 0)] if closed and n > 2 else [])
    segs = [Segment(pts[i], pts[j], owner, corner[i] and corner[j]) for i, j in pairs
            if math.dist(pts[i], pts[j]) > 1e-9]
    return segs, [(pts[i], owner) for i in range(n) if corner[i]]


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


def rotate(p: Point, angle: float) -> Point:
    """``p`` girado de ``angle`` radianos em torno de (0, 0)."""
    c, s = math.cos(angle), math.sin(angle)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c)


def grid_point(p: Point, grid: float, angle: float = 0.0) -> Point:
    """Nó da grade mais próximo; com a vista girada (spec/ui 39 §3), a grade gira junto,
    em torno da origem do pavimento."""
    q = rotate(p, -angle) if angle else p
    q = (round(q[0] / grid) * grid, round(q[1] / grid) * grid)
    return rotate(q, angle) if angle else q


def snap(walls: list[WallPath], p: Point, tol: float, grid: float | None = 0.1,
         extra: list[Point] = (), index: SnapIndex | None = None,
         origin: Point | None = None, kinds=None, angle: float = 0.0) -> Snap:
    """Ponto atraído, por prioridade (spec/ui 23 §2.2): extremidades (e ``extra``) e
    interseções, meio, centro, perpendicular e tangente (a partir de ``origin``), na
    parede ou na borda, grade. ``kinds``: tipos ligados (None = todos). ``angle``: giro
    da vista, que a grade segue."""
    on = set(KINDS if kinds is None else kinds)
    if "near" in on:
        on.add("path")
    found: dict[str, list[tuple[float, Snap]]] = {}

    def add(kind: str, q: Point, wall: str | None = None) -> None:
        d = math.dist(p, q)
        if d <= tol and kind in on:
            found.setdefault(kind, []).append((d, Snap((float(q[0]), float(q[1])), kind,
                                                       wall)))

    for w in walls:
        for q in w.ends():
            add("end", q, w.gid)
        add("mid", w.middle(), w.gid)
        q, _, _ = w.project(p)
        add("path", q, w.gid)
    for q in extra:
        add("end", tuple(q))
    if index is not None:
        _index_candidates(index, p, tol, origin, add)
    for tier in _TIERS:
        best = [c for kind in tier for c in found.get(kind, ())]
        if best:
            return min(best, key=lambda c: (c[0], tier.index(c[1].kind)))[1]
    if grid and "grid" in on:
        return Snap(grid_point(p, grid, angle), "grid")
    return Snap(tuple(p), "free")


def _index_candidates(index: SnapIndex, p: Point, tol: float, origin: Point | None,
                      add) -> None:
    for q, _ in index.corners_near(p, tol):
        add("end", q)
    segs = index.segments_near(p, tol)
    for s in segs:
        if s.straight:
            add("mid", ((s.a[0] + s.b[0]) / 2, (s.a[1] + s.b[1]) / 2))
        add("near", _foot(p, s.a, s.b, clamp=True))
        if origin is not None and s.straight:
            foot = _foot(origin, s.a, s.b, clamp=False)
            if _seg_dist(foot, s.a, s.b) < 1e-9 and math.dist(foot, origin) > 1e-9:
                add("perp", foot)
    circles = index.circles_near(p, tol)
    for c in index.circles:
        if math.dist(p, c.center) <= tol:
            add("center", c.center)
    for c in circles:
        if c.span is not None:
            a0, a1 = c.span
            mid = math.radians(a0 + ((a1 - a0) % 360.0) / 2)
            add("mid", (c.center[0] + c.radius * math.cos(mid),
                        c.center[1] + c.radius * math.sin(mid)))
    for i, s in enumerate(segs):
        for t in segs[i + 1:]:
            q = _seg_cross(s, t) if s.straight or t.straight or s.owner != t.owner else None
            if q is not None:
                add("inter", q)
        for c in circles:
            if c.owner == s.owner:  # a própria curva aproximada
                continue
            line = geom2d.StraightLine(s.a, _unit(s.a, s.b))
            for q in geom2d.intersect(line, geom2d.Circle(c.center, c.radius)):
                if _seg_dist(q, s.a, s.b) < 1e-9 and c.contains(q):
                    add("inter", q)
    for i, c in enumerate(circles):
        for k in circles[i + 1:]:
            for q in geom2d.intersect(geom2d.Circle(c.center, c.radius),
                                      geom2d.Circle(k.center, k.radius)):
                if c.contains(q) and k.contains(q):
                    add("inter", q)
        if origin is not None:
            for q in tangent_points(origin, c.center, c.radius):
                if c.contains(q):
                    add("tan", q)


def _unit(a: Point, b: Point) -> Point:
    n = math.dist(a, b)
    return ((b[0] - a[0]) / n, (b[1] - a[1]) / n)


def _seg_cross(s: Segment, t: Segment) -> Point | None:
    """Cruzamento de dois segmentos fora das pontas compartilhadas, ou None."""
    r = (s.b[0] - s.a[0], s.b[1] - s.a[1])
    q = (t.b[0] - t.a[0], t.b[1] - t.a[1])
    den = r[0] * q[1] - r[1] * q[0]
    if abs(den) < 1e-12:
        return None
    w = (t.a[0] - s.a[0], t.a[1] - s.a[1])
    u = (w[0] * q[1] - w[1] * q[0]) / den
    v = (w[0] * r[1] - w[1] * r[0]) / den
    eps = 1e-9
    if not (-eps <= u <= 1 + eps and -eps <= v <= 1 + eps):
        return None
    if min(u, 1 - u) < 1e-7 and min(v, 1 - v) < 1e-7:
        return None  # ponta dos dois (vértice compartilhado): é extremidade, se for
    return (s.a[0] + u * r[0], s.a[1] + u * r[1])


def tangent_points(origin: Point, center: Point, radius: float) -> list[Point]:
    """Pontos de tangência das retas que saem de ``origin`` e tocam o círculo."""
    d = math.dist(origin, center)
    if d <= radius + 1e-9:
        return []
    base = math.atan2(origin[1] - center[1], origin[0] - center[0])
    half = math.acos(radius / d)
    return [(center[0] + radius * math.cos(base + s * half),
             center[1] + radius * math.sin(base + s * half)) for s in (-1, 1)]


def build_index(doc: Document, storey, the_plan) -> SnapIndex:
    """Índice do pavimento a partir da planta já montada (spec/ui 23 §2.1): formas dos
    elementos, traços das anotações (inclusive o desenho importado) e as curvas exatas
    de círculos, arcos e paredes em arco."""
    from brasbim.core.annotations import drawing2d

    segments, corners, circles, owners, bulk = [], [], [], set(), []
    for shape in the_plan.shapes:
        owners.add(shape.owner)
        segs, pts = polyline_parts(shape.points, shape.closed, shape.owner)
        segments += segs
        corners += pts
    for owner, prims in the_plan.annotations:
        owners.add(owner)
        for stroke in prims.strokes:
            segs, pts = polyline_parts(stroke.points, stroke.closed, owner)
            segments += segs
            corners += pts
        bulk += [(owner, lines) for lines, _ in prims.bulk]
    for owner in sorted(owners):
        found = drawing2d.curve_of(doc, owner)
        if found is None:
            continue
        span = None
        element = doc.find(owner)
        if element is not None and element.is_a("IfcAnnotation"):
            from brasbim.core.annotations import base as annotation_base

            state = annotation_base.read_state(element)
            if annotation_base.kind_of(element) is drawing2d.ARC:
                span = (float(state["start"]), float(state["end"]))
        else:
            span = _wall_span(doc, element)
        circles.append(CircleRef(found[0], found[1], owner, span))
    return SnapIndex(segments, circles, corners, bulk)


def _wall_span(doc: Document, wall) -> tuple[float, float] | None:
    path = geom2d.path_from_dict(read_wall(doc, wall)["path"])
    center = geom2d.frame(path).to_global(path.local_center())
    a = [math.degrees(math.atan2(q[1] - center[1], q[0] - center[0]))
         for q in (path.start, path.end)]
    return (a[0], a[1]) if path.ccw else (a[1], a[0])


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


def constrain(origin: Point, p: Point, step_deg: float = 45.0, base: float = 0.0) -> Point:
    """Ponto na direção múltipla de ``step_deg`` mais próxima, à mesma distância (Shift).
    ``base``: giro da vista em radianos, de onde os múltiplos partem."""
    dx, dy = p[0] - origin[0], p[1] - origin[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return p
    step = math.radians(step_deg)
    angle = round((math.atan2(dy, dx) - base) / step) * step + base
    return (origin[0] + length * math.cos(angle), origin[1] + length * math.sin(angle))
