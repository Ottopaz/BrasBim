# SPDX-License-Identifier: GPL-3.0-or-later
"""Unidades do projeto na interface (spec/ui 44 §2): UN05."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from brasbim.core import units
from brasbim.core.annotations import base
from brasbim.core.annotations import commands as ac
from brasbim.ui import icons
from brasbim.ui.units_dialog import UnitsDialog


def test_un05_barra_da_vista_padroes_e_janela(window, app):
    s = window.session
    doc = s.doc
    assert "units" in icons.names()
    bar = window.view_bar
    bar.refresh()
    assert bar.units.text() == "m · 2 casas"
    menu = [x.text() for x in window.menuBar().actions()
            for x in x.menu().actions() if x.menu() is None]
    assert "Unidades do projeto" in menu
    s.run(lambda: ac.create_dimension(doc, s.storey, [(0, 0), (3.25, 0)], "fixed", 0.0, -0.6))
    (dim,) = [a for a in doc.ifc.by_type("IfcAnnotation") if a.PredefinedType == "DIMENSION"]

    # Padrão pronto pelo menu do botão.
    bar._fill_units()
    actions = {a.text(): a for a in bar.units.menu().actions()}
    assert actions["Metros, 2 casas (projeto legal)"].isChecked()
    actions["Centímetros, sem casas (executivo)"].trigger()
    app.processEvents()
    assert bar.units.text() == "cm · 0 casas"
    assert [t.text for t in base.build(doc, dim).texts] == ["325"]
    s.history.undo()
    app.processEvents()
    assert bar.units.text() == "m · 2 casas"

    # Janela: mudar a área e o nível, com o exemplo ao lado; Aplicar é uma ação.
    def fill(dialog):
        row = dialog.rows["area"]
        row["decimals"].setValue(1)
        assert row["example"].text() == "12,4 m²"
        row = dialog.rows["level"]
        row["unit"].setCurrentIndex(row["unit"].findData("cm"))
        row["decimals"].setValue(0)
        assert row["example"].text() == "+280"
        dialog.apply()

    assert window.edit_units(fill)
    cfg = units.config(doc)
    assert cfg["area"]["decimals"] == 1 and cfg["level"]["unit"] == "cm"
    assert s.history.undo_stack[-1].label == "Unidades do projeto"

    def restore(dialog):
        dialog.reset()
        assert dialog.rows["level"]["example"].text() == "+2,80"
        dialog.apply()

    assert window.edit_units(restore)
    assert units.config(doc) == units.default_config()
    assert isinstance(UnitsDialog(s), UnitsDialog)


def test_un06_trabalhar_em_centimetros(window, app):
    """Com o padrão Centímetros, digita-se e lê-se em cm (spec/ui 44 §2a): quadro de
    medidas, linha de comando, ficha e barra Opções; o modelo continua em metros."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QLineEdit
    from test_interface import _click, _move
    from test_interface_medidas_3d import _path

    from brasbim.core.walls import commands as cmd

    s = window.session
    s.run(lambda: units.apply_preset(s.doc, "centimeters"))
    assert units.work_unit() == "cm"

    # Quadro de medidas: "325" é 3,25 m.
    window.activate_tool("wall")
    _click(window, (0, 0))
    _move(window, (2, 0))
    QTest.keyClicks(window.plan, "3")  # a primeira tecla abre o quadro
    QTest.keyClicks(window.plan.numeric, "25")
    measure = window.plan.measure
    assert measure.units[0].text() == "cm"
    QTest.keyClick(window.plan.numeric, Qt.Key_Return)
    QTest.keyClick(window.plan, Qt.Key_Return)
    (wall,) = s.doc.ifc.by_type("IfcWall")
    assert _path(s, wall).end == pytest.approx((3.25, 0))

    # Linha de comando: coordenadas em cm.
    window.activate_tool("wall")
    line = window.command_line
    line.field.setText("0;100")
    line.run()
    line.field.setText("@250;0")
    assert line.run() == "ponto 250; 100"
    QTest.keyClick(window.plan, Qt.Key_Return)
    second = next(w for w in s.doc.ifc.by_type("IfcWall") if w != wall)
    assert _path(s, second).start == pytest.approx((0, 1))
    assert _path(s, second).end == pytest.approx((2.5, 1))

    # Ficha: comprimento e espessura em cm; o nome do campo diz a unidade.
    window.activate_tool("select")
    s.select([wall.GlobalId])
    app.processEvents()
    rows = {n: w for g in window.properties.groups for n, w in g.rows}
    assert rows["Comprimento"].text() == "325"
    assert rows["Espessura"].text() == "14"
    rows["Comprimento"].setText("400")
    rows["Comprimento"].editingFinished.emit()
    assert _path(s, wall).length == pytest.approx(4.0)
    assert cmd.read_state(s.doc, wall)["path"]

    # Barra Opções: altura fixa em cm.
    window.activate_tool("wall")
    tool = window.toolbox.active
    tool.options.top = "fixed"
    window.options_bar.show_for(tool)
    (height,) = [w for w in window.options_bar.findChildren(QLineEdit)
                 if w.toolTip().startswith("Altura da parede")]
    assert "(cm)" in height.toolTip()
    height.setText("270")
    height.editingFinished.emit()
    assert tool.options.fixed_height == pytest.approx(2.70)

    # De volta a metros, tudo como antes.
    s.run(lambda: units.apply_preset(s.doc, "meters"))
    assert units.work_unit() == "m"
