# SPDX-License-Identifier: LGPL-3.0-or-later
"""Assistente: objeto novo criado pela IA (spec/ui/54-assistente-foto-e-objeto-novo.md
§3.1 e §3.2): AF04–AF06. O resultado é conferido no IFC."""

import json

import ifcopenshell.util.element as ue
import pytest
from conftest import snapshot

from brasbim.core.assistant.tools import MAX_PIECES, Context, default_registry
from brasbim.core.objects import elements as objects
from brasbim.core.objects import types as ot


@pytest.fixture
def ctx(model):
    return Context(model.doc, model.commit, model.terreo.GlobalId)


def _call(ctx, tool, **args):
    result = default_registry().call(ctx, tool, args)
    text = result["content"][0]["text"]
    return (json.loads(text) if not result["isError"] else text), result["isError"]


def _fogao(**extra):
    return {
        "name": "Fogão de piso 5 bocas", "category": "appliance",
        "predefined_type": "ELECTRICCOOKER",
        "description": "Medidas informadas pelo usuário: 76 × 60 × 85 cm.",
        "params": [
            {"name": "largura", "label": "Largura", "value": 0.76, "min": 0.5},
            {"name": "profundidade", "label": "Profundidade", "value": 0.60},
            {"name": "altura", "label": "Altura", "value": 0.85},
        ],
        "pieces": [
            {"kind": "box", "name": "Corpo", "width": "largura", "depth": "profundidade",
             "height": "altura - 0,02", "material": "Eletrodoméstico", "role": "Body"},
            {"kind": "box", "name": "Tampo", "z": "altura - 0,02", "width": "largura",
             "depth": "profundidade", "height": 0.02, "material": "Inox", "role": "Finish"},
            {"kind": "cylinder", "name": "Boca", "x": "largura / 4", "y": 0.17,
             "z": "altura", "radius": 0.05, "height": 0.015, "material": "Inox",
             "repeat": {"count": 3, "dx": "largura / 4"}},
            {"kind": "cylinder", "name": "Puxador do forno", "x": 0.10, "y": -0.03,
             "z": 0.62, "radius": 0.012, "height": "largura - 0,20", "axis": "x",
             "material": "Inox"},
        ],
        **extra,
    }


# AF04: definição + tipo no IFC; com "at", a ocorrência no pavimento


def test_af04_cria_o_objeto_e_insere(ctx, model):
    out, error = _call(ctx, "create_object", **_fogao(at=[2.0, 1.0], rotation=90))
    assert not error, out
    assert out["objeto"] == out["tipo"] == "Fogão de piso 5 bocas" and out["pecas"] == 4
    # a caixa confere com as medidas: o puxador passa 4,2 cm para a frente
    box = out["caixa"]
    assert box["largura"] == pytest.approx(0.76)
    assert box["altura"] == pytest.approx(0.865)  # bocas 1,5 cm acima do tampo
    assert box["profundidade"] == pytest.approx(0.642)
    ifc = model.doc.ifc
    (t,) = ifc.by_type("IfcElectricApplianceType")
    assert t.Name == "Fogão de piso 5 bocas" and t.PredefinedType == "ELECTRICCOOKER"
    defn = ot.definition_of(t)
    assert defn["object_id"] == out["object_id"]
    assert "informadas pelo usuário" in defn["description"]
    assert ue.get_pset(t, ot.PSET, should_inherit=False)
    (occ,) = ifc.by_type("IfcElectricAppliance")
    assert occ.GlobalId == out["id"] and ue.get_type(occ) == t
    assert ue.get_container(occ) == model.terreo
    state = objects.read_state(model.doc, occ)
    assert state["point"] == pytest.approx([2.0, 1.0]) and state["angle"] == pytest.approx(90)
    assert occ.Representation is not None
    # os parâmetros valem: o tipo com outra largura dá outra caixa
    values = ot.evaluate({**ot.read(t), "values": {"largura": 0.9}})
    assert values["largura"] == pytest.approx(0.9)


