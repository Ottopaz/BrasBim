# SPDX-License-Identifier: LGPL-3.0-or-later
"""Ocorrência de parede (``IfcWall``): estado, leitura/gravação e operações.

Operações (spec §5.2): ``wall.create`` / ``wall.delete`` (data: estado completo),
``wall.edit`` (before/after: campos de ``params.STATE_KEYS`` alterados) e ``wall.split``
(data: ``path`` original, ponto ``at`` e GlobalId ``new`` da segunda parte), cuja inversa
é ``wall.merge`` (mesmos dados).

O IFC é a fonte da verdade: o estado é lido do modelo (tipo, contenção, posicionamento,
curva ``Axis``, Pset ``BrasBim_Parede``, ``Pset_WallCommon``) e gravado de volta nele.
O que é derivado (corpo, ``IfcMaterialLayerSetUsage``, quantidades) fica em ``rebuild``.
"""

from __future__ import annotations

import math

import ifcopenshell.api.material
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.type
import ifcopenshell.util.element

from brasbim.core import geom2d, guid, props
from brasbim.core.document import Document, OpError, axis_placement, local_placement
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair
from brasbim.core.walls import params, rebuild, top
from brasbim.core.walls import types as wall_types

COMMON_PSET = "Pset_WallCommon"


# --- leitura -----------------------------------------------------------------


def _frame(wall) -> tuple[tuple[float, float], float, float]:
    """(origem no pavimento, ângulo do eixo x local, z) do posicionamento da parede."""
    rp = wall.ObjectPlacement.RelativePlacement
    x, y, *z = rp.Location.Coordinates
    d = rp.RefDirection.DirectionRatios if rp.RefDirection else (1.0, 0.0, 0.0)
    return (float(x), float(y)), math.atan2(d[1], d[0]), float(z[0]) if z else 0.0


def to_storey(origin, angle, p) -> tuple[float, float]:
    c, s = math.cos(angle), math.sin(angle)
    return (origin[0] + c * p[0] - s * p[1], origin[1] + s * p[0] + c * p[1])


def _read_path(wall) -> dict:
    axis = props.representation(wall, "Axis")
    if axis is None:
        raise OpError(f"parede {wall.GlobalId} sem representação Axis")
    origin, angle, _ = _frame(wall)
    curve = axis.Items[0]
    points = None
    if curve.is_a("IfcPolyline"):
        points = [p.Coordinates for p in curve.Points]
    elif curve.is_a("IfcIndexedPolyCurve") and not curve.Segments:
        points = curve.Points.CoordList  # IFC de outra origem
    if points is not None:
        if len(points) != 2:
            raise OpError(f"parede {wall.GlobalId}: eixo poligonal com {len(points)} pontos")
        start, end = (to_storey(origin, angle, p[:2]) for p in points)
        return geom2d.LinePath(start, end).to_dict()
    if curve.is_a("IfcTrimmedCurve"):
        radius = float(curve.BasisCurve.Radius)
        ccw = bool(curve.SenseAgreement)
        local_end = next(t for t in curve.Trim2 if t.is_a("IfcCartesianPoint")).Coordinates
        x, y = local_end[0], local_end[1]
        t = math.atan2(x, radius - y) if ccw else math.atan2(x, y + radius)
        large = t % (2 * math.pi) > math.pi
        end = to_storey(origin, angle, (x, y))
        return geom2d.ArcPath(origin, end, radius, ccw, large).to_dict()
    raise OpError(f"curva Axis não suportada: {curve.is_a()}")


def common_defaults(wall_type) -> dict:
    """Padrão de ``Pset_WallCommon`` para paredes do tipo (o que não é gravado como
    diferença em ``common``)."""
    defaults = {"Reference": wall_type.Name, "Status": "NEW", "IsExternal": False}
    load_bearing = {"SOLIDWALL": True, "PARTITIONING": False}.get(wall_type.PredefinedType)
    if load_bearing is not None:
        defaults["LoadBearing"] = load_bearing
    return defaults


def _read_common(wall, wall_type) -> dict:
    values = ifcopenshell.util.element.get_pset(wall, COMMON_PSET, should_inherit=False) or {}
    values = {k: v for k, v in values.items() if k != "id"}
    if isinstance(values.get("Status"), (list, tuple)):
        values["Status"] = values["Status"][0] if values["Status"] else None
    defaults = common_defaults(wall_type) if wall_type else {}
    return {k: v for k, v in values.items() if defaults.get(k) != v}


