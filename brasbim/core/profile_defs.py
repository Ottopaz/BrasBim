# SPDX-License-Identifier: LGPL-3.0-or-later
"""Perfis do projeto: seções desenhadas, usadas por vários elementos (spec/ui 41 §4, §4.1).

Estado de um perfil::

    {"name": "Viga T", "uses": ["beam", "column"],
     "stretch_x": 0.10, "stretch_y": None,
     "parts": [{"material": "Concreto", "role": "core",
                "outline": [[x, y], ...], "holes": [[[x, y], ...]]}]}

Coordenadas em metros no plano do desenho; a origem (0, 0) é o ponto de inserção (eixo
da viga, ponto do pilar). ``stretch_x``/``stretch_y``: linhas de esticar (x = constante,
y = constante); o que está além delas anda quando a largura ou a altura do elemento
mudam. Sem a linha, a medida naquela direção é fixa.

Gravação: um ``IfcMaterialProfileSet`` sem dono, com um ``IfcMaterialProfile`` por parte
(material, ``IfcArbitraryClosedProfileDef`` ou ``...WithVoids``, ``Category``
``LoadBearing``/``Finish``) e o Pset ``BrasBim_Perfil`` (``IfcMaterialProperties``):
``Identificador``, ``Usos``, ``EsticarX``, ``EsticarY``.

Operações ``profile_def.create``/``delete`` (data: estado completo) e
``profile_def.edit`` (before/after). ``id`` = o ``Identificador`` (o conjunto de
materiais não tem GlobalId). Editar refaz os tipos que usam o perfil.
"""

from __future__ import annotations

import copy

import ifcopenshell.api.material
import ifcopenshell.api.pset
import ifcopenshell.util.element
from shapely.geometry import Polygon
from shapely.ops import unary_union

from brasbim.core import guid
from brasbim.core.document import Document, OpError
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair
from brasbim.core.ops.history import Transaction

PSET = "BrasBim_Perfil"
USES = ("wall", "beam", "column", "railing", "edge", "path")
USE_LABEL = {"wall": "Parede", "beam": "Viga", "column": "Pilar", "railing": "Guarda-corpo",
             "edge": "Borda de laje ou cobertura", "path": "Caminho livre"}
ROLES = ("core", "finish")
_CATEGORY = {"core": "LoadBearing", "finish": "Finish"}
MIN_AREA = 1e-6  # m²
TOL = 1e-6


# --- geometria (sem IFC) ---------------------------------------------------------------


def _polygon(part: dict) -> Polygon:
    return Polygon(part["outline"], part.get("holes") or [])


def bounds(parts: list[dict]) -> tuple[float, float, float, float]:
    """(xmin, ymin, xmax, ymax) de todas as partes."""
    xs = [p[0] for part in parts for p in part["outline"]]
    ys = [p[1] for part in parts for p in part["outline"]]
    return min(xs), min(ys), max(xs), max(ys)


def nominal(state: dict) -> tuple[float, float]:
    """(largura, altura) do desenho, sem esticar."""
    x0, y0, x1, y1 = bounds(state["parts"])
    return x1 - x0, y1 - y0


def validate(state: dict) -> None:
    if not str(state.get("name") or "").strip():
        raise OpError("o perfil precisa de um nome")
    uses = state.get("uses") or []
    if not uses or any(u not in USES for u in uses):
        raise OpError(f"usos inválidos: {uses!r}")
    parts = state.get("parts") or []
    if not parts:
        raise OpError("o perfil precisa de pelo menos uma parte")
    shapes = []
    for i, part in enumerate(parts, 1):
        if part.get("role") not in ROLES:
            raise OpError(f"parte {i}: papel inválido {part.get('role')!r}")
        if not part.get("material"):
            raise OpError(f"parte {i}: falta o material")
        if len(part.get("outline") or []) < 3:
            raise OpError(f"parte {i}: o contorno precisa de 3 pontos ou mais")
        poly = _polygon(part)
        if not poly.is_valid or poly.area < MIN_AREA:
            raise OpError(f"parte {i}: contorno cruzado ou sem área")
        shapes.append(poly)
    for i, a in enumerate(shapes):
        for j in range(i + 1, len(shapes)):
            if a.intersection(shapes[j]).area > MIN_AREA:
                raise OpError(f"as partes {i + 1} e {j + 1} se sobrepõem")
    x0, y0, x1, y1 = bounds(parts)
    for key, low, high in (("stretch_x", x0, x1), ("stretch_y", y0, y1)):
        line = state.get(key)
        if line is not None and not low < line < high:
            raise OpError("a linha de esticar tem de cruzar o perfil")


