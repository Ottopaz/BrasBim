# SPDX-License-Identifier: GPL-3.0-or-later
"""Cortes e fachadas na interface (spec/ui 14 §7), com o Qt sem tela."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest

from brasbim.core.drawings import views
from brasbim.core.walls import commands as cmd
from brasbim.ui.main_window import delete_transaction
from brasbim.ui.tools import Mods


@pytest.fixture(autouse=True)
def _planta_visivel(window):
    window.plan.origin = QPointF(150, 450)


def _rect(window):
    s = window.session
    s.run(lambda: cmd.create_rectangle(s.doc, window.toolbox.tools["wall"].options.type,
                                       s.storey, (0, 0), (6, 4)))


def _section(window, a=(3, -1), b=(3, 5), side_point=(1, 2)):
    window.activate_tool("section")
    tool = window.toolbox.active
    for p in (a, b, side_point):
        tool.move(p, Mods())
        tool.press(p, Mods())
    (view,) = views.all_views(window.session.doc)
    return view


def test_corte_pela_ferramenta_e_aba(window):
    s = window.session
    _rect(window)
    view = _section(window)
    state = views.read_state(view)
    assert (state["letter"], state["side"], state["name"]) == ("A", "left", "Corte A")
    assert window.project.view_ids() == [view.GlobalId]
    tab = window.open_view(view.GlobalId)
    assert window.tabs.currentWidget() is tab
    assert window.tabs.tabText(window.tabs.indexOf(tab)) == "Corte A"
    assert tab.drawing.cuts()
    tab.resize(600, 400)
    tab.fit()
    tab.grab()
    # clique numa seção seleciona a parede
    cut = next(it for it in tab.drawing.cuts() if it.weight)
    ring = cut.rings[0]
    c = (sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring))
    assert tab.drawing.pick(c) == cut.owner
    QTest.mouseClick(tab, Qt.LeftButton, Qt.NoModifier, tab.to_screen(c).toPoint())
    assert s.selection == {cut.owner}


def test_corte_acompanha_e_fecha(window):
    s = window.session
    _rect(window)
    view = _section(window)
    tab = window.open_view(view.GlobalId)
    before = len(tab.drawing.items)
    s.run(lambda: cmd.create_wall(s.doc, window.toolbox.tools["wall"].options.type, s.storey,
                                  (0, 2), (6, 2)))
    assert len(tab.drawing.items) > before
    s.select([view.GlobalId])
    window.properties._rebuild()
    assert window.properties.groups[0].title == "Corte A"
    tx, _ = delete_transaction(s)
    s.run(tx)
    assert not window.section_views
    assert window.tabs.indexOf(tab) == -1


def test_fachada_e_simbolos(window):
    _rect(window)
    window.activate_tool("elevation")
    tool = window.toolbox.active
    for p in ((7, -2), (-1, -2), (3, 1)):
        tool.move(p, Mods())
        tool.press(p, Mods())
    (view,) = views.all_views(window.session.doc)
    assert views.read_state(view)["kind"] == "elevation"
    assert view.GlobalId in window.ctx.plan.views
    window.view_symbols_action.trigger()
    assert window.plan.show_view_symbols is False
    window.plan.grab()
    tab = window.open_view(view.GlobalId)
    assert not tab.drawing.cuts() and tab.drawing.items
