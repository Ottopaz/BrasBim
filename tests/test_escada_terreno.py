# SPDX-License-Identifier: LGPL-3.0-or-later
"""Escada, guarda-corpo e terreno (spec/elementos/escada-terreno.md §5): ET01 a ET07."""

import itertools
import logging
import math

import ifcopenshell.util.element as ue
import pytest
from estrutura import bounds, check_history, created, valid

from brasbim.core import guid, plan, terrain, transform
from brasbim.core.annotations import commands as ac
from brasbim.core.delete import delete_elements
from brasbim.core.drawings import section
from brasbim.core.structure import railings, stairs


def _stair(model, start=(0, 0), angle=0.0, **options):
    return created(model, stairs.create_stair(model.doc, model.terreo, start, angle, **options))


def _parts(stair, ifc_class):
    return [p for p in stairs.parts_of(stair) if p.is_a(ifc_class)]


def test_et01_escada_reta(model):
    def create():
        _stair(model, railing="none")

    check_history(model, create)
    (stair,) = model.doc.ifc.by_type("IfcStair")
    assert stair.PredefinedType == "STRAIGHT_RUN_STAIR"
    assert ue.get_container(stair) == model.terreo
    lay = stairs.layout(model.doc, stairs.read_state(stair))
    assert lay.risers == 16
    assert lay.riser == pytest.approx(0.175)
    assert lay.tread == pytest.approx(0.28)
    (flight,) = _parts(stair, "IfcStairFlight")
    assert not flight.ContainedInStructure  # só a escada fica no pavimento
    assert (flight.NumberOfRisers, flight.NumberOfTreads) == (16, 15)
    assert flight.RiserHeight == pytest.approx(0.175)
    assert flight.TreadLength == pytest.approx(0.28)
    lo, hi = bounds(flight)
    assert hi[2] + flight.RiserHeight == pytest.approx(2.80)  # o último espelho chega
    assert lo[2] == pytest.approx(0.0, abs=1e-6)
    assert hi[0] == pytest.approx(15 * 0.28)
    assert (lo[1], hi[1]) == pytest.approx((0.0, 1.20))
    common = ue.get_pset(stair, "Pset_StairCommon")
    assert common["NumberOfRiser"] == 16 and common["NumberOfTreads"] == 15
    assert not stairs.warnings_of(lay)
    assert valid(model.doc.ifc)


@pytest.mark.parametrize("shape", ["L", "U"])
def test_et02_escada_em_l_e_em_u(model, shape):
    stair = _stair(model, shape=shape, railing="none")
    assert stair.PredefinedType == stairs.PREDEFINED[shape]
    flights = _parts(stair, "IfcStairFlight")
    (landing,) = _parts(stair, "IfcSlab")
    assert len(flights) == 2 and landing.PredefinedType == "LANDING"
    assert [f.NumberOfRisers for f in flights] == [8, 8]
    assert bounds(landing)[1][2] == pytest.approx(8 * 0.175)
    assert max(bounds(f)[1][2] for f in flights) + 0.175 == pytest.approx(2.80)
    # a laje do patamar não entra nas listas de lajes
    from brasbim.core.structure import commands as sc

    assert not sc.is_structure(landing)
    left_y = [q[1] for ring in stairs.footprint(model.doc, stairs.read_state(stair))
              for q in ring]
    model.commit(stairs.edit_stair(model.doc, stair, turn="right"))
    right_y = [q[1] for ring in stairs.footprint(model.doc, stairs.read_state(stair))
               for q in ring]
    assert min(left_y) == pytest.approx(0.0) and max(left_y) > 1.20
    assert max(right_y) == pytest.approx(1.20) and min(right_y) < 0.0
    assert valid(model.doc.ifc)


