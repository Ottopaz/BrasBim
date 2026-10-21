# SPDX-License-Identifier: LGPL-3.0-or-later
"""Camadas (spec/ui 18 §8), no núcleo: CM01–CM13 e CM16."""

import ifcopenshell
import ifcopenshell.api.layer
import ifcopenshell.validate
import pytest
from conftest import PROJECT_ID, snapshot
from estrutura import check_history, column_type, created, foreign_ifc, slab_type, valid

from brasbim.core import display_layers as dl
from brasbim.core import plan, props, transform
from brasbim.core.annotations import commands as ac
from brasbim.core.document import Document, OpError
from brasbim.core.drawings import section
from brasbim.core.fillings import commands as fc
from brasbim.core.ops import History, Op, Transaction
from brasbim.core.structure import commands as sc
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import top


def _id(doc, name):
    return next(x["id"] for x in dl.read_config(doc)["layers"] if x["name"] == name)


def _group(doc, name):
    return next(x["id"] for x in dl.read_config(doc)["groups"] if x["name"] == name)


def _ifc_layers(doc) -> dict:
    """{nome da camada: {GlobalIds dos donos das representações}}, lido só do IFC."""
    out = {}
    for assignment in doc.ifc.by_type("IfcPresentationLayerAssignment"):
        owners = set()
        for rep in assignment.AssignedItems:
            for shape in rep.OfProductRepresentation:
                for product in shape.ShapeOfProduct:
                    owners.add(product.GlobalId)
        out[assignment.Name] = owners
    return out


def _house(model):
    """Casa de teste da §8."""
    corners = [(0, 0), (8, 0), (8, 5), (0, 5)]
    walls = [model.wall(corners[i], corners[(i + 1) % 4]) for i in range(4)]
    south = walls[0]
    door_type = model.doc.get(model.commit(fc.create_door_type(model.doc, "P1")).ops[0].id)
    model.commit(fc.create_door(model.doc, door_type, south, 1.0))
    window_type = model.doc.get(model.commit(fc.create_window_type(model.doc, "J1")).ops[0].id)
    model.commit(fc.create_window(model.doc, window_type, south, 5.0))
    column = created(model, sc.create_column(model.doc, column_type(model), model.terreo,
                                             (4, 2.5)))
    slab = created(model, sc.create_slab(model.doc, slab_type(model), model.terreo,
                                         [(0, 0), (8, 0), (8, 5), (0, 5)]))
    space = created(model, ac.create_space_in_room(model.doc, model.terreo, (2, 2)))
    dim = created(model, ac.create_dimension(model.doc, model.terreo, [(0, -1), (8, -1)]))
    text = created(model, ac.create_annotation(model.doc, "text", model.terreo, at=[1, 1],
                                               text="SALA"))
    return {"walls": walls, "column": column, "slab": slab, "space": space, "dim": dim,
            "text": text}


def test_cm01_projeto_novo(model, tmp_path):
    config = dl.read_config(model.doc)
    assert [g["name"] for g in config["groups"]] == [
        "Arquitetura", "Estrutura", "Documentação", "Entorno", "Interiores"]
    assert len(config["layers"]) == 16  # com Levantamento (spec/ui 22)
    h = _house(model)
    found = _ifc_layers(model.doc)
    assert {w.GlobalId for w in h["walls"]} == found["Paredes"]
    assert len(found["Esquadrias"]) == 2
    assert found["Pilares"] == {h["column"].GlobalId}
    assert found["Pisos e lajes"] == {h["slab"].GlobalId}
    assert found["Ambientes"] == {h["space"].GlobalId}
    assert found["Cotas"] == {h["dim"].GlobalId}
    assert found["Textos e rótulos"] == {h["text"].GlobalId}
    # Todas as representações do elemento, não só o corpo.
    wall = h["walls"][0]
    layer = model.doc.ifc.by_type("IfcPresentationLayerWithStyle")
    items = {r for x in layer for r in x.AssignedItems}
    assert all(r in items for r in wall.Representation.Representations)
    assert valid(model.reopen(tmp_path))


