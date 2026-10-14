# SPDX-License-Identifier: LGPL-3.0-or-later
"""Aberturas em paredes (``IfcOpeningElement``) e preenchimentos (spec §6.3).

Operações:

- ``opening.create`` / ``opening.delete`` (``id`` = GlobalId da abertura; ``data`` =
  estado completo) e ``opening.edit`` (before/after: campos de ``STATE_KEYS``).
- ``filling.attach`` / ``filling.detach`` (``id`` = GlobalId do elemento que preenche,
  ex.: ``IfcDoor``; ``data`` = ``{"opening": GlobalId}``).

Estado de uma abertura (coordenadas no sistema local da parede, em metros)::

    {"wall": "<GlobalId>", "kind": "OPENING" | "RECESS", "distance": 1.0,
     "width": 0.9, "height": 2.1, "sill": 0.0, "depth": None, "side": "left"}

``distance``: do início da parede ao começo da abertura, ao longo do caminho. ``sill``:
base da abertura em relação à base da parede. ``depth`` e ``side`` (face de entrada,
``left`` | ``right``) só valem para nicho (``RECESS``).

O IFC é a fonte da verdade: o estado é lido do posicionamento (``distance``, ``sill``) e
do corpo (largura, altura, profundidade e face). O corpo depende da espessura da parede
e é refeito sempre que ela é recalculada (``refresh``).
"""

from __future__ import annotations

import logging

import ifcopenshell.api.root
import ifcopenshell.util.element

from brasbim.core import geom2d, guid, props
from brasbim.core.document import Document, OpError
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair

log = logging.getLogger(__name__)

KINDS = ("OPENING", "RECESS")
SIDES = ("left", "right")
CLEARANCE = 0.01  # folga de cada lado da abertura passante (spec §6.3)
STATE_KEYS = ("wall", "kind", "distance", "width", "height", "sill", "depth", "side")


def default_state() -> dict:
    return {"kind": "OPENING", "sill": 0.0, "depth": None, "side": "left"}


# --- leitura -----------------------------------------------------------------


def of_wall(wall) -> list:
    """Aberturas da parede, em ordem de GlobalId."""
    return sorted((r.RelatedOpeningElement for r in wall.HasOpenings),
                  key=lambda o: o.GlobalId)


def host(opening):
    rels = opening.VoidsElements
    return rels[0].RelatingBuildingElement if rels else None


def _body(opening):
    if opening.Representation is None:
        return None
    for rep in opening.Representation.Representations:
        if rep.RepresentationIdentifier == "Body":
            return rep.Items[0]
    return None


def read_state(opening) -> dict:
    wall = host(opening)
    x, _, z = opening.ObjectPlacement.RelativePlacement.Location.Coordinates
    solid = _body(opening)
    if solid is None or not solid.SweptArea.is_a("IfcRectangleProfileDef"):
        raise OpError(f"abertura {opening.GlobalId} com corpo não suportado")
    axis = solid.Position.Axis.DirectionRatios
    recess = opening.PredefinedType == "RECESS"
    return {
        "wall": wall.GlobalId if wall else None,
        "kind": "RECESS" if recess else "OPENING",
        "distance": float(x),
        "width": float(solid.SweptArea.XDim),
        "height": float(solid.SweptArea.YDim),
        "sill": float(z),
        "depth": float(solid.Depth) if recess else None,
        "side": "left" if axis[1] < 0 else "right",
    }


# --- validação -----------------------------------------------------------------


def wall_info(doc: Document, wall):
    """(faixa da parede, altura da parede), lidas do estado dela."""
    from brasbim.core.walls import rebuild
    from brasbim.core.walls.wall import read_state as read_wall

    state = read_wall(doc, wall)
    return rebuild.band(doc, state), rebuild.height(doc, state)


def _validate(state: dict) -> None:
    if state["kind"] not in KINDS:
        raise OpError(f"tipo de abertura inválido: {state['kind']!r}")
    if state["side"] not in SIDES:
        raise OpError(f"face de entrada inválida: {state['side']!r}")
    if state["width"] <= 0 or state["height"] <= 0:
        raise OpError("largura e altura da abertura devem ser maiores que zero")


def problems(state: dict, band, wall_height: float) -> list[str]:
    """Motivos pelos quais a abertura não cabe na parede (vazio se cabe)."""
    out = []
    tol = 1e-6
    if state["distance"] < -tol or state["distance"] + state["width"] > band.path.length + tol:
        out.append("fora do comprimento da parede")
    if state["sill"] < -tol or state["sill"] + state["height"] > wall_height + tol:
        out.append("fora da altura da parede")
    if state["kind"] == "RECESS" and not (0 < (state["depth"] or 0) < band.thickness):
        out.append("profundidade do nicho deve ser positiva e menor que a espessura")
    return out


