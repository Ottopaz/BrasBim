# SPDX-License-Identifier: GPL-3.0-or-later
"""Interface da janela e ponto de referência (``spec/ui/09-janela.md`` §10), com o Qt sem
tela: UI82 a UI95."""

import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import ifcopenshell.util.element as ue
import pytest

pytest.importorskip("PySide6")

from brasbim.core import snap
from brasbim.core.fillings import commands as fc
from brasbim.core.fillings import geometry
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import openings
from brasbim.ui.tools import Mods

Y = 3.0  # parede de (0, 3) a (5, 3)


def _wall(window, a=(0, Y), b=(5, Y)):
    s = window.session
    assert s.run(lambda: cmd.create_wall(s.doc, window.toolbox.tools["wall"].options.type,
                                         s.storey, a, b))
    return s.doc.get(s.history.undo_stack[-1].ops[0].id)


def _path(window, wall) -> snap.WallPath:
    window.ctx.invalidate()
    return next(w for w in window.ctx.walls if w.gid == wall.GlobalId)


def _inside(window, wall, along):
    """Ponto no meio da espessura da parede, a ``along`` do início."""
    w = _path(window, wall)
    return w.frame.to_global((along, (w.ymin + w.ymax) / 2 + 0.01))


def _tool(window, name="window"):
    window.activate_tool(name)
    return window.toolbox.active


def _opening(window, element):
    return openings.read_state(fc.opening_of(element))


def _last(window, cls="IfcWindow"):
    return max(window.session.doc.ifc.by_type(cls), key=lambda e: e.id())


def test_ui82_criar_janela(window):
    s = window.session
    wall = _wall(window)
    tool = _tool(window)
    assert s.doc.get(tool.type).Name.startswith("J1")
    p = _inside(window, wall, 2.1)
    tool.move(p, Mods())
    tool.press(p, Mods())
    tx = s.history.undo_stack[-1]
    assert [op.op for op in tx.ops] == ["opening.create", "window.create", "filling.attach"]
    o = _opening(window, _last(window))
    assert (o["distance"], o["width"], o["sill"]) == pytest.approx((1.5, 1.2, 1.1))
    assert "peitoril 1,10 · verga 2,10" in [t for _, t in tool.labels()]
    s.history.undo()
    assert not s.doc.ifc.by_type("IfcWindow")


def test_ui83_distancia_da_ponta_e_peitoril(window):
    wall = _wall(window)
    tool = _tool(window)
    tool.move(_inside(window, wall, 4.2), Mods())
    assert [f.key for f in tool.fields()] == ["ref", "sill"]
    assert tool.fix("ref", 0.30) is None and tool.fix("sill", 1.20) is None
    assert tool.confirm()
    o = _opening(window, _last(window))
    assert o["distance"] + o["width"] == pytest.approx(4.70)
    assert o["sill"] == pytest.approx(1.20)
    assert tool.base == pytest.approx(1.20)  # a próxima janela já sugere 1,20


def test_ui83a_referencia_na_borda_de_uma_porta(window):
    s = window.session
    wall = _wall(window)
    door_type = min(s.doc.ifc.by_type("IfcDoorType"), key=lambda t: t.Name)
    s.run(lambda: fc.create_door(s.doc, door_type, wall, 1.0))  # vão de 1,00 a 1,86
    tool = _tool(window)
    w = _path(window, wall)
    corner = w.frame.to_global((1.86, w.ymax))
    tool.move(corner, Mods())
    window.plan._dwelled()  # 0,4 s parado
    assert tool.reference == pytest.approx(corner)
    tool.move(_inside(window, wall, 3.0), Mods())
    assert tool.field_anchor() is not None
    tool.fix("ref", 0.50)
    tool.confirm()
    assert _opening(window, _last(window))["distance"] == pytest.approx(2.36)
    assert tool.reference is None  # solta ao criar
    tool.move(corner, Mods())
    window.plan._dwelled()
    assert tool.cancel() and tool.reference is None  # Esc solta a referência
    assert not tool.cancel()


