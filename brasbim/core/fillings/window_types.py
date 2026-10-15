# SPDX-License-Identifier: LGPL-3.0-or-later
"""Tipos de janela (``IfcWindowType``), ``spec/elementos/janela.md`` §2 e §3.2.

Operações: ``window_type.create`` / ``window_type.delete`` (data: estado completo) e
``window_type.edit`` (before/after: campos de ``STATE_KEYS``).

Estado de um tipo::

    {"name": "J1 – correr 2 folhas 120", "code": "J1", "predefined_type": "WINDOW",
     "partitioning": "DOUBLE_PANEL_VERTICAL",
     "lining": {"depth": 0.05, "thickness": 0.03, "mullion_thickness": 0.03,
                "mullion_offsets": [0.5], "transom_thickness": 0.03,
                "transom_offsets": []},
     "panels": [{"operation": "SLIDINGHORIZONTAL", "position": "LEFT",
                 "frame_depth": 0.03, "frame_thickness": 0.04}, ...],
     "materials": {"lining": "Alumínio", "framing": "Alumínio", "glazing": "Vidro"},
     "defaults": {"width": 1.2, "height": 1.0, "base": 1.1},
     "variant": None}

Marco e caixilhos ficam em ``IfcWindowLiningProperties`` e ``IfcWindowPanelProperties``
(mesma decisão da porta, janela §2.5). ``code`` é o ``Reference`` do
``Pset_WindowCommon`` do tipo (vazio = o nome sem o sufixo de mão). ``variant`` é o
GlobalId do tipo com a outra mão (janela §2.4).
"""

from __future__ import annotations

import ifcopenshell.api.material
import ifcopenshell.api.root
import ifcopenshell.util.element

from brasbim.core import guid, materials, props
from brasbim.core.document import Document, OpError
from brasbim.core.fillings import params
from brasbim.core.fillings.door_types import _write_materials
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair

STATE_KEYS = ("name", "code", "partitioning", "lining", "panels", "materials", "defaults",
              "variant")
COMMON_PSET = "Pset_WindowCommon"
_CONSTITUENTS = {"lining": "Lining", "framing": "Framing", "glazing": "Glazing"}
_PREDEFINED = ("IfcWindowLiningProperties", "IfcWindowPanelProperties")


def default_state(partitioning: str = "DOUBLE_PANEL_VERTICAL", operations=None) -> dict:
    return {
        "name": None,
        "code": None,
        "predefined_type": "WINDOW",
        "partitioning": partitioning,
        "lining": params.default_window_lining(partitioning),
        "panels": params.default_window_panels(partitioning, operations),
        "materials": {"lining": "Alumínio", "framing": "Alumínio", "glazing": "Vidro"},
        "defaults": dict(params.DEFAULT_WINDOW_SIZE),
        "variant": None,
    }


def hand(state: dict) -> str | None:
    return params.window_hand(state["partitioning"], state["lining"], state["panels"])


def code(state: dict) -> str:
    return state.get("code") or params.base_name(state["name"] or "")


def mirrored(state: dict, variant: str | None) -> dict:
    """Variante com a outra mão: caixilhos e montantes espelhados, nome com o sufixo da
    mão nova; ``variant`` aponta para o tipo original."""
    lining, panels = params.mirror_window(state["partitioning"], state["lining"],
                                          state["panels"])
    new_hand = params.window_hand(state["partitioning"], lining, panels)
    if new_hand is None:
        raise OpError(f"o tipo {state['name']} não tem mão")
    return {**state, "name": params.base_name(state["name"]) + params.HAND_SUFFIX[new_hand],
            "code": code(state), "lining": lining, "panels": panels, "variant": variant}


def mirror_fields(state: dict) -> dict:
    """Campos que a variante recebe espelhados quando o tipo muda."""
    lining, panels = params.mirror_window(state["partitioning"], state["lining"],
                                          state["panels"])
    return {"partitioning": state["partitioning"], "lining": lining, "panels": panels}


def with_partitioning(state: dict, partitioning: str) -> dict:
    """Troca a divisão (spec/ui 09 §5.1): posições que continuam mantêm a operação; as
    novas ganham a do primeiro caixilho; montantes e travessas voltam ao padrão."""
    old = {p["position"]: p for p in state["panels"]}
    first = state["panels"][0] if state["panels"] else None
    panels = []
    for position in params.WINDOW_PARTITIONINGS[partitioning]:
        source = old.get(position) or first
        panel = {**params.DEFAULT_WINDOW_FRAME, "operation": "SLIDINGHORIZONTAL"}
        if source is not None:
            panel.update(operation=source["operation"], frame_depth=source["frame_depth"],
                         frame_thickness=source["frame_thickness"])
        panels.append({**panel, "position": position})
    lining = {**state["lining"], "mullion_offsets": [], "transom_offsets": []}
    key = "mullion_offsets" if params.is_vertical(partitioning) else "transom_offsets"
    lining[key] = params.default_offsets(partitioning)
    return {**state, "partitioning": partitioning, "lining": lining, "panels": panels}