def test_et03_guarda_corpo_da_escada(model):
    stair = _stair(model)
    rails = _parts(stair, "IfcRailing")
    assert len(rails) == 2
    for rail in rails:
        assert rail.PredefinedType == "GUARDRAIL"
        lo, hi = bounds(rail)
        assert lo[2] == pytest.approx(0.175, abs=0.03)  # sobe a partir do primeiro degrau
        assert hi[2] == pytest.approx(2.80 + 1.10, abs=0.05)
    ys = sorted(bounds(r)[0][1] for r in rails)
    assert ys[0] == pytest.approx(stairs.INSET - railings.POST / 2, abs=0.03)
    # em L, o guarda-corpo de fora contorna o patamar na cota dele
    model.commit(stairs.edit_stair(model.doc, stair, shape="L"))
    rails = _parts(stair, "IfcRailing")
    assert len(rails) == 5
    (landing,) = [r for r in rails if r.GlobalId == guid.derived(stair.GlobalId,
                                                                    "railing/landing")]
    assert bounds(landing)[0][2] == pytest.approx(8 * 0.175, abs=1e-6)
    assert bounds(landing)[1][2] == pytest.approx(8 * 0.175 + 1.10, abs=1e-3)
    model.commit(stairs.edit_stair(model.doc, stair, railing="none"))
    assert not model.doc.ifc.by_type("IfcRailing")
    model.history.undo()
    assert len(model.doc.ifc.by_type("IfcRailing")) == 5
    assert valid(model.doc.ifc)


def test_et04_planta_transformacoes_e_exclusao(model):
    stair = _stair(model)
    p = plan.storey_plan(model.doc, model.terreo)
    prims = dict(p.annotations)[stair.GlobalId]
    dashed = [s for s in prims.strokes if s.dash == "dashed"]
    solid_steps = [s for s in prims.strokes if s.dash == "solid" and len(s.points) == 2
                   and s.weight == 0.18]
    assert dashed and solid_steps  # degraus acima do plano de corte tracejados
    assert stair.GlobalId in {s.owner for s in p.shapes}
    gid = stair.GlobalId
    # corte longitudinal no meio da largura: o lance cortado responde pela escada
    view = created(model, ac.create_view(model.doc, "section", (-1, 0.6), (6, 0.6), "left"))
    cuts = [it for it in section.draw(model.doc, view).cuts() if it.owner == gid]
    assert cuts
    top = max(q[1] for it in cuts for r in it.rings for q in r)
    assert top == pytest.approx(2.80 - 0.175, abs=1e-3)
    model.commit(delete_elements(model.doc, [view.GlobalId])[0])

    def transform_all():
        model.commit(transform.move_elements(model.doc, [gid], (2.0, 1.0)))
        model.commit(transform.rotate_elements(model.doc, [gid], (2.0, 1.0), math.pi / 2))

    check_history(model, transform_all)
    state = stairs.read_state(stair)
    assert state["start"] == pytest.approx([2.0, 1.0])
    assert state["angle"] == pytest.approx(90.0)
    lo, hi = bounds(_parts(stair, "IfcStairFlight")[0])
    assert (lo[0], hi[0]) == pytest.approx((2.0 - 1.20, 2.0), abs=1e-6)
    assert hi[1] == pytest.approx(1.0 + 15 * 0.28)
    # selecionar uma peça (o lance) move a escada inteira
    flight = _parts(stair, "IfcStairFlight")[0]
    model.commit(transform.move_elements(model.doc, [flight.GlobalId], (1.0, 0.0)))
    assert stairs.read_state(stair)["start"] == pytest.approx([3.0, 1.0])
    # espelhar troca o giro e mantém a planta no lugar da imagem
    before = stairs.footprint(model.doc, stairs.read_state(stair))[0]
    model.commit(transform.mirror_elements(model.doc, [gid], (0, 0), (0, 10)))
    state = stairs.read_state(stair)
    assert state["turn"] == "right"
    after = stairs.footprint(model.doc, state)[0]
    assert sorted((round(-x, 6), round(y, 6)) for x, y in before) == \
        sorted((round(x, 6), round(y, 6)) for x, y in after)
    tx = transform.copy_elements(model.doc, [gid], (5.0, 0.0))
    model.commit(tx)
    assert sorted(s.Name for s in stairs.all_stairs(model.doc)) == ["Escada 1", "Escada 2"]
    tx, _ = delete_elements(model.doc, [flight.GlobalId])
    assert tx.label == "Excluir"
    model.commit(tx)
    assert len(model.doc.ifc.by_type("IfcStair")) == 1
    assert len(model.doc.ifc.by_type("IfcStairFlight")) == 1
    assert len(model.doc.ifc.by_type("IfcRailing")) == 2
    model.history.undo()
    assert len(model.doc.ifc.by_type("IfcStairFlight")) == 2
    assert valid(model.doc.ifc)


