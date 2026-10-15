# SPDX-License-Identifier: LGPL-3.0-or-later
"""Topo inclinado, empena e livre (``spec/ui/08-parede-no-3d-topo-e-inclinacao.md`` §4).

O topo é um perfil: lista de pontos ``[posição, altura]``, com a posição ao longo da linha
de referência (de 0 ao comprimento) e a altura medida da base da parede. Topo plano: lista
vazia. Fora de ``[0, comprimento]`` (pontas prolongadas pelas junções) o topo segue a reta
do primeiro ou do último trecho.
"""

from __future__ import annotations

import itertools
import math

from brasbim.core import geom2d

SHAPES = ("flat", "slope", "gable", "free")
PSET_SHAPES = {"flat": "PLANO", "slope": "INCLINADO", "gable": "EMPENA", "free": "LIVRE"}
TOL = 1e-6

Profile = list[list[float]]


# --- formas ------------------------------------------------------------------------


def slope(length: float, h_start: float, h_end: float) -> Profile:
    return [[0.0, float(h_start)], [float(length), float(h_end)]]


def slope_by_angle(length: float, h_start: float, degrees: float) -> Profile:
    return slope(length, h_start, h_start + length * math.tan(math.radians(degrees)))


def gable(length: float, h_ends: float, h_ridge: float, ridge: float | None = None) -> Profile:
    x = length / 2 if ridge is None else float(ridge)
    return [[0.0, float(h_ends)], [x, float(h_ridge)], [float(length), float(h_ends)]]


def gable_by_angle(length: float, h_ends: float, degrees: float,
                   ridge: float | None = None) -> Profile:
    x = length / 2 if ridge is None else float(ridge)
    rise = min(x, length - x) * math.tan(math.radians(degrees))
    return gable(length, h_ends, h_ends + rise, x)


def angle(profile: Profile, segment: int = 0) -> float:
    """Ângulo (graus, a partir da horizontal) do trecho ``segment``."""
    (x0, h0), (x1, h1) = profile[segment], profile[segment + 1]
    return math.degrees(math.atan2(h1 - h0, x1 - x0))


def validate(shape: str, profile: Profile, length: float) -> None:
    if shape not in SHAPES:
        raise ValueError(f"forma do topo inválida: {shape!r}")
    if shape == "flat":
        if profile:
            raise ValueError("topo plano não tem perfil")
        return
    expected = {"slope": 2, "gable": 3}.get(shape)
    if len(profile) < 2 or (expected and len(profile) != expected):
        raise ValueError(f"perfil do topo com {len(profile)} pontos não serve para {shape}")
    xs = [p[0] for p in profile]
    if abs(xs[0]) > TOL or abs(xs[-1] - length) > 1e-4:
        raise ValueError("o perfil do topo deve ir do início ao fim da parede")
    if any(b - a < geom2d.MIN_LENGTH for a, b in itertools.pairwise(xs)):
        raise ValueError("as posições do perfil do topo devem ser crescentes")
    if any(h <= 0 for _, h in profile):
        raise ValueError("as alturas do topo devem ser maiores que zero")


# --- cálculo -----------------------------------------------------------------------


def scaled(profile: Profile, old_length: float, new_length: float) -> Profile:
    """Pontos reposicionados proporcionalmente; alturas mantidas (§4.1)."""
    if not profile or old_length <= 0:
        return profile
    k = new_length / old_length
    out = [[x * k, h] for x, h in profile]
    out[-1][0] = float(new_length)
    return out


def reversed_profile(profile: Profile, length: float) -> Profile:
    """Perfil visto do outro sentido (parede espelhada, caminho invertido)."""
    if not profile:
        return profile
    out = [[length - x, h] for x, h in reversed(profile)]
    out[0][0], out[-1][0] = 0.0, float(length)
    return out


def at(profile: Profile, x: float) -> float:
    """Altura do topo na posição ``x`` (retas do primeiro/último trecho fora dele)."""
    k = 0
    while k < len(profile) - 2 and x > profile[k + 1][0]:
        k += 1
    (x0, h0), (x1, h1) = profile[k], profile[k + 1]
    return h0 + (h1 - h0) * (x - x0) / (x1 - x0)


def lowest(profile: Profile, x0: float, x1: float) -> float:
    """Menor altura do topo no intervalo ``[x0, x1]``."""
    inner = [h for x, h in profile if x0 < x < x1]
    return min([at(profile, x0), at(profile, x1), *inner])


def highest(profile: Profile) -> float:
    return max(h for _, h in profile)


def _breaks(profile: Profile) -> list[float]:
    """Limites dos trechos: o primeiro e o último vão ao infinito."""
    return [-math.inf, *(x for x, _ in profile[1:-1]), math.inf]


def side_area(profile: Profile, x0: float, x1: float) -> float:
    """Área sob o topo entre ``x0`` e ``x1`` (integral da altura)."""
    xs = sorted({x0, x1, *(x for x, _ in profile if x0 < x < x1)})
    return sum((b - a) * (at(profile, a) + at(profile, b)) / 2
               for a, b in itertools.pairwise(xs))


def _moments(points: list) -> tuple[float, float]:
    """(área, momento de primeira ordem em x) de um polígono simples."""
    a = sx = 0.0
    n = len(points)
    for i in range(n):
        (xa, ya), (xb, yb) = points[i], points[(i + 1) % n]
        c = xa * yb - xb * ya
        a += c
        sx += (xa + xb) * c
    if abs(a) < 1e-15:
        return 0.0, 0.0
    area = abs(a) / 2
    return area, area * (sx / 3) / a  # área × x do centroide


def volume(points: list, profile: Profile, y0: float = -math.inf,
           y1: float = math.inf) -> float:
    """Volume sob o topo do prisma de planta ``points`` (polígono), recortado em y."""
    total = 0.0
    breaks = _breaks(profile)
    for k, (a, b) in enumerate(itertools.pairwise(breaks)):
        piece = geom2d.clip_rect(points, a, b, y0, y1)
        if not piece:
            continue
        area, mx = _moments(piece)
        (xa, ha), (xb, hb) = profile[k], profile[k + 1]
        slope_k = (hb - ha) / (xb - xa)
        # ∫∫ (ha + s (x − xa)) dA = ha A + s (Mx − xa A)
        total += ha * area + slope_k * (mx - xa * area)
    return total
