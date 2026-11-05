# SPDX-License-Identifier: LGPL-3.0-or-later
"""Perfil complexo (spec/ui 41 §4 e §4.1), etapa 1: perfis do projeto em viga e pilar."""

import ifcopenshell.util.element as ue
import pytest
from estrutura import bounds, check_history, created, qto, valid

from brasbim.core import materials, plan, profile_defs
from brasbim.core.document import Document, OpError
from brasbim.core.ops import History, Transaction
from brasbim.core.structure import columns, profiles
from brasbim.core.structure import commands as sc
from brasbim.core.structure import types as st_types

# Viga T com a origem no meio do topo: mesa 0,60 × 0,10 e alma 0,20 × 0,40.
FLANGE = [[-0.3, -0.1], [0.3, -0.1], [0.3, 0.0], [-0.3, 0.0]]
WEB = [[-0.1, -0.5], [0.1, -0.5], [0.1, -0.1], [-0.1, -0.1]]


def tee(**changes):
    state = {"name": "Viga T", "uses": ["beam", "column"], "stretch_x": None,
             "stretch_y": None,
             "parts": [{"material": "Concreto", "role": "core", "outline": FLANGE},
                       {"material": "Reboco", "role": "finish", "outline": WEB}]}
    state.update(changes)
    return state


def new_profile(model, **changes) -> str:
    tx = model.commit(profile_defs.create(model.doc, tee(**changes)))
    return tx.ops[0].id


def custom(def_id, b=0.6, h=0.5):
    return {"shape": "custom", "profile": def_id, "b": b, "h": h}


def beam(model, def_id, b=0.6, h=0.5, start=(0, 0), end=(4, 0)):
    return created(model, sc.create_beam(model.doc, None, model.terreo, start, end,
                                         section=custom(def_id, b, h)))


def column(model, def_id, b=0.6, h=0.5, point=(10, 0)):
    return created(model, sc.create_column(model.doc, None, model.terreo, point,
                                           section=custom(def_id, b, h)))


def test_pc01_perfil_com_duas_partes(model, tmp_path):
    def_id = new_profile(model)
    b = beam(model, def_id)
    t = ue.get_type(b)
    pset = ue.get_material(t)
    assert pset.is_a("IfcMaterialProfileSet")
    assert [mp.Material.Name for mp in pset.MaterialProfiles] == ["Concreto", "Reboco"]
    assert [mp.Category for mp in pset.MaterialProfiles] == ["LoadBearing", "Finish"]
    assert pset.CompositeProfile.is_a("IfcCompositeProfileDef")
    (body,) = [r for r in b.Representation.Representations
               if r.RepresentationIdentifier == "Body"]
    assert body.Items[0].SweptArea == pset.CompositeProfile
    # forma: largura 0,60 (y do mundo), altura 0,50 abaixo do topo da viga
    lo, hi = bounds(b)
    assert (lo[1], hi[1]) == pytest.approx((-0.3, 0.3))
    assert hi[2] - lo[2] == pytest.approx(0.5)
    q = qto(b, "Qto_BeamBaseQuantities")
    assert q["CrossSectionArea"] == pytest.approx(0.6 * 0.1 + 0.2 * 0.4)
    assert q["GrossVolume"] == pytest.approx(4 * (0.06 + 0.08))
    assert "Viga T" in t.Name
    assert valid(model.doc.ifc)
    # reabre igual
    path = tmp_path / "perfil.ifc"
    model.doc.save(str(path))
    other = Document.open(str(path))
    (definition,) = profile_defs.all_defs(other)
    assert [p["outline"] for p in profile_defs.read_state(definition)["parts"]] == [FLANGE, WEB]
    section = st_types.section(other.get(t.GlobalId))
    assert (section["shape"], section["profile"], section["b"], section["h"]) == \
        ("custom", def_id, 0.6, 0.5)


def test_pc02_esticar(model):
    def_id = new_profile(model, stretch_y=-0.3)
    b = beam(model, def_id, h=0.7)  # alma 0,20 mais alta: só o que está abaixo da linha anda
    lo, hi = bounds(b)
    assert hi[2] - lo[2] == pytest.approx(0.7)
    assert (lo[1], hi[1]) == pytest.approx((-0.3, 0.3))
    # a linha está em y = -0,3: tudo acima dela fica; a altura cresce 0,20 para cima,
    # porque esticar move o que está ALÉM da linha (y maior)
    section = st_types.section(ue.get_type(b))
    flange = section["parts"][0]["outline"]
    assert max(p[1] for p in flange) == pytest.approx(0.2)
    # sem linha de esticar na largura, a largura é fixa
    with pytest.raises(OpError, match="não estica na largura"):
        beam(model, def_id, b=0.8)


