# SPDX-License-Identifier: GPL-3.0-or-later
"""Interface 0.2 (``spec/ui/02-edicao.md`` §11): UI14 a UI27 pela janela, com o Qt sem
tela. O núcleo das mesmas ações é testado em ``test_edicao.py``."""

import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import ifcopenshell.util.element as ue
import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit
from test_interface import _click, _field, _move, _ops, _rectangle, _walls

from brasbim.core import geom2d
from brasbim.core.fillings import commands as fc
from brasbim.core.fillings import door_types
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import openings
from brasbim.ui.tools import Mods
from brasbim.ui.types_dialog import DoorTypesDialog, WallTypesDialog


def _path(s, wall):
    return geom2d.path_from_dict(cmd.read_state(s.doc, wall)["path"])


def _wall_from(s, walls, start):
    return next(w for w in walls if _path(s, w).start == pytest.approx(start))


def _joins(s):
    return s.doc.ifc.by_type("IfcRelConnectsPathElements")


def _type_numeric(window, text):
    QTest.keyClicks(window.plan, text[0])
    assert window.plan.numeric.isVisible()
    QTest.keyClicks(window.plan.numeric, text[1:])
    QTest.keyClick(window.plan.numeric, Qt.Key_Return)


def _drag(window, a, b, modifier=Qt.NoModifier, release=None):
    plan = window.plan
    QTest.mousePress(plan, Qt.LeftButton, modifier, plan.to_screen(a).toPoint())
    QTest.mouseMove(plan, plan.to_screen(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)).toPoint())
    QTest.mouseMove(plan, plan.to_screen(b).toPoint())
    QTest.mouseRelease(plan, Qt.LeftButton, modifier if release is None else release,
                       plan.to_screen(b).toPoint())


# --- UI14 --------------------------------------------------------------------------------


def test_ui14_janela_e_cruzamento(window):
    s = window.session
    walls = _rectangle(window)  # (0, 0)–(6, 4)
    window.session.run(lambda: cmd.create_wall(s.doc, walls[0].IsTypedBy[0].RelatingType,
                                               s.storey, (8, 0), (10, 0)))
    single = next(w for w in _walls(s) if w not in walls)
    _drag(window, (7.5, -1), (10.5, 1))  # para a direita: só o que está inteiro
    assert s.selection == {single.GlobalId}
    _drag(window, (9, 1), (5, 2))  # para a esquerda: o que toca
    east = _wall_from(s, walls, (6, 4))
    assert s.selection == {east.GlobalId}
    _drag(window, (10.5, 1), (7.5, -1), Qt.ControlModifier)  # Ctrl soma
    assert s.selection == {east.GlobalId, single.GlobalId}
    window.plan.repaint()


# --- UI15–UI18: alças ----------------------------------------------------------------------


def test_ui15_alca_de_extremidade(window):
    s = window.session
    walls = _rectangle(window)
    north = _wall_from(s, walls, (0, 4))
    s.select([north.GlobalId])
    tool = window.toolbox.active
    assert len(tool.handles()) == 3
    window.plan.repaint()
    _drag(window, (6, 4), (7, 5))
    assert len(_joins(s)) == 4
    assert _path(s, north).end == pytest.approx((7, 5))
    assert _path(s, _wall_from(s, walls, (7, 5))).end == pytest.approx((6, 0))
    tx = s.history.undo_stack[-1]
    assert tx.label == "Mover extremidade de parede"
    window.undo()
    _drag(window, (6, 4), (7, 5), release=Qt.ControlModifier)  # Ctrl ao soltar: só esta
    assert len(_joins(s)) == 3


def test_ui16_alca_presa_ao_cursor_com_numero(window):
    s = window.session
    walls = _rectangle(window)
    north = _wall_from(s, walls, (0, 4))
    s.select([north.GlobalId])
    _click(window, (6, 4))  # clique sem arrastar: a alça segue o cursor
    _move(window, (8, 4))
    _type_numeric(window, "7")
    assert _path(s, north).length == pytest.approx(7)


def test_ui17_alca_do_meio_com_numero(window):
    s = window.session
    walls = _rectangle(window)
    south = _wall_from(s, walls, (6, 0))
    s.select([south.GlobalId])
    _click(window, (3, 0))  # alça do meio
    _move(window, (3, -1))
    _type_numeric(window, "0,5")
    path = _path(s, south)
    assert path.start == pytest.approx((6, -0.5)) and path.length == pytest.approx(6)
    assert sorted(round(_path(s, w).length, 6) for w in walls) == [4.5, 4.5, 6, 6]
    assert len(_joins(s)) == 4


def test_ui18_alca_do_arco(window):
    s = window.session
    tool_type = window.toolbox.tools["wall"].options.type
    s.run(lambda: cmd.create_arc_wall(s.doc, tool_type, s.storey, (0, 0), (2, 1), (4, 0)))
    (arc,) = _walls(s)
    s.select([arc.GlobalId])
    tool = window.toolbox.active
    mid = geom2d.path_midpoint(_path(s, arc))
    tool.press(mid, Mods())
    tool.move((2, 2), Mods(alt=True))
    tool.release((2, 2), Mods(alt=True))
    assert geom2d.path_midpoint(_path(s, arc)) == pytest.approx((2, 2))
    count = len(s.history.undo_stack)
    tool.press((2, 2), Mods())
    tool.move((2, 0), Mods(alt=True))
    assert tool.drag["error"]
    tool.release((2, 0), Mods(alt=True))
    assert len(s.history.undo_stack) == count


