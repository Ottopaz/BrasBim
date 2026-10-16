# SPDX-License-Identifier: LGPL-3.0-or-later
"""Mover, copiar e girar elementos (``spec/ui/02-edicao.md`` §6), sem Qt.

As transações usam só operações que já existem (spec/ui 02 §1): mover e girar viram
``wall.edit`` (caminho novo) e, para a porta sem a sua parede, ``opening.edit``; copiar
vira ``wall.create``, ``opening.create``, ``door.create`` e ``filling.attach``. As junções
são recalculadas por ``connections.sync_ops``. Pilares, vigas e lajes viram um
``*.edit`` (ou ``*.create``, ao copiar) cada, na mesma transação (spec/ui 10 §4.1).
"""

from __future__ import annotations

import copy
import math

import ifcopenshell.util.element

from brasbim.core import geom2d, guid
from brasbim.core.document import Document, OpError
from brasbim.core.fillings import commands as door_cmd
from brasbim.core.fillings import doors
from brasbim.core.ops import Op, Transaction
from brasbim.core.ops.history import combine
from brasbim.core.structure import commands as structure_cmd
from brasbim.core.structure import common as structure_common
from brasbim.core.structure import profiles, slab_openings, slabs
from brasbim.core.walls import connections, openings, rebuild, top
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
        if not (e.is_a("IfcDoor") or e.is_a("IfcWindow")):
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
        raise OpError(f"gire a parede que contém a {door_cmd.kind(lone[0]).noun}")
    _check_follows(walls)
    ops, changed = _wall_moves(doc, walls, fn)
    moved = {w.GlobalId for w in walls}
    for door in lone:
        wall, distance, _ = _lone_target(doc, door, fn, moved)
        ops += door_cmd.edit_door(doc, door, wall=wall, distance=distance).ops
    return Transaction(label, ops + connections.sync_ops(doc, changed))


def _move_elements_walls(doc: Document, gids, vector) -> Transaction:
    """Desloca paredes (com aberturas e portas) e portas pelo vetor (spec/ui 02 §6.1)."""
    return _transform(doc, gids, geom2d.translation(tuple(vector)), "Mover", True)


def _rotate_elements_walls(doc: Document, gids, center, angle: float) -> Transaction:
    """Gira paredes (com aberturas e portas) ``angle`` radianos, anti-horário, em torno
    de ``center`` (spec/ui 02 §6.3)."""
    return _transform(doc, gids, geom2d.rotation(tuple(center), angle), "Girar", False)


def _copy_door_ops(doc: Document, door, opening_data: dict) -> list[Op]:
    if not doors.is_parametric(door):
        raise OpError(f"a {door_cmd.kind(door).noun} {door.GlobalId} é de outra origem e "
                      "não pode ser copiada")
    opening_id, door_id = guid.new(), guid.new()
    state = copy.deepcopy(doors.read_state(door))
    return [Op("opening.create", opening_id, data=opening_data),
            Op(f"{door_cmd.kind(door).prefix}.create", door_id, data=state),
            Op("filling.attach", door_id, data={"opening": opening_id})]


def _copy_elements_walls(doc: Document, gids, vector) -> Transaction:
    """Cópia deslocada pelo vetor (spec/ui 02 §6.2): ``GlobalId``s novos, mesmos tipos;
    a parede leva cópias das suas aberturas e portas."""
    fn = geom2d.translation(tuple(vector))
    walls, lone = _split(doc, gids)
    ops, new = [], {}
    opening_ops = []
    for wall in walls:
        state = copy.deepcopy(read_wall(doc, wall))
        state["path"] = geom2d.mapped(geom2d.path_from_dict(state["path"]), fn).to_dict()
        state["no_join"] = []
        gid = guid.new()
        ops.append(Op("wall.create", gid, data=state))
        new[gid] = state
        for opening in openings.of_wall(wall):
            data = {**openings.read_state(opening), "wall": gid}
            fillings = [r.RelatedBuildingElement for r in opening.HasFillings]
            if any(not (f.is_a("IfcDoor") or f.is_a("IfcWindow")) for f in fillings):
                raise OpError(f"a abertura {opening.GlobalId} tem preenchimento que não "
                              "pode ser copiado")
            if fillings:
                opening_ops += _copy_door_ops(doc, fillings[0], data)
            else:
                opening_ops.append(Op("opening.create", guid.new(), data=data))
    for door in lone:
        wall, distance, o = _lone_target(doc, door, fn, set())
        data = {**o, "wall": wall, "distance": distance}
        copied = _copy_door_ops(doc, door, data)  # recusa a de outra origem antes
        openings.check_fits(doc, doc.get(wall, "IfcWall"), data)
        opening_ops += copied
    ops += opening_ops
    return Transaction("Copiar", ops + connections.sync_ops(doc, new))


