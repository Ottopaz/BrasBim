# SPDX-License-Identifier: LGPL-3.0-or-later
"""Forma livre (``spec/elementos/forma-livre.md``): peça única de geometria em malha, sem
tipo nem parâmetros.

Operações: ``freeform.create`` / ``freeform.delete`` (data: estado completo) e
``freeform.edit`` (before/after: campos de ``STATE_KEYS``).

Estado::

    {"name": "Poltrona", "category": "furniture", "object_type": "Poltrona",
     "storey": "<GlobalId>", "point": [2.0, 3.0], "elevation": 0.0, "angle": 0.0,
     "parts": [{"name": "Estrutura", "material": "Madeira",
                "vertices": [[x, y, z], ...], "faces": [[i, j, k], ...]}],
     "source": "assistente", "description": "", "recipe": [...] | None}

``point``, ``elevation`` e ``angle`` (graus, anti-horário) põem a peça no pavimento; os
vértices ficam no sistema local dela (origem no ponto de inserção, x para a direita, y
para trás, z para cima). No IFC a malha é o corpo (``Tessellation``, um
``IfcTriangulatedFaceSet`` por parte) e é dele que ``read_state`` a lê de volta; o Pset
``BrasBim_FormaLivre`` guarda o resto. A silhueta vista de cima vai na representação
``FootPrint``, de onde a planta a lê (§7).
"""

from __future__ import annotations

import copy
import json
import math

import ifcopenshell.api.root
import ifcopenshell.util.element
import ifcopenshell.util.schema
import numpy as np

from brasbim.core import materials, props
from brasbim.core.document import Document, OpError, axis_placement, local_placement
from brasbim.core.freeform import mesh
from brasbim.core.objects import definition as od
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair
from brasbim.core.structure import common

PSET = "BrasBim_FormaLivre"
STATE_KEYS = ("name", "category", "object_type", "storey", "point", "elevation", "angle",
              "parts", "source", "description", "recipe")
CLASSES = tuple(v[0] for v in od.CATEGORIES.values())
DEFAULT_NAME = "Forma livre"
_MIN_RING_AREA = 1e-4  # m²: lascas da reunião dos triângulos não entram na silhueta


def default_state() -> dict:
    return {"name": DEFAULT_NAME, "category": "proxy", "object_type": "", "storey": None,
            "point": [0.0, 0.0], "elevation": 0.0, "angle": 0.0, "parts": [],
            "source": "", "description": "", "recipe": None}


def _params(element) -> dict | None:
    values = ifcopenshell.util.element.get_pset(element, PSET, should_inherit=False)
    if not values or "Parametros" not in values:
        return None
    return json.loads(values["Parametros"])


def is_freeform(entity) -> bool:
    return entity is not None and any(entity.is_a(c) for c in CLASSES) \
        and _params(entity) is not None


def all_freeforms(doc: Document) -> list:
    out = []
    for cls in CLASSES:
        out += [e for e in doc.ifc.by_type(cls, include_subtypes=False) if is_freeform(e)]
    return sorted(out, key=lambda e: e.GlobalId)


def kind_of(element) -> str:
    """Chave da camada padrão: a mesma dos objetos da categoria (spec/ui 18 §3.2)."""
    return f"object:{_params(element)['category']}"


def _read_parts(element, meta: list) -> list:
    rep = props.representation(element, "Body")
    items = [i for i in (rep.Items if rep is not None else ()) or ()
             if i.is_a("IfcTriangulatedFaceSet")]
    parts = []
    for i, item in enumerate(items):
        info = meta[i] if i < len(meta) else {}
        vertices = np.round(np.asarray(item.Coordinates.CoordList, dtype=float),
                            mesh.DECIMALS)
        faces = np.asarray(item.CoordIndex, dtype=np.int64) - 1
        parts.append({"name": info.get("name") or "Corpo",
                      "material": info.get("material") or None,
                      "vertices": vertices.tolist(), "faces": faces.tolist()})
    return parts


def read_state(doc: Document, element) -> dict:
    params = _params(element)
    if params is None:
        raise OpError(f"{element.GlobalId} não é forma livre")
    state = default_state()
    state.update({k: copy.deepcopy(params[k]) for k in STATE_KEYS
                  if k in params and k not in ("parts", "storey")})
    container = ifcopenshell.util.element.get_container(element)
    state["storey"] = container.GlobalId if container else None
    state["parts"] = _read_parts(element, params.get("parts") or [])
    return state


