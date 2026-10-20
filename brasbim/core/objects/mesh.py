# SPDX-License-Identifier: LGPL-3.0-or-later
"""Malha aproximada das peças, para miniaturas e a prévia do editor
(``spec/elementos/objeto-parametrico.md`` §4.2 e §5.3), sem IFC e sem Qt.

O corpo gravado no IFC continua exato (``shapes``); aqui cada peça vira triângulos no
sistema local do objeto, com o material, para um desenho rápido.
"""

from __future__ import annotations

import logging
import math

from brasbim.core.objects.definition import Solid, footprint, z_range

_STEPS = 20
log = logging.getLogger(__name__)

Point3 = tuple[float, float, float]


def _prism(ring: list[tuple[float, float]], z0: float, z1: float, to3) -> list:
    """Triângulos de um prisma de base ``ring`` (anti-horário) entre ``z0`` e ``z1``."""
    out = []
    n = len(ring)
    bottom = [to3(x, y, z0) for x, y in ring]
    top = [to3(x, y, z1) for x, y in ring]
    for i in range(1, n - 1):  # leque (a base pode ser côncava: aproximação)
        out.append((top[0], top[i], top[i + 1]))
        out.append((bottom[0], bottom[i + 1], bottom[i]))
    for i in range(n):
        j = (i + 1) % n
        out.append((bottom[i], bottom[j], top[j]))
        out.append((bottom[i], top[j], top[i]))
    return out


def _ccw(ring):
    area = sum(ring[i][0] * ring[(i + 1) % len(ring)][1]
               - ring[(i + 1) % len(ring)][0] * ring[i][1] for i in range(len(ring)))
    return ring if area > 0 else ring[::-1]


def _circle(cx, cy, r, steps=_STEPS):
    return [(cx + r * math.cos(2 * math.pi * k / steps), cy + r * math.sin(2 * math.pi * k / steps))
            for k in range(steps)]


def triangles(s: Solid) -> list[tuple[Point3, Point3, Point3]]:
    def flat(x, y, z):
        return (x, y, z)

    if s.kind == "box":
        z0, z1 = z_range(s)
        return _prism(_ccw(footprint(s)), z0, z1, flat)
    if s.kind == "cylinder":
        x, y, z = s.origin
        r, h = s.dims["radius"], s.dims["height"]
        axis = s.dims.get("axis", "z")
        ring = _circle(0.0, 0.0, r)
        if axis == "z":
            return _prism(ring, z, z + h, lambda a, b, c: (x + a, y + b, c))
        if axis == "x":
            return _prism(ring, 0.0, h, lambda a, b, c: (x + c, y + a, z + b))
        return _prism(ring, 0.0, h, lambda a, b, c: (x + a, y + c, z + b))
    if s.kind == "extrusion":
        dx, dy, dz = s.origin
        t0, t = s.dims["offset"], s.dims["thickness"]
        plane = s.dims.get("plane", "xy")
        ring = _ccw([tuple(p) for p in s.points])
        if plane == "xy":
            return _prism(ring, t0, t0 + t, lambda a, b, c: (dx + a, dy + b, dz + c))
        if plane == "xz":
            return _prism(ring, t0, t0 + t, lambda a, b, c: (dx + a, dy + c, dz + b))
        return _prism(ring, t0, t0 + t, lambda a, b, c: (dx + c, dy + a, dz + b))
    # revolução: anéis do perfil girados
    x, y, z = s.origin
    angle = math.radians(min(s.dims["angle"], 360.0))
    steps = max(4, int(_STEPS * angle / (2 * math.pi)))
    profile = list(s.points)
    out = []
    for k in range(steps):
        a0, a1 = angle * k / steps, angle * (k + 1) / steps
        for i in range(len(profile)):
            (r0, h0), (r1, h1) = profile[i], profile[(i + 1) % len(profile)]
            p = [(x + r0 * math.cos(a0), y + r0 * math.sin(a0), z + h0),
                 (x + r1 * math.cos(a0), y + r1 * math.sin(a0), z + h1),
                 (x + r1 * math.cos(a1), y + r1 * math.sin(a1), z + h1),
                 (x + r0 * math.cos(a1), y + r0 * math.sin(a1), z + h0)]
            out.append((p[0], p[1], p[2]))
            out.append((p[0], p[2], p[3]))
    return out


def _outward(tris: list) -> list:
    """Triângulos virados para fora (pelo centro da peça): a prévia descarta os de costas."""
    if not tris:
        return tris
    pts = [p for t in tris for p in t]
    c = tuple(sum(p[i] for p in pts) / len(pts) for i in range(3))
    out = []
    for t in tris:
        (x0, y0, z0), (x1, y1, z1), (x2, y2, z2) = t
        n = ((y1 - y0) * (z2 - z0) - (z1 - z0) * (y2 - y0),
             (z1 - z0) * (x2 - x0) - (x1 - x0) * (z2 - z0),
             (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0))
        m = ((x0 + x1 + x2) / 3 - c[0], (y0 + y1 + y2) / 3 - c[1], (z0 + z1 + z2) / 3 - c[2])
        out.append(t if n[0] * m[0] + n[1] * m[1] + n[2] * m[2] >= 0 else t[::-1])
    return out


def mesh(solids: list[Solid], mirror: bool = False) -> list[tuple[tuple, str | None, int]]:
    """[(triângulo, material, peça)] de todas as peças (sem o vão)."""
    out = []
    for k, s in enumerate(solids):
        if s.void:
            continue
        for tri in _outward(triangles(s)):
            if mirror:
                tri = tuple((-p[0], p[1], p[2]) for p in tri[::-1])
            out.append((tri, s.material, k))
    return out


def _transform(tri, origin, rotation: float, mirror: bool):
    a = math.radians(rotation)
    c, s = math.cos(a), math.sin(a)
    out = []
    for x, y, z in tri:
        if mirror:
            x = -x
        out.append((origin[0] + c * x - s * y, origin[1] + s * x + c * y, origin[2] + z))
    return tuple(out[::-1]) if mirror else tuple(out)


def object_mesh(defn: dict, values: dict, resolver=None, mirror: bool = False,
                depth: int = 0) -> list[tuple[tuple, str | None, int]]:
    """Malha do objeto com os aninhados. ``resolver(nome do tipo)`` devolve o estado do
    tipo (``definition``, ``values``, ``defaults``) ou ``None``."""
    from brasbim.core.objects import definition as od

    out = mesh(od.solids(defn, values), mirror)
    if resolver is None or depth >= od.MAX_NESTING:
        return out
    group = 1000 * (depth + 1)
    for i, n in enumerate(od.nested(defn, values)):
        state = resolver(n.type_name)
        if state is None:
            continue
        try:
            inner = od.evaluate(state["definition"], state["values"],
                                {**state["defaults"], **n.values})
            tris = object_mesh(state["definition"], inner, resolver, n.mirror, depth + 1)
        except Exception as e:  # noqa: BLE001 - aninhado que não se calcula fica de fora
            log.debug("prévia sem o aninhado %s: %s", n.type_name, e)
            continue
        m = -1.0 if mirror else 1.0
        origin = (m * n.origin[0], n.origin[1], n.origin[2])
        rotation = m * n.rotation
        for tri, material, part in tris:
            out.append((_transform(tri, origin, rotation, mirror), material,
                        group * (i + 1) + part))
    return out
