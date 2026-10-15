# SPDX-License-Identifier: GPL-3.0-or-later
"""Medidas ao desenhar e edição no 3D (``spec/ui/07-medidas-e-edicao-no-3d.md`` §6): UI61 a
UI72, com o Qt sem tela. O resultado é conferido no modelo IFC."""

import json
import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

pytest.importorskip("PySide6")

from conftest import snapshot
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from test_interface import _click, _door_on_south, _move, _rectangle, _walls

from brasbim.core import geom2d
from brasbim.core.document import Document
from brasbim.core.ops import History, Transaction
from brasbim.core.walls import commands as cmd
from brasbim.ui.scene3d import ray_plane
from brasbim.ui.tools import Mods, polar_point, rect_corner


@pytest.fixture(autouse=True)
def _planta_visivel(window):
    """(0, 0) em (150, 350): os pontos dos testes caem dentro da planta (464 × 530 px)."""
    window.plan.origin = QPointF(150, 350)


def _path(s, wall):
    return geom2d.path_from_dict(cmd.read_state(s.doc, wall)["path"])


def _ends(s, walls):
    return {tuple(round(c, 6) + 0.0 for c in p) for w in walls
            for p in (_path(s, w).start, _path(s, w).end)}


def _tab_values(window, *values, view=None):
    """Tab, digita cada valor (Tab entre eles) e Enter no quadro de medidas."""
    view = view or window.plan
    QTest.keyClick(view, Qt.Key_Tab)
    assert view.measure.isVisible() and view.measure.editing == 0
    for i, value in enumerate(values):
        QTest.keyClicks(view.numeric, value)
        if i < len(values) - 1:
            QTest.keyClick(view.numeric, Qt.Key_Tab)
    QTest.keyClick(view.numeric, Qt.Key_Return)


# --- UI61–UI66: campos de medida ------------------------------------------------------------


def test_ui61_parede_com_comprimento_e_angulo(window):
    s = window.session
    window.activate_tool("wall")
    _click(window, (0, 0))
    _move(window, (2, 1))
    tool = window.toolbox.active
    assert [f.label for f in tool.fields()] == ["Comprimento", "Ângulo"]
    assert window.plan.measure.isVisible()
    assert tool.fields()[0].value == pytest.approx(math.hypot(2, 1))
    _tab_values(window, "3", "90")
    QTest.keyClick(window.plan, Qt.Key_Return)  # encerra a cadeia
    (wall,) = _walls(s)
    path = _path(s, wall)
    assert path.start == pytest.approx((0, 0))
    assert path.end == pytest.approx((0, 3), abs=1e-9)


def test_ui62_valor_fixado_e_cursor(window):
    assert polar_point((0, 0), (10, 10), length=2.5) == pytest.approx((1.76777, 1.76777),
                                                                       abs=1e-5)
    assert polar_point((0, 0), (4, 3), angle=0) == pytest.approx((4, 0))
    assert rect_corner((0, 0), (-1, 2), width=4) == pytest.approx((-4, 2))
    tool = window.toolbox.activate("wall")
    tool.press((0, 0), Mods())
    tool.move((10, 10), Mods())
    tool.fix("length", 2.5)
    assert tool.snapped.point == pytest.approx((1.76777, 1.76777), abs=1e-5)
    tool.fix("length", None)
    tool.fix("angle", 0.0)
    tool.move((4, 3), Mods())
    assert tool.snapped.point == pytest.approx((4, 0))
    assert any(m.style == "guide" for m in tool.preview())  # guia do ângulo fixado
    tool.fix("length", 1.0)
    tool.move((-7, 5), Mods())  # os dois fixados: o cursor não muda nada
    assert tool.snapped.point == pytest.approx((1, 0))


def test_ui63_numero_sem_tab(window):
    s = window.session
    window.activate_tool("wall")
    _click(window, (1, 1))
    _move(window, (3, 1))
    QTest.keyClicks(window.plan, "3")
    assert window.plan.measure.editing == 0 and window.plan.numeric.text() == "3"
    QTest.keyClick(window.plan.numeric, Qt.Key_Return)
    QTest.keyClick(window.plan, Qt.Key_Return)
    (wall,) = _walls(s)
    assert _path(s, wall).end == pytest.approx((4, 1))


