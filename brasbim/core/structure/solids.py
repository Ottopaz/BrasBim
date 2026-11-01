# SPDX-License-Identifier: LGPL-3.0-or-later
"""Operações de sólidos (spec/ui 41 §3): um elemento (alvo) recortado pela forma de outro
(operador), que não muda. Associativo: mexer em qualquer um dos dois refaz o alvo.

No IFC, uma ``IfcRelInterferesElements`` por par, com ``RelatingElement`` = alvo,
``RelatedElement`` = operador, ``ImpliedOrder`` verdadeiro e ``InterferenceType``:

- ``SUBTRACT``: tira do alvo o volume do operador;
- ``SUBTRACT_UP``: tira o operador e tudo acima dele;
- ``SUBTRACT_DOWN``: tira o operador e tudo abaixo dele;
- ``INTERSECT``: o alvo fica só com a parte dentro do operador.

(Os recortes automáticos por prioridade, ``cuts``, usam a mesma relação com o tipo
``Recorte`` e não se misturam com estes.)

O resultado também vai no ``Body`` do alvo, por cima do corpo que a classe refaz:
para cima e para baixo, um ``IfcPolygonalBoundedHalfSpace`` por face de baixo (ou de cima)
do operador, limitado pela projeção dela em planta; subtrair e intersectar, o corpo do
operador como ``IfcTriangulatedFaceSet`` posto nas coordenadas do alvo. O ``NetVolume``
desconta o que saiu.

Operações: ``solid.add`` e ``solid.remove`` (``id`` = GlobalId da relação, ``data`` =
{"target", "operator", "operation"}). Alvos: parede, pilar, viga e laje do BrasBim (não as
águas da cobertura nem os de outra origem); operador: qualquer elemento com corpo, ou uma
cobertura (as águas dela).
"""

from __future__ import annotations

import logging

import ifcopenshell.geom
import ifcopenshell.util.element
import ifcopenshell.util.placement
import numpy as np

from brasbim.core import clip, guid, props
from brasbim.core.document import Document, OpError
from brasbim.core.ops.base import Op, register_derive, register_inverse_pair

log = logging.getLogger(__name__)

SUBTRACT, UP, DOWN, INTERSECT = "SUBTRACT", "SUBTRACT_UP", "SUBTRACT_DOWN", "INTERSECT"
OPERATIONS = (SUBTRACT, UP, DOWN, INTERSECT)
LABELS = {SUBTRACT: "subtrair", UP: "subtrair para cima", DOWN: "subtrair para baixo",
          INTERSECT: "interseção"}
TARGET_CLASSES = ("IfcWall", "IfcColumn", "IfcBeam", "IfcSlab")
_MIN_AREA = 1e-6  # m²: face menor que isto não vira semiespaço


# --- consulta --------------------------------------------------------------------------


def is_solid_rel(rel) -> bool:
    return rel.is_a("IfcRelInterferesElements") and rel.InterferenceType in OPERATIONS


def _rels(doc: Document) -> list:
    return [r for r in doc.ifc.by_type("IfcRelInterferesElements") if is_solid_rel(r)]


def cut_by(element) -> list:
    """Relações em que ``element`` é o alvo (seção "Recortado por" da ficha)."""
    return sorted((r for r in getattr(element, "InterferesElements", ()) or ()
                   if is_solid_rel(r)), key=lambda r: r.RelatedElement.GlobalId
                  if r.RelatedElement else "")


def cutting(element) -> list:
    """Relações em que ``element`` é o operador (seção "Recorta" da ficha)."""
    return sorted((r for r in getattr(element, "IsInterferedByElements", ()) or ()
                   if is_solid_rel(r)), key=lambda r: r.RelatingElement.GlobalId
                  if r.RelatingElement else "")


def relations_of(element) -> list:
    return [*cut_by(element), *cutting(element)]


