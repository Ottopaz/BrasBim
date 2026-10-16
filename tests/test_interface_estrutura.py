# SPDX-License-Identifier: GPL-3.0-or-later
"""Laje, pilar e viga na interface (``spec/ui/10-laje-pilar-viga.md`` §11), com o Qt sem
tela: UI96 a UI109. O resultado é conferido no modelo IFC."""

import json
import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import ifcopenshell.util.element as ue
import numpy as np
import pytest

pytest.importorskip("PySide6")

from conftest import snapshot
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from test_interface import _click, _move

from brasbim.core import plan
from brasbim.core.document import Document
from brasbim.core.ops import History, Transaction
from brasbim.core.structure import beams, columns, slabs
from brasbim.core.structure import commands as sc
from brasbim.core.walls import commands as cmd
from brasbim.ui.main_window import delete_transaction
from brasbim.ui.tools import Mods


@pytest.fixture(autouse=True)
def _planta_visivel(window):
    """(0, 0) em (150, 450) a 50 px/m: os pontos dos testes caem dentro da planta."""
    window.plan.origin = QPointF(150, 450)


def _tool(window, name):
    window.activate_tool(name)
    return window.toolbox.active


def _type(window, ifc_class, name):
    return next(t for t in window.session.doc.ifc.by_type(ifc_class) if t.Name == name)


def _all(window, cls):
    return sorted(window.session.doc.ifc.by_type(cls), key=lambda e: e.id())


def _last_ops(window):
    return [op.op for op in window.session.history.undo_stack[-1].ops]


def _rect_walls(window, a=(0, 0), b=(5, 4)):
    s = window.session
    s.run(lambda: cmd.create_rectangle(s.doc, window.toolbox.tools["wall"].options.type,
                                       s.storey, a, b))


def _column(window, point=(2, 3), **options):
    s = window.session
    s.run(lambda: sc.create_column(s.doc, _type(window, "IfcColumnType", "Pilar 20×40"),
                                   s.storey, point, **options))
    return _all(window, "IfcColumn")[-1]


def _beam(window, a=(0, 0), b=(5, 0), **options):
    s = window.session
    s.run(lambda: sc.create_beam(s.doc, _type(window, "IfcBeamType", "Viga 14×40"),
                                 s.storey, a, b, **options))
    return _all(window, "IfcBeam")[-1]


def _slab(window, a=(0, 0), b=(5, 4), storey=None, name="Laje maciça 10 cm"):
    s = window.session
    s.run(lambda: sc.create_slab_rectangle(s.doc, _type(window, "IfcSlabType", name),
                                           storey or s.storey, a, b))
    return _all(window, "IfcSlab")[-1]


# --- UI96–UI99: ferramentas -------------------------------------------------------------


def test_ui96_ferramenta_pilar(window):
    s = window.session
    tool = _tool(window, "column")
    assert s.doc.get(tool.type).Name == "Pilar 20×40"
    assert window.options_bar.isVisible()
    _click(window, (2, 3))
    assert _last_ops(window) == ["column.create"]
    (column,) = _all(window, "IfcColumn")
    state = columns.read_state(s.doc, column)
    assert state["point"] == pytest.approx([2, 3]) and state["angle"] == pytest.approx(0)
    assert column.Name == "P1"
    _move(window, (6, 3))
    QTest.keyClick(window.plan, Qt.Key_Space)  # gira 90° antes do clique
    _click(window, (6, 3))
    assert columns.read_state(s.doc, _all(window, "IfcColumn")[-1])["angle"] == pytest.approx(90)


def test_ui97_pilar_no_canto_da_juncao(window):
    s = window.session
    _rect_walls(window)  # paredes por dentro do retângulo: canto externo em (0, 0)
    tool = _tool(window, "column")
    tool.insertion = (0, 0)  # canto inferior esquerdo, como na barra Opções
    tool.move((0.03, -0.02), Mods())
    assert tool.snapped.point == pytest.approx((0, 0))
    tool.press((0.03, -0.02), Mods())
    column = _all(window, "IfcColumn")[-1]
    ring = columns.outline(s.doc, columns.read_state(s.doc, column))
    assert min(ring) == pytest.approx((0, 0))  # o canto do pilar no ponto


