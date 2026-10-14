# SPDX-License-Identifier: GPL-3.0-or-later
"""Acabamento de parede e porta (``spec/ui/05-acabamento-parede-porta.md`` §9): UI41 a
UI50, no núcleo e pela janela."""

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import ifcopenshell.util.element as ue
import pytest
from conftest import PROJECT_ID, Model, snapshot

from brasbim.core import geom2d, plan, transform
from brasbim.core.document import Document, OpError
from brasbim.core.fillings import commands as fc
from brasbim.core.fillings import params
from brasbim.core.ops import History, Transaction
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import openings
from brasbim.core.walls.wall import read_state


def _rect(m, a=(0, 0), b=(4, 3)):
    tx = m.commit(cmd.create_rectangle(m.doc, m.type14, m.terreo, a, b))
    return [m.doc.get(op.id) for op in tx.ops if op.op == "wall.create"]


def _path(m, wall):
    return geom2d.path_from_dict(read_state(m.doc, wall)["path"])


def _joins(doc):
    return doc.ifc.by_type("IfcRelConnectsPathElements")


def _door(m, wall, distance=1.0):
    t = m.commit(fc.create_door_type(m.doc, "P1"))
    tx = m.commit(fc.create_door(m.doc, t.ops[0].id, wall, distance, opens_to="left"))
    return m.doc.get(next(op.id for op in tx.ops if op.op == "door.create"))


def _hand(door):
    return params.hand_of(ue.get_type(door).OperationType)


# --- UI41–UI42: espelhar ----------------------------------------------------------------


def test_ui41_espelhar(model):
    walls = _rect(model)
    south = next(w for w in walls if _path(model, w).start == pytest.approx((4, 0)))
    door = _door(model, south, 1.0)  # vão de x = 3 a 2,14 (a parede vai de 4 a 0)
    initial = snapshot(model.doc.ifc)
    hand = _hand(door)
    tx = model.commit(transform.mirror_elements(model.doc, [w.GlobalId for w in walls],
                                                (10, 0), (10, 1)))
    assert tx.label == "Espelhar"
    path = _path(model, south)
    assert path.start == pytest.approx((20, 0)) and path.end == pytest.approx((16, 0))
    assert len(_joins(model.doc)) == 4
    o = openings.read_state(fc.opening_of(door))
    assert o["distance"] == pytest.approx(4 - 1.0 - 0.86)
    # porta na posição espelhada: o vão ia de x 3 a 2,14; agora de 17 a 17,86
    x0 = path.start[0] - o["distance"] - o["width"]
    assert x0 == pytest.approx(16 + 1.0)
    assert _hand(door) != hand
    model.history.undo()
    assert snapshot(model.doc.ifc) == initial

    tx = model.commit(transform.mirror_elements(model.doc, [w.GlobalId for w in walls],
                                                (10, 0), (10, 1), keep=True))
    assert tx.label == "Espelhar cópia"
    assert len(model.doc.ifc.by_type("IfcWall")) == 8
    assert len(model.doc.ifc.by_type("IfcDoor")) == 2
    copies = [d for d in model.doc.ifc.by_type("IfcDoor") if d != door]
    assert _hand(copies[0]) != _hand(door)


def test_ui42_espelhar_recusas(model, tmp_path):
    wall = model.wall()
    door = _door(model, wall)
    with pytest.raises(OpError, match="espelhe a parede"):
        transform.mirror_elements(model.doc, [door.GlobalId], (0, 5), (1, 5))
    from test_porta_edicao import _foreign_door_ifc

    src = tmp_path / "outro.ifc"
    gid = _foreign_door_ifc(src)
    doc = Document.open(str(src))
    host = openings.host(fc.opening_of(doc.get(gid)))
    with pytest.raises(OpError, match="outra origem"):
        transform.mirror_elements(doc, [host.GlobalId], (0, 5), (1, 5))


# --- UI43: comprimento e ângulo -----------------------------------------------------------


def test_ui43_comprimento_e_angulo_no_painel(window):
    from test_interface import _field, _rectangle

    s = window.session
    walls = _rectangle(window)
    south = next(w for w in walls
                 if cmd.read_state(s.doc, w)["path"]["start"] == [6.0, 0.0])
    s.select([south.GlobalId])
    field = _field(window, "Comprimento")
    assert field.text() == "6,00"
    field.setText("5,00")
    field.editingFinished.emit()
    path = geom2d.path_from_dict(cmd.read_state(s.doc, south)["path"])
    assert path.end == pytest.approx((1, 0))
    west = next(w for w in walls if w != south and geom2d.path_from_dict(
        cmd.read_state(s.doc, w)["path"]).start == pytest.approx((1, 0)))
    assert west is not None  # a vizinha em L acompanhou
    s.run(lambda: cmd.create_wall(s.doc, ue.get_type(south), s.storey, (10, 0), (14, 0)))
    single = next(w for w in s.doc.ifc.by_type("IfcWall") if w not in walls)
    s.select([single.GlobalId])
    angle = _field(window, "Ângulo (°)")
    assert angle.text() == "0,00"
    angle.setText("90")
    angle.editingFinished.emit()
    path = geom2d.path_from_dict(cmd.read_state(s.doc, single)["path"])
    assert path.end == pytest.approx((10, 4))


