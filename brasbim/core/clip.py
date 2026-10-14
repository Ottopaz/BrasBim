# SPDX-License-Identifier: LGPL-3.0-or-later
"""Booleanos 2D sobre polígonos, com Clipper2 (``pyclipr``).

Uma região é uma lista de anéis (``Rings``), em metros. Os furos vêm com orientação
oposta à do contorno; para desenhar, preencher com a regra par-ímpar.
"""

from __future__ import annotations

import math

import numpy as np
import pyclipr

from brasbim.core.geom2d import Point

Ring = list[Point]
Rings = list[Ring]

SCALE = 1_000_000  # 1 µm: precisão de sobra para obras e folga para coordenadas grandes


def _clipper() -> pyclipr.Clipper:
    c = pyclipr.Clipper()
    c.scaleFactor = SCALE
    return c


def _rings(paths) -> Rings:
    return [[(float(x), float(y)) for x, y in p] for p in paths if len(p) >= 3]


def _valid(rings: Rings) -> list:
    return [np.asarray(r, dtype=float) for r in rings if len(r) >= 3]


def _run(op, subject: Rings, clip: Rings | None = None) -> Rings:
    subject = _valid(subject)
    if not subject:
        return []
    c = _clipper()
    c.addPaths(subject, pyclipr.Subject)
    clip = _valid(clip or [])
    if clip:
        c.addPaths(clip, pyclipr.Clip)
    elif op != pyclipr.Union:
        return [] if op == pyclipr.Intersection else [list(map(tuple, r)) for r in subject]
    return _rings(c.execute(op, pyclipr.FillRule.NonZero))


def union(*groups: Rings) -> Rings:
    return _run(pyclipr.Union, [r for g in groups for r in g])


def intersection(a: Rings, b: Rings) -> Rings:
    return _run(pyclipr.Intersection, a, b)


def difference(a: Rings, b: Rings) -> Rings:
    return _run(pyclipr.Difference, a, b)


def signed_area(ring: Ring) -> float:
    return 0.5 * sum(ring[i - 1][0] * ring[i][1] - ring[i][0] * ring[i - 1][1]
                     for i in range(len(ring)))


def area(rings: Rings) -> float:
    """Área da região (furos descontados)."""
    return abs(sum(signed_area(r) for r in rings))


def offset(rings: Rings, delta: float) -> Rings:
    rings = _valid(rings)
    if not rings:
        return []
    o = pyclipr.ClipperOffset()
    o.scaleFactor = SCALE
    o.addPaths(rings, pyclipr.JoinType.Miter, pyclipr.EndType.Polygon)
    return _rings(o.execute(delta))


def clip_lines(lines: list[list[Point]], rings: Rings) -> list[list[Point]]:
    """Trechos das polilinhas abertas que ficam dentro da região."""
    lines = [np.asarray(p, dtype=float) for p in lines if len(p) >= 2]
    rings = _valid(rings)
    if not lines or not rings:
        return []
    c = _clipper()
    for line in lines:
        c.addPath(line, pyclipr.Subject, True)
    c.addPaths(rings, pyclipr.Clip)
    _, open_paths = c.execute(pyclipr.Intersection, pyclipr.FillRule.NonZero,
                              returnOpenPaths=True)
    return [[(float(x), float(y)) for x, y in p] for p in open_paths if len(p) >= 2]


def halfplane(origin: Point, direction: Point, limit: float, reach: float = 1e4) -> Ring:
    """Semiplano ``s < limit``, com ``s`` medido de ``origin`` ao longo de ``direction``
    (unitário), como um retângulo grande."""
    d = direction
    n = (-d[1], d[0])

    def at(s, t):
        return (origin[0] + d[0] * s + n[0] * t, origin[1] + d[1] * s + n[1] * t)

    return [at(-reach, -reach), at(limit, -reach), at(limit, reach), at(-reach, reach)]


def project_min(rings: Rings, origin: Point, direction: Point) -> float:
    """Menor abscissa dos vértices da região ao longo de ``direction`` (∞ se vazia)."""
    values = [(p[0] - origin[0]) * direction[0] + (p[1] - origin[1]) * direction[1]
              for r in rings for p in r]
    return min(values) if values else math.inf
