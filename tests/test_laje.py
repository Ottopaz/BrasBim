# SPDX-License-Identifier: LGPL-3.0-or-later
"""Laje (RF-ELE-02): critérios de aceite de spec/elementos/laje.md §9."""

import ifcopenshell.util.element as ue
import pytest
from conftest import snapshot
from estrutura import SLAB_145, bounds, check_history, created, foreign_ifc, qto, slab_type, valid

from brasbim.core import plan, transform
from brasbim.core.document import Document, OpError
from brasbim.core.ops import History
from brasbim.core.structure import commands as sc
from brasbim.core.structure import slabs

L_SHAPE_CW = [(0, 0), (0, 4), (2, 4), (2, 2), (5, 2), (5, 0)]


def _slab(model, outline=None, t=None, storey=None, **options):
    t = t or slab_type(model)
    storey = storey or model.terreo
    if outline is None:
        tx = sc.create_slab_rectangle(model.doc, t, storey, (0, 0), (5, 4), **options)
    else:
        tx = sc.create_slab(model.doc, t, storey, outline, **options)
    return created(model, tx)


def test_la01_retangulo(model, tmp_path):
    slab = _slab(model)
    lo, hi = bounds(slab)
    assert lo == pytest.approx((0, 0, -0.1)) and hi == pytest.approx((5, 4, 0))
    ifc = model.reopen(tmp_path)
    (slab,) = ifc.by_type("IfcSlab")
    assert ue.get_type(slab).PredefinedType == "FLOOR" and slab.PredefinedType is None
    (rep,) = slab.Representation.Representations
    assert rep.RepresentationType == "SweptSolid"
    assert rep.Items[0].SweptArea.is_a("IfcArbitraryClosedProfileDef")


def test_la02_camadas(model):
    slab = _slab(model)
    usage = ue.get_material(slab, should_inherit=False)
    assert usage.is_a("IfcMaterialLayerSetUsage")
    assert (usage.LayerSetDirection, usage.DirectionSense) == ("AXIS3", "POSITIVE")
    assert usage.OffsetFromReferenceLine == 0
    total = sum(layer.LayerThickness for layer in usage.ForLayerSet.MaterialLayers)
    assert total == pytest.approx(0.10)
    assert slab.Representation.Representations[0].Items[0].Depth == pytest.approx(0.10)


def test_la03_poligono_horario(model):
    slab = _slab(model, L_SHAPE_CW)
    outline = slabs.read_state(model.doc, slab)["outline"]
    assert len(outline) == 6
    signed = sum(outline[i][0] * outline[(i + 1) % 6][1] - outline[(i + 1) % 6][0] * outline[i][1]
                 for i in range(6))
    assert signed > 0  # anti-horário
    q = qto(slab, "Qto_SlabBaseQuantities")
    assert q["GrossArea"] == pytest.approx(14) and q["Perimeter"] == pytest.approx(18)
    assert q.get("Length") is None


@pytest.mark.parametrize("outline", [[(0, 0), (4, 4), (4, 0), (0, 4)],
                                     [(0, 0), (1, 0), (2, 0)], [(0, 0), (1, 1)]])
def test_la04_contorno_invalido(model, outline):
    t = slab_type(model)
    before = snapshot(model.doc.ifc)
    with pytest.raises(OpError):
        model.commit(sc.create_slab(model.doc, t, model.terreo, outline))
    assert snapshot(model.doc.ifc) == before


def test_la05_deslocamento_do_topo(model, tmp_path):
    slab = _slab(model, top_offset=-0.05)
    lo, hi = bounds(slab)
    assert (lo[2], hi[2]) == pytest.approx((-0.15, -0.05))
    assert ue.get_pset(slab, slabs.PSET)["DeslocamentoTopo"] == pytest.approx(-0.05)
    state = slabs.read_state(model.doc, slab)
    reopened = Document(model.reopen(tmp_path))
    assert slabs.read_state(reopened, reopened.get(slab.GlobalId)) == state


