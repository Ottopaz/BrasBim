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


def test_pc11_parede_de_perfil_sem_espessura_livre(model):
    """A espessura livre (spec/ui 43 §3) estica uma camada; a parede de perfil não tem
    camada: a largura vem do perfil. Recusa na ficha; sobra da barra Opções é ignorada."""
    from brasbim.core import type_variants

    _, t = profile_type(model)
    assert type_variants.is_profile(t)
    assert type_variants.type_thickness(t) == pytest.approx(0.20)
    w = wall_of(model, t)
    with pytest.raises(OpError, match="perfil"):
        type_variants.set_thickness(model.doc, [w], 0.30)
    # o mesmo valor do tipo não pede variante
    assert not type_variants.set_thickness(model.doc, [w], 0.20).ops
    tx = model.commit(type_variants.create_with(
        model.doc, t.GlobalId, 0.30,
        lambda gid: wc.create_wall(model.doc, model.doc.get(gid), model.terreo, (0, 2), (4, 2))))
    w2 = model.doc.get(tx.ops[0].id)
    assert ue.get_type(w2) == t
    assert not type_variants.variants_of(model.doc, t)
    assert valid(model.doc.ifc)


def test_pc12_referencia_das_aberturas(model):
    """A janela se alinha à linha de referência do perfil, e não ao envolvente; a linha
    anda com o esticar e espelha com as camadas invertidas."""
    from brasbim.core.fillings import commands as fc

    def_id, t = profile_type(model, opening_ref=0.07, stretch_x=0.0)
    assert profile_defs.state(model.doc, def_id)["opening_ref"] == pytest.approx(0.07)
    wt = model.doc.get(model.commit(fc.create_window_type(
        model.doc, "J", lining={"depth": 0.04})).ops[0].id)

    def window_y(wall):
        tx = model.commit(fc.create_window(model.doc, wt, wall, 1.0, 1.0, 1.0, 0.5,
                                           align="axis"))
        window = next(model.doc.get(op.id) for op in tx.ops if op.op == "filling.attach")
        lo, hi = bounds(window)
        return lo[1], hi[1]

    w = wall_of(model, t)
    # perfil de 0,20 esticado para 0,20 (igual): linha em 0,07, janela de 0,05 a 0,09
    assert window_y(w) == pytest.approx((0.05, 0.09), abs=1e-6)
    # editar a linha no perfil leva a janela junto; desfazer volta
    window = model.doc.ifc.by_type("IfcWindow")[-1]
    model.commit(profile_defs.edit(model.doc, def_id, opening_ref=-0.07))
    assert [c[1] for c in bounds(window)] == pytest.approx([-0.09, -0.05], abs=1e-6)
    model.history.undo()
    assert [c[1] for c in bounds(window)] == pytest.approx([0.05, 0.09], abs=1e-6)
    flipped = wall_of(model, t, (0, 5), (5, 5), flip_layers=True)
    lo, hi = window_y(flipped)
    assert (lo - 5, hi - 5) == pytest.approx((-0.09, -0.05), abs=1e-6)
    # tipo mais largo: a linha (à direita da faixa de esticar) anda junto
    model.commit(wc.edit_wall_type(model.doc, t, profile={"id": def_id, "b": 0.30}))
    assert rebuild.opening_line(model.doc, read_state(model.doc, w)) == pytest.approx(0.17)
    with pytest.raises(OpError, match="referência das aberturas"):
        model.commit(profile_defs.edit(model.doc, def_id, opening_ref=0.5))
    assert valid(model.doc.ifc)


