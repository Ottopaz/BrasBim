# SPDX-License-Identifier: LGPL-3.0-or-later
"""Ocorrência de porta (``IfcDoor``) e de janela (``IfcWindow``),
``spec/elementos/porta.md`` §3.1 e §5.2 e ``janela.md`` §3.1 e §5.2.

Operações: ``door.create`` / ``door.delete`` (data: estado completo) e ``door.edit``
(before/after: campos de ``STATE_KEYS``); ``window.*`` iguais, para a janela. O que vale
para as duas fica escrito aqui uma vez só; o que muda é a classe, o Pset comum e o
conjunto de quantidades (``KINDS``). Na janela, ``foreign["operation_type"]`` guarda o
``PartitioningType`` da ocorrência.

Estado de uma porta::

    {"name": None, "type": "<GlobalId do IfcDoorType>", "opens_to": "left",
     "align": "axis", "offset": 0.0, "common": {}}

``opens_to``: face da parede para onde a folha abre; é lida do sentido do eixo x do
posicionamento (+x da parede = ``left``). ``align``/``offset``: Pset ``BrasBim_Esquadria``.
``common``: propriedades de ``Pset_DoorCommon`` diferentes do padrão.

Porta de outra origem (sem ``BrasBim_Esquadria``, §6.6): o corpo não é regenerado e
``common`` traz o Pset como está. ``foreign`` guarda o que o BrasBim não sabe refazer
(representações, posicionamento, dimensões, enumerações da ocorrência, quantidades e o
GlobalId da relação com o tipo), para que a conversão em porta paramétrica
(``door.edit`` com ``foreign`` → ``None``) possa ser desfeita sem perda. Nas portas do
BrasBim, ``foreign`` é ``None``.

Largura, altura, distância e base são da abertura (``opening.*``). Posição, dimensões
gravadas na porta, contenção, corpo e quantidades são derivados (``rebuild``).
"""

from __future__ import annotations

import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.type
import ifcopenshell.util.element

from brasbim.core import fragment, guid, props
from brasbim.core.document import Document, OpError
from brasbim.core.fillings import door_types, params, window_types
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair

COMMON_PSET = "Pset_DoorCommon"
# Classe → (classe do tipo, Pset comum, quantidades, prefixo das operações).
KINDS = {
    "IfcDoor": ("IfcDoorType", "Pset_DoorCommon", params.QTO, "door"),
    "IfcWindow": ("IfcWindowType", "Pset_WindowCommon", params.WINDOW_QTO, "window"),
}
STATE_KEYS = ("name", "type", "opens_to", "align", "offset", "common", "foreign")
# Quantidades que o BrasBim grava (porta §8); as demais, de outra origem, ficam intactas.
_QUANTITIES = ("Width", "Height", "Area", "Perimeter")


def default_state() -> dict:
    return {"name": None, "opens_to": "left", "align": "axis", "offset": 0.0, "common": {},
            "foreign": None}


# --- leitura -----------------------------------------------------------------


def kind_of(element) -> tuple[str, str, str, str, str]:
    """(classe, classe do tipo, Pset comum, quantidades, prefixo) da esquadria."""
    cls = "IfcWindow" if element.is_a("IfcWindow") else "IfcDoor"
    return (cls, *KINDS[cls])


def is_parametric(door) -> bool:
    """Porta gerada pelo BrasBim (tem o Pset próprio); as outras preservam o corpo."""
    return bool(ifcopenshell.util.element.get_pset(door, params.PSET, should_inherit=False))


def common_defaults(code: str) -> dict:
    """Padrão de ``Pset_DoorCommon``. ``Reference`` é o código do tipo
    (``door_types.code``), igual nas duas variantes de mão (porta §3.3)."""
    return {"Reference": code, "Status": "NEW", "IsExternal": False}