def test_pc04_pilar_com_perfil(model):
    def_id = new_profile(model)
    c = column(model, def_id)
    lo, hi = bounds(c)
    assert (lo[0], hi[0]) == pytest.approx((9.7, 10.3))
    assert (lo[1], hi[1]) == pytest.approx((-0.5, 0.0))
    q = qto(c, "Qto_ColumnBaseQuantities")
    assert q["CrossSectionArea"] == pytest.approx(0.14)
    # planta: o contorno do pilar é a união das partes (forma de T)
    assert len(columns.outline(model.doc, columns.read_state(model.doc, c))) == 8
    assert plan.storey_plan(model.doc, model.terreo).regions
    assert valid(model.doc.ifc)


def test_pc07_um_perfil_em_viga_e_pilar(model):
    def_id = new_profile(model)
    b, c = beam(model, def_id), column(model, def_id)
    # a viga e o pilar usam tipos diferentes, ambos com o mesmo perfil do projeto
    assert {st_types.profile_def_of(ue.get_type(e)) for e in (b, c)} == {def_id}
    assert {u.GlobalId for u in profile_defs.users(model.doc, def_id)} == {
        ue.get_type(b).GlobalId, ue.get_type(c).GlobalId}
    wide = [[-0.4, -0.1], [0.4, -0.1], [0.4, 0.0], [-0.4, 0.0]]
    parts = tee()["parts"]
    parts[0]["outline"] = wide

    def edit():
        model.commit(profile_defs.edit(model.doc, def_id, parts=parts))

    check_history(model, edit)
    assert (bounds(b)[0][1], bounds(b)[1][1]) == pytest.approx((-0.4, 0.4))
    assert (bounds(c)[0][0], bounds(c)[1][0]) == pytest.approx((9.6, 10.4))
    assert qto(c, "Qto_ColumnBaseQuantities")["CrossSectionArea"] == pytest.approx(0.16)
    # nenhum perfil solto no arquivo depois de refazer
    used = {mp.Profile for s in model.doc.ifc.by_type("IfcMaterialProfileSet")
            for mp in s.MaterialProfiles}
    composites = {s.CompositeProfile for s in model.doc.ifc.by_type("IfcMaterialProfileSet")
                  if s.CompositeProfile}
    loose = [p for p in model.doc.ifc.by_type("IfcArbitraryClosedProfileDef")
             if p not in used and not any(p in c.Profiles for c in composites)]
    assert loose == []
    assert valid(model.doc.ifc)


def test_pc10_lista_por_uso_e_recusas(model):
    only_beam = new_profile(model, name="Só viga", uses=["beam"])
    both = new_profile(model)
    assert [profile_defs.id_of(s) for s in profile_defs.for_use(model.doc, "column")] == [both]
    with pytest.raises(OpError, match="não serve para pilares"):
        column(model, only_beam)
    with pytest.raises(OpError, match="já existe"):
        profile_defs.create(model.doc, tee())
    overlapping = tee(name="Ruim")
    overlapping["parts"][1]["outline"] = [[-0.1, -0.5], [0.1, -0.5], [0.1, -0.05], [-0.1, -0.05]]
    # sobreposta: aceita, e o acabamento (alma) é recortado pelo núcleo (mesa)
    made = profile_defs.state(model.doc, model.commit(
        profile_defs.create(model.doc, overlapping)).ops[0].id)
    assert profile_defs.area(made["parts"]) == pytest.approx(0.06 + 0.2 * 0.4)
    # a operação em si continua recusando partes sobrepostas (o IFC não as tem)
    from brasbim.core.ops import Op
    with pytest.raises(OpError, match="se sobrepõem"):
        model.commit(Transaction("x", [Op("profile_def.create", "x1",
                                         data=tee(name="Ruim 2", parts=overlapping["parts"]))]))
    beam(model, both)
    with pytest.raises(OpError, match="em uso"):
        profile_defs.delete(model.doc, both)
    model.commit(profile_defs.delete(model.doc, only_beam))
    assert profile_defs.find(model.doc, only_beam) is None


def test_pc_desfazer_e_diario(model):
    def go():
        def_id = new_profile(model)
        beam(model, def_id)
        column(model, def_id)

    check_history(model, go)