def test_af04_sem_at_so_o_tipo_e_nome_repetido_ganha_sufixo(ctx, model):
    first, _ = _call(ctx, "create_object", **_fogao())
    assert "id" not in first and not model.doc.ifc.by_type("IfcElectricAppliance")
    second, error = _call(ctx, "create_object", **_fogao())
    assert not error
    assert second["objeto"] == "Fogão de piso 5 bocas (2)"
    assert second["tipo"] == "Fogão de piso 5 bocas (2)"
    assert second["object_id"] != first["object_id"]
    third, _ = _call(ctx, "create_object", **_fogao(type_name="Fogão 76"))
    assert third["tipo"] == "Fogão 76" and third["objeto"] == "Fogão de piso 5 bocas (3)"


# AF05: recusas com o lugar, sem nada no histórico


def test_af05_definicao_com_erro_e_recusada(ctx, model):
    before = snapshot(model.doc.ifc)
    undo = len(model.history.undo_stack)

    def refused(**changes):
        args = _fogao()
        args.update(changes)
        text, error = _call(ctx, "create_object", **args)
        assert error
        assert snapshot(model.doc.ifc) == before
        assert len(model.history.undo_stack) == undo
        return text

    pieces = _fogao()["pieces"]
    # fórmula com parâmetro que não existe: diz a peça e o campo
    text = refused(pieces=[{**pieces[0], "width": "comprimento"}, *pieces[1:]])
    assert "peça 1 'Corpo'" in text and "largura" in text
    # medida que dá zero
    text = refused(pieces=[*pieces[:1], {**pieces[1], "height": "altura - altura"}])
    assert "Tampo" in text and "≤ 0" in text
    # peça aninhada, peças demais, nenhuma peça, categoria errada
    assert "não aceito" in refused(pieces=[{"kind": "object", "type": "Cadeira"}])
    many = [dict(pieces[0], name=f"P{i}") for i in range(MAX_PIECES + 1)]
    assert f"limite é {MAX_PIECES}" in refused(pieces=many)
    assert "pelo menos uma peça" in refused(pieces=[])
    assert "categoria inválida" in refused(category="fogao")
    assert "tipo predefinido" in refused(predefined_type="STOVE")
    assert "nome" in refused(name="")


# AF06: corrigir a definição refaz a ocorrência e mantém a identidade dela


def test_af06_corrige_a_definicao(ctx, model):
    made, _ = _call(ctx, "create_object", **_fogao(at=[1.0, 1.0]))
    occ = model.doc.get(made["id"])
    shape_before = snapshot(model.doc.ifc)
    pieces = _fogao()["pieces"]
    pieces.append({"kind": "box", "name": "Painel", "x": 0, "y": "profundidade - 0,05",
                   "z": "altura", "width": "largura", "depth": 0.05, "height": 0.10,
                   "material": "Inox"})
    out, error = _call(ctx, "edit_object_definition", object="Fogão de piso 5 bocas",
                       pieces=pieces)
    assert not error, out
    assert out["pecas"] == 5 and out["ocorrencias_refeitas"] == 1
    assert out["caixa"]["altura"] == pytest.approx(0.95)
    assert snapshot(model.doc.ifc) != shape_before
    assert model.doc.find(made["id"]) is not None  # a mesma ocorrência
    t = ue.get_type(model.doc.get(made["id"]))
    defn = ot.definition_of(t)
    assert defn["object_id"] == made["object_id"] and defn["version"] == 2
    assert [p["name"] for p in defn["pieces"]][-1] == "Painel"
    assert defn["description"].startswith("Medidas informadas")  # o que não veio fica
    assert [p["name"] for p in defn["params"] if p["name"] == "largura"]
    del occ
    # desfazer volta à definição de antes
    model.history.undo()
    assert snapshot(model.doc.ifc) == shape_before
    # recusas
    text, error = _call(ctx, "edit_object_definition", object="Geladeira", pieces=pieces)
    assert error and "não está no projeto" in text
    text, error = _call(ctx, "edit_object_definition", object=made["tipo"],
                        pieces=[{**pieces[0], "height": 0}])
    assert error and "≤ 0" in text
    assert snapshot(model.doc.ifc) == shape_before


def test_af06_tirar_parametro_usado_numa_ocorrencia_continua_valendo(ctx, model):
    made, _ = _call(ctx, "create_object", **_fogao(at=[1.0, 1.0]))
    # sem o parâmetro "profundidade", as peças que o usam não se calculam
    params = [p for p in _fogao()["params"] if p["name"] != "profundidade"]
    text, error = _call(ctx, "edit_object_definition", object=made["tipo"], params=params)
    assert error and "profundidade" in text
