# SPDX-License-Identifier: LGPL-3.0-or-later
"""Janela (``spec/elementos/janela.md`` §9): JA01 a JA14."""

import json

import ifcopenshell
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.util.element as ue
import ifcopenshell.util.placement
import ifcopenshell.validate
import numpy as np
import pytest
from conftest import PROJECT_ID, Model, snapshot
from test_divisao_e_importacao import _foreign_ifc

from brasbim.core.document import Document, OpError
from brasbim.core.fillings import commands as fc
from brasbim.core.fillings import doors, geometry, params, window_types
from brasbim.core.ops import History, Transaction
from brasbim.core.walls import commands as cmd

T = 0.14


def _window_type(model, name="J1", partitioning="DOUBLE_PANEL_VERTICAL", operations=None,
                 **options):
    tx = model.commit(fc.create_window_type(model.doc, name, partitioning, operations,
                                            **options))
    return model.doc.get(tx.ops[0].id)


def _window(model, wall, distance=1.5, window_type=None, **options):
    window_type = window_type or _window_type(model)
    tx = model.commit(fc.create_window(model.doc, window_type, wall, distance, **options))
    return next(model.doc.get(op.id) for op in tx.ops if op.op == "window.create")


def _world(element):
    return ifcopenshell.util.placement.get_local_placement(element.ObjectPlacement)


def _body(element):
    (body,) = [r for r in element.Representation.Representations
               if r.RepresentationIdentifier == "Body"]
    return body


def test_ja01_janela_no_vao(model, tmp_path):
    wall = model.wall()
    window = _window(model, wall)
    ifc = model.reopen(tmp_path)
    (w,) = ifc.by_type("IfcWindow")
    (o,) = ifc.by_type("IfcOpeningElement")
    assert w.GlobalId == window.GlobalId
    assert (w.OverallWidth, w.OverallHeight) == pytest.approx((1.2, 1.0))
    m_wall = ifcopenshell.util.placement.get_local_placement(
        ifc.by_guid(wall.GlobalId).ObjectPlacement)
    local = np.linalg.inv(m_wall) @ ifcopenshell.util.placement.get_local_placement(
        o.ObjectPlacement)[:, 3]
    assert local[0] == pytest.approx(1.5) and local[2] == pytest.approx(1.10)
    (voids,) = ifc.by_type("IfcRelVoidsElement")
    (fills,) = ifc.by_type("IfcRelFillsElement")
    assert voids.RelatedOpeningElement == o
    assert fills.RelatingOpeningElement == o and fills.RelatedBuildingElement == w
    assert ue.get_container(w).GlobalId == model.terreo.GlobalId


def test_ja02_tipo(model, tmp_path):
    _window(model, model.wall())
    ifc = model.reopen(tmp_path)
    (t,) = ifc.by_type("IfcWindowType")
    (w,) = ifc.by_type("IfcWindow")
    assert (t.PredefinedType, t.PartitioningType) == ("WINDOW", "DOUBLE_PANEL_VERTICAL")
    assert t.ParameterTakesPrecedence is True
    assert w.PredefinedType is None and w.PartitioningType is None
    (lining,) = [p for p in t.HasPropertySets if p.is_a("IfcWindowLiningProperties")]
    assert lining.LiningDepth == pytest.approx(0.05)
    assert lining.FirstMullionOffset == pytest.approx(0.5)
    assert lining.SecondMullionOffset is None
    panels = [p for p in t.HasPropertySets if p.is_a("IfcWindowPanelProperties")]
    assert [(p.PanelPosition, p.OperationType) for p in panels] == [
        ("LEFT", "SLIDINGHORIZONTAL"), ("RIGHT", "SLIDINGHORIZONTAL")]
    material = ue.get_material(t)
    assert [c.Name for c in material.MaterialConstituents] == ["Lining", "Framing", "Glazing"]