def test_pc_diario_reaplicado_noutro_documento(model):
    def_id = new_profile(model)
    beam(model, def_id)
    other = Document.new(project_id=model.doc.project.GlobalId)
    history = History(other)
    for tx in model.history.journal:
        history.commit(Transaction.from_dict(tx.to_dict()))
    assert profile_defs.find(other, def_id) is not None
    assert profiles.CUSTOM == st_types.section(other.ifc.by_type("IfcBeamType")[-1])["shape"]


def test_pc05b_planta_por_parte(model):
    """Pilar de perfil cortado: uma região por parte, com o corte do material dela."""
    def_id = new_profile(model)
    c = column(model, def_id)
    p = plan.storey_plan(model.doc, model.terreo)
    regions = [r for r in p.regions if r.key == c.GlobalId]
    assert len(regions) == 2
    concrete = materials.style(model.doc, "Concreto")["cut"]["pattern"]
    plaster = materials.style(model.doc, "Reboco")["cut"]["pattern"]
    assert sorted(r.fill["pattern"] for r in regions) == sorted([concrete, plaster])


# Cantoneira (L) com a origem no canto: aba 0,30 × 0,10 e alma 0,10 × 0,30.
ANGLE_PARTS = [
    {"material": "Concreto", "role": "core",
     "outline": [[0, 0], [0.3, 0], [0.3, 0.1], [0, 0.1]]},
    {"material": "Concreto", "role": "core",
     "outline": [[0, 0.1], [0.1, 0.1], [0.1, 0.4], [0, 0.4]]}]


def test_pc13_giro_e_espelhar_em_viga_e_pilar(model):
    def_id = new_profile(model, name="Cantoneira", parts=ANGLE_PARTS)

    def xy(element):
        lo, hi = bounds(element)
        return (lo[0], hi[0], lo[1], hi[1])

    def at(point, **extra):
        return column(model, def_id, b=0.3, h=0.4, point=point) if not extra else created(
            model, sc.create_column(model.doc, None, model.terreo, point,
                                    section={**custom(def_id, 0.3, 0.4), **extra}))

    assert xy(at((10, 0))) == pytest.approx((10.0, 10.3, 0.0, 0.4))
    mirrored = at((20, 0), mirror=True)
    assert xy(mirrored) == pytest.approx((19.7, 20.0, 0.0, 0.4))
    turned = at((30, 0), angle=90.0)
    assert xy(turned) == pytest.approx((29.6, 30.0, 0.0, 0.3))
    # cada giro/espelho é um tipo, com o nome dizendo qual
    t = ue.get_type(turned)
    assert t != ue.get_type(mirrored) and "90°" in t.Name
    assert "espelhado" in ue.get_type(mirrored).Name
    assert st_types.read_profile_type(t)["section"]["angle"] == pytest.approx(90.0)
    # a seção sem giro nem espelho continua como antes (diários antigos)
    assert set(st_types.read_profile_type(ue.get_type(at((40, 0))))["section"]) == {
        "shape", "profile", "b", "h"}
    # viga espelhada: a aba vai para o outro lado do eixo
    plain = beam(model, def_id, b=0.3, h=0.4, start=(0, 5), end=(4, 5))
    flipped = created(model, sc.create_beam(
        model.doc, None, model.terreo, (0, 8), (4, 8),
        section={**custom(def_id, 0.3, 0.4), "mirror": True}))
    (_, _, a0, a1), (_, _, b0, b1) = xy(plain), xy(flipped)
    assert (b0 - 8, b1 - 8) == pytest.approx((-(a1 - 5), -(a0 - 5)))

    # editar o perfil do projeto mantém o giro do tipo; desfazer volta
    def edit():
        parts = [dict(p) for p in ANGLE_PARTS]
        parts[0] = {**parts[0], "outline": [[0, 0], [0.5, 0], [0.5, 0.1], [0, 0.1]]}
        model.commit(profile_defs.edit(model.doc, def_id, parts=parts))

    check_history(model, edit)
    assert xy(turned) == pytest.approx((29.6, 30.0, 0.0, 0.5))
    # girar pela edição do elemento
    model.commit(sc.edit_element(model.doc, mirrored,
                                 section={**custom(def_id, 0.5, 0.4), "angle": 180.0}))
    assert xy(mirrored) == pytest.approx((19.5, 20.0, -0.4, 0.0))
    assert valid(model.doc.ifc)


