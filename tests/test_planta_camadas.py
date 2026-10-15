# SPDX-License-Identifier: LGPL-3.0-or-later
"""Planta por detalhe e plano de corte (``spec/ui/06-planta-por-camadas.md`` §2, §3;
UI51, UI54, UI55 no núcleo)."""

import ifcopenshell.util.element as ue
import pytest
from conftest import LAYERS_14

from brasbim.core import clip, plan, storeys
from brasbim.core.fillings import commands as fc
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import top


def _roles(drawing, owner):
    return sorted(s.role for s in drawing.shapes if s.owner == owner)


# --- UI51: simplificado -------------------------------------------------------------------


def test_ui51_mesmo_tipo_uma_mancha(model):
    model.commit(cmd.create_chain(model.doc, model.type14, model.terreo,
                                  [(0, 0), (4, 0), (4, -3)]))
    drawing = plan.storey_plan(model.doc, model.terreo)
    (region,) = drawing.regions
    assert region.key == model.type14.GlobalId and len(region.rings) == 1
    (edge,) = drawing.edges
    assert len(edge.rings) == 1  # contorno só na borda da união: sem linha na junção
    assert edge.weight == pytest.approx(0.0005)


def test_ui51_tipos_diferentes_mantem_a_linha(model):
    tx = model.commit(cmd.create_wall_type(model.doc, "Outra 14", LAYERS_14))
    other = model.doc.get(tx.ops[0].id)
    model.wall((0, 0), (4, 0))
    model.commit(cmd.create_wall(model.doc, other, model.terreo, (4, 0), (4, -3)))
    drawing = plan.storey_plan(model.doc, model.terreo)
    assert {r.key for r in drawing.regions} == {model.type14.GlobalId, other.GlobalId}
    assert len(drawing.edges) == 2
    a, b = (r.rings for r in drawing.regions)
    assert clip.area(clip.intersection(a, b)) == pytest.approx(0, abs=1e-9)


def test_x_de_tipos_diferentes_a_continua_cobre(model):
    tx = model.commit(cmd.create_wall_type(model.doc, "Outra 14", LAYERS_14))
    other = model.doc.get(tx.ops[0].id)
    model.wall((0, 0), (6, 0), ref_line="axis")
    model.commit(cmd.create_wall(model.doc, other, model.terreo, (3, -3), (3, 3),
                                 ref_line="axis"))
    drawing = plan.storey_plan(model.doc, model.terreo)
    total = sum(clip.area(r.rings) for r in drawing.regions)
    assert total == pytest.approx(6 * 0.14 + 6 * 0.14 - 0.14 * 0.14)


# --- por camadas ------------------------------------------------------------------------


def test_por_camadas_regioes_por_material(model):
    model.commit(cmd.create_chain(model.doc, model.type14, model.terreo,
                                  [(0, 0), (4, 0), (4, -3)]))
    drawing = plan.storey_plan(model.doc, model.terreo, detail="layers")
    assert {r.key for r in drawing.regions} == {"Bloco cerâmico", "Reboco"}
    block = next(r for r in drawing.regions if r.key == "Bloco cerâmico")
    assert block.fill["pattern"] == "lines" and block.fill["spacing"] == pytest.approx(0.03)
    weights = sorted(e.weight for e in drawing.edges)
    assert weights == [0.00018, 0.00018, 0.0005]  # divisas finas e contorno do tipo


# --- UI54: plano de corte ---------------------------------------------------------------


def test_ui54_abaixo_e_acima_do_plano(model):
    model.commit(cmd.edit_storey(model.doc, model.terreo, cut_height=1.0))
    assert ue.get_pset(model.terreo, storeys.PSET)["AlturaPlanoCorte"] == pytest.approx(1.0)
    low = model.wall((0, 0), (4, 0), top_mode="fixed", fixed_height=0.9)
    high = model.wall((0, 2), (4, 2), base_offset=1.2)
    cut = model.wall((0, 4), (4, 4))
    drawing = plan.storey_plan(model.doc, model.terreo)
    assert _roles(drawing, low.GlobalId) == ["wall_view"]
    assert _roles(drawing, high.GlobalId) == ["wall_above"]
    assert _roles(drawing, cut.GlobalId) == ["wall"]
    assert [s.role for s in drawing.shapes] == ["wall_above", "wall_view", "wall"]
    assert drawing.pick((2, -0.07), 0.05) == low.GlobalId  # escolha pelo contorno
    assert drawing.pick((2, 1.93), 0.05) == high.GlobalId
    hidden = plan.storey_plan(model.doc, model.terreo, show_above=False)
    assert _roles(hidden, high.GlobalId) == []
    model.commit(cmd.edit_storey(model.doc, model.terreo, cut_height=1.5))
    assert ue.get_pset(model.terreo, storeys.PSET) is None  # o padrão não é gravado
    model.history.undo()
    assert storeys.cut_height(model.terreo) == pytest.approx(1.0)


