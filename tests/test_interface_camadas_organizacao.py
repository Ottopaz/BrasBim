# SPDX-License-Identifier: GPL-3.0-or-later
"""Camadas na interface (spec/ui 18 §8: CM10, CM14, CM15, CM17), com o Qt sem tela."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from brasbim.core import display_layers as dl
from brasbim.core import plan
from brasbim.core.assistant.tools import Context, default_registry
from brasbim.core.drawings import sheets
from brasbim.core.structure import commands as sc
from brasbim.core.walls import commands as cmd
from brasbim.ui import layers_panel as lp


def _id(doc, name):
    return next(x["id"] for x in dl.read_config(doc)["layers"] if x["name"] == name)


def _casa(window):
    s = window.session
    s.run(lambda: cmd.create_rectangle(s.doc, window.toolbox.tools["wall"].options.type,
                                       s.storey, (0, 0), (6, 4)))
    column_type = next(t for t in s.doc.ifc.by_type("IfcColumnType"))
    s.run(lambda: sc.create_column(s.doc, column_type, s.storey, (3, 2)))
    return sorted(s.doc.ifc.by_type("IfcWall"), key=lambda w: w.GlobalId)


def _item(panel, key):
    item = panel._find(key)
    assert item is not None, key
    return item


def test_cm14_painel_planta_3d_e_propriedades(window):
    s = window.session
    walls = _casa(window)
    paredes = _id(s.doc, "Paredes")
    panel = window.layers
    item = _item(panel, (lp.LAYER, paredes))
    assert item.text(lp.COUNT) == "4"
    journal = len(s.history.journal)
    panel._clicked(item, lp.EYE)  # olho: oculta
    assert paredes in s.display.hidden
    assert len(s.history.journal) == journal  # fora do desfazer (§5.1)
    owners = {sh.owner for sh in window.ctx.plan.shapes}
    assert not owners & {w.GlobalId for w in walls}
    assert not set(window.scene.meshes) & {w.GlobalId for w in walls}
    panel._clicked(_item(panel, (lp.LAYER, paredes)), lp.EYE)  # mostra de novo
    assert {w.GlobalId for w in walls} <= set(window.scene.meshes)
    # Alt + clique isola; de novo, volta ao estado anterior.
    panel.isolate((lp.LAYER, paredes))
    column = s.doc.ifc.by_type("IfcColumn")[0]
    assert column.GlobalId not in window.scene.meshes
    assert {w.GlobalId for w in walls} <= set(window.scene.meshes)
    panel.isolate((lp.LAYER, paredes))
    assert column.GlobalId in window.scene.meshes
    # Painel de propriedades: Camada de dois elementos numa transação só.
    s.select([walls[0].GlobalId, walls[1].GlobalId])
    window.properties._rebuild()
    combo = next(w for g in window.properties.groups for n, w in g.rows if n == "Camada")
    vigas = _id(s.doc, "Vigas")
    count = len(s.history.undo_stack)
    combo.setCurrentIndex(combo.findData(vigas))
    assert len(s.history.undo_stack) == count + 1
    assert dl.layer_of(s.doc, walls[0]) == dl.layer_of(s.doc, walls[1]) == vigas
    # Bloqueada: a seleção pelo clique não pega a parede.
    s.set_display(dl.Display(locked=frozenset({vigas})))
    assert not s.selection
    s.select([walls[0].GlobalId])
    assert not s.selection


def test_cm14_camada_padrao_na_barra_e_camada_oculta(window):
    s = window.session
    window.activate_tool("wall")
    names = [w.toolTip() for w in window.options_bar.findChildren(type(window.layers.combination))]
    assert "Camada em que esta ferramenta desenha" in names
    paredes = _id(s.doc, "Paredes")
    s.set_display(dl.Display(hidden=frozenset({paredes})))
    _casa(window)
    assert paredes not in s.display.hidden  # criar mostra a camada (§3.2)
    assert any("mostrada" in m["text"] for m in s.messages)
    s.set_display(dl.Display(locked=frozenset({paredes})))
    count = len(s.history.undo_stack)
    assert not s.run(lambda: cmd.create_wall(s.doc, window.toolbox.tools["wall"].options.type,
                                             s.storey, (10, 0), (12, 0)))
    assert len(s.history.undo_stack) == count
    assert "bloqueada" in s.messages[-1]["text"]


def test_cm17_busca(window):
    panel = window.layers
    panel.search.setText("cot")
    visible = []
    for i in range(panel.tree.topLevelItemCount()):
        top = panel.tree.topLevelItem(i)
        if top.isHidden():
            continue
        visible.append(top.text(lp.NAME))
        visible += [top.child(j).text(lp.NAME) for j in range(top.childCount())
                    if not top.child(j).isHidden()]
    assert visible == ["Documentação", "Cotas"]
    assert panel._find((lp.GROUP, next(
        g["id"] for g in dl.read_config(window.session.doc)["groups"]
        if g["name"] == "Documentação"))).isExpanded()


def test_cm10_vista_da_prancha_com_combinacao(window):
    s = window.session
    _casa(window)
    column = s.doc.ifc.by_type("IfcColumn")[0]
    tx = sheets.create_sheet(s.doc, "Arquitetura")
    s.run(tx)
    sheet = s.doc.get(tx.ops[0].id)
    s.run(lambda: sheets.add_to_sheet(s.doc, sheet, {"kind": "plan",
                                                     "storey": s.storey.GlobalId}))
    comb = next(c for c in dl.read_config(s.doc)["combinations"] if c["name"] == "Arquitetura")
    s.select([sheet.GlobalId])
    window.properties._rebuild()
    combo = next(w for g in window.properties.groups for n, w in g.rows if n == "  Camadas")
    combo.setCurrentIndex(combo.findData(comb["id"]))
    item = sheets.read_state(s.doc.get(sheet.GlobalId))["views"][0]
    assert item["combination"] == comb["id"]
    before = s.display
    with sheets.item_display(s.doc, item):
        owners = {sh.owner for sh in plan.storey_plan(s.doc, s.storey).shapes}
    assert column.GlobalId not in owners  # Arquitetura oculta a Estrutura
    assert s.display == before  # a janela não muda
    assert column.GlobalId in {sh.owner for sh in plan.storey_plan(s.doc, s.storey).shapes}


def test_cm15_assistente(window):
    s = window.session
    walls = _casa(window)
    registry = default_registry()
    ctx = Context(s.doc, s.history.commit, s.storey.GlobalId)
    s.set_display(dl.Display(hidden=frozenset({_id(s.doc, "Paredes")})))
    out = registry.call(ctx, "describe_model", {})
    assert '"paredes": []' in out["content"][0]["text"]
    s.set_display(dl.Display(locked=frozenset({_id(s.doc, "Paredes")})))
    out = registry.call(ctx, "describe_model", {})
    assert '"bloqueado": true' in out["content"][0]["text"]
    out = registry.call(ctx, "edit_wall", {"id": walls[0].GlobalId, "height": 3.0})
    assert out["isError"] and "bloqueada" in out["content"][0]["text"]


def test_menu_do_elemento_oculta_a_camada(window):
    s = window.session
    walls = _casa(window)
    actions = dict(window.context_actions(window.plan, walls[0].GlobalId))
    actions["Ocultar a camada deste elemento"]()
    assert _id(s.doc, "Paredes") in s.display.hidden
