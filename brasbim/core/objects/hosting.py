# SPDX-License-Identifier: LGPL-3.0-or-later
"""Objetos presos à parede (``spec/elementos/objeto-parametrico.md`` §2.4 e §6.3).

Hospedagem no estado da ocorrência: ``{"wall": GlobalId, "side": "left" | "right",
"distance": m}``. ``side`` é a face da parede (a da esquerda do caminho = ``left``, como
nos nichos) e ``distance``, do início da parede até o começo do objeto ao longo dela.

O fundo do objeto (o maior y local da caixa que envolve) encosta na face, com a frente
(−y local) para fora. O posicionamento é relativo ao da parede: mover a parede leva o
objeto. ``IfcRelConnectsElements`` liga parede e objeto; a peça marcada como vão vira um
``IfcOpeningElement`` na parede (nicho ou passante), sem ``IfcRelFillsElement``.
"""

from __future__ import annotations

import logging
import math

import ifcopenshell.api.root
import ifcopenshell.util.element

from brasbim.core import geom2d, guid, props
from brasbim.core.document import Document, OpError
from brasbim.core.objects import shapes

log = logging.getLogger(__name__)

SIDES = ("left", "right")
OPENING_PSET = "BrasBim_VaoObjeto"


def _wall(doc: Document, gid: str):
    from brasbim.core.walls import rebuild
    from brasbim.core.walls.wall import read_state as read_wall

    wall = doc.get(gid, "IfcWall")
    state = read_wall(doc, wall)
    band = rebuild.band(doc, state)
    if not isinstance(band.path, geom2d.LinePath):
        raise OpError("objeto preso só em parede reta")
    if abs(state.get("tilt") or 0.0) > 1e-9:
        raise OpError("objeto preso não vai em parede tombada")
    return wall, state, band


def _validate(host: dict) -> None:
    if host.get("side") not in SIDES:
        raise OpError(f"face inválida: {host.get('side')!r}")
    if not host.get("wall"):
        raise OpError("objeto preso precisa da parede")


def local_frame(doc: Document, host: dict, built) -> dict:
    """Posição do objeto no sistema da parede: ``location`` (x, y, z), ``direction``,
    e o mesmo em coordenadas do pavimento (``point``, ``angle``)."""
    _validate(host)
    wall, wall_state, band = _wall(doc, host["wall"])
    box = shapes.mirrored_box(built.box, built.mirror) or (0, 0, 0, 0, 0, 0)
    x0, x1, _, y1, _, _ = box
    d = float(host["distance"])
    if host["side"] == "left":
        ox, oy, angle = d + x1, band.ymax + y1, 180.0
    else:
        ox, oy, angle = d - x0, band.ymin - y1, 0.0
    z = float(built.values.get("elevacao", 0.0)) - float(wall_state["base_offset"])
    frame = band.frame
    a = math.radians(angle)
    return {"wall": wall, "band": band, "wall_state": wall_state,
            "location": (ox, oy, z), "direction": (math.cos(a), math.sin(a)),
            "point": list(frame.to_global((ox, oy))),
            "angle": (math.degrees(frame.angle) + angle + 180.0) % 360.0 - 180.0,
            "span": (d, d + (x1 - x0))}


def place(doc: Document, state: dict, built) -> dict:
    """Estado com ``point`` e ``angle`` calculados pela parede (§6.3)."""
    frame = local_frame(doc, state["host"], built)
    length = frame["band"].path.length
    a, b = frame["span"]
    if a < -1e-6 or b > length + 1e-6:
        log.warning("Objeto preso à parede ficou fora dela (de %s a %s m numa parede de "
                    "%s m): ajuste a distância", f"{a:.2f}".replace(".", ","),
                    f"{b:.2f}".replace(".", ","), f"{length:.2f}".replace(".", ","))
    return {**state, "point": frame["point"], "angle": frame["angle"], "_frame": frame}


def is_object_opening(opening) -> bool:
    return bool(ifcopenshell.util.element.get_pset(opening, OPENING_PSET,
                                                   should_inherit=False))


def opening_id(element) -> str:
    return guid.derived(element.GlobalId, "opening")


def opening_state(built, frame: dict, host: dict) -> dict | None:
    """Estado da abertura (``walls.openings``) a partir da peça marcada como vão, ou
    ``None`` se não houver vão (§3.3, §6.3)."""
    voids = [s for s in built.solids if s.void and s.kind == "box"]
    if not voids or built.box is None:
        return None
    s = voids[0]
    w, dpt, h = s.dims["width"], s.dims["depth"], s.dims["height"]
    vx0, vx1 = s.origin[0], s.origin[0] + w
    if built.mirror:
        vx0, vx1 = -vx1, -vx0
    back = (shapes.mirrored_box(built.box, built.mirror))[3]
    depth = s.origin[1] + dpt - back
    if depth <= 1e-6:
        return None
    ox, _, oz = frame["location"]
    if host["side"] == "left":
        x_start = ox - vx1
    else:
        x_start = ox + vx0
    thickness = frame["band"].thickness
    through = depth >= thickness - 1e-6
    return {"wall": host["wall"], "kind": "OPENING" if through else "RECESS",
            "distance": x_start, "width": w, "height": h, "sill": oz + s.origin[2],
            "depth": None if through else depth, "side": host["side"]}


def _connection(element):
    for rel in getattr(element, "ConnectedFrom", ()) or ():
        if rel.is_a() == "IfcRelConnectsElements":
            return rel
    return None