def world_parts(element) -> list[tuple[np.ndarray, np.ndarray, str | None]]:
    """(vértices no mundo, faces, material) de cada parte, lidos direto da malha gravada.
    O 3D e os cortes usam isto em vez da triangulação genérica do IFC, que leva segundos
    numa malha grande (§6)."""
    import ifcopenshell.util.placement

    meta = (_params(element) or {}).get("parts") or []
    m = ifcopenshell.util.placement.get_local_placement(element.ObjectPlacement)
    rep = props.representation(element, "Body")
    out = []
    items = [i for i in (rep.Items if rep is not None else ()) or ()
             if i.is_a("IfcTriangulatedFaceSet")]
    for i, item in enumerate(items):
        vertices = np.asarray(item.Coordinates.CoordList, dtype=float)
        faces = np.asarray(item.CoordIndex, dtype=np.int64) - 1
        world = vertices @ m[:3, :3].T + m[:3, 3]
        out.append((world, faces, (meta[i].get("material") if i < len(meta) else None)))
    return out


def footprint(element) -> list[list[tuple[float, float]]]:
    """Silhueta gravada (anéis no sistema local da peça)."""
    rep = props.representation(element, "FootPrint")
    rings = []
    for item in (rep.Items if rep is not None else ()) or ():
        for curve in getattr(item, "Elements", ()) or ():
            if curve.is_a("IfcPolyline"):
                pts = [tuple(p.Coordinates[:2]) for p in curve.Points]
                rings.append(pts[:-1] if len(pts) > 1 and pts[0] == pts[-1] else pts)
    return rings


def to_storey(state: dict, p) -> tuple[float, float]:
    """Ponto local → coordenadas do pavimento."""
    a = math.radians(state["angle"])
    c, s = math.cos(a), math.sin(a)
    return (state["point"][0] + c * p[0] - s * p[1], state["point"][1] + s * p[0] + c * p[1])


def box_of(state: dict) -> dict:
    """Medidas da caixa que envolve a peça (metros) e os limites em cada eixo local."""
    b = mesh.bounds(state["parts"])
    return {"largura": round(b[1] - b[0], 4), "profundidade": round(b[3] - b[2], 4),
            "altura": round(b[5] - b[4], 4), "x": [round(b[0], 4), round(b[1], 4)],
            "y": [round(b[2], 4), round(b[3], 4)], "z": [round(b[4], 4), round(b[5], 4)]}


# --- gravação ----------------------------------------------------------------------------


def validate(state: dict) -> None:
    if not str(state.get("name") or "").strip():
        raise OpError("a forma livre precisa de um nome")
    if state.get("category") not in od.CATEGORIES:
        raise OpError(f"categoria inválida: {state.get('category')!r}")
    if not state.get("storey"):
        raise OpError("a forma livre precisa de um pavimento")
    if len(state.get("point") or []) != 2:
        raise OpError("ponto de inserção inválido")
    mesh.validate(state.get("parts"))


def _clear_styles(doc: Document, element) -> None:
    rep = props.representation(element, "Body")
    for item in (rep.Items if rep is not None else []) or []:
        for styled in [i for i in doc.ifc.get_inverse(item) if i.is_a("IfcStyledItem")]:
            doc.ifc.remove(styled)


def _write_body(doc: Document, element, parts: list) -> None:
    from brasbim.core.objects import types as ot

    ifc = doc.ifc
    _clear_styles(doc, element)
    ot.ensure_materials(doc, [p.get("material") for p in parts])
    items = []
    for part in parts:
        vertices, faces = mesh.arrays(part)
        coords = ifc.createIfcCartesianPointList3D(
            [tuple(float(c) for c in v) for v in np.round(vertices, mesh.DECIMALS)])
        item = ifc.createIfcTriangulatedFaceSet(
            coords, None, bool(mesh.is_closed(part)),
            [tuple(int(k) + 1 for k in f) for f in faces], None)
        style = materials.surface_style(doc, part["material"]) if part.get("material") \
            else None
        if style is not None:
            ifc.createIfcStyledItem(item, [style], None)
        items.append(item)
    props.replace_representation(doc, element, "Body", ifc.createIfcShapeRepresentation(
        doc.body_context, "Body", "Tessellation", items))


def _write_footprint(doc: Document, element, parts: list) -> None:
    ifc = doc.ifc
    curves = []
    for ring in mesh.silhouette(parts):
        x, y = np.asarray(ring).T
        if abs(float(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y))) / 2 \
                < _MIN_RING_AREA:
            continue
        points = [ifc.createIfcCartesianPoint((float(a), float(b))) for a, b in ring]
        curves.append(ifc.createIfcPolyline([*points, points[0]]))
    if curves:
        props.replace_representation(doc, element, "FootPrint", ifc.createIfcShapeRepresentation(
            doc.footprint_context, "FootPrint", "GeometricCurveSet",
            [ifc.createIfcGeometricCurveSet(curves)]))


