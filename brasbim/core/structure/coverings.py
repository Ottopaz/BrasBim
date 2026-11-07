# SPDX-License-Identifier: LGPL-3.0-or-later
"""Forro e piso como revestimento (``IfcCovering`` ``CEILING``/``FLOORING``), spec/ui 46.

Tipos: ``covering_type.create`` / ``.delete`` (data: estado completo) e ``.edit``
(before/after: campos alterados)::

    {"name": "Forro de gesso", "predefined_type": "CEILING",
     "layers": [{"material": "Gesso", "thickness": 0.0125}]}

``layers`` de cima para baixo, como na laje (o ``IfcMaterialLayerSet`` grava de baixo para
cima).

Ocorrências: ``covering.create`` / ``.delete`` / ``.edit``::

    {"name": None, "type": "<GlobalId do IfcCoveringType>", "storey": "<GlobalId>",
     "outline": [[0, 0], [4, 0], [4, 3], [0, 3]], "space": "<GlobalId>" ou None,
     "elevation": 2.60}

``elevation``: no forro, a cota da face de baixo; no piso, a do topo (a espessura desce
dela), ambas a partir do pavimento. ``space``: o ambiente a que o revestimento está preso;
enquanto existir, o contorno é o do ambiente, refeito na derivação (``sync``), e o
``IfcRelCoversSpaces`` liga os dois. O corpo desconta os pilares do pavimento (ponto (d)).
Pset ``BrasBim_Revestimento``: ``Ambiente``, ``Altura`` (forro) ou ``Deslocamento`` (piso).
O contorno é lido do ``FootPrint``.
"""

from __future__ import annotations

import copy
import math

import ifcopenshell.api.material
import ifcopenshell.api.root
import ifcopenshell.util.element

from brasbim.core import clip, guid, props
from brasbim.core.document import Document, OpError, axis_placement, local_placement
from brasbim.core.ops import Transaction
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair
from brasbim.core.structure import common
from brasbim.core.structure import types as st_types

PSET = "BrasBim_Revestimento"
COMMON_PSET = "Pset_CoveringCommon"
QTO = "Qto_CoveringBaseQuantities"
KINDS = ("CEILING", "FLOORING")
NOUN = {"CEILING": "forro", "FLOORING": "piso"}
PLURAL = {"CEILING": "forros", "FLOORING": "pisos"}
DEFAULT_ELEVATION = {"CEILING": 2.60, "FLOORING": 0.0}  # pontos (b) e (c)
COLUMN_GAP = 0.10  # m
STATE_KEYS = ("name", "type", "storey", "outline", "space", "elevation")
TYPE_KEYS = ("name", "predefined_type", "layers")


def predefined(entity) -> str | None:
    """Uso (``CEILING``/``FLOORING``): o do tipo, que o IFC 4 guarda só nele."""
    return ifcopenshell.util.element.get_predefined_type(entity)


def is_covering(entity) -> bool:
    return entity is not None and entity.is_a("IfcCovering") and \
        predefined(entity) in KINDS and bool(
            ifcopenshell.util.element.get_pset(entity, PSET, should_inherit=False))


# --- tipos -------------------------------------------------------------------------------


def types_of(doc: Document, kind: str | None = None) -> list:
    """Tipos de forro e de piso (só um deles com ``kind``), em ordem de nome."""
    return sorted((t for t in doc.ifc.by_type("IfcCoveringType")
                   if (kind is None and t.PredefinedType in KINDS) or t.PredefinedType == kind),
                  key=lambda t: t.Name or "")


def type_thickness(covering_type) -> float:
    return st_types.slab_thickness(covering_type)


def read_type(covering_type) -> dict:
    layers = [{"material": la.Material.Name if la.Material else None,
               "thickness": float(la.LayerThickness)}
              for la in reversed(st_types.layer_set(covering_type).MaterialLayers)]
    return {"name": covering_type.Name, "predefined_type": covering_type.PredefinedType,
            "layers": layers}


