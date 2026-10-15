# SPDX-License-Identifier: LGPL-3.0-or-later
"""Topo inclinado, empena e parede tombada
(``spec/ui/08-parede-no-3d-topo-e-inclinacao.md`` §4, §5 e §7): UI77 a UI81 no núcleo.
O resultado é conferido no IFC gravado e no sólido triangulado pelo IfcOpenShell."""

import json
import math

import ifcopenshell.geom
import ifcopenshell.util.element as ue
import ifcopenshell.validate
import numpy as np
import pytest
from conftest import PROJECT_ID, Model, snapshot

from brasbim.core import transform
from brasbim.core.document import Document, OpError
from brasbim.core.fillings import commands as fc
from brasbim.core.ops import History, Transaction
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import top


def _vertices(wall) -> np.ndarray:
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    shape = ifcopenshell.geom.create_shape(settings, wall)
    return np.asarray(shape.geometry.verts).reshape(-1, 3)


def _top_z(verts, x) -> float:
    return max(z for vx, _, z in verts if abs(vx - x) < 1e-6)


def _profile(state) -> np.ndarray:
    return np.array(state["top_profile"], dtype=float)


def _body(wall):
    return next(r for r in wall.Representation.Representations
                if r.RepresentationIdentifier == "Body")


def _door(m, wall, distance, height):
    t = m.commit(fc.create_door_type(m.doc, "P1"))
    return fc.create_door(m.doc, t.ops[0].id, wall, distance, width=0.8, height=height)


def _gable(m):
    wall = m.wall((0, 0), (6, 0), top_mode="fixed")
    m.commit(cmd.edit_wall(m.doc, wall, top_shape="gable",
                           top_profile=top.gable(6, 2.8, 4.0)))
    return wall


def test_ui77_empena(model, tmp_path):
    _gable(model)
    ifc = model.reopen(tmp_path)
    (wall,) = ifc.by_type("IfcWall")
    body = _body(wall)
    assert body.RepresentationType == "Clipping"
    (result,) = body.Items
    assert result.is_a("IfcBooleanClippingResult") and result.Operator == "DIFFERENCE"
    assert result.FirstOperand.is_a("IfcBooleanClippingResult")
    assert result.FirstOperand.FirstOperand.is_a("IfcExtrudedAreaSolid")
    assert result.FirstOperand.FirstOperand.Depth == pytest.approx(4.0)
    assert len(ifc.by_type("IfcPolygonalBoundedHalfSpace")) == 2

    verts = _vertices(wall)
    assert verts[:, 2].max() == pytest.approx(4.0)
    assert _top_z(verts, 3.0) == pytest.approx(4.0)
    assert _top_z(verts, 0.0) == pytest.approx(2.8)
    assert _top_z(verts, 6.0) == pytest.approx(2.8)

    assert ue.get_material(wall, should_inherit=False).is_a("IfcMaterialLayerSetUsage")
    qto = ue.get_pset(wall, "Qto_WallBaseQuantities")
    assert qto["Height"] == pytest.approx(4.0)
    side = 6 * 2.8 + 6 * 1.2 / 2
    assert qto["GrossSideArea"] == pytest.approx(side)
    assert qto["NetVolume"] == pytest.approx(side * 0.14)
    pset = ue.get_pset(wall, "BrasBim_Parede")
    assert pset["FormaTopo"] == "EMPENA"
    assert pset["PerfilTopoPosicoes"] == pytest.approx([0, 3, 6])
    assert pset["PerfilTopoAlturas"] == pytest.approx([2.8, 4.0, 2.8])
    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifc, logger)
    assert logger.statements == []


def test_ui77_voltar_a_topo_plano(model):
    wall = _gable(model)
    model.commit(cmd.edit_wall(model.doc, wall, top_shape="flat", top_profile=[]))
    assert _body(wall).RepresentationType == "SweptSolid"
    assert not model.doc.ifc.by_type("IfcPolygonalBoundedHalfSpace")
    assert "PerfilTopoAlturas" not in ue.get_pset(wall, "BrasBim_Parede")
    assert ue.get_pset(wall, "Qto_WallBaseQuantities")["Height"] == pytest.approx(2.8)


