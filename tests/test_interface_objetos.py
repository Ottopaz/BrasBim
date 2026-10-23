# SPDX-License-Identifier: GPL-3.0-or-later
"""Objetos paramétricos na interface (objeto-parametrico.md §4.2, §4.4, §5; OB19), com o
Qt sem tela. O resultado é conferido no modelo IFC."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from test_interface import _click, _move

from brasbim.core.objects import commands as oc
from brasbim.core.objects import elements
from brasbim.core.objects import types as ot
from brasbim.core.walls import commands as cmd
from brasbim.ui.tools import Mods


@pytest.fixture(autouse=True)
def _planta_visivel(window):
    window.plan.origin = QPointF(150, 450)


def _entry(window, name):
    return next(e for e in window.library.index.entries() if e.name == name)


def _objects(window):
    return elements.all_objects(window.session.doc)


def _use(window, name):
    """Como o clique duplo na biblioteca: carrega e ativa a ferramenta com o tipo."""
    (gid,) = window.library.load([_entry(window, name)], ask=False)
    window.use_object_type(gid)
    return window.toolbox.active


def test_ob19_biblioteca_e_ferramenta(window, app):
    window.show_library()
    assert window.library_dock.isVisible()
    assert window.library.tree.topLevelItemCount() >= 4
    tool = _use(window, "Cama de casal 1,38 × 1,88")
    assert tool.name == "object"
    assert window.tool_actions["object"].isChecked()
    assert window.options_bar.isVisible()
    _move(window, (2, 2))
    app.processEvents()
    assert tool.preview(), "o fantasma segue o cursor"
    QTest.keyClick(window.plan, Qt.Key_Space)
    assert tool.angle == pytest.approx(90.0)
    _click(window, (2, 2))
    (e,) = _objects(window)
    state = elements.read_state(window.session.doc, e)
    assert state["point"] == pytest.approx([2.0, 2.0], abs=0.06)
    assert state["angle"] == pytest.approx(90.0)
    # Tab: rotação digitada
    tool.fix("angle", 45.0)
    tool.press((5.0, 2.0), Mods())
    (new,) = [x for x in _objects(window) if x != e]
    assert elements.read_state(window.session.doc, new)["angle"] == pytest.approx(45.0)
    # biblioteca mostra que o tipo está no projeto
    window.library.refresh()
    texts = []

    def walk(item):
        texts.append(item.text(0))
        for i in range(item.childCount()):
            walk(item.child(i))

    for i in range(window.library.tree.topLevelItemCount()):
        walk(window.library.tree.topLevelItem(i))
    assert any("Cama de casal" in t and "no projeto" in t for t in texts)


def test_ob19_preso_a_parede(window, app):
    s = window.session
    s.run(lambda: cmd.create_wall(s.doc, window.toolbox.tools["wall"].options.type, s.storey,
                                  (0, 0), (5, 0)))
    tool = _use(window, "Lavatório suspenso")
    assert tool.hosted()
    _move(window, (2.0, 0.3))
    assert tool.host is not None and tool.host["side"] == "left"
    assert tool.preview()[0].style == "preview"
    assert [f.key for f in tool.fields()] == ["distance", "elevation"]
    _move(window, (2.0, 4.0))  # longe da parede: sem lugar
    assert tool.host is None
    tool.press((2.0, 0.3), Mods())
    (e,) = _objects(window)
    state = elements.read_state(s.doc, e)
    assert state["host"]["distance"] == pytest.approx(1.75, abs=0.06)


def test_ob19_alca_e_painel(window, app):
    s = window.session
    tool = _use(window, "Guarda-roupa 2 portas")
    tool.press((1.0, 1.0), Mods())
    (e,) = _objects(window)
    window.activate_tool("select")
    s.select([e.GlobalId])
    app.processEvents()
    select = window.toolbox.active
    handles = [h for h in select._all_handles() if h[1] == "obj:largura"]
    assert len(handles) == 1
    q = handles[0][2]
    assert q[0] == pytest.approx(2.0, abs=1e-6)  # 1,00 de largura: a borda direita
    select.press(q, Mods())
    select.move((2.5, q[1]), Mods())
    select.move((2.5, q[1]), Mods())
    assert select.drag and select.drag["tx"] is not None
    select.release((2.5, q[1]), Mods())
    values = elements.values_of(s.doc, e)
    assert values["largura"] == pytest.approx(1.5, abs=0.011)
    # painel de propriedades: parâmetros de ocorrência editáveis, de tipo só leitura
    window.properties._rebuild()
    names = [n for g in window.properties.groups for n, _ in g.rows if n]
    assert "Largura (m)" in names and "Portas" in names
    # mini-barra: trocar tipo e selecionar todos do mesmo tipo
    from brasbim.ui.tools import selection_actions

    actions = selection_actions(s.doc, s.selection)
    assert {"swap_type", "edit_object_type", "select_similar"} <= set(actions)
    other = window.library.load([_entry(window, "Guarda-roupa 3 portas")], ask=False)[0]
    s.run(lambda: oc.change_type(s.doc, [e.GlobalId], other))
    assert elements.read_state(s.doc, e)["type"] == other
    assert ot.by_name(s.doc, "Guarda-roupa 3 portas").GlobalId == other


def test_ob18_editor(window, app, monkeypatch):
    from brasbim.core.objects import definition as od
    from brasbim.ui import object_editor
    from brasbim.ui.object_editor import ObjectEditor

    warnings = []
    monkeypatch.setattr(object_editor.QMessageBox, "warning",
                        lambda *a, **k: warnings.append(a[2]))
    s = window.session
    editor = ObjectEditor(s, None, parent=window)
    editor._set_defn("name", "Banco")
    editor.defn["params"].insert(0, od.new_param("largura", "length", "type", 1.2,
                                                 label="Largura"))
    editor.defn["params"].insert(1, od.new_param("altura", "length", "occurrence", 0.45,
                                                 label="Altura"))
    editor.defn["pieces"].append(od.new_piece("box", width="largura", depth=0.4,
                                              height="altura", material="Madeira"))
    editor._fill_params()
    editor._fill_items("pieces")
    editor._fill_types()
    editor._update()
    assert not editor.problems
    assert editor.preview.tris and editor.apply_button.isEnabled()
    # ciclo: recusado na linha, sem gravar
    editor.defn["params"][0]["formula"] = "altura * 2"
    editor.defn["params"][1]["formula"] = "largura / 2"
    editor._update()
    assert editor.problems and not editor.apply_button.isEnabled()
    rows = {p.where[1] for p in editor.problems if p.where[0] == "param"}
    assert rows & {0, 1}
    editor.defn["params"][0]["formula"] = None
    editor.defn["params"][1]["formula"] = None
    editor._update()
    assert editor.apply()
    (t,) = [x for x in ot.all_types(s.doc) if ot.definition_of(x)["name"] == "Banco"]
    assert ot.read(t)["definition"]["version"] == 1
    tool = window.toolbox.tools["object"]
    tool.set_type(t.GlobalId)
    window.activate_tool("object")
    tool.press((1.0, 1.0), Mods())
    (e,) = _objects(window)
    # editar a definição: versão + 1 e a ocorrência refeita
    editor = ObjectEditor(s, ot.definition_of(t)["object_id"], parent=window)
    editor.defn["pieces"][0]["depth"] = 0.5
    editor._update()
    assert editor.apply()
    assert ot.read(t)["definition"]["version"] == 2
    box = next(r for r in e.Representation.Representations
               if r.RepresentationIdentifier == "Box").Items[0]
    assert box.YDim == pytest.approx(0.5)
    # valores que deixam a ocorrência inválida: nada é gravado e a mensagem lista
    editor.defn["pieces"][0]["height"] = "altura - 1"
    editor._update()
    assert not editor.apply()
    assert warnings and "Banco" in warnings[-1]
    assert ot.read(t)["definition"]["version"] == 2
