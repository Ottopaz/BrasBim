# SPDX-License-Identifier: LGPL-3.0-or-later
"""Forro e piso como revestimento (spec/ui 46, FP01–FP07)."""

import ifcopenshell.util.element as ue
import pytest
from estrutura import bounds, check_history, column_type, created, qto, valid

from brasbim.core import delete
from brasbim.core.annotations import commands as ac
from brasbim.core.annotations import spaces
from brasbim.core.document import OpError
from brasbim.core.structure import commands as sc
from brasbim.core.structure import coverings as cv
from brasbim.core.walls import commands as wc

ROOM = [(0, 0), (4, 0), (4, 3), (0, 3)]


def ctype(model, name="Forro de gesso", kind="CEILING", layers=None):
    return created(model, cv.create_type(model.doc, name, layers or [
        {"material": "Gesso", "thickness": 0.0125}], kind))


def floor_type(model):
    return ctype(model, "Porcelanato", "FLOORING", [
        {"material": "Porcelanato", "thickness": 0.01},
        {"material": "Argamassa", "thickness": 0.005}])


def space(model, outline=ROOM):
    return created(model, ac.create_space(model.doc, model.terreo, outline))


def room_with_walls(model):
    """Quatro paredes de 14 cm por fora de 4,28 × 3,28: o ambiente fica em 4 × 3."""
    model.commit(wc.create_rectangle(model.doc, model.type14, model.terreo, (-0.14, -0.14),
                                     (4.14, 3.14)))
    return created(model, ac.create_space_in_room(model.doc, model.terreo, (2, 1.5)))


def rel_space(model, covering):
    rels = [r for r in model.doc.ifc.by_type("IfcRelCoversSpaces")
            if covering in r.RelatedCoverings]
    return rels[0].RelatingSpace if rels else None


def test_fp01_forro_no_ambiente(model, tmp_path):
    t = ctype(model)
    s = space(model)
    c = created(model, cv.create_in_space(model.doc, t, s))
    assert c.is_a("IfcCovering") and cv.predefined(c) == "CEILING"
    assert ue.get_type(c) == t
    assert ue.get_material(c).is_a("IfcMaterialLayerSetUsage")
    assert rel_space(model, c) == s
    lo, hi = bounds(c)
    assert lo[2] == pytest.approx(2.60) and hi[2] == pytest.approx(2.6125)
    q = qto(c, cv.QTO)
    assert q["Width"] == pytest.approx(0.0125)
    assert q["GrossArea"] == pytest.approx(12.0) and q["NetArea"] == pytest.approx(12.0)
    assert ue.get_pset(c, cv.COMMON_PSET)["Reference"] == "Forro de gesso"
    assert valid(model.doc.ifc)
    from brasbim.core.document import Document

    path = tmp_path / "fp01.ifc"
    model.doc.ifc.write(str(path))
    again = Document.open(str(path))
    state = cv.read_state(again.get(c.GlobalId))
    assert state["space"] == s.GlobalId and state["elevation"] == pytest.approx(2.60)


def test_fp02_piso_topo_no_nivel(model):
    t = floor_type(model)
    s = space(model)
    c = created(model, cv.create_in_space(model.doc, t, s))
    assert cv.predefined(c) == "FLOORING"
    lo, hi = bounds(c)
    assert hi[2] == pytest.approx(0.0) and lo[2] == pytest.approx(-0.015)
    assert cv.top_material(t) == "Porcelanato"
    # pilar no meio: o piso desconta (ponto (d))
    col = column_type(model)
    model.commit(sc.create_column(model.doc, col, model.terreo, (2, 1.5)))
    q = qto(c, cv.QTO)
    assert q["GrossArea"] == pytest.approx(12.0)
    assert q["NetArea"] == pytest.approx(12.0 - 0.20 * 0.40)
    assert valid(model.doc.ifc)


def test_fp03_parede_movida_refaz_forro_e_piso(model):
    s = room_with_walls(model)
    ceiling = created(model, cv.create_in_space(model.doc, ctype(model), s))
    floor = created(model, cv.create_in_space(model.doc, floor_type(model), s))
    assert qto(floor, cv.QTO)["GrossArea"] == pytest.approx(12.0)
    east = max(model.doc.ifc.by_type("IfcWall"), key=lambda w: bounds(w)[0][0])

    def move():  # a parede leva as junções (spec/ui 13 §3)
        model.commit(wc.offset_wall(model.doc, east, 1.0))

    check_history(model, move)
    grown = qto(floor, cv.QTO)["GrossArea"]
    assert abs(grown - 12.0) == pytest.approx(3.0)
    assert qto(ceiling, cv.QTO)["GrossArea"] == pytest.approx(grown)
    model.history.undo()
    assert qto(floor, cv.QTO)["GrossArea"] == pytest.approx(12.0)
    assert valid(model.doc.ifc)


def test_fp04_em_todos_os_ambientes(model):
    t = floor_type(model)
    a = space(model)
    b = space(model, [(5, 0), (8, 0), (8, 3), (5, 3)])
    model.commit(cv.fill_storey(model.doc, t, model.terreo))
    assert len(cv.bound_to(model.doc, a)) == 1 and len(cv.bound_to(model.doc, b)) == 1
    with pytest.raises(OpError, match="já têm"):
        cv.fill_storey(model.doc, t, model.terreo)
    with pytest.raises(OpError, match="já tem"):
        cv.create_in_space(model.doc, t, a)
    # forro é outro uso: entra nos dois
    tx = cv.fill_storey(model.doc, ctype(model), model.terreo)
    assert len(tx.ops) == 2
    assert valid(model.doc.ifc)