# --- UI19: dividir -----------------------------------------------------------------------


def test_ui19_dividir(window):
    s = window.session
    walls = _rectangle(window)
    south = _wall_from(s, walls, (6, 0))
    window.activate_tool("split")
    _click(window, (2, 0.05))
    assert _ops(s.history.undo_stack[-1])[0] == "wall.split"
    _move(window, (5.5, 4))
    _type_numeric(window, "1,2")
    north = _wall_from(s, _walls(s), (0, 4))
    assert _path(s, north).length == pytest.approx(1.2)
    s.run(lambda: fc.create_door(s.doc, s.doc.ifc.by_type("IfcDoorType")[0], south, 1.0))
    count = len(s.history.undo_stack)
    _click(window, (4.5, 0.05))  # sobre a porta (no trecho 6→2, a porta vai de 5 a 4,14)
    assert len(s.history.undo_stack) == count
    assert s.messages[-1]["level"] == "recusa"
    window.plan.repaint()


# --- UI20–UI23: mover, copiar, girar -------------------------------------------------------


def test_ui20_mover_pela_ferramenta(window):
    s = window.session
    walls = _rectangle(window)
    assert not window.tool_actions["move"].isEnabled()
    s.select([w.GlobalId for w in walls])
    assert window.tool_actions["move"].isEnabled()
    window.activate_tool("move")
    _click(window, (0, 0))
    _move(window, (2, 1))
    window.plan.repaint()
    _click(window, (2, 1))
    assert s.history.undo_stack[-1].label == "Mover"
    assert _path(s, walls[0]).start[0] - 2 in (pytest.approx(0), pytest.approx(6))
    assert window.toolbox.active.name == "select"  # volta a Selecionar
    assert len(_joins(s)) == 4


def test_ui20_arrastar_a_selecao(window):
    s = window.session
    walls = _rectangle(window)
    s.select([w.GlobalId for w in walls])
    _drag(window, (1.5, 4.05), (1.5, 6.05))  # fora das alças
    assert s.history.undo_stack[-1].label == "Mover"
    assert {round(_path(s, w).start[1], 6) for w in walls} == {2, 6}


def test_ui21_copiar(window):
    s = window.session
    walls = _rectangle(window)
    s.select([w.GlobalId for w in walls])
    window.activate_tool("copy")
    _click(window, (0, 0))
    _click(window, (10, 0))
    _click(window, (20, 0))
    QTest.keyClick(window.plan, Qt.Key_Escape)
    assert len(_walls(s)) == 12
    assert [tx.label for tx in s.history.undo_stack[-2:]] == ["Copiar", "Copiar"]


def test_ui22_girar_com_angulo(window):
    s = window.session
    walls = _rectangle(window)
    s.select([w.GlobalId for w in walls])
    window.activate_tool("rotate")
    _click(window, (0, 0))
    _type_numeric(window, "90")
    points = {tuple(round(c, 6) + 0.0 for c in p) for w in walls
              for p in (_path(s, w).start, _path(s, w).end)}
    assert points == {(0, 0), (0, 6), (-4, 6), (-4, 0)}
    assert window.toolbox.active.name == "select"


def test_ui22_girar_por_tres_pontos(window):
    s = window.session
    walls = _rectangle(window)
    s.select([w.GlobalId for w in walls])
    tool = window.toolbox.activate("rotate")
    tool.press((0, 0), Mods())
    tool.press((1, 0), Mods())
    tool.move((1, 0.9), Mods(shift=True))  # Shift: múltiplos de 15° → 45°
    assert tool.labels()[0][1] == "45,0°"
    tool.press((1, 0.9), Mods(shift=True))
    north = _wall_from(s, walls, (0, 0))  # o lado oeste começa no centro do giro
    assert math.degrees(_path(s, north).start_angle) == pytest.approx(135)


# --- UI24: pavimentos --------------------------------------------------------------------


def test_ui24_painel_de_pavimentos(window):
    s = window.session
    panel = window.project
    assert panel.table.rowCount() == 2
    panel.add_storey()
    assert s.storey.Name == "Pavimento 3" and s.storey.Elevation == pytest.approx(5.6)
    assert panel.table.item(0, 0).text() == "● Pavimento 3"
    panel.table.item(0, 1).setText("6,00")  # editar a cota
    assert s.storey.Elevation == pytest.approx(6.0)
    panel.table.item(0, 0).setText("Cobertura")
    assert s.storey.Name == "Cobertura"
    panel._activate(2)
    assert s.storey.Name == "Térreo"
    panel.table.selectRow(0)
    panel.delete_storey()
    assert [st.Name for st in s.doc.storeys()] == ["Térreo", "Superior"]
    _rectangle(window)
    panel.table.selectRow(1)  # Térreo, com paredes: recusado
    panel.delete_storey()
    assert s.messages[-1]["level"] == "recusa" and "contém 4" in s.messages[-1]["text"]


