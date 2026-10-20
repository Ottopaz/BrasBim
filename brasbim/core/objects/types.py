# SPDX-License-Identifier: LGPL-3.0-or-later
"""Tipos de objeto paramétrico (``spec/elementos/objeto-parametrico.md`` §2 e §3.4).

Operações: ``object_type.create`` / ``object_type.delete`` (data: estado completo) e
``object_type.edit`` (before/after: campos de ``STATE_KEYS``, inclusive a definição).

Estado de um tipo::

    {"name": "Cama casal 1,38 × 1,88", "definition": {...},  # definition.py
     "values": {"largura": 1.38, "codigo": "M1"},  # parâmetros de tipo sem fórmula
     "defaults": {"elevacao": 0.0},                # padrões dos de ocorrência
     "library": None}  # ou {"file": "mobiliario.ifc", "object_id": "…", "version": 2}

Gravação: o tipo IFC da categoria (``IfcFurnitureType``…), **sem** ``RepresentationMaps``
(cada ocorrência tem o próprio corpo, §2.3). Pset ``BrasBim_DefinicaoObjeto`` com a
definição e os valores em JSON; Pset ``BrasBim_Parametros`` com os parâmetros de tipo
como propriedades IFC (rótulo → valor); Pset comum com ``Reference`` e as medidas
nominais; ``IfcMaterialConstituentSet`` com um constituinte por papel; origem na
biblioteca por ``IfcRelAssociatesLibrary``.
"""

from __future__ import annotations

import copy
import json

import ifcopenshell.api.material
import ifcopenshell.api.root
import ifcopenshell.util.element

from brasbim.core import guid, materials, props
from brasbim.core.document import Document, OpError
from brasbim.core.objects import definition as od
from brasbim.core.objects import formula as fm
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair

PSET = "BrasBim_DefinicaoObjeto"
VALUES_PSET = "BrasBim_Parametros"
STATE_KEYS = ("name", "definition", "values", "defaults", "library")
TYPE_CLASSES = tuple(v[1] for v in od.CATEGORIES.values())


def default_state() -> dict:
    return {"name": None, "definition": None, "values": {}, "defaults": {}, "library": None}


def is_object_type(entity) -> bool:
    return (entity is not None and entity.is_a("IfcTypeObject") and bool(
        ifcopenshell.util.element.get_pset(entity, PSET, should_inherit=False)))


def all_types(doc: Document) -> list:
    out = []
    for cls in TYPE_CLASSES:
        out += [t for t in doc.ifc.by_type(cls) if is_object_type(t)]
    return sorted(out, key=lambda t: (t.Name or "", t.GlobalId))


def definition_of(element_type) -> dict:
    values = ifcopenshell.util.element.get_pset(element_type, PSET, should_inherit=False)
    if not values:
        raise OpError(f"{element_type.GlobalId} não é tipo de objeto paramétrico")
    return od.normalized(json.loads(values["Definicao"]))


def types_of_definition(doc: Document, object_id: str) -> list:
    return [t for t in all_types(doc) if definition_of(t)["object_id"] == object_id]


def by_name(doc: Document, name: str, type_class: str | None = None):
    """Tipo de objeto com esse nome (os nomes são únicos por classe, §3.4)."""
    for t in all_types(doc):
        if t.Name == name and (type_class is None or t.is_a(type_class)):
            return t
    return None


# --- leitura ---------------------------------------------------------------------------


def _read_library(element_type) -> dict | None:
    for rel in getattr(element_type, "HasAssociations", ()) or ():
        if not rel.is_a("IfcRelAssociatesLibrary"):
            continue
        ref = rel.RelatingLibrary
        info = ref.ReferencedLibrary if ref.is_a("IfcLibraryReference") else ref
        if ref.is_a("IfcLibraryReference") and info is not None:
            try:
                version = int(info.Version or 1)
            except ValueError:
                version = 1
            return {"file": info.Location, "object_id": ref.Identification,
                    "version": version}
    return None