def test_ui64_esc_e_valor_invalido(window):
    s = window.session
    window.activate_tool("wall")
    tool = window.toolbox.active
    _click(window, (0, 0))
    _move(window, (2, 0))
    QTest.keyClick(window.plan, Qt.Key_Tab)
    QTest.keyClicks(window.plan.numeric, "0")
    QTest.keyClick(window.plan.numeric, Qt.Key_Return)
    assert "fdecea" in window.plan.numeric.styleSheet()  # vermelho
    assert window.plan.measure.editing == 0 and not tool.fixed
    assert s.messages[-1]["text"] == "comprimento pequeno demais"
    window.plan.numeric.clear()
    QTest.keyClicks(window.plan.numeric, "1")
    QTest.keyClick(window.plan.numeric, Qt.Key_Tab)
    assert tool.fixed == {"length": 1.0}
    QTest.keyClick(window.plan.numeric, Qt.Key_Escape)  # solta os valores fixados
    assert not tool.fixed and tool.points == [(0, 0)]
    assert window.plan.measure.editing is None
    QTest.keyClick(window.plan, Qt.Key_Escape)  # descarta a parede em andamento
    assert tool.points == [] and _walls(s) == []


def test_ui65_retangulo_com_largura_e_altura(window):
    s = window.session
    window.activate_tool("rectangle")
    _click(window, (1, 1))
    _move(window, (0, 3))  # cursor à esquerda e acima do 1º canto
    _tab_values(window, "4", "3")
    walls = _walls(s)
    assert len(walls) == 4
    assert _ends(s, walls) == {(1, 1), (-3, 1), (-3, 4), (1, 4)}


def test_ui66_mover_e_girar_com_campos(window):
    s = window.session
    walls = _rectangle(window)
    s.select([w.GlobalId for w in walls])
    window.activate_tool("move")
    _click(window, (0, 0))
    _move(window, (1, 1))
    _tab_values(window, "2", "180")
    assert _ends(s, walls) == {(-2, 0), (4, 0), (4, 4), (-2, 4)}
    assert s.history.undo_stack[-1].label == "Mover"
    window.activate_tool("rotate")
    _click(window, (0, 0))
    _click(window, (1, 0))
    _tab_values(window, "90")
    assert _ends(s, walls) == {(0, -2), (0, 4), (-4, 4), (-4, -2)}


# --- UI67–UI72: vista 3D ---------------------------------------------------------------------


def _split(window):
    window.set_view("split")
    QApplication.processEvents()
    window.view3d.fit()
    return window.view3d


def _screen(view, point) -> QPoint:
    x, y = view.camera.project(point, view.width(), view.height())
    return QPointF(x, y).toPoint()


def _top_center(view, gid):
    low, high = view.scene.selection_bounds({gid})
    return ((low[0] + high[0]) / 2, (low[1] + high[1]) / 2, high[2])


def _south(s, walls):
    return next(w for w in walls if _path(s, w).start == pytest.approx((6, 0)))


def test_ui67_escolha_por_raio(window):
    s = window.session
    walls = _rectangle(window)
    door = _door_on_south(window)
    south = _south(s, walls)
    scene = window.scene
    gid, point = scene.pick((1, 0.07, 10), (0, 0, -1))
    assert gid == south.GlobalId and point[2] == pytest.approx(2.8)
    low, high = scene.selection_bounds({door.GlobalId})
    center = (low + high) / 2
    gid, _ = scene.pick((center[0], -5, 1.0), (0, 1, 0))  # pelo vão: a porta é a primeira
    assert gid == door.GlobalId
    assert scene.pick((20, 20, 10), (0, 0, -1)) is None


def test_ui68_ponto_dado_no_3d(window):
    s = window.session
    walls = _rectangle(window)
    view = _split(window)
    south = _south(s, walls)
    top = _top_center(view, south.GlobalId)
    p = view.world_point(QPointF(_screen(view, top)))
    assert p == pytest.approx(top[:2], abs=0.05)  # o (x, y) do topo, não do piso
    p = view.world_point(QPointF(_screen(view, (8, 0, 0))))
    assert p == pytest.approx((8, 0), abs=0.05)  # no vazio: o plano do pavimento
    assert ray_plane(np.array([0, 0, 1.0]), np.array([1.0, 0, 0]), 0.0) is None


def test_ui69_selecao_no_3d(window):
    s = window.session
    walls = _rectangle(window)
    view = _split(window)
    south = _south(s, walls)
    east = next(w for w in walls if _path(s, w).start == pytest.approx((6, 4)))
    QTest.mouseClick(view, Qt.LeftButton, Qt.NoModifier, _screen(view, _top_center(
        view, south.GlobalId)))
    assert s.selection == {south.GlobalId}
    window.plan.repaint()  # a planta desenha a mesma seleção
    QTest.mouseClick(view, Qt.LeftButton, Qt.ControlModifier, _screen(view, _top_center(
        view, east.GlobalId)))
    assert s.selection == {south.GlobalId, east.GlobalId}
    yaw = view.camera.yaw
    start = _screen(view, _top_center(view, south.GlobalId))
    QTest.mousePress(view, Qt.LeftButton, Qt.NoModifier, start)
    QTest.mouseMove(view, start + QPoint(10, 0))
    QTest.mouseRelease(view, Qt.LeftButton, Qt.NoModifier, start + QPoint(10, 0))
    assert view.camera.yaw != yaw  # arrastar orbita
    assert s.selection == {south.GlobalId, east.GlobalId}  # e não seleciona
    QTest.mouseClick(view, Qt.LeftButton, Qt.NoModifier, QPoint(3, 3))  # céu: limpa
    assert s.selection == set()


