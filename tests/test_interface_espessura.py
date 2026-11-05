# SPDX-License-Identifier: GPL-3.0-or-later
"""Espessura livre na interface (spec/ui 43 §3.1): EL06."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

import ifcopenshell.util.element as ue
from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit

from brasbim.core import type_variants as tv
from brasbim.core.structure import commands as sc
from brasbim.core.walls import commands as wc
from brasbim.ui.tools import Mods


def _field(window, name):
    QApplication.processEvents()
    return next(w for g in window.properties.groups for n, w in g.rows if n == name)


def _type(doc, cls, prefix):
    return next(t for t in doc.ifc.by_type(cls)
                if (t.Name or "").startswith(prefix) and not tv.is_variant(t))


def test_el06_ficha_e_barra_opcoes(window, app):
    s = window.session
    doc = s.doc
    t = doc.ifc.by_type("IfcWallType")[0]
    nominal = tv.type_thickness(t)
    s.run(lambda: wc.create_wall(doc, t, s.storey, (0, 0), (5, 0)))
    s.run(lambda: wc.create_wall(doc, t, s.storey, (0, 3), (5, 3)))
    a, b = doc.ifc.by_type("IfcWall")

    # Ficha de uma parede: digitar a espessura cria a variante.
    s.select([a.GlobalId])
    field = _field(window, "Espessura")
    assert isinstance(field, QLineEdit) and field.text() != ""
    field.setText("0,2")
    field.editingFinished.emit()
    variant = ue.get_type(a)
    assert tv.is_variant(variant) and variant.Name == f"{t.Name} · 20 cm"
    # A variante aparece logo abaixo do tipo de origem, recuada.
    combo = _field(window, "Tipo")
    assert isinstance(combo, QComboBox)
    texts = [combo.itemText(i) for i in range(combo.count())]
    assert texts[texts.index(t.Name) + 1] == f"    {variant.Name}"
    assert combo.currentData() == variant.GlobalId

    # Várias paredes: valores diferentes ficam vazios; digitar vale para todas.
    s.select([a.GlobalId, b.GlobalId])
    field = _field(window, "Espessura")
    assert field.text() == ""
    field.setText(f"{nominal}".replace(".", ","))
    field.editingFinished.emit()
    assert ue.get_type(a) == t and ue.get_type(b) == t
    assert doc.find(variant.GlobalId) is None  # sem uso, saiu
    s.history.undo()
    assert tv.is_variant(ue.get_type(a))
    s.history.redo()

    # Barra Opções da parede: a próxima parede nasce com a espessura digitada; as
    # variantes não aparecem na lista de tipos.
    window.activate_tool("wall")
    tool = window.toolbox.active
    bar_fields = [w for w in window.options_bar.findChildren(QLineEdit)
                  if w.toolTip().startswith("Espessura da próxima parede")]
    assert len(bar_fields) == 1
    bar_fields[0].setText("0,25")
    bar_fields[0].editingFinished.emit()
    assert tool.options.thickness == 0.25
    assert all(not tv.is_variant(doc.find(window.options_bar.type_combo.itemData(i)))
               for i in range(window.options_bar.type_combo.count()))
    before = {w.GlobalId for w in doc.ifc.by_type("IfcWall")}
    tool.press((0, 8), Mods())
    tool.press((4, 8), Mods())
    tool.key("enter")
    (new,) = [w for w in doc.ifc.by_type("IfcWall") if w.GlobalId not in before]
    assert tv.thickness_of(doc, new) == pytest.approx(0.25)
    s.history.undo()  # a parede e a variante saem juntas (uma transação)
    assert not any(tv.is_variant(x) for x in doc.ifc.by_type("IfcWallType"))

    # Laje: ficha.
    st = _type(doc, "IfcSlabType", "Laje")
    s.run(lambda: sc.create_slab(doc, st, s.storey, [(0, 0), (4, 0), (4, 3), (0, 3)]))
    (slab,) = [x for x in doc.ifc.by_type("IfcSlab") if ue.get_type(x) == st]
    s.select([slab.GlobalId])
    field = _field(window, "Espessura")
    field.setText("0,3")
    field.editingFinished.emit()
    assert tv.thickness_of(doc, slab) == pytest.approx(0.30)
    assert tv.read(ue.get_type(slab))["origin"] == st.GlobalId
