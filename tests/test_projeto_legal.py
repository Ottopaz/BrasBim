# SPDX-License-Identifier: LGPL-3.0-or-later
"""Projeto legal, etapa 1 (spec/ui/31-projeto-legal.md §2–§3), no núcleo: PL01–PL03."""

import ifcopenshell.util.element as ue
import pytest
from estrutura import check_history, created, valid

from brasbim.core import display_layers as dl
from brasbim.core import intervention as iv
from brasbim.core import plan, select_similar, transform
from brasbim.core.annotations import commands as ac
from brasbim.core.delete import delete_elements
from brasbim.core.document import OpError
from brasbim.core.drawings import saved_views as sv
from brasbim.core.drawings import section
from brasbim.core.walls import commands as cmd


def _status(element, pset="Pset_WallCommon"):
    values = ue.get_pset(element, pset, should_inherit=False) or {}
    status = values.get("Status")
    return status[0] if isinstance(status, (list, tuple)) and status else status


def _own(element):
    return (ue.get_pset(element, iv.PSET, should_inherit=False) or {}).get(iv.PROPERTY)


def _owners(p: plan.Plan) -> set[str]:
    return {s.owner for s in p.shapes} | {g for g, _ in p.annotations}


def test_pl01_situacao_no_ifc_e_desfazer(model):
    wall = model.wall()
    space = created(model, ac.create_space(model.doc, model.terreo,
                                           [(0, 0), (4, 0), (4, 3), (0, 3)]))
    dim = created(model, ac.create_dimension(model.doc, model.terreo, [(0, -1), (5, -1)]))
    # Padrão: a construir, sem o Pset próprio; o Status comum continua NEW.
    assert iv.situation_of(model.doc, wall) == "A_CONSTRUIR" and _own(wall) is None
    assert _status(wall) == "NEW"

    check_history(model, lambda: model.commit(iv.set_situation(model.doc, [wall.GlobalId],
                                                               "A_DEMOLIR")))
    assert _own(wall) == "A_DEMOLIR" and _status(wall) == "DEMOLISH"
    assert iv.situation_of(model.doc, wall) == "A_DEMOLIR"
    # O estado da parede lê o Status (edições seguintes o regravam igual).
    assert cmd.read_state(model.doc, wall)["common"]["Status"] == "DEMOLISH"
    model.commit(cmd.edit_wall(model.doc, wall, path={"kind": "line", "start": [0.0, 0.0], "end": [6.0, 0.0]}))
    assert _status(wall) == "DEMOLISH" and _own(wall) == "A_DEMOLIR"

    model.commit(iv.set_situation(model.doc, [wall.GlobalId], "A_REGULARIZAR"))
    assert _own(wall) == "A_REGULARIZAR" and _status(wall) == "EXISTING"
    model.history.undo()
    assert _own(wall) == "A_DEMOLIR" and _status(wall) == "DEMOLISH"
    model.history.undo()
    model.history.undo()
    assert _own(wall) is None and _status(wall) == "NEW"
    assert iv.situation_of(model.doc, wall) == "A_CONSTRUIR"

    # Ambiente e cota: só o Pset próprio (não há Status comum para eles).
    tx = model.commit(iv.set_situation(model.doc, [space.GlobalId, dim.GlobalId],
                                       "EXISTENTE"))
    assert [op.op for op in tx.ops] == ["situation.set"] * 2
    for element in (space, dim):
        assert _own(element) == "EXISTENTE"
        assert not any(name.startswith("Pset_") and "Status" in values
                       for name, values in ue.get_psets(element).items())
    assert valid(model.doc.ifc)
    with pytest.raises(OpError):
        iv.set_situation(model.doc, [wall.GlobalId], "DEMOLIDO")


def test_pl01b_excluir_e_desfazer_devolve_a_situacao(model, tmp_path):
    walls = [model.wall((0, 0), (5, 0)), model.wall((5, 0), (5, 4))]
    model.commit(iv.set_situation(model.doc, [walls[0].GlobalId], "A_TRANSFORMAR"))
    gid = walls[0].GlobalId
    model.commit(delete_elements(model.doc, [gid])[0])
    assert model.doc.find(gid) is None
    model.history.undo()
    wall = model.doc.get(gid)
    assert _own(wall) == "A_TRANSFORMAR" and _status(wall) == "EXISTING"
    # Arquivo reaberto: a situação vem do IFC (memória montada na primeira consulta).
    path = tmp_path / "legal.ifc"
    model.doc.save(str(path))
    from brasbim.core.document import Document

    other = Document.open(str(path))
    assert iv.situation_of(other, other.get(gid)) == "A_TRANSFORMAR"
    assert iv.situation_of(other, other.get(walls[1].GlobalId)) == "A_CONSTRUIR"