# --- espelhar (spec/ui 05 §2) ---------------------------------------------------------


def _mirrored(path: geom2d.Path, fn) -> geom2d.Path:
    """Caminho espelhado e com o sentido invertido: as camadas ficam do lado espelhado.
    (O espelho inverte o giro do arco; inverter o sentido o desfaz.)"""
    start, end = fn(path.end), fn(path.start)
    if isinstance(path, geom2d.LinePath):
        return geom2d.LinePath(start, end)
    return geom2d.ArcPath(start, end, path.radius, path.ccw, path.large)


def _has_hand(doc: Document, door) -> bool:
    state = doors.read_state(door)
    if state["foreign"] is not None or not state["type"]:
        return False
    return door_cmd.hand(doc, door) is not None


def _mirror_elements_walls(doc: Document, gids, a, b, keep: bool = False) -> Transaction:
    """Imagem espelhada da seleção pelo eixo ``a``–``b``; com ``keep``, espelha uma cópia
    e mantém o original. Portas e janelas trocam a mão (variante)."""
    if math.dist(a, b) < geom2d.MIN_LENGTH:
        raise OpError("o eixo de simetria precisa de dois pontos distintos")
    fn = geom2d.reflection(tuple(a), tuple(b))
    walls, lone = _split(doc, gids)
    if lone or not walls:
        noun = door_cmd.kind(lone[0]).noun if lone else "porta"
        raise OpError(f"espelhe a parede que contém a {noun}")
    door_list = []
    for wall in walls:
        for opening in openings.of_wall(wall):
            for rel in opening.HasFillings:
                element = rel.RelatedBuildingElement
                filling = element.is_a("IfcDoor") or element.is_a("IfcWindow")
                if not filling or not doors.is_parametric(element):
                    raise OpError(f"o elemento {element.GlobalId}, de outra origem, não pode "
                                  "ser espelhado")
                door_list.append(element)
    ops, changed, new_doors = [], {}, []
    opening_ops = []
    for wall in walls:
        state = read_wall(doc, wall)
        path = geom2d.path_from_dict(state["path"])
        mirrored = _mirrored(path, fn)
        gid = guid.new() if keep else wall.GlobalId
        future = {**copy.deepcopy(state), "path": mirrored.to_dict()}
        changes = {"path": mirrored.to_dict()}
        if state["top_profile"]:  # o caminho é percorrido ao contrário
            changes["top_profile"] = top.reversed_profile(state["top_profile"], path.length)
            future["top_profile"] = changes["top_profile"]
        if keep:
            future["no_join"] = []
            ops.append(Op("wall.create", gid, data=future))
        else:
            ops.append(Op("wall.edit", gid, before={k: state[k] for k in changes},
                          after=changes))
        changed[gid] = future
        for opening in openings.of_wall(wall):
            o = openings.read_state(opening)
            distance = path.length - o["distance"] - o["width"]
            if keep:
                data = {**o, "wall": gid, "distance": distance}
                fillings = [r.RelatedBuildingElement for r in opening.HasFillings]
                if fillings:
                    door_ops = _copy_door_ops(doc, fillings[0], data)
                    opening_ops += door_ops
                    if _has_hand(doc, fillings[0]):
                        new_doors.append(door_ops[1].id)
                else:
                    opening_ops.append(Op("opening.create", guid.new(), data=data))
            elif abs(distance - o["distance"]) > 1e-9:
                opening_ops.append(Op("opening.edit", opening.GlobalId,
                                      before={"distance": o["distance"]},
                                      after={"distance": distance}))
    base = Transaction("", ops + opening_ops + connections.sync_ops(doc, changed))
    flips = new_doors if keep else [d.GlobalId for d in door_list if _has_hand(doc, d)]
    return combine(doc, "Espelhar cópia" if keep else "Espelhar",
                   [lambda: base, *[lambda d=d: door_cmd.flip_hinges(doc, d) for d in flips]])


# --- pilar, viga e laje (spec/ui 10 §4.1) ------------------------------------------------


