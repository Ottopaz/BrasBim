# SPDX-License-Identifier: LGPL-3.0-or-later
"""Escada (``IfcStair``), ``spec/elementos/escada-terreno.md`` §2.

Operações: ``stair.create`` / ``stair.delete`` (data: estado completo) e ``stair.edit``
(before/after: campos de ``STATE_KEYS``).

Estado::

    {"name": "Escada 1", "storey": "<GlobalId>", "shape": "straight" | "L" | "U",
     "start": [x, y], "angle": 0.0, "width": 1.2, "height": None, "risers": None,
     "tread": None, "turn": "left", "split": None, "waist": 0.12, "railing": "both",
     "railing_height": 1.10}

Sistema da escada: origem em ``start`` (canto direito do primeiro degrau, de quem
sobe), x na direção de subida (``angle``), y para a esquerda. O lance 1 ocupa
``0 ≤ y ≤ width``. ``height``/``risers``/``tread`` vazios = calculados (§2.2). A escada
agrega os lances (``IfcStairFlight``), o patamar (``IfcSlab`` ``LANDING``) e os
guarda-corpos (``IfcRailing``), com GlobalIds derivados dela.
"""

from __future__ import annotations

import copy
import json
import logging
import math
from dataclasses import dataclass

import ifcopenshell.api.aggregate
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.util.element

from brasbim.core import guid, materials, props
from brasbim.core.document import Document, OpError, axis_placement, local_placement
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair

log = logging.getLogger(__name__)

PSET = "BrasBim_Escada"
STATE_KEYS = ("name", "storey", "shape", "start", "angle", "width", "height", "risers",
              "tread", "turn", "split", "waist", "railing", "railing_height")
SHAPES = ("straight", "L", "U")
SHAPE_NAMES = {"straight": "reta", "L": "em L", "U": "em U"}
PREDEFINED = {"straight": "STRAIGHT_RUN_STAIR", "L": "QUARTER_TURN_STAIR",
              "U": "HALF_TURN_STAIR"}
RAILINGS = ("both", "left", "right", "none")
MAX_RISER = 0.18
BLONDEL = 0.63
GAP = 0.10  # m: poço entre os lances da escada em U
INSET = 0.05  # m: guarda-corpo para dentro da borda
MATERIAL = "Concreto"


def default_state() -> dict:
    return {"name": "Escada 1", "storey": None, "shape": "straight", "start": [0.0, 0.0],
            "angle": 0.0, "width": 1.20, "height": None, "risers": None, "tread": None,
            "turn": "left", "split": None, "waist": 0.12, "railing": "both",
            "railing_height": 1.10}


def is_stair(entity) -> bool:
    return entity is not None and entity.is_a("IfcStair") and bool(
        ifcopenshell.util.element.get_pset(entity, PSET, should_inherit=False))


def stair_of(entity):
    """A escada do BrasBim de que ``entity`` é peça, ou ``None``."""
    for rel in getattr(entity, "Decomposes", None) or ():
        if rel.is_a("IfcRelAggregates") and is_stair(rel.RelatingObject):
            return rel.RelatingObject
    return None


def parts_of(stair) -> list:
    return sorted((p for rel in stair.IsDecomposedBy or () for p in rel.RelatedObjects),
                  key=lambda p: p.GlobalId)


def all_stairs(doc: Document) -> list:
    return sorted((s for s in doc.ifc.by_type("IfcStair") if is_stair(s)),
                  key=lambda s: s.GlobalId)


def read_state(stair) -> dict:
    values = ifcopenshell.util.element.get_pset(stair, PSET, should_inherit=False) or {}
    if "Parametros" not in values:
        raise OpError(f"escada {stair.GlobalId} sem os parâmetros do BrasBim")
    state = {**default_state(), **json.loads(values["Parametros"])}
    storey = ifcopenshell.util.element.get_container(stair)
    state["storey"] = storey.GlobalId if storey else state["storey"]
    return state


# --- cálculo ---------------------------------------------------------------------------------


