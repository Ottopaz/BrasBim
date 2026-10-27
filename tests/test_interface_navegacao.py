# SPDX-License-Identifier: GPL-3.0-or-later
"""Painel Projeto com ícones e abas que fecham (spec/ui/32-navegacao-e-abas.md): NV01–NV03."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QIcon
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QTabBar

from brasbim.core.annotations import commands as ac
from brasbim.core.drawings import saved_views as sv
from brasbim.core.drawings import sheets, views
from brasbim.core.walls import commands as cmd


def _casa(window):
    s = window.session
    s.run(lambda: cmd.create_rectangle(s.doc, window.toolbox.tools["wall"].options.type,
                                       s.storey, (0, 0), (6, 4)))
    s.run(lambda: ac.create_view(s.doc, "section", (3, -1), (3, 5), "left"))
    s.run(lambda: ac.create_view(s.doc, "elevation", (-2, -2), (8, -2), "left"))
    s.run(lambda: ac.create_view(s.doc, "section", (-1, 2), (7, 2), "right"))
    return views.all_views(s.doc)


def _groups(tree):
    return {tree.topLevelItem(i).text(0): tree.topLevelItem(i)
            for i in range(tree.topLevelItemCount())}


def test_nv01_cortes_e_fachadas_em_grupos_com_icone(window):
    project = window.project
    assert project.views.topLevelItemCount() == 0  # grupo vazio não aparece
    made = _casa(window)
    groups = _groups(project.views)
    assert set(groups) == {"Cortes (2)", "Fachadas (1)"}
    for group in groups.values():
        assert not group.icon(0).isNull() and group.isExpanded()
        # aberto, o ícone não troca para a cor sobre o destaque (sumiria no fundo)
        on, off = (group.icon(0).pixmap(16, QIcon.Normal, state).toImage()
                   for state in (QIcon.On, QIcon.Off))
        assert on == off
        for j in range(group.childCount()):
            assert not group.child(j).icon(0).isNull()
    assert sorted(project.view_ids()) == sorted(v.GlobalId for v in made)
    # clique duplo abre a aba; clique simples seleciona o símbolo
    elevation = groups["Fachadas (1)"].child(0)
    project._select_view_item(elevation)
    assert window.session.selection == {elevation.data(0, Qt.UserRole)}
    project._open_view_item(elevation)
    assert window.tabs.currentWidget() is window.section_views[elevation.data(0, Qt.UserRole)]
    project._open_view_item(groups["Cortes (2)"])  # o grupo não abre nada
    assert len(window.section_views) == 1
    # grupo fechado continua fechado depois de atualizar
    groups["Cortes (2)"].setExpanded(False)
    project.refresh()
    assert not _groups(project.views)["Cortes (2)"].isExpanded()
    # ícones nas outras listas
    window.project.add_table("fillings")
    assert not project.tables.item(0).icon().isNull()


def test_nv02_prancha_mostra_os_desenhos_e_abre_a_origem(window):
    s = window.session
    made = _casa(window)
    window.project.add_sheet({})
    (sheet,) = sheets.all_sheets(s.doc)
    window.set_view("plan")
    saved = window.save_view(name="Térreo 1:100")
    assert saved
    window.close_saved_view()
    for item in ({"kind": "plan", "storey": s.storey.GlobalId},
                 {"kind": "view", "view": made[0].GlobalId},
                 {"kind": "saved", "saved": saved}):
        s.run(lambda item=item: sheets.add_to_sheet(s.doc, sheet, item))
    top = window.project.sheets.topLevelItem(0)
    names = [top.child(j).text(0) for j in range(top.childCount())]
    assert names == [f"Planta · {s.storey.Name}", views.read_state(made[0])["name"],
                     "Térreo 1:100"]
    assert all(not top.child(j).icon(0).isNull() for j in range(top.childCount()))
    project = window.project
    project._open_sheet_item(top)
    assert window.tabs.currentWidget() is window.sheet_views[sheet.GlobalId]
    project._open_sheet_item(top.child(1))
    assert window.tabs.currentWidget() is window.section_views[made[0].GlobalId]
    project._open_sheet_item(top.child(0))
    assert window.tabs.currentWidget() is window.plan
    project._open_sheet_item(top.child(2))
    assert window.active_saved_view == saved
    window.close_saved_view()
    # prancha aberta (expandida) continua aberta; excluir pelo desenho exclui a prancha
    top = project.sheets.topLevelItem(0)  # o painel foi refeito ao abrir a vista
    top.setExpanded(True)
    project.refresh()
    top = project.sheets.topLevelItem(0)
    assert top.isExpanded()
    project.sheets.setCurrentItem(top.child(0))
    project.delete_sheet()
    assert sheets.all_sheets(s.doc) == []
    s.undo()
    # desenho cuja origem sumiu não aparece
    s.run(lambda: sv.delete_saved_view(s.doc, s.doc.get(saved)))
    top = project.sheets.topLevelItem(0)
    assert [top.child(j).text(0) for j in range(top.childCount())] == names[:2]


def test_nv03_abas_fecham(window):
    s = window.session
    made = _casa(window)
    window.project.add_sheet({})
    (sheet,) = sheets.all_sheets(s.doc)
    master = window.project.add_master("A3", "landscape")
    window.open_view(made[0].GlobalId)
    window.open_view(made[1].GlobalId)
    tabs, bar = window.tabs, window.tabs.tabBar()
    assert tabs.count() == 2 + 4
    # Planta e 3D sem o botão de fechar; as outras com
    for i in range(tabs.count()):
        fixed = tabs.widget(i) in (window.plan, window.view3d)
        button = bar.tabButton(i, QTabBar.RightSide) or bar.tabButton(i, QTabBar.LeftSide)
        assert (button is None) == fixed, tabs.tabText(i)
    # botão ×: fecha a folha mestra (o que foi editado já está no projeto)
    tabs.tabCloseRequested.emit(tabs.indexOf(window.master_views[master]))
    assert master not in window.master_views and tabs.count() == 5
    # clique do meio
    rect = bar.tabRect(tabs.indexOf(window.sheet_views[sheet.GlobalId]))
    QTest.mouseClick(bar, Qt.MiddleButton, Qt.NoModifier, rect.center())
    assert not window.sheet_views and tabs.count() == 4
    # Ctrl+W fecha a aba à frente; na planta, avisa e não fecha
    tabs.setCurrentWidget(window.section_views[made[1].GlobalId])
    assert window.close_tab()
    assert made[1].GlobalId not in window.section_views
    tabs.setCurrentWidget(window.plan)
    assert not window.close_tab() and tabs.count() == 3
    assert "sempre abertos" in s.messages[-1]["text"]
    # fechar todas deixa só a planta e o 3D; reabrir funciona
    window.open_sheet(sheet.GlobalId)
    window.close_tabs()
    assert tabs.count() == 2 and not window.section_views
    assert window.open_view(made[0].GlobalId) is tabs.currentWidget()
    # o lado a lado e a volta mantêm Planta e 3D sem o botão
    window.set_view("split")
    window.set_view("plan")
    for i in range(tabs.count()):
        if tabs.widget(i) in (window.plan, window.view3d):
            assert bar.tabButton(i, QTabBar.RightSide) is None
    assert {tabs.tabText(i) for i in range(tabs.count())} >= {"Planta", "3D"}
    assert bar.tabAt(QPoint(-5, -5)) == -1
    window.close_tabs()
