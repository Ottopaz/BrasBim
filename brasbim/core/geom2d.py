# SPDX-License-Identifier: LGPL-3.0-or-later
"""Geometria 2D pura (sem IFC): caminhos de parede, perfis e áreas.

Convenções:
- Coordenadas em metros, no plano do pavimento.
- Sistema local de um caminho: origem no ponto inicial, eixo x na tangente inicial,
  eixo y para a esquerda de quem percorre o caminho.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import NamedTuple

TOL = 1e-9
MIN_LENGTH = 0.001

Point = tuple[float, float]


class Line(NamedTuple):
    p0: Point
    p1: Point


class Arc(NamedTuple):
    """Arco pelos pontos inicial, intermediário e final."""

    p0: Point
    pm: Point
    p1: Point


Segment = Line | Arc


def _sub(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1])


def _cross(a: Point, b: Point) -> float:
    return a[0] * b[1] - a[1] * b[0]


def _dist(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def circle_through(p0: Point, pm: Point, p1: Point) -> tuple[Point, float]:
    """Centro e raio do círculo pelos três pontos."""
    ax, ay = p0
    bx, by = pm
    cx, cy = p1
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < TOL:
        raise ValueError("pontos colineares não definem um arco")
    a2, b2, c2 = ax * ax + ay * ay, bx * bx + by * by, cx * cx + cy * cy
    ux = (a2 * (by - cy) + b2 * (cy - ay) + c2 * (ay - by)) / d
    uy = (a2 * (cx - bx) + b2 * (ax - cx) + c2 * (bx - ax)) / d
    return (ux, uy), _dist((ux, uy), p0)


def _arc_central_angle(arc: Arc) -> tuple[float, float]:
    """(raio, ângulo central em (0, 2π)) do arco."""
    c, r = circle_through(*arc)
    a0 = math.atan2(arc.p0[1] - c[1], arc.p0[0] - c[0])
    am = math.atan2(arc.pm[1] - c[1], arc.pm[0] - c[0])
    a1 = math.atan2(arc.p1[1] - c[1], arc.p1[0] - c[0])
    tau = 2 * math.pi
    to_end = (a1 - a0) % tau
    to_mid = (am - a0) % tau
    phi = to_end if to_mid < to_end else tau - to_end
    return r, phi


def area(segments: list[Segment]) -> float:
    """Área de um contorno fechado formado por retas e arcos."""
    signed = 0.0
    for seg in segments:
        signed += _cross(seg.p0, seg.p1) / 2
        if isinstance(seg, Arc):
            r, phi = _arc_central_angle(seg)
            lens = r * r / 2 * (phi - math.sin(phi))
            bulge_left = _cross(_sub(seg.p1, seg.p0), _sub(seg.pm, seg.p0)) > 0
            signed += -lens if bulge_left else lens
    return abs(signed)


def polygon(segments: list[Segment], arc_steps: int = 64) -> list[Point]:
    """Vértices de um contorno fechado, com os arcos aproximados por cordas."""
    points: list[Point] = []
    for seg in segments:
        points.append(seg.p0)
        if isinstance(seg, Arc):
            c, r = circle_through(*seg)
            a0 = math.atan2(seg.p0[1] - c[1], seg.p0[0] - c[0])
            am = math.atan2(seg.pm[1] - c[1], seg.pm[0] - c[0])
            a1 = math.atan2(seg.p1[1] - c[1], seg.p1[0] - c[0])
            tau = 2 * math.pi
            sweep = (a1 - a0) % tau
            if (am - a0) % tau > sweep:
                sweep -= tau
            for k in range(1, arc_steps):
                a = a0 + sweep * k / arc_steps
                points.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a)))
    return points


def polygon_area(points: list[Point]) -> float:
    n = len(points)
    return abs(sum(_cross(points[i], points[(i + 1) % n]) for i in range(n))) / 2


def clip_rect(points: list[Point], x0: float, x1: float, y0: float, y1: float) -> list[Point]:
    """Parte do polígono dentro do retângulo ``[x0, x1] × [y0, y1]`` (Sutherland–Hodgman;
    os limites podem ser infinitos)."""

    def clip(pts, inside, cut):
        out = []
        for i, cur in enumerate(pts):
            prev = pts[i - 1]
            if inside(cur):
                if not inside(prev):
                    out.append(cut(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(cut(prev, cur))
        return out

    def at_x(x):
        return lambda p, q: (x, p[1] + (q[1] - p[1]) * (x - p[0]) / (q[0] - p[0]))

    def at_y(y):
        return lambda p, q: (p[0] + (q[0] - p[0]) * (y - p[1]) / (q[1] - p[1]), y)

    pts = list(points)
    for inside, cut in (
        (lambda p: p[0] >= x0, at_x(x0)),
        (lambda p: p[0] <= x1, at_x(x1)),
        (lambda p: p[1] >= y0, at_y(y0)),
        (lambda p: p[1] <= y1, at_y(y1)),
    ):
        if not pts:
            return []
        pts = clip(pts, inside, cut)
    return pts if len(pts) >= 3 else []


def clip_area(points: list[Point], x0: float, x1: float, y0: float, y1: float) -> float:
    """Área da parte do polígono dentro do retângulo ``[x0, x1] × [y0, y1]``."""
    pts = clip_rect(points, x0, x1, y0, y1)
    return polygon_area(pts) if pts else 0.0


# --- Curvas infinitas e referenciais ----------------------------------------------


def _unit(v: Point) -> Point:
    n = math.hypot(v[0], v[1])
    if n < TOL:
        raise ValueError("vetor nulo")
    return (v[0] / n, v[1] / n)


@dataclass(frozen=True)
class StraightLine:
    """Reta infinita por ``point`` com direção unitária ``direction``."""

    point: Point
    direction: Point


@dataclass(frozen=True)
class Circle:
    center: Point
    radius: float


Curve = StraightLine | Circle


def line_through(p: Point, q: Point) -> StraightLine:
    return StraightLine(p, _unit(_sub(q, p)))


def intersect(a: Curve, b: Curve) -> list[Point]:
    """Pontos de interseção de duas curvas (vazio se paralelas ou disjuntas)."""
    if isinstance(a, Circle) and isinstance(b, StraightLine):
        a, b = b, a
    if isinstance(a, StraightLine) and isinstance(b, StraightLine):
        den = _cross(a.direction, b.direction)
        if abs(den) < 1e-12:
            return []
        t = _cross(_sub(b.point, a.point), b.direction) / den
        return [(a.point[0] + t * a.direction[0], a.point[1] + t * a.direction[1])]
    if isinstance(a, StraightLine):
        d = a.direction
        w = _sub(b.center, a.point)
        t = w[0] * d[0] + w[1] * d[1]
        foot = (a.point[0] + t * d[0], a.point[1] + t * d[1])
        h = _dist(foot, b.center)
        if h > b.radius + 1e-9:
            return []
        half = math.sqrt(max(0.0, b.radius * b.radius - h * h))
        if half < 1e-12:
            return [foot]
        return [(foot[0] - half * d[0], foot[1] - half * d[1]),
                (foot[0] + half * d[0], foot[1] + half * d[1])]
    c0, r0, c1, r1 = a.center, a.radius, b.center, b.radius
    d = _dist(c0, c1)
    if d < 1e-12 or d > r0 + r1 + 1e-9 or d < abs(r0 - r1) - 1e-9:
        return []
    x = (d * d + r0 * r0 - r1 * r1) / (2 * d)
    h = math.sqrt(max(0.0, r0 * r0 - x * x))
    u = ((c1[0] - c0[0]) / d, (c1[1] - c0[1]) / d)
    base = (c0[0] + x * u[0], c0[1] + x * u[1])
    if h < 1e-12:
        return [base]
    return [(base[0] - h * u[1], base[1] + h * u[0]), (base[0] + h * u[1], base[1] - h * u[0])]


def nearest(points: list[Point], ref: Point) -> Point | None:
    return min(points, key=lambda p: _dist(p, ref)) if points else None


@dataclass(frozen=True)
class Frame:
    """Referencial local: origem e ângulo do eixo x em relação ao pavimento."""

    origin: Point
    angle: float

    def vector_to_global(self, v: Point) -> Point:
        c, s = math.cos(self.angle), math.sin(self.angle)
        return (c * v[0] - s * v[1], s * v[0] + c * v[1])

    def vector_to_local(self, v: Point) -> Point:
        c, s = math.cos(self.angle), math.sin(self.angle)
        return (c * v[0] + s * v[1], -s * v[0] + c * v[1])

    def to_global(self, p: Point) -> Point:
        v = self.vector_to_global(p)
        return (self.origin[0] + v[0], self.origin[1] + v[1])

    def to_local(self, p: Point) -> Point:
        return self.vector_to_local(_sub(p, self.origin))

    def curve_to_global(self, c: Curve) -> Curve:
        if isinstance(c, StraightLine):
            return StraightLine(self.to_global(c.point), self.vector_to_global(c.direction))
        return Circle(self.to_global(c.center), c.radius)

    def curve_to_local(self, c: Curve) -> Curve:
        if isinstance(c, StraightLine):
            return StraightLine(self.to_local(c.point), self.vector_to_local(c.direction))
        return Circle(self.to_local(c.center), c.radius)


# --- Caminhos ---------------------------------------------------------------


@dataclass(frozen=True)
class LinePath:
    start: Point
    end: Point

    kind = "line"

    def __post_init__(self):
        if _dist(self.start, self.end) <= MIN_LENGTH:
            raise ValueError(f"comprimento deve ser maior que {MIN_LENGTH} m")

    @property
    def length(self) -> float:
        return _dist(self.start, self.end)

    @property
    def start_angle(self) -> float:
        """Ângulo (rad) da tangente inicial em relação ao eixo x do pavimento."""
        return math.atan2(self.end[1] - self.start[1], self.end[0] - self.start[0])

    def centerline_length(self, y: float) -> float:
        return self.length

    def local_end(self) -> Point:
        return (self.length, 0.0)

    # Parametrização local: t = abscissa (0 a ``t_end``); y = afastamento à esquerda.

    @property
    def t_end(self) -> float:
        return self.length

    def point(self, y: float, t: float) -> Point:
        return (t, y)

    def param(self, p: Point) -> float:
        return p[0]

    def tangent(self, t: float) -> Point:
        return (1.0, 0.0)

    def offset(self, p: Point) -> float:
        return p[1]

    def face(self, y: float) -> Curve:
        return StraightLine((0.0, y), (1.0, 0.0))

    def arc_length(self, t: float) -> float:
        return t

    def local_profile(self, ymin: float, ymax: float) -> list[Segment]:
        """Contorno da faixa ``ymin <= y <= ymax`` ao longo do caminho, anti-horário."""
        return band_profile(self, ymin, ymax)

    def to_dict(self) -> dict:
        return {"kind": "line", "start": list(self.start), "end": list(self.end)}


@dataclass(frozen=True)
class ArcPath:
    """Arco de circunferência de ``start`` a ``end``.

    ``ccw``: sentido anti-horário. ``large``: arco maior que meia volta.
    """

    start: Point
    end: Point
    radius: float
    ccw: bool = True
    large: bool = False

    kind = "arc"

    def __post_init__(self):
        chord = _dist(self.start, self.end)
        if chord <= MIN_LENGTH:
            raise ValueError(f"comprimento deve ser maior que {MIN_LENGTH} m")
        if chord > 2 * self.radius + 1e-9:
            raise ValueError("raio menor que metade da corda")

    @property
    def sweep(self) -> float:
        chord = _dist(self.start, self.end)
        small = 2 * math.asin(min(1.0, chord / (2 * self.radius)))
        return 2 * math.pi - small if self.large else small

    @property
    def start_angle(self) -> float:
        chord_angle = math.atan2(self.end[1] - self.start[1], self.end[0] - self.start[0])
        half = self.sweep / 2
        return chord_angle - half if self.ccw else chord_angle + half

    @property
    def length(self) -> float:
        return self.radius * self.sweep

    def _radius_at(self, y: float) -> float:
        """Raio da curva paralela afastada ``y`` (positivo = esquerda)."""
        return self.radius - y if self.ccw else self.radius + y

    def _local_point(self, y: float, t: float) -> Point:
        r = self._radius_at(y)
        if self.ccw:
            return (r * math.sin(t), self.radius - r * math.cos(t))
        return (r * math.sin(t), -self.radius + r * math.cos(t))

    def local_center(self) -> Point:
        return (0.0, self.radius if self.ccw else -self.radius)

    def centerline_length(self, y: float) -> float:
        return self._radius_at(y) * self.sweep

    def local_end(self) -> Point:
        return self._local_point(0.0, self.sweep)

    # Parametrização local: t = ângulo percorrido desde o início (0 a ``t_end``).

    @property
    def t_end(self) -> float:
        return self.sweep

    def point(self, y: float, t: float) -> Point:
        return self._local_point(y, t)

    def param(self, p: Point) -> float:
        """Ângulo de ``p`` em (−π, π]; quem usa ajusta a volta (ver ``_unwrap``)."""
        if self.ccw:
            return math.atan2(p[0], self.radius - p[1])
        return math.atan2(p[0], p[1] + self.radius)

    def tangent(self, t: float) -> Point:
        return (math.cos(t), math.sin(t)) if self.ccw else (math.cos(t), -math.sin(t))

    def offset(self, p: Point) -> float:
        r = _dist(p, self.local_center())
        return self.radius - r if self.ccw else r - self.radius

    def face(self, y: float) -> Curve:
        return Circle(self.local_center(), self._radius_at(y))

    def arc_length(self, t: float) -> float:
        return self.radius * t

    def local_profile(self, ymin: float, ymax: float) -> list[Segment]:
        return band_profile(self, ymin, ymax)

    def to_dict(self) -> dict:
        return {
            "kind": "arc",
            "start": list(self.start),
            "end": list(self.end),
            "radius": self.radius,
            "ccw": self.ccw,
            "large": self.large,
        }


Path = LinePath | ArcPath


def split(path: Path, at: Point) -> tuple[Path, Path, float]:
    """Divide o caminho no ponto mais próximo de ``at``.

    Devolve as duas partes e a posição do ponto ao longo do caminho (comprimento desde o
    início). Rejeita ponto a menos de ``MIN_LENGTH`` das extremidades.
    """
    f = frame(path)
    t = path.param(f.to_local(at))
    if isinstance(path, ArcPath):
        t %= 2 * math.pi
    if not (0 < path.arc_length(t) < path.length):
        raise ValueError("o ponto de divisão fica fora da parede")
    p = f.to_global(path.point(0.0, t))
    if isinstance(path, LinePath):
        return LinePath(path.start, p), LinePath(p, path.end), t
    rest = path.sweep - t
    return (ArcPath(path.start, p, path.radius, path.ccw, t > math.pi),
            ArcPath(p, path.end, path.radius, path.ccw, rest > math.pi),
            path.arc_length(t))


def frame(path: Path) -> Frame:
    """Referencial local do caminho (origem no início, x na tangente inicial)."""
    return Frame(path.start, path.start_angle)


def unwrap(path: Path, t: float, ref: float) -> float:
    """Para arcos, escolhe a volta de ``t`` mais próxima de ``ref``."""
    if isinstance(path, LinePath):
        return t
    return ref + (t - ref + math.pi) % (2 * math.pi) - math.pi


def _cut_param(path: Path, y: float, cut: Curve, ref: float) -> float:
    """Parâmetro, na face ``y``, do ponto de corte mais próximo da extremidade ``ref``."""
    p = nearest(intersect(path.face(y), cut), path.point(y, ref))
    if p is None:
        raise ValueError("a face da parede não alcança o corte da junção")
    return unwrap(path, path.param(p), ref)


def _piece(path: Path, y: float, t0: float, t1: float) -> Segment:
    p0, p1 = path.point(y, t0), path.point(y, t1)
    if isinstance(path, LinePath):
        return Line(p0, p1)
    return Arc(p0, path.point(y, (t0 + t1) / 2), p1)


def _cap(p: Point, q: Point, cut: Curve | None) -> Segment:
    """Tampa de ``p`` a ``q`` sobre a curva de corte (reta ou arco)."""
    if not isinstance(cut, Circle):
        return Line(p, q)
    c, r = cut.center, cut.radius
    m = _unit(_sub(((p[0] + q[0]) / 2, (p[1] + q[1]) / 2), c))
    return Arc(p, (c[0] + r * m[0], c[1] + r * m[1]), q)


def band_profile(path: Path, ymin: float, ymax: float, start_cut: Curve | None = None,
                 end_cut: Curve | None = None) -> list[Segment]:
    """Contorno anti-horário da faixa ``ymin <= y <= ymax`` (coordenadas locais).

    Sem corte, as extremidades são retas perpendiculares ao caminho. Com corte (curva em
    coordenadas locais), cada face vai até a interseção com ele e a tampa segue o corte.
    """
    if isinstance(path, ArcPath):
        for y in (ymin, ymax):
            if path._radius_at(y) <= MIN_LENGTH:
                raise ValueError("raio pequeno demais para a espessura da parede")
    ranges = []
    for y in (ymin, ymax):
        t0 = 0.0 if start_cut is None else _cut_param(path, y, start_cut, 0.0)
        t1 = path.t_end if end_cut is None else _cut_param(path, y, end_cut, path.t_end)
        if path.arc_length(t1 - t0) <= MIN_LENGTH or (
            isinstance(path, ArcPath) and t1 - t0 >= 2 * math.pi
        ):
            raise ValueError("os cortes das junções se cruzam")
        ranges.append((t0, t1))
    (a0, a1), (b0, b1) = ranges
    return [
        _piece(path, ymin, a0, a1),
        _cap(path.point(ymin, a1), path.point(ymax, b1), end_cut),
        _piece(path, ymax, b1, b0),
        _cap(path.point(ymax, b0), path.point(ymin, a0), start_cut),
    ]


def path_from_dict(d: dict) -> Path:
    start, end = tuple(map(float, d["start"])), tuple(map(float, d["end"]))
    if d["kind"] == "line":
        return LinePath(start, end)
    if d["kind"] == "arc":
        return ArcPath(start, end, float(d["radius"]), bool(d["ccw"]), bool(d["large"]))
    raise ValueError(f"forma de caminho desconhecida: {d['kind']!r}")


def arc_through(start: Point, through: Point, end: Point) -> ArcPath:
    """Arco pelos três pontos (modo de criação por 3 pontos)."""
    center, radius = circle_through(start, through, end)
    chord = _sub(end, start)
    side_through = _cross(chord, _sub(through, start))
    side_center = _cross(chord, _sub(center, start))
    ccw = side_through < 0
    large = abs(side_center) > TOL and (side_center > 0) == (side_through > 0)
    return ArcPath(start, end, radius, ccw, large)


# --- transformações e edição de caminhos -----------------------------------------------


def path_midpoint(path: Path) -> Point:
    """Ponto do meio do caminho (coordenadas do pavimento)."""
    return frame(path).to_global(path.point(0.0, path.t_end / 2))


def with_ends(path: Path, start: Point, end: Point) -> Path:
    """O caminho com extremidades novas; o arco continua passando pelo seu ponto médio."""
    if isinstance(path, LinePath):
        return LinePath(tuple(start), tuple(end))
    return arc_through(tuple(start), path_midpoint(path), tuple(end))


def mapped(path: Path, fn) -> Path:
    """Caminho levado por ``fn``, um movimento rígido (translação ou rotação) que
    preserva o sentido de giro dos arcos."""
    start, end = fn(path.start), fn(path.end)
    if isinstance(path, LinePath):
        return LinePath(start, end)
    return ArcPath(start, end, path.radius, path.ccw, path.large)


def stretched(path: Path, fn) -> Path:
    """Caminho com as pontas levadas por ``fn`` (que pode mover só uma delas): o arco
    mantém o ângulo central e o sentido (spec/ui 38 §3)."""
    start, end = fn(path.start), fn(path.end)
    if isinstance(path, LinePath):
        return LinePath(start, end)
    chord = math.dist(path.start, path.end)
    scale = math.dist(start, end) / chord if chord > 1e-12 else 1.0
    return ArcPath(start, end, path.radius * scale, path.ccw, path.large)


def translation(v: Point):
    return lambda p: (p[0] + v[0], p[1] + v[1])


def rotation(center: Point, angle: float):
    """Rotação de ``angle`` radianos (anti-horário) em torno de ``center``."""
    c, s = math.cos(angle), math.sin(angle)

    def fn(p: Point) -> Point:
        dx, dy = p[0] - center[0], p[1] - center[1]
        return (center[0] + c * dx - s * dy, center[1] + s * dx + c * dy)

    return fn


def reflection(a: Point, b: Point):
    """Espelho pela reta que passa por ``a`` e ``b``."""
    d = _unit(_sub(b, a))

    def fn(p: Point) -> Point:
        v = _sub(p, a)
        t = v[0] * d[0] + v[1] * d[1]
        foot = (a[0] + t * d[0], a[1] + t * d[1])
        return (2 * foot[0] - p[0], 2 * foot[1] - p[1])

    return fn


def convex_hull(points: list[Point]) -> list[Point]:
    """Fecho convexo, anti-horário (cadeia monótona)."""
    pts = sorted({(round(x, 9), round(y, 9)) for x, y in points})
    if len(pts) < 3:
        return pts

    def half(seq):
        out: list[Point] = []
        for q in seq:
            while len(out) >= 2 and _cross(_sub(out[-1], out[-2]), _sub(q, out[-2])) <= 0:
                out.pop()
            out.append(q)
        return out

    lower, upper = half(pts), half(list(reversed(pts)))
    return lower[:-1] + upper[:-1]
