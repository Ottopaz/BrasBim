# SPDX-License-Identifier: LGPL-3.0-or-later
"""Quantitativos e tabelas (spec/ui 17 §7), no núcleo: TB01 a TB09 e TB11."""

import json
import zipfile
from xml.etree import ElementTree

import ifcopenshell.util.element as ue
import pytest
from estrutura import check_history, valid

from brasbim.core.annotations import commands as ac
from brasbim.core.assistant import tools
from brasbim.core.fillings import commands as fc
from brasbim.core.quantities import export
from brasbim.core.quantities import tables as tb
from brasbim.core.walls import commands as cmd


def _new(model, tx):
    model.commit(tx)
    return model.doc.get(tx.ops[0].id)


@pytest.fixture
def casa(model):
    """Retângulo (0, 0)–(8, 5) com parede interna em x = 5; duas P1, três J1 e uma J2;
    Sala e Quarto."""
    doc = model.doc
    model.commit(cmd.create_rectangle(doc, model.type14, model.terreo, (0, 0), (8, 5)))
    model.commit(cmd.create_wall(doc, model.type14, model.terreo, (5, 0), (5, 5)))
    left, top, right, bottom, inner = doc.ifc.by_type("IfcWall")
    model.p1 = _new(model, fc.create_door_type(doc, "P1"))
    model.j1 = _new(model, fc.create_window_type(doc, "J1", defaults={
        "width": 1.2, "height": 1.0, "base": 1.1}))
    model.j2 = _new(model, fc.create_window_type(doc, "J2", defaults={
        "width": 1.5, "height": 1.2, "base": 1.1}))
    model.commit(fc.create_door(doc, model.p1, bottom, 1.0))
    model.commit(fc.create_door(doc, model.p1, inner, 2.0))
    for wall, distance in ((top, 1.0), (top, 6.0), (left, 2.0)):
        model.commit(fc.create_window(doc, model.j1, wall, distance))
    model.commit(fc.create_window(doc, model.j2, right, 2.0))
    model.commit(ac.create_space_in_room(doc, model.terreo, (2, 2), name="Sala"))
    model.commit(ac.create_space_in_room(doc, model.terreo, (6.5, 2), name="Quarto"))
    model.walls = (left, top, right, bottom, inner)
    return model


def _table(model, template, **options):
    tx = model.commit(tb.create_table(model.doc, template, **options))
    return model.doc.get(tx.ops[0].id)


def _cells(result, kind):
    return [dict(zip([c.field for c in result.columns], r.cells, strict=True))
            for r in result.rows if r.kind == kind]


def test_tb01_quadro_de_esquadrias(casa):
    table = _table(casa, "fillings")
    assert table.is_a("IfcAnnotation") and table.ObjectType == "Tabela"
    result = tb.compute(casa.doc, table)
    groups = _cells(result, "group")
    assert [(g["code"], g["count"]) for g in groups] == [("J1", 3), ("J2", 1), ("P1", 2)]
    j1, j2, p1 = groups
    assert (j1["width"], j1["height"], j1["sill"]) == pytest.approx((1.2, 1.0, 1.1))
    assert (j2["width"], j2["height"]) == pytest.approx((1.5, 1.2))
    assert (p1["width"], p1["height"], p1["sill"]) == pytest.approx((0.86, 2.13, 0.0))
    (total,) = _cells(result, "total")
    assert total["count"] == 6 and total["code"] == "Total"
    assert [c.title for c in result.columns] == ["Código", "Tipo", "Largura (m)",
                                                 "Altura (m)", "Peitoril (m)", "Contagem"]
    (j1_row,) = [r for r in result.rows if r.kind == "group" and r.cells[0] == "J1"]
    assert len(j1_row.elements) == 3


def test_tb02_quadro_de_areas(casa):
    result = tb.compute(casa.doc, _table(casa, "areas"))
    spaces = {s.LongName: s for s in casa.doc.ifc.by_type("IfcSpace")}
    rows = _cells(result, "element")
    assert [r["space_name"] for r in rows] == ["Sala", "Quarto"]
    for r in rows:
        net = ue.get_pset(spaces[r["space_name"]], "Qto_SpaceBaseQuantities")["NetFloorArea"]
        assert r["floor_area"] == pytest.approx(net)
    (subtotal,) = _cells(result, "subtotal")
    assert subtotal["number"] == "Subtotal Térreo"
    assert subtotal["floor_area"] == pytest.approx(sum(r["floor_area"] for r in rows))
    (built,) = _cells(result, "built")
    assert built["number"] == "Área construída Térreo"
    assert built["floor_area"] == pytest.approx(8 * 5)  # face externa: (0, 0)–(8, 5)


