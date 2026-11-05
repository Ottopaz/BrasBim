# SPDX-License-Identifier: GPL-3.0-or-later
"""Exportar IFC na interface (spec/ui 47, EX06). Qt sem tela."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

import ifcopenshell
from PySide6.QtCore import QSettings

from brasbim.core import ifc_export as ie
from brasbim.ui import main_window as mw
from brasbim.ui.export_dialog import ExportIfcDialog


def test_ex06_quadro_e_balao(window, tmp_path):
    s = window.session
    window.activate_tool("wall")
    tool = window.toolbox.active
    from brasbim.ui.tools import Mods

    tool.press((0, 0), Mods())
    tool.press((5, 0), Mods())
    tool.key("enter")
    labels = [a.text() for m in window.menuBar().actions() for a in m.menu().actions()
              if m.menu() is not None]
    assert "Exportar IFC (2x3, 4)" in labels
    dialog = ExportIfcDialog(ie.Options(), str(tmp_path / "a.ifc"), window)
    assert dialog.version.currentData() == "IFC2X3" and not dialog.drawings.isEnabled()
    dialog.version.setCurrentIndex(dialog.version.findData("IFC4"))
    assert dialog.drawings.isEnabled()
    dialog.target.setCurrentIndex(dialog.target.findData("engineering"))
    options = dialog.options()
    assert (options.version, options.target) == ("IFC4", "engineering")
    path = str(tmp_path / "casa.ifc")
    assert window.export_ifc(path, ie.Options()) == path
    assert ifcopenshell.open(path).schema == "IFC2X3"
    assert s.messages[-1]["text"].startswith("IFC 2x3 exportado")
    # as opções voltam na próxima vez
    settings = QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat)
    settings.setValue("exportar_ifc/version", "IFC4")
    settings.setValue("exportar_ifc/drawings", "true")
    found = mw.ifc_options(settings)
    assert found.version == "IFC4" and found.drawings is True and found.own_properties


def test_g05_exportar_3d_pelo_menu(window, tmp_path):
    from brasbim.core import model_export as me
    from brasbim.ui.tools import Mods

    window.activate_tool("wall")
    tool = window.toolbox.active
    tool.press((0, 0), Mods())
    tool.press((4, 0), Mods())
    tool.key("enter")
    labels = [a.text() for m in window.menuBar().actions() if m.menu() is not None
              for a in m.menu().actions()]
    assert "Exportar 3D (glTF, OBJ)" in labels
    path = str(tmp_path / "casa.glb")
    assert window.export_3d(path) == path
    doc, _ = me.read_glb(path)
    assert any(n.get("extras", {}).get("ClasseIfc") == "IfcWall" for n in doc["nodes"])
    assert window.session.messages[-1]["text"].startswith("3D exportado")
