# SPDX-License-Identifier: LGPL-3.0-or-later
"""Assistente (spec/ui 16): ferramentas no núcleo, planta por ambientes e servidor MCP."""

import json
import urllib.error
import urllib.request

import pytest
from conftest import snapshot

from brasbim.core.annotations import spaces
from brasbim.core.assistant import layout, mcp
from brasbim.core.assistant.tools import Context, default_registry
from brasbim.core.fillings import commands as fc
from brasbim.core.fillings import doors
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import openings


@pytest.fixture
def ctx(model):
    model.commit(fc.create_door_type(model.doc, "P1 – giro 80", defaults={"width": 0.86}))
    model.commit(fc.create_window_type(model.doc, "J1 – correr 120", code="J1",
                                       defaults={"width": 1.2, "height": 1.0, "base": 1.1}))
    return Context(model.doc, model.commit, model.terreo.GlobalId)


def _call(ctx, tool, **args):
    result = default_registry().call(ctx, tool, args)
    text = result["content"][0]["text"]
    return (json.loads(text) if not result["isError"] else text), result["isError"]


def _rooms():
    return layout.rooms_from([
        {"name": "Sala", "x": 0, "y": 0, "width": 5, "depth": 4},
        {"name": "Cozinha", "x": 5, "y": 0, "width": 3, "depth": 4},
        {"name": "Quarto", "x": 0, "y": 4, "width": 8, "depth": 3},
    ])


# AS01: bordas comuns viram uma parede só; trechos alinhados se juntam


def test_as01_bordas_comuns_uma_vez():
    segs = layout.segments(_rooms())
    ext = [s for s in segs if s.kind == "exterior"]
    inner = [s for s in segs if s.kind == "interior"]
    assert {(s.start, s.end) for s in inner} == {((0, 4), (8, 4)), ((5, 0), (5, 4))}
    assert len(ext) == 4  # o contorno 8 × 7, sem pedaços
    assert ((0, 0), (8, 0)) in {(s.start, s.end) for s in ext}


def test_as01_cozinha_integrada_sem_parede():
    segs = layout.segments(_rooms(), open_between=[("Sala", "Cozinha")])
    assert all(not (s.start[0] == 5 and s.end[0] == 5) for s in segs)


def test_as01_sobreposicao_recusada():
    with pytest.raises(Exception, match="se sobrepõem"):
        layout.rooms_from([{"name": "A", "x": 0, "y": 0, "width": 4, "depth": 4},
                           {"name": "B", "x": 3, "y": 0, "width": 4, "depth": 4}])


# AS02: layout_rooms cria paredes pelo eixo, junções e ambientes com a área útil


def test_as02_planta_por_ambientes(ctx, model):
    out, error = _call(ctx, "layout_rooms", rooms=[
        {"name": "Sala", "x": 0, "y": 0, "width": 5, "depth": 4},
        {"name": "Cozinha", "x": 5, "y": 0, "width": 3, "depth": 4},
        {"name": "Quarto", "x": 0, "y": 4, "width": 8, "depth": 3}])
    assert not error
    assert len(out["paredes"]) == 6
    walls = model.doc.ifc.by_type("IfcWall")
    assert len(walls) == 6
    assert len(model.doc.ifc.by_type("IfcRelConnectsPathElements")) >= 6
    areas = {r["nome"]: r["area_util"] for r in out["ambientes"]}
    assert areas["Sala"] == pytest.approx((5 - 0.14) * (4 - 0.14), abs=1e-3)
    assert {s.LongName for s in model.doc.ifc.by_type("IfcSpace")} == {"Sala", "Cozinha",
                                                                        "Quarto"}
    space = next(s for s in model.doc.ifc.by_type("IfcSpace") if s.LongName == "Quarto")
    assert spaces.area(spaces.read_state(space)["outline"]) == pytest.approx(
        (8 - 0.14) * (3 - 0.14), abs=1e-3)
    assert out["area_construida"] == pytest.approx(8.14 * 7.14, abs=1e-3)


# AS03: porta e janela pelo centro, na parede certa, abrindo para o lado pedido