def _structure(doc: Document, gids) -> tuple[list, list, list]:
    """(GlobalIds dos outros elementos, pilares/vigas/lajes, aberturas na laje sem a laje
    na seleção), na ordem da seleção. A laje leva as aberturas dela (spec/ui 12 §3.2)."""
    rest, found, openings = [], [], []
    for g in dict.fromkeys(gids):
        e = doc.get(g if isinstance(g, str) else g.GlobalId)
        if slab_openings.is_slab_opening(e):
            openings.append(e)
        else:
            (found if structure_cmd.is_structure(e) else rest).append(e.GlobalId)
    lone = [o for o in openings if slab_openings.host(o).GlobalId not in found]
    return rest, [doc.get(g) for g in found], lone


def _opening_ops(doc: Document, elements, fn, lone=()) -> list[Op]:
    """Aberturas das lajes transformadas (e as soltas) levadas por ``fn``."""
    ops = []
    slabs_ = [e for e in elements if e.is_a("IfcSlab")]
    for opening in [o for s in slabs_ for o in slab_openings.of_slab(s)] + list(lone):
        state = slab_openings.read_state(opening)
        new = slabs.clean([fn(p) for p in state["outline"]])
        ops.append(Op("slab_opening.edit", opening.GlobalId,
                      before={"outline": state["outline"]}, after={"outline": new}))
    return ops


def _check_lone(doc: Document, lone, fn) -> None:
    """A abertura movida sozinha continua dentro da laje dela."""
    for opening in lone:
        state = slab_openings.read_state(opening)
        slab_openings.check(doc, {**state, "outline": [fn(p) for p in state["outline"]]})


def _foreign_placement(doc: Document, element, state: dict, fn, angle: float) -> dict:
    if not structure_common.relative_to_storey(element, doc.get(state["storey"])):
        raise OpError(f"{element.is_a()} {element.GlobalId}, de outra origem, não está "
                      "posicionado em relação ao pavimento")
    return structure_common.placement_moved(state["placement"], fn, angle)


def _moved_state(doc: Document, element, fn, angle: float) -> dict:
    """Campos do estado levados por ``fn`` (translação ou rotação de ``angle`` rad)."""
    state = structure_cmd.read_state(doc, element)
    if state["foreign"] is not None:
        return {"placement": _foreign_placement(doc, element, state, fn, angle)}
    if element.is_a("IfcColumn"):
        return {"point": list(fn(state["point"])),
                "angle": (state["angle"] + math.degrees(angle) + 180.0) % 360.0 - 180.0}
    if element.is_a("IfcBeam"):
        return {"start": list(fn(state["start"])), "end": list(fn(state["end"]))}
    return {"outline": [list(fn(p)) for p in state["outline"]]}


def _mirrored_state(doc: Document, element, fn, a, b) -> dict:
    state = structure_cmd.read_state(doc, element)
    if state["foreign"] is not None:
        raise OpError(f"{element.is_a()} {element.GlobalId}, de outra origem, não pode ser "
                      "espelhado")
    if element.is_a("IfcColumn"):
        axis = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        angle = (2 * axis - state["angle"] + 180.0) % 360.0 - 180.0
        return {"point": list(fn(state["point"])), "angle": angle,
                "cardinal": profiles.mirrored_cardinal(state["cardinal"])}
    if element.is_a("IfcBeam"):
        swap = {"left_face": "right_face", "right_face": "left_face", "axis": "axis"}
        return {"start": list(fn(state["start"])), "end": list(fn(state["end"])),
                "ref_line": swap[state["ref_line"]]}
    return {"outline": [list(fn(p)) for p in state["outline"]]}


def _edit_ops(doc: Document, elements, changes_of) -> list[Op]:
    return [op for e in elements
            for op in structure_cmd.edit_element(doc, e, **changes_of(e)).ops]


def _copy_ops(doc: Document, elements, changes_of, fn=None, lone=()) -> list[Op]:
    """Cópias com GlobalIds novos e os próximos nomes livres (P…, V…); a laje leva cópias
    das aberturas, e a abertura sozinha é copiada na mesma laje."""
    ops, taken = [], {"IfcColumn": set(), "IfcBeam": set()}
    for opening in lone:
        state = slab_openings.read_state(opening)
        data = {**state, "outline": slab_openings.check(
            doc, {**state, "outline": [fn(p) for p in state["outline"]]})}
        ops.append(Op("slab_opening.create", guid.new(), data=data))
    for e in elements:
        module, prefix, _, _ = structure_cmd.ELEMENTS[e.is_a()]
        state = copy.deepcopy(module.read_state(doc, e))
        changes = changes_of(e)
        if "outline" in changes:
            changes["outline"] = slabs.clean(changes["outline"])
        state.update(changes)
        if e.is_a() in taken and state["foreign"] is None:
            letter = "P" if e.is_a("IfcColumn") else "V"
            used = {x.Name for x in doc.ifc.by_type(e.is_a())} | taken[e.is_a()]
            n = 1
            while f"{letter}{n}" in used:
                n += 1
            state["name"] = f"{letter}{n}"
            taken[e.is_a()].add(state["name"])
        new = guid.new()
        ops.append(Op(f"{prefix}.create", new, data=state))
        if e.is_a("IfcSlab"):
            for opening in slab_openings.of_slab(e):
                outline = slab_openings.read_state(opening)["outline"]
                ops.append(Op("slab_opening.create", guid.new(), data={
                    "slab": new, "outline": slabs.clean([fn(p) for p in outline])}))
    return ops


