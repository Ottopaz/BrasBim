# SPDX-License-Identifier: LGPL-3.0-or-later
"""Perfil complexo, etapa 2: parede de perfil do projeto (spec/ui 41 §4, PC03 e PC05)."""

import ifcopenshell.util.element as ue
import pytest
from estrutura import bounds, check_history, qto, valid

from brasbim.core import layers, profile_defs
from brasbim.core.document import OpError
from brasbim.core.walls import commands as wc
from brasbim.core.walls import rebuild
from brasbim.core.walls import types as wall_types
from brasbim.core.walls.wall import read_state

# Muro com capa, origem no eixo e na base: bloco 0,14 × 1,00 e capa 0,20 × 0,05.
BLOCK = [[-0.07, 0.0], [0.07, 0.0], [0.07, 1.0], [-0.07, 1.0]]
CAP = [[-0.10, 1.0], [0.10, 1.0], [0.10, 1.05], [-0.10, 1.05]]


def muro(**changes):
    state = {"name": "Muro com capa", "uses": ["wall"], "stretch_x": None, "stretch_y": 0.5,
             "parts": [{"material": "Bloco cerâmico", "role": "core", "outline": BLOCK},
                       {"material": "Concreto", "role": "finish", "outline": CAP}]}
    state.update(changes)
    return state


def profile_type(model, **changes):
    def_id = model.commit(profile_defs.create(model.doc, muro(**changes))).ops[0].id
    tx = model.commit(wc.create_wall_type(model.doc, "Muro", [], profile={"id": def_id,
                                                                        "b": 0.20}))
    return def_id, model.doc.get(tx.ops[0].id)


def wall_of(model, t, start=(0, 0), end=(5, 0), **options):
    tx = model.commit(wc.create_wall(model.doc, t, model.terreo, start, end, **options))
    return model.doc.get(tx.ops[0].id)


def test_pc03_parede_reta_de_perfil(model):
    def_id, t = profile_type(model)
    assert wall_types.read(t)["profile"] == {"id": def_id, "b": 0.20}
    assert wall_types.thickness(t) == pytest.approx(0.20)
    assert ue.get_material(t).is_a("IfcMaterialProfileSet")
    w = wall_of(model, t)
    assert ue.get_material(w) == ue.get_material(t)
    lo, hi = bounds(w)
    # esticado até o pavimento de cima (2,80): bloco até 2,75, capa de 2,75 a 2,80
    assert (lo[1], hi[1]) == pytest.approx((-0.10, 0.10), abs=1e-6)
    assert (lo[2], hi[2]) == pytest.approx((0.0, 2.8), abs=1e-6)
    area = 0.14 * 2.75 + 0.20 * 0.05
    q = qto(w, "Qto_WallBaseQuantities")
    assert q["Width"] == pytest.approx(0.20) and q["Height"] == pytest.approx(2.8)
    assert q["GrossVolume"] == pytest.approx(area * 5)
    assert valid(model.doc.ifc)


def test_pc03_altura_fixa_sem_esticar(model):
    _, t = profile_type(model, stretch_y=None)
    w = wall_of(model, t)
    assert rebuild.height(model.doc, read_state(model.doc, w)) == pytest.approx(1.05)
    assert bounds(w)[1][2] == pytest.approx(1.05, abs=1e-6)


def test_pc03_parede_em_arco_e_invertida(model):
    _, t = profile_type(model)
    tx = model.commit(wc.create_arc_wall(model.doc, t, model.terreo, (10, 0), (12, 2), (14, 0)))
    arc = model.doc.get(tx.ops[0].id)
    lo, hi = bounds(arc)
    assert hi[2] == pytest.approx(2.8, abs=1e-6)
    assert hi[1] == pytest.approx(2.10, abs=1e-3)  # raio 2 + meia capa
    # (o arco vira polígono no motor geométrico: alguns centímetros de diferença)
    assert lo[0] == pytest.approx(9.90, abs=0.03) and hi[0] == pytest.approx(14.10, abs=0.03)
    # camadas invertidas: o desenho espelha (aqui é simétrico; a faixa continua igual)
    w = wall_of(model, t, flip_layers=True)
    band = rebuild.band(model.doc, read_state(model.doc, w))
    assert (band.ymin, band.ymax) == pytest.approx((-0.10, 0.10))
    with pytest.raises(OpError, match="não tomba"):
        model.commit(wc.edit_wall(model.doc, w, tilt=5.0))
    assert valid(model.doc.ifc)


