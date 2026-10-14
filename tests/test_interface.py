# SPDX-License-Identifier: GPL-3.0-or-later
"""Interface 0.1 (``spec/ui/01-janela-e-ferramentas.md`` §12): UI01 a UI13, com o Qt sem
tela. As ferramentas são acionadas por eventos de mouse e teclado na planta ou chamadas
diretamente, e o resultado é conferido no modelo IFC."""

import json
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import ifcopenshell
import ifcopenshell.util.element as ue
import ifcopenshell.util.placement
import pytest

pytest.importorskip("PySide6")

from conftest import snapshot
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFormLayout, QLabel, QLineEdit, QPushButton
from test_porta_edicao import _foreign_door_ifc

from brasbim.core.document import Document
from brasbim.core.ops import History, Transaction
from brasbim.core.walls import commands as cmd
from brasbim.ui import feedback
from brasbim.ui import main_window as mw
from brasbim.ui.session import Session
from brasbim.ui.tools import Mods


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app, tmp_path):
    session = Session(journal_dir=tmp_path / "diarios")
    w = mw.MainWindow(session)
    w.resize(1200, 800)
    w.show()
    w.plan.scale, w.plan.origin = 50.0, QPointF(100, 600)
    w.plan._sync_tol()
    app.processEvents()
    yield w
    session.modified = False
    w.close()


def _ops(tx):
    return [op.op for op in tx.ops]


def _click(window, p, modifier=Qt.NoModifier):
    QTest.mouseClick(window.plan, Qt.LeftButton, modifier, window.plan.to_screen(p).toPoint())


def _move(window, p):
    QTest.mouseMove(window.plan, window.plan.to_screen(p).toPoint())


def _walls(session):
    return sorted(session.doc.ifc.by_type("IfcWall"), key=lambda w: w.GlobalId)


def _rectangle(window, a=(0, 0), b=(6, 4)):
    window.session.run(lambda: cmd.create_rectangle(
        window.session.doc, window.toolbox.tools["wall"].options.type, window.session.storey,
        a, b))
    return _walls(window.session)


def _field(window, label, kind=QLineEdit):
    QApplication.processEvents()  # o painel é refeito depois do evento atual
    form = window.properties.form
    for row in range(form.rowCount()):
        text = form.itemAt(row, QFormLayout.LabelRole)
        field = form.itemAt(row, QFormLayout.FieldRole)
        if text and field and isinstance(text.widget(), QLabel) \
                and text.widget().text() == label and isinstance(field.widget(), kind):
            return field.widget()
    raise LookupError(label)



# --- UI01 --------------------------------------------------------------------------------


def test_ui01_projeto_novo_e_salvar(window, tmp_path):
    s = window.session
    assert [st.Name for st in s.doc.storeys()] == ["Térreo", "Superior"]
    assert len(s.doc.ifc.by_type("IfcWallType")) == 2
    assert len(s.doc.ifc.by_type("IfcDoorType")) == 3
    assert s.history.undo_stack == [] and not s.modified
    assert s.storey.Name == "Térreo"
    _rectangle(window)
    path = tmp_path / "casa.ifc"
    s.save(str(path))
    assert snapshot(ifcopenshell.open(str(path))).keys() == snapshot(s.doc.ifc).keys()
    s.open(str(path))
    assert s.path == str(path) and len(_walls(s)) == 4


# --- UI02–UI05 ---------------------------------------------------------------------------


def test_ui02_cadeia_de_paredes_pela_planta(window):
    s = window.session
    window.activate_tool("wall")
    for p in [(0, 0), (4, 0), (4, 3), (1, 3)]:
        _click(window, p)
    QTest.keyClick(window.plan, Qt.Key_Return)
    (tx,) = s.history.undo_stack
    assert _ops(tx).count("wall.create") == 3
    assert _ops(tx).count("path_connection.create") == 2
    window.undo()
    assert not _walls(s)

    _click(window, (0, 0))
    _click(window, (2, 0))
    QTest.keyClick(window.plan, Qt.Key_Escape)  # descarta a cadeia
    assert not _walls(s) and len(s.history.undo_stack) == 0
    QTest.keyClick(window.plan, Qt.Key_Escape)  # sem nada em andamento: volta a Selecionar
    assert window.toolbox.active.name == "select"


