# SPDX-License-Identifier: LGPL-3.0-or-later
"""Edição da versão 0.2, no núcleo (``spec/ui/02-edicao.md``): alças, mover, copiar,
girar, pavimentos, tipos, edição em lote e seleção por janela."""

import json
import math

import ifcopenshell.util.element as ue
import ifcopenshell.util.placement
import pytest
from conftest import LAYERS_14, PROJECT_ID, Model, snapshot

from brasbim.core import geom2d, plan, transform
from brasbim.core.document import Document, OpError
from brasbim.core.fillings import commands as fc
from brasbim.core.fillings import door_types
from brasbim.core.ops import History, Transaction
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import openings
from brasbim.core.walls.wall import read_state


def _rect(model, a=(0, 0), b=(4, 3)):
    tx = model.commit(cmd.create_rectangle(model.doc, model.type14, model.terreo, a, b))
    return [model.doc.get(op.id) for op in tx.ops if op.op == "wall.create"]


def _path(model, wall):
    return geom2d.path_from_dict(read_state(model.doc, wall)["path"])


def _joins(model):
    return model.doc.ifc.by_type("IfcRelConnectsPathElements")


def _door_type(model, name="P1"):
    tx = model.commit(fc.create_door_type(model.doc, name))
    return model.doc.get(tx.ops[0].id)


def _door(model, wall, distance=1.0, door_type=None):
    door_type = door_type or _door_type(model)
    tx = model.commit(fc.create_door(model.doc, door_type, wall, distance))
    return model.doc.get(next(op.id for op in tx.ops if op.op == "door.create"))


def _world_xy(element):
    m = ifcopenshell.util.placement.get_local_placement(element.ObjectPlacement)
    return (float(m[0][3]), float(m[1][3]))


def _wall_with_end(walls, model, point):
    return next(w for w in walls if _path(model, w).end == pytest.approx(point)
                or _path(model, w).start == pytest.approx(point))


# --- alças (§4) ------------------------------------------------------------------------


def test_ui15_extremidade_leva_a_vizinha_em_l(model):
    walls = _rect(model)
    initial = snapshot(model.doc.ifc)
    wall = next(w for w in walls if _path(model, w).end == pytest.approx((4, 3)))
    tx = model.commit(cmd.move_wall_end(model.doc, wall, "end", (5, 3.5)))
    assert len(_joins(model)) == 4
    ends = [p for w in walls for p in (_path(model, w).start, _path(model, w).end)]
    assert sum(1 for p in ends if p == pytest.approx((5, 3.5))) == 2
    assert [op.op for op in tx.ops].count("wall.edit") == 2
    model.history.undo()
    assert snapshot(model.doc.ifc) == initial


def test_ui15_ctrl_solta_a_junção(model):
    walls = _rect(model)
    wall = next(w for w in walls if _path(model, w).end == pytest.approx((4, 3)))
    model.commit(cmd.move_wall_end(model.doc, wall, "end", (5, 3.5), carry=False))
    assert len(_joins(model)) == 3


def test_ui16_porta_fica_no_lugar_ao_mover_o_inicio(model):
    wall = model.wall((0, 0), (5, 0))
    door = _door(model, wall, 2.0)
    before = _world_xy(door)
    model.commit(cmd.move_wall_end(model.doc, wall, "start", (1, 0)))
    assert _world_xy(door) == pytest.approx(before)
    opening = fc.opening_of(door)
    assert openings.read_state(opening)["distance"] == pytest.approx(1.0)
    with pytest.raises(OpError, match="não caberia"):
        cmd.move_wall_end(model.doc, wall, "start", (2.5, 0))


def test_ui17_alca_do_meio_estica_as_vizinhas(model):
    walls = _rect(model)
    bottom = next(w for w in walls
                  if abs(_path(model, w).start[1]) + abs(_path(model, w).end[1]) < 1e-9)
    path = _path(model, bottom)
    # O deslocamento é para a esquerda do caminho; para baixo, sinal conforme o sentido.
    left = geom2d.frame(path).vector_to_global((0.0, 1.0))
    distance = -0.5 if left[1] > 0 else 0.5
    tx = model.commit(cmd.offset_wall(model.doc, bottom, distance))
    new = _path(model, bottom)
    assert new.length == pytest.approx(4.0)
    assert {tuple(round(c, 6) for c in p) for p in (new.start, new.end)} == {(0, -0.5),
                                                                              (4, -0.5)}
    lengths = sorted(round(_path(model, w).length, 6) for w in walls)
    assert lengths == [3.5, 3.5, 4, 4]
    assert len(_joins(model)) == 4
    assert [op.op for op in tx.ops].count("wall.edit") == 3