def test_ui83b_porta_a_partir_do_canto_da_juncao(window):
    a = _wall(window, (0, 6), (0, 2))
    b = _wall(window, (0, 2), (6, 2))
    assert a and b
    window.ctx.invalidate()
    # Faces à direita: as paredes ficam em x < 0 e y < 2; o canto de dentro é (0, 2).
    corner = min(window.ctx.vertices, key=lambda v: math.dist(v, (0.0, 2.0)))
    assert corner == pytest.approx((0.0, 2.0))
    tool = _tool(window, "door")
    assert tool.acquire(corner)
    tool.move(_inside(window, b, 3.0), Mods())
    tool.fix("ref", 0.15)
    tool.confirm()
    door = _last(window, "IfcDoor")
    o = _opening(window, door)
    w = _path(window, b)
    edges = [w.frame.to_global((x, 0))[0] for x in (o["distance"], o["distance"] + o["width"])]
    assert min(abs(x - corner[0]) for x in edges) == pytest.approx(0.15)
    assert ue.get_type(door).OperationType == "SINGLE_SWING_LEFT"


def test_ui83c_parede_a_partir_da_ponta_de_outra(window):
    _wall(window)
    tool = _tool(window, "wall")
    assert tool.acquire((5.0, Y))
    tool.move((6.0, Y + 0.03), Mods())
    assert [f.key for f in tool.fields()] == ["ref"]
    assert tool.fields()[0].value == pytest.approx(1.0)
    tool.fix("ref", 1.20)
    tool.confirm()
    assert tool.points == [pytest.approx((6.2, Y))]
    assert tool.reference is None
    tool.move((8.0, 5.0), Mods())
    assert [f.key for f in tool.fields()] == ["length", "angle"]


def test_ui83d_retangulo_e_cruzamento(window):
    _wall(window)
    tool = _tool(window, "rectangle")
    assert tool.acquire((5.0, Y))
    tool.move((5.03, 4.0), Mods())
    tool.fix("ref", 0.50)
    tool.confirm()
    assert tool.points == [pytest.approx((5.0, 3.5))]
    tool.cancel()
    wall_tool = _tool(window, "wall")
    wall_tool.press((0.0, 6.0), Mods())
    assert wall_tool.acquire((5.0, Y))
    wall_tool.move((5.03, 6.04), Mods())
    assert wall_tool.snapped.point == pytest.approx((5.0, 6.0))


def test_ui84_vao_que_nao_cabe(window):
    s = window.session
    wall = _wall(window)
    door_type = min(s.doc.ifc.by_type("IfcDoorType"), key=lambda t: t.Name)
    s.run(lambda: fc.create_door(s.doc, door_type, wall, 1.0))
    tool = _tool(window)
    tool.base = 2.0  # verga 3,00 > 2,80
    tool.move(_inside(window, wall, 3.5), Mods())
    assert tool.target["error"]
    tool.base = None
    tool.move(_inside(window, wall, 1.4), Mods())  # sobre a porta
    assert tool.target["error"]
    tool.press(_inside(window, wall, 1.4), Mods())
    assert not s.doc.ifc.by_type("IfcWindow")
    assert s.messages[-1]["level"] == "recusa"


def test_ui85_mao_na_barra_de_opcoes(window):
    s = window.session
    wall = _wall(window)
    s.run(lambda: fc.create_window_type(s.doc, "J7 – de abrir", "SINGLE_PANEL",
                                        ["SIDEHUNGLEFTHAND"], code="J7"))
    tool = _tool(window)
    tool.type = next(t.GlobalId for t in s.doc.ifc.by_type("IfcWindowType")
                     if t.Name == "J7 – de abrir")
    window.options_bar.show_for(tool)
    hands = [a for a in window.options_bar.actions() if a.text().startswith("Mão")]
    assert [a.text() for a in hands] == ["Mão esquerda", "Mão direita"]
    hands[1].trigger()
    assert tool.hinges == "right"
    for along in (1.0, 3.5):
        p = _inside(window, wall, along)
        tool.move(p, Mods())
        tool.press(p, Mods())
    types = {ue.get_type(w).Name for w in s.doc.ifc.by_type("IfcWindow")}
    assert types == {"J7 – de abrir (D)"}
    assert len(s.doc.ifc.by_type("IfcWindowType")) == 8


