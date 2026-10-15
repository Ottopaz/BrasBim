# SPDX-License-Identifier: GPL-3.0-or-later
"""Parede no 3D (``spec/ui/08-parede-no-3d-topo-e-inclinacao.md`` §7): alças, topo e
inclinação, com o Qt sem tela. O resultado é conferido no modelo IFC."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from test_interface import _rectangle
from test_interface_edicao import _drag

from brasbim.core import geom2d
from brasbim.core.walls import commands as cmd


@pytest.fixture(autouse=True)
def _planta_visivel(window):
    """(0, 0) em (150, 350): os pontos dos testes caem dentro da planta (464 × 530 px)."""
    window.plan.origin = QPointF(150, 350)


def _path(s, wall):
    return geom2d.path_from_dict(cmd.read_state(s.doc, wall)["path"])


def _wall_from(s, walls, start):
    return next(w for w in walls if _path(s, w).start == pytest.approx(start))


def _split(window):
    window.set_view("split")
    QApplication.processEvents()
    window.view3d.fit()
    return window.view3d


def _screen(view, point) -> QPoint:
    x, y = view.camera.project(point, view.width(), view.height())
    return QPointF(x, y).toPoint()


def _handle(view, kind):
    return dict(view.handles())[kind]


def _drag3d(view, a, b, modifier=Qt.NoModifier):
    pa, pb = _screen(view, a), _screen(view, b)
    QTest.mousePress(view, Qt.LeftButton, Qt.NoModifier, pa)
    QTest.mouseMove(view, (pa + pb) / 2)
    QTest.mouseMove(view, pb)
    QTest.mouseRelease(view, Qt.LeftButton, modifier, pb)


def test_ui74_alcas_da_parede_no_3d(window):
    s = window.session
    walls = _rectangle(window)
    view = _split(window)
    south = _wall_from(s, walls, (6, 0))
    s.select([south.GlobalId])
    assert [k for k, _ in view.handles()] == ["start", "end", "face", "top", "base"]
    assert _handle(view, "top")[2] == pytest.approx(2.8)
    s.select([w.GlobalId for w in walls[:2]])
    assert view.handles() == []
    window.activate_tool("move")
    s.select([south.GlobalId])
    assert view.handles() == []  # só com Selecionar


def test_ui75_alca_de_topo(window):
    s = window.session
    walls = _rectangle(window)  # topo no pavimento de cima (2,80)
    view = _split(window)
    south = _wall_from(s, walls, (6, 0))
    s.select([south.GlobalId])
    top = _handle(view, "top")
    _drag3d(view, top, (top[0], top[1], 2.5))
    state = cmd.read_state(s.doc, south)
    assert state["top_mode"] == "storey" and state["top_offset"] == pytest.approx(-0.3)
    assert s.history.undo_stack[-1].ops[0].op == "wall.edit"

    s.run(lambda: cmd.edit_wall(s.doc, south, top_mode="fixed", fixed_height=2.8))
    s.select([south.GlobalId])
    at = _screen(view, _handle(view, "top"))
    QTest.mouseClick(view, Qt.LeftButton, Qt.NoModifier, at)  # presa ao cursor
    tool = window.toolbox.active
    assert tool.drag3d is not None and tool.drag3d.sticky
    assert [f.label for f in tool.fields()] == ["Altura"]
    QTest.keyClicks(view, "3")
    QTest.keyClick(view.numeric, Qt.Key_Return)
    state = cmd.read_state(s.doc, south)
    assert state["top_mode"] == "fixed" and state["fixed_height"] == pytest.approx(3.0)
    assert tool.drag3d is None

    s.select([south.GlobalId])
    base = _handle(view, "base")
    _drag3d(view, base, (base[0], base[1], 0.5))
    assert cmd.read_state(s.doc, south)["base_offset"] == pytest.approx(0.5)
    QTest.mouseClick(view, Qt.LeftButton, Qt.NoModifier, _screen(view, _handle(view, "top")))
    QTest.keyClick(view, Qt.Key_Escape)  # Esc solta a alça sem mudar nada
    assert tool.drag3d is None


def test_ui76_alcas_3d_iguais_as_da_planta(window):
    s = window.session
    walls = _rectangle(window)
    view = _split(window)
    north = _wall_from(s, walls, (0, 4))
    s.select([north.GlobalId])
    _drag3d(view, _handle(view, "end"), (5.5, 5, 0))
    tx3d = s.history.undo_stack[-1].to_dict()
    assert _path(s, north).end == pytest.approx((5.5, 5))
    assert len(s.doc.ifc.by_type("IfcRelConnectsPathElements")) == 3  # só esta parede
    window.undo()
    s.select([north.GlobalId])
    _drag(window, (6, 4), (5.5, 5))
    assert s.history.undo_stack[-1].to_dict()["ops"] == tx3d["ops"]

    window.undo()
    south = _wall_from(s, walls, (6, 0))
    s.select([south.GlobalId])
    w = view.selected_wall()
    face = _handle(view, "face")
    target = w.frame.to_global((w.path.length / 2, w.ymax + 0.5))
    _drag3d(view, face, (*target, face[2]))
    tx3d = s.history.undo_stack[-1].to_dict()
    window.undo()
    s.select([south.GlobalId])
    _drag(window, w.middle(), w.frame.to_global((w.path.length / 2, 0.5)))
    assert s.history.undo_stack[-1].to_dict()["ops"] == tx3d["ops"]