def test_ui17_vizinha_em_t_acompanha(model):
    a = model.wall((0, 0), (6, 0))
    b = model.wall((3, 0), (3, 4))
    assert len(_joins(model)) == 1
    model.commit(cmd.offset_wall(model.doc, a, 1.0))  # esquerda de A = +y
    assert _path(model, b).start == pytest.approx((3, 1))
    assert _path(model, a).start == pytest.approx((0, 1))
    (rel,) = _joins(model)
    assert "ATPATH" in (rel.RelatingConnectionType, rel.RelatedConnectionType)


def test_ui17_vizinha_invertida_recusa(model):
    a = model.wall((0, 0), (6, 0))
    model.wall((3, 0), (3, 1))
    with pytest.raises(OpError, match="invertida"):
        cmd.offset_wall(model.doc, a, 2.0)


def test_ui18_alca_do_arco(model):
    tx = model.commit(cmd.create_arc_wall(model.doc, model.type14, model.terreo, (0, 0),
                                          (2, 1), (4, 0)))
    wall = model.doc.get(tx.ops[0].id)
    model.commit(cmd.bend_arc_wall(model.doc, wall, (2, 2)))
    new = _path(model, wall)
    assert geom2d.path_midpoint(new) == pytest.approx((2, 2))
    with pytest.raises(OpError, match="arco"):
        cmd.bend_arc_wall(model.doc, wall, (2, 0))
    with pytest.raises(OpError):
        cmd.offset_wall(model.doc, wall, 1.0)


# --- mover, copiar, girar (§6) ---------------------------------------------------------


def test_ui20_mover_duas_paredes_com_porta(model):
    a = model.wall((0, 0), (5, 0))
    b = model.wall((5, 0), (5, 4))
    c = model.wall((0, 0), (0, 4))
    door = _door(model, a, 1.0)
    assert len(_joins(model)) == 2
    before = _world_xy(door)
    tx = model.commit(transform.move_elements(model.doc, [a.GlobalId, b.GlobalId, door],
                                              (2, 1)))
    assert _path(model, a).start == pytest.approx((2, 1))
    assert _path(model, b).end == pytest.approx((7, 5))
    assert _path(model, c).start == pytest.approx((0, 0))
    assert _world_xy(door) == pytest.approx((before[0] + 2, before[1] + 1))
    assert openings.read_state(fc.opening_of(door))["distance"] == pytest.approx(1.0)
    assert len(_joins(model)) == 1  # a–b continua; a–c se desfez
    assert tx.label == "Mover"


def test_ui21_copiar_parede_com_porta(model):
    wall = model.wall((0, 0), (5, 0))
    door = _door(model, wall, 1.0)
    ids = {e.GlobalId for e in model.doc.ifc.by_type("IfcRoot")}
    for k in (1, 2):
        model.commit(transform.copy_elements(model.doc, [wall.GlobalId], (0, 3 * k)))
    walls = model.doc.ifc.by_type("IfcWall")
    doors = model.doc.ifc.by_type("IfcDoor")
    assert len(walls) == 3 and len(doors) == 3
    assert {ue.get_type(w) for w in walls} == {model.type14}
    assert {ue.get_type(d) for d in doors} == {ue.get_type(door)}
    copies = [w for w in walls if w.GlobalId not in ids]
    assert sorted(_path(model, w).start[1] for w in copies) == pytest.approx([3, 6])
    for d in doors:
        assert d.FillsVoids