def test_ui70_mover_no_3d_igual_a_planta(window):
    s = window.session
    walls = _rectangle(window)
    gids = [w.GlobalId for w in walls]
    view = _split(window)
    s.select(gids)
    window.activate_tool("move")
    for point in ((8, 0, 0), (10, 1, 0)):
        at = _screen(view, point)
        QTest.mouseMove(view, at)
        QTest.mouseClick(view, Qt.LeftButton, Qt.NoModifier, at)
    tx3d = s.history.undo_stack[-1].to_dict()
    assert tx3d["label"] == "Mover"
    assert _ends(s, walls) == {(2, 1), (8, 1), (8, 5), (2, 5)}

    data = json.loads(s.journal_path.read_text(encoding="utf-8"))
    other = Document.new(project_id=s.doc.project.GlobalId)
    history = History(other)
    for tx in data["transactions"]:
        history.commit(Transaction.from_dict(tx))
    assert snapshot(other.ifc) == snapshot(s.doc.ifc)

    s.undo()
    s.select(gids)
    window.plan.scale, window.plan.origin = 30.0, QPointF(20, 350)
    window.plan._sync_tol()
    window.activate_tool("move")
    _click(window, (8, 0))
    _click(window, (10, 1))
    assert s.history.undo_stack[-1].to_dict()["ops"] == tx3d["ops"]


def test_ui71_mostrar_na_planta(window):
    s = window.session
    terreo, superior = s.doc.storeys()
    wall_type = window.toolbox.tools["wall"].options.type
    s.run(lambda: cmd.create_wall(s.doc, wall_type, superior, (20, 10), (21, 10)))
    (wall,) = _walls(s)
    window.set_view("3d")
    assert s.storey.GlobalId == terreo.GlobalId
    s.select([wall.GlobalId])
    actions = dict(window.context_actions(window.view3d, wall.GlobalId))
    assert list(actions) == ["Mostrar na planta", "Enquadrar a seleção"]
    actions["Mostrar na planta"]()
    QApplication.processEvents()
    assert s.storey.GlobalId == superior.GlobalId
    assert window.tabs.currentWidget() is window.plan
    x0, y0, x1, y1 = window.plan.selection_rect()
    assert 0 <= x0 < x1 <= window.plan.width() and 0 <= y0 < y1 <= window.plan.height()
    assert x1 - x0 <= 220  # 1 m não ocupa a tela inteira (aproximação máxima)
    assert list(dict(window.context_actions(window.plan, wall.GlobalId))) == [
        "Mostrar no 3D", "Enquadrar a seleção"]
    assert list(dict(window.context_actions(window.plan, None))) == ["Enquadrar tudo"]


def test_ui72_mostrar_no_3d(window):
    s = window.session
    walls = _rectangle(window)
    south = _south(s, walls)
    s.select([south.GlobalId])
    view = window.view3d
    view.fit()
    yaw, pitch = view.camera.yaw, view.camera.pitch
    assert window.show_in_3d()
    low, high = window.scene.selection_bounds({south.GlobalId})
    assert view.camera.target == pytest.approx((low + high) / 2)
    assert (view.camera.yaw, view.camera.pitch) == (yaw, pitch)
    assert window.tabs.currentWidget() is view


def test_ui61b_quadro_mostra_a_medida_ao_vivo(window):
    """O quadro informa comprimento e ângulo enquanto se desenha; o campo aberto pelo Tab
    segue o cursor até a primeira tecla, e Tab sem digitar não fixa nada."""
    window.activate_tool("wall")
    tool = window.toolbox.active
    box = window.plan.measure
    _click(window, (0, 0))
    _move(window, (3, 0))
    assert box.isVisible()
    assert [e.text() for e in box.edits] == ["3,00", "0,0"]
    _move(window, (0, 2))
    assert [e.text() for e in box.edits] == ["2,00", "90,0"]
    QTest.keyClick(window.plan, Qt.Key_Tab)
    assert box.editing == 0 and box.edits[0].selectedText() == "2,00"
    _move(window, (4, 0))
    assert box.edits[0].text() == "4,00" and box.edits[1].text() == "0,0"
    QTest.keyClick(window.plan.numeric, Qt.Key_Tab)  # sem digitar: não fixa
    assert box.editing == 1 and not tool.fixed
    QTest.keyClicks(window.plan.numeric, "45")
    _move(window, (4, 1))
    assert box.edits[1].text() == "45"  # depois da tecla, o campo para de seguir
