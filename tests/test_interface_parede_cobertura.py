# SPDX-License-Identifier: GPL-3.0-or-later
"""Parede até a cobertura na interface (spec/ui 45, RC08): barra Opções, ficha, Prender e
Soltar. Qt sem tela; o resultado é conferido no modelo."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox, QPushButton
from test_interface import _click

from brasbim.core.structure import commands as sc
from brasbim.core.walls import roof_top
from brasbim.core.walls.wall import read_state
from brasbim.ui.tools import Mods

TILE = [{"material": "Telha cerâmica", "thickness": 0.05}]


@pytest.fixture(autouse=True)
def _planta_visivel(window):
    window.plan.origin = QPointF(150, 450)


def _roof(window, outline=((0, 0), (10, 0), (10, 6), (0, 6))):
    s = window.session
    t = next(t for t in s.doc.ifc.by_type("IfcSlabType") if t.PredefinedType == "ROOF")
    assert s.run(lambda: sc.create_roof(s.doc, t, s.storey, list(outline), base_height=2.8))
    return max(s.doc.ifc.by_type("IfcRoof"), key=lambda e: e.id())


def _field(window, name):
    QApplication.processEvents()
    return next(w for g in window.properties.groups for n, w in g.rows if n == name)


def _last_wall(s):
    return max(s.doc.ifc.by_type("IfcWall"), key=lambda e: e.id())


def test_rc08_ferramenta_e_ficha(window):
    s = window.session
    roof = _roof(window)
    # ferramenta Parede com o topo até a cobertura: a parede nova pega a de cima
    window.activate_tool("wall")
    tool = window.toolbox.active
    tool.options.top = "roof"
    window.options_bar.show_for(tool)
    _click(window, (0, 0))
    _click(window, (0, 6))
    QTest.keyClick(window.plan, Qt.Key_Return)
    wall = _last_wall(s)
    state = read_state(s.doc, wall)
    assert state["top_mode"] == "roof" and state["top_roofs"] == [roof.GlobalId]
    # ficha: a cobertura (clicar seleciona), a face, a altura e Soltar
    s.select([wall.GlobalId])
    assert isinstance(_field(window, "Cobertura"), QPushButton)
    face = _field(window, "Até a face")
    assert isinstance(face, QComboBox)
    face.setCurrentIndex(face.findData("top"))
    assert read_state(s.doc, wall)["roof_face"] == "top"
    release = next(w for g in window.properties.groups for n, w in g.rows
                   if isinstance(w, QPushButton) and w.text() == "Soltar da cobertura")
    release.click()
    assert read_state(s.doc, wall)["top_mode"] == "storey"
    # de volta pela ficha: "Até a cobertura" no Topo
    top = _field(window, "Topo")
    top.setCurrentIndex(top.findData("roof"))
    assert read_state(s.doc, wall)["top_roofs"] == [roof.GlobalId]


def test_rc08_prender_e_soltar_pelo_menu(window):
    s = window.session
    roof = _roof(window, outline=((20, 0), (30, 0), (30, 6), (20, 6)))
    window.activate_tool("wall")
    tool = window.toolbox.active
    tool.press((20, 0), Mods())
    tool.press((20, 6), Mods())
    tool.key("enter")
    wall = _last_wall(s)
    assert read_state(s.doc, wall)["top_mode"] == "storey"
    labels = [t for t, _ in window.context_actions(window.plan, wall.GlobalId)]
    assert "Prender à cobertura" in labels and "Soltar da cobertura" not in labels
    # Prender: com a parede selecionada, clica-se na cobertura (na borda dela)
    s.select([wall.GlobalId])
    window.activate_tool("roof_attach")
    tool = window.toolbox.active
    assert "cobertura" in tool.hint().lower()
    gid = window.ctx.plan.pick((25.0, -0.6), window.ctx.tol)
    assert gid is not None
    tool.press((25.0, -0.6), Mods())
    assert read_state(s.doc, wall)["top_roofs"] == [roof.GlobalId]
    labels = [t for t, _ in window.context_actions(window.plan, wall.GlobalId)]
    assert "Soltar da cobertura" in labels
    window.detach_from_roof(wall.GlobalId)
    assert read_state(s.doc, wall)["top_mode"] == "storey"
    assert not [r for r in wall.InterferesElements if roof_top.is_roof_rel(r)]
