# SPDX-License-Identifier: LGPL-3.0-or-later
"""Cobertura simples (``IfcRoof`` agregando uma ``IfcSlab`` ``ROOF`` por água),
``spec/elementos/cobertura.md``.

Operações: ``roof.create`` / ``roof.delete`` (data: estado completo) e ``roof.edit``
(before/after: campos de ``STATE_KEYS`` alterados).

Estado::

    {"name": "Cobertura 1", "type": "<GlobalId do IfcSlabType ROOF>",
     "storey": "<GlobalId>", "outline": [[0, 0], [10, 0], [10, 6], [0, 6]],
     "shape": "gable", "slope": 30.0, "overhang": 0.6, "base_height": 2.8, "side": 0,
     "common": {}, "parts": ["<GlobalId da água 1>", "<água 2>"], "foreign": None}

``outline`` é o contorno de apoio (anti-horário), ``slope`` a inclinação em %,
``base_height`` a cota da face de baixo sobre o contorno (§3.1) e ``side`` o índice do
lado mais baixo (uma água) ou paralelo à cumeeira (duas águas). Os parâmetros ficam em
JSON no Pset ``BrasBim_Cobertura``; as peças são refeitas a partir deles a cada gravação.

Geometria (§6): cada água é o plano que passa por um lado do contorno na cota de apoio e
sobe para dentro com a declividade. A superfície do telhado é a mais baixa das águas
participantes em cada ponto; num contorno convexo, isso dá a divisão em águas (cumeeira e
espigões) sem calcular o esqueleto. Cada peça fica no plano da sua água, com o perfil na
face de cima e a extrusão perpendicular, para baixo.
"""

from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass

import ifcopenshell.api.aggregate
import ifcopenshell.api.root
import ifcopenshell.util.element

from brasbim.core import guid, props
from brasbim.core.document import Document, OpError, axis_placement, local_placement
from brasbim.core.ops.base import (
    Op,
    check_before,
    invert_swap,
    register,
    register_derive,
    register_inverse_pair,
)
from brasbim.core.structure import common, slabs
from brasbim.core.structure import types as st_types

PSET = "BrasBim_Cobertura"
COMMON_PSET = "Pset_RoofCommon"
PART_COMMON = "Pset_SlabCommon"
SHAPES = ("flat", "shed", "gable", "hip")
SHAPE_NAMES = {"flat": "plana", "shed": "uma água", "gable": "duas águas",
               "hip": "quatro águas"}
PREDEFINED = {"flat": "FLAT_ROOF", "shed": "SHED_ROOF", "gable": "GABLE_ROOF",
              "hip": "HIP_ROOF"}
PART_COUNT = {"flat": 1, "shed": 1, "gable": 2, "hip": 4}
DEFAULT_SLOPE = 30.0  # % (§3.1, CG)
DEFAULT_OVERHANG = 0.60  # m
DEFAULT_BASE = 2.80  # m, sem paredes no pavimento
MAX_OVERHANG = 2.0
MIN_SLOPE, MAX_SLOPE = 1.0, 100.0
STATE_KEYS = ("name", "type", "storey", "outline", "shape", "slope", "overhang",
              "base_height", "side", "common", "parts", "foreign")
_EPS = 1e-9
RECT_ONLY = ("Duas e quatro águas só com contorno retangular; use uma água, plana ou "
             "várias coberturas")


def default_state() -> dict:
    return {"name": None, "shape": "gable", "slope": DEFAULT_SLOPE,
            "overhang": DEFAULT_OVERHANG, "base_height": DEFAULT_BASE, "side": None,
            "common": {}, "parts": [], "foreign": None}


# --- quem é cobertura --------------------------------------------------------------------


def is_roof(entity) -> bool:
    """Cobertura do BrasBim (com os parâmetros); a de outra origem fica como está."""
    return (entity is not None and entity.is_a("IfcRoof")
            and bool(ifcopenshell.util.element.get_pset(entity, PSET, should_inherit=False)))


def roof_of(entity):
    """A cobertura do BrasBim de que ``entity`` é peça, ou ``None``."""
    for rel in getattr(entity, "Decomposes", None) or ():
        if rel.is_a("IfcRelAggregates") and is_roof(rel.RelatingObject):
            return rel.RelatingObject
    return None


