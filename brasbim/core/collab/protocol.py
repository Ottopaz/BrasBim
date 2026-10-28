# SPDX-License-Identifier: LGPL-3.0-or-later
"""Mensagens e descoberta do projeto compartilhado (spec/ui 33 §2).

Cada mensagem é um objeto JSON numa linha (RFC 8259), com o tipo em ``t``. A descoberta
pergunta por UDP em broadcast e cada servidor responde com o projeto, o anfitrião e a
porta TCP.
"""

from __future__ import annotations

import json
import socket
import time

VERSION = 1
TCP_PORT = 47815  # primeira tentada; as seguintes se estiver ocupada
TCP_TRIES = 20
UDP_PORT = 47816
PROBE = b"BRASBIM?1"

# Cores das pessoas, na ordem de entrada (contornos na planta, painel Equipe).
COLORS = ("#D9480F", "#1971C2", "#2F9E44", "#AE3EC9", "#E8590C", "#0C8599", "#C2255C",
          "#5F3DC4")


def encode(msg: dict) -> bytes:
    return (json.dumps(msg, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def decode(line: bytes) -> dict:
    return json.loads(line.decode("utf-8"))


def reservable(tx, project_id: str | None) -> list[str]:
    """GlobalIds que a transação reserva (§3): todos os ``id`` das operações, menos as
    junções de paredes e as configurações do projeto (``IfcProject``)."""
    seen: dict[str, None] = {}
    for op in tx.ops:
        if op.op.startswith("path_connection.") or op.id == project_id:
            continue
        seen.setdefault(op.id)
    return list(seen)


def local_addresses() -> list[str]:
    """IPs desta máquina na rede local (para mostrar aos colegas)."""
    found: list[str] = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and ip not in found:
                found.append(ip)
    except OSError:
        pass
    try:  # a interface da rota padrão (não envia nada)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
            if not ip.startswith("127.") and ip not in found:
                found.insert(0, ip)
    except OSError:
        pass
    return found


def discover(timeout: float = 1.0, port: int = UDP_PORT,
             targets: tuple[str, ...] = ("<broadcast>", "127.0.0.1")) -> list[dict]:
    """Projetos compartilhados que responderam: ``{"project", "host", "address", "port"}``.
    """
    found: dict[tuple, dict] = {}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(0.1)
        for target in targets:
            try:
                s.sendto(PROBE, (target, port))
            except OSError:
                pass
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            try:
                data, (ip, _) = s.recvfrom(4096)
            except (TimeoutError, ConnectionResetError):  # Windows: ICMP de porta fechada
                continue
            except OSError:
                break
            try:
                info = json.loads(data.decode("utf-8"))
            except ValueError:
                continue
            if info.get("brasbim") != VERSION:
                continue
            # A mesma máquina responde por 127.0.0.1 e pelo IP da rede: fica o da rede.
            key = (info.get("id"), info.get("port"))
            if key in found and ip.startswith("127."):
                continue
            found[key] = {"project": info.get("project", ""), "host": info.get("host", ""),
                          "address": ip, "port": int(info.get("port", TCP_PORT))}
    return list(found.values())
