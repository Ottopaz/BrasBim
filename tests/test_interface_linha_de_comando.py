# SPDX-License-Identifier: GPL-3.0-or-later
"""Linha de comando na janela (spec/ui/24-linha-de-comando.md §10): LC03, LC06–LC10, com
o Qt sem tela."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from brasbim.core.walls import commands as wc
from brasbim.ui import command_palette
from brasbim.ui.command_input import DEFAULT_ALIASES


def _type(widget, text):
    for ch in text:
        widget.keyPressEvent(QKeyEvent(QEvent.KeyPress, 0, Qt.NoModifier, ch))


def _line(window, text):
    """Digita na linha de comando e dá Enter."""
    line = window.command_line
    line.field.setText(text)
    return line.run()


def _walls(window):
    return window.session.doc.ifc.by_type("IfcWall")


def test_lc03_apelidos_apontam_para_comandos(window):
    commands, targets = command_palette.collect(window)
    keys = {c.key for c in commands}
    assert set(DEFAULT_ALIASES) <= keys
    assert set(targets) == keys


def test_lc06_teclado_vai_para_a_linha(window, app):
    line = window.command_line
    assert line.isVisible()
    window.plan.setFocus()
    _type(window.plan, "p")
    assert line.field.text() == "p"
    assert line.popup.isVisible()
    _type(line.field, "d")
    line.field.setText("pd")
    app.sendEvent(line.field, QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier))
    assert window.toolbox.active.name == "wall"
    assert line.field.text() == ""
    assert "tool:wall" == window.recent_commands[0]
    # algarismo com a parede esperando: quadro de medidas; ";" passa para a linha
    _type(window.plan, "3")  # parede sem o primeiro ponto: não espera número
    assert line.field.text() == "3" and window.plan.measure.editing is None
    line.run()
    line.field.setText("0;0")
    line.run()
    window.plan.setFocus()
    _type(window.plan, "3")
    measure = window.plan.measure
    assert measure.editing is not None
    edit = measure.current()
    app.sendEvent(edit, QKeyEvent(QEvent.KeyPress, 0, Qt.NoModifier, ";"))
    assert line.field.text() == "3;"
    assert measure.editing is None and not measure.isVisible()
    # Ctrl+letra e espaço não vão para a linha
    line.field.clear()
    window.plan.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_A, Qt.ControlModifier, "a"))
    assert line.field.text() == ""


def test_lc07_parede_por_coordenadas(window):
    _line(window, "PD")
    assert window.toolbox.active.name == "wall"
    assert _line(window, "0;0") == "ponto 0,00; 0,00"
    _line(window, "@4;0")
    _line(window, "@0;3,2")
    _line(window, "")  # Enter vazio encerra a corrente
    walls = _walls(window)
    assert len(walls) == 2
    doc = window.session.doc
    paths = sorted([*wc.read_state(doc, w)["path"]["start"],
                    *wc.read_state(doc, w)["path"]["end"]] for w in walls)
    assert paths[0] == pytest.approx([0, 0, 4, 0])
    assert paths[1] == pytest.approx([4, 0, 4, 3.2])
    # a relativa conta do último ponto, mesmo depois de encerrar
    assert window.ctx.last_point == pytest.approx((4, 3.2))
    assert window.toolbox.active.name == "wall"


def test_lc08_dica_e_opcoes(window):
    _line(window, "dp")
    line = window.command_line
    tool = window.toolbox.active
    assert tool.name == "offset"
    assert line.prompt.startswith(tool.hint() or tool.label)
    assert line.prompt.endswith("x;y")
    labels = [o.label for o in line.options]
    assert labels[:2] == ["Copiar", "Mover o original"]
    assert line.options[0].current and tool.copy is True
    assert _line(window, "mover") == "opção Mover o original"
    assert tool.copy is False
    assert window.options_bar.choices[0][2]() == 1  # a barra Opções acompanha
    assert line.options[1].current
    line.follow("opt:0:0")  # clique no link "Copiar"
    assert tool.copy is True
    assert window.options_bar.choices[0][2]() == 0
    assert 'href="opt:0:0"' in line.options_label.text()
    # lista longa (camada) vira um link que abre um menu, e não responde ao texto
    _line(window, "PD")
    labels = [o.label for o in line.options]
    assert "Parede em arco" in labels and "Eixo" in labels
    text = line.options_label.text()
    assert text.count('href="menu:') == 1 and "Camada: " in text
    assert not any(o.label.startswith("Arquitetura") for o in line.options)


def test_lc09_historico_recusa_e_esc(window):
    messages = []
    window.session.listeners.append(lambda e: messages.append(e))
    assert _line(window, "xyzw") == "comando não encontrado"
    assert window.session.messages[-1]["level"] == "recusa"
    assert _line(window, "1;1") == "recusado"  # Selecionar não espera ponto
    _line(window, "lj")
    texts = [t for t, _ in window.command_line.history.lines]
    assert texts == ["xyzw", "1;1", "lj"]
    assert window.command_line.history.lines[-1][1] == "Laje"
    line = window.command_line
    line.show_history()
    assert line.popup.list.count() == 3
    line.field.setText("abc")
    line.escape()
    assert line.field.text() == "" and not line.popup.isVisible()
    assert window.toolbox.active.name == "slab"
    line.escape()  # vazio: Esc da vista, a laje volta para Selecionar
    assert window.toolbox.active.name == "select"


def test_lc10_esconder_a_linha(window):
    window.command_line_action.trigger()
    line = window.command_line
    assert not line.isVisible()
    assert window.hint.isVisible()
    window.plan.setFocus()
    _type(window.plan, "p")
    assert line.field.text() == ""
    window.command_line_action.trigger()
    assert line.isVisible() and not window.hint.isVisible()


def test_lc04_dialogo_de_apelidos(window, monkeypatch):
    from brasbim.ui import command_line as cl

    commands, _ = command_palette.collect(window)
    dialog = cl.AliasesDialog(window, commands, window.command_line.aliases)
    row = dialog.keys.index("tool:wall")
    dialog.table.item(row, 2).setText("pp")
    other = dialog.keys.index("tool:slab")
    dialog.table.item(other, 2).setText("PP")
    dialog._accept()
    assert "repetido" in dialog.error.text()
    dialog.table.item(other, 2).setText("")
    dialog._accept()
    assert dialog.result() == cl.AliasesDialog.Accepted
    values = dialog.values()
    assert values["tool:wall"] == "PP" and "tool:slab" not in values
    dialog.restore_defaults()
    assert dialog.values()["tool:wall"] == "PD"
