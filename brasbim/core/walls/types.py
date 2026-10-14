# SPDX-License-Identifier: LGPL-3.0-or-later
"""Tipos de parede (``IfcWallType`` + ``IfcMaterialLayerSet``), spec §2.1 e §2.3.

Operações: ``wall_type.create`` / ``wall_type.delete`` (data: estado completo) e
``wall_type.edit`` (before/after: name, layers). ``wall_type.create`` é provisória
(RF-TIP-01 ainda sem spec).

Estado de um tipo::

    {"name": "Alvenaria 14", "predefined_type": "SOLIDWALL", "object_type": None,
     "layers": [{"material": "Bloco cerâmico", "thickness": 0.09, "name": None,
                 "category": "LoadBearing", "priority": 80, "is_ventilated": False}]}
"""

from __future__ import annotations

import ifcopenshell.api.material
import ifcopenshell.api.root
import ifcopenshell.util.element

from brasbim.core import guid
from brasbim.core.document import Document, OpError
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair

PREDEFINED_TYPES = ("SOLIDWALL", "PARTITIONING", "PARAPET", "PLUMBINGWALL", "USERDEFINED")

_LAYER_DEFAULTS = {"name": None, "category": None, "priority": None, "is_ventilated": False}


def layer_set(wall_type):
    material = ifcopenshell.util.element.get_material(wall_type)
    if material is None or not material.is_a("IfcMaterialLayerSet"):
        raise OpError(f"tipo {wall_type.GlobalId} sem IfcMaterialLayerSet")
    return material


def thickness(wall_type) -> float:
    return sum(layer.LayerThickness for layer in layer_set(wall_type).MaterialLayers)


def read(wall_type) -> dict:
    layers = []
    for layer in layer_set(wall_type).MaterialLayers:
        layers.append(
            {
                "material": layer.Material.Name if layer.Material else None,
                "thickness": float(layer.LayerThickness),
                "name": layer.Name,
                "category": layer.Category,
                "priority": layer.Priority,
                "is_ventilated": layer.IsVentilated is True,
            }
        )
    return {
        "name": wall_type.Name,
        "predefined_type": wall_type.PredefinedType,
        "object_type": wall_type.ElementType,
        "layers": layers,
    }


def _validate(state: dict) -> None:
    if state["predefined_type"] not in PREDEFINED_TYPES:
        raise OpError(f"PredefinedType inválido: {state['predefined_type']!r}")
    if state["predefined_type"] == "USERDEFINED" and not state.get("object_type"):
        raise OpError("USERDEFINED exige object_type")
    if not state["layers"]:
        raise OpError("o tipo precisa de pelo menos uma camada")
    for layer in state["layers"]:
        if layer["thickness"] <= 0:
            raise OpError("espessura de camada deve ser maior que zero")
        p = layer.get("priority")
        if p is not None and not 0 <= p <= 100:
            raise OpError("prioridade da camada deve estar entre 0 e 100")


def _material(doc: Document, name: str):
    for m in doc.ifc.by_type("IfcMaterial"):
        if m.Name == name:
            return m
    return ifcopenshell.api.material.add_material(doc.ifc, name=name)


def _write_layers(doc: Document, lset, layers: list[dict]) -> None:
    for old in list(lset.MaterialLayers or []):
        ifcopenshell.api.material.remove_layer(doc.ifc, layer=old)
    for spec in layers:
        spec = {**_LAYER_DEFAULTS, **spec}
        layer = ifcopenshell.api.material.add_layer(
            doc.ifc, layer_set=lset, material=_material(doc, spec["material"])
        )
        layer.LayerThickness = float(spec["thickness"])
        layer.Name = spec["name"]
        layer.Category = spec["category"]
        layer.Priority = spec["priority"]
        layer.IsVentilated = bool(spec["is_ventilated"])


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    state = op.data
    _validate(state)
    wall_type = ifcopenshell.api.root.create_entity(
        doc.ifc, ifc_class="IfcWallType", predefined_type=state["predefined_type"],
        name=state["name"],
    )
    wall_type.GlobalId = op.id
    wall_type.ElementType = state.get("object_type")
    lset = ifcopenshell.api.material.add_material_set(
        doc.ifc, name=state["name"], set_type="IfcMaterialLayerSet"
    )
    _write_layers(doc, lset, state["layers"])
    rel = ifcopenshell.api.material.assign_material(
        doc.ifc, products=[wall_type], type="IfcMaterialLayerSet", material=lset
    )
    guid.stamp(rel, op.id, "material")
    return {op.id}


def _delete(doc: Document, op: Op) -> set[str]:
    wall_type = doc.get(op.id, "IfcWallType")
    if ifcopenshell.util.element.get_types(wall_type):
        raise OpError("o tipo está em uso por paredes")
    lset = layer_set(wall_type)
    ifcopenshell.api.root.remove_product(doc.ifc, product=wall_type)
    ifcopenshell.api.material.remove_material_set(doc.ifc, material=lset)
    return {op.id}


def _edit(doc: Document, op: Op) -> set[str]:
    wall_type = doc.get(op.id, "IfcWallType")
    state = read(wall_type)
    check_before(op, state)
    state.update(op.after or {})
    _validate(state)
    wall_type.Name = state["name"]
    lset = layer_set(wall_type)
    lset.LayerSetName = state["name"]
    if "layers" in (op.after or {}):
        _write_layers(doc, lset, state["layers"])
    return {op.id}


register_inverse_pair("wall_type.create", _create, "wall_type.delete", _delete)
register("wall_type.edit", _edit, invert_swap)