def test_fp05_pe_direito_pelo_forro(model):
    s = space(model)
    assert ue.get_pset(s, spaces.QTO)["Height"] == pytest.approx(2.80)
    c = created(model, cv.create_in_space(model.doc, ctype(model), s, elevation=2.50))
    assert ue.get_pset(s, spaces.QTO)["Height"] == pytest.approx(2.50)
    model.commit(cv.edit_covering(model.doc, c, elevation=2.40))
    assert ue.get_pset(s, spaces.QTO)["Height"] == pytest.approx(2.40)
    model.commit(ac.edit_element(model.doc, s, height=3.0))  # fixo continua fixo
    assert ue.get_pset(s, spaces.QTO)["Height"] == pytest.approx(3.0)


def test_fp06_apagar_o_ambiente_solta(model):
    s = space(model)
    c = created(model, cv.create_in_space(model.doc, floor_type(model), s))

    def remove():
        tx, _ = delete.delete_elements(model.doc, [s.GlobalId])
        model.commit(tx)

    check_history(model, remove)
    state = cv.read_state(c)
    assert state["space"] is None and len(state["outline"]) == 4
    assert rel_space(model, c) is None
    model.commit(cv.edit_covering(model.doc, c, outline=[[0, 0], [2, 0], [2, 2], [0, 2]]))
    assert qto(c, cv.QTO)["GrossArea"] == pytest.approx(4.0)
    model.history.undo()
    model.history.undo()
    assert cv.read_state(c)["space"] == s.GlobalId
    # editar o contorno à mão solta do ambiente
    model.commit(cv.edit_covering(model.doc, c, outline=[[0, 0], [2, 0], [2, 2], [0, 2]]))
    assert cv.read_state(c)["space"] is None
    # excluir o revestimento
    tx, _ = delete.delete_elements(model.doc, [c.GlobalId])
    model.commit(tx)
    assert not model.doc.ifc.by_type("IfcCovering")
    assert valid(model.doc.ifc)


def test_fp06_contorno_livre_e_tipos(model):
    t = floor_type(model)
    c = created(model, cv.create_covering(model.doc, t, model.terreo,
                                          [(0, 0), (2, 0), (2, 1), (0, 1)]))
    assert cv.read_state(c)["space"] is None and qto(c, cv.QTO)["NetArea"] == pytest.approx(2)
    with pytest.raises(OpError, match="forro"):
        cv.edit_covering(model.doc, c, type=ctype(model).GlobalId)
    # tipo mais espesso: o piso desce
    model.commit(cv.edit_type(model.doc, t, layers=[
        {"material": "Porcelanato", "thickness": 0.01},
        {"material": "Argamassa", "thickness": 0.03}]))
    assert bounds(c)[0][2] == pytest.approx(-0.04)
    other = created(model, cv.create_type(model.doc, "Cerâmica", [
        {"material": "Cerâmica", "thickness": 0.008}], "FLOORING"))
    model.commit(cv.delete_type(model.doc, t, other))
    assert ue.get_type(c) == other
    model.history.undo()
    assert ue.get_type(c).GlobalId == t.GlobalId
    assert valid(model.doc.ifc)


def test_fp07_planta_e_tabelas(model):
    from brasbim.core import plan
    from brasbim.core.quantities import tables

    s = space(model)
    floor = created(model, cv.create_in_space(model.doc, floor_type(model), s))
    ceiling = created(model, cv.create_in_space(model.doc, ctype(model), s))
    p = plan.storey_plan(model.doc, model.terreo)
    (region,) = [r for r in p.regions if r.key == floor.GlobalId]
    assert region.fill["pattern"] == "cross" and region.fill["spacing"] == pytest.approx(0.60)
    assert any(sh.owner == floor.GlobalId and sh.role == "covering" for sh in p.shapes)
    assert not any(sh.owner == ceiling.GlobalId for sh in p.shapes)  # acima do corte
    assert p.pick((2, 1.5), 0.05) == s.GlobalId  # dentro: o ambiente vem antes
    # tabela de revestimentos e colunas na de ambientes
    state = {"name": "Revestimentos", "category": "coverings",
             "columns": [{"field": "kind"}, {"field": "type"}, {"field": "space"},
                         {"field": "area"}]}
    rows = [r.cells for r in tables.compute(model.doc, state).rows if r.kind == "element"]
    assert sorted(r[0] for r in rows) == ["Forro", "Piso"]
    assert all(r[2] == "01 Ambiente" and r[3] == pytest.approx(12.0) for r in rows)
    state = {"name": "Ambientes", "category": "spaces",
             "columns": [{"field": "number"}, {"field": "ceiling"}, {"field": "floor"},
                         {"field": "flooring_area"}]}
    (row,) = [r.cells for r in tables.compute(model.doc, state).rows if r.kind == "element"]
    assert row[1:] == ["Forro de gesso", "Porcelanato", pytest.approx(12.0)]
    model.commit(tables.create_table(model.doc, "coverings"))


def test_fp06_mover_e_copiar(model):
    from brasbim.core import transform

    s = space(model)
    c = created(model, cv.create_in_space(model.doc, floor_type(model), s))
    # o ambiente leva o piso junto
    model.commit(transform.move_elements(model.doc, [s.GlobalId, c.GlobalId], (10, 0)))
    state = cv.read_state(c)
    assert state["space"] == s.GlobalId and min(p[0] for p in state["outline"]) == 10
    # o piso sozinho solta; a cópia sai solta
    model.commit(transform.move_elements(model.doc, [c.GlobalId], (0, 5)))
    assert cv.read_state(c)["space"] is None
    model.commit(transform.copy_elements(model.doc, [c.GlobalId], (0, 5)))
    assert len(model.doc.ifc.by_type("IfcCovering")) == 2
    assert valid(model.doc.ifc)
