# SPDX-License-Identifier: LGPL-3.0-or-later
"""Ações do usuário sobre paredes, cada uma convertida em uma ``Transaction``.

Os comandos só leem o modelo para montar as operações; quem altera o modelo é
``History.commit``. Assim, cada ação gera exatamente as operações de spec §5.2.
"""

from __future__ import annotations

import itertools

from brasbim.core import geom2d, guid
from brasbim.core.document import Document, OpError
from brasbim.core.ops import Op, Transaction
from brasbim.core.walls import connections, openings, params
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
              "fixed_height")


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
    """Exclui a abertura e as portas do BrasBim que a preenchem (porta §6.4). Outros
    elementos que preenchem (ex.: de outra origem) só são desligados."""
    from brasbim.core.fillings import commands as filling_cmd  # evita import circular
    from brasbim.core.fillings import doors

    ops = []
    for rel in opening.HasFillings:
        element = rel.RelatedBuildingElement
        if element.is_a("IfcDoor") and doors.is_parametric(element):
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
                     object_type: str | None = None) -> Transaction:
    data = {"name": name, "predefined_type": predefined_type, "object_type": object_type,
            "layers": layers}
    return Transaction("Criar tipo de parede", [Op("wall_type.create", guid.new(), data=data)])


def edit_wall_type(doc: Document, wall_type, **changes) -> Transaction:
    state = wall_types.read(doc.get(_gid(wall_type), "IfcWallType"))
    before = {k: state[k] for k in changes}
    return Transaction(
        "Editar tipo de parede",
        [Op("wall_type.edit", _gid(wall_type), before=before, after=dict(changes))],
    )


def create_storey(doc: Document, name: str, elevation: float) -> Transaction:
    data = {"name": name, "elevation": float(elevation)}
    return Transaction("Criar pavimento", [Op("storey.create", guid.new(), data=data)])


def edit_storey(doc: Document, storey, **changes) -> Transaction:
    storey = doc.get(_gid(storey), "IfcBuildingStorey")
    current = {"name": storey.Name, "elevation": float(storey.Elevation or 0.0)}
    before = {k: current[k] for k in changes}
    return Transaction(
        "Editar pavimento", [Op("storey.edit", storey.GlobalId, before=before, after=changes)]
    )
