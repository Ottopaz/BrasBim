# SPDX-License-Identifier: LGPL-3.0-or-later
"""Servidor MCP mínimo (spec/ui 16 §3): JSON-RPC 2.0 sobre HTTP, só no próprio PC.

O Model Context Protocol é aberto (modelcontextprotocol.io). Daqui só precisamos do
lado servidor com ferramentas: ``initialize``, ``tools/list``, ``tools/call`` e
``ping``. O transporte é o "Streamable HTTP" na forma mais simples: cada POST traz uma
mensagem (ou lista) e a resposta volta como ``application/json``; notificações recebem
202 sem corpo.

Segurança: escuta só em 127.0.0.1, exige ``Authorization: Bearer <token>`` (sorteado a
cada abertura) e recusa ``Origin`` que não seja do próprio PC.
"""

from __future__ import annotations

import json
import secrets
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
SERVER_NAME = "brasbim"
PATH = "/mcp"

INSTRUCTIONS = """\
Você está desenhando no BrasBim, um software BIM livre que guarda o modelo em IFC 4.3.
Convenções:
- Unidades em metros; áreas em m². Coordenadas [x, y] no sistema do pavimento, com x
  para a direita (leste) e y para cima (norte) na planta.
- Paredes são dadas pelo EIXO. As dimensões de um cômodo em layout_rooms são de eixo a
  eixo; a área útil (devolvida) já desconta meia parede de cada lado.
- Comece com describe_model para ver pavimentos, tipos e o que já existe. Prefira
  layout_rooms para plantas novas; depois portas (insert_door) e janelas
  (insert_window). Faça só o que foi pedido; num pedido de casa ou edificação
  inteira, inclua também o piso (create_slab com o contorno_externo devolvido).
- Cobertura (create_roof) só quando o pedido fala em telhado ou cobertura, ou é de uma
  edificação inteira. Padrão: duas águas, Telha cerâmica, 30 %, beiral de 60 cm,
  apoiada no contorno externo das paredes (sem outline). Duas e quatro águas só em
  contorno retangular; numa planta em L, use uma água, plana ou uma cobertura por
  retângulo. Para mudar, edit_roof.
- Portas e janelas são postas pelo CENTRO, num ponto sobre o eixo da parede. Deixe ao
  menos 10 cm entre um vão e o canto ou outro vão. Portas abrem para dentro do cômodo
  (opens_toward = um ponto dentro dele).
- Para mudar o que existe, edite em vez de apagar e refazer: move_wall (aumentar ou
  diminuir um cômodo: desloque a parede dele, os ambientes acompanham), edit_wall,
  edit_opening, edit_space, set_type, move_elements, rotate_elements,
  mirror_elements. Os ids vêm de describe_model.
- Cada pedido começa com uma linha "[BrasBim] ..." com o pavimento ativo e o que o
  usuário selecionou na tela: "essa parede", "esta porta" se referem a isso.
- A conversa pode continuar pedidos anteriores, mas o usuário pode ter mudado o
  modelo à mão desde então: releia com describe_model antes de editar.
- Perguntas de quantidade (quantos, quantos m², metros de parede, volume de
  concreto): use table, que lê as quantidades do modelo, em vez de somar à mão
  os dados de describe_model.
- Se uma ferramenta recusar, leia a mensagem e corrija; não repita igual.
- Confira o resultado com describe_model (e view_plan, se houver) antes de terminar.
- A resposta final aparece num painel pequeno, em texto simples: sem Markdown (nada de
  **, #, tabelas). Seja breve: o que foi feito e as áreas, uma linha por item.
"""


