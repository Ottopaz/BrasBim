# SPDX-License-Identifier: LGPL-3.0-or-later
"""Ações do usuário sobre paredes, cada uma convertida em uma ``Transaction``.

Os comandos só leem o modelo para montar as operações; quem altera o modelo é
``History.commit``. Assim, cada ação gera exatamente as operações de spec §5.2.
"""

from __future__ import annotations

import itertools
import math

import ifcopenshell.util.element

from brasbim.core import geom2d, guid, storeys
from brasbim.core.document import Document, OpError
from brasbim.core.ops import Op, Transaction
from brasbim.core.ops.history import combine
from brasbim.core.walls import connections, joins, openings, params, rebuild
from brasbim.core.walls import types as wall_types
from brasbim.core.walls.wall import read_state


def _gid(obj) -> str:
    return obj if isinstance(obj, str) else obj.GlobalId


def _wall_data(doc: Document, wall_type, storey, path: geom2d.Path, options: dict) -> dict:
    data = {
        **params.default_state(),
        "type": _gid(wall_type),
        "storey": _gid(storey),
        "path": path.to_dict(),
    }
    unknown = set(options) - set(params.STATE_KEYS)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    data.update(options)
    if "top_mode" not in options:
        # Padrão (spec §3.1): topo ligado ao pavimento imediatamente acima, se houver.
        above = doc.storey_above(doc.get(data["storey"], "IfcBuildingStorey"))
        if above is not None:
            data["top_mode"], data["top_storey"] = "storey", above.GlobalId
    if data["top_mode"] == "storey" and data.get("top_storey"):
        data["top_storey"] = _gid(data["top_storey"])
    return data


# Campos que mudam a detecção de junções.
_JOIN_KEYS = ("path", "storey", "base_offset", "top_mode", "top_storey", "top_offset",
              "fixed_height", "top_profile", "tilt")


def _create_walls(doc: Document, label: str, wall_type, storey, paths, options) -> Transaction:
    """Cria as paredes e as junções detectadas (spec §6.2) numa só transação."""
    new = {guid.new(): _wall_data(doc, wall_type, storey, p, dict(options)) for p in paths}
    ops = [Op("wall.create", gid, data=data) for gid, data in new.items()]
    return Transaction(label, ops + connections.sync_ops(doc, new))


def create_wall(doc: Document, wall_type, storey, start, end, **options) -> Transaction:
    """Parede reta de ``start`` a ``end`` (coordenadas do pavimento, em metros)."""
    path = geom2d.LinePath(tuple(start), tuple(end))
    return _create_walls(doc, "Criar parede", wall_type, storey, [path], options)


def create_arc_wall(doc: Document, wall_type, storey, start, through, end, **options):
    """Parede em arco por 3 pontos: início, um ponto no arco e fim (spec §4)."""
    path = geom2d.arc_through(tuple(start), tuple(through), tuple(end))
    return _create_walls(doc, "Criar parede em arco", wall_type, storey, [path], options)


def create_chain(doc: Document, wall_type, storey, points, closed: bool = False, **options):
    """Cadeia de paredes retas pelos ``points`` (spec §4). ``closed`` liga o último ponto
    ao primeiro. Junções L entre segmentos consecutivos."""
    points = [tuple(p) for p in points]
    if closed:
        points.append(points[0])
    if len(points) < 2:
        raise OpError("a cadeia precisa de pelo menos 2 pontos")
    paths = [geom2d.LinePath(a, b) for a, b in itertools.pairwise(points)]
    return _create_walls(doc, "Criar cadeia de paredes", wall_type, storey, paths, options)