def read(element_type) -> dict:
    values = ifcopenshell.util.element.get_pset(element_type, PSET, should_inherit=False)
    if not values:
        raise OpError(f"{element_type.GlobalId} não é tipo de objeto paramétrico")
    return {"name": element_type.Name,
            "definition": od.normalized(json.loads(values["Definicao"])),
            "values": json.loads(values.get("Valores") or "{}"),
            "defaults": json.loads(values.get("Padroes") or "{}"),
            "library": _read_library(element_type)}


# --- valores -----------------------------------------------------------------------------


def stored_values(defn: dict, values: dict, level: str) -> dict:
    """Só os parâmetros do nível que guardam valor (sem fórmula), pelo identificador da
    definição; o que sobra (parâmetro que sumiu) sai."""
    out = {}
    lookup = {fm.key(k): v for k, v in (values or {}).items()}
    for p in defn["params"]:
        if p["level"] == level and od.editable(p) and fm.key(p["name"]) in lookup:
            out[p["name"]] = lookup[fm.key(p["name"])]
    return out


def evaluate(state: dict, occurrence_values: dict | None = None, level: str = "occurrence"):
    defn = state["definition"]
    return od.evaluate(defn, state["values"], {**state["defaults"], **(occurrence_values or {})},
                       level)


def property_value(ifc, p: dict, value):
    """Propriedade IFC tipada de um parâmetro (§2.2)."""
    kind = p["kind"]
    if kind == "length":
        return ifc.createIfcLengthMeasure(float(value))
    if kind == "angle":
        return ifc.createIfcPlaneAngleMeasure(float(value) * 3.141592653589793 / 180.0)
    if kind == "number":
        return ifc.createIfcReal(float(value))
    if kind == "integer":
        return ifc.createIfcInteger(int(value))
    if kind == "bool":
        return ifc.createIfcBoolean(bool(value))
    if kind == "text" and value == "":
        return None
    return ifc.createIfcLabel(str(value)) if value != "" else None


def write_values_pset(doc: Document, product, defn: dict, values: dict, level: str) -> None:
    """``BrasBim_Parametros``: os parâmetros do nível, pelo rótulo (choice vira lista
    enumerada; ``codigo``/``descricao`` ficam no Pset comum e no tipo)."""
    out, enums = {}, []
    for p in defn["params"]:
        if p["level"] != level or fm.key(p["name"]) in ("codigo", "descricao"):
            continue
        value = values.get(fm.key(p["name"]))
        if value is None:
            continue
        if p["kind"] == "choice":
            enums.append((p, value))
            continue
        prop = property_value(doc.ifc, p, value)
        if prop is not None:
            out[p["label"]] = prop
    if out or enums or ifcopenshell.util.element.get_pset(product, VALUES_PSET,
                                                          should_inherit=False):
        props.write_pset(doc, product, VALUES_PSET, out)
        pset = props.ensure_pset(doc, product, VALUES_PSET)
        for p, value in enums:
            _write_enumerated(doc, pset, p, value)


def _write_enumerated(doc: Document, pset, p: dict, value: str) -> None:
    ifc = doc.ifc
    enum = ifc.createIfcPropertyEnumeration(
        f"{p['label']} ({', '.join(p['options'])})",
        [ifc.createIfcLabel(o) for o in p["options"]], None)
    prop = ifc.createIfcPropertyEnumeratedValue(p["label"], None, [ifc.createIfcLabel(value)],
                                                enum)
    pset.HasProperties = [*(pset.HasProperties or []), prop]


def remove_values_pset(doc: Document, product) -> None:
    found = ifcopenshell.util.element.get_pset(product, VALUES_PSET, should_inherit=False)
    if not found:
        return
    pset = doc.ifc.by_id(found["id"])
    enums = [p.EnumerationReference for p in pset.HasProperties or []
             if p.is_a("IfcPropertyEnumeratedValue") and p.EnumerationReference]
    props.remove_pset(doc, product, VALUES_PSET)
    for e in enums:
        if e.id() and not doc.ifc.get_total_inverses(e):
            doc.ifc.remove(e)


