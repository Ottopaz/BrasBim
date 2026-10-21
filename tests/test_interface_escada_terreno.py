# SPDX-License-Identifier: GPL-3.0-or-later
"""Escada, guarda-corpo e terreno na interface (escada-terreno.md §5, ET08), com o Qt sem
tela."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF

from brasbim.core import terrain
from brasbim.core.structure import railings, stairs
from brasbim.ui.tools import Mods, selection_actions


@pytest.fixture(autouse=True)
def _planta_visivel(window):
    window.plan.origin = QPointF(150, 450)


def _click(tool, p, mods=None):
    mods = mods or Mods(alt=True)
    tool.move(p, mods)
    tool.press(p, mods)


def _panel(window, gid):
    window.session.select([gid])
    window.properties._rebuild()
    return window.properties.groups


def test_et08_escada(window, app):
    s = window.session
    window.activate_tool("stair")
    tool = window.toolbox.active
    tool.options.shape = "L"
    window.options_bar.show_for(tool)
    _click(tool, (1, 1))
    tool.move((1, 4), Mods(alt=True))
    assert tool.preview()
    assert [f.key for f in tool.fields()] == ["angle"]
    tool.press((1, 4), Mods(alt=True))
    (stair,) = stairs.all_stairs(s.doc)
    state = stairs.read_state(stair)
    assert state["start"] == pytest.approx([1, 1])
    assert state["angle"] == pytest.approx(90.0)
    assert state["shape"] == "L"
    assert "rotate" in selection_actions(s.doc, [stair.GlobalId])
    groups = _panel(window, stair.GlobalId)
    assert groups[0].title == "Escada 1"
    assert [g.title for g in groups[1:3]] == ["Cálculo", "Posição"]
    # Tab digita o ângulo
    _click(tool, (6, 1))
    tool.fix("angle", 0.0)
    assert tool.confirm()
    assert len(stairs.all_stairs(s.doc)) == 2


def test_et08_guarda_corpo(window, app):
    s = window.session
    window.activate_tool("railing")
    tool = window.toolbox.active
    tool.options.height = 0.90
    window.options_bar.show_for(tool)
    for p in ((0, 0), (4, 0), (4, 3)):
        _click(tool, p)
    assert tool.preview()
    tool.key("enter")
    (rail,) = [r for r in s.doc.ifc.by_type("IfcRailing") if railings.is_railing(r)]
    state = railings.read_state(rail)
    assert [tuple(q) for q in state["points"]] == [(0, 0), (4, 0), (4, 3)]
    assert state["height"] == pytest.approx(0.90)
    groups = _panel(window, rail.GlobalId)
    assert groups[0].title == "Guarda-corpo"


def test_et08_terreno(window, app):
    s = window.session
    window.activate_tool("terrain")
    tool = window.toolbox.active
    window.options_bar.show_for(tool)
    for p, z in (((0, 0), 0.0), ((10, 0), 1.0), ((10, 8), 3.0), ((0, 8), None)):
        tool.move(p, Mods(alt=True))
        if z is not None:
            assert tool.fix("z", z) is None
        tool.press(p, Mods(alt=True))
        tool.fixed.clear()
    assert [label for _, label in tool.labels()] == ["0,00", "1,00", "3,00", "3,00"]
    tool.key("enter")
    (t,) = terrain.all_terrains(s.doc)
    assert [q[2] for q in terrain.read_state(t)["points"]] == pytest.approx([0, 1, 3, 3])
    groups = _panel(window, t.GlobalId)
    assert groups[0].title == "Terreno"
    # com menos de 3 pontos, recusa sem criar
    _click(tool, (20, 0))
    _click(tool, (25, 0))
    tool.key("enter")
    assert len(terrain.all_terrains(s.doc)) == 1
