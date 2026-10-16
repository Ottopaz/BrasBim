# SPDX-License-Identifier: LGPL-3.0-or-later
"""Ocorrência de pilar (``IfcColumn``), ``pilar.md`` §3.1 e §5.2.

Operações: ``column.create`` / ``column.delete`` (data: estado completo) e
``column.edit`` (before/after: campos de ``STATE_KEYS`` alterados).

Estado::

    {"name": "P1", "type": "<GlobalId do IfcColumnType>", "storey": "<GlobalId>",
     "point": [2.0, 3.0], "cardinal": 5, "angle": 0.0, "base_offset": 0.0,
     "top_mode": "storey", "top_storey": "<GlobalId>", "top_offset": 0.0,
     "fixed_height": 2.80, "common": {}, "foreign": None, "placement": None}

``point``: ponto de inserção no pavimento; ``cardinal``: ``CardinalPoint`` do
``IfcMaterialProfileSetUsage`` (``profiles``); ``angle`` em graus, anti-horário.
Posicionamento: origem no ponto de inserção, na cota da base, eixo x girado pelo ângulo.
O que é derivado (corpo, eixo, quantidades) fica em ``rebuild``.
"""

from __future__ import annotations

import math

import ifcopenshell.api.material
import ifcopenshell.api.root
import ifcopenshell.util.element

from brasbim.core import guid, props
from brasbim.core.document import Document, OpError, axis_placement, local_placement
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair
from brasbim.core.structure import common, profiles
from brasbim.core.structure import types as st_types

PSET = "BrasBim_Pilar"
COMMON_PSET = "Pset_ColumnCommon"
STATE_KEYS = ("name", "type", "storey", "point", "cardinal", "angle", "base_offset",
              "top_mode", "top_storey", "top_offset", "fixed_height", "common", "foreign",
              "placement")


def default_state() -> dict:
    return {"name": None, "cardinal": 5, "angle": 0.0, "base_offset": 0.0,
            "top_mode": "fixed", "top_storey": None, "top_offset": 0.0,
            "fixed_height": common.DEFAULT_TOP, "common": {}, "foreign": None,
            "placement": None}


def is_parametric(column) -> bool:
    return bool(ifcopenshell.util.element.get_pset(column, PSET, should_inherit=False))


# --- leitura -----------------------------------------------------------------------------


def _usage(column):
    usage = ifcopenshell.util.element.get_material(column, should_inherit=False)
    return usage if usage is not None and usage.is_a("IfcMaterialProfileSetUsage") else None


def read_state(doc: Document, column) -> dict:
    state = default_state()
    column_type = ifcopenshell.util.element.get_type(column)
    container = ifcopenshell.util.element.get_container(column)
    state.update(name=column.Name, type=column_type.GlobalId if column_type else None,
                 storey=container.GlobalId if container else None)
    placement = common.read_placement(column)
    if placement is not None:
        state["point"] = placement["location"][:2]
        ref = placement["ref"]
        state["angle"] = round(math.degrees(math.atan2(ref[1], ref[0])), 9)
    values = ifcopenshell.util.element.get_pset(column, PSET, should_inherit=False)
    foreign = not values
    if foreign:
        state["foreign"] = common.read_foreign(column)
        state["placement"] = placement
    else:
        usage = _usage(column)
        state["cardinal"] = int(usage.CardinalPoint or 5) if usage else 5
        state.update(base_offset=float(values["DeslocamentoBase"]),
                     top_mode=common.top_from_pset(values.get("TipoTopo")),
                     top_storey=values.get("PavimentoTopo"),
                     top_offset=float(values.get("DeslocamentoTopo") or 0.0),
                     fixed_height=float(values.get("AlturaFixa") or common.DEFAULT_TOP),
                     angle=round(math.degrees(float(values.get("Angulo") or 0.0)), 9))
    state["common"] = common.read_common(column, COMMON_PSET, column_type, foreign)
    return state


# --- cálculo -----------------------------------------------------------------------------


def height(doc: Document, state: dict) -> float:
    if state["top_mode"] == "fixed":
        return float(state["fixed_height"])
    z_top = common.elevation(doc, state["top_storey"]) + state["top_offset"]
    return z_top - (common.elevation(doc, state["storey"]) + state["base_offset"])


def section(doc: Document, state: dict) -> dict:
    return st_types.section(doc.get(state["type"], "IfcColumnType"))


def outline(doc: Document, state: dict, sec: dict | None = None) -> list[tuple[float, float]]:
    """Contorno da seção no pavimento (anti-horário); ``sec`` no lugar da do tipo."""
    sec = sec or section(doc, state)
    cx, cy = profiles.insertion(sec, state["cardinal"])
    a = math.radians(state["angle"])
    c, s = math.cos(a), math.sin(a)
    x0, y0 = state["point"]
    return [(x0 + c * (x - cx) - s * (y - cy), y0 + s * (x - cx) + c * (y - cy))
            for x, y in profiles.outline(sec)]


