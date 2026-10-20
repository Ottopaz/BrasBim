# SPDX-License-Identifier: LGPL-3.0-or-later
"""Recortes por prioridade entre pilar, viga, laje e parede (spec/ui 12 §2).

Ordem: pilar > viga > laje > parede. Onde dois elementos de classes diferentes ocupam o
mesmo espaço, o de prioridade mais alta (C) corta o outro (E). Os dois são prismas na
vertical (a viga é uma caixa), então o recorte é sempre um semiespaço horizontal limitado,
em planta, pelo contorno de C (``IfcPolygonalBoundedHalfSpace``), nas coordenadas de E:

- ``through``: C atravessa E na altura → sai tudo dentro do contorno de C;
- ``top``: C ocupa o alto de E → sai o que fica acima da base de C;
- ``bottom``: C ocupa o baixo de E → sai o que fica abaixo do topo de C;
- C inteiro dentro da altura de E → sem recorte (aviso; spec/ui 12 §2.3).

Coordenadas: as plantas dos pavimentos têm o mesmo x, y da edificação; as cotas aqui são
as da edificação (cota do pavimento + cota local).
"""

from __future__ import annotations

import itertools
import logging
import math
from dataclasses import dataclass

import ifcopenshell.util.element

from brasbim.core import clip, geom2d, guid, props
from brasbim.core.document import Document, OpError

log = logging.getLogger(__name__)

PRIORITY = {"IfcColumn": 4, "IfcBeam": 3, "IfcSlab": 2, "IfcWall": 1}
TOL = 0.001  # m: sobreposição menor que isto não é recorte
_MIN_AREA = 1e-6  # m²
INTERFERENCE = "Recorte"


@dataclass
class Piece:
    """Elemento como prisma: contorno em planta e cotas da base e do topo."""

    element: object
    ring: list[tuple[float, float]]
    z0: float
    z1: float
    foreign: bool = False

    @property
    def gid(self) -> str:
        return self.element.GlobalId

    @property
    def priority(self) -> int:
        return PRIORITY[self.element.is_a()]


@dataclass
class Cut:
    cutter: Piece
    mode: str  # through, top, bottom


def _elevation(element) -> float:
    storey = ifcopenshell.util.element.get_container(element)
    return float(storey.Elevation or 0.0) if storey is not None else 0.0


def piece(doc: Document, element) -> Piece | None:
    """Prisma do elemento; ``None`` se não dá para saber (sem tipo, parede inclinada…)."""
    from brasbim.core.structure import beams, columns, slabs  # evita import circular
    from brasbim.core.walls import rebuild as wall_rebuild
    from brasbim.core.walls.wall import read_state as read_wall

    try:
        z = _elevation(element)
        if element.is_a("IfcWall"):
            state = read_wall(doc, element)
            if state["top_profile"] or abs(state["tilt"] or 0.0) > 1e-9:
                return None  # topo inclinado e parede tombada: sem recorte (spec/ui 12 §2.4)
            band = wall_rebuild.band(doc, state)
            segments = wall_rebuild.profile(doc, element, band)
            ring = [band.frame.to_global(p) for p in geom2d.polygon(segments)]
            z0 = z + state["base_offset"]
            return Piece(element, ring, z0, z0 + wall_rebuild.height(doc, state))
        module = {"IfcColumn": columns, "IfcBeam": beams, "IfcSlab": slabs}[element.is_a()]
        state = module.read_state(doc, element)
        if state["foreign"] is not None:
            return _foreign_piece(element)
        if element.is_a("IfcColumn"):
            z0 = z + state["base_offset"]
            return Piece(element, columns.outline(doc, state), z0,
                         z0 + columns.height(doc, state))
        if element.is_a("IfcBeam"):
            z1 = z + beams.top_z(doc, state)
            return Piece(element, beams.outline(doc, state),
                         z1 - beams.section(doc, state)["h"], z1)
        z1 = z + state["top_offset"]
        return Piece(element, [tuple(p) for p in state["outline"]],
                     z1 - slabs.thickness(doc, state), z1)
    except (OpError, ValueError, KeyError, TypeError) as e:
        log.debug("%s %s sem recortes: %s", element.is_a(), element.GlobalId, e)
        return None


def _foreign_piece(element) -> Piece | None:
    """Elemento de outra origem: contorno convexo e cotas do corpo."""
    import ifcopenshell.geom
    import numpy as np

    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    try:
        shape = props.body_shape(settings, element)
    except RuntimeError:
        return None
    verts = np.array(shape.geometry.verts, dtype=float).reshape(-1, 3)
    if not len(verts):
        return None
    ring = geom2d.convex_hull([(float(x), float(y)) for x, y, _ in verts])
    if len(ring) < 3:
        return None
    return Piece(element, ring, float(verts[:, 2].min()), float(verts[:, 2].max()), True)