def test_cadeia_fechada_no_ponto_inicial(window):
    window.activate_tool("wall")
    for p in [(0, 0), (4, 0), (4, 3), (0, 3), (0, 0)]:
        _click(window, p)
    (tx,) = window.session.history.undo_stack
    assert _ops(tx).count("wall.create") == 4
    assert _ops(tx).count("path_connection.create") == 4


def test_ui03_retangulo_e_arco(window):
    s = window.session
    window.activate_tool("rectangle")
    tool = window.toolbox.active
    tool.press((0, 0), Mods())
    tool.press((5, 3), Mods())
    starts = sorted(tuple(cmd.read_state(s.doc, w)["path"]["start"]) for w in _walls(s))
    assert starts == [(0, 0), (0, 3), (5, 0), (5, 3)]
    window.activate_tool("arc")
    tool = window.toolbox.active
    for p in [(8, 0), (10, 2), (12, 0)]:
        tool.press(p, Mods())
    arc = [w for w in _walls(s) if cmd.read_state(s.doc, w)["path"]["kind"] == "arc"]
    assert len(arc) == 1


def test_ui04_snap_na_extremidade(window):
    s = window.session
    s.run(lambda: cmd.create_wall(s.doc, window.toolbox.tools["wall"].options.type, s.storey,
                                  (0, 0), (4, 0)))
    window.activate_tool("wall")
    tool = window.toolbox.active
    near = (4.0 + 6 / window.plan.scale, 0.04)  # 6 px da extremidade
    tool.press(near, Mods())
    assert tool.points == [(4, 0)]
    tool.press((4, 3), Mods())
    tool.key("enter")
    tx = s.history.undo_stack[-1]
    assert "path_connection.create" in _ops(tx)

    tool.press(near, Mods(alt=True))  # Alt: sem atração
    assert tool.points[0] == pytest.approx(near)
    tool.cancel()


def test_ui05_entrada_numerica(window):
    s = window.session
    window.activate_tool("wall")
    _click(window, (1, 1))
    _move(window, (3, 1))
    QTest.keyClicks(window.plan, "3")
    assert window.plan.numeric.isVisible()
    QTest.keyClicks(window.plan.numeric, ",5")
    QTest.keyClick(window.plan.numeric, Qt.Key_Return)
    QTest.keyClick(window.plan, Qt.Key_Return)
    (wall,) = _walls(s)
    assert ue.get_pset(wall, "Qto_WallBaseQuantities")["Length"] == pytest.approx(3.5)


# --- UI06–UI09 ---------------------------------------------------------------------------


def test_ui06_porta_lado_dobradicas_e_arco(window):
    s = window.session
    walls = _rectangle(window)  # sentido horário, linha de referência na face esquerda
    window.activate_tool("door")
    tool = window.toolbox.active
    south = next(w for w in walls if cmd.read_state(s.doc, w)["path"]["start"] == [6.0, 0.0])
    # Parede sul vai de (6,0) a (0,0): a esquerda dela é -y (fora); a faixa fica em y 0..0,14.
    tool.move((3.0, 0.12), Mods())  # lado de dentro = direita da parede
    assert tool.target["wall"] == south.GlobalId and tool.target["opens_to"] == "right"
    QTest.keyClick(window.plan, Qt.Key_Tab)
    assert tool.hinges == "right"
    tool.press((3.0, 0.12), Mods())
    door = s.doc.ifc.by_type("IfcDoor")[0]
    assert ue.get_type(door).OperationType == "SINGLE_SWING_RIGHT"

    s.run(lambda: cmd.create_arc_wall(s.doc, window.toolbox.tools["wall"].options.type,
                                      s.storey, (10, 0), (12, 2), (14, 0), ref_line="axis"))
    tool.move((12, 2), Mods())
    assert "arco" in tool.target["error"]
    tool.press((12, 2), Mods())
    assert len(s.doc.ifc.by_type("IfcDoor")) == 1
    assert "arco" in s.messages[-1]["text"]


