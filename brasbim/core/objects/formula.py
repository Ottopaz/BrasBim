# SPDX-License-Identifier: LGPL-3.0-or-later
"""Fórmulas dos objetos paramétricos (``spec/elementos/objeto-parametrico.md`` §3.2).

Linguagem própria, analisada aqui e nunca executada como código Python:

- números com vírgula (ou ponto) decimal: ``0,60``; texto entre aspas: ``"redondo"``;
- ``+ - * / ^``, parênteses, ``= <> < <= > >=``, ``e``, ``ou``, ``não``;
- ``sim``/``não`` e ``verdadeiro``/``falso``; ``não`` seguido de um operando é a negação;
- funções com argumentos separados por ``;``: ``se``, ``mín``, ``máx``, ``arred``,
  ``arred_baixo``, ``arred_cima``, ``abs``, ``raiz``, ``sen``, ``cos``, ``tg`` (graus) e
  ``pi()``; o nome sem acento também vale.

Os nomes (parâmetros) não diferenciam maiúsculas. ``parse`` devolve a árvore (tuplas),
``names`` os nomes usados, ``infer`` o tipo do resultado (``number``, ``bool``, ``text``)
e ``evaluate`` o valor.
"""

from __future__ import annotations

import math

from brasbim.core.document import OpError

NUMBER, BOOL, TEXT = "number", "bool", "text"
_EPS = 1e-9


class FormulaError(OpError):
    """Fórmula inválida ou que não pode ser calculada com esses valores."""


def key(name: str) -> str:
    """Nome normalizado de um parâmetro (sem diferenciar maiúsculas)."""
    return name.strip().casefold()


_KEYWORDS = {"e": "and", "ou": "or", "não": "not", "nao": "not"}
_LITERALS = {"sim": True, "verdadeiro": True, "falso": False}
_FALSE_WORDS = ("não", "nao")
# nome → (mínimo, máximo de argumentos; None = qualquer)
_FUNCTIONS = {
    "se": (3, 3), "mín": (1, None), "min": (1, None), "máx": (1, None), "max": (1, None),
    "arred": (1, 2), "arred_baixo": (1, 1), "arred_cima": (1, 1), "abs": (1, 1),
    "raiz": (1, 1), "sen": (1, 1), "cos": (1, 1), "tg": (1, 1), "pi": (0, 0),
}
_ALIASES = {"mín": "min", "máx": "max"}
_COMPARE = ("=", "<>", "<", "<=", ">", ">=")


# --- análise -----------------------------------------------------------------------------


def _tokens(text: str) -> list[tuple[str, object]]:
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
        elif c.isdigit() or (c in ",." and i + 1 < n and text[i + 1].isdigit()):
            j = i
            seen_sep = False
            while j < n and (text[j].isdigit() or (text[j] in ",." and not seen_sep
                                                   and j + 1 < n and text[j + 1].isdigit())):
                seen_sep = seen_sep or text[j] in ",."
                j += 1
            out.append(("num", float(text[i:j].replace(",", "."))))
            i = j
        elif c.isalpha() or c == "_":
            j = i
            while j < n and (text[j].isalnum() or text[j] == "_"):
                j += 1
            out.append(("name", text[i:j]))
            i = j
        elif c == '"':
            j = text.find('"', i + 1)
            if j < 0:
                raise FormulaError("texto sem aspas de fechamento")
            out.append(("str", text[i + 1:j]))
            i = j + 1
        elif text.startswith(("<>", "<=", ">="), i):
            out.append(("op", text[i:i + 2]))
            i += 2
        elif c in "+-*/^()=<>;":
            out.append(("op", c))
            i += 1
        else:
            raise FormulaError(f"caractere inválido na fórmula: {c!r}")
    out.append(("end", None))
    return out