# --- UI44: alças da porta -------------------------------------------------------------------


def test_ui44_alcas_da_porta(window):
    from test_interface import _rectangle

    from brasbim.ui.tools import Mods

    s = window.session
    walls = _rectangle(window)
    south = next(w for w in walls
                 if cmd.read_state(s.doc, w)["path"]["start"] == [6.0, 0.0])
    tx = fc.create_door(s.doc, s.doc.ifc.by_type("IfcDoorType")[0], south, 2.0)
    s.run(tx)
    door = s.doc.get(next(op.id for op in tx.ops if op.op == "door.create"))
    s.select([door.GlobalId])
    tool = window.toolbox.active
    assert len(tool.handles()) == 2
    # a parede vai de x 6 a 0: o vão vai de x 4 a 3,14; "door_end" fica em x 3,14
    y = -0.07
    tool.press((3.14, y), Mods())
    tool.move((3.0, y), Mods(alt=True))
    tool.release((3.0, y), Mods(alt=True))
    o = openings.read_state(fc.opening_of(door))
    assert o["width"] == pytest.approx(1.0) and o["distance"] == pytest.approx(2.0)
    tool.press((3.0, y), Mods())
    tool.release((3.0, y), Mods())  # clique: a alça segue o cursor
    assert tool.numeric(0.9)
    o = openings.read_state(fc.opening_of(door))
    assert o["width"] == pytest.approx(0.9) and o["distance"] == pytest.approx(2.0)
    count = len(s.history.undo_stack)
    tool.press((3.1, y), Mods())
    tool.move((-1.0, y), Mods(alt=True))  # passa do fim da parede
    assert tool.drag["error"]
    tool.release((-1.0, y), Mods(alt=True))
    assert len(s.history.undo_stack) == count
    window.plan.repaint()


# --- UI45: etiqueta ---------------------------------------------------------------------------


def test_ui45_etiqueta_da_porta(model):
    wall = model.wall((0, 0), (5, 0), ref_line="axis")
    door = _door(model, wall, 1.0)  # abre para a esquerda (+y)
    (label,) = plan.storey_plan(model.doc, model.terreo).labels
    assert label.owner == door.GlobalId and label.code == "P1"
    assert label.size == "0,86 × 2,13"
    assert label.at[1] < -0.07  # do lado oposto ao da folha, fora da parede
    assert label.at[0] == pytest.approx(1.43)


def test_ui45_etiqueta_na_janela(window):
    from test_interface import _rectangle

    s = window.session
    walls = _rectangle(window)
    s.run(fc.create_door(s.doc, s.doc.ifc.by_type("IfcDoorType")[0], walls[0], 1.0))
    window.plan.repaint()
    assert window.plan.show_tags and not window.plan.show_tag_size
    window.tag_size_action.trigger()
    assert window.plan.show_tag_size
    window.tags_action.trigger()
    assert not window.plan.show_tags
    window.plan.repaint()
    window.tags_action.trigger()
    window.tag_size_action.trigger()


# --- UI46: propriedades comuns ----------------------------------------------------------------


def test_ui46_propriedades_comuns(window):
    from PySide6.QtWidgets import QComboBox
    from test_interface import _field, _rectangle

    s = window.session
    walls = _rectangle(window)
    s.select([walls[0].GlobalId])
    external = _field(window, "Externa", QComboBox)
    external.setCurrentIndex(external.findData(True))
    fire = _field(window, "Resistência ao fogo")
    fire.setText("EI 60")
    fire.editingFinished.emit()
    pset = ue.get_pset(walls[0], "Pset_WallCommon")
    assert pset["IsExternal"] is True and pset["FireRating"] == "EI 60"
    external = _field(window, "Externa", QComboBox)
    external.setCurrentIndex(external.findData(False))  # volta ao padrão
    assert "IsExternal" not in cmd.read_state(s.doc, walls[0])["common"]

    s.select([w.GlobalId for w in walls[:3]])
    status = _field(window, "Situação", QComboBox)
    status.setCurrentIndex(status.findData("EXISTING"))
    tx = s.history.undo_stack[-1]
    assert [op.op for op in tx.ops] == ["wall.edit"] * 3
    assert {cmd.read_state(s.doc, w)["common"]["Status"] for w in walls[:3]} == {"EXISTING"}

    tx = fc.create_door(s.doc, s.doc.ifc.by_type("IfcDoorType")[0], walls[0], 1.0)
    s.run(tx)
    door = s.doc.get(next(op.id for op in tx.ops if op.op == "door.create"))
    s.select([door.GlobalId])
    accessible = _field(window, "Acessível", QComboBox)
    accessible.setCurrentIndex(accessible.findData(True))
    assert ue.get_pset(door, "Pset_DoorCommon")["HandicapAccessible"] is True