def top_material(covering_type) -> str | None:
    """Material de cima (o que se vê no piso; no forro, o de baixo é o que se vê, mas a
    hachura da planta é só do piso)."""
    layers = read_type(covering_type)["layers"]
    if covering_type.PredefinedType == "CEILING":
        layers = list(reversed(layers))
    return layers[0]["material"] if layers else None


def _validate_type(state: dict) -> None:
    if state["predefined_type"] not in KINDS:
        raise OpError(f"tipo de revestimento inválido: {state['predefined_type']!r}")
    if not state["layers"]:
        raise OpError("o tipo precisa de pelo menos uma camada")
    if any(layer["thickness"] <= 0 for layer in state["layers"]):
        raise OpError("espessura de camada deve ser maior que zero")


def _type_create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    state = op.data
    _validate_type(state)
    covering_type = ifcopenshell.api.root.create_entity(
        doc.ifc, ifc_class="IfcCoveringType", predefined_type=state["predefined_type"],
        name=state["name"])
    covering_type.GlobalId = op.id
    lset = ifcopenshell.api.material.add_material_set(
        doc.ifc, name=state["name"], set_type="IfcMaterialLayerSet")
    st_types._write_slab_layers(doc, lset, state["layers"])
    rel = ifcopenshell.api.material.assign_material(
        doc.ifc, products=[covering_type], type="IfcMaterialLayerSet", material=lset)
    guid.stamp(rel, op.id, "material")
    return {op.id}


def _type_delete(doc: Document, op: Op) -> set[str]:
    covering_type = doc.get(op.id, "IfcCoveringType")
    if ifcopenshell.util.element.get_types(covering_type):
        raise OpError("o tipo está em uso")
    lset = st_types.layer_set(covering_type)
    ifcopenshell.api.root.remove_product(doc.ifc, product=covering_type)
    ifcopenshell.api.material.remove_material_set(doc.ifc, material=lset)
    return {op.id}


def _type_edit(doc: Document, op: Op) -> set[str]:
    covering_type = doc.get(op.id, "IfcCoveringType")
    state = read_type(covering_type)
    check_before(op, state)
    after = op.after or {}
    unknown = set(after) - set(TYPE_KEYS)
    if unknown:
        raise OpError(f"covering_type.edit: campos desconhecidos {sorted(unknown)}")
    if "predefined_type" in after and after["predefined_type"] != state["predefined_type"] \
            and ifcopenshell.util.element.get_types(covering_type):
        raise OpError("o tipo está em uso: não dá para trocar forro por piso")
    state.update(after)
    _validate_type(state)
    covering_type.Name = state["name"]
    covering_type.PredefinedType = state["predefined_type"]
    lset = st_types.layer_set(covering_type)
    lset.LayerSetName = state["name"]
    if "layers" in after:
        st_types._write_slab_layers(doc, lset, state["layers"])
    return {op.id}


register_inverse_pair("covering_type.create", _type_create, "covering_type.delete",
                      _type_delete)
register("covering_type.edit", _type_edit, invert_swap)


def create_type(doc: Document, name: str, layers: list[dict],
                predefined_type: str = "FLOORING") -> Transaction:
    state = {"name": name, "predefined_type": predefined_type,
             "layers": [{"material": la["material"], "thickness": float(la["thickness"])}
                        for la in layers]}
    _validate_type(state)
    return Transaction(f"Criar tipo de {NOUN[predefined_type]}",
                       [Op("covering_type.create", guid.new(), data=state)])


def edit_type(doc: Document, covering_type, **changes) -> Transaction:
    covering_type = doc.get(covering_type if isinstance(covering_type, str)
                            else covering_type.GlobalId, "IfcCoveringType")
    state = read_type(covering_type)
    after = {k: copy.deepcopy(v) for k, v in changes.items() if state.get(k) != v}
    if not after:
        return Transaction("Editar tipo", [])
    return Transaction("Editar tipo", [Op(
        "covering_type.edit", covering_type.GlobalId,
        before={k: copy.deepcopy(state[k]) for k in after}, after=after)])


