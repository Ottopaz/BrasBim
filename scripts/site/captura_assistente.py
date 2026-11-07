# SPDX-License-Identifier: GPL-3.0-or-later
"""Grava o painel Assistente do BrasBim atendendo um pedido real (Claude Code via MCP).
Salva um PNG por segundo da janela até a IA terminar."""
import socket
import sys
from pathlib import Path

socket.gethostname = lambda: "escritorio"

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication

from brasbim.ui import theme
from brasbim.ui.main_window import MainWindow
from brasbim.ui.session import Session

saida = Path(sys.argv[1])
pedido = sys.argv[2]
saida.mkdir(parents=True, exist_ok=True)
QSettings.setDefaultFormat(QSettings.IniFormat)
QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(saida / "prefs"))
app = QApplication(sys.argv[:1])
theme.apply(app)
session = Session(journal_dir=saida / "diarios")
w = MainWindow(session)
w.quiet_dialogs = True
w.resize(1600, 900)
w.show()
w.messages_dock.hide()
w.assistant_dock.show()
w.assistant_dock.raise_()
w.set_view("split")

n = 0
fim = {"t": None}


def quadro():
    global n
    w.grab().save(str(saida / f"q{n:04d}.png"))
    n += 1
    if fim["t"] is not None:
        fim["t"] += 1
        if fim["t"] == 3:  # mais alguns quadros com o 3D enquadrado
            w.fit_all()
        if fim["t"] >= 8:
            session.modified = False
            w.close()
            app.quit()


def terminou():
    print("terminou", flush=True)
    fim["t"] = 0


def enviar():
    w.assistant.prompt.setPlainText(pedido)
    w.assistant.send()
    print("enviado", flush=True)


w.assistant.finished.connect(terminou)
t = QTimer()
t.timeout.connect(quadro)
t.start(1000)
QTimer.singleShot(2500, enviar)
QTimer.singleShot(20 * 60 * 1000, lambda: (print("tempo esgotado", flush=True), app.quit()))
app.exec()
print("quadros", n)
