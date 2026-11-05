# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unidades e casas decimais do projeto (spec/ui 44): UN01–UN04."""

import ifcopenshell.util.element as ue
import pytest
from estrutura import check_history, created

from brasbim.core import plan, units
from brasbim.core.annotations import base
from brasbim.core.annotations import commands as ac
from brasbim.core.document import Document, OpError


def _set(model, **changes):
    cfg = units.config(model.doc)
    new = {k: {**v, **changes.get(k, {})} for k, v in cfg.items()}
    return model.commit(units.set_units(model.doc, new))


def _dim(model, length=3.255):
    return created(model, ac.create_dimension(model.doc, model.terreo, [(0, 0), (length, 0)],
                                              "fixed", 0.0, -0.6))


def _texts(model, element):
    return [t.text for t in base.build(model.doc, element).texts]


def test_un01_padrao_igual_ao_de_antes(model):
    assert units.config(model.doc) == units.default_config()
    assert units.length(model.doc, "linear", 3.255) == "3,25" or \
        units.length(model.doc, "linear", 3.255) == "3,26"
    assert units.length(model.doc, "linear", 5.0) == "5,00"
    assert units.length(model.doc, "level", 2.8, signed=True) == "+2,80"
    assert units.length(model.doc, "level", -0.15, signed=True) == "−0,15"
    assert units.length(model.doc, "level", -0.0001, signed=True) == "+0,00"
    assert units.angle(model.doc, 45.0) == "45,0°"
    assert units.area(model.doc, 12.4) == "12,40 m²"
    assert units.summary(model.doc) == "m · 2 casas"
    assert not ue.get_pset(model.doc.ifc.by_type("IfcProject")[0], units.PSET)


def test_un02_cota_linear(model):
    dim = _dim(model, 3.25)
    assert _texts(model, dim) == ["3,25"]
    _set(model, linear={"unit": "cm", "decimals": 0})
    assert _texts(model, dim) == ["325"]  # o desenho da cota é refeito
    _set(model, linear={"unit": "mm", "show_unit": True})
    assert _texts(model, dim) == ["3250 mm"]
    _set(model, linear={"unit": "m", "decimals": 3, "show_unit": False, "hide_zeros": True})
    assert _texts(model, dim) == ["3,25"]
    assert units.length(model.doc, "linear", 3.0) == "3"
    with pytest.raises(OpError):
        units.set_units(model.doc, {"linear": {"unit": "km"}})
    with pytest.raises(OpError):
        units.set_units(model.doc, {"linear": {"decimals": 7}})


def test_un03_outros_tipos(model):
    doc = model.doc
    _set(model, radius={"unit": "cm", "decimals": 1},
         angle={"unit": "dms", "decimals": 0},
         level={"unit": "cm", "decimals": 0},
         elevation={"unit": "mm", "decimals": 0},
         opening={"unit": "cm", "decimals": 0},
         area={"decimals": 1, "hide_zeros": True})
    assert units.length(doc, "radius", 0.455) in ("45,5", "45,6")
    assert units.angle(doc, 30.5) == "30°30'00\""
    assert units.angle(doc, 90.0) == "90°00'00\""
    assert units.length(doc, "level", 2.8, signed=True) == "+280"
    assert units.length(doc, "elevation", -0.15, signed=True) == "−150"
    assert units.length(doc, "opening", 0.8) == "80"
    assert units.area(doc, 12.0) == "12 m²"
    assert units.area(doc, 12.44) == "12,4 m²"
    _set(model, area={"unit": "cm2", "decimals": 0})
    assert units.area(doc, 0.5) == "5000 cm²"
    _set(model, angle={"unit": "deg", "decimals": 2, "show_unit": False})
    assert units.angle(doc, 12.5) == "12,50"

    # Na planta: a área do ambiente segue a unidade.
    created(model, ac.create_space(doc, model.terreo, [(0, 0), (4, 0), (4, 3), (0, 3)]))
    _set(model, area={"unit": "m2", "decimals": 1, "hide_zeros": False})
    labels = [lb for lb in plan.storey_plan(doc, model.terreo).labels if lb.kind == "space"]
    assert labels and labels[0].size == "12,0 m²"


def test_un03_padroes_prontos(model):
    model.commit(units.apply_preset(model.doc, "centimeters"))
    cfg = units.config(model.doc)
    assert cfg["linear"]["unit"] == cfg["radius"]["unit"] == cfg["opening"]["unit"] == "cm"
    assert cfg["level"]["unit"] == "m"  # nível fica em metros
    assert units.preset_of(model.doc) == "centimeters"
    assert units.summary(model.doc) == "cm · 0 casas"
    model.commit(units.apply_preset(model.doc, "meters"))
    assert units.config(model.doc) == units.default_config()
    assert not ue.get_pset(model.doc.ifc.by_type("IfcProject")[0], units.PSET)


def test_un04_gravar_reabrir_e_desfazer(model, tmp_path):
    dim = _dim(model, 2.0)
    check_history(model, lambda: _set(model, linear={"unit": "cm", "decimals": 1}))
    assert _texts(model, dim) == ["200,0"]
    model.history.undo()
    assert _texts(model, dim) == ["2,00"]
    model.history.redo()
    path = tmp_path / "unidades.ifc"
    model.doc.save(str(path))
    other = Document.open(str(path))
    assert units.config(other)["linear"] == {"unit": "cm", "decimals": 1, "show_unit": False,
                                             "hide_zeros": False}
    assert units.length(other, "linear", 2.0) == "200,0"