def can_be_target(doc: Document, element) -> bool:
    from brasbim.core.structure import beams, columns, roofs, slabs

    if element is None or not any(element.is_a(c) for c in TARGET_CLASSES):
        return False
    if element.is_a("IfcWall"):
        return True
    if roofs.is_part(element):
        return False
    module = {"IfcColumn": columns, "IfcBeam": beams, "IfcSlab": slabs}[element.is_a()]
    try:
        return module.read_state(doc, element)["foreign"] is None
    except (OpError, KeyError, ValueError, TypeError):
        return False


def _bodies(element) -> list:
    """Elementos cujo corpo forma o operador: ele mesmo ou, sem corpo, as partes (águas da
    cobertura)."""
    if props.representation(element, "Body") is not None:
        return [element]
    return [p for rel in getattr(element, "IsDecomposedBy", ()) or ()
            for p in rel.RelatedObjects if props.representation(p, "Body") is not None]


def can_be_operator(element) -> bool:
    return element is not None and element.is_a("IfcElement") and bool(_bodies(element))


def _operators_of(element) -> set:
    return {r.RelatedElement.GlobalId for r in cut_by(element) if r.RelatedElement}


def rel_id(target_id: str, operator_id: str) -> str:
    return guid.derived(target_id, f"solid/{operator_id}")


def describe(rel, element) -> str:
    """'Cobertura 1 · subtrair para cima': o outro elemento e a operação."""
    other = rel.RelatedElement if rel.RelatingElement == element else rel.RelatingElement
    name = (other.Name or other.is_a()[3:]) if other is not None else "?"
    return f"{name} · {LABELS[rel.InterferenceType]}"


# --- comandos --------------------------------------------------------------------------


def add_ops(doc: Document, targets, operators, operation: str) -> list[Op]:
    """Uma ``solid.add`` por par alvo × operador. Recusa par repetido, alvo que não pode
    ser recortado, operador sem corpo e ciclos (A recorta B que recorta A)."""
    if operation not in OPERATIONS:
        raise OpError(f"operação de sólido desconhecida: {operation!r}")
    ops, pairs = [], {}
    for target in targets:
        if not can_be_target(doc, target):
            raise OpError(f"{target.Name or target.is_a()[3:]} não pode ser recortado por "
                          "elemento (só parede, pilar, viga e laje do BrasBim)")
        for operator in operators:
            if operator == target:
                continue
            if not can_be_operator(operator):
                raise OpError(f"{operator.Name or operator.is_a()[3:]} não tem corpo para "
                              "recortar")
            gid = rel_id(target.GlobalId, operator.GlobalId)
            if doc.find(gid) is not None:
                raise OpError(f"{target.Name or target.GlobalId} já é recortado por "
                              f"{operator.Name or operator.GlobalId}")
            pairs.setdefault(target.GlobalId, set()).add(operator.GlobalId)
            ops.append(Op("solid.add", gid, data={"target": target.GlobalId,
                                                  "operator": operator.GlobalId,
                                                  "operation": operation}))
    if not ops:
        raise OpError("escolha um elemento diferente do alvo para recortar")
    _check_cycles(doc, pairs)
    return ops


def _check_cycles(doc: Document, extra: dict) -> None:
    graph: dict[str, set] = {}
    for rel in _rels(doc):
        if rel.RelatingElement and rel.RelatedElement:
            graph.setdefault(rel.RelatingElement.GlobalId, set()).add(
                rel.RelatedElement.GlobalId)
    for t, ops in extra.items():
        graph.setdefault(t, set()).update(ops)
    state: dict[str, int] = {}

    def visit(n) -> None:
        state[n] = 1
        for m in graph.get(n, ()):
            if state.get(m) == 1:
                raise OpError("recorte circular: um elemento acabaria recortando a si mesmo")
            if m not in state:
                visit(m)
        state[n] = 2

    for n in sorted(graph):
        if n not in state:
            visit(n)


def _data(rel, warn: bool = False) -> dict:
    d = {"target": rel.RelatingElement.GlobalId, "operator": rel.RelatedElement.GlobalId,
         "operation": rel.InterferenceType}
    if warn:
        d["warn"] = True
    return d


def remove_ops(doc: Document, rels, warn: bool = False) -> list[Op]:
    """``solid.remove`` das relações (``warn``: avisa que o recorte foi desfeito, como ao
    apagar o operador)."""
    return [Op("solid.remove", r.GlobalId, data=_data(r, warn)) for r in rels
            if r.RelatingElement is not None and r.RelatedElement is not None]


