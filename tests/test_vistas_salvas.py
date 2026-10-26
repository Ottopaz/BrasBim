# SPDX-License-Identifier: LGPL-3.0-or-later
"""Vistas salvas (spec/ui 25 §7), no núcleo: VS01 a VS05."""

import ifcopenshell.util.element as ue
import pytest
from estrutura import check_history, created

from brasbim.core import display_layers as dl
from brasbim.core import plan, storeys
from brasbim.core.annotations import commands as ac
from brasbim.core.document import OpError
from brasbim.core.drawings import saved_views as sv
from brasbim.core.drawings import sheets
from brasbim.core.walls import commands as cmd

CAMERA = {"target": [3.0, 2.0, 1.0], "distance": 20.0, "yaw": -1.0, "pitch": 0.5,
          "aspect": 2.0}


@pytest.fixture
def casa(model):
    model.commit(cmd.create_rectangle(model.doc, model.type14, model.terreo, (0, 0), (6, 4)))
    return model


def _id(doc, name):
    return next(x["id"] for x in dl.read_config(doc)["layers"] if x["name"] == name)


def _plan_view(model, **fields):
    fields = {"storey": model.terreo.GlobalId, "scale": 50, **fields}
    return created(model, sv.create_saved_view(model.doc, "Térreo", "plan", **fields))


def test_vs01_criar_editar_excluir(casa, tmp_path):
    def action():
        _plan_view(casa, layers=dl.states_of(casa.doc, dl.Display()))
        view = casa.doc.get(casa.history.undo_stack[-1].ops[0].id)
        casa.commit(sv.edit_saved_view(casa.doc, view, name="Térreo 1:100", scale=100))
        created(casa, sv.create_saved_view(casa.doc, "3D 1", "3d", camera=CAMERA))
        corte = created(casa, ac.create_view(casa.doc, "section", (3, -1), (3, 5), "left"))
        created(casa, sv.create_saved_view(casa.doc, "Corte A", "section",
                                           view=corte.GlobalId, scale=25))

    check_history(casa, action)
    views = sv.all_saved_views(casa.doc)
    assert [sv.read_state(v)["name"] for v in views] == ["3D 1", "Corte A", "Térreo 1:100"]
    entity = views[2]
    assert entity.is_a("IfcAnnotation") and entity.ObjectType == "VistaSalva"
    assert "Parametros" in ue.get_pset(entity, "BrasBim_VistaSalva")
    assert not dl.layerable(entity)
    reopened = casa.reopen(tmp_path)
    names = sorted(e.Name for e in reopened.by_type("IfcAnnotation")
                   if e.ObjectType == "VistaSalva")
    assert names == ["3D 1", "Corte A", "Térreo 1:100"]
    check_history(casa, lambda: casa.commit(sv.delete_saved_view(casa.doc, entity)))
    with pytest.raises(OpError):
        sv.create_saved_view(casa.doc, "", "plan", storey=casa.terreo.GlobalId)
    with pytest.raises(OpError):
        sv.create_saved_view(casa.doc, "x", "3d", camera={"target": [0, 0, 0]})


def test_vs02_camadas_copiadas(casa):
    paredes = _id(casa.doc, "Paredes")
    hidden = dl.Display(hidden=frozenset({paredes}))
    view = _plan_view(casa, layers=dl.states_of(casa.doc, hidden))
    walls = {w.GlobalId for w in casa.doc.ifc.by_type("IfcWall")}
    state = sv.read_state(view)
    with sv.drawing(casa.doc, state):
        drawn = sv.plan_of(casa.doc, state)
    assert not {s.owner for s in drawn.shapes} & walls
    # a janela continua como estava (tudo visível)
    assert walls <= {s.owner for s in plan.storey_plan(casa.doc, casa.terreo).shapes}
    # mudar uma combinação depois não muda a vista
    casa.commit(dl.save_combination(casa.doc, "Outra", dl.Display()))
    assert sv.read_state(view)["layers"] == dl.states_of(casa.doc, hidden)