def stretched(state: dict, width: float, height: float) -> list[dict]:
    """Partes com a largura e a altura pedidas, movendo o que está além das linhas de
    esticar. Sem linha numa direção, a medida tem de ser a do desenho."""
    w0, h0 = nominal(state)
    dx, dy = width - w0, height - h0
    for delta, key, what in ((dx, "stretch_x", "largura"), (dy, "stretch_y", "altura")):
        if abs(delta) > TOL and state.get(key) is None:
            raise OpError(f"o perfil {state['name']!r} não estica na {what}")
    sx, sy = state.get("stretch_x"), state.get("stretch_y")

    def move(p):
        x, y = p
        return [x + (dx if sx is not None and x > sx else 0.0),
                y + (dy if sy is not None and y > sy else 0.0)]

    parts = []
    for part in state["parts"]:
        new = {**part, "outline": [move(p) for p in part["outline"]],
               "holes": [[move(p) for p in ring] for ring in part.get("holes") or []]}
        if not _polygon(new).is_valid or _polygon(new).area < MIN_AREA:
            raise OpError(f"o perfil {state['name']!r} não encolhe tanto")
        parts.append(new)
    return parts


def area(parts: list[dict]) -> float:
    return sum(_polygon(p).area for p in parts)


def union(parts: list[dict]):
    return unary_union([_polygon(p) for p in parts])


# --- IFC -------------------------------------------------------------------------------


def _closed_curve(ifc, ring):
    pts = ifc.createIfcCartesianPointList2D([(float(x), float(y)) for x, y in ring])
    index = tuple(range(1, len(ring) + 1)) + (1,)
    return ifc.createIfcIndexedPolyCurve(pts, [ifc.createIfcLineIndex(index)], False)


def write_part_profile(ifc, part: dict, name: str | None = None):
    """``IfcArbitraryClosedProfileDef`` (ou ``...WithVoids``) de uma parte."""
    outer = _closed_curve(ifc, part["outline"])
    holes = part.get("holes") or []
    if holes:
        return ifc.createIfcArbitraryProfileDefWithVoids(
            "AREA", name, outer, [_closed_curve(ifc, h) for h in holes])
    return ifc.createIfcArbitraryClosedProfileDef("AREA", name, outer)


def _ring(curve) -> list[list[float]]:
    if curve.is_a("IfcIndexedPolyCurve"):
        pts = [list(map(float, p)) for p in curve.Points.CoordList]
    else:  # IfcPolyline
        pts = [list(map(float, p.Coordinates)) for p in curve.Points]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts.pop()
    return pts


def read_part_profile(profile) -> tuple[list, list]:
    holes = [_ring(c) for c in profile.InnerCurves] if profile.is_a(
        "IfcArbitraryProfileDefWithVoids") else []
    return _ring(profile.OuterCurve), holes


def read_parts(material_profiles) -> list[dict]:
    parts = []
    for mp in material_profiles or []:
        outline, holes = read_part_profile(mp.Profile)
        parts.append({"material": mp.Material.Name if mp.Material else None,
                      "role": "finish" if mp.Category == "Finish" else "core",
                      "outline": outline, "holes": holes})
    return parts