def test_ui21_porta_de_outra_origem_nao_copia(tmp_path):
    from test_porta_edicao import _foreign_door_ifc

    path = tmp_path / "outra.ifc"
    gid = _foreign_door_ifc(path)
    doc = Document.open(str(path))
    wall = openings.host(fc.opening_of(doc.get(gid)))
    with pytest.raises(OpError, match="outra origem"):
        transform.copy_elements(doc, [wall.GlobalId], (0, 3))
    with pytest.raises(OpError, match="outra origem"):
        transform.copy_elements(doc, [gid], (0, 0))
    transform.move_elements(doc, [wall.GlobalId], (0, 3))  # mover é aceito


def test_ui22_girar_retangulo(model):
    walls = _rect(model)
    door = _door(model, walls[0], 1.0)
    distance = openings.read_state(fc.opening_of(door))["distance"]
    model.commit(transform.rotate_elements(model.doc, [w.GlobalId for w in walls], (0, 0),
                                           math.pi / 2))
    points = {tuple(round(c, 6) + 0.0 for c in p) for w in walls
              for p in (_path(model, w).start, _path(model, w).end)}
    assert points == {(0, 0), (0, 4), (-3, 4), (-3, 0)}
    assert len(_joins(model)) == 4
    assert openings.read_state(fc.opening_of(door))["distance"] == pytest.approx(distance)
    with pytest.raises(OpError, match="gire a parede"):
        transform.rotate_elements(model.doc, [door.GlobalId], (0, 0), 1.0)


def test_ui23_mover_so_a_porta(model):
    a = model.wall((0, 0), (5, 0))
    b = model.wall((0, 3), (5, 3))
    door = _door(model, a, 1.0)
    model.commit(transform.move_elements(model.doc, [door.GlobalId], (1, 3)))
    o = openings.read_state(fc.opening_of(door))
    assert o["wall"] == b.GlobalId and o["distance"] == pytest.approx(2.0)
    with pytest.raises(OpError, match="parede reta"):
        transform.move_elements(model.doc, [door.GlobalId], (0, 5))
    model.commit(transform.copy_elements(model.doc, [door.GlobalId], (0, -3)))
    assert len(openings.of_wall(a)) == 1 and len(openings.of_wall(b)) == 1


# --- pavimentos e tipos (§7, §8) -------------------------------------------------------


def test_ui24_pavimentos(model):
    wall = model.wall((0, 0), (5, 0))  # topo no Superior (2,80)
    tx = model.commit(cmd.create_storey(model.doc, "Cobertura", 5.6))
    cobertura = model.doc.get(tx.ops[0].id)
    model.commit(cmd.edit_storey(model.doc, model.superior, elevation=3.0))
    assert ue.get_psets(wall)["Qto_WallBaseQuantities"]["Height"] == pytest.approx(3.0)
    with pytest.raises(OpError, match="contém 1"):
        cmd.delete_storey(model.doc, model.terreo)
    tx = model.commit(cmd.delete_storey(model.doc, model.superior))
    state = read_state(model.doc, wall)
    assert state["top_mode"] == "fixed" and state["fixed_height"] == pytest.approx(3.0)
    assert [op.op for op in tx.ops] == ["wall.edit", "storey.delete"]
    model.commit(cmd.delete_storey(model.doc, cobertura))
    with pytest.raises(OpError, match="pelo menos um"):
        cmd.delete_storey(model.doc, model.terreo)
    model.history.undo()
    model.history.undo()
    assert read_state(model.doc, wall)["top_storey"] == model.superior.GlobalId


def test_ui25_tipo_de_parede(model):
    wall = model.wall((0, 0), (5, 0), ref_line="left_face")
    layers = [dict(layer) for layer in LAYERS_14]
    layers[1]["thickness"] = 0.14
    tx = model.commit(cmd.edit_wall_type(model.doc, model.type14, layers=layers,
                                         predefined_type="PARTITIONING"))
    assert len(tx.ops) == 1
    assert model.type14.PredefinedType == "PARTITIONING"
    qto = ue.get_psets(wall)["Qto_WallBaseQuantities"]
    assert qto["Width"] == pytest.approx(0.19)
    assert _path(model, wall).start == pytest.approx((0, 0))
    with pytest.raises(OpError, match="usado por 1"):
        cmd.delete_wall_type(model.doc, model.type14)
    tx = model.commit(cmd.create_wall_type(model.doc, "Outro", LAYERS_14))
    model.commit(cmd.delete_wall_type(model.doc, tx.ops[0].id))
    assert len(model.doc.ifc.by_type("IfcWallType")) == 1