def test_tb03_paredes_por_tipo(casa):
    result = tb.compute(casa.doc, _table(casa, "walls"))
    (group,) = _cells(result, "group")
    walls = casa.doc.ifc.by_type("IfcWall")
    qtos = [ue.get_pset(w, "Qto_WallBaseQuantities") for w in walls]
    assert group["type"] == "Alvenaria 14" and group["thickness"] == pytest.approx(0.14)
    assert group["length"] == pytest.approx(sum(q["Length"] for q in qtos))
    assert group["side_area"] == pytest.approx(sum(q["NetSideArea"] for q in qtos))
    assert group["side_area"] < sum(q["GrossSideArea"] for q in qtos)  # sem os vãos
    assert group["volume"] == pytest.approx(sum(q["NetVolume"] for q in qtos))


def test_tb04_filtro_agrupamento_e_ordem(casa):
    doc = casa.doc
    tx = casa.commit(cmd.create_wall(doc, casa.type14, casa.superior, (0, 0), (3, 0)))
    upper = doc.get(tx.ops[0].id)
    table = _table(casa, "blank", category="walls")
    casa.commit(tb.edit_table(doc, table, columns=[{"field": "storey"},
                                                   {"field": "length"}],
                              group_by="storey", rows="group"))
    groups = _cells(tb.compute(doc, table), "group")
    assert [g["storey"] for g in groups] == ["Térreo", "Superior"]  # pela cota
    assert groups[1]["length"] == pytest.approx(3.0)
    casa.commit(tb.edit_table(doc, table, storeys=[casa.superior.GlobalId]))
    rows = tb.compute(doc, table).rows
    assert rows[0].elements == [upper.GlobalId]
    # elementos ordenados pelo comprimento, decrescente; "vários" no que muda no grupo
    casa.commit(tb.edit_table(doc, table, storeys=[], group_by=None, rows="element",
                              columns=[{"field": "length"}, {"field": "storey"}],
                              sort={"field": "length", "descending": True}))
    lengths = [r["length"] for r in _cells(tb.compute(doc, table), "element")]
    assert lengths == sorted(lengths, reverse=True) and len(lengths) == 6
    casa.commit(tb.edit_table(doc, table, group_by="type", rows="group"))
    (group,) = _cells(tb.compute(doc, table), "group")
    assert group["storey"] == tb.MIXED
    # filtro por tipo
    windows = _table(casa, "fillings")
    casa.commit(tb.edit_table(doc, windows, types=[casa.j1.GlobalId]))
    assert [g["code"] for g in _cells(tb.compute(doc, windows), "group")] == ["J1"]


def test_tb05_acompanha_o_modelo(casa):
    doc = casa.doc
    table = _table(casa, "fillings")
    before = tb.read_state(table)
    left = casa.walls[0]
    tx = casa.commit(fc.create_door(doc, casa.p1, left, 4.0))
    door = doc.get(tx.ops[-2].id)
    counts = {g["code"]: g["count"] for g in _cells(tb.compute(doc, table), "group")}
    assert counts["P1"] == 3
    casa.commit(fc.edit_door(doc, door, width=1.0))
    (p1,) = [g for g in _cells(tb.compute(doc, table), "group") if g["code"] == "P1"]
    assert p1["width"] == tb.MIXED
    casa.history.undo()
    casa.history.undo()
    counts = {g["code"]: g["count"] for g in _cells(tb.compute(doc, table), "group")}
    assert counts["P1"] == 2
    assert tb.read_state(table) == before


def test_tb06_operacoes_diario_e_validacao(casa, tmp_path):
    def action():
        table = _table(casa, "fillings")
        casa.commit(tb.edit_table(casa.doc, table, name="Esquadrias", totals=False,
                                  columns=[{"field": "code", "title": "Cód."},
                                           {"field": "count"}]))
        tx = casa.commit(tb.create_table(casa.doc, "structure"))
        assert [op.op for op in tx.ops] == ["table.create"] * 3
        casa.commit(tb.delete_table(casa.doc, tx.ops[1].id))

    check_history(casa, action)
    reopened = casa.reopen(tmp_path)
    assert valid(reopened)
    found = [e for e in reopened.by_type("IfcAnnotation") if e.ObjectType == "Tabela"]
    assert len(found) == 3
    names = sorted(tb.read_state(e)["name"] for e in found)
    assert names == ["Esquadrias", "Estrutura: lajes", "Estrutura: pilares"]
    (fillings,) = [e for e in found if e.Name == "Esquadrias"]
    params = json.loads(ue.get_pset(fillings, tb.PSET)["Parametros"])
    assert params["columns"][0] == {"field": "code", "title": "Cód."}


