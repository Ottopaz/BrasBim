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