def test_ui78_inclinado_e_portas(model):
    wall = model.wall((0, 0), (6, 0), top_mode="fixed")
    model.commit(cmd.edit_wall(model.doc, wall, top_shape="slope",
                               top_profile=top.slope(6, 2.4, 3.0)))
    model.commit(_door(model, wall, 2.0, 2.10))
    with pytest.raises(OpError, match="ultrapassa o topo"):
        _door(model, wall, 0.1, 2.60)
    assert len(wall.HasOpenings) == 1

    model.commit(cmd.move_wall_end(model.doc, wall, "end", (8, 0), carry=False))
    state = cmd.read_state(model.doc, wall)
    assert _profile(state) == pytest.approx(np.array([[0, 2.4], [8, 3.0]]))
    verts = _vertices(wall)
    assert _top_z(verts, 8.0) == pytest.approx(3.0)
    assert _top_z(verts, 0.0) == pytest.approx(2.4)


def test_ui78_cumeeira_continua_no_meio(model):
    wall = _gable(model)
    model.commit(cmd.move_wall_end(model.doc, wall, "end", (10, 0), carry=False))
    assert _profile(cmd.read_state(model.doc, wall)) == pytest.approx(
        np.array([[0, 2.8], [5, 4.0], [10, 2.8]]))


def test_ui78_espelhar_inverte_o_perfil(model):
    wall = model.wall((0, 0), (6, 0), top_mode="fixed")
    model.commit(cmd.edit_wall(model.doc, wall, top_shape="free",
                               top_profile=[[0, 2.8], [1, 3.5], [6, 3.0]]))
    model.commit(transform.mirror_elements(model.doc, [wall.GlobalId], (0, 5), (1, 5)))
    assert _profile(cmd.read_state(model.doc, wall)) == pytest.approx(
        np.array([[0, 3.0], [5, 3.5], [6, 2.8]]))
    verts = _vertices(wall)
    assert _top_z(verts, 1.0) == pytest.approx(3.5)  # o ponto alto continua no mesmo lugar


def test_ui78_perfil_invalido_e_divisao(model):
    wall = model.wall((0, 0), (6, 0), top_mode="fixed")
    with pytest.raises(OpError, match="início ao fim"):
        model.commit(cmd.edit_wall(model.doc, wall, top_shape="slope",
                                   top_profile=top.slope(5, 2.4, 3.0)))
    model.commit(cmd.edit_wall(model.doc, wall, top_shape="slope",
                               top_profile=top.slope(6, 2.4, 3.0)))
    with pytest.raises(OpError, match="topo inclinado"):
        cmd.split_wall(model.doc, wall, (3, 0))


def test_ui79_parede_tombada(model, tmp_path):
    wall = model.wall((0, 0), (5, 0), top_mode="fixed")
    model.commit(cmd.edit_wall(model.doc, wall, tilt=10.0))
    ifc = model.reopen(tmp_path)
    (wall_r,) = ifc.by_type("IfcWall")
    (solid,) = _body(wall_r).Items
    assert solid.ExtrudedDirection.DirectionRatios == pytest.approx((0, 0.17365, 0.98481),
                                                                    abs=1e-4)
    assert solid.Depth * math.cos(math.radians(10)) == pytest.approx(2.8)
    material = ue.get_material(wall_r, should_inherit=False)
    assert material.is_a("IfcMaterialLayerSet")
    assert material == ue.get_material(ue.get_type(wall_r))
    assert not ifc.by_type("IfcMaterialLayerSetUsage")

    verts = _vertices(wall_r)
    top_ys = [y for _, y, z in verts if abs(z - 2.8) < 1e-6]
    base_ys = [y for _, y, z in verts if abs(z) < 1e-6]
    assert max(base_ys) == pytest.approx(0.0)  # a linha de referência na base fica
    assert max(top_ys) == pytest.approx(2.8 * math.tan(math.radians(10)), abs=1e-3)
    assert max(top_ys) == pytest.approx(0.494, abs=1e-3)
    width = max(top_ys) - min(top_ys)
    assert width * math.cos(math.radians(10)) == pytest.approx(0.14)  # espessura verdadeira
    assert ue.get_pset(wall_r, "BrasBim_Parede")["Inclinacao"] == pytest.approx(10.0)
    assert ue.get_pset(wall_r, "Qto_WallBaseQuantities")["Width"] == pytest.approx(0.14)

    model.commit(cmd.edit_wall(model.doc, wall, tilt=0.0))
    usage = ue.get_material(wall, should_inherit=False)
    assert usage.is_a("IfcMaterialLayerSetUsage")
    assert usage.DirectionSense == "POSITIVE" and usage.OffsetFromReferenceLine == \
        pytest.approx(-0.14)
    (solid,) = _body(wall).Items
    assert solid.ExtrudedDirection.DirectionRatios == pytest.approx((0, 0, 1))