def test_ja03_maxim_ar_para_a_direita(model):
    wall = model.wall(ref_line="axis")
    maxim = _window_type(model, "J3", "SINGLE_PANEL", ["TOPHUNG"],
                         defaults={"width": 0.6, "height": 0.6, "base": 1.5})
    window = _window(model, wall, window_type=maxim, opens_to="right")
    (t,) = [p for p in maxim.HasPropertySets if p.is_a("IfcWindowPanelProperties")]
    assert maxim.PartitioningType == "SINGLE_PANEL" and t.OperationType == "TOPHUNG"
    assert np.dot(_world(window)[:3, 1], _world(wall)[:3, 1]) == pytest.approx(-1)


def test_ja04_profile(model):
    window = _window(model, model.wall())
    (rep,) = [r for r in window.Representation.Representations
              if r.RepresentationIdentifier == "Profile"]
    points = [p.Coordinates for p in rep.Items[0].Points]
    assert points[:4] == [(0, 0, 0), (1.2, 0, 0), (1.2, 0, 1.0), (0, 0, 1.0)]


def _lining_y(window):
    """Faixa em y (no sistema da parede) ocupada pelo marco da janela."""
    wall_m = _world(window.FillsVoids[0].RelatingOpeningElement.VoidsElements[0]
                    .RelatingBuildingElement)
    m = np.linalg.inv(wall_m) @ _world(window)
    ys = []
    for item in _body(window).Items[:1]:  # marco esquerdo
        p = item.SweptArea.Position.Location.Coordinates
        half = item.SweptArea.YDim / 2
        for y in (p[1] - half, p[1] + half):
            ys.append((m @ np.array([p[0], y, 0, 1]))[1])
    return min(ys), max(ys)


def test_ja05_marco_fixo_e_centrado(model):
    wall = model.wall()  # face esquerda: faixa y de -0,14 a 0
    window = _window(model, wall)
    gid = window.GlobalId
    assert _lining_y(window) == pytest.approx((-0.095, -0.045))
    model.commit(cmd.create_wall_type(model.doc, "Bloco 19", [{"material": "B",
                                                               "thickness": 0.19}]))
    t19 = next(t for t in model.doc.ifc.by_type("IfcWallType") if t.Name == "Bloco 19")
    model.commit(cmd.edit_wall(model.doc, wall, type=t19))
    assert _lining_y(model.doc.get(gid)) == pytest.approx((-0.12, -0.07))


def test_ja06_marco_mais_profundo_avisa(model, caplog):
    deep = _window_type(model, lining={"depth": 0.20})
    _window(model, model.wall(), window_type=deep)
    assert "mais profundo que a parede" in caplog.text
    assert model.doc.ifc.by_type("IfcWindow")


def test_ja07_variante_de_mao(model):
    wall = model.wall()
    one = _window_type(model, "J7", "SINGLE_PANEL", ["SIDEHUNGLEFTHAND"])
    assert window_types.hand(window_types.read(one)) == "left"
    window = _window(model, wall, window_type=one)
    model.commit(fc.flip_hinges(model.doc, window))
    variant = ue.get_type(window)
    assert variant != one and variant.Name == "J7 (D)"
    (panel,) = [p for p in variant.HasPropertySets if p.is_a("IfcWindowPanelProperties")]
    assert panel.OperationType == "SIDEHUNGRIGHTHAND"
    second = _window(model, wall, 3.0, window_type=one, hinges="right")
    assert ue.get_type(second) == variant
    assert len(model.doc.ifc.by_type("IfcWindowType")) == 2
    assert window_types.read(variant)["code"] == "J7"

    two = _window_type(model, "J5", "DOUBLE_PANEL_VERTICAL",
                       ["SIDEHUNGLEFTHAND", "SIDEHUNGRIGHTHAND"])
    assert window_types.hand(window_types.read(two)) is None
    with pytest.raises(OpError):
        fc.flip_hinges(model.doc, _window(model, model.wall((0, 3), (5, 3)), window_type=two))


def test_ja08_peitoril(model):
    wall = model.wall()
    window = _window(model, wall)
    tx = model.commit(fc.edit_window(model.doc, window, base=1.30))
    assert [op.op for op in tx.ops] == ["opening.edit"]
    assert tx.ops[0].after == {"sill": 1.30}
    with pytest.raises(OpError):
        fc.edit_window(model.doc, window, base=2.0)  # verga 3,00 > 2,80