def test_pc14_pilar_mesmo_material_junto_na_planta(model):
    """A cantoneira tem duas partes de concreto: na planta, um contorno só."""
    from brasbim.core.structure import columns

    def_id = new_profile(model, name="Cantoneira", parts=ANGLE_PARTS)
    c = column(model, def_id, b=0.3, h=0.4)
    found = columns.part_outlines(model.doc, columns.read_state(model.doc, c))
    assert [name for name, _ in found] == ["Concreto"] and len(found[0][1]) == 6


def test_pc15_criar_perfil_a_partir_da_selecao(model):
    """Viga e pilar retangular ou circular e parede de camadas viram perfis do projeto;
    usar o perfil novo dá a mesma forma."""
    from estrutura import beam_type, circle_type, column_type

    from brasbim.core.walls import commands as wc

    def make(tx):
        return created(model, tx)

    rect = make(sc.create_column(model.doc, column_type(model, 0.2, 0.4), model.terreo,
                                 (0, 0)))
    state = profile_defs.from_element(model.doc, rect)
    assert state["uses"] == ["column", "beam"] and len(state["parts"]) == 1
    assert profile_defs.bounds(state["parts"]) == pytest.approx((-0.1, -0.2, 0.1, 0.2))
    assert state["stretch_x"] == pytest.approx(0.0) and state["stretch_y"] == pytest.approx(0.0)
    def_id = model.commit(profile_defs.create_from(model.doc, rect)).ops[0].id
    again = column(model, def_id, b=0.2, h=0.4, point=(5, 0))
    lo, hi = bounds(again)
    assert (lo[0], hi[0], lo[1], hi[1]) == pytest.approx((4.9, 5.1, -0.2, 0.2))
    with pytest.raises(OpError, match="já usa"):
        profile_defs.from_element(model.doc, again)

    round_ = make(sc.create_column(model.doc, circle_type(model, 0.3), model.terreo, (8, 0)))
    state = profile_defs.from_element(model.doc, round_)
    assert state["stretch_x"] is None and profile_defs.area(state["parts"]) == \
        pytest.approx(3.1416 * 0.15 ** 2, rel=0.01)

    b = make(sc.create_beam(model.doc, beam_type(model, 0.14, 0.40), model.terreo,
                            (0, 3), (4, 3)))
    state = profile_defs.from_element(model.doc, b)
    # origem no eixo da viga, no topo: a seção fica abaixo
    assert profile_defs.bounds(state["parts"]) == pytest.approx((-0.07, -0.4, 0.07, 0.0))

    wall_type = model.doc.ifc.by_type("IfcWallType")[0]
    w = make(wc.create_wall(model.doc, wall_type, model.terreo, (0, 6), (5, 6)))
    state = profile_defs.from_element(model.doc, w)
    assert state["uses"] == ["wall"] and state["parts"]
    assert {p["role"] for p in state["parts"]} >= {"core"}
    thickness = sum(p["outline"][1][0] - p["outline"][0][0] for p in state["parts"])
    from brasbim.core.walls import types as wall_types
    assert thickness == pytest.approx(wall_types.thickness(wall_type))
    model.commit(profile_defs.create_from(model.doc, w))
    assert valid(model.doc.ifc)


def test_pc16_partes_sobrepostas_recortadas_ao_gravar(model):
    """O editor aceita partes sobrepostas; ao gravar, o núcleo corta o acabamento e, entre
    iguais, a de cima (desenhada depois) corta a de baixo."""
    core = [[0, 0], [0.2, 0], [0.2, 0.4], [0, 0.4]]
    plaster = [[-0.02, -0.02], [0.22, -0.02], [0.22, 0.42], [-0.02, 0.42]]  # envolve o núcleo
    def_id = new_profile(model, name="Pilar rebocado", parts=[
        {"material": "Reboco", "role": "finish", "outline": plaster},
        {"material": "Concreto", "role": "core", "outline": core}])
    parts = profile_defs.state(model.doc, def_id)["parts"]
    finish = next(p for p in parts if p["role"] == "finish")
    assert len(finish["holes"]) == 1  # o reboco virou um anel em volta do concreto
    assert profile_defs.area(parts) == pytest.approx(0.24 * 0.44)
    # dois núcleos: o de cima corta o de baixo
    top = [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3], [0.1, 0.3]]
    model.commit(profile_defs.edit(model.doc, def_id, parts=[
        {"material": "Concreto", "role": "core", "outline": core},
        {"material": "Aço", "role": "core", "outline": top}]))
    a, b = profile_defs.state(model.doc, def_id)["parts"]
    assert profile_defs.area([a]) == pytest.approx(0.08 - 0.02)
    assert profile_defs.area([b]) == pytest.approx(0.04)
