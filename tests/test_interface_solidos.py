# SPDX-License-Identifier: GPL-3.0-or-later
"""Operações de sólidos na interface (spec/ui 41 §3): SO06."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

import ifcopenshell.util.element as ue
from PySide6.QtWidgets import QPushButton

from brasbim.core import plan as plan_mod
from brasbim.core.structure import solids
from brasbim.core.walls import commands as wc
from brasbim.ui import icons
from brasbim.ui.tools import Mods


def _walls(window):
    """Parede A de (0, 0) a (5, 0) e B atravessando-a em x = 2,5."""
    s = window.session
    t = s.doc.ifc.by_type("IfcWallType")[0]
    out = []
    for start, end, options in (((0, 0), (5, 0), {}), ((2.5, -1), (2.5, 1), {"ref_line": "axis"})):
        before = {w.GlobalId for w in s.doc.ifc.by_type("IfcWall")}
        s.run(lambda a=start, b=end, o=options: wc.create_wall(s.doc, t, s.storey, a, b, **o))
        (new,) = [w for w in s.doc.ifc.by_type("IfcWall") if w.GlobalId not in before]
        out.append(new)
    window.ctx.invalidate()
    return out


def _net(wall):
    return ue.get_pset(wall, "Qto_WallBaseQuantities")["NetVolume"]


def test_so06_ferramenta_ficha_botao_direito_e_planta(window, app):
    s = window.session
    a, b = _walls(window)
    full = _net(a)
    assert {"solid_cut", "solid_subtract", "solid_up", "solid_down",
            "solid_intersect"} <= set(icons.names())
    menu = [x.text() for x in window.menuBar().actions()
            for x in x.menu().actions() if x.menu() is None]
    assert "Recortar por elemento" in menu and "Tirar recortes" in menu

    # Ferramenta: com o alvo selecionado, clica o operador e Enter aplica.
    s.select([a.GlobalId])
    window.activate_tool("solid_cut")
    tool = window.toolbox.active
    assert tool.name == "solid_cut" and "recorta" in tool.hint()
    assert tool.operation == solids.SUBTRACT
    tool.press((2.5, 0.6), Mods())  # na parede B, fora da A
    assert tool.operators == [b.GlobalId]
    assert tool.key("enter")
    app.processEvents()
    assert [r.RelatedElement for r in solids.cut_by(a)] == [b]
    assert _net(a) < full - 0.04
    assert s.selection == {a.GlobalId}

    # Ficha: "Recortado por" no alvo, "Recorta" no operador.
    window.properties._rebuild()
    titles = [g.title for g in window.properties.groups]
    assert "Recortado por" in titles
    group = next(g for g in window.properties.groups if g.title == "Recortado por")
    texts = [w.findChild(QPushButton).text() for _, w in group.rows]
    assert texts == ["Tirar"]
    s.select([b.GlobalId])
    window.properties._rebuild()
    assert "Recorta" in [g.title for g in window.properties.groups]

    # Planta: a parede A cortada não cobre mais o trecho da B.
    plan = plan_mod.storey_plan(s.doc, s.storey)
    pieces = [sh for sh in plan.shapes if sh.owner == a.GlobalId and sh.role == "wall"]
    assert len(pieces) == 2
    assert all(not (2.44 < sum(p[0] for p in sh.points) / len(sh.points) < 2.56)
               for sh in pieces)

    # Botão direito: Tirar recortes desfaz.
    actions = dict(window.context_actions(window.plan, a.GlobalId))
    actions["Tirar recortes"]()
    assert not solids.cut_by(a)
    assert _net(a) == pytest.approx(full)
    assert "Tirar recortes" not in dict(window.context_actions(window.plan, a.GlobalId))


def test_so06_sem_selecao_clica_os_alvos_antes(window):
    s = window.session
    a, _b = _walls(window)
    s.select([])
    window.activate_tool("solid_cut")
    tool = window.toolbox.active
    tool.operation = solids.INTERSECT
    assert "a recortar" in tool.hint()
    tool.press((1, -0.07), Mods())  # parede A
    assert tool.targets == [a.GlobalId]
    tool.key("enter")
    assert "recorta" in tool.hint()
    tool.press((2.5, 0.6), Mods())
    tool.key("enter")
    assert solids.cut_by(a)[0].InterferenceType == "INTERSECT"


def test_so07_quadro_e_destaque_ao_selecionar(window, app):
    """Selecionado um elemento com recorte: o quadro junto dele mostra a operação (ícone e
    o outro elemento) e o outro fica destacado na planta e no 3D (pedido de 2026-11-01)."""
    from brasbim.ui.solid_badge import OPERATION_ICON, partner_ids

    s = window.session
    a, b = _walls(window)
    s.run(lambda: solids.cut_elements(s.doc, [a], [b], solids.SUBTRACT))
    badge = window.plan.solid_badge
    s.select([a.GlobalId])
    window.plan.repaint()
    app.processEvents()
    assert badge.isVisible()
    name_b = b.Name or "Wall"
    assert badge.texts() == [f"Recortado por {name_b} · subtrair"]
    assert partner_ids(window.plan) == {b.GlobalId}
    assert OPERATION_ICON[solids.SUBTRACT] in icons.names()
    window.set_view("split")
    app.processEvents()
    assert partner_ids(window.view3d) == {b.GlobalId}
    # clicar na linha seleciona o outro; o quadro passa a mostrar o lado dele
    badge.rows[0].click()
    assert s.selection == {b.GlobalId}
    window.plan.repaint()
    app.processEvents()
    assert badge.texts() == [f"Recorta {a.Name or 'Wall'} · subtrair"]
    # sem recorte, ou com outra ferramenta, nada aparece
    s.select([])
    window.plan.repaint()
    assert not badge.isVisible() and partner_ids(window.plan) == set()
