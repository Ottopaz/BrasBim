# SPDX-License-Identifier: LGPL-3.0-or-later
"""Tipos de pilar, viga e laje (``pilar.md`` §3.2, ``viga.md`` §3.2, ``laje.md`` §3.2).

Operações: ``column_type.*``, ``beam_type.*`` e ``slab_type.*``, com ``create`` /
``delete`` (data: estado completo) e ``edit`` (before/after: campos alterados).

Estado de um tipo de pilar ou de viga::

    {"name": "Pilar 20×40", "predefined_type": "COLUMN",
     "section": {"shape": "rect", "b": 0.20, "h": 0.40}, "material": "Concreto",
     "plan_style": None}

Gravação: ``IfcMaterialProfileSet`` com um ``IfcMaterialProfile`` (material + perfil); o
perfil é a mesma entidade nos corpos de todas as ocorrências (pilar.md §2.2). Mudar as
dimensões altera o perfil no lugar; mudar a forma troca o perfil.

Estado de um tipo de laje::

    {"name": "Laje maciça 10 cm", "predefined_type": "FLOOR",
     "layers": [{"material": "Concreto", "thickness": 0.10}], "plan_style": None}

``layers`` vem **de cima para baixo**, como a interface mostra; o ``IfcMaterialLayerSet``
grava na ordem inversa (camada 1 = a de baixo, laje.md §2.3).

``plan_style``: Pset ``BrasBim_RepresentacaoPlanta`` do tipo, como na parede.
"""

from __future__ import annotations

from dataclasses import dataclass

import ifcopenshell.api.material
import ifcopenshell.api.root
import ifcopenshell.util.element

from brasbim.core import guid
from brasbim.core.document import Document, OpError
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair
from brasbim.core.structure import profiles
from brasbim.core.walls import types as wall_types


@dataclass(frozen=True)
class ProfileKind:
    prefix: str  # das operações: column / beam
    type_class: str
    element_class: str
    predefined_types: tuple[str, ...]
    shapes: tuple[str, ...]
    noun: str
    plural: str


COLUMN = ProfileKind("column", "IfcColumnType", "IfcColumn", ("COLUMN",), profiles.SHAPES,
                     "pilar", "pilares")
BEAM = ProfileKind("beam", "IfcBeamType", "IfcBeam", ("BEAM",), ("rect",), "viga", "vigas")
PROFILE_KINDS = {k.prefix: k for k in (COLUMN, BEAM)}

SLAB_TYPES = ("FLOOR", "BASESLAB")


def profile_kind(entity) -> ProfileKind:
    """Pilar ou viga, pela ocorrência ou pelo tipo."""
    for k in (COLUMN, BEAM):
        if entity.is_a(k.type_class) or entity.is_a(k.element_class):
            return k
    raise OpError(f"{entity.is_a()} não é pilar nem viga")


def _material_set(element_type, ifc_class: str):
    material = ifcopenshell.util.element.get_material(element_type)
    if material is None or not material.is_a(ifc_class):
        raise OpError(f"tipo {element_type.GlobalId} sem {ifc_class}")
    return material


# --- pilar e viga ----------------------------------------------------------------------


def profile_set(element_type):
    return _material_set(element_type, "IfcMaterialProfileSet")


def material_profile(element_type):
    found = profile_set(element_type).MaterialProfiles or []
    if not found:
        raise OpError(f"tipo {element_type.GlobalId} sem IfcMaterialProfile")
    return found[0]


def profile(element_type):
    """``IfcProfileDef`` do tipo (compartilhado pelos corpos das ocorrências)."""
    return material_profile(element_type).Profile


def section(element_type) -> dict:
    found = profiles.read(profile(element_type))
    if found is None:
        raise OpError(f"tipo {element_type.GlobalId}: perfil {profile(element_type).is_a()} "
                      "não suportado")
    return found