def test_as03_porta_pelo_centro(ctx, model):
    _call(ctx, "layout_rooms", rooms=[{"name": "Quarto", "x": 0, "y": 0, "width": 4,
                                       "depth": 3}])
    out, error = _call(ctx, "insert_door", at=[2, 0], type="P1", opens_toward=[2, 1.5])
    assert not error
    door = model.doc.get(out["id"])
    opening = door.FillsVoids[0].RelatingOpeningElement
    state = openings.read_state(opening)
    assert state["distance"] + state["width"] / 2 == pytest.approx(2.0)
    assert state["width"] == pytest.approx(0.86)
    win, error = _call(ctx, "insert_window", at=[4, 1.5], type="J1", sill=1.2)
    assert not error
    o = openings.read_state(model.doc.get(win["id"]).FillsVoids[0].RelatingOpeningElement)
    assert o["sill"] == pytest.approx(1.2)


def test_as03_lado_da_folha(ctx, model):
    _call(ctx, "create_walls", walls=[{"start": [0, 0], "end": [4, 0]}])
    a, _ = _call(ctx, "insert_door", at=[2, 0], opens_toward=[2, 1])
    b, _ = _call(ctx, "insert_door", at=[3.2, 0], opens_toward=[3.2, -1])
    sa = doors.read_state(model.doc.get(a["id"]))["opens_to"]
    sb = doors.read_state(model.doc.get(b["id"]))["opens_to"]
    assert sa == "left" and sb == "right"  # +y fica à esquerda da parede de x crescente


def test_as03_recusas_voltam_como_erro(ctx, model):
    _call(ctx, "create_walls", walls=[{"start": [0, 0], "end": [4, 0]}])
    n = len(model.history.undo_stack)
    text, error = _call(ctx, "insert_door", at=[10, 10])
    assert error and "nenhuma parede" in text
    text, error = _call(ctx, "insert_door", at=[2, 0], type="Inexistente")
    assert error and "P1" in text  # lista os tipos que há
    text, error = _call(ctx, "create_walls", walls=[{"start": [0, 0]}])
    assert error and "argumentos inválidos" in text
    assert len(model.history.undo_stack) == n  # recusa não entra no histórico


# AS04: o pedido inteiro vira um passo de desfazer


def test_as04_um_passo_de_desfazer(ctx, model):
    before = snapshot(model.doc.ifc)
    n = len(model.history.undo_stack)
    _call(ctx, "layout_rooms", rooms=[{"name": "Sala", "x": 0, "y": 0, "width": 4,
                                       "depth": 3}])
    _call(ctx, "insert_door", at=[2, 0])
    _call(ctx, "create_slab", outline=[[0, 0], [4, 0], [4, 3], [0, 3]])
    after = snapshot(model.doc.ifc)
    count = len(model.history.undo_stack) - n
    tx = model.history.squash(count, "Assistente: sala")
    assert tx is not None and len(model.history.undo_stack) == n + 1
    model.history.undo()
    assert snapshot(model.doc.ifc) == before
    model.history.redo()
    assert snapshot(model.doc.ifc) == after


def test_as04_excluir_e_descrever(ctx, model):
    out, _ = _call(ctx, "create_walls", walls=[{"start": [0, 0], "end": [4, 0]}])
    _call(ctx, "insert_window", at=[2, 0], type="J1")
    info, _ = _call(ctx, "describe_model")
    assert info["paredes"][0]["inicio"] == [0, 0] and info["paredes"][0]["fim"] == [4, 0]
    assert info["esquadrias"][0]["centro"] == [2, 0]
    assert "Alvenaria 14 (14 cm)" in info["tipos"]["parede"]
    gone, error = _call(ctx, "delete_elements", ids=out["paredes"])
    assert not error and gone["janelas_junto"] == 1
    assert not model.doc.ifc.by_type("IfcWall") and not model.doc.ifc.by_type("IfcWindow")


# AS05: protocolo MCP (JSON-RPC)


def _handler(ctx):
    reg = default_registry()
    return mcp.Handler(reg.specs, lambda name, args: reg.call(ctx, name, args))


def test_as05_protocolo(ctx):
    h = _handler(ctx)
    init = h.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                     "params": {"protocolVersion": "2025-03-26"}})
    assert init["result"]["protocolVersion"] == "2025-03-26"
    assert "tools" in init["result"]["capabilities"]
    assert "EIXO" in init["result"]["instructions"]
    assert h.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    tools = h.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]
    names = {t["name"] for t in tools}
    assert {"describe_model", "layout_rooms", "insert_door", "insert_window"} <= names
    assert all(t["inputSchema"]["type"] == "object" for t in tools)
    call = h.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                     "params": {"name": "describe_model", "arguments": {}}})
    assert call["result"]["isError"] is False
    assert h.handle({"jsonrpc": "2.0", "id": 4, "method": "x"})["error"]["code"] == -32601
    assert h.handle({"id": 5})["error"]["code"] == -32600


