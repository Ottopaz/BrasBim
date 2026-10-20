# SPDX-License-Identifier: LGPL-3.0-or-later
"""Biblioteca de objetos em arquivos IFC (objeto-parametrico.md §4, OB14, OB15)."""

import ifcopenshell
import ifcopenshell.util.element as ue
import pytest
from conftest import Model
from estrutura import valid
from test_objetos import cadeira, cama, load, mesa, put

from brasbim.core.document import OpError
from brasbim.core.objects import commands as oc
from brasbim.core.objects import definition as od
from brasbim.core.objects import elements, library
from brasbim.core.objects import types as ot


def test_ob14_gravar_e_carregar(model, tmp_path):
    defn = cama()
    load(model, defn, "Cama casal")
    load(model, defn, "Cama solteiro", largura=0.88)
    path = tmp_path / "quarto" / "camas.ifc"
    names = library.save(model.doc, path, defn["object_id"])
    assert names == ["Cama casal", "Cama solteiro"]
    ifc = ifcopenshell.open(str(path))
    (lib,) = ifc.by_type("IfcProjectLibrary")
    declared = [d for r in lib.Declares for d in r.RelatedDefinitions]
    assert sorted(t.Name for t in declared) == names
    assert all(r.RelatingContext == ifc.by_type("IfcProject")[0]
               for r in lib.HasContext)
    assert len(ifc.by_type("IfcFurniture")) == 2  # uma amostra por tipo
    assert valid(ifc)
    other = Model()
    entries = library.read_file(path)
    tx = other.commit(library.load(other.doc, entries, [e for e in entries
                                                        if e.name == "Cama solteiro"]))
    t = ot.by_name(other.doc, "Cama solteiro")
    assert ue.get_pset(t, "BrasBim_Parametros")["Largura"] == pytest.approx(0.88)
    assert ot.read(t)["library"]["object_id"] == defn["object_id"]
    assert ot.read(t)["library"]["version"] == 1
    # carregar de novo: manter, substituir ou novo tipo
    assert not library.load(other.doc, entries, entries[1:2]).ops
    tx = library.load(other.doc, entries, [e for e in entries if e.name == "Cama solteiro"],
                      conflict="new")
    other.commit(tx)
    assert ot.by_name(other.doc, "Cama solteiro (2)") is not None
    assert valid(other.doc.ifc)


def test_ob14_aninhados_vao_junto(model, tmp_path):
    load(model, cadeira(), "Cadeira simples")
    defn = mesa()
    load(model, defn, "Mesa")
    path = tmp_path / "jantar.ifc"
    assert library.save(model.doc, path, defn["object_id"]) == ["Cadeira simples", "Mesa"]
    other = Model()
    entries = library.read_file(path)
    other.commit(library.load(other.doc, entries, [e for e in entries if e.name == "Mesa"]))
    t = ot.by_name(other.doc, "Mesa")
    m = put(other, t)
    assert len(elements.parts_of(m)) == 6


def test_ob14_biblioteca_do_brasbim_so_leitura(model):
    defn = cama()
    load(model, defn, "Cama casal")
    with pytest.raises(OpError, match="não pode ser gravada"):
        library.save(model.doc, library.builtin_folder() / "x.ifc", defn["object_id"])


def test_ob15_atualizar_da_biblioteca(model, tmp_path):
    defn = cama()
    folder = tmp_path / "bib"
    load(model, defn, "Cama casal")
    library.save(model.doc, folder / "camas.ifc", defn["object_id"])
    other = Model()
    index = library.Index([folder])
    other.commit(library.load(other.doc, index.entries(), index.entries()))
    t = ot.by_name(other.doc, "Cama casal")
    other.commit(oc.edit_type(other.doc, t, values={"largura": 1.58}))
    e = put(other, t)
    assert library.updates(other.doc, index) == {}
    # versão 2 na biblioteca, com um parâmetro novo
    v2 = od.normalized(defn)
    v2["version"] = 2
    v2["params"].append(od.new_param("pes", "length", "type", 0.10, label="Altura dos pés"))
    state = ot.read(model.doc.ifc.by_type("IfcFurnitureType")[0])
    library.write_file(folder / "camas.ifc", [{**state, "definition": v2, "library": None}])
    found = library.updates(other.doc, index)
    assert list(found) == [defn["object_id"]]
    other.commit(library.update_from(other.doc, found[defn["object_id"]]))
    state = ot.read(t)
    assert state["definition"]["version"] == 2
    assert state["values"]["largura"] == pytest.approx(1.58)  # o valor do tipo ficou
    assert ue.get_pset(t, "BrasBim_Parametros")["Altura dos pés"] == pytest.approx(0.10)
    assert state["library"]["version"] == 2
    assert elements.read_state(other.doc, e)["type"] == t.GlobalId
    other.history.undo()
    assert ot.read(t)["definition"]["version"] == 1


BUILTIN = library.Index([library.builtin_folder()])


def test_ob21_arquivos_da_biblioteca_validos():
    files = BUILTIN.files()
    assert len(files) == 10
    for path in files:
        assert valid(ifcopenshell.open(str(path)))
    assert BUILTIN.errors == {}


@pytest.mark.parametrize("name", sorted(e.name for e in BUILTIN.entries()))
def test_ob21_cada_tipo_da_biblioteca(model, name):
    from brasbim.core import plan
    from brasbim.ui.scene3d import Scene

    entries = BUILTIN.entries()
    entry = next(e for e in entries if e.name == name)
    model.commit(library.load(model.doc, entries, [entry]))
    t = ot.by_name(model.doc, name)
    if entry.definition["hosting"] == "wall":
        wall = model.wall((0, 0), (5, 0))
        tx = oc.create_object(model.doc, t, model.terreo, (0, 0),
                              host={"wall": wall.GlobalId, "side": "left", "distance": 1.0})
    else:
        tx = oc.create_object(model.doc, t, model.terreo, (1.0, 1.0))
    model.commit(tx)
    e = model.doc.get(tx.ops[-1].id)
    shapes = [s for s in plan.storey_plan(model.doc, model.terreo).shapes
              if s.owner == e.GlobalId and s.role != "object_box"]
    assert shapes, "sem símbolo na planta"
    scene = Scene()
    scene.load(model.doc.ifc, model.doc)
    assert e.GlobalId in scene.meshes
    assert valid(model.doc.ifc)
