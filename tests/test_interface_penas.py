# SPDX-License-Identifier: GPL-3.0-or-later
"""Tabela de penas na interface (spec/ui 27 §6: PN02, PN03, PN04), com o Qt sem tela."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QImage, QPainter

from brasbim.core import pens
from brasbim.core.drawings import saved_views as sv
from brasbim.core.drawings import sheets
from brasbim.core.walls import commands as cmd
from brasbim.ui import paper

RED = "#FF0000"


def _casa(window):
    s = window.session
    s.run(lambda: cmd.create_rectangle(s.doc, window.toolbox.tools["wall"].options.type,
                                       s.storey, (0, 0), (6, 4)))


def _reddish(image: QImage) -> int:
    count = 0
    for y in range(0, image.height(), 2):
        for x in range(0, image.width(), 2):
            c = QColor(image.pixel(x, y))
            if c.red() > 180 and c.green() < 90 and c.blue() < 90:
                count += 1
    return count


def _red_cut(dialog):
    """No quadro: pena 5 (corte) em vermelho e 0,7 mm."""
    dialog.choose_color("5", RED)
    dialog.set_pen("5", weight=0.7)


def test_pn04_quadro_e_menu(window):
    s = window.session
    _casa(window)
    assert window.edit_pens(apply=_red_cut)
    table = pens.table(pens.config(s.doc), None)
    assert table["pens"]["5"] == {"color": RED, "weight": 0.7, "note": "grossa (corte)"}
    assert window.plan.pens.color("cut") == RED
    # PN02: a planta pinta as paredes cortadas com a pena
    image = window.plan.grab().toImage()
    assert _reddish(image) > 20
    # categorias: as cotas passam para a pena 9 numa tabela nova
    def new_table(dialog):
        dialog.new_table()
        dialog.rename_table("Prefeitura")
        dialog.set_category("dimension", "9")
        dialog.current.setChecked(True)

    assert window.edit_pens(apply=new_table)
    cfg = pens.config(s.doc)
    assert [t["name"] for t in cfg["tables"]] == ["Padrão", "Prefeitura"]
    assert pens.table(cfg, None)["name"] == "Prefeitura"
    assert window.plan.pens.pen("dimension").color == "#C0392B"
    # Exibir > Tabela de penas troca a tabela da janela
    window._fill_pens_menu()
    names = [a.text() for a in window.pens_menu.actions() if a.text()]
    assert names[:2] == ["Padrão", "Prefeitura"]
    assert window.use_pen_table("padrao")
    assert window.plan.pens.color("cut") == RED
    s.history.undo()
    assert pens.table(pens.config(s.doc), None)["name"] == "Prefeitura"


def test_pn03_vista_salva_e_impressao_em_preto(window):
    s = window.session
    _casa(window)
    window.edit_pens(apply=_red_cut)

    def black_copy(dialog):
        dialog.duplicate_table()
        dialog.black.setChecked(True)

    window.edit_pens(apply=black_copy)
    black = next(t["id"] for t in pens.config(s.doc)["tables"] if t["print_black"])
    red = window.save_view(name="Térreo vermelho")
    assert sv.read_state(s.doc.get(red))["pens"] == "padrao"
    window.close_saved_view()
    s.run(lambda: sv.edit_saved_view(s.doc, red, pens="padrao"))
    tx = sv.create_saved_view(s.doc, "Térreo P&B", "plan", storey=s.storey.GlobalId,
                              scale=50, pens=black)
    s.run(tx)
    mono = tx.ops[0].id
    s.run(lambda: sheets.create_sheet(s.doc))
    (sheet,) = sheets.all_sheets(s.doc)

    def render(gid):
        s.run(lambda: sheets.edit_sheet(s.doc, sheet, views=[]))
        s.run(lambda: sheets.add_to_sheet(s.doc, sheet, {"kind": "saved", "saved": gid}))
        w, h = sheets.paper_of(s.doc, sheets.read_state(sheet))
        image = QImage(int(w * 2), int(h * 2), QImage.Format_RGB32)
        painter = QPainter(image)
        paper.render_sheet(painter, s.doc, s.doc.get(sheet.GlobalId), 2.0, QPointF(0, 0),
                           1.0, "d")
        painter.end()
        return image

    assert _reddish(render(red)) > 20  # a vista leva a tabela dela
    assert _reddish(render(mono)) == 0  # imprimir em preto
    # abrir a vista salva troca a tabela da janela
    assert window.open_saved_view(mono)
    assert window.window_pen_table() == black
    window.close_saved_view()
    assert window.window_pen_table() == pens.config(s.doc)["current"]
