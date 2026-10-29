# SPDX-License-Identifier: LGPL-3.0-or-later
"""Cliente do projeto compartilhado (spec/ui 33 §2–§5).

Liga um ``History`` ao servidor. A transação é aplicada aqui na hora e enviada; fica
pendente até o ``ack``. Se chega uma transação de outra pessoa antes, as pendentes são
desfeitas, a outra é aplicada e as pendentes são reaplicadas, para que todos fiquem na
ordem do servidor. A leitura da rede roda numa thread e só enfileira; ``poll`` (chamado
pela interface, na thread dela) aplica, avisa o histórico com ``remote`` e os
``listeners`` com ``(evento, dados)``:

- ``users`` {users, event}: entrou ou saiu alguém;
- ``reservations`` {ids}: reservas mudaram;
- ``request`` {from, name, ids}: pedido de liberação;
- ``message`` {text, level};
- ``resync`` {ifc}: o projeto inteiro veio de novo (a cópia local divergiu);
- ``closed`` {reason}: a conexão acabou.
"""

from __future__ import annotations

import logging
import queue
import socket
import threading
from collections.abc import Callable
from dataclasses import dataclass

from brasbim.core.collab import protocol
from brasbim.core.document import OpError
from brasbim.core.ops import History, Transaction

log = logging.getLogger(__name__)


# Nome do elemento nas recusas (§3); os tipos antes das classes de elemento.
_NOUNS = (
    ("IfcTypeObject", "O tipo"),
    ("IfcWall", "A parede"),
    ("IfcDoor", "A porta"),
    ("IfcWindow", "A janela"),
    ("IfcSlab", "A laje"),
    ("IfcRoof", "A cobertura"),
    ("IfcColumn", "O pilar"),
    ("IfcBeam", "A viga"),
    ("IfcStair", "A escada"),
    ("IfcRailing", "O guarda-corpo"),
    ("IfcSpace", "O ambiente"),
    ("IfcOpeningElement", "A abertura"),
    ("IfcBuildingStorey", "O pavimento"),
    ("IfcAnnotation", "A anotação"),
)


@dataclass
class _Pending:
    cid: int
    tx: Transaction  # o que foi aplicado (no desfazer, o inverso)
    origin: Transaction  # a transação das pilhas
    kind: str  # commit, undo, redo
    live: bool = True  # aplicada na cópia local