def check_fits(doc: Document, wall, state: dict) -> None:
    """Rejeita abertura que não cabe na parede. Usada pelos comandos: ao aplicar uma
    operação (inclusive desfazer), abertura fora dos limites só gera aviso (spec §6.3)."""
    band, wall_height = wall_info(doc, wall)
    if not isinstance(band.path, geom2d.LinePath):
        raise OpError("aberturas, portas e janelas em parede em arco ainda não são "
                      "suportadas (V1)")
    found = problems(state, band, wall_height)
    if found:
        raise OpError(f"abertura não cabe na parede: {'; '.join(found)}")


# --- gravação ----------------------------------------------------------------


def _write_body(doc: Document, opening, state: dict, band) -> None:
    ifc = doc.ifc
    through = state["kind"] == "OPENING"
    gap = CLEARANCE if through else 0.0
    depth = band.thickness + 2 * CLEARANCE if through else float(state["depth"])
    w, h = float(state["width"]), float(state["height"])
    # Perfil no plano vertical da parede (x ao longo dela, y para cima), extrudado
    # perpendicularmente para dentro a partir da face de entrada.
    if state["side"] == "left":
        origin, axis, ref = (0.0, band.ymax + gap, 0.0), (0.0, -1.0, 0.0), (1.0, 0.0, 0.0)
    else:
        origin, axis, ref = (0.0, band.ymin - gap, 0.0), (0.0, 1.0, 0.0), (-1.0, 0.0, 0.0)
    center = w / 2 if state["side"] == "left" else -w / 2
    profile = ifc.createIfcRectangleProfileDef(
        "AREA", None,
        ifc.createIfcAxis2Placement2D(ifc.createIfcCartesianPoint((center, h / 2)), None), w, h,
    )
    solid = ifc.createIfcExtrudedAreaSolid(
        profile,
        ifc.createIfcAxis2Placement3D(ifc.createIfcCartesianPoint(origin),
                                      ifc.createIfcDirection(axis), ifc.createIfcDirection(ref)),
        ifc.createIfcDirection((0.0, 0.0, 1.0)),
        depth,
    )
    rep = ifc.createIfcShapeRepresentation(doc.body_context, "Body", "SweptSolid", [solid])
    props.replace_representation(doc, opening, "Body", rep)


def _place(doc: Document, opening, wall, state: dict) -> None:
    ifc = doc.ifc
    location = ifc.createIfcAxis2Placement3D(
        ifc.createIfcCartesianPoint((float(state["distance"]), 0.0, float(state["sill"]))),
        None, None,
    )
    placement = opening.ObjectPlacement
    if placement is None:
        opening.ObjectPlacement = ifc.createIfcLocalPlacement(wall.ObjectPlacement, location)
        return
    old = placement.RelativePlacement
    placement.PlacementRelTo = wall.ObjectPlacement
    placement.RelativePlacement = location
    ifcopenshell.util.element.remove_deep2(ifc, old)


def _set_host(doc: Document, opening, wall) -> None:
    rels = opening.VoidsElements
    if rels and rels[0].RelatingBuildingElement == wall:
        return
    for rel in rels:
        doc.ifc.remove(rel)
    doc.ifc.create_entity(
        "IfcRelVoidsElement", GlobalId=guid.derived(opening.GlobalId, "voids"),
        RelatingBuildingElement=wall, RelatedOpeningElement=opening,
    )


def write_state(doc: Document, opening, state: dict) -> None:
    _validate(state)
    wall = doc.get(state["wall"], "IfcWall")
    band = wall_info(doc, wall)[0]
    if not isinstance(band.path, geom2d.LinePath):
        raise OpError("abertura em parede curva ainda não é suportada (V1)")
    opening.PredefinedType = state["kind"]
    _set_host(doc, opening, wall)
    _place(doc, opening, wall, state)
    _write_body(doc, opening, state, band)


def refresh(doc: Document, wall, band, wall_height: float) -> None:
    """Refaz o corpo das aberturas da parede (a espessura pode ter mudado).

    Abertura que deixou de caber não é excluída; fica com aviso (spec §6.3).
    """
    spans = []
    for opening in of_wall(wall):
        state = read_state(opening)
        _write_body(doc, opening, state, band)
        found = problems(state, band, wall_height)
        if found:
            log.warning("abertura %s inválida: %s", opening.GlobalId, "; ".join(found))
        spans.append((opening.GlobalId, state))
    for i, (a, sa) in enumerate(spans):
        for b, sb in spans[i + 1:]:
            if _overlap(sa, sb):
                log.warning("aberturas %s e %s se sobrepõem", a, b)