class Handler:
    """Despacha mensagens JSON-RPC. ``call_tool(nome, args)`` devolve o resultado MCP
    (``content``, ``isError``) e pode rodar em outra thread (a interface usa isso)."""

    def __init__(self, list_tools: Callable[[], list[dict]],
                 call_tool: Callable[[str, dict], dict], version: str = "0.0.1",
                 instructions: str = INSTRUCTIONS):
        self.list_tools = list_tools
        self.call_tool = call_tool
        self.version = version
        self.instructions = instructions

    def handle(self, message):
        """Resposta (dict, lista ou ``None`` para notificações)."""
        if isinstance(message, list):
            out = [r for r in (self._one(m) for m in message) if r is not None]
            return out or None
        return self._one(message)

    def _one(self, msg) -> dict | None:
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or "method" not in msg:
            return _fail(msg.get("id") if isinstance(msg, dict) else None, -32600,
                         "requisição inválida")
        method, params = msg["method"], msg.get("params") or {}
        if "id" not in msg:
            return None  # notificação (notifications/initialized, cancelled...)
        rid = msg["id"]
        if method == "initialize":
            asked = params.get("protocolVersion")
            version = asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]
            return _ok(rid, {"protocolVersion": version,
                             "capabilities": {"tools": {"listChanged": False}},
                             "serverInfo": {"name": SERVER_NAME, "title": "BrasBim",
                                            "version": self.version},
                             "instructions": self.instructions})
        if method == "ping":
            return _ok(rid, {})
        if method == "tools/list":
            return _ok(rid, {"tools": self.list_tools()})
        if method == "tools/call":
            name = params.get("name")
            if not isinstance(name, str):
                return _fail(rid, -32602, "falta o nome da ferramenta")
            return _ok(rid, self.call_tool(name, params.get("arguments") or {}))
        return _fail(rid, -32601, f"método desconhecido: {method}")


def _ok(rid, result) -> dict:
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def _fail(rid, code: int, text: str) -> dict:
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": text}}


_LOCAL_HOSTS = ("127.0.0.1", "localhost", "[::1]", "::1")


class _HTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        """O cliente fechar a conexão (fim do pedido, Parar) não é erro."""
        import sys

        if not isinstance(sys.exc_info()[1], ConnectionError):
            super().handle_error(request, client_address)


class Server:
    """Servidor HTTP numa thread própria; ``url`` e ``token`` vão para o cliente."""

    def __init__(self, handler: Handler, port: int = 0):
        self.handler = handler
        self.token = secrets.token_urlsafe(24)
        outer = self

        class _Request(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):  # sem eco no terminal
                pass

            def _send(self, code: int, body: bytes = b"", ctype: str = "application/json"):
                self.send_response(code)
                if body:
                    self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if body:
                    self.wfile.write(body)

            def _allowed(self) -> bool:
                origin = self.headers.get("Origin")
                if origin and urlparse(origin).hostname not in _LOCAL_HOSTS:
                    return False
                expected = f"Bearer {outer.token}"
                return secrets.compare_digest(self.headers.get("Authorization", ""), expected)

            def do_POST(self):
                if urlparse(self.path).path != PATH:
                    return self._send(404)
                if not self._allowed():
                    return self._send(401)
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    message = json.loads(self.rfile.read(length) or b"null")
                except (ValueError, UnicodeDecodeError):
                    body = json.dumps(_fail(None, -32700, "JSON inválido")).encode()
                    return self._send(400, body)
                reply = outer.handler.handle(message)
                if reply is None:
                    return self._send(202)
                return self._send(200, json.dumps(reply, ensure_ascii=False).encode("utf-8"))

            def do_GET(self):
                self._send(405)

            def do_DELETE(self):
                self._send(405)

        self.httpd = _HTTPServer(("127.0.0.1", port), _Request)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True,
                                       name="brasbim-mcp")

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.httpd.server_address[1]}{PATH}"

    def start(self) -> Server:
        self.thread.start()
        return self

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def client_config(self, name: str = SERVER_NAME) -> dict:
        """Configuração MCP para o cliente (formato ``mcpServers`` do Claude Code)."""
        return {"mcpServers": {name: {"type": "http", "url": self.url,
                                      "headers": {"Authorization": f"Bearer {self.token}"}}}}