def test_cm02_camada_sobrevive_a_edicao(model):
    wall = model.wall(top_mode="fixed")
    count = len(list(model.doc.ifc))
    model.commit(transform.move_elements(model.doc, [wall], (0.5, 0)))
    model.commit(cmd.edit_wall(model.doc, wall, top_shape="gable",
                               top_profile=top.gable(5, 2.8, 4.0)))
    assert _ifc_layers(model.doc)["Paredes"] == {wall.GlobalId}
    for rep in wall.Representation.Representations:
        assert dl._rep_layer(rep) == _id(model.doc, "Paredes")
    # Nenhuma representação solta na camada.
    (layer,) = model.doc.ifc.by_type("IfcPresentationLayerWithStyle")
    assert all(r.OfProductRepresentation for r in layer.AssignedItems)
    model.history.undo()
    model.history.undo()
    assert len(list(model.doc.ifc)) == count
    assert _ifc_layers(model.doc)["Paredes"] == {wall.GlobalId}


def test_cm03_camada_vazia(model):
    wall = model.wall()
    paredes = _id(model.doc, "Paredes")
    model.commit(dl.assign(model.doc, [wall.GlobalId], _id(model.doc, "Esquadrias")))
    assert "Paredes" not in _ifc_layers(model.doc)
    assert dl.layer(model.doc, paredes) is not None  # continua no JSON
    model.commit(dl.assign(model.doc, [wall.GlobalId], paredes))
    assert _ifc_layers(model.doc) == {"Paredes": {wall.GlobalId}}
    model.commit(cmd.delete_wall(model.doc, wall))
    assert not model.doc.ifc.by_type("IfcPresentationLayerAssignment")
    model.history.undo()  # desfazer a exclusão devolve a parede à camada que tinha
    assert _ifc_layers(model.doc) == {"Paredes": {wall.GlobalId}}


def test_cm03b_desfazer_exclusao_lembra_a_camada(model):
    wall = model.wall()
    other = _id(model.doc, "Vigas")
    model.commit(dl.assign(model.doc, [wall.GlobalId], other))
    model.commit(cmd.delete_wall(model.doc, wall))
    model.history.undo()
    assert dl.layer_of(model.doc, model.doc.get(wall.GlobalId)) == other


def test_cm04_ocultar_paredes(model):
    h = _house(model)
    model.doc.display = dl.Display(hidden=frozenset({_id(model.doc, "Paredes")}))
    p = plan.storey_plan(model.doc, model.terreo)
    owners = {s.owner for s in p.shapes}
    assert not owners & {w.GlobalId for w in h["walls"]}
    # Porta e janela seguem a própria camada e ficam.
    assert len({s.owner for s in p.shapes if s.role.startswith(("door", "window"))}) == 2
    assert h["column"].GlobalId in owners
    view = created(model, ac.create_view(model.doc, "section", (-1, 2), (9, 2)))
    drawing = section.draw(model.doc, view)
    assert not {it.owner for it in drawing.items} & {w.GlobalId for w in h["walls"]}
    # Seleção pela planta: as paredes não estão nela.
    assert plan.storey_plan(model.doc, model.terreo).pick((4, 0), 0.05) != h["walls"][0]
    model.doc.display = dl.Display()
    assert {w.GlobalId for w in h["walls"]} <= {
        s.owner for s in plan.storey_plan(model.doc, model.terreo).shapes}


def test_cm05_bloqueada(model):
    wall = model.wall()
    model.doc.display = dl.Display(locked=frozenset({_id(model.doc, "Paredes")}))
    assert dl.is_locked(model.doc, wall)
    assert not dl.is_hidden(model.doc, wall)
    assert wall.GlobalId in dl.locked_ids(model.doc)
    # Desenhada normalmente (o snap usa a planta).
    assert wall.GlobalId in {s.owner for s in plan.storey_plan(model.doc, model.terreo).shapes}


def test_cm06_grupo(model):
    estrutura = _group(model.doc, "Estrutura")
    layers = dl.group_layers(model.doc, estrutura)
    display = dl.Display()
    for lay in layers:
        display = display.with_layer(lay, visible=False)
    assert dl.group_state(model.doc, display, estrutura) == (False, False)
    display = display.with_layer(_id(model.doc, "Pilares"), visible=True)
    assert dl.group_state(model.doc, display, estrutura) == (None, False)


