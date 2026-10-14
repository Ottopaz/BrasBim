# SPDX-License-Identifier: LGPL-3.0-or-later
"""Mover, copiar e girar elementos (``spec/ui/02-edicao.md`` §6), sem Qt.

As transações usam só operações que já existem (spec/ui 02 §1): mover e girar viram
``wall.edit`` (caminho novo) e, para a porta sem a sua parede, ``opening.edit``; copiar
vira ``wall.create``, ``opening.create``, ``door.create`` e ``filling.attach``. As junções
são recalculadas por ``connections.sync_ops``.
"""

from __future__ import annotations

import copy

from brasbim.core import geom2d, guid
from brasbim.core.document import Document, OpError
from brasbim.core.fillings import commands as door_cmd
from brasbim.core.fillings import doors
from brasbim.core.ops import Op, Transaction
from brasbim.core.walls import connections, openings, rebuild
from brasbim.core.walls.wall import read_state as read_wall

_TOL = 0.01  # folga para achar a parede sob o centro de uma porta deslocada


def _split(doc: Document, gids) -> tuple[list, list]:
    """(paredes, portas sem a sua parede na seleção); recusa outras classes."""
    elements = [doc.get(g if isinstance(g, str) else g.GlobalId) for g in dict.fromkeys(gids)]
    walls = [e for e in elements if e.is_a("IfcWall")]
    wall_ids = {w.GlobalId for w in walls}
    lone = []
    for e in elements:
        if e.is_a("IfcWall"):
            continue
        if not e.is_a("IfcDoor"):
            raise OpError(f"{e.is_a()} {e.GlobalId}: mover, copiar e girar ainda não "
                          "suportam esta classe")
        host = host_wall(e)
        if host is None or host.GlobalId not in wall_ids:
            lone.append(e)
    if not walls and not lone:
        raise OpError("nada selecionado")
    return walls, lone


def host_wall(door):
    opening = door_cmd.opening_of(door)
    return openings.host(opening) if opening is not None else None


def _check_follows(walls) -> None:
    """Porta de outra origem que não está posicionada em relação à abertura não
    acompanharia a parede (porta §6.6)."""
    for wall in walls:
        for opening in openings.of_wall(wall):
            for rel in opening.HasFillings:
                element = rel.RelatedBuildingElement
                if element.ObjectPlacement and (
                        element.ObjectPlacement.PlacementRelTo != opening.ObjectPlacement):
                    raise OpError(f"o elemento {element.GlobalId}, de outra origem, não "
                                  "acompanharia a parede")


def _bands(doc: Document, storey_id: str, exclude: set[str]) -> list:
    from brasbim.core import snap  # evita import circular

    storey = doc.get(storey_id, "IfcBuildingStorey")
    return [w for w in snap.wall_paths(doc, storey) if w.gid not in exclude]


def _lone_target(doc: Document, door, fn, exclude: set[str]) -> tuple[str, float, dict]:
    """Parede reta e distância para onde vai a porta sem a sua parede (como soltar a
    porta sobre outra parede, PO11). Devolve (parede, distância, estado da abertura)."""
    from brasbim.core import snap

    opening = door_cmd.opening_of(door)
    if opening is None:
        raise OpError(f"porta {door.GlobalId} não está numa abertura")
    o = openings.read_state(opening)
    wall = openings.host(opening)
    state = read_wall(doc, wall)
    band = rebuild.band(doc, state)
    center = band.frame.to_global((o["distance"] + o["width"] / 2,
                                   (band.ymin + band.ymax) / 2))
    hit = snap.wall_at(_bands(doc, state["storey"], exclude), fn(center), _TOL)
    if hit is None or not hit.wall.straight:
        raise OpError(f"não há parede reta no destino da porta {door.GlobalId}")
    return hit.wall.gid, hit.along - o["width"] / 2, o


def _wall_moves(doc: Document, walls, fn) -> tuple[list[Op], dict]:
    ops, changed = [], {}
    for wall in walls:
        state = read_wall(doc, wall)
        path = geom2d.mapped(geom2d.path_from_dict(state["path"]), fn)
        ops.append(Op("wall.edit", wall.GlobalId, before={"path": state["path"]},
                      after={"path": path.to_dict()}))
        changed[wall.GlobalId] = {**state, "path": path.to_dict()}
    return ops, changed


def _transform(doc: Document, gids, fn, label: str, lone_allowed: bool) -> Transaction:
    walls, lone = _split(doc, gids)
    if lone and not lone_allowed:
        raise OpError("gire a parede que contém a porta")
    _check_follows(walls)
    ops, changed = _wall_moves(doc, walls, fn)
    moved = {w.GlobalId for w in walls}
    for door in lone:
        wall, distance, _ = _lone_target(doc, door, fn, moved)
        ops += door_cmd.edit_door(doc, door, wall=wall, distance=distance).ops
    return Transaction(label, ops + connections.sync_ops(doc, changed))


def move_elements(doc: Document, gids, vector) -> Transaction:
    """Desloca paredes (com aberturas e portas) e portas pelo vetor (spec/ui 02 §6.1)."""
    return _transform(doc, gids, geom2d.translation(tuple(vector)), "Mover", True)


def rotate_elements(doc: Document, gids, center, angle: float) -> Transaction:
    """Gira paredes (com aberturas e portas) ``angle`` radianos, anti-horário, em torno
    de ``center`` (spec/ui 02 §6.3)."""
    return _transform(doc, gids, geom2d.rotation(tuple(center), angle), "Girar", False)


def _copy_door_ops(doc: Document, door, opening_data: dict) -> list[Op]:
    if not doors.is_parametric(door):
        raise OpError(f"a porta {door.GlobalId} é de outra origem e não pode ser copiada")
    opening_id, door_id = guid.new(), guid.new()
    state = copy.deepcopy(doors.read_state(door))
    return [Op("opening.create", opening_id, data=opening_data),
            Op("door.create", door_id, data=state),
            Op("filling.attach", door_id, data={"opening": opening_id})]


def copy_elements(doc: Document, gids, vector) -> Transaction:
    """Cópia deslocada pelo vetor (spec/ui 02 §6.2): ``GlobalId``s novos, mesmos tipos;
    a parede leva cópias das suas aberturas e portas."""
    fn = geom2d.translation(tuple(vector))
    walls, lone = _split(doc, gids)
    ops, new = [], {}
    opening_ops = []
    for wall in walls:
        state = copy.deepcopy(read_wall(doc, wall))
        state["path"] = geom2d.mapped(geom2d.path_from_dict(state["path"]), fn).to_dict()
        gid = guid.new()
        ops.append(Op("wall.create", gid, data=state))
        new[gid] = state
        for opening in openings.of_wall(wall):
            data = {**openings.read_state(opening), "wall": gid}
            fillings = [r.RelatedBuildingElement for r in opening.HasFillings]
            if any(not f.is_a("IfcDoor") for f in fillings):
                raise OpError(f"a abertura {opening.GlobalId} tem preenchimento que não "
                              "pode ser copiado")
            if fillings:
                opening_ops += _copy_door_ops(doc, fillings[0], data)
            else:
                opening_ops.append(Op("opening.create", guid.new(), data=data))
    for door in lone:
        wall, distance, o = _lone_target(doc, door, fn, set())
        data = {**o, "wall": wall, "distance": distance}
        openings.check_fits(doc, doc.get(wall, "IfcWall"), data)
        opening_ops += _copy_door_ops(doc, door, data)
    ops += opening_ops
    return Transaction("Copiar", ops + connections.sync_ops(doc, new))