# --- leitura -----------------------------------------------------------------


def _predefined(window_type, ifc_class: str) -> list:
    return [p for p in window_type.HasPropertySets or [] if p.is_a(ifc_class)]


def _num(value):
    return None if value is None else float(value)


def read(window_type) -> dict:
    partitioning = window_type.PartitioningType or "SINGLE_PANEL"
    if partitioning not in params.WINDOW_PARTITIONINGS:
        partitioning = "SINGLE_PANEL"
    state = default_state(partitioning)
    state["name"] = window_type.Name
    state["predefined_type"] = window_type.PredefinedType
    linings = _predefined(window_type, "IfcWindowLiningProperties")
    if linings:
        lp = linings[0]
        mullions = [_num(v) for v in (lp.FirstMullionOffset, lp.SecondMullionOffset)]
        transoms = [_num(v) for v in (lp.FirstTransomOffset, lp.SecondTransomOffset)]
        state["lining"] = {
            "depth": _num(lp.LiningDepth),
            "thickness": _num(lp.LiningThickness) or 0.0,
            "mullion_thickness": _num(lp.MullionThickness) or 0.0,
            "mullion_offsets": [v for v in mullions if v is not None],
            "transom_thickness": _num(lp.TransomThickness) or 0.0,
            "transom_offsets": [v for v in transoms if v is not None],
        }
    state["panels"] = [
        {"operation": p.OperationType, "position": p.PanelPosition,
         "frame_depth": _num(p.FrameDepth), "frame_thickness": _num(p.FrameThickness)}
        for p in _predefined(window_type, "IfcWindowPanelProperties")
    ]
    material = ifcopenshell.util.element.get_material(window_type)
    if material is not None and material.is_a("IfcMaterialConstituentSet"):
        names = {c.Name: c.Material.Name for c in material.MaterialConstituents or []}
        state["materials"] = {k: names.get(v) for k, v in _CONSTITUENTS.items()}
    values = ifcopenshell.util.element.get_pset(window_type, params.TYPE_PSET) or {}
    if values:
        state["defaults"] = {"width": float(values["LarguraPadrao"]),
                             "height": float(values["AlturaPadrao"]),
                             "base": float(values["BasePadrao"])}
        state["variant"] = values.get("Variante")
    common = ifcopenshell.util.element.get_pset(window_type, COMMON_PSET) or {}
    state["code"] = common.get("Reference")
    return state


# --- validação -----------------------------------------------------------------


def _check_offsets(offsets: list, n: int, what: str) -> None:
    if len(offsets) != n:
        raise OpError(f"a divisão pede {n} posição(ões) de {what}")
    last = 0.0
    for f in offsets:
        if not last < f < 1:
            raise OpError(f"posições de {what} devem ficar entre 0 e 1, crescentes")
        last = f


def validate(state: dict) -> None:
    if not state.get("name"):
        raise OpError("o tipo de janela precisa de nome")
    if state["predefined_type"] not in params.WINDOW_PREDEFINED_TYPES:
        raise OpError(f"PredefinedType de janela inválido: {state['predefined_type']!r}")
    positions = params.WINDOW_PARTITIONINGS.get(state["partitioning"])
    if positions is None:
        raise OpError(f"divisão de janela inválida: {state['partitioning']!r}")
    lining = state["lining"]
    if not lining["depth"] or lining["depth"] <= 0:
        raise OpError("profundidade do marco deve ser maior que zero")
    for key in ("thickness", "mullion_thickness", "transom_thickness"):
        if lining[key] is None or lining[key] < 0:
            raise OpError("espessuras do marco, montante e travessa devem ser ≥ 0")
    n = len(positions) - 1
    vertical = params.is_vertical(state["partitioning"])
    _check_offsets(lining["mullion_offsets"], n if vertical else 0, "montante")
    _check_offsets(lining["transom_offsets"], 0 if vertical else n, "travessa")
    panels = state["panels"]
    if tuple(p["position"] for p in panels) != positions:
        raise OpError(f"caixilhos não correspondem à divisão {state['partitioning']}")
    for p in panels:
        if p["operation"] not in params.WINDOW_OPERATIONS:
            raise OpError(f"operação de caixilho inválida: {p['operation']!r}")
        if not p["frame_depth"] or p["frame_depth"] <= 0 or p["frame_thickness"] is None \
                or p["frame_thickness"] < 0:
            raise OpError("perfil do caixilho com profundidade ou largura inválida")
    d = state["defaults"]
    if d["width"] <= 0 or d["height"] <= 0:
        raise OpError("dimensões padrão devem ser maiores que zero")