def test_cm07_atribuir_desfazer_e_diario(model, tmp_path):
    h = _house(model)
    vigas = _id(model.doc, "Vigas")

    def layers_now(doc):
        return {g: dl.layer_of(doc, doc.get(g)) for g in
                (h["column"].GlobalId, h["slab"].GlobalId, h["walls"][0].GlobalId)}

    before = layers_now(model.doc)

    def action():
        model.commit(dl.assign(model.doc, [h["column"].GlobalId, h["slab"].GlobalId], vigas))
        model.commit(dl.create_layer(model.doc, "Demolição"))
        model.commit(dl.save_combination(model.doc, "Obra", dl.Display()))

    check_history(model, action)
    after = layers_now(model.doc)
    assert after[h["column"].GlobalId] == after[h["slab"].GlobalId] == vigas
    model.history.undo()
    model.history.undo()
    model.history.undo()
    assert layers_now(model.doc) == before
    for _ in range(3):
        model.history.redo()
    # Diário reaplicado: as mesmas camadas.
    other = Document.new(project_id=PROJECT_ID)
    history = History(other)
    for tx in model.history.journal:
        history.commit(tx)
    assert _ifc_layers(other) == _ifc_layers(model.doc)
    # Reabrir traz camadas, grupos e combinações.
    reopened = Document(model.reopen(tmp_path))
    assert dl.read_config(reopened) == dl.read_config(model.doc)
    assert layers_now(reopened) == after


def test_cm08_excluir_camada_e_grupo(model):
    wall = model.wall()
    paredes, vigas = _id(model.doc, "Paredes"), _id(model.doc, "Vigas")
    with pytest.raises(OpError):  # com elementos, só pela transação que os move
        model.commit(Transaction("x", [Op("layer.delete", paredes, data={
            "name": "Paredes", "group": None, "index": 0})]))
    model.commit(dl.delete_layer(model.doc, paredes, move_to=vigas))
    assert dl.layer(model.doc, paredes) is None
    assert dl.layer_of(model.doc, wall) == vigas
    assert dl.read_config(model.doc)["defaults"]["wall"] == vigas
    model.history.undo()
    assert dl.layer_of(model.doc, wall) == paredes
    assert dl.read_config(model.doc)["defaults"]["wall"] == paredes
    arq = _group(model.doc, "Arquitetura")
    model.commit(dl.delete_group(model.doc, arq))
    assert dl.layer(model.doc, paredes)["group"] is None
    assert dl.layer(model.doc, paredes) is not None


def test_cm09_combinacao(model):
    config = dl.read_config(model.doc)
    comb = next(c for c in config["combinations"] if c["name"] == "Estrutura")
    display = dl.display_of(comb["states"])
    visible = {x["name"] for x in config["layers"] if display.state(x["id"])[0]}
    assert visible == {"Pilares", "Vigas", "Lajes estruturais", "Cotas"}
    assert dl.matching_combination(model.doc, display)["name"] == "Estrutura"
    changed = display.with_layer(_id(model.doc, "Paredes"), visible=True)
    assert dl.matching_combination(model.doc, changed) is None  # "(alterada)"
    tx = model.commit(dl.create_layer(model.doc, "Demolição"))
    new = tx.ops[0].id
    display = dl.display_of(dl.combination(model.doc, comb["id"])["states"])
    assert display.state(new) == (True, False)  # entra visível e livre


def test_cm11_outra_origem(tmp_path):
    path = foreign_ifc(tmp_path / "outro.ifc", "IfcWall")
    f = ifcopenshell.open(path)
    element = f.by_type("IfcWall")[0]
    layer = ifcopenshell.api.layer.add_layer(f, name="A-PAREDE")
    ifcopenshell.api.layer.assign_layer(f, items=list(element.Representation.Representations),
                                        layer=layer)
    loose = ifcopenshell.api.root.create_entity(f, ifc_class="IfcColumn", name="Solto")
    loose.Representation = f.createIfcProductDefinitionShape(
        None, None, [f.createIfcShapeRepresentation(
            element.Representation.Representations[0].ContextOfItems, "Body", "SweptSolid",
            [element.Representation.Representations[0].Items[0]])])
    f.write(path)
    doc = Document.open(path)
    assert dl.read_config(doc) is None
    history = History(doc)
    history.commit(dl.organize(doc))
    config = dl.read_config(doc)
    imported = next(x for x in config["layers"] if x["name"] == "A-PAREDE")
    assert next(g for g in config["groups"] if g["id"] == imported["group"])["name"] == \
        "Importadas"
    wall = doc.ifc.by_type("IfcWall")[0]
    assert dl.layer_of(doc, wall) == imported["id"]
    assert dl.layer_of(doc, doc.ifc.by_type("IfcColumn")[0]) is None  # Sem camada
    doc.display = dl.Display(hidden=frozenset({imported["id"]}))
    assert dl.is_hidden(doc, wall)
    doc.display = dl.Display(hidden=frozenset({dl.NONE}))
    assert dl.is_hidden(doc, doc.ifc.by_type("IfcColumn")[0]) and not dl.is_hidden(doc, wall)
    history.undo()
    assert dl.read_config(doc) is None
    assert doc.ifc.by_type("IfcPresentationLayerAssignment")[0].Identifier is None


