# SPDX-License-Identifier: LGPL-3.0-or-later
"""Formas que viram a malha de uma forma livre (``spec/elementos/forma-livre.md`` §4.1).

Cada forma é um dicionário (a "receita" guardada no elemento)::

    {"kind": "box", "name": "Assento", "material": "Tecido",
     "position": [x, y, z], "rotation": [rx, ry, rz],   # graus, aplicados em x, y, z
     ...campos da forma}

| kind | campos (metros; no sistema da própria forma, antes de girar e pôr no lugar) |
|---|---|
| box | size [largura x, profundidade y, altura z], radius (canto; 0 = viva); centrada em x e y, base em z = 0 |
| ellipsoid | radii [rx, ry, rz]; centrado na origem |
| cone | radius (base), top_radius (padrão = radius; 0 = ponta), height; base em z = 0 |
| tube | path [[x, y, z], ...], radius **ou** section [largura, altura], smooth (sim/não) |
| sections | sections [{"z", "center" [x, y], "radii" [rx, ry] | "points" [[x, y], ...], "twist"}], smooth |
| revolution | profile [[raio, z], ...] de baixo para cima (a superfície de fora), smooth, angle (padrão 360) |
| extrusion | profile [[x, y], ...] fechado, height, smooth |

Sem Qt e sem IFC. ``build`` devolve as partes (uma por material) com vértices e faces
(triângulos, anti-horário visto de fora) no sistema local da forma livre: origem no ponto
de inserção, x para a direita, y para trás, z para cima.
"""

from __future__ import annotations

import itertools
import math

import numpy as np

from brasbim.core.document import OpError

KINDS = ("box", "ellipsoid", "cone", "tube", "sections", "revolution", "extrusion")
MAX_SHAPES = 80
MAX_TRIANGLES = 20000  # por forma livre (§3)
PREFERRED = 9000  # o que uma peça feita de formas procura não passar
DETAILS = (28, 20, 12, 8)  # divisões de uma volta (múltiplos de 4); cai até caber
_EPS = 1e-9


class ShapeError(OpError):
    """Forma que não dá um sólido, com o lugar ("forma 3 'Encosto': ...")."""


def _fail(label: str, message: str):
    raise ShapeError(f"{label}: {message}")


def _num(shape: dict, key: str, label: str, default=None, positive: bool = False) -> float:
    value = shape.get(key, default)
    if value is None:
        _fail(label, f"falta '{key}'")
    try:
        value = float(value)
    except (TypeError, ValueError):
        _fail(label, f"'{key}' precisa ser número")
    if not math.isfinite(value) or (positive and value <= 1e-6):
        _fail(label, f"'{key}' ≤ 0" if positive else f"'{key}' inválido")
    return value


def _vec(shape: dict, key: str, label: str, size: int, default=None, positive=False):
    value = shape.get(key, default)
    try:
        out = [float(c) for c in value]
    except (TypeError, ValueError):
        _fail(label, f"'{key}' precisa ser uma lista de {size} números")
    if len(out) != size or not all(math.isfinite(c) for c in out):
        _fail(label, f"'{key}' precisa ser uma lista de {size} números")
    if positive and min(out) <= 1e-6:
        _fail(label, f"'{key}' tem medida ≤ 0")
    return out


def _points(value, label: str, key: str, size: int, minimum: int) -> np.ndarray:
    try:
        pts = np.asarray([[float(c) for c in p] for p in value], dtype=float)
    except (TypeError, ValueError):
        _fail(label, f"'{key}' precisa ser uma lista de pontos")
    if pts.ndim != 2 or pts.shape[1] != size or len(pts) < minimum \
            or not np.isfinite(pts).all():
        _fail(label, f"'{key}' precisa de pelo menos {minimum} pontos de {size} números")
    return pts


# --- curvas -------------------------------------------------------------------------------


