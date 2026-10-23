# SPDX-License-Identifier: LGPL-3.0-or-later
"""Deslocar paralela, aparar/estender e concordar (``spec/ui/23-precisao.md`` §4–§6),
sem Qt.

Coordenadas do pavimento, em metros. Os limites de aparar e estender vêm do índice de
atração (``snap.SnapIndex``): todas as arestas e curvas visíveis do pavimento.
"""

from __future__ import annotations

import math

from brasbim.core import geom2d, snap
from brasbim.core.annotations import base as annotation_base
from brasbim.core.annotations import commands as ac
from brasbim.core.annotations import drawing2d
from brasbim.core.document import Document, OpError
from brasbim.core.geom2d import Point
from brasbim.core.ops import Transaction
from brasbim.core.walls import commands as wc
from brasbim.core.walls import params as wall_params
from brasbim.core.walls.wall import read_state as read_wall

EPS = 1e-7
NOTHING = "nada para aparar ou estender aqui"


# --- geometria -----------------------------------------------------------------------------


def _sub(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1])


def _cross(a: Point, b: Point) -> float:
    return a[0] * b[1] - a[1] * b[0]


def _unit(v: Point) -> Point:
    n = math.hypot(*v)
    return (v[0] / n, v[1] / n)


def _line_cross(a: Point, b: Point, c: Point, d: Point) -> tuple[float, float] | None:
    """Parâmetros (t em a→b, u em c→d) do cruzamento das retas, ou None se paralelas."""
    r, q = _sub(b, a), _sub(d, c)
    den = _cross(r, q)
    if abs(den) < 1e-12:
        return None
    w = _sub(c, a)
    return _cross(w, q) / den, _cross(w, r) / den


def _at(a: Point, b: Point, t: float) -> Point:
    return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))


def _param_on(a: Point, b: Point, p: Point) -> float:
    d = _sub(b, a)
    return ((p[0] - a[0]) * d[0] + (p[1] - a[1]) * d[1]) / (d[0] ** 2 + d[1] ** 2)


def offset_polyline(points, closed: bool, d: float) -> list[Point]:
    """Polilinha paralela a ``d`` para a esquerda do sentido (negativo: direita), com
    cantos em ponta. Recusa trechos nulos."""
    pts = [tuple(map(float, q)) for q in points]
    n = len(pts)
    if n < 2:
        raise OpError("a linha precisa de pelo menos 2 pontos")
    segs = [(i, (i + 1) % n) for i in range(n if closed else n - 1)]
    lines = []
    for i, j in segs:
        u = _unit(_sub(pts[j], pts[i]))
        nrm = (-u[1] * d, u[0] * d)
        lines.append(((pts[i][0] + nrm[0], pts[i][1] + nrm[1]),
                      (pts[j][0] + nrm[0], pts[j][1] + nrm[1])))
    out = []
    for k in range(n):
        if not closed and k == 0:
            out.append(lines[0][0])
        elif not closed and k == n - 1:
            out.append(lines[-1][1])
        else:
            prev, nxt = lines[k - 1], lines[k % len(lines)]
            found = _line_cross(prev[0], prev[1], nxt[0], nxt[1])
            out.append(_at(prev[0], prev[1], found[0]) if found else prev[1])
    return out


def side(points, closed: bool, cursor: Point) -> float:
    """+1 se o cursor está à esquerda do trecho mais próximo (fechada: fora), senão -1."""
    pts = [tuple(map(float, q)) for q in points]
    if closed:
        area = sum(_cross(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))) / 2
        inside = _inside(pts, cursor)
        ccw = area > 0
        # anti-horário: a esquerda é dentro
        return (-1.0 if inside else 1.0) * (-1.0 if ccw else 1.0)
    best = min(range(len(pts) - 1),
               key=lambda i: snap._seg_dist(cursor, pts[i], pts[i + 1]))
    a, b = pts[best], pts[best + 1]
    return 1.0 if _cross(_sub(b, a), _sub(cursor, a)) >= 0 else -1.0


def _inside(ring, p) -> bool:
    found = False
    for i in range(len(ring)):
        (x0, y0), (x1, y1) = ring[i], ring[(i + 1) % len(ring)]
        if (y0 > p[1]) != (y1 > p[1]) and p[0] < x0 + (p[1] - y0) * (x1 - x0) / (y1 - y0):
            found = not found
    return found


def distance_to(points, closed: bool, cursor: Point) -> float:
    pts = [tuple(map(float, q)) for q in points]
    pairs = list(zip(pts, pts[1:] + (pts[:1] if closed else []), strict=False))
    return min(snap._seg_dist(cursor, a, b) for a, b in pairs)


