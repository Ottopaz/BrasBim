# SPDX-License-Identifier: LGPL-3.0-or-later
"""Objetos paramétricos no IFC (spec/elementos/objeto-parametrico.md §9)."""

import ifcopenshell.util.element as ue
import pytest
from conftest import snapshot
from estrutura import check_history, valid

from brasbim.core import display_layers, plan, transform
from brasbim.core.document import OpError
from brasbim.core.objects import commands as oc
from brasbim.core.objects import definition as od
from brasbim.core.objects import elements
from brasbim.core.objects import types as ot


def cama():
    params = [
        od.new_param("largura", "length", "type", 1.38, min=0.5, label="Largura"),
        od.new_param("comprimento", "length", "type", 1.88, min=1.0, label="Comprimento"),
        od.new_param("colchao", "length", "type", 0.25, label="Altura do colchão"),
        od.new_param("cabeceira", "bool", "type", True, label="Cabeceira"),
    ]
    pieces = [
        od.new_piece("box", name="Estrado", width="largura", depth="comprimento",
                     height=0.30, role="Frame", material="Madeira"),
        od.new_piece("box", name="Colchão", z=0.30, width="largura", depth="comprimento",
                     height="colchao", role="Padding", material="Tecido"),
        od.new_piece("box", name="Cabeceira", y="comprimento", width="largura", depth=0.05,
                     height=1.0, role="Frame", material="Madeira", visible="cabeceira"),
    ]
    return od.new_definition("Cama", "furniture", predefined_type="BED", params=params,
                             pieces=pieces)


def bancada():
    params = [od.new_param("comprimento", "length", "occurrence", 1.80, min=0.6,
                           label="Comprimento", handle={"axis": "x", "side": "end"})]
    pieces = [od.new_piece("box", name="Tampo", z=0.88, width="comprimento", depth=0.60,
                           height=0.02, role="Body", material="Granito")]
    return od.new_definition("Bancada", "sanitary", predefined_type="SINK", params=params,
                             pieces=pieces)


def load(model, defn, name, **values):
    tx = model.commit(oc.create_type(model.doc, defn, name, values=values))
    return model.doc.get(tx.ops[-1].id)


def put(model, element_type, point=(1.0, 1.0), **options):
    tx = model.commit(oc.create_object(model.doc, element_type, model.terreo, point, **options))
    return model.doc.get(tx.ops[-1].id)


def test_ob02_tipo_carregado(model):
    t = load(model, cama(), "Cama casal", codigo="M1")
    assert t.is_a("IfcFurnitureType") and t.PredefinedType == "BED"
    assert not t.RepresentationMaps
    assert ue.get_pset(t, "BrasBim_DefinicaoObjeto")["Definicao"]
    values = ue.get_pset(t, "BrasBim_Parametros")
    assert values["Largura"] == pytest.approx(1.38)
    assert values["Comprimento"] == pytest.approx(1.88)
    assert values["Cabeceira"] is True
    common = ue.get_pset(t, "Pset_FurnitureTypeCommon")
    assert common["Reference"] == "M1"
    assert common["NominalLength"] == pytest.approx(1.38)
    assert common["NominalDepth"] == pytest.approx(1.93)
    assert common["NominalHeight"] == pytest.approx(1.0)
    material = ue.get_material(t)
    assert material.is_a("IfcMaterialConstituentSet")
    assert {c.Name: c.Material.Name for c in material.MaterialConstituents} == {
        "Frame": "Madeira", "Padding": "Tecido"}
    assert valid(model.doc.ifc)


def test_ob03_ocorrencias(model):
    t = load(model, cama(), "Cama casal")
    a, b = put(model, t, (1, 1)), put(model, t, (4, 1), angle=90)
    for e in (a, b):
        assert e.is_a("IfcFurniture")
        assert ue.get_type(e) == t
        assert ue.get_container(e) == model.terreo
        body = next(r for r in e.Representation.Representations
                if r.RepresentationIdentifier == "Body")
        assert len(body.Items) == 3
        assert all(model.doc.ifc.get_inverse(i) for i in body.Items)  # IfcStyledItem
        box = next(r for r in e.Representation.Representations
               if r.RepresentationIdentifier == "Box").Items[0]
        assert (box.XDim, box.YDim) == pytest.approx((1.38, 1.93))
        assert display_layers.layer_name(
            model.doc, display_layers.layer_of(model.doc, e)) == "Mobiliário"
    assert valid(model.doc.ifc)