def write_parts(doc: Document, profile_set, parts: list[dict], name: str) -> list:
    """Uma ``IfcMaterialProfile`` por parte; devolve os perfis criados."""
    from brasbim.core.walls import types as wall_types  # evita import circular

    made = []
    for i, part in enumerate(parts, 1):
        profile = write_part_profile(doc.ifc, part, f"{name} {i}")
        mp = ifcopenshell.api.material.add_profile(
            doc.ifc, profile_set=profile_set,
            material=wall_types.material_named(doc, part["material"]), profile=profile)
        mp.Category = _CATEGORY[part["role"]]
        made.append(profile)
    return made


def remove_parts(doc: Document, profile_set) -> list:
    """Tira as ``IfcMaterialProfile`` do conjunto; devolve os perfis que ficaram soltos
    (podem ainda estar no ``IfcCompositeProfileDef`` de algum corpo)."""
    old = []
    for mp in list(profile_set.MaterialProfiles or []):
        old.append(mp.Profile)
        ifcopenshell.api.material.remove_profile(doc.ifc, profile=mp)
    return [p for p in old if p is not None]


def drop_profiles(doc: Document, profiles) -> None:
    """Apaga os perfis (e as curvas deles) que ninguém mais usa."""
    for profile in profiles:
        try:
            if profile.id() and not doc.ifc.get_total_inverses(profile):
                ifcopenshell.util.element.remove_deep2(doc.ifc, profile)
        except RuntimeError:
            continue  # já saiu junto com o perfil composto que o usava


def _pset_values(entity) -> dict:
    return ifcopenshell.util.element.get_pset(entity, PSET) or {}


def all_defs(doc: Document) -> list:
    """Conjuntos que são perfis do projeto, por nome."""
    found = [s for s in doc.ifc.by_type("IfcMaterialProfileSet")
             if _pset_values(s).get("Identificador")]
    return sorted(found, key=lambda s: (s.Name or "").lower())


def find(doc: Document, def_id: str):
    return next((s for s in all_defs(doc) if _pset_values(s)["Identificador"] == def_id), None)


def get(doc: Document, def_id: str):
    found = find(doc, def_id)
    if found is None:
        raise OpError(f"perfil {def_id} não existe")
    return found


def id_of(profile_set) -> str:
    return _pset_values(profile_set)["Identificador"]


def read_state(profile_set) -> dict:
    values = _pset_values(profile_set)
    uses = [u for u in (values.get("Usos") or "").split(";") if u]
    return {"name": profile_set.Name, "uses": uses,
            "stretch_x": values.get("EsticarX"), "stretch_y": values.get("EsticarY"),
            "parts": read_parts(profile_set.MaterialProfiles)}


def state(doc: Document, def_id: str) -> dict:
    return read_state(get(doc, def_id))


def _write_pset(doc: Document, profile_set, def_id: str, state_: dict) -> None:
    pset = next((d for d in getattr(profile_set, "HasProperties", None) or []
                 if d.Name == PSET), None)
    if pset is None:
        pset = ifcopenshell.api.pset.add_pset(doc.ifc, product=profile_set, name=PSET)
    ifcopenshell.api.pset.edit_pset(doc.ifc, pset=pset, properties={
        "Identificador": def_id, "Usos": ";".join(state_["uses"]),
        "EsticarX": state_.get("stretch_x"), "EsticarY": state_.get("stretch_y")})


def users(doc: Document, def_id: str) -> list:
    """Tipos (de qualquer elemento) que usam o perfil."""
    from brasbim.core.structure import types as st_types  # evita import circular

    return [t for t in doc.ifc.by_type("IfcTypeObject") if st_types.profile_def_of(t) == def_id]


def _names(doc: Document, skip=None) -> set[str]:
    return {s.Name for s in all_defs(doc) if s is not skip}


def _check_name(doc: Document, name: str, skip=None) -> None:
    if name in _names(doc, skip):
        raise OpError(f"já existe um perfil chamado {name!r}")