def remove_for_deleted(doc: Document, gids) -> list[Op]:
    """Relações que saem com os elementos excluídos: as do alvo (sem aviso) e as do operador
    (com aviso, spec/ui 41 §6 (g))."""
    gids = set(gids)
    ops = []
    for rel in _rels(doc):
        t, o = rel.RelatingElement, rel.RelatedElement
        if t is None or o is None:
            continue
        if t.GlobalId in gids:
            ops += remove_ops(doc, [rel])
        elif o.GlobalId in gids:
            ops += remove_ops(doc, [rel], warn=True)
    return ops


# --- operações -------------------------------------------------------------------------


def _add(doc: Document, op: Op) -> set[str]:
    d = op.data
    target, operator = doc.get(d["target"]), doc.get(d["operator"])
    if d["operation"] not in OPERATIONS:
        raise OpError(f"operação de sólido desconhecida: {d['operation']!r}")
    if doc.find(op.id) is not None:
        raise OpError(f"recorte {op.id} já existe")
    doc.ifc.create_entity("IfcRelInterferesElements", GlobalId=op.id,
                          RelatingElement=target, RelatedElement=operator,
                          InterferenceType=d["operation"], ImpliedOrder=True)
    return {d["target"], d["operator"]}


def _remove(doc: Document, op: Op) -> set[str]:
    rel = doc.get(op.id, "IfcRelInterferesElements")
    d = op.data
    if op.data.get("warn"):
        target = rel.RelatingElement
        operator = rel.RelatedElement
        log.warning("%s deixou de ser recortado por %s (%s): a forma voltou a ser a de "
                    "antes", target.Name or target.GlobalId,
                    operator.Name or operator.GlobalId, LABELS[d["operation"]])
    doc.ifc.remove(rel)
    return {d["target"], d["operator"]}


register_inverse_pair("solid.add", _add, "solid.remove", _remove)


# --- geometria -------------------------------------------------------------------------


def _world_mesh(element):
    """(vértices n×3, triângulos m×3) do corpo do operador, no mundo."""
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    verts, faces = [], []
    for part in _bodies(element):
        try:
            shape = props.body_shape(settings, part)
        except RuntimeError as e:
            log.debug("corpo de %s não processado: %s", part.GlobalId, e)
            continue
        v = np.array(shape.geometry.verts, dtype=float).reshape(-1, 3)
        f = np.array(shape.geometry.faces, dtype=int).reshape(-1, 3)
        faces.append(f + sum(len(x) for x in verts))
        verts.append(v)
    if not verts or not sum(len(f) for f in faces):
        return None
    return np.vstack(verts), np.vstack(faces)


def _inverse(element) -> np.ndarray:
    m = ifcopenshell.util.placement.get_local_placement(element.ObjectPlacement)
    return np.linalg.inv(np.asarray(m, dtype=float))


def _to_local(minv, pts) -> np.ndarray:
    pts = np.asarray(pts, dtype=float).reshape(-1, 3)
    return pts @ minv[:3, :3].T + minv[:3, 3]


def _dir_local(minv, v) -> np.ndarray:
    d = minv[:3, :3] @ np.asarray(v, dtype=float)
    return d / np.linalg.norm(d)


def _point(ifc, p):
    return ifc.createIfcCartesianPoint(tuple(float(c) for c in p))


def _direction(ifc, v):
    return ifc.createIfcDirection(tuple(float(c) for c in v))


def _faceset(ifc, mesh, minv):
    verts, faces = mesh
    local = _to_local(minv, verts)
    return ifc.create_entity(
        "IfcTriangulatedFaceSet",
        Coordinates=ifc.createIfcCartesianPointList3D([tuple(map(float, p)) for p in local]),
        Closed=True, CoordIndex=[tuple(int(i) + 1 for i in f) for f in faces])


def _perpendicular(n) -> np.ndarray:
    a = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    r = a - n * np.dot(a, n)
    return r / np.linalg.norm(r)