def read_profile_type(element_type) -> dict:
    mp = material_profile(element_type)
    return {"name": element_type.Name, "predefined_type": element_type.PredefinedType,
            "section": section(element_type),
            "material": mp.Material.Name if mp.Material else None,
            "plan_style": wall_types.read_plan_style(element_type)}


def _validate_profile_type(k: ProfileKind, state: dict) -> None:
    if state["predefined_type"] not in k.predefined_types:
        raise OpError(f"PredefinedType inválido: {state['predefined_type']!r}")
    if not state.get("material"):
        raise OpError("o tipo precisa de um material")
    try:
        profiles.validate(state["section"], k.shapes)
    except (ValueError, KeyError) as e:
        raise OpError(str(e)) from e
    wall_types.validate_plan_style(state.get("plan_style"))


def _profile_create(k: ProfileKind):
    def apply(doc: Document, op: Op) -> set[str]:
        if doc.find(op.id) is not None:
            raise OpError(f"GlobalId {op.id} já existe")
        state = op.data
        _validate_profile_type(k, state)
        element_type = ifcopenshell.api.root.create_entity(
            doc.ifc, ifc_class=k.type_class, predefined_type=state["predefined_type"],
            name=state["name"])
        element_type.GlobalId = op.id
        pset = ifcopenshell.api.material.add_material_set(
            doc.ifc, name=state["name"], set_type="IfcMaterialProfileSet")
        ifcopenshell.api.material.add_profile(
            doc.ifc, profile_set=pset,
            material=wall_types.material_named(doc, state["material"]),
            profile=profiles.create(doc.ifc, state["section"], state["name"]))
        rel = ifcopenshell.api.material.assign_material(
            doc.ifc, products=[element_type], type="IfcMaterialProfileSet", material=pset)
        guid.stamp(rel, op.id, "material")
        wall_types.write_plan_style(doc, element_type, state.get("plan_style"))
        return {op.id}

    return apply


def _profile_delete(k: ProfileKind):
    def apply(doc: Document, op: Op) -> set[str]:
        element_type = doc.get(op.id, k.type_class)
        if ifcopenshell.util.element.get_types(element_type):
            raise OpError(f"o tipo está em uso por {k.plural}")
        pset = profile_set(element_type)
        old = [mp.Profile for mp in pset.MaterialProfiles or []]
        ifcopenshell.api.root.remove_product(doc.ifc, product=element_type)
        ifcopenshell.api.material.remove_material_set(doc.ifc, material=pset)
        for p in old:
            if p is not None and not doc.ifc.get_total_inverses(p):
                doc.ifc.remove(p)
        return {op.id}

    return apply


def _profile_edit(k: ProfileKind):
    def apply(doc: Document, op: Op) -> set[str]:
        element_type = doc.get(op.id, k.type_class)
        state = read_profile_type(element_type)
        check_before(op, state)
        after = op.after or {}
        state.update(after)
        _validate_profile_type(k, state)
        element_type.Name = state["name"]
        element_type.PredefinedType = state["predefined_type"]
        pset = profile_set(element_type)
        pset.Name = state["name"]
        mp = material_profile(element_type)
        mp.Profile.ProfileName = state["name"]
        if "material" in after:
            mp.Material = wall_types.material_named(doc, state["material"])
        if "section" in after and not profiles.update(mp.Profile, state["section"]):
            old = mp.Profile
            mp.Profile = profiles.create(doc.ifc, state["section"], state["name"])
            # Os corpos ainda apontam para o perfil antigo; ``rebuild`` refaz as
            # ocorrências e apaga o perfil que sobrar sem uso.
            doc.orphan_profiles.append(old)
        if "plan_style" in after:
            wall_types.write_plan_style(doc, element_type, state["plan_style"])
        return {op.id}

    return apply


