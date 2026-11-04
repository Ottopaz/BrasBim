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
