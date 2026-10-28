# SPDX-License-Identifier: LGPL-3.0-or-later
"""Projeto legal, etapa 2 (spec/ui/31-projeto-legal.md §4 e §13), no núcleo: perfil
municipal (PL04, PL09–PL11)."""

import copy
import json

import ifcopenshell.util.element as ue
import pytest
from estrutura import check_history

from brasbim.core import intervention as iv
from brasbim.core import municipal, plan, storeys
from brasbim.core.annotations import commands as ac
from brasbim.core.document import Document, OpError
from brasbim.core.drawings import views


def _profile(profile_id):
    return next(p for p in municipal.builtin() if p["id"] == profile_id)


def test_pl09_perfis_prontos():
    found = municipal.builtin()
    assert found[0]["id"] == "generico"
    assert {p["id"] for p in found} == {"generico", "sp-araras", "sp-jacarei",
                                        "sp-sao-paulo", "pr-curitiba"}
    for p in found:
        municipal.validate(p)
        assert p["fonte"]["documento"] and p["versao"] >= 1
        assert set(p["cores"]) == set(iv.CODES)
    generic = _profile("generico")
    assert {c: d["cor"] for c, d in generic["cores"].items() if d["cor"]} == \
        iv.GENERIC_COLORS
    # Araras traz as quatro cores da fonte; o resto vem do Genérico, e o perfil diz isso.
    araras = _profile("sp-araras")
    assert araras["cores"]["A_CONSTRUIR"]["cor"] == "#D62828"
    assert araras["cores"]["A_DEMOLIR"]["cor"] == "#E0A800"
    assert araras["herdado"] == ["A_REGULARIZAR", "TEMPORARIO"]
    assert araras["cores"]["EXISTENTE"]["hachura"] == "solid"  # hachura do Genérico
    assert _profile("sp-jacarei")["escalas"]["implantacao"] == 200
    assert _profile("sp-jacarei")["quadro_de_areas"]["piscina_a_parte"] is True
    assert _profile("sp-sao-paulo")["planta"] == "simplificada"
    assert _profile("pr-curitiba")["pdf"] == {"max_mb": 3, "carimbo_ultima_prancha": True}
    assert _profile("pr-curitiba")["escalas"]["plantas"] == storeys.DEFAULT_SCALE


def test_pl04_perfil_copiado_no_ifc(model, tmp_path, monkeypatch):
    doc = model.doc
    assert municipal.read(doc) is None and municipal.current(doc)["id"] == "generico"
    build = model.wall((0, 0), (5, 0))
    keep = model.wall((0, 4), (5, 4))
    model.commit(iv.set_situation(doc, [keep.GlobalId], "EXISTENTE"))
    araras = copy.deepcopy(_profile("sp-araras"))
    araras["cores"]["A_CONSTRUIR"]["cor"] = "#AA0000"  # editado na cópia do projeto
    check_history(model, lambda: model.commit(municipal.set_profile(doc, araras)))
    assert municipal.set_profile(doc, araras).ops == []
    values = ue.get_pset(doc.project, municipal.PSET, should_inherit=False)
    assert json.loads(values["Parametros"])["nome"] == "Araras/SP"
    assert plan.storey_plan(doc, model.terreo).colors[build.GlobalId] == "#AA0000"

    # Abre igual em outra máquina, mesmo sem os arquivos dos perfis.
    path = tmp_path / "araras.ifc"
    doc.save(str(path))
    monkeypatch.setattr(municipal, "FOLDER", tmp_path / "sem-perfis")
    other = Document.open(str(path))
    assert municipal.current(other)["nome"] == "Araras/SP"
    terreo = other.ifc.by_type("IfcBuildingStorey")[0]
    assert plan.storey_plan(other, terreo).colors[build.GlobalId] == "#AA0000"

    # Voltar ao Genérico tira a cópia; desfazer devolve.
    monkeypatch.undo()
    model.commit(municipal.set_profile(doc, None))
    assert municipal.read(doc) is None
    assert plan.storey_plan(doc, model.terreo).colors[build.GlobalId] == \
        iv.GENERIC_COLORS["A_CONSTRUIR"]
    model.history.undo()
    assert municipal.read(doc)["cores"]["A_CONSTRUIR"]["cor"] == "#AA0000"


