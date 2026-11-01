# SPDX-License-Identifier: LGPL-3.0-or-later
"""Operações de sólidos (spec/ui 41 §3): SO01 a SO05."""

import logging

import ifcopenshell.util.element as ue
import pytest
from estrutura import bounds, check_history, slab_type, valid

from brasbim.core import delete, transform
from brasbim.core.document import OpError
from brasbim.core.ops import Transaction
from brasbim.core.structure import commands as sc
from brasbim.core.structure import solids
from brasbim.core.walls import commands as cmd

TILE = [{"material": "Telha cerâmica", "thickness": 0.05}]


def _net(wall):
    return ue.get_pset(wall, "Qto_WallBaseQuantities")["NetVolume"]


def _cut(model, targets, operators, operation):
    return model.commit(Transaction("Recortar por elemento", solids.add_ops(
        model.doc, targets, operators, operation)))


def _rels(element):
    return [r for r in element.InterferesElements if solids.is_solid_rel(r)]


def _crossing(model):
    """Parede A de (0, 0) a (5, 0) e parede B atravessando-a em x = 2,5 (sem junção)."""
    a = model.wall((0, 0), (5, 0))
    b = model.wall((2.43, -1), (2.43, 1), ref_line="axis")
    return a, b


def test_so01_subtrair(model, tmp_path):
    a, b = _crossing(model)
    assert _net(a) == pytest.approx(5 * 0.14 * 2.8)
    _cut(model, [a], [b], solids.SUBTRACT)
    (rel,) = _rels(a)
    assert rel.RelatingElement == a and rel.RelatedElement == b
    assert rel.InterferenceType == "SUBTRACT" and rel.ImpliedOrder is True
    body = next(r for r in a.Representation.Representations
                if r.RepresentationIdentifier == "Body")
    assert body.RepresentationType == "CSG"
    assert body.Items[0].is_a("IfcBooleanResult")
    assert body.Items[0].SecondOperand.is_a("IfcTriangulatedFaceSet")
    # sai o pedaço comum: 0,14 × 0,14 × 2,80
    assert _net(a) == pytest.approx(5 * 0.14 * 2.8 - 0.14 * 0.14 * 2.8, abs=1e-4)
    assert _net(b) == pytest.approx(2 * 0.14 * 2.8)  # o operador não muda
    valid(model.doc.ifc)
    f = model.reopen(tmp_path)
    (rel2,) = [r for r in f.by_type("IfcRelInterferesElements")
               if r.InterferenceType == "SUBTRACT"]
    assert rel2.RelatingElement.GlobalId == a.GlobalId


def test_so01_historico(model):
    a, b = _crossing(model)
    check_history(model, lambda: _cut(model, [a], [b], solids.SUBTRACT))


def test_so01_recusas(model):
    a, b = _crossing(model)
    _cut(model, [a], [b], solids.SUBTRACT)
    with pytest.raises(OpError, match="já é recortado"):
        solids.add_ops(model.doc, [a], [b], solids.INTERSECT)
    with pytest.raises(OpError, match="circular"):
        solids.add_ops(model.doc, [b], [a], solids.SUBTRACT)
    with pytest.raises(OpError, match="diferente"):
        solids.add_ops(model.doc, [a], [a], solids.SUBTRACT)


def test_so02_cobertura_aparando_parede(model):
    wall = model.wall((0, 0), (0, 6), ref_line="axis", top_mode="fixed", fixed_height=6.0)
    roof_type = slab_type(model, "Telha", TILE, "ROOF")
    roof = model.doc.get(model.commit(sc.create_roof(
        model.doc, roof_type, model.terreo, [(-1, 0), (1, 0), (1, 6), (-1, 6)],
        shape="gable", side=1, base_height=2.8, overhang=0.6)).ops[0].id)
    before = _net(wall)
    _cut(model, [wall], [roof], solids.UP)
    body = next(r for r in wall.Representation.Representations
                if r.RepresentationIdentifier == "Body")
    assert body.RepresentationType == "Clipping"
    _lo, hi = bounds(wall)
    # cumeeira em y = 3: abaixo da parede de 6 m, que fica cortada pela água
    assert hi[2] < 4.0
    assert _net(wall) < before - 0.14 * 6 * 2.0
    valid(model.doc.ifc)


def test_so03_mover_o_operador_refaz_o_alvo(model):
    a, b = _crossing(model)
    _cut(model, [a], [b], solids.SUBTRACT)
    cut = _net(a)
    model.commit(transform.move_elements(model.doc, [b.GlobalId], (10, 0)))
    assert _net(a) == pytest.approx(5 * 0.14 * 2.8, abs=1e-4)  # longe: nada a tirar
    assert _rels(a)
    model.commit(transform.move_elements(model.doc, [b.GlobalId], (-10, 0)))
    assert _net(a) == pytest.approx(cut, abs=1e-6)
    # editar o alvo mantém o recorte
    model.commit(cmd.edit_wall(model.doc, a, top_mode="fixed", fixed_height=3.0))
    assert _net(a) == pytest.approx(5 * 0.14 * 3.0 - 0.14 * 0.14 * 2.8, abs=1e-4)


def test_so04_apagar_o_operador_devolve_e_avisa(model, caplog):
    a, b = _crossing(model)
    _cut(model, [a], [b], solids.SUBTRACT)
    tx, _ = delete.delete_elements(model.doc, [b.GlobalId])
    with caplog.at_level(logging.WARNING):
        model.commit(tx)
    assert "deixou de ser recortado" in caplog.text
    assert not _rels(a)
    assert _net(a) == pytest.approx(5 * 0.14 * 2.8)
    assert next(r for r in a.Representation.Representations
            if r.RepresentationIdentifier == "Body").RepresentationType == "SweptSolid"
    model.history.undo()
    assert len(_rels(a)) == 1
    assert _net(a) < 5 * 0.14 * 2.8 - 0.05
    valid(model.doc.ifc)


def test_so04_apagar_o_alvo(model):
    a, b = _crossing(model)
    _cut(model, [a], [b], solids.SUBTRACT)
    tx, _ = delete.delete_elements(model.doc, [a.GlobalId])
    model.commit(tx)
    assert not model.doc.ifc.by_type("IfcRelInterferesElements")
    model.history.undo()
    a = model.doc.get(a.GlobalId)
    assert len(_rels(a)) == 1


def test_so05_intersecao(model):
    a, b = _crossing(model)
    _cut(model, [a], [b], solids.INTERSECT)
    assert _net(a) == pytest.approx(0.14 * 0.14 * 2.8, abs=1e-4)
    lo, hi = bounds(a)
    assert (lo[0], hi[0]) == pytest.approx((2.36, 2.50), abs=1e-3)
    valid(model.doc.ifc)
