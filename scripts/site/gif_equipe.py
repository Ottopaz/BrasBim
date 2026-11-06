# SPDX-License-Identifier: GPL-3.0-or-later
"""GIF do projeto compartilhado: Ana compartilha, Bruno entra, os dois editam o mesmo
pavimento ao mesmo tempo. A planta das duas janelas é gravada a cada passo."""
import math
import socket
import sys
from pathlib import Path

socket.gethostname = lambda: "escritorio"

import ifcopenshell.util.element as ue
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication

from brasbim.core.structure import commands as st
from brasbim.ui import theme
from brasbim.ui.main_window import MainWindow
from brasbim.ui.session import Session

ifc, saida, pav = sys.argv[1], Path(sys.argv[2]), int(sys.argv[3])
saida.mkdir(parents=True, exist_ok=True)
QSettings.setDefaultFormat(QSettings.IniFormat)
QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(saida / "prefs"))
app = QApplication(sys.argv[:1])
theme.apply(app)


def janela(nome):
    s = Session(journal_dir=saida / f"diarios-{nome}")
    w = MainWindow(s)
    w.quiet_dialogs = True
    w.resize(1600, 1000)
    w.show()
    return s, w


ana, wa = janela("ana")
ana.open(ifc)
ana.share("Ana", port=47913, discovery=False)
bruno, wb = janela("bruno")
bruno.join("127.0.0.1", 47913, "Bruno")


def preparar(s, w):
    andar = s.doc.storeys()[pav]
    s.set_storey(andar)
    w.messages_dock.hide()
    w.team_dock.show()
    w.team_dock.raise_()
    w.set_view("plan")


def elementos(s, tipo):
    andar = s.doc.storeys()[pav]
    achados = [e for e in s.doc.ifc.by_type("IfcColumn")
               if ue.get_container(e) == andar and (ue.get_type(e).Name or "").startswith(tipo)]

    def ang(e):
        x, y = st.read_state(s.doc, e)["point"]
        return math.atan2(y, x)
    return sorted(achados, key=ang)


def enquadrar(w):
    plan = w.plan
    plan.scale = 30.0
    plan._center_on((-7.0, -7.5))
    plan._sync_tol()
    plan.update()


quadros = []


def gravar():
    for _ in range(6):
        ana.poll()
        bruno.poll()
        app.processEvents()
    for w in (wa, wb):
        w.team.refresh()
    app.processEvents()
    i = len(quadros)
    wa.grab().save(str(saida / f"a{i:03d}.png"))
    wb.grab().save(str(saida / f"b{i:03d}.png"))
    quadros.append(i)


passos = []


def montar():
    for s, w in ((ana, wa), (bruno, wb)):
        preparar(s, w)
        w.fit_all()
    for w in (wa, wb):
        enquadrar(w)
    brises = elementos(ana, "Brise")[:14]
    pilares = elementos(bruno, "Pilar")[:5]
    print("brises", len(brises), "pilares", len(pilares), flush=True)
    passos.append(lambda: None)
    passos.append(lambda: None)
    feitos_a, feitos_b = [], []
    for k in range(max(len(brises), len(pilares) * 3)):
        def passo(k=k):
            if k < len(brises):
                b = brises[k]
                ana.run(lambda: st.edit_element(ana.doc, b, angle=0.0))
                feitos_a.append(b.GlobalId)
                ana.select(list(feitos_a))
            if k % 3 == 1 and k // 3 < len(pilares):
                p = pilares[k // 3]
                bruno.run(lambda: st.edit_element(bruno.doc, p,
                                                  section={"shape": "circle", "d": 1.0}))
                feitos_b.append(p.GlobalId)
                bruno.select(list(feitos_b))
        passos.append(passo)

    def pedir():
        bruno.select([brises[2].GlobalId])
        bruno.request_release([brises[2].GlobalId])
    passos.append(pedir)
    passos.extend([lambda: None] * 3)


def proximo():
    if not passos:
        for s in (bruno, ana):
            s.modified = False
        wb.close()
        wa.close()
        app.quit()
        return
    passos.pop(0)()
    gravar()
    QTimer.singleShot(300, proximo)


def comecar():
    montar()
    QTimer.singleShot(500, proximo)


QTimer.singleShot(2000, comecar)
app.exec()
print("quadros", len(quadros))
