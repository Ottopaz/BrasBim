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
    # a nova parte sobrepõe a primeira (0,20 × 0,40, topo em 0): avisa que recorta
    assert "sobrepostas" in dialog.note.text()
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


def test_pc06_editor_em_centimetros(window):
    """Com a unidade de trabalho em cm (spec/ui 44 §2a), o editor de perfis lê e mostra
    as medidas em cm; o perfil continua gravado em metros."""
    from brasbim.core import units

    s = window.session
    s.run(lambda: units.apply_preset(s.doc, "centimeters"))
    try:
        dialog = ProfilesDialog(s, window)
        dialog.show()
        dialog.add()  # retângulo 0,20 × 0,40
        assert "Largura 20" in dialog.size_label.text() and " cm " in dialog.size_label.text()
        for field, text in zip(dialog.rect_fields, ("-30", "0", "60", "10"), strict=True):
            field.setText(text)
        dialog.add_exact_rect()
        added = dialog.state["parts"][1]["outline"]
        assert [tuple(round(v, 4) for v in q) for q in added] == [
            (-0.3, 0.0), (0.3, 0.0), (0.3, 0.1), (-0.3, 0.1)]
        dialog.stretch_boxes["stretch_y"].setChecked(True)
        dialog.stretch_fields["stretch_y"].setText("-20")
        dialog._stretch_edited("stretch_y")
        assert dialog.apply()
        state = profile_defs.read_state(profile_defs.all_defs(s.doc)[0])
        assert state["stretch_y"] == pytest.approx(-0.2)
        dialog.load(dialog.current)
        assert dialog.stretch_fields["stretch_y"].text() == "-20"
        dialog.close()
    finally:
        s.run(lambda: units.apply_preset(s.doc, "meters"))


def test_pc13_ficha_giro_e_espelhar(window):
    """Ficha do pilar de perfil: altura nominal (só a direção que estica), giro e
    espelhar; a janela de tipos não perde o giro."""
    from PySide6.QtWidgets import QCheckBox, QLineEdit

    from brasbim.core.structure import commands as sc

    s = window.session
    def_id = _profile(window)
    s.run(lambda: sc.create_column(s.doc, None, s.storey, (2, 3), section={
        "shape": "custom", "profile": def_id, "b": 0.6, "h": 0.5}))
    column = max(s.doc.ifc.by_type("IfcColumn"), key=lambda e: e.id())

    def field(name):
        QApplication.processEvents()
        return next(w for g in window.properties.groups for n, w in g.rows if n == name)

    def section():
        return st_types.section(ue.get_type(column))

    s.select([column.GlobalId])
    QApplication.processEvents()
    names = [n for g in window.properties.groups for n, _ in g.rows]
    assert "Altura nominal" in names and "Largura nominal" not in names  # só estica em y
    turn = field("Giro do perfil (°)")
    assert isinstance(turn, QLineEdit)
    turn.setText("90")
    turn.editingFinished.emit()
    assert section()["angle"] == pytest.approx(90.0)
    mirror = field("Espelhar perfil")
    assert isinstance(mirror, QCheckBox) and not mirror.isChecked()
    mirror.click()
    assert section()["mirror"] and section()["angle"] == pytest.approx(90.0)
    # a janela de tipos guarda a seção com o giro e o espelhar
    dialog = ColumnTypesDialog(s, window, select=ue.get_type(column).GlobalId)
    assert dialog.read_section()["mirror"] is True
    dialog.close()


def test_pc15_criar_perfil_a_partir_da_selecao(window):
    from brasbim.core.walls import commands as wc

    s = window.session
    t = s.doc.ifc.by_type("IfcWallType")[0]
    s.run(lambda: wc.create_wall(s.doc, t, s.storey, (0, 0), (5, 0)))
    wall = s.doc.ifc.by_type("IfcWall")[-1]
    dialog = ProfilesDialog(s, window)
    dialog.from_selection()  # nada selecionado: recusa
    assert not profile_defs.all_defs(s.doc)
    assert s.messages[-1]["level"] == "recusa"
    s.select([wall.GlobalId])
    dialog.from_selection()
    (made,) = profile_defs.all_defs(s.doc)
    assert dialog.current == profile_defs.id_of(made)
    assert profile_defs.read_state(made)["uses"] == ["wall"]
    assert made.Name.startswith(t.Name)
    dialog.close()


def test_pc12_referencia_das_aberturas_no_editor(window):
    s = window.session
    dialog = ProfilesDialog(s, window)
    dialog.add()  # retângulo de x −0,10 a 0,10
    box = dialog.stretch_boxes["opening_ref"]
    box.setChecked(True)  # começa no meio do desenho
    assert dialog.state["opening_ref"] == pytest.approx(0.0)
    dialog.stretch_fields["opening_ref"].setText("0,05")
    dialog.stretch_fields["opening_ref"].textEdited.emit("0,05")
    assert dialog.apply()
    (made,) = profile_defs.all_defs(s.doc)
    assert profile_defs.read_state(made)["opening_ref"] == pytest.approx(0.05)
    dialog.close()