def test_ui98_vigas_em_cadeia(window):
    s = window.session
    _tool(window, "beam")
    _click(window, (0, 0))
    _click(window, (5, 0))
    assert _last_ops(window) == ["beam.create"]
    _move(window, (5, 3))
    QTest.keyClick(window.plan, Qt.Key_Tab)
    QTest.keyClicks(window.plan.numeric, "4")
    QTest.keyClick(window.plan.numeric, Qt.Key_Return)
    assert _last_ops(window) == ["beam.create"]
    first, second = _all(window, "IfcBeam")
    assert beams.read_state(s.doc, first)["end"] == pytest.approx([5, 0])
    state = beams.read_state(s.doc, second)
    assert state["start"] == pytest.approx([5, 0]) and beams.length(state) == pytest.approx(4)
    assert (first.Name, second.Name) == ("V1", "V2")
    QTest.keyClick(window.plan, Qt.Key_Escape)  # encerra a cadeia
    assert window.toolbox.active.points == []


def test_ui99_laje_retangulo_e_poligono(window):
    s = window.session
    tool = _tool(window, "slab")
    tool.options.mode = "rectangle"
    _click(window, (0, 0))
    _click(window, (5, 4))
    (slab,) = _all(window, "IfcSlab")
    assert ue.get_pset(slab, "Qto_SlabBaseQuantities")["GrossArea"] == pytest.approx(20)
    tool.options.mode = "polygon"
    for p in [(0, 5), (4, 5), (4, 6), (2, 6), (2, 8), (0, 8)]:
        _click(window, p)
    _click(window, (0, 5))  # fecha no primeiro ponto
    slab = _all(window, "IfcSlab")[-1]
    assert len(slabs.read_state(s.doc, slab)["outline"]) == 6
    count = len(_all(window, "IfcSlab"))
    for p in [(10, 0), (14, 4), (14, 0), (10, 4)]:  # contorno que se cruza
        _click(window, p)
    assert tool.shape_preview()[0].style == "invalid"
    QTest.keyClick(window.plan, Qt.Key_Return)
    assert len(_all(window, "IfcSlab")) == count
    assert "se cruza" in s.messages[-1]["text"]
    QTest.keyClick(window.plan, Qt.Key_Escape)  # tira o último vértice
    assert len(tool.points) == 3


# --- UI100–UI104: planta, seleção, alças, painel, transformações ---------------------------


def test_ui100_planta(window):
    s = window.session
    _, superior = s.doc.storeys()
    wall = window.session.doc.get(_first_wall(window))
    column = _column(window, (2.5, 0))
    beam = _beam(window, (0, 2), (5, 2))
    upper = _slab(window, storey=superior)
    window.set_show_above(False)
    p = window.ctx.plan
    assert column.GlobalId in {r.key for r in p.regions}
    roles = [sh.role for sh in p.shapes if sh.owner in (column.GlobalId, wall.GlobalId)]
    assert roles.index("column") > roles.index("wall")  # o pilar por cima da parede
    assert [sh.role for sh in p.shapes if sh.owner == beam.GlobalId].count("beam_above") == 2
    assert upper.GlobalId not in {sh.owner for sh in p.shapes}
    s.set_storey(superior)
    window.ctx.invalidate()
    assert "slab_view" in [sh.role for sh in window.ctx.plan.shapes if sh.owner == upper.GlobalId]


def _first_wall(window):
    s = window.session
    s.run(lambda: cmd.create_wall(s.doc, window.toolbox.tools["wall"].options.type, s.storey,
                                  (0, 0), (5, 0), ref_line="axis"))
    return s.history.undo_stack[-1].ops[0].id


def test_ui101_clique_e_janela(window):
    s = window.session
    _rect_walls(window)
    slab = _slab(window)
    column = _column(window, (5, 4))
    window.activate_tool("select")
    _click(window, (2.5, 2))
    assert s.selection == {slab.GlobalId}
    _click(window, (1.0, 0.07))  # longe das alças da laje selecionada
    wall = next(iter(s.selection))
    assert s.doc.get(wall).is_a("IfcWall")
    _click(window, (4.95, 3.95))
    assert s.selection == {column.GlobalId}
    found = window.ctx.plan.in_rect((-1, -1), (2.5, 5), crossing=True)
    assert slab.GlobalId not in found


