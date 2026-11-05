# SPDX-License-Identifier: LGPL-3.0-or-later
"""Parede com o topo até a cobertura (spec/ui 45).

No modo de topo ``roof`` a parede guarda as coberturas (``top_roofs``) e a face que vale
(``roof_face``: ``bottom``, o telhado apoia na parede; ``top``, a parede passa como
platibanda até a face de cima). A altura sai sozinha: a maior cota dessa face sobre a
planta da parede. O corpo é extrudado até lá e recortado, água por água, por um
semiespaço no plano da face limitado pela água em planta. O trecho sem cobertura em
cima fica no topo de reserva, que é o topo de antes (pavimento de cima ou altura fixa,
guardados em ``top_storey``/``fixed_height``); soltar volta a ele.

No IFC, uma ``IfcRelInterferesElements`` por cobertura: parede = ``RelatingElement``,
``IfcRoof`` = ``RelatedElement``, ``SUBTRACT_UP``, com o nome ``REL_NAME`` para não se
misturar com as operações de sólidos do usuário.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import ifcopenshell.util.element
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from brasbim.core import geom2d, guid
from brasbim.core.document import Document, OpError

REL_NAME = "BrasBim: topo até a cobertura"
FACES = ("bottom", "top")
FACE_LABEL = {"bottom": "Face de baixo (telhado apoiado)", "top": "Face de cima (platibanda)"}
_MIN_AREA = 1e-6  # m²
_GROW = 1e-3  # m: as águas se encostam sem fresta no recorte


@dataclass
class Surface:
    """Uma água vista pela parede: a região em planta (pavimento da parede) e o plano da
    face escolhida, em cotas absolutas: ``z(p) = z0 + gx·(x − x0) + gy·(y − y0)``."""

    region: Polygon  # a água em planta, exata (alturas e volumes)
    point: tuple[float, float, float]
    gradient: tuple[float, float]
    grown: Polygon | None = None  # a água com 1 mm de folga (limite do recorte)

    def z(self, p) -> float:
        return (self.point[2] + self.gradient[0] * (p[0] - self.point[0])
                + self.gradient[1] * (p[1] - self.point[1]))


def is_roof_rel(rel) -> bool:
    return rel.is_a("IfcRelInterferesElements") and rel.Name == REL_NAME


def _elevation(doc: Document, storey_id: str) -> float:
    return float(doc.get(storey_id, "IfcBuildingStorey").Elevation or 0.0)


def base_z(doc: Document, state: dict) -> float:
    return _elevation(doc, state["storey"]) + float(state["base_offset"])


def surfaces(doc: Document, state: dict) -> list[Surface]:
    """As águas das coberturas da parede, com o plano da face escolhida."""
    from brasbim.core.structure import roofs

    out = []
    for gid in state.get("top_roofs") or []:
        roof = doc.find(gid)
        if roof is None or not roofs.is_roof(roof):
            raise OpError(f"a cobertura {gid} não existe")
        rstate = roofs.read_state(doc, roof)
        z_storey = _elevation(doc, rstate["storey"])
        s = float(rstate["slope"]) / 100.0
        for face in roofs.faces(rstate):
            sloped = face.side is not None
            # a espessura é medida na perpendicular da água: na vertical, t / cos
            extra = 0.0
            if state.get("roof_face") == "top":
                t = roofs.thickness(doc, rstate)
                extra = t * math.sqrt(1.0 + s * s) if sloped else t
            origin = face.origin
            z0 = z_storey + roofs.bottom_z(rstate, face, origin) + extra
            gradient = (s * face.inward[0], s * face.inward[1]) if sloped else (0.0, 0.0)
            region = Polygon(face.ring)
            out.append(Surface(region, (origin[0], origin[1], z0), gradient,
                               region.buffer(_GROW, join_style="mitre")))
    return out


def reserve_height(doc: Document, state: dict) -> float:
    """Altura do trecho sem cobertura em cima: o topo de antes (spec/ui 45 §3 item 4)."""
    if state.get("top_storey"):
        return (_elevation(doc, state["top_storey"]) + float(state["top_offset"])
                - base_z(doc, state))
    return float(state["fixed_height"])


def footprint(doc: Document, state: dict) -> Polygon:
    """A planta da parede (faixa inteira, sem os recortes das junções)."""
    from brasbim.core.walls import rebuild

    own = rebuild.band(doc, state)
    local = geom2d.polygon(geom2d.band_profile(own.path, own.ymin, own.ymax))
    return Polygon([own.frame.to_global(p) for p in local]).buffer(0)


@dataclass
class Shape:
    height: float  # altura da parede (do ponto mais alto)
    surfaces: list[Surface]
    uncovered: list[Polygon]  # trechos sem cobertura em cima (planta do pavimento)
    reserve: float


def shape(doc: Document, state: dict, plan: Polygon | None = None) -> Shape:
    """Altura e recortes da parede presa à cobertura. Recusa a parede sem nenhuma água
    em cima."""
    plan = footprint(doc, state) if plan is None else plan
    found = surfaces(doc, state)
    z_base = base_z(doc, state)
    tops = []
    for surface in found:
        piece = plan.intersection(surface.region)
        if piece.area < _MIN_AREA:
            continue
        for geom in getattr(piece, "geoms", [piece]):
            if geom.geom_type == "Polygon":
                tops += [surface.z(p) - z_base for p in geom.exterior.coords]
    if not tops:
        raise OpError("a cobertura não passa sobre esta parede")
    rest = plan.difference(unary_union([s.region for s in found]))
    uncovered = [g for g in getattr(rest, "geoms", [rest])
                 if g.geom_type == "Polygon" and g.area > _MIN_AREA]
    reserve = reserve_height(doc, state)
    height = max([*tops, *([reserve] if uncovered else [])])
    if height <= 0:
        raise OpError("a cobertura fica abaixo da base da parede")
    return Shape(height, found, uncovered, reserve)


def volume(doc: Document, state: dict, plan: Polygon, result: Shape) -> float:
    """Volume da parede recortada sobre a planta ``plan`` (já com as junções): a altura é
    linear em cada água, então a integral é área × altura no centroide."""
    z_base = base_z(doc, state)
    total = 0.0
    covered = []
    for surface in result.surfaces:
        piece = plan.intersection(surface.region)
        for geom in getattr(piece, "geoms", [piece]):
            if geom.geom_type != "Polygon" or geom.area < _MIN_AREA:
                continue
            # coberturas sobrepostas: cada trecho conta uma vez
            geom = geom.difference(unary_union(covered)) if covered else geom
            if geom.area < _MIN_AREA:
                continue
            c = geom.centroid
            total += geom.area * max(0.0, min(result.height, surface.z((c.x, c.y)) - z_base))
            covered.append(geom)
    rest = plan.difference(unary_union(covered)) if covered else plan
    total += rest.area * result.reserve if result.uncovered else 0.0
    return total


def top_at(doc: Document, state: dict, result: Shape, p) -> float:
    """Altura do topo recortado no ponto ``p`` da planta: a água mais baixa que o cobre
    (várias coberturas recortam juntas), senão o topo de reserva."""
    from shapely.geometry import Point

    z_base = base_z(doc, state)
    found = [s.z(p) - z_base for s in result.surfaces if s.region.covers(Point(p))]
    return min(result.height, min(found)) if found else result.reserve


def axis_profile(doc: Document, state: dict, result: Shape) -> list[list[float]]:
    """Topo ao longo do eixo da parede reta, ``[[posição, altura], ...]``, com um ponto
    onde o eixo cruza a borda de cada água (entre eles, a altura é linear). Usado na
    conferência das aberturas (spec/ui 45 §4). Arco: vazio."""
    path = geom2d.path_from_dict(state["path"])
    if not isinstance(path, geom2d.LinePath):
        return []
    from brasbim.core.walls import rebuild

    own = rebuild.band(doc, state)
    y = (own.ymin + own.ymax) / 2
    a, b = own.frame.to_global((0.0, y)), own.frame.to_global((path.length, y))
    line = LineString([a, b])
    stops = {0.0, path.length}
    for surface in result.surfaces:
        crossing = line.intersection(surface.region.exterior)
        for geom in getattr(crossing, "geoms", [crossing]):
            if geom.geom_type == "Point":
                stops.add(round(math.dist(a, (geom.x, geom.y)), 9))
    out = []
    for s in sorted(stops):
        t = s / path.length
        p = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
        out.append([s, top_at(doc, state, result, p)])
    return out


# --- corpo (coordenadas locais da parede) ------------------------------------------------


def halfspaces(doc: Document, state: dict, frame: geom2d.Frame, result: Shape) -> list:
    """Semiespaços a tirar do corpo: um por água (o plano da face, limitado pela água em
    planta) e um por trecho descoberto (horizontal no topo de reserva)."""
    ifc = doc.ifc
    z_base = base_z(doc, state)
    out = []

    def local3(p, z):
        x, y = frame.to_local(p)
        return (float(x), float(y), float(z - z_base))

    def cut(point3, normal, ring):
        nx, ny, nz = normal
        n = math.sqrt(nx * nx + ny * ny + nz * nz)
        normal = (nx / n, ny / n, nz / n)
        ref = (1.0, 0.0, 0.0) if abs(normal[0]) < 0.9 else (0.0, 1.0, 0.0)
        plane = ifc.createIfcPlane(ifc.createIfcAxis2Placement3D(
            ifc.createIfcCartesianPoint(point3), ifc.createIfcDirection(normal),
            ifc.createIfcDirection(ref)))
        pts = [ifc.createIfcCartesianPoint((float(x), float(y))) for x, y in ring]
        boundary = ifc.createIfcPolyline([*pts, pts[0]])
        # AgreementFlag falso: o lado para onde a normal (para cima) aponta sai do corpo
        return ifc.createIfcPolygonalBoundedHalfSpace(
            plane, False,
            ifc.createIfcAxis2Placement3D(ifc.createIfcCartesianPoint((0.0, 0.0, 0.0)),
                                          None, None), boundary)

    for surface in result.surfaces:
        gx, gy = surface.gradient
        nx, ny = frame.vector_to_local((-gx, -gy))
        ring = [frame.to_local(p) for p in list(surface.grown.exterior.coords)[:-1]]
        x0, y0, z0 = surface.point
        out.append(cut(local3((x0, y0), z0), (nx, ny, 1.0), ring))
    for poly in result.uncovered:
        ring = [frame.to_local(p) for p in list(poly.exterior.coords)[:-1]]
        out.append(cut((0.0, 0.0, float(result.reserve)), (0.0, 0.0, 1.0), ring))
    return out


# --- relações ----------------------------------------------------------------------------


def sync_relations(doc: Document, wall, state: dict) -> None:
    """Uma ``IfcRelInterferesElements`` ``SUBTRACT_UP`` por cobertura do topo."""
    wanted = set(state.get("top_roofs") or []) if state["top_mode"] == "roof" else set()
    for rel in list(getattr(wall, "InterferesElements", ()) or ()):
        if not is_roof_rel(rel):
            continue
        related = rel.RelatedElement
        if related is None or related.GlobalId not in wanted:
            doc.ifc.remove(rel)
        else:
            wanted.discard(related.GlobalId)
    for gid in sorted(wanted):
        doc.ifc.create_entity("IfcRelInterferesElements",
                              GlobalId=guid.derived(wall.GlobalId, f"roof/{gid}"),
                              Name=REL_NAME, RelatingElement=wall,
                              RelatedElement=doc.get(gid), InterferenceType="SUBTRACT_UP",
                              ImpliedOrder=True)


def walls_of(doc: Document, roof_ids) -> list:
    """Paredes presas a alguma das coberturas ``roof_ids``."""
    from brasbim.core.walls import params

    roof_ids = set(roof_ids)
    found = []
    for wall in doc.ifc.by_type("IfcWall"):
        values = ifcopenshell.util.element.get_pset(wall, params.PSET,
                                                    should_inherit=False) or {}
        if values.get("TipoTopo") == "COBERTURA" and roof_ids & set(
                (values.get("CoberturasTopo") or "").split()):
            found.append(wall)
    return found


# --- comandos ----------------------------------------------------------------------------

_CATCH = 0.50  # m: ao criar a cobertura, prende a parede com o topo até isto da face


def _gid(obj) -> str:
    return obj if isinstance(obj, str) else obj.GlobalId


def _attached_state(state: dict, roof_ids, face: str | None) -> dict:
    roofs_ = list(state["top_roofs"]) if state["top_mode"] == "roof" else []
    roofs_ += [r for r in roof_ids if r not in roofs_]
    out = {**state, "top_mode": "roof", "top_roofs": roofs_}
    if face is not None:
        out["roof_face"] = face
    return out


def _attach_ops(doc: Document, wall, roof_ids, face: str | None) -> list:
    from brasbim.core.walls import commands as wc
    from brasbim.core.walls import types as wall_types
    from brasbim.core.walls.wall import ROOF_TOP_REFUSED, read_state

    state = read_state(doc, wall)
    if abs(state["tilt"] or 0.0) > 1e-9:
        raise OpError(ROOF_TOP_REFUSED["tilt"])
    if wall_types.profile_of(doc.get(state["type"], "IfcWallType")) is not None:
        raise OpError(ROOF_TOP_REFUSED["profile"])
    if state["top_profile"]:
        raise OpError(ROOF_TOP_REFUSED["top_profile"])
    new = _attached_state(state, roof_ids, face)
    if new["top_roofs"] == state["top_roofs"] and state["top_mode"] == "roof" and (
            face is None or face == state["roof_face"]):
        return []
    shape(doc, new)  # recusa a parede sem cobertura em cima
    changes = {"top_mode": "roof", "top_roofs": new["top_roofs"]}
    if face is not None and face != state["roof_face"]:
        changes["roof_face"] = face
    return wc.edit_wall(doc, wall, **changes).ops


def attach(doc: Document, walls, roof, face: str | None = None):
    """Prender à cobertura (spec/ui 45 §2): o topo das paredes passa a ir até ``roof``.
    Com várias paredes, as que não estão sob a cobertura ficam de fora (com motivo); se
    nenhuma serve, recusa."""
    from brasbim.core.ops.history import Transaction
    from brasbim.core.structure import roofs

    roof = doc.get(_gid(roof))
    if not roofs.is_roof(roof):
        roof = roofs.roof_of(roof)
    if roof is None:
        raise OpError("clique numa cobertura")
    ops, problems = [], []
    walls = [doc.get(_gid(w), "IfcWall") for w in walls]
    for wall in walls:
        try:
            ops += _attach_ops(doc, wall, [roof.GlobalId], face)
        except OpError as e:
            problems.append(f"{wall.Name or 'parede'}: {e}")
    if not ops:
        raise OpError(problems[0] if len(problems) == 1 else
                      "nenhuma parede foi presa" + (f" ({'; '.join(problems)})"
                                                     if problems else ""))
    n = len({op.id for op in ops if op.op == "wall.edit"})
    label = "Prender parede à cobertura" if n == 1 else f"Prender {n} paredes à cobertura"
    return Transaction(label, ops)


def detach(doc: Document, walls, roof=None):
    """Soltar da cobertura: tira ``roof`` (ou todas) do topo; sem nenhuma, a parede volta
    ao topo de antes (pavimento de cima, se havia, senão a altura fixa)."""
    from brasbim.core.ops.history import Transaction

    ops = []
    for wall in walls:
        ops += _detach_ops(doc, doc.get(_gid(wall), "IfcWall"),
                           None if roof is None else {_gid(roof)})
    if not ops:
        raise OpError("a seleção não tem parede presa à cobertura")
    return Transaction("Soltar da cobertura", ops)


def _detach_ops(doc: Document, wall, roof_ids: set | None) -> list:
    from brasbim.core.walls import commands as wc
    from brasbim.core.walls.wall import read_state

    state = read_state(doc, wall)
    if state["top_mode"] != "roof":
        return []
    left = [r for r in state["top_roofs"] if roof_ids is not None and r not in roof_ids]
    if left == state["top_roofs"]:
        return []
    if left:
        return wc.edit_wall(doc, wall, top_roofs=left).ops
    mode = "storey" if state["top_storey"] else "fixed"
    return wc.edit_wall(doc, wall, top_mode=mode, top_roofs=[]).ops


def detach_ops_for_deleted(doc: Document, gone: set) -> list:
    """Paredes presas a coberturas que saem: soltas (voltam ao topo de antes)."""
    roof_ids = {g for g in gone if (e := doc.find(g)) is not None and e.is_a("IfcRoof")}
    if not roof_ids:
        return []
    return [op for wall in walls_of(doc, roof_ids) if wall.GlobalId not in gone
            for op in _detach_ops(doc, wall, roof_ids)]


def candidates(doc: Document, roof) -> list:
    """Paredes que ficam sob a cobertura recém-criada (spec/ui 45 §2, ponto (c)): no
    mesmo pavimento, com metade da planta ou mais sob as águas e o topo a até 0,50 m da
    face de baixo. As que não podem ir até a cobertura ficam de fora."""
    from brasbim.core.structure import roofs
    from brasbim.core.walls import rebuild
    from brasbim.core.walls import types as wall_types
    from brasbim.core.walls.wall import read_state

    rstate = roofs.read_state(doc, roof)
    storey = doc.get(rstate["storey"], "IfcBuildingStorey")
    found = []
    for wall in ifcopenshell.util.element.get_decomposition(storey):
        if not wall.is_a("IfcWall"):
            continue
        try:
            state = read_state(doc, wall)
            if state["top_mode"] == "roof" or abs(state["tilt"] or 0.0) > 1e-9 \
                    or state["top_profile"] or wall_types.profile_of(
                        doc.get(state["type"], "IfcWallType")) is not None:
                continue
            plan = footprint(doc, state)
            trial = {**state, "top_mode": "roof", "top_roofs": [roof.GlobalId],
                     "roof_face": "bottom"}
            covered = sum(plan.intersection(s.region).area for s in surfaces(doc, trial))
            if covered < 0.5 * plan.area:
                continue
            z_base = base_z(doc, state)
            low = min(s.z(p) - z_base for s in surfaces(doc, trial)
                      for p in plan.exterior.coords if s.region.covers(_point(p)))
            current = rebuild.height(doc, state)
            if low - _CATCH <= current <= shape(doc, trial).height + _CATCH:
                found.append(wall)
        except (OpError, ValueError, KeyError):
            continue
    return found


def _point(p):
    from shapely.geometry import Point

    return Point(p)


def auto_attach(doc: Document, roof):
    """Transação que prende à cobertura nova as paredes de baixo, ou ``None``."""
    roof = doc.get(_gid(roof))
    walls = candidates(doc, roof)
    if not walls:
        return None
    try:
        return attach(doc, walls, roof)
    except OpError:
        return None


def roofs_over(doc: Document, state: dict) -> list[str]:
    """Coberturas que passam sobre a parede (todas as do projeto, por GlobalId)."""
    from brasbim.core.structure import roofs

    found = []
    for roof in sorted(doc.ifc.by_type("IfcRoof"), key=lambda r: r.GlobalId):
        if not roofs.is_roof(roof):
            continue
        try:
            shape(doc, {**state, "top_mode": "roof", "top_roofs": [roof.GlobalId]})
        except (OpError, ValueError, KeyError):
            continue
        found.append(roof.GlobalId)
    return found


def to_roof_ops(doc: Document, wall, face: str | None = None) -> list:
    """Topo "até a cobertura" escolhido na ficha: as coberturas que passam sobre a
    parede. Recusa se não há nenhuma."""
    from brasbim.core.walls.wall import read_state

    state = read_state(doc, wall)
    found = roofs_over(doc, state)
    if not found:
        raise OpError("não há cobertura sobre esta parede")
    return _attach_ops(doc, wall, found, face)