def create_rectangle(doc: Document, wall_type, storey, corner, opposite, **options):
    """4 paredes pelos cantos opostos, percorridas no sentido horário: com a linha de
    referência na face esquerda (padrão), as paredes ficam dentro do retângulo."""
    (x0, x1), (y0, y1) = sorted((corner[0], opposite[0])), sorted((corner[1], opposite[1]))
    points = [(x0, y0), (x0, y1), (x1, y1), (x1, y0), (x0, y0)]
    paths = [geom2d.LinePath(a, b) for a, b in itertools.pairwise(points)]
    return _create_walls(doc, "Criar retângulo de paredes", wall_type, storey, paths, options)


def edit_wall(doc: Document, wall, **changes) -> Transaction:
    """Altera campos do estado da parede (``params.STATE_KEYS``)."""
    wall = doc.get(_gid(wall), "IfcWall")
    state = read_state(doc, wall)
    for key in ("type", "storey", "top_storey"):
        if changes.get(key) is not None:
            changes[key] = _gid(changes[key])
    if "path" in changes and not isinstance(changes["path"], dict):
        changes["path"] = changes["path"].to_dict()
    unknown = set(changes) - set(params.STATE_KEYS)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    if "top_mode" in changes and "top_storey" not in changes:
        # O pavimento do topo só é gravado no modo "storey"; levá-lo junto permite
        # desfazer a troca para altura fixa.
        changes["top_storey"] = state["top_storey"] if changes["top_mode"] == "storey" else None
    before = {k: state[k] for k in changes}
    ops = [Op("wall.edit", wall.GlobalId, before=before, after=dict(changes))]
    if any(k in changes for k in _JOIN_KEYS):
        ops += connections.sync_ops(doc, {wall.GlobalId: {**state, **changes}})
    return Transaction("Editar parede", ops)


def split_wall(doc: Document, wall, at) -> Transaction:
    """Divide a parede no ponto ``at`` (spec §5.1): a segunda parte é uma parede nova,
    ligada à primeira por junção L colinear. Aberturas depois do ponto passam para a
    nova parede; abertura cortada pelo ponto impede a divisão."""
    wall = doc.get(_gid(wall), "IfcWall")
    state = read_state(doc, wall)
    if state["top_profile"]:
        raise OpError("dividir parede com topo inclinado ainda não é possível; "
                      "volte o topo a plano antes")
    try:
        first, second, s = geom2d.split(geom2d.path_from_dict(state["path"]), tuple(at))
    except ValueError as e:
        raise OpError(str(e)) from e
    new = guid.new()
    ops = [Op("wall.split", wall.GlobalId,
              data={"path": state["path"], "at": [float(at[0]), float(at[1])], "new": new})]
    for opening in openings.of_wall(wall):
        o = openings.read_state(opening)
        if o["distance"] < s < o["distance"] + o["width"]:
            raise OpError(f"o ponto de divisão corta a abertura {opening.GlobalId}")
        if o["distance"] >= s:
            ops.append(Op("opening.edit", opening.GlobalId,
                          before={"wall": wall.GlobalId, "distance": o["distance"]},
                          after={"wall": new, "distance": o["distance"] - s}))
    ops += connections.sync_ops(doc, {wall.GlobalId: {**state, "path": first.to_dict()},
                                      new: {**state, "path": second.to_dict()}})
    return Transaction("Dividir parede", ops)


def edit_walls(doc: Document, walls, **changes) -> Transaction:
    """Edição em lote (spec/ui 02 §9): o mesmo ``edit_wall`` em cada parede, numa
    transação só."""
    walls = list(walls)
    if len(walls) == 1:
        return edit_wall(doc, walls[0], **changes)
    return combine(doc, f"Editar {len(walls)} paredes",
                   [lambda w=w: edit_wall(doc, w, **dict(changes)) for w in walls])


# --- alças (spec/ui 02 §4) -------------------------------------------------------------


def _paths_of_storey(doc: Document, storey_id: str) -> dict[str, geom2d.Path]:
    out = {}
    storey = doc.get(storey_id, "IfcBuildingStorey")
    for wall in ifcopenshell.util.element.get_contained(storey):
        if wall.is_a("IfcWall"):
            try:
                out[wall.GlobalId] = geom2d.path_from_dict(read_state(doc, wall)["path"])
            except (OpError, ValueError):
                continue
    return out


