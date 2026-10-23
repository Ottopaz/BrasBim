# SPDX-License-Identifier: GPL-3.0-or-later
"""Linha de comando sem Qt (spec/ui/24-linha-de-comando.md §10): LC01–LC05."""

import pytest

from brasbim.ui.command_input import (
    DEFAULT_ALIASES,
    EntryError,
    History,
    Option,
    candidates,
    diff_aliases,
    interpret,
    merge_aliases,
    parse_point,
    validate_aliases,
)
from brasbim.ui.command_search import Command, normalize

COMMANDS = [
    Command("tool:wall", "Parede", "Ferramentas", "", ("IfcWall", "muro")),
    Command("tool:arc", "Parede em arco", "Ferramentas"),
    Command("tool:slab", "Laje", "Ferramentas"),
    Command("tool:door", "Porta", "Ferramentas"),
    Command("tool:offset", "Deslocar paralela", "Edição"),
    Command("menu:Editar/Mover", "Mover", "Editar"),
]


def test_lc01_coordenadas():
    assert parse_point("3,5;2", None) == (3.5, 2.0)
    assert parse_point(" 3.5 ; 2 ", None) == (3.5, 2.0)
    assert parse_point("-1;0", None) == (-1.0, 0.0)
    assert parse_point("@4;0", (1, 2)) == (5.0, 2.0)
    assert parse_point("@0;-2,5", (1, 2)) == (1.0, -0.5)
    with pytest.raises(EntryError, match="ponto anterior"):
        parse_point("@1;1", None)
    for bad in ("3;", "a;b", "1;2;3", "@4"):
        with pytest.raises(EntryError):
            parse_point(bad, (0, 0))
    assert parse_point("3,5", None) is None
    assert parse_point("parede", None) is None


def test_lc02_ordem_da_leitura():
    aliases = {"tool:wall": "PD", "tool:door": "PT", "tool:offset": "MO"}
    options = [Option(0, 0, "Copiar", True), Option(0, 1, "Mover o original")]
    assert interpret("", COMMANDS, aliases).kind == "empty"
    e = interpret("3;4", COMMANDS, aliases, options)
    assert (e.kind, e.point) == ("point", (3.0, 4.0))
    assert interpret("@1;x", COMMANDS, aliases).kind == "error"
    e = interpret("2,40", COMMANDS, aliases)
    assert (e.kind, e.value) == ("number", 2.4)
    e = interpret("pd", COMMANDS, aliases)
    assert (e.kind, e.key) == ("command", "tool:wall")
    e = interpret("PT", COMMANDS, aliases)
    assert e.key == "tool:door"
    # opção vence a busca; apelido exato vence a opção
    e = interpret("mov", COMMANDS, aliases, options)
    assert (e.kind, e.option.label) == ("option", "Mover o original")
    e = interpret("mo", COMMANDS, aliases, options)
    assert (e.kind, e.key) == ("command", "tool:offset")
    # sem opção: a busca acha o comando; sem acento e sem caixa
    e = interpret("mov", COMMANDS, aliases)
    assert e.key == "menu:Editar/Mover"
    assert interpret("LÁJE", COMMANDS, aliases).key == "tool:slab"
    assert interpret("muro", COMMANDS, aliases).key == "tool:wall"
    e = interpret("xyzw", COMMANDS, aliases)
    assert e.kind == "unknown" and "xyzw" in e.text
    # sugestões na mesma ordem: apelido exato, opções, apelidos que começam, busca
    found = candidates("p", COMMANDS, aliases, options)
    assert [c.key for c in found[:2]] == ["tool:wall", "tool:door"]
    assert len({c.key for c in found if c.kind == "command"}) == \
        len([c for c in found if c.kind == "command"])


def test_lc03_apelidos_padrao():
    values = [a.lower() for a in DEFAULT_ALIASES.values()]
    assert len(values) == len(set(values))
    assert not validate_aliases(DEFAULT_ALIASES)
    names = {"tool:select": "Selecionar", "tool:wall": "Parede", "tool:arc": "Parede em arco",
             "tool:rectangle": "Retângulo de paredes", "tool:door": "Porta",
             "tool:window": "Janela", "tool:wall_opening": "Vão", "tool:column": "Pilar",
             "tool:beam": "Viga", "tool:slab": "Laje", "tool:roof": "Cobertura",
             "tool:skylight": "Claraboia", "tool:stair": "Escada",
             "tool:railing": "Guarda-corpo", "tool:object": "Objeto", "tool:grid": "Eixos",
             "tool:terrain": "Terreno", "tool:space": "Ambiente", "tool:dimension": "Cota",
             "tool:radius_dim": "Cota de raio", "tool:angle_dim": "Cota de ângulo",
             "tool:level_mark": "Nível", "tool:text": "Texto", "tool:label": "Rótulo",
             "tool:line2d": "Linha", "tool:spline2d": "Curva", "tool:circle2d": "Círculo",
             "tool:arc2d": "Arco", "tool:hatch": "Hachura", "tool:north": "Norte",
             "tool:revision": "Alteração", "tool:section": "Corte",
             "tool:elevation": "Fachada", "tool:offset": "Deslocar paralela",
             "tool:trim": "Aparar/estender", "tool:fillet": "Concordar"}
    for key, alias in DEFAULT_ALIASES.items():
        assert 2 <= len(alias) <= 3 and alias.isalpha() and alias.isupper()
        name = normalize(names.get(key) or key.split("/")[-1])
        it = iter(name)  # letras na ordem dentro do nome em português (§7)
        assert all(ch in it for ch in alias.lower()), (alias, name)


def test_lc04_apelidos_editaveis():
    assert validate_aliases({"a": "PD", "b": "pd"}) == ["pd: repetido"]
    assert validate_aliases({"a": "1X"}) == ["1X: começa por letra"]
    assert validate_aliases({"a": "ABCDEFG"})[0].startswith("ABCDEFG: no máximo")
    assert validate_aliases({"a": "P-D"})[0].endswith("só letras e algarismos")
    assert validate_aliases({"a": "", "b": "X1"}) == []
    changed = dict(DEFAULT_ALIASES)
    changed["tool:wall"] = "pa1"
    del changed["tool:slab"]
    changed["menu:Arquivo/Salvar"] = "sv"
    diff = diff_aliases(changed)
    assert diff == {"tool:wall": "PA1", "tool:slab": "", "menu:Arquivo/Salvar": "SV"}
    merged = merge_aliases(diff)
    assert merged["tool:wall"] == "PA1" and "tool:slab" not in merged
    assert merged["menu:Arquivo/Salvar"] == "SV"
    assert merge_aliases({}) == DEFAULT_ALIASES


def test_lc05_historico():
    h = History(limit=3)
    assert h.step(-1) is None
    for text in ("pd", "0;0", "0;0", "@4;0"):
        h.add(text, "ok")
    assert len(h.lines) == 3
    assert h.texts() == ["0;0", "@4;0"]
    assert h.step(-1) == "@4;0"
    assert h.step(-1) == "0;0"
    assert h.step(-1) == "0;0"  # fica no primeiro
    assert h.step(1) == "@4;0"
    assert h.step(1) is None  # passou do fim: campo vazio
