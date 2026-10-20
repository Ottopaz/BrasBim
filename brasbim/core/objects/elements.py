# SPDX-License-Identifier: LGPL-3.0-or-later
"""Ocorrências de objeto paramétrico (``spec/elementos/objeto-parametrico.md`` §2.3, §2.4,
§5.2 e §6).

Operações: ``object.create`` / ``object.delete`` (data: estado completo) e
``object.edit`` (before/after: campos de ``STATE_KEYS``).

Estado::

    {"name": None, "type": "<GlobalId do tipo>", "storey": "<GlobalId>",
     "point": [2.0, 3.0], "angle": 0.0, "mirror": False,
     "values": {"comprimento": 2.4, "elevacao": 0.0},  # parâmetros de ocorrência
     "host": None}  # preso à parede: {"wall": "<GlobalId>", "side": "left", "distance": 1.2}

``point`` e ``angle`` (graus, anti-horário) posicionam o objeto livre no pavimento; a
elevação é o parâmetro ``elevacao``. Preso à parede, ``point`` e ``angle`` são calculados
(``hosting``). Corpo, símbolo, caixa, Psets e os aninhados são refeitos a cada gravação.
Os aninhados (§6.4) e o vão (§6.3) têm GlobalIds derivados do objeto (``guid.derived``):
desfazer e refazer dão sempre os mesmos.
"""

from __future__ import annotations

import copy
import json
import math

import ifcopenshell.api.aggregate
import ifcopenshell.api.root
import ifcopenshell.util.element

from brasbim.core import guid, props
from brasbim.core.document import Document, OpError, axis_placement, local_placement
from brasbim.core.objects import definition as od
from brasbim.core.objects import formula as fm
from brasbim.core.objects import shapes
from brasbim.core.objects import types as ot
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair
from brasbim.core.structure import common

PSET = "BrasBim_Objeto"
STATE_KEYS = ("name", "type", "storey", "point", "angle", "mirror", "values", "host")
OCCURRENCE_CLASSES = tuple(v[0] for v in od.CATEGORIES.values())


def default_state() -> dict:
    return {"name": None, "type": None, "storey": None, "point": [0.0, 0.0], "angle": 0.0,
            "mirror": False, "values": {}, "host": None}


def _params(element) -> dict | None:
    values = ifcopenshell.util.element.get_pset(element, PSET, should_inherit=False)
    if not values or "Parametros" not in values:
        return None
    return json.loads(values["Parametros"])


def is_object(entity) -> bool:
    """Ocorrência de objeto paramétrico de primeiro nível (não aninhada)."""
    if entity is None or not any(entity.is_a(c) for c in OCCURRENCE_CLASSES):
        return False
    params = _params(entity)
    return params is not None and not params.get("parent")


def is_part(entity) -> bool:
    """Objeto aninhado: responde pelo objeto de fora (§6.4)."""
    if entity is None or not any(entity.is_a(c) for c in OCCURRENCE_CLASSES):
        return False
    params = _params(entity)
    return params is not None and bool(params.get("parent"))


def parent_of(entity):
    """Objeto de primeiro nível que contém ``entity`` (ele mesmo, se não for aninhado)."""
    while is_part(entity):
        rel = entity.Decomposes[0] if entity.Decomposes else None
        if rel is None:
            return entity
        entity = rel.RelatingObject
    return entity


def parts_of(element) -> list:
    return [p for rel in element.IsDecomposedBy or () for p in rel.RelatedObjects
            if is_part(p)]


def all_objects(doc: Document) -> list:
    out = []
    for cls in OCCURRENCE_CLASSES:
        out += [e for e in doc.ifc.by_type(cls) if is_object(e)]
    return sorted(out, key=lambda e: e.GlobalId)


def type_of(doc: Document, element):
    return ifcopenshell.util.element.get_type(element)


def read_state(doc: Document, element) -> dict:
    params = _params(element)
    if params is None:
        raise OpError(f"{element.GlobalId} não é objeto paramétrico")
    if params.get("parent"):
        raise OpError("objeto aninhado: edite o objeto de fora")
    state = default_state()
    state.update({k: copy.deepcopy(params[k]) for k in STATE_KEYS if k in params})
    element_type = type_of(doc, element)
    container = ifcopenshell.util.element.get_container(element)
    state.update(name=params.get("name"),
                 type=element_type.GlobalId if element_type else None,
                 storey=container.GlobalId if container else None)
    return state


# --- cálculo -----------------------------------------------------------------------------


class Built:
    """Tudo o que a ocorrência gera com os valores dela (sem gravar)."""

    def __init__(self, type_state: dict, values: dict, mirror: bool):
        self.type_state = type_state
        self.definition = type_state["definition"]
        self.values = values
        self.mirror = mirror
        self.solids = od.solids(self.definition, values)
        self.nested = od.nested(self.definition, values)
        self.strokes = od.symbol_items(self.definition, values)
        self.box = od.bounds(self.solids)


