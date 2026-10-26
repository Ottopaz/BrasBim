# SPDX-License-Identifier: GPL-3.0-or-later
"""Seleção na prancha e na folha mestra, limite e moldura (spec/ui 29 §5): PS03–PS05."""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QWidget

from brasbim.core.annotations import commands as ac
from brasbim.core.drawings import masters, sheets
from brasbim.core.walls import commands as cmd
from brasbim.ui import master_editor as me
from brasbim.ui import paper


def _prancha(window):
    s = window.session
    s.run(lambda: cmd.create_rectangle(s.doc, window.toolbox.tools["wall"].options.type,
                                       s.storey, (0, 0), (6, 4)))
    s.run(lambda: ac.create_view(s.doc, "section", (3, -1), (3, 5), "left"))
    window.project.add_sheet({})
    (sheet,) = sheets.all_sheets(s.doc)
    view = next(v for v in s.doc.ifc.by_type("IfcAnnotation") if v.ObjectType == "VistaDeCorte")
    s.run(lambda: sheets.add_to_sheet(s.doc, sheet, {"kind": "plan",
                                                     "storey": s.storey.GlobalId}))
    s.run(lambda: sheets.add_to_sheet(s.doc, sheet, {"kind": "view", "view": view.GlobalId}))
    tab = window.sheet_views[sheet.GlobalId]
    tab.resize(900, 650)
    tab.fit()
    tab.grab()
    return sheet, tab


def _centro(tab, i):
    x0, y0, x1, y1 = sheets.item_rect(tab.session.doc, tab.items[i])
    return ((x0 + x1) / 2, (y0 + y1) / 2)


def test_ps03_gestos_na_prancha(window):
    s = window.session
    sheet, tab = _prancha(window)
    # clique soma; Shift tira; Esc limpa
    for i in (0, 1):
        tab.press(_centro(tab, i))
        tab.release(_centro(tab, i))
    assert tab.selected == {0, 1}
    tab.press(_centro(tab, 0), shift=True)
    tab.release(_centro(tab, 0), shift=True)
    assert tab.selected == {1}
    assert tab.escape() and tab.selected == set()
    # janela por dois cliques: para a direita só o inteiro, para a esquerda o que toca
    r0 = sheets.item_rect(s.doc, tab.items[0])
    a, b = (r0[0] - 2, r0[1] - 2), (r0[2] + 2, r0[3] + 2)
    tab.press(a)
    tab.release(a)
    tab.move(b)
    tab.press(b)
    tab.release(b)
    assert tab.selected == {0}
    tab.escape()
    meio = ((r0[0] + r0[2]) / 2, (r0[1] + r0[3]) / 2)
    tab.press(b)
    tab.release(b)
    tab.move(meio)
    tab.press(meio)
    tab.release(meio)
    assert 0 in tab.selected  # cruzamento: tocou o desenho
    tab.escape()
    # laço ao arrastar no vazio, para a direita, em volta do desenho 0
    tab.press(a)
    for q in ((r0[2] + 2, r0[1] - 2), b, (r0[0] - 2, r0[3] + 2)):
        tab.move(q)
    tab.release((r0[0] - 2, r0[3] + 2))
    assert tab.selected == {0}
    # realce: o cursor parado sobre o outro desenho
    tab.move(_centro(tab, 1))
    assert tab.selection.hover == 1
    tab.grab()
    # arrastar um desenho selecionado leva a seleção inteira numa transação
    tab.press(_centro(tab, 1))
    tab.release(_centro(tab, 1))
    before = [list(it["at"]) for it in tab.items]
    start = _centro(tab, 0)
    tab.press(start)
    tab.move((start[0] + 20, start[1]))
    tab.release((start[0] + 20, start[1]))
    after = [it["at"] for it in tab.items]
    assert [a[0] - b[0] for a, b in zip(after, before, strict=True)] == [
        pytest.approx(20), pytest.approx(20)]
    assert len(s.history.undo_stack[-1].ops) == 1
    # Delete pelo menu Editar tira da prancha os selecionados
    window.delete_selection()
    assert sheets.read_state(sheet)["views"] == []
    s.history.undo()
    assert len(sheets.read_state(sheet)["views"]) == 2


def test_ps03_mouse_e_cursor(window):
    _, tab = _prancha(window)
    assert tab.cursor().shape() == Qt.BitmapCursor
    center = tab.rects[0].center().toPoint()
    QTest.mouseClick(tab, Qt.LeftButton, Qt.NoModifier, center)
    assert tab.selected == {0}
    QTest.keyClick(tab, Qt.Key_Escape)
    assert tab.selected == set()
    # modo antigo (Editar > Modo de seleção): clique troca
    window.set_select_mode(False, save=False)
    QTest.mouseClick(tab, Qt.LeftButton, Qt.NoModifier, tab.rects[1].center().toPoint())
    QTest.mouseClick(tab, Qt.LeftButton, Qt.NoModifier, center)
    assert tab.selected == {0}
    window.set_select_mode(True, save=False)


