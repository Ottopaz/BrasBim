# SPDX-License-Identifier: LGPL-3.0-or-later
"""Servidor do projeto compartilhado (spec/ui 33 §2–§3).

Roda em threads do computador que compartilha. Guarda uma cópia do projeto e aplica as
transações na ordem de chegada (uma de cada vez, sob ``_lock``): quem envia recebe
``ack`` ou ``reject``; os outros recebem ``tx``. Também guarda as reservas (GlobalId →
pessoa) e repassa pedidos de liberação.

Mensagens recebidas: ``hello`` {name}, ``tx`` {cid, tx}, ``release`` {ids | None},
``request`` {ids}, ``grant`` {to, ids}, ``deny`` {to, ids}, ``snapshot``.
Enviadas: ``welcome``, ``ack``, ``reject``, ``tx``, ``reservations``, ``users``,
``request``, ``granted``, ``denied``, ``snapshot``, ``bye``.
"""

from __future__ import annotations

import json
import logging
import socket
import threading
import uuid

import ifcopenshell

from brasbim.core.collab import protocol
from brasbim.core.document import Document
from brasbim.core.ops import Transaction
from brasbim.core.ops.history import run

log = logging.getLogger(__name__)


class _Conn:
    def __init__(self, sock: socket.socket, uid: str):
        self.sock = sock
        self.uid = uid
        self.name = ""
        self.color = ""
        self.ready = False  # já recebeu o welcome
        self._send_lock = threading.Lock()

    def send(self, msg: dict) -> None:
        data = protocol.encode(msg)
        with self._send_lock:
            try:
                self.sock.sendall(data)
            except OSError:
                pass