def _join(doc: Document, label: str, rest, walls_tx, structure_ops: list[Op]) -> Transaction:
    ops = walls_tx().ops if rest else []
    if not rest and not structure_ops:
        raise OpError("nada selecionado")
    return Transaction(label, ops + structure_ops)


def _no_lone(lone) -> None:
    if lone:
        raise OpError("gire ou espelhe a laje que contém a abertura")


def _move_elements_core(doc: Document, gids, vector) -> Transaction:
    """Desloca paredes (com aberturas e portas), portas, pilares, vigas, lajes (com as
    aberturas) e aberturas na laje pelo vetor (spec/ui 02 §6.1)."""
    rest, structure, lone = _structure(doc, gids)
    fn = geom2d.translation(tuple(vector))
    _check_lone(doc, lone, fn)
    ops = (_edit_ops(doc, structure, lambda e: _moved_state(doc, e, fn, 0.0))
           + _opening_ops(doc, structure, fn, lone))
    return _join(doc, "Mover", rest, lambda: _move_elements_walls(doc, rest, vector), ops)


def _rotate_elements_core(doc: Document, gids, center, angle: float) -> Transaction:
    """Gira a seleção ``angle`` radianos, anti-horário, em torno de ``center``
    (spec/ui 02 §6.3)."""
    rest, structure, lone = _structure(doc, gids)
    _no_lone(lone)
    fn = geom2d.rotation(tuple(center), angle)
    ops = (_edit_ops(doc, structure, lambda e: _moved_state(doc, e, fn, angle))
           + _opening_ops(doc, structure, fn))
    return _join(doc, "Girar", rest,
                 lambda: _rotate_elements_walls(doc, rest, center, angle), ops)


def _copy_elements_core(doc: Document, gids, vector) -> Transaction:
    """Cópia deslocada pelo vetor (spec/ui 02 §6.2)."""
    rest, structure, lone = _structure(doc, gids)
    fn = geom2d.translation(tuple(vector))
    ops = _copy_ops(doc, structure, lambda e: _moved_state(doc, e, fn, 0.0), fn, lone)
    return _join(doc, "Copiar", rest, lambda: _copy_elements_walls(doc, rest, vector), ops)


def _mirror_elements_core(doc: Document, gids, a, b, keep: bool = False) -> Transaction:
    """Imagem espelhada da seleção pelo eixo ``a``–``b`` (spec/ui 05 §2); com ``keep``,
    espelha uma cópia e mantém o original."""
    if math.dist(a, b) < geom2d.MIN_LENGTH:
        raise OpError("o eixo de simetria precisa de dois pontos distintos")
    rest, structure, lone = _structure(doc, gids)
    _no_lone(lone)
    fn = geom2d.reflection(tuple(a), tuple(b))
    changes = lambda e: _mirrored_state(doc, e, fn, a, b)
    ops = (_copy_ops(doc, structure, changes, fn) if keep
           else _edit_ops(doc, structure, changes) + _opening_ops(doc, structure, fn))
    label = "Espelhar cópia" if keep else "Espelhar"
    if not rest:
        return _join(doc, label, rest, None, ops)
    # As portas trocam de mão numa transação montada por ``combine``: os elementos
    # estruturais entram depois dela, sem depender do que ela cria.
    tx = _mirror_elements_walls(doc, rest, a, b, keep)
    return Transaction(label, tx.ops + ops)


# --- ambientes e anotações (spec/ui 13 §6) -----------------------------------------------


def _annotations(doc: Document, gids) -> tuple[list[str], list]:
    """(GlobalIds dos outros elementos, ambientes e anotações)."""
    from brasbim.core.annotations import commands as anno_cmd

    others, annos = [], []
    for g in dict.fromkeys(gids):
        e = doc.get(g if isinstance(g, str) else g.GlobalId)
        (annos if anno_cmd.is_annotation(e) else others).append(
            e if anno_cmd.is_annotation(e) else e.GlobalId)
    return others, annos