def test_ui102_alcas(window):
    s = window.session
    beam = _beam(window)
    slab = _slab(window, (0, 3), (4, 6))
    tool = _tool(window, "select")
    s.select([beam.GlobalId])
    tool.press((5, 0), Mods())
    tool.move((5.5, 0), Mods())
    assert tool.numeric(6.0)
    assert beams.length(beams.read_state(s.doc, beam)) == pytest.approx(6)
    s.select([slab.GlobalId])
    area = ue.get_pset(slab, "Qto_SlabBaseQuantities")["GrossArea"]
    tool.press((4, 6), Mods())  # vértice
    tool.move((5, 6), Mods())
    tool.release((5, 6), Mods())
    assert ue.get_pset(slab, "Qto_SlabBaseQuantities")["GrossArea"] > area
    state = slabs.read_state(s.doc, slab)
    i = min(range(len(state["outline"])), key=lambda k: state["outline"][k][1])
    a, b = state["outline"][i], state["outline"][(i + 1) % len(state["outline"])]
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)  # meio do lado de baixo
    tool.press(mid, Mods())
    tool.move((mid[0], mid[1] - 1), Mods())
    tool.release((mid[0], mid[1] - 1), Mods())
    assert min(q[1] for q in slabs.read_state(s.doc, slab)["outline"]) == pytest.approx(2)


def test_ui103_painel(window):
    s = window.session
    slab, column, beam = _slab(window), _column(window), _beam(window, (1, 1), (5, 1))
    assert s.run(lambda: sc.edit_element(s.doc, slab, top_offset=-0.05))
    assert slabs.read_state(s.doc, slab)["top_offset"] == pytest.approx(-0.05)
    s.select([column.GlobalId])
    window.properties._rebuild()
    assert window.properties.groups[0].title == "Pilar P1"
    s.run(lambda: sc.edit_element(s.doc, column, top_mode="fixed", fixed_height=3.0))
    assert ue.get_pset(column, "Qto_ColumnBaseQuantities")["Length"] == pytest.approx(3)
    s.select([beam.GlobalId])
    window.properties._rebuild()
    field = next(w for name, w in (r for g in window.properties.groups for r in g.rows)
                 if name == "Ângulo (°)")
    field.setText("90")
    field.editingFinished.emit()
    state = beams.read_state(s.doc, beam)
    assert state["start"] == pytest.approx([1, 1])
    assert state["end"] == pytest.approx([1, 5], abs=1e-9)


def test_ui104_transformar_mistura(window):
    s = window.session
    wall = s.doc.get(_first_wall(window))
    column, beam, slab = _column(window, (1, 2)), _beam(window, (0, 3), (4, 3)), _slab(window)
    before = snapshot(s.doc.ifc)
    gids = sorted(g.GlobalId for g in (wall, column, beam, slab))
    from brasbim.core import transform

    for build in (lambda: transform.move_elements(s.doc, gids, (1, 0)),
                  lambda: transform.rotate_elements(s.doc, gids, (0, 0), 0.5),
                  lambda: transform.mirror_elements(s.doc, gids, (0, 0), (0, 1))):
        assert s.run(build)
        ops = [op for op in s.history.undo_stack[-1].ops if op.op.endswith(".edit")]
        edited = {op.id for op in ops if op.op.split(".")[0] in ("column", "beam", "slab")}
        assert edited == {column.GlobalId, beam.GlobalId, slab.GlobalId}
    for _ in range(3):
        s.undo()
    assert snapshot(s.doc.ifc) == before
    s.select(gids)
    tx, _ = delete_transaction(s)
    assert {op.op for op in tx.ops} >= {"column.delete", "beam.delete", "slab.delete"}


# --- UI105–UI109: tipos, 3D, pavimentos, biblioteca, diário --------------------------------


def test_ui105_tipos(window):
    s = window.session
    c1, c2 = _column(window, (0, 0)), _column(window, (3, 0))
    t = _type(window, "IfcColumnType", "Pilar 20×40")
    profile = ue.get_material(t).MaterialProfiles[0].Profile
    assert s.run(lambda: sc.edit_type(s.doc, t, section={"shape": "rect", "b": 0.25,
                                                          "h": 0.50}))
    for column in (c1, c2):
        body = next(r for r in column.Representation.Representations
                    if r.RepresentationIdentifier == "Body")
        assert body.Items[0].SweptArea == profile
    assert (profile.XDim, profile.YDim) == pytest.approx((0.25, 0.5))
    from brasbim.ui.types_dialog import SlabTypesDialog

    slab_type = _type(window, "IfcSlabType", "Laje 12 cm com contrapiso")
    dialog = SlabTypesDialog(s, window, select=slab_type.GlobalId)
    names = [dialog.layers.item(r, 0).text() for r in range(dialog.layers.rowCount())]
    assert names == ["Contrapiso", "Concreto", "Reboco"]
    dialog.close()


