# SPDX-License-Identifier: LGPL-3.0-or-later
"""Pranchas (spec/ui 15 §6), no núcleo: PR01, PR03, PR04, PR06 e PR07."""

import pytest
from estrutura import check_history, created, valid

from brasbim.core.annotations import commands as ac
from brasbim.core.drawings import sheets
from brasbim.core.walls import commands as cmd


@pytest.fixture
def casa(model):
    model.commit(cmd.create_rectangle(model.doc, model.type14, model.terreo, (0, 0), (6, 4)))
    return model


def _sheet(model, **options):
    return created(model, sheets.create_sheet(model.doc, **options))


def _corte(model):
    return created(model, ac.create_view(model.doc, "section", (3, -1), (3, 5), "left"))


def test_pr01_prancha(casa):
    first = _sheet(casa, title="Planta baixa")
    assert first.is_a("IfcAnnotation") and first.ObjectType == "Prancha"
    state = sheets.read_state(first)
    assert (state["number"], state["format"], state["orientation"]) == ("01", "A3",
                                                                        "landscape")
    assert sheets.paper(state) == (420.0, 297.0)
    assert sheets.read_state(_sheet(casa))["number"] == "02"


def test_pr02_tamanho_da_planta_no_papel(casa):
    sheet = _sheet(casa)
    casa.commit(sheets.add_to_sheet(casa.doc, sheet, {"kind": "plan",
                                                      "storey": casa.terreo.GlobalId}))
    (item,) = sheets.read_state(sheet)["views"]
    w, h = sheets.view_size(casa.doc, item)
    assert w == pytest.approx(6000 / 50, abs=1) and h == pytest.approx(4000 / 50, abs=1)
    x0, _, x1, _ = sheets.frame(sheets.read_state(sheet))
    assert x0 <= item["at"][0] - w / 2 and item["at"][0] + w / 2 <= x1


def test_pr03_corte_na_prancha_e_exclusao(casa):
    sheet = _sheet(casa)
    view = _corte(casa)
    casa.commit(sheets.add_to_sheet(casa.doc, sheet, {"kind": "view", "view": view.GlobalId}))
    assert len(sheets.read_state(sheet)["views"]) == 1
    tx = casa.commit(ac.delete_element(casa.doc, view))
    assert [op.op for op in tx.ops] == ["sheet.edit", "view.delete"]
    assert sheets.read_state(sheet)["views"] == []
    casa.history.undo()
    assert len(sheets.read_state(sheet)["views"]) == 1


def test_pr04_carimbo(casa):
    casa.commit(sheets.edit_project(casa.doc, name="Casa Silva", owner="Maria Silva",
                                    responsible="Ana Souza", registration="CAU A12345-6"))
    sheet = _sheet(casa, title="Planta baixa do térreo")
    _sheet(casa)
    casa.commit(sheets.add_to_sheet(casa.doc, sheet, {"kind": "plan",
                                                      "storey": casa.terreo.GlobalId}))
    _, texts = sheets.title_items(casa.doc, sheet, "16/10/2026")
    lines = [t.text for t in texts]
    assert "Casa Silva" in lines
    assert "Proprietário: Maria Silva" in lines
    assert "Responsável técnico: Ana Souza · CAU A12345-6" in lines
    assert any("Escala 1:50" in t and "Folha 01/02" in t and "16/10/2026" in t
               for t in lines)


def test_pr06_mover_vista(casa):
    sheet = _sheet(casa)
    casa.commit(sheets.add_to_sheet(casa.doc, sheet, {"kind": "plan",
                                                      "storey": casa.terreo.GlobalId}))
    tx = casa.commit(sheets.move_on_sheet(casa.doc, sheet, 0, (200, 150)))
    assert [op.op for op in tx.ops] == ["sheet.edit"]
    assert sheets.read_state(sheet)["views"][0]["at"] == [200.0, 150.0]
    casa.history.undo()
    assert sheets.read_state(sheet)["views"][0]["at"] != [200.0, 150.0]


def test_pr07_validacao_e_diario(casa, tmp_path):
    def action():
        sheet = _sheet(casa, title="Plantas")
        view = _corte(casa)
        casa.commit(sheets.add_to_sheet(casa.doc, sheet, {"kind": "plan",
                                                          "storey": casa.terreo.GlobalId}))
        casa.commit(sheets.add_to_sheet(casa.doc, sheet, {"kind": "view",
                                                          "view": view.GlobalId}))
        casa.commit(sheets.edit_sheet(casa.doc, sheet, format="A2"))
        casa.commit(sheets.edit_project(casa.doc, address="Rua A, 10"))
        tx = casa.commit(cmd.create_storey(casa.doc, "Cobertura", 5.6))
        roof = tx.ops[0].id
        casa.commit(sheets.add_to_sheet(casa.doc, sheet, {"kind": "plan", "storey": roof}))
        tx = casa.commit(cmd.delete_storey(casa.doc, roof))  # a planta sai da prancha
        assert [op.op for op in tx.ops] == ["sheet.edit", "storey.delete"]

    check_history(casa, action)
    assert valid(casa.reopen(tmp_path))


def test_dobras(casa):
    a1 = {**sheets.default_state(), "format": "A1"}
    marks = sheets.fold_marks(a1)
    xs = sorted({round(s.points[0][0], 3) for s in marks if s.points[0][1] in (0.0, 594.0)})
    assert xs[-1] == pytest.approx(841 - 190)