def read_state(doc: Document, wall) -> dict:
    state = params.default_state()
    wall_type = ifcopenshell.util.element.get_type(wall)
    container = ifcopenshell.util.element.get_container(wall)
    state["name"] = wall.Name
    state["type"] = wall_type.GlobalId if wall_type else None
    state["storey"] = container.GlobalId if container else None
    state["path"] = _read_path(wall)
    values = ifcopenshell.util.element.get_pset(wall, params.PSET, should_inherit=False)
    if values:
        state.update(params.state_from_pset(values))
    else:
        # IFC de outra origem: lido como altura fixa (spec §3.1).
        state["base_offset"] = _frame(wall)[2]
        body = props.representation(wall, "Body")
        if body is not None and body.Items[0].is_a("IfcExtrudedAreaSolid"):
            state["fixed_height"] = float(body.Items[0].Depth)
        usage = ifcopenshell.util.element.get_material(wall, should_inherit=False)
        if wall_type and usage is not None and usage.is_a("IfcMaterialLayerSetUsage"):
            found = params.ref_line_from_usage(
                usage.DirectionSense, usage.OffsetFromReferenceLine, wall_types.thickness(wall_type)
            )
            if found:
                state["ref_line"], state["flip_layers"] = found
    state["common"] = _read_common(wall, wall_type)
    return state


# --- gravação ----------------------------------------------------------------

TILT_WITH_OPENINGS = "parede tombada ainda não aceita aberturas"
_PROFILE_PROPS = ("PerfilTopoPosicoes", "PerfilTopoAlturas")


def _validate_shape(state: dict, path: geom2d.Path) -> None:
    """Topo com perfil e inclinação só em parede reta (spec/ui 08 §4.1, §5.1)."""
    shape = state.get("top_shape") or "flat"
    straight = isinstance(path, geom2d.LinePath)
    if not straight and (shape != "flat" or abs(state.get("tilt") or 0.0) > 1e-9):
        raise ValueError("topo inclinado e parede tombada só em parede reta")
    top.validate(shape, state.get("top_profile") or [], path.length)


def _remove_profile_props(doc: Document, pset) -> None:
    """As listas do perfil são refeitas a cada gravação (o IfcOpenShell não edita
    ``IfcPropertyListValue``)."""
    old = [p for p in pset.HasProperties or [] if p.Name in _PROFILE_PROPS]
    if old:
        pset.HasProperties = [p for p in pset.HasProperties if p not in old]
        for prop in old:
            ifcopenshell.util.element.remove_deep2(doc.ifc, prop)



def _assign_type(doc: Document, wall, wall_type, tilted: bool = False) -> None:
    """Tipo e material. Parede tombada associa o ``IfcMaterialLayerSet`` do tipo, sem
    ``IfcMaterialLayerSetUsage`` (o IFC exige extrusão vertical nele; spec/ui 08 §5.2)."""
    if ifcopenshell.util.element.get_type(wall) != wall_type:
        rel = ifcopenshell.api.type.assign_type(
            doc.ifc, related_objects=[wall], relating_type=wall_type
        )
        guid.stamp(rel, wall_type.GlobalId, "types")
    lset = wall_types.layer_set(wall_type)
    usage = ifcopenshell.util.element.get_material(wall, should_inherit=False)
    if tilted:
        wanted = usage is not None and usage == lset
    else:
        wanted = (usage is not None and usage.is_a("IfcMaterialLayerSetUsage")
                  and usage.ForLayerSet == lset)
    if not wanted:
        if usage is not None:
            ifcopenshell.api.material.unassign_material(doc.ifc, products=[wall])
        if tilted:
            rel = doc.ifc.create_entity(
                "IfcRelAssociatesMaterial", GlobalId=guid.new(), RelatedObjects=[wall],
                RelatingMaterial=lset)
        else:
            ifcopenshell.api.material.assign_material(
                doc.ifc, products=[wall], type="IfcMaterialLayerSetUsage", material=lset
            )
    rel = next(r for r in wall.HasAssociations if r.is_a("IfcRelAssociatesMaterial"))
    guid.stamp(rel, wall.GlobalId, "material")


def _place(doc: Document, wall, storey, path: geom2d.Path, base_offset: float) -> None:
    direction = (math.cos(path.start_angle), math.sin(path.start_angle))
    placement = wall.ObjectPlacement
    if placement is None:
        wall.ObjectPlacement = local_placement(
            doc.ifc, storey.ObjectPlacement, base_offset, path.start, direction
        )
        return
    old = placement.RelativePlacement
    placement.PlacementRelTo = storey.ObjectPlacement
    placement.RelativePlacement = axis_placement(doc.ifc, path.start, base_offset, direction)
    ifcopenshell.util.element.remove_deep2(doc.ifc, old)


