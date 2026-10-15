# SPDX-License-Identifier: GPL-3.0-or-later
"""Cor por camada no 3D e cor vinda do estilo do material
(``spec/ui/06-planta-por-camadas.md`` §4, §5; UI58)."""

import numpy as np
import pytest

pytest.importorskip("PySide6")

from brasbim.core import materials, mesh_layers
from brasbim.core.fillings import commands as fc
from brasbim.core.ops import Transaction
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import openings
from brasbim.ui.scene3d import Scene, material_color


def _scene(model, doc=True):
    scene = Scene()
    scene.load(model.doc.ifc, model.doc if doc else None)
    return scene


def _where(tri, fn):
    t = tri.reshape(-1, 3, 3)
    return t[[fn(x) for x in t]]


def test_ui58_parede_com_porta_por_camadas(model):
    wall = model.wall((0, 0), (5, 0))  # face esquerda em y = 0, parede de y −0,14 a 0
    tx = model.commit(fc.create_door_type(model.doc, "P", "SINGLE_SWING_LEFT"))
    model.commit(fc.create_door(model.doc, model.doc.get(tx.ops[0].id), wall, 1.0))
    (opening,) = openings.of_wall(wall)
    o = openings.read_state(opening)
    mesh = _scene(model).meshes[wall.GlobalId]
    plain = _scene(model, doc=False).meshes[wall.GlobalId]
    parts = mesh.parts
    assert set(parts) == {"Reboco", "Bloco cerâmico"}  # nada fica sem camada
    total = mesh_layers.area(plain.vertices)
    assert sum(mesh_layers.area(p) for p in parts.values()) == pytest.approx(total, rel=1e-6)
    top = 2.8

    def on_top(t):
        return np.allclose(t[:, 2], top, atol=1e-6)

    assert mesh_layers.area(_where(parts["Reboco"], on_top)) == pytest.approx(5 * 0.05)
    assert mesh_layers.area(_where(parts["Bloco cerâmico"], on_top)) == pytest.approx(5 * 0.09)

    def on_face(t):
        return np.allclose(t[:, 1], 0.0, atol=1e-6) or np.allclose(t[:, 1], -0.14, atol=1e-6)

    faces = 2 * (5 * top - o["width"] * o["height"])
    assert mesh_layers.area(_where(parts["Reboco"], on_face)) == pytest.approx(faces)
    assert mesh_layers.area(_where(parts["Bloco cerâmico"], on_face)) == pytest.approx(0)

    def on_jamb(t):  # laterais do vão
        x = o["distance"]
        return np.allclose(t[:, 0], x, atol=1e-6) and t[:, 2].max() <= o["height"] + 1e-6

    assert mesh_layers.area(_where(parts["Bloco cerâmico"], on_jamb)) == pytest.approx(
        0.09 * o["height"])
    # As cores do 3D vêm do estilo de cada material.
    colors = {tuple(np.round(c, 3)) for c in mesh.colors}
    assert len(colors) > 2


def test_cor_vem_do_estilo_do_material(model):
    wall = model.wall()
    block = materials.style(model.doc, "Bloco cerâmico")
    assert material_color(wall) == pytest.approx(materials.rgb(block["color"]))
    new = {"color": "#AA5533", "cut": block["cut"]}
    model.commit(_tx(model, new))
    assert material_color(wall) == pytest.approx(materials.rgb("#AA5533"))
    mesh = _scene(model).meshes[wall.GlobalId]
    shaded = mesh.colors.reshape(-1, 3, 3)[:, 0]
    ratio = shaded / np.asarray(materials.rgb("#AA5533"))
    assert np.any(np.ptp(ratio, axis=1) < 1e-4)  # algum triângulo com a cor nova


def _tx(model, new):
    return Transaction("Editar material", [materials.edit_op(model.doc, "Bloco cerâmico", new)])


def test_tombada_fica_com_uma_cor(model):
    wall = model.wall()
    model.commit(cmd.edit_wall(model.doc, wall, tilt=5.0))
    assert _scene(model).meshes[wall.GlobalId].parts is None