def test_ob04_parametro_de_tipo(model):
    t = load(model, cama(), "Cama casal")
    a, b = put(model, t, (1, 1)), put(model, t, (4, 1))

    def edit():
        model.commit(oc.edit_type(model.doc, t, values={"largura": 1.58}))

    check_history(model, edit)
    for e in (a, b):
        box = next(r for r in e.Representation.Representations
               if r.RepresentationIdentifier == "Box").Items[0]
        assert box.XDim == pytest.approx(1.58)


def test_ob05_parametro_de_ocorrencia(model):
    t = load(model, bancada(), "Bancada")
    a = put(model, t, (1, 1), values={"comprimento": 2.40})
    b = put(model, t, (1, 3))
    assert ue.get_pset(a, "BrasBim_Parametros")["Comprimento"] == pytest.approx(2.40)
    assert ue.get_pset(b, "BrasBim_Parametros")["Comprimento"] == pytest.approx(1.80)
    # regra do IFC: a propriedade da ocorrência prevalece sobre a do tipo
    assert ue.get_pset(a, "Pset_SanitaryTerminalTypeCommon")["NominalLength"] == \
        pytest.approx(2.40)
    assert ue.get_pset(b, "Pset_SanitaryTerminalTypeCommon")["NominalLength"] == \
        pytest.approx(1.80)
    assert display_layers.layer_name(
        model.doc, display_layers.layer_of(model.doc, a)) == "Equipamentos"

    def edit():
        model.commit(oc.edit_object(model.doc, b, values={"comprimento": 1.20}))

    check_history(model, edit)
    assert ue.get_pset(a, "BrasBim_Parametros")["Comprimento"] == pytest.approx(2.40)
    assert valid(model.doc.ifc)


def test_ob08_valor_recusado_nao_muda_o_modelo(model):
    t = load(model, bancada(), "Bancada")
    a = put(model, t)
    before = snapshot(model.doc.ifc)
    with pytest.raises(OpError):
        model.commit(oc.edit_object(model.doc, a, values={"comprimento": 0.2}))
    assert snapshot(model.doc.ifc) == before


def test_criar_e_excluir_com_desfazer(model):
    t = load(model, cama(), "Cama casal")

    def create():
        put(model, t)

    check_history(model, create)
    (e,) = elements.all_objects(model.doc)
    before = snapshot(model.doc.ifc)
    from brasbim.core.delete import delete_elements

    tx, _ = delete_elements(model.doc, [e.GlobalId])
    model.commit(tx)
    assert not elements.all_objects(model.doc)
    model.history.undo()
    assert snapshot(model.doc.ifc) == before


def test_ob13_transformacoes(model):
    t = load(model, bancada(), "Bancada")
    a = put(model, t, (1, 1))
    model.commit(transform.move_elements(model.doc, [a.GlobalId], (1.0, 2.0)))
    assert elements.read_state(model.doc, a)["point"] == pytest.approx([2.0, 3.0])
    model.commit(transform.rotate_elements(model.doc, [a.GlobalId], (2.0, 3.0), 1.5707963))
    assert elements.read_state(model.doc, a)["angle"] == pytest.approx(90.0, abs=1e-4)
    tx = model.commit(transform.copy_elements(model.doc, [a.GlobalId], (3.0, 0.0)))
    copy_ = model.doc.get(next(o.id for o in tx.ops if o.op == "object.create"))
    assert elements.read_state(model.doc, copy_)["point"] == pytest.approx([5.0, 3.0])
    assert display_layers.layer_of(model.doc, copy_) == display_layers.layer_of(model.doc, a)
    model.commit(transform.mirror_elements(model.doc, [a.GlobalId], (0, 0), (0, 1)))
    state = elements.read_state(model.doc, a)
    assert state["mirror"] is True
    assert state["point"] == pytest.approx([-2.0, 3.0])
    # o x local (para +y) continua para +y: com o x invertido, o ângulo vira −90°
    assert state["angle"] == pytest.approx(-90.0, abs=1e-4)
    assert valid(model.doc.ifc)


