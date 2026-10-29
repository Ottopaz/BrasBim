# SPDX-License-Identifier: GPL-3.0-or-later
"""Ícones isométricos próprios das ferramentas de modelagem (spec/ui 34 §2).

Cada ícone é montado com sólidos e faces simples em 3D, projetado em isometria (x para
a direita e para baixo, y para a esquerda e para baixo, z para cima), com as linhas
escondidas removidas e as faces laterais levemente sombreadas com ``currentColor``.
O resultado é ajustado ao quadro 24 × 24. Usado por ``scripts/gerar_icones.py``.
"""

from __future__ import annotations

import math

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

C30, S30 = math.cos(math.radians(30)), 0.5
SHADE = {"top": 0.0, "left": 0.08, "right": 0.18}  # opacidade das faces, pela orientação
STROKE = 1.25
FINE = 1.0


def proj(p):
    x, y, z = p
    return ((x - y) * C30, (x + y) * S30 - z)


def box(x0, y0, z0, x1, y1, z1, rot=0.0, pivot=(0.0, 0.0)):
    """Seis faces de uma caixa, girada ``rot`` graus em torno do eixo vertical."""
    pts = [(x, y, z) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
    if rot:
        a = math.radians(rot)
        px, py = pivot
        pts = [(px + (x - px) * math.cos(a) - (y - py) * math.sin(a),
                py + (x - px) * math.sin(a) + (y - py) * math.cos(a), z) for x, y, z in pts]
    idx = [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]
    return [[pts[k] for k in f] for f in idx]


def _normal(face):
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = face[0], face[1], face[2]
    u = (bx - ax, by - ay, bz - az)
    v = (cx - ax, cy - ay, cz - az)
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])


def _outward(solid):
    pts = [p for f in solid for p in f]
    c = [sum(p[i] for p in pts) / len(pts) for i in range(3)]
    out = []
    for f in solid:
        n = _normal(f)
        m = [sum(p[i] for p in f) / len(f) for i in range(3)]
        out.append(f[::-1] if sum(n[i] * (m[i] - c[i]) for i in range(3)) < 0 else f)
    return out


def _kind(n) -> str:
    k = max(range(3), key=lambda i: abs(n[i]))
    return "top" if k == 2 else ("right" if k == 0 else "left")


def _path(coords, closed=False) -> str:
    d = "M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in coords)
    return d + (" Z" if closed else "")


def render(solids=(), planes=(), lines=(), margin=2.0) -> str:
    """SVG do ícone. ``solids``: listas de faces (só as de frente aparecem); ``planes``:
    faces soltas, vistas dos dois lados; ``lines``: ``(pontos, espessura)`` por cima."""
    faces = []
    for solid in solids:
        for f in _outward(solid):
            n = _normal(f)
            if sum(n) > 1e-9:
                faces.append(f)
    for f in planes:
        faces.append(f if sum(_normal(f)) >= 0 else f[::-1])
    faces.sort(key=lambda f: sum(sum(p) for p in f) / len(f))  # pintor: de trás para frente
    pts = [proj(p) for f in faces for p in f] + [proj(p) for line, _ in lines for p in line]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    s = (24 - 2 * margin) / max(max(xs) - min(xs), max(ys) - min(ys))
    ox = 12 - (max(xs) + min(xs)) / 2 * s
    oy = 12 - (max(ys) + min(ys)) / 2 * s

    def tr(p):
        x, y = proj(p)
        return (ox + x * s, oy + y * s)

    polys = [Polygon([tr(p) for p in f]).buffer(0) for f in faces]
    body = []
    for i, f in enumerate(faces):
        cover = unary_union(polys[i + 1:]) if i + 1 < len(polys) else None
        shade = SHADE[_kind(_normal(f))]
        visible = polys[i].difference(cover) if cover is not None else polys[i]
        if shade and not visible.is_empty:
            for g in getattr(visible, "geoms", [visible]):
                if g.geom_type == "Polygon" and g.area > 0.05:
                    body.append(f'<path d="{_path(g.exterior.coords, True)}" '
                                f'fill="currentColor" fill-opacity="{shade}" stroke="none"/>')
        edges = LineString([tr(p) for p in f] + [tr(f[0])])
        if cover is not None:
            edges = edges.difference(cover.buffer(-0.02))
        for g in getattr(edges, "geoms", [edges]):
            if not g.is_empty and g.length >= 0.15:
                body.append(f'<path d="{_path(g.coords)}"/>')
    for line, width in lines:
        attr = "" if width == STROKE else f' stroke-width="{width}"'
        body.append(f'<path d="{_path([tr(p) for p in line])}"{attr}/>')
    head = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="{STROKE}" stroke-linecap="round" '
            'stroke-linejoin="round">\n'
            '<!-- SPDX-License-Identifier: GPL-3.0-or-later. Ícone próprio do BrasBim. -->\n')
    return head + "\n".join(body) + "\n</svg>\n"


def _rect_xz(x0, x1, z0, z1, y=0.0):
    return [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1), (x0, y, z0)]