@dataclass
class Flight:
    origin: tuple[float, float]  # canto direito do primeiro degrau (sistema da escada)
    dir: tuple[float, float]
    width: float
    z0: float
    treads: int  # degraus (o último espelho chega ao patamar ou ao piso de cima)
    riser: float
    tread: float

    @property
    def left(self) -> tuple[float, float]:
        return (-self.dir[1], self.dir[0])

    @property
    def length(self) -> float:
        return self.treads * self.tread

    def at(self, a: float, lateral: float) -> tuple[float, float]:
        return (self.origin[0] + self.dir[0] * a + self.left[0] * lateral,
                self.origin[1] + self.dir[1] * a + self.left[1] * lateral)

    def outline(self) -> list[tuple[float, float]]:
        length = max(self.length, 0.02)
        return [self.at(0, 0), self.at(length, 0), self.at(length, self.width),
                self.at(0, self.width)]


@dataclass
class Layout:
    height: float
    risers: int
    riser: float
    tread: float
    flights: list
    landings: list  # (x0, x1, y0, y1, z) no sistema da escada


def total_height(doc: Document, state: dict) -> float:
    if state["height"]:
        return float(state["height"])
    storey = doc.get(state["storey"], "IfcBuildingStorey")
    above = doc.storey_above(storey)
    if above is not None:
        return float(above.Elevation or 0.0) - float(storey.Elevation or 0.0)
    return 2.80


