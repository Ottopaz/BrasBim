# SPDX-License-Identifier: LGPL-3.0-or-later
"""Folhas mestras (spec/ui 26 §6), no núcleo: FM01 a FM04."""

import ifcopenshell.util.element as ue
import pytest
from estrutura import check_history, created

from brasbim.core.document import OpError
from brasbim.core.drawings import masters, sheets
from brasbim.core.walls import commands as cmd


@pytest.fixture
def casa(model):
    model.commit(cmd.create_rectangle(model.doc, model.type14, model.terreo, (0, 0), (6, 4)))
    return model


def _master(model, *args, **kw):
    return created(model, masters.create_master(model.doc, *args, **kw))


def test_fm01_criar_editar_excluir(casa, tmp_path):
    def action():
        m = _master(casa, "A1 escritório", "A1")
        items = [*masters.read_state(m)["items"],
                 {"kind": "text", "at": [30, 30], "text": "Escritório X", "height": 3.0,
                  "align": "center", "bold": True}]
        casa.commit(masters.edit_master(casa.doc, m, items=items, margins=[20, 5, 5, 5]))
        custom = _master(casa, "", "custom", size=[500, 700])
        casa.commit(masters.edit_master(casa.doc, custom, orientation="portrait"))
        casa.commit(masters.duplicate_master(casa.doc, m))

    check_history(casa, action)
    found = masters.all_masters(casa.doc)
    names = [masters.read_state(m)["name"] for m in found]
    assert names == ["500 × 700 mm", "A1 escritório", "A1 escritório (cópia)"]
    a1 = found[1]
    assert a1.is_a("IfcAnnotation") and a1.ObjectType == "FolhaMestra"
    assert "Parametros" in ue.get_pset(a1, "BrasBim_FolhaMestra")
    state = masters.read_state(a1)
    assert masters.paper_size(state) == (841.0, 594.0)
    assert state["margins"] == [20, 5, 5, 5]
    reopened = casa.reopen(tmp_path)
    assert len([e for e in reopened.by_type("IfcAnnotation")
                if e.ObjectType == "FolhaMestra"]) == 3
    check_history(casa, lambda: casa.commit(masters.delete_master(casa.doc, found[2])))
    with pytest.raises(OpError):
        masters.edit_master(casa.doc, a1, margins=[500, 0, 500, 0])
    with pytest.raises(OpError):
        masters.create_master(casa.doc, "x", "custom")


def test_fm02_campos_e_carimbo_padrao(casa):
    casa.commit(sheets.edit_project(casa.doc, name="Casa Silva", responsible="Ana Souza"))
    m = _master(casa, "A3", "A3")
    state = masters.read_state(m)
    texts = [it["text"] for it in state["items"] if it["kind"] == "text"]
    assert "{projeto}" in texts and "Proprietário: {proprietario}" in texts
    sheet = created(casa, sheets.create_sheet(casa.doc, "Planta baixa", master=m.GlobalId))
    casa.commit(sheets.add_to_sheet(casa.doc, sheet, {"kind": "plan",
                                                      "storey": casa.terreo.GlobalId}))
    _, out = sheets.title_items(casa.doc, sheet, "26/10/2026")
    lines = [t.text for t in out]
    assert "Casa Silva" in lines and "Planta baixa" in lines
    assert "Responsável técnico: Ana Souza" in lines
    assert not any(t.startswith("Proprietário") for t in lines)  # campo vazio: some
    assert any(t == "Escala 1:50    26/10/2026    Folha 01/01" for t in lines)
    # a prancha sem folha mestra desenha o mesmo carimbo
    plain = created(casa, sheets.create_sheet(casa.doc, "Planta baixa"))
    casa.commit(sheets.add_to_sheet(casa.doc, plain, {"kind": "plan",
                                                      "storey": casa.terreo.GlobalId}))
    strokes_a, texts_a = sheets.title_items(casa.doc, sheet, "d")
    strokes_b, texts_b = sheets.title_items(casa.doc, plain, "d")
    assert strokes_a == strokes_b
    assert [t.at for t in texts_a] == [t.at for t in texts_b]
    assert masters.fill("{titulo} — {data}", {"titulo": "", "data": ""}) is None
    assert masters.fill("Folha {folha} {outro}", {"folha": "02"}) == "Folha 02 {outro}"


def test_fm03_papel_personalizado(casa):
    m = _master(casa, "Painel", "custom", size=[600, 400], margins=[10, 10, 10, 10],
                items=[{"kind": "line", "points": [[10, 10], [590, 10], [590, 60], [10, 60]],
                        "closed": True, "weight": 0.5}])
    sheet = created(casa, sheets.create_sheet(casa.doc, master=m.GlobalId))
    state = sheets.read_state(sheet)
    assert sheets.paper_of(casa.doc, state) == (600.0, 400.0)
    paper_layout = sheets.layout(casa.doc, state)
    assert paper_layout.frame == (10.0, 10.0, 590.0, 390.0)
    casa.commit(sheets.add_to_sheet(casa.doc, sheet, {"kind": "plan",
                                                      "storey": casa.terreo.GlobalId}))
    (item,) = sheets.read_state(sheet)["views"]
    _, h = sheets.view_size(casa.doc, item)
    assert item["at"][1] - h / 2 >= 60  # acima do desenho do carimbo
    strokes, _ = sheets.title_items(casa.doc, sheet, "d")
    assert any(s.points[0] == (10.0, 10.0) and s.closed for s in strokes)
    with pytest.raises(OpError):
        sheets.create_sheet(casa.doc, master=casa.terreo.GlobalId)


def test_fm04_excluir_em_uso(casa):
    m = _master(casa, "A2 vertical", "A2", "portrait")
    sheet = created(casa, sheets.create_sheet(casa.doc, master=m.GlobalId))
    tx = casa.commit(masters.delete_master(casa.doc, m))
    assert [op.op for op in tx.ops] == ["sheet.edit", "sheet_master.delete"]
    state = sheets.read_state(sheet)
    assert (state["master"], state["format"], state["orientation"]) == (None, "A2",
                                                                       "portrait")
    casa.history.undo()
    assert sheets.read_state(sheet)["master"] == m.GlobalId
