# SPDX-License-Identifier: GPL-3.0-or-later
"""Desenho 2D na interface (spec/ui/19-desenho-2d.md §3; D2D08), com o Qt sem tela."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF

from brasbim.core import display_layers
from brasbim.core.annotations import base
from brasbim.core.annotations import commands as ac
from brasbim.ui.tools import Mods


@pytest.fixture(autouse=True)
def _planta_visivel(window):
    window.plan.origin = QPointF(150, 450)


def _made(window, prefix):
    return [e for e in window.session.doc.ifc.by_type("IfcAnnotation")
            if (k := base.kind_of(e)) is not None and k.prefix == prefix]


def _clicks(window, name, *points):
    window.activate_tool(name)
    tool = window.toolbox.active
    for p in points:
        tool.move(p, Mods(alt=True))
        tool.press(p, Mods(alt=True))
    return tool


def _layer(window, element):
    doc = window.session.doc
    return display_layers.layer_name(doc, display_layers.layer_of(doc, element))


def test_d2d08_ferramentas(window, app):
    tool = _clicks(window, "circle2d", (1, 1))
    tool.move((2, 1), Mods(alt=True))
    assert tool.preview(), "o círculo aparece enquanto se escolhe o raio"
    assert [f.key for f in tool.fields()] == ["radius"]
    tool.press((2, 1), Mods(alt=True))
    (circle,) = _made(window, "circle2d")
    assert base.read_state(circle)["radius"] == pytest.approx(1.0)
    assert _layer(window, circle) == "Linhas e hachuras"
    _clicks(window, "arc2d", (4, 0), (5, 1), (6, 0))
    (arc,) = _made(window, "arc2d")
    assert base.read_state(arc)["radius"] == pytest.approx(1.0)
    _clicks(window, "radius_dim", (2, 1), (3, 2))
    (radius,) = _made(window, "radius_dim")
    assert base.read_state(radius)["ref"] == circle.GlobalId
    _clicks(window, "angle_dim", (0, 0), (2, 0), (0, 2), (1, 0.2))
    (angle,) = _made(window, "angle_dim")
    assert _layer(window, angle) == "Cotas"
    window.toolbox.tools["label"].ask = lambda current: "Nota livre"
    _clicks(window, "label", (8, 5), (9, 6))
    (label,) = _made(window, "label")
    assert base.read_state(label)["text"] == "Nota livre"
    assert _layer(window, label) == "Textos e rótulos"
    _clicks(window, "revision", (0, 3), (2, 4))
    (rev,) = _made(window, "revision")
    assert base.read_state(rev)["number"] == "1"
    window.activate_tool("spline2d")
    tool = window.toolbox.active
    for p in ((0, 6), (1, 7), (2, 6)):
        tool.move(p, Mods(alt=True))
        tool.press(p, Mods(alt=True))
    tool.key("enter")
    (curve,) = _made(window, "spline2d")
    assert len(base.read_state(curve)["points"]) == 3
    # painel de propriedades do círculo: raio editável
    s = window.session
    s.select([circle.GlobalId])
    window.properties._rebuild()
    names = [n for g in window.properties.groups for n, _ in g.rows if n]
    assert "Raio (m)" in names
    s.run(lambda: ac.edit_element(s.doc, circle, radius=1.5))
    assert base.read_state(circle)["radius"] == pytest.approx(1.5)
