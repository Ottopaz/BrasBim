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


# --- §6–§9 ----------------------------------------------------------------------------------


def test_aj05_pegar_todas_as_linhas_da_camada(window, tmp_path):
    from test_importar_desenho import E0, N0, levantamento

    from brasbim.core import terrain
    from brasbim.core.annotations import base, reference
    from brasbim.ui.tools import Mods

    s = window.session
    assert window.import_drawing(str(levantamento(tmp_path / "topo.dxf")),
                                 choose=lambda d: (set(d.layers), "m", (E0, N0)))
    s.run(lambda: terrain.create_terrain(s.doc, boundary=[(0, 0), (20, 0), (20, 15),
                                                          (0, 15)]))
    (t,) = terrain.all_terrains(s.doc)
    s.select([t.GlobalId])
    window.run_selection_action("pick_curves")
    tool = window.toolbox.active
    state = base.read_state(next(a for a in s.doc.ifc.by_type("IfcAnnotation")
                                 if reference.is_reference(a)
                                 and base.read_state(a)["layer"] == "CURVAS"))
    q = tuple(state["lines"][1]["points"][4])
    tool.move(q, Mods())  # sem Shift: só a linha
    assert len(tool.preview()) == 1
    tool.move(q, Mods(shift=True))  # com Shift: a camada inteira
    assert len(tool.preview()) == len(state["lines"]) == 3
    assert tool.labels()[0][1] == "3 linhas da camada"
    tool.press(q, Mods(shift=True))
    assert sorted(c["z"] for c in terrain.read_state(t)["curves"]) == [100.0, 101.0, 102.0]
    s.history.undo()  # uma transação só
    assert terrain.read_state(t)["curves"] == []


def test_aj06_medir(window):
    s = window.session
    window.activate_tool("measure")
    tool = window.toolbox.active
    assert tool.name == "measure"
    count = len(s.history.undo_stack)

    def click(q, **mods):
        from brasbim.ui.tools import Mods

        tool.move(q, Mods(alt=True, **mods))
        tool.press(q, Mods(alt=True, **mods))

    for q in ((0, 0), (4, 0), (4, 3)):
        click(q)
    tool.move((0, 3), tool.mods)
    assert tool.labels()[-1][1] == "total 11,00 m; área 12,00 m², perímetro 14,00 m"
    tool.key("enter")
    assert s.messages[-1]["text"] == "Medida: 7,00 m (4,00 + 3,00)"
    assert "Medida: 7,00 m" in tool.hint()  # barra de estado
    for q in ((0, 0), (4, 0), (4, 3), (0, 3), (0, 0)):  # fecha no primeiro: área
        click(q)
    assert s.messages[-1]["text"] == "Medida: área 12,00 m², perímetro 14,00 m"
    assert not tool.points
    # Shift+clique num elemento: o contorno dele
    s.run(lambda: cmd.create_rectangle(s.doc, s.doc.ifc.by_type("IfcWallType")[0], s.storey,
                                       (10, 0), (16, 4)))
    count = len(s.history.undo_stack)
    window.ctx.invalidate()
    click((13, 0), shift=True)
    text = s.messages[-1]["text"]
    assert text.startswith("Medida de ") and "área" in text and "perímetro" in text
    assert len(s.history.undo_stack) == count  # não cria nada no modelo
    window._show_messages()
    assert window.copy_messages() == text  # copiável, sem a hora
    assert window.command_line.aliases["tool:measure"] == "MD"