def test_pl10_hachura_da_situacao(model):
    doc = model.doc
    build = model.wall((0, 0), (5, 0))
    keep = model.wall((0, 4), (5, 4))
    gone = model.wall((0, 8), (5, 8))
    model.commit(iv.set_situation(doc, [keep.GlobalId], "EXISTENTE"))
    model.commit(iv.set_situation(doc, [gone.GlobalId], "A_DEMOLIR"))
    p = plan.storey_plan(doc, model.terreo)
    assert p.hatches[keep.GlobalId] == {"pattern": "solid", "angle": 45.0}
    assert p.hatches[build.GlobalId]["pattern"] == "lines"
    assert {r.hatch["pattern"] for r in p.regions if r.tint} == {"solid", "lines", "none"}
    # Duas situações com a mesma cor e hachuras diferentes não se juntam numa região.
    profile = copy.deepcopy(municipal.current(doc))
    profile["cores"]["A_DEMOLIR"]["cor"] = profile["cores"]["EXISTENTE"]["cor"]
    model.commit(municipal.set_profile(doc, profile))
    p = plan.storey_plan(doc, model.terreo)
    black = [r for r in p.regions if r.tint == profile["cores"]["EXISTENTE"]["cor"]]
    assert sorted(r.hatch["pattern"] for r in black) == ["none", "solid"]
    # Situação sem cor no perfil não é pintada.
    profile["cores"]["A_CONSTRUIR"]["cor"] = None
    model.commit(municipal.set_profile(doc, profile))
    assert build.GlobalId not in plan.storey_plan(doc, model.terreo).colors


def test_pl11_escalas_do_perfil(model):
    doc = model.doc
    model.wall()
    model.commit(ac.create_view(doc, "section", (0, -1), (0, 5)))
    (cut,) = views.all_views(doc)
    assert views.read_state(cut)["scale"] == storeys.DEFAULT_SCALE
    jacarei = _profile("sp-jacarei")

    def action():
        model.commit(municipal.choose(doc, jacarei, scales=True))

    check_history(model, action)
    tx = model.history.undo_stack[-1]
    stories = doc.ifc.by_type("IfcBuildingStorey")
    assert [op.op for op in tx.ops] ==         ["municipal.set"] + ["storey.edit"] * len(stories) + ["view.edit"]
    assert {storeys.stored_scale(s) for s in stories} == {100}
    assert views.read_state(cut)["scale"] == 100
    # Corte e fachada novos já nascem na escala do perfil.
    model.commit(ac.create_view(doc, "elevation", (6, -1), (6, 5)))
    assert {views.read_state(v)["scale"] for v in views.all_views(doc)} == {100}
    assert municipal.apply_scales(doc, jacarei).ops == []  # já está tudo na escala
    # Sem aplicar: só a cópia do perfil muda.
    model.commit(municipal.choose(doc, _profile("generico"), scales=False))
    assert storeys.stored_scale(model.terreo) == 100
    assert municipal.view_scale(doc, "section") == storeys.DEFAULT_SCALE


def test_pl12_perfil_invalido(model):
    good = _profile("generico")
    for change, message in (
            (lambda p: p.update(nome=" "), "nome"),
            (lambda p: p["cores"].update(OUTRA={"cor": "#000000"}), "desconhecidas"),
            (lambda p: p["cores"]["EXISTENTE"].update(cor="preto"), "cor inválida"),
            (lambda p: p["cores"]["EXISTENTE"].update(hachura="pontos"), "hachura"),
            (lambda p: p["escalas"].update(plantas=0), "escala"),
            (lambda p: p.update(planta="parcial"), "planta"),
            (lambda p: p["pdf"].update(max_mb=-1), "PDF")):
        bad = copy.deepcopy(good)
        change(bad)
        with pytest.raises(OpError, match=message):
            municipal.set_profile(model.doc, bad)