def test_pl02_copiar_herda_e_selecionar_semelhantes(model):
    old = model.wall((0, 0), (5, 0))
    new = model.wall((0, 4), (5, 4))
    text = created(model, ac.create_annotation(model.doc, "text", model.terreo, at=[1, 1],
                                               text="SALA"))
    model.commit(iv.set_situation(model.doc, [old.GlobalId, text.GlobalId], "EXISTENTE"))

    def copy():
        model.commit(transform.copy_elements(model.doc, [old.GlobalId, text.GlobalId],
                                             (0, -2)))

    check_history(model, copy)
    copies = [model.doc.get(op.id) for op in model.history.undo_stack[-1].ops
              if op.op in ("wall.create", "text.create")]
    assert len(copies) == 2
    for c in copies:
        assert iv.situation_of(model.doc, c) == "EXISTENTE" and _own(c) == "EXISTENTE"
    assert _status(next(c for c in copies if c.is_a("IfcWall"))) == "EXISTING"
    # Cópia em série, espelho com cópia e dividir também herdam.
    model.commit(transform.copy_series(model.doc, [old.GlobalId], (0, -1), 2))
    model.commit(transform.mirror_elements(model.doc, [old.GlobalId], (0, 10), (5, 10),
                                           keep=True))
    model.commit(cmd.split_wall(model.doc, old, (2.0, 0.0)))
    existing = {w.GlobalId for w in model.doc.ifc.by_type("IfcWall")
                if iv.situation_of(model.doc, w) == "EXISTENTE"}
    assert len(existing) == 1 + 1 + 2 + 1 + 1  # original, cópia, série, espelho, trecho
    assert new.GlobalId not in existing

    found = select_similar.similar(model.doc, model.terreo, [old.GlobalId], "situation")
    texts = {text.GlobalId} | {c.GlobalId for c in copies if c.is_a("IfcAnnotation")}
    assert set(found) == existing | texts  # o texto existente e a cópia dele também
    found = select_similar.similar(model.doc, model.terreo, [new.GlobalId], "situation")
    assert found == [new.GlobalId]
    assert ("situation", "Mesma situação") in select_similar.CRITERIA


def test_pl02b_situacao_dos_novos_elementos(model):
    wall = model.wall()
    tx = cmd.create_wall(model.doc, model.type14, model.terreo, (0, 2), (5, 2))
    tx = iv.stamp_created(model.doc, tx, "EXISTENTE")
    assert [op.op for op in tx.ops][-1] == "situation.set"
    check_history(model, lambda: model.commit(tx))
    made = model.doc.get(tx.ops[0].id)
    assert _own(made) == "EXISTENTE" and _status(made) == "EXISTING"
    assert iv.stamp_created(model.doc, tx, "A_CONSTRUIR") is tx
    assert _own(wall) is None


def test_pl03_filtro_e_cores(model):
    demolish = model.wall((0, 0), (5, 0))
    build = model.wall((0, 4), (5, 4))
    keep = model.wall((0, 8), (5, 8))
    doc = model.doc
    # Obra nova (tudo a construir): a vista Projeto não pinta nada.
    assert plan.storey_plan(doc, model.terreo).colors == {}
    model.commit(iv.set_situation(doc, [demolish.GlobalId], "A_DEMOLIR"))
    model.commit(iv.set_situation(doc, [keep.GlobalId], "EXISTENTE"))

    p = plan.storey_plan(doc, model.terreo)
    assert {demolish.GlobalId, build.GlobalId, keep.GlobalId} <= _owners(p)
    assert p.colors[build.GlobalId] == iv.GENERIC_COLORS["A_CONSTRUIR"]
    assert p.colors[demolish.GlobalId] == iv.GENERIC_COLORS["A_DEMOLIR"]
    # A parede a construir cortada leva a cor no traço e no preenchimento da região.
    red = iv.GENERIC_COLORS["A_CONSTRUIR"]
    assert any(e.tint == red for e in p.edges) and any(r.tint == red for r in p.regions)
    assert iv.present(doc) == ["A_CONSTRUIR", "EXISTENTE", "A_DEMOLIR"]

    with iv.using(doc, "after"):
        p = plan.storey_plan(doc, model.terreo)
        assert demolish.GlobalId not in _owners(p)
        assert {build.GlobalId, keep.GlobalId} <= _owners(p)
        assert p.colors == {}  # sem cor fora da vista Projeto
        assert dl.is_hidden(doc, demolish) and not dl.is_hidden(doc, build)
    with iv.using(doc, "before"):
        assert _owners(plan.storey_plan(doc, model.terreo)) & {
            demolish.GlobalId, build.GlobalId, keep.GlobalId} == {demolish.GlobalId,
                                                                  keep.GlobalId}
    with iv.using(doc, "plain"):
        p = plan.storey_plan(doc, model.terreo)
        assert p.colors == {} and demolish.GlobalId in _owners(p)
    assert doc.situation_view == "project"

    # Corte: o filtro tira a parede a demolir; na vista Projeto, cores por dono.
    view = created(model, ac.create_view(doc, "section", (2.5, -1), (2.5, 9)))
    drawing = section.draw(doc, view)
    assert drawing.colors.get(build.GlobalId) == red
    with iv.using(doc, "after"):
        assert demolish.GlobalId not in {it.owner for it in section.draw(doc, view).items}

    # A vista salva guarda o filtro e o aplica enquanto se desenha.
    saved = created(model, sv.create_saved_view(doc, "Depois", "plan",
                                                storey=model.terreo.GlobalId,
                                                options={"situation": "after"}))
    state = sv.read_state(saved)
    assert sv.options(state)["situation"] == "after"
    with sv.drawing(doc, state):
        assert doc.situation_view == "after"
        assert demolish.GlobalId not in _owners(sv.plan_of(doc, state))
    assert doc.situation_view == "project"
    with pytest.raises(OpError):
        sv.create_saved_view(doc, "x", "plan", storey=model.terreo.GlobalId,
                             options={"situation": "durante"})


def test_pl01c_psets_com_status_conferem_com_o_esquema():
    """A tabela fixa de ``STATUS_PSETS`` confere com os modelos de Pset do IFC 4.3."""
    import ifcopenshell.util.pset

    template = ifcopenshell.util.pset.get_template("IFC4X3")
    for cls, name in iv.STATUS_PSETS.items():
        assert name in template.get_applicable_names(cls, pset_only=True), cls
        assert any(p.Name == "Status" for p in template.get_by_name(name).HasPropertyTemplates)
    for cls in ("IfcSpace", "IfcAnnotation"):  # só o Pset próprio (§2)
        for name in template.get_applicable_names(cls, pset_only=True):
            found = template.get_by_name(name)
            assert not any(p.Name == "Status" for p in found.HasPropertyTemplates), name