def test_ui79_limite_e_arco(model):
    wall = model.wall((0, 0), (5, 0))
    with pytest.raises(OpError, match="limite"):
        model.commit(cmd.edit_wall(model.doc, wall, tilt=50.0))
    arc = model.doc.get(model.commit(cmd.create_arc_wall(
        model.doc, model.type14, model.terreo, (0, 5), (2, 6), (4, 5))).ops[0].id)
    with pytest.raises(OpError, match="só em parede reta"):
        model.commit(cmd.edit_wall(model.doc, arc, tilt=5.0))


def test_ui79_tombada_com_topo_inclinado(model):
    wall = _gable(model)
    model.commit(cmd.edit_wall(model.doc, wall, tilt=-10.0))
    verts = _vertices(wall)
    assert verts[:, 2].max() == pytest.approx(4.0)
    ridge = [y for x, y, z in verts if abs(z - 4.0) < 1e-6]
    assert min(ridge) == pytest.approx(-0.142 - 4.0 * math.tan(math.radians(10)), abs=1e-3)


def test_ui80_tombada_e_aberturas(model):
    wall = model.wall((0, 0), (5, 0))
    model.commit(_door(model, wall, 1.0, 2.1))
    with pytest.raises(OpError, match="não aceita aberturas"):
        model.commit(cmd.edit_wall(model.doc, wall, tilt=5.0))
    assert cmd.read_state(model.doc, wall)["tilt"] == 0.0

    other = model.wall((0, 3), (5, 3))
    model.commit(cmd.edit_wall(model.doc, other, tilt=5.0))
    with pytest.raises(OpError, match="não aceita aberturas"):
        _door(model, other, 1.0, 2.1)


def test_ui81_reabrir_e_reaplicar_diario(tmp_path):
    m = Model()
    start = len(m.history.undo_stack)
    a = _gable(m)
    b = m.wall((0, 2), (5, 2), top_mode="fixed")
    m.commit(cmd.edit_wall(m.doc, b, top_shape="free",
                           top_profile=[[0, 2.5], [2, 3.2], [4, 2.9], [5, 3.1]]))
    m.commit(cmd.edit_wall(m.doc, b, tilt=-7.5))
    c = m.wall((0, 5), (5, 5), top_mode="fixed")
    m.commit(cmd.edit_wall(m.doc, c, tilt=12.0))
    m.commit(cmd.edit_wall(m.doc, c, tilt=0.0))
    m.commit(cmd.move_wall_end(m.doc, a, "start", (-1, 0), carry=False))
    states = {w.GlobalId: cmd.read_state(m.doc, w) for w in (a, b, c)}

    path = tmp_path / "topo.ifc"
    m.doc.save(str(path))
    reopened = Document.open(str(path))
    for gid, state in states.items():
        again = cmd.read_state(reopened, reopened.get(gid))
        assert again["top_shape"] == state["top_shape"]
        assert _profile(again) == pytest.approx(_profile(state))
        assert again["tilt"] == pytest.approx(state["tilt"])

    final = snapshot(m.doc.ifc)
    count = len(m.history.undo_stack) - start
    for _ in range(count):
        m.history.undo()
    for _ in range(count):
        m.history.redo()
    assert snapshot(m.doc.ifc) == final
    journal = json.loads(json.dumps([tx.to_dict() for tx in m.history.journal]))
    other = Document.new(project_id=PROJECT_ID)
    history = History(other)
    for tx in journal:
        history.commit(Transaction.from_dict(tx))
    assert snapshot(other.ifc) == final