def _wall_plane_with(hole, inner=()):
    """Parede de quatro linhas com a abertura (janela e vão, §2)."""
    return render(lines=[(_rect_xz(0, 12, 0, 9.5), STROKE), (_rect_xz(*hole), STROKE),
                         *[(p, FINE) for p in inner]])


def _stair():
    rise, run, n = 1.6, 2.0, 4
    planes = []
    for i in range(n):
        y = run * (n - i)
        planes.append([(0, y, i * rise), (6, y, i * rise), (6, y, (i + 1) * rise),
                       (0, y, (i + 1) * rise)])
        planes.append([(0, y, (i + 1) * rise), (6, y, (i + 1) * rise),
                       (6, y - run, (i + 1) * rise), (0, y - run, (i + 1) * rise)])
    return render(planes=planes)


def _skylight():
    def at(t, u):  # na água: t ao longo da beira, u da beira baixa (frente) ao topo
        return (t, 8 - 8 * u, 5 * u)

    return render(planes=[[at(0, 0), at(10, 0), at(10, 1), at(0, 1)]],
                  lines=[([at(3, 0.3), at(7, 0.3), at(7, 0.75), at(3, 0.75), at(3, 0.3)],
                          STROKE)])


def _terrain():
    """Malha ondulada: linhas de uma superfície z = f(x, y)."""
    def z(x, y):
        return 1.6 * math.sin(x / 3.2) + 1.2 * math.cos(y / 2.6)

    n = 10
    lines = []
    for i in range(0, n + 1, 2):
        lines.append(([(i, y / 2, z(i, y / 2)) for y in range(2 * n + 1)], FINE))
        lines.append(([(x / 2, i, z(x / 2, i)) for x in range(2 * n + 1)], FINE))
    edge = [(x / 2, 0, z(x / 2, 0)) for x in range(2 * n + 1)]
    edge += [(n, y / 2, z(n, y / 2)) for y in range(1, 2 * n + 1)]
    edge += [(x / 2, n, z(x / 2, n)) for x in range(2 * n - 1, -1, -1)]
    edge += [(0, y / 2, z(0, y / 2)) for y in range(2 * n - 1, -1, -1)]
    return render(lines=[*lines, (edge, STROKE)])


def _object():
    """Cadeira: assento, encosto e pernas."""
    legs = [([(x, y, 0), (x, y, 4)], FINE) for x, y in ((0.4, 0.4), (4.6, 0.4), (4.6, 4.6),
                                                         (0.4, 4.6))]
    return render(solids=[box(0, 0, 4, 5, 5, 4.7), box(0, 0, 4.7, 0.7, 5, 10)], lines=legs)


ICONS = {
    "wall": render([box(0, 0, 0, 12, 1.8, 6)]),
    # porta: a folha fechada, em pé, com a maçaneta
    "door": render([box(0, 0, 0, 5.5, 0.45, 11)],
                   lines=[([(4.3, 0.45, 4.8), (3.4, 0.45, 4.8)], 1.6)]),
    "window": _wall_plane_with((2.2, 9.8, 2.0, 7.5),
                               [[(6, 0, 2.0), (6, 0, 7.5)], [(2.2, 0, 5.4), (9.8, 0, 5.4)]]),
    "wall_opening": _wall_plane_with((2.2, 9.8, 2.0, 7.5)),
    "column": render([box(0.6, 0.6, 0, 3.0, 3.0, 10.5)]),
    "beam": render([box(0, 0, 0, 12, 1.6, 2.6)],
                   lines=[([(0.8, 0.8, 0), (0.8, 0.8, -4)], FINE),
                          ([(11.2, 0.8, 0), (11.2, 0.8, -4)], FINE)]),
    "slab": render([box(0, 0, 0, 10, 9, 1.4)]),
    "slab_opening": render(planes=[[(0, 0, 0), (10, 0, 0), (10, 9, 0), (0, 9, 0)]],
                           lines=[([(3, 2.5, 0), (7, 2.5, 0), (7, 6.5, 0), (3, 6.5, 0),
                                    (3, 2.5, 0)], STROKE)]),
    # cobertura: só as duas águas, em trapézio (inclinação baixa: na isometria uma água
    # mais íngreme que a vista some atrás da cumeeira)
    "roof": render(planes=[[(0, 10, 0), (12, 10, 0), (9.5, 5, 2.1), (2.5, 5, 2.1)],
                           [(2.5, 5, 2.1), (9.5, 5, 2.1), (12, 0, 0), (0, 0, 0)]]),
    "skylight": _skylight(),
    "stair": _stair(),
    # guarda-corpo: corrimão, montantes e uma barra, só em linhas
    "railing": render(lines=[([(-0.5, 0, 5), (10.5, 0, 5)], STROKE),
                             *[([(x, 0, 0), (x, 0, 5)], FINE) for x in (0, 5, 10)],
                             ([(0, 0, 2.5), (10, 0, 2.5)], FINE)]),
    "terrain": _terrain(),
    "object": _object(),
}
