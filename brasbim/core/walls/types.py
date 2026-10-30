# SPDX-License-Identifier: LGPL-3.0-or-later
"""Tipos de parede (``IfcWallType`` + ``IfcMaterialLayerSet``), spec §2.1 e §2.3.

Operações: ``wall_type.create`` / ``wall_type.delete`` (data: estado completo) e
``wall_type.edit`` (before/after: name, predefined_type, object_type, layers,
plan_style). ``wall_type.create`` é provisória (RF-TIP-01 ainda sem spec).

``plan_style`` é a representação na planta (spec/ui 03 §6), no Pset
``BrasBim_RepresentacaoPlanta`` do tipo; ``None`` = sem o Pset (valem os padrões).

Estado de um tipo::

    {"name": "Alvenaria 14", "predefined_type": "SOLIDWALL", "object_type": None,
     "layers": [{"material": "Bloco cerâmico", "thickness": 0.09, "name": None,
                 "category": "LoadBearing", "priority": 80, "is_ventilated": False}],
     "profile": None}

Parede de perfil do projeto (spec/ui 41 §4): ``profile`` = ``{"id": <perfil>, "b":
espessura}`` e ``layers`` vazio. O tipo grava um ``IfcMaterialProfileSet`` com as partes
na espessura ``b`` e na altura do desenho, o ``CompositeProfile`` e o Pset
``BrasBim_Perfil`` (``PerfilId``, ``Largura``); cada parede estica o perfil na própria
altura (``rebuild``).
"""

from __future__ import annotations

import math

import ifcopenshell.api.material
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.util.element

from brasbim.core import guid, profile_defs, props
from brasbim.core.document import Document, OpError
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair

PREDEFINED_TYPES = ("SOLIDWALL", "PARTITIONING", "PARAPET", "PLUMBINGWALL", "USERDEFINED")

_LAYER_DEFAULTS = {"name": None, "category": None, "priority": None, "is_ventilated": False}

# Representação na planta (spec/ui 03 §6).
PLAN_PSET = "BrasBim_RepresentacaoPlanta"
FILLS = ("none", "solid", "hatch")
_FILL_PSET = {"none": "NENHUM", "solid": "SOLIDO", "hatch": "HACHURA"}
# Espessuras de linha da série da ABNT NBR 8403, em metros.
LINE_WEIGHTS = (0.00013, 0.00018, 0.00025, 0.00035, 0.0005, 0.0007)
DEFAULT_PLAN_STYLE = {"fill": "solid", "fill_color": "#9C9A93", "hatch_angle": 45.0,
                      "hatch_spacing": 0.10, "line_weight": 0.0005, "line_color": "#2B2A27"}


def read_plan_style(wall_type) -> dict | None:
    """Estilo gravado no tipo (``hatch_angle`` em graus), ou ``None`` sem o Pset."""
    values = ifcopenshell.util.element.get_pset(wall_type, PLAN_PSET, should_inherit=False)
    if not values:
        return None
    fill = {v: k for k, v in _FILL_PSET.items()}
    d = DEFAULT_PLAN_STYLE
    angle = values.get("AnguloHachura")
    return {
        "fill": fill.get(values.get("Preenchimento"), d["fill"]),
        "fill_color": values.get("CorPreenchimento") or d["fill_color"],
        "hatch_angle": d["hatch_angle"] if angle is None else round(math.degrees(angle), 9),
        "hatch_spacing": float(values.get("EspacamentoHachura") or d["hatch_spacing"]),
        "line_weight": float(values.get("EspessuraLinha") or d["line_weight"]),
        "line_color": values.get("CorLinha") or d["line_color"],
    }


def plan_style(wall_type) -> dict:
    """Estilo do tipo com os padrões no que faltar (tipo de outra origem: só padrões)."""
    return {**DEFAULT_PLAN_STYLE, **(read_plan_style(wall_type) or {})}


def validate_plan_style(style: dict | None) -> None:
    if style is None:
        return
    if style.get("fill") not in FILLS:
        raise OpError(f"preenchimento inválido: {style.get('fill')!r}")
    if style["hatch_spacing"] <= 0 or style["line_weight"] <= 0:
        raise OpError("espaçamento da hachura e espessura da linha devem ser positivos")
    for key in ("fill_color", "line_color"):
        color = style[key]
        if not (isinstance(color, str) and len(color) == 7 and color.startswith("#")):
            raise OpError(f"cor inválida: {color!r}")


def write_plan_style(doc: Document, wall_type, style: dict | None) -> None:
    if style is None:
        props.remove_pset(doc, wall_type, PLAN_PSET)
        return
    style = {**DEFAULT_PLAN_STYLE, **style}
    f = doc.ifc
    props.write_pset(doc, wall_type, PLAN_PSET, {
        "Preenchimento": f.createIfcLabel(_FILL_PSET[style["fill"]]),
        "CorPreenchimento": f.createIfcLabel(style["fill_color"].upper()),
        "AnguloHachura": f.createIfcPlaneAngleMeasure(math.radians(style["hatch_angle"])),
        "EspacamentoHachura": f.createIfcPositiveLengthMeasure(float(style["hatch_spacing"])),
        "EspessuraLinha": f.createIfcPositiveLengthMeasure(float(style["line_weight"])),
        "CorLinha": f.createIfcLabel(style["line_color"].upper()),
    })


