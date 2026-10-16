# SPDX-License-Identifier: GPL-3.0-or-later
"""Documentação da planta na interface (spec/ui 13), com o Qt sem tela: ferramentas,
barra Opções, painel, escala, espessuras (DO03) e os aceites de interface."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from test_interface import _click, _move

from brasbim.core import storeys
from brasbim.core.annotations import base, dimensions, drafting
from brasbim.core.annotations import commands as ac
from brasbim.core.walls import commands as cmd
from brasbim.ui.tools import Mods


@pytest.fixture(autouse=True)
def _planta_visivel(window):
    window.plan.origin = QPointF(150, 450)


def _rect(window, a=(0, 0), b=(5, 4)):
    s = window.session
    s.run(lambda: cmd.create_rectangle(s.doc, window.toolbox.tools["wall"].options.type,
                                       s.storey, a, b))


def _tool(window, name):
    window.activate_tool(name)
    return window.toolbox.active


def _annotations(window, kind):
    return [e for e in window.session.doc.ifc.by_type("IfcAnnotation")
            if base.kind_of(e) is kind]


def test_ambiente_pelo_comodo_e_painel(window):
    s = window.session
    _rect(window)
    tool = _tool(window, "space")
    tool.options.name = "Sala"
    _move(window, (2, 2))
    assert tool.shape_preview()
    _click(window, (2, 2))
    (space,) = s.doc.ifc.by_type("IfcSpace")
    assert (space.Name, space.LongName) == ("01", "Sala")
    labels = [lb for lb in window.ctx.plan.labels if lb.kind == "space"]
    assert labels[0].code == "Sala" and labels[0].size == "17,56 m²"
    window.activate_tool("select")
    _click(window, (2.5, 2.0))
    assert s.selection == {space.GlobalId}
    window.properties._rebuild()
    assert window.properties.groups[0].title == "Ambiente 01"


def test_cota_com_pontos_presos(window):
    s = window.session
    _rect(window)
    tool = _tool(window, "dimension")
    tool.direction = "horizontal"
    tool.move((0.0, 0.0), Mods())
    assert tool.hover is not None and tool.hover[1]["kind"] == "wall"
    tool.press((0.0, 0.0), Mods())
    tool.move((5.0, 0.0), Mods())
    tool.press((5.0, 0.0), Mods())
    tool.move((2.5, -0.8), Mods())
    assert tool.preview() and tool.labels()
    tool.press((2.5, -0.8), Mods())
    (dim,) = _annotations(window, dimensions.DIMENSION)
    state = base.read_state(dim)
    assert all(p["ref"] for p in state["points"])
    assert [t.text for t in base.build(s.doc, dim).texts] == ["5,00"]


def test_cotar_parede_pela_mini_barra(window):
    s = window.session
    _rect(window)
    wall = min(s.doc.ifc.by_type("IfcWall"), key=lambda w: w.GlobalId)
    s.select([wall.GlobalId])
    window.run_selection_action("auto_dimension")
    (dim,) = _annotations(window, dimensions.DIMENSION)
    assert base.build(s.doc, dim).texts


def test_nivel_norte_linha_hachura(window):
    _tool(window, "level_mark")
    _click(window, (1, 1))
    assert _annotations(window, drafting.LEVEL)
    tool = _tool(window, "north")
    tool.press((6, 1), Mods())
    tool.press((6, 3), Mods())
    (north,) = _annotations(window, drafting.NORTH)
    assert base.read_state(north)["angle"] == pytest.approx(90)
    line = _tool(window, "line2d")
    line.options.dash = "dashed"
    for p in [(0, 5), (2, 5), (2, 6)]:
        _click(window, p)
    QTest.keyClick(window.plan, Qt.Key_Return)
    (ln,) = _annotations(window, drafting.LINE)
    assert len(base.read_state(ln)["points"]) == 3
    hatch = _tool(window, "hatch")
    hatch.options.pattern = "cross"
    _click(window, (3, 1))
    _click(window, (4, 2))
    (h,) = _annotations(window, drafting.HATCH)
    assert h.GlobalId in {r.key for r in window.ctx.plan.regions}


def test_texto_digitado_e_editado(window):
    s = window.session
    tool = _tool(window, "text")
    tool.ask = lambda current: "PLANTA BAIXA"
    tool.options.size = 5.0
    _click(window, (1, 1))
    (text,) = _annotations(window, drafting.TEXT)
    assert base.read_state(text)["text"] == "PLANTA BAIXA"
    select = _tool(window, "select")
    select.ask_text = lambda current: current + "\nesc. 1:50"
    p = base.build(s.doc, text).texts[0].at
    select.double((p[0] + 0.3, p[1] + 0.1), Mods())
    assert base.read_state(text)["text"] == "PLANTA BAIXA\nesc. 1:50"
    s.select([text.GlobalId])
    window.properties._rebuild()
    assert window.properties.groups[0].title == "Texto"


def test_escala_pela_barra_de_estado(window):
    s = window.session
    combo = window.scale_combo
    assert combo.currentData() == 50
    combo.setCurrentIndex(combo.findData(100))
    assert storeys.scale(s.storey) == 100
    labels = window.ctx.plan.labels
    assert all(lb.height == pytest.approx(0.25) for lb in labels)  # 2,5 mm a 1:100
    s.undo()
    window._refresh_all()
    assert window.scale_combo.currentData() == 50


def test_do03_espessuras_de_linha(window):
    assert window.plan.show_weights
    window.weights_action.trigger()
    assert window.plan.show_weights is False
    assert window.plan._line_px(0.5) == 1.0
    window.plan.grab()
    window.weights_action.trigger()
    assert window.plan._line_px(0.5) > 1.0


def test_paineis_das_anotacoes(window):
    s = window.session
    _rect(window)
    s.run(lambda: ac.create_dimension(s.doc, s.storey, [(0, 0), (5, 0)], offset=-0.6))
    for kind, fields in ((drafting.LINE, {"points": [[0, 0], [1, 1]]}),
                         (drafting.HATCH, {"outline": [[0, 0], [1, 0], [1, 1]]}),
                         (drafting.NORTH, {"at": [3, 3]}),
                         (drafting.LEVEL, {"at": [2, 2]})):
        s.run(lambda k=kind, f=fields: ac.create_annotation(s.doc, k.prefix, s.storey, **f))
    for element in s.doc.ifc.by_type("IfcAnnotation"):
        s.select([element.GlobalId])
        window.properties._rebuild()
        assert window.properties.groups[0].title
