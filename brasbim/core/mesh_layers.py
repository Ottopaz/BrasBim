# SPDX-License-Identifier: LGPL-3.0-or-later
"""Divisão de uma malha triangulada pelas regiões das camadas (``spec/ui/06-planta-por-camadas.md``
§5): cor por camada no 3D, sem mudar o corpo no IFC.

- Faces verticais (laterais, pontas): a aresta em planta, recuada 1 mm para dentro do
  sólido, é recortada pelas regiões; o triângulo é dividido por planos verticais nos
  limites dos trechos.
- Demais faces (topo, base, topo inclinado): interseção em planta do triângulo com cada
  região, triangulada de novo e levantada para o plano do triângulo.

O que não cai em nenhuma região fica com a chave ``None`` (cor do elemento). Coordenadas
no sistema das regiões (o do pavimento).
"""

from __future__ import annotations

import numpy as np

from brasbim.core import clip
from brasbim.core.clip import Rings

INSET = 0.001  # m: recuo das faces verticais para dentro do sólido
_VERTICAL = 1e-6  # |nz| abaixo disto: face vertical
_TINY = 1e-12  # m²
_REST = 1e-6  # m²: sobra de arredondamento do recorte, descartada


def _ear_clip(ring: list) -> list[tuple]:
    """Triângulos de um polígono simples (anel sem furos), por recorte de orelhas."""
    pts = [tuple(p) for p in ring]
    if clip.signed_area(pts) < 0:
        pts.reverse()
    out = []
    idx = list(range(len(pts)))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    guard = 0
    while len(idx) > 3 and guard < 10 * len(pts) ** 2:
        guard += 1
        n = len(idx)
        for k in range(n):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % n]
            a, b, c = pts[i0], pts[i1], pts[i2]
            if cross(a, b, c) <= 1e-18:
                continue
            if any(cross(a, b, pts[j]) >= 0 and cross(b, c, pts[j]) >= 0
                   and cross(c, a, pts[j]) >= 0 for j in idx if j not in (i0, i1, i2)):
                continue
            out.append((a, b, c))
            idx.pop(k)
            break
        else:  # sem orelha (polígono degenerado): leque
            break
    o = pts[idx[0]]
    out += [(o, pts[idx[i]], pts[idx[i + 1]]) for i in range(1, len(idx) - 1)]
    return out


def _lift(tri3: np.ndarray, flat: list[tuple]) -> list[np.ndarray]:
    """Triângulos em planta → no plano do triângulo ``tri3``."""
    p0, p1, p2 = tri3
    n = np.cross(p1 - p0, p2 - p0)
    out = []
    for t in flat:
        pts = [(x, y, p0[2] - (n[0] * (x - p0[0]) + n[1] * (y - p0[1])) / n[2]) for x, y in t]
        out.append(np.array(pts))
    return out


def _flat(tri3: np.ndarray, regions: list[tuple[object, Rings]]) -> dict:
    ring = [tuple(p[:2]) for p in tri3]
    out: dict = {}
    covered: Rings = []
    for key, rings in regions:
        part = clip.intersection([ring], rings)
        if clip.area(part) <= _TINY:
            continue
        covered += part
        out.setdefault(key, []).extend(_triangulate(tri3, part))
    rest = clip.difference([ring], clip.union(covered)) if covered else [ring]
    if clip.area(rest) > _REST:
        out.setdefault(None, []).extend(_triangulate(tri3, rest))
    return out


def _triangulate(tri3: np.ndarray, rings: Rings, depth: int = 0) -> list[np.ndarray]:
    """Triângulos da região (em planta) levantados para o plano de ``tri3``. Região com
    furo: cortada por uma reta vertical que passa pelo furo, e cada metade de novo."""
    signs = [clip.signed_area(r) for r in rings]
    outer = max(signs, key=abs, default=0.0)
    holes = [r for r, a in zip(rings, signs, strict=True) if a * outer < 0]
    if not holes or depth > 8:
        return [t for r, a in zip(rings, signs, strict=True) if a * outer > 0
                for t in _lift(tri3, _ear_clip(r))]
    xs = [p[0] for p in holes[0]]
    cut = (min(xs) + max(xs)) / 2
    pts = [p for r in rings for p in r]
    x0, x1 = min(p[0] for p in pts) - 1, max(p[0] for p in pts) + 1
    y0, y1 = min(p[1] for p in pts) - 1, max(p[1] for p in pts) + 1
    out = []
    for a, b in ((x0, cut), (cut, x1)):
        half = clip.intersection(rings, [[(a, y0), (b, y0), (b, y1), (a, y1)]])
        out += _triangulate(tri3, half, depth + 1)
    return out