def test_ui106_3d(window):
    s = window.session
    column, beam = _column(window), _beam(window)
    slab = _slab(window, name="Laje 12 cm com contrapiso")
    scene = window.scene
    window.scene.load(s.doc.ifc, s.doc)
    concrete = next(m for m in s.doc.ifc.by_type("IfcMaterial") if m.Name == "Concreto")
    from brasbim.ui.scene3d import color_of

    for element in (column, beam):
        assert scene.meshes[element.GlobalId].base == pytest.approx(color_of(concrete))
    parts = scene.meshes[slab.GlobalId].parts
    assert set(parts) == {"Contrapiso", "Concreto", "Reboco"}
    top = parts["Contrapiso"].reshape(-1, 3)[:, 2]
    assert top.min() == pytest.approx(-0.03) and top.max() == pytest.approx(0)
    hit = scene.pick((2.0, 3.0, 10.0), (0.0, 0.0, -1.0))
    assert hit is not None and hit[0] == column.GlobalId


def test_ui107_cota_do_superior(window):
    s = window.session
    _, superior = s.doc.storeys()
    column, beam = _column(window), _beam(window)
    upper = _slab(window, storey=superior)
    assert s.run(lambda: cmd.edit_storey(s.doc, superior, elevation=3.0))
    assert columns.height(s.doc, columns.read_state(s.doc, column)) == pytest.approx(3.0)
    assert beams.top_z(s.doc, beams.read_state(s.doc, beam)) == pytest.approx(3.0)
    m = window.scene.meshes[upper.GlobalId].vertices
    assert np.max(m[:, 2]) == pytest.approx(3.0)


def test_ui108_biblioteca(window):
    s = window.session
    names = {t.Name for c in ("IfcColumnType", "IfcBeamType", "IfcSlabType")
             for t in s.doc.ifc.by_type(c)}
    assert {"Pilar 14×30", "Pilar 20×20", "Pilar 20×40", "Pilar 25×50", "Pilar Ø30",
            "Viga 12×30", "Viga 14×40", "Viga 15×40", "Viga 20×50", "Laje maciça 10 cm",
            "Laje 12 cm com contrapiso", "Laje pré-moldada 12 cm", "Radier 15 cm"} <= names
    materials = {m.Name for m in s.doc.ifc.by_type("IfcMaterial")}
    assert {"Contrapiso", "Laje pré-moldada", "Reboco", "Concreto"} <= materials
    radier = _type(window, "IfcSlabType", "Radier 15 cm")
    assert radier.PredefinedType == "BASESLAB"


def test_ui109_diario_reaplicado(window):
    s = window.session
    _rect_walls(window)
    tool = _tool(window, "column")
    _click(window, (2, 3))
    _tool(window, "beam")
    _click(window, (0, 2))
    _click(window, (5, 2))
    QTest.keyClick(window.plan, Qt.Key_Escape)
    slab_tool = _tool(window, "slab")
    slab_tool.options.mode = "rectangle"
    _click(window, (0, 0))
    _click(window, (5, 4))
    column = _all(window, "IfcColumn")[-1]
    from brasbim.core import transform

    s.run(lambda: transform.rotate_elements(s.doc, [column.GlobalId], (2, 3), math.pi / 4))
    s.run(lambda: cmd.edit_storey(s.doc, s.doc.storeys()[1], elevation=3.0))
    assert tool.name == "column"
    journal = json.loads(json.dumps([tx.to_dict() for tx in s.history.journal]))
    other = Document.new(project_id=s.doc.ifc.by_type("IfcProject")[0].GlobalId)
    history = History(other)
    for tx in journal:
        history.commit(Transaction.from_dict(tx))
    assert snapshot(other.ifc) == snapshot(s.doc.ifc)
    assert plan.storey_plan(other, other.storeys()[0]).owners("column")


def test_paineis_barras_e_tipos_abrem(window):
    """Barra Opções, painel (um, vários) e janela de tipos de cada elemento montam sem
    erro (spec/ui 10 §3–§5)."""
    from brasbim.ui.types_dialog import BeamTypesDialog, ColumnTypesDialog, SlabTypesDialog

    s = window.session
    elements = [_column(window), _column(window, (3, 3)), _beam(window), _slab(window)]
    for name in ("column", "beam", "slab"):
        window.activate_tool(name)
        assert window.options_bar.actions()
    window.activate_tool("select")
    for group in ([elements[0]], [elements[2]], [elements[3]], elements[:2], elements):
        s.select([e.GlobalId for e in group])
        window.properties._rebuild()
        assert window.properties.groups[0].title
    for dialog_class, cls in ((ColumnTypesDialog, "IfcColumnType"),
                              (BeamTypesDialog, "IfcBeamType"),
                              (SlabTypesDialog, "IfcSlabType")):
        dialog = dialog_class(s, window)
        assert dialog.list.count() == len(s.doc.ifc.by_type(cls))
        dialog.name.setText(dialog.name.text() + " novo")
        assert dialog.apply()
        dialog.close()