def test_et05_aviso_de_espelho(model, caplog):
    with caplog.at_level(logging.WARNING, logger="brasbim.core.structure.stairs"):
        _stair(model)
    assert not caplog.records
    with caplog.at_level(logging.WARNING, logger="brasbim.core.structure.stairs"):
        stair = _stair(model, start=(0, 3), risers=14)
    assert any("espelho de 20,0 cm fora de 16–18 cm" in r.getMessage()
               for r in caplog.records)
    assert stairs.read_state(stair)["risers"] == 14
    with pytest.raises(Exception, match="2 espelhos"):
        stairs.create_stair(model.doc, model.terreo, (0, 0), risers=1)
    with pytest.raises(Exception, match="60 cm"):
        stairs.create_stair(model.doc, model.terreo, (0, 0), width=0.5)


def test_et06_guarda_corpo_solto(model):
    def create():
        model.commit(railings.create_railing(model.doc, model.superior,
                                             [(0, 0), (5, 0), (5, 2)]))

    check_history(model, create)
    (rail,) = model.doc.ifc.by_type("IfcRailing")
    assert railings.is_railing(rail) and rail.PredefinedType == "GUARDRAIL"
    assert ue.get_container(rail) == model.superior
    state = railings.read_state(rail)
    feet = railings.posts([(*q, state["base"]) for q in state["points"]], state["spacing"])
    gaps = [math.dist(a[:2], b[:2]) for a, b in itertools.pairwise(feet)]
    assert max(gaps) <= 1.20 + 1e-9
    assert len(feet) == 1 + 5 + 2  # 5 m em 5 vãos de 1,00; 2 m em 2 vãos
    lo, hi = bounds(rail)
    assert lo[2] == pytest.approx(2.80, abs=1e-6)
    assert hi[2] == pytest.approx(2.80 + 1.10, abs=1e-3)
    assert ue.get_pset(rail, "Qto_RailingBaseQuantities")["Length"] == pytest.approx(7.0)
    assert ue.get_pset(rail, "Pset_RailingCommon")["Height"] == pytest.approx(1.10)
    p = plan.storey_plan(model.doc, model.superior)
    assert rail.GlobalId in dict(p.annotations)
    model.commit(transform.move_elements(model.doc, [rail.GlobalId], (1.0, 0.0)))
    assert railings.read_state(rail)["points"][0] == pytest.approx([1.0, 0.0])
    model.commit(delete_elements(model.doc, [rail.GlobalId])[0])
    assert not model.doc.ifc.by_type("IfcRailing")
    with pytest.raises(Exception, match="2 pontos"):
        railings.create_railing(model.doc, model.superior, [(0, 0)])
    assert valid(model.doc.ifc)


POINTS = [(0, 0, 0.0), (10, 0, 1.0), (10, 8, 3.0), (0, 8, 2.0), (5, 4, 2.5)]


def test_et07_terreno(model):
    def create():
        model.commit(terrain.create_terrain(model.doc, POINTS))

    check_history(model, create)
    (t,) = model.doc.ifc.by_type("IfcGeographicElement")
    assert t.PredefinedType == "TERRAIN"
    assert ue.get_container(t) == model.doc.ifc.by_type("IfcSite")[0]
    (faces,) = t.Representation.Representations[0].Items
    assert faces.is_a("IfcTriangulatedFaceSet")
    assert len(faces.CoordIndex) == 4
    assert terrain.height_at(terrain.read_state(t), (5, 4)) == pytest.approx(2.5)
    levels = [z for z, _ in terrain.contours(terrain.read_state(t))]
    assert levels == pytest.approx([1.0, 2.0])  # 0 e 3 tocam só um vértice: sem curva
    low = plan.storey_plan(model.doc, model.terreo)
    assert t.GlobalId in dict(low.annotations)
    high = plan.storey_plan(model.doc, model.superior)
    assert t.GlobalId not in dict(high.annotations)
    model.commit(terrain.edit_terrain(model.doc, t, interval=0.5))
    assert len(terrain.contours(terrain.read_state(t))) == 5  # 0,5 a 2,5
    model.commit(transform.move_elements(model.doc, [t.GlobalId], (1.0, 1.0)))
    assert terrain.read_state(t)["points"][0] == pytest.approx([1.0, 1.0, 0.0])
    with pytest.raises(Exception, match="alinhados"):
        terrain.create_terrain(model.doc, [(0, 0, 0), (1, 0, 0), (2, 0, 0)])
    model.commit(delete_elements(model.doc, [t.GlobalId])[0])
    assert not model.doc.ifc.by_type("IfcGeographicElement")
    assert valid(model.doc.ifc)