def test_aj07_contas_e_coordenadas(window):
    from PySide6.QtTest import QTest

    from brasbim.ui.tools import parse_entry

    assert parse_entry("1,20+0,15") == ("value", pytest.approx(1.35))
    assert parse_entry("2*", 1.5) == ("value", pytest.approx(3.0))
    assert parse_entry("+0,15", 1.0) == ("value", pytest.approx(1.15))
    assert parse_entry("-0,15", 1.0) == ("value", pytest.approx(0.85))
    assert parse_entry("-30", 10.0, signed=True) == ("value", pytest.approx(-30.0))
    assert parse_entry("/3", 1.2) == ("value", pytest.approx(0.4))
    assert parse_entry("*2", 1.2) == ("value", pytest.approx(2.4))
    assert parse_entry("x5 y3") == ("point", (5.0, 3.0))
    assert parse_entry("X5,5;y-1") == ("point", (5.5, -1.0))
    assert parse_entry("x5") == ("copies", 5)
    for bad in ("2+", "abc", "1/0", "1>0"):
        with pytest.raises(ValueError):
            parse_entry(bad)
    s = window.session
    window.activate_tool("wall")
    plan = window.plan

    def type_length(text):
        QTest.keyClick(plan, Qt.Key_Tab)
        QTest.keyClicks(plan.numeric, text)
        QTest.keyClick(plan.numeric, Qt.Key_Return)

    def ends():
        from brasbim.core import geom2d

        out = []
        for w in s.doc.ifc.by_type("IfcWall"):
            path = geom2d.path_from_dict(cmd.read_state(s.doc, w)["path"])
            out.append((tuple(round(c, 6) + 0 for c in path.start),
                        tuple(round(c, 6) + 0 for c in path.end)))
        return sorted(out)

    plan.enter_point((0, 0))
    tool = window.toolbox.active
    from brasbim.ui.tools import Mods

    tool.move((2, 0), Mods(alt=True))
    type_length("2*")  # dobra o medido: 4 m
    assert tool.points[-1] == pytest.approx((4, 0))
    tool.move((4, 2), Mods(alt=True))
    type_length("1,20+0,15")
    assert tool.points[-1] == pytest.approx((4, 1.35))
    type_length("x5 y3")  # coordenada absoluta no campo de comprimento
    assert tool.points[-1] == pytest.approx((5, 3))
    QTest.keyClick(plan, Qt.Key_Return)
    assert ends() == [((0, 0), (4, 0)), ((4, 0), (4, 1.35)), ((4, 1.35), (5, 3))]
    assert not [m for m in s.messages if m["level"] == "recusa"]


def test_aj08_copia_em_serie(window):
    from PySide6.QtTest import QTest

    from brasbim.core import geom2d
    from brasbim.ui.tools import Mods

    s = window.session
    wall_type = s.doc.ifc.by_type("IfcWallType")[0]
    s.run(lambda: cmd.create_chain(s.doc, wall_type, s.storey, [(0, 0), (3, 0)]))
    (wall,) = s.doc.ifc.by_type("IfcWall")
    s.select([wall.GlobalId])
    window.run_selection_action("copy")
    tool, plan = window.toolbox.active, window.plan
    assert tool.name == "copy"
    plan.enter_point((0, 0))
    tool.move((0, 1), Mods(alt=True))
    assert [f.label for f in tool.fields()] == ["Distância", "Ângulo", "Cópias"]
    QTest.keyClick(plan, Qt.Key_Tab)
    for i, value in enumerate(("2", "90", "3")):
        QTest.keyClicks(plan.numeric, value)
        QTest.keyClick(plan.numeric, Qt.Key_Tab if i < 2 else Qt.Key_Return)

    def ys():
        return sorted(round(geom2d.path_from_dict(cmd.read_state(s.doc, w)["path"]).start[1],
                            6) + 0 for w in s.doc.ifc.by_type("IfcWall"))

    assert ys() == [0, 2, 4, 6]
    s.history.undo()  # um desfazer só
    assert ys() == [0]
    # x4 no campo de distância: quatro cópias no próximo clique
    tool.cancel()
    window.run_selection_action("copy")
    tool = window.toolbox.active
    plan.enter_point((0, 0))
    tool.move((0, 1), Mods(alt=True))
    QTest.keyClick(plan, Qt.Key_Tab)
    QTest.keyClicks(plan.numeric, "x4")
    QTest.keyClick(plan.numeric, Qt.Key_Return)
    assert ys() == [0] and tool.count == 4  # só fixou
    plan.enter_point((0, 1.5))
    assert ys() == [0, 1.5, 3, 4.5, 6]