def test_ob16_planta(model):
    t = load(model, cama(), "Cama casal")
    a = put(model, t, (1, 1))
    p = plan.storey_plan(model.doc, model.terreo)
    shapes = [s for s in p.shapes if s.owner == a.GlobalId]
    assert shapes
    xs = [q[0] for s in shapes for q in s.points]
    ys = [q[1] for s in shapes for q in s.points]
    assert (min(xs), max(xs)) == pytest.approx((1.0, 2.38))
    assert (min(ys), max(ys)) == pytest.approx((1.0, 2.93))
    assert p.pick((1.5, 1.5), 0.05) == a.GlobalId
    assert p.in_rect((0, 0), (3, 3)) == [a.GlobalId]


def test_tipo_em_uso_pede_substituto(model):
    t = load(model, cama(), "Cama casal")
    other = load(model, cama(), "Cama solteiro", largura=0.88)
    a = put(model, t)
    with pytest.raises(OpError, match="substituto"):
        oc.delete_type(model.doc, t)
    model.commit(oc.delete_type(model.doc, t, replacement=other))
    assert ue.get_type(a) == other
    assert ot.by_name(model.doc, "Cama casal") is None


PIECES = {
    "caixa girada": od.new_piece("box", x=0.2, y=0.1, z=0.3, width=0.6, depth=0.4,
                                 height=0.5, rotation=30),
    "cilindro z": od.new_piece("cylinder", x=0.5, y=0.5, radius=0.2, height=0.7),
    "cilindro x": od.new_piece("cylinder", x=0.1, y=0.5, z=0.4, radius=0.2, height=0.9,
                               axis="x"),
    "cilindro y": od.new_piece("cylinder", x=0.3, y=0.1, z=0.4, radius=0.2, height=0.9,
                               axis="y"),
    "extrusão xy": od.new_piece("extrusion", plane="xy", offset=0.2, thickness=0.3,
                                points=[[0, 0], [1, 0], [1, 0.4], [0.3, 0.8]]),
    "extrusão xz": od.new_piece("extrusion", plane="xz", offset=0.2, thickness=0.3,
                                points=[[0.1, 0], [1, 0], [1, 0.4], [0.3, 0.8]]),
    "extrusão yz": od.new_piece("extrusion", plane="yz", offset=0.2, thickness=0.3,
                                points=[[0.1, 0], [1, 0], [1, 0.4], [0.3, 0.8]]),
    "revolução 90°": od.new_piece("revolution", x=0.5, y=0.5, angle=90,
                                  points=[[0, 0], [0.4, 0], [0.4, 0.3], [0, 0.6]]),
}


@pytest.mark.parametrize("mirror", [False, True])
@pytest.mark.parametrize("name", sorted(PIECES))
def test_geometria_das_pecas(model, name, mirror):
    from estrutura import bounds

    defn = od.new_definition("Peça", "proxy", pieces=[PIECES[name]])
    t = load(model, defn, "Peça")
    e = put(model, t, (0.0, 0.0), mirror=mirror)
    x0, x1, y0, y1, z0, z1 = od.bounds(od.solids(defn, od.evaluate(defn)))
    if mirror:
        x0, x1 = -x1, -x0
    low, high = bounds(e)
    tol = 0.02 if "revolução" in name or "cilindro" in name else 1e-4
    assert low == pytest.approx([x0, y0, z0], abs=tol)
    assert high == pytest.approx([x1, y1, z1], abs=tol)


def cadeira():
    params = [od.new_param("assento", "length", "occurrence", 0.45, label="Altura do assento")]
    pieces = [od.new_piece("box", name="Assento", x=-0.22, y=-0.22, z="assento - 0,04",
                           width=0.44, depth=0.44, height=0.04, role="Frame",
                           material="Madeira")]
    return od.new_definition("Cadeira", "furniture", predefined_type="CHAIR", params=params,
                             pieces=pieces)


def mesa():
    params = [
        od.new_param("comprimento", "length", "occurrence", 1.80, min=0.8,
                     label="Comprimento", handle={"axis": "x", "side": "end"}),
        od.new_param("lugares", "integer", "occurrence",
                     formula="arred_baixo(comprimento / 0,60) * 2", label="Lugares"),
        od.new_param("cadeira", "object_type", "type", "Cadeira simples", label="Cadeira",
                     accepts={"category": "furniture", "predefined_type": "CHAIR"}),
    ]
    pieces = [
        od.new_piece("box", name="Tampo", z=0.73, width="comprimento", depth=0.90,
                     height=0.03, role="Frame", material="Madeira"),
        od.new_piece("object", name="Cadeiras da frente", type={"param": "cadeira"},
                     x=0.30, y=-0.15, values={"assento": 0.46},
                     repeat={"count": "lugares / 2", "dx": 0.60}),
        od.new_piece("object", name="Cadeiras de trás", type={"param": "cadeira"},
                     x=0.30, y=1.05, rotation=180, repeat={"count": "lugares / 2", "dx": 0.60}),
    ]
    return od.new_definition("Mesa", "furniture", predefined_type="TABLE", params=params,
                             pieces=pieces)


