# SPDX-License-Identifier: GPL-3.0-or-later
"""Limpeza da janela: interface (``spec/ui/42-limpeza-da-janela.md`` §5)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QAbstractButton, QDockWidget

from brasbim.ui import balloon


def _docks(window):
    return [d for d in window.findChildren(QDockWidget) if d.isVisible()]


def _qt_buttons(dock):
    """Botões de soltar e fechar que o próprio Qt põe no título do painel."""
    return [b for b in dock.findChildren(QAbstractButton)
            if b.objectName().startswith("qt_dockwidget_") and b.isVisible()]


# LJ01: encaixado, o painel mostra só o nome


def test_lj01_painel_encaixado_sem_botoes(window):
    docks = _docks(window)
    assert window.storeys_dock in docks and window.tools_bar in docks
    for dock in docks:
        title = dock.titleBarWidget()
        assert title is not None, dock.objectName()
        assert not title.close_button.isVisible()
        assert not _qt_buttons(dock)
    assert window.storeys_dock.titleBarWidget().label.text() == "Pavimentos"
    assert window.storeys_dock.titleBarWidget().label.width() > 0


# LJ02: solto, o painel ganha o botão de fechar; encaixado de novo, perde


def test_lj02_painel_solto_tem_fechar(window, app):
    dock = window.storeys_dock
    title = dock.titleBarWidget()
    dock.setFloating(True)
    app.processEvents()
    assert title.close_button.isVisible()
    title.close_button.click()
    app.processEvents()
    assert not dock.isVisible()
    assert not dock.toggleViewAction().isChecked()  # volta por Exibir > Painéis
    dock.toggleViewAction().trigger()
    dock.setFloating(False)
    app.processEvents()
    assert dock.isVisible() and not title.close_button.isVisible()


# LJ03: clique duplo na faixa solta e encaixa, como antes


def test_lj03_clique_duplo_solta_e_encaixa(window, app):
    dock = window.project_dock
    title = dock.titleBarWidget()
    QTest.mouseDClick(title, Qt.LeftButton, Qt.NoModifier, QPoint(40, title.height() // 2))
    app.processEvents()
    assert dock.isFloating()
    QTest.mouseDClick(title, Qt.LeftButton, Qt.NoModifier, QPoint(40, title.height() // 2))
    app.processEvents()
    assert not dock.isFloating()


# LJ04: a coluna de ferramentas rola sem barra de rolagem


def test_lj04_ferramentas_sem_barra_de_rolagem(window):
    scroll = window.tools_bar.widget()
    assert scroll.verticalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    assert not scroll.verticalScrollBar().isVisible()


# LJ05: a barra da vista se espalha até o fim da vista


def test_lj05_barra_da_vista_espalhada(window, app):
    window.resize(2000, 800)
    app.processEvents()
    bar = window.view_bar
    assert bar.width() > 800
    right = bar.situation.geometry().right()
    assert right > bar.width() * 0.6  # o último grupo vai longe, não fica colado no zoom
    assert bar.detail.x() - bar.layers.geometry().right() > 20  # vão entre os grupos
    assert bar.pick_locked.geometry().right() > bar.width() - 20  # cadeado na ponta


# LJ06: sem opções da ferramenta, o campo vai até o Histórico


def test_lj06_campo_ate_o_historico(window, app):
    line = window.command_line
    window.activate_tool("select")
    app.processEvents()
    if not window.options_bar.choices:
        assert not line.options_label.isVisible()
        gap = line.history_button.x() - line.field.geometry().right()
        assert gap < 20
    window.activate_tool("wall")
    app.processEvents()
    assert window.options_bar.choices and line.options_label.isVisible()


# LJ07: balão com a última mensagem, acima da barra da vista, que some sozinho


def test_lj07_balao_da_mensagem(window, app):
    b = window.balloon
    window.session.message("Parede criada", "info")
    app.processEvents()
    assert b.isVisible() and b.label.text() == "Parede criada"
    assert b.x() < 40  # à esquerda da vista
    assert b.geometry().bottom() < window.view_bar.y()  # logo acima da barra da vista
    assert b.timer.isActive()
    window.session.message("Sem espaço para a porta", "recusa")
    app.processEvents()
    assert b.label.text() == "Sem espaço para a porta"  # a nova toma o lugar
    assert balloon.LEVEL_COLOR["recusa"] in b.styleSheet()
    assert b.testAttribute(Qt.WA_TransparentForMouseEvents)  # o clique passa para a vista
    b.timer.stop()
    b.dismiss()
    b.fade.setCurrentTime(b.fade.duration())  # o esmaecer chega ao fim sem esperar
    app.processEvents()
    assert not b.isVisible()
    assert window.messages.count() == 2  # o painel Mensagens continua com tudo


def test_lj07_tempo_do_balao():
    assert balloon.duration("ok", "info") >= 3000
    assert balloon.duration("ok", "recusa") > balloon.duration("ok", "info")
    assert balloon.duration("palavra " * 500, "info") == 10000