def nominal(defn: dict, box) -> dict:
    """Medidas nominais do Pset comum (§2.1) a partir da caixa que envolve o objeto."""
    if box is None:
        return {}
    x, y, z = box[1] - box[0], box[3] - box[2], box[5] - box[4]
    category = defn["category"]
    if category == "furniture":
        return {"NominalLength": x, "NominalDepth": y, "NominalHeight": z}
    if category == "sanitary":
        return {"NominalLength": x, "NominalWidth": y}
    return {}


def role_materials(defn: dict, values: dict) -> dict[str, str]:
    """Papel → material das peças calculadas (o primeiro material de cada papel)."""
    out = {}
    for s in od.solids(defn, values):
        if s.void or not s.material:
            continue
        out.setdefault(s.role or od.ROLES[defn["category"]][0], s.material)
    return out


def ensure_materials(doc: Document, names) -> None:
    from brasbim.core.walls.types import material_named

    for name in sorted({n for n in names if n}):
        material_named(doc, name)
        materials.ensure_style(doc, name)


def assign_constituents(doc: Document, product, mapping: dict[str, str], owner: str) -> None:
    """``IfcMaterialConstituentSet`` do produto (um constituinte por papel); vazio tira."""
    from brasbim.core.walls.types import material_named

    current = ifcopenshell.util.element.get_material(product, should_inherit=False)
    if current is not None:
        if current.is_a("IfcMaterialConstituentSet") and _same(current, mapping):
            return
        ifcopenshell.api.material.unassign_material(doc.ifc, products=[product])
        if current.is_a("IfcMaterialConstituentSet") and current.id() and \
                not doc.ifc.get_total_inverses(current):
            for c in list(current.MaterialConstituents or []):
                doc.ifc.remove(c)
            doc.ifc.remove(current)
    if not mapping:
        return
    cset = doc.ifc.createIfcMaterialConstituentSet(owner, None, [])
    cset.MaterialConstituents = [
        doc.ifc.createIfcMaterialConstituent(role, None, material_named(doc, name), None, role)
        for role, name in sorted(mapping.items())]
    doc.ifc.create_entity("IfcRelAssociatesMaterial",
                          GlobalId=guid.derived(product.GlobalId, "material"),
                          RelatedObjects=[product], RelatingMaterial=cset)


def _same(cset, mapping: dict) -> bool:
    have = {c.Name: c.Material.Name for c in cset.MaterialConstituents or [] if c.Material}
    return have == mapping


def _write_library(doc: Document, element_type, library: dict | None) -> None:
    for rel in list(getattr(element_type, "HasAssociations", ()) or ()):
        if rel.is_a("IfcRelAssociatesLibrary"):
            ref = rel.RelatingLibrary
            info = ref.ReferencedLibrary if ref.is_a("IfcLibraryReference") else None
            doc.ifc.remove(rel)
            if not doc.ifc.get_total_inverses(ref):
                doc.ifc.remove(ref)
            if info is not None and not doc.ifc.get_total_inverses(info):
                doc.ifc.remove(info)
    if not library:
        return
    ifc = doc.ifc
    file = str(library.get("file") or "")
    info = ifc.createIfcLibraryInformation(file.replace("\\", "/").rsplit("/", 1)[-1] or
                                           "Biblioteca", str(library.get("version") or 1),
                                           None, None, file or None, None)
    ref = ifc.createIfcLibraryReference(None, library.get("object_id"), element_type.Name,
                                        None, None, info)
    ifc.create_entity("IfcRelAssociatesLibrary",
                      GlobalId=guid.derived(element_type.GlobalId, "library"),
                      RelatedObjects=[element_type], RelatingLibrary=ref)


# --- gravação ----------------------------------------------------------------------------


def validate(state: dict) -> None:
    if not str(state.get("name") or "").strip():
        raise OpError("o tipo precisa de um nome")
    defn = state["definition"]
    if defn is None:
        raise OpError("o tipo precisa de uma definição")
    od.validate(defn)
    evaluate(state)  # recusa valores fora dos limites e fórmulas que não fecham