def delete_type(doc: Document, covering_type, replacement=None) -> Transaction:
    """Exclui o tipo; em uso, os revestimentos passam para ``replacement`` (do mesmo
    uso)."""
    covering_type = doc.get(covering_type if isinstance(covering_type, str)
                            else covering_type.GlobalId, "IfcCoveringType")
    users = ifcopenshell.util.element.get_types(covering_type)
    ops = []
    if users:
        if replacement is None:
            raise OpError(f"o tipo {covering_type.Name} está em uso")
        new = doc.get(replacement if isinstance(replacement, str)
                      else replacement.GlobalId, "IfcCoveringType")
        if new.PredefinedType != covering_type.PredefinedType:
            raise OpError("o tipo que fica no lugar precisa ser do mesmo uso")
        for e in sorted(users, key=lambda e: e.GlobalId):
            ops.append(Op("covering.edit", e.GlobalId, before={"type": covering_type.GlobalId},
                          after={"type": new.GlobalId}))
    ops.append(Op("covering_type.delete", covering_type.GlobalId,
                  data=read_type(covering_type)))
    return Transaction("Excluir tipo", ops)


# --- ocorrência: leitura -----------------------------------------------------------------


def default_state() -> dict:
    return {"name": None, "space": None, "elevation": 0.0}


def kind_of(doc: Document, state: dict) -> str:
    return doc.get(state["type"], "IfcCoveringType").PredefinedType


def read_state(covering) -> dict:
    values = ifcopenshell.util.element.get_pset(covering, PSET, should_inherit=False) or {}
    if not values:
        raise OpError(f"revestimento {covering.GlobalId} sem os parâmetros do BrasBim")
    covering_type = ifcopenshell.util.element.get_type(covering)
    storey = ifcopenshell.util.element.get_container(covering)
    rep = props.representation(covering, "FootPrint")
    outline = None
    if rep is not None and rep.Items and rep.Items[0].is_a("IfcPolyline"):
        x, y, _ = covering.ObjectPlacement.RelativePlacement.Location.Coordinates
        pts = [p.Coordinates for p in rep.Items[0].Points]
        if len(pts) > 1 and pts[0] == pts[-1]:
            pts = pts[:-1]
        outline = [[x + p[0], y + p[1]] for p in pts]
    elevation = values.get("Altura", values.get("Deslocamento", 0.0))
    return {"name": covering.Name,
            "type": covering_type.GlobalId if covering_type else None,
            "storey": storey.GlobalId if storey else None, "outline": outline,
            "space": values.get("Ambiente") or None, "elevation": float(elevation or 0.0)}


def thickness(doc: Document, state: dict) -> float:
    return type_thickness(doc.get(state["type"], "IfcCoveringType"))


def z_range(doc: Document, state: dict) -> tuple[float, float]:
    """(fundo, topo) a partir do pavimento."""
    t = thickness(doc, state)
    z = float(state["elevation"])
    return (z, z + t) if kind_of(doc, state) == "CEILING" else (z - t, z)


def space_outline(space) -> list | None:
    from brasbim.core.annotations import spaces

    return spaces.read_state(space)["outline"]


def column_rings(doc: Document, storey, z0: float, z1: float) -> list:
    """Planta dos pilares do pavimento que atravessam as cotas ``z0``–``z1`` (a partir do
    pavimento)."""
    from brasbim.core.structure import cuts

    base = float(storey.Elevation or 0.0)
    out = []
    for column in ifcopenshell.util.element.get_decomposition(storey):
        if not column.is_a("IfcColumn"):
            continue
        pc = cuts.piece(doc, column)
        # o pilar que nasce no nível do piso acabado (ou logo abaixo do forro) também
        # conta: o revestimento contorna o pilar
        if pc is not None and pc.z0 - base < z1 + COLUMN_GAP and pc.z1 - base > z0 - COLUMN_GAP:
            out.append(list(pc.ring))
    return out


def net_rings(doc: Document, state: dict) -> list:
    """Contorno menos os pilares (anéis: externos anti-horários, furos horários)."""
    storey = doc.get(state["storey"], "IfcBuildingStorey")
    ring = [tuple(p) for p in state["outline"]]
    holes = column_rings(doc, storey, *z_range(doc, state))
    return clip.difference([ring], holes) if holes else [ring]


