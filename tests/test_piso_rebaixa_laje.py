# SPDX-License-Identifier: LGPL-3.0-or-later
"""Piso rebaixa a laje (spec/ui 46 §8 (c), revisão de 2026-11-07): a laje e o piso tinham o
topo na mesma cota e se sobrepunham (o 3D piscava e o volume contava duas vezes). Agora o
piso corta a laje no seu contorno, na sua espessura (``IfcRelInterferesElements``)."""

import pytest
from estrutura import bounds, created, qto, slab_type, valid
from test_forro_piso import ROOM, ctype, floor_type, room_with_walls, space

from brasbim.core import delete
from brasbim.core.structure import commands as sc
from brasbim.core.structure import coverings as cv
from brasbim.core.structure import cuts
from brasbim.core.walls import commands as wc

T_PISO = 0.015  # Porcelanato 10 mm + argamassa 5 mm


def _slab(model):
    return created(model, sc.create_slab(model.doc, slab_type(model), model.terreo,
                                         [(-1, -1), (5, -1), (5, 4), (-1, 4)]))


def _recesses(slab):
    return [r.RelatedElement for r in slab.InterferesElements or ()
            if r.is_a("IfcRelInterferesElements") and r.InterferenceType == cuts.INTERFERENCE]


def test_piso_rebaixa_a_laje(model):
    slab = _slab(model)
    floor = created(model, cv.create_in_space(model.doc, floor_type(model), space(model)))
    (cut,) = cuts.cuts_of(model.doc, slab)
    assert cut.cutter.gid == floor.GlobalId and cut.mode == "top"
    assert _recesses(slab) == [floor]
    q = qto(slab, "Qto_SlabBaseQuantities")
    assert q["GrossVolume"] - q["NetVolume"] == pytest.approx(12 * T_PISO)
    assert q["NetArea"] == pytest.approx(q["GrossArea"])  # rebaixo não fura
    assert any(r.RepresentationType == "Clipping" for r in slab.Representation.Representations)
    _lo, hi = bounds(slab)
    assert hi[2] == pytest.approx(0.0)  # fora do ambiente a laje continua no nível
    assert valid(model.doc.ifc)


def test_piso_excluido_ou_desfeito_devolve_a_laje(model):
    slab = _slab(model)
    floor = created(model, cv.create_in_space(model.doc, floor_type(model), space(model)))
    tx, _ = delete.delete_elements(model.doc, [floor.GlobalId])
    model.commit(tx)
    q = qto(slab, "Qto_SlabBaseQuantities")
    assert q["NetVolume"] == pytest.approx(q["GrossVolume"])
    assert _recesses(slab) == []
    model.history.undo()
    assert len(_recesses(slab)) == 1
    model.history.undo()  # desfaz a criação do piso
    assert _recesses(slab) == []
    assert qto(slab, "Qto_SlabBaseQuantities")["NetVolume"] == pytest.approx(
        qto(slab, "Qto_SlabBaseQuantities")["GrossVolume"])


def test_rebaixo_acompanha_o_ambiente(model):
    slab = _slab(model)
    s = room_with_walls(model)
    floor = created(model, cv.create_in_space(model.doc, floor_type(model), s))

    def removed():
        q = qto(slab, "Qto_SlabBaseQuantities")
        return q["GrossVolume"] - q["NetVolume"]

    assert removed() == pytest.approx(12 * T_PISO)
    east = max(model.doc.ifc.by_type("IfcWall"), key=lambda w: bounds(w)[0][0])
    model.commit(wc.offset_wall(model.doc, east, 1.0))
    area = qto(floor, cv.QTO)["GrossArea"]
    assert area != pytest.approx(12.0)
    assert removed() == pytest.approx(area * T_PISO)
    model.history.undo()
    assert removed() == pytest.approx(12 * T_PISO)


def test_forro_e_parede_nao_entram(model):
    slab = _slab(model)
    floor = created(model, cv.create_in_space(model.doc, floor_type(model), space(model)))
    created(model, cv.create_covering(model.doc, ctype(model), model.terreo, ROOM,
                                      elevation=-0.05))
    assert [c.cutter.gid for c in cuts.cuts_of(model.doc, slab)] == [floor.GlobalId]
    wall = model.wall((0, 1), (4, 1))  # parede sobre o piso: o piso não a corta
    assert all(c.cutter.element.is_a() != "IfcCovering"
               for c in cuts.cuts_of(model.doc, wall))