def _create(doc: Document, op: Op) -> set[str]:
    if find(doc, op.id) is not None:
        raise OpError(f"perfil {op.id} já existe")
    data = op.data
    validate(data)
    _check_name(doc, data["name"])
    profile_set = ifcopenshell.api.material.add_material_set(
        doc.ifc, name=data["name"], set_type="IfcMaterialProfileSet")
    write_parts(doc, profile_set, data["parts"], data["name"])
    _write_pset(doc, profile_set, op.id, data)
    return set()


def _delete(doc: Document, op: Op) -> set[str]:
    profile_set = get(doc, op.id)
    if users(doc, op.id):
        raise OpError(f"o perfil {profile_set.Name!r} está em uso por tipos")
    drop_profiles(doc, remove_parts(doc, profile_set))
    for definition in list(getattr(profile_set, "HasProperties", None) or []):
        for prop in list(definition.Properties or []):
            doc.ifc.remove(prop)
        doc.ifc.remove(definition)
    ifcopenshell.api.material.remove_material_set(doc.ifc, material=profile_set)
    return set()


def _edit(doc: Document, op: Op) -> set[str]:
    from brasbim.core.structure import types as st_types  # evita import circular

    profile_set = get(doc, op.id)
    current = read_state(profile_set)
    check_before(op, current)
    after = op.after or {}
    current.update(copy.deepcopy(after))
    validate(current)
    if "name" in after:
        _check_name(doc, current["name"], skip=profile_set)
        profile_set.Name = current["name"]
    if "parts" in after:
        drop_profiles(doc, remove_parts(doc, profile_set))
        write_parts(doc, profile_set, current["parts"], current["name"])
    _write_pset(doc, profile_set, op.id, current)
    from brasbim.core.walls import types as wall_types

    dirty = set()
    for element_type in users(doc, op.id):
        module = wall_types if element_type.is_a("IfcWallType") else st_types
        module.refresh_profile_def(doc, element_type, current)
        dirty.add(element_type.GlobalId)
    return dirty


register_inverse_pair("profile_def.create", _create, "profile_def.delete", _delete)
register("profile_def.edit", _edit, invert_swap)


# --- comandos ---------------------------------------------------------------------------


def _normal_parts(parts) -> list[dict]:
    """Partes como o IFC devolve: pontos em ``float`` e ``holes`` sempre presente."""
    def ring(points):
        return [[float(x), float(y)] for x, y in points]

    return [{"material": p["material"], "role": p["role"], "outline": ring(p["outline"]),
             "holes": [ring(h) for h in p.get("holes") or []]} for p in parts or []]


def create(doc: Document, state_: dict) -> Transaction:
    """Novo perfil; o id fica em ``tx.ops[0].id``."""
    data = copy.deepcopy(state_)
    data.setdefault("stretch_x", None)
    data.setdefault("stretch_y", None)
    data["parts"] = _normal_parts(data.get("parts"))
    validate(data)
    _check_name(doc, data["name"])
    return Transaction(f"Criar perfil {data['name']}", [Op("profile_def.create", guid.new(),
                                                           data=data)])


def edit(doc: Document, def_id: str, **changes) -> Transaction:
    current = state(doc, def_id)
    unknown = set(changes) - set(current)
    if unknown:
        raise OpError(f"campos desconhecidos: {sorted(unknown)}")
    if "parts" in changes:
        changes["parts"] = _normal_parts(changes["parts"])
    before = {k: current[k] for k in changes}
    return Transaction(f"Editar perfil {current['name']}",
                       [Op("profile_def.edit", def_id, before=before,
                           after=copy.deepcopy(changes))])


def delete(doc: Document, def_id: str) -> Transaction:
    current = state(doc, def_id)
    if users(doc, def_id):
        raise OpError(f"o perfil {current['name']!r} está em uso por tipos")
    return Transaction(f"Excluir perfil {current['name']}",
                       [Op("profile_def.delete", def_id, data=current)])


def for_use(doc: Document, use: str) -> list:
    """Perfis marcados para ``use`` (a lista de cada ferramenta)."""
    return [s for s in all_defs(doc) if use in read_state(s)["uses"]]