class Client:
    def __init__(self, name: str):
        self.name = name
        self.me: str | None = None
        self.users: dict[str, dict] = {}
        self.reservations: dict[str, str] = {}
        self.project = ""
        self.host = ""
        self.address: tuple[str, int] | None = None
        self.listeners: list[Callable[[str, dict], None]] = []
        self.history: History | None = None
        self._sock: socket.socket | None = None
        self._inbox: queue.Queue = queue.Queue()
        self._pending: list[_Pending] = []
        self._cid = 0
        self._resyncing = False
        self._applying = False
        self.connected = False

    # --- conexão -----------------------------------------------------------------------

    def connect(self, host: str, port: int = protocol.TCP_PORT,
                timeout: float = 10.0) -> dict:
        """Conecta e espera o ``welcome`` (com o IFC atual). Devolve o ``welcome``."""
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.sendall(protocol.encode({"t": "hello", "name": self.name,
                                      "version": protocol.VERSION}))
        stream = sock.makefile("rb")
        line = stream.readline()
        if not line:
            sock.close()
            raise OSError("o servidor fechou a conexão")
        welcome = protocol.decode(line)
        if welcome.get("t") != "welcome":
            sock.close()
            raise OSError(f"resposta inesperada do servidor: {welcome.get('t')!r}")
        sock.settimeout(None)
        self._sock = sock
        self.address = (host, port)
        self.me = welcome["you"]
        self.project = welcome.get("project", "")
        self.host = welcome.get("host", "")
        self.users = {u["id"]: u for u in welcome.get("users", [])}
        self.reservations = dict(welcome.get("reservations", {}))
        self.connected = True
        threading.Thread(target=self._reader, args=(stream,), daemon=True).start()
        return welcome

    def attach(self, history: History) -> None:
        """Passa a sincronizar este histórico (o documento já é o do ``welcome``)."""
        self.detach()
        self.history = history
        history.listeners.append(self._on_history)
        history.guards.append(self.guard)
        self._pending.clear()

    def detach(self) -> None:
        if self.history is not None:
            if self._on_history in self.history.listeners:
                self.history.listeners.remove(self._on_history)
            if self.guard in self.history.guards:
                self.history.guards.remove(self.guard)
        self.history = None

    def close(self) -> None:
        self.detach()
        self.connected = False
        if self._sock is not None:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self._sock.close()
            self._sock = None

    def _reader(self, stream) -> None:
        try:
            for line in stream:
                if line.strip():
                    try:
                        self._inbox.put(protocol.decode(line))
                    except ValueError:
                        continue
        except OSError:
            pass
        self._inbox.put({"t": "_closed"})

    def _send(self, msg: dict) -> None:
        if self._sock is None:
            return
        try:
            self._sock.sendall(protocol.encode(msg))
        except OSError as e:
            log.debug("envio falhou: %s", e)

    def _emit(self, event: str, data: dict | None = None) -> None:
        for listener in list(self.listeners):
            listener(event, data or {})

    # --- reservas ----------------------------------------------------------------------

    def owner(self, gid: str) -> dict | None:
        """Quem reservou (``{"id", "name", "color"}``), ou ``None`` se está livre."""
        uid = self.reservations.get(gid)
        if uid is None:
            return None
        return self.users.get(uid, {"id": uid, "name": "outra pessoa", "color": "#888888"})

    def reserved_by_others(self) -> dict[str, str]:
        """GlobalId → cor de quem reservou, sem as minhas."""
        return {g: self.users.get(u, {}).get("color", "#888888")
                for g, u in self.reservations.items() if u != self.me}

    def mine(self) -> list[str]:
        return [g for g, u in self.reservations.items() if u == self.me]

    def guard(self, tx: Transaction) -> None:
        """Recusa antes de aplicar o que mexe em reserva de outra pessoa (§3)."""
        if self._applying:
            return
        if not self.connected:
            return
        if self._resyncing:
            raise OpError("aguardando o projeto do servidor; tente de novo em instantes")
        doc = self.history.doc if self.history is not None else None
        project = doc.project.GlobalId if doc is not None else None
        for gid in protocol.reservable(tx, project):
            uid = self.reservations.get(gid)
            if uid is not None and uid != self.me:
                label = self._label(gid)
                ending = "a" if label.startswith("A ") else "o"
                raise OpError(f"{label} está reservad{ending} por "
                              f"{self.owner(gid)['name']}; peça a liberação "
                              "(Equipe > Pedir liberação)")

    def _label(self, gid: str) -> str:
        doc = self.history.doc if self.history is not None else None
        entity = doc.find(gid) if doc is not None else None
        if entity is None:
            return "O elemento"
        noun = next((n for cls, n in _NOUNS if entity.is_a(cls)), "O elemento")
        name = getattr(entity, "Name", None)
        return f"{noun} {name}" if name else noun

    def request(self, ids) -> None:
        self._send({"t": "request", "ids": list(ids)})

    def release(self, ids=None) -> None:
        self._send({"t": "release", "ids": None if ids is None else list(ids)})

    def grant(self, to: str, ids) -> None:
        self._send({"t": "grant", "to": to, "ids": list(ids)})

    def deny(self, to: str, ids) -> None:
        self._send({"t": "deny", "to": to, "ids": list(ids)})

    # --- transações --------------------------------------------------------------------

    def _on_history(self, kind: str, tx: Transaction, changed: set[str]) -> None:
        if kind not in ("commit", "undo", "redo") or self._applying or not self.connected:
            return
        applied = self.history.journal[-1]
        self._cid += 1
        self._pending.append(_Pending(self._cid, applied, tx, kind))
        self._send({"t": "tx", "cid": self._cid, "tx": applied.to_dict(copy_=False)})

    def _rollback(self) -> set[str]:
        changed: set[str] = set()
        for p in reversed(self._pending):
            if p.live:
                changed |= self.history.replay(p.tx.inverse())
                p.live = False
        return changed

    def _reapply(self) -> tuple[set[str], list[_Pending]]:
        changed: set[str] = set()
        failed = []
        for p in self._pending:
            try:
                changed |= self.history.replay(p.tx)
                p.live = True
            except Exception:  # noqa: BLE001 - a cópia local não aceita mais
                failed.append(p)
        return changed, failed

    def _drop_from_stacks(self, p: _Pending) -> None:
        """A transação ``p`` não valeu: as pilhas voltam ao estado de antes dela."""
        h = self.history
        if p.kind in ("commit", "redo"):
            if h.undo_stack and h.undo_stack[-1] is p.origin:
                h.undo_stack.pop()
            elif p.origin in h.undo_stack:
                h.undo_stack.remove(p.origin)
            if p.kind == "redo":
                h.redo_stack.append(p.origin)
        else:  # desfazer recusado: o passo continua desfazível
            if p.origin in h.redo_stack:
                h.redo_stack.remove(p.origin)
            h.undo_stack.append(p.origin)

    def poll(self) -> None:
        """Processa o que chegou (na thread da interface)."""
        changed: set[str] = set()
        notes: list[str] = []
        while True:
            try:
                msg = self._inbox.get_nowait()
            except queue.Empty:
                break
            changed |= self._process(msg, notes)
            if not self.connected:
                break
        if (changed or notes) and self.history is not None:
            label = notes[0] if len(notes) == 1 else "Alterações da equipe"
            self.history.notify("remote", Transaction(label, []), changed)

    def _process(self, msg: dict, notes: list[str]) -> set[str]:
        kind = msg.get("t")
        if kind == "_closed":
            if self.connected:
                self.connected = False
                self._emit("closed", {"reason": "a conexão com o projeto compartilhado "
                                                "caiu"})
            return set()
        if kind == "bye":
            self.connected = False
            self._emit("closed", {"reason": msg.get("reason", "")})
            return set()
        if kind == "users":
            self.users = {u["id"]: u for u in msg.get("users", [])}
            self._emit("users", {"event": msg.get("event", "")})
        elif kind == "reservations":
            for gid, uid in msg["changes"].items():
                if uid is None:
                    self.reservations.pop(gid, None)
                else:
                    self.reservations[gid] = uid
            self._emit("reservations", {"ids": list(msg["changes"])})
        elif kind == "request":
            self._emit("request", msg)
        elif kind == "granted":
            if msg.get("ids"):
                self._emit("message", {"text": f"{msg['name']} liberou "
                                               f"{len(msg['ids'])} elemento(s) para você",
                                       "level": "info"})
        elif kind == "denied":
            self._emit("message", {"text": f"{msg['name']} recusou o pedido de liberação",
                                   "level": "aviso"})
        elif kind == "snapshot":
            self._resyncing = False
            self._pending.clear()
            self.reservations = dict(msg.get("reservations", {}))
            self._emit("resync", {"ifc": msg["ifc"]})
        elif self._resyncing or self.history is None:
            return set()
        elif kind == "ack":
            if self._pending and self._pending[0].cid == msg.get("cid"):
                p = self._pending.pop(0)
                if not p.live:  # o servidor aceitou o que aqui não coube
                    self._resync()
        elif kind == "reject":
            return self._on_reject(msg, notes)
        elif kind == "tx":
            return self._on_remote(msg, notes)
        return set()

    def _on_remote(self, msg: dict, notes: list[str]) -> set[str]:
        tx = Transaction.from_dict(msg["tx"])
        self._applying = True
        try:
            changed = self._rollback()
            try:
                changed |= self.history.replay(tx)
            except Exception as e:  # noqa: BLE001
                log.warning("transação de %s não aplicou aqui: %s", msg.get("name"), e)
                self._resync()
                return changed
            more, _ = self._reapply()
            changed |= more
        finally:
            self._applying = False
        notes.append(f"{msg.get('name', 'Outra pessoa')}: {tx.label}")
        return changed

    def _on_reject(self, msg: dict, notes: list[str]) -> set[str]:
        if not self._pending or self._pending[0].cid != msg.get("cid"):
            return set()
        self._applying = True
        try:
            changed = self._rollback()
            p = self._pending.pop(0)
            self._drop_from_stacks(p)
            more, _ = self._reapply()
            changed |= more
        finally:
            self._applying = False
        reason = msg.get("reason", "")
        self._emit("message", {"text": f"Recusado pelo projeto compartilhado "
                                       f"({p.tx.label}): {reason}", "level": "recusa"})
        notes.append(f"Recusado: {p.tx.label}")
        return changed

    def _resync(self) -> None:
        """A cópia local divergiu: pede o projeto inteiro e ignora o que vier antes."""
        if self._resyncing:
            return
        self._resyncing = True
        self._emit("message", {"text": "Atualizando o projeto inteiro do servidor",
                               "level": "aviso"})
        self._send({"t": "snapshot"})
