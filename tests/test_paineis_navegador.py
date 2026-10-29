# SPDX-License-Identifier: GPL-3.0-or-later
"""Painéis Pavimentos e Navegador (``spec/ui/40-reticencias-paineis-e-orientacao-3d.md``
§3 e §5, NV01–NV02). O resultado é conferido no modelo IFC."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QDockWidget

from brasbim.core.drawings import masters as masters_
from brasbim.core.drawings import sheets as sheets_
from brasbim.core.quantities import tables as tables_
from brasbim.ui.project_panel import SECTIONS


def test_nv01_paineis_pavimentos_e_navegador(window):
    s = window.session
    docks = {d.objectName(): d for d in window.findChildren(QDockWidget)}
    assert "projeto" not in docks
    assert docks["pavimentos"].windowTitle() == "Pavimentos"
    assert docks["navegador"].windowTitle() == "Navegador"
    panels = [a.text() for a in window.panels_menu.actions()]
    assert panels[:2] == ["Pavimentos", "Navegador"]
    # Pavimentos fica em cima do Navegador, à esquerda
    assert window.dockWidgetArea(window.storeys_dock) == window.dockWidgetArea(
        window.project_dock)
    assert window.storeys_dock.y() < window.project_dock.y()
    # a tabela cria e ativa pavimentos
    storeys = window.storeys
    count = len(s.doc.storeys())
    storeys.add_button.click()
    assert len(s.doc.storeys()) == count + 1
    top = max(s.doc.storeys(), key=lambda e: e.Elevation)
    assert s.storey_id == top.GlobalId and top.Elevation == pytest.approx(2.8 * count)
    assert storeys.table.rowCount() == count + 1
    storeys.table.cellClicked.emit(storeys.table.rowCount() - 1, 0)  # o mais baixo
    assert s.storey_id == min(s.doc.storeys(), key=lambda e: e.Elevation).GlobalId
    # as seis seções na ordem da spec, só com ícone e o nome na dica
    nav = window.project
    assert list(nav.section_buttons) == list(SECTIONS) == [
        "views", "saved", "sheets", "masters", "tables", "objects"]
    for key, button in nav.section_buttons.items():
        assert button.text() == "" and button.toolTip().startswith(SECTIONS[key][0])
    nav.section_buttons["tables"].click()
    assert nav.section == "tables" and nav.stack.currentWidget() is nav.pages["tables"]
    assert nav.title.text() == "Tabelas (0)"


def test_nv02_criar_abre_a_secao(window):
    s = window.session
    nav = window.project
    sheet = nav.add_sheet({"title": "Plantas"})
    assert sheets_.read_state(s.doc.get(sheet))["title"] == "Plantas"
    assert nav.section == "sheets" and nav.title.text() == "Pranchas (1)"
    master = nav.add_master("A3", "landscape")
    assert masters_.read_state(s.doc.get(master))["format"] == "A3"
    assert nav.section == "masters"
    assert nav.title.text() == f"Folhas mestras ({len(masters_.all_masters(s.doc))})"
    table = nav.add_table("walls")
    assert s.doc.get(table).is_a() and tables_.all_tables(s.doc)
    assert nav.section == "tables"
    assert nav.title.text() == f"Tabelas ({len(tables_.all_tables(s.doc))})"
    # desfazer atualiza a contagem
    window.undo()
    QApplication.processEvents()
    assert nav.title.text() == f"Tabelas ({len(tables_.all_tables(s.doc))})"
    assert nav.section_buttons["sheets"].toolTip() == "Pranchas (1)"
