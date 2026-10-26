# SPDX-License-Identifier: GPL-3.0-or-later
"""Seleção pelo cursor como no CAD (spec/ui 28 §5: SE01 a SE05)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication

from brasbim.core import display_layers as dl
from brasbim.core import plan
from brasbim.core.structure import commands as sc
from brasbim.core.walls import commands as cmd
from brasbim.ui.tools import Mods


def _walls(window):
    """Retângulo 6 × 4 e uma parede solta de (8, 0) a (8, 4); devolve {nome: GlobalId}."""
    s = window.session
    wall_type = window.toolbox.tools["wall"].options.type
    s.run(lambda: cmd.create_rectangle(s.doc, wall_type, s.storey, (0, 0), (6, 4)))
    s.run(lambda: cmd.create_wall(s.doc, wall_type, s.storey, (8, 0), (8, 4)))
    loose = s.history.undo_stack[-1].ops[0].id
    out = {"loose": loose}
    for wall in s.doc.ifc.by_type("IfcWall"):
        if wall.GlobalId == loose:
            continue
        box = [p for sh in window.ctx.plan.shapes if sh.owner == wall.GlobalId
               for p in sh.points]
        xs, ys = [p[0] for p in box], [p[1] for p in box]
        if max(ys) - min(ys) < 1:
            out["south" if max(ys) < 2 else "north"] = wall.GlobalId
        else:
            out["west" if max(xs) < 3 else "east"] = wall.GlobalId
    return out


def _click(tool, p, mods=None):
    mods = mods or Mods()
    tool.move(p, mods)
    tool.press(p, mods)
    tool.release(p, mods)


def test_se01_laco_no_nucleo(model):
    from estrutura import slab_type

    model.commit(cmd.create_rectangle(model.doc, model.type14, model.terreo, (0, 0), (6, 4)))
    tx = model.commit(sc.create_slab(model.doc, slab_type(model), model.terreo,
                                     [(0, 0), (6, 0), (6, 4), (0, 4)]))
    slab = tx.ops[0].id
    drawn = plan.storey_plan(model.doc, model.terreo)
    walls = {w.GlobalId for w in model.doc.ifc.by_type("IfcWall")}
    # triângulo no canto de baixo à esquerda: toca as paredes sul e oeste
    lasso = [(-1, -1), (5, -1), (-1, 3)]
    inside = set(drawn.in_polygon(lasso))
    touching = set(drawn.in_polygon(lasso, crossing=True))
    assert not inside & walls  # nenhuma parede inteira no triângulo
    assert len(touching & walls) == 2
    assert slab not in touching  # a laje só entra inteira (spec/ui 10 §4.1)
    big = [(-1, -1), (7, -1), (7, 5), (-1, 5)]
    assert set(drawn.in_polygon(big)) >= walls | {slab}
    assert drawn.in_polygon([(0, 0), (1, 1)]) == []


def test_se02_clique_soma_shift_tira_janela(window):
    s = window.session
    w = _walls(window)
    tool = window.toolbox.tools["select"]
    window.activate_tool("select")
    assert window.ctx.accumulate
    _click(tool, (3.0, 0.07))
    _click(tool, (3.0, 3.93))
    assert s.selection == {w["south"], w["north"]}
    _click(tool, (3.0, 0.07), Mods(shift=True))
    assert s.selection == {w["north"]}
    # clique no vazio abre a janela; o segundo clique fecha (para a direita: inteiros)
    _click(tool, (7.5, -1.0))
    assert tool.drag["kind"] == "window" and tool.drag["clicks"]
    tool.move((8.5, 5.0), Mods())
    assert tool.preview()[0].style == "window"
    tool.press((8.5, 5.0), Mods())
    assert s.selection == {w["north"], w["loose"]}
    # para a esquerda: os que tocam
    _click(tool, (6.5, 3.0))
    tool.press((5.5, 1.0), Mods())
    assert s.selection == {w["north"], w["loose"], w["east"]}
    # Shift ao fechar tira
    _click(tool, (7.5, -1.0))
    tool.press((8.5, 5.0), Mods(shift=True))
    assert s.selection == {w["north"], w["east"]}
    # Esc cancela a janela; o segundo Esc limpa
    _click(tool, (7.5, -1.0))
    window.plan.press_escape()
    assert tool.drag is None and s.selection == {w["north"], w["east"]}
    window.plan.press_escape()
    assert s.selection == set()


def test_se03_laco_destaque_e_camada_bloqueada(window):
    s = window.session
    w = _walls(window)
    tool = window.toolbox.tools["select"]
    window.activate_tool("select")
    # laço para a direita em volta da parede solta: só ela
    pts = [(7.5, -0.5), (8.5, -0.5), (8.5, 4.5), (7.5, 4.5)]
    tool.move(pts[0], Mods())
    tool.press(pts[0], Mods())
    for p in pts[1:]:
        tool.move(p, Mods())
    assert tool.drag["kind"] == "lasso" and not tool.drag["crossing"]
    assert tool.preview()[0].style == "window"
    tool.release(pts[-1], Mods())
    assert s.selection == {w["loose"]}
    # laço para a esquerda que só toca a parede leste: cruzamento
    pts = [(6.5, 1.0), (5.8, 1.0), (5.8, 3.0), (6.5, 3.0)]
    tool.move(pts[0], Mods())
    tool.press(pts[0], Mods())
    for p in pts[1:]:
        tool.move(p, Mods())
    assert tool.drag["crossing"]
    tool.release(pts[-1], Mods())
    assert s.selection == {w["loose"], w["east"]}
    # destaque sob o cursor
    tool.move((3.0, 0.07), Mods())
    assert window.ctx.hover == w["south"]
    window.plan.grab()
    tool.move((3.0, 2.0), Mods())
    assert window.ctx.hover is None
    # camada bloqueada: nem destaque nem escolha
    paredes = next(x["id"] for x in dl.read_config(s.doc)["layers"] if x["name"] == "Paredes")
    s.select([])
    s.set_display(dl.Display(locked=frozenset({paredes})))
    window.ctx.invalidate()
    tool.move((3.0, 0.07), Mods())
    assert window.ctx.hover is None
    _click(tool, (3.0, 0.07))
    assert s.selection == set()


def test_se04_3d(window):
    s = window.session
    w = _walls(window)
    window.set_view("split")
    QApplication.processEvents()
    view = window.view3d
    view.fit()
    screen = {}
    for name, gid in w.items():
        low, high = view.scene.selection_bounds({gid})
        center = ((low[0] + high[0]) / 2, (low[1] + high[1]) / 2, high[2])
        screen[name] = QPointF(*view.camera.project(center, view.width(), view.height()))
    view.click(screen["south"], "left", Mods())
    view.click(screen["loose"], "left", Mods())
    assert s.selection == {w["south"], w["loose"]}
    view.click(screen["south"], "left", Mods(shift=True))
    assert s.selection == {w["loose"]}
    s.select([])
    # janela para a esquerda do tamanho da vista: tudo o que aparece
    view.click(QPointF(view.width() - 2, view.height() - 2), "left", Mods())
    assert view.window_start is not None
    view.mouse_pos = QPointF(2, 2)
    view.grab()
    view.click(QPointF(2, 2), "left", Mods())
    assert s.selection >= set(w.values())
    # janela pequena que atravessa a parede solta, de chão vazio a chão vazio
    def at(point):
        return QPointF(*view.camera.project(point, view.width(), view.height()))

    a, b = at((9.0, 1.5, 0.0)), at((7.2, 2.5, 0.0))
    right, left = (a, b) if a.x() > b.x() else (b, a)
    assert view.pick(a) is None and view.pick(b) is None
    s.select([])
    view.click(right, "left", Mods())  # para a esquerda: cruzamento pega a parede
    view.click(left, "left", Mods())
    assert s.selection == {w["loose"]}
    s.select([])
    view.click(left, "left", Mods())  # para a direita: a parede não está inteira
    view.click(right, "left", Mods())
    assert s.selection == set()
    # destaque
    view._feed_move(screen["south"], Mods())
    assert window.ctx.hover == w["south"]


def test_se05_modo_trocar(window):
    s = window.session
    w = _walls(window)
    tool = window.toolbox.tools["select"]
    window.activate_tool("select")
    window.set_select_mode(False)
    _click(tool, (3.0, 0.07))
    _click(tool, (3.0, 3.93))
    assert s.selection == {w["north"]}  # troca
    _click(tool, (3.0, 0.07), Mods(ctrl=True))
    assert s.selection == {w["north"], w["south"]}
    _click(tool, (10.0, 10.0))
    assert s.selection == set()  # clique no vazio limpa
    tool.move((7.5, -1.0), Mods())
    tool.press((7.5, -1.0), Mods())
    tool.move((8.5, 5.0), Mods())
    assert tool.drag["kind"] == "window"  # arrastar faz a janela (sem laço)
    tool.release((8.5, 5.0), Mods())
    assert s.selection == {w["loose"]}
    assert window.select_mode_actions[False].isChecked()
    window.set_select_mode(True)
