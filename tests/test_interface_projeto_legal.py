# SPDX-License-Identifier: LGPL-3.0-or-later
"""Projeto legal, etapa 1 (spec/ui/31-projeto-legal.md §2–§3), na interface: PL01–PL03."""

import ifcopenshell.util.element as ue
from PySide6.QtWidgets import QComboBox
from test_interface import _field

from brasbim.core import intervention as iv
from brasbim.core.drawings import saved_views as sv
from brasbim.core.walls import commands as cmd
from brasbim.ui.toolbars import OptionsBar


def _walls(window):
    s = window.session
    tx = cmd.create_rectangle(s.doc, s.doc.ifc.by_type("IfcWallType")[0], s.storey,
                              (0, 0), (6, 4))
    s.run(tx)
    return [s.doc.get(op.id) for op in tx.ops if op.op == "wall.create"]


def test_pl01_painel_e_mini_barra(window):
    s = window.session
    walls = _walls(window)
    s.select([w.GlobalId for w in walls[:2]])
    combo = _field(window, "Situação", QComboBox)
    assert combo.currentData() == "A_CONSTRUIR"
    assert [combo.itemData(i) for i in range(combo.count())] == list(iv.CODES)
    combo.setCurrentIndex(combo.findData("A_DEMOLIR"))
    tx = s.history.undo_stack[-1]
    assert [op.op for op in tx.ops] == ["situation.set"] * 2
    assert {ue.get_pset(w, iv.PSET)[iv.PROPERTY] for w in walls[:2]} == {"A_DEMOLIR"}
    # Seleção com situações diferentes: "vários"; a escolha vale para todos.
    s.select([walls[0].GlobalId, walls[2].GlobalId])
    combo = _field(window, "Situação", QComboBox)
    assert combo.currentData() is None
    # As propriedades comuns não têm mais o campo Status próprio.
    assert _field(window, "Situação", QComboBox) is combo
    # Mini-barra e Editar > Situação.
    window.plan.repaint()
    assert "situation" in window.plan.selection_bar.visible_actions()
    window.set_selection_situation("EXISTENTE")
    assert {iv.situation_of(s.doc, w) for w in (walls[0], walls[2])} == {"EXISTENTE"}
    s.undo()
    assert iv.situation_of(s.doc, walls[0]) == "A_DEMOLIR"
    assert iv.situation_of(s.doc, walls[2]) == "A_CONSTRUIR"


def test_pl02_opcao_de_criacao(window):
    s = window.session
    window.activate_tool("wall")
    bar: OptionsBar = window.options_bar
    names = [name for name, *_ in bar.choices]
    assert "Situação" in names
    _, labels, current, choose = next(c for c in bar.choices if c[0] == "Situação")
    assert labels[current()] == "A construir"
    choose(labels.index("Existente (manter)"))
    assert s.new_situation == "EXISTENTE"
    walls = _walls(window)
    assert {iv.situation_of(s.doc, w) for w in walls} == {"EXISTENTE"}
    assert s.history.undo_stack[-1].ops[-1].op == "situation.set"
    s.new_situation = iv.DEFAULT
    window.activate_tool("select")


def test_pl03_filtro_da_janela_e_vista_salva(window):
    s = window.session
    walls = _walls(window)
    s.run(iv.set_situation(s.doc, [walls[0].GlobalId], "A_DEMOLIR"))
    assert window.ctx.plan.colors[walls[1].GlobalId] == iv.GENERIC_COLORS["A_CONSTRUIR"]
    s.select([walls[0].GlobalId])
    window.set_situation_view("after")
    assert window.situation_actions["after"].isChecked()
    owners = {sh.owner for sh in window.ctx.plan.shapes}
    assert walls[0].GlobalId not in owners and walls[1].GlobalId in owners
    assert s.selection == set()  # o que some sai da seleção
    assert walls[0].GlobalId not in window.scene.meshes  # 3D também
    s.select([walls[0].GlobalId])
    assert s.selection == set()
    gid = window.save_view(name="Depois da obra")
    assert sv.read_state(s.doc.get(gid))["options"]["situation"] == "after"
    window.close_saved_view()
    window.set_situation_view("project")
    assert walls[0].GlobalId in {sh.owner for sh in window.ctx.plan.shapes}
    assert window.open_saved_view(gid)
    assert s.situation_view == "after" and window.situation_actions["after"].isChecked()
    window.close_saved_view()
    window.set_situation_view("project")
