# SPDX-License-Identifier: GPL-3.0-or-later
"""Barras, ícones, mini-barra da seleção e representação da parede
(``spec/ui/03-barras-e-icones.md`` §8): UI29 a UI36."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

import ifcopenshell.util.element as ue
from conftest import LAYERS_14, Model
from PySide6.QtCore import QRect, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QToolBar, QToolButton
from test_interface import _click, _move, _rectangle, _walls

from brasbim.core import plan
from brasbim.core.document import Document
from brasbim.core.fillings import commands as fc
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import types as wall_types
from brasbim.ui import icons
from brasbim.ui.tools import Mods, bar_position
from brasbim.ui.types_dialog import WallTypesDialog


def _ops(tx):
    return [op.op for op in tx.ops]


def _alvenaria(s):
    return next(t for t in s.doc.ifc.by_type("IfcWallType") if t.Name == "Alvenaria 14")


# --- UI29–UI30: barras e ícones -------------------------------------------------------


def test_ui29_barras_moveis_e_lembradas(window):
    bars = {b.objectName(): b for b in window.findChildren(QToolBar)}
    assert {"barra_ferramentas", "barra_historico", "barra_opcoes"} <= bars.keys()
    tools = bars["barra_ferramentas"]
    assert window.toolBarArea(tools) == Qt.LeftToolBarArea
    for bar in bars.values():
        assert bar.allowedAreas() == Qt.AllToolBarAreas and bar.isMovable()
        assert bar.isFloatable()
    window.removeToolBar(tools)
    window.addToolBar(Qt.BottomToolBarArea, tools)
    tools.show()
    state = window.saveState(3)
    window.reset_bars()
    assert window.toolBarArea(tools) == Qt.LeftToolBarArea
    assert window.restoreState(state, 3)
    assert window.toolBarArea(tools) == Qt.BottomToolBarArea
    window.reset_bars()


def test_ui30_icones_sem_texto_e_com_dica(window):
    window.activate_tool("wall")
    QApplication.processEvents()
    for bar in (window.tools_bar, window.history_bar, window.options_bar):
        buttons = [(a, bar.widgetForAction(a)) for a in bar.actions()
                   if isinstance(bar.widgetForAction(a), QToolButton)]  # sem campos e listas
        assert buttons
        for action, button in buttons:
            assert not action.icon().isNull(), action.text()
            assert action.toolTip().startswith(action.text())
            assert button.toolButtonStyle() == Qt.ToolButtonIconOnly
    assert set(icons.names()) >= {"select", "wall", "door", "move", "copy", "rotate", "split",
                                  "delete", "undo", "redo"}


# --- UI31–UI32: barra de opções -------------------------------------------------------


def test_ui31_barra_de_opcoes_da_parede(window):
    s = window.session
    assert not window.options_bar.isVisible()
    window.tool_actions["wall"].trigger()
    assert window.toolbox.active.name == "wall" and window.options_bar.isVisible()
    forms = {a.data(): a for a in window.options_bar.actions() if a.data() in
             ("wall", "arc", "rectangle")}
    forms["arc"].trigger()
    assert window.toolbox.active.name == "arc"
    for p in [(0, 0), (2, 1), (4, 0)]:
        _click(window, p)
    (wall,) = _walls(s)
    assert cmd.read_state(s.doc, wall)["path"]["kind"] == "arc"
    window.tool_actions["select"].trigger()
    assert not window.options_bar.isVisible()
    window.tool_actions["wall"].trigger()  # lembra a última forma
    assert window.toolbox.active.name == "arc"


def test_ui32_tipo_e_linha_de_referencia_pela_barra(window):
    s = window.session
    window.activate_tool("wall")
    bar = window.options_bar
    drywall = next(t for t in s.doc.ifc.by_type("IfcWallType") if t.Name.startswith("Drywall"))
    bar.type_combo.setCurrentIndex(bar.type_combo.findData(drywall.GlobalId))
    next(a for a in bar.actions() if a.data() == "axis").trigger()
    _click(window, (0, 0))
    _click(window, (3, 0))
    QTest.keyClick(window.plan, Qt.Key_Return)
    (wall,) = _walls(s)
    state = cmd.read_state(s.doc, wall)
    assert state["type"] == drywall.GlobalId and state["ref_line"] == "axis"


# --- UI33–UI34: mini-barra --------------------------------------------------------------


def test_ui33_mini_barra(window):
    s = window.session
    walls = _rectangle(window)
    bar = window.selection_bar
    window.plan.repaint()
    assert bar.isHidden()
    south = next(w for w in walls if cmd.read_state(s.doc, w)["path"]["start"] == [6.0, 0.0])
    s.select([south.GlobalId])
    window.plan.repaint()
    assert not bar.isHidden()
    assert bar.visible_actions() == ["move", "copy", "rotate", "mirror", "split",
                                     "auto_dimension", "select_similar", "situation",
                                     "delete"]  # Cotar: spec/ui 13 §4.5; spec/ui 23 §7
    view = window.plan.rect()
    assert view.contains(QRect(bar.pos(), bar.size()))
    _, y0, _, y1 = window.plan.selection_rect()
    assert bar.y() + bar.height() <= y0 or bar.y() >= y1  # não cobre a parede
    tx = fc.create_door(s.doc, s.doc.ifc.by_type("IfcDoorType")[0], south, 1.0)
    s.run(tx)
    door = next(op.id for op in tx.ops if op.op == "door.create")
    s.select([door])
    window.plan.repaint()
    assert bar.visible_actions() == ["move", "copy", "flip_opening", "flip_hinges",
                                     "select_similar", "situation", "delete"]
    tool = window.toolbox.active  # durante um arrasto, a mini-barra some
    tool.press((3, 0.2), Mods())
    window.plan.repaint()
    assert bar.isHidden()
    tool.cancel()
    window.plan.repaint()
    assert not bar.isHidden()
    QTest.keyClick(window.plan, Qt.Key_Escape)  # Esc limpa a seleção
    window.plan.repaint()
    assert not s.selection and bar.isHidden()


def test_ui33_posicao_da_mini_barra():
    assert bar_position((100, 200, 300, 260), (120, 30), (800, 600)) == (180, 158)
    assert bar_position((100, 10, 300, 60), (120, 30), (800, 600)) == (180, 72)
    assert bar_position((-50, 10, 60, 600), (120, 30), (800, 600)) == (0, 570)


def test_ui34_acoes_da_mini_barra(window):
    s = window.session
    walls = _rectangle(window)
    south = next(w for w in walls if cmd.read_state(s.doc, w)["path"]["start"] == [6.0, 0.0])
    north = next(w for w in walls if cmd.read_state(s.doc, w)["path"]["start"] == [0.0, 4.0])
    s.select([south.GlobalId])
    window.plan.repaint()
    window.selection_bar.buttons["split"].click()
    assert window.toolbox.active.name == "split"
    count = len(s.history.undo_stack)
    _click(window, (3, 4.05))  # outra parede: ignorada
    assert len(s.history.undo_stack) == count
    _click(window, (2, 0.05))
    assert _ops(s.history.undo_stack[-1])[0] == "wall.split"
    assert s.history.undo_stack[-1].ops[0].id == south.GlobalId
    assert window.toolbox.active.name == "select"
    assert north.GlobalId not in {op.id for op in s.history.undo_stack[-1].ops
                                  if op.op == "wall.split"}
    s.select([w.GlobalId for w in walls])
    window.plan.repaint()
    window.selection_bar.buttons["move"].click()
    assert window.toolbox.active.name == "move"
    _click(window, (0, 0))
    _move(window, (1, 0))
    _click(window, (1, 0))
    assert s.history.undo_stack[-1].label == "Mover"
    assert window.toolbox.active.name == "select"


# --- UI35–UI36: representação da parede ----------------------------------------------------


def test_ui35_representacao_no_tipo(window, tmp_path):
    s = window.session
    walls = _rectangle(window)
    alvenaria = _alvenaria(s)
    shape = next(sh for sh in plan.storey_plan(s.doc, s.storey).shapes if sh.role == "wall")
    assert shape.style["fill"] == "solid"
    dialog = WallTypesDialog(s, window, select=alvenaria.GlobalId)
    dialog.fill.setCurrentIndex(dialog.fill.findData("hatch"))
    dialog.set_color(dialog.fill_color, "#336699")
    dialog.line_weight.setCurrentIndex(dialog.line_weight.findData(0.00035))
    assert dialog.sample.pixmap() is not None
    assert dialog.apply()
    tx = s.history.undo_stack[-1]
    assert _ops(tx) == ["wall_type.edit"] and set(tx.ops[0].after) == {"plan_style"}
    pset = ue.get_pset(alvenaria, wall_types.PLAN_PSET)
    assert pset["Preenchimento"] == "HACHURA" and pset["CorPreenchimento"] == "#336699"
    assert pset["EspessuraLinha"] == pytest.approx(0.00035)
    shape = next(sh for sh in plan.storey_plan(s.doc, s.storey).shapes
                 if sh.role == "wall" and sh.owner == walls[0].GlobalId)
    assert shape.style["fill"] == "hatch"
    window.plan.repaint()
    dialog.dirty = False
    dialog.close()
    path = tmp_path / "estilo.ifc"
    s.save(str(path))
    reopened = Document.open(str(path))
    assert wall_types.read_plan_style(reopened.get(alvenaria.GlobalId))["fill"] == "hatch"
    window.undo()
    assert wall_types.plan_style(alvenaria)["fill"] == "solid"


def test_ui36_tipo_sem_pset_usa_padroes():
    m = Model()  # tipo criado sem plan_style, como um IFC de outra origem
    assert ue.get_pset(m.type14, wall_types.PLAN_PSET) is None
    assert wall_types.read_plan_style(m.type14) is None
    assert wall_types.plan_style(m.type14) == wall_types.DEFAULT_PLAN_STYLE
    m.wall()
    shape = next(sh for sh in plan.storey_plan(m.doc, m.terreo).shapes if sh.role == "wall")
    assert shape.style == wall_types.DEFAULT_PLAN_STYLE
    style = {**wall_types.DEFAULT_PLAN_STYLE, "fill": "none"}
    tx = m.commit(cmd.edit_wall_type(m.doc, m.type14, plan_style=style))
    assert wall_types.read_plan_style(m.type14)["fill"] == "none"
    m.history.undo()
    assert ue.get_pset(m.type14, wall_types.PLAN_PSET) is None  # desfazer remove o Pset
    assert tx.ops[0].before == {"plan_style": None}
    tx = m.commit(cmd.create_wall_type(m.doc, "Com estilo", LAYERS_14, plan_style=style))
    assert wall_types.read_plan_style(m.doc.get(tx.ops[0].id))["fill"] == "none"