def test_pc03_editar_o_perfil_refaz_a_parede(model):
    def_id, t = profile_type(model)
    w = wall_of(model, t)
    parts = muro()["parts"]
    parts[1]["outline"] = [[-0.12, 1.0], [0.12, 1.0], [0.12, 1.05], [-0.12, 1.05]]

    def edit():
        model.commit(profile_defs.edit(model.doc, def_id, parts=parts))

    check_history(model, edit)
    # sem linha de esticar na largura, a espessura do tipo vai para a do desenho
    assert wall_types.thickness(t) == pytest.approx(0.24)
    lo, hi = bounds(w)
    assert (lo[1], hi[1]) == pytest.approx((-0.12, 0.12), abs=1e-6)
    assert valid(model.doc.ifc)


def test_pc03_junta_em_l_e_desfazer(model):
    def go():
        _, t = profile_type(model)
        wall_of(model, t, (0, 0), (5, 0))
        wall_of(model, t, (5, 0), (5, 4))

    check_history(model, go)
    a, b = sorted(model.doc.ifc.by_type("IfcWall"), key=lambda e: e.id())[-2:]
    # canto em esquadria: as duas chegam até a face externa da outra
    assert bounds(a)[1][0] == pytest.approx(5.10, abs=1e-6)
    assert bounds(b)[0][1] == pytest.approx(-0.10, abs=1e-6)
    assert valid(model.doc.ifc)


def test_pc05_planta_corta_o_perfil(model):
    _, t = profile_type(model)
    w = wall_of(model, t)
    found = layers.wall_layers(model.doc, read_state(model.doc, w))
    # plano de corte a 1,50: só o bloco é cortado (a capa está a 2,75)
    assert [(ly.material, ly.ymin, ly.ymax) for ly in found] == [
        ("Bloco cerâmico", pytest.approx(-0.07), pytest.approx(0.07))]


def test_tipo_volta_para_camadas(model):
    _, t = profile_type(model)
    w = wall_of(model, t)
    layer = [{"material": "Concreto", "thickness": 0.12, "name": None, "category": None,
              "priority": None, "is_ventilated": False}]
    model.commit(wc.edit_wall_type(model.doc, t, profile=None, layers=layer))
    assert wall_types.profile_of(t) is None
    assert ue.get_material(w, should_inherit=False).is_a("IfcMaterialLayerSetUsage")
    assert qto(w, "Qto_WallBaseQuantities")["Width"] == pytest.approx(0.12)
    model.history.undo()
    assert wall_types.profile_of(t) is not None
    assert valid(model.doc.ifc)


@pytest.mark.parametrize("through", [(-0.5, 2), (0.5, 2), (-1.2, 2), (1.2, 2)])
def test_pc03_arco_cobre_o_caminho_todo(model, through):
    """Arcos de menos de meia volta, nos dois sentidos: o corpo vai de uma ponta à outra
    (uma revolução no sentido errado não cruza o caminho e o corpo some ou encurta)."""
    _, t = profile_type(model)
    tx = model.commit(wc.create_arc_wall(model.doc, t, model.terreo, (0, 0), through, (0, 4)))
    lo, hi = bounds(model.doc.get(tx.ops[0].id))
    assert lo[1] == pytest.approx(0.0, abs=0.12) and hi[1] == pytest.approx(4.0, abs=0.12)
    side = lo[0] if through[0] < 0 else hi[0]
    assert abs(side) == pytest.approx(abs(through[0]) + 0.10, abs=0.05)
    assert hi[2] == pytest.approx(2.8, abs=1e-6)