def test_ui94_biblioteca_inicial(window):
    doc = window.session.doc
    names = sorted(t.Name for t in doc.ifc.by_type("IfcWindowType"))
    assert [n.split(" ")[0] for n in names] == ["J1", "J2", "J3", "J4", "J5", "J6"]
    j3 = next(t for t in doc.ifc.by_type("IfcWindowType") if t.Name.startswith("J3"))
    assert ue.get_pset(j3, "Pset_WindowCommon")["Reference"] == "J3"
    assert ue.get_pset(j3, "BrasBim_EsquadriaTipo")["BasePadrao"] == pytest.approx(1.5)
    materials = {m.Name for m in doc.ifc.by_type("IfcMaterial")}
    assert {"Alumínio", "Vidro"} <= materials


def _placed(window, along=2.1, wall=None, **options):
    s = window.session
    wall = wall or _wall(window)
    j1 = min(s.doc.ifc.by_type("IfcWindowType"), key=lambda t: t.Name)
    tx = fc.create_window(s.doc, j1, wall, along - 0.6, **options)
    s.run(tx)
    return wall, s.doc.get(next(op.id for op in tx.ops if op.op == "window.create"))


def test_ui87_etiquetas_de_esquadrias(window):
    _placed(window)
    assert window.tags_action.text() == "Etiquetas de esquadrias"
    labels = window.ctx.plan.labels
    assert [(la.code, la.size) for la in labels] == [("J1", "1,20 × 1,00 / 1,10")]


def test_ui88_painel_verga_e_peitoril_do_piso(window):
    from PySide6.QtWidgets import QComboBox, QLabel
    from test_interface import _field

    s = window.session
    wall, win = _placed(window)
    s.select([win.GlobalId])
    verga = _field(window, "Verga")
    assert verga.text() == "2,10"
    verga.setText("2,30")
    verga.editingFinished.emit()
    tx = s.history.undo_stack[-1]
    assert [op.op for op in tx.ops] == ["opening.edit"]
    o = _opening(window, win)
    assert (o["height"], o["sill"]) == pytest.approx((1.2, 1.1))
    s.run(lambda: cmd.edit_wall(s.doc, wall, base_offset=0.20))
    s.select([])
    s.select([win.GlobalId])
    assert _field(window, "Peitoril do piso", QLabel).text() == "1,30 m"
    assert _field(window, "Lado interno", QComboBox)  # correr: sem giro (janela §2.4)


def test_ui89_alcas_na_planta(window):
    s = window.session
    wall, win = _placed(window)
    s.select([win.GlobalId])
    tool = window.toolbox.active
    assert len(tool.handles()) == 2
    w = _path(window, wall)
    y = (w.ymin + w.ymax) / 2
    end = w.frame.to_global((2.7, y))
    tool.press(end, Mods())
    target = w.frame.to_global((3.0, y))
    tool.move(target, Mods(alt=True))
    tool.release(target, Mods(alt=True))
    o = _opening(window, win)
    assert (o["distance"], o["width"]) == pytest.approx((1.5, 1.5))


