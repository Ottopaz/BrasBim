# SPDX-License-Identifier: LGPL-3.0-or-later
"""Recortes por prioridade (spec/ui 12 §2): RC01 a RC10."""

import ifcopenshell.util.element as ue
import pytest
from conftest import snapshot
from estrutura import (
    beam_type,
    bounds,
    check_history,
    column_type,
    created,
    foreign_ifc,
    slab_type,
    valid,
)

from brasbim.core import transform
from brasbim.core.document import Document
from brasbim.core.ops import History
from brasbim.core.structure import commands as sc


def _column(model, p, t=None, storey=None):
    return created(model, sc.create_column(model.doc, t or column_type(model),
                                           storey or model.terreo, p))


def _beam(model, a=(0, 0), b=(5, 0), t=None, **options):
    return created(model, sc.create_beam(model.doc, t or beam_type(model), model.terreo, a, b,
                                         **options))


def _slab(model, a=(0, 0), b=(5, 4), storey=None):
    return created(model, sc.create_slab_rectangle(model.doc, slab_type(model),
                                                   storey or model.superior, a, b))


def _body(element):
    return next(r for r in element.Representation.Representations
                if r.RepresentationIdentifier == "Body")


def _q(element, name):
    return ue.get_pset(element, name)


def _rels(element):
    return [r for r in element.InterferesElements if r.is_a("IfcRelInterferesElements")]


def test_rc01_viga_termina_na_face_dos_pilares(model):
    t = column_type(model)
    _column(model, (0, 0), t)
    _column(model, (5, 0), t)
    beam = _beam(model)
    body = _body(beam)
    assert body.RepresentationType == "Clipping"
    item, n = body.Items[0], 0
    while item.is_a("IfcBooleanClippingResult"):
        item, n = item.FirstOperand, n + 1
    assert n == 2
    assert _q(beam, "Qto_BeamBaseQuantities")["NetVolume"] == pytest.approx(0.14 * 0.4 * 4.8)
    assert _q(beam, "Qto_BeamBaseQuantities")["GrossVolume"] == pytest.approx(0.28)
    lo, hi = bounds(beam)
    assert (lo[0], hi[0]) == pytest.approx((0.1, 4.9))


def test_rc02_pilar_fica_inteiro(model):
    t = column_type(model)
    column = _column(model, (0, 0), t)
    _beam(model)
    assert _body(column).RepresentationType == "SweptSolid"
    assert _q(column, "Qto_ColumnBaseQuantities")["NetVolume"] == pytest.approx(0.08 * 2.8)


def test_rc03_pilar_atravessa_a_laje_do_superior(model):
    _column(model, (0.1, 0.2))  # seção x ∈ [0; 0,2], y ∈ [0; 0,4]: dentro da laje
    slab = _slab(model)
    q = _q(slab, "Qto_SlabBaseQuantities")
    assert q["NetVolume"] == pytest.approx(2.0 - 0.08 * 0.10)
    assert q["NetArea"] == pytest.approx(20 - 0.08)
    assert q["GrossArea"] == pytest.approx(20)


def test_rc04_viga_corta_a_laje(model):
    beam = _beam(model, (0, 2), (5, 2))
    slab = _slab(model)
    q = _q(slab, "Qto_SlabBaseQuantities")
    assert q["NetVolume"] == pytest.approx(2.0 - 0.14 * 5 * 0.10)
    assert _body(beam).RepresentationType == "SweptSolid"


def test_rc05_viga_sobre_a_parede(model):
    wall = model.wall((0, 0), (5, 0), ref_line="axis")
    _beam(model)
    q = ue.get_pset(wall, "Qto_WallBaseQuantities")
    assert q["NetVolume"] == pytest.approx(0.14 * 5 * 2.40)
    assert _body(wall).RepresentationType == "Clipping"
    _, hi = bounds(wall)
    assert hi[2] == pytest.approx(2.40)


def test_rc06_relacao_de_interferencia(model):
    t = column_type(model)
    column = _column(model, (0, 0), t)
    beam = _beam(model)
    (rel,) = _rels(beam)
    assert rel.RelatingElement == beam and rel.RelatedElement == column
    assert rel.ImpliedOrder is True and rel.InterferenceType == "Recorte"
    model.commit(transform.move_elements(model.doc, [column], (0, 3)))
    assert _rels(beam) == []
    model.history.undo()
    assert len(_rels(beam)) == 1


def test_rc07_mover_desfazer_e_diario(model):
    t, bt = column_type(model), beam_type(model)

    def action():
        column = _column(model, (0, 0), t)
        beam = _beam(model, t=bt)
        model.commit(transform.move_elements(model.doc, [column], (0, 3)))
        assert _body(beam).RepresentationType == "SweptSolid"
        assert _q(beam, "Qto_BeamBaseQuantities")["NetVolume"] == pytest.approx(0.28)
        model.commit(transform.move_elements(model.doc, [column], (0, -3)))
        model.commit(sc.delete_element(model.doc, column))
        assert _body(beam).RepresentationType == "SweptSolid"

    check_history(model, action)


def test_rc08_viga_no_meio_da_parede_alta(model, caplog):
    wall = model.wall((0, 0), (5, 0), ref_line="axis", top_mode="fixed", fixed_height=4.0)
    _beam(model, top_mode="fixed", top_elevation=2.8)
    assert _body(wall).RepresentationType == "SweptSolid"
    assert "não a corta" in caplog.text


def test_rc09_outra_origem(tmp_path):
    doc = Document.open(foreign_ifc(tmp_path / "outro.ifc", "IfcColumn"))
    history = History(doc)
    (storey,) = doc.ifc.by_type("IfcBuildingStorey")
    history.commit(sc.create_beam_type(doc, "Viga 14×40", 0.14, 0.40))
    (t,) = doc.ifc.by_type("IfcBeamType")
    tx = sc.create_beam(doc, t, storey, (0, 2.15), (4, 2.15), top_mode="fixed",
                        top_elevation=0.8)
    history.commit(tx)
    beam = doc.get(tx.ops[-1].id)
    assert _body(beam).RepresentationType == "Clipping"  # o pilar importado corta
    (column,) = doc.ifc.by_type("IfcColumn")
    assert _body(column).Items[0].is_a("IfcExtrudedAreaSolid")  # e não é cortado


def test_rc10_validacao_e_3d(model, tmp_path):
    t = column_type(model)
    _column(model, (0, 0), t)
    _column(model, (5, 0), t)
    beam = _beam(model)
    model.wall((0, 0), (5, 0), ref_line="axis")
    _slab(model)
    assert valid(model.reopen(tmp_path))
    import ifcopenshell.geom
    import numpy as np

    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    verts = np.array(ifcopenshell.geom.create_shape(settings, beam).geometry.verts).reshape(-1, 3)
    assert verts[:, 0].min() == pytest.approx(0.1) and verts[:, 0].max() == pytest.approx(4.9)
    assert snapshot(model.doc.ifc)
