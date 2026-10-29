# SPDX-License-Identifier: LGPL-3.0-or-later
"""Projeto legal, etapa 3 (spec/ui/31-projeto-legal.md §5 e §14), no núcleo: quadro de
áreas com classificação, dados do lote, índices e memória de cálculo (PL05, PL05b–PL05e)."""

import copy

import ifcopenshell.util.element as ue
import pytest
from estrutura import check_history

from brasbim.core import clip, municipal, terrain
from brasbim.core import intervention as iv
from brasbim.core.annotations import commands as ac
from brasbim.core.annotations import spaces
from brasbim.core.document import OpError
from brasbim.core.quantities import export
from brasbim.core.quantities import legal_areas as la
from brasbim.core.quantities import tables as tb
from brasbim.core.structure import rooms
from brasbim.core.walls import commands as cmd


def _space(model, outline, name):
    tx = model.commit(ac.create_space(model.doc, model.terreo, outline, name=name))
    return model.doc.get(tx.ops[0].id)


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _line(lines, label):
    return next(line for line in lines if line.label == label)


@pytest.fixture
def lote(model):
    """Lote 10 × 30 (300 m²); casa 8 × 10 (Sala) com varanda 2 × 8."""
    model.commit(terrain.create_terrain(model.doc, boundary=_rect(0, 0, 10, 30)))
    model.sala = _space(model, _rect(0, 0, 8, 10), "Sala")
    model.varanda = _space(model, _rect(0, 10, 8, 12), "Varanda")
    return model


def test_pl05_indices_e_memoria(lote):
    doc = lote.doc
    lines = la.compute(doc)
    assert _line(lines, "Área construída total").area == pytest.approx(96.0)
    nc = _line(lines, "Área não computável")
    assert nc.area == pytest.approx(16.0) and nc.spaces == [lote.varanda.GlobalId]
    assert "Varanda 16,00 (varanda)" in nc.memo  # regra do perfil Genérico pelo nome
    assert _line(lines, "Área computável").area == pytest.approx(80.0)
    assert _line(lines, "Área do terreno (levantamento)").area == pytest.approx(300.0)
    assert _line(lines, "Projeção da edificação").area == pytest.approx(96.0)
    assert _line(lines, "Área livre").area == pytest.approx(204.0)
    to = _line(lines, la.INDICES["TO"])
    ca = _line(lines, la.INDICES["CA"])
    assert to.index == "32,00 %" and ca.index == la.num(80 / 300)
    assert ca.memo.startswith("computável 80,00 / terreno (levantamento) 300,00")
    assert to.ok is None and to.limit is None  # sem limites do zoneamento
    # A memória de cada pavimento lista os ambientes e a conta.
    built = _line(lines, "Área construída: Térreo")
    assert built.area == pytest.approx(96.0)
    item = _line(lines, iv.LABEL["A_CONSTRUIR"])
    assert set(item.spaces) == {lote.sala.GlobalId, lote.varanda.GlobalId}
    assert item.memo == "01 Sala 80,00 + 02 Varanda 16,00 = 96,00"


def test_pl05b_lote_escritura_e_limites(lote):
    doc = lote.doc
    check_history(lote, lambda: lote.commit(la.edit_lot(doc, deed_area=320, to_max=0.3,
                                                         ca_max=0.2, tp_min=0.1)))
    assert la.edit_lot(doc, deed_area=320).ops == []
    assert la.read_lot(doc) == {"deed_area": 320.0, "to_max": 0.3, "ca_max": 0.2,
                                "tp_min": 0.1}
    values = ue.get_pset(doc.ifc.by_type("IfcSite")[0], la.LOT_PSET, should_inherit=False)
    assert values["Parametros"]
    lines = la.compute(doc)
    assert _line(lines, "Área do terreno (escritura)").area == pytest.approx(320.0)
    to = _line(lines, la.INDICES["TO"])
    assert to.index == "30,00 %" and to.ok is True and to.limit == "máx. 30,00 %"
    ca = _line(lines, la.INDICES["CA"])
    assert ca.ok is False and "não atende" in ca.memo and "escritura" in ca.memo
    tp = _line(lines, la.INDICES["TP"])
    assert tp.ok is False and tp.index == "0,00 %"
    # Jardim permeável (regra do perfil) faz a TP atender.
    _space(lote, _rect(0, 20, 10, 30), "Jardim")
    lines = la.compute(doc)
    assert _line(lines, "Área permeável").area == pytest.approx(100.0)
    assert _line(lines, la.INDICES["TP"]).ok is True
    assert _line(lines, "Área construída total").area == pytest.approx(96.0)
    # Apagar um campo; valores fora da faixa são recusados.
    lote.commit(la.edit_lot(doc, deed_area=None))
    assert la.read_lot(doc)["deed_area"] is None
    with pytest.raises(OpError):
        la.edit_lot(doc, to_max=1.5)
    with pytest.raises(OpError):
        la.edit_lot(doc, deed_area=-1)
    with pytest.raises(OpError):
        la.edit_lot(doc, frente=10)