def is_part(entity) -> bool:
    """Água da cobertura, ou patamar da escada (escada-terreno.md §2.1): lajes que não
    entram nas listas de lajes; quem responde por elas é a cobertura ou a escada."""
    if entity is None or not entity.is_a("IfcSlab"):
        return False
    if roof_of(entity) is not None:
        return True
    from brasbim.core.structure import stairs

    return stairs.stair_of(entity) is not None


def parts_of(roof) -> list:
    state = _params(roof)
    doc_parts = {p.GlobalId: p for rel in roof.IsDecomposedBy or ()
                 for p in rel.RelatedObjects}
    return [doc_parts[g] for g in state.get("parts", []) if g in doc_parts]


def all_roofs(doc: Document) -> list:
    return sorted((r for r in doc.ifc.by_type("IfcRoof") if is_roof(r)),
                  key=lambda r: r.GlobalId)


# --- geometria ---------------------------------------------------------------------------


def clean(outline) -> list[list[float]]:
    """Contorno de apoio limpo, anti-horário (mesmas regras do contorno da laje)."""
    try:
        return slabs.clean(outline)
    except OpError as e:
        raise OpError(str(e).replace("da laje", "da cobertura")) from None


def is_rectangle(outline) -> bool:
    return slabs.rectangle_sides(outline) is not None


def _unit(a, b) -> tuple[float, float]:
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy)
    return dx / n, dy / n


def _meet(p, d, q, e):
    det = d[0] * e[1] - d[1] * e[0]
    if abs(det) < 1e-12:
        return None
    t = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / det
    return (p[0] + t * d[0], p[1] + t * d[1])


def offset_outline(outline, distance: float) -> list[tuple[float, float]]:
    """Contorno afastado ``distance`` para fora, com os cantos em esquadro (o contorno
    é anti-horário: fora fica à direita de cada lado)."""
    pts = [tuple(p) for p in outline]
    if distance <= _EPS:
        return pts
    n = len(pts)
    lines = []
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        ux, uy = _unit(a, b)
        lines.append(((a[0] + uy * distance, a[1] - ux * distance), (ux, uy)))
    out = []
    for i in range(n):
        (p, d), (q, e) = lines[i - 1], lines[i]
        out.append(_meet(p, d, q, e) or q)
    return out


def longest_side(outline) -> int:
    n = len(outline)
    lengths = [math.dist(outline[i], outline[(i + 1) % n]) for i in range(n)]
    return max(range(n), key=lambda i: (lengths[i] - 1e-9 * i))


def _planes(state: dict) -> list[int]:
    shape, side = state["shape"], state["side"]
    if shape == "flat":
        return []
    if shape == "shed":
        return [side]
    if shape == "gable":
        return [side, (side + 2) % 4]
    return list(range(len(state["outline"])))


@dataclass
class Face:
    """Uma água: ``ring`` em planta (anti-horário), o lado que a gera (``None`` na
    plana), a origem e a normal para dentro desse lado."""

    ring: list[tuple[float, float]]
    side: int | None
    origin: tuple[float, float]
    inward: tuple[float, float]


def _rise(face_or_plane, p) -> float:
    origin, inward = face_or_plane
    return (p[0] - origin[0]) * inward[0] + (p[1] - origin[1]) * inward[1]


