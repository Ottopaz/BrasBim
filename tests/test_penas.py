# SPDX-License-Identifier: LGPL-3.0-or-later
"""Tabela de penas (spec/ui 27 §6), no núcleo: PN01 e parte de PN02."""

import copy

import ifcopenshell.util.element as ue
import pytest
from estrutura import check_history

from brasbim.core import pens, plan
from brasbim.core.annotations import commands as ac
from brasbim.core.document import OpError
from brasbim.core.walls import commands as cmd


def test_pn01_configuracao(model, tmp_path):
    doc = model.doc
    assert pens.read_config(doc) is None
    assert pens.config(doc) == pens.default_config()
    resolved = pens.resolve(doc)
    assert resolved.pen("cut") == pens.Pen(pens.INK, 0.5)
    assert resolved.scale("cut") == 1.0 and resolved.weight("dimension", 0.13) == 0.13

    def action():
        cfg = copy.deepcopy(pens.config(doc))
        table = cfg["tables"][0]
        table["pens"]["5"]["weight"] = 0.7
        table["pens"]["13"] = {"color": "#FF0000", "weight": 0.35, "note": "vermelha"}
        table["categories"]["dimension"] = 13
        other = pens.default_table("P&B", "pb")
        other["print_black"] = True
        cfg["tables"].append(other)
        model.commit(pens.edit_config(doc, cfg))
        model.commit(pens.use_table(doc, "pb"))

    check_history(model, action)
    assert pens.read_config(doc)["current"] == "pb"
    padrao = pens.resolve(doc, "padrao")
    assert padrao.pen("cut").weight == 0.7 and padrao.scale("cut") == pytest.approx(1.4)
    assert padrao.pen("dimension") == pens.Pen("#FF0000", 0.35)
    assert pens.resolve(doc, "pb", paper=True).color("dimension") == pens.INK
    assert pens.resolve(doc).table["id"] == "pb"
    assert "Parametros" in ue.get_pset(doc.project, "BrasBim_Penas")
    reopened = model.reopen(tmp_path)
    assert "BrasBim_Penas" in ue.get_psets(reopened.by_type("IfcProject")[0])
    bad = copy.deepcopy(pens.config(doc))
    bad["tables"][0]["pens"]["1"]["color"] = "vermelho"
    with pytest.raises(OpError):
        pens.edit_config(doc, bad)
    bad = copy.deepcopy(pens.config(doc))
    bad["tables"][0]["categories"]["cut"] = 99
    with pytest.raises(OpError):
        pens.edit_config(doc, bad)


def test_pn02_categorias_da_planta(model):
    doc = model.doc
    model.commit(cmd.create_rectangle(doc, model.type14, model.terreo, (0, 0), (6, 4)))
    tx = model.commit(ac.create_annotation(doc, "text", model.terreo, at=[1, 1], text="Sala"))
    text = tx.ops[0].id
    tx = model.commit(ac.create_dimension(doc, model.terreo, [(0, -1), (6, -1)], offset=0.5))
    dim = tx.ops[0].id
    drawn = plan.storey_plan(doc, model.terreo)
    assert {e.pen for e in drawn.edges} <= {"cut", "layer"}
    assert drawn.pens[text] == "text" and drawn.pens[dim] == "dimension"
