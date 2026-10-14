# SPDX-License-Identifier: LGPL-3.0-or-later
"""Tipos de porta (``IfcDoorType``), ``spec/elementos/porta.md`` §2.1, §2.4, §2.5 e §3.2.

Operações: ``door_type.create`` / ``door_type.delete`` (data: estado completo) e
``door_type.edit`` (before/after: campos de ``STATE_KEYS``).

Estado de um tipo::

    {"name": "P1", "predefined_type": "DOOR", "operation_type": "SINGLE_SWING_LEFT",
     "lining": {"thickness": 0.03, "depth": None, "casing_thickness": 0.05,
                "casing_depth": 0.01, "threshold_thickness": None},
     "panels": [{"operation": "SWINGING", "position": "MIDDLE", "width": 1.0,
                 "depth": 0.035}],
     "materials": {"lining": "Madeira", "framing": None, "glazing": None},
     "defaults": {"width": 0.86, "height": 2.13, "base": 0.0},
     "variant": None}

Marco e folhas ficam em ``IfcDoorLiningProperties`` e ``IfcDoorPanelProperties``
(descontinuadas no IFC 4.3.2, mas as únicas que descrevem N folhas num tipo; porta §2.5).
``variant`` é o GlobalId do tipo com a outra mão (porta §2.2).
"""

from __future__ import annotations

import ifcopenshell.api.material
import ifcopenshell.api.root
import ifcopenshell.util.element

from brasbim.core import guid, props
from brasbim.core.document import Document, OpError
from brasbim.core.fillings import params
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair
from brasbim.core.walls.types import material_named

STATE_KEYS = ("name", "operation_type", "lining", "panels", "materials", "defaults", "variant")
# Constituintes do material (porta §2.4) e chaves do estado.
_CONSTITUENTS = {"lining": "Lining", "framing": "Framing", "glazing": "Glazing"}
_PREDEFINED = ("IfcDoorLiningProperties", "IfcDoorPanelProperties")


def default_state(operation_type: str = "SINGLE_SWING_LEFT") -> dict:
    return {
        "predefined_type": "DOOR",
        "operation_type": operation_type,
        "lining": dict(params.DEFAULT_LINING),
        "panels": (params.default_panels(operation_type)
                   if operation_type in params.DOOR_OPERATIONS else []),
        "materials": {"lining": "Madeira", "framing": None, "glazing": None},
        "defaults": dict(params.DEFAULT_DOOR_SIZE),
        "variant": None,
    }


# --- leitura -----------------------------------------------------------------


def _predefined(door_type, ifc_class: str) -> list:
    return [p for p in door_type.HasPropertySets or [] if p.is_a(ifc_class)]


def _num(value):
    return None if value is None else float(value)


def read(door_type) -> dict:
    state = default_state(door_type.OperationType or "NOTDEFINED")
    state["name"] = door_type.Name
    state["predefined_type"] = door_type.PredefinedType
    linings = _predefined(door_type, "IfcDoorLiningProperties")
    if linings:
        lp = linings[0]
        state["lining"] = {
            "thickness": _num(lp.LiningThickness),
            "depth": _num(lp.LiningDepth),
            "casing_thickness": _num(lp.CasingThickness),
            "casing_depth": _num(lp.CasingDepth),
            "threshold_thickness": _num(lp.ThresholdThickness),
        }
    panels = _predefined(door_type, "IfcDoorPanelProperties")  # na ordem gravada
    state["panels"] = [
        {"operation": p.PanelOperation, "position": p.PanelPosition,
         "width": float(p.PanelWidth) if p.PanelWidth is not None else 1.0,
         "depth": _num(p.PanelDepth)}
        for p in panels
    ]
    material = ifcopenshell.util.element.get_material(door_type)
    if material is not None and material.is_a("IfcMaterialConstituentSet"):
        names = {c.Name: c.Material.Name for c in material.MaterialConstituents or []}
        state["materials"] = {k: names.get(v) for k, v in _CONSTITUENTS.items()}
    values = ifcopenshell.util.element.get_pset(door_type, params.TYPE_PSET) or {}
    if values:
        state["defaults"] = {"width": float(values["LarguraPadrao"]),
                             "height": float(values["AlturaPadrao"]),
                             "base": float(values["BasePadrao"])}
        state["variant"] = values.get("Variante")
    return state


# --- validação -----------------------------------------------------------------


def validate(state: dict) -> None:
    if state["predefined_type"] not in params.DOOR_PREDEFINED_TYPES:
        raise OpError(f"PredefinedType de porta inválido: {state['predefined_type']!r}")
    layout = params.DOOR_OPERATIONS.get(state["operation_type"])
    if layout is None:
        raise OpError(f"operação de porta inválida: {state['operation_type']!r}")
    lining = state["lining"]
    if lining["thickness"] is None or lining["thickness"] < 0:
        raise OpError("espessura do marco deve ser maior ou igual a zero")
    if lining["depth"] is not None and lining["depth"] <= 0:
        raise OpError("profundidade do marco deve ser maior que zero")
    if (lining["casing_thickness"] is None) != (lining["casing_depth"] is None):
        raise OpError("guarnição exige largura e espessura (ou nenhuma das duas)")
    panels = state["panels"]
    if [(p["operation"], p["position"]) for p in panels] != layout:
        raise OpError(f"folhas não correspondem à operação {state['operation_type']}")
    for p in panels:
        if not p["depth"] or p["depth"] <= 0 or not 0 < p["width"] <= 1:
            raise OpError("folha com espessura ou proporção inválida")
    if panels and abs(sum(p["width"] for p in panels) - 1) > 1e-6:
        raise OpError("as proporções das folhas devem somar 1")
    d = state["defaults"]
    if d["width"] <= 0 or d["height"] <= 0:
        raise OpError("dimensões padrão devem ser maiores que zero")