def type_common_defaults(element_type) -> dict:
    """Padrão do Pset comum da esquadria com esse tipo. Janela: ``Reference`` é o código
    do tipo e ``IsExternal`` é verdadeiro (janela §3.3)."""
    if element_type.is_a("IfcWindowType"):
        return {"Reference": window_types.code(window_types.read(element_type)),
                "Status": "NEW", "IsExternal": True}
    return common_defaults(door_types.code(door_types.read(element_type)))



def retag(doc, element_type, old: str, new: str) -> set[str]:
    """Código do tipo mudou: as esquadrias que usavam o código antigo (o padrão) passam
    a ter o novo no ``Reference``; as que tinham código próprio ficam. Devolve as que
    mudaram."""
    if old == new:
        return set()
    changed = set()
    for door in ifcopenshell.util.element.get_types(element_type):
        pset = kind_of(door)[2]
        values = ifcopenshell.util.element.get_pset(door, pset, should_inherit=False) or {}
        if values.get("Reference") == old:
            props.write_pset(doc, door, pset, {
                **{k: v for k, v in values.items() if k not in ("id", "Reference")},
                "Reference": new})
            changed.add(door.GlobalId)
    return changed

def _read_common(door, door_type) -> dict:
    """Pset comum sem o que é padrão do tipo (sem tipo: o Pset inteiro)."""
    pset = kind_of(door)[2]
    values = ifcopenshell.util.element.get_pset(door, pset, should_inherit=False) or {}
    values = {k: v for k, v in values.items() if k != "id"}
    if isinstance(values.get("Status"), (list, tuple)):
        values["Status"] = values["Status"][0] if values["Status"] else None
    defaults = type_common_defaults(door_type) if door_type else {}
    return {k: v for k, v in values.items() if defaults.get(k) != v}


def _read_foreign(door) -> dict:
    ifc = door.file
    placement = door.ObjectPlacement
    rel = next(iter(door.IsTypedBy), None)
    qto = ifcopenshell.util.element.get_pset(door, kind_of(door)[3], should_inherit=False)
    return {
        "shape": fragment.dump(ifc, door.Representation),
        "placement": None if placement is None else [
            fragment.dump(ifc, placement.PlacementRelTo),
            fragment.dump(ifc, placement.RelativePlacement)],
        "overall": [door.OverallWidth, door.OverallHeight],
        "predefined_type": door.PredefinedType,
        "operation_type": (door.PartitioningType if door.is_a("IfcWindow")
                           else door.OperationType),
        "object_type": door.ObjectType,
        "type_rel": rel.GlobalId if rel else None,
        "quantities": None if not qto else {k: qto.get(k) for k in _QUANTITIES},
    }


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
    else:
        state["common"] = _read_common(door, None)
        state["foreign"] = _read_foreign(door)
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


def _clear_shape(doc: Document, door) -> None:
    shape = door.Representation
    if shape is not None:
        door.Representation = None
        fragment.remove(doc.ifc, shape)


def _write_common(doc: Document, door, values: dict) -> None:
    values = dict(values)
    if values.get("Status") is not None:
        values["Status"] = [values["Status"]]
    pset = kind_of(door)[2]
    if values:
        props.write_pset(doc, door, pset, values)
    else:
        props.remove_pset(doc, door, pset)


def _restore_foreign(doc: Document, door, foreign: dict) -> None:
    """Desfaz a conversão: volta corpo, posição, dimensões e quantidades de origem."""
    ifc = doc.ifc
    props.remove_pset(doc, door, params.PSET)
    _clear_shape(doc, door)
    door.Representation = fragment.load(ifc, foreign["shape"])
    if foreign["placement"] is not None:
        placement = door.ObjectPlacement
        old = placement.RelativePlacement
        placement.PlacementRelTo = fragment.load(ifc, foreign["placement"][0])
        placement.RelativePlacement = fragment.load(ifc, foreign["placement"][1])
        ifcopenshell.util.element.remove_deep2(ifc, old)
    door.OverallWidth, door.OverallHeight = foreign["overall"]
    qto = kind_of(door)[3]
    if foreign["quantities"] is None:
        props.remove_pset(doc, door, qto)
    else:
        found = ifcopenshell.util.element.get_pset(door, qto, should_inherit=False)
        ifcopenshell.api.pset.edit_qto(ifc, qto=ifc.by_id(found["id"]),
                                       properties=foreign["quantities"])


