# SPDX-License-Identifier: GPL-3.0-or-later
"""Controle de orientação no 3D (``spec/ui/40-reticencias-paineis-e-orientacao-3d.md`` §4
e §5, OR01–OR03)."""

import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

from brasbim.ui.scene3d import (
    STANDARD_VIEWS,
    Camera,
    current_mark,
    orientation_marks,
    orientation_pick,
)

CENTER = (100.0, 100.0)


def _marks(camera):
    return {key: (x, y, depth) for key, x, y, depth in orientation_marks(camera, CENTER, 30)}


def test_or01_marcas_na_tela():
    camera = Camera()
    camera.look_from("top")
    marks = _marks(camera)
    assert marks["+z"][:2] == pytest.approx(CENTER, abs=0.1)  # olhando de cima
    assert marks["+z"][2] < 0 < marks["-z"][2]  # +Z na frente, −Z atrás
    assert marks["+x"][0] == pytest.approx(130, abs=0.1)  # leste à direita
    assert marks["+y"][1] == pytest.approx(70, abs=0.1)  # norte para cima
    # na isométrica nordeste, os positivos ficam na frente e são desenhados depois
    camera.look_from("iso_ne")
    marks = _marks(camera)
    assert all(marks[f"+{a}"][2] < 0 for a in "xyz")
    order = [key for key, *_ in orientation_marks(camera, CENTER, 30)]
    assert all(order.index(f"-{a}") < order.index(f"+{a}") for a in "xyz")
    # escolher: a marca da frente quando duas se cobrem (topo: +Z cobre −Z)
    camera.look_from("top")
    assert orientation_pick(camera, CENTER, 30, CENTER, 10) == "+z"
    assert orientation_pick(camera, CENTER, 30, (130, 100), 10) == "+x"
    assert orientation_pick(camera, CENTER, 30, (115, 85), 5) is None
    # de baixo: a vista inversa do topo
    camera.look_from("bottom")
    assert current_mark(camera) == "-z"
    assert STANDARD_VIEWS["bottom"][0] == "De baixo"


@pytest.fixture
def view3d(window):
    from PySide6.QtWidgets import QApplication

    window.set_view("3d")
    QApplication.processEvents()
    view = window.view3d
    view.camera.target = np.array([2.0, 1.0, 0.5])
    view.camera.distance = 17.0
    return view


def _press(view, at, to=None):
    """Aperta em ``at`` e solta lá (clique) ou em ``to`` (arraste)."""
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtTest import QTest

    start = QPointF(*at).toPoint()
    end = QPointF(*(to or at)).toPoint()
    QTest.mousePress(view, Qt.LeftButton, Qt.NoModifier, start)
    if to is not None:
        QTest.mouseMove(view, end)
    QTest.mouseRelease(view, Qt.LeftButton, Qt.NoModifier, end)


def _mark_at(view, key):
    for k, x, y, _ in orientation_marks(view.camera, view.orientation_center(), 32):
        if k == key:
            return x, y
    raise KeyError(key)


def test_or02_clicar_da_a_vista_e_de_novo_a_inversa(view3d):
    view = view3d
    camera = view.camera
    _press(view, _mark_at(view, "+x"))
    assert current_mark(camera) == "+x"
    assert math.degrees(camera.yaw) == pytest.approx(0) and camera.pitch == pytest.approx(0)
    assert camera.target == pytest.approx([2.0, 1.0, 0.5]) and camera.distance == 17.0
    _press(view, _mark_at(view, "+x"))  # de novo: do oeste
    assert current_mark(camera) == "-x"
    _press(view, _mark_at(view, "+z"))
    assert current_mark(camera) == "+z"
    _press(view, _mark_at(view, "+z"))
    assert current_mark(camera) == "-z"
    assert camera.target == pytest.approx([2.0, 1.0, 0.5]) and camera.distance == 17.0
    # a marca de trás também se escolhe quando aparece (de baixo, +Z fica atrás)
    camera.look_from("iso_sw")
    _press(view, _mark_at(view, "-y"))
    assert current_mark(camera) == "-y"
    # a dica dá o nome da vista
    from PySide6.QtCore import QPointF

    assert view.orientation_at(QPointF(*_mark_at(view, "-y"))) == "-y"


def test_or03_controle_nao_vai_para_a_ferramenta(view3d, window):
    view = view3d
    s = window.session
    window.toolbox.activate("wall")
    walls = len(s.doc.ifc.by_type("IfcWall"))
    selection = set(s.selection)
    camera = view.camera
    camera.look_from("iso_sw")
    cx, cy = view.orientation_center()
    _press(view, (cx + 3, cy + 3))  # no disco, fora das marcas: nada
    _press(view, _mark_at(view, "+y"))
    assert current_mark(camera) == "+y"
    assert len(s.doc.ifc.by_type("IfcWall")) == walls and s.selection == selection
    assert window.toolbox.active.name == "wall"
    # arrastar a partir do controle orbita
    yaw = camera.yaw
    _press(view, (cx, cy), (cx - 60, cy))
    assert camera.yaw != pytest.approx(yaw)
    assert len(s.doc.ifc.by_type("IfcWall")) == walls