def _clip(ring, f) -> list[tuple[float, float]]:
    """Parte do polígono convexo onde ``f(p) <= 0`` (Sutherland–Hodgman)."""
    out = []
    n = len(ring)
    for i in range(n):
        p, q = ring[i], ring[(i + 1) % n]
        fp, fq = f(p), f(q)
        if fp <= _EPS:
            out.append(p)
        if (fp < -_EPS < fq) or (fq < -_EPS < fp):
            t = fp / (fp - fq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    clean_ = []
    for p in out:
        if not clean_ or math.dist(clean_[-1], p) > 1e-7:
            clean_.append(p)
    if len(clean_) > 1 and math.dist(clean_[0], clean_[-1]) <= 1e-7:
        clean_.pop()
    return clean_


def _area(ring) -> float:
    n = len(ring)
    return sum(ring[i][0] * ring[(i + 1) % n][1] - ring[(i + 1) % n][0] * ring[i][1]
               for i in range(n)) / 2.0


def faces(state: dict) -> list[Face]:
    """As águas da cobertura, na ordem dos lados que as geram (§6)."""
    outline = [tuple(p) for p in state["outline"]]
    eave = offset_outline(outline, float(state["overhang"]))
    sides = _planes(state)
    if not sides:
        return [Face(eave, None, outline[0], (0.0, 0.0))]
    n = len(outline)
    planes = {}
    for k in sides:
        a, b = outline[k], outline[(k + 1) % n]
        ux, uy = _unit(a, b)
        planes[k] = (a, (-uy, ux))
    out = []
    for k in sides:
        ring = list(eave)
        for j in sides:
            if j != k:
                ring = _clip(ring, lambda p, k=k, j=j: _rise(planes[k], p) - _rise(planes[j], p))
            if len(ring) < 3:
                break
        if len(ring) >= 3 and abs(_area(ring)) > 1e-9:
            out.append(Face(ring, k, *planes[k]))
    return out


def eave_outline(state: dict) -> list[tuple[float, float]]:
    return offset_outline([tuple(p) for p in state["outline"]], float(state["overhang"]))


def bottom_z(state: dict, face: Face, p) -> float:
    """Cota da face de baixo da água no ponto ``p`` (em relação ao pavimento)."""
    if face.side is None:
        return float(state["base_height"])
    return float(state["base_height"]) + float(state["slope"]) / 100.0 * _rise(
        (face.origin, face.inward), p)


def ridge_lines(state: dict) -> list[list[tuple[float, float]]]:
    """Cumeeira e espigões em planta: os lados comuns a duas águas."""
    found = faces(state)
    out = []
    for i, f in enumerate(found):
        for g in found[i + 1:]:
            common_pts = [p for p in f.ring
                          if any(math.dist(p, q) <= 1e-6 for q in g.ring)]
            if len(common_pts) >= 2:
                a = common_pts[0]
                b = max(common_pts[1:], key=lambda q: math.dist(a, q))
                if math.dist(a, b) > 1e-6:
                    out.append([a, b])
    return out


def slope_angle(state: dict) -> float:
    """Ângulo da água com a horizontal, em radianos (0 na plana)."""
    return 0.0 if state["shape"] == "flat" else math.atan(float(state["slope"]) / 100.0)


def projected_area(state: dict) -> float:
    return abs(_area(eave_outline(state)))


def face_area(state: dict, face: Face) -> float:
    """Área inclinada da água (área em planta ÷ cos α)."""
    a = abs(_area(face.ring))
    return a if face.side is None else a / math.cos(slope_angle(state))


# --- validação ---------------------------------------------------------------------------


def validate(state: dict) -> None:
    if state["shape"] not in SHAPES:
        raise OpError(f"forma de cobertura inválida: {state['shape']!r}")
    outline = state["outline"]
    n = len(outline)
    if state["shape"] in ("gable", "hip") and not is_rectangle(outline):
        raise OpError(RECT_ONLY)
    if state["shape"] != "flat" and not (
            MIN_SLOPE - 1e-9 <= float(state["slope"]) <= MAX_SLOPE + 1e-9):
        raise OpError(f"a inclinação deve ficar entre {MIN_SLOPE:.0f} e "
                          f"{MAX_SLOPE:.0f} %")
    if not -1e-9 <= float(state["overhang"]) <= MAX_OVERHANG + 1e-9:
        raise OpError(f"o beiral deve ficar entre 0 e {MAX_OVERHANG:.0f} m")
    if state["shape"] in ("shed", "gable"):
        side = state["side"]
        if not isinstance(side, int) or isinstance(side, bool) or not 0 <= side < n:
            raise OpError(f"lado inválido: {side!r}")
    if len(state["parts"]) != PART_COUNT[state["shape"]]:
        raise OpError(f"a cobertura {SHAPE_NAMES[state['shape']]} tem "
                      f"{PART_COUNT[state['shape']]} peça(s)")
    if len(set(state["parts"])) != len(state["parts"]):
        raise OpError("peças repetidas na cobertura")


def normalized(state: dict) -> dict:
    """Estado com o contorno limpo, o lado padrão (o maior) e os números como float."""
    state = copy.deepcopy(state)
    state["outline"] = clean(state["outline"])
    state["slope"] = float(state["slope"])
    state["overhang"] = float(state["overhang"])
    state["base_height"] = float(state["base_height"])
    if state["shape"] in ("shed", "gable"):
        if state["side"] is None:
            state["side"] = longest_side(state["outline"])
    else:
        state["side"] = None
    return state


# --- leitura -----------------------------------------------------------------------------


def _params(roof) -> dict:
    values = ifcopenshell.util.element.get_pset(roof, PSET, should_inherit=False) or {}
    if "Parametros" not in values:
        raise OpError(f"cobertura {roof.GlobalId} sem parâmetros")
    return json.loads(values["Parametros"])


def read_state(doc: Document, roof) -> dict:
    state = {**default_state(), **_params(roof)}
    container = ifcopenshell.util.element.get_container(roof)
    state.update(name=roof.Name, storey=container.GlobalId if container else None)
    values = ifcopenshell.util.element.get_pset(roof, COMMON_PSET, should_inherit=False) or {}
    values = {k: v for k, v in values.items() if k != "id"}
    if isinstance(values.get("Status"), (list, tuple)):
        values["Status"] = values["Status"][0] if values["Status"] else None
    defaults = _common_defaults(doc.find(state["type"]) if state["type"] else None)
    state["common"] = {k: v for k, v in values.items() if defaults.get(k) != v}
    state["foreign"] = None
    return state


def thickness(doc: Document, state: dict) -> float:
    return st_types.slab_thickness(doc.get(state["type"], "IfcSlabType"))


# --- gravação ----------------------------------------------------------------------------


def _common_defaults(slab_type) -> dict:
    return {"Reference": slab_type.Name if slab_type is not None else None,
            "Status": "NEW", "IsExternal": True}


def _write_common(doc: Document, element, pset: str, values: dict) -> None:
    values = {k: v for k, v in values.items() if v is not None}
    if values.get("Status") is not None:
        values["Status"] = [values["Status"]]
    props.write_pset(doc, element, pset, values)


def _point3(ifc, p):
    return ifc.createIfcCartesianPoint(tuple(float(c) for c in p))


def _part_frame(state: dict, face: Face, t: float):
    """(origem no topo, eixo x, eixo y, normal) da peça, em coordenadas do pavimento."""
    i = float(state["slope"]) / 100.0 if face.side is not None else 0.0
    if face.side is None:
        ex, ey, ez = (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)
    else:
        nx, ny = face.inward
        s = math.sqrt(1.0 + i * i)
        ex = (ny, -nx, 0.0)  # ao longo do lado (o lado vai de a para b: ux = ny, uy = -nx)
        ey = (nx / s, ny / s, i / s)  # morro acima, no plano
        ez = (-i * nx / s, -i * ny / s, 1.0 / s)
    lift = t * math.sqrt(1.0 + i * i)  # da face de baixo à de cima, na vertical

    def top(p):
        return (p[0], p[1], bottom_z(state, face, p) + lift)

    return top, ex, ey, ez


def _part_body(doc: Document, part, state: dict, face: Face, t: float, origin3) -> list:
    """Corpo da peça e o anel 3D da face de cima (coordenadas do pavimento)."""
    ifc = doc.ifc
    top, ex, ey, ez = _part_frame(state, face, t)
    ring3 = [top(p) for p in face.ring]
    o = ring3[0]

    def local(q):
        d = (q[0] - o[0], q[1] - o[1], q[2] - o[2])
        return (d[0] * ex[0] + d[1] * ex[1] + d[2] * ex[2],
                d[0] * ey[0] + d[1] * ey[1] + d[2] * ey[2])

    pts = [ifc.createIfcCartesianPoint(tuple(float(c) for c in local(q))) for q in ring3]
    profile = ifc.createIfcArbitraryClosedProfileDef(
        "AREA", None, ifc.createIfcPolyline([*pts, pts[0]]))
    solid = ifc.createIfcExtrudedAreaSolid(
        profile, ifc.createIfcAxis2Placement3D(ifc.createIfcCartesianPoint((0.0, 0.0, -t)),
                                               None, None),
        ifc.createIfcDirection((0.0, 0.0, 1.0)), float(t))
    rep = ifc.createIfcShapeRepresentation(doc.body_context, "Body", "SweptSolid", [solid])
    props.replace_representation(doc, part, "Body", rep)
    rel = (o[0] - origin3[0], o[1] - origin3[1], o[2] - origin3[2])
    placement = ifc.createIfcAxis2Placement3D(
        _point3(ifc, rel), ifc.createIfcDirection(ez), ifc.createIfcDirection(ex))
    roof_placement = roof_of(part).ObjectPlacement
    if part.ObjectPlacement is None:
        part.ObjectPlacement = ifc.createIfcLocalPlacement(roof_placement, placement)
    else:
        old = part.ObjectPlacement.RelativePlacement
        part.ObjectPlacement.PlacementRelTo = roof_placement
        part.ObjectPlacement.RelativePlacement = placement
        ifcopenshell.util.element.remove_deep2(ifc, old)
    return ring3


def _sync_parts(doc: Document, roof, gids: list[str]) -> list:
    """Peças com os GlobalIds dados (cria as que faltam, apaga as que sobram)."""
    current = {p.GlobalId: p for rel in roof.IsDecomposedBy or () for p in rel.RelatedObjects
               if p.is_a("IfcSlab")}
    for gid, part in current.items():
        if gid not in gids:
            doc.changed.add(gid)
            common.remove(doc, part)
    out = []
    for gid in gids:
        part = current.get(gid)
        if part is None:
            if doc.find(gid) is not None:
                raise OpError(f"GlobalId {gid} já existe")
            part = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcSlab")
            part.GlobalId = gid
            rel = ifcopenshell.api.aggregate.assign_object(doc.ifc, products=[part],
                                                           relating_object=roof)
            guid.stamp(rel, roof.GlobalId, "aggregates")
        out.append(part)
        doc.changed.add(gid)
    return out


def write_state(doc: Document, roof, state: dict) -> None:
    state = normalized(state)
    validate(state)
    storey = doc.get(state["storey"], "IfcBuildingStorey")
    slab_type = doc.get(state["type"], "IfcSlabType")
    if slab_type.PredefinedType != "ROOF":
        raise OpError(f"o tipo {slab_type.Name} não é de cobertura")
    t = st_types.slab_thickness(slab_type)
    found = faces(state)
    if len(found) != len(state["parts"]):
        raise OpError("não foi possível dividir a cobertura em águas")
    roof.Name = state["name"]
    sides = slabs.rectangle_sides(state["outline"])
    pavilion = state["shape"] == "hip" and sides is not None and abs(sides[0] - sides[1]) <= 1e-6
    roof.PredefinedType = "PAVILION_ROOF" if pavilion else PREDEFINED[state["shape"]]
    common.assign_container(doc, roof, storey)
    origin = state["outline"][0]
    if roof.ObjectPlacement is None:
        roof.ObjectPlacement = local_placement(doc.ifc, storey.ObjectPlacement, 0.0, origin)
    else:
        old = roof.ObjectPlacement.RelativePlacement
        roof.ObjectPlacement.PlacementRelTo = storey.ObjectPlacement
        roof.ObjectPlacement.RelativePlacement = axis_placement(doc.ifc, origin, 0.0,
                                                                (1.0, 0.0))
        ifcopenshell.util.element.remove_deep2(doc.ifc, old)
    params = {k: state[k] for k in STATE_KEYS
              if k not in ("name", "storey", "common", "foreign")}
    props.write_pset(doc, roof, PSET, {
        "Parametros": doc.ifc.createIfcText(json.dumps(params, sort_keys=True,
                                                       ensure_ascii=False)),
        "AreaProjecao": doc.ifc.createIfcAreaMeasure(projected_area(state))})
    parts = _sync_parts(doc, roof, state["parts"])
    pitch = slope_angle(state)
    total = 0.0
    origin3 = (origin[0], origin[1], 0.0)
    for n, (part, face) in enumerate(zip(parts, found, strict=True), start=1):
        part.Name = f"Água {n}"
        common.assign_type(doc, part, slab_type)
        slabs._assign_material(doc, part, slab_type)
        ring3 = _part_body(doc, part, state, face, t, origin3)
        area = face_area(state, face)
        total += area
        perimeter = sum(math.dist(ring3[i], ring3[(i + 1) % len(ring3)])
                        for i in range(len(ring3)))
        _write_common(doc, part, PART_COMMON, {
            **_common_defaults(slab_type), "PitchAngle": pitch,
            **{k: v for k, v in state["common"].items() if k in ("Status",)}})
        props.write_qto(doc, part, "Qto_SlabBaseQuantities", {
            "Width": t, "Perimeter": perimeter, "GrossArea": area, "NetArea": area,
            "GrossVolume": area * t, "NetVolume": area * t})
    _write_common(doc, roof, COMMON_PSET, {**_common_defaults(slab_type), **state["common"]})
    props.write_qto(doc, roof, "Qto_RoofBaseQuantities",
                    {"GrossArea": total, "NetArea": total})
    doc.changed.add(roof.GlobalId)


def remove(doc: Document, roof) -> set[str]:
    gone = {roof.GlobalId}
    for rel in list(roof.IsDecomposedBy or ()):
        for part in list(rel.RelatedObjects):
            gone.add(part.GlobalId)
            common.remove(doc, part)
    ifcopenshell.api.root.remove_product(doc.ifc, product=roof)
    return gone


# --- operações ---------------------------------------------------------------------------


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    roof = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcRoof")
    roof.GlobalId = op.id
    state = {**default_state(), **copy.deepcopy(op.data)}
    try:
        write_state(doc, roof, state)
    except Exception:
        remove(doc, roof)
        raise
    return {op.id, *state["parts"]}


def _delete(doc: Document, op: Op) -> set[str]:
    roof = doc.get(op.id, "IfcRoof")
    return remove(doc, roof)


def _edit(doc: Document, op: Op) -> set[str]:
    roof = doc.get(op.id, "IfcRoof")
    state = read_state(doc, roof)
    check_before(op, state)
    unknown = set(op.after or {}) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"roof.edit: campos desconhecidos {sorted(unknown)}")
    old_parts = set(state["parts"])
    state.update(copy.deepcopy(op.after or {}))
    write_state(doc, roof, state)
    return {op.id, *old_parts, *state["parts"]}