def test_ui26_tipo_de_porta(model):
    wall = model.wall((0, 0), (5, 0))
    p1 = _door_type(model)
    door = _door(model, wall, 1.0, p1)
    model.commit(fc.flip_hinges(model.doc, door))
    variant = ue.get_type(door)
    assert variant != p1
    defaults = {**door_types.read(p1)["defaults"], "width": 0.96}
    model.commit(fc.edit_door_type(model.doc, p1, defaults=defaults))
    assert float(door.OverallWidth) == pytest.approx(0.86)
    lining = {**door_types.read(p1)["lining"], "thickness": 0.05}
    model.commit(fc.edit_door_type(model.doc, p1, lining=lining))
    assert door_types.read(variant)["lining"]["thickness"] == pytest.approx(0.05)


# --- lote (§9) -------------------------------------------------------------------------


def test_ui27_lote_de_paredes(model):
    walls = [model.wall((0, y), (5, y)) for y in (0, 2, 4)]
    tx = model.commit(cmd.create_wall_type(model.doc, "Fina", LAYERS_14[:1]))
    fina = tx.ops[0].id
    model.commit(cmd.edit_wall(model.doc, walls[0], type=fina))
    tx = model.commit(cmd.edit_walls(model.doc, walls, type=model.type14.GlobalId))
    assert [op.op for op in tx.ops] == ["wall.edit"] * 3
    assert tx.label == "Editar 3 paredes"
    tx = model.commit(cmd.edit_walls(model.doc, walls, top_mode="fixed", fixed_height=2.5))
    assert len(tx.ops) == 3
    assert {read_state(model.doc, w)["fixed_height"] for w in walls} == {2.5}


def test_ui27_lote_de_portas_cria_uma_variante(model):
    wall = model.wall((0, 0), (8, 0))
    p1 = _door_type(model)
    d1, d2 = _door(model, wall, 1.0, p1), _door(model, wall, 4.0, p1)
    tx = model.commit(fc.edit_doors(model.doc, [d1, d2], hinges="right"))
    assert [op.op for op in tx.ops].count("door_type.create") == 1
    assert ue.get_type(d1) == ue.get_type(d2) != p1
    tx = model.commit(fc.flip_each(model.doc, [d1, d2], fc.flip_opening))
    assert tx.label == "Inverter sentido de abertura (2 portas)"


# --- seleção por janela (§3.1) ---------------------------------------------------------


def test_ui14_janela_e_cruzamento(model):
    a = model.wall((0, 0), (2, 0))
    b = model.wall((3, 0), (6, 0))
    drawing = plan.storey_plan(model.doc, model.terreo)
    assert drawing.in_rect((-1, -1), (2.5, 1)) == [a.GlobalId]
    assert sorted(drawing.in_rect((-1, -1), (4, 1), crossing=True)) == sorted(
        [a.GlobalId, b.GlobalId])
    assert drawing.in_rect((3.5, -0.01), (4, 0.01), crossing=True) == [b.GlobalId]


# --- UI28: desfazer e reaplicar --------------------------------------------------------


def test_ui28_diario_reproduz_o_ifc():
    m = Model()
    initial_count = len(m.history.undo_stack)
    walls = _rect(m)
    door = _door(m, walls[0], 1.0)
    m.commit(cmd.move_wall_end(m.doc, walls[1], "end", (4.5, 3.5)))
    m.commit(cmd.offset_wall(m.doc, walls[2], 0.3))
    m.commit(transform.copy_elements(m.doc, [w.GlobalId for w in walls], (10, 0)))
    m.commit(transform.rotate_elements(m.doc, [w.GlobalId for w in walls], (0, 0), 0.3))
    along = geom2d.frame(_path(m, walls[0])).vector_to_global((0.5, 0.0))
    m.commit(transform.move_elements(m.doc, [door.GlobalId], along))
    m.commit(cmd.edit_walls(m.doc, walls, fixed_height=2.0, top_mode="fixed"))
    m.commit(cmd.delete_storey(m.doc, m.superior))
    final = snapshot(m.doc.ifc)
    count = len(m.history.undo_stack) - initial_count
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
