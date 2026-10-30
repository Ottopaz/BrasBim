# SPDX-License-Identifier: GPL-3.0-or-later
"""Perfil complexo na interface (spec/ui 41 §4, PC06): Projeto > Perfis, as ferramentas
Pilar e Viga com perfil e a janela de tipos. Qt sem tela; o resultado é conferido no
modelo IFC."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import ifcopenshell.util.element as ue
import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel
from test_interface import _click

from brasbim.core import profile_defs
from brasbim.core.structure import profiles
from brasbim.core.structure import types as st_types
from brasbim.ui.profiles_dialog import ProfilesDialog
from brasbim.ui.types_dialog import BeamTypesDialog, ColumnTypesDialog

TEE = {"name": "Viga T", "uses": ["beam", "column"], "stretch_x": None, "stretch_y": -0.3,
       "parts": [{"material": "Concreto", "role": "core",
                  "outline": [[-0.3, -0.1], [0.3, -0.1], [0.3, 0.0], [-0.3, 0.0]]},
                 {"material": "Concreto", "role": "core",
                  "outline": [[-0.1, -0.5], [0.1, -0.5], [0.1, -0.1], [-0.1, -0.1]]}]}


@pytest.fixture(autouse=True)
def _planta_visivel(window):
    window.plan.origin = QPointF(150, 450)


def _profile(window, state=None) -> str:
    s = window.session
    holder = {}

    def build():
        tx = profile_defs.create(s.doc, state or TEE)
        holder["id"] = tx.ops[0].id
        return tx

    assert s.run(build)
    return holder["id"]


def _labels(window):
    QApplication.processEvents()  # a barra posiciona os widgets novos no laço de eventos
    return [w.text().strip() for w in window.options_bar.findChildren(QLabel)
            if w.isVisibleTo(window.options_bar)]


def test_pc06_editor_de_perfis(window):
    s = window.session
    assert "Perfis" in [a.text() for m in window.menuBar().actions() if m.menu()
                        for a in m.menu().actions()]
    dialog = ProfilesDialog(s, window)
    dialog.show()
    assert dialog.list.count() == 0 and not dialog.editor.isEnabled()
    dialog.add()  # Novo: retângulo 0,20 × 0,40 com a origem no meio do topo
    (definition,) = profile_defs.all_defs(s.doc)
    assert dialog.current == profile_defs.id_of(definition)
    assert profile_defs.read_state(definition)["uses"] == ["wall", "beam", "column"]
    # retângulo por cliques na área de desenho: dois cantos, com atração à grade
    canvas = dialog.canvas
    canvas.set_mode("rect")
    for p in ((-0.3, -0.1), (0.3, 0.0)):
        QTest.mouseClick(canvas, Qt.LeftButton, Qt.NoModifier,
                         canvas.to_screen(p).toPoint())
    assert len(dialog.state["parts"]) == 2
    added = dialog.state["parts"][1]["outline"]
    assert [tuple(round(v, 2) for v in q) for q in added] == [
        (-0.3, -0.1), (0.3, -0.1), (0.3, 0.0), (-0.3, 0.0)]
    # a nova parte sobrepõe a primeira (0,20 × 0,40, topo em 0): o aviso aparece
    assert "sobrepõem" in dialog.note.text()
    canvas.remove_selected()
    # por medidas: x, y, largura, altura
    for field, text in zip(dialog.rect_fields, ("-0,3", "0", "0,6", "0,1"), strict=True):
        field.setText(text)
    dialog.add_exact_rect()
    dialog.stretch_boxes["stretch_y"].setChecked(True)
    dialog.stretch_fields["stretch_y"].setText("-0,2")
    dialog._stretch_edited("stretch_y")
    dialog.name.setText("Viga com mesa")
    dialog._name_edited("Viga com mesa")
    assert dialog.apply()
    state = profile_defs.read_state(profile_defs.all_defs(s.doc)[0])
    assert state["name"] == "Viga com mesa" and state["stretch_y"] == pytest.approx(-0.2)
    assert len(state["parts"]) == 2
    assert dialog.list.item(0).text().startswith("Viga com mesa")
    # desfazer volta o perfil de antes
    s.history.undo()
    assert profile_defs.read_state(profile_defs.all_defs(s.doc)[0])["name"] == "Novo perfil"
    dialog.close()


def test_pc06_pilar_e_viga_com_perfil_pela_ferramenta(window):
    s = window.session
    def_id = _profile(window)
    window.activate_tool("column")
    tool = window.toolbox.active
    tool.use_profile(def_id)
    window.options_bar.show_for(tool)
    labels = _labels(window)
    assert "Seção" in labels and "Inserção" not in labels  # inserção = origem do perfil
    assert "h" in labels and "b" not in labels  # só estica na altura
    _click(window, (2, 3))
    column = max(s.doc.ifc.by_type("IfcColumn"), key=lambda e: e.id())
    section = st_types.section(ue.get_type(column))
    assert (section["shape"], section["profile"]) == (profiles.CUSTOM, def_id)
    assert ue.get_type(column).Name.startswith("Pilar Viga T")

    window.activate_tool("beam")
    tool = window.toolbox.active
    tool.options.use_profile(def_id)
    tool.options.h = 0.7
    window.options_bar.show_for(tool)
    _click(window, (0, 0))
    _click(window, (4, 0))
    QTest.keyClick(window.plan, Qt.Key_Escape)
    beam = max(s.doc.ifc.by_type("IfcBeam"), key=lambda e: e.id())
    section = st_types.section(ue.get_type(beam))
    assert (section["profile"], section["h"]) == (def_id, pytest.approx(0.7))
    assert profiles.area(section) == pytest.approx(0.06 + 0.2 * 0.6)


def test_pc06_tipos_com_perfil(window):
    s = window.session
    def_id = _profile(window)
    for dialog_class in (ColumnTypesDialog, BeamTypesDialog):
        dialog = dialog_class(s, window)
        dialog.shape.setCurrentIndex(dialog.shape.findData(profiles.CUSTOM))
        assert dialog.profile.currentData() == def_id
        assert not dialog.material_row.isVisibleTo(dialog)
        assert dialog.preview.section["parts"]
        assert dialog.apply()
        element_type = s.doc.get(dialog.current)
        assert st_types.profile_def_of(element_type) == def_id
        dialog.duplicate()
        copy = s.doc.get(dialog.current)
        assert copy.GlobalId != element_type.GlobalId
        assert st_types.profile_def_of(copy) == def_id
        dialog.close()
    assert len(profile_defs.users(s.doc, def_id)) == 4


def test_pc06_3d_por_material(window):
    """No 3D, cada parte do perfil com a cor do seu material."""
    from brasbim.core.structure import commands as sc
    from brasbim.ui.scene3d import Scene

    s = window.session
    state = dict(TEE, parts=[dict(TEE["parts"][0]),
                             dict(TEE["parts"][1], material="Bloco cerâmico")])
    def_id = _profile(window, state)
    section = {"shape": "custom", "profile": def_id, "b": 0.6, "h": 0.5}
    s.run(lambda: sc.create_beam(s.doc, None, s.storey, (0, 0), (4, 0), section=section))
    beam = max(s.doc.ifc.by_type("IfcBeam"), key=lambda e: e.id())
    scene = Scene()
    scene.load(s.doc.ifc, s.doc)
    mesh = scene.meshes[beam.GlobalId]
    assert set(mesh.parts) == {"Concreto", "Bloco cerâmico"}
    assert len(mesh.vertices) == sum(len(t) * 3 for t in mesh.parts.values())


def test_pc06_tipo_de_parede_com_perfil(window):
    """Janela de tipos de parede: Estrutura > Perfil do projeto; a parede refaz e o 3D
    pinta cada parte com o seu material."""
    from test_parede_perfil import muro

    from brasbim.core.walls import commands as wc
    from brasbim.core.walls import types as wall_types
    from brasbim.ui.scene3d import Scene
    from brasbim.ui.types_dialog import WallTypesDialog

    s = window.session
    def_id = _profile(window, muro())
    t = window.toolbox.tools["wall"].options.type
    s.run(lambda: wc.create_wall(s.doc, t, s.storey, (0, 0), (5, 0)))
    wall = max(s.doc.ifc.by_type("IfcWall"), key=lambda e: e.id())
    dialog = WallTypesDialog(s, window, select=t)
    assert dialog.structure.isVisibleTo(dialog)
    dialog.structure.setCurrentIndex(dialog.structure.findData("profile"))
    assert dialog.profile.currentData() == def_id
    assert dialog.profile_b.text() == "0,20" and dialog.profile_b.isReadOnly()
    assert not dialog.layers.isVisibleTo(dialog)
    assert dialog.apply()
    assert wall_types.profile_of(s.doc.get(t)) == {"id": def_id, "b": 0.2}
    scene = Scene()
    scene.load(s.doc.ifc, s.doc)
    assert set(scene.meshes[wall.GlobalId].parts) == {"Bloco cerâmico", "Concreto"}
    s.history.undo()  # volta às camadas
    assert wall_types.profile_of(s.doc.get(t)) is None
    dialog.close()
