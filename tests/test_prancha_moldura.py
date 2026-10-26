# SPDX-License-Identifier: LGPL-3.0-or-later
"""Seleção, limite e moldura dos desenhos na prancha (spec/ui 29 §5), no núcleo: PS01 e
PS02."""

import json

import ifcopenshell.util.element
import pytest
from estrutura import check_history, created, valid

from brasbim.core import plan
from brasbim.core.annotations import commands as ac
from brasbim.core.document import OpError
from brasbim.core.drawings import sheets
from brasbim.core.walls import commands as cmd


@pytest.fixture
def casa(model):
    model.commit(cmd.create_rectangle(model.doc, model.type14, model.terreo, (0, 0), (6, 4)))
    return model


def _prancha(model):
    sheet = created(model, sheets.create_sheet(model.doc))
    view = created(model, ac.create_view(model.doc, "section", (3, -1), (3, 5), "left"))
    model.commit(sheets.add_to_sheet(model.doc, sheet, {"kind": "plan",
                                                        "storey": model.terreo.GlobalId}))
    model.commit(sheets.add_to_sheet(model.doc, sheet, {"kind": "view",
                                                        "view": view.GlobalId}))
    return sheet


def _gravado(ifc, gid):
    """Itens da prancha como estão no IFC relido (Pset ``BrasBim_Prancha``)."""
    pset = ifcopenshell.util.element.get_pset(ifc.by_guid(gid), sheets.PSET)
    return json.loads(pset["Parametros"])["views"]


def test_ps01_varios_numa_transacao_e_ifc(casa, tmp_path):
    sheet = _prancha(casa)
    gid = sheet.GlobalId
    before = [it["at"] for it in sheets.read_state(sheet)["views"]]

    def action():
        tx = casa.commit(sheets.move_many_on_sheet(casa.doc, sheet, [0, 1], (10, -5)))
        assert [op.op for op in tx.ops] == ["sheet.edit"]  # uma transação para os dois
        casa.commit(sheets.set_item_frame(casa.doc, sheet, [0, 1], True, "dashdot", 4))
        casa.commit(sheets.set_item_limit(casa.doc, sheet, 0, [0.5, 0.5, 4.0, 3.0]))

    check_history(casa, action)
    items = _gravado(casa.reopen(tmp_path), gid)
    assert [it["at"] for it in items] == [[b[0] + 10, b[1] - 5] for b in before]
    assert items[1]["frame"] == {"show": True, "dash": "dashdot", "pen": 4}
    assert items[0]["limit"] == [0.5, 0.5, 4.0, 3.0] and "limit" not in items[1]
    assert valid(casa.reopened)
    # tirar os dois de uma vez
    tx = casa.commit(sheets.remove_many_from_sheet(casa.doc, sheet, [0, 1]))
    assert [op.op for op in tx.ops] == ["sheet.edit"]
    assert sheets.read_state(sheet)["views"] == []
    casa.history.undo()
    assert len(sheets.read_state(sheet)["views"]) == 2


def test_ps01_validacao(casa):
    sheet = _prancha(casa)
    with pytest.raises(OpError, match="moldura"):
        sheets.set_item_frame(casa.doc, sheet, [0], True, "pontilhada", 3)
    with pytest.raises(OpError, match="pena"):
        sheets.set_item_frame(casa.doc, sheet, [0], True, "solid", 0)
    with pytest.raises(OpError, match="limite"):
        sheets.set_item_limit(casa.doc, sheet, 0, [4.0, 0.0, 1.0, 3.0])


def test_ps02_limite_pela_alca(casa):
    sheet = _prancha(casa)
    item = sheets.read_state(sheet)["views"][0]  # planta de 6 m a 1:50 = 120 mm
    x0, y0, x1, y1 = sheets.item_rect(casa.doc, item)
    assert x1 - x0 == pytest.approx(120, abs=1)
    box = sheets.view_bounds(casa.doc, item)
    handles = sheets.handle_points(casa.doc, item)
    assert set(handles) == set(sheets.HANDLES)
    # leva o lado direito 40 mm para a esquerda: recorta 2 m do desenho
    limit, at = sheets.limit_from_handle(casa.doc, item, "e", (x1 - 40, handles["e"][1]))
    assert limit[2] == pytest.approx(box[2] - 2.0, abs=1e-3)
    assert limit[0] == pytest.approx(box[0]) and limit[1:4:2] == pytest.approx(
        [box[1], box[3]])
    casa.commit(sheets.set_item_limit(casa.doc, sheet, 0, limit, at))
    item = sheets.read_state(sheet)["views"][0]
    nx0, ny0, nx1, ny1 = sheets.item_rect(casa.doc, item)
    assert (nx0, ny0, ny1) == (pytest.approx(x0), pytest.approx(y0), pytest.approx(y1))
    assert nx1 == pytest.approx(x1 - 40)  # o lado oposto ficou parado
    # o limite fica no modelo: a parede nova fora dele não muda o tamanho no papel
    casa.commit(cmd.create_wall(casa.doc, casa.type14, casa.terreo, (6, 0), (12, 0)))
    assert sheets.item_rect(casa.doc, item) == pytest.approx((nx0, ny0, nx1, ny1))
    # menor lado: 5 mm
    limit, _ = sheets.limit_from_handle(casa.doc, item, "w", (nx1 + 50, 0))
    assert (limit[2] - limit[0]) * 1000 / 50 == pytest.approx(sheets.MIN_LIMIT_MM)
    # ajustar ao desenho: volta o desenho inteiro, alinhado com o recorte
    casa.commit(sheets.set_item_limit(casa.doc, sheet, 0, None))
    item = sheets.read_state(sheet)["views"][0]
    assert "limit" not in item
    fx0, fy0, _, _ = sheets.item_rect(casa.doc, item)
    assert (fx0, fy0) == (pytest.approx(x0), pytest.approx(y0))
    # o corte também tem alças (a vista 3D não, por ``sheets.is_3d``)
    corte = sheets.read_state(sheet)["views"][1]
    assert sheets.handle_points(casa.doc, corte)


def test_contornos_na_area():
    quadrado = [([(0, 0), (2, 0), (2, 2), (0, 2)], True)]
    linha = [([(5, 5), (9, 5)], False)]
    janela = [(-1, -1), (6, -1), (6, 6), (-1, 6)]
    assert plan.outlines_in_area([quadrado, linha], janela) == [0]
    assert plan.outlines_in_area([quadrado, linha], janela, crossing=True) == [0, 1]
    laco = [(1, 1), (3, 1), (3, 3), (1, 3)]  # pega só um canto do quadrado
    assert plan.outlines_in_area([quadrado], laco) == []
    assert plan.outlines_in_area([quadrado], laco, crossing=True) == [0]