for _k in (COLUMN, BEAM):
    register_inverse_pair(f"{_k.prefix}_type.create", _profile_create(_k),
                          f"{_k.prefix}_type.delete", _profile_delete(_k))
    register(f"{_k.prefix}_type.edit", _profile_edit(_k), invert_swap)


# --- laje ------------------------------------------------------------------------------


def layer_set(slab_type):
    return _material_set(slab_type, "IfcMaterialLayerSet")


def slab_thickness(slab_type) -> float:
    return sum(layer.LayerThickness for layer in layer_set(slab_type).MaterialLayers)


def read_slab_type(slab_type) -> dict:
    layers = [{"material": layer.Material.Name if layer.Material else None,
               "thickness": float(layer.LayerThickness)}
              for layer in reversed(layer_set(slab_type).MaterialLayers)]
    return {"name": slab_type.Name, "predefined_type": slab_type.PredefinedType,
            "layers": layers, "plan_style": wall_types.read_plan_style(slab_type)}


def _validate_slab_type(state: dict) -> None:
    if state["predefined_type"] not in SLAB_TYPES:
        raise OpError(f"PredefinedType inválido: {state['predefined_type']!r}")
    if not state["layers"]:
        raise OpError("o tipo precisa de pelo menos uma camada")
    if any(layer["thickness"] <= 0 for layer in state["layers"]):
        raise OpError("espessura de camada deve ser maior que zero")
    wall_types.validate_plan_style(state.get("plan_style"))


def _write_slab_layers(doc: Document, lset, layers: list[dict]) -> None:
    for old in list(lset.MaterialLayers or []):
        ifcopenshell.api.material.remove_layer(doc.ifc, layer=old)
    for spec in reversed(layers):  # IFC: de baixo para cima
        layer = ifcopenshell.api.material.add_layer(
            doc.ifc, layer_set=lset, material=wall_types.material_named(doc, spec["material"]))
        layer.LayerThickness = float(spec["thickness"])


def _slab_create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    state = op.data
    _validate_slab_type(state)
    slab_type = ifcopenshell.api.root.create_entity(
        doc.ifc, ifc_class="IfcSlabType", predefined_type=state["predefined_type"],
        name=state["name"])
    slab_type.GlobalId = op.id
    lset = ifcopenshell.api.material.add_material_set(
        doc.ifc, name=state["name"], set_type="IfcMaterialLayerSet")
    _write_slab_layers(doc, lset, state["layers"])
    rel = ifcopenshell.api.material.assign_material(
        doc.ifc, products=[slab_type], type="IfcMaterialLayerSet", material=lset)
    guid.stamp(rel, op.id, "material")
    wall_types.write_plan_style(doc, slab_type, state.get("plan_style"))
    return {op.id}


def _slab_delete(doc: Document, op: Op) -> set[str]:
    slab_type = doc.get(op.id, "IfcSlabType")
    if ifcopenshell.util.element.get_types(slab_type):
        raise OpError("o tipo está em uso por lajes")
    lset = layer_set(slab_type)
    ifcopenshell.api.root.remove_product(doc.ifc, product=slab_type)
    ifcopenshell.api.material.remove_material_set(doc.ifc, material=lset)
    return {op.id}


def _slab_edit(doc: Document, op: Op) -> set[str]:
    slab_type = doc.get(op.id, "IfcSlabType")
    state = read_slab_type(slab_type)
    check_before(op, state)
    after = op.after or {}
    state.update(after)
    _validate_slab_type(state)
    slab_type.Name = state["name"]
    slab_type.PredefinedType = state["predefined_type"]
    lset = layer_set(slab_type)
    lset.LayerSetName = state["name"]
    if "layers" in after:
        _write_slab_layers(doc, lset, state["layers"])
    if "plan_style" in after:
        wall_types.write_plan_style(doc, slab_type, state["plan_style"])
    return {op.id}


register_inverse_pair("slab_type.create", _slab_create, "slab_type.delete", _slab_delete)
register("slab_type.edit", _slab_edit, invert_swap)