def test_vs03_escala_da_vista(casa):
    view = _plan_view(casa, scale=100)
    state = sv.read_state(view)
    assert storeys.scale(casa.terreo) == 50
    with sv.drawing(casa.doc, state):
        assert storeys.scale(casa.terreo) == 100
    assert storeys.scale(casa.terreo) == 50
    sheet = created(casa, sheets.create_sheet(casa.doc))
    casa.commit(sheets.add_to_sheet(casa.doc, sheet, {"kind": "saved",
                                                      "saved": view.GlobalId}))
    (item,) = sheets.read_state(sheet)["views"]
    assert sheets.scale_of(casa.doc, item) == 100
    w, _ = sheets.view_size(casa.doc, item)
    assert w == pytest.approx(6000 / 100, abs=1)
    # a escala da janela não vaza para a planta do pavimento posta na prancha
    storeys.set_scale_override(casa.terreo.GlobalId, 200)
    try:
        plan_item = {"kind": "plan", "storey": casa.terreo.GlobalId}
        assert sheets.view_size(casa.doc, plan_item)[0] == pytest.approx(6000 / 50, abs=1)
    finally:
        storeys.clear_scale_overrides()


def test_vs04_recorte(casa):
    view = _plan_view(casa, crop=[0.0, 0.0, 3.0, 2.0])
    item = {"kind": "saved", "saved": view.GlobalId}
    assert sheets.view_size(casa.doc, item) == pytest.approx((60.0, 40.0))


def test_vs05_por_na_prancha_e_excluir(casa):
    view = _plan_view(casa)
    three = created(casa, sv.create_saved_view(casa.doc, "3D 1", "3d", camera=CAMERA))
    sheet = created(casa, sheets.create_sheet(casa.doc))
    casa.commit(sheets.add_to_sheet(casa.doc, sheet, {"kind": "saved",
                                                      "saved": view.GlobalId}, at=(100, 150)))
    casa.commit(sheets.add_to_sheet(casa.doc, sheet, {"kind": "saved",
                                                      "saved": three.GlobalId}))
    items = sheets.read_state(sheet)["views"]
    assert items[0]["at"] == [100.0, 150.0]
    assert sheets.view_size(casa.doc, items[1]) == pytest.approx((160.0, 80.0))
    assert sheets.scale_of(casa.doc, items[1]) is None
    casa.commit(sheets.set_item_width(casa.doc, sheet, 1, 100))
    assert sheets.view_size(casa.doc, sheets.read_state(sheet)["views"][1])[0] == 100
    _, texts = sheets.title_items(casa.doc, sheet, "26/10/2026")
    assert any("Escala 1:50 " in t.text for t in texts)
    with pytest.raises(OpError):
        sheets.add_to_sheet(casa.doc, sheet, {"kind": "saved", "saved": view.GlobalId})
    tx = casa.commit(sv.delete_saved_view(casa.doc, view))
    assert [op.op for op in tx.ops] == ["sheet.edit", "saved_view.delete"]
    assert len(sheets.read_state(sheet)["views"]) == 1
    casa.history.undo()
    assert len(sheets.read_state(sheet)["views"]) == 2


def test_vs05b_excluir_pavimento_ou_corte_leva_a_vista(casa):
    view = _plan_view(casa, storey=casa.superior.GlobalId)
    corte = created(casa, ac.create_view(casa.doc, "section", (3, -1), (3, 5), "left"))
    sec = created(casa, sv.create_saved_view(casa.doc, "Corte A", "section",
                                             view=corte.GlobalId, scale=50))
    sheet = created(casa, sheets.create_sheet(casa.doc))
    for v in (view, sec):
        casa.commit(sheets.add_to_sheet(casa.doc, sheet, {"kind": "saved",
                                                          "saved": v.GlobalId}))
    casa.commit(cmd.delete_storey(casa.doc, casa.superior))
    assert [sv.read_state(v)["name"] for v in sv.all_saved_views(casa.doc)] == ["Corte A"]
    assert len(sheets.read_state(sheet)["views"]) == 1
    casa.history.undo()
    assert len(sv.all_saved_views(casa.doc)) == 2
    assert len(sheets.read_state(sheet)["views"]) == 2
    casa.commit(ac.delete_element(casa.doc, corte))
    assert [sv.read_state(v)["name"] for v in sv.all_saved_views(casa.doc)] == ["Térreo"]
    assert len(sheets.read_state(sheet)["views"]) == 1