register_inverse_pair("roof.create", _create, "roof.delete", _delete)
register("roof.edit", _edit, invert_swap)


def derive(doc: Document, dirty: set[str]) -> None:
    """Refaz as coberturas cujo tipo mudou (espessura, camadas, nome)."""
    found = {}
    for gid in dirty:
        entity = doc.find(gid)
        if entity is None or not entity.is_a("IfcSlabType"):
            continue
        for part in ifcopenshell.util.element.get_types(entity):
            roof = roof_of(part)
            if roof is not None:
                found[roof.GlobalId] = roof
    for gid in sorted(found):
        roof = found[gid]
        write_state(doc, roof, read_state(doc, roof))


register_derive(derive)


# --- comandos auxiliares -------------------------------------------------------------


def part_ids(shape: str, current: list[str] | None = None) -> list[str]:
    """GlobalIds das peças para a forma: mantém os atuais quando a quantidade é a mesma."""
    count = PART_COUNT[shape]
    kept = list(current or [])[:count]
    return kept + [guid.new() for _ in range(count - len(kept))]


def mapped_side(state: dict, fn, new_outline) -> int | None:
    """Índice, no contorno novo, do lado que era ``side`` antes de ``fn`` (mover, girar
    ou espelhar): a uma água continua baixa do mesmo lado físico (§5.1)."""
    side = state.get("side")
    if side is None:
        return None
    old = state["outline"]
    a, b = fn(old[side]), fn(old[(side + 1) % len(old)])
    n = len(new_outline)
    for i in range(n):
        p, q = new_outline[i], new_outline[(i + 1) % n]
        if (math.dist(p, a) <= 1e-6 and math.dist(q, b) <= 1e-6) or (
                math.dist(p, b) <= 1e-6 and math.dist(q, a) <= 1e-6):
            return i
    return side


def wall_top(doc: Document, storey) -> float:
    """Altura de apoio padrão: o topo mais alto das paredes do pavimento (§3.1)."""
    from brasbim.core.walls import rebuild as wall_rebuild
    from brasbim.core.walls.wall import read_state as read_wall

    tops = []
    for wall in ifcopenshell.util.element.get_decomposition(storey):
        if not wall.is_a("IfcWall"):
            continue
        try:
            state = read_wall(doc, wall)
            tops.append(float(state["base_offset"]) + wall_rebuild.height(doc, state))
        except (OpError, ValueError, KeyError, TypeError):
            continue
    return max(tops) if tops else DEFAULT_BASE
