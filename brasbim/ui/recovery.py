# SPDX-License-Identifier: GPL-3.0-or-later
"""Cópias de segurança e recuperação após falha (``spec/ui/21-salvamento-automatico.md``),
sem Qt.

Cada cópia é um IFC na pasta de recuperação com um JSON ao lado::

    {"file": "C:/obras/Casa.ifc" | null, "saved": "2026-10-21T14:05:00",
     "heartbeat": "2026-10-21T14:07:00"}

O sinal de vida (``heartbeat``) é renovado enquanto a sessão está aberta; a cópia com
sinal velho é órfã (o BrasBim que a gravou não fechou direito).
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

ORPHAN_AGE = 180.0  # s sem sinal de vida para a cópia ser órfã (§4)


def sidecar(path: Path) -> Path:
    return path.with_suffix(".json")


def _write_json(path: Path, data: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def write(doc, path: Path, original: str | None, now: datetime) -> None:
    """Grava a cópia (IFC e JSON) por troca de nome: uma falha no meio não estraga a
    cópia anterior (§2)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.stem + ".tmp.ifc")
    doc.save(str(tmp))
    os.replace(tmp, path)
    stamp = now.isoformat(timespec="seconds")
    _write_json(sidecar(path), {"file": original, "saved": stamp, "heartbeat": stamp})


def touch(path: Path, now: datetime) -> None:
    """Renova o sinal de vida da cópia, se ela existe."""
    meta = sidecar(path)
    try:
        data = json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    data["heartbeat"] = now.isoformat(timespec="seconds")
    _write_json(meta, data)


def remove(path: Path) -> None:
    for p in (path, sidecar(path)):
        try:
            p.unlink()
        except FileNotFoundError:
            pass


def orphans(directory: Path | None, own: Path | None, now: datetime,
            max_age: float = ORPHAN_AGE) -> list[dict]:
    """Cópias órfãs, da mais recente para a mais antiga: ``{"path", "file", "saved"}``."""
    if directory is None or not directory.is_dir():
        return []
    out = []
    for path in directory.glob("*.ifc"):
        if path.name.endswith(".tmp.ifc") or (own is not None and path == own):
            continue
        try:
            data = json.loads(sidecar(path).read_text(encoding="utf-8"))
            saved = datetime.fromisoformat(data["saved"])
            heartbeat = datetime.fromisoformat(data.get("heartbeat") or data["saved"])
        except (OSError, ValueError, KeyError):
            continue
        if (now - heartbeat).total_seconds() < max_age:
            continue  # outra janela do BrasBim ainda está com ela
        out.append({"path": path, "file": data.get("file"), "saved": saved})
    return sorted(out, key=lambda e: e["saved"], reverse=True)


def adopt(entry: dict, path: Path, now: datetime) -> None:
    """A cópia recuperada passa a ser a da sessão atual (§4)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    os.replace(entry["path"], path)
    try:
        os.replace(sidecar(entry["path"]), sidecar(path))
    except FileNotFoundError:
        pass
    touch(path, now)