def build(doc: Document, type_state: dict, occurrence_values: dict, mirror: bool) -> Built:
    values = ot.evaluate(type_state, occurrence_values)
    return Built(type_state, values, mirror)


def resolve(doc: Document, state: dict) -> tuple[object, dict, Built]:
    element_type = doc.get(state["type"], "IfcTypeObject")
    tstate = ot.read(element_type)
    stored = ot.stored_values(tstate["definition"], state["values"], "occurrence")
    return element_type, tstate, build(doc, tstate, stored, bool(state["mirror"]))


def to_storey(state: dict, p) -> tuple[float, float]:
    """Ponto local (já espelhado, se for o caso) → coordenadas do pavimento."""
    a = math.radians(state["angle"])
    c, s = math.cos(a), math.sin(a)
    return (state["point"][0] + c * p[0] - s * p[1], state["point"][1] + s * p[0] + c * p[1])


# --- gravação ----------------------------------------------------------------------------


def _validate(state: dict) -> None:
    if not state.get("type"):
        raise OpError("o objeto precisa de um tipo")
    if not state.get("storey"):
        raise OpError("o objeto precisa de um pavimento")
    if len(state.get("point") or []) != 2:
        raise OpError("ponto de inserção inválido")


def _set_placement(doc: Document, element, relative_to, location3, direction) -> None:
    placement = element.ObjectPlacement
    if placement is None:
        element.ObjectPlacement = local_placement(doc.ifc, relative_to, location3[2],
                                                  location3[:2], direction)
        return
    old = placement.RelativePlacement
    placement.PlacementRelTo = relative_to
    placement.RelativePlacement = axis_placement(doc.ifc, location3[:2], location3[2],
                                                 direction)
    ifcopenshell.util.element.remove_deep2(doc.ifc, old)


def _clear_styles(doc: Document, element) -> None:
    rep = props.representation(element, "Body")
    for item in (rep.Items if rep is not None else []) or []:
        for styled in [i for i in doc.ifc.get_inverse(item) if i.is_a("IfcStyledItem")]:
            doc.ifc.remove(styled)


def _write_shape(doc: Document, element, built: Built) -> None:
    from brasbim.core import materials

    ifc = doc.ifc
    _clear_styles(doc, element)
    items = []
    for s in built.solids:
        if s.void:
            continue
        item = shapes.solid_item(ifc, s, built.mirror)
        style = materials.surface_style(doc, s.material) if s.material else None
        if style is not None:
            ifc.createIfcStyledItem(item, [style], None)
        items.append(item)
    if items:
        props.replace_representation(doc, element, "Body", ifc.createIfcShapeRepresentation(
            doc.body_context, "Body", "SweptSolid", items))
    else:
        _drop(doc, element, "Body")
    strokes = built.strokes if (built.definition.get("symbol") or {}).get(
        "mode") == "drawn" else []
    curves = shapes.curve_items(ifc, strokes, built.mirror)
    if curves:
        props.replace_representation(doc, element, "Annotation", ifc.createIfcShapeRepresentation(
            doc.annotation_context, "Annotation", "GeometricCurveSet",
            [ifc.createIfcGeometricCurveSet(curves)]))
    else:
        _drop(doc, element, "Annotation")
    box = shapes.box_item(ifc, shapes.mirrored_box(built.box, built.mirror)) \
        if built.box else None
    if box is not None:
        props.replace_representation(doc, element, "Box", ifc.createIfcShapeRepresentation(
            doc._subcontext("Model", "Box", "MODEL_VIEW"), "Box", "BoundingBox", [box]))
    else:
        _drop(doc, element, "Box")


def _drop(doc: Document, element, identifier: str) -> None:
    shape = element.Representation
    if shape is None:
        return
    old = [r for r in shape.Representations if r.RepresentationIdentifier == identifier]
    if not old:
        return
    keep = set(doc.ifc.by_type("IfcGeometricRepresentationContext"))
    rest = [r for r in shape.Representations if r not in old]
    if rest:
        shape.Representations = rest
    else:
        element.Representation = None
        doc.ifc.remove(shape)
    for rep in old:
        ifcopenshell.util.element.remove_deep2(doc.ifc, rep, do_not_delete=keep)