def _door_on_south(window, x=3.0):
    window.activate_tool("door")
    tool = window.toolbox.active
    tool.press((x, 0.12), Mods())
    window.activate_tool("select")
    return window.session.doc.ifc.by_type("IfcDoor")[-1]


def test_ui07_painel_da_porta(window):
    s = window.session
    _rectangle(window)
    door = _door_on_south(window)
    s.select([door.GlobalId])
    width = _field(window, "Largura")
    assert width.text() == "0,86"
    width.setText("0,96")
    width.editingFinished.emit()
    assert _ops(s.history.undo_stack[-1]) == ["opening.edit"]
    assert door.OverallWidth == pytest.approx(0.96)

    QApplication.processEvents()
    buttons = window.properties.findChildren(QPushButton)
    flip = next(b for b in buttons if b.text() == "Inverter dobradiças")
    flip.click()
    assert _ops(s.history.undo_stack[-1]) == ["door_type.create", "door_type.edit", "door.edit"]

    QApplication.processEvents()
    bad = _field(window, "Altura")
    bad.setText("3,5")  # mais alta que a parede: recusada, o painel volta ao valor
    bad.editingFinished.emit()
    assert s.messages[-1]["level"] == "recusa"
    QApplication.processEvents()
    assert _field(window, "Altura").text() == "2,13"


def test_ui08_arrastar_porta(window):
    s = window.session
    walls = _rectangle(window)
    door = _door_on_south(window)
    tool = window.toolbox.tools["select"]
    tool.press((3.0, 0.3), Mods())  # na folha aberta
    assert s.selection == {door.GlobalId}
    tool.move((4.0, 0.07), Mods())
    tool.release((4.0, 0.07), Mods())
    assert _ops(s.history.undo_stack[-1]) == ["opening.edit"]
    count = len(s.history.undo_stack)

    east = next(w for w in walls if cmd.read_state(s.doc, w)["path"]["start"] == [6.0, 4.0])
    tool.press((4.0, 0.3), Mods())
    tool.move((5.93, 2.0), Mods())  # outra parede
    tool.release((5.93, 2.0), Mods())
    assert fc_opening_host(door) == east

    tool.press((5.7, 2.0), Mods())
    tool.move((5.93, 3.9), Mods())  # não cabe: vermelho e nada muda
    assert tool.drag["target"]["error"]
    tool.release((5.93, 3.9), Mods())
    assert len(s.history.undo_stack) == count + 1


def fc_opening_host(door):
    return door.FillsVoids[0].RelatingOpeningElement.VoidsElements[0].RelatingBuildingElement


def test_ui09_excluir_parede_com_porta(window, monkeypatch):
    s = window.session
    walls = _rectangle(window)
    door = _door_on_south(window)
    wall = fc_opening_host(door)
    s.select([wall.GlobalId])
    asked = []
    monkeypatch.setattr(window, "confirm", lambda text: asked.append(text) or False)
    window.delete_selection()
    assert asked and len(_walls(s)) == 4  # recusou a confirmação
    monkeypatch.setattr(window, "confirm", lambda text: True)
    window.delete_selection()
    ops = _ops(s.history.undo_stack[-1])
    assert ops[:3] == ["filling.detach", "door.delete", "opening.delete"]
    assert ops[-1] == "wall.delete" and len(_walls(s)) == 3
    assert walls  # sem porta, nada a confirmar
    s.select([_walls(s)[0].GlobalId])
    monkeypatch.setattr(window, "confirm", lambda text: pytest.fail("não devia perguntar"))
    window.delete_selection()
    assert len(_walls(s)) == 2


