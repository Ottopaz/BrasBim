# SPDX-License-Identifier: GPL-3.0-or-later
"""Projeto legal, etapa 2 (spec/ui/31-projeto-legal.md §4 e §13), na interface: diálogo
do perfil municipal (PL04) e hachura da situação em Imprimir em preto (PL10)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QImage, QPainter

from brasbim.core import intervention as iv
from brasbim.core import municipal, pens, storeys
from brasbim.core.drawings import sheets
from brasbim.core.walls import commands as cmd
from brasbim.ui import paper
from brasbim.ui.municipal_dialog import PROJECT

BLUE = "#00AAFF"


def _walls(window):
    s = window.session
    tx = cmd.create_rectangle(s.doc, s.doc.ifc.by_type("IfcWallType")[0], s.storey,
                              (0, 0), (6, 4))
    s.run(tx)
    return [s.doc.get(op.id) for op in tx.ops if op.op == "wall.create"]


def _dark(image: QImage) -> int:
    count = 0
    for y in range(0, image.height(), 2):
        for x in range(0, image.width(), 2):
            if QColor(image.pixel(x, y)).lightness() < 60:
                count += 1
    return count


def test_pl04_dialogo_do_perfil(window):
    s = window.session
    walls = _walls(window)
    s.run(iv.set_situation(s.doc, [walls[0].GlobalId], "EXISTENTE"))

    def araras(dialog):
        assert dialog.choice.itemData(0) == "generico"  # sem cópia no projeto
        dialog.choose("sp-araras")
        assert "Araras" in dialog.source.text() and "A regularizar" in dialog.source.text()
        assert dialog.scales["plantas"].currentData() == 100
        dialog.choose_color("A_CONSTRUIR", BLUE)
        dialog.set_mark("EXISTENTE", hachura="cross")
        dialog.notes.setPlainText("Nota um\n\nNota dois")

    assert window.edit_municipal(apply=araras)
    profile = municipal.read(s.doc)
    assert profile["nome"] == "Araras/SP" and profile["notas"] == ["Nota um", "Nota dois"]
    assert profile["cores"]["EXISTENTE"]["hachura"] == "cross"
    assert window.ctx.plan.colors[walls[1].GlobalId] == BLUE
    assert storeys.stored_scale(s.storey) == 100
    # Abrir de novo mostra a cópia do projeto primeiro; desfazer volta tudo numa vez.
    def check(dialog):
        assert dialog.choice.itemData(0) == PROJECT
        assert dialog.profile["cores"]["A_CONSTRUIR"]["cor"] == BLUE

    window.edit_municipal(apply=check)
    s.undo()
    assert municipal.read(s.doc) is None
    assert storeys.stored_scale(s.storey) == storeys.DEFAULT_SCALE
    assert window.ctx.plan.colors[walls[1].GlobalId] == iv.GENERIC_COLORS["A_CONSTRUIR"]
    assert any(a.text() == "Perfil municipal" for m in window.menuBar().actions()
               for a in m.menu().actions())


def test_pl10_hachura_em_preto_na_prancha(window):
    s = window.session
    walls = _walls(window)
    s.run(iv.set_situation(s.doc, [w.GlobalId for w in walls], "EXISTENTE"))
    cfg = pens.config(s.doc)
    cfg["tables"][0]["print_black"] = True
    s.run(lambda: pens.edit_config(s.doc, cfg))
    s.run(lambda: sheets.create_sheet(s.doc))
    (sheet,) = sheets.all_sheets(s.doc)
    s.run(lambda: sheets.add_to_sheet(s.doc, sheet, {"kind": "plan",
                                                    "storey": s.storey.GlobalId}))

    def render():
        w, h = sheets.paper_of(s.doc, sheets.read_state(sheet))
        image = QImage(int(w * 2), int(h * 2), QImage.Format_RGB32)
        image.fill(QColor("white"))
        painter = QPainter(image)
        paper.render_sheet(painter, s.doc, s.doc.get(sheet.GlobalId), 2.0, QPointF(0, 0),
                           1.0, "d")
        painter.end()
        return image

    solid = _dark(render())  # Genérico: existente = cheia
    profile = municipal.current(s.doc)
    profile["cores"]["EXISTENTE"]["hachura"] = "none"
    s.run(lambda: municipal.set_profile(s.doc, profile))
    empty = _dark(render())
    assert solid - empty > 300  # a mancha cheia das paredes (o carimbo conta nos dois)