# AS06: servidor só aceita quem tem o token e é do próprio PC


def test_as06_servidor_local_com_token(ctx):
    server = mcp.Server(_handler(ctx)).start()
    try:
        assert server.url.startswith("http://127.0.0.1:")

        def post(headers):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}).encode()
            req = urllib.request.Request(server.url, body, {"Content-Type": "application/json",
                                                            **headers})
            try:
                with urllib.request.urlopen(req, timeout=5) as r:
                    return r.status, json.loads(r.read())
            except urllib.error.HTTPError as e:
                return e.code, None

        auth = {"Authorization": f"Bearer {server.token}"}
        assert post({})[0] == 401
        assert post({"Authorization": "Bearer errado"})[0] == 401
        assert post({**auth, "Origin": "http://exemplo.com"})[0] == 401
        status, reply = post(auth)
        assert status == 200 and reply["result"] == {}
        config = server.client_config()["mcpServers"]["brasbim"]
        assert config["type"] == "http" and config["url"] == server.url
    finally:
        server.stop()


def test_as06_criar_paredes_soltas(model):
    tx = cmd.create_walls(model.doc, model.type14, model.terreo,
                          [((0, 0), (4, 0)), ((4, 0), (4, 3))])
    model.commit(tx)
    assert len(model.doc.ifc.by_type("IfcWall")) == 2
    assert len(model.doc.ifc.by_type("IfcRelConnectsPathElements")) == 1


# AS11: edição pela IA


def _casa(ctx):
    out, _ = _call(ctx, "layout_rooms", rooms=[
        {"name": "Sala", "x": 0, "y": 0, "width": 5, "depth": 4},
        {"name": "Quarto", "x": 0, "y": 4, "width": 5, "depth": 3}])
    walls = {(tuple(w["inicio"]), tuple(w["fim"])): w["id"] for w in out["paredes"]}
    rooms = {r["nome"]: r["id"] for r in out["ambientes"]}
    return walls, rooms


def _area(model, gid):
    return spaces.area(spaces.read_state(model.doc.get(gid))["outline"])


def test_as11_deslocar_parede_leva_os_ambientes(ctx, model):
    walls, rooms = _casa(ctx)
    middle = walls[((0, 4), (5, 4))]
    out, error = _call(ctx, "move_wall", id=middle, distance=0.5, toward=[2, 10])
    assert not error
    assert out["inicio"] == [0, 4.5] and out["fim"] == [5, 4.5]
    assert _area(model, rooms["Sala"]) == pytest.approx(4.86 * 4.36, abs=1e-3)
    assert _area(model, rooms["Quarto"]) == pytest.approx(4.86 * 2.36, abs=1e-3)
    # a parede de cima, com as laterais esticando junto
    top = walls[((0, 7), (5, 7))]
    out, _ = _call(ctx, "move_wall", id=top, distance=1, toward=[2, 0])  # para baixo
    assert out["inicio"] == [0, 6] and set(out["paredes_alteradas"]) > {top}
    assert _area(model, rooms["Quarto"]) == pytest.approx(4.86 * 1.36, abs=1e-3)