PROFILE_PSET = "BrasBim_Perfil"


def profile_of(wall_type) -> dict | None:
    """``{"id", "b"}`` do tipo de parede de perfil do projeto, ou ``None``."""
    values = ifcopenshell.util.element.get_pset(wall_type, PROFILE_PSET,
                                                should_inherit=False) or {}
    if not values.get("PerfilId"):
        return None
    return {"id": values["PerfilId"], "b": float(values["Largura"])}


def profile_set(wall_type):
    material = ifcopenshell.util.element.get_material(wall_type)
    if material is None or not material.is_a("IfcMaterialProfileSet"):
        raise OpError(f"tipo {wall_type.GlobalId} sem IfcMaterialProfileSet")
    return material


def profile_parts(wall_type) -> list[dict]:
    """Partes do perfil do tipo (espessura do tipo, altura do desenho)."""
    return profile_defs.read_parts(profile_set(wall_type).MaterialProfiles)


def layer_set(wall_type):
    material = ifcopenshell.util.element.get_material(wall_type)
    if material is None or not material.is_a("IfcMaterialLayerSet"):
        raise OpError(f"tipo {wall_type.GlobalId} sem IfcMaterialLayerSet")
    return material


def thickness(wall_type) -> float:
    found = profile_of(wall_type)
    if found is not None:
        return found["b"]
    return sum(layer.LayerThickness for layer in layer_set(wall_type).MaterialLayers)


def read(wall_type) -> dict:
    found = profile_of(wall_type)
    layers = []
    for layer in ([] if found else layer_set(wall_type).MaterialLayers):
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
        "plan_style": read_plan_style(wall_type),
        "profile": found,
    }


def _validate(state: dict) -> None:
    if state["predefined_type"] not in PREDEFINED_TYPES:
        raise OpError(f"PredefinedType inválido: {state['predefined_type']!r}")
    if state["predefined_type"] == "USERDEFINED" and not state.get("object_type"):
        raise OpError("USERDEFINED exige object_type")
    if state.get("profile"):
        if state["layers"]:
            raise OpError("parede de perfil não tem camadas")
        if state["profile"]["b"] <= 0:
            raise OpError("espessura do perfil deve ser maior que zero")
    elif not state["layers"]:
        raise OpError("o tipo precisa de pelo menos uma camada")
    for layer in state["layers"]:
        if layer["thickness"] <= 0:
            raise OpError("espessura de camada deve ser maior que zero")
        p = layer.get("priority")
        if p is not None and not 0 <= p <= 100:
            raise OpError("prioridade da camada deve estar entre 0 e 100")
    validate_plan_style(state.get("plan_style"))


def material_named(doc: Document, name: str):
    """Material com esse nome, criado se faltar (com o estilo da biblioteca, se houver;
    spec/ui 06 §4.4)."""
    from brasbim.core import materials

    for m in doc.ifc.by_type("IfcMaterial"):
        if m.Name == name:
            return m
    material = ifcopenshell.api.material.add_material(doc.ifc, name=name)
    if name in materials.LIBRARY:
        materials.write_style(doc, material, materials.default_style(name))
    return material


def _write_layers(doc: Document, lset, layers: list[dict]) -> None:
    for old in list(lset.MaterialLayers or []):
        ifcopenshell.api.material.remove_layer(doc.ifc, layer=old)
    for spec in layers:
        spec = {**_LAYER_DEFAULTS, **spec}
        layer = ifcopenshell.api.material.add_layer(
            doc.ifc, layer_set=lset, material=material_named(doc, spec["material"])
        )
        layer.LayerThickness = float(spec["thickness"])
        layer.Name = spec["name"]
        layer.Category = spec["category"]
        layer.Priority = spec["priority"]
        layer.IsVentilated = bool(spec["is_ventilated"])


def _check_profile(doc: Document, state: dict) -> dict | None:
    """Estado do perfil do projeto da parede, conferido (serve para parede, espessura)."""
    found = state.get("profile")
    if not found:
        return None
    definition = profile_defs.state(doc, found["id"])
    if "wall" not in definition["uses"]:
        raise OpError(f"o perfil {definition['name']!r} não serve para paredes")
    profile_defs.stretched(definition, found["b"], profile_defs.nominal(definition)[1])
    return definition


