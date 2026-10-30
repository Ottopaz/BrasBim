# SPDX-License-Identifier: LGPL-3.0-or-later
"""Perfil complexo (spec/ui 41 §4 e §4.1), etapa 1: perfis do projeto em viga e pilar."""

import ifcopenshell.util.element as ue
import pytest
from estrutura import bounds, check_history, created, qto, valid

from brasbim.core import plan, profile_defs
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
    with pytest.raises(OpError, match="se sobrepõem"):
        profile_defs.create(model.doc, overlapping)
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
