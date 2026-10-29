# SPDX-License-Identifier: GPL-3.0-or-later
"""Sem reticências na interface (``spec/ui/40-reticencias-paineis-e-orientacao-3d.md`` §2
e §5, RT01)."""

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QApplication,
    QMenu,
    QTabBar,
)

from brasbim.ui.command_line import ALIASES_KEY, load_aliases


def _menu_texts(menu: QMenu, path=()):
    for action in menu.actions():
        if action.menu() is not None:
            yield from _menu_texts(action.menu(), (*path, action.text()))
        elif action.text():
            yield " > ".join((*path, action.text()))


def test_rt01_sem_reticencias_nos_menus_e_botoes(window):
    window.project.add_sheet({"title": "Plantas"})
    window.project.add_table("walls")
    QApplication.processEvents()
    texts = []
    for action in window.menuBar().actions():
        texts += _menu_texts(action.menu(), (action.text(),))
    for widget in (window, window.layers, window.library, window.team, window.assistant):
        texts += [b.text() for b in widget.findChildren(QAbstractButton)]
        texts += [b.toolTip() for b in widget.findChildren(QAbstractButton) if not b.text()]
        for menu in widget.findChildren(QMenu):
            texts += list(_menu_texts(menu))
        for bar in widget.findChildren(QTabBar):
            texts += [bar.tabText(i) for i in range(bar.count())]
    # menu do botão direito numa vista salva e nos objetos
    saved = window.save_view(name="Térreo")
    texts += list(_menu_texts(window.project.saved_menu(saved)))
    texts += list(_menu_texts(window.project._objects_menu()))
    assert texts
    assert [t for t in texts if "…" in t or "..." in t] == []


def test_rt01_qt_nao_corta_com_reticencias(window):
    for view in window.findChildren(QAbstractItemView):
        assert view.textElideMode() == Qt.ElideNone, view
    for bar in window.findChildren(QTabBar):
        assert bar.elideMode() == Qt.ElideNone, bar


def test_rt01_apelido_gravado_com_reticencias(app):
    from PySide6.QtCore import QSettings

    settings = QSettings("BrasBim-testes", "reticencias")
    settings.setValue(ALIASES_KEY, json.dumps({"menu:Exibir/Salvar vista…": "VV"}))
    aliases = load_aliases(settings)
    assert aliases["menu:Exibir/Salvar vista"] == "VV"
    assert not any("…" in key for key in aliases)
    settings.clear()


def test_rt01_dica_da_linha_de_comando_cabe(window):
    line = window.command_line
    window.toolbox.activate("wall")
    window.resize(900, 700)
    QApplication.processEvents()
    field = line.field
    shown = field.placeholderText()
    assert field.fontMetrics().horizontalAdvance(shown) <= field.width() - 16
    assert line.prompt.startswith(shown) and line.prompt.endswith("x;y")
    if shown != line.prompt:
        assert line.prompt in field.toolTip()


def test_rt01_titulo_do_painel_estreito_some(window):
    from PySide6.QtWidgets import QDockWidget

    dock = window.tools_bar
    action = dock.toggleViewAction()
    window.resizeDocks([dock], [50], Qt.Horizontal)  # uma coluna de ícones
    QApplication.processEvents()
    assert dock.windowTitle() == "" and action.text() == "Ferramentas"
    window.resizeDocks([dock], [260], Qt.Horizontal)
    QApplication.processEvents()
    assert dock.windowTitle() == "Ferramentas" and action.text() == "Ferramentas"
    assert all("…" not in d.windowTitle() for d in window.findChildren(QDockWidget))