def _smooth(pts: np.ndarray, steps: int, closed: bool = False) -> np.ndarray:
    """Curva suave (Catmull-Rom) que passa pelos pontos, ``steps`` trechos entre cada par."""
    n = len(pts)
    if n < 3 or steps < 2:
        return pts
    out = []
    count = n if closed else n - 1
    for i in range(count):
        p0 = pts[(i - 1) % n] if closed or i > 0 else pts[0]
        p1, p2 = pts[i], pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if closed or i + 2 < n else pts[n - 1]
        for k in range(steps):
            t = k / steps
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t
                              + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    if not closed:
        out.append(pts[-1])
    return np.asarray(out)


def _dedupe(pts: np.ndarray, closed: bool = False) -> np.ndarray:
    keep = [0]
    for i in range(1, len(pts)):
        if np.linalg.norm(pts[i] - pts[keep[-1]]) > 1e-7:
            keep.append(i)
    if closed and len(keep) > 1 and np.linalg.norm(pts[keep[-1]] - pts[keep[0]]) <= 1e-7:
        keep.pop()
    return pts[keep]


def _area2(poly: np.ndarray) -> float:
    x, y = poly[:, 0], poly[:, 1]
    return float(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y))


def _resample(poly: np.ndarray, count: int) -> np.ndarray:
    """``count`` pontos igualmente espaçados no contorno fechado, a partir do ponto de
    menor ângulo em torno do centro (para os contornos de seções vizinhas casarem)."""
    center = poly.mean(axis=0)
    angles = np.arctan2(poly[:, 1] - center[1], poly[:, 0] - center[0])
    poly = np.roll(poly, -int(np.argmin(np.abs(angles))), axis=0)
    ring = np.vstack([poly, poly[:1]])
    lengths = np.linalg.norm(np.diff(ring, axis=0), axis=1)
    total = lengths.sum()
    marks = np.concatenate([[0.0], np.cumsum(lengths)])
    at = np.linspace(0.0, total, count, endpoint=False)
    return np.column_stack([np.interp(at, marks, ring[:, 0]), np.interp(at, marks, ring[:, 1])])


def triangulate(poly: np.ndarray) -> list[tuple[int, int, int]]:
    """Triângulos (índices, anti-horário) de um polígono simples, por corte de orelhas."""
    n = len(poly)
    order = list(range(n)) if _area2(poly) > 0 else list(range(n - 1, -1, -1))
    out = []

    def cross(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    guard = 0
    while len(order) > 3 and guard < 4 * n * n:
        guard += 1
        m = len(order)
        for k in range(m):
            i, j, l = order[k - 1], order[k], order[(k + 1) % m]
            a, b, c = poly[i], poly[j], poly[l]
            if cross(a, b, c) <= 1e-12:
                continue
            inside = False
            for o in order:
                if o in (i, j, l):
                    continue
                p = poly[o]
                if cross(a, b, p) >= -1e-12 and cross(b, c, p) >= -1e-12 \
                        and cross(c, a, p) >= -1e-12:
                    inside = True
                    break
            if not inside:
                out.append((i, j, l))
                order.pop(k)
                break
        else:  # polígono degenerado: fecha em leque para não travar
            break
    for k in range(1, len(order) - 1):
        out.append((order[0], order[k], order[k + 1]))
    return out


# --- malha --------------------------------------------------------------------------------


class _Mesh:
    def __init__(self):
        self.vertices: list = []
        self.faces: list = []

    def add(self, points) -> int:
        start = len(self.vertices)
        self.vertices.extend(np.asarray(points, dtype=float).tolist())
        return start

    def quad_strip(self, a: int, b: int, count: int) -> None:
        """Liga dois anéis de ``count`` pontos (``a`` embaixo, ``b`` em cima; os anéis são
        anti-horários vistos de cima): faces para fora."""
        for i in range(count):
            j = (i + 1) % count
            self.faces.append((a + i, a + j, b + j))
            self.faces.append((a + i, b + j, b + i))

    def cap(self, start: int, ring2d: np.ndarray, up: bool) -> None:
        for i, j, k in triangulate(ring2d):
            self.faces.append((start + i, start + j, start + k) if up
                              else (start + i, start + k, start + j))

    def arrays(self):
        """Vértices e faces, com os vértices repetidos soldados (o eixo de uma revolução,
        por exemplo) e as faces sem área tiradas."""
        vertices = np.asarray(self.vertices, dtype=float).reshape(-1, 3)
        faces = np.asarray(self.faces, dtype=np.int64).reshape(-1, 3)
        _, first, inverse = np.unique(np.round(vertices, 7), axis=0, return_index=True,
                                      return_inverse=True)
        faces = inverse.reshape(-1)[faces]
        keep = (faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2])             & (faces[:, 0] != faces[:, 2])
        return vertices[first], faces[keep]


