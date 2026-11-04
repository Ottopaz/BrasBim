# SPDX-License-Identifier: LGPL-3.0-or-later
"""Espessura livre de parede e laje (spec/ui 43 §3): EL01–EL05."""

import ifcopenshell.util.element as ue
import pytest
from estrutura import check_history, slab_type, valid

from brasbim.core import type_variants as tv
from brasbim.core.document import OpError
from brasbim.core.structure import commands as sc
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import types as wall_types


def _layers(t):
    return [round(x.LayerThickness, 6) for x in wall_types.layer_set(t).MaterialLayers]


def _set(model, elements, value):
    return model.commit(tv.set_thickness(model.doc, elements, value))


def test_el01_parede_com_espessura_digitada(model, tmp_path):
    wall = model.wall((0, 0), (5, 0))
    other = model.wall((5, 0), (5, 4))  # junção em L
    before = ue.get_pset(wall, "Qto_WallBaseQuantities")["GrossVolume"]
    _set(model, [wall], 0.17)
    variant = ue.get_type(wall)
    assert variant != model.type14 and variant.is_a("IfcWallType")
    assert variant.Name == "Alvenaria 14 · 17 cm"
    assert tv.read(variant) == {"origin": model.type14.GlobalId, "thickness": 0.17}
    assert _layers(variant) == [0.025, 0.12, 0.025]  # o bloco estica
    assert _layers(model.type14) == [0.025, 0.09, 0.025]
    usage = ue.get_material(wall)
    assert usage.is_a("IfcMaterialLayerSetUsage")
    assert usage.ForLayerSet == wall_types.layer_set(variant)
    after = ue.get_pset(wall, "Qto_WallBaseQuantities")["GrossVolume"]
    assert after == pytest.approx(before * 0.17 / 0.14, rel=1e-3)
    assert ue.get_type(other) == model.type14
    valid(model.doc.ifc)
    reopened = model.reopen(tmp_path)
    t = ue.get_type(reopened.by_guid(wall.GlobalId))
    assert ue.get_pset(t, tv.PSET)["Origem"] == model.type14.GlobalId


def test_el01_historico(model):
    wall = model.wall()
    check_history(model, lambda: _set(model, [wall], 0.19))


def test_el01_recusas(model):
    wall = model.wall()
    with pytest.raises(OpError, match="pequena demais"):
        tv.set_thickness(model.doc, [wall], 0.055)  # bloco ficaria com 0,5 cm
    with pytest.raises(OpError):
        tv.set_thickness(model.doc, [wall], 0)


def test_el02_mesma_espessura_mesma_variante(model):
    a, b = model.wall((0, 0), (5, 0)), model.wall((0, 3), (5, 3))
    _set(model, [a], 0.17)
    _set(model, [b], 0.17)
    assert ue.get_type(a) == ue.get_type(b)
    c, d = model.wall((0, 6), (5, 6)), model.wall((0, 9), (5, 9))
    _set(model, [c, d], 0.20)  # várias de uma vez: uma variante só
    assert ue.get_type(c) == ue.get_type(d)
    assert len(tv.variants_of(model.doc, model.type14)) == 2


def test_el03_voltar_a_espessura_do_tipo(model):
    a, b = model.wall((0, 0), (5, 0)), model.wall((0, 3), (5, 3))
    _set(model, [a, b], 0.17)
    variant = ue.get_type(a)
    _set(model, [a], 0.14)
    assert ue.get_type(a) == model.type14
    assert model.doc.find(variant.GlobalId) is not None  # b ainda usa
    _set(model, [b], 0.20)  # trocar de variante também apaga a sem uso
    assert model.doc.find(variant.GlobalId) is None
    assert [tv.read(v)["thickness"] for v in tv.variants_of(model.doc, model.type14)] == [0.20]
    # Variante de variante: a origem continua sendo o tipo de partida.
    _set(model, [b], 0.25)
    assert tv.read(ue.get_type(b))["origin"] == model.type14.GlobalId
    check_history(model, lambda: _set(model, [b], 0.14))
    assert tv.variants_of(model.doc, model.type14) == []


def test_el04_laje(model):
    t = slab_type(model, "Laje 14,5", [{"material": "Contrapiso", "thickness": 0.03},
                                       {"material": "Concreto", "thickness": 0.10},
                                       {"material": "Reboco", "thickness": 0.015}])
    tx = model.commit(sc.create_slab(model.doc, t, model.terreo,
                                     [(0, 0), (4, 0), (4, 3), (0, 3)]))
    slab = model.doc.get(tx.ops[-1].id)
    _set(model, [slab], 0.20)
    variant = ue.get_type(slab)
    assert variant.is_a("IfcSlabType") and variant.Name == "Laje 14,5 · 20 cm"
    thick = sorted(round(x.LayerThickness, 6) for x in
                   variant.HasAssociations[0].RelatingMaterial.MaterialLayers)
    assert thick == [0.015, 0.03, 0.155]  # o concreto (mais grosso) estica
    assert tv.thickness_of(model.doc, slab) == pytest.approx(0.20)
    valid(model.doc.ifc)
    check_history(model, lambda: _set(model, [slab], 0.12))


def test_el05_mudar_o_tipo_de_origem_chega_a_variante(model):
    wall = model.wall()
    _set(model, [wall], 0.19)
    variant = ue.get_type(wall)
    layers = wall_types.read(model.type14)["layers"]
    layers[0] = {**layers[0], "material": "Gesso", "thickness": 0.01}

    def edit():
        model.commit(cmd.edit_wall_type(model.doc, model.type14, layers=layers,
                                        name="Bloco 14"))

    check_history(model, edit)
    state = wall_types.read(variant)
    assert state["layers"][0]["material"] == "Gesso"
    assert sum(x["thickness"] for x in state["layers"]) == pytest.approx(0.19)
    assert variant.Name == "Bloco 14 · 19 cm"
    volume = ue.get_pset(wall, "Qto_WallBaseQuantities")["GrossVolume"]
    assert volume == pytest.approx(5 * 0.19 * 2.8, rel=1e-2)