def test_ob09_aninhados(model):
    simple = load(model, cadeira(), "Cadeira simples")
    other = load(model, cadeira(), "Cadeira estofada")
    t = load(model, mesa(), "Mesa")
    m = put(model, t, (1, 1))
    parts = elements.parts_of(m)
    assert len(parts) == 6
    assert all(ue.get_type(p) == simple for p in parts)
    assert all(p.Decomposes[0].RelatingObject == m for p in parts)
    assert all(not p.ContainedInStructure for p in parts)
    assert ue.get_pset(parts[0], "BrasBim_Parametros")["Altura do assento"] in (
        pytest.approx(0.46), pytest.approx(0.45))
    ids = sorted(p.GlobalId for p in parts)

    def longer():
        model.commit(oc.edit_object(model.doc, m, values={"comprimento": 2.40}))

    check_history(model, longer)
    assert len(elements.parts_of(m)) == 8
    model.history.undo()
    assert sorted(p.GlobalId for p in elements.parts_of(m)) == ids
    model.commit(oc.edit_type(model.doc, t, values={"cadeira": "Cadeira estofada"}))
    assert all(ue.get_type(p) == other for p in elements.parts_of(m))
    # o clique escolhe a mesa; as cadeiras contam como cadeiras
    p = plan.storey_plan(model.doc, model.terreo)
    assert {s.owner for s in p.shapes if s.role.startswith("object")} == {m.GlobalId}
    assert valid(model.doc.ifc)


def test_ob09_ciclo_e_tipo_ausente(model):
    defn = mesa()
    defn["params"][2]["value"] = "Mesa"
    t = load(model, defn, "Mesa", cadeira="Cadeira simples")
    with pytest.raises(OpError, match="não está no projeto"):
        put(model, t)


def lavatorio(void=False):
    pieces = [od.new_piece("box", name="Cuba", x=0, y=0, z=0, width=0.50, depth=0.40,
                           height=0.18, role="Body", material="Louça")]
    if void:
        pieces.append(od.new_piece("box", name="Nicho", x=0.05, y=0.40, z=0.20, width=0.40,
                                   depth=0.05, height=0.30, void=True))
    return od.new_definition("Lavatório suspenso", "sanitary", predefined_type="WASHHANDBASIN",
                             hosting="wall", elevation=0.80, pieces=pieces)


def test_ob10_preso_a_parede(model):
    wall = model.wall((0, 0), (5, 0))
    t = load(model, lavatorio(), "Lavatório")
    assert ue.get_pset(t, "Pset_SanitaryTerminalTypeCommon")
    tx = model.commit(oc.create_object(model.doc, t, model.terreo, (0, 0),
                                       host={"wall": wall.GlobalId, "side": "left",
                                             "distance": 1.0}))
    e = model.doc.get(tx.ops[-1].id)
    rel = next(r for r in wall.ConnectedTo if r.is_a() == "IfcRelConnectsElements")
    assert rel.RelatedElement == e
    from estrutura import bounds

    from brasbim.core.walls import rebuild
    from brasbim.core.walls.wall import read_state as read_wall

    face = rebuild.band(model.doc, read_wall(model.doc, wall)).ymax
    low, high = bounds(e)
    # o fundo encosta na face esquerda da parede, a frente para +y
    assert low == pytest.approx([1.0, face, 0.80], abs=1e-4)
    assert high == pytest.approx([1.5, face + 0.40, 0.98], abs=1e-4)
    # mover a parede leva o objeto
    from brasbim.core.walls import commands as wc

    model.commit(transform.move_elements(model.doc, [wall.GlobalId], (0.0, 0.5)))
    low, _ = bounds(e)
    assert low[1] == pytest.approx(face + 0.5, abs=1e-4)
    # mover só o objeto desliza ao longo da parede
    model.commit(transform.move_elements(model.doc, [e.GlobalId], (0.3, 2.0)))
    assert elements.read_state(model.doc, e)["host"]["distance"] == pytest.approx(1.3)
    with pytest.raises(OpError, match="gira"):
        transform.rotate_elements(model.doc, [e.GlobalId], (0, 0), 1.0)
    # excluir a parede exclui o objeto, e desfazer devolve os dois
    from brasbim.core.delete import delete_elements

    before = snapshot(model.doc.ifc)
    tx, cascade = delete_elements(model.doc, [wall.GlobalId])
    assert cascade["objects"] == 1
    model.commit(tx)
    assert model.doc.find(e.GlobalId) is None
    model.history.undo()
    assert snapshot(model.doc.ifc) == before
    del wc
    assert valid(model.doc.ifc)