def test_as11_editar_esquadria(ctx, model):
    walls, _ = _casa(ctx)
    door, _ = _call(ctx, "insert_door", at=[2.5, 0], type="P1", opens_toward=[2.5, 1])
    _call(ctx, "edit_opening", id=door["id"], width=1.0, opens_toward=[2.5, -1])
    o = openings.read_state(model.doc.get(door["id"]).FillsVoids[0].RelatingOpeningElement)
    assert o["width"] == pytest.approx(1.0) and o["distance"] == pytest.approx(2.0)
    assert doors.read_state(model.doc.get(door["id"]))["opens_to"] == "right"
    _, error = _call(ctx, "edit_opening", id=door["id"], at=[0, 2])  # outra parede
    assert not error
    o = openings.read_state(model.doc.get(door["id"]).FillsVoids[0].RelatingOpeningElement)
    assert o["wall"] == walls[((0, 0), (0, 7))] and o["distance"] == pytest.approx(1.5)
    model.commit(fc.create_door_type(model.doc, "P3 – correr", "DOUBLE_DOOR_SLIDING",
                                     defaults={"width": 1.66}))
    _call(ctx, "edit_opening", id=door["id"], type="P3")  # tamanho do tipo novo, mesmo centro
    o = openings.read_state(model.doc.get(door["id"]).FillsVoids[0].RelatingOpeningElement)
    assert o["width"] == pytest.approx(1.66) and o["distance"] == pytest.approx(2.0 - 0.83)
    win, _ = _call(ctx, "insert_window", at=[2.5, 7], type="J1")
    _call(ctx, "edit_opening", id=win["id"], sill=0.9, height=1.2)
    o = openings.read_state(model.doc.get(win["id"]).FillsVoids[0].RelatingOpeningElement)
    assert o["sill"] == pytest.approx(0.9) and o["height"] == pytest.approx(1.2)


def test_as11_tipo_altura_pontas_e_ambiente(ctx, model):
    model.commit(cmd.create_wall_type(model.doc, "Drywall 9,5", [
        {"material": "Gesso", "thickness": 0.095}], predefined_type="PARTITIONING"))
    walls, rooms = _casa(ctx)
    middle = walls[((0, 4), (5, 4))]
    door, _ = _call(ctx, "insert_door", at=[2.5, 0])
    text, error = _call(ctx, "set_type", ids=[middle, door["id"]], type="Drywall")
    assert error and "uma classe por vez" in text
    out, error = _call(ctx, "set_type", ids=[middle], type="Drywall")
    assert not error and out["tipo"] == "Drywall 9,5"
    out, _ = _call(ctx, "edit_space", id=rooms["Sala"], name="Estar", refit=True)
    assert out["nome"] == "Estar"
    assert out["area"] == pytest.approx(4.86 * (4 - 0.07 - 0.0475), abs=1e-3)
    out, _ = _call(ctx, "edit_wall", id=middle, height=2.5)
    from brasbim.core.walls.wall import read_state as read_wall

    state = read_wall(model.doc, model.doc.get(middle))
    assert state["top_mode"] == "fixed" and state["fixed_height"] == pytest.approx(2.5)
    text, error = _call(ctx, "edit_wall", id=middle)
    assert error and "nada a mudar" in text


def test_as11_mover_copiar_girar_espelhar(ctx, model):
    out, _ = _call(ctx, "create_walls", walls=[{"start": [0, 0], "end": [4, 0]}])
    (wall,) = out["paredes"]
    _call(ctx, "move_elements", ids=[wall], vector=[0, 1])
    info, _ = _call(ctx, "describe_model")
    assert info["paredes"][0]["inicio"] == [0, 1]
    copy, _ = _call(ctx, "move_elements", ids=[wall], vector=[0, 2], copy=True)
    assert len(copy["copias"]) == 1 and len(model.doc.ifc.by_type("IfcWall")) == 2
    _call(ctx, "rotate_elements", ids=[wall], center=[0, 1], angle=90)
    _call(ctx, "mirror_elements", ids=copy["copias"], axis_start=[10, 0], axis_end=[10, 1])
    ends = {(tuple(w["inicio"]), tuple(w["fim"])) for w in _call(ctx, "describe_model")[0][
        "paredes"]}
    assert ((0, 1), (0, 5)) in ends
    assert ((16, 3), (20, 3)) in ends  # espelhada em x = 10


# AS12: o pedido leva o pavimento ativo e a seleção


def test_as12_nota_da_selecao(ctx, model):
    from brasbim.core.assistant.tools import selection_note

    walls, rooms = _casa(ctx)
    middle = walls[((0, 4), (5, 4))]
    note = selection_note(model.doc, model.terreo, {middle, rooms["Sala"]})
    assert note.startswith('[BrasBim] Pavimento ativo: "Térreo".')
    assert f"parede {middle}, tipo Alvenaria 14, de [0.0, 4.0] a [5.0, 4.0]" in note
    assert f"ambiente {rooms['Sala']} (Sala)" in note
    assert "Nada selecionado" in selection_note(model.doc, model.terreo, set())
