# SPDX-License-Identifier: LGPL-3.0-or-later
"""Ambientes (``IfcSpace``), spec/ui 13 §3.

Operações: ``space.create`` / ``space.delete`` (data: estado completo) e ``space.edit``
(before/after: campos alterados).

Estado::

    {"storey": "<GlobalId>", "outline": [[x, y], ...], "number": "01", "name": "Sala",
     "height": None, "label_at": None, "seed": None, "area_class": None,
     "area_reason": None}

``number`` vai em ``Name`` e ``name`` em ``LongName`` [IFC-SPACE]. ``height`` ``None`` =
pé-direito calculado (da cota do pavimento ao fundo da laje que cobre o centro; sem laje,
até o pavimento de cima; sem pavimento de cima, 2,80). ``label_at`` ``None`` = centro.
``seed`` é o ponto clicado no ambiente pelo cômodo: enquanto existir, o contorno é refeito
pelas paredes na derivação (``refit``); editar o contorno à mão o apaga.
``area_class`` / ``area_reason`` = classificação no quadro de áreas (spec/ui 31 §5), no Pset
``BrasBim_QuadroDeAreas`` (``Classificacao``, ``Motivo``); ``None`` = a regra do perfil
municipal (``quantities.legal_areas.classify``).
Pset ``BrasBim_Ambiente``: ``PeDireitoFixo``, ``EtiquetaX``/``EtiquetaY``,
``SementeX``/``SementeY``. O contorno é lido do ``FootPrint``; ``Body`` e quantidades são
derivados (``rebuild``). ``GrossFloorArea`` é a área do contorno; ``NetFloorArea`` desconta
pilares e paredes dentro dele [IFC-QTO-SPACE].
"""

from __future__ import annotations

import ifcopenshell.api.aggregate
import ifcopenshell.api.root
import ifcopenshell.util.element

from brasbim.core import geom2d, guid, props
from brasbim.core.document import Document, OpError, axis_placement, local_placement
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair

PSET = "BrasBim_Ambiente"
AREA_PSET = "BrasBim_QuadroDeAreas"
QTO = "Qto_SpaceBaseQuantities"
DEFAULT_HEIGHT = 2.80
DEFAULT_NAME = "Ambiente"
NAMES = ("Sala", "Cozinha", "Quarto", "Banheiro", "Área de serviço", "Varanda", "Circulação",
         "Garagem", "Quintal", "Jardim", "Piscina")  # sugestões (spec/ui 13 §3.3)
STATE_KEYS = ("storey", "outline", "number", "name", "height", "label_at", "seed",
              "area_class", "area_reason")


def default_state() -> dict:
    return {"number": None, "name": DEFAULT_NAME, "height": None, "label_at": None,
            "seed": None, "area_class": None, "area_reason": None}


def storey_of(space):
    found = ifcopenshell.util.element.get_aggregate(space)
    return found if found is not None and found.is_a("IfcBuildingStorey") else None


def read_state(space) -> dict:
    storey = storey_of(space)
    rep = props.representation(space, "FootPrint")
    outline = None
    if rep is not None and rep.Items and rep.Items[0].is_a("IfcPolyline"):
        x, y, _ = space.ObjectPlacement.RelativePlacement.Location.Coordinates
        pts = [p.Coordinates for p in rep.Items[0].Points]
        if len(pts) > 1 and pts[0] == pts[-1]:
            pts = pts[:-1]
        outline = [[x + p[0], y + p[1]] for p in pts]
    values = ifcopenshell.util.element.get_pset(space, PSET, should_inherit=False) or {}
    fixed = values.get("PeDireitoFixo")
    lx, ly = values.get("EtiquetaX"), values.get("EtiquetaY")
    sx, sy = values.get("SementeX"), values.get("SementeY")
    area_values = ifcopenshell.util.element.get_pset(space, AREA_PSET,
                                                     should_inherit=False) or {}
    return {"storey": storey.GlobalId if storey else None, "outline": outline,
            "number": space.Name, "name": space.LongName,
            "height": None if fixed is None else float(fixed),
            "label_at": None if lx is None else [float(lx), float(ly)],
            "seed": None if sx is None else [float(sx), float(sy)],
            "area_class": area_values.get("Classificacao"),
            "area_reason": area_values.get("Motivo")}


def area(outline) -> float:
    return geom2d.polygon_area([tuple(p) for p in outline])


def perimeter(outline) -> float:
    n = len(outline)
    return sum(geom2d._dist(outline[i], outline[(i + 1) % n]) for i in range(n))