class Server:
    """``ifc_text``: o projeto no estado atual (``ifc.to_string()``)."""

    def __init__(self, ifc_text: str, project: str = "", host: str = "",
                 port: int = protocol.TCP_PORT, discovery: bool = True,
                 udp_port: int = protocol.UDP_PORT):
        self.doc = Document(ifcopenshell.file.from_string(ifc_text))
        self.project_id = self.doc.project.GlobalId
        self.project = project
        self.host = host or socket.gethostname()
        self.id = uuid.uuid4().hex
        self.seq = 0
        self.reservations: dict[str, str] = {}
        self._conns: dict[str, _Conn] = {}
        self._colors = 0
        self._lock = threading.RLock()
        self._closing = False
        self._tcp = self._bind(port)
        self.port = self._tcp.getsockname()[1]
        self._udp = self._bind_udp(udp_port) if discovery else None
        self._threads: list[threading.Thread] = []

    # --- rede --------------------------------------------------------------------------

    @staticmethod
    def _bind(port: int) -> socket.socket:
        tries = range(port, port + protocol.TCP_TRIES) if port else [0]
        last = None
        for p in tries:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.bind(("0.0.0.0", p))
            except OSError as e:
                s.close()
                last = e
                continue
            s.listen()
            return s
        raise OSError(f"nenhuma porta livre a partir de {port}: {last}")

    @staticmethod
    def _bind_udp(port: int) -> socket.socket | None:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", port))
        except OSError as e:
            log.warning("descoberta na rede indisponível (porta UDP %s): %s", port, e)
            s.close()
            return None
        return s

    def start(self) -> Server:
        self._spawn(self._accept_loop)
        if self._udp is not None:
            self._spawn(self._udp_loop)
        return self

    def _spawn(self, target, *args) -> None:
        t = threading.Thread(target=target, args=args, daemon=True)
        t.start()
        self._threads.append(t)

    def stop(self) -> None:
        self._closing = True
        with self._lock:
            conns = list(self._conns.values())
        for conn in conns:
            conn.send({"t": "bye", "reason": "o anfitrião encerrou o compartilhamento"})
            try:
                conn.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            conn.sock.close()
        for s in (self._tcp, self._udp):
            if s is not None:
                s.close()

    def _accept_loop(self) -> None:
        while not self._closing:
            try:
                sock, _ = self._tcp.accept()
            except OSError:
                return
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self._spawn(self._reader, _Conn(sock, uuid.uuid4().hex[:12]))

    def _udp_loop(self) -> None:
        while not self._closing:
            try:
                data, addr = self._udp.recvfrom(1024)
            except OSError:
                return
            if data.strip() != protocol.PROBE:
                continue
            reply = json.dumps({"brasbim": protocol.VERSION, "id": self.id,
                                "project": self.project, "host": self.host,
                                "port": self.port}, ensure_ascii=False)
            try:
                self._udp.sendto(reply.encode("utf-8"), addr)
            except OSError:
                pass

    def _reader(self, conn: _Conn) -> None:
        stream = conn.sock.makefile("rb")
        try:
            for line in stream:
                if not line.strip():
                    continue
                try:
                    msg = protocol.decode(line)
                except ValueError:
                    continue
                with self._lock:
                    self._handle(conn, msg)
        except OSError:
            pass
        finally:
            with self._lock:
                self._drop(conn)

    # --- estado ------------------------------------------------------------------------

    def _users(self) -> list[dict]:
        return [{"id": c.uid, "name": c.name, "color": c.color}
                for c in self._conns.values() if c.ready]

    def _broadcast(self, msg: dict, skip: _Conn | None = None) -> None:
        for conn in self._conns.values():
            if conn.ready and conn is not skip:
                conn.send(msg)

    def _reserve(self, changes: dict[str, str | None]) -> None:
        changes = {g: u for g, u in changes.items() if self.reservations.get(g) != u}
        if not changes:
            return
        for gid, uid in changes.items():
            if uid is None:
                self.reservations.pop(gid, None)
            else:
                self.reservations[gid] = uid
        self._broadcast({"t": "reservations", "changes": changes})

    def _drop(self, conn: _Conn) -> None:
        if self._conns.pop(conn.uid, None) is None:
            return
        try:
            conn.sock.close()
        except OSError:
            pass
        if self._closing:
            return
        self._reserve({g: None for g, u in self.reservations.items() if u == conn.uid})
        self._broadcast({"t": "users", "users": self._users(),
                         "event": f"{conn.name} saiu"})

    def _snapshot(self) -> dict:
        return {"ifc": self.doc.ifc.to_string(), "seq": self.seq,
                "reservations": dict(self.reservations)}

    def _handle(self, conn: _Conn, msg: dict) -> None:
        kind = msg.get("t")
        if kind == "hello":
            conn.name = str(msg.get("name") or "Sem nome")[:60]
            conn.color = protocol.COLORS[self._colors % len(protocol.COLORS)]
            self._colors += 1
            self._conns[conn.uid] = conn
            conn.ready = True
            conn.send({"t": "welcome", "you": conn.uid, "project": self.project,
                       "host": self.host, "users": self._users(), **self._snapshot()})
            self._broadcast({"t": "users", "users": self._users(),
                             "event": f"{conn.name} entrou"}, skip=conn)
        elif not conn.ready:
            return
        elif kind == "tx":
            self._on_tx(conn, msg)
        elif kind == "release":
            ids = msg.get("ids")
            self._reserve({g: None for g, u in self.reservations.items()
                           if u == conn.uid and (ids is None or g in ids)})
        elif kind == "request":
            by_owner: dict[str, list[str]] = {}
            for gid in msg.get("ids") or []:
                owner = self.reservations.get(gid)
                if owner and owner != conn.uid:
                    by_owner.setdefault(owner, []).append(gid)
            for owner, ids in by_owner.items():
                if owner in self._conns:
                    self._conns[owner].send({"t": "request", "from": conn.uid,
                                             "name": conn.name, "ids": ids})
        elif kind in ("grant", "deny"):
            target = self._conns.get(msg.get("to"))
            ids = [g for g in msg.get("ids") or [] if self.reservations.get(g) == conn.uid]
            if kind == "grant":
                self._reserve({g: (target.uid if target else None) for g in ids})
            if target is not None:
                target.send({"t": "granted" if kind == "grant" else "denied",
                             "name": conn.name, "ids": ids})
        elif kind == "snapshot":
            conn.send({"t": "snapshot", **self._snapshot()})

    def _on_tx(self, conn: _Conn, msg: dict) -> None:
        cid = msg.get("cid")
        try:
            tx = Transaction.from_dict(msg["tx"])
        except (KeyError, TypeError) as e:
            conn.send({"t": "reject", "cid": cid, "reason": f"transação inválida: {e}"})
            return
        ids = protocol.reservable(tx, self.project_id)
        for gid in ids:
            owner = self.reservations.get(gid)
            if owner and owner != conn.uid:
                name = self._conns[owner].name if owner in self._conns else "outra pessoa"
                conn.send({"t": "reject", "cid": cid,
                           "reason": f"{gid} está reservado por {name}"})
                return
        try:
            run(self.doc, tx)
        except Exception as e:  # noqa: BLE001 - qualquer falha recusa a transação
            conn.send({"t": "reject", "cid": cid, "reason": str(e) or type(e).__name__})
            return
        self.seq += 1
        conn.send({"t": "ack", "cid": cid, "seq": self.seq})
        self._broadcast({"t": "tx", "seq": self.seq, "author": conn.uid, "name": conn.name,
                         "tx": msg["tx"]}, skip=conn)
        self._reserve({g: (conn.uid if self.doc.find(g) is not None else None)
                       for g in ids})