def test_ja09_quantidades(model):
    q = ue.get_pset(_window(model, model.wall()), "Qto_WindowBaseQuantities")
    assert q["Area"] == pytest.approx(1.2) and q["Perimeter"] == pytest.approx(4.4)


def test_ja10_pset_comum(model):
    window = _window(model, model.wall())
    common = ue.get_pset(window, "Pset_WindowCommon")
    assert common["Status"] == ["NEW"] and common["IsExternal"] is True
    assert common["Reference"] == "J1"
    coded = _window_type(model, "J2 – correr 150", code="J2")
    other = _window(model, model.wall((0, 3), (5, 3)), window_type=coded)
    assert ue.get_pset(other, "Pset_WindowCommon")["Reference"] == "J2"
    assert doors.read_state(other)["common"] == {}


def test_ja11_excluir_parede_com_porta_e_janela(model):
    a = model.wall((0, 0), (5, 0))
    model.wall((5, 0), (5, 4))
    door_type = model.doc.get(model.commit(fc.create_door_type(model.doc, "P1")).ops[0].id)
    model.commit(fc.create_door(model.doc, door_type, a, 0.3))
    _window(model, a, 2.5)
    before = snapshot(model.doc.ifc)
    tx = model.commit(cmd.delete_wall(model.doc, a))
    assert "window.delete" in [op.op for op in tx.ops]
    for cls in ("IfcDoor", "IfcWindow", "IfcOpeningElement", "IfcRelFillsElement",
                "IfcRelVoidsElement"):
        assert not model.doc.ifc.by_type(cls), cls
    model.history.undo()
    assert snapshot(model.doc.ifc) == before


def _session(m: Model):
    wall = m.wall()
    j1 = _window_type(m)
    window = _window(m, wall, window_type=j1)
    m.commit(fc.edit_window(m.doc, window, opens_to="right", align="right_face", offset=0.01))
    triple = window_types.with_partitioning(window_types.read(j1), "TRIPLE_PANEL_VERTICAL")
    m.commit(fc.edit_window_type(m.doc, j1, **{k: triple[k] for k in
                                               ("partitioning", "lining", "panels")}))
    one = _window_type(m, "J7", "SINGLE_PANEL", ["SIDEHUNGLEFTHAND"])
    other = _window(m, wall, 3.2, window_type=one, hinges="right", width=0.8)
    m.commit(fc.edit_window(m.doc, other, base=1.2))
    m.commit(fc.delete_window(m.doc, window))


def test_ja12_desfazer_refazer_e_reaplicar(model):
    start_state = snapshot(model.doc.ifc)
    start = len(model.history.undo_stack)
    _session(model)
    count = len(model.history.undo_stack) - start
    ops = {op.op for tx in model.history.journal for op in tx.ops}
    assert {"window_type.create", "window_type.edit", "window.create", "window.edit",
            "window.delete"} <= ops
    for _ in range(count):
        model.history.undo()
    assert snapshot(model.doc.ifc) == start_state
    for _ in range(count):
        model.history.redo()
    final = snapshot(model.doc.ifc)
    journal = json.loads(json.dumps([tx.to_dict() for tx in model.history.journal]))
    other = Document.new(project_id=PROJECT_ID)
    history = History(other)
    for tx in journal:
        history.commit(Transaction.from_dict(tx))
    assert snapshot(other.ifc) == final