def test_ob11_vao_do_objeto(model):
    wall = model.wall((0, 0), (5, 0))
    t = load(model, lavatorio(void=True), "Armário com nicho")
    host = {"wall": wall.GlobalId, "side": "left", "distance": 1.0}
    tx = model.commit(oc.create_object(model.doc, t, model.terreo, (0, 0), host=host))
    e = model.doc.get(tx.ops[-1].id)
    from brasbim.core.walls import openings

    (opening,) = openings.of_wall(wall, objects=True)
    assert openings.of_wall(wall) == []
    assert opening.PredefinedType == "RECESS"
    assert opening.VoidsElements[0].RelatingBuildingElement == wall
    assert not opening.HasFillings
    state = openings.read_state(opening)
    assert state["distance"] == pytest.approx(1.05)
    assert state["width"] == pytest.approx(0.40)
    assert state["depth"] == pytest.approx(0.05)
    assert state["sill"] == pytest.approx(1.0)
    # objeto sobre uma janela é recusado
    from brasbim.core.fillings import commands as fc

    model.commit(fc.create_window_type(model.doc, "J1"))
    (window_type,) = model.doc.ifc.by_type("IfcWindowType")
    model.commit(fc.create_window(model.doc, window_type, wall, 3.0, width=1.0, height=1.0,
                                  base=1.0))
    with pytest.raises(OpError, match="não cabe"):
        oc.create_object(model.doc, t, model.terreo, (0, 0),
                         host={**host, "distance": 3.0})
    # soltar da parede tira o vão
    model.commit(oc.detach(model.doc, e))
    assert all(openings.read_state(o)["kind"] == "OPENING"
               for o in openings.of_wall(wall, objects=True))
    assert elements.read_state(model.doc, e)["host"] is None
    assert valid(model.doc.ifc)


def test_alca_mantem_o_lado_oposto_no_projeto(model):
    from estrutura import bounds

    t = load(model, bancada(), "Bancada")
    e = put(model, t, (1.0, 1.0), angle=90)
    model.commit(oc.handle_value_ops(model.doc, e, "comprimento", 2.4))
    low, high = bounds(e)
    # girada 90°: o comprimento corre em y; a alça "end" estica, a origem fica
    assert (low[1], high[1]) == pytest.approx((1.0, 3.4), abs=1e-6)
    wall = model.wall((0, 0), (5, 0))
    defn = bancada()
    defn["hosting"] = "wall"
    defn["params"][0]["handle"]["side"] = "end"
    t2 = load(model, defn, "Bancada na parede")
    tx = model.commit(oc.create_object(model.doc, t2, model.terreo, (0, 0), host={
        "wall": wall.GlobalId, "side": "left", "distance": 1.0}))
    h = model.doc.get(tx.ops[-1].id)
    _, before_high = bounds(h)
    model.commit(oc.handle_value_ops(model.doc, h, "comprimento", 2.0))
    low, high = bounds(h)
    # face esquerda: o x local corre para trás; a ponta do início (x local 0) fica
    assert high[0] == pytest.approx(before_high[0], abs=1e-6)
    assert high[0] - low[0] == pytest.approx(2.0, abs=1e-6)


