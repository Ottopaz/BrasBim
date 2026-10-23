# SPDX-License-Identifier: GPL-3.0-or-later
"""Leitura do que se digita na linha de comando (``spec/ui/24-linha-de-comando.md``), sem Qt.

O texto vira uma ``Entry``: coordenada ("x;y" ou "@dx;dy"), número, apelido, opção da
ferramenta ou comando achado pela busca da paleta (``command_search``), nessa ordem.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from brasbim.ui.command_search import Command, normalize, search

Point = tuple[float, float]

# Apelidos próprios (§7): 2 ou 3 letras que aparecem na ordem no nome em português.
DEFAULT_ALIASES = {
    "tool:select": "SL",
    "tool:wall": "PD",
    "tool:arc": "PA",
    "tool:rectangle": "RP",
    "tool:door": "PT",
    "tool:window": "JN",
    "tool:wall_opening": "VA",
    "tool:column": "PI",
    "tool:beam": "VG",
    "tool:slab": "LJ",
    "tool:roof": "CB",
    "tool:skylight": "CLB",
    "tool:stair": "ED",
    "tool:railing": "GC",
    "tool:object": "OB",
    "tool:grid": "EI",
    "tool:terrain": "TN",
    "tool:space": "AM",
    "tool:dimension": "CT",
    "tool:radius_dim": "CTR",
    "tool:angle_dim": "CTA",
    "tool:level_mark": "NV",
    "tool:text": "TX",
    "tool:label": "RT",
    "tool:line2d": "LN",
    "tool:spline2d": "CV",
    "tool:circle2d": "CI",
    "tool:arc2d": "AC",
    "tool:hatch": "HC",
    "tool:north": "NT",
    "tool:revision": "AT",
    "tool:section": "CE",
    "tool:elevation": "FC",
    "tool:offset": "DP",
    "tool:trim": "AE",
    "tool:fillet": "CD",
    "menu:Editar/Mover": "MV",
    "menu:Editar/Copiar": "CPR",
    "menu:Editar/Girar": "GR",
    "menu:Editar/Espelhar": "EP",
    "menu:Editar/Dividir": "DV",
    "menu:Exibir/Enquadrar tudo": "EQ",
}
MAX_ALIAS = 6
SUGGESTIONS = 8
_NUMBER = re.compile(r"^[+-]?(\d+([.,]\d*)?|[.,]\d+)$")


class EntryError(ValueError):
    """Texto que parece coordenada mas não é válido (ou falta o ponto anterior)."""


@dataclass(frozen=True)
class Option:
    """Escolha da barra Opções mostrada na linha (§5): grupo, posição no grupo."""

    group: int
    index: int
    label: str
    current: bool = False


@dataclass(frozen=True)
class Entry:
    kind: str  # empty, point, number, command, option, unknown, error
    point: Point | None = None
    value: float | None = None
    key: str = ""  # comando
    option: Option | None = None
    text: str = ""  # mensagem do erro


@dataclass(frozen=True)
class Candidate:
    """Linha da lista de sugestões (§4)."""

    kind: str  # command, option
    label: str
    key: str = ""
    alias: str = ""
    where: str = ""
    option: Option | None = None


def parse_number(text: str) -> float | None:
    text = text.strip().replace(" ", "")
    if not _NUMBER.match(text):
        return None
    return float(text.replace(",", "."))


def parse_point(text: str, base: Point | None) -> Point | None:
    """Coordenada "x;y" ou "@dx;dy" (relativa a ``base``); None se o texto não é
    coordenada. ``EntryError`` se parece coordenada e está errada."""
    text = text.strip().replace(" ", "")
    relative = text.startswith("@")
    if relative:
        text = text[1:]
    if ";" not in text:
        if relative:
            raise EntryError("coordenada relativa: use @dx;dy")
        return None
    parts = text.split(";")
    values = [parse_number(p) for p in parts]
    if len(parts) != 2 or None in values:
        raise EntryError(f"coordenada inválida: {text!r} (use x;y)")
    x, y = values
    if relative:
        if base is None:
            raise EntryError("não há ponto anterior para a coordenada relativa")
        return (base[0] + x, base[1] + y)
    return (x, y)


def _alias_index(aliases: dict[str, str]) -> dict[str, str]:
    return {a.lower(): key for key, a in aliases.items() if a}


def match_options(text: str, options: list[Option]) -> list[Option]:
    """Opções cujo nome começa pelo texto (sem acento nem caixa)."""
    q = normalize(text)
    if not q:
        return []
    return [o for o in options if normalize(o.label).startswith(q)]


def interpret(text: str, commands: list[Command], aliases: dict[str, str],
              options: list[Option] = (), base: Point | None = None,
              recent: list[str] = ()) -> Entry:
    """O que o Enter faz com ``text`` (§4)."""
    if not text.strip():
        return Entry("empty")
    try:
        point = parse_point(text, base)
    except EntryError as error:
        return Entry("error", text=str(error))
    if point is not None:
        return Entry("point", point=point)
    value = parse_number(text)
    if value is not None:
        return Entry("number", value=value)
    found = candidates(text, commands, aliases, options, recent, limit=1)
    if not found:
        return Entry("unknown", text=f"comando não encontrado: {text.strip()}")
    first = found[0]
    if first.kind == "option":
        return Entry("option", option=first.option)
    return Entry("command", key=first.key)


def candidates(text: str, commands: list[Command], aliases: dict[str, str],
               options: list[Option] = (), recent: list[str] = (),
               limit: int = SUGGESTIONS) -> list[Candidate]:
    """Sugestões na ordem do Enter: apelido exato, opções, apelidos que começam pelo
    texto e busca da paleta, sem repetir comando."""
    q = text.strip().lower()
    if not q:
        return []
    by_key = {}
    for c in commands:
        by_key.setdefault(c.key, c)
    index = _alias_index(aliases)
    out: list[Candidate] = []
    seen: set[str] = set()

    def add(command: Command) -> None:
        if command.key not in seen:
            seen.add(command.key)
            out.append(Candidate("command", command.label, command.key,
                                 aliases.get(command.key, ""), command.where))

    if q in index and index[q] in by_key:
        add(by_key[index[q]])
    out += [Candidate("option", o.label, option=o) for o in match_options(text, options)]
    for alias in sorted(a for a in index if a.startswith(q) and a != q):
        if index[alias] in by_key:
            add(by_key[index[alias]])
    for command in search(text, commands, list(recent)):
        add(command)
        if len(out) >= limit:
            break
    return out[:limit]


# --- apelidos editáveis (§7) ----------------------------------------------------------


def validate_aliases(aliases: dict[str, str]) -> list[str]:
    """Problemas da tabela de apelidos (vazio = sem apelido, aceito)."""
    errors, seen = [], {}
    for key, alias in aliases.items():
        alias = (alias or "").strip()
        if not alias:
            continue
        if len(alias) > MAX_ALIAS:
            errors.append(f"{alias}: no máximo {MAX_ALIAS} caracteres")
        elif not alias.isascii() or not alias.isalnum():
            errors.append(f"{alias}: só letras e algarismos")
        elif not alias[0].isalpha():
            errors.append(f"{alias}: começa por letra")
        low = alias.lower()
        if low in seen:
            errors.append(f"{alias}: repetido")
        seen[low] = key
    return errors


def merge_aliases(changes: dict[str, str], defaults: dict[str, str] = DEFAULT_ALIASES
                  ) -> dict[str, str]:
    """Padrão com as diferenças gravadas pelo usuário ("" tira o apelido)."""
    out = dict(defaults)
    for key, alias in changes.items():
        if alias:
            out[key] = alias.upper()
        else:
            out.pop(key, None)
    return out


def diff_aliases(aliases: dict[str, str], defaults: dict[str, str] = DEFAULT_ALIASES
                 ) -> dict[str, str]:
    """Só o que difere do padrão, para gravar nas preferências."""
    out = {key: alias.upper() for key, alias in aliases.items()
           if alias and defaults.get(key, "").upper() != alias.upper()}
    out.update({key: "" for key in defaults if not aliases.get(key)})
    return out


# --- histórico (§6) ---------------------------------------------------------------------


class History:
    """Linhas digitadas e resultados da sessão; ↑/↓ percorrem os textos."""

    def __init__(self, limit: int = 100):
        self.limit = limit
        self.lines: list[tuple[str, str]] = []  # (texto, resultado)
        self.pos: int | None = None  # posição ao percorrer com ↑/↓

    def add(self, text: str, result: str) -> None:
        self.lines.append((text, result))
        del self.lines[:-self.limit]
        self.pos = None

    def texts(self) -> list[str]:
        out: list[str] = []
        for text, _ in self.lines:
            if text and (not out or out[-1] != text):
                out.append(text)
        return out

    def step(self, delta: int) -> str | None:
        """↑ (-1) ou ↓ (+1); None ao passar do fim (campo vazio)."""
        texts = self.texts()
        if not texts:
            return None
        pos = len(texts) if self.pos is None else self.pos
        pos = max(0, min(len(texts), pos + delta))
        self.pos = pos
        return texts[pos] if pos < len(texts) else None