# --- UI47–UI49: junções manuais ---------------------------------------------------------------


def test_ui47_unir(model):
    a = model.wall((0, 0), (4, 0))
    b = model.wall((5, 1), (5, 4))
    assert not _joins(model.doc)
    model.commit(cmd.join_walls(model.doc, a, b))
    assert _path(model, a).end == pytest.approx((5, 0))
    assert _path(model, b).start == pytest.approx((5, 0))
    assert len(_joins(model.doc)) == 1
    c = model.wall((2, 3), (2, 1))  # termina antes da parede a: vira T
    model.commit(cmd.join_walls(model.doc, a, c))
    assert _path(model, c).end == pytest.approx((2, 0))
    assert _path(model, a).start == pytest.approx((0, 0))
    rel = next(r for r in _joins(model.doc) if c in (r.RelatingElement, r.RelatedElement))
    assert "ATPATH" in (rel.RelatingConnectionType, rel.RelatedConnectionType)
    with pytest.raises(OpError, match="já estão unidas"):
        cmd.join_walls(model.doc, a, b)
    d = model.wall((0, 2), (1, 2))
    with pytest.raises(OpError, match="paralelas"):
        cmd.join_walls(model.doc, a, d)


def test_ui48_desfazer_juncao(model):
    a = model.wall((0, 0), (4, 0))
    b = model.wall((4, 0), (4, 3))
    tx = model.commit(cmd.unjoin_walls(model.doc, a, b))
    assert not _joins(model.doc)
    assert ue.get_pset(a, "BrasBim_Parede")["SemJuncaoCom"] == b.GlobalId
    assert read_state(model.doc, b)["no_join"] == [a.GlobalId]
    assert [op.op for op in tx.ops] == ["path_connection.delete", "wall.edit", "wall.edit"]
    model.commit(cmd.edit_wall(model.doc, b, fixed_height=2.5, top_mode="fixed"))
    model.commit(transform.move_elements(model.doc, [b.GlobalId], (0, 0.5)))
    model.commit(transform.move_elements(model.doc, [b.GlobalId], (0, -0.5)))
    assert not _joins(model.doc)  # a junção não volta sozinha
    model.commit(cmd.join_walls(model.doc, a, b))
    assert len(_joins(model.doc)) == 1
    assert read_state(model.doc, a)["no_join"] == []
    assert "SemJuncaoCom" not in ue.get_pset(a, "BrasBim_Parede")


def test_ui49_trocar_a_continua(model):
    a = model.wall((0, 2), (6, 2))
    b = model.wall((3, 0), (3, 5))
    (rel,) = _joins(model.doc)
    first = rel.RelatingElement
    with pytest.raises(OpError, match="cruzam"):
        cmd.swap_continuous(model.doc, a, model.wall((6, 2), (6, 6)))
    model.commit(cmd.swap_continuous(model.doc, a, b))
    (rel,) = [r for r in _joins(model.doc)
              if {r.RelatingElement, r.RelatedElement} == {a, b}]
    assert rel.RelatingElement != first
    model.commit(cmd.edit_wall(model.doc, a, base_offset=0.1))
    (rel,) = [r for r in _joins(model.doc)
              if {r.RelatingElement, r.RelatedElement} == {a, b}]
    assert rel.RelatingElement != first  # a escolha se mantém
    order = [s.owner for s in plan.storey_plan(model.doc, model.terreo).shapes
             if s.role == "wall" and s.owner in (a.GlobalId, b.GlobalId)]
    assert order[-1] == rel.RelatingElement.GlobalId  # a contínua por cima


# --- UI50: diário ------------------------------------------------------------------------------


def test_ui50_diario_reproduz_o_ifc():
    m = Model()
    start = len(m.history.undo_stack)
    walls = _rect(m)
    south = next(w for w in walls if _path(m, w).start == pytest.approx((4, 0)))
    _door(m, south, 1.0)
    gids = [w.GlobalId for w in walls]
    m.commit(transform.mirror_elements(m.doc, gids, (10, 0), (10, 1)))
    m.commit(transform.mirror_elements(m.doc, gids, (0, 10), (1, 10), keep=True))
    a = m.wall((30, 0), (34, 0))
    b = m.wall((35, 1), (35, 4))
    m.commit(cmd.join_walls(m.doc, a, b))
    m.commit(cmd.unjoin_walls(m.doc, a, b))
    c = m.wall((32, -2), (32, 2))
    m.commit(cmd.swap_continuous(m.doc, a, c))
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