def test_ps03_alca_do_limite(window):
    s = window.session
    _, tab = _prancha(window)
    tab.press(_centro(tab, 0))
    tab.release(_centro(tab, 0))
    handles = tab._handles()
    assert len(handles) == 8
    e = handles["e"]
    tab.press(e)
    tab.move((e[0] - 30, e[1]))
    tab.grab()  # o limite em andamento aparece
    tab.release((e[0] - 30, e[1]))
    item = tab.items[0]
    assert item.get("limit")
    x1 = sheets.item_rect(s.doc, item)[2]
    assert x1 == pytest.approx(e[0] - 30)
    menu = tab.context_menu(tab.at(_centro(tab, 0)), 0)
    fit = next(a for a in menu.actions() if a.text() == "Ajustar o limite ao desenho")
    assert fit.isEnabled()
    fit.trigger()
    assert "limit" not in tab.items[0]
    # Exibir > Limites dos desenhos na prancha
    window.set_sheet_limits(False, save=False)
    assert not tab.show_limits()
    tab.grab()
    window.set_sheet_limits(True, save=False)


def _pixel_cor(image, x, y, cor, raio=2):
    alvo = QColor(cor)
    for dx in range(-raio, raio + 1):
        for dy in range(-raio, raio + 1):
            c = image.pixelColor(x + dx, y + dy)
            if abs(c.red() - alvo.red()) + abs(c.green() - alvo.green()) \
                    + abs(c.blue() - alvo.blue()) < 60:
                return True
    return False


def test_ps05_moldura(window, tmp_path):
    s = window.session
    sheet, tab = _prancha(window)
    dialog = paper.FrameDialog(s.doc, None)
    assert dialog.pen.count() >= 12 and dialog.dash.count() == 3
    dialog.dash.setCurrentIndex(dialog.dash.findData("dashed"))
    dialog.pen.setCurrentIndex(dialog.pen.findData(9))  # vermelho
    assert dialog.values() == (True, "dashed", 9)
    assert tab.set_frame([0], *dialog.values())
    k = 4.0  # pixels por mm
    w, h = sheets.paper_of(s.doc, sheets.read_state(sheet))

    def render():
        image = QImage(round(w * k), round(h * k), QImage.Format_RGB32)
        image.fill(QColor("white"))
        painter = QPainter(image)
        paper.render_sheet(painter, s.doc, sheet, k, QPointF(0, 0), 1.0, "26/10/2026")
        painter.end()
        return image

    x0, _, x1, y1 = sheets.item_rect(s.doc, tab.items[0])
    image = render()
    # algum ponto do lado de cima da moldura sai em vermelho (tracejada: nem todos)
    top = round((h - y1) * k)
    xs = [round((x0 + t * (x1 - x0)) * k) for t in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7)]
    assert any(_pixel_cor(image, x, top, "#C0392B") for x in xs)
    assert not all(_pixel_cor(image, x, top, "#C0392B", raio=0)
                   for x in range(xs[0], xs[-1]))  # tem falhas: é tracejada
    # sem moldura: nada vermelho ali
    assert tab.set_frame([0], False, "dashed", 9)
    image = render()
    assert not any(_pixel_cor(image, x, top, "#C0392B") for x in xs)
    assert window.export_pdf(str(tmp_path / "moldura.pdf")) == 1


def test_ps04_folha_mestra(window):
    s = window.session
    gid = window.project.add_master("A3", "landscape")
    editor = window.master_views[gid]
    canvas = editor.canvas
    assert QWidget.cursor(canvas).shape() == Qt.BitmapCursor  # ``cursor`` é o ponto
    count = len(masters.read_state(s.doc.get(gid))["items"])
    editor.set_tool("line")
    for p in ((30.0, 40.0), (80.0, 40.0)):
        canvas.press(p)
    canvas.finish_line()
    for p in ((30.0, 60.0), (80.0, 60.0)):
        canvas.press(p)
    canvas.finish_line()
    editor.set_tool("select")
    a, b = count, count + 1
    # clique soma; Shift tira; Esc limpa
    canvas.press((50.0, 40.0))
    canvas.release((50.0, 40.0))
    canvas.press((50.0, 60.0))
    canvas.release((50.0, 60.0))
    assert canvas.selected == {a, b}
    canvas.press((50.0, 60.0), shift=True)
    canvas.release((50.0, 60.0), shift=True)
    assert canvas.selected == {a}
    QTest.keyClick(canvas, Qt.Key_Escape)
    assert canvas.selected == set()
    # janela de dois cliques para a esquerda pega a linha que toca
    canvas.press((90.0, 65.0))
    canvas.release((90.0, 65.0))
    canvas.move((50.0, 55.0))
    canvas.press((50.0, 55.0))
    canvas.release((50.0, 55.0))
    assert canvas.selected == {b}
    canvas.selection.escape()
    # laço para a direita em volta das duas
    canvas.press((25.0, 35.0))
    for q in ((85.0, 35.0), (85.0, 65.0), (25.0, 65.0)):
        canvas.move(q)
    canvas.release((25.0, 65.0))
    assert canvas.selected == {a, b}
    # realce e arrasto das duas numa transação, em mm inteiros
    canvas.selection.hover = None
    canvas.press((50.0, 40.0))
    canvas.move((60.2, 45.0))
    canvas.grab()
    canvas.release((60.2, 45.0))
    items = masters.read_state(s.doc.get(gid))["items"]
    assert items[a]["points"][0] == [40.0, 45.0] and items[b]["points"][0] == [40.0, 65.0]
    # Delete pelo menu Editar apaga os selecionados
    window.tabs.setCurrentWidget(editor)
    window.delete_selection()
    assert len(masters.read_state(s.doc.get(gid))["items"]) == count
    assert me.outlines([{"kind": "text", "at": [0, 0], "text": "A", "height": 2.5,
                         "align": "left"}])[0][0][1] is True