def center(outline) -> tuple[float, float]:
    """Centroide do contorno."""
    a2 = cx = cy = 0.0
    n = len(outline)
    for i in range(n):
        (x0, y0), (x1, y1) = outline[i], outline[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        a2 += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    if abs(a2) < 1e-12:
        return (sum(p[0] for p in outline) / n, sum(p[1] for p in outline) / n)
    return (cx / (3 * a2), cy / (3 * a2))


def label_point(state: dict) -> tuple[float, float]:
    return tuple(state["label_at"]) if state["label_at"] else center(state["outline"])


def height(doc: Document, state: dict) -> float:
    """Pé-direito (spec/ui 13 §3.2)."""
    if state["height"] is not None:
        return float(state["height"])
    from brasbim.core.annotations.drafting import _inside
    from brasbim.core.structure import slabs

    storey = doc.get(state["storey"], "IfcBuildingStorey")
    z = float(storey.Elevation or 0.0)
    above = doc.storey_above(storey)
    c = center(state["outline"])
    bottoms = []
    for s in [storey] + ([above] if above is not None else []):
        for slab in ifcopenshell.util.element.get_decomposition(s):
            if not slab.is_a("IfcSlab"):
                continue
            try:
                st = slabs.read_state(doc, slab)
            except OpError:
                continue
            if st["foreign"] is not None or not _inside(st["outline"], c):
                continue
            bottom = float(s.Elevation or 0.0) + st["top_offset"] - slabs.thickness(doc, st)
            if bottom > z + 0.01:
                bottoms.append(bottom)
    if bottoms:
        return min(bottoms) - z
    if above is not None:
        return float(above.Elevation or 0.0) - z
    return DEFAULT_HEIGHT


def next_number(doc: Document, storey) -> str:
    used = {s.Name for s in ifcopenshell.util.element.get_decomposition(storey)
            if s.is_a("IfcSpace")}
    n = 1
    while f"{n:02d}" in used:
        n += 1
    return f"{n:02d}"


# --- gravação ----------------------------------------------------------------------------


def _write(doc: Document, space, state: dict) -> None:
    from brasbim.core.structure import slabs

    outline = slabs.clean(state["outline"])
    storey = doc.get(state["storey"], "IfcBuildingStorey")
    if storey_of(space) != storey:
        if storey_of(space) is not None:
            ifcopenshell.api.aggregate.unassign_object(doc.ifc, products=[space])
        rel = ifcopenshell.api.aggregate.assign_object(doc.ifc, products=[space],
                                                       relating_object=storey)
        guid.stamp(rel, storey.GlobalId, "aggregates/spaces")
    space.Name = state["number"]
    space.LongName = state["name"]
    ox, oy = outline[0]
    if space.ObjectPlacement is None:
        space.ObjectPlacement = local_placement(doc.ifc, storey.ObjectPlacement, 0.0, (ox, oy))
    else:
        old = space.ObjectPlacement.RelativePlacement
        space.ObjectPlacement.PlacementRelTo = storey.ObjectPlacement
        space.ObjectPlacement.RelativePlacement = axis_placement(doc.ifc, (ox, oy), 0.0,
                                                                 (1.0, 0.0))
        ifcopenshell.util.element.remove_deep2(doc.ifc, old)
    pts = [doc.ifc.createIfcCartesianPoint((float(x - ox), float(y - oy))) for x, y in outline]
    rep = doc.ifc.createIfcShapeRepresentation(doc.footprint_context, "FootPrint", "Curve2D",
                                               [doc.ifc.createIfcPolyline([*pts, pts[0]])])
    props.replace_representation(doc, space, "FootPrint", rep)
    values = {}
    if state["height"] is not None:
        values["PeDireitoFixo"] = doc.ifc.createIfcPositiveLengthMeasure(float(state["height"]))
    if state["label_at"] is not None:
        values["EtiquetaX"] = doc.ifc.createIfcLengthMeasure(float(state["label_at"][0]))
        values["EtiquetaY"] = doc.ifc.createIfcLengthMeasure(float(state["label_at"][1]))
    if state.get("seed") is not None:
        values["SementeX"] = doc.ifc.createIfcLengthMeasure(float(state["seed"][0]))
        values["SementeY"] = doc.ifc.createIfcLengthMeasure(float(state["seed"][1]))
    if values:
        props.write_pset(doc, space, PSET, values)
    else:
        props.remove_pset(doc, space, PSET)
    _write_area_class(doc, space, state)


def _write_area_class(doc: Document, space, state: dict) -> None:
    from brasbim.core.quantities import legal_areas

    values = {}
    if state.get("area_class") is not None:
        values["Classificacao"] = doc.ifc.createIfcLabel(
            legal_areas.check_class(state["area_class"]))
    if state.get("area_reason"):
        values["Motivo"] = doc.ifc.createIfcLabel(str(state["area_reason"]))
    if values:
        props.write_pset(doc, space, AREA_PSET, values)
    else:
        props.remove_pset(doc, space, AREA_PSET)


def refit(doc: Document, space, walls=None) -> bool:
    """Refaz o contorno pelas paredes a partir do ``seed`` (ou, se ele caiu numa parede,
    do centro do contorno atual). Devolve se mudou; sem cômodo fechado, deixa como está."""
    from brasbim.core.structure import rooms, slabs

    state = read_state(space)
    if state["seed"] is None or state["outline"] is None:
        return False
    storey = doc.get(state["storey"], "IfcBuildingStorey")
    for point in (state["seed"], center(state["outline"])):
        try:
            outline = slabs.clean(rooms.room_outline(doc, storey, tuple(point), "inner",
                                                     walls=walls))
        except OpError:
            continue
        old = slabs.clean(state["outline"])
        if len(old) == len(outline) and all(
                abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6
                for a, b in zip(old, outline, strict=True)):
            return False
        _write(doc, space, {**state, "outline": outline})
        return True
    return False


def net_area(doc: Document, state: dict) -> float:
    """Área do contorno menos a dos pilares e paredes do pavimento dentro dele."""
    from brasbim.core import clip
    from brasbim.core.structure import cuts, rooms

    ring = [tuple(p) for p in state["outline"]]
    storey = doc.get(state["storey"], "IfcBuildingStorey")
    covered = [r for r, _ in rooms.walls_of(doc, storey)]
    for column in ifcopenshell.util.element.get_decomposition(storey):
        if column.is_a("IfcColumn") and (pc := cuts.piece(doc, column)) is not None:
            covered.append(pc.ring)
    gross = area(state["outline"])
    if not covered:
        return gross
    return max(0.0, gross - clip.area(clip.intersection([ring], clip.union(covered))))


def rebuild(doc: Document, space) -> None:
    """``Body`` (contorno extrudado com o pé-direito) e quantidades."""
    state = read_state(space)
    if state["outline"] is None:
        return
    doc.changed.add(space.GlobalId)
    h = height(doc, state)
    ifc = doc.ifc
    ox, oy = state["outline"][0]
    pts = [ifc.createIfcCartesianPoint((float(x - ox), float(y - oy)))
           for x, y in state["outline"]]
    profile = ifc.createIfcArbitraryClosedProfileDef("AREA", None,
                                                     ifc.createIfcPolyline([*pts, pts[0]]))
    solid = ifc.createIfcExtrudedAreaSolid(
        profile, ifc.createIfcAxis2Placement3D(ifc.createIfcCartesianPoint((0.0, 0.0, 0.0)),
                                               None, None),
        ifc.createIfcDirection((0.0, 0.0, 1.0)), float(h))
    props.replace_representation(doc, space, "Body", ifc.createIfcShapeRepresentation(
        doc.body_context, "Body", "SweptSolid", [solid]))
    a = area(state["outline"])
    props.write_qto(doc, space, QTO, {"NetFloorArea": net_area(doc, state),
                                      "GrossFloorArea": a,
                                      "GrossPerimeter": perimeter(state["outline"]),
                                      "Height": h})


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    space = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcSpace",
                                                predefined_type="INTERNAL")
    space.GlobalId = op.id
    try:
        _write(doc, space, {**default_state(), **op.data})
    except Exception:
        remove(doc, space)
        raise
    return {op.id}


def remove(doc: Document, space) -> None:
    ifcopenshell.api.root.remove_product(doc.ifc, product=space)


def _delete(doc: Document, op: Op) -> set[str]:
    remove(doc, doc.get(op.id, "IfcSpace"))
    return {op.id}


def _edit(doc: Document, op: Op) -> set[str]:
    space = doc.get(op.id, "IfcSpace")
    state = read_state(space)
    check_before(op, state)
    unknown = set(op.after or {}) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"space.edit: campos desconhecidos {sorted(unknown)}")
    state.update(op.after or {})
    _write(doc, space, state)
    return {op.id}


register_inverse_pair("space.create", _create, "space.delete", _delete)
register("space.edit", _edit, invert_swap)
