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