def test_plano_relativo_a_base_da_parede(model):
    # Base a 0,60 e plano a 1,50: o plano corta a parede a 0,90 da base dela.
    wall = model.wall((0, 0), (5, 0), base_offset=0.6)
    model.commit(cmd.create_opening(model.doc, wall, 1.0, 1.0, 1.0, sill=0.0))
    drawing = plan.storey_plan(model.doc, model.terreo)
    assert _roles(drawing, wall.GlobalId) == ["wall", "wall"]


def test_topo_inclinado_por_trecho(model):
    wall = model.wall((0, 0), (6, 0))
    model.commit(cmd.edit_wall(model.doc, wall, top_shape="slope",
                               top_profile=top.slope(6, 2.0, 1.0)))
    drawing = plan.storey_plan(model.doc, model.terreo)
    (cut,) = [s for s in drawing.shapes if s.role == "wall"]
    (view,) = [s for s in drawing.shapes if s.role == "wall_view"]
    assert max(p[0] for p in cut.points) == pytest.approx(3.0)  # topo a 1,50 em x = 3
    assert min(p[0] for p in view.points) == pytest.approx(3.0)


# --- UI55: vãos --------------------------------------------------------------------------


def test_ui55_peitoril_em_vista(model):
    wall = model.wall((0, 0), (5, 0))
    model.commit(cmd.create_opening(model.doc, wall, 1.0, 1.0, 1.2, sill=1.0))
    drawing = plan.storey_plan(model.doc, model.terreo)
    assert _roles(drawing, wall.GlobalId) == ["wall", "wall", "wall_view", "wall_view"]
    faces = [s for s in drawing.shapes if s.role == "wall_view"]
    assert all(not s.closed for s in faces)
    assert sorted(s.points[0][1] for s in faces) == pytest.approx([-0.14, 0.0])
    model.commit(cmd.edit_storey(model.doc, model.terreo, cut_height=0.5))
    # Não interrompida; o vão, todo acima do plano, fica tracejado.
    assert _roles(plan.storey_plan(model.doc, model.terreo), wall.GlobalId) == ["wall", "wall_above"]


def test_vao_acima_do_plano_tracejado(model):
    wall = model.wall((0, 0), (5, 0))
    model.commit(cmd.create_opening(model.doc, wall, 1.0, 1.0, 0.6, sill=2.0))
    drawing = plan.storey_plan(model.doc, model.terreo)
    assert _roles(drawing, wall.GlobalId) == ["wall", "wall_above"]
    hidden = plan.storey_plan(model.doc, model.terreo, show_above=False)
    assert _roles(hidden, wall.GlobalId) == ["wall"]


def test_nicho_recorta_a_face(model):
    wall = model.wall((0, 0), (5, 0))  # face esquerda (ymax) em y = 0
    model.commit(cmd.create_opening(model.doc, wall, 1.0, 1.0, 2.0, kind="RECESS",
                                    depth=0.05, side="left"))
    drawing = plan.storey_plan(model.doc, model.terreo)
    (piece,) = [s for s in drawing.shapes if s.role == "wall"]
    assert abs(clip.signed_area(list(piece.points))) == pytest.approx(5 * 0.14 - 0.05)
    assert any(p[1] == pytest.approx(-0.05) for p in piece.points)


def test_porta_some_quando_o_plano_passa_acima_do_vao(model):
    wall = model.wall((0, 0), (5, 0))
    tx = model.commit(fc.create_door_type(model.doc, "P", "SINGLE_SWING_LEFT"))
    tx = model.commit(fc.create_door(model.doc, model.doc.get(tx.ops[0].id), wall, 1.0))
    door = next(op.id for op in tx.ops if op.op == "door.create")
    assert _roles(plan.storey_plan(model.doc, model.terreo), door)
    model.commit(cmd.edit_storey(model.doc, model.terreo, cut_height=2.5))
    drawing = plan.storey_plan(model.doc, model.terreo)
    assert _roles(drawing, door) == [] and drawing.labels == []
    assert _roles(drawing, wall.GlobalId) == ["wall"]  # cortada acima do vão