def _foreign_window_ifc(path):
    """Janela montada direto no IfcOpenShell, com corpo próprio e sem Psets do BrasBim."""
    wall_id = _foreign_ifc(path)
    f = ifcopenshell.open(str(path))
    wall = f.by_guid(wall_id)
    storey = ue.get_container(wall)
    body_ctx = next(c for c in f.by_type("IfcGeometricRepresentationSubContext")
                    if c.ContextIdentifier == "Body")

    def axis(origin, z=None, x=None):
        return f.createIfcAxis2Placement3D(
            f.createIfcCartesianPoint(origin), z and f.createIfcDirection(z),
            x and f.createIfcDirection(x))

    def box(origin, xdim, ydim, depth, position=None):
        profile = f.createIfcRectangleProfileDef(
            "AREA", None, f.createIfcAxis2Placement2D(f.createIfcCartesianPoint(origin), None),
            xdim, ydim)
        return f.createIfcExtrudedAreaSolid(profile, position or axis((0.0, 0.0, 0.0)),
                                            f.createIfcDirection((0.0, 0.0, 1.0)), depth)

    opening = ifcopenshell.api.root.create_entity(f, ifc_class="IfcOpeningElement")
    opening.PredefinedType = "OPENING"
    opening.ObjectPlacement = f.createIfcLocalPlacement(wall.ObjectPlacement,
                                                        axis((1.0, 0.0, 1.0)))
    hole = box((0.5, 0.5), 1.0, 1.0, 0.3,
               axis((0.0, 0.25, 0.0), (0.0, -1.0, 0.0), (1.0, 0.0, 0.0)))
    opening.Representation = f.createIfcProductDefinitionShape(None, None, [
        f.createIfcShapeRepresentation(body_ctx, "Body", "SweptSolid", [hole])])
    f.createIfcRelVoidsElement(ifcopenshell.guid.new(), None, None, None, wall, opening)
    window = ifcopenshell.api.root.create_entity(f, ifc_class="IfcWindow", name="Janela X")
    window.PredefinedType = "WINDOW"
    window.PartitioningType = "SINGLE_PANEL"
    window.OverallWidth, window.OverallHeight = 1.0, 1.0
    window.ObjectPlacement = f.createIfcLocalPlacement(opening.ObjectPlacement,
                                                       axis((0.0, 0.05, 0.0)))
    pane = box((0.5, 0.02), 1.0, 0.04, 1.0)
    window.Representation = f.createIfcProductDefinitionShape(None, None, [
        f.createIfcShapeRepresentation(body_ctx, "Body", "SweptSolid", [pane])])
    f.createIfcRelFillsElement(ifcopenshell.guid.new(), None, None, None, opening, window)
    ifcopenshell.api.spatial.assign_container(f, products=[window], relating_structure=storey)
    pset = ifcopenshell.api.pset.add_pset(f, product=window, name="Pset_WindowCommon")
    ifcopenshell.api.pset.edit_pset(f, pset=pset, properties={"Reference": "JX"})
    f.write(str(path))
    return window.GlobalId


def test_ja13_janela_de_outra_origem(tmp_path):
    src = tmp_path / "outro.ifc"
    gid = _foreign_window_ifc(src)
    doc = Document.open(str(src))
    history = History(doc)
    window = doc.get(gid, "IfcWindow")
    state = doors.read_state(window)
    assert state["foreign"]["operation_type"] == "SINGLE_PANEL"
    assert state["common"] == {"Reference": "JX"}
    body = _body(window).Items[0].SweptArea.XDim
    start = _world(window)
    tx = fc.edit_window(doc, window, distance=2.0)
    assert [op.op for op in tx.ops] == ["opening.edit"]
    history.commit(tx)
    window = doc.get(gid)
    assert _body(window).Items[0].SweptArea.XDim == body
    assert (_world(window) @ np.linalg.inv(start))[:3, 3] == pytest.approx((1.0, 0, 0))
    # Mudar o tamanho converte em janela paramétrica; desfazer volta o corpo de origem.
    history.commit(fc.edit_window(doc, window, width=1.2))
    window = doc.get(gid)
    assert doors.is_parametric(window) and window.OverallWidth == pytest.approx(1.2)
    assert ue.get_type(window).is_a("IfcWindowType")
    history.undo()
    window = doc.get(gid)
    assert not doors.is_parametric(window)
    assert _body(window).Items[0].SweptArea.XDim == body


def test_ja14_validacao(model, tmp_path):
    wall = model.wall()
    _window(model, wall)
    _window(model, wall, 3.2, window_type=_window_type(
        model, "J3", "SINGLE_PANEL", ["TOPHUNG"],
        defaults={"width": 0.6, "height": 0.6, "base": 1.5}), opens_to="right")
    ifc = model.reopen(tmp_path)
    log = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifc, log)
    assert log.statements == []