class _Parser:
    def __init__(self, text: str):
        self.tokens = _tokens(text)
        self.i = 0

    def peek(self, offset: int = 0):
        return self.tokens[min(self.i + offset, len(self.tokens) - 1)]

    def take(self):
        tok = self.tokens[self.i]
        self.i += 1
        return tok

    def accept(self, kind: str, value=None) -> bool:
        tok = self.peek()
        if tok[0] == kind and (value is None or tok[1] == value):
            self.i += 1
            return True
        return False

    def word(self, offset: int = 0) -> str | None:
        tok = self.peek(offset)
        return _KEYWORDS.get(key(tok[1])) if tok[0] == "name" else None

    def expect(self, value: str) -> None:
        if not self.accept("op", value):
            raise FormulaError(f"esperado '{value}'")

    def parse(self):
        node = self.or_()
        if self.peek()[0] != "end":
            raise FormulaError(f"sobra na fórmula: {self.peek()[1]!r}")
        return node

    def or_(self):
        node = self.and_()
        while self.word() == "or":
            self.take()
            node = ("bin", "or", node, self.and_())
        return node

    def and_(self):
        node = self.not_()
        while self.word() == "and":
            self.take()
            node = ("bin", "and", node, self.not_())
        return node

    def _starts_operand(self, offset: int) -> bool:
        tok = self.peek(offset)
        if tok[0] in ("num", "str"):
            return True
        if tok[0] == "op":
            return tok[1] in ("(", "-", "+")
        if tok[0] == "name":
            return _KEYWORDS.get(key(tok[1])) in (None, "not")
        return False

    def not_(self):
        if self.word() == "not" and self._starts_operand(1):
            self.take()
            return ("un", "not", self.not_())
        return self.compare()

    def compare(self):
        node = self.add()
        tok = self.peek()
        if tok[0] == "op" and tok[1] in _COMPARE:
            self.take()
            node = ("bin", tok[1], node, self.add())
        return node

    def add(self):
        node = self.mul()
        while self.peek()[0] == "op" and self.peek()[1] in "+-":
            op = self.take()[1]
            node = ("bin", op, node, self.mul())
        return node

    def mul(self):
        node = self.unary()
        while self.peek()[0] == "op" and self.peek()[1] in "*/":
            op = self.take()[1]
            node = ("bin", op, node, self.unary())
        return node

    def unary(self):
        if self.peek()[0] == "op" and self.peek()[1] in "+-":
            op = self.take()[1]
            node = self.unary()
            return node if op == "+" else ("un", "-", node)
        return self.power()

    def power(self):
        node = self.atom()
        if self.accept("op", "^"):
            node = ("bin", "^", node, self.unary())
        return node

    def atom(self):
        kind, value = self.take()
        if kind == "num":
            return ("num", value)
        if kind == "str":
            return ("str", value)
        if kind == "op" and value == "(":
            node = self.or_()
            self.expect(")")
            return node
        if kind == "name":
            k = key(value)
            if self.peek() == ("op", "("):
                if k not in _FUNCTIONS:
                    raise FormulaError(f"função desconhecida: {value}")
                self.take()
                args = []
                if not self.accept("op", ")"):
                    args.append(self.or_())
                    while self.accept("op", ";"):
                        args.append(self.or_())
                    self.expect(")")
                low, high = _FUNCTIONS[k]
                if len(args) < low or (high is not None and len(args) > high):
                    raise FormulaError(f"número de argumentos errado em {value}()")
                return ("call", _ALIASES.get(k, k), args)
            if k in _LITERALS:
                return ("bool", _LITERALS[k])
            if k in _FALSE_WORDS:
                return ("bool", False)
            if k in _KEYWORDS:
                raise FormulaError(f"'{value}' fora do lugar")
            return ("name", k)
        if kind == "end":
            raise FormulaError("fórmula incompleta")
        raise FormulaError(f"'{value}' fora do lugar")


def parse(text: str):
    """Árvore da fórmula; ``=`` no início é opcional (``= largura / 2``)."""
    text = (text or "").strip()
    text = text.removeprefix("=")
    if not text.strip():
        raise FormulaError("fórmula vazia")
    return _Parser(text).parse()


def names(node) -> set[str]:
    """Nomes de parâmetros usados na fórmula (normalizados)."""
    kind = node[0]
    if kind == "name":
        return {node[1]}
    if kind == "bin":
        return names(node[2]) | names(node[3])
    if kind == "un":
        return names(node[2])
    if kind == "call":
        return set().union(*(names(a) for a in node[2])) if node[2] else set()
    return set()


# --- tipos -------------------------------------------------------------------------------


def infer(node, types: dict[str, str]) -> str:
    """Tipo do resultado; ``types``: nome normalizado → tipo. Recusa mistura de tipos."""
    kind = node[0]
    if kind == "num":
        return NUMBER
    if kind == "str":
        return TEXT
    if kind == "bool":
        return BOOL
    if kind == "name":
        if node[1] not in types:
            raise FormulaError(f"nome desconhecido: {node[1]}")
        return types[node[1]]
    if kind == "un":
        inner = infer(node[2], types)
        want = BOOL if node[1] == "not" else NUMBER
        if inner != want:
            raise FormulaError(f"'{'não' if node[1] == 'not' else '-'}' pede "
                               f"{_noun(want)}, recebeu {_noun(inner)}")
        return want
    if kind == "bin":
        op, a, b = node[1], infer(node[2], types), infer(node[3], types)
        if op in ("and", "or"):
            if a != BOOL or b != BOOL:
                raise FormulaError(f"'{'e' if op == 'and' else 'ou'}' pede sim/não")
            return BOOL
        if op in _COMPARE:
            if a != b:
                raise FormulaError(f"comparação entre {_noun(a)} e {_noun(b)}")
            if a != NUMBER and op not in ("=", "<>"):
                raise FormulaError(f"'{op}' só compara números")
            return BOOL
        if a != NUMBER or b != NUMBER:
            raise FormulaError(f"'{op}' pede números, recebeu {_noun(a if a != NUMBER else b)}")
        return NUMBER
    # chamada
    name, args = node[1], node[2]
    kinds = [infer(a, types) for a in args]
    if name == "se":
        if kinds[0] != BOOL:
            raise FormulaError("o primeiro argumento de se() é uma condição (sim/não)")
        if kinds[1] != kinds[2]:
            raise FormulaError(f"se(): {_noun(kinds[1])} num caso e {_noun(kinds[2])} no outro")
        return kinds[1]
    if any(k != NUMBER for k in kinds):
        raise FormulaError(f"{name}() pede números")
    return NUMBER