def _faces(rings) -> list[tuple[list, list[list]]]:
    """Anéis do recorte agrupados em (externo, furos)."""
    from brasbim.core.structure.rooms import _inside

    outers = [r for r in rings if clip.signed_area(r) > 0]
    holes = [r for r in rings if clip.signed_area(r) < 0]
    out = [(o, []) for o in sorted(outers, key=lambda r: -clip.signed_area(r))]
    for h in holes:
        for o, found in sorted(out, key=lambda f: clip.signed_area(f[0])):
            if _inside(o, h[0]) or _inside(o, ((h[0][0] + h[1][0]) / 2,
                                               (h[0][1] + h[1][1]) / 2)):
                found.append(h)
                break
    return out


def area(outline) -> float:
    from brasbim.core.annotations import spaces

    return spaces.area(outline)


def perimeter(outline) -> float:
    from brasbim.core.annotations import spaces

    return spaces.perimeter(outline)


# --- ocorrência: gravação ----------------------------------------------------------------


def _curve(ifc, ring, ox, oy):
    pts = [ifc.createIfcCartesianPoint((float(x - ox), float(y - oy))) for x, y in ring]
    return ifc.createIfcPolyline([*pts, pts[0]])


def _body(doc: Document, rings, ox: float, oy: float, depth: float) -> list:
    ifc = doc.ifc
    items = []
    for outer, holes in _faces(rings):
        if holes:
            profile = ifc.createIfcArbitraryProfileDefWithVoids(
                "AREA", None, _curve(ifc, outer, ox, oy),
                [_curve(ifc, list(reversed(h)), ox, oy) for h in holes])
        else:
            profile = ifc.createIfcArbitraryClosedProfileDef("AREA", None,
                                                             _curve(ifc, outer, ox, oy))
        items.append(ifc.createIfcExtrudedAreaSolid(
            profile, ifc.createIfcAxis2Placement3D(ifc.createIfcCartesianPoint(
                (0.0, 0.0, 0.0)), None, None),
            ifc.createIfcDirection((0.0, 0.0, 1.0)), float(depth)))
    return items


def _place(doc: Document, covering, storey, origin, z: float) -> None:
    placement = covering.ObjectPlacement
    if placement is None:
        covering.ObjectPlacement = local_placement(doc.ifc, storey.ObjectPlacement, z, origin)
        return
    old = placement.RelativePlacement
    placement.PlacementRelTo = storey.ObjectPlacement
    placement.RelativePlacement = axis_placement(doc.ifc, origin, z, (1.0, 0.0))
    ifcopenshell.util.element.remove_deep2(doc.ifc, old)


def _assign_material(doc: Document, covering, covering_type) -> None:
    lset = st_types.layer_set(covering_type)
    usage = ifcopenshell.util.element.get_material(covering, should_inherit=False)
    if usage is None or not usage.is_a("IfcMaterialLayerSetUsage") \
            or usage.ForLayerSet != lset:
        if usage is not None:
            ifcopenshell.api.material.unassign_material(doc.ifc, products=[covering])
        ifcopenshell.api.material.assign_material(
            doc.ifc, products=[covering], type="IfcMaterialLayerSetUsage", material=lset)
        usage = ifcopenshell.util.element.get_material(covering, should_inherit=False)
    common.stamp_material(covering)
    usage.LayerSetDirection = "AXIS3"
    usage.DirectionSense = "POSITIVE"
    usage.OffsetFromReferenceLine = 0.0


def _rel_of(doc: Document, space):
    for rel in doc.ifc.by_type("IfcRelCoversSpaces"):
        if rel.RelatingSpace == space:
            return rel
    return None


def _unlink(doc: Document, covering) -> None:
    for rel in list(doc.ifc.by_type("IfcRelCoversSpaces")):
        if covering in (rel.RelatedCoverings or ()):
            rest = [c for c in rel.RelatedCoverings if c != covering]
            if rest:
                rel.RelatedCoverings = rest
            else:
                doc.ifc.remove(rel)