# --- corpo e estilos (janela §6.2; spec/ui 09 §7) -----------------------------------------


def test_corpo_correr_dois_trilhos_sobrepostos():
    state = window_types.default_state("DOUBLE_PANEL_VERTICAL")
    parts = geometry.window_parts(1.2, 1.0, state)
    roles = [r for _, r in parts]
    assert roles.count("lining") == 4  # sem montante entre caixilhos de correr
    glass = [b for b, r in parts if r == "glazing"]
    assert len(glass) == 2
    (_, l1, ly0, ly1, *_), (r0, _, ry0, ry1, *_) = glass
    ft = params.DEFAULT_WINDOW_FRAME["frame_thickness"]
    assert l1 + ft > r0 - ft  # caixilhos sobrepostos na largura do montante
    assert ly1 <= ry0 or ry1 <= ly0  # trilhos diferentes


def test_corpo_tres_caixilhos_com_montantes():
    state = window_types.with_partitioning(window_types.default_state(), "TRIPLE_PANEL_VERTICAL")
    state["panels"] = [{**p, "operation": "FIXEDCASEMENT"} for p in state["panels"]]
    parts = geometry.window_parts(1.5, 1.2, state)
    assert [r for _, r in parts].count("lining") == 6  # marco + 2 montantes
    assert len([b for b, r in parts if r == "glazing"]) == 3


def test_pecas_com_estilo_do_material(model):
    window = _window(model, model.wall())
    items = _body(window).Items
    styles = {}
    for item in items:
        (styled,) = [i for i in model.doc.ifc.get_inverse(item) if i.is_a("IfcStyledItem")]
        styles[styled.Styles[0].Name] = styled.Styles[0]
    assert set(styles) == {"Alumínio", "Vidro"}
    shading = styles["Vidro"].Styles[0]
    assert shading.Transparency == pytest.approx(0.6)
    # Editar o tipo refaz o corpo sem deixar estilos soltos.
    count = len(model.doc.ifc.by_type("IfcStyledItem"))
    model.commit(fc.edit_window_type(model.doc, ue.get_type(window),
                                     defaults={"width": 1.0, "height": 1.0, "base": 1.0}))
    model.commit(fc.edit_window(model.doc, window, width=1.0))
    assert len(model.doc.ifc.by_type("IfcStyledItem")) == count


def test_mao_e_espelho_dos_caixilhos():
    lining = params.default_window_lining("TRIPLE_PANEL_VERTICAL")
    panels = params.default_window_panels("TRIPLE_PANEL_VERTICAL",
                                          ["SIDEHUNGLEFTHAND", "FIXEDCASEMENT", "FIXEDCASEMENT"])
    assert params.window_hand("TRIPLE_PANEL_VERTICAL", lining, panels) == "left"
    _, mirrored = params.mirror_window("TRIPLE_PANEL_VERTICAL", lining, panels)
    assert [(p["position"], p["operation"]) for p in mirrored] == [
        ("LEFT", "FIXEDCASEMENT"), ("MIDDLE", "FIXEDCASEMENT"), ("RIGHT", "SIDEHUNGRIGHTHAND")]


def test_mover_copiar_e_espelhar_com_janela(model):
    from brasbim.core import transform

    wall = model.wall()
    one = _window_type(model, "J7", "SINGLE_PANEL", ["SIDEHUNGLEFTHAND"])
    window = _window(model, wall, window_type=one)
    model.commit(transform.copy_elements(model.doc, [wall.GlobalId], (0, 3)))
    assert len(model.doc.ifc.by_type("IfcWindow")) == 2
    model.commit(transform.move_elements(model.doc, [window.GlobalId], (1.0, 0)))
    o = fc.opening_of(model.doc.get(window.GlobalId))
    assert o.ObjectPlacement is not None
    model.commit(transform.mirror_elements(model.doc, [wall.GlobalId], (10, 0), (10, 1)))
    assert ue.get_type(model.doc.get(window.GlobalId)).Name == "J7 (D)"
    with pytest.raises(OpError, match="janela"):
        transform.mirror_elements(model.doc, [window.GlobalId], (10, 0), (10, 1))