def write_state(doc: Document, wall, state: dict) -> None:
    try:
        params.validate(state)
        path = geom2d.path_from_dict(state["path"])
        _validate_shape(state, path)
    except (ValueError, KeyError) as e:
        raise OpError(f"parede {wall.GlobalId}: {e}") from e
    tilted = abs(state.get("tilt") or 0.0) > 1e-9
    if tilted and wall.HasOpenings:
        raise OpError(TILT_WITH_OPENINGS)
    wall_type = doc.get(state["type"], "IfcWallType")
    storey = doc.get(state["storey"], "IfcBuildingStorey")
    if state["top_mode"] == "storey":
        doc.get(state["top_storey"], "IfcBuildingStorey")

    wall.Name = state["name"]
    _assign_type(doc, wall, wall_type, tilted)
    if ifcopenshell.util.element.get_container(wall) != storey:
        rel = ifcopenshell.api.spatial.assign_container(
            doc.ifc, products=[wall], relating_structure=storey
        )
        guid.stamp(rel, storey.GlobalId, "contains")
    _place(doc, wall, storey, path, float(state["base_offset"]))

    # Axis faz parte do estado (o caminho); o corpo é derivado.
    rebuild.set_axis(doc, wall, path)

    values = params.pset_values(state)
    for key in ("DeslocamentoBase", "DeslocamentoTopo", "AlturaFixa"):
        values[key] = doc.ifc.createIfcLengthMeasure(values[key])
    for key in ("PavimentoBase", "PavimentoTopo"):
        if values[key] is not None:
            values[key] = doc.ifc.createIfcIdentifier(values[key])
    if values["SemJuncaoCom"] is not None:
        values["SemJuncaoCom"] = doc.ifc.createIfcText(values["SemJuncaoCom"])
    values["Inclinacao"] = doc.ifc.createIfcPlaneAngleMeasure(values["Inclinacao"])
    pset = props.ensure_pset(doc, wall, params.PSET)
    _remove_profile_props(doc, pset)
    profile = state.get("top_profile") or []
    if profile:
        for key, column in (("PerfilTopoPosicoes", 0), ("PerfilTopoAlturas", 1)):
            values[key] = doc.ifc.create_entity(
                "IfcPropertyListValue", Name=key,
                ListValues=[doc.ifc.createIfcLengthMeasure(float(p[column])) for p in profile])
    ifcopenshell.api.pset.edit_pset(doc.ifc, pset=pset, properties=values)

    common = {**common_defaults(wall_type), **(state.get("common") or {})}
    if common.get("Status") is not None:
        common["Status"] = [common["Status"]]
    props.write_pset(doc, wall, COMMON_PSET, common)


# --- operações ---------------------------------------------------------------


def _full_state(op: Op) -> dict:
    return {**params.default_state(), **op.data}


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    wall = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcWall")
    wall.GlobalId = op.id
    try:
        write_state(doc, wall, _full_state(op))
    except Exception:
        remove(doc, wall)
        raise
    return {op.id}


def remove(doc: Document, wall) -> None:
    ifcopenshell.api.root.remove_product(doc.ifc, product=wall)


def _delete(doc: Document, op: Op) -> set[str]:
    remove(doc, doc.get(op.id, "IfcWall"))
    return {op.id}


def _edit(doc: Document, op: Op) -> set[str]:
    wall = doc.get(op.id, "IfcWall")
    state = read_state(doc, wall)
    check_before(op, state)
    unknown = set(op.after or {}) - set(params.STATE_KEYS)
    if unknown:
        raise OpError(f"wall.edit: campos desconhecidos {sorted(unknown)}")
    after = op.after or {}
    if "path" in after and "top_profile" not in after and state["top_profile"]:
        # Mudar o comprimento reposiciona os pontos do topo (spec/ui 08 §4.1).
        old = geom2d.path_from_dict(state["path"]).length
        new = geom2d.path_from_dict(after["path"]).length
        state["top_profile"] = top.scaled(state["top_profile"], old, new)
    state.update(after)
    write_state(doc, wall, state)
    return {op.id}


def _split(doc: Document, op: Op) -> set[str]:
    wall = doc.get(op.id, "IfcWall")
    state = read_state(doc, wall)
    check_before(Op(op.op, op.id, before={"path": op.data["path"]}), state)
    if doc.find(op.data["new"]) is not None:
        raise OpError(f"GlobalId {op.data['new']} já existe")
    try:
        first, second, _ = geom2d.split(geom2d.path_from_dict(state["path"]),
                                        tuple(op.data["at"]))
    except ValueError as e:
        raise OpError(f"wall.split {op.id}: {e}") from e
    write_state(doc, wall, {**state, "path": first.to_dict()})
    _create(doc, Op("wall.create", op.data["new"], data={**state, "path": second.to_dict()}))
    return {op.id, op.data["new"]}


def _merge(doc: Document, op: Op) -> set[str]:
    wall = doc.get(op.id, "IfcWall")
    other = doc.get(op.data["new"], "IfcWall")
    if other.HasOpenings or any(r.is_a("IfcRelConnectsPathElements")
                                for r in (*other.ConnectedTo, *other.ConnectedFrom)):
        raise OpError(f"wall.merge: {other.GlobalId} ainda tem aberturas ou junções")
    remove(doc, other)
    write_state(doc, wall, {**read_state(doc, wall), "path": op.data["path"]})
    return {op.id}


def _swap_split(name: str):
    return lambda op: Op(name, op.id, data=dict(op.data))


register_inverse_pair("wall.create", _create, "wall.delete", _delete)
register("wall.edit", _edit, invert_swap)
register("wall.split", _split, _swap_split("wall.merge"))
register("wall.merge", _merge, _swap_split("wall.split"))
