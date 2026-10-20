# SPDX-License-Identifier: GPL-3.0-or-later
"""Eixos, vão e claraboia na interface (spec/ui/20 §5, EV06), com o Qt sem tela."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF

from brasbim.core.structure import commands as sc
from brasbim.core.structure import skylights
from brasbim.core.walls import commands as wc
from brasbim.core.walls import openings
from brasbim.ui.tools import Mods


@pytest.fixture(autouse=True)
def _planta_visivel(window):
    window.plan.origin = QPointF(150, 450)


def _press(window, name, *points):
    window.activate_tool(name)
    tool = window.toolbox.active
    for p in points:
        tool.move(p, Mods(alt=True))
        tool.press(p, Mods(alt=True))
    return tool


def test_ev06_ferramentas(window, app):
    s = window.session
    tool = _press(window, "grid", (0, 0))
    tool.options.u, tool.options.v = "4; 4", "5"
    tool.move((3, 0), Mods(alt=True))
    assert tool.preview()
    tool.press((3, 0), Mods(alt=True))
    (g,) = s.doc.ifc.by_type("IfcGrid")
    assert [a.AxisTag for a in g.UAxes] == ["1", "2", "3"]
    s.run(lambda: wc.create_wall(s.doc, window.toolbox.tools["wall"].options.type, s.storey,
                                 (0, 0), (6, 0)))
    (wall,) = s.doc.ifc.by_type("IfcWall")
    tool = _press(window, "wall_opening")
    tool.options.kind = "RECESS"
    tool.move((2, 0.05), Mods())
    assert tool.target and not tool.target["error"]
    tool.press((2, 0.05), Mods())
    (nicho,) = openings.of_wall(wall)
    assert nicho.PredefinedType == "RECESS"
    s.select([nicho.GlobalId])
    window.properties._rebuild()
    assert window.properties.groups[0].title == "Nicho"
    slab_type = next(t for t in s.doc.ifc.by_type("IfcSlabType") if t.PredefinedType != "ROOF")
    s.run(lambda: sc.create_slab_rectangle(s.doc, slab_type, s.storey, (0, 1), (6, 5)))
    _press(window, "skylight", (3, 3))
    (w,) = skylights.all_skylights(s.doc)
    assert skylights.read_state(w)["center"] == pytest.approx([3, 3])
    s.select([w.GlobalId])
    window.properties._rebuild()
    assert window.properties.groups[0].title.startswith("Claraboia")