# --- UI25–UI26: tipos ----------------------------------------------------------------------


def test_ui25_tipos_de_parede(window):
    s = window.session
    walls = _rectangle(window)
    dialog = WallTypesDialog(s, window)
    assert dialog.list.count() == 2
    used = ue.get_type(walls[0])
    assert dialog.current == used.GlobalId  # "Alvenaria 14" é o primeiro
    dialog.layers.item(1, 1).setText("0,14")
    assert dialog.dirty and dialog.total.text() == "0,19 m"
    count = len(s.history.undo_stack)
    assert dialog.apply()
    assert len(s.history.undo_stack) == count + 1
    assert _ops(s.history.undo_stack[-1]) == ["wall_type.edit"]
    assert ue.get_pset(walls[0], "Qto_WallBaseQuantities")["Width"] == pytest.approx(0.19)
    dialog.delete()
    assert "usado por 4" in s.messages[-1]["text"]
    dialog.duplicate()
    assert dialog.list.count() == 3 and "Alvenaria 14 (cópia)" in [
        t.Name for t in s.doc.ifc.by_type("IfcWallType")]
    dialog.delete()
    assert dialog.list.count() == 2
    dialog.dirty = False
    dialog.close()


def test_ui26_tipos_de_porta(window):
    s = window.session
    walls = _rectangle(window)
    south = _wall_from(s, walls, (6, 0))
    p1 = next(t for t in s.doc.ifc.by_type("IfcDoorType") if t.Name.startswith("P1"))
    tx = fc.create_door(s.doc, p1, south, 1.0, hinges="right")
    s.run(tx)
    door = s.doc.get(next(op.id for op in tx.ops if op.op == "door.create"))
    variant = ue.get_type(door)
    assert variant != p1
    dialog = DoorTypesDialog(s, window)
    names = [dialog.list.item(i).text() for i in range(dialog.list.count())]
    assert len(names) == 3 and "P1 – giro 80  (1)" in names  # a variante não aparece
    dialog.list.setCurrentRow(names.index("P1 – giro 80  (1)"))
    assert dialog.current == p1.GlobalId
    dialog.width.setText("0,96")
    dialog.lining_thickness.setText("0,05")
    dialog.touched()
    assert dialog.apply()
    assert door_types.read(variant)["lining"]["thickness"] == pytest.approx(0.05)
    assert door_types.read(p1)["defaults"]["width"] == pytest.approx(0.96)
    assert float(door.OverallWidth) == pytest.approx(0.86)  # portas existentes não mudam
    dialog.close()


# --- UI27: lote ----------------------------------------------------------------------------


def test_ui27_edicao_em_lote(window):
    s = window.session
    walls = _rectangle(window)
    drywall = next(t for t in s.doc.ifc.by_type("IfcWallType") if t.Name.startswith("Drywall"))
    s.run(lambda: cmd.edit_wall(s.doc, walls[0], type=drywall))
    s.select([w.GlobalId for w in walls[:3]])
    combo = _field(window, "Tipo", QComboBox)
    assert combo.currentText() == "(vários)"
    assert _field(window, "Base", QLineEdit).text() == "0,00"  # igual nas três
    combo.setCurrentIndex(combo.findText("Alvenaria 14"))
    tx = s.history.undo_stack[-1]
    assert _ops(tx) == ["wall.edit"] * 3 and tx.label == "Editar 3 paredes"
    top = _field(window, "Topo", QComboBox)
    top.setCurrentIndex(top.findData("fixed"))
    assert {cmd.read_state(s.doc, w)["top_mode"] for w in walls[:3]} == {"fixed"}
    height = _field(window, "Altura", QLineEdit)
    height.setText("2,50")
    height.editingFinished.emit()
    assert {cmd.read_state(s.doc, w)["fixed_height"] for w in walls[:3]} == {2.5}


def test_ui27_lote_de_portas(window):
    s = window.session
    walls = _rectangle(window)
    south = _wall_from(s, walls, (6, 0))
    p1 = next(t for t in s.doc.ifc.by_type("IfcDoorType") if t.Name.startswith("P1"))
    ids = []
    for d in (1.0, 4.0):
        tx = fc.create_door(s.doc, p1, south, d)
        s.run(tx)
        ids.append(next(op.id for op in tx.ops if op.op == "door.create"))
    s.select(ids)
    width = _field(window, "Largura", QLineEdit)
    width.setText("0,90")
    width.editingFinished.emit()
    assert [openings.read_state(fc.opening_of(s.doc.get(g)))["width"] for g in ids] == [
        pytest.approx(0.9)] * 2
    QApplication.processEvents()
    hinges = _field(window, "Dobradiças", QComboBox)
    hinges.setCurrentIndex(hinges.findData("right"))
    tx = s.history.undo_stack[-1]
    assert _ops(tx).count("door_type.create") == 1
