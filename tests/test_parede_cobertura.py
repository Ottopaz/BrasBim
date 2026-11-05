# SPDX-License-Identifier: LGPL-3.0-or-later
"""Parede com o topo até a cobertura (spec/ui 45, RC01–RC07)."""

import ifcopenshell.util.element as ue
import pytest
from estrutura import bounds, check_history, created, qto, slab_type, valid

from brasbim.core import delete
from brasbim.core.document import OpError
from brasbim.core.structure import commands as sc
from brasbim.core.structure import solids
from brasbim.core.walls import commands as wc
from brasbim.core.walls import rebuild, roof_top
from brasbim.core.walls.wall import read_state

TILE = [{"material": "Telha cerâmica", "thickness": 0.05}]


def roof_of(model, outline=None, **options):
    """Duas águas sobre 10 × 6 (cumeeira em y = 3), apoio a 2,80, 30 %, beiral 0,60."""
    t = slab_type(model, "Telha cerâmica", TILE, "ROOF")
    options.setdefault("base_height", 2.80)
    return created(model, sc.create_roof(model.doc, t, model.terreo,
                                         outline or [(0, 0), (10, 0), (10, 6), (0, 6)],
                                         **options))


def wall_type(model):
    return model.doc.ifc.by_type("IfcWallType")[0]


def wall(model, start, end, **options):
    return created(model, wc.create_wall(model.doc, wall_type(model), model.terreo, start,
                                         end, **options))


def thickness(model):
    from brasbim.core.walls import types as wall_types

    return wall_types.thickness(wall_type(model))


def body_volume(element) -> float:
    """Volume do corpo medido pelo motor geométrico (confere os semiespaços)."""
    import ifcopenshell.geom
    import ifcopenshell.util.shape

    settings = ifcopenshell.geom.settings()
    return ifcopenshell.util.shape.get_volume(
        ifcopenshell.geom.create_shape(settings, element).geometry)


def roof_rels(element):
    return [r for r in element.InterferesElements if roof_top.is_roof_rel(r)]


def test_rc01_oitao_sob_duas_aguas(model, tmp_path):
    roof = roof_of(model)
    w = wall(model, (0, 0), (0, 6))  # perpendicular à cumeeira: o oitão
    model.commit(roof_top.attach(model.doc, [w], roof))
    state = read_state(model.doc, w)
    assert state["top_mode"] == "roof" and state["top_roofs"] == [roof.GlobalId]
    assert rebuild.height(model.doc, state) == pytest.approx(3.70)
    hi = bounds(w)[1]
    assert hi[2] == pytest.approx(3.70, abs=1e-6)
    t = thickness(model)
    q = qto(w, "Qto_WallBaseQuantities")
    # retângulo até o beiral (2,80 em y = 0 e 6) + o triângulo até a cumeeira
    assert q["Height"] == pytest.approx(3.70)
    assert q["NetVolume"] == pytest.approx(t * (6 * 2.8 + 0.5 * 6 * 0.9), rel=1e-3)
    assert body_volume(w) == pytest.approx(q["NetVolume"], rel=1e-3)
    (rel,) = roof_rels(w)
    assert rel.RelatedElement == roof and rel.InterferenceType == "SUBTRACT_UP"
    assert rel.ImpliedOrder and not solids.cut_by(w)  # não é operação de sólido
    assert valid(model.doc.ifc)
    # reabre igual
    from brasbim.core.document import Document

    path = tmp_path / "rc01.ifc"
    model.doc.ifc.write(str(path))
    again = Document.open(str(path))
    assert read_state(again, again.get(w.GlobalId))["top_roofs"] == [roof.GlobalId]


def test_rc02_parede_paralela_a_cumeeira(model):
    roof = roof_of(model)
    # parede em y = 1, paralela à cumeeira: topo inclinado na espessura
    w = wall(model, (0, 1), (10, 1))
    model.commit(roof_top.attach(model.doc, [w], roof))
    t = thickness(model)
    hi = bounds(w)[1]
    # left_face: a faixa vai de y = 1 − t a 1; o ponto mais alto é na face y = 1
    assert hi[2] == pytest.approx(2.8 + 0.3 * 1.0, abs=1e-6)
    q = qto(w, "Qto_WallBaseQuantities")
    mid = 1.0 - t / 2
    assert q["NetVolume"] == pytest.approx(10 * t * (2.8 + 0.3 * mid), rel=1e-3)


def test_rc02_face_de_cima_platibanda(model):
    roof = roof_of(model)
    w = wall(model, (0, 0), (0, 6))
    model.commit(roof_top.attach(model.doc, [w], roof, face="top"))
    import math

    assert read_state(model.doc, w)["roof_face"] == "top"
    assert bounds(w)[1][2] == pytest.approx(3.70 + 0.05 * math.sqrt(1.09), abs=1e-6)


def test_rc03_associativa(model):
    roof = roof_of(model)
    w = wall(model, (0, 0), (0, 6))
    model.commit(roof_top.attach(model.doc, [w], roof))

    def edit():
        model.commit(sc.edit_element(model.doc, roof, slope=50.0))

    check_history(model, edit)
    assert bounds(w)[1][2] == pytest.approx(2.8 + 0.5 * 3, abs=1e-6)
    model.commit(sc.edit_element(model.doc, roof, base_height=3.0))
    assert bounds(w)[1][2] == pytest.approx(3.0 + 0.5 * 3, abs=1e-6)
    # contorno mais largo: a cumeeira sobe (y = 4)
    model.commit(sc.edit_element(model.doc, roof,
                                 outline=[[0, 0], [10, 0], [10, 8], [0, 8]]))
    assert rebuild.height(model.doc, read_state(model.doc, w)) == pytest.approx(
        3.0 + 0.5 * 4)
    assert valid(model.doc.ifc)