def _anno_ops(doc: Document, annos, fn, turn, mirrored: bool, moving: set[str],
              copy_: bool = False) -> list[Op]:
    from brasbim.core.annotations import commands as anno_cmd

    ops = []
    for e in annos:
        changes = anno_cmd.mapped(doc, e, fn, turn, mirrored, moving)
        if copy_:
            state = {**copy.deepcopy(anno_cmd.read_state(doc, e)), **changes}
            if anno_cmd.prefix_of(e) == "view":  # a cópia ganha letra e nome novos
                from brasbim.core.drawings import views

                taken = {o.data.get("letter") for o in ops if o.op == "view.create"}
                letter = views.next_letter(doc)
                while letter in taken:
                    letter = chr(ord(letter[-1]) + 1) if letter[-1] < "Z" else letter + "A"
                state["letter"] = letter if state["kind"] == "section" else None
                state["name"] = (f"Corte {letter}" if state["kind"] == "section"
                                 else f"{state['name']} (cópia)")
            if e.is_a("IfcSpace"):  # a cópia ganha o próximo número livre
                state["outline"] = slabs.clean(state["outline"])
                storey = doc.get(state["storey"])
                used = {x.Name for x in ifcopenshell.util.element.get_decomposition(storey)
                        if x.is_a("IfcSpace")}
                used |= {o.data["number"] for o in ops if o.op == "space.create"}
                n = 1
                while f"{n:02d}" in used:
                    n += 1
                state["number"] = f"{n:02d}"
            ops.append(Op(f"{anno_cmd.prefix_of(e)}.create", guid.new(), data=state))
        else:
            ops += anno_cmd.edit_element(doc, e, **changes).ops
    return ops


def _with_annotations(label: str, doc: Document, gids, core, annos_ops) -> Transaction:
    others, annos = _annotations(doc, gids)
    extra = annos_ops(annos)
    if not others:
        if not extra:
            raise OpError("nada selecionado")
        return Transaction(label, extra)
    tx = core(others)
    return Transaction(tx.label, tx.ops + extra)


def _moving(doc: Document, gids) -> set[str]:
    return {g if isinstance(g, str) else g.GlobalId for g in gids}


def move_elements(doc: Document, gids, vector) -> Transaction:
    """Desloca a seleção pelo vetor (spec/ui 02 §6.1), com ambientes e anotações."""
    fn = geom2d.translation(tuple(vector))
    return _with_annotations(
        "Mover", doc, gids, lambda others: _move_elements_core(doc, others, vector),
        lambda annos: _anno_ops(doc, annos, fn, lambda a: a, False, _moving(doc, gids)))


def rotate_elements(doc: Document, gids, center, angle: float) -> Transaction:
    """Gira a seleção ``angle`` radianos, anti-horário, em torno de ``center``."""
    fn = geom2d.rotation(tuple(center), angle)
    deg = math.degrees(angle)
    return _with_annotations(
        "Girar", doc, gids, lambda others: _rotate_elements_core(doc, others, center, angle),
        lambda annos: _anno_ops(doc, annos, fn, lambda a: a + deg, False, _moving(doc, gids)))


def copy_elements(doc: Document, gids, vector) -> Transaction:
    """Cópia deslocada pelo vetor (spec/ui 02 §6.2); as cotas copiadas ficam soltas."""
    fn = geom2d.translation(tuple(vector))
    return _with_annotations(
        "Copiar", doc, gids, lambda others: _copy_elements_core(doc, others, vector),
        lambda annos: _anno_ops(doc, annos, fn, lambda a: a, False, set(), copy_=True))


def mirror_elements(doc: Document, gids, a, b, keep: bool = False) -> Transaction:
    """Imagem espelhada pelo eixo ``a``–``b``; com ``keep``, espelha uma cópia."""
    if math.dist(a, b) < geom2d.MIN_LENGTH:
        raise OpError("o eixo de simetria precisa de dois pontos distintos")
    fn = geom2d.reflection(tuple(a), tuple(b))
    axis = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    moving = set() if keep else _moving(doc, gids)
    return _with_annotations(
        "Espelhar cópia" if keep else "Espelhar", doc, gids,
        lambda others: _mirror_elements_core(doc, others, a, b, keep),
        lambda annos: _anno_ops(doc, annos, fn, lambda x: 2 * axis - x, True, moving,
                                copy_=keep))
