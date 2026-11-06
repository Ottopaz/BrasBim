# SPDX-License-Identifier: GPL-3.0-or-later
"""Prancha da casa de campo feita pelo Assistente: refaz a casa pelo diário da sessão,
cota as paredes externas, cria um corte e monta uma prancha com planta, corte e carimbo."""
import json
import socket
import sys
from pathlib import Path

socket.gethostname = lambda: "escritorio"

import ifcopenshell.util.element as ue
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication

from brasbim.core.annotations import commands as ac
from brasbim.core.document import Document
from brasbim.core.drawings import sheets
from brasbim.core.ops import History, Transaction
from brasbim.ui import theme
from brasbim.ui.main_window import MainWindow
from brasbim.ui.session import Session

diario, saida = Path(sys.argv[1]), Path(sys.argv[2])
saida.mkdir(parents=True, exist_ok=True)

# 1) a casa, transação por transação, como a IA fez
doc = Document.new("Casa de campo")
hist = History(doc)
for tx in json.loads(diario.read_text(encoding="utf-8"))["transactions"]:
    hist.commit(Transaction.from_dict(tx))
ifc = saida / "casa-de-campo.ifc"
doc.save(str(ifc))
print("casa", len(doc.ifc.by_type("IfcWall")), "paredes", len(doc.ifc.by_type("IfcSpace")), "ambientes")

QSettings.setDefaultFormat(QSettings.IniFormat)
QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(saida / "prefs"))
app = QApplication(sys.argv[:1])
theme.apply(app)
s = Session(journal_dir=saida / "diarios")
w = MainWindow(s)
w.quiet_dialogs = True
w.resize(1800, 1100)
w.show()
w.messages_dock.hide()
s.open(str(ifc))
terreo = s.doc.storeys()[0]
s.set_storey(terreo)

# 2) cotas automáticas nas paredes do contorno da casa
from brasbim.core import geom2d
from brasbim.core.walls.wall import read_state as read_wall

caminhos = {}
for wall in s.doc.ifc.by_type("IfcWall"):
    if ue.get_container(wall) == terreo:
        path = geom2d.path_from_dict(read_wall(s.doc, wall)["path"])
        if isinstance(path, geom2d.LinePath):
            caminhos[wall.GlobalId] = (wall, path.start, path.end)
xs = [c for _, a0, b0 in caminhos.values() for c in (a0[0], b0[0])]
ys = [c for _, a0, b0 in caminhos.values() for c in (a0[1], b0[1])]
x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
print("contorno", x0, x1, y0, y1)
cotadas = 0
for wall, a0, b0 in caminhos.values():
    borda = any(abs(a0[i] - v) < 0.2 and abs(b0[i] - v) < 0.2
                for i, v in ((0, x0), (0, x1), (1, y0), (1, y1)))
    if borda and s.run(lambda wall=wall: ac.auto_dimension_wall(s.doc, wall)):
        cotadas += 1
print("paredes cotadas", cotadas)

# 3) corte pelo meio da casa
cx = (x0 + x1) / 2 + 0.3
s.run(lambda: ac.create_view(s.doc, "section", (cx, y0 - 2), (cx, y1 + 2), "left"))
corte = next(v for v in s.doc.ifc.by_type("IfcAnnotation") if v.ObjectType == "VistaDeCorte")

# 4) prancha A3 com planta e corte em 1:100 e o carimbo preenchido
from brasbim.core.walls import commands as wc

s.run(lambda: wc.edit_storey(s.doc, terreo, scale=100))
s.run(lambda: ac.edit_element(s.doc, corte, scale=100))
s.run(lambda: sheets.edit_project(s.doc, name="Casa de campo",
                                  address="Estrada do Sítio, km 4, zona rural (exemplo)",
                                  owner="Proprietário do exemplo",
                                  responsible="Responsável técnico do exemplo",
                                  registration="CAU A00000-0"))
s.run(lambda: sheets.create_sheet(s.doc, "Planta baixa e corte AA"))
(prancha,) = sheets.all_sheets(s.doc)
s.run(lambda: sheets.add_to_sheet(s.doc, prancha, {"kind": "plan", "storey": terreo.GlobalId},
                                  at=(100, 150)))
s.run(lambda: sheets.add_to_sheet(s.doc, prancha, {"kind": "view", "view": corte.GlobalId},
                                  at=(300, 95)))
print("prancha", sheets.read_state(prancha))


def capturar():
    from PySide6.QtCore import QSize
    from PySide6.QtPdf import QPdfDocument
    w.set_view("plan")
    w.plan.fit()
    w.plan.grab().save(str(saida / "planta.png"))
    pdf = saida / "prancha.pdf"
    print("pdf", w.export_pdf(str(pdf)))
    d = QPdfDocument()
    d.load(str(pdf))
    pt = d.pagePointSize(0)
    escala = 2400 / pt.width()
    img = d.render(0, QSize(2400, round(pt.height() * escala)))
    img.save(str(saida / "prancha.png"))
    s.modified = False
    w.close()
    app.quit()


QTimer.singleShot(3000, capturar)
app.exec()
