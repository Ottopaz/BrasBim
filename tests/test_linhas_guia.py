# SPDX-License-Identifier: GPL-3.0-or-later
"""Linhas-guia a partir de pontos de referência e do ponto anterior
(``spec/ui/37-linhas-guia.md`` §7): LG01 a LG06."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from brasbim.core import guides
from brasbim.core.annotations import commands as ac
from brasbim.core.walls import commands as cmd
from brasbim.ui.tools import Mods

Y = 3.0  # parede de (0, 3) a (5, 3)


def _wall(window, a=(0, Y), b=(5, Y)):
    s = window.session
    assert s.run(lambda: cmd.create_wall(s.doc, window.toolbox.tools["wall"].options.type,
                                         s.storey, a, b))
    window.ctx.invalidate()


def _line(window, *points):
    s = window.session
    assert s.run(lambda: ac.create_annotation(s.doc, "line2d", s.storey,
                                              points=[list(p) for p in points]))
    window.ctx.invalidate()
    return s.doc.get(s.history.undo_stack[-1].ops[0].id)


def _tool(window, name):
    window.activate_tool(name)
    window.ctx.tol = 0.1
    return window.toolbox.active


def test_lg01_guia_prende_pela_projecao():
    lines = guides.guides_from([(0.0, 0.0)], None)
    t = guides.track((3.0, 0.04), lines, 0.1)
    assert t.point == pytest.approx((3.0, 0.0)) and t.guides[0].angle == 0.0
    t = guides.track((-0.03, -2.0), lines, 0.1)
    assert t.point == pytest.approx((0.0, -2.0)) and t.guides[0].angle == 90.0
    t = guides.track((2.03, 1.97), lines, 0.1)
    assert t.point == pytest.approx((2.0, 2.0)) and t.guides[0].angle == 45.0
    t = guides.track((-2.0, 2.05), lines, 0.1)
    assert t.point == pytest.approx((-2.025, 2.025)) and t.guides[0].angle == 135.0
    assert guides.track((3.0, 1.0), lines, 0.1) is None
    assert guides.track((0.05, 0.02), lines, 0.1) is None  # sobre a origem: nada


def test_lg02_cruzamentos_vencem_a_guia_so():
    lines = guides.guides_from([(0.0, 0.0)], (4.0, 1.0))
    t = guides.track((0.04, 1.05), lines, 0.1)  # x = 0 da referência × y = 1 do anterior
    assert t.crossing and t.point == pytest.approx((0.0, 1.0))
    assert {g.from_ref for g in t.guides} == {True, False}
    lines = guides.guides_from([(0.0, 0.0)], None)
    t = guides.track((2.04, 0.03), lines, 0.1, segments=[((2.0, -1.0), (2.0, 1.0))])
    assert t.crossing and t.point == pytest.approx((2.0, 0.0))
    t = guides.track((5.0, 0.03), lines, 0.1, segments=[((2.0, -1.0), (2.0, 1.0))])
    assert not t.crossing and t.point == pytest.approx((5.0, 0.0))


def test_lg03_pegar_soltar_e_ate_tres(window):
    _wall(window)
    _line(window, (10, 0), (14, 0))
    tool = _tool(window, "line2d")
    assert tool.acquire((12.02, 0.01))  # meio da linha 2D
    assert window.ctx.references == [pytest.approx((12.0, 0.0))]
    assert not tool.acquire((12.0, 0.0))  # já é referência
    assert not tool.acquire((7.0, 7.0))  # nada ali
    assert tool.acquire((5.0, Y)) and tool.acquire((10.0, 0.0)) and tool.acquire((14.0, 0.0))
    assert window.ctx.references == [pytest.approx(q) for q in ((5, Y), (10, 0), (14, 0))]
    tool.move((20.0, 5.0), Mods())
    window.plan.press_escape()  # o primeiro Esc solta as referências
    assert window.ctx.references == []
    tool.acquire((5.0, Y))
    window.activate_tool("wall")
    assert window.ctx.references == []  # troca de ferramenta também


def _last_wall_ends(window):
    s = window.session
    wall = max(s.doc.ifc.by_type("IfcWall"), key=lambda e: e.id())
    window.ctx.invalidate()
    return next(w for w in window.ctx.walls if w.gid == wall.GlobalId).ends()


def test_lg04_parede_pela_guia(window):
    _wall(window)
    tool = _tool(window, "wall")
    tool.press((10.0, 0.0), Mods())
    tool.move((12.38, 2.31), Mods())  # diagonal a partir do ponto anterior
    assert tool.snapped.kind == "guide"
    d = 3.3 / 2 ** 0.5  # sobre a guia, a distância segue o passo da grade (0,10 m)
    assert tool.snapped.point == pytest.approx((10.0 + d, d))
    tool.cancel()
    tool.cancel()
    assert tool.acquire((5.0, Y))
    tool.press((0.0, 6.0), Mods())
    # 45° da referência (5, 3) × 0° do ponto anterior (0, 6): (8, 6)
    tool.move((8.04, 6.03), Mods())
    assert tool.snapped.kind == "inter" and tool.snapped.point == pytest.approx((8.0, 6.0))
    tool.press((8.04, 6.03), Mods())
    tool.key("enter")  # encerra a cadeia: grava a parede
    ends = _last_wall_ends(window)
    assert sorted(map(tuple, ends)) == [pytest.approx((0.0, 6.0)), pytest.approx((8.0, 6.0))]


def test_lg05_referencia_fica_e_prioridades(window):
    _wall(window)
    tool = _tool(window, "wall")
    assert tool.acquire((5.0, Y))
    tool.move((5.03, 4.0), Mods())
    tool.fix("ref", 0.5)
    tool.press((5.03, 4.0), Mods())
    assert tool.points == [pytest.approx((5.0, 3.5))]
    assert window.ctx.references == [pytest.approx((5.0, Y))]  # continua depois do clique
    tool.move((0.03, 3.04), Mods())  # ponta da parede vence a guia
    assert tool.snapped.kind == "end" and tool.snapped.point == pytest.approx((0.0, Y))
    window.ctx.guides_on = False
    tool.move((5.04, 7.33), Mods())
    assert window.ctx.tracked is None and tool.snapped.kind not in ("guide", "inter")
    window.ctx.guides_on = True
    tool.move((5.04, 7.33), Mods())
    assert tool.snapped.point == pytest.approx((5.0, 7.3))
    assert window.ctx.guide_marks()  # x da referência e a guia


def test_lg06_mover_com_referencia(window):
    _wall(window)
    line = _line(window, (20, 0), (22, 0))
    window.session.select([line.GlobalId])
    tool = _tool(window, "move")
    tool.press((20.0, 0.0), Mods())
    assert tool.acquire((5.0, Y))
    # 135° da referência (5, 3) cruza y = 0 do ponto de base em (8, 0)
    tool.move((8.04, 0.03), Mods())
    assert tool.snapped.point == pytest.approx((8.0, 0.0))
    tool.press((8.04, 0.03), Mods())
    pts = ac.read_state(window.session.doc, window.session.doc.get(line.GlobalId))["points"]
    assert [tuple(p) for p in pts] == [pytest.approx((8.0, 0.0)), pytest.approx((10.0, 0.0))]