def _circle(n: int) -> np.ndarray:
    a = np.linspace(0.0, 2 * math.pi, n, endpoint=False)
    return np.column_stack([np.cos(a), np.sin(a)])


def _stack(mesh: _Mesh, rings: list[np.ndarray], zs=None) -> None:
    """Sólido por anéis 3D sucessivos (todos com a mesma contagem), com tampas."""
    count = len(rings[0])
    starts = [mesh.add(r) for r in rings]
    for a, b in itertools.pairwise(starts):
        mesh.quad_strip(a, b, count)


def _box(shape: dict, label: str, n: int) -> _Mesh:
    w, d, h = _vec(shape, "size", label, 3, positive=True)
    r = min(_num(shape, "radius", label, 0.0), w / 2, d / 2, h / 2)
    mesh = _Mesh()
    if r <= 1e-6:
        x, y = w / 2, d / 2
        mesh.add([[-x, -y, 0], [x, -y, 0], [x, y, 0], [-x, y, 0],
                  [-x, -y, h], [x, -y, h], [x, y, h], [-x, y, h]])
        mesh.faces += [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
                       (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
        return mesh
    # esfera de raio r "esticada": cada vértice anda (meia medida − r) para o seu lado
    lon = max(8, 4 * round(n / 4))
    lat = max(4, 2 * round(n / 4))
    half = np.array([w / 2 - r, d / 2 - r, h / 2 - r])
    angles = (np.arange(lon) + 0.5) * 2 * math.pi / lon  # nenhum vértice com x ou y = 0
    rings = []
    for k in range(lat):
        phi = -math.pi / 2 + (k + 0.5) * math.pi / lat  # nem com z = 0
        ring = np.column_stack([np.cos(phi) * np.cos(angles), np.cos(phi) * np.sin(angles),
                                np.full(lon, math.sin(phi))])
        rings.append(ring * r + np.sign(ring) * half + [0, 0, h / 2])
    starts = [mesh.add(ring) for ring in rings]
    for a, b in itertools.pairwise(starts):
        mesh.quad_strip(a, b, lon)
    mesh.cap(starts[0], rings[0][:, :2], up=False)
    mesh.cap(starts[-1], rings[-1][:, :2], up=True)
    # a esfera amostrada não toca os extremos: acerta para a medida pedida
    points = np.asarray(mesh.vertices)
    center = np.array([0.0, 0.0, h / 2])
    extent = np.abs(points - center).max(axis=0)
    mesh.vertices = ((points - center) * (np.array([w, d, h]) / 2 / extent)
                     + center).tolist()
    return mesh


def _ellipsoid(shape: dict, label: str, n: int) -> _Mesh:
    radii = np.array(_vec(shape, "radii", label, 3, positive=True))
    mesh = _Mesh()
    lat = max(4, n // 2)
    circle = _circle(n)
    starts = []
    for k in range(1, lat):
        phi = -math.pi / 2 + k * math.pi / lat
        ring = np.column_stack([circle * math.cos(phi), np.full(n, math.sin(phi))]) * radii
        starts.append(mesh.add(ring))
    for a, b in itertools.pairwise(starts):
        mesh.quad_strip(a, b, n)
    bottom = mesh.add([[0, 0, -radii[2]]])
    top = mesh.add([[0, 0, radii[2]]])
    for i in range(n):
        j = (i + 1) % n
        mesh.faces.append((bottom, starts[0] + j, starts[0] + i))
        mesh.faces.append((top, starts[-1] + i, starts[-1] + j))
    return mesh


def _cone(shape: dict, label: str, n: int) -> _Mesh:
    r0 = _num(shape, "radius", label, positive=True)
    r1 = _num(shape, "top_radius", label, r0)
    h = _num(shape, "height", label, positive=True)
    if r1 < 0:
        _fail(label, "'top_radius' < 0")
    mesh = _Mesh()
    circle = _circle(n)
    base = mesh.add(np.column_stack([circle * r0, np.zeros(n)]))
    mesh.cap(base, circle, up=False)
    if r1 <= 1e-6:
        apex = mesh.add([[0, 0, h]])
        for i in range(n):
            mesh.faces.append((base + i, base + (i + 1) % n, apex))
        return mesh
    top = mesh.add(np.column_stack([circle * r1, np.full(n, h)]))
    mesh.quad_strip(base, top, n)
    mesh.cap(top, circle, up=True)
    return mesh


def _tube(shape: dict, label: str, n: int) -> _Mesh:
    path = _points(shape.get("path"), label, "path", 3, 2)
    if shape.get("smooth"):
        path = _smooth(path, max(3, n // 4))
    path = _dedupe(path)
    if len(path) < 2:
        _fail(label, "o caminho precisa de dois pontos diferentes")
    if shape.get("section") is not None:
        sw, sh = _vec(shape, "section", label, 2, positive=True)
        profile = np.array([[-sw / 2, -sh / 2], [sw / 2, -sh / 2], [sw / 2, sh / 2],
                            [-sw / 2, sh / 2]])
    else:
        profile = _circle(max(8, 4 * round(n / 8))) * _num(shape, "radius", label,
                                                              positive=True)
    # tangentes e um referencial que acompanha o caminho sem torcer
    seg = np.diff(path, axis=0)
    seg /= np.linalg.norm(seg, axis=1)[:, None]
    tangents = np.vstack([seg[:1], seg[:-1] + seg[1:], seg[-1:]])
    norms = np.linalg.norm(tangents, axis=1)
    tangents = np.where(norms[:, None] > 1e-9, tangents / np.maximum(norms, 1e-12)[:, None],
                        np.vstack([seg[:1], seg[1:], seg[-1:]]))
    up = np.array([0.0, 0.0, 1.0])
    side = np.cross(up, tangents[0])
    if np.linalg.norm(side) < 1e-6:  # caminho que começa na vertical
        side = np.array([1.0, 0.0, 0.0])
    side /= np.linalg.norm(side)
    mesh, rings = _Mesh(), []
    for point, tangent in zip(path, tangents, strict=True):
        side = side - tangent * np.dot(side, tangent)
        length = np.linalg.norm(side)
        side = side / length if length > 1e-9 else np.cross(tangent, up)
        normal = np.cross(tangent, side)
        rings.append(point + profile[:, :1] * side + profile[:, 1:] * normal)
    starts = [mesh.add(r) for r in rings]
    for a, b in itertools.pairwise(starts):
        mesh.quad_strip(a, b, len(profile))
    mesh.cap(starts[0], profile, up=False)
    mesh.cap(starts[-1], profile, up=True)
    return mesh


def _section_ring(section: dict, label: str, count: int) -> np.ndarray:
    z = _num(section, "z", label)
    cx, cy = _vec(section, "center", label, 2, default=[0.0, 0.0])
    if section.get("points") is not None:
        outline = _dedupe(_points(section["points"], label, "points", 2, 3), closed=True)
        if len(outline) < 3 or abs(_area2(outline)) < 1e-9:
            _fail(label, "contorno sem área")
        if _area2(outline) < 0:
            outline = outline[::-1]
        ring = _resample(outline, count)
    else:
        radii = section.get("radii", section.get("radius"))
        if isinstance(radii, (int, float)):
            radii = [radii, radii]
        rx, ry = _vec({"radii": radii}, "radii", label, 2, positive=True)
        ring = _circle(count) * [rx, ry]
    twist = math.radians(_num(section, "twist", label, 0.0))
    if twist:
        c, s = math.cos(twist), math.sin(twist)
        ring = ring @ np.array([[c, s], [-s, c]])
    return np.column_stack([ring + [cx, cy], np.full(count, z)])


def _sections(shape: dict, label: str, n: int) -> _Mesh:
    found = shape.get("sections")
    if not isinstance(found, list) or len(found) < 2:
        _fail(label, "'sections' precisa de pelo menos duas seções")
    rings = [_section_ring(s if isinstance(s, dict) else {}, f"{label}, seção {i + 1}", n)
             for i, s in enumerate(found)]
    zs = [r[0, 2] for r in rings]
    if any(b - a <= 1e-6 for a, b in itertools.pairwise(zs)):
        _fail(label, "as seções precisam estar em 'z' crescente")
    if shape.get("smooth") and len(rings) > 2:
        stacked = np.asarray(rings)  # (seções, n, 3)
        steps = max(2, n // 6)
        rings = list(np.stack([_smooth(stacked[:, i, :], steps) for i in range(n)], axis=1))
    mesh = _Mesh()
    starts = [mesh.add(r) for r in rings]
    for a, b in itertools.pairwise(starts):
        mesh.quad_strip(a, b, n)
    mesh.cap(starts[0], rings[0][:, :2], up=False)
    mesh.cap(starts[-1], rings[-1][:, :2], up=True)
    return mesh


def _revolution(shape: dict, label: str, n: int) -> _Mesh:
    profile = _points(shape.get("profile"), label, "profile", 2, 2)
    if (profile[:, 0] < -1e-9).any():
        _fail(label, "o perfil da revolução fica do lado raio ≥ 0")
    if shape.get("smooth"):
        profile = _smooth(profile, max(3, n // 4))
        profile[:, 0] = np.maximum(profile[:, 0], 0.0)
    profile = _dedupe(profile)
    if profile[0, 1] > profile[-1, 1]:
        profile = profile[::-1]
    if profile[:, 0].max() <= 1e-6 or len(profile) < 2:
        _fail(label, "perfil sem raio")
    angle = _num(shape, "angle", label, 360.0)
    if not 0 < angle <= 360 + 1e-9:
        _fail(label, "ângulo da revolução fora de (0, 360]")
    full = angle >= 360 - 1e-9
    steps = n if full else max(3, round(n * angle / 360))
    angles = np.linspace(0.0, math.radians(angle), steps, endpoint=False) if full \
        else np.linspace(0.0, math.radians(angle), steps + 1)
    mesh = _Mesh()
    # fecha o perfil no eixo: (0, z do começo) ... perfil ... (0, z do fim)
    outline = profile
    if outline[0, 0] > 1e-6:
        outline = np.vstack([[0.0, outline[0, 1]], outline])
    if outline[-1, 0] > 1e-6:
        outline = np.vstack([outline, [0.0, outline[-1, 1]]])
    columns = [mesh.add(np.column_stack([outline[:, 0] * math.cos(a),
                                         outline[:, 0] * math.sin(a), outline[:, 1]]))
               for a in angles]
    m = len(outline)
    pairs = list(zip(columns, columns[1:] + ([columns[0]] if full else []), strict=False))
    for a, b in pairs:
        for i in range(m - 1):
            lower, upper = outline[i, 0] > 1e-6, outline[i + 1, 0] > 1e-6
            if lower:
                mesh.faces.append((a + i, b + i, b + i + 1) if upper
                                  else (a + i, b + i, a + i + 1))
            if upper and lower or upper:
                mesh.faces.append((a + i, b + i + 1, a + i + 1))
    if not full:  # as duas faces planas do corte
        flat = np.column_stack([outline[:, 0], outline[:, 1]])
        for i, j, k in triangulate(flat):
            first, last = columns[0], columns[-1]
            ccw = _area2(flat) > 0
            mesh.faces.append((first + i, first + j, first + k) if ccw
                              else (first + i, first + k, first + j))
            mesh.faces.append((last + i, last + k, last + j) if ccw
                              else (last + i, last + j, last + k))
    return mesh


def _extrusion(shape: dict, label: str, n: int) -> _Mesh:
    profile = _points(shape.get("profile"), label, "profile", 2, 3)
    if shape.get("smooth"):
        profile = _smooth(profile, max(3, n // 4), closed=True)
    profile = _dedupe(profile, closed=True)
    if len(profile) < 3 or abs(_area2(profile)) < 1e-9:
        _fail(label, "perfil sem área")
    if _area2(profile) < 0:
        profile = profile[::-1]
    h = _num(shape, "height", label, positive=True)
    mesh = _Mesh()
    base = mesh.add(np.column_stack([profile, np.zeros(len(profile))]))
    top = mesh.add(np.column_stack([profile, np.full(len(profile), h)]))
    mesh.quad_strip(base, top, len(profile))
    mesh.cap(base, profile, up=False)
    mesh.cap(top, profile, up=True)
    return mesh


_BUILDERS = {"box": _box, "ellipsoid": _ellipsoid, "cone": _cone, "tube": _tube,
             "sections": _sections, "revolution": _revolution, "extrusion": _extrusion}


def rotation_matrix(rotation) -> np.ndarray:
    """Matriz de [rx, ry, rz] em graus: gira em x, depois em y, depois em z."""
    rx, ry, rz = (math.radians(float(a)) for a in rotation)
    cx, sx, cy, sy, cz, sz = (math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry),
                              math.cos(rz), math.sin(rz))
    mx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    my = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    mz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return mz @ my @ mx


def label_of(shape, index: int) -> str:
    name = shape.get("name") if isinstance(shape, dict) else None
    return f"forma {index + 1} {str(name)!r}" if name else f"forma {index + 1}"


def shape_mesh(shape: dict, index: int = 0, detail: int = DETAILS[0]):
    """(vértices, faces) de uma forma, já girada e posta no lugar."""
    label = label_of(shape, index)
    if not isinstance(shape, dict) or shape.get("kind") not in KINDS:
        kind = shape.get("kind") if isinstance(shape, dict) else shape
        _fail(label, f"tipo {kind!r} não existe (use {', '.join(KINDS)})")
    vertices, faces = _BUILDERS[shape["kind"]](shape, label, detail).arrays()
    rotation = _vec(shape, "rotation", label, 3, default=[0.0, 0.0, 0.0])
    position = _vec(shape, "position", label, 3, default=[0.0, 0.0, 0.0])
    if any(rotation):
        vertices = vertices @ rotation_matrix(rotation).T
    return vertices + position, faces


def build(recipe: list, limit: int = MAX_TRIANGLES, prefer: int = PREFERRED) -> list[dict]:
    """Partes da forma livre (uma por material, na ordem em que aparecem), com
    ``vertices`` e ``faces`` em listas. O detalhe das curvas é o maior que cabe em
    ``prefer`` triângulos; se nenhum cabe, o menor, desde que caiba em ``limit``. Recusa
    receita vazia, com formas demais ou que passa de ``limit`` no menor detalhe."""
    if not isinstance(recipe, list) or not recipe:
        raise OpError("a forma livre precisa de pelo menos uma forma em 'shapes'")
    if len(recipe) > MAX_SHAPES:
        raise OpError(f"{len(recipe)} formas: o limite é {MAX_SHAPES}. Simplifique")
    for detail in DETAILS:
        meshes = [shape_mesh(shape, i, detail) for i, shape in enumerate(recipe)]
        if sum(len(f) for _, f in meshes) <= prefer:
            break
    if sum(len(f) for _, f in meshes) > limit:
        raise OpError(f"a malha passa de {limit} triângulos mesmo no menor detalhe: use "
                      "menos formas")
    parts: dict[str, dict] = {}
    for shape, (vertices, faces) in zip(recipe, meshes, strict=True):
        material = str(shape.get("material") or "").strip()
        part = parts.setdefault(material, {"name": material or "Corpo", "material":
                                           material or None, "v": [], "f": [], "n": 0})
        part["f"].append(faces + part["n"])
        part["v"].append(vertices)
        part["n"] += len(vertices)
    return [{"name": p["name"], "material": p["material"],
             "vertices": np.round(np.vstack(p["v"]), 4).tolist(),
             "faces": np.vstack(p["f"]).tolist()} for p in parts.values()]