def _halfspaces(ifc, mesh, minv, up: bool) -> list:
    """Um semiespaço por face de baixo (``up``: o que fica acima dela) ou de cima (o que
    fica abaixo), limitado pela projeção da face em planta e posto nas coordenadas do
    alvo."""
    verts, faces = mesh
    a, b, c = verts[faces[:, 0]], verts[faces[:, 1]], verts[faces[:, 2]]
    normals = np.cross(b - a, c - a)
    lengths = np.linalg.norm(normals, axis=1)
    groups: dict[tuple, list] = {}
    for k in range(len(faces)):
        if lengths[k] < 1e-12:
            continue
        n = normals[k] / lengths[k]
        if (n[2] > -1e-3) if up else (n[2] < 1e-3):
            continue  # só as faces de baixo (para cima) ou de cima (para baixo)
        key = (*np.round(n, 4), round(float(np.dot(n, a[k])), 4))
        groups.setdefault(key, []).append(k)
    out = []
    # O contorno fica no plano XY do mundo, estendido na vertical (posição do mundo).
    boundary_position = ifc.createIfcAxis2Placement3D(
        _point(ifc, _to_local(minv, [0.0, 0.0, 0.0])[0]),
        _direction(ifc, _dir_local(minv, [0.0, 0.0, 1.0])),
        _direction(ifc, _dir_local(minv, [1.0, 0.0, 0.0])))
    for key in sorted(groups):
        ks = groups[key]
        tris = [[tuple(map(float, p[:2])) for p in (a[k], b[k], c[k])] for k in ks]
        tris = [t if clip.signed_area(t) > 0 else t[::-1] for t in tris]
        region = clip.union(tris)
        n = normals[ks[0]] / lengths[ks[0]]
        p0 = a[ks[0]]
        plane = ifc.createIfcPlane(ifc.createIfcAxis2Placement3D(
            _point(ifc, _to_local(minv, p0)[0]), _direction(ifc, _dir_local(minv, n)),
            _direction(ifc, _dir_local(minv, _perpendicular(n)))))
        for ring in region:
            if clip.signed_area(ring) <= _MIN_AREA:
                continue  # furo da face (ou fiapo): fica sem semiespaço
            points = [ifc.createIfcCartesianPoint((float(x), float(y))) for x, y in ring]
            # AgreementFlag verdadeiro: o semiespaço fica do lado contrário à normal da face
            # (a normal aponta para fora do operador: para baixo nas faces de baixo).
            out.append(ifc.createIfcPolygonalBoundedHalfSpace(
                plane, True, boundary_position, ifc.createIfcPolyline([*points, points[0]])))
    return out


def _volume(item) -> float | None:
    try:
        g = ifcopenshell.geom.create_shape(ifcopenshell.geom.settings(), item)
    except RuntimeError:
        return None
    v = np.array(g.verts, dtype=float).reshape(-1, 3)
    f = np.array(g.faces, dtype=int).reshape(-1, 3)
    if not len(f):
        return 0.0
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)


def _clip_ok(item) -> bool:
    return item.is_a("IfcSweptAreaSolid") or item.is_a("IfcSweptDiskSolid") or item.is_a(
        "IfcBooleanClippingResult")