def _write_foreign(doc: Document, door, state: dict) -> None:
    """Porta de outra origem: só nome, tipo e Psets; o corpo fica o gravado (§6.6)."""
    foreign = state["foreign"]
    if is_parametric(door):
        _restore_foreign(doc, door, foreign)
    door_type = doc.get(state["type"], kind_of(door)[1]) if state["type"] else None
    if ifcopenshell.util.element.get_type(door) != door_type:
        if door_type is None:
            ifcopenshell.api.type.unassign_type(doc.ifc, related_objects=[door])
        else:
            rel = ifcopenshell.api.type.assign_type(
                doc.ifc, related_objects=[door], relating_type=door_type,
                should_map_representations=False)
            if list(rel.RelatedObjects) == [door] and foreign["type_rel"]:
                rel.GlobalId = foreign["type_rel"]
    door.Name = state["name"]
    door.PredefinedType = foreign["predefined_type"]
    if door.is_a("IfcWindow"):
        door.PartitioningType = foreign["operation_type"]
    else:
        door.OperationType = foreign["operation_type"]
    door.ObjectType = foreign["object_type"]
    _write_common(doc, door, state.get("common") or {})


def write_state(doc: Document, door, state: dict) -> None:
    _validate(state)
    if state.get("foreign") is not None:
        _write_foreign(doc, door, state)
        return
    door_type = doc.get(state["type"], kind_of(door)[1])
    if not is_parametric(door):
        _clear_shape(doc, door)  # conversão de porta de outra origem: o corpo será gerado
    door.Name = state["name"]
    door.PredefinedType = None
    if door.is_a("IfcWindow"):
        door.PartitioningType = None
    else:
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
    _write_common(doc, door, {**type_common_defaults(door_type),
                              **(state.get("common") or {})})


# --- operações ---------------------------------------------------------------


def _create(doc: Document, op: Op, ifc_class: str = "IfcDoor") -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    if op.data.get("foreign") is not None:
        raise OpError(f"{op.op} não recria esquadria de outra origem")
    door = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class=ifc_class)
    door.GlobalId = op.id
    try:
        write_state(doc, door, {**default_state(), **op.data})
    except Exception:
        ifcopenshell.api.root.remove_product(doc.ifc, product=door)
        raise
    return {op.id}


def _delete(doc: Document, op: Op, ifc_class: str = "IfcDoor") -> set[str]:
    door = doc.get(op.id, ifc_class)
    if door.FillsVoids:
        raise OpError(f"esquadria {op.id} ainda preenche uma abertura")
    ifcopenshell.api.root.remove_product(doc.ifc, product=door)
    return set()


def _edit(doc: Document, op: Op, ifc_class: str = "IfcDoor") -> set[str]:
    door = doc.get(op.id, ifc_class)
    state = read_state(door)
    check_before(op, state)
    unknown = set(op.after or {}) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"{op.op}: campos desconhecidos {sorted(unknown)}")
    state.update(op.after or {})
    write_state(doc, door, state)
    return {op.id}


register_inverse_pair("door.create", _create, "door.delete", _delete)
register("door.edit", _edit, invert_swap)
register_inverse_pair("window.create", lambda doc, op: _create(doc, op, "IfcWindow"),
                      "window.delete", lambda doc, op: _delete(doc, op, "IfcWindow"))
register("window.edit", lambda doc, op: _edit(doc, op, "IfcWindow"), invert_swap)
