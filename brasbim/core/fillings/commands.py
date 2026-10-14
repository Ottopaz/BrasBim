# SPDX-License-Identifier: LGPL-3.0-or-later
"""Ações do usuário sobre portas, cada uma convertida em uma ``Transaction``.

Como nos comandos da parede, aqui só se lê o modelo para montar as operações de
``porta.md`` §5.2; quem altera o modelo é ``History.commit``.
"""

from __future__ import annotations

from brasbim.core import guid
from brasbim.core.document import Document, OpError
from brasbim.core.fillings import door_types, doors, params
from brasbim.core.ops import Op, Transaction
from brasbim.core.walls import commands as wall_cmd
from brasbim.core.walls import openings

# Campos da porta que pertencem à abertura (porta §3.1) → campo da abertura.
_OPENING_KEYS = {"wall": "wall", "distance": "distance", "width": "width", "height": "height",
                 "base": "sill"}


def _gid(obj) -> str:
    return obj if isinstance(obj, str) else obj.GlobalId


# --- tipos -------------------------------------------------------------------------


def create_door_type(doc: Document, name: str, operation_type: str = "SINGLE_SWING_LEFT",
                     **options) -> Transaction:
    """Tipo de porta. ``lining`` e ``defaults`` podem ser parciais (completam o padrão);
    sem ``panels``, as folhas vêm da operação, com a espessura ``panel_depth``."""
    data = door_types.default_state(operation_type)
    depth = options.pop("panel_depth", params.DEFAULT_PANEL_DEPTH)
    data["panels"] = params.default_panels(operation_type, depth)
    for key in ("lining", "defaults", "materials"):
        data[key].update(options.pop(key, {}))
    unknown = set(options) - set(door_types.STATE_KEYS) - {"predefined_type"}
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    data.update(options, name=name)
    door_types.validate(data)
    return Transaction("Criar tipo de porta", [Op("door_type.create", guid.new(), data=data)])


def edit_door_type(doc: Document, door_type, **changes) -> Transaction:
    state = door_types.read(doc.get(_gid(door_type), "IfcDoorType"))
    unknown = set(changes) - set(door_types.STATE_KEYS)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    door_types.validate({**state, **changes})
    before = {k: state[k] for k in changes}
    return Transaction("Editar tipo de porta",
                       [Op("door_type.edit", _gid(door_type), before=before, after=changes)])


def delete_door_type(doc: Document, door_type) -> Transaction:
    """Exclui um tipo sem portas (porta §6.4)."""
    door_type = doc.get(_gid(door_type), "IfcDoorType")
    return Transaction("Excluir tipo de porta", [
        Op("door_type.delete", door_type.GlobalId, data=door_types.read(door_type))])


# --- portas ------------------------------------------------------------------------


def create_door(doc: Document, door_type, wall, distance: float, width: float | None = None,
                height: float | None = None, base: float | None = None, **options) -> Transaction:
    """Porta num vão novo da parede, a ``distance`` do início dela (porta §4).

    Sem ``width``/``height``/``base``, valem as dimensões padrão do tipo. ``options``:
    ``opens_to``, ``align``, ``offset``, ``name``, ``common``.
    """
    door_type = doc.get(_gid(door_type), "IfcDoorType")
    defaults = door_types.read(door_type)["defaults"]
    opening_tx = wall_cmd.create_opening(
        doc, wall, distance,
        defaults["width"] if width is None else width,
        defaults["height"] if height is None else height,
        sill=defaults["base"] if base is None else base)
    unknown = set(options) - set(doors.STATE_KEYS)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    data = {**doors.default_state(), **options, "type": door_type.GlobalId}
    if data["opens_to"] not in params.OPENS_TO or data["align"] not in params.ALIGNS:
        raise OpError("sentido de abertura ou alinhamento inválido")
    opening_id, door_id = opening_tx.ops[0].id, guid.new()
    return Transaction("Criar porta", [
        *opening_tx.ops,
        Op("door.create", door_id, data=data),
        Op("filling.attach", door_id, data={"opening": opening_id}),
    ])


def opening_of(door):
    rels = door.FillsVoids
    return rels[0].RelatingOpeningElement if rels else None


def edit_door(doc: Document, door, **changes) -> Transaction:
    """Altera a porta. ``wall``, ``distance``, ``width``, ``height`` e ``base`` mudam a
    abertura (``opening.edit``); os demais, a porta (``door.edit``)."""
    door = doc.get(_gid(door), "IfcDoor")
    ops = []
    opening_changes = {_OPENING_KEYS[k]: changes.pop(k) for k in list(changes)
                       if k in _OPENING_KEYS}
    if opening_changes:
        opening = opening_of(door)
        if opening is None:
            raise OpError(f"porta {door.GlobalId} não está numa abertura")
        ops += wall_cmd.edit_opening(doc, opening, **opening_changes).ops
    if changes.get("type") is not None:
        changes["type"] = doc.get(_gid(changes["type"]), "IfcDoorType").GlobalId
    unknown = set(changes) - set(doors.STATE_KEYS)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    if changes:
        state = doors.read_state(door)
        before = {k: state[k] for k in changes}
        ops.append(Op("door.edit", door.GlobalId, before=before, after=changes))
    return Transaction("Editar porta", ops)


def delete_ops(door) -> list[Op]:
    """Desliga a porta da abertura e exclui a porta (sem a abertura)."""
    ops = [Op("filling.detach", door.GlobalId,
              data={"opening": rel.RelatingOpeningElement.GlobalId}) for rel in door.FillsVoids]
    ops.append(Op("door.delete", door.GlobalId, data=doors.read_state(door)))
    return ops


def delete_door(doc: Document, door, keep_opening: bool = False) -> Transaction:
    """Exclui a porta e a abertura dela (porta §6.4); ``keep_opening`` mantém o vão."""
    door = doc.get(_gid(door), "IfcDoor")
    opening = opening_of(door)
    ops = delete_ops(door)
    label = "Remover porta e manter vão" if keep_opening else "Excluir porta"
    if opening is not None and not keep_opening:
        ops.append(Op("opening.delete", opening.GlobalId, data=openings.read_state(opening)))
    return Transaction(label, ops)
