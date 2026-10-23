# SPDX-License-Identifier: GPL-3.0-or-later
"""Pacote de precisão na interface (spec/ui/23-precisao.md §11): PR06, PR07, PR13, PR14 e
as ferramentas de edição, com o Qt sem tela."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import math

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent

from brasbim.core.annotations import base
from brasbim.core.annotations import commands as ac
from brasbim.core.walls import commands as wc
from brasbim.ui.command_search import Command, search
from brasbim.ui.tools import Mods


@pytest.fixture(autouse=True)
def _planta_visivel(window):
    window.plan.origin = QPointF(150, 450)


def _key(window, key, modifiers=Qt.NoModifier):
    window.plan.keyPressEvent(QKeyEvent(QEvent.KeyPress, key, modifiers))


def _walls(window):
    return window.session.doc.ifc.by_type("IfcWall")


def _path(window, wall):
    return wc.read_state(window.session.doc, wall)["path"]


def test_pr06_setas_travam_o_eixo(window, app):
    window.activate_tool("wall")
    tool = window.toolbox.active
    tool.move((0, 0), Mods(alt=True))
    tool.press((0, 0), Mods(alt=True))
    tool.move((3, 0.7), Mods(alt=True))
    _key(window, Qt.Key_Right)
    assert window.ctx.axis_lock[0] == "x"
    assert tool.snapped.point == pytest.approx((3, 0))
    # ponto atraído: vale a projeção dele na trava
    doc, storey = window.session.doc, window.session.storey
    window.session.run(lambda: ac.create_annotation(doc, "line2d", storey,
                                                    points=[[4, 2], [4, 5]]))
    window.ctx.invalidate()
    tool.move((4.03, 2.02), Mods())
    assert tool.snapped.point == pytest.approx((4, 0))
    assert tool.snapped.source == pytest.approx((4, 2))
    tool.press((4.03, 2.02), Mods())
    tool.move((4, 3), Mods(alt=True))
    assert tool.snapped.point == pytest.approx((4, 3)), "a trava caiu ao confirmar"
    _key(window, Qt.Key_Up)
    tool.move((5, 3), Mods(alt=True))
    assert tool.snapped.point == pytest.approx((4, 3))
    _key(window, Qt.Key_Up)  # a mesma seta solta
    tool.move((5, 3), Mods(alt=True))
    assert tool.snapped.point == pytest.approx((5, 3))


def test_pr07_enter_repete_a_ferramenta(window, app):
    window.activate_tool("line2d")
    window.activate_tool("select")
    assert "Enter: repetir Linha" in window.toolbox.active.hint()
    _key(window, Qt.Key_Return)
    assert window.toolbox.active.name == "line2d"
    window.activate_tool("wall")
    tool = window.toolbox.active
    for p in ((0, 0), (4, 0)):
        tool.move(p, Mods(alt=True))
        tool.press(p, Mods(alt=True))
    tool.finish()
    window.activate_tool("select")
    window.session.select([_walls(window)[0].GlobalId])
    _key(window, Qt.Key_Return)
    assert window.toolbox.active.name == "select", "com seleção, Enter não repete"


def test_pr13_girar_90(window, app):
    s = window.session
    s.run(lambda: wc.create_wall(s.doc, s.doc.ifc.by_type("IfcWallType")[0], s.storey,
                                 (0, 0), (4, 0)))
    (wall,) = _walls(window)
    s.select([wall.GlobalId])
    window.ctx.invalidate()
    window.rotate_quarter(1)
    path = _path(window, wall)
    xs = sorted(round(q, 3) for q in (path["start"][0], path["end"][0]))
    ys = sorted(round(q, 3) for q in (path["start"][1], path["end"][1]))
    assert xs[0] == pytest.approx(xs[1], abs=1e-6), "a parede ficou vertical"
    assert ys[1] - ys[0] == pytest.approx(4.0)
    window.ctx.invalidate()
    window.rotate_quarter(-1)
    path = _path(window, wall)
    assert abs(path["start"][1] - path["end"][1]) < 1e-6, "Ctrl+Shift+R volta"
    window.undo()
    window.undo()  # uma transação por giro: dois desfazer voltam ao início
    assert _path(window, wall)["start"] == pytest.approx([0, 0])


def test_pr14_paleta_de_comandos(window, app):
    commands = [Command("tool:wall", "Parede", words=("IfcWall", "muro", "alvenaria")),
                Command("tool:door", "Porta", words=("IfcDoor",)),
                Command("menu:Arquivo/Salvar", "Salvar", "Arquivo", "Ctrl+S"),
                Command("tool:space", "Ambiente", words=("IfcSpace", "cômodo"))]
    for query in ("pard", "PAREDE", "ifcwall", "muro"):
        assert search(query, commands)[0].key == "tool:wall", query
    assert search("comodo", commands)[0].key == "tool:space"  # sem acento
    assert next(c.key for c in search("", commands, ["tool:door"])) == "tool:door"
    assert not search("xyzw", commands)
    window.open_palette()
    palette = window.palette_widget
    assert palette.isVisible()
    palette.field.setText("deslocar")
    assert palette.list.currentItem().data(Qt.UserRole) == "tool:offset"
    palette.run()
    assert window.toolbox.active.name == "offset"
    assert palette.recent[0] == "tool:offset"
    keys = {c.key for c in palette.commands}
    assert "menu:Arquivo/Salvar" in keys and "tool:wall" in keys


def test_pr15_ferramentas_de_edicao(window, app):
    s = window.session
    doc, storey = s.doc, s.storey
    t = doc.ifc.by_type("IfcWallType")[0]
    s.run(lambda: wc.create_wall(doc, t, storey, (0, 0), (5, 0)))
    window.ctx.invalidate()
    window.activate_tool("offset")
    tool = window.toolbox.active
    tool.move((2.5, 0), Mods())
    tool.press((2.5, 0), Mods())
    assert tool.target is not None
    tool.move((2.5, 1.0), Mods(alt=True))
    assert tool.fields()[0].value == pytest.approx(1.0)
    assert tool.preview()
    tool.numeric(0.6)
    tool.press((2.5, 1.0), Mods(alt=True))
    assert len(_walls(window)) == 2
    new = next(w for w in _walls(window) if _path(window, w)["start"][1] > 0.1)
    assert _path(window, new)["start"] == pytest.approx([0, 0.6])
    assert tool.fixed["distance"] == pytest.approx(0.6), "a distância continua fixada"
    # concordar duas linhas e aparar
    s.run(lambda: ac.create_annotation(doc, "line2d", storey, points=[[0, 5], [4, 5]]))
    s.run(lambda: ac.create_annotation(doc, "line2d", storey, points=[[5, 6], [5, 9]]))
    window.ctx.invalidate()
    window.activate_tool("fillet")
    tool = window.toolbox.active
    tool.press((1, 5), Mods())
    tool.press((5, 8), Mods())
    lines = [e for e in doc.ifc.by_type("IfcAnnotation") if base.kind_of(e).prefix == "line2d"]
    ends = sorted(tuple(round(v, 6) for v in base.read_state(e)["points"][i])
                  for e, i in zip(lines, (-1, 0), strict=True))
    assert ends == [(5, 5), (5, 5)]
    window.ctx.invalidate()
    window.activate_tool("trim")
    s.run(lambda: ac.create_annotation(doc, "line2d", storey, points=[[0, 7], [8, 7]]))
    window.ctx.invalidate()
    longest = next(e for e in doc.ifc.by_type("IfcAnnotation")
                   if base.read_state(e).get("points", [[0, 0]])[0] == [0, 7])
    window.toolbox.active.press((7, 7), Mods())
    assert base.read_state(longest)["points"][-1] == pytest.approx([5, 7])
    assert math.isfinite(base.read_state(longest)["points"][0][0])
