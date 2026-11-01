# SPDX-License-Identifier: GPL-3.0-or-later
"""Estilos do 3D (spec/ui 43 §2): E3D01–E3D03; e alças da laje no 3D (pedido do revisor
em 2026-11-01)."""

import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from test_parede_3d import _drag3d, _screen

from brasbim.core import view_styles
from brasbim.core.drawings import saved_views
from brasbim.core.structure import commands as sc
from brasbim.ui import view3d
from brasbim.ui.scene3d import Mesh, feature_edges, silhouette_edges


@pytest.fixture(autouse=True)
def _planta_visivel(window):
    window.plan.origin = QPointF(150, 350)


def _box(x0=0.0, y0=0.0, z0=0.0, x1=1.0, y1=1.0, z1=1.0):
    v = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]])
    f = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (1, 2, 6),
         (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return v[np.array(f)].reshape(-1, 3)


def _cylinder(sides=32, r=1.0, h=2.0):
    a = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    ring = np.c_[np.cos(a), np.sin(a)] * r
    out = []
    for i in range(sides):
        j = (i + 1) % sides
        p0, p1 = (*ring[i], 0), (*ring[j], 0)
        q0, q1 = (*ring[i], h), (*ring[j], h)
        out += [p0, p1, q1, p0, q1, q0, (0, 0, 0), p1, p0, (0, 0, h), q0, q1]
    return np.array(out)


def test_e3d01_contorno_tira_as_emendas():
    hard, smooth, _ = feature_edges(_box())
    assert len(hard) // 2 == 12  # as 12 arestas da caixa
    assert len(smooth) == 6  # as diagonais das faces saem
    hard, smooth, normals = feature_edges(_cylinder())
    assert len(hard) // 2 == 64  # só as bordas das tampas: as 32 emendas do lado saem
    rim = silhouette_edges(smooth, normals, (10.0, 0.0, 1.0))
    assert len(rim) // 2 == 2  # de lado, as duas silhuetas
    tops = rim.reshape(-1, 2, 3)
    assert all(abs(seg[0][1]) > 0.95 for seg in tops)  # perto das bordas em y = ±1


def test_e3d02_cores_de_cada_estilo():
    tri = _box().astype(np.float32)
    colors = np.tile(np.array([0.6, 0.3, 0.2], np.float32), (len(tri), 1))
    mesh = Mesh(tri, colors, np.zeros((0, 3), np.float32), (0.6, 0.3, 0.2))
    assert [s["id"] for s in view_styles.FACTORY] == [
        "colorido", "colorido_sem_linhas", "maquete_branca", "maquete_branca_sem_linhas",
        "desenho", "arame"]
    assert view3d.face_colors(mesh, view_styles.get("colorido")) is mesh.colors
    white = view3d.face_colors(mesh, view_styles.get("maquete_branca"))
    assert np.allclose(white[:, 0] / white[:, 2], 0xF4 / 0xEC, atol=1e-3)  # uma cor só
    drawing = view3d.face_colors(mesh, view_styles.get("desenho"))
    assert np.allclose(drawing, view3d._BACKGROUND)  # faces na cor do fundo, sem luz
    assert view_styles.get("arame")["faces"] == "none"
    assert view_styles.get("colorido_sem_linhas")["edges"] == "none"
    assert view_styles.get("nao-existe")["id"] == view_styles.DEFAULT


def test_e3d03_menu_barra_e_vista_salva(window):
    window.set_view("split")
    QApplication.processEvents()
    assert window.view3d.style_id == "colorido"
    assert window.view_bar.style3d.isVisible()
    assert window.view_bar.style3d.text() == "Colorido"
    window.style3d_actions["desenho"].trigger()
    assert window.view3d.style_id == "desenho"
    assert window.view_bar.style3d.text() == "Desenho"
    # a vista salva guarda o estilo; abri-la com outro estilo ativo o traz de volta
    window.set_view("3d")
    assert window.view_bar.style3d.isVisible()
    window.save_view(name="Perspectiva")
    (entity,) = [e for e in saved_views.all_saved_views(window.session.doc)
                 if saved_views.read_state(e)["kind"] == "3d"]
    state = saved_views.read_state(entity)
    assert state["options"]["style"] == "desenho"
    window.set_style3d("arame")
    window.open_saved_view(entity.GlobalId)
    assert window.view3d.style_id == "desenho"
    # a imagem da prancha usa o estilo gravado
    from brasbim.ui import saved_views_ui

    assert saved_views_ui.style_of(state)["id"] == "desenho"
    assert saved_views_ui.style_of({"kind": "3d"})["id"] == view_styles.DEFAULT
    window.set_view("plan")
    assert not window.view_bar.style3d.isVisible()


# --- laje no 3D ----------------------------------------------------------------------


def _slab(window):
    s = window.session
    tx = s.doc.ifc.by_type("IfcSlabType")
    if not tx:
        s.run(lambda: sc.create_slab_type(s.doc, "Laje 10", [
            {"material": "Concreto", "thickness": 0.10}]))
    slab_type = s.doc.ifc.by_type("IfcSlabType")[0]
    before = {e.GlobalId for e in s.doc.ifc.by_type("IfcSlab")}
    s.run(lambda: sc.create_slab(s.doc, slab_type, s.storey,
                                 [(0, 0), (4, 0), (4, 3), (0, 3)]))
    (gid,) = {e.GlobalId for e in s.doc.ifc.by_type("IfcSlab")} - before
    window.set_view("split")
    QApplication.processEvents()
    window.view3d.fit()
    return gid, window.view3d


def _outline(s, gid):
    return [tuple(round(c, 6) for c in p) for p in sc.outline_of(s.doc, gid)]


def test_laje_alcas_no_3d_mover_em_x(window):
    s = window.session
    gid, view = _slab(window)
    s.select([gid])
    kinds = [k for k, _ in view.handles()]
    assert kinds[-3:] == ["slab_move", "slab_x", "slab_y"]
    assert {f"slab_v{i}" for i in range(4)} <= set(kinds)
    handles = dict(view.handles())
    z = handles["slab_move"][2]
    assert z == pytest.approx(max(p[2] for p in handles.values()))  # na face de cima
    # seta X: o arrasto puxa também em y, mas a laje anda só em x
    x = handles["slab_x"]
    _drag3d(view, x, (x[0] + 1.0, x[1] + 0.7, z))
    out = _outline(s, gid)
    assert out[0][1] == pytest.approx(0.0, abs=1e-6)
    assert out[0][0] == pytest.approx(1.0, abs=0.06)
    assert s.history.undo_stack[-1].label.startswith("Mover")


def test_laje_seta_y_com_distancia_digitada(window):
    s = window.session
    gid, view = _slab(window)
    s.select([gid])
    y = dict(view.handles())["slab_y"]
    QTest.mouseClick(view, Qt.LeftButton, Qt.NoModifier, _screen(view, y))
    tool = window.toolbox.active
    assert tool.drag3d is not None and [f.label for f in tool.fields()] == ["Distância"]
    QTest.keyClicks(view, "2")
    QTest.keyClick(view.numeric, Qt.Key_Return)
    assert _outline(s, gid)[0] == pytest.approx((0.0, 2.0))
    assert tool.drag3d is None


def test_laje_vertice_e_lado_no_3d(window):
    s = window.session
    gid, view = _slab(window)
    s.select([gid])
    handles = dict(view.handles())
    v = handles["slab_v2"]
    _drag3d(view, v, (5.0, 4.0, v[2]))
    assert _outline(s, gid)[2] == pytest.approx((5.0, 4.0), abs=0.06)
    s.select([gid])
    e = dict(view.handles())["slab_e0"]  # lado de baixo (y = 0): para fora é -y
    _drag3d(view, e, (e[0], -0.5, e[2]))
    out = _outline(s, gid)
    assert out[0][1] == pytest.approx(-0.5, abs=0.06)
    assert out[1][1] == pytest.approx(-0.5, abs=0.06)
    assert math.isclose(out[3][1], 3.0, abs_tol=1e-6)


def test_laje_alcas_so_com_selecionar(window):
    s = window.session
    gid, view = _slab(window)
    window.activate_tool("move")
    s.select([gid])
    assert view.handles() == []  # só com Selecionar