def test_la06_trocar_o_tipo(model):
    slab = _slab(model)
    t145 = slab_type(model, "Laje 12 cm com contrapiso", SLAB_145)
    model.commit(sc.edit_element(model.doc, slab, type=t145))
    lo, hi = bounds(slab)
    assert (lo[2], hi[2]) == pytest.approx((-0.145, 0.0))
    layers = ue.get_material(t145).MaterialLayers
    assert [layer.Material.Name for layer in layers] == ["Reboco", "Concreto", "Contrapiso"]
    assert sc.read_type(t145)["layers"][0]["material"] == "Contrapiso"


def test_la07_quantidades(model):
    q = qto(_slab(model), "Qto_SlabBaseQuantities")
    assert q["Width"] == pytest.approx(0.10) and q["Perimeter"] == pytest.approx(18)
    assert q["GrossArea"] == pytest.approx(20) == q["NetArea"]
    assert q["GrossVolume"] == pytest.approx(2) == q["NetVolume"]
    assert (q["Length"], q["Depth"]) == pytest.approx((5, 4))


def test_la08_pset_comum(model):
    common = ue.get_pset(_slab(model), "Pset_SlabCommon")
    assert common["Reference"] == "Laje maciça 10 cm" and common["Status"] == ["NEW"]
    assert common["LoadBearing"] is True


def test_la09_editar_desfazer_e_diario(model):
    t = slab_type(model)

    def action():
        slab = _slab(model, L_SHAPE_CW, t)
        model.commit(transform.move_elements(model.doc, [slab], (1, 1)))
        model.commit(transform.rotate_elements(model.doc, [slab], (0, 0), 0.4))
        model.commit(transform.mirror_elements(model.doc, [slab], (0, 0), (0, 1)))
        model.commit(sc.move_slab_vertex(model.doc, slab, 0, (-1, -1)))
        model.commit(sc.offset_slab_edge(model.doc, slab, 1, 0.5))

    check_history(model, action)


def test_la09_deslocar_lado(model):
    slab = _slab(model)
    model.commit(sc.offset_slab_edge(model.doc, slab, 0, 1.0))  # lado de baixo, para fora
    assert qto(slab, "Qto_SlabBaseQuantities")["GrossArea"] == pytest.approx(25)
    lo, _ = bounds(slab)
    assert lo[1] == pytest.approx(-1)


def test_la10_excluir_e_desfazer(model):
    slab = _slab(model)
    before = snapshot(model.doc.ifc)
    count = len(list(model.doc.ifc))
    model.commit(sc.delete_element(model.doc, slab))
    assert len(list(model.doc.ifc)) < count
    model.history.undo()
    assert snapshot(model.doc.ifc) == before and len(list(model.doc.ifc)) == count


def test_la11_outra_origem(tmp_path):
    doc = Document.open(foreign_ifc(tmp_path / "outro.ifc", "IfcSlab"))
    history = History(doc)
    (slab,) = doc.ifc.by_type("IfcSlab")
    history.commit(transform.move_elements(doc, [slab], (0, -2)))
    assert slab.ObjectPlacement.RelativePlacement.Location.Coordinates == (1.0, 0.0, 0.0)
    assert slab.Representation.Representations[0].Items[0].Depth == pytest.approx(1.0)
    with pytest.raises(OpError):
        transform.mirror_elements(doc, [slab], (0, 0), (0, 1))


def test_la12_validacao(model, tmp_path):
    _slab(model)
    _slab(model, L_SHAPE_CW, slab_type(model, "Radier 15 cm", [
        {"material": "Concreto", "thickness": 0.15}], "BASESLAB"), storey=model.superior)
    assert valid(model.reopen(tmp_path))


def test_laje_na_planta_escolha_e_janela(model):
    """spec/ui 10 §4.1 e §6: laje sob as paredes, escolhida por último; na seleção por
    janela, só inteira."""
    wall = model.wall((0, 0), (5, 0))
    slab = _slab(model)
    p = plan.storey_plan(model.doc, model.terreo)
    roles = [s.role for s in p.shapes]
    assert roles.index("slab_view") < roles.index("wall")
    assert p.pick((2.5, 2.0), 0.05) == slab.GlobalId
    assert p.pick((2.5, -0.07), 0.05) == wall.GlobalId
    assert slab.GlobalId not in p.in_rect((-1, -1), (3, 5), crossing=True)
    assert slab.GlobalId in p.in_rect((-1, -1), (6, 5))
    upper = plan.storey_plan(model.doc, model.superior)
    assert not upper.owners("slab")