def test_pc14_mesmo_material_sem_linha_entre_partes(model):
    """Duas partes encostadas do mesmo material viram um trecho só na planta e no corte
    (spec/ui 41 ponto (o)); materiais diferentes continuam separados."""
    left = [[-0.07, 0.0], [0.0, 0.0], [0.0, 2.0], [-0.07, 2.0]]
    right = [[0.0, 0.0], [0.07, 0.0], [0.07, 2.0], [0.0, 2.0]]
    finish = [[0.07, 0.0], [0.09, 0.0], [0.09, 2.0], [0.07, 2.0]]
    def_id = model.commit(profile_defs.create(model.doc, muro(stretch_y=None, parts=[
        {"material": "Bloco cerâmico", "role": "core", "outline": left},
        {"material": "Bloco cerâmico", "role": "core", "outline": right},
        {"material": "Reboco", "role": "finish", "outline": finish}]))).ops[0].id
    t = model.doc.get(model.commit(wc.create_wall_type(
        model.doc, "Muro", [], profile={"id": def_id, "b": 0.16})).ops[0].id)
    found = layers.wall_layers(model.doc, read_state(model.doc, wall_of(model, t)))
    assert [(ly.material, ly.ymin, ly.ymax) for ly in found] == [
        ("Bloco cerâmico", pytest.approx(-0.07), pytest.approx(0.07)),
        ("Reboco", pytest.approx(0.07), pytest.approx(0.09))]


# --- revisão de 2026-11-07: planta e corte da parede de perfil ----------------------------


def _widths(shapes, owner, role):
    out = []
    for s in shapes:
        if s.owner == owner and s.role == role:
            ys = [p[1] for p in s.points]
            out.append((round(min(ys), 4), round(max(ys), 4)))
    return sorted(out)


def test_pc05_planta_corta_so_o_bloco_e_tracejada_a_capa(model):
    from brasbim.core import plan

    _, t = profile_type(model)
    w = wall_of(model, t)
    p = plan.storey_plan(model.doc, model.terreo)
    # cortado no plano (1,50): só o bloco de 0,14; a capa (0,20, a 2,75) passa por fora
    # dele acima do plano: tracejada dos dois lados
    assert _widths(p.shapes, w.GlobalId, "wall") == [(-0.07, 0.07)]
    assert _widths(p.shapes, w.GlobalId, "wall_above") == [(-0.10, -0.07), (0.07, 0.10)]
    (edge,) = [e for e in p.edges if e.pen == "cut"]
    assert {round(q[1], 4) for r in edge.rings for q in r} == {-0.07, 0.07}


def test_pc05_muro_baixo_todo_em_vista(model):
    from brasbim.core import plan

    _, t = profile_type(model, stretch_y=None)  # sem esticar: 1,05 m, abaixo do plano
    w = wall_of(model, t)
    p = plan.storey_plan(model.doc, model.terreo)
    assert _widths(p.shapes, w.GlobalId, "wall") == []
    assert _widths(p.shapes, w.GlobalId, "wall_view") == [(-0.10, 0.10)]


def _section_cuts(model, owner, a, b):
    from brasbim.core.annotations import commands as ac
    from brasbim.core.drawings import section, views

    model.commit(ac.create_view(model.doc, "section", a, b, "left"))
    view = views.all_views(model.doc)[-1]
    out = []
    for it in section.draw(model.doc, view).items:
        if it.kind == "cut" and it.owner == owner and it.fill.get("source") == "material":
            for r in it.rings:
                us, zs = [q[0] for q in r], [q[1] for q in r]
                out.append((round(max(us) - min(us), 3), round(min(zs), 3),
                            round(max(zs), 3)))
    return sorted(out, key=lambda t: t[1])


def test_pc16_corte_divide_pelas_partes(model):
    """O corte usava as faixas do plano da planta: a capa, mais larga e acima do plano,
    saía com o material errado."""
    _, t = profile_type(model)
    w = wall_of(model, t)
    assert _section_cuts(model, w.GlobalId, (2.5, -3), (2.5, 3)) == [
        (0.14, 0.0, 2.75), (0.20, 2.75, 2.8)]


def test_pc16_corte_da_parede_em_arco(model):
    _, t = profile_type(model)
    tx = model.commit(wc.create_arc_wall(model.doc, t, model.terreo, (10, 0), (12, 2), (14, 0)))
    arc = model.doc.get(tx.ops[0].id)
    found = _section_cuts(model, arc.GlobalId, (12, 5), (12, 0.5))
    assert [f[1:] for f in found] == [(0.0, 2.75), (2.75, 2.8)]
    assert found[0][0] == pytest.approx(0.14, abs=2e-3)
    assert found[1][0] == pytest.approx(0.20, abs=2e-3)