def _write_materials(doc: Document, element, state: dict) -> None:
    from brasbim.core.objects import types as ot

    mapping = {}
    for part in state["parts"]:
        if part.get("material"):
            mapping.setdefault(part["name"], part["material"])
    ot.assign_constituents(doc, element, mapping, state["name"])


def _set_placement(doc: Document, element, storey, state: dict) -> None:
    a = math.radians(state["angle"])
    direction = (math.cos(a), math.sin(a))
    placement = element.ObjectPlacement
    if placement is None:
        element.ObjectPlacement = local_placement(
            doc.ifc, storey.ObjectPlacement, float(state["elevation"]), state["point"],
            direction)
        return
    old = placement.RelativePlacement
    placement.PlacementRelTo = storey.ObjectPlacement
    placement.RelativePlacement = axis_placement(doc.ifc, state["point"],
                                                 float(state["elevation"]), direction)
    ifcopenshell.util.element.remove_deep2(doc.ifc, old)


def write_state(doc: Document, element, state: dict, geometry: bool = True) -> None:
    """Grava o estado. ``geometry=False``: a malha não mudou (só posição, nome, origem…),
    e o corpo e a silhueta ficam como estão."""
    state = {**default_state(), **state}
    validate(state)
    storey = doc.get(state["storey"], "IfcBuildingStorey")
    if not element.is_a(od.CATEGORIES[state["category"]][0]):
        raise OpError("a categoria nova é de outra classe IFC")
    element.Name = state["name"]
    element.ObjectType = state["object_type"] or None
    if element.is_a("IfcGeographicElement"):
        element.PredefinedType = "VEGETATION"
    else:
        element.PredefinedType = "USERDEFINED" if state["object_type"] else "NOTDEFINED"
    common.assign_container(doc, element, storey)
    _set_placement(doc, element, storey, state)
    if geometry or props.representation(element, "Body") is None:
        _write_body(doc, element, state["parts"])
        _write_footprint(doc, element, state["parts"])
    _write_materials(doc, element, state)
    params = {k: copy.deepcopy(state[k]) for k in STATE_KEYS if k not in ("parts", "storey")}
    params["parts"] = [{"name": p["name"], "material": p.get("material")}
                       for p in state["parts"]]
    values = {"Parametros": doc.ifc.createIfcText(
        json.dumps(params, ensure_ascii=False, sort_keys=True))}
    box = box_of(state)
    for key, label in (("largura", "Largura"), ("profundidade", "Profundidade"),
                       ("altura", "Altura")):
        values[label] = doc.ifc.createIfcPositiveLengthMeasure(max(box[key], 1e-6))
    values["Triangulos"] = doc.ifc.createIfcInteger(mesh.triangle_count(state["parts"]))
    solid = mesh.volume(state["parts"])
    if solid is not None and solid > 0:
        values["Volume"] = doc.ifc.createIfcVolumeMeasure(round(solid, 6))
    props.remove_pset(doc, element, PSET)
    props.write_pset(doc, element, PSET, values)
    doc.changed.add(element.GlobalId)


def remove_element(doc: Document, element) -> None:
    from brasbim.core.objects import types as ot

    doc.changed.add(element.GlobalId)
    ot.assign_constituents(doc, element, {}, "")
    _clear_styles(doc, element)
    common.remove(doc, element)


# --- operações ---------------------------------------------------------------------------


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    state = {**default_state(), **copy.deepcopy(op.data)}
    validate(state)
    element = ifcopenshell.api.root.create_entity(
        doc.ifc, ifc_class=od.CATEGORIES[state["category"]][0])
    element.GlobalId = op.id
    try:
        write_state(doc, element, state)
    except Exception:
        remove_element(doc, element)
        raise
    return {op.id}


def _delete(doc: Document, op: Op) -> set[str]:
    element = doc.get(op.id)
    if not is_freeform(element):
        raise OpError(f"{op.id} não é forma livre")
    remove_element(doc, element)
    return {op.id}


def _edit(doc: Document, op: Op) -> set[str]:
    element = doc.get(op.id)
    if not is_freeform(element):
        raise OpError(f"{op.id} não é forma livre")
    state = read_state(doc, element)
    check_before(op, state)
    after = op.after or {}
    unknown = set(after) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"freeform.edit: campos desconhecidos {sorted(unknown)}")
    state.update(copy.deepcopy(after))
    if "category" in after and not element.is_a(od.CATEGORIES.get(
            state["category"], ("",))[0]):
        validate(state)
        element = ifcopenshell.util.schema.reassign_class(
            doc.ifc, element, od.CATEGORIES[state["category"]][0])
    write_state(doc, element, state, geometry="parts" in after)
    return {op.id}


register_inverse_pair("freeform.create", _create, "freeform.delete", _delete)
register("freeform.edit", _edit, invert_swap)
