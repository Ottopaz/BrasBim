# SPDX-License-Identifier: LGPL-3.0-or-later
"""Ocorrência de porta (``IfcDoor``), ``spec/elementos/porta.md`` §3.1 e §5.2.

Operações: ``door.create`` / ``door.delete`` (data: estado completo) e ``door.edit``
(before/after: campos de ``STATE_KEYS``).

Estado de uma porta::

    {"name": None, "type": "<GlobalId do IfcDoorType>", "opens_to": "left",
     "align": "axis", "offset": 0.0, "common": {}}

``opens_to``: face da parede para onde a folha abre; é lida do sentido do eixo x do
posicionamento (+x da parede = ``left``). ``align``/``offset``: Pset ``BrasBim_Esquadria``.
``common``: propriedades de ``Pset_DoorCommon`` diferentes do padrão.

Largura, altura, distância e base são da abertura (``opening.*``). Posição, dimensões
gravadas na porta, contenção, corpo e quantidades são derivados (``rebuild``).
"""

from __future__ import annotations

import ifcopenshell.api.root
import ifcopenshell.api.type
import ifcopenshell.util.element

from brasbim.core import guid, props
from brasbim.core.document import Document, OpError
from brasbim.core.fillings import params
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair

COMMON_PSET = "Pset_DoorCommon"
STATE_KEYS = ("name", "type", "opens_to", "align", "offset", "common")


def default_state() -> dict:
    return {"name": None, "opens_to": "left", "align": "axis", "offset": 0.0, "common": {}}


# --- leitura -----------------------------------------------------------------


def is_parametric(door) -> bool:
    """Porta gerada pelo BrasBim (tem o Pset próprio); as outras preservam o corpo."""
    return bool(ifcopenshell.util.element.get_pset(door, params.PSET, should_inherit=False))


def _common_defaults(door_type) -> dict:
    return {"Reference": door_type.Name, "Status": "NEW", "IsExternal": False}


def _read_common(door, door_type) -> dict:
    values = ifcopenshell.util.element.get_pset(door, COMMON_PSET, should_inherit=False) or {}
    values = {k: v for k, v in values.items() if k != "id"}
    if isinstance(values.get("Status"), (list, tuple)):
        values["Status"] = values["Status"][0] if values["Status"] else None
    defaults = _common_defaults(door_type) if door_type else {}
    return {k: v for k, v in values.items() if defaults.get(k) != v}


def read_state(door) -> dict:
    state = default_state()
    door_type = ifcopenshell.util.element.get_type(door)
    state["name"] = door.Name
    state["type"] = door_type.GlobalId if door_type else None
    rp = door.ObjectPlacement.RelativePlacement if door.ObjectPlacement else None
    if rp is not None and rp.RefDirection is not None and rp.RefDirection.DirectionRatios[0] < 0:
        state["opens_to"] = "right"
    values = ifcopenshell.util.element.get_pset(door, params.PSET, should_inherit=False)
    if values:
        state["align"] = params.align_from_pset(values["Alinhamento"])
        state["offset"] = float(values["Deslocamento"])
    state["common"] = _read_common(door, door_type)
    return state


# --- gravação ----------------------------------------------------------------


def _validate(state: dict) -> None:
    if state["opens_to"] not in params.OPENS_TO:
        raise OpError(f"sentido de abertura inválido: {state['opens_to']!r}")
    if state["align"] not in params.ALIGNS:
        raise OpError(f"alinhamento inválido: {state['align']!r}")


def _orient(doc: Document, door, opens_to: str) -> None:
    """Grava o sentido no eixo x do posicionamento; a origem é refeita pelo ``rebuild``."""
    ifc = doc.ifc
    placement = door.ObjectPlacement
    location = (0.0, 0.0, 0.0)
    if placement is not None:
        location = tuple(placement.RelativePlacement.Location.Coordinates)
    x = 1.0 if opens_to == "left" else -1.0
    relative = ifc.createIfcAxis2Placement3D(
        ifc.createIfcCartesianPoint(location), ifc.createIfcDirection((0.0, 0.0, 1.0)),
        ifc.createIfcDirection((x, 0.0, 0.0)))
    if placement is None:
        door.ObjectPlacement = ifc.createIfcLocalPlacement(None, relative)
        return
    old = placement.RelativePlacement
    placement.RelativePlacement = relative
    ifcopenshell.util.element.remove_deep2(ifc, old)


def write_state(doc: Document, door, state: dict) -> None:
    _validate(state)
    door_type = doc.get(state["type"], "IfcDoorType")
    door.Name = state["name"]
    door.PredefinedType = None
    door.OperationType = None
    if ifcopenshell.util.element.get_type(door) != door_type:
        rel = ifcopenshell.api.type.assign_type(
            doc.ifc, related_objects=[door], relating_type=door_type)
        guid.stamp(rel, door_type.GlobalId, "types")
    _orient(doc, door, state["opens_to"])
    props.write_pset(doc, door, params.PSET, {
        "Alinhamento": doc.ifc.createIfcLabel(params.align_to_pset(state["align"])),
        "Deslocamento": doc.ifc.createIfcLengthMeasure(float(state["offset"])),
    })
    common = {**_common_defaults(door_type), **(state.get("common") or {})}
    if common.get("Status") is not None:
        common["Status"] = [common["Status"]]
    props.write_pset(doc, door, COMMON_PSET, common)


# --- operações ---------------------------------------------------------------


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    door = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcDoor")
    door.GlobalId = op.id
    try:
        write_state(doc, door, {**default_state(), **op.data})
    except Exception:
        ifcopenshell.api.root.remove_product(doc.ifc, product=door)
        raise
    return {op.id}


def _delete(doc: Document, op: Op) -> set[str]:
    door = doc.get(op.id, "IfcDoor")
    if door.FillsVoids:
        raise OpError(f"porta {op.id} ainda preenche uma abertura")
    ifcopenshell.api.root.remove_product(doc.ifc, product=door)
    return set()


def _edit(doc: Document, op: Op) -> set[str]:
    door = doc.get(op.id, "IfcDoor")
    state = read_state(door)
    check_before(op, state)
    unknown = set(op.after or {}) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"door.edit: campos desconhecidos {sorted(unknown)}")
    state.update(op.after or {})
    write_state(doc, door, state)
    return {op.id}


register_inverse_pair("door.create", _create, "door.delete", _delete)
register("door.edit", _edit, invert_swap)
