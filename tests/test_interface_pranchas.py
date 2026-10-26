# SPDX-License-Identifier: GPL-3.0-or-later
"""Pranchas na interface e PDF (spec/ui 15 §5, §6: PR02, PR05, PR06), com o Qt sem tela."""

import os
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest

from brasbim.core.annotations import commands as ac
from brasbim.core.drawings import sheets
from brasbim.core.walls import commands as cmd


def _casa(window):
    s = window.session
    s.run(lambda: cmd.create_rectangle(s.doc, window.toolbox.tools["wall"].options.type,
                                       s.storey, (0, 0), (6, 4)))
    s.run(lambda: ac.create_view(s.doc, "section", (3, -1), (3, 5), "left"))


def test_prancha_pelo_painel_e_aba(window):
    s = window.session
    _casa(window)
    window.project.add_sheet({})
    (sheet,) = sheets.all_sheets(s.doc)
    tab = window.sheet_views[sheet.GlobalId]
    assert window.tabs.currentWidget() is tab
    assert window.project.sheets.count() == 1
    s.select([sheet.GlobalId])
    window.properties._rebuild()
    assert window.properties.groups[0].title == "Prancha 01"
    s.run(lambda: sheets.add_to_sheet(s.doc, sheet, {"kind": "plan",
                                                     "storey": s.storey.GlobalId}))
    view = next(v for v in s.doc.ifc.by_type("IfcAnnotation") if v.ObjectType == "VistaDeCorte")
    s.run(lambda: sheets.add_to_sheet(s.doc, sheet, {"kind": "view", "view": view.GlobalId}))
    tab.resize(900, 650)
    tab.fit()
    tab.grab()
    assert len(tab.rects) == 2
    # PR02: a planta mede 120 mm na largura do papel
    assert tab.rects[0].width() / tab.zoom == pytest.approx(120, abs=1)


def test_pr06_arrastar_vista(window):
    s = window.session
    _casa(window)
    window.project.add_sheet({})
    (sheet,) = sheets.all_sheets(s.doc)
    s.run(lambda: sheets.add_to_sheet(s.doc, sheet, {"kind": "plan",
                                                     "storey": s.storey.GlobalId}))
    tab = window.sheet_views[sheet.GlobalId]
    tab.resize(900, 650)
    tab.fit()
    tab.grab()
    before = sheets.read_state(sheet)["views"][0]["at"]
    start = tab.rects[0].center().toPoint()
    QTest.mousePress(tab, Qt.LeftButton, Qt.NoModifier, start)
    QTest.mouseMove(tab, start + QPointF(40, 0).toPoint())
    QTest.mouseRelease(tab, Qt.LeftButton, Qt.NoModifier, start + QPointF(40, 0).toPoint())
    after = sheets.read_state(sheet)["views"][0]["at"]
    assert after[0] == pytest.approx(before[0] + 40 / tab.zoom, abs=0.5)
    assert s.history.undo_stack[-1].ops[0].op == "sheet.edit"


def test_pr05_pdf(window, tmp_path):
    s = window.session
    _casa(window)
    window.project.add_sheet({})
    window.project.add_sheet({})
    first = sheets.all_sheets(s.doc)[0]
    s.run(lambda: sheets.add_to_sheet(s.doc, first, {"kind": "plan",
                                                     "storey": s.storey.GlobalId}))
    path = tmp_path / "pranchas.pdf"
    assert window.export_pdf(str(path)) == 2
    data = path.read_bytes()
    assert data.startswith(b"%PDF")
    boxes = re.findall(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", data)
    assert len(boxes) == 2
    for w, h in boxes:  # 420 × 297 mm em pontos (1 pt = 25,4/72 mm)
        assert float(w) * 25.4 / 72 == pytest.approx(420, abs=0.5)
        assert float(h) * 25.4 / 72 == pytest.approx(297, abs=0.5)
