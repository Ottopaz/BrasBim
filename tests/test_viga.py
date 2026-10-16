# SPDX-License-Identifier: LGPL-3.0-or-later
"""Viga (RF-ELE-04): critérios de aceite de spec/elementos/viga.md §9."""

import math

import ifcopenshell.util.element as ue
import pytest
from conftest import snapshot
from estrutura import beam_type, bounds, check_history, created, foreign_ifc, qto, valid

from brasbim.core import plan, transform
from brasbim.core.document import Document
from brasbim.core.ops import History
from brasbim.core.ops.base import same_value
from brasbim.core.structure import beams
from brasbim.core.structure import commands as sc
from brasbim.core.walls import commands as wall_cmd


def _beam(model, start=(0, 0), end=(5, 0), t=None, **options):
    return created(model, sc.create_beam(model.doc, t or beam_type(model), model.terreo,
                                         start, end, **options))


def _rep(element, identifier):
    return next(r for r in element.Representation.Representations
                if r.RepresentationIdentifier == identifier)


def test_vi01_viga_basica(model, tmp_path):
    beam = _beam(model)
    lo, hi = bounds(beam)
    assert lo == pytest.approx((0, -0.07, 2.4)) and hi == pytest.approx((5, 0.07, 2.8))
    ifc = model.reopen(tmp_path)
    (beam,) = ifc.by_type("IfcBeam")
    assert ue.get_type(beam).PredefinedType == "BEAM"
    (axis,) = _rep(beam, "Axis").Items
    assert math.dist(*(p.Coordinates for p in axis.Points)) == pytest.approx(5)


def test_vi02_perfil_e_ponto_cardinal(model):
    beam = _beam(model)
    usage = ue.get_material(beam, should_inherit=False)
    assert usage.is_a("IfcMaterialProfileSetUsage") and usage.CardinalPoint == 8
    (mp,) = ue.get_material(ue.get_type(beam)).MaterialProfiles
    assert _rep(beam, "Body").Items[0].SweptArea == mp.Profile


def test_vi03_face_esquerda(model):
    beam = _beam(model, ref_line="left_face")
    assert ue.get_material(beam, should_inherit=False).CardinalPoint == 7
    lo, hi = bounds(beam)
    assert (lo[1], hi[1]) == pytest.approx((-0.14, 0.0))


def test_vi04_viga_inclinada_em_planta(model):
    a = math.radians(30)
    end = (1 + 4 * math.cos(a), 1 + 4 * math.sin(a))
    beam = _beam(model, (1, 1), end)
    state = beams.read_state(model.doc, beam)
    assert state["start"] == pytest.approx([1, 1]) and state["end"] == pytest.approx(list(end))
    assert qto(beam, "Qto_BeamBaseQuantities")["Length"] == pytest.approx(4)


def test_vi05_cota_fixa(model):
    beam = _beam(model, top_mode="fixed", top_elevation=2.6)
    assert bounds(beam)[1][2] == pytest.approx(2.6)
    model.commit(wall_cmd.edit_storey(model.doc, model.superior, elevation=3.0))
    assert bounds(beam)[1][2] == pytest.approx(2.6)


def test_vi06_ligada_ao_pavimento(model):
    beam = _beam(model)
    model.commit(wall_cmd.edit_storey(model.doc, model.superior, elevation=3.0))
    assert bounds(beam)[1][2] == pytest.approx(3.0)


def test_vi07_quantidades(model):
    q = qto(_beam(model), "Qto_BeamBaseQuantities")
    assert q["Length"] == pytest.approx(5)
    assert q["CrossSectionArea"] == pytest.approx(0.056)
    assert q["OuterSurfaceArea"] == pytest.approx(5.4)
    assert q["GrossVolume"] == pytest.approx(0.28) == q["NetVolume"]


def test_vi08_psets_e_reabrir(model, tmp_path):
    beam = _beam(model, ref_line="right_face")
    common = ue.get_pset(beam, "Pset_BeamCommon")
    assert common["Reference"] == "Viga 14×40" and common["Status"] == ["NEW"]
    assert common["LoadBearing"] is True
    state = beams.read_state(model.doc, beam)
    reopened = Document(model.reopen(tmp_path))
    assert same_value(beams.read_state(reopened, reopened.get(beam.GlobalId)), state)


def test_vi09_nomes_automaticos(model):
    t = beam_type(model)
    tx = model.commit(sc.create_beam_chain(model.doc, t, model.terreo, [(0, 0), (5, 0), (5, 4)]))
    assert [model.doc.get(op.id).Name for op in tx.ops] == ["V1", "V2"]
    assert _beam(model, (0, 4), (5, 4), t).Name == "V3"


@pytest.mark.parametrize("show_above", [True, False])
def test_vi10_tracejada_na_planta(model, show_above):
    beam = _beam(model)
    p = plan.storey_plan(model.doc, model.terreo, show_above=show_above)
    faces = [s for s in p.shapes if s.owner == beam.GlobalId and s.role == "beam_above"]
    assert len(faces) == 2 and not any(s.closed for s in faces)
    assert sorted(round(s.points[0][1], 6) for s in faces) == [-0.07, 0.07]
    assert p.pick((2.5, 0.0), 0.05) == beam.GlobalId


def test_vi11_editar_desfazer_e_diario(model):
    t = beam_type(model)

    def action():
        beam = _beam(model, (0, 0), (5, 0), t, ref_line="left_face")
        model.commit(sc.move_beam_end(model.doc, beam, "end", (6, 0)))
        model.commit(transform.move_elements(model.doc, [beam], (1, 1)))
        model.commit(transform.rotate_elements(model.doc, [beam], (0, 0), 0.3))
        model.commit(transform.mirror_elements(model.doc, [beam], (0, 0), (1, 0)))
        model.commit(sc.delete_element(model.doc, beam))

    check_history(model, action)


def test_vi11_espelhar_mantem_o_lado(model):
    beam = _beam(model, ref_line="left_face")
    model.commit(transform.mirror_elements(model.doc, [beam], (0, 1), (1, 1)))
    lo, hi = bounds(beam)
    assert (lo[1], hi[1]) == pytest.approx((2.0, 2.14))
    assert beams.read_state(model.doc, beam)["ref_line"] == "right_face"


def test_vi11_excluir_e_desfazer(model):
    beam = _beam(model)
    before = snapshot(model.doc.ifc)
    count = len(list(model.doc.ifc))
    model.commit(sc.delete_element(model.doc, beam))
    model.history.undo()
    assert snapshot(model.doc.ifc) == before and len(list(model.doc.ifc)) == count


def test_vi12_outra_origem(tmp_path):
    doc = Document.open(foreign_ifc(tmp_path / "outro.ifc", "IfcBeam"))
    history = History(doc)
    (beam,) = doc.ifc.by_type("IfcBeam")
    history.commit(transform.rotate_elements(doc, [beam], (0, 0), math.pi / 2))
    rp = beam.ObjectPlacement.RelativePlacement
    assert rp.Location.Coordinates == pytest.approx((-2.0, 1.0, 0.0))
    assert rp.RefDirection.DirectionRatios == pytest.approx((0.0, 1.0, 0.0))
    assert beam.Representation.Representations[0].Items[0].Depth == pytest.approx(1.0)


def test_vi13_validacao(model, tmp_path):
    t = beam_type(model)
    _beam(model, (0, 0), (5, 0), t)
    _beam(model, (0, 0), (3, 4), t, ref_line="left_face", top_mode="fixed", top_elevation=2.5)
    assert valid(model.reopen(tmp_path))