def layout(doc: Document, state: dict) -> Layout:
    """Espelhos, piso, lances e patamares (§2.2)."""
    height = total_height(doc, state)
    if height <= 0:
        raise OpError("a escada precisa de altura positiva")
    n = int(state["risers"] or math.ceil(height / MAX_RISER - 1e-9))
    if n < 2:
        raise OpError("a escada precisa de pelo menos 2 espelhos")
    h = height / n
    p = float(state["tread"] or min(max(BLONDEL - 2 * h, 0.25), 0.32))
    w = float(state["width"])
    if w < 0.6:
        raise OpError("a escada precisa de pelo menos 60 cm de largura")
    if state["shape"] == "straight":
        return Layout(height, n, h, p, [Flight((0.0, 0.0), (1.0, 0.0), w, 0.0, n - 1, h, p)],
                      [])
    n1 = int(state["split"] or n // 2)
    if not 1 <= n1 < n:
        raise OpError("a divisão dos espelhos deve deixar degraus nos dois lances")
    n2 = n - n1
    a1 = (n1 - 1) * p
    z1 = n1 * h
    f1 = Flight((0.0, 0.0), (1.0, 0.0), w, 0.0, n1 - 1, h, p)
    left = state["turn"] == "left"
    if state["shape"] == "L":
        landing = (a1, a1 + w, 0.0, w, z1)
        f2 = (Flight((a1 + w, w), (0.0, 1.0), w, z1, n2 - 1, h, p) if left
              else Flight((a1, 0.0), (0.0, -1.0), w, z1, n2 - 1, h, p))
    else:
        if left:
            landing = (a1, a1 + w, 0.0, 2 * w + GAP, z1)
            f2 = Flight((a1, 2 * w + GAP), (-1.0, 0.0), w, z1, n2 - 1, h, p)
        else:
            landing = (a1, a1 + w, -w - GAP, w, z1)
            f2 = Flight((a1, -GAP), (-1.0, 0.0), w, z1, n2 - 1, h, p)
    return Layout(height, n, h, p, [f1, f2], [landing])


def warnings_of(lay: Layout) -> list[str]:
    """Avisos (§2.2): espelho, piso e Blondel fora do usual (sem recusar)."""
    out = []
    h, p = lay.riser, lay.tread
    if not 0.16 - 1e-6 <= h <= 0.18 + 1e-6:
        out.append(f"espelho de {h * 100:.1f} cm fora de 16–18 cm".replace(".", ","))
    if p < 0.28 - 1e-6:
        out.append(f"piso de {p * 100:.1f} cm abaixo de 28 cm".replace(".", ","))
    blondel = 2 * h + p
    if not 0.63 - 1e-6 <= blondel <= 0.64 + 1e-6:
        out.append(f"Blondel 2e + p = {blondel * 100:.1f} cm fora de 63–64 cm".replace(".",
                                                                                       ","))
    return out


def to_storey(state: dict, p) -> tuple[float, float]:
    a = math.radians(state["angle"])
    c, s = math.cos(a), math.sin(a)
    x0, y0 = state["start"]
    return (x0 + c * p[0] - s * p[1], y0 + s * p[0] + c * p[1])


def walking_line(lay: Layout) -> list[tuple[float, float]]:
    """Linha de percurso no meio dos lances e do patamar (sistema da escada)."""
    f1 = lay.flights[0]
    pts = [f1.at(0, f1.width / 2), f1.at(f1.length, f1.width / 2)]
    if lay.landings:
        x0, x1 = lay.landings[0][:2]
        xm = (x0 + x1) / 2
        f2 = lay.flights[1]
        start2 = f2.at(0, f2.width / 2)
        pts.append((xm, pts[-1][1]))
        if f2.dir[0] != 0:  # em U: atravessa o patamar até o eixo do lance 2
            pts.append((xm, start2[1]))
        pts += [start2, f2.at(f2.length, f2.width / 2)]
    return pts


# --- gravação ------------------------------------------------------------------------------------


def _pt(ifc, p):
    return ifc.createIfcCartesianPoint(tuple(float(c) for c in p))


def _flight_solid(ifc, f: Flight, waist: float):
    """Perfil em serra (a, z) extrudado na largura (§2.1)."""
    h, p, k, z0 = f.riser, f.tread, f.treads, f.z0
    if k == 0:  # um espelho só: um bloco
        pts = [(0.0, 0.0), (0.0, h), (0.02, h), (0.02, 0.0)]
    else:
        steps = [(0.0, h)]
        for i in range(1, k + 1):
            steps += [(i * p, i * h), (i * p, (i + 1) * h)]
        waist_v = waist / math.cos(math.atan2(h, p))  # espessura medida na vertical
        end = (k * p, (k + 1) * h - waist_v)
        a0 = (waist_v - h) * p / h  # onde a face de baixo encontra o piso
        if a0 > 0:
            pts = [(0.0, 0.0), *steps, end, (a0, 0.0)]
        else:
            pts = [(0.0, h - waist_v), *steps, end]
    cleaned = []
    for q in pts:
        if not cleaned or math.dist(q, cleaned[-1]) > 1e-9:
            cleaned.append(q)
    profile = ifc.createIfcArbitraryClosedProfileDef(
        "AREA", None, ifc.createIfcPolyline([_pt(ifc, q) for q in [*cleaned, cleaned[0]]]))
    far = f.at(0, f.width)
    position = ifc.createIfcAxis2Placement3D(
        _pt(ifc, (far[0], far[1], z0)), ifc.createIfcDirection((f.dir[1], -f.dir[0], 0.0)),
        ifc.createIfcDirection((f.dir[0], f.dir[1], 0.0)))
    return ifc.createIfcExtrudedAreaSolid(profile, position,
                                          ifc.createIfcDirection((0.0, 0.0, 1.0)), f.width)


def _landing_solid(ifc, landing, waist: float):
    x0, x1, y0, y1, z = landing
    profile = ifc.createIfcRectangleProfileDef(
        "AREA", None, ifc.createIfcAxis2Placement2D(_pt(ifc, ((x0 + x1) / 2, (y0 + y1) / 2)),
                                                    None), x1 - x0, y1 - y0)
    return ifc.createIfcExtrudedAreaSolid(
        profile, ifc.createIfcAxis2Placement3D(_pt(ifc, (0.0, 0.0, z - waist)), None, None),
        ifc.createIfcDirection((0.0, 0.0, 1.0)), waist)


def _styled(doc: Document, item) -> None:
    style = materials.surface_style(doc, MATERIAL)
    if style is not None:
        doc.ifc.createIfcStyledItem(item, [style], None)


def _clear_styles(doc: Document, element) -> None:
    rep = props.representation(element, "Body")
    for item in (rep.Items if rep is not None else []) or []:
        for styled in [i for i in doc.ifc.get_inverse(item) if i.is_a("IfcStyledItem")]:
            doc.ifc.remove(styled)


def _part(doc: Document, stair, gid: str, ifc_class: str, name: str):
    part = doc.find(gid)
    if part is not None and not part.is_a(ifc_class):
        _remove_part(doc, part)
        part = None
    if part is None:
        part = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class=ifc_class)
        part.GlobalId = gid
        rel = ifcopenshell.api.aggregate.assign_object(doc.ifc, products=[part],
                                                       relating_object=stair)
        guid.stamp(rel, stair.GlobalId, "aggregates")
    part.Name = name
    if part.ObjectPlacement is None:
        part.ObjectPlacement = doc.ifc.createIfcLocalPlacement(
            stair.ObjectPlacement, doc.ifc.createIfcAxis2Placement3D(_pt(doc.ifc, (0, 0, 0)),
                                                                     None, None))
    doc.changed.add(gid)
    return part