def test_pc17_editor_desenho_livre(window):
    """O editor desenha como a planta (pedido de 2026‑11‑05): aplicar com partes
    sobrepostas grava (recortadas), a medida digitada vale na unidade de trabalho,
    vértices atraem e se arrastam, e a recusa aparece no próprio diálogo."""
    from brasbim.core import units

    s = window.session
    s.run(lambda: units.apply_preset(s.doc, "centimeters"))
    try:
        dialog = ProfilesDialog(s, window)
        dialog.show()
        dialog.add()  # retângulo de x −10 a 10 cm, y −40 a 0
        canvas = dialog.canvas

        def at(p):
            return canvas.to_screen(p).toPoint()

        def move(p, buttons=Qt.NoButton):
            from PySide6.QtCore import QEvent
            from PySide6.QtGui import QMouseEvent

            q = QPointF(at(p))
            QApplication.sendEvent(canvas, QMouseEvent(
                QEvent.MouseMove, q, canvas.mapToGlobal(q), Qt.NoButton, buttons,
                Qt.NoModifier))

        # o meio da aresta direita atrai
        point, kind = canvas.snap(canvas.to_screen((0.101, -0.198)))
        assert kind == "meio" and point == pytest.approx((0.1, -0.2))
        # polígono por clique + medidas digitadas em cm: capa por cima do retângulo
        canvas.set_mode("polygon")
        QTest.mouseClick(canvas, Qt.LeftButton, Qt.NoModifier, at((-0.1, 0.0)))
        move((0.2, 0.0))  # direção: para a direita
        QTest.keyClicks(canvas, "30")
        QTest.keyClick(canvas, Qt.Key_Return)
        QTest.keyClicks(canvas, "-5;5")  # deslocamento x;y
        QTest.keyClick(canvas, Qt.Key_Return)
        QTest.keyClicks(canvas, "-25;0")
        QTest.keyClick(canvas, Qt.Key_Return)
        QTest.keyClick(canvas, Qt.Key_Return)  # Enter sem medida fecha
        cap = dialog.state["parts"][-1]["outline"]
        assert [tuple(round(v, 4) for v in q) for q in cap] == [
            (-0.1, 0.0), (0.2, 0.0), (0.15, 0.05), (-0.1, 0.05)]
        # arrastar um vértice da capa, com atração à grade de 1 cm
        canvas.set_mode("select")
        canvas.scale, canvas.center = 2000.0, (0.1, 0.0)  # perto: grade de 1 cm
        canvas.select(len(dialog.state["parts"]) - 1)
        QTest.mousePress(canvas, Qt.LeftButton, Qt.NoModifier, at((0.15, 0.05)))
        move((0.1702, 0.0699), Qt.LeftButton)
        QTest.mouseRelease(canvas, Qt.LeftButton, Qt.NoModifier, at((0.1702, 0.0699)))
        assert dialog.state["parts"][-1]["outline"][2] == pytest.approx([0.17, 0.07])
        # Ctrl+Z do editor desfaz o arrastar
        QTest.keyClick(canvas, Qt.Key_Z, Qt.ControlModifier)
        assert dialog.state["parts"][-1]["outline"][2] == pytest.approx([0.15, 0.05])
        # retângulo sobreposto ao primeiro: aplicar grava, recortado
        dialog.canvas.add_outline([[-0.05, -0.2], [0.05, -0.2], [0.05, -0.1], [-0.05, -0.1]])
        assert dialog.apply()
        parts = profile_defs.read_state(profile_defs.all_defs(s.doc)[0])["parts"]
        assert len(parts) == 3 and len(parts[0]["holes"]) == 1  # o de baixo foi furado
        # recusa (linha de esticar fora do perfil): aparece no diálogo
        dialog.stretch_boxes["stretch_x"].setChecked(True)
        dialog.stretch_fields["stretch_x"].setText("500")
        dialog._stretch_edited("stretch_x")
        from unittest import mock

        with mock.patch("brasbim.ui.profiles_dialog.QMessageBox.warning") as warning:
            assert not dialog.apply()
        assert warning.called and "Não aplicado" in dialog.note.text()
        dialog.dirty = False
        dialog.close()
    finally:
        s.run(lambda: units.apply_preset(s.doc, "meters"))


def test_pc18_ficha_poe_e_tira_o_perfil(window):
    """Pilar e viga que já existem: "Perfil do projeto" na ficha põe o perfil (na medida
    do desenho) e "Nenhum" volta ao retângulo."""
    from PySide6.QtWidgets import QComboBox

    from brasbim.core.structure import commands as sc

    s = window.session
    def_id = _profile(window)
    s.run(lambda: sc.create_column(s.doc, None, s.storey, (2, 3),
                                   section={"shape": "rect", "b": 0.2, "h": 0.4}))
    column = max(s.doc.ifc.by_type("IfcColumn"), key=lambda e: e.id())

    def combo():
        QApplication.processEvents()
        return next(w for g in window.properties.groups for n, w in g.rows
                    if n == "Perfil do projeto")

    s.select([column.GlobalId])
    box = combo()
    assert isinstance(box, QComboBox) and box.currentData() is None
    box.setCurrentIndex(box.findData(def_id))
    section = st_types.section(ue.get_type(column))
    assert (section["shape"], section["profile"]) == (profiles.CUSTOM, def_id)
    assert (section["b"], section["h"]) == pytest.approx((0.6, 0.5))
    box = combo()
    box.setCurrentIndex(box.findData(None))
    section = st_types.section(ue.get_type(column))
    assert section == {"shape": "rect", "b": pytest.approx(0.6), "h": pytest.approx(0.5)}