def _write_props(doc: Document, element, built: Built, element_type) -> None:
    defn = built.definition
    ot.remove_values_pset(doc, element)
    ot.write_values_pset(doc, element, defn, built.values, "occurrence")
    common_name = od.CATEGORIES[defn["category"]][2]
    if common_name is None or defn["category"] == "vegetation":
        return
    own = ot.nominal(defn, built.box)
    type_values = ifcopenshell.util.element.get_pset(element_type, common_name,
                                                     should_inherit=False) or {}
    differs = {k: v for k, v in own.items() if abs(float(type_values.get(k, -1)) - v) > 1e-6}
    if differs:
        props.write_pset(doc, element, common_name, differs)
    else:
        props.remove_pset(doc, element, common_name)


def _write_material(doc: Document, element, built: Built, element_type) -> None:
    mapping = ot.role_materials(built.definition, built.values)
    ot.ensure_materials(doc, mapping.values())
    type_mapping = ot.role_materials(built.definition, ot.evaluate(built.type_state))
    ot.assign_constituents(doc, element, mapping if mapping != type_mapping else {},
                           built.definition["name"])


def write_element(doc: Document, element, element_type, built: Built, relative_to,
                  location3, direction, params: dict, depth: int = 0) -> None:
    """Grava uma ocorrência (de primeiro nível ou aninhada) já calculada."""
    assign_type(doc, element, element_type)
    _set_placement(doc, element, relative_to, location3, direction)
    props.write_pset(doc, element, PSET, {"Parametros": doc.ifc.createIfcText(
        json.dumps(params, ensure_ascii=False, sort_keys=True))})
    _write_shape(doc, element, built)
    _write_props(doc, element, built, element_type)
    _write_material(doc, element, built, element_type)
    _sync_nested(doc, element, built, depth)
    doc.changed.add(element.GlobalId)


def part_id(owner: str, piece: int, copy_: int) -> str:
    return guid.derived(owner, f"part/{piece}/{copy_}")


def _nested_type(doc: Document, name: str, owner_type):
    found = ot.by_name(doc, name)
    if found is None:
        raise OpError(f"o tipo aninhado '{name}' não está no projeto")
    if found == owner_type:
        raise OpError(f"o objeto '{name}' não pode conter a si mesmo")
    return found


def _sync_nested(doc: Document, element, built: Built, depth: int) -> None:
    wanted = {part_id(element.GlobalId, n.piece, n.copy): n for n in built.nested}
    if wanted and depth + 1 > od.MAX_NESTING - 1:
        raise OpError(f"objetos aninhados em mais de {od.MAX_NESTING} níveis")
    for part in parts_of(element):
        if part.GlobalId not in wanted:
            remove_element(doc, part)
    element_type = type_of(doc, element)
    m = -1.0 if built.mirror else 1.0
    for gid in sorted(wanted):
        n = wanted[gid]
        part_type = _nested_type(doc, n.type_name, element_type)
        part_state = ot.read(part_type)
        stored = ot.stored_values(part_state["definition"], n.values, "occurrence")
        mirror = bool(n.mirror) != built.mirror
        part_built = build(doc, part_state, stored, mirror)
        a = math.radians(m * n.rotation)
        part = doc.find(gid)
        occ_class = od.classes(part_state["definition"])[0]
        if part is not None and not part.is_a(occ_class):
            remove_element(doc, part)
            part = None
        if part is None:
            part = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class=occ_class)
            part.GlobalId = gid
        if not part.Decomposes:
            rel = ifcopenshell.api.aggregate.assign_object(doc.ifc, products=[part],
                                                           relating_object=element)
            guid.stamp(rel, element.GlobalId, "aggregates")
        part.Name = part_type.Name
        write_element(doc, part, part_type, part_built, element.ObjectPlacement,
                      (m * n.origin[0], n.origin[1], n.origin[2]), (math.cos(a), math.sin(a)),
                      {"parent": element.GlobalId, "values": stored, "mirror": mirror},
                      depth + 1)


def remove_element(doc: Document, element) -> None:
    """Apaga a ocorrência, os aninhados e o vão."""
    for part in parts_of(element):
        remove_element(doc, part)
    doc.changed.add(element.GlobalId)
    ot.remove_values_pset(doc, element)
    ot.assign_constituents(doc, element, {}, "")
    _clear_styles(doc, element)
    common.remove(doc, element)