def _link(doc: Document, covering, space) -> None:
    rel = _rel_of(doc, space)
    if rel is None:
        rel = doc.ifc.createIfcRelCoversSpaces(
            guid.derived(space.GlobalId, "covers"), None, None, None, space, [covering])
        return
    if covering not in rel.RelatedCoverings:
        rel.RelatedCoverings = sorted([*rel.RelatedCoverings, covering],
                                      key=lambda c: c.GlobalId)


def validate(doc: Document, state: dict) -> None:
    from brasbim.core.structure import slabs

    if state["type"] is None or doc.find(state["type"]) is None:
        raise OpError("o revestimento precisa de um tipo de forro ou de piso")
    if not doc.get(state["type"]).is_a("IfcCoveringType"):
        raise OpError("o tipo não é de forro nem de piso")
    slabs.clean(state["outline"])
    if not math.isfinite(float(state["elevation"])):
        raise OpError("cota inválida")


def write_state(doc: Document, covering, state: dict) -> None:
    from brasbim.core.structure import slabs

    validate(doc, state)
    storey = doc.get(state["storey"], "IfcBuildingStorey")
    covering_type = doc.get(state["type"], "IfcCoveringType")
    outline = slabs.clean(state["outline"])
    state = {**state, "outline": outline}
    covering.Name = state["name"]
    common.assign_type(doc, covering, covering_type)
    covering.PredefinedType = None  # o uso fica no tipo
    common.assign_container(doc, covering, storey)
    _assign_material(doc, covering, covering_type)
    z0, z1 = z_range(doc, state)
    ox, oy = outline[0]
    _place(doc, covering, storey, (ox, oy), z0)
    ifc = doc.ifc
    props.replace_representation(doc, covering, "FootPrint", ifc.createIfcShapeRepresentation(
        doc.footprint_context, "FootPrint", "Curve2D", [_curve(ifc, outline, ox, oy)]))
    rings = net_rings(doc, state)
    items = _body(doc, rings, ox, oy, z1 - z0)
    if items:
        props.replace_representation(doc, covering, "Body", ifc.createIfcShapeRepresentation(
            doc.body_context, "Body", "SweptSolid", items))
    _unlink(doc, covering)
    space = doc.find(state["space"]) if state["space"] else None
    if space is not None:
        _link(doc, covering, space)
    values = {("Altura" if covering_type.PredefinedType == "CEILING" else "Deslocamento"):
              ifc.createIfcLengthMeasure(float(state["elevation"]))}
    if state["space"]:
        values["Ambiente"] = ifc.createIfcLabel(state["space"])
    props.write_pset(doc, covering, PSET, values)
    props.write_pset(doc, covering, COMMON_PSET, {"Reference": covering_type.Name,
                                                  "IsExternal": False})
    props.write_qto(doc, covering, QTO, {"Width": z1 - z0, "GrossArea": area(outline),
                                         "NetArea": clip.area(rings)})
    doc.changed.add(covering.GlobalId)


def remove(doc: Document, covering) -> None:
    _unlink(doc, covering)
    common.remove(doc, covering)


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    covering = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcCovering")
    covering.GlobalId = op.id
    try:
        write_state(doc, covering, {**default_state(), **copy.deepcopy(op.data)})
    except Exception:
        remove(doc, covering)
        raise
    return {op.id}


def _delete(doc: Document, op: Op) -> set[str]:
    remove(doc, doc.get(op.id, "IfcCovering"))
    return {op.id}


def _edit(doc: Document, op: Op) -> set[str]:
    covering = doc.get(op.id, "IfcCovering")
    state = read_state(covering)
    check_before(op, state)
    unknown = set(op.after or {}) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"covering.edit: campos desconhecidos {sorted(unknown)}")
    state.update(copy.deepcopy(op.after or {}))
    write_state(doc, covering, state)
    return {op.id}


register_inverse_pair("covering.create", _create, "covering.delete", _delete)
register("covering.edit", _edit, invert_swap)


# --- comandos ----------------------------------------------------------------------------


def _gid(obj) -> str:
    return obj if isinstance(obj, str) else obj.GlobalId


def bound_to(doc: Document, space) -> list:
    """Revestimentos presos ao ambiente."""
    gid = _gid(space)
    return sorted((c for c in doc.ifc.by_type("IfcCovering")
                   if is_covering(c) and read_state(c)["space"] == gid),
                  key=lambda c: c.GlobalId)