def _check_name(doc: Document, element_type, name: str) -> None:
    for t in doc.ifc.by_type(element_type.is_a()):
        if t != element_type and (t.Name or "").casefold() == name.strip().casefold():
            raise OpError(f"já existe um tipo chamado '{name}'")


def write(doc: Document, element_type, state: dict) -> None:
    state = {**default_state(), **state}
    state["definition"] = od.normalized(state["definition"])
    defn = state["definition"]
    _, type_class = od.classes(defn)
    if not element_type.is_a(type_class):
        raise OpError(f"a categoria do objeto pede {type_class}, o tipo é {element_type.is_a()}")
    validate(state)
    _check_name(doc, element_type, state["name"])
    state["values"] = stored_values(defn, state["values"], "type")
    state["defaults"] = stored_values(defn, state["defaults"], "occurrence")
    element_type.Name = state["name"].strip()
    element_type.PredefinedType = defn["predefined_type"]
    if hasattr(element_type, "ElementType"):
        element_type.ElementType = ((defn.get("element_type") or defn["name"])
                                    if defn["predefined_type"] == "USERDEFINED" else None)
    values = evaluate(state)
    element_type.Description = values.get("descricao") or None
    f = doc.ifc
    props.write_pset(doc, element_type, PSET, {
        "Definicao": f.createIfcText(json.dumps(defn, ensure_ascii=False, sort_keys=True)),
        "Valores": f.createIfcText(json.dumps(state["values"], ensure_ascii=False,
                                              sort_keys=True)),
        "Padroes": f.createIfcText(json.dumps(state["defaults"], ensure_ascii=False,
                                              sort_keys=True)),
    })
    remove_values_pset(doc, element_type)
    write_values_pset(doc, element_type, defn, values, "type")
    found = od.solids(defn, values)
    common = od.CATEGORIES[defn["category"]][2]
    if common is not None:
        common_values = {"Reference": values.get("codigo") or None,
                         **nominal(defn, od.bounds(found))}
        if defn["category"] == "furniture":
            common_values["IsBuiltIn"] = defn["hosting"] == "wall"
        if defn["category"] == "vegetation":
            common_values = {}
        common_values = {k: v for k, v in common_values.items() if v is not None}
        if common_values or ifcopenshell.util.element.get_pset(element_type, common,
                                                               should_inherit=False):
            props.write_pset(doc, element_type, common, common_values)
    mapping = role_materials(defn, values)
    ensure_materials(doc, mapping.values())
    assign_constituents(doc, element_type, mapping, defn["name"])
    _write_library(doc, element_type, state["library"])
    doc.changed.add(element_type.GlobalId)


def remove(doc: Document, element_type) -> None:
    if ifcopenshell.util.element.get_types(element_type):
        raise OpError(f"o tipo {element_type.Name} tem ocorrências")
    _write_library(doc, element_type, None)
    assign_constituents(doc, element_type, {}, "")
    remove_values_pset(doc, element_type)
    ifcopenshell.api.root.remove_product(doc.ifc, product=element_type)


# --- operações ---------------------------------------------------------------------------


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    state = {**default_state(), **copy.deepcopy(op.data)}
    _, type_class = od.classes(od.normalized(state["definition"]))
    element_type = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class=type_class)
    element_type.GlobalId = op.id
    try:
        write(doc, element_type, state)
    except Exception:
        ifcopenshell.api.root.remove_product(doc.ifc, product=element_type)
        raise
    return {op.id}


def _delete(doc: Document, op: Op) -> set[str]:
    element_type = doc.get(op.id, "IfcTypeObject")
    remove(doc, element_type)
    return {op.id}


def _edit(doc: Document, op: Op) -> set[str]:
    element_type = doc.get(op.id, "IfcTypeObject")
    state = read(element_type)
    check_before(op, state)
    unknown = set(op.after or {}) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"object_type.edit: campos desconhecidos {sorted(unknown)}")
    state.update(copy.deepcopy(op.after or {}))
    write(doc, element_type, state)
    return {op.id}


register_inverse_pair("object_type.create", _create, "object_type.delete", _delete)
register("object_type.edit", _edit, invert_swap)