def _remove_part(doc: Document, part) -> None:
    from brasbim.core import fragment

    _clear_styles(doc, part)
    shape = part.Representation
    part.Representation = None
    ifcopenshell.api.root.remove_product(doc.ifc, product=part)
    if shape is not None:
        fragment.remove(doc.ifc, shape)


def _railing_paths(state: dict, lay: Layout) -> list[tuple[str, list]]:
    """(chave, caminho 3D) dos guarda-corpos: um por lado de cada lance."""
    sides = {"both": ("left", "right"), "left": ("left",), "right": ("right",),
             "none": ()}[state["railing"]]
    out = []
    for i, f in enumerate(lay.flights):
        if f.treads < 1:
            continue
        for side in sides:
            lateral = f.width - INSET if side == "left" else INSET
            a0, a1 = 0.0, f.length
            p0, p1 = f.at(a0, lateral), f.at(a1, lateral)
            z0 = f.z0 + f.riser
            z1 = f.z0 + f.riser * (f.treads + 1)
            out.append((f"railing/{i}/{side}", [(p0[0], p0[1], z0), (p1[0], p1[1], z1)]))
    return out


def write(doc: Document, stair, state: dict) -> None:
    from brasbim.core.structure import railings
    from brasbim.core.walls.types import material_named

    state = {**default_state(), **state}
    if state["shape"] not in SHAPES:
        raise OpError(f"forma de escada inválida: {state['shape']!r}")
    if state["railing"] not in RAILINGS:
        raise OpError(f"guarda-corpo inválido: {state['railing']!r}")
    storey = doc.get(state["storey"], "IfcBuildingStorey")
    lay = layout(doc, state)
    ifc = doc.ifc
    stair.Name = state["name"]
    stair.PredefinedType = PREDEFINED[state["shape"]]
    if ifcopenshell.util.element.get_container(stair) != storey:
        rel = ifcopenshell.api.spatial.assign_container(ifc, products=[stair],
                                                        relating_structure=storey)
        guid.stamp(rel, storey.GlobalId, "contains")
    a = math.radians(state["angle"])
    direction = (math.cos(a), math.sin(a))
    if stair.ObjectPlacement is None:
        stair.ObjectPlacement = local_placement(ifc, storey.ObjectPlacement, 0.0,
                                                state["start"], direction)
    else:
        old = stair.ObjectPlacement.RelativePlacement
        stair.ObjectPlacement.PlacementRelTo = storey.ObjectPlacement
        stair.ObjectPlacement.RelativePlacement = axis_placement(ifc, state["start"], 0.0,
                                                                 direction)
        ifcopenshell.util.element.remove_deep2(ifc, old)
    material_named(doc, MATERIAL)
    materials.ensure_style(doc, MATERIAL)
    wanted = set()
    for i, f in enumerate(lay.flights):
        gid = guid.derived(stair.GlobalId, f"flight/{i}")
        wanted.add(gid)
        part = _part(doc, stair, gid, "IfcStairFlight", f"Lance {i + 1}")
        part.PredefinedType = "STRAIGHT"
        part.NumberOfRisers, part.NumberOfTreads = f.treads + 1, f.treads
        part.RiserHeight, part.TreadLength = f.riser, f.tread
        _clear_styles(doc, part)
        solid = _flight_solid(ifc, f, state["waist"])
        _styled(doc, solid)
        props.replace_representation(doc, part, "Body", ifc.createIfcShapeRepresentation(
            doc.body_context, "Body", "SweptSolid", [solid]))
    for i, landing in enumerate(lay.landings):
        gid = guid.derived(stair.GlobalId, f"landing/{i}")
        wanted.add(gid)
        part = _part(doc, stair, gid, "IfcSlab", f"Patamar {i + 1}")
        part.PredefinedType = "LANDING"
        _clear_styles(doc, part)
        solid = _landing_solid(ifc, landing, state["waist"])
        _styled(doc, solid)
        props.replace_representation(doc, part, "Body", ifc.createIfcShapeRepresentation(
            doc.body_context, "Body", "SweptSolid", [solid]))
    for key, path in _railing_paths(state, lay):
        gid = guid.derived(stair.GlobalId, key)
        wanted.add(gid)
        part = _part(doc, stair, gid, "IfcRailing", "Guarda-corpo")
        railings.write_body(doc, part, path, state["railing_height"], 1.20)
    for part in parts_of(stair):
        if part.GlobalId not in wanted:
            doc.changed.add(part.GlobalId)
            _remove_part(doc, part)
    props.write_pset(doc, stair, PSET, {"Parametros": ifc.createIfcText(json.dumps(
        {k: state[k] for k in STATE_KEYS if k != "storey"}, ensure_ascii=False,
        sort_keys=True))})
    props.write_pset(doc, stair, "Pset_StairCommon", {
        "NumberOfRiser": lay.risers, "NumberOfTreads": lay.risers - len(lay.flights),
        "RiserHeight": lay.riser, "TreadLength": lay.tread})
    for text in warnings_of(lay):
        log.warning("Escada %s: %s (conferir na NBR 9077 e no código de obras)",
                    state["name"], text)
    doc.changed.add(stair.GlobalId)


