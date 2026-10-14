# SPDX-License-Identifier: LGPL-3.0-or-later
"""Núcleo da interface (``spec/ui/01-janela-e-ferramentas.md`` §3, §3.2, §10): planta,
atração a pontos e avisos de alteração do histórico."""

import math

import pytest

from brasbim.core import geom2d, plan, snap
from brasbim.core.fillings import commands as fc
from brasbim.core.walls import commands as cmd


def _door(model, wall, distance=1.0, operation="SINGLE_SWING_LEFT", **options):
    tx = model.commit(fc.create_door_type(model.doc, f"T{operation}", operation))
    door_type = model.doc.get(tx.ops[0].id)
    tx = model.commit(fc.create_door(model.doc, door_type, wall, distance, **options))
    return model.doc.get(next(op.id for op in tx.ops if op.op == "door.create"))


def test_planta_corta_a_parede_no_vao(model):
    wall = model.wall((0, 0), (5, 0))
    door = _door(model, wall)
    drawing = plan.storey_plan(model.doc, model.terreo)
    pieces = [s for s in drawing.shapes if s.role == "wall"]
    assert len(pieces) == 2
    spans = sorted((min(p[0] for p in s.points), max(p[0] for p in s.points)) for s in pieces)
    assert spans == [pytest.approx((0, 1.0)), pytest.approx((1.86, 5))]
    total = sum(geom2d.polygon_area(s.points) for s in pieces)
    assert total == pytest.approx((5 - 0.86) * 0.14)
    roles = {s.role for s in drawing.shapes if s.owner == door.GlobalId}
    assert roles == {"door_frame", "door_leaf", "door_swing"}


@pytest.mark.parametrize("opens_to,side", [("left", 1), ("right", -1)])
def test_folha_abre_para_o_lado_escolhido(model, opens_to, side):
    wall = model.wall((0, 0), (5, 0), ref_line="axis")
    door = _door(model, wall, opens_to=opens_to)
    drawing = plan.storey_plan(model.doc, model.terreo)
    (leaf,) = [s for s in drawing.shapes if s.owner == door.GlobalId and s.role == "door_leaf"]
    ys = [p[1] * side for p in leaf.points]
    assert max(ys) == pytest.approx(0.07 + 0.80)  # face da parede + folha a 90°


def test_dobradicas_mudam_o_lado_da_folha(model):
    wall = model.wall((0, 0), (5, 0), ref_line="axis")
    door = _door(model, wall)

    def leaf_x():
        drawing = plan.storey_plan(model.doc, model.terreo)
        (leaf,) = [s for s in drawing.shapes if s.owner == door.GlobalId and s.role == "door_leaf"]
        return min(p[0] for p in leaf.points)

    assert leaf_x() == pytest.approx(1.03)  # dobradiças à esquerda: junto ao marco inicial
    model.commit(fc.flip_hinges(model.doc, door))
    assert leaf_x() == pytest.approx(1.86 - 0.03 - 0.035)


def test_simbolos_das_outras_operacoes():
    lining = {"thickness": 0.03}

    def roles(op, panels):
        return [r for r, _, _ in plan.door_symbol(1.2, 0.14, op, lining, panels)]

    slide = [{"operation": "SLIDING", "position": p, "width": 0.5, "depth": 0.035}
             for p in ("LEFT", "RIGHT")]
    assert roles("DOUBLE_DOOR_SLIDING", slide).count("door_arrow") == 4
    act = [{"operation": "DOUBLE_ACTING", "position": "MIDDLE", "width": 1.0, "depth": 0.035}]
    assert roles("DOUBLE_SWING_LEFT", act).count("door_swing") == 2
    assert roles("NOTDEFINED", []) == ["door_frame", "door_frame"]


def test_pavimento_de_baixo_e_selecao(model):
    a = model.wall((0, 0), (5, 0))
    tx = model.commit(cmd.create_wall(model.doc, model.type14, model.superior, (0, 2), (5, 2)))
    b = model.doc.get(tx.ops[0].id)
    door = _door(model, a)
    above = plan.storey_plan(model.doc, model.superior)
    assert {s.owner for s in above.shapes if s.role == "below"} == {a.GlobalId}
    assert {s.owner for s in above.shapes if s.role == "wall"} == {b.GlobalId}

    below = plan.storey_plan(model.doc, model.terreo)
    assert below.pick((3.0, -0.07), 0.05) == a.GlobalId
    assert below.pick((1.4, 0.3), 0.05) == door.GlobalId  # porta antes da parede
    assert below.pick((3.0, 1.0), 0.05) is None
    assert below.bounds() == pytest.approx((0, -0.14, 5, 0.80))  # folha aberta: 0,80


def test_snap_por_prioridade(model):
    model.wall((0, 0), (5, 0))
    walls = snap.wall_paths(model.doc, model.terreo)
    assert snap.snap(walls, (4.97, 0.02), 0.05) == snap.Snap((5, 0), "end", walls[0].gid)
    assert snap.snap(walls, (2.52, 0.01), 0.05).kind == "mid"
    s = snap.snap(walls, (3.33, 0.02), 0.05)
    assert (s.kind, s.point) == ("path", pytest.approx((3.33, 0)))
    s = snap.snap(walls, (3.33, 1.04), 0.05)
    assert (s.kind, s.point) == ("grid", pytest.approx((3.3, 1.0)))
    s = snap.snap(walls, (7.01, 1.0), 0.05, extra=[(7, 1)])
    assert (s.kind, s.point) == ("end", (7, 1))
    assert snap.snap(walls, (3.33, 1.04), 0.05, grid=None).kind == "free"


def test_parede_sob_o_cursor(model):
    model.wall((0, 0), (5, 0))  # faixa y de -0,14 a 0
    tx = model.commit(cmd.create_arc_wall(model.doc, model.type14, model.terreo,
                                          (10, 0), (12, 2), (14, 0), ref_line="axis"))
    walls = snap.wall_paths(model.doc, model.terreo)
    hit = snap.wall_at(walls, (2.0, -0.02), 0.01)
    assert (hit.along, hit.left) == (pytest.approx(2.0), True)
    assert snap.wall_at(walls, (2.0, -0.12), 0.01).left is False
    assert snap.wall_at(walls, (2.0, 0.5), 0.01) is None
    assert snap.wall_at(walls, (6.0, -0.07), 0.01) is None
    arc = snap.wall_at(walls, (12, 2.0), 0.01)
    assert arc.wall.gid == tx.ops[0].id and not arc.wall.straight
    assert arc.along == pytest.approx(math.pi)


def test_ortogonal():
    assert snap.constrain((0, 0), (3, 0.4)) == pytest.approx((math.hypot(3, 0.4), 0))
    p = snap.constrain((1, 1), (3, 3.2))
    assert p[0] - 1 == pytest.approx(p[1] - 1)


def test_historico_avisa_o_que_mudou(model):
    events = []
    model.history.listeners.append(lambda kind, tx, changed: events.append((kind, changed)))
    a = model.wall((0, 0), (5, 0))
    b = model.wall((5, 0), (5, 4))  # junção L: a parede a também é recalculada
    kind, changed = events[-1]
    assert kind == "commit" and {a.GlobalId, b.GlobalId} <= changed
    door = _door(model, a)
    model.commit(fc.edit_door(model.doc, door, distance=2.0))
    assert door.GlobalId in events[-1][1]
    model.history.undo()
    assert events[-1][0] == "undo" and door.GlobalId in events[-1][1]
    model.history.redo()
    assert events[-1][0] == "redo"
