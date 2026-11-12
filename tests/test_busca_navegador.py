# SPDX-License-Identifier: GPL-3.0-or-later
"""Campo de busca no Navegador (spec/ui/53-busca-no-navegador.md): BN01–BN04."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from brasbim.core.annotations import commands as ac
from brasbim.core.drawings import sheets, views
from brasbim.ui.project_panel import matches, search_terms


def _vistas(window):
    s = window.session
    s.run(lambda: ac.create_view(s.doc, "section", (3, -1), (3, 5), "left"))
    s.run(lambda: ac.create_view(s.doc, "elevation", (-2, -2), (8, -2), "left"))
    s.run(lambda: ac.create_view(s.doc, "section", (-1, 2), (7, 2), "right"))
    return views.all_views(s.doc)


def _visible_texts(tree):
    out = []
    for i in range(tree.topLevelItemCount()):
        top = tree.topLevelItem(i)
        if not top.isHidden():
            out.append(top.text(0))
            out += [f"  {top.child(j).text(0)}" for j in range(top.childCount())
                    if not top.child(j).isHidden()]
    return out


def test_bn00_palavras_sem_acento_e_em_qualquer_ordem():
    assert search_terms("  Fáchada   SUL ") == ["fachada", "sul"]
    assert matches("Fachada Sul 1:50", search_terms("sul fachada"))
    assert matches("Térreo", search_terms("terreo"))
    assert not matches("Fachada Norte", search_terms("fachada sul"))
    assert matches("qualquer", [])


def test_bn01_filtra_cortes_e_fachadas(window):
    nav = window.project
    made = _vistas(window)
    elevation = next(v for v in made if views.read_state(v)["kind"] == "elevation")
    name = views.read_state(elevation)["name"]
    nav.show_section("views")
    assert nav.title.text() == "Cortes e fachadas (3)"
    for text in ("fachada", "FACHADA", "fáchada"):
        nav.search.setText(text)
        assert _visible_texts(nav.views) == ["Fachadas (1)", f"  {name}"]
        assert nav.title.text() == "Cortes e fachadas (1 de 3)"
    # o nome da vista também casa, sem o grupo
    nav.search.setText(name)
    assert [i.data(0, Qt.UserRole) for i in nav._matches_of("views")] == [elevation.GlobalId]
    nav.search.clear()
    assert len(_visible_texts(nav.views)) == 5  # 2 grupos + 3 vistas
    assert nav.title.text() == "Cortes e fachadas (3)"
    assert not nav.no_match.isVisible()


def test_bn02_busca_abre_e_fecha_o_que_abriu(window):
    s = window.session
    nav = window.project
    made = _vistas(window)
    for title in ("Plantas", "Cortes"):
        nav.add_sheet({"title": title})
    plantas, cortes = sheets.all_sheets(s.doc)
    view_name = views.read_state(made[0])["name"]
    s.run(lambda: sheets.add_to_sheet(s.doc, cortes, {"kind": "view",
                                                      "view": made[0].GlobalId}))
    s.run(lambda: sheets.add_to_sheet(s.doc, plantas, {"kind": "view",
                                                       "view": made[1].GlobalId}))
    nav.show_section("sheets")
    top = {nav.sheets.topLevelItem(i).data(0, Qt.UserRole): nav.sheets.topLevelItem(i)
           for i in range(nav.sheets.topLevelItemCount())}
    top[plantas.GlobalId].setExpanded(True)  # aberta pelo usuário
    assert not top[cortes.GlobalId].isExpanded()
    nav.search.setText(view_name)
    top = {nav.sheets.topLevelItem(i).data(0, Qt.UserRole): nav.sheets.topLevelItem(i)
           for i in range(nav.sheets.topLevelItemCount())}
    assert not top[cortes.GlobalId].isHidden() and top[cortes.GlobalId].isExpanded()
    assert top[plantas.GlobalId].isHidden()
    assert nav.title.text() == "Pranchas (1 de 2)"
    # nome da prancha casa: aparece com tudo o que está dentro
    nav.search.setText("plantas")
    item = top[plantas.GlobalId]
    assert not item.isHidden() and not item.child(0).isHidden()
    nav.search.clear()
    top = {nav.sheets.topLevelItem(i).data(0, Qt.UserRole): nav.sheets.topLevelItem(i)
           for i in range(nav.sheets.topLevelItemCount())}
    assert not top[cortes.GlobalId].isExpanded()  # a busca abriu, a busca fecha
    assert top[plantas.GlobalId].isExpanded()  # o usuário abriu, continua aberta


def test_bn03_secoes_refresh_aviso_enter_e_esc(window):
    s = window.session
    nav = window.project
    made = _vistas(window)
    nav.add_table("walls")
    nav.search.setText("fachada")
    nav.show_section("tables")  # o filtro vale na seção nova
    assert nav.search.text() == "fachada"
    assert nav.title.text() == "Tabelas (0 de 1)"
    assert nav.no_match.isVisible() and "fachada" in nav.no_match.text()
    assert nav.section_buttons["views"].toolTip() == "Cortes e fachadas (1 de 3)"
    # mudar o modelo refaz a lista e o filtro continua
    s.run(lambda: ac.create_view(s.doc, "elevation", (0, 8), (6, 8), "left"))
    QApplication.processEvents()
    assert nav.section_buttons["views"].toolTip() == "Cortes e fachadas (2 de 4)"
    window.undo()
    QApplication.processEvents()
    assert nav.section_buttons["views"].toolTip() == "Cortes e fachadas (1 de 3)"
    # Enter abre o primeiro achado
    nav.show_section("views")
    assert not nav.no_match.isVisible()
    QTest.keyClick(nav.search, Qt.Key_Return)
    elevation = next(v for v in made if views.read_state(v)["kind"] == "elevation")
    assert window.tabs.currentWidget() is window.section_views[elevation.GlobalId]
    # Esc limpa
    QTest.keyClick(nav.search, Qt.Key_Escape)
    assert nav.search.text() == "" and nav.title.text() == "Cortes e fachadas (3)"
    # projeto novo: a busca some
    nav.search.setText("corte")
    s.new()
    QApplication.processEvents()
    assert nav.search.text() == ""


def test_bn04_varias_palavras_e_ctrl_f(window):
    nav = window.project
    _vistas(window)
    nav.show_section("views")
    nav.search.setText("fachadas cortes")  # nenhum item tem as duas
    assert nav.shown_counts["views"] == 0 and nav.no_match.isVisible()
    window.project_dock.hide()
    window.find_in_navigator()
    QApplication.processEvents()
    assert window.project_dock.isVisible()
    assert nav.search.hasFocus() and nav.search.selectedText() == "fachadas cortes"
    action = next(a for a in window.findChildren(type(window.panels_menu.menuAction()))
                  if a.text() == "Buscar no Navegador")
    assert action.shortcut().toString() == "Ctrl+F"