# --- gravação ----------------------------------------------------------------


def _write_predefined(doc: Document, door_type, state: dict) -> None:
    """Refaz ``IfcDoorLiningProperties`` e ``IfcDoorPanelProperties`` do tipo."""
    ifc = doc.ifc
    old = [p for p in door_type.HasPropertySets or [] if p.is_a() in _PREDEFINED]
    keep = [p for p in door_type.HasPropertySets or [] if p.is_a() not in _PREDEFINED]
    door_type.HasPropertySets = keep or None
    for entity in old:
        ifc.remove(entity)
    lining = state["lining"]
    no_lining = lining["thickness"] == 0  # sem marco: os demais ficam vazios (IFC-DLP)
    new = [ifc.create_entity(
        "IfcDoorLiningProperties",
        GlobalId=guid.derived(door_type.GlobalId, "lining"),
        Name="Marco",
        LiningThickness=float(lining["thickness"]),
        LiningDepth=None if no_lining else _num(lining["depth"]),
        ThresholdThickness=None if no_lining else _num(lining["threshold_thickness"]),
        CasingThickness=None if no_lining else _num(lining["casing_thickness"]),
        CasingDepth=None if no_lining else _num(lining["casing_depth"]),
    )]
    for i, panel in enumerate(state["panels"]):
        new.append(ifc.create_entity(
            "IfcDoorPanelProperties",
            GlobalId=guid.derived(door_type.GlobalId, f"panel/{i}"),
            Name=f"Folha {i + 1}",
            PanelDepth=float(panel["depth"]),
            PanelOperation=panel["operation"],
            PanelWidth=float(panel["width"]),
            PanelPosition=panel["position"],
        ))
    door_type.HasPropertySets = new + keep


def _write_materials(doc: Document, door_type, materials: dict) -> None:
    cset = ifcopenshell.util.element.get_material(door_type)
    if cset is None:
        cset = ifcopenshell.api.material.add_material_set(
            doc.ifc, name=door_type.Name, set_type="IfcMaterialConstituentSet")
        rel = ifcopenshell.api.material.assign_material(
            doc.ifc, products=[door_type], type="IfcMaterialConstituentSet", material=cset)
        guid.stamp(rel, door_type.GlobalId, "material")
    for constituent in list(cset.MaterialConstituents or []):
        ifcopenshell.api.material.remove_constituent(doc.ifc, constituent=constituent)
    for key, name in _CONSTITUENTS.items():
        if materials.get(key):
            ifcopenshell.api.material.add_constituent(
                doc.ifc, constituent_set=cset, material=material_named(doc, materials[key]),
                name=name)


def write(doc: Document, door_type, state: dict) -> None:
    validate(state)
    door_type.Name = state["name"]
    door_type.PredefinedType = state["predefined_type"]
    door_type.OperationType = state["operation_type"]
    door_type.ParameterTakesPrecedence = True
    _write_predefined(doc, door_type, state)
    _write_materials(doc, door_type, state["materials"])
    d = state["defaults"]
    ifc = doc.ifc
    props.write_pset(doc, door_type, params.TYPE_PSET, {
        "LarguraPadrao": ifc.createIfcPositiveLengthMeasure(float(d["width"])),
        "AlturaPadrao": ifc.createIfcPositiveLengthMeasure(float(d["height"])),
        "BasePadrao": ifc.createIfcLengthMeasure(float(d["base"])),
        **({"Variante": ifc.createIfcIdentifier(state["variant"])} if state["variant"] else {}),
    })


# --- operações ---------------------------------------------------------------


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    state = {**default_state(op.data.get("operation_type", "SINGLE_SWING_LEFT")), **op.data}
    validate(state)
    door_type = ifcopenshell.api.root.create_entity(
        doc.ifc, ifc_class="IfcDoorType", predefined_type=state["predefined_type"],
        name=state["name"])
    door_type.GlobalId = op.id
    write(doc, door_type, state)
    return {op.id}


def _delete(doc: Document, op: Op) -> set[str]:
    door_type = doc.get(op.id, "IfcDoorType")
    if ifcopenshell.util.element.get_types(door_type):
        raise OpError("o tipo está em uso por portas")
    cset = ifcopenshell.util.element.get_material(door_type)
    for entity in [p for p in door_type.HasPropertySets or [] if p.is_a() in _PREDEFINED]:
        door_type.HasPropertySets = [p for p in door_type.HasPropertySets if p != entity] or None
        doc.ifc.remove(entity)
    ifcopenshell.api.root.remove_product(doc.ifc, product=door_type)
    if cset is not None:
        ifcopenshell.api.material.remove_material_set(doc.ifc, material=cset)
    return set()


def _edit(doc: Document, op: Op) -> set[str]:
    door_type = doc.get(op.id, "IfcDoorType")
    state = read(door_type)
    check_before(op, state)
    unknown = set(op.after or {}) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"door_type.edit: campos desconhecidos {sorted(unknown)}")
    state.update(op.after or {})
    write(doc, door_type, state)
    return {op.id}


register_inverse_pair("door_type.create", _create, "door_type.delete", _delete)
register("door_type.edit", _edit, invert_swap)
