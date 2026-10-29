# SPDX-License-Identifier: GPL-3.0-or-later
"""Projeto legal, etapa 3 (spec/ui/31-projeto-legal.md §5), na interface: classificação no
painel do ambiente, dados do lote no painel do quadro e memória de cálculo na aba (PL05)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QComboBox, QLineEdit
from test_interface import _field

from brasbim.core import terrain
from brasbim.core.annotations import commands as ac
from brasbim.core.annotations import spaces
from brasbim.core.quantities import legal_areas as la


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def test_pl05_quadro_na_interface(window):
    s = window.session
    s.run(lambda: terrain.create_terrain(s.doc, boundary=_rect(0, 0, 10, 30)))
    s.run(lambda: ac.create_space(s.doc, s.storey, _rect(0, 0, 8, 10), name="Sala"))
    tx = ac.create_space(s.doc, s.storey, _rect(0, 10, 8, 12), name="Varanda")
    s.run(tx)
    varanda = s.doc.get(tx.ops[0].id)
    # Painel do ambiente: a regra do perfil aparece; escolher outra é uma transação.
    s.select([varanda.GlobalId])
    window.properties._rebuild()
    combo = _field(window, "Classificação", QComboBox)
    assert combo.currentText() == "Pelo perfil: Não computável (varanda)"
    combo.setCurrentIndex(combo.findData("COMPUTAVEL"))
    assert spaces.read_state(varanda)["area_class"] == "COMPUTAVEL"
    window.undo()
    assert spaces.read_state(varanda)["area_class"] is None
    # Quadro do projeto legal: aba com a memória embaixo, coluna da memória escondida.
    gid = window.project.add_table("legal_areas")
    tab = window.table_views[gid]
    labels = [tab.grid.item(r, 0).text() for r in range(tab.grid.rowCount())]
    row = labels.index("Área não computável")
    assert tab.grid.item(row, 1).text() == "16,00"
    assert tab.grid.isColumnHidden(tab.grid.columnCount() - 1)
    assert tab.memo.isVisibleTo(tab)
    tab._clicked(row)
    assert "Varanda 16,00 (varanda)" in tab.memo.text()
    assert s.selection == {varanda.GlobalId}
    # Painel do quadro: dados do lote (TO em %), sem colunas nem filtro.
    window.properties._rebuild()
    assert [g.title for g in window.properties.groups] == [
        "Tabela: Quadro de áreas (projeto legal)", "Dados do lote"]
    field = _field(window, "TO máxima (%)", QLineEdit)
    field.setText("40")
    field.editingFinished.emit()
    assert la.read_lot(s.doc)["to_max"] == pytest.approx(0.4)
    labels = [tab.grid.item(r, 0).text() for r in range(tab.grid.rowCount())]
    to = labels.index(la.INDICES["TO"])
    assert tab.grid.item(to, 3).text() == "máx. 40,00 %"
    assert tab.grid.item(to, 4).text() == "sim"
