# SPDX-License-Identifier: GPL-3.0-or-later
"""Seleção pelo cursor no papel (``spec/ui/29-prancha-selecao-e-moldura.md`` §2): os
gestos da planta (spec/ui 28 §2) sobre itens numerados — os desenhos da prancha e as
linhas e textos da folha mestra.

``PaperSelection`` trabalha em mm do papel e não conhece Qt; quem a usa dá ``pick(p)``
(índice sob o ponto) e ``outlines()`` (contornos de cada item para a janela e o laço).
``draw_overlay`` pinta a janela, o laço e o realce."""

from __future__ import annotations

import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF

from brasbim.core.plan import outlines_in_area

DRAG_PX = 4.0  # pixels que o cursor anda para virar arrasto


class PaperSelection:
    def __init__(self, pick, outlines, accumulate=lambda: True):
        self.pick = pick
        self.outlines = outlines
        self.accumulate = accumulate
        self.selected: set[int] = set()
        self.hover: int | None = None
        self.drag: dict | None = None

    # gestos (p em mm; ``reach``: mm que o cursor anda para virar arrasto)

    def press(self, p, shift: bool = False, ctrl: bool = False) -> None:
        d = self.drag
        if d and d["kind"] == "window" and d.get("clicks"):  # 2º clique fecha a janela
            self.drag = None
            self._finish(_rect(d["start"], p), p[0] < d["start"][0], shift or d["shift"])
            return
        self.hover = None
        index = self.pick(p)
        accumulate = self.accumulate()
        if index is not None and shift:
            self.selected.discard(index)
            self.drag = None
            return
        if index is not None and index not in self.selected:
            if accumulate or ctrl:
                self.selected.add(index)
            else:
                self.selected = {index}
            self.drag = {"kind": "move", "start": p, "end": p, "active": False,
                         "fresh": True, "index": index}
            return
        if index is not None:  # já selecionado: arrastar move a seleção
            self.drag = {"kind": "move", "start": p, "end": p, "active": False,
                         "fresh": False, "index": index}
            return
        self.drag = {"kind": "pending", "start": p, "shift": shift, "ctrl": ctrl}

    def move(self, p, reach: float) -> None:
        d = self.drag
        if not d:
            index = self.pick(p) if self.accumulate() else None
            self.hover = index if index not in self.selected else None
            return
        moved = math.dist(p, d["start"]) >= reach
        if d["kind"] == "pending" and moved:
            if self.accumulate():
                self.drag = {"kind": "lasso", "start": d["start"], "points": [d["start"], p],
                             "crossing": p[0] < d["start"][0], "shift": d["shift"]}
            else:
                self.drag = {"kind": "window", "start": d["start"], "end": p,
                             "shift": d["shift"], "ctrl": d["ctrl"]}
        elif d["kind"] == "window":
            d["end"] = p
        elif d["kind"] == "lasso":
            if math.dist(p, d["points"][-1]) >= reach / 2:
                d["points"].append(p)
        elif d["kind"] == "move":
            d["active"] = d["active"] or moved
            d["end"] = p

    def release(self, p, shift: bool = False):
        """Fim do gesto; devolve o deslocamento (mm) quando a seleção foi arrastada."""
        d = self.drag
        if not d:
            return None
        kind = d["kind"]
        if kind == "window" and d.get("clicks"):
            d["end"] = p
            return None
        self.drag = None
        if kind == "pending":
            if not self.accumulate():
                if not d["ctrl"]:
                    self.selected = set()
                return None
            self.drag = {"kind": "window", "start": d["start"], "end": p, "clicks": True,
                         "shift": d["shift"]}  # a janela segue o cursor até o 2º clique
            return None
        if kind == "window":
            self._finish(_rect(d["start"], d["end"]), d["end"][0] < d["start"][0],
                         d["shift"] or shift, ctrl=d.get("ctrl", False))
            return None
        if kind == "lasso":
            self._finish(d["points"], d["crossing"], d["shift"] or shift)
            return None
        if not d["active"]:
            if not self.accumulate() and not d["fresh"]:
                self.selected = {d["index"]}
            return None
        return (p[0] - d["start"][0], p[1] - d["start"][1])

    def escape(self) -> bool:
        """Esc: cancela o gesto; sem gesto, limpa a seleção. Devolve se fez algo."""
        if self.drag is not None:
            self.drag = None
            return True
        if self.selected:
            self.selected = set()
            return True
        return False

    def prune(self, count: int) -> None:
        self.selected = {i for i in self.selected if i < count}
        if self.hover is not None and self.hover >= count:
            self.hover = None

    def _finish(self, area, crossing: bool, shift: bool, ctrl: bool = False) -> None:
        found = set(outlines_in_area(self.outlines(), area, crossing))
        if shift:
            self.selected -= found
        elif self.accumulate() or ctrl:
            self.selected |= found
        else:
            self.selected = found

    # o que pintar

    def area(self):
        """(contorno, cruzamento) da janela ou do laço em andamento, ou ``None``."""
        d = self.drag
        if d and d["kind"] == "window":
            return _rect(d["start"], d["end"]), d["end"][0] < d["start"][0]
        if d and d["kind"] == "lasso":
            return d["points"], d["crossing"]
        return None

    def offset(self):
        """Deslocamento do arrasto em andamento (mm), ou ``None``."""
        d = self.drag
        if d and d["kind"] == "move" and d["active"]:
            return d["end"][0] - d["start"][0], d["end"][1] - d["start"][1]
        return None


def _rect(a, b):
    return [(a[0], a[1]), (b[0], a[1]), (b[0], b[1]), (a[0], b[1])]


def draw_overlay(painter: QPainter, selection: PaperSelection, at) -> None:
    """Janela/laço (contínuo azul para a direita, tracejado verde para a esquerda) e
    realce do item sob o cursor; ``at`` leva mm do papel a pixels."""
    from brasbim.ui.plan_view import C

    if selection.hover is not None:
        outlines = selection.outlines()
        if selection.hover < len(outlines):
            color = QColor(C["select"])
            color.setAlpha(140)
            painter.setPen(QPen(color, 2.5))
            painter.setBrush(Qt.NoBrush)
            for pts, closed in outlines[selection.hover]:
                poly = QPolygonF([at(q) for q in pts])
                painter.drawPolygon(poly) if closed else painter.drawPolyline(poly)
    found = selection.area()
    if found is None:
        return
    pts, crossing = found
    color = QColor(C["crossing"] if crossing else C["preview"])
    painter.setPen(QPen(color, 1, Qt.DashLine if crossing else Qt.SolidLine))
    fill = QColor(color)
    fill.setAlpha(30)
    painter.setBrush(fill)
    painter.drawPolygon(QPolygonF([at(q) for q in pts]))
    painter.setBrush(Qt.NoBrush)
