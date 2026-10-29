# SPDX-License-Identifier: GPL-3.0-or-later
"""Vistas salvas na interface (spec/ui 25 §7: VS06, VS07), com o Qt sem tela."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QMimeData, QPointF, Qt
from PySide6.QtGui import QDropEvent

from brasbim.core import display_layers as dl
from brasbim.core import storeys
from brasbim.core.annotations import commands as ac
from brasbim.core.drawings import saved_views as sv
from brasbim.core.drawings import sheets
from brasbim.core.walls import commands as cmd
from brasbim.ui import saved_views_ui


def _casa(window):
    s = window.session
    s.run(lambda: cmd.create_rectangle(s.doc, window.toolbox.tools["wall"].options.type,
                                       s.storey, (0, 0), (6, 4)))


def _layer(doc, name):
    return next(x["id"] for x in dl.read_config(doc)["layers"] if x["name"] == name)


def test_vs06_salvar_e_abrir_planta(window):
    s = window.session
    _casa(window)
    terreo = s.storey
    paredes = _layer(s.doc, "Paredes")
    button = window.project.save_view_button  # no canto das abas de vistas do painel
    assert button.isVisible() and button.parent() is not None
    window.set_view("split")  # lado a lado as abas das vistas somem; o botão fica
    assert button.isVisible()
    window.set_view("plan")
    # planta: camadas, escala do pavimento e opções da janela
    s.set_display(dl.Display(hidden=frozenset({paredes})))
    window.set_show_above(False)
    gid = window.save_view(name="Térreo sem paredes")
    state = sv.read_state(s.doc.get(gid))
    assert state["kind"] == "plan" and state["storey"] == terreo.GlobalId
    assert state["scale"] == 50 and state["options"]["show_above"] is False
    assert dl.display_of(state["layers"]).hidden == frozenset({paredes})
    assert window.project.saved.count() == 1
    assert window.saved_view_label.isVisibleTo(window)
    # a janela muda (outro pavimento, camadas, opções); abrir a vista devolve tudo
    window.close_saved_view()
    s.set_display(dl.Display())
    window.set_show_above(True)
    s.set_storey(s.doc.storeys()[-1] if s.doc.storeys()[-1] != terreo else terreo)
    s.run(lambda: sv.edit_saved_view(s.doc, gid, scale=100))
    assert window.open_saved_view(gid)
    assert s.storey == terreo
    assert s.display.hidden == frozenset({paredes})
    assert window.ctx.show_above is False
    assert storeys.scale(terreo) == 100 and storeys.stored_scale(terreo) == 50
    assert window.scale_combo.currentData() == 100
    # escolher outra escala com a vista aberta muda só a janela
    window.scale_combo.setCurrentIndex(window.scale_combo.findData(75))
    assert storeys.scale(terreo) == 75 and storeys.stored_scale(terreo) == 50
    # Atualizar com a janela regrava a escala
    assert window.update_saved_view(gid)
    assert sv.read_state(s.doc.get(gid))["scale"] == 75
    window.close_saved_view()
    assert storeys.scale(terreo) == 50


def test_vs06_salvar_3d_e_corte(window):
    s = window.session
    _casa(window)
    window.set_view("3d")
    window.view3d.camera.yaw = 0.5
    gid = window.save_view(name="3D frente")
    state = sv.read_state(s.doc.get(gid))
    assert state["kind"] == "3d" and state["camera"]["yaw"] == pytest.approx(0.5)
    window.view3d.camera.yaw = 2.0
    window.set_view("plan")
    assert window.open_saved_view(gid)
    assert window.tabs.currentWidget() is window.view3d
    assert window.view3d.camera.yaw == pytest.approx(0.5)
    # corte: escala da vista e aba do corte
    s.run(lambda: ac.create_view(s.doc, "section", (3, -1), (3, 5), "left"))
    view = next(v for v in s.doc.ifc.by_type("IfcAnnotation") if v.ObjectType == "VistaDeCorte")
    window.open_view(view.GlobalId)
    gid = window.save_view(name="Corte A")
    assert sv.read_state(s.doc.get(gid))["view"] == view.GlobalId
    s.run(lambda: sv.edit_saved_view(s.doc, gid, scale=25))
    assert window.open_saved_view(gid)
    tab = window.section_views[view.GlobalId]
    assert window.tabs.currentWidget() is tab and tab.scale_override == 25
    # aba que não é vista: avisa e não salva
    window.project.add_sheet({})
    assert window.save_view(name="x") is None


def test_vs07_por_na_prancha(window):
    s = window.session
    _casa(window)
    gid = window.save_view(name="Térreo")
    window.set_view("3d")
    gid3 = window.save_view(name="3D")
    window.project.add_sheet({})
    (sheet,) = sheets.all_sheets(s.doc)
    tab = window.sheet_views[sheet.GlobalId]
    tab.resize(900, 650)
    tab.fit()
    # botão direito no papel: "Pôr vista salva" com a lista
    menu = tab.context_menu(QPointF(300, 300), None)
    (sub,) = [a.menu() for a in menu.actions() if a.menu() is not None]
    assert [a.text() for a in sub.actions()] == ["3D", "Térreo"]
    next(a for a in sub.actions() if a.text() == "Térreo").trigger()
    (item,) = sheets.read_state(sheet)["views"]
    assert item["kind"] == "saved" and item["saved"] == gid
    assert item["at"] == pytest.approx(list(tab.to_paper(QPointF(300, 300))), abs=0.01)
    # arrastar da lista do painel para a prancha
    listing = window.project.saved
    row = next(i for i in range(listing.count())
               if listing.item(i).data(Qt.UserRole) == gid3)
    data = listing.mimeData([listing.item(row)])
    assert isinstance(data, QMimeData) and data.hasFormat(saved_views_ui.MIME)
    drop = QDropEvent(QPointF(600, 300), Qt.CopyAction, data, Qt.LeftButton, Qt.NoModifier)
    tab.dropEvent(drop)
    items = sheets.read_state(sheet)["views"]
    assert [it["saved"] for it in items] == [gid, gid3]
    # a vista 3D aparece com o tamanho dela (imagem ou o quadro de "sem OpenGL")
    tab.grab()
    assert tab.rects[1].width() / tab.zoom == pytest.approx(160, abs=0.5)
    menu = tab.context_menu(tab.rects[1].center(), 1)
    assert "Largura no papel" in [a.text() for a in menu.actions()]
    # pelo painel: Pôr na prancha ▸ e Excluir
    menu = window.project.saved_menu(gid)
    texts = [a.text() for a in menu.actions()]
    assert texts[:3] == ["Abrir", "Atualizar com a janela", "Renomear"]
    window.project.rename_saved_view(gid, "Planta do térreo")
    assert sv.read_state(s.doc.get(gid))["name"] == "Planta do térreo"
    s.run(lambda: sv.delete_saved_view(s.doc, gid))
    assert [it["saved"] for it in sheets.read_state(sheet)["views"]] == [gid3]
    assert window.project.saved.count() == 1