def _write_material(doc: Document, wall_type, state: dict, definition: dict | None) -> None:
    """Conjunto de camadas, ou de perfis, do tipo (associado a ele)."""
    if definition is None:
        material = ifcopenshell.api.material.add_material_set(
            doc.ifc, name=state["name"], set_type="IfcMaterialLayerSet")
        _write_layers(doc, material, state["layers"])
        kind = "IfcMaterialLayerSet"
    else:
        b = state["profile"]["b"]
        material = ifcopenshell.api.material.add_material_set(
            doc.ifc, name=state["name"], set_type="IfcMaterialProfileSet")
        parts = profile_defs.stretched(definition, b, profile_defs.nominal(definition)[1])
        made = profile_defs.write_parts(doc, material, parts, definition["name"])
        material.CompositeProfile = doc.ifc.createIfcCompositeProfileDef(
            "AREA", definition["name"], made, None)
        kind = "IfcMaterialProfileSet"
    rel = ifcopenshell.api.material.assign_material(
        doc.ifc, products=[wall_type], type=kind, material=material)
    guid.stamp(rel, wall_type.GlobalId, "material")
    found = ifcopenshell.util.element.get_pset(wall_type, PROFILE_PSET, should_inherit=False)
    if definition is None:
        if found is not None:
            ifcopenshell.api.pset.remove_pset(doc.ifc, product=wall_type,
                                              pset=doc.ifc.by_id(found["id"]))
        return
    if found is None:
        entity = ifcopenshell.api.pset.add_pset(doc.ifc, product=wall_type, name=PROFILE_PSET)
        guid.stamp(entity, wall_type.GlobalId, "perfil")
    else:
        entity = doc.ifc.by_id(found["id"])
    ifcopenshell.api.pset.edit_pset(doc.ifc, pset=entity, properties={
        "PerfilId": state["profile"]["id"], "Largura": float(state["profile"]["b"])})


def _drop_material(doc: Document, wall_type) -> None:
    """Tira o conjunto do tipo (e das paredes, que o ``rebuild`` associa de novo)."""
    material = ifcopenshell.util.element.get_material(wall_type)
    walls = ifcopenshell.util.element.get_types(wall_type)
    if walls:
        ifcopenshell.api.material.unassign_material(doc.ifc, products=list(walls))
    ifcopenshell.api.material.unassign_material(doc.ifc, products=[wall_type])
    if material is None:
        return
    old = []
    if material.is_a("IfcMaterialProfileSet"):
        if material.CompositeProfile is not None:
            old.append(material.CompositeProfile)
        old += profile_defs.remove_parts(doc, material)
    ifcopenshell.api.material.remove_material_set(doc.ifc, material=material)
    doc.orphan_profiles.extend(old)  # os corpos das paredes ainda podem usá-los


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    state = {"profile": None, **op.data}
    _validate(state)
    definition = _check_profile(doc, state)
    wall_type = ifcopenshell.api.root.create_entity(
        doc.ifc, ifc_class="IfcWallType", predefined_type=state["predefined_type"],
        name=state["name"],
    )
    wall_type.GlobalId = op.id
    wall_type.ElementType = state.get("object_type")
    _write_material(doc, wall_type, state, definition)
    write_plan_style(doc, wall_type, state.get("plan_style"))
    return {op.id}


def _delete(doc: Document, op: Op) -> set[str]:
    wall_type = doc.get(op.id, "IfcWallType")
    if ifcopenshell.util.element.get_types(wall_type):
        raise OpError("o tipo está em uso por paredes")
    _drop_material(doc, wall_type)
    ifcopenshell.api.root.remove_product(doc.ifc, product=wall_type)
    profile_defs.drop_profiles(doc, doc.orphan_profiles)
    doc.orphan_profiles.clear()
    return {op.id}


def refresh_profile_def(doc: Document, wall_type, definition: dict) -> None:
    """Refaz o conjunto do tipo depois que o perfil do projeto mudou; sem linha de
    esticar na largura, a espessura volta à do desenho."""
    state = read(wall_type)
    if definition.get("stretch_x") is None:
        state["profile"] = {**state["profile"], "b": profile_defs.nominal(definition)[0]}
    _drop_material(doc, wall_type)
    _write_material(doc, wall_type, state, definition)


def _edit(doc: Document, op: Op) -> set[str]:
    wall_type = doc.get(op.id, "IfcWallType")
    state = read(wall_type)
    check_before(op, state)
    was_profile = state["profile"] is not None
    after = op.after or {}
    state.update(after)
    _validate(state)
    definition = _check_profile(doc, state)
    wall_type.Name = state["name"]
    wall_type.PredefinedType = state["predefined_type"]
    wall_type.ElementType = state.get("object_type")
    if was_profile or definition is not None:
        if "profile" in after or "layers" in after:
            _drop_material(doc, wall_type)
            _write_material(doc, wall_type, state, definition)
        if definition is not None:
            profile_set(wall_type).Name = state["name"]
        else:
            layer_set(wall_type).LayerSetName = state["name"]
    else:
        lset = layer_set(wall_type)
        lset.LayerSetName = state["name"]
        if "layers" in after:
            _write_layers(doc, lset, state["layers"])
    if "plan_style" in (op.after or {}):
        write_plan_style(doc, wall_type, state["plan_style"])
    return {op.id}


register_inverse_pair("wall_type.create", _create, "wall_type.delete", _delete)
register("wall_type.edit", _edit, invert_swap)