# --- UI10–UI13 ---------------------------------------------------------------------------


def test_ui10_vistas_acompanham_o_modelo(window):
    s = window.session
    _rectangle(window)
    s.run(lambda: cmd.create_wall(s.doc, window.toolbox.tools["wall"].options.type, s.storey,
                                  (10, 0), (14, 0)))  # parede solta, sem junções
    loose = s.history.undo_stack[-1].ops[0].id
    door = _door_on_south(window)
    assert set(window.scene.meshes) >= {w.GlobalId for w in _walls(s)} | {door.GlobalId}
    loose_mesh = window.scene.meshes[loose]
    before = window.scene.tessellations
    window.toolbox.tools["select"].press((3.0, 0.3), Mods())
    window.toolbox.tools["select"].move((2.0, 0.07), Mods())
    window.toolbox.tools["select"].release((2.0, 0.07), Mods())
    # Só a parede do vão, as vizinhas dela (junções) e a porta são trianguladas de novo.
    assert window.scene.tessellations - before == 4
    assert window.scene.meshes[loose] is loose_mesh
    leaf = [sh for sh in window.ctx.plan.shapes if sh.owner == door.GlobalId]
    assert min(p[0] for sh in leaf for p in sh.points) < 2.0


def test_ui11_porta_de_outra_origem(window, tmp_path):
    src = tmp_path / "outro.ifc"
    gid = _foreign_door_ifc(src)
    s = window.session
    s.open(str(src))
    assert window.ctx.plan.owners("door").keys() == {gid}
    s.select([gid])
    door = s.doc.get(gid)
    world = door.ObjectPlacement
    start = (ifcopenshell.util.placement.get_local_placement(world))[:2, 3]
    tool = window.toolbox.tools["select"]
    tool.press(tuple(start + (0.3, 0.02)), Mods())
    tool.move((3.9, 2.1), Mods())
    tool.release((3.9, 2.1), Mods())
    assert _ops(s.history.undo_stack[-1]) == ["opening.edit"]


def test_ui12_observacao_e_diario(window, tmp_path):
    s = window.session
    _rectangle(window)
    _door_on_south(window)
    s.select([s.doc.ifc.by_type("IfcDoor")[0].GlobalId])
    note = feedback.write_note(s, "A porta abriu para o lado errado.", "Porta",
                               folder=tmp_path / "feedback")
    text = note.read_text(encoding="utf-8")
    assert "A porta abriu para o lado errado." in text
    assert "Ferramenta: Porta" in text and "IfcDoor" in text and "Criar porta" in text

    data = json.loads(s.journal_path.read_text(encoding="utf-8"))
    other = Document.new(project_id=s.doc.project.GlobalId)
    history = History(other)
    for tx in data["transactions"]:
        history.commit(Transaction.from_dict(tx))
    assert snapshot(other.ifc) == snapshot(s.doc.ifc)


def test_ui13_erro_inesperado_nao_fecha(window, tmp_path, monkeypatch):
    shown = []
    monkeypatch.setattr(mw.QMessageBox, "critical", lambda *a: shown.append(a))
    monkeypatch.setattr(feedback, "feedback_dir", lambda: tmp_path / "feedback")
    window.install_excepthook()
    try:
        raise RuntimeError("falha de teste")
    except RuntimeError as e:
        sys.excepthook(type(e), e, e.__traceback__)
    assert shown and "falha de teste" in shown[0][2]
    (report,) = (tmp_path / "feedback" / "diarios").glob("erro-*.md")
    assert "RuntimeError: falha de teste" in report.read_text(encoding="utf-8")
    sys.excepthook = sys.__excepthook__