def test_rc04_soltar_e_apagar_a_cobertura(model):
    roof = roof_of(model)
    w = wall(model, (0, 0), (0, 6))
    before = read_state(model.doc, w)
    assert before["top_mode"] == "storey"
    model.commit(roof_top.attach(model.doc, [w], roof))
    model.commit(roof_top.detach(model.doc, [w]))
    after = read_state(model.doc, w)
    assert (after["top_mode"], after["top_storey"]) == ("storey", before["top_storey"])
    assert not roof_rels(w)
    # apagar a cobertura solta a parede; desfazer prende de novo
    model.commit(roof_top.attach(model.doc, [w], roof))
    tx, _ = delete.delete_elements(model.doc, [roof.GlobalId])
    model.commit(tx)
    assert read_state(model.doc, w)["top_mode"] == "storey"
    model.history.undo()
    assert read_state(model.doc, w)["top_roofs"] == [roof.GlobalId]
    assert roof_rels(w)
    assert valid(model.doc.ifc)


def test_rc05_trecho_descoberto_e_recusas(model):
    roof = roof_of(model, outline=[(0, 0), (6, 0), (6, 6), (0, 6)], base_height=2.0)
    # parede que sai do telhado: do x = 3 ao x = 12 (o beiral vai até 6,60)
    w = wall(model, (3, 3), (12, 3))
    model.commit(roof_top.attach(model.doc, [w], roof))
    state = read_state(model.doc, w)
    result = roof_top.shape(model.doc, state)
    assert result.uncovered and result.reserve == pytest.approx(2.80)
    profile = roof_top.axis_profile(model.doc, state, result)
    assert profile[-1][1] == pytest.approx(2.80)  # ponta descoberta: no pavimento de cima
    assert body_volume(w) == pytest.approx(qto(w, "Qto_WallBaseQuantities")["NetVolume"],
                                           rel=1e-3)
    # sob o telhado, a altura da água (a parede corre na cumeeira, a 2,90)
    assert roof_top.top_at(model.doc, state, result, (4.5, 2.99)) == pytest.approx(
        2.0 + 0.3 * 2.99)
    with pytest.raises(OpError, match="não passa sobre"):
        roof_top.attach(model.doc, [wall(model, (20, 0), (25, 0))], roof)
    tilted = wall(model, (1, 1), (1, 5), tilt=5.0)
    with pytest.raises(OpError, match="tombada"):
        roof_top.attach(model.doc, [tilted], roof)
    assert valid(model.doc.ifc)


def test_rc06_duas_coberturas_na_mesma_parede(model):
    low = roof_of(model, outline=[(0, 0), (5, 0), (5, 6), (0, 6)], shape="shed",
                  base_height=2.6, side=0)
    high = roof_of(model, outline=[(5, 0), (10, 0), (10, 6), (5, 6)], shape="shed",
                   base_height=3.0, side=0, overhang=0.0)
    w = wall(model, (0, 6), (10, 6))
    model.commit(roof_top.attach(model.doc, [w], low))
    model.commit(roof_top.attach(model.doc, [w], high))
    state = read_state(model.doc, w)
    assert state["top_roofs"] == [low.GlobalId, high.GlobalId]
    assert len(roof_rels(w)) == 2
    assert body_volume(w) == pytest.approx(qto(w, "Qto_WallBaseQuantities")["NetVolume"],
                                           rel=1e-3)
    result = roof_top.shape(model.doc, state)
    assert roof_top.top_at(model.doc, state, result, (2.5, 6 - 0.01)) < \
        roof_top.top_at(model.doc, state, result, (7.5, 6 - 0.01))
    assert valid(model.doc.ifc)


def test_rc07_criar_a_cobertura_prende_as_paredes(model):
    t = wall_type(model)
    model.commit(wc.create_rectangle(model.doc, t, model.terreo, (0, 0), (10, 6)))
    walls = model.doc.ifc.by_type("IfcWall")
    inner = wall(model, (5, 0), (5, 6), top_mode="fixed", fixed_height=1.2)  # baixa
    roof = roof_of(model)
    found = roof_top.candidates(model.doc, roof)
    assert set(found) == set(walls) and inner not in found
    model.commit(roof_top.auto_attach(model.doc, roof))
    assert all(read_state(model.doc, w)["top_mode"] == "roof" for w in walls)
    # janela acima do telhado na parede da frente (topo 2,80 sob o beiral) recebe o aviso
    from brasbim.core.walls import openings

    front = min(walls, key=lambda w: bounds(w)[0][1])
    state = read_state(model.doc, front)
    result = roof_top.shape(model.doc, state)
    band = rebuild.band(model.doc, state)
    found = openings.problems(
        {"kind": "OPENING", "distance": 4.0, "width": 1.0, "height": 1.0, "sill": 2.2,
         "depth": None, "side": "left"},
        band, result.height, roof_top.axis_profile(model.doc, state, result))
    assert found == ["ultrapassa o topo da parede"]
    assert ue.get_container(roof) == model.terreo
    assert valid(model.doc.ifc)
