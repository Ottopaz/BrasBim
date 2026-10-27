# SPDX-License-Identifier: LGPL-3.0-or-later
"""Ajustes curtos do pente fino (spec/ui 30), na interface."""

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent

from brasbim.core.walls import commands as cmd


def _double_click(widget) -> None:
    pos = QPointF(5, 5)
    event = QMouseEvent(QMouseEvent.MouseButtonDblClick, pos, widget.mapToGlobal(pos),
                        Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    widget.mouseDoubleClickEvent(event)


def test_aj02_clique_duplo_maximiza(window):
    window.resize(1200, 800)
    window.set_view("split")
    plan_pane, pane3d = window.panes
    assert window.plan.parent() is plan_pane and window.view3d.parent() is pane3d
    assert min(window.splitter.sizes()) > 0
    _double_click(pane3d.header)
    assert window.splitter.sizes()[0] == 0 and window.splitter.sizes()[1] > 0
    _double_click(pane3d.header)  # de novo: as duas metades
    a, b = window.splitter.sizes()
    assert a > 0 and abs(a - b) <= 1
    _double_click(plan_pane.header)
    assert window.splitter.sizes()[1] == 0
    window.set_view("plan")  # volta às abas
    assert window.tabs.indexOf(window.plan) >= 0 and window.tabs.indexOf(window.view3d) >= 0
    window.set_view("split")
    assert window.plan.parent() is plan_pane and min(window.splitter.sizes()) > 0


def test_aj03_vistas_3d_padrao(window):
    s = window.session
    s.run(lambda: cmd.create_rectangle(s.doc, s.doc.ifc.by_type("IfcWallType")[0], s.storey,
                                       (0, 0), (6, 4)))
    window.set_view("plan")
    window.standard_view("top")
    assert window.tabs.currentWidget() is window.view3d  # passa para o 3D
    cam = window.view3d.camera
    d = cam.eye() - cam.target
    assert d[2] == pytest.approx(cam.distance, rel=1e-6)
    assert cam.target[:2] == pytest.approx((3, 2), abs=0.2)
    window.standard_view("front")
    d = cam.eye() - cam.target
    assert d[1] < 0 and abs(d[0]) < 1e-6 and abs(d[2]) < 1e-6
    window.standard_view("iso_ne")
    d = cam.eye() - cam.target
    assert d[0] > 0 and d[1] > 0 and d[2] > 0
    assert d[0] == pytest.approx(d[1]) and d[0] == pytest.approx(d[2], rel=1e-6)
    labels = [a for a, _ in window.context_actions(window.view3d, None)]
    assert labels == ["Enquadrar tudo", "Vista de topo", "Isométrica"]


def _item_of(tree, name):
    def walk(item):
        entry = item.data(0, Qt.UserRole)
        if entry is not None and entry.name == name:
            return item
        for i in range(item.childCount()):
            found = walk(item.child(i))
            if found is not None:
                return found
        return None

    for i in range(tree.topLevelItemCount()):
        found = walk(tree.topLevelItem(i))
        if found is not None:
            return found
    raise AssertionError(name)


def test_aj04_arrastar_da_biblioteca(window, app):
    from PySide6.QtGui import QDropEvent

    from brasbim.core.objects import elements

    window.show_library()
    tree = window.library.tree
    mime = tree.mimeData([_item_of(tree, "Cama de casal 1,38 × 1,88")])
    assert mime is not None and mime.hasFormat("application/x-brasbim-objeto")
    event = QDropEvent(window.plan.to_screen((3, 2)), Qt.CopyAction, mime, Qt.LeftButton,
                       Qt.NoModifier)
    window.plan.dropEvent(event)
    (obj,) = elements.all_objects(window.session.doc)
    state = elements.read_state(window.session.doc, obj)
    assert state["point"] == pytest.approx([3.0, 2.0], abs=0.06)
    assert window.toolbox.active.name == "object"
