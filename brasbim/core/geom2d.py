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

    def local_profile(self, ymin: float, ymax: float) -> list[Segment]:
        """Contorno da faixa ``ymin <= y <= ymax`` ao longo do caminho, anti-horário."""
        n = self.length
        a, b, c, d = (0.0, ymin), (n, ymin), (n, ymax), (0.0, ymax)
        return [Line(a, b), Line(b, c), Line(c, d), Line(d, a)]

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

    def local_profile(self, ymin: float, ymax: float) -> list[Segment]:
        for y in (ymin, ymax):
            if self._radius_at(y) <= MIN_LENGTH:
                raise ValueError("raio pequeno demais para a espessura da parede")
        s = self.sweep
        a0, am, a1 = (self._local_point(ymin, t) for t in (0.0, s / 2, s))
        b0, bm, b1 = (self._local_point(ymax, t) for t in (0.0, s / 2, s))
        return [Arc(a0, am, a1), Line(a1, b1), Arc(b1, bm, b0), Line(b0, a0)]

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