def create_covering(doc: Document, covering_type, storey, outline,
                    elevation: float | None = None) -> Transaction:
    """Revestimento de contorno livre (modo Contorno)."""
    from brasbim.core.structure import slabs

    covering_type = doc.get(_gid(covering_type), "IfcCoveringType")
    kind = covering_type.PredefinedType
    state = {**default_state(), "type": covering_type.GlobalId, "storey": _gid(storey),
             "outline": slabs.clean(outline),
             "elevation": DEFAULT_ELEVATION[kind] if elevation is None else float(elevation)}
    validate(doc, state)
    return Transaction(f"Criar {NOUN[kind]}", [Op("covering.create", guid.new(), data=state)])


def _in_space_op(doc: Document, covering_type, space, elevation) -> Op:
    from brasbim.core.annotations import spaces

    sstate = spaces.read_state(space)
    if not sstate["outline"]:
        raise OpError("o ambiente não tem contorno")
    kind = covering_type.PredefinedType
    state = {**default_state(), "type": covering_type.GlobalId, "storey": sstate["storey"],
             "outline": [list(p) for p in sstate["outline"]], "space": space.GlobalId,
             "elevation": DEFAULT_ELEVATION[kind] if elevation is None else float(elevation)}
    validate(doc, state)
    return Op("covering.create", guid.new(), data=state)


def create_in_space(doc: Document, covering_type, space,
                    elevation: float | None = None) -> Transaction:
    """Revestimento preso ao ambiente (modo Ambiente). Recusa o mesmo tipo duas vezes no
    mesmo ambiente."""
    covering_type = doc.get(_gid(covering_type), "IfcCoveringType")
    space = doc.get(_gid(space), "IfcSpace")
    kind = covering_type.PredefinedType
    if any(read_state(c)["type"] == covering_type.GlobalId for c in bound_to(doc, space)):
        raise OpError(f"o ambiente já tem o {NOUN[kind]} {covering_type.Name}")
    return Transaction(f"Criar {NOUN[kind]}",
                       [_in_space_op(doc, covering_type, space, elevation)])


def fill_storey(doc: Document, covering_type, storey,
                elevation: float | None = None) -> Transaction:
    """O tipo em cada ambiente do pavimento que ainda não tem um revestimento desse uso
    (forro ou piso) preso a ele."""
    covering_type = doc.get(_gid(covering_type), "IfcCoveringType")
    storey = doc.get(_gid(storey), "IfcBuildingStorey")
    kind = covering_type.PredefinedType
    ops = []
    for space in sorted((s for s in ifcopenshell.util.element.get_decomposition(storey)
                         if s.is_a("IfcSpace")), key=lambda s: (s.Name or "", s.GlobalId)):
        if any(predefined(c) == kind for c in bound_to(doc, space)):
            continue
        try:
            ops.append(_in_space_op(doc, covering_type, space, elevation))
        except OpError:
            continue
    if not ops:
        raise OpError(f"todos os ambientes do pavimento já têm {NOUN[kind]}"
                      if any(s.is_a("IfcSpace") for s in
                             ifcopenshell.util.element.get_decomposition(storey))
                      else "não há ambientes no pavimento")
    return Transaction(f"{PLURAL[kind].capitalize()} em todos os ambientes", ops)


def edit_covering(doc: Document, covering, **changes) -> Transaction:
    covering = doc.get(_gid(covering), "IfcCovering")
    state = read_state(covering)
    if "outline" in changes and state["space"] and "space" not in changes:
        changes["space"] = None  # contorno editado à mão: solta do ambiente
    if "type" in changes and changes["type"] != state["type"]:
        new = doc.get(changes["type"], "IfcCoveringType")
        if new.PredefinedType != predefined(covering):
            raise OpError(f"o tipo escolhido é de {NOUN[new.PredefinedType]}")
    after = {k: copy.deepcopy(v) for k, v in changes.items() if state.get(k) != v}
    if not after:
        return Transaction("Editar revestimento", [])
    validate(doc, {**state, **after})
    noun = NOUN.get(predefined(covering), "revestimento")
    label = f"Soltar {noun} do ambiente" if after.keys() == {"space"} and \
        after["space"] is None else f"Editar {noun}"
    return Transaction(label, [Op("covering.edit", covering.GlobalId,
                                  before={k: copy.deepcopy(state[k]) for k in after},
                                  after=after)])


