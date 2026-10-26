# SPDX-License-Identifier: GPL-3.0-or-later
"""Folhas mestras na interface (spec/ui 26 §6: FM05, FM06), com o Qt sem tela."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QComboBox

from brasbim.core.drawings import masters, sheets
from brasbim.ui import master_editor as me


def _field_combo(panel, name):
    for group in panel.groups:
        for label, widget in group.rows:
            if label == name and isinstance(widget, QComboBox):
                return widget
    raise LookupError(name)


def test_fm05_nova_prancha_com_folha_mestra(window, tmp_path):
    s = window.session
    gid = window.project.add_master("A2", "portrait")
    assert gid in window.master_views
    assert window.project.masters.count() == 1
    # o quadro de nova prancha lista a folha mestra e os formatos padrão
    dialog = me.NewSheetDialog(s.doc)
    texts = [dialog.master.itemText(i) for i in range(dialog.master.count())]
    assert texts[0].startswith("A2 vertical") and "Padrão A3 horizontal" in texts
    dialog.title.setText("Planta baixa")
    assert dialog.choice() == {"title": "Planta baixa", "master": gid}
    sheet_gid = window.project.add_sheet(dialog.choice())
    sheet = s.doc.get(sheet_gid)
    assert sheets.read_state(sheet)["master"] == gid
    assert sheets.paper_of(s.doc, sheets.read_state(sheet)) == (420.0, 594.0)
    # no painel de propriedades a folha mestra se troca; formato só sem folha mestra
    s.select([sheet_gid])
    window.properties._rebuild()
    combo = _field_combo(window.properties, "Folha mestra")
    with pytest.raises(LookupError):
        _field_combo(window.properties, "Formato")
    combo.setCurrentIndex(combo.findData(""))
    assert sheets.read_state(sheet)["master"] is None
    window.properties._rebuild()
    assert _field_combo(window.properties, "Formato") is not None
    s.run(lambda: sheets.edit_sheet(s.doc, sheet, master=gid))
    # PDF com o papel da folha mestra
    from PySide6.QtPdf import QPdfDocument

    from brasbim.ui import paper

    path = str(tmp_path / "f.pdf")
    paper.export_pdf(path, s.doc, [sheet])
    pdf = QPdfDocument()
    pdf.load(path)
    size = pdf.pagePointSize(0)
    assert (size.width() * 25.4 / 72, size.height() * 25.4 / 72) == (
        pytest.approx(420, abs=1), pytest.approx(594, abs=1))


def test_fm06_editar_o_carimbo(window):
    s = window.session
    gid = window.project.add_master("A3", "landscape")
    editor = window.master_views[gid]
    count = len(masters.read_state(s.doc.get(gid))["items"])
    canvas = editor.canvas
    # linha: dois cliques e Enter; o ponto atrai para a grade de 1 mm
    editor.set_tool("line")
    assert me.snap_point((30.4, 40.6), []) == (30.0, 41.0)
    canvas.press((30.0, 41.0))
    canvas.press((80.0, 41.0))
    canvas.finish_line()
    items = masters.read_state(s.doc.get(gid))["items"]
    assert len(items) == count + 1 and items[-1]["points"] == [[30.0, 41.0], [80.0, 41.0]]
    # a ponta da linha atrai
    assert me.snap_point((80.9, 42.2), items) == (80.0, 41.0)
    # retângulo por dois cantos
    editor.set_tool("rect")
    canvas.press((30.0, 50.0))
    canvas.press((60.0, 70.0))
    items = masters.read_state(s.doc.get(gid))["items"]
    assert items[-1]["closed"] and len(items[-1]["points"]) == 4
    # texto com campo
    assert editor.add_text((35.0, 55.0), "Obra: {projeto}")
    items = masters.read_state(s.doc.get(gid))["items"]
    assert items[-1]["text"] == "Obra: {projeto}"
    # selecionar, mover, editar texto e apagar
    editor.set_tool("select")
    index = me.pick((36.0, 56.0), items)
    assert index == len(items) - 1
    canvas.press((36.0, 56.0))
    assert canvas.selected == {index}
    assert editor.move_selected(10, -5)
    assert masters.read_state(s.doc.get(gid))["items"][index]["at"] == [45.0, 50.0]
    assert editor.edit_text(index, {"text": "{titulo}", "bold": True})
    assert masters.read_state(s.doc.get(gid))["items"][index]["bold"] is True
    assert editor.delete_selected()
    assert len(masters.read_state(s.doc.get(gid))["items"]) == count + 2
    s.history.undo()
    assert len(masters.read_state(s.doc.get(gid))["items"]) == count + 3
    # papel e margens
    assert editor.edit_paper({"format": masters.CUSTOM, "size": [500, 300],
                              "margins": [10, 10, 10, 10]})
    state = masters.read_state(s.doc.get(gid))
    assert masters.paper_size(state) == (500.0, 300.0)
    assert window.tabs.tabText(window.tabs.indexOf(editor)).startswith("Folha mestra:")
    editor.grab()
    # excluir a folha mestra fecha a aba
    window.project.masters.setCurrentRow(0)
    window.project.delete_master()
    assert gid not in window.master_views