def remove(doc: Document, stair) -> set[str]:
    gone = {stair.GlobalId}
    for part in parts_of(stair):
        gone.add(part.GlobalId)
        _remove_part(doc, part)
    ifcopenshell.api.root.remove_product(doc.ifc, product=stair)
    return gone


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    stair = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcStair")
    stair.GlobalId = op.id
    try:
        write(doc, stair, copy.deepcopy(op.data))
    except Exception:
        remove(doc, stair)
        raise
    return {op.id}


def _delete(doc: Document, op: Op) -> set[str]:
    return remove(doc, doc.get(op.id, "IfcStair"))


def _edit(doc: Document, op: Op) -> set[str]:
    stair = doc.get(op.id, "IfcStair")
    state = read_state(stair)
    check_before(op, state)
    unknown = set(op.after or {}) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"stair.edit: campos desconhecidos {sorted(unknown)}")
    before = {p.GlobalId for p in parts_of(stair)}
    state.update(copy.deepcopy(op.after or {}))
    write(doc, stair, state)
    return {op.id, *before, *(p.GlobalId for p in parts_of(stair))}


register_inverse_pair("stair.create", _create, "stair.delete", _delete)
register("stair.edit", _edit, invert_swap)


# --- planta -------------------------------------------------------------------------------------


def plan_prims(doc: Document, state: dict, cut: float):
    """Desenho na planta (§2.3): contorno, degraus (tracejados acima do corte), linha de
    corte e linha de percurso com seta. Coordenadas do pavimento."""
    from brasbim.core.annotations.prims import Prims, Stroke

    lay = layout(doc, state)
    out = Prims()

    def g(p):
        return to_storey(state, p)

    broken = False
    for f in lay.flights:
        out.strokes.append(Stroke(tuple(g(q) for q in f.outline()), True, 0.25))
        for i in range(1, f.treads + 1):
            z = f.z0 + (i + 1) * f.riser  # topo do degrau i
            line = (g(f.at(i * f.tread, 0)), g(f.at(i * f.tread, f.width)))
            hidden = z > cut + 1e-6
            if hidden and not broken:
                a = (i - 0.5) * f.tread
                out.strokes.append(Stroke((g(f.at(a - f.tread * 0.6, -0.05)),
                                           g(f.at(a + f.tread * 0.6, f.width + 0.05))),
                                          False, 0.25))
                broken = True
            out.strokes.append(Stroke(line, False, 0.18, "dashed" if hidden else "solid"))
    for x0, x1, y0, y1, _ in lay.landings:
        ring = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
        out.strokes.append(Stroke(tuple(g(q) for q in ring), True, 0.25))
    path = walking_line(lay)
    out.strokes.append(Stroke(tuple(g(q) for q in path), False, 0.13))
    if len(path) >= 2:
        a, b = path[-2], path[-1]
        d = (b[0] - a[0], b[1] - a[1])
        n = math.hypot(*d) or 1.0
        d = (d[0] / n, d[1] / n)
        s = 0.12
        tip = b
        wing = ((b[0] - d[0] * s - d[1] * s * 0.5, b[1] - d[1] * s + d[0] * s * 0.5),
                (b[0] - d[0] * s + d[1] * s * 0.5, b[1] - d[1] * s - d[0] * s * 0.5))
        out.strokes.append(Stroke((g(wing[0]), g(tip), g(wing[1])), False, 0.13))
    for _, path3 in _railing_paths(state, lay):
        out.strokes.append(Stroke(tuple(g(q[:2]) for q in path3), False, 0.13))
    return out