# --- deslocar paralela (§4) ------------------------------------------------------------------

OFFSETTABLE = ("wall", "line2d", "circle2d", "arc2d", "slab", "space", "hatch")


def kind_of(doc: Document, element) -> str | None:
    """Categoria do elemento para as edições deste módulo, ou None."""
    if element is None:
        return None
    if element.is_a("IfcWall"):
        return "wall"
    if element.is_a("IfcSlab") and not element.is_a("IfcRoof"):
        from brasbim.core.structure import slabs

        return "slab" if slabs.is_parametric(element) else None
    if element.is_a("IfcSpace"):
        return "space"
    if element.is_a("IfcAnnotation"):
        kind = annotation_base.kind_of(element)
        if kind is not None and kind.prefix in ("line2d", "circle2d", "arc2d", "hatch"):
            return kind.prefix
    return None


def offset_geometry(doc: Document, element, distance: float, cursor: Point) -> dict:
    """Estado novo (só os campos que mudam) do elemento deslocado ``distance`` para o
    lado do cursor."""
    kind = kind_of(doc, element)
    if kind is None:
        raise OpError("este elemento não se desloca em paralelo")
    if distance <= 0:
        raise OpError("a distância deve ser positiva")
    if kind == "wall":
        path = geom2d.path_from_dict(read_wall(doc, element)["path"])
        frame = geom2d.frame(path)
        y = distance if path.offset(frame.to_local(cursor)) >= 0 else -distance
        pts = [frame.to_global(path.point(y, t)) for t in (0.0, path.t_end / 2, path.t_end)]
        try:
            new = (geom2d.LinePath(pts[0], pts[2]) if isinstance(path, geom2d.LinePath)
                   else geom2d.arc_through(*pts))
        except ValueError as e:
            raise OpError(f"a parede não cabe deslocada: {e}") from e
        return {"path": new}
    state = annotation_base.read_state(element) if element.is_a("IfcAnnotation") else (
        ac.read_state(doc, element) if kind == "space" else _slab_state(doc, element))
    if kind in ("circle2d", "arc2d"):
        outside = math.dist(cursor, state["center"]) >= state["radius"]
        radius = state["radius"] + (distance if outside else -distance)
        if radius <= 1e-6:
            raise OpError("o raio ficaria nulo ou negativo")
        return {"radius": radius}
    key = "points" if kind == "line2d" else "outline"
    closed = state.get("closed", False) if kind == "line2d" else True
    pts = state[key]
    d = distance * side(pts, closed, cursor)
    new = offset_polyline(pts, closed, d)
    if closed and abs(_area(new)) < 1e-6 or (closed and _area(new) * _area(pts) < 0):
        raise OpError("o contorno sumiria deslocado para dentro")
    return {key: [list(q) for q in new]}


def _area(pts) -> float:
    pts = [tuple(q) for q in pts]
    return sum(_cross(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))) / 2


def _slab_state(doc: Document, slab) -> dict:
    from brasbim.core.structure import slabs

    return slabs.read_state(doc, slab)


def offset_element(doc: Document, element, distance: float, cursor: Point,
                   copy: bool = True) -> Transaction:
    """Deslocar paralela: cópia nova (``copy``) ou o próprio elemento movido."""
    kind = kind_of(doc, element)
    changes = offset_geometry(doc, element, distance, cursor)
    label = "Deslocar paralela"
    if kind == "wall":
        if not copy:
            tx = wc.edit_wall(doc, element, path=changes["path"])
            return Transaction(label, tx.ops)
        state = read_wall(doc, element)
        options = {k: state[k] for k in wall_params.STATE_KEYS
                   if k not in ("type", "storey", "path", "name") and k in state}
        return wc.create_wall_path(doc, state["type"], state["storey"], changes["path"],
                                   label, **options)
    if kind == "slab":
        from brasbim.core.structure import commands as sc
        from brasbim.core.structure import slabs

        if not copy:
            return Transaction(label, sc.edit_outline(doc, element, changes["outline"]).ops)
        state = slabs.read_state(doc, element)
        options = {k: state[k] for k in slabs.STATE_KEYS
                   if k not in ("type", "storey", "outline") and k in state}
        tx = sc.create_slab(doc, state["type"], state["storey"], changes["outline"],
                            **options)
        return Transaction(label, tx.ops)
    if kind == "space":
        if not copy:
            return Transaction(label, ac.edit_element(doc, element, **changes).ops)
        state = ac.read_state(doc, element)
        tx = ac.create_space(doc, state["storey"], changes["outline"], name=state["name"],
                             height=state.get("height"))
        return Transaction(label, tx.ops)
    if not copy:
        return Transaction(label, ac.edit_element(doc, element, **changes).ops)
    state = _fields(annotation_base.read_state(element))
    tx = ac.create_annotation(doc, kind, _storey_of(doc, element), **{**state, **changes})
    return Transaction(label, tx.ops)