def center(doc: Document, state: dict) -> tuple[float, float]:
    """Centro da seção no pavimento."""
    cx, cy = profiles.insertion(section(doc, state), state["cardinal"])
    a = math.radians(state["angle"])
    c, s = math.cos(a), math.sin(a)
    return (state["point"][0] - c * cx + s * cy, state["point"][1] - s * cx - c * cy)


# --- gravação ----------------------------------------------------------------------------


def _validate(doc: Document, state: dict) -> None:
    if state["foreign"] is not None:
        return
    common.validate_top(state)
    if not 1 <= int(state["cardinal"]) <= 9:
        raise OpError(f"ponto de inserção inválido: {state['cardinal']}")
    if state["top_mode"] == "fixed" and state["fixed_height"] <= 0:
        raise OpError("altura fixa deve ser maior que zero")
    if section(doc, state)["shape"] == "circle" and state["cardinal"] != 5:
        raise OpError("o pilar circular só tem o centro como ponto de inserção")
    if height(doc, state) <= 0:
        raise OpError("o topo do pilar ficaria abaixo da base")


def _place(doc: Document, column, storey, state: dict) -> None:
    a = math.radians(state["angle"])
    direction = (math.cos(a), math.sin(a))
    placement = column.ObjectPlacement
    if placement is None:
        column.ObjectPlacement = local_placement(
            doc.ifc, storey.ObjectPlacement, state["base_offset"], state["point"], direction)
        return
    old = placement.RelativePlacement
    placement.PlacementRelTo = storey.ObjectPlacement
    placement.RelativePlacement = axis_placement(doc.ifc, state["point"],
                                                 state["base_offset"], direction)
    ifcopenshell.util.element.remove_deep2(doc.ifc, old)


def _assign_material(doc: Document, column, column_type, cardinal: int) -> None:
    pset = st_types.profile_set(column_type)
    usage = _usage(column)
    if usage is None or usage.ForProfileSet != pset:
        if ifcopenshell.util.element.get_material(column, should_inherit=False) is not None:
            ifcopenshell.api.material.unassign_material(doc.ifc, products=[column])
        usage = doc.ifc.createIfcMaterialProfileSetUsage(pset, int(cardinal), None)
        doc.ifc.create_entity("IfcRelAssociatesMaterial",
                              GlobalId=guid.derived(column.GlobalId, "material"),
                              RelatedObjects=[column], RelatingMaterial=usage)
    usage.CardinalPoint = int(cardinal)
    common.stamp_material(column)


def write_state(doc: Document, column, state: dict) -> None:
    _validate(doc, state)
    storey = doc.get(state["storey"], "IfcBuildingStorey")
    column_type = doc.find(state["type"]) if state["type"] else None
    column.Name = state["name"]
    if column_type is not None:
        common.assign_type(doc, column, column_type)
    common.assign_container(doc, column, storey)
    foreign = state["foreign"] is not None
    if foreign:
        common.write_foreign(doc, column, state)
    else:
        if state["top_mode"] == "storey":
            doc.get(state["top_storey"], "IfcBuildingStorey")
        _assign_material(doc, column, column_type, state["cardinal"])
        _place(doc, column, storey, state)
        f = doc.ifc
        props.write_pset(doc, column, PSET, {
            "PavimentoBase": f.createIfcIdentifier(state["storey"]),
            "DeslocamentoBase": f.createIfcLengthMeasure(float(state["base_offset"])),
            "TipoTopo": f.createIfcLabel(common.top_to_pset(state["top_mode"])),
            "PavimentoTopo": (f.createIfcIdentifier(state["top_storey"])
                              if state["top_mode"] == "storey" else None),
            "DeslocamentoTopo": f.createIfcLengthMeasure(float(state["top_offset"])),
            "AlturaFixa": f.createIfcPositiveLengthMeasure(float(state["fixed_height"])),
            "Angulo": f.createIfcPlaneAngleMeasure(math.radians(state["angle"])),
        })
    common.write_common(doc, column, COMMON_PSET, column_type, state["common"], foreign)


# --- operações ---------------------------------------------------------------------------


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    column = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcColumn")
    column.GlobalId = op.id
    try:
        write_state(doc, column, {**default_state(), **op.data})
    except Exception:
        common.remove(doc, column)
        raise
    return {op.id}


def _delete(doc: Document, op: Op) -> set[str]:
    common.remove(doc, doc.get(op.id, "IfcColumn"))
    return {op.id}


def _edit(doc: Document, op: Op) -> set[str]:
    column = doc.get(op.id, "IfcColumn")
    state = read_state(doc, column)
    check_before(op, state)
    unknown = set(op.after or {}) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"column.edit: campos desconhecidos {sorted(unknown)}")
    state.update(op.after or {})
    write_state(doc, column, state)
    return {op.id}


register_inverse_pair("column.create", _create, "column.delete", _delete)
register("column.edit", _edit, invert_swap)