def test_pl05c_classificacao_no_ambiente(lote):
    doc = lote.doc
    state = spaces.read_state(lote.varanda)
    assert la.classify(municipal.current(doc), state, 16.0) == (
        "NAO_COMPUTAVEL", "varanda", "perfil")
    check_history(lote, lambda: lote.commit(ac.edit_element(
        doc, lote.varanda, area_class="COMPUTAVEL")))
    values = ue.get_pset(lote.varanda, spaces.AREA_PSET, should_inherit=False)
    assert values["Classificacao"] == "COMPUTAVEL"
    lines = la.compute(doc)
    assert _line(lines, "Área não computável").area == pytest.approx(0.0)
    assert _line(lines, "Área computável").area == pytest.approx(96.0)
    # Motivo próprio; voltar à regra do perfil apaga o Pset.
    lote.commit(ac.edit_element(doc, lote.varanda, area_class="NAO_COMPUTAVEL",
                                area_reason="sacada em balanço"))
    assert "(sacada em balanço)" in _line(la.compute(doc), "Área não computável").memo
    lote.commit(ac.edit_element(doc, lote.varanda, area_class=None, area_reason=None))
    assert not ue.get_pset(lote.varanda, spaces.AREA_PSET, should_inherit=False)
    with pytest.raises(OpError):
        lote.commit(ac.edit_element(doc, lote.varanda, area_class="QUALQUER"))
    # Descoberta: fora da área construída e da projeção.
    lote.commit(ac.edit_element(doc, lote.varanda, area_class="DESCOBERTA"))
    lines = la.compute(doc)
    assert _line(lines, "Área descoberta").area == pytest.approx(16.0)
    assert _line(lines, "Projeção da edificação").area == pytest.approx(80.0)


def test_pl05d_por_situacao_com_paredes(model):
    """Paredes existentes sem ambiente: a área toda é existente; uma ampliação a construir
    e um anexo a demolir, que aparece mas não soma."""
    doc = model.doc
    model.commit(cmd.create_rectangle(doc, model.type14, model.terreo, (0, 0), (5, 4)))
    existing = [w.GlobalId for w in doc.ifc.by_type("IfcWall")]
    model.commit(iv.set_situation(doc, existing, "EXISTENTE"))
    old = set(existing)
    model.commit(cmd.create_rectangle(doc, model.type14, model.terreo, (10, 0), (13, 3)))
    annex = [w.GlobalId for w in doc.ifc.by_type("IfcWall") if w.GlobalId not in old]
    model.commit(iv.set_situation(doc, annex, "A_DEMOLIR"))
    old |= set(annex)
    model.commit(cmd.create_rectangle(doc, model.type14, model.terreo, (0, 6), (4, 9)))
    rings = rooms.building_rings(doc, model.terreo)
    areas = sorted(abs(clip.signed_area(r)) for r in rings)
    small, middle, big = areas
    lines = la.compute(doc)
    assert _line(lines, iv.LABEL["EXISTENTE"]).area == pytest.approx(big)
    assert _line(lines, iv.LABEL["A_CONSTRUIR"]).area == pytest.approx(middle)
    assert _line(lines, "A demolir (não soma)").area == pytest.approx(small)
    assert _line(lines, "Área construída: Térreo").area == pytest.approx(big + middle)
    assert _line(lines, "Projeção da edificação").area == pytest.approx(big + middle)
    assert _line(lines, "Área construída: Térreo").memo == \
        (f"a construir {la.num(middle)} + existente (manter) {la.num(big)} = "
         f"{la.num(big + middle)}")
    # Sem terreno: os índices pedem a área do terreno.
    assert "sem a área do terreno" in _line(lines, la.INDICES["TO"]).memo


def test_pl05e_perfil_piscina_e_tabela(lote, tmp_path):
    doc = lote.doc
    jacarei = next(p for p in municipal.builtin() if p["id"] == "sp-jacarei")
    lote.commit(municipal.set_profile(doc, jacarei))
    pool = _space(lote, _rect(1, 14, 5, 18), "Piscina")
    lines = la.compute(doc)
    apart = _line(lines, "Fora do total: piscina")
    assert apart.area == pytest.approx(16.0) and apart.spaces == [pool.GlobalId]
    assert _line(lines, "Área construída total").area == pytest.approx(96.0)
    # Regras inválidas no perfil são recusadas.
    bad = copy.deepcopy(jacarei)
    bad["quadro_de_areas"]["regras"] = [{"nomes": ["Varanda"], "classe": "XX"}]
    with pytest.raises(OpError):
        municipal.validate(bad)
    # Tabela "Quadro de áreas (projeto legal)": linhas fixas, memória na última coluna.
    tx = lote.commit(tb.create_table(doc, "legal_areas"))
    table = doc.get(tx.ops[0].id)
    result = tb.compute(doc, table)
    assert [c.field for c in result.columns] == list(tb.LEGAL_COLUMNS)
    row = next(r for r in result.rows if r.cells[0] == "Área não computável")
    assert row.kind == "total" and row.elements == [lote.varanda.GlobalId]
    assert row.memo == row.cells[-1] and "Varanda" in row.memo
    path = tmp_path / "quadro.csv"
    export.write_csv(str(path), result)
    text = path.read_text(encoding="utf-8-sig")
    assert "Memória de cálculo" in text and "Fora do total: piscina;16,00" in text
    # Trocar a categoria de outra tabela para o quadro ajusta a definição.
    tx = lote.commit(tb.create_table(doc, "blank", "walls"))
    lote.commit(tb.edit_table(doc, tx.ops[0].id, category=tb.LEGAL))
    state = tb.read_state(doc.get(tx.ops[0].id))
    assert [c["field"] for c in state["columns"]] == list(tb.LEGAL_COLUMNS)