def _clip_slab(poly: list, s0: float, s1: float) -> list:
    """Polígono convexo em (s, z) recortado em ``s0 ≤ s ≤ s1``."""
    for bound, sign in ((s0, 1), (s1, -1)):
        out = []
        for i in range(len(poly)):
            a, b = poly[i - 1], poly[i]
            ina, inb = sign * (a[0] - bound) >= 0, sign * (b[0] - bound) >= 0
            if ina != inb:
                t = (bound - a[0]) / (b[0] - a[0])
                out.append((bound, a[1] + t * (b[1] - a[1])))
            if inb:
                out.append(b)
        poly = out
        if len(poly) < 3:
            return []
    return poly


def _vertical(tri3: np.ndarray, normal: np.ndarray, regions: list[tuple[object, Rings]]) -> dict:
    nxy = normal[:2] / np.linalg.norm(normal[:2])
    u = np.array([-nxy[1], nxy[0]])
    base = tri3[0, :2]
    ss = [(float(np.dot(p[:2] - base, u)), float(p[2])) for p in tri3]
    lo, hi = min(s for s, _ in ss), max(s for s, _ in ss)
    if hi - lo < 1e-9:
        return {}
    intervals: list[tuple[float, float, object]] = []
    for side in (-1, 1):  # para dentro; se nada cobre, a normal estava invertida
        shift = base + side * INSET * nxy
        line = [tuple(shift + u * lo), tuple(shift + u * hi)]
        for key, rings in regions:
            for piece in clip.clip_lines([line], rings):
                s = sorted(float(np.dot(np.asarray(q) - shift, u)) for q in piece)
                intervals.append((max(s[0], lo), min(s[-1], hi), key))
        if intervals:
            break
    intervals.sort(key=lambda iv: iv[0])
    pieces, x = [], lo
    for a, b, key in intervals:
        if a > x + 1e-9:
            pieces.append((x, a, None))
        a = max(a, x)
        if b > a + 1e-9:
            pieces.append((a, b, key))
            x = b
    if x < hi - 1e-9:
        pieces.append((x, hi, None))
    out: dict = {}
    for a, b, key in pieces:
        poly = _clip_slab(ss, a, b)
        tris = [np.array([[*(base + u * p[0]), p[1]] for p in (poly[0], poly[i], poly[i + 1])])
                for i in range(1, len(poly) - 1)]
        if tris:
            out.setdefault(key, []).extend(tris)
    return out


def split(triangles: np.ndarray, regions: list[tuple[object, Rings]]) -> dict:
    """``{chave da região ou None: triângulos (n, 3, 3)}``."""
    out: dict = {}
    for tri in np.asarray(triangles, dtype=np.float64).reshape(-1, 3, 3):
        normal = np.cross(tri[1] - tri[0], tri[2] - tri[0])
        length = np.linalg.norm(normal)
        if length < 1e-15:
            continue
        if abs(normal[2]) / length < _VERTICAL:
            found = _vertical(tri, normal, regions)
        else:
            found = _flat(tri, regions)
        for key, tris in found.items():
            out.setdefault(key, []).extend(tris)
    result = {}
    for key, tris in out.items():
        t = np.array(tris).reshape(-1, 3, 3)
        keep = np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1) > 1e-12
        if keep.any():
            result[key] = t[keep]
    return result


def area(triangles: np.ndarray) -> float:
    t = np.asarray(triangles, dtype=np.float64).reshape(-1, 3, 3)
    return float(np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1).sum() / 2)