def _fields(state: dict) -> dict:
    """Estado de uma anotação sem o que a criação recebe à parte."""
    return {k: v for k, v in state.items() if k != "storey"}


def _storey_of(doc: Document, element):
    import ifcopenshell.util.element

    return ifcopenshell.util.element.get_container(element)


# --- aparar e estender (§5) ------------------------------------------------------------------


def _limits(index: snap.SnapIndex, owner: str):
    segs = [s for s in index.segments if s.owner != owner]
    circles = [c for c in index.circles if c.owner != owner]
    return segs, circles


def _hits(a: Point, b: Point, segs, circles, ray: bool = False) -> list[float]:
    """Parâmetros t (0 em ``a``, 1 em ``b``) onde a reta a→b cruza os limites; com
    ``ray``, também além de ``b``; sem, só dentro do trecho."""
    out = []
    for s in segs:
        found = _line_cross(a, b, s.a, s.b)
        if found and -EPS <= found[1] <= 1 + EPS:
            out.append(found[0])
    if math.dist(a, b) > EPS:
        line = geom2d.StraightLine(a, _unit(_sub(b, a)))
        for c in circles:
            for q in geom2d.intersect(line, geom2d.Circle(c.center, c.radius)):
                if c.contains(q):
                    out.append(_param_on(a, b, q))
    hi = math.inf if ray else 1 - EPS
    return sorted(t for t in out if EPS < t < hi)


def _cut_params(pts, closed: bool, segs, circles) -> list[float]:
    """Parâmetros de corte ao longo da polilinha (k + t no trecho k)."""
    n = len(pts)
    pairs = [(i, (i + 1) % n) for i in range(n if closed else n - 1)]
    cuts = []
    for k, (i, j) in enumerate(pairs):
        cuts += [k + t for t in _hits(pts[i], pts[j], segs, circles)]
    return sorted({round(c, 9) for c in cuts})


def _clicked(pts, closed: bool, p: Point) -> float:
    n = len(pts)
    pairs = [(i, (i + 1) % n) for i in range(n if closed else n - 1)]
    k = min(range(len(pairs)), key=lambda k: snap._seg_dist(p, pts[pairs[k][0]],
                                                            pts[pairs[k][1]]))
    a, b = pts[pairs[k][0]], pts[pairs[k][1]]
    return k + min(max(_param_on(a, b, p), 0.0), 1.0)


def _point_at(pts, closed: bool, s: float) -> Point:
    n = len(pts)
    k = min(math.floor(s), (n if closed else n - 1) - 1)
    return _at(pts[k], pts[(k + 1) % n], s - k)


def _piece(pts, closed: bool, s0: float, s1: float) -> list[Point]:
    """Pedaço da polilinha de s0 a s1 (fechada: s1 pode passar do fim e dar a volta)."""
    n = len(pts)
    total = n if closed else n - 1
    out = [_point_at(pts, closed, s0 % total if closed else s0)]
    k = math.floor(s0) + 1
    while k < s1 - EPS:
        out.append(pts[k % n])
        k += 1
    out.append(_point_at(pts, closed, s1 % total if closed and s1 > total else s1))
    return [q for i, q in enumerate(out) if i == 0 or math.dist(q, out[i - 1]) > EPS]


def trim_extend(doc: Document, element, p: Point, index: snap.SnapIndex,
                force_extend: bool = False) -> Transaction:
    """Apara o trecho clicado entre cruzamentos, ou estende a ponta solta até o primeiro
    limite à frente (spec/ui 23 §5)."""
    kind = kind_of(doc, element)
    if kind == "wall":
        return _trim_extend_wall(doc, element, p, force_extend)
    if kind != "line2d":
        raise OpError("aparar e estender valem para linhas 2D e paredes retas")
    state = annotation_base.read_state(element)
    pts = [tuple(map(float, q)) for q in state["points"]]
    closed = state.get("closed", False)
    segs, circles = _limits(index, element.GlobalId)
    cuts = _cut_params(pts, closed, segs, circles)
    sc = _clicked(pts, closed, p)
    total = len(pts) if closed else len(pts) - 1
    if cuts and not force_extend:
        return _trim_line(doc, element, state, pts, closed, cuts, sc, total)
    if closed:
        raise OpError(NOTHING)
    return _extend_line(doc, element, pts, sc, total, segs, circles)


