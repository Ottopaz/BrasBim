# SPDX-License-Identifier: GPL-3.0-or-later
"""Área de seleção: ferramenta na planta (``spec/ui/38-area-de-selecao.md`` §2, §8): AS05."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from brasbim.core.walls import commands as cmd
from brasbim.core.walls.wall import read_state as read_wall
from brasbim.ui.tools import Mods


def _tool(window):
    window.activate_tool("selection_area")
    window.ctx.tol = 0.1
    return window.toolbox.active


def _click(tool, p):
    tool.move(p, Mods())
    tool.press(p, Mods())
    tool.release(p, Mods())


def _drag(tool, a, b):
    tool.move(a, Mods())
    tool.press(a, Mods())
    tool.move(b, Mods())
    tool.release(b, Mods())


def _wall(window, a, b):
    s = window.session
    assert s.run(lambda: cmd.create_wall(s.doc, window.toolbox.tools["wall"].options.type,
                                         s.storey, a, b))
    window.ctx.invalidate()
    return max(s.doc.ifc.by_type("IfcWall"), key=lambda e: e.id())


def test_as05_retangulo_poligono_e_esc(window):
    tool = _tool(window)
    _click(tool, (1.0, 1.0))
    assert window.ctx.area is None and tool.fields()  # largura e altura
    _click(tool, (4.0, 3.0))
    assert window.ctx.area.bounds() == pytest.approx((1, 1, 4, 3))
    _drag(tool, (10.0, 10.0), (12.0, 13.0))  # arrastado: outra área troca a anterior
    assert window.ctx.area.bounds() == pytest.approx((10, 10, 12, 13))
    tool.shape = "polygon"
    for p in ((0.0, 5.0), (3.0, 5.0), (3.0, 8.0)):
        _click(tool, p)
    assert window.ctx.area.bounds() == pytest.approx((10, 10, 12, 13))  # ainda desenhando
    _click(tool, (0.02, 5.03))  # fecha no primeiro ponto
    assert [pytest.approx(q) for q in window.ctx.area.points] == [(0, 5), (3, 5), (3, 8)]
    window.activate_tool("wall")
    assert window.ctx.area is not None  # fica ao trocar de ferramenta
    tool = _tool(window)
    window.plan.press_escape()  # Esc na ferramenta remove a área
    assert window.ctx.area is None and window.toolbox.active is tool
    window.plan.press_escape()  # sem área: volta para Selecionar
    assert window.toolbox.active.name == "select"


def test_as05_esticar_e_mover_a_area(window):
    wall = _wall(window, (0.0, 0.0), (5.0, 0.0))
    tool = _tool(window)
    _click(tool, (4.0, -1.0))
    _click(tool, (6.0, 1.0))
    _drag(tool, (5.0, 0.0), (6.5, 0.0))  # da ponta da parede: estica
    path = read_wall(window.session.doc, wall)["path"]
    assert path["start"] == pytest.approx([0, 0]) and path["end"] == pytest.approx([6.5, 0])
    assert window.ctx.area.bounds() == pytest.approx((5.5, -1, 7.5, 1))  # andou junto
    window.ctx.invalidate()
    _click(tool, (7.0, 0.6))  # ponto dentro que não é vértice: move só a área
    assert tool.fields()  # distância e ângulo até o destino
    _click(tool, (7.0, 2.6))
    assert window.ctx.area.bounds() == pytest.approx((5.5, 1, 7.5, 3))
    assert read_wall(window.session.doc, wall)["path"]["end"] == pytest.approx([6.5, 0])
    window.session.undo()  # Esticar é uma transação
    assert read_wall(window.session.doc, wall)["path"]["end"] == pytest.approx([5, 0])


def test_as05_todos_os_pavimentos_e_menu(window):
    tool = _tool(window)
    _click(tool, (0.0, 0.0))
    _click(tool, (2.0, 2.0))
    assert not window.ctx.area.all_storeys
    tool.set_all_storeys(True)  # barra Opções: vale para a área já desenhada
    assert window.ctx.area.all_storeys and window.ctx.area.bounds() == pytest.approx(
        (0, 0, 2, 2))
    window.remove_selection_area()  # Editar > Remover área de seleção
    assert window.ctx.area is None


def _area(window, a, b, all_storeys=False):
    tool = _tool(window)
    tool.set_all_storeys(all_storeys)
    _click(tool, a)
    _click(tool, b)
    window.activate_tool("select")


def test_as06_3d_da_area_recortado(window):
    inside = _wall(window, (0.0, 0.0), (10.0, 0.0))  # cruza a área: sai recortada
    far = _wall(window, (0.0, 20.0), (10.0, 20.0))  # longe: não entra
    assert window.open_area_3d() is None  # sem área: recusa
    _area(window, (2.0, -1.0), (5.0, 1.0))
    view = window.open_area_3d()
    assert window.tabs.currentWidget() is view and window.closable(view)
    view.rebuild()
    assert set(view.scene.meshes) == {inside.GlobalId}
    low, high = view.scene.bounds()
    assert (low[0], high[0]) == (pytest.approx(2.0), pytest.approx(5.0))
    xs = window.scene.meshes[inside.GlobalId].vertices[:, 0]
    assert xs.min() < 0.1 and xs.max() > 9.9  # o 3D principal não muda
    assert far.GlobalId in window.scene.meshes
    window.ctx.area = window.ctx.area.moved((0.0, 20.0))  # a aba acompanha a área
    view.rebuild()
    assert set(view.scene.meshes) == {far.GlobalId}
    window.close_tab(view)
    assert not window.area_views


def test_as06_concava_inteira_e_pavimentos(window):
    s = window.session
    wall = _wall(window, (0.0, 0.0), (10.0, 0.0))
    if len(s.doc.storeys()) < 2:
        assert s.run(lambda: cmd.create_storey(s.doc, "Superior", 2.8))
    s.set_storey(s.doc.storeys()[1])
    top = _wall(window, (0.0, 0.0), (10.0, 0.0))
    tool = _tool(window)
    tool.shape = "polygon"  # em L: côncavo, mostra os elementos inteiros
    for p in ((2.0, -1.0), (6.0, -1.0), (6.0, 3.0), (4.0, 3.0), (4.0, 1.0), (2.0, 1.0),
              (2.0, -1.0)):
        _click(tool, p)
    view = window.open_area_3d()
    view.rebuild()
    assert set(view.scene.meshes) == {top.GlobalId}  # este pavimento: só o de cima
    xs = view.scene.meshes[top.GlobalId].vertices[:, 0]
    assert xs.min() < 0.1 and xs.max() > 9.9
    tool.set_all_storeys(True)
    view.rebuild()
    assert set(view.scene.meshes) == {wall.GlobalId, top.GlobalId}
    s.run(lambda: cmd.create_wall(s.doc, window.toolbox.tools["wall"].options.type,
                                  s.storey, (3.0, 2.0), (3.0, 5.0)))  # o modelo muda
    view.rebuild()
    assert len(view.scene.meshes) == 3