def _noun(kind: str) -> str:
    return {NUMBER: "número", BOOL: "sim/não", TEXT: "texto"}[kind]


# --- cálculo -----------------------------------------------------------------------------


def _number(v) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise FormulaError(f"esperado número, recebeu {v!r}")
    return float(v)


def _check(v: float) -> float:
    if math.isnan(v) or math.isinf(v):
        raise FormulaError("resultado inválido (infinito)")
    return v


def evaluate(node, values: dict):
    """Valor da fórmula com ``values`` (nome normalizado → valor)."""
    kind = node[0]
    if kind in ("num", "str", "bool"):
        return node[1]
    if kind == "name":
        if node[1] not in values:
            raise FormulaError(f"nome desconhecido: {node[1]}")
        return values[node[1]]
    if kind == "un":
        v = evaluate(node[2], values)
        if node[1] == "not":
            return not bool(v)
        return -_number(v)
    if kind == "bin":
        op = node[1]
        if op == "and":
            return bool(evaluate(node[2], values)) and bool(evaluate(node[3], values))
        if op == "or":
            return bool(evaluate(node[2], values)) or bool(evaluate(node[3], values))
        a, b = evaluate(node[2], values), evaluate(node[3], values)
        if op in _COMPARE:
            return _compare(op, a, b)
        a, b = _number(a), _number(b)
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if op == "/":
            if abs(b) < _EPS:
                raise FormulaError("divisão por zero")
            return a / b
        try:
            return _check(math.pow(a, b))
        except (OverflowError, ValueError):
            raise FormulaError("potência inválida") from None
    name, args = node[1], node[2]
    if name == "se":
        return evaluate(args[1] if evaluate(args[0], values) else args[2], values)
    nums = [_number(evaluate(a, values)) for a in args]
    return _call(name, nums)


def _compare(op: str, a, b) -> bool:
    if isinstance(a, (int, float)) and not isinstance(a, bool) and \
            isinstance(b, (int, float)) and not isinstance(b, bool):
        if op == "=":
            return abs(a - b) <= _EPS
        if op == "<>":
            return abs(a - b) > _EPS
        return {"<": a < b - _EPS, "<=": a <= b + _EPS, ">": a > b + _EPS,
                ">=": a >= b - _EPS}[op]
    if op == "=":
        return a == b
    if op == "<>":
        return a != b
    raise FormulaError(f"'{op}' só compara números")


def _call(name: str, args: list[float]) -> float:
    if name == "min":
        return min(args)
    if name == "max":
        return max(args)
    if name == "arred":
        digits = int(args[1]) if len(args) > 1 else 0
        scale = 10 ** digits
        return math.floor(args[0] * scale + 0.5) / scale
    if name == "arred_baixo":
        return float(math.floor(args[0] + _EPS))
    if name == "arred_cima":
        return float(math.ceil(args[0] - _EPS))
    if name == "abs":
        return abs(args[0])
    if name == "raiz":
        if args[0] < 0:
            raise FormulaError("raiz de número negativo")
        return math.sqrt(args[0])
    if name == "sen":
        return math.sin(math.radians(args[0]))
    if name == "cos":
        return math.cos(math.radians(args[0]))
    if name == "tg":
        c = math.cos(math.radians(args[0]))
        if abs(c) < _EPS:
            raise FormulaError("tangente infinita")
        return math.tan(math.radians(args[0]))
    if name == "pi":
        return math.pi
    raise FormulaError(f"função desconhecida: {name}")  # pragma: no cover


def calc(text, values: dict | None = None):
    """Atalho: valor de um número ou de uma fórmula em texto."""
    if isinstance(text, (int, float)) and not isinstance(text, bool):
        return float(text)
    return evaluate(parse(str(text)), {key(k): v for k, v in (values or {}).items()})