def _trim_line(doc, element, state, pts, closed, cuts, sc, total) -> Transaction:
    label = "Aparar linha"
    if closed:
        if len(cuts) < 2:
            raise OpError(NOTHING)
        lo = max((c for c in cuts if c < sc), default=cuts[-1] - total)
        hi = min((c for c in cuts if c > sc), default=cuts[0] + total)
        keep = _piece(pts, True, hi, lo + total if lo < hi else lo)
        tx = ac.edit_element(doc, element, points=[list(q) for q in keep], closed=False)
        return Transaction(label, tx.ops)
    lo = max((c for c in cuts if c < sc), default=0.0)
    hi = min((c for c in cuts if c > sc), default=float(total))
    first = _piece(pts, False, 0.0, lo) if lo > EPS else None
    second = _piece(pts, False, hi, float(total)) if hi < total - EPS else None
    if first is None and second is None:
        raise OpError(NOTHING)
    keep, extra = (first, second) if first is not None else (second, None)
    ops = list(ac.edit_element(doc, element, points=[list(q) for q in keep]).ops)
    if extra is not None:
        fields = {**_fields(state), "points": [list(q) for q in extra]}
        ops += ac.create_annotation(doc, "line2d", _storey_of(doc, element), **fields).ops
    return Transaction(label, ops)


def _extend_line(doc, element, pts, sc, total, segs, circles) -> Transaction:
    at_start = sc < total / 2
    a, b = (pts[1], pts[0]) if at_start else (pts[-2], pts[-1])
    hits = [t for t in _hits(a, b, segs, circles, ray=True) if t > 1 + EPS]
    if not hits:
        raise OpError(NOTHING)
    q = _at(a, b, hits[0])
    new = [list(q)] + [list(x) for x in pts[1:]] if at_start else \
        [list(x) for x in pts[:-1]] + [list(q)]
    return Transaction("Estender linha", ac.edit_element(doc, element, points=new).ops)


def _wall_axes(doc: Document, wall) -> tuple[list, list]:
    """Eixos das outras paredes do pavimento: segmentos retos e arcos (como círculos)."""
    import ifcopenshell.util.element

    storey = ifcopenshell.util.element.get_container(wall)
    segs, circles = [], []
    for w in snap.wall_paths(doc, storey):
        if w.gid == wall.GlobalId:
            continue
        if w.straight:
            segs.append(snap.Segment(w.path.start, w.path.end, w.gid))
        else:
            center = w.frame.to_global(w.path.local_center())
            segs_span = snap._wall_span(doc, doc.get(w.gid))
            circles.append(snap.CircleRef(center, w.path.radius, w.gid, segs_span))
    return segs, circles


def _straight_wall(doc, wall) -> geom2d.LinePath:
    path = geom2d.path_from_dict(read_wall(doc, wall)["path"])
    if not isinstance(path, geom2d.LinePath):
        raise OpError("parede em arco: aparar, estender e concordar valem só para retas")
    return path


def _trim_extend_wall(doc, wall, p, force_extend) -> Transaction:
    path = _straight_wall(doc, wall)
    segs, circles = _wall_axes(doc, wall)
    a, b = path.start, path.end
    tc = min(max(_param_on(a, b, p), 0.0), 1.0)
    cuts = _hits(a, b, segs, circles)
    end = "end" if tc >= 0.5 else "start"
    if cuts and not force_extend:
        if end == "end":
            inner = [c for c in cuts if c < tc]
            if not inner or any(c > tc for c in cuts):
                raise OpError(NOTHING)
            q = _at(a, b, inner[-1])
        else:
            inner = [c for c in cuts if c > tc]
            if not inner or any(c < tc for c in cuts):
                raise OpError(NOTHING)
            q = _at(a, b, inner[0])
        return wc.set_wall_ends(doc, {wall.GlobalId: {end: q}}, "Aparar parede")
    far, near = (a, b) if end == "end" else (b, a)
    hits = [t for t in _hits(far, near, segs, circles, ray=True) if t > 1 + EPS]
    if not hits:
        raise OpError(NOTHING)
    return wc.set_wall_ends(doc, {wall.GlobalId: {end: _at(far, near, hits[0])}},
                            "Estender parede")


# --- concordar (§6) --------------------------------------------------------------------------


def _line_end_segment(state, p) -> tuple[int, Point, Point]:
    pts = [tuple(map(float, q)) for q in state["points"]]
    if state.get("closed"):
        raise OpError("concordar vale para linhas abertas")
    k = math.floor(_clicked(pts, False, p))
    k = min(k, len(pts) - 2)
    return k, pts[k], pts[k + 1]