def _overlap(a: dict, b: dict) -> bool:
    def gap(a0, a1, b0, b1):
        return min(a1, b1) - max(a0, b0) > 1e-6

    return gap(a["distance"], a["distance"] + a["width"], b["distance"],
               b["distance"] + b["width"]) and gap(a["sill"], a["sill"] + a["height"],
                                                   b["sill"], b["sill"] + b["height"])


# --- operações ---------------------------------------------------------------


def _full(op: Op) -> dict:
    return {**default_state(), **op.data}


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    state = _full(op)
    opening = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcOpeningElement")
    opening.GlobalId = op.id
    try:
        write_state(doc, opening, state)
    except Exception:
        for rel in opening.VoidsElements:
            doc.ifc.remove(rel)
        ifcopenshell.api.root.remove_product(doc.ifc, product=opening)
        raise
    return {state["wall"]}


def _delete(doc: Document, op: Op) -> set[str]:
    opening = doc.get(op.id, "IfcOpeningElement")
    if opening.HasFillings:
        raise OpError(f"abertura {op.id} ainda tem preenchimento")
    wall = host(opening)
    for rel in opening.VoidsElements:
        doc.ifc.remove(rel)
    ifcopenshell.api.root.remove_product(doc.ifc, product=opening)
    return {wall.GlobalId} if wall else set()


def _edit(doc: Document, op: Op) -> set[str]:
    opening = doc.get(op.id, "IfcOpeningElement")
    state = read_state(opening)
    check_before(op, state)
    unknown = set(op.after or {}) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"opening.edit: campos desconhecidos {sorted(unknown)}")
    old_wall = state["wall"]
    state.update(op.after or {})
    write_state(doc, opening, state)
    return {old_wall, state["wall"]}


def _attach(doc: Document, op: Op) -> set[str]:
    element = doc.get(op.id, "IfcElement")
    opening = doc.get(op.data["opening"], "IfcOpeningElement")
    if element.FillsVoids:
        raise OpError(f"{op.id} já preenche uma abertura")
    if opening.HasFillings:
        raise OpError(f"abertura {opening.GlobalId} já tem preenchimento")
    doc.ifc.create_entity(
        "IfcRelFillsElement", GlobalId=guid.derived(element.GlobalId, "fills"),
        RelatingOpeningElement=opening, RelatedBuildingElement=element,
    )
    return {element.GlobalId}


def _detach(doc: Document, op: Op) -> set[str]:
    element = doc.get(op.id, "IfcElement")
    rels = [r for r in element.FillsVoids
            if r.RelatingOpeningElement.GlobalId == op.data["opening"]]
    if not rels:
        raise OpError(f"{op.id} não preenche a abertura {op.data['opening']}")
    for rel in rels:
        doc.ifc.remove(rel)
    return {element.GlobalId}


register_inverse_pair("opening.create", _create, "opening.delete", _delete)
register("opening.edit", _edit, invert_swap)
register_inverse_pair("filling.attach", _attach, "filling.detach", _detach)


# --- quantidades (spec §8) -------------------------------------------------------


def deductions(wall, band, wall_height: float, profile: list) -> dict:
    """Descontos das aberturas nas quantidades da parede.

    ``profile``: perfil do corpo (coordenadas locais, após junções).
    """
    poly = geom2d.polygon(profile)
    side = volume = footprint = 0.0
    for opening in of_wall(wall):
        s = read_state(opening)
        x0, x1 = s["distance"], s["distance"] + s["width"]
        h = max(0.0, min(s["sill"] + s["height"], wall_height) - max(s["sill"], 0.0))
        if s["kind"] == "OPENING":
            y0, y1 = band.ymin - 1.0, band.ymax + 1.0
        elif s["side"] == "left":
            y0, y1 = band.ymax - s["depth"], band.ymax
        else:
            y0, y1 = band.ymin, band.ymin + s["depth"]
        plan = geom2d.clip_area(poly, x0, x1, y0, y1)
        volume += plan * h
        if s["kind"] == "OPENING":
            side += s["width"] * h
            if abs(s["sill"]) < 1e-6:
                footprint += plan
    return {"side": side, "volume": volume, "footprint": footprint}
