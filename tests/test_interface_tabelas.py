# SPDX-License-Identifier: GPL-3.0-or-later
"""Tabelas na interface (spec/ui 17 §5, §7: TB10), com o Qt sem tela."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QCheckBox, QWidget

from brasbim.core.fillings import commands as fc
from brasbim.core.quantities import tables
from brasbim.core.walls import commands as cmd


def _casa(window):
    s = window.session
    s.run(lambda: cmd.create_rectangle(s.doc, window.toolbox.tools["wall"].options.type,
                                       s.storey, (0, 0), (6, 4)))
    left, _, _, bottom = s.doc.ifc.by_type("IfcWall")
    door_type = next(t for t in s.doc.ifc.by_type("IfcDoorType") if t.Name.startswith("P1"))
    window_type = next(t for t in s.doc.ifc.by_type("IfcWindowType")
                       if t.Name.startswith("J1"))
    s.run(lambda: fc.create_door(s.doc, door_type, bottom, 1.0))
    s.run(lambda: fc.create_window(s.doc, window_type, left, 0.3))
    s.run(lambda: fc.create_window(s.doc, window_type, left, 2.0))


def test_tb10_nova_tabela_aba_e_selecao(window):
    s = window.session
    _casa(window)
    gid = window.project.add_table("fillings")
    tab = window.table_views[gid]
    assert window.tabs.currentWidget() is tab
    assert window.tabs.tabText(window.tabs.indexOf(tab)) == "Quadro de esquadrias"
    assert window.project.tables.count() == 1
    codes = [tab.grid.item(r, 0).text() for r in range(tab.grid.rowCount())]
    assert codes[0] == "J1" and codes[1].startswith("P1") and codes[2] == "Total"
    assert tab.grid.item(0, 5).text() == "2"
    # clicar numa linha seleciona os elementos dela
    tab._clicked(0)
    assert s.selection == set(tab.result.rows[0].elements)
    assert {s.doc.find(g).is_a() for g in s.selection} == {"IfcWindow"}
    # com a aba à frente, o painel é o da tabela
    window.properties._rebuild()
    assert window.properties.groups[0].title == "Tabela: Quadro de esquadrias"
    # marcar uma coluna no painel é uma transação
    row = window.properties.findChild(QWidget, "coluna_area")
    row.findChild(QCheckBox).setChecked(True)
    assert s.history.undo_stack[-1].label == "Editar tabela"
    assert [c["field"] for c in tables.read_state(s.doc.find(gid))["columns"]][-1] == "area"
    assert tab.grid.columnCount() == 7
    window.undo()
    assert tab.grid.columnCount() == 6
    # a aba acompanha o modelo
    s.run(lambda: cmd.create_storey(s.doc, "Superior", 2.8))
    assert tab.grid.rowCount() == 3


def test_tb10_exportar_e_excluir(window, tmp_path):
    s = window.session
    _casa(window)
    window.export_table(path=str(tmp_path / "x.csv"))  # sem aba de tabela: recusa
    assert s.messages[-1]["level"] == "recusa"
    gid = window.project.add_table("areas")
    out = window.export_table(path=str(tmp_path / "areas.csv"))
    assert out and (tmp_path / "areas.csv").read_bytes().startswith(b"\xef\xbb\xbf")
    out = window.export_table(path=str(tmp_path / "areas.xlsx"))
    assert out and (tmp_path / "areas.xlsx").read_bytes()[:2] == b"PK"
    window.project.tables.setCurrentRow(0)
    window.project.delete_table()
    assert gid not in window.table_views
    assert window.project.tables.count() == 0
    assert window.properties.active_table is None


def test_tb10_estrutura_cria_tres(window):
    window.project.add_table("structure")
    assert len(window.table_views) == 3
    assert window.tabs.tabText(window.tabs.currentIndex()) == "Estrutura: pilares"
