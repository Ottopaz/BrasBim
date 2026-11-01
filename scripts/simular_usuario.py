# SPDX-License-Identifier: GPL-3.0-or-later
"""Simula uma pessoa usando o BrasBim (janela real, sem tela) e cronometra cada ação.

Uso (na pasta do projeto): python scripts/simular_usuario.py <pasta de saída>
Grava tempos.csv, perfil.txt e perfil.prof na pasta e mostra o resumo por ação.
"""
import cProfile
import csv
import itertools
import os
import pathlib
import pstats
import statistics
import sys
import tempfile
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
OUT = pathlib.Path(sys.argv[1])

from PySide6.QtCore import QPointF, QSettings, Qt

QSettings.setDefaultFormat(QSettings.IniFormat)
QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, tempfile.mkdtemp())
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

app = QApplication([])

from brasbim.core.objects import commands as oc
from brasbim.core.objects import library
from brasbim.ui.main_window import MainWindow
from brasbim.ui.session import Session

rows = []  # (fase, ação, ms, nº de elementos)


def count(w):
    ifc = w.session.doc.ifc
    return sum(len(ifc.by_type(c)) for c in ("IfcWall", "IfcDoor", "IfcWindow", "IfcSlab",
                                             "IfcFurniture", "IfcGeographicElement"))


def timed(w, phase, action, fn):
    t = time.perf_counter()
    result = fn()
    app.processEvents()
    ms = (time.perf_counter() - t) * 1000
    rows.append((phase, action, round(ms, 1), count(w)))
    return result


def scr(w, p):
    return w.plan.to_screen(p).toPoint()


def click(w, p):
    QTest.mouseClick(w.plan, Qt.LeftButton, Qt.NoModifier, scr(w, p))


def hover(w, phase, a, b, steps=12):
    """Cursor andando de a até b: cada passo é um quadro que a pessoa sente."""
    for i in range(1, steps + 1):
        p = (a[0] + (b[0] - a[0]) * i / steps, a[1] + (b[1] - a[1]) * i / steps)
        timed(w, phase, "mover o cursor", lambda p=p: (QTest.mouseMove(w.plan, scr(w, p)),
                                                       w.plan.repaint()))


def floor(w, phase, ox=0.0):
    s = w.session
    # paredes externas: cadeia fechada 12 × 9, com o cursor andando entre cliques
    w.activate_tool("wall")
    pts = [(ox, 0), (ox + 12, 0), (ox + 12, 9), (ox, 9), (ox, 0)]
    for a, b in itertools.pairwise(pts):
        timed(w, phase, "clicar ponto da parede", lambda a=a: click(w, a))
        hover(w, phase, a, b)
    timed(w, phase, "fechar cadeia de paredes", lambda: click(w, pts[-1]))
    # paredes internas
    for a, b in (((ox + 5, 0), (ox + 5, 9)), ((ox, 4.5), (ox + 5, 4.5)),
                 ((ox + 5, 6), (ox + 12, 6)), ((ox + 9, 6), (ox + 9, 9))):
        timed(w, phase, "clicar ponto da parede", lambda a=a: click(w, a))
        hover(w, phase, a, b, 6)
        timed(w, phase, "clicar ponto da parede", lambda b=b: click(w, b))
        timed(w, phase, "terminar parede (Enter)",
              lambda: QTest.keyClick(w.plan, Qt.Key_Return))
    QTest.keyClick(w.plan, Qt.Key_Escape)
    # portas e janelas pela ferramenta (passa o cursor e clica)
    for tool, places in (("door", [(ox + 2.5, 4.55), (ox + 5.05, 2), (ox + 7, 6.05),
                                   (ox + 10.5, 6.05), (ox + 8, 0.07)]),
                         ("window", [(ox + 2, 0.07), (ox + 10, 0.07), (ox + 2, 8.95),
                                     (ox + 7, 8.95), (ox + 11.95, 3), (ox + 0.05, 6.5)])):
        w.activate_tool(tool)
        for p in places:
            hover(w, phase, (p[0] - 1, p[1] + 1), p, 6)
            timed(w, phase, f"pôr {'porta' if tool == 'door' else 'janela'}",
                  lambda p=p: click(w, p))
        QTest.keyClick(w.plan, Qt.Key_Escape)
    # laje pelo cômodo
    w.activate_tool("slab")
    w.toolbox.active.options.mode = "room"
    for p in ((ox + 2, 2), (ox + 8, 3), (ox + 2, 7), (ox + 7, 7.5), (ox + 10.5, 7.5)):
        hover(w, phase, (p[0] + 0.5, p[1] + 0.5), p, 4)
        timed(w, phase, "laje pelo cômodo", lambda p=p: click(w, p))
    QTest.keyClick(w.plan, Qt.Key_Escape)
    # móveis
    s = w.session
    for name, p in (("Cama casal", (ox + 2, 2)), ("Sofá 3 lugares", (ox + 8, 2)),
                    ("Mesa de jantar 6 lugares", (ox + 8, 4)), ("Geladeira", (ox + 6, 8))):
        t = next((t for t in s.doc.ifc.by_type("IfcFurnitureType") if t.Name == name), None)
        if t is not None:
            timed(w, phase, "pôr móvel",
                  lambda t=t, p=p: s.run(lambda: oc.create_object(s.doc, t, s.storey, p)))


