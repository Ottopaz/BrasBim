# SPDX-License-Identifier: GPL-3.0-or-later
"""Painel Assistente (spec/ui 16 §5), com o Qt sem tela e sem chamar IA nenhuma."""

import os
import threading

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from brasbim.ui.assistant import ClaudeCode, plan_image


def _from_thread(app, fn):
    """Chama ``fn`` noutra thread (como o servidor MCP) enquanto a interface roda."""
    box = {}
    thread = threading.Thread(target=lambda: box.setdefault("value", fn()))
    thread.start()
    while thread.is_alive():
        app.processEvents()
    return box["value"]


def test_as07_ferramenta_vinda_do_servidor_roda_na_interface(app, window):
    s, a = window.session, window.assistant
    n = len(s.history.undo_stack)
    a._prompt = "um quarto com porta"
    r1 = _from_thread(app, lambda: a._call_from_server("layout_rooms", {"rooms": [
        {"name": "Quarto", "x": 0, "y": 0, "width": 4, "depth": 3}]}))
    r2 = _from_thread(app, lambda: a._call_from_server("insert_door", {"at": [2, 0]}))
    r3 = _from_thread(app, lambda: a._call_from_server("insert_door", {"at": [9, 9]}))
    assert not r1["isError"] and not r2["isError"] and r3["isError"]
    assert len(s.doc.ifc.by_type("IfcWall")) == 4
    texts = [a.log.item(i).text() for i in range(a.log.count())]
    assert any("Desenhando os ambientes" in t for t in texts)
    assert any(t.startswith("✗") and "nenhuma parede" in t for t in texts)
    a._group()
    assert len(s.history.undo_stack) == n + 1
    assert s.history.undo_stack[-1].label == "Assistente: um quarto com porta"
    window.undo()
    assert not s.doc.ifc.by_type("IfcWall") and not s.doc.ifc.by_type("IfcSpace")


def test_as08_eventos_do_claude_code(window):
    a = window.assistant
    a.handle_event({"type": "system", "subtype": "init", "model": "m",
                    "mcp_servers": [{"name": "brasbim", "status": "failed"}]})
    a.handle_event({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "mcp__brasbim__describe_model"},
        {"type": "text", "text": "Pronto: sala de 20 m²."}]}})
    a.handle_event({"type": "result", "is_error": False, "duration_ms": 12000})
    texts = [a.log.item(i).text() for i in range(a.log.count())]
    assert "não conectou" in texts[0]
    assert texts[1] == "Pronto: sala de 20 m²."
    assert texts[2] == "Concluído em 12 s."


def test_as09_imagem_da_planta(window):
    s = window.session
    tool = window.assistant.registry.tools["view_plan"]
    from brasbim.core.assistant.tools import Context

    window.assistant.execute("create_walls", {"walls": [{"start": [0, 0], "end": [4, 0]}]})
    png, info = plan_image(s.doc, s.storey, 600)
    assert png.startswith(b"\x89PNG") and info["pixels_por_metro"] > 0
    out = tool.fn(Context(s.doc, s.history.commit, s.storey_id), {})
    assert out[0]["type"] == "image" and out[0]["mimeType"] == "image/png"


def test_as10_claude_code_so_com_as_ferramentas_do_brasbim():
    args = ClaudeCode(program="claude").arguments("cfg.json")
    assert args[args.index("--tools") + 1] == ""  # sem terminal nem arquivos
    assert "--strict-mcp-config" in args
    assert args[args.index("--mcp-config") + 1] == "cfg.json"
    assert args[args.index("--allowedTools") + 1] == "mcp__brasbim"
    assert ClaudeCode(program=None).available is False


def test_as10_painel_no_menu_exibir(window):
    panels = window.panels_menu.actions()
    for dock in (window.project_dock, window.properties_dock, window.messages_dock,
                 window.assistant_dock):
        assert dock.toggleViewAction() in panels
    assert not window.assistant_dock.isVisible()  # fechado até ser pedido


# AS13: memória entre pedidos, contexto da tela e seleção do que mudou


def test_as13_conversa_continua_e_recomeca(window):
    a = window.assistant
    assert "--resume" not in ClaudeCode(program="claude").arguments("c.json")
    assert ClaudeCode(program="claude").arguments("c.json", "abc")[-2:] == ["--resume", "abc"]
    a.handle_event({"type": "system", "subtype": "init", "session_id": "abc"})
    assert a.conversation == "abc"
    a._idle_status()
    assert a.new_button.isEnabled() and "continuando" in a.status.text()
    a.new_conversation()
    assert a.conversation is None and not a.new_button.isEnabled()
    a.handle_event({"type": "result", "session_id": "xyz", "duration_ms": 0})
    window.session.new()  # outro projeto: a conversa não passa adiante
    assert a.conversation is None and a.log.count() == 0


def test_as13_contexto_e_selecao_do_que_mudou(app, window):
    s, a = window.session, window.assistant
    a._prompt = "sala"
    _from_thread(app, lambda: a._call_from_server("layout_rooms", {"rooms": [
        {"name": "Sala", "x": 0, "y": 0, "width": 4, "depth": 3}]}))
    wall = next(w for w in s.doc.ifc.by_type("IfcWall"))
    s.select([wall.GlobalId])
    assert f"parede {wall.GlobalId}" in a.context_note()
    _from_thread(app, lambda: a._call_from_server("move_wall", {
        "id": wall.GlobalId, "distance": 0.5, "toward": [2, -5]}))
    a._group()
    kinds = {s.doc.find(g).is_a() for g in s.selection}
    assert kinds == {"IfcWall", "IfcSpace"}  # paredes e o ambiente, sem aberturas
    assert len([g for g in s.selection if s.doc.find(g).is_a("IfcWall")]) == 4


# AS14: trocar de pavimento pelo teclado


def test_as14_page_up_e_page_down(window):
    s = window.session
    terreo, superior = s.doc.storeys()
    assert s.storey == terreo
    window.step_storey(1)
    assert s.storey == superior
    window.step_storey(1)  # não passa do último
    assert s.storey == superior
    window.step_storey(-1)
    assert s.storey == terreo
    shortcuts = {a.text(): a.shortcut().toString() for a in window.menuBar().actions()[2]
                 .menu().actions()}
    assert shortcuts["Pavimento acima"] == "PgUp"
    assert shortcuts["Pavimento abaixo"] == "PgDown"