def test_tb06_definicao_invalida(casa):
    table = _table(casa, "blank", category="walls")
    with pytest.raises(Exception, match="coluna"):
        tb.edit_table(casa.doc, table, columns=[{"field": "floor_area"}])
    # trocar a categoria tira o que ela não tem
    casa.commit(tb.edit_table(casa.doc, table, columns=[{"field": "type"},
                                                        {"field": "length"}],
                              group_by="thickness"))
    casa.commit(tb.edit_table(casa.doc, table, category="spaces"))
    state = tb.read_state(table)
    assert state["columns"] == [{"field": "type"}] and state["group_by"] is None


def test_tb07_excluir_pavimento_do_filtro(casa):
    doc = casa.doc
    tx = casa.commit(cmd.create_storey(doc, "Cobertura", 5.6))
    roof = tx.ops[0].id
    table = _table(casa, "walls")
    casa.commit(tb.edit_table(doc, table, storeys=[roof]))
    tx = casa.commit(cmd.delete_storey(doc, roof))
    assert [op.op for op in tx.ops] == ["table.edit", "storey.delete"]
    assert tb.read_state(table)["storeys"] == []  # vazio: vale para todos
    casa.history.undo()
    assert tb.read_state(table)["storeys"] == [roof]
    # o tipo excluído também sai do filtro
    tx = casa.commit(fc.create_window_type(doc, "J9"))
    j9 = tx.ops[0].id
    windows = _table(casa, "fillings")
    casa.commit(tb.edit_table(doc, windows, types=[j9, casa.j1.GlobalId]))
    tx = casa.commit(fc.delete_door_type(doc, j9))
    assert [op.op for op in tx.ops] == ["table.edit", "window_type.delete"]
    assert tb.read_state(windows)["types"] == [casa.j1.GlobalId]


def test_tb08_csv(casa, tmp_path):
    result = tb.compute(casa.doc, _table(casa, "areas"))
    path = tmp_path / "areas.csv"
    export.write_csv(str(path), result)
    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    lines = raw.decode("utf-8-sig").split("\r\n")
    assert lines[0] == "Número;Nome do ambiente;Área útil (m²);Perímetro (m)"
    assert lines[1].startswith("01;Sala;") and "," in lines[1].split(";")[2]
    assert any(line.startswith("Subtotal Térreo;;") for line in lines)
    assert any(line.startswith("Área construída Térreo;;40,00") for line in lines)
    assert lines[-2].startswith("Total;;")


def _read_xlsx(data: bytes) -> list[list]:
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(__import__("io").BytesIO(data)) as z:
        names = set(z.namelist())
        assert {"[Content_Types].xml", "_rels/.rels", "xl/workbook.xml",
                "xl/_rels/workbook.xml.rels", "xl/worksheets/sheet1.xml", "xl/styles.xml",
                "xl/sharedStrings.xml"} <= names
        for name in names:
            ElementTree.fromstring(z.read(name))  # todo XML bem formado
        strings = [si.find("m:t", ns).text for si in
                   ElementTree.fromstring(z.read("xl/sharedStrings.xml"))]
        sheet = ElementTree.fromstring(z.read("xl/worksheets/sheet1.xml"))
    rows = []
    for row in sheet.find("m:sheetData", ns):
        values = []
        for c in row:
            v = c.find("m:v", ns).text
            values.append(strings[int(v)] if c.get("t") == "s" else float(v))
        rows.append(values)
    return rows


def test_tb09_xlsx(casa, tmp_path):
    result = tb.compute(casa.doc, _table(casa, "fillings"))
    path = tmp_path / "esquadrias.xlsx"
    export.write_xlsx(str(path), result)
    rows = _read_xlsx(path.read_bytes())
    assert rows[0] == [c.title for c in result.columns]
    assert rows[1][0] == "J1" and rows[1][2] == pytest.approx(1.2) and rows[1][5] == 3
    assert isinstance(rows[1][2], float)  # número, não texto
    assert rows[-1][0] == "Total" and rows[-1][-1] == 6
    assert len(rows) == len(result.rows) + 1
    assert export.sheet_name("Quadro: térreo/1º [rev]") == "Quadro  térreo 1º  rev"


def test_tb11_assistente(casa):
    ctx = tools.Context(casa.doc, casa.commit, casa.terreo.GlobalId)
    reg = tools.default_registry()
    out = reg.call(ctx, "table", {"category": "fillings", "columns": ["code", "count"],
                                  "group_by": "type"})
    assert not out["isError"]
    data = json.loads(out["content"][0]["text"])
    counts = {r["code"]: r["count"] for r in data["linhas"] if r["linha"] == "group"}
    assert counts == {"P1": 2, "J1": 3, "J2": 1}
    out = reg.call(ctx, "table", {"category": "walls", "columns": ["side_area"],
                                  "storeys": ["Térreo"]})
    rows = json.loads(out["content"][0]["text"])["linhas"]
    assert rows[-1]["linha"] == "total" and rows[-1]["side_area"] > 0
    assert not reg.tools["table"].changes