# --- quem corta quem -------------------------------------------------------------------


def _storeys_near(doc: Document, element) -> list:
    """Pavimento do elemento e os imediatamente abaixo e acima (spec/ui 12 §2.2)."""
    storey = ifcopenshell.util.element.get_container(element)
    storeys = doc.storeys()
    if storey not in storeys:
        return [storey] if storey is not None else []
    i = storeys.index(storey)
    return storeys[max(0, i - 1):i + 2]


def _bbox(ring):
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    return min(xs), min(ys), max(xs), max(ys)


def _boxes_meet(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def nearby(doc: Document, element, classes) -> list:
    """Elementos das ``classes`` nos pavimentos vizinhos, menos o próprio."""
    out = []
    for storey in _storeys_near(doc, element):
        for e in ifcopenshell.util.element.get_decomposition(storey):
            if e != element and any(e.is_a(c) for c in classes) and not _roof_part(e):
                out.append(e)
    return sorted(set(out), key=lambda e: e.GlobalId)


def _roof_part(e) -> bool:
    """As águas da cobertura não entram nos recortes (cobertura.md §6)."""
    from brasbim.core.structure import roofs

    return roofs.is_part(e)


def _mode(c: Piece, e: Piece) -> str | None:
    low, high = max(c.z0, e.z0), min(c.z1, e.z1)
    if high - low <= TOL:
        return None
    below, above = c.z0 <= e.z0 + TOL, c.z1 >= e.z1 - TOL
    if below and above:
        return "through"
    if above:
        return "top"
    if below:
        return "bottom"
    return "inside"


def cuts_of(doc: Document, element, own: Piece | None = None) -> list[Cut]:
    """Recortes que ``element`` sofre (spec/ui 12 §2.2). Elemento de outra origem não é
    cortado."""
    own = own or piece(doc, element)
    if own is None or own.foreign:
        return []
    higher = [c for c, p in PRIORITY.items() if p > own.priority]
    box = _bbox(own.ring)
    out = []
    for other in nearby(doc, element, higher):
        c = piece(doc, other)
        if c is None or not _boxes_meet(box, _bbox(c.ring)):
            continue
        if clip.area(clip.intersection([own.ring], [c.ring])) <= _MIN_AREA:
            continue
        mode = _mode(c, own)
        if mode is None:
            continue
        if mode == "inside":
            log.warning("%s %s: o %s %s fica no meio da altura dela e não a corta nesta "
                        "etapa", _noun(element), element.Name or element.GlobalId,
                        _noun(other), other.Name or other.GlobalId)
            continue
        out.append(Cut(c, mode))
    return out


def _noun(element) -> str:
    return {"IfcColumn": "pilar", "IfcBeam": "viga", "IfcSlab": "laje",
            "IfcWall": "parede"}[element.is_a()]


def cut_by(doc: Document, element) -> list:
    """Elementos que ``element`` corta agora ou cortava (pela relação gravada): os que
    precisam ser refeitos quando ele muda."""
    found = {r.RelatingElement for r in getattr(element, "IsInterferedByElements", ()) or ()
             if r.is_a("IfcRelInterferesElements")}
    own = piece(doc, element)
    if own is not None:
        lower = [c for c, p in PRIORITY.items() if p < own.priority]
        box = _bbox(own.ring)
        for other in nearby(doc, element, lower):
            e = piece(doc, other)
            if e is not None and _boxes_meet(box, _bbox(e.ring)) and _mode(own, e):
                found.add(other)
    return sorted((e for e in found if e is not None), key=lambda e: e.GlobalId)


# --- IFC -------------------------------------------------------------------------------


class Frame:
    """Sistema do corpo do elemento cortado: planta → 2D do contorno do semiespaço, e cota
    da edificação → plano horizontal."""

    def __init__(self, ifc, origin, angle: float, z: float, beam: bool = False):
        self.ifc, self.origin, self.z, self.beam = ifc, origin, z, beam
        self.c, self.s = math.cos(angle), math.sin(angle)

    def local(self, p) -> tuple[float, float]:
        """(u, v) do ponto no plano do contorno."""
        dx, dy = p[0] - self.origin[0], p[1] - self.origin[1]
        along, side = self.c * dx + self.s * dy, -self.s * dx + self.c * dy
        return along, side  # viga: u ao longo dela, v à esquerda; demais: x, y locais

    def _point(self, coords):
        return self.ifc.createIfcCartesianPoint(tuple(float(c) for c in coords))

    def _dir(self, coords):
        return self.ifc.createIfcDirection(tuple(float(c) for c in coords))

    def boundary_position(self):
        if self.beam:  # z do elemento = direção da viga; y = para cima; x = esquerda
            return self.ifc.createIfcAxis2Placement3D(self._point((0, 0, 0)),
                                                      self._dir((0, 1, 0)),
                                                      self._dir((0, 0, 1)))
        return self.ifc.createIfcAxis2Placement3D(self._point((0, 0, 0)), None, None)

    def plane(self, z_world: float):
        h = z_world - self.z
        if self.beam:
            position = self.ifc.createIfcAxis2Placement3D(
                self._point((0, h, 0)), self._dir((0, 1, 0)), self._dir((0, 0, 1)))
        else:
            position = self.ifc.createIfcAxis2Placement3D(self._point((0, 0, h)), None, None)
        return self.ifc.createIfcPlane(position)


def halfspace(frame: Frame, cut: Cut, own: Piece):
    """``IfcPolygonalBoundedHalfSpace`` que retira de E a parte comum com C."""
    ifc = frame.ifc
    c = cut.cutter
    if cut.mode == "through":
        z, above = own.z0 - 1.0, True
    elif cut.mode == "top":
        z, above = c.z0, True
    else:
        z, above = c.z1, False
    ring = [frame.local(p) for p in c.ring]
    if clip.signed_area(ring) < 0:
        ring.reverse()
    points = [ifc.createIfcCartesianPoint((float(u), float(v))) for u, v in ring]
    boundary = ifc.createIfcPolyline([*points, points[0]])
    # AgreementFlag falso: o semiespaço é o lado para onde a normal (para cima) aponta.
    return ifc.createIfcPolygonalBoundedHalfSpace(frame.plane(z), not above,
                                                  frame.boundary_position(), boundary)


def clipped(ifc, solid, frame: Frame, cuts: list[Cut], own: Piece):
    """Sólido com os recortes, encadeados pelo GlobalId de quem corta (ordem estável)."""
    for cut in sorted(cuts, key=lambda k: k.cutter.gid):
        solid = ifc.createIfcBooleanClippingResult("DIFFERENCE", solid,
                                                   halfspace(frame, cut, own))
    return solid


def removed_volume(own: Piece, cuts: list[Cut], ring=None, holes=()) -> float:
    """Volume retirado (união das partes, sem contar duas vezes a parte comum a dois
    recortes): fatias horizontais entre as cotas de todos os recortes. ``holes``: contornos
    que atravessam o elemento inteiro (aberturas da laje, spec/ui 12 §3.4)."""
    if not cuts and not holes:
        return 0.0
    base = [list(ring or own.ring)]
    spans = [(own.z0, own.z1, list(h)) for h in holes]
    for cut in cuts:
        c = cut.cutter
        lo, hi = {"through": (own.z0, own.z1), "top": (c.z0, own.z1),
                  "bottom": (own.z0, c.z1)}[cut.mode]
        lo, hi = max(lo, own.z0), min(hi, own.z1)
        if hi > lo:
            spans.append((lo, hi, c.ring))
    levels = sorted({z for lo, hi, _ in spans for z in (lo, hi)})
    total = 0.0
    for a, b in itertools.pairwise(levels):
        active = [r for lo, hi, r in spans if lo <= a and hi >= b]
        if active:
            total += clip.area(clip.intersection(base, clip.union([list(r) for r in active]))) \
                * (b - a)
    return total


def removed_area(own: Piece, cuts: list[Cut], holes=()) -> float:
    """Área em planta dos recortes que atravessam o elemento e das aberturas (laje:
    ``NetArea``)."""
    through = [list(c.cutter.ring) for c in cuts if c.mode == "through"] + [
        list(h) for h in holes]
    if not through:
        return 0.0
    return clip.area(clip.intersection([list(own.ring)], clip.union(through)))


def sync_relations(doc: Document, element, cuts: list[Cut]) -> None:
    """``IfcRelInterferesElements`` do elemento cortado: uma por quem corta, com
    ``ImpliedOrder`` verdadeiro (spec/ui 12 §2.3, [IFC-INTERF])."""
    wanted = {c.cutter.gid for c in cuts}
    for rel in list(getattr(element, "InterferesElements", ()) or ()):
        if not rel.is_a("IfcRelInterferesElements"):
            continue
        related = rel.RelatedElement
        if related is None or related.GlobalId not in wanted:
            doc.ifc.remove(rel)
        else:
            wanted.discard(related.GlobalId)
    for gid in sorted(wanted):
        doc.ifc.create_entity("IfcRelInterferesElements",
                              GlobalId=guid.derived(element.GlobalId, f"interferes/{gid}"),
                              RelatingElement=element, RelatedElement=doc.get(gid),
                              InterferenceType=INTERFERENCE, ImpliedOrder=True)
