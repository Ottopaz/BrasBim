# SPDX-License-Identifier: GPL-3.0-or-later
"""Retorno de uso (``spec/ui/01-janela-e-ferramentas.md`` §9 e §8): observações com o
contexto da sessão e relatórios de erro inesperado."""

from __future__ import annotations

import subprocess
import traceback
from datetime import datetime
from pathlib import Path

from brasbim import __version__
from brasbim.ui.session import Session, feedback_dir


def version() -> str:
    """Versão do pacote e, se houver, o commit do repositório."""
    repo = Path(__file__).resolve().parents[2]
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo, check=False,
                                capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        commit = ""
    return f"{__version__} ({commit})" if commit else __version__


def _describe(session: Session, gid: str) -> str:
    entity = session.doc.find(gid)
    if entity is None:
        return f"`{gid}` (excluído)"
    name = f" «{entity.Name}»" if getattr(entity, "Name", None) else ""
    return f"{entity.is_a()}{name} `{gid}`"


def context(session: Session, tool: str = "") -> list[str]:
    storey = session.storey
    lines = [
        f"- Versão: {version()}",
        f"- Arquivo: {session.path or '(não salvo)'}",
        f"- Pavimento ativo: {storey.Name if storey else '—'}",
        f"- Ferramenta: {tool or '—'}",
        "- Seleção: " + (", ".join(_describe(session, g) for g in sorted(session.selection))
                         or "nada"),
    ]
    if session.journal_path:
        lines.append(f"- Diário da sessão: `{session.journal_path.name}`")
    recent = session.history.journal[-5:]
    if recent:
        lines.append("- Últimas transações:")
        for tx in recent:
            ops = ", ".join(op.op for op in tx.ops)
            lines.append(f"  - {tx.label}: {ops}")
    if session.messages:
        lines.append("- Últimas mensagens:")
        for m in session.messages[-5:]:
            lines.append(f"  - {m['time']} [{m['level']}] {m['text']}")
    return lines


def write_note(session: Session, text: str, tool: str = "", folder: Path | None = None) -> Path:
    """Acrescenta a observação a ``feedback/AAAA-MM-DD.md`` e devolve o arquivo."""
    folder = folder or feedback_dir()
    folder.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    path = folder / f"{now:%Y-%m-%d}.md"
    new = not path.exists()
    with path.open("a", encoding="utf-8") as f:
        if new:
            f.write(f"# Observações de uso — {now:%d/%m/%Y}\n")
        f.write(f"\n## {now:%H:%M}\n\n{text.strip()}\n\n")
        f.write("\n".join(context(session, tool)) + "\n")
    return path


def write_crash(session: Session | None, exc: BaseException, tool: str = "",
                folder: Path | None = None) -> Path:
    """Relatório de erro inesperado (§8), com o contexto e o rastreio da pilha."""
    folder = (folder or feedback_dir()) / "diarios"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"erro-{datetime.now():%Y-%m-%d_%H-%M-%S}.md"
    lines = ["# Erro inesperado", ""]
    if session is not None:
        lines += context(session, tool) + [""]
    lines += ["```", "".join(traceback.format_exception(exc)).rstrip(), "```", ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