def main():
    w = MainWindow(Session(journal_dir=pathlib.Path(tempfile.mkdtemp())))
    w.quiet_dialogs = True
    w.resize(1400, 900)
    w.show()
    app.processEvents()
    w.plan.scale, w.plan.origin = 40.0, QPointF(80, 700)
    w.plan._sync_tol()
    s = w.session
    # biblioteca: móveis e vegetação
    entries = []
    for f in pathlib.Path("brasbim/library/objetos").rglob("*.ifc"):
        entries += library.read_file(f)
    timed(w, "preparo", "carregar biblioteca",
          lambda: s.run(library.load(s.doc, entries, entries)))
    # três pavimentos iguais (o terceiro com Pavimento acima)
    for i in range(3):
        if i:
            if i >= len(s.doc.storeys()):
                from brasbim.core.walls import commands as cmd
                s.run(lambda i=i: cmd.create_storey(s.doc, f"Pav {i + 1}", 2.8 * i))
            timed(w, f"pav{i + 1}", "trocar de pavimento", lambda: w.step_storey(1))
        floor(w, f"pav{i + 1}")
    # cobertura sobre o último pavimento
    w.activate_tool("roof")
    timed(w, "cobertura", "cobertura pelas paredes",
          lambda: (click(w, (3, 3)), QTest.keyClick(w.plan, Qt.Key_Return)))
    QTest.keyClick(w.plan, Qt.Key_Escape)
    # árvores no terreno
    w.step_storey(-2)
    tree = next((t for t in s.doc.ifc.by_type("IfcGeographicElementType")
                 if t.Name == "Árvore média"), None)
    for k in range(8):
        if tree is not None:
            timed(w, "terreno", "pôr árvore", lambda k=k: s.run(
                lambda: oc.create_object(s.doc, tree, s.storey, (-4 + 2.5 * k, -4))))
    # edição: selecionar e arrastar uma parede, desfazer e refazer
    w.activate_tool("select")
    wall = s.doc.ifc.by_type("IfcWall")[0]
    timed(w, "edição", "selecionar parede", lambda: s.select([wall.GlobalId]))
    timed(w, "edição", "mover seleção 0,5 m", lambda: w.run_selection_action("move") or (
        click(w, (6, 0)), click(w, (6, -0.5))))
    for _ in range(5):
        timed(w, "edição", "desfazer", w.undo)
    for _ in range(5):
        timed(w, "edição", "refazer", w.redo)
    # navegação na planta
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QWheelEvent

    def wheel(delta):
        pos = QPointF(scr(w, (6, 4)))
        ev = QWheelEvent(pos, w.plan.mapToGlobal(pos), QPoint(), QPoint(0, delta),
                         Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
        w.plan.wheelEvent(ev)
        w.plan.repaint()

    for d in (120, 120, 120, -120, -120, -120):
        timed(w, "navegação", "zoom com a roda", lambda d=d: wheel(d))
    timed(w, "navegação", "redesenhar a planta", w.plan.repaint)
    timed(w, "navegação", "enquadrar tudo", w.fit_all)
    # 3D: abrir (triangulação) e editar com ele aberto
    timed(w, "3D", "abrir 3D lado a lado", lambda: w.set_view("split"))
    timed(w, "3D", "carregar a cena 3D", lambda: w.scene.load(s.doc.ifc, s.doc))
    timed(w, "3D", "contorno das malhas (1ª vez)", lambda: [
        __import__("brasbim.ui.scene3d", fromlist=["x"]).contour_of(m)
        for m in w.scene.meshes.values()])
    w.activate_tool("wall")
    timed(w, "3D", "parede nova com 3D aberto",
          lambda: (click(w, (14, 0)), click(w, (14, 5)), QTest.keyClick(w.plan, Qt.Key_Return)))
    QTest.keyClick(w.plan, Qt.Key_Escape)
    # salvar e abrir
    path = OUT / "simulacao.ifc"
    timed(w, "arquivo", "salvar", lambda: s.doc.save(str(path)))
    s.modified = False
    timed(w, "arquivo", "abrir de novo", lambda: s.open(str(path)))
    s.modified = False
    return w


prof = cProfile.Profile()
t0 = time.perf_counter()
prof.enable()
window = main()
prof.disable()
total = time.perf_counter() - t0
with open(OUT / "tempos.csv", "w", newline="", encoding="utf-8") as f:
    csv.writer(f).writerows([("fase", "ação", "ms", "elementos"), *rows])
prof.dump_stats(str(OUT / "perfil.prof"))
with open(OUT / "perfil.txt", "w", encoding="utf-8") as f:
    st = pstats.Stats(prof, stream=f)
    st.sort_stats("cumulative").print_stats(r"brasbim", 60)
    st.sort_stats("tottime").print_stats(40)
# resumo
by = {}
for phase, action, ms, n in rows:
    by.setdefault(action, []).append(ms)
print(f"total {total:.1f} s, {len(rows)} ações, {count(window)} elementos")
for action, values in sorted(by.items(), key=lambda kv: -max(kv[1])):
    print(f"{action:34s} n={len(values):3d}  mediana={statistics.median(values):8.1f} ms"
          f"  máx={max(values):8.1f} ms")