def _field(window, name):
    return next(w for g in window.properties.groups for n, w in g.rows if n == name)


def test_dimensoes_na_hora_ferramenta_e_painel(window):
    """Decisão do revisor (2026-10-16): pilar e viga com as dimensões digitadas, sem
    cadastro de tamanhos (spec/ui 10 §3 e §4.3)."""
    s = window.session
    tool = _tool(window, "column")
    from PySide6.QtWidgets import QLabel

    labels = [w.text().strip() for w in window.options_bar.findChildren(QLabel)
              if w.isVisibleTo(window.options_bar)]
    assert "b" in labels and "h" in labels and "Tipo" not in labels
    tool.b, tool.h = 0.25, 0.60
    _click(window, (2, 3))
    first = _all(window, "IfcColumn")[-1]
    assert ue.get_type(first).Name == "Pilar 25×60"
    tool.shape, tool.d = "circle", 0.35
    _click(window, (6, 3))
    second = _all(window, "IfcColumn")[-1]
    assert ue.get_type(second).Name == "Pilar Ø35"
    beam_tool = _tool(window, "beam")
    beam_tool.options.b, beam_tool.options.h = 0.12, 0.50
    _click(window, (0, 0))
    _click(window, (4, 0))
    assert ue.get_type(_all(window, "IfcBeam")[-1]).Name == "Viga 12×50"
    # painel: muda só o pilar selecionado
    window.activate_tool("select")
    third = _column(window, (8, 3))  # 20 × 40 da biblioteca
    s.select([first.GlobalId])
    window.properties._rebuild()
    field = _field(window, "h (profundidade)")
    field.setText("0,70")
    field.editingFinished.emit()
    assert ue.get_type(first).Name == "Pilar 25×70"
    assert ue.get_type(third).Name == "Pilar 20×40"
    s.select([first.GlobalId, third.GlobalId])
    window.properties._rebuild()
    field = _field(window, "b (largura)")
    assert field.text() == ""  # "vários"
    field.setText("0,30")
    field.editingFinished.emit()
    assert ue.get_type(first).Name == "Pilar 30×70"
    assert ue.get_type(third).Name == "Pilar 30×40"


def test_al05_abertura_pela_mini_barra(window):
    """spec/ui 12 §3.3: Abertura na mini-barra da laje, modo Retângulo, dois cliques."""
    from brasbim.ui.tools import selection_actions

    s = window.session
    slab = _slab(window)
    window.activate_tool("select")
    s.select([slab.GlobalId])
    assert "slab_opening" in selection_actions(s.doc, s.selection)
    window.run_selection_action("slab_opening")
    tool = window.toolbox.active
    assert tool.name == "slab_opening" and tool.slab == slab.GlobalId
    _click(window, (4, 3))
    _move(window, (6, 5))  # sai da laje: vermelho
    assert tool.shape_preview()[0].style == "invalid"
    _click(window, (6, 5))
    assert not s.doc.ifc.by_type("IfcOpeningElement")
    QTest.keyClick(window.plan, Qt.Key_Escape)
    window.run_selection_action("slab_opening")
    _click(window, (1, 1))
    _click(window, (2, 3))
    (opening,) = s.doc.ifc.by_type("IfcOpeningElement")
    assert window.toolbox.active.name == "select"
    s.select([opening.GlobalId])
    window.properties._rebuild()
    assert window.properties.groups[0].title == "Abertura na laje"


def test_lc_laje_pelo_comodo_na_ferramenta(window):
    """spec/ui 12 §4: modo Pelo cômodo, pré-visualização e clique."""
    s = window.session
    _rect_walls(window)
    tool = _tool(window, "slab")
    tool.options.mode = "room"
    window.options_bar.show_for(tool)
    _move(window, (2, 2))
    assert tool.shape_preview() and len(tool.shape_preview()[0].points) == 4
    tool.move((5.8, 1), Mods())  # fora do cômodo
    assert tool.shape_preview() == []
    _click(window, (2, 2))
    (slab,) = _all(window, "IfcSlab")
    assert ue.get_pset(slab, "Qto_SlabBaseQuantities")["GrossArea"] == pytest.approx(20)
    tool.press((5.8, 1), Mods())
    assert "cômodo fechado" in s.messages[-1]["text"]