def apply(doc: Document, target) -> None:
    """Põe as operações de sólido no ``Body`` que a classe acabou de refazer e desconta o
    volume retirado do ``NetVolume``."""
    body = props.representation(target, "Body")
    rels = [r for r in cut_by(target) if r.RelatedElement is not None]
    if body is None or not rels:
        return
    ifc = doc.ifc
    minv = _inverse(target)
    halfspaces, solids = [], []
    for rel in rels:
        mesh = _world_mesh(rel.RelatedElement)
        if mesh is None:
            log.warning("%s: o corpo de %s não foi lido; o recorte fica de fora",
                        target.Name or target.GlobalId,
                        rel.RelatedElement.Name or rel.RelatedElement.GlobalId)
            continue
        kind = rel.InterferenceType
        if kind in (UP, DOWN):
            halfspaces += _halfspaces(ifc, mesh, minv, up=kind == UP)
        else:
            solids.append(("DIFFERENCE" if kind == SUBTRACT else "INTERSECTION",
                           _faceset(ifc, mesh, minv)))
    if not halfspaces and not solids:
        return
    before = [_volume(i) for i in body.Items]
    items, clipping = [], True
    for item in body.Items:
        ok = _clip_ok(item)
        for hs in halfspaces:
            item = (ifc.createIfcBooleanClippingResult if ok else ifc.createIfcBooleanResult)(
                "DIFFERENCE", item, hs)
        for operator, solid in solids:
            item, ok = ifc.createIfcBooleanResult(operator, item, solid), False
        clipping &= ok
        items.append(item)
    body.Items = items
    body.RepresentationType = "Clipping" if clipping else "CSG"
    after = [_volume(i) for i in items]
    if None in before or None in after:
        log.warning("%s: o volume recortado não foi medido", target.Name or target.GlobalId)
        return
    removed = max(0.0, sum(before) - sum(after))
    for name, values in ifcopenshell.util.element.get_psets(target, qtos_only=True).items():
        if values.get("NetVolume") is not None and name.endswith("BaseQuantities"):
            props.write_qto(doc, target, name, {"NetVolume": values["NetVolume"] - removed})
            break


# --- derivação -------------------------------------------------------------------------


def _operator_ids(element) -> set[str]:
    return {element.GlobalId, *(p.GlobalId for p in _bodies(element))}


def expand(doc: Document, dirty: set[str]) -> None:
    """Antes dos corpos: o alvo de um operador que mudou é refeito também (associativo), e
    guarda o ``Body`` atual de cada alvo para saber, no fim, quem foi refeito."""
    rels = [r for r in _rels(doc) if r.RelatingElement and r.RelatedElement]
    changed = True
    while changed:
        changed = False
        for rel in rels:
            t = rel.RelatingElement.GlobalId
            if t not in dirty and _operator_ids(rel.RelatedElement) & dirty:
                dirty.add(t)
                changed = True
    doc.solid_bodies = {}
    for rel in rels:
        body = props.representation(rel.RelatingElement, "Body")
        doc.solid_bodies[rel.RelatingElement.GlobalId] = body.id() if body else None


def _rebuild(doc: Document, target) -> None:
    from brasbim.core.structure import rebuild
    from brasbim.core.walls import rebuild as wall_rebuild

    if target.is_a("IfcWall"):
        wall_rebuild.rebuild_wall(doc, target)
    else:
        rebuild._REBUILD[target.is_a()](doc, target)


def derive(doc: Document, dirty: set[str]) -> None:
    """Depois de todos os corpos: aplica as operações nos alvos refeitos, operadores antes
    dos alvos (um alvo que também recorta outro entra já recortado)."""
    seen = getattr(doc, "solid_bodies", None) or {}
    doc.solid_bodies = {}
    for rel in _rels(doc):  # relação órfã (elemento apagado por outro caminho)
        if rel.RelatingElement is None or rel.RelatedElement is None:
            if rel.RelatingElement is not None:
                dirty.add(rel.RelatingElement.GlobalId)
                _rebuild(doc, rel.RelatingElement)
            doc.ifc.remove(rel)
    targets = {r.RelatingElement.GlobalId: r.RelatingElement for r in _rels(doc)}
    done: set[str] = set()
    applied: set[str] = set()

    def visit(gid: str) -> None:
        if gid in done:
            return
        done.add(gid)
        target = targets[gid]
        for op_gid in sorted(_operators_of(target)):
            if op_gid in targets:
                visit(op_gid)
        body = props.representation(target, "Body")
        rebuilt = body is None or seen.get(gid) != body.id()
        if not rebuilt:
            if gid not in dirty and not _operators_of(target) & applied:
                return  # nada mudou: o corpo já está recortado
            _rebuild(doc, target)  # alvo sujo que a classe não refez
        apply(doc, target)
        applied.add(gid)
        doc.changed.add(gid)

    for gid in sorted(targets):
        visit(gid)


register_derive(expand, first=True)
register_derive(derive, last=True)