def test_ui90_mini_barra(window):
    from brasbim.ui.tools import selection_actions

    s = window.session
    s.run(lambda: fc.create_window_type(s.doc, "J7", "SINGLE_PANEL", ["SIDEHUNGLEFTHAND"]))
    j7 = next(t for t in s.doc.ifc.by_type("IfcWindowType") if t.Name == "J7")
    wall = _wall(window)
    tx = fc.create_window(s.doc, j7, wall, 1.0)
    s.run(tx)
    win = s.doc.get(next(op.id for op in tx.ops if op.op == "window.create"))
    s.select([win.GlobalId])
    actions = selection_actions(s.doc, s.selection)
    assert "flip_opening" in actions and "flip_hinges" in actions
    window.run_selection_action("flip_opening")
    assert fc.doors.read_state(win)["opens_to"] == "right"
    window.run_selection_action("flip_hinges")
    assert ue.get_type(win).Name == "J7 (D)"
    other = _wall(window, (0, 6), (5, 6))
    tool = window.toolbox.active
    start = _inside(window, wall, 1.4)
    tool.press(start, Mods())
    dest = _inside(window, other, 2.5)
    tool.move(dest, Mods())
    tool.release(dest, Mods())
    tx = s.history.undo_stack[-1]
    assert [op.op for op in tx.ops] == ["opening.edit"]
    assert openings.host(fc.opening_of(win)) == other


def test_ui91_tipos_de_janela(window):
    from brasbim.core import plan
    from brasbim.core.fillings import window_types
    from brasbim.ui.types_dialog import WindowTypesDialog

    s = window.session
    _, win = _placed(window)
    j1 = ue.get_type(win)
    dialog = WindowTypesDialog(s, window, select=j1.GlobalId)
    assert dialog.list.count() == 6
    dialog.partitioning.setCurrentIndex(
        dialog.partitioning.findData("TRIPLE_PANEL_VERTICAL"))
    assert len(dialog.operations) == 3
    assert [f.text() for f in dialog.bar_positions] == ["33,3", "66,7"]
    roles = [r for r, _, _ in dialog.preview.drawing]
    assert roles.count("glass") == 3
    assert dialog.apply()
    state = window_types.read(j1)
    assert state["partitioning"] == "TRIPLE_PANEL_VERTICAL"
    assert [p["position"] for p in state["panels"]] == ["LEFT", "MIDDLE", "RIGHT"]
    assert state["lining"]["mullion_offsets"] == pytest.approx([1 / 3, 2 / 3], abs=1e-3)
    glass = [b for b, r in geometry.window_parts(1.2, 1.0, state) if r == "glazing"]
    assert len(glass) == 3
    body = next(r for r in win.Representation.Representations if r.RepresentationIdentifier
            == "Body")
    assert len(body.Items) == len(geometry.window_parts(1.2, 1.0, state))
    assert plan.window_elevation(1.2, 1.0, state)
    dialog.close()


def test_ui93_excluir_parede_com_porta_e_janelas(window, monkeypatch):
    from brasbim.ui.main_window import delete_transaction

    s = window.session
    wall, _ = _placed(window, 2.1)
    j1 = min(s.doc.ifc.by_type("IfcWindowType"), key=lambda t: t.Name)
    s.run(fc.create_window(s.doc, j1, wall, 3.6))
    p1 = min(s.doc.ifc.by_type("IfcDoorType"), key=lambda t: t.Name)
    s.run(fc.create_door(s.doc, p1, wall, 0.2))
    s.select([wall.GlobalId])
    _tx, cascade = delete_transaction(s)
    assert cascade == "1 porta e 2 janelas"
    asked = []
    monkeypatch.setattr(window, "confirm", lambda text: asked.append(text) or True)
    window.delete_selection()
    assert "1 porta e 2 janelas" in asked[0]
    assert not s.doc.ifc.by_type("IfcWindow") and not s.doc.ifc.by_type("IfcDoor")


# --- 3D (spec/ui 09 §4.2 e §7) --------------------------------------------------------------


def _view3d(window):
    from PySide6.QtCore import QPointF
    from PySide6.QtWidgets import QApplication

    window.plan.origin = QPointF(150, 350)
    window.set_view("split")
    QApplication.processEvents()
    window.view3d.fit()
    return window.view3d


