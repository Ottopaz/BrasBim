# SPDX-License-Identifier: GPL-3.0-or-later
"""Cobertura na interface (spec/elementos/cobertura.md §4, §5, §7), com o Qt sem tela.
O resultado é conferido no modelo IFC."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from test_interface import _click, _move

from brasbim.core.structure import commands as sc
from brasbim.core.structure import roofs
from brasbim.core.walls import commands as cmd
from brasbim.ui.toolbars import ROOF_SHAPES


@pytest.fixture(autouse=True)
def _planta_visivel(window):
    window.plan.origin = QPointF(150, 450)


def _roofs(window):
    return sorted(window.session.doc.ifc.by_type("IfcRoof"), key=lambda e: e.id())


def _field(window, name):
    return next(w for g in window.properties.groups for n, w in g.rows if n == name)


def test_cb14_ferramenta_pelas_paredes(window):
    s = window.session
    s.run(lambda: cmd.create_rectangle(s.doc, window.toolbox.tools["wall"].options.type,
                                       s.storey, (0, 0), (8, 5)))
    window.activate_tool("roof")
    tool = window.toolbox.active
    assert tool.options.mode == "room" and tool.options.shape == "gable"
    assert s.doc.get(tool.options.type).Name == "Telha cerâmica"
    _move(window, (4, 2.5))
    assert tool.shape_preview()  # o contorno das paredes aparece
    _click(window, (4, 2.5))
    assert tool.pending is not None and not _roofs(window)
    QTest.keyClick(window.plan, Qt.Key_Return)  # cumeeira paralela ao lado maior
    (roof,) = _roofs(window)
    state = roofs.read_state(s.doc, roof)
    a, b = state["outline"][state["side"]], state["outline"][(state["side"] + 1) % 4]
    assert abs(a[1] - b[1]) < 1e-9  # lado horizontal (o maior)
    assert state["base_height"] == pytest.approx(roofs.wall_top(s.doc, s.storey))
    shapes = [sh for sh in window.ctx.plan.shapes if sh.owner == roof.GlobalId]
    assert [sh.role for sh in shapes] == ["roof_edge"]  # acima do plano de corte


def test_cb15_uma_agua_clicando_o_lado(window):
    s = window.session
    window.activate_tool("roof")
    tool = window.toolbox.active
    tool.options.mode, tool.options.shape, tool.options.overhang = "rectangle", "shed", 0.0
    _click(window, (0, 0))
    _click(window, (6, 4))
    _move(window, (3, 4.05))
    assert tool.side is not None
    _click(window, (3, 4.05))  # o lado de cima é o mais baixo
    (roof,) = _roofs(window)
    state = roofs.read_state(s.doc, roof)
    (face,) = roofs.faces(state)
    assert roofs.bottom_z(state, face, (3, 4)) < roofs.bottom_z(state, face, (3, 0))
    # Duas águas em L: recusada antes de pedir o lado.
    tool.options.mode, tool.options.shape = "polygon", "gable"
    for p in [(10, 0), (16, 0), (16, 3), (13, 3), (13, 5), (10, 5)]:
        _click(window, p)
    _click(window, (10, 0))
    assert tool.pending is None and len(_roofs(window)) == 1
    assert "retangular" in s.messages[-1]["text"]


def test_cb16_painel_e_barra(window):
    s = window.session
    tile = next(t for t in s.doc.ifc.by_type("IfcSlabType") if t.Name == "Telha cerâmica")
    s.run(lambda: sc.create_roof(s.doc, tile, s.storey, [(0, 0), (10, 0), (10, 6), (0, 6)],
                                 base_height=2.8))
    (roof,) = _roofs(window)
    parts = {p.GlobalId for p in roofs.parts_of(roof)}
    s.select([roof.GlobalId])
    window.properties._rebuild()
    assert window.properties.groups[0].title == "Cobertura 1"
    field = _field(window, "Inclinação (%)")
    field.setText("35")
    field.editingFinished.emit()
    assert roofs.read_state(s.doc, roof)["slope"] == pytest.approx(35)
    assert {p.GlobalId for p in roofs.parts_of(roof)} == parts
    combo = _field(window, "Forma")
    combo.setCurrentIndex(combo.findData("hip"))
    assert len(roofs.parts_of(roof)) == 4
    # A peça escolhida pela planta é a cobertura.
    assert window.ctx.plan.pick((5, -0.6), 0.05) == roof.GlobalId
    # A ferramenta Laje não oferece os tipos de cobertura.
    window.activate_tool("slab")
    names = {s.doc.get(g).Name for g in [window.toolbox.active.options.type]}
    assert "Telha cerâmica" not in names
    assert [v for v, *_ in ROOF_SHAPES] == list(roofs.SHAPES)


def test_cb17_3d_mostra_a_cobertura(window):
    from brasbim.ui.scene3d import Scene

    s = window.session
    tile = next(t for t in s.doc.ifc.by_type("IfcSlabType") if t.Name == "Telha cerâmica")
    s.run(lambda: sc.create_roof(s.doc, tile, s.storey, [(0, 0), (10, 0), (10, 6), (0, 6)],
                                 base_height=2.8))
    (roof,) = _roofs(window)
    scene = Scene()
    scene.load(s.doc.ifc, s.doc)
    assert roof.GlobalId in scene.meshes
    assert not {p.GlobalId for p in roofs.parts_of(roof)} & set(scene.meshes)
    hit = scene.pick((5, 1, 10), (0, 0, -1))
    assert hit is not None and hit[0] == roof.GlobalId
    s.run(lambda: sc.edit_element(s.doc, roof, shape="hip"))
    scene.update(s.doc.ifc, s.last_changed)
    assert roof.GlobalId in scene.meshes
    assert not set(scene.meshes) - {roof.GlobalId}