def write_state(doc: Document, element, state: dict) -> None:
    from brasbim.core.objects import hosting

    state = {**default_state(), **state}
    _validate(state)
    storey = doc.get(state["storey"], "IfcBuildingStorey")
    element_type, tstate, built = resolve(doc, state)
    occ_class, _ = od.classes(tstate["definition"])
    if not element.is_a(occ_class):
        raise OpError(f"o tipo {element_type.Name} é para {occ_class}")
    if (tstate["definition"]["hosting"] == "wall") != (state["host"] is not None):
        raise OpError("objeto preso à parede precisa da parede, e o livre não tem parede"
                      if state["host"] is None else "este objeto não se prende à parede")
    state["values"] = ot.stored_values(tstate["definition"], state["values"], "occurrence")
    element.Name = state["name"] or element_type.Name
    common.assign_container(doc, element, storey)
    elevation = float(built.values.get("elevacao", 0.0))
    if state["host"] is not None:
        state = hosting.place(doc, state, built)
    a = math.radians(state["angle"])
    params = {k: copy.deepcopy(state[k]) for k in STATE_KEYS if k not in ("type", "storey")}
    write_element(doc, element, element_type, built, storey.ObjectPlacement,
                  (state["point"][0], state["point"][1], elevation),
                  (math.cos(a), math.sin(a)), params)
    hosting.sync(doc, element, state, built)


def assign_type(doc: Document, element, element_type) -> None:
    """Tipo sem mapear representações: o tipo não tem ``RepresentationMaps`` (§2.3)."""
    import ifcopenshell.api.type

    if ifcopenshell.util.element.get_type(element) != element_type:
        rel = ifcopenshell.api.type.assign_type(doc.ifc, related_objects=[element],
                                                relating_type=element_type,
                                                should_map_representations=False)
        guid.stamp(rel, element_type.GlobalId, "types")


# --- operações ---------------------------------------------------------------------------


def new_entity(doc: Document, gid: str, type_gid: str):
    tstate = ot.read(doc.get(type_gid, "IfcTypeObject"))
    occ_class, _ = od.classes(tstate["definition"])
    element = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class=occ_class)
    element.GlobalId = gid
    return element


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    state = {**default_state(), **copy.deepcopy(op.data)}
    if not state.get("type"):
        raise OpError("o objeto precisa de um tipo")
    element = new_entity(doc, op.id, state["type"])
    try:
        write_state(doc, element, state)
    except Exception:
        _abort(doc, element)
        raise
    return {op.id}


def _abort(doc: Document, element) -> None:
    from brasbim.core.objects import hosting

    hosting.release(doc, element)
    remove_element(doc, element)


def _delete(doc: Document, op: Op) -> set[str]:
    from brasbim.core.objects import hosting

    element = doc.get(op.id)
    if not is_object(element):
        raise OpError(f"{op.id} não é objeto paramétrico")
    gone = {op.id, *(p.GlobalId for p in parts_of(element))}
    hosting.release(doc, element)
    remove_element(doc, element)
    return gone


def _edit(doc: Document, op: Op) -> set[str]:
    element = doc.get(op.id)
    if not is_object(element):
        raise OpError(f"{op.id} não é objeto paramétrico")
    state = read_state(doc, element)
    check_before(op, state)
    unknown = set(op.after or {}) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"object.edit: campos desconhecidos {sorted(unknown)}")
    before_parts = {p.GlobalId for p in parts_of(element)}
    state.update(copy.deepcopy(op.after or {}))
    if "type" in (op.after or {}) and type_of(doc, element) is not None and \
            not element.is_a(od.classes(ot.read(doc.get(state["type"]))["definition"])[0]):
        raise OpError("o tipo novo é de outra classe")
    write_state(doc, element, state)
    return {op.id, *before_parts, *(p.GlobalId for p in parts_of(element))}


register_inverse_pair("object.create", _create, "object.delete", _delete)
register("object.edit", _edit, invert_swap)


def values_of(doc: Document, element) -> dict:
    """Todos os valores calculados da ocorrência (identificador normalizado → valor)."""
    state = read_state(doc, element)
    return resolve(doc, state)[2].values


def label_of(defn: dict, name: str) -> str:
    p = od.param(defn, name)
    return p["label"] if p else name


def key(name: str) -> str:
    return fm.key(name)


def kind_of_type(element_type) -> str | None:
    """Chave da camada padrão (``object:<categoria>``) pelo tipo."""
    if not ot.is_object_type(element_type):
        return None
    return f"object:{ot.definition_of(element_type)['category']}"


def kind_of(element) -> str | None:
    element = parent_of(element)
    return kind_of_type(ifcopenshell.util.element.get_type(element))


def built_of(doc: Document, element) -> Built:
    """Cálculo da ocorrência (de primeiro nível ou aninhada) a partir do que está gravado."""
    params = _params(element)
    if params is None:
        raise OpError(f"{element.GlobalId} não é objeto paramétrico")
    tstate = ot.read(type_of(doc, element))
    stored = ot.stored_values(tstate["definition"], params.get("values") or {}, "occurrence")
    return build(doc, tstate, stored, bool(params.get("mirror")))


def code_of(doc: Document, element) -> str:
    element_type = type_of(doc, element)
    values = ot.read(element_type)["values"] if element_type is not None else {}
    return str(values.get("codigo") or "")