# --- gravação ----------------------------------------------------------------


def _write_predefined(doc: Document, window_type, state: dict) -> None:
    ifc = doc.ifc
    old = [p for p in window_type.HasPropertySets or [] if p.is_a() in _PREDEFINED]
    keep = [p for p in window_type.HasPropertySets or [] if p.is_a() not in _PREDEFINED]
    window_type.HasPropertySets = keep or None
    for entity in old:
        ifc.remove(entity)
    lining = state["lining"]
    mullions = list(lining["mullion_offsets"]) + [None, None]
    transoms = list(lining["transom_offsets"]) + [None, None]
    vertical = params.is_vertical(state["partitioning"])
    single = state["partitioning"] == "SINGLE_PANEL"
    new = [ifc.create_entity(
        "IfcWindowLiningProperties",
        GlobalId=guid.derived(window_type.GlobalId, "lining"),
        Name="Marco",
        LiningDepth=float(lining["depth"]),
        LiningThickness=float(lining["thickness"]),
        MullionThickness=None if single or not vertical else float(lining["mullion_thickness"]),
        TransomThickness=None if single or vertical else float(lining["transom_thickness"]),
        FirstMullionOffset=_num(mullions[0]),
        SecondMullionOffset=_num(mullions[1]),
        FirstTransomOffset=_num(transoms[0]),
        SecondTransomOffset=_num(transoms[1]),
    )]
    for i, panel in enumerate(state["panels"]):
        new.append(ifc.create_entity(
            "IfcWindowPanelProperties",
            GlobalId=guid.derived(window_type.GlobalId, f"panel/{i}"),
            Name=f"Caixilho {i + 1}",
            OperationType=panel["operation"],
            PanelPosition=panel["position"],
            FrameDepth=float(panel["frame_depth"]),
            FrameThickness=float(panel["frame_thickness"]),
        ))
    window_type.HasPropertySets = new + keep


def write(doc: Document, window_type, state: dict) -> None:
    validate(state)
    window_type.Name = state["name"]
    window_type.PredefinedType = state["predefined_type"]
    window_type.PartitioningType = state["partitioning"]
    window_type.ParameterTakesPrecedence = True
    _write_predefined(doc, window_type, state)
    _write_materials(doc, window_type, state["materials"])
    for name in state["materials"].values():
        if name:
            materials.ensure_style(doc, name)
    d = state["defaults"]
    ifc = doc.ifc
    props.write_pset(doc, window_type, params.TYPE_PSET, {
        "LarguraPadrao": ifc.createIfcPositiveLengthMeasure(float(d["width"])),
        "AlturaPadrao": ifc.createIfcPositiveLengthMeasure(float(d["height"])),
        "BasePadrao": ifc.createIfcLengthMeasure(float(d["base"])),
        **({"Variante": ifc.createIfcIdentifier(state["variant"])} if state["variant"] else {}),
    })
    if state.get("code"):
        props.write_pset(doc, window_type, COMMON_PSET,
                         {"Reference": ifc.createIfcIdentifier(state["code"])})
    else:
        props.remove_pset(doc, window_type, COMMON_PSET)


# --- operações ---------------------------------------------------------------


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    state = {**default_state(op.data.get("partitioning", "DOUBLE_PANEL_VERTICAL")), **op.data}
    validate(state)
    window_type = ifcopenshell.api.root.create_entity(
        doc.ifc, ifc_class="IfcWindowType", predefined_type=state["predefined_type"],
        name=state["name"])
    window_type.GlobalId = op.id
    write(doc, window_type, state)
    return {op.id}


def _delete(doc: Document, op: Op) -> set[str]:
    window_type = doc.get(op.id, "IfcWindowType")
    if ifcopenshell.util.element.get_types(window_type):
        raise OpError("o tipo está em uso por janelas")
    cset = ifcopenshell.util.element.get_material(window_type)
    for entity in [p for p in window_type.HasPropertySets or [] if p.is_a() in _PREDEFINED]:
        window_type.HasPropertySets = [p for p in window_type.HasPropertySets
                                       if p != entity] or None
        doc.ifc.remove(entity)
    props.remove_pset(doc, window_type, COMMON_PSET)
    ifcopenshell.api.root.remove_product(doc.ifc, product=window_type)
    if cset is not None:
        ifcopenshell.api.material.remove_material_set(doc.ifc, material=cset)
    return set()


def _edit(doc: Document, op: Op) -> set[str]:
    window_type = doc.get(op.id, "IfcWindowType")
    state = read(window_type)
    check_before(op, state)
    unknown = set(op.after or {}) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"window_type.edit: campos desconhecidos {sorted(unknown)}")
    state.update(op.after or {})
    write(doc, window_type, state)
    return {op.id}


register_inverse_pair("window_type.create", _create, "window_type.delete", _delete)
register("window_type.edit", _edit, invert_swap)