def test_ob17_tabelas(model):
    from brasbim.core.quantities import tables

    load(model, cadeira(), "Cadeira simples")
    t = load(model, cama(), "Cama casal", codigo="M1")
    put(model, t, (1, 1))
    put(model, t, (4, 1))
    put(model, load(model, mesa(), "Mesa"), (1, 4))
    tx = model.commit(tables.create_table(model.doc, "objects"))
    result = tables.compute(model.doc, model.doc.get(tx.ops[0].id))
    rows = {r.cells[2]: r.cells for r in result.rows if r.kind == "group"}
    assert rows["Cama casal"][0] == "M1" and rows["Cama casal"][3] == 2
    assert rows["Mesa"][3] == 1
    assert rows["Cadeira simples"][3] == 6  # as cadeiras da mesa contam como cadeiras
    # "parte de" e as colunas de parâmetro
    state = {"name": "Cadeiras", "category": "furniture",
             "columns": [{"field": "type"}, {"field": "part_of"}, {"field": "count"}],
             "group_by": "type", "rows": "group"}
    result = tables.compute(model.doc, state)
    chairs = next(r for r in result.rows if r.kind == "group" and r.cells[0] == "Cadeira simples")
    assert chairs.cells[1] == "Mesa"
    fields = tables.fields_of("furniture", model.doc)
    assert "param:largura" in fields and fields["param:largura"].title == "Largura"
    state = {"name": "Camas", "category": "furniture", "types": [t.GlobalId],
             "columns": [{"field": "type"}, {"field": "param:largura"}, {"field": "count"}],
             "group_by": "type", "rows": "group"}
    result = tables.compute(model.doc, state)
    (row,) = [r for r in result.rows if r.kind == "group"]
    assert row.cells[1] == pytest.approx(1.38)


def test_ob20_assistente(model):
    import json

    from brasbim.core.assistant.tools import Context, default_registry

    ctx = Context(model.doc, model.commit, model.terreo.GlobalId)

    def call(tool, **args):
        result = default_registry().call(ctx, tool, args)
        text = result["content"][0]["text"]
        return (text if result["isError"] else json.loads(text)), result["isError"]

    out, err = call("list_objects", query="cama")
    assert not err, out
    (cama_lib,) = [o for o in out["na_biblioteca"] if o["objeto"] == "Cama"]
    assert "Cama de casal 1,38 × 1,88" in cama_lib["tipos"]
    assert {p["nome"]: p["nivel"] for p in cama_lib["parametros"]}["largura"] == "tipo"
    out, err = call("insert_object", type="Cama de casal 1,38 × 1,88", at=[2, 2])
    assert not err, out
    model_out, _ = call("describe_model")
    (obj,) = model_out["objetos"]
    assert obj["tipo"] == "Cama de casal 1,38 × 1,88" and obj["ponto"] == [2.0, 2.0]
    out, err = call("edit_object", id=obj["id"], rotation=90)
    assert not err, out
    assert elements.read_state(model.doc, model.doc.get(obj["id"]))["angle"] == \
        pytest.approx(90.0)
    model.wall((0, 0), (5, 0))
    out, err = call("insert_object", type="Lavatório suspenso", at=[1.5, 0.2])
    assert not err, out
    assert elements.read_state(model.doc, model.doc.get(out["id"]))["host"] is not None


def test_ob12_troca_de_tipo(model):
    load(model, cadeira(), "Cadeira simples")
    seis = load(model, mesa(), "Mesa 6")
    quatro = load(model, mesa(), "Mesa 4")
    m = put(model, seis, (1, 1), angle=30)
    layer = display_layers.layer_of(model.doc, m)
    model.commit(oc.change_type(model.doc, [m.GlobalId], quatro))
    state = elements.read_state(model.doc, m)
    assert state["type"] == quatro.GlobalId
    assert state["point"] == pytest.approx([1.0, 1.0]) and state["angle"] == pytest.approx(30)
    assert display_layers.layer_of(model.doc, m) == layer
    # outra classe não aparece entre os tipos compatíveis
    bench = load(model, bancada(), "Bancada")
    assert bench not in oc.compatible_types(model.doc, m)
    with pytest.raises(OpError):
        oc.change_type(model.doc, [m.GlobalId], bench)
    # substituir em todas
    other = put(model, seis, (5, 1))
    model.commit(oc.replace_all(model.doc, seis, quatro))
    assert elements.read_state(model.doc, other)["type"] == quatro.GlobalId


def test_ob16_etiqueta(model):
    t = load(model, cama(), "Cama casal", codigo="M1")
    a = put(model, t, (1, 1))
    labels = [lb for lb in plan.storey_plan(model.doc, model.terreo).labels
              if lb.kind == "object"]
    assert [(lb.owner, lb.code) for lb in labels] == [(a.GlobalId, "M1")]
    assert labels[0].at == pytest.approx((1.69, 1.965))