def test_ui89_alcas_no_3d(window):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from test_parede_3d import _drag3d, _handle, _screen

    s = window.session
    _, win = _placed(window)
    view = _view3d(window)
    s.select([win.GlobalId])
    assert [k for k, _ in view.handles()] == ["edge_start", "edge_end", "sill", "head"]
    sill = _handle(view, "sill")
    assert sill[2] == pytest.approx(1.1)
    QTest.mouseClick(view, Qt.LeftButton, Qt.NoModifier, _screen(view, sill))
    tool = window.toolbox.active
    assert [f.label for f in tool.fields()] == ["Peitoril"]
    QTest.keyClicks(view, "1")  # o primeiro número abre o quadro; o resto vai para ele
    QTest.keyClicks(view.numeric, ",3")
    QTest.keyClick(view.numeric, Qt.Key_Return)
    o = _opening(window, win)
    assert (o["sill"], o["height"]) == pytest.approx((1.3, 1.0))
    s.select([win.GlobalId])
    head = _handle(view, "head")
    QTest.mouseClick(view, Qt.LeftButton, Qt.NoModifier, _screen(view, head))
    QTest.keyClicks(view, "2")
    QTest.keyClicks(view.numeric, ",5")
    QTest.keyClick(view.numeric, Qt.Key_Return)
    o = _opening(window, win)
    assert (o["sill"], o["height"]) == pytest.approx((1.3, 1.2))
    s.select([win.GlobalId])
    end = _handle(view, "edge_end")
    _drag3d(view, end, (end[0] + 0.3, end[1], end[2]))
    o = _opening(window, win)
    assert o["distance"] == pytest.approx(1.5) and o["width"] == pytest.approx(1.5, abs=0.02)

    p1 = min(s.doc.ifc.by_type("IfcDoorType"), key=lambda t: t.Name)
    tx = fc.create_door(s.doc, p1, _wall(window, (0, 6), (5, 6)), 1.0)
    s.run(tx)
    s.select([next(op.id for op in tx.ops if op.op == "door.create")])
    assert [k for k, _ in view.handles()] == ["edge_start", "edge_end", "head"]


def test_ui92_cores_e_vidro_no_3d(window):
    s = window.session
    _, win = _placed(window)
    view = _view3d(window)
    mesh = view.scene.meshes[win.GlobalId]
    assert mesh.glass is not None and len(mesh.glass)
    assert mesh.glass_colors[:, 3] == pytest.approx(0.4)  # transparência 0,6
    assert len(mesh.vertices)
    body = next(r for r in win.Representation.Representations
                if r.RepresentationIdentifier == "Body")
    for item in body.Items:
        assert any(i.is_a("IfcStyledItem") for i in s.doc.ifc.get_inverse(item))
    p = mesh.glass[0]
    hit = view.scene.pick((p[0], p[1] - 5, p[2]), (0, 1, 0))
    assert hit is not None


def test_ui95_diario_reaplicado(window):
    import json

    from conftest import snapshot

    from brasbim.core.document import Document
    from brasbim.core.ops import History, Transaction

    s = window.session
    wall, win = _placed(window)
    tool = _tool(window)
    tool.move(_inside(window, wall, 4.2), Mods())
    tool.fix("ref", 0.30)
    tool.confirm()
    s.run(fc.flip_opening(s.doc, win))
    s.run(fc.edit_window(s.doc, win, base=1.2))
    s.run(lambda: fc.create_window_type(s.doc, "J9", "TRIPLE_PANEL_HORIZONTAL",
                                        ["FIXEDCASEMENT", "TOPHUNG", "FIXEDCASEMENT"]))
    journal = json.loads(json.dumps([tx.to_dict() for tx in s.history.journal]))
    other = Document.new(project_id=s.doc.ifc.by_type("IfcProject")[0].GlobalId)
    history = History(other)
    for tx in journal:
        history.commit(Transaction.from_dict(tx))
    assert snapshot(other.ifc) == snapshot(s.doc.ifc)