def _ends_at(paths: dict[str, geom2d.Path], point, exclude: str) -> list[tuple[str, str]]:
    """(GlobalId, extremidade) das paredes com uma extremidade em ``point``."""
    return [(gid, which) for gid, path in sorted(paths.items()) if gid != exclude
            for which, q in (("start", path.start), ("end", path.end))
            if math.dist(q, point) <= joins.TOL]


def _on_segment(p, a, b) -> bool:
    """``p`` sobre o segmento ``a``–``b``, longe das extremidades."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length2
    foot = (a[0] + t * dx, a[1] + t * dy)
    margin = joins.TOL / math.sqrt(length2)
    return margin < t < 1 - margin and math.dist(p, foot) <= joins.TOL


def _reshape(doc: Document, label: str, paths: dict[str, geom2d.Path],
             extra: dict[str, dict] | None = None) -> Transaction:
    """Troca o caminho das paredes (e, em ``extra``, outros campos do estado). As
    aberturas não saem do lugar quando o início da parede se move (a distância ao início
    é corrigida); abertura que deixaria de caber recusa a ação (spec/ui 02 §4.1)."""
    changed, wall_ops, opening_ops = {}, [], []
    extra = extra or {}
    for gid in dict.fromkeys([*paths, *extra]):
        wall = doc.get(gid, "IfcWall")
        state = read_state(doc, wall)
        old = geom2d.path_from_dict(state["path"])
        new = paths.get(gid, old)
        more = extra.get(gid, {})
        future = {**state, **more, "path": new.to_dict()}
        band, height = rebuild.band(doc, future), rebuild.height(doc, future)
        keep_place = (isinstance(old, geom2d.LinePath) and isinstance(new, geom2d.LinePath)
                      and math.dist(old.start, new.start) > 1e-9)
        for opening in openings.of_wall(wall):
            o = openings.read_state(opening)
            distance = o["distance"]
            if keep_place:
                p = geom2d.frame(old).to_global((distance, 0.0))
                distance = geom2d.frame(new).to_local(p)[0]
            found = openings.problems({**o, "distance": distance}, band, height)
            if found:
                raise OpError(f"a abertura {opening.GlobalId} não caberia na parede "
                              f"{gid}: {'; '.join(found)}")
            if abs(distance - o["distance"]) > 1e-9:
                opening_ops.append(Op("opening.edit", opening.GlobalId,
                                      before={"distance": o["distance"]},
                                      after={"distance": distance}))
        after = {**more, "path": new.to_dict()} if gid in paths else dict(more)
        wall_ops.append(Op("wall.edit", gid, before={k: state[k] for k in after},
                           after=after))
        changed[gid] = future
    return Transaction(label, wall_ops + opening_ops + connections.sync_ops(doc, changed))


def _set_end(paths: dict, new: dict, gid: str, which: str, point) -> None:
    current = new.get(gid, paths[gid])
    point = (float(point[0]), float(point[1]))
    start, end = (point, current.end) if which == "start" else (current.start, point)
    try:
        new[gid] = geom2d.with_ends(current, start, end)
    except ValueError as e:
        raise OpError(f"parede {gid}: {e}") from e


def move_wall_end(doc: Document, wall, end: str, point, carry: bool = True) -> Transaction:
    """Alça de extremidade (spec/ui 02 §4.1): move o início (``end="start"``) ou o fim
    da parede para ``point``. Com ``carry``, as paredes com extremidade no mesmo ponto
    vão junto (a junção L se mantém)."""
    if end not in ("start", "end"):
        raise OpError(f"extremidade inválida: {end!r}")
    wall = doc.get(_gid(wall), "IfcWall")
    state = read_state(doc, wall)
    paths = _paths_of_storey(doc, state["storey"])
    path = paths[wall.GlobalId]
    node = path.start if end == "start" else path.end
    new: dict[str, geom2d.Path] = {}
    _set_end(paths, new, wall.GlobalId, end, point)
    if carry:
        for gid, which in _ends_at(paths, node, wall.GlobalId):
            _set_end(paths, new, gid, which, point)
    return _reshape(doc, "Mover extremidade de parede", new)


def _line(path: geom2d.LinePath) -> geom2d.StraightLine:
    return geom2d.line_through(path.start, path.end)


def _crossing(path, line: geom2d.StraightLine, fallback):
    """Cruzamento da reta de ``path`` com ``line``; ``fallback`` se ``path`` for arco ou
    paralela."""
    if not isinstance(path, geom2d.LinePath):
        return fallback
    found = geom2d.intersect(_line(path), line)
    return found[0] if found else fallback


def offset_wall(doc: Document, wall, distance: float, carry: bool = True) -> Transaction:
    """Alça de meio da parede reta (spec/ui 02 §4.2): desloca a parede ``distance`` para
    a esquerda (negativo: direita), paralela a si mesma. Com ``carry``, as vizinhas em L
    e em T esticam ou encurtam pela própria direção até a nova linha."""
    wall = doc.get(_gid(wall), "IfcWall")
    state = read_state(doc, wall)
    paths = _paths_of_storey(doc, state["storey"])
    path = paths[wall.GlobalId]
    if not isinstance(path, geom2d.LinePath):
        raise OpError("só a parede reta se desloca pela alça do meio")
    n = geom2d.frame(path).vector_to_global((0.0, 1.0))
    shift = geom2d.translation((n[0] * distance, n[1] * distance))
    if not carry:
        return _reshape(doc, "Deslocar parede", {wall.GlobalId: geom2d.mapped(path, shift)})
    line = geom2d.StraightLine(shift(path.start), _line(path).direction)
    new: dict[str, geom2d.Path] = {}
    ends = {}
    for which, node in (("start", path.start), ("end", path.end)):
        corner = None
        for gid, other_end in _ends_at(paths, node, wall.GlobalId):  # vizinhas em L
            q = _crossing(paths[gid], line, None)
            _set_end(paths, new, gid, other_end, q or shift(node))
            corner = corner or q
        if corner is None:  # esta parede chega em T numa parede reta?
            for gid, other in sorted(paths.items()):
                if (gid != wall.GlobalId and isinstance(other, geom2d.LinePath)
                        and _on_segment(node, other.start, other.end)):
                    corner = _crossing(other, line, None)
                    break
        ends[which] = corner or shift(node)
    for gid, other in sorted(paths.items()):  # vizinhas que chegam em T nesta parede
        if gid == wall.GlobalId or gid in new:
            continue
        for which, q in (("start", other.start), ("end", other.end)):
            if _on_segment(q, path.start, path.end):
                _set_end(paths, new, gid, which, _crossing(other, line, shift(q)))
    _set_end(paths, new, wall.GlobalId, "start", ends["start"])
    _set_end(paths, new, wall.GlobalId, "end", ends["end"])
    for gid, p in new.items():
        old = paths[gid]
        if isinstance(old, geom2d.LinePath) and math.cos(p.start_angle - old.start_angle) < 0:
            raise OpError(f"a parede {gid} ficaria invertida")
    return _reshape(doc, "Deslocar parede", new)


def bend_arc_wall(doc: Document, wall, through) -> Transaction:
    """Alça de meio da parede em arco (spec/ui 02 §4.3): o arco passa por ``through``."""
    wall = doc.get(_gid(wall), "IfcWall")
    path = geom2d.path_from_dict(read_state(doc, wall)["path"])
    if not isinstance(path, geom2d.ArcPath):
        raise OpError("só a parede em arco muda de curvatura")
    try:
        new = geom2d.arc_through(path.start, tuple(through), path.end)
    except ValueError as e:
        raise OpError(f"o ponto não forma um arco: {e}") from e
    return _reshape(doc, "Curvar parede", {wall.GlobalId: new})


def delete_wall(doc: Document, wall) -> Transaction:
    """Exclui a parede. A cascata (spec §6.4) entra nesta mesma transação, antes do
    ``wall.delete``: exclui as portas, as aberturas e as junções."""
    wall = doc.get(_gid(wall), "IfcWall")
    ops = []
    for opening in openings.of_wall(wall):
        ops += _opening_delete_ops(opening)
    ops += connections.sync_ops(doc, {wall.GlobalId: None})
    ops.append(Op("wall.delete", wall.GlobalId, data=read_state(doc, wall)))
    return Transaction("Excluir parede", ops)


# --- aberturas e preenchimentos (spec §6.3) ------------------------------------------


def create_opening(doc: Document, wall, distance: float, width: float, height: float,
                   sill: float = 0.0, kind: str = "OPENING", depth: float | None = None,
                   side: str = "left") -> Transaction:
    """Abertura (vão ou nicho) a ``distance`` do início da parede (spec §6.3)."""
    data = {
        "wall": doc.get(_gid(wall), "IfcWall").GlobalId,
        "kind": kind,
        "distance": float(distance),
        "width": float(width),
        "height": float(height),
        "sill": float(sill),
        "depth": None if depth is None else float(depth),
        "side": side,
    }
    openings.check_fits(doc, doc.get(data["wall"]), {**openings.default_state(), **data})
    label = "Criar nicho" if kind == "RECESS" else "Criar abertura"
    return Transaction(label, [Op("opening.create", guid.new(), data=data)])


def edit_opening(doc: Document, opening, **changes) -> Transaction:
    opening = doc.get(_gid(opening), "IfcOpeningElement")
    if changes.get("wall") is not None:
        changes["wall"] = _gid(changes["wall"])
    unknown = set(changes) - set(openings.STATE_KEYS)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    state = openings.read_state(opening)
    before = {k: state[k] for k in changes}
    after = {**state, **changes}
    openings.check_fits(doc, doc.get(after["wall"], "IfcWall"), after)
    return Transaction("Editar abertura", [Op("opening.edit", opening.GlobalId, before=before,
                                              after=dict(changes))])


def _opening_delete_ops(opening) -> list[Op]:
    """Exclui a abertura e as portas e janelas do BrasBim que a preenchem (porta §6.4).
    Outros elementos que preenchem (ex.: de outra origem) só são desligados."""
    from brasbim.core.fillings import commands as filling_cmd  # evita import circular
    from brasbim.core.fillings import doors

    ops = []
    for rel in opening.HasFillings:
        element = rel.RelatedBuildingElement
        filling = element.is_a("IfcDoor") or element.is_a("IfcWindow")
        if filling and doors.is_parametric(element):
            ops += filling_cmd.delete_ops(element)
        else:
            ops.append(Op("filling.detach", element.GlobalId,
                          data={"opening": opening.GlobalId}))
    ops.append(Op("opening.delete", opening.GlobalId, data=openings.read_state(opening)))
    return ops


def delete_opening(doc: Document, opening) -> Transaction:
    opening = doc.get(_gid(opening), "IfcOpeningElement")
    return Transaction("Excluir abertura", _opening_delete_ops(opening))


def attach_filling(doc: Document, opening, element) -> Transaction:
    """Liga uma porta ou janela à abertura (``IfcRelFillsElement``)."""
    data = {"opening": doc.get(_gid(opening), "IfcOpeningElement").GlobalId}
    return Transaction("Preencher abertura", [Op("filling.attach", _gid(element), data=data)])


def detach_filling(doc: Document, element) -> Transaction:
    element = doc.get(_gid(element), "IfcElement")
    ops = [Op("filling.detach", element.GlobalId,
              data={"opening": rel.RelatingOpeningElement.GlobalId})
           for rel in element.FillsVoids]
    return Transaction("Desligar preenchimento", ops)


# --- tipos e pavimentos (provisório) -------------------------------------------------


def create_wall_type(doc: Document, name: str, layers: list[dict], predefined_type="SOLIDWALL",
                     object_type: str | None = None,
                     plan_style: dict | None = None) -> Transaction:
    data = {"name": name, "predefined_type": predefined_type, "object_type": object_type,
            "layers": layers}
    if plan_style is not None:
        data["plan_style"] = plan_style
    return Transaction("Criar tipo de parede", [Op("wall_type.create", guid.new(), data=data)])


def edit_wall_type(doc: Document, wall_type, **changes) -> Transaction:
    state = wall_types.read(doc.get(_gid(wall_type), "IfcWallType"))
    before = {k: state[k] for k in changes}
    return Transaction(
        "Editar tipo de parede",
        [Op("wall_type.edit", _gid(wall_type), before=before, after=dict(changes))],
    )


def delete_wall_type(doc: Document, wall_type) -> Transaction:
    """Exclui um tipo de parede sem uso (spec/ui 02 §8)."""
    wall_type = doc.get(_gid(wall_type), "IfcWallType")
    used = ifcopenshell.util.element.get_types(wall_type)
    if used:
        raise OpError(f"o tipo {wall_type.Name} é usado por {len(used)} parede(s)")
    return Transaction("Excluir tipo de parede",
                       [Op("wall_type.delete", wall_type.GlobalId,
                           data=wall_types.read(wall_type))])


def create_storey(doc: Document, name: str, elevation: float) -> Transaction:
    data = {"name": name, "elevation": float(elevation)}
    return Transaction("Criar pavimento", [Op("storey.create", guid.new(), data=data)])


def edit_storey(doc: Document, storey, **changes) -> Transaction:
    storey = doc.get(_gid(storey), "IfcBuildingStorey")
    current = storeys.read(storey)
    cut = changes.get("cut_height")
    if cut is not None and abs(cut - storeys.DEFAULT_CUT_HEIGHT) < 1e-9:
        changes["cut_height"] = None  # o padrão não é gravado (spec/ui 06 §3.1)
    before = {k: current[k] for k in changes}
    return Transaction(
        "Editar pavimento", [Op("storey.edit", storey.GlobalId, before=before, after=changes)]
    )


def delete_storey(doc: Document, storey) -> Transaction:
    """Exclui um pavimento vazio (spec/ui 02 §7). Paredes com topo nele passam a altura
    fixa com a altura atual (parede §5.1), na mesma transação."""
    storey = doc.get(_gid(storey), "IfcBuildingStorey")
    if len(doc.storeys()) <= 1:
        raise OpError("o projeto precisa de pelo menos um pavimento")
    contained = ifcopenshell.util.element.get_contained(storey)
    if contained:
        raise OpError(f"o pavimento {storey.Name} contém {len(contained)} elemento(s)")
    ops = []
    for wall in sorted(doc.ifc.by_type("IfcWall"), key=lambda w: w.GlobalId):
        try:
            state = read_state(doc, wall)
        except OpError:
            continue
        if state["top_mode"] == "storey" and state["top_storey"] == storey.GlobalId:
            keys = ("top_mode", "top_storey", "fixed_height")
            ops.append(Op("wall.edit", wall.GlobalId, before={k: state[k] for k in keys},
                          after={"top_mode": "fixed", "top_storey": None,
                                 "fixed_height": rebuild.height(doc, state)}))
    ops.append(Op("storey.delete", storey.GlobalId, data=storeys.read(storey)))
    return Transaction("Excluir pavimento", ops)


# --- junções manuais (spec/ui 05 §7) -----------------------------------------------------


def _relations_between(wall_a, wall_b) -> list:
    return [r for r in connections.of_wall(wall_a)
            if wall_b in (r.RelatingElement, r.RelatedElement)]


def unjoin_walls(doc: Document, a, b) -> Transaction:
    """Desfaz a junção entre duas paredes e lembra a decisão (``no_join``): a detecção
    automática não a recria."""
    wall_a, wall_b = doc.get(_gid(a), "IfcWall"), doc.get(_gid(b), "IfcWall")
    rels = _relations_between(wall_a, wall_b)
    if not rels:
        raise OpError("as paredes não estão ligadas por uma junção")
    ops = [Op("path_connection.delete", r.GlobalId, data=connections.read(r)) for r in rels]
    for wall, other in ((wall_a, wall_b), (wall_b, wall_a)):
        current = read_state(doc, wall)["no_join"]
        ops.append(Op("wall.edit", wall.GlobalId, before={"no_join": current},
                      after={"no_join": sorted({*current, other.GlobalId})}))
    return Transaction("Desfazer junção", ops)


def join_walls(doc: Document, a, b) -> Transaction:
    """Une duas paredes retas (spec/ui 05 §7): cada uma estende ou encurta pela própria
    direção até o cruzamento dos caminhos; a que já passa pelo cruzamento fica (T)."""
    wall_a, wall_b = doc.get(_gid(a), "IfcWall"), doc.get(_gid(b), "IfcWall")
    states = {w.GlobalId: read_state(doc, w) for w in (wall_a, wall_b)}
    paths = {g: geom2d.path_from_dict(s["path"]) for g, s in states.items()}
    if not all(isinstance(p, geom2d.LinePath) for p in paths.values()):
        raise OpError("só paredes retas podem ser unidas")
    pa, pb = paths[wall_a.GlobalId], paths[wall_b.GlobalId]
    found = geom2d.intersect(_line(pa), _line(pb))
    if not found:
        raise OpError("as paredes são paralelas e não se cruzam")
    point = found[0]
    new = {}
    for gid, path in paths.items():
        if _on_segment(point, path.start, path.end):
            continue  # o cruzamento cai no meio desta parede: junção T
        which = "start" if math.dist(path.start, point) < math.dist(path.end, point) else "end"
        if math.dist(path.start if which == "start" else path.end, point) <= joins.TOL:
            continue
        _set_end(paths, new, gid, which, point)
        if math.cos(new[gid].start_angle - path.start_angle) < 0:
            raise OpError(f"a parede {gid} ficaria invertida")
    other = {wall_a.GlobalId: wall_b.GlobalId, wall_b.GlobalId: wall_a.GlobalId}
    extra = {g: {"no_join": [x for x in s["no_join"] if x != other[g]]}
             for g, s in states.items() if other[g] in s["no_join"]}
    if not new and not extra:
        if _relations_between(wall_a, wall_b):
            raise OpError("as paredes já estão unidas")
        raise OpError("as paredes já se cruzam")
    return _reshape(doc, "Unir paredes", new, extra)


def swap_continuous(doc: Document, a, b) -> Transaction:
    """Em X, a outra parede passa a ser a contínua (``RelatingElement``)."""
    wall_a, wall_b = doc.get(_gid(a), "IfcWall"), doc.get(_gid(b), "IfcWall")
    rels = [r for r in _relations_between(wall_a, wall_b)
            if r.RelatingConnectionType == "ATPATH" and r.RelatedConnectionType == "ATPATH"]
    if not rels:
        raise OpError("trocar a contínua só vale para paredes que se cruzam (junção em X)")
    rel = rels[0]
    data = connections.read(rel)
    swapped = {**data, "relating": data["related"], "related": data["relating"]}
    return Transaction("Trocar a contínua", [
        Op("path_connection.delete", rel.GlobalId, data=data),
        Op("path_connection.create", guid.new(), data=swapped)])