def release(doc: Document, covering) -> Transaction:
    """Solta do ambiente: o contorno fica como está, livre."""
    return edit_covering(doc, covering, space=None)


def delete_ops(doc: Document, covering) -> list[Op]:
    return [Op("covering.delete", covering.GlobalId, data=read_state(covering))]


def release_ops_for_deleted(doc: Document, gone: set[str]) -> list[Op]:
    """Os revestimentos dos ambientes excluídos ficam com o último contorno, soltos."""
    ops = []
    for c in sorted(doc.ifc.by_type("IfcCovering"), key=lambda c: c.GlobalId):
        if not is_covering(c) or c.GlobalId in gone:
            continue
        space = read_state(c)["space"]
        if space and space in gone:
            ops.append(Op("covering.edit", c.GlobalId, before={"space": space},
                          after={"space": None}))
    return ops


def space_at(doc: Document, storey, point):
    """Ambiente do pavimento que contém o ponto (o menor, se um está dentro de outro)."""
    from brasbim.core.annotations import spaces
    from brasbim.core.structure.rooms import _inside

    found = []
    for s in ifcopenshell.util.element.get_decomposition(storey):
        if not s.is_a("IfcSpace"):
            continue
        outline = spaces.read_state(s)["outline"]
        if outline and _inside([tuple(p) for p in outline], tuple(point)):
            found.append((spaces.area(outline), s.GlobalId, s))
    return min(found)[2] if found else None


def ceiling_height(doc: Document, storey, point, space_gid: str | None = None) -> float | None:
    """Cota (do pavimento) da face de baixo do forro mais baixo do ambiente: o preso a
    ele, ou um forro do pavimento que cobre o ponto. ``None`` sem forro."""
    from brasbim.core.structure.rooms import _inside

    found = []
    for c in ifcopenshell.util.element.get_decomposition(storey):
        if not (c.is_a("IfcCovering") and is_covering(c) and predefined(c) == "CEILING"):
            continue
        try:
            state = read_state(c)
        except OpError:
            continue
        if (space_gid and state["space"] == space_gid) or (
                state["outline"] and _inside([tuple(p) for p in state["outline"]],
                                             tuple(point))):
            found.append(float(state["elevation"]))
    return min(found) if found else None


# --- derivação ---------------------------------------------------------------------------

_COLUMN_LIKE = ("IfcColumn", "IfcColumnType", "IfcBuildingStorey", "IfcCoveringType",
                "IfcMaterial")


def sync(doc: Document, touched: set[str]) -> None:
    """Refaz os revestimentos depois dos ambientes (chamado pela derivação deles): o
    contorno do preso acompanha o ambiente; o corpo, os pilares e o tipo."""
    coverings = [c for c in doc.ifc.by_type("IfcCovering") if is_covering(c)]
    if not coverings:
        return
    seen = set(touched) | set(doc.changed)
    entities = [doc.find(g) for g in sorted(touched)]
    others = any(e is None or any(e.is_a(c) for c in _COLUMN_LIKE) for e in entities)
    rewritten = []
    for covering in sorted(coverings, key=lambda c: c.GlobalId):
        try:
            state = read_state(covering)
        except OpError:
            continue
        if not (covering.GlobalId in touched or others or state["type"] in touched
                or (state["space"] and state["space"] in seen)):
            continue
        space = doc.find(state["space"]) if state["space"] else None
        if space is not None:
            outline = space_outline(space)
            if outline:
                state["outline"] = [list(p) for p in outline]
        try:
            write_state(doc, covering, state)
        except OpError:
            continue
        rewritten.append(covering)
    if rewritten:  # a laje sob o piso acompanha o rebaixo (spec/ui 46 §8 (c))
        from brasbim.core.structure import rebuild

        rebuild.refresh_slabs_under(doc, rewritten)