def test_cm12_arquivo_antigo(model, tmp_path):
    h = _house(model)
    # Arquivo de antes do pacote 12: sem o Pset e sem camadas.
    for x in model.doc.ifc.by_type("IfcPresentationLayerAssignment"):
        model.doc.ifc.remove(x)
    props.remove_pset(model.doc, model.doc.project, dl.PSET)
    path = tmp_path / "antigo.ifc"
    model.doc.save(str(path))
    doc = Document.open(str(path))
    history = History(doc)
    before = snapshot(doc.ifc)
    history.commit(dl.organize(doc))
    found = _ifc_layers(doc)
    assert found["Paredes"] == {w.GlobalId for w in h["walls"]}
    assert found["Pilares"] == {h["column"].GlobalId}
    assert found["Cotas"] == {h["dim"].GlobalId}
    assert dl.organize(doc) is None  # já organizado
    history.undo()
    assert snapshot(doc.ifc) == before
    assert not doc.ifc.by_type("IfcPresentationLayerAssignment")


def test_cm13_camada_padrao(model):
    vigas = _id(model.doc, "Vigas")
    model.commit(dl.set_default(model.doc, "wall", vigas))
    wall = model.wall()
    assert dl.layer_of(model.doc, wall) == vigas


def test_cm16_exibicao_fora_do_desfazer(model, tmp_path):
    model.wall()
    paredes, cotas = _id(model.doc, "Paredes"), _id(model.doc, "Cotas")
    count = len(model.history.journal)
    display = dl.Display(hidden=frozenset({paredes}), locked=frozenset({cotas}))
    model.doc.display = display
    assert len(model.history.journal) == count
    dl.write_display(model.doc, display)
    model.doc.save(str(tmp_path / "x.ifc"))
    doc = Document.open(str(tmp_path / "x.ifc"))
    assert dl.read_display(doc) == display
    (layer,) = doc.ifc.by_type("IfcPresentationLayerWithStyle")
    assert layer.LayerOn is False and layer.LayerBlocked is False
    log = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(doc.ifc, log)
    assert log.statements == []


def test_cm18_copia_e_divisao_mantem_a_camada(model):
    """§5: copiar e dividir mantêm a camada do original."""
    wall = model.wall()
    vigas = _id(model.doc, "Vigas")
    model.commit(dl.assign(model.doc, [wall.GlobalId], vigas))
    tx = model.commit(transform.copy_elements(model.doc, [wall.GlobalId], (0, 3)))
    copy_ = next(o.id for o in tx.ops if o.op == "wall.create")
    assert dl.layer_of(model.doc, model.doc.get(copy_)) == vigas
    tx = model.commit(cmd.split_wall(model.doc, wall, (2, 0)))
    new = next(o.data["new"] for o in tx.ops if o.op == "wall.split")
    assert dl.layer_of(model.doc, model.doc.get(new)) == vigas
    model.history.undo()
    model.history.undo()
    model.history.redo()
    assert dl.layer_of(model.doc, model.doc.get(copy_)) == vigas


def test_cm19_reordenar_e_mudar_de_grupo(model):
    """O que o arrastar no painel faz (§7): grupo novo e ordem nova, com desfazer."""
    config = dl.read_config(model.doc)
    layers = [x["id"] for x in config["layers"]]
    groups = [x["id"] for x in config["groups"]]
    paredes, interiores = _id(model.doc, "Paredes"), _group(model.doc, "Interiores")
    tx = dl.edit_layer(model.doc, paredes, group=interiores)
    order = dl.reorder(model.doc, list(reversed(layers)), list(reversed(groups)))
    model.commit(Transaction("Organizar camadas", tx.ops + order.ops))
    after = dl.read_config(model.doc)
    assert [x["id"] for x in after["layers"]] == list(reversed(layers))
    assert [x["id"] for x in after["groups"]] == list(reversed(groups))
    assert dl.layer(model.doc, paredes)["group"] == interiores
    model.history.undo()
    assert dl.read_config(model.doc) == config
    with pytest.raises(OpError):  # renomear para um nome que já existe
        model.commit(dl.edit_layer(model.doc, paredes, name="vigas"))