def fillet(doc: Document, first, p1: Point, second, p2: Point,
           radius: float = 0.0) -> Transaction:
    """Concorda dois trechos retos (linhas 2D ou paredes retas) no cruzamento das retas;
    fica o lado de cada um em que se clicou (spec/ui 23 §6)."""
    k1, k2 = kind_of(doc, first), kind_of(doc, second)
    if radius < 0:
        raise OpError("o raio não pode ser negativo")
    if first.GlobalId == second.GlobalId:
        raise OpError("escolha dois elementos diferentes")
    if k1 == k2 == "wall":
        if radius > EPS:
            raise OpError("concordância com arco em paredes fica para depois: use raio 0")
        return _fillet_walls(doc, first, p1, second, p2)
    if k1 == k2 == "line2d":
        return _fillet_lines(doc, first, p1, second, p2, radius)
    raise OpError("concordar vale para duas linhas 2D ou duas paredes retas")


def _moving_end(a: Point, b: Point, p: Point, x: Point, free: tuple[bool, bool]) -> str:
    """Qual ponta (``"a"`` ou ``"b"``) vai ao cruzamento ``x``: a do outro lado do
    clique. ``free``: se cada ponta pode mudar (ponta da polilinha)."""
    tc, tx = _param_on(a, b, p), _param_on(a, b, x)
    which = "b" if tc <= tx else "a"
    if not free[0 if which == "a" else 1]:
        raise OpError("concordar muda só as pontas da linha")
    return which


def _fillet_walls(doc, w1, p1, w2, p2) -> Transaction:
    ends = {}
    paths = [_straight_wall(doc, w) for w in (w1, w2)]
    found = _line_cross(paths[0].start, paths[0].end, paths[1].start, paths[1].end)
    if found is None:
        raise OpError("as paredes são paralelas")
    x = _at(paths[0].start, paths[0].end, found[0])
    for wall, path, p in ((w1, paths[0], p1), (w2, paths[1], p2)):
        which = _moving_end(path.start, path.end, p, x, (True, True))
        ends[wall.GlobalId] = {"start" if which == "a" else "end": x}
    return wc.set_wall_ends(doc, ends, "Concordar paredes")


def _fillet_lines(doc, l1, p1, l2, p2, radius) -> Transaction:
    states = [annotation_base.read_state(e) for e in (l1, l2)]
    picks = [_line_end_segment(st, p) for st, p in zip(states, (p1, p2), strict=True)]
    (_, a1, b1), (_, a2, b2) = picks
    found = _line_cross(a1, b1, a2, b2)
    if found is None:
        raise OpError("as linhas são paralelas")
    x = _at(a1, b1, found[0])
    news, keeps = [], []
    for st, (k, a, b), p in zip(states, picks, (p1, p2), strict=True):
        n = len(st["points"])
        which = _moving_end(a, b, p, x, (k == 0, k + 1 == n - 1))
        keeps.append(b if which == "a" else a)  # ponta que fica, no lado do clique
        news.append((which, k))
    ends = [x, x]
    arc = None
    if radius > EPS:
        u = [_unit(_sub(keep, x)) for keep in keeps]
        cos = max(-1.0, min(1.0, u[0][0] * u[1][0] + u[0][1] * u[1][1]))
        theta = math.acos(cos)
        if theta < 1e-6 or math.pi - theta < 1e-6:
            raise OpError("as linhas estão alinhadas: não há concordância")
        dt = radius / math.tan(theta / 2)
        for i in range(2):
            if dt > math.dist(x, keeps[i]) + EPS:
                raise OpError("o raio não cabe nas linhas")
        ends = [(x[0] + u[i][0] * dt, x[1] + u[i][1] * dt) for i in range(2)]
        bis = _unit((u[0][0] + u[1][0], u[0][1] + u[1][1]))
        h = radius / math.sin(theta / 2)
        center = (x[0] + bis[0] * h, x[1] + bis[1] * h)
        mid = (center[0] - bis[0] * radius, center[1] - bis[1] * radius)
        arc = drawing2d.arc_from_points(ends[0], mid, ends[1])
    ops = []
    for element, st, (which, k), q in zip((l1, l2), states, news, ends, strict=True):
        pts = [list(v) for v in st["points"]]
        pts[k if which == "a" else k + 1] = [float(q[0]), float(q[1])]
        ops += ac.edit_element(doc, element, points=pts).ops
    if arc is not None:
        style = {"weight": states[0]["weight"], "dash": states[0]["dash"]}
        ops += ac.create_annotation(doc, "arc2d", _storey_of(doc, l1), **arc, **style).ops
    return Transaction("Concordar linhas", ops)