def sync(doc: Document, element, state: dict, built) -> None:
    """Relação com a parede e o vão do objeto (refeitos a cada gravação)."""
    from brasbim.core.walls import openings

    rel = _connection(element)
    host = state.get("host")
    wall = doc.get(host["wall"], "IfcWall") if host else None
    if rel is not None and (wall is None or rel.RelatingElement != wall):
        doc.ifc.remove(rel)
        rel = None
    if wall is not None and rel is None:
        doc.ifc.create_entity("IfcRelConnectsElements",
                              GlobalId=guid.derived(element.GlobalId, "host"),
                              RelatingElement=wall, RelatedElement=element)
    ostate = None
    if host is not None:
        ostate = opening_state(built, state["_frame"], host)
    gid = opening_id(element)
    opening = doc.find(gid)
    if ostate is None:
        if opening is not None:
            _remove_opening(doc, opening)
        return
    if opening is None:
        opening = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcOpeningElement")
        opening.GlobalId = gid
    opening.Name = "Vão do objeto"
    openings.write_state(doc, opening, {**openings.default_state(), **ostate})
    props.write_pset(doc, opening, OPENING_PSET, {
        "Objeto": doc.ifc.createIfcIdentifier(element.GlobalId)})
    doc.changed.add(wall.GlobalId)


def _remove_opening(doc: Document, opening) -> None:
    from brasbim.core.walls import openings

    wall = openings.host(opening)
    for rel in opening.VoidsElements:
        doc.ifc.remove(rel)
    props.remove_pset(doc, opening, OPENING_PSET)
    shape = opening.Representation
    opening.Representation = None
    ifcopenshell.api.root.remove_product(doc.ifc, product=opening)
    if shape is not None:
        from brasbim.core import fragment

        fragment.remove(doc.ifc, shape)
    if wall is not None:
        doc.changed.add(wall.GlobalId)


def release(doc: Document, element) -> None:
    """Desfaz a relação com a parede e apaga o vão."""
    rel = _connection(element)
    if rel is not None:
        doc.changed.add(rel.RelatingElement.GlobalId)
        doc.ifc.remove(rel)
    opening = doc.find(opening_id(element))
    if opening is not None:
        _remove_opening(doc, opening)


def wall_of(doc: Document, element):
    rel = _connection(element)
    return rel.RelatingElement if rel is not None else None


def hosted_by(doc: Document, wall) -> list:
    """Objetos presos à parede (pela ``IfcRelConnectsElements``)."""
    from brasbim.core.objects import elements

    out = [rel.RelatedElement for rel in getattr(wall, "ConnectedTo", ()) or ()
           if rel.is_a() == "IfcRelConnectsElements" and elements.is_object(rel.RelatedElement)]
    return sorted(out, key=lambda e: e.GlobalId)


def check(doc: Document, state: dict, built, exclude: str | None = None) -> None:
    """Recusa (nos comandos) objeto fora da parede ou vão que não cabe (§4.4)."""
    from brasbim.core.walls import openings

    frame = local_frame(doc, state["host"], built)
    length = frame["band"].path.length
    a, b = frame["span"]
    if a < -1e-6 or b > length + 1e-6:
        raise OpError("o objeto não cabe na parede")
    ostate = opening_state(built, frame, state["host"])
    if ostate is not None:
        openings.check_fits(doc, frame["wall"], {**openings.default_state(), **ostate},
                            exclude=exclude)


def slid(doc: Document, state: dict, vector) -> dict:
    """Hospedagem depois de mover o objeto sozinho: desliza ao longo da parede (§6.3)."""
    _, _, band = _wall(doc, state["host"]["wall"])
    along = band.frame.vector_to_local(tuple(vector))[0]
    return {**state["host"], "distance": float(state["host"]["distance"]) + along}


def at_point(doc: Document, wall, point, built_box_width: float = 0.0) -> dict | None:
    """Hospedagem pelo ponto clicado: face mais próxima e distância com o objeto centrado
    no ponto (ferramenta, §4.4). ``None`` se a parede não serve."""
    try:
        _, _, band = _wall(doc, wall.GlobalId)
    except OpError:
        return None
    x, y = band.frame.to_local(tuple(point))
    side = "left" if y >= (band.ymin + band.ymax) / 2 else "right"
    return {"wall": wall.GlobalId, "side": side, "distance": x - built_box_width / 2}


def copied_ops(doc: Document, tx, found, vector) -> list:
    """Cópia do objeto preso cuja parede também foi copiada: vai na parede nova (§6.3)."""
    import copy

    from brasbim.core.objects import elements
    from brasbim.core.ops import Op
    from brasbim.core.walls.wall import read_state as read_wall

    created = [op for op in tx.ops if op.op == "wall.create"]
    out = []
    for e in found:
        state = elements.read_state(doc, e)
        host = state["host"]
        if host is None:
            continue
        wall = doc.find(host["wall"])
        if wall is None:
            continue
        path = read_wall(doc, wall)["path"]
        moved = geom2d.mapped(geom2d.path_from_dict(path),
                              geom2d.translation(tuple(vector))).to_dict()
        target = next((op for op in created
                       if _same_path(op.data.get("path"), moved)), None)
        if target is None:
            continue
        data = {**copy.deepcopy(state), "host": {**host, "wall": target.id}}
        out.append(Op("object.create", guid.new(), data=data))
    return out


def _same_path(a, b) -> bool:
    from brasbim.core.ops.base import same_value

    return a is not None and same_value(a, b, 1e-6)