def footprint(doc: Document, state: dict) -> list[list[tuple[float, float]]]:
    lay = layout(doc, state)
    rings = [[to_storey(state, q) for q in f.outline()] for f in lay.flights]
    for x0, x1, y0, y1, _ in lay.landings:
        rings.append([to_storey(state, q) for q in ((x0, y0), (x1, y0), (x1, y1),
                                                    (x0, y1))])
    return rings


# --- comandos --------------------------------------------------------------------------------


def next_name(doc: Document) -> str:
    used = {s.Name for s in all_stairs(doc)}
    n = 1
    while f"Escada {n}" in used:
        n += 1
    return f"Escada {n}"


def create_stair(doc: Document, storey, start, angle: float = 0.0, **options):
    from brasbim.core.ops import Transaction

    state = {**default_state(), "storey": storey if isinstance(storey, str) else
             storey.GlobalId, "start": [float(start[0]), float(start[1])],
             "angle": float(angle), "name": next_name(doc), **options}
    layout(doc, state)  # recusa antes de gravar
    return Transaction("Criar escada", [Op("stair.create", guid.new(), data=state)])


def edit_stair(doc: Document, stair, **changes):
    from brasbim.core.ops import Transaction

    stair = doc.get(stair if isinstance(stair, str) else stair.GlobalId, "IfcStair")
    state = read_state(stair)
    after = {k: copy.deepcopy(v) for k, v in changes.items() if state.get(k) != v}
    unknown = set(after) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    layout(doc, {**state, **after})
    if not after:
        return Transaction("Editar escada", [])
    return Transaction("Editar escada", [Op(
        "stair.edit", stair.GlobalId, before={k: copy.deepcopy(state[k]) for k in after},
        after=after)])


def delete_ops(doc: Document, stair) -> list[Op]:
    return [Op("stair.delete", stair.GlobalId, data=read_state(stair))]


def mapped(state: dict, fn, turn: float = 0.0, mirror_axis: float | None = None) -> dict:
    """Escada levada por uma transformação: espelhar troca o giro e põe o início no outro
    canto do primeiro degrau."""
    if mirror_axis is None:
        start = fn(tuple(state["start"]))
        return {"start": [float(start[0]), float(start[1])],
                "angle": (state["angle"] + turn) % 360.0}
    # o canto esquerdo do primeiro degrau vira o direito da imagem
    left_corner = to_storey(state, (0.0, float(state["width"])))
    start = fn(left_corner)
    angle = (2 * mirror_axis - state["angle"]) % 360.0
    return {"start": [float(start[0]), float(start[1])], "angle": angle,
            "turn": "right" if state["turn"] == "left" else "left"}
