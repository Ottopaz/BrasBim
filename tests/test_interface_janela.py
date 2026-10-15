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
