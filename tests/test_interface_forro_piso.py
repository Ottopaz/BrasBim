# SPDX-License-Identifier: GPL-3.0-or-later
"""Forro e piso na interface (spec/ui 46, FP08): ferramentas, barra Opções, ficha e Em
todos os ambientes com Desfazer no balão. Qt sem tela; o resultado é conferido no
modelo."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication, QPushButton

from brasbim.core.annotations import commands as ac
from brasbim.core.structure import coverings as cv
from brasbim.ui.tools import Mods


@pytest.fixture(autouse=True)
def _planta_visivel(window):
    window.plan.origin = QPointF(150, 450)


def _space(window, outline):
    s = window.session
    assert s.run(lambda: ac.create_space(s.doc, s.storey, outline))
    return max(s.doc.ifc.by_type("IfcSpace"), key=lambda e: e.id())


def _coverings(s, kind):
    return [c for c in s.doc.ifc.by_type("IfcCovering") if cv.predefined(c) == kind]


def _field(window, name):
    QApplication.processEvents()
    return next(w for g in window.properties.groups for n, w in g.rows if n == name)


def test_fp08_ferramentas_ficha_e_todos(window):
    s = window.session
    a = _space(window, [(40, 0), (44, 0), (44, 3), (40, 3)])
    b = _space(window, [(45, 0), (48, 0), (48, 3), (45, 3)])
    # Piso pelo ambiente: um clique dentro
    window.activate_tool("flooring")
    tool = window.toolbox.active
    window.options_bar.show_for(tool)
    labels = [a.text() for a in window.options_bar.actions()]
    assert "Em todos os ambientes" in labels and "Pelo ambiente" in labels
    assert tool.options.type == next(t.GlobalId for t in cv.types_of(s.doc, "FLOORING")
                                     if t.Name == "Porcelanato")
    tool.move((42, 1.5), Mods())
    assert tool.shape_preview()  # o contorno do ambiente sob o cursor
    tool.press((42, 1.5), Mods())
    (floor,) = _coverings(s, "FLOORING")
    assert cv.read_state(floor)["space"] == a.GlobalId
    tool.press((30, 30), Mods())  # fora de ambiente: recusa
    assert "ambiente" in s.messages[-1]["text"]
    # Em todos os ambientes: só o b ainda não tem piso; Desfazer no balão
    tool.fill_all()
    assert len(_coverings(s, "FLOORING")) == 2
    message = s.messages[-1]
    assert message["text"].startswith("1 piso") and message["action"][0] == "Desfazer"
    message["action"][1]()
    assert len(_coverings(s, "FLOORING")) == 1
    # Forro pelo contorno (retângulo)
    window.activate_tool("ceiling")
    tool = window.toolbox.active
    tool.options.mode = "rectangle"
    tool.options.elevation = 2.5
    tool.press((45.5, 0.5), Mods())
    tool.press((47.5, 2.5), Mods())
    (ceiling,) = _coverings(s, "CEILING")
    state = cv.read_state(ceiling)
    assert state["space"] is None and state["elevation"] == pytest.approx(2.5)
    # ficha do piso: tipo, ambiente (clicar seleciona) e Soltar
    s.select([floor.GlobalId])
    assert _field(window, "Tipo").currentText() == "Porcelanato"
    button = _field(window, "Preso a")
    assert isinstance(button, QPushButton)
    release = next(w for g in window.properties.groups for _, w in g.rows
                   if isinstance(w, QPushButton) and w.text() == "Soltar do ambiente")
    release.click()
    assert cv.read_state(floor)["space"] is None
    # a ficha do ambiente lista o forro e piso presos; o b recebe um piso
    assert s.run(lambda: cv.create_in_space(s.doc, cv.types_of(s.doc, "FLOORING")[0], b))
    s.select([b.GlobalId])
    assert isinstance(_field(window, "Piso"), QPushButton)
    # Projeto > Tipos de forro e piso
    from brasbim.ui.types_dialog import CoveringTypesDialog

    dialog = CoveringTypesDialog(s, window)
    names = [dialog.list.item(i).text() for i in range(dialog.list.count())]
    assert any(n.startswith("Forro de gesso") for n in names)
    dialog.close()
