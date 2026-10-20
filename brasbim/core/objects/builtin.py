# SPDX-License-Identifier: LGPL-3.0-or-later
"""Biblioteca inicial do BrasBim (``spec/elementos/objeto-parametrico.md`` §4.5).

Feita do zero para o BrasBim, licença CC BY 4.0. As medidas são as usuais no mercado
brasileiro (conhecimento geral), arredondadas, como ponto de partida; a altura da bacia
acessível fica a conferir na NBR 9050. ``scripts/gerar_biblioteca.py`` grava estes
objetos em ``brasbim/library/objetos/``.

Convenção das peças: origem no ponto de inserção, x para a direita, y para trás (a frente
olha para −y), z para cima. ``FILES`` diz em que arquivo (e pasta, a subcategoria) cada
objeto vai.
"""

from __future__ import annotations

from brasbim.core import guid
from brasbim.core.objects import definition as od

_NAMESPACE = "BrasBim/biblioteca/objetos"
P, B, C = od.new_param, od.new_piece, od.new_symbol_item


def _defn(name: str, category: str, predefined: str, params, pieces, **extra) -> dict:
    defn = od.new_definition(name, category, predefined_type=predefined, params=params,
                             pieces=pieces, **extra)
    defn["object_id"] = guid.derived(_NAMESPACE, name)
    return defn


def _types(defn: dict, *types) -> list[dict]:
    """Estados de tipo: (nome, valores de tipo, padrões de ocorrência)."""
    out = []
    for name, values, *rest in types:
        out.append({"name": name, "definition": defn, "values": dict(values),
                    "defaults": dict(rest[0]) if rest else {}, "library": None})
    return out


def _wavy(radius: str, points: int = 12, inner: float = 0.82) -> list[list[str]]:
    """Contorno ondulado (copa, arbusto) com raios alternados, em fórmulas."""
    out = []
    for k in range(points):
        a = 360.0 * k / points
        r = f"{radius} * {1.0 if k % 2 == 0 else inner:.2f}".replace(".", ",")
        out.append([f"{r} * cos({a:.1f})".replace(".", ","),
                    f"{r} * sen({a:.1f})".replace(".", ",")])
    return out


def _f(value: float) -> str:
    return f"{value:g}".replace(".", ",")


# --- mobiliário: quarto ---------------------------------------------------------------------


def cama() -> list[dict]:
    pillows = "se(largura > 1,2; 2; 1)"
    pillow_w = f"(largura - 0,10 * ({pillows} + 1)) / {pillows}"
    defn = _defn("Cama", "furniture", "BED", [
        P("largura", "length", "type", 1.38, min=0.6, max=2.5, label="Largura"),
        P("comprimento", "length", "type", 1.88, min=1.5, max=2.5, label="Comprimento"),
        P("colchao", "length", "type", 0.25, min=0.10, max=0.45, label="Altura do colchão"),
        P("cabeceira", "bool", "type", True, label="Cabeceira"),
    ], [
        B("box", name="Estrado", width="largura", depth="comprimento", height=0.30,
          role="Frame", material="Madeira"),
        B("box", name="Colchão", z=0.30, width="largura", depth="comprimento",
          height="colchao", role="Padding", material="Tecido"),
        B("box", name="Travesseiro", x=0.10, y="comprimento - 0,45", z="0,30 + colchao",
          width=pillow_w, depth=0.35, height=0.12, role="Padding", material="Tecido",
          repeat={"count": pillows, "dx": f"{pillow_w} + 0,10"}),
        B("box", name="Cabeceira", y="comprimento", width="largura", depth=0.05,
          height=1.0, role="Frame", material="Madeira", visible="cabeceira"),
    ], description="Cama com estrado, colchão, travesseiros e cabeceira opcional.")
    return _types(defn,
                  ("Cama de solteiro 0,88 × 1,88", {"largura": 0.88, "comprimento": 1.88}),
                  ("Cama de casal 1,38 × 1,88", {"largura": 1.38, "comprimento": 1.88}),
                  ("Cama queen 1,58 × 1,98", {"largura": 1.58, "comprimento": 1.98}),
                  ("Cama king 1,93 × 2,03", {"largura": 1.93, "comprimento": 2.03}))


def criado_mudo() -> list[dict]:
    step = "(altura - 0,10) / gavetas"
    defn = _defn("Criado-mudo", "furniture", "USERDEFINED", [
        P("largura", "length", "type", 0.45, min=0.30, label="Largura"),
        P("profundidade", "length", "type", 0.40, min=0.25, label="Profundidade"),
        P("altura", "length", "type", 0.55, min=0.35, label="Altura"),
        P("gavetas", "integer", "type", 2, min=1, max=4, label="Gavetas"),
    ], [
        B("box", name="Corpo", y=0.01, width="largura", depth="profundidade - 0,01",
          height="altura", role="Frame", material="Madeira MDF branca"),
        B("box", name="Frente da gaveta", x=0.02, z=0.06, width="largura - 0,04", depth=0.01,
          height=f"{step} - 0,02", role="Finish", material="Madeira",
          repeat={"count": "gavetas", "dz": step}),
    ], element_type="Criado-mudo")
    return _types(defn, ("Criado-mudo 0,45 × 0,40", {}))


def guarda_roupa() -> list[dict]:
    defn = _defn("Guarda-roupa", "furniture", "USERDEFINED", [
        P("largura", "length", "occurrence", 1.50, min=0.6, max=4.0, label="Largura",
          handle={"axis": "x", "side": "end"}),
        P("profundidade", "length", "type", 0.60, min=0.45, label="Profundidade"),
        P("altura", "length", "type", 2.40, min=1.6, max=2.8, label="Altura"),
        P("portas", "integer", "type", 3, min=1, max=6, label="Portas"),
        P("abertura", "choice", "type", "de abrir", options=["de abrir", "de correr"],
          label="Portas de"),
    ], [
        B("box", name="Corpo", y=0.02, width="largura", depth="profundidade - 0,02",
          height="altura", role="Frame", material="Madeira MDF branca"),
        B("box", name="Porta", x=0.003, width="largura / portas - 0,006", depth=0.02,
          height="altura - 0,02", z=0.01, role="Finish", material="Madeira",
          visible='abertura = "de abrir"', repeat={"count": "portas", "dx": "largura / portas"}),
        B("box", name="Puxador", x="largura / portas - 0,05", y=-0.02, z="altura / 2 - 0,15",
          width=0.02, depth=0.02, height=0.30, role="Hardware", material="Alumínio",
          visible='abertura = "de abrir"', repeat={"count": "portas", "dx": "largura / portas"}),
        B("box", name="Porta de correr da frente", y=-0.02, z=0.01,
          width="largura / 2 + 0,02", depth=0.02, height="altura - 0,02", role="Finish",
          material="Madeira", visible='abertura = "de correr"'),
        B("box", name="Porta de correr de trás", x="largura / 2 - 0,02", z=0.01,
          width="largura / 2 + 0,02", depth=0.02, height="altura - 0,02", role="Finish",
          material="Madeira", visible='abertura = "de correr"'),
    ], element_type="Guarda-roupa")
    return _types(defn,
                  ("Guarda-roupa 2 portas", {"portas": 2}, {"largura": 1.00}),
                  ("Guarda-roupa 3 portas", {"portas": 3}, {"largura": 1.50}),
                  ("Guarda-roupa 4 portas de correr", {"portas": 4, "abertura": "de correr"},
                   {"largura": 2.00}))


# --- mobiliário: sala e jantar ---------------------------------------------------------------


def _sofa(name: str, seats: int | None) -> dict:
    params = [
        P("lugares", "integer", "type", seats or 1, min=1, max=5, label="Lugares"),
        P("assento", "length", "type", 0.65 if seats else 0.70, min=0.45,
          label="Largura por lugar"),
        P("com_braco", "bool", "type", True, label="Com braços"),
        P("braco", "length", "type", 0.18, min=0.08, label="Largura do braço"),
        P("profundidade", "length", "type", 0.90, min=0.6, label="Profundidade"),
        P("largura", "length", "type",
          formula="lugares * assento + se(com_braco; 2 * braco; 0)", label="Largura"),
    ]
    x0 = "se(com_braco; braco; 0)"
    pieces = [
        B("box", name="Base", x=x0, z=0.10, width="lugares * assento",
          depth="profundidade - 0,20", height=0.25, role="Frame", material="Madeira"),
        B("box", name="Almofada", x=x0, z=0.35, width="assento - 0,01",
          depth="profundidade - 0,22", height=0.10, role="Padding", material="Tecido",
          repeat={"count": "lugares", "dx": "assento"}),
        B("box", name="Encosto", y="profundidade - 0,20", width="largura", depth=0.20,
          height=0.85, role="Padding", material="Tecido"),
        B("box", name="Braço esquerdo", width="braco", depth="profundidade - 0,20",
          height=0.60, role="Padding", material="Tecido", visible="com_braco"),
        B("box", name="Braço direito", x="largura - braco", width="braco",
          depth="profundidade - 0,20", height=0.60, role="Padding", material="Tecido",
          visible="com_braco"),
    ]
    return _defn(name, "furniture", "SOFA" if seats else "CHAIR", params, pieces)


def sofa() -> list[dict]:
    defn = _sofa("Sofá", 3)
    return _types(defn, ("Sofá 2 lugares", {"lugares": 2}), ("Sofá 3 lugares", {"lugares": 3}))


def poltrona() -> list[dict]:
    defn = _sofa("Poltrona", None)
    for p in defn["params"]:
        if p["name"] == "lugares":
            p.update(formula="1", value=None, min=None, max=None)
    return _types(defn, ("Poltrona", {}))


def cadeira() -> list[dict]:
    defn = _defn("Cadeira", "furniture", "CHAIR", [
        P("assento", "length", "type", 0.45, min=0.35, max=0.60, label="Altura do assento"),
        P("largura", "length", "type", 0.45, min=0.35, label="Largura"),
    ], [
        B("box", name="Assento", x="-largura / 2", y=-0.22, z="assento - 0,04",
          width="largura", depth=0.44, height=0.04, role="Frame", material="Madeira"),
        B("box", name="Encosto", x="-largura / 2", y=0.19, z="assento",
          width="largura", depth=0.03, height="0,90 - assento", role="Frame",
          material="Madeira"),
        B("cylinder", name="Pé da frente", x="-largura / 2 + 0,03", y=-0.19, radius=0.015,
          height="assento - 0,04", role="Frame", material="Madeira",
          repeat={"count": 2, "dx": "largura - 0,06"}),
        B("cylinder", name="Pé de trás", x="-largura / 2 + 0,03", y=0.19, radius=0.015,
          height="assento - 0,04", role="Frame", material="Madeira",
          repeat={"count": 2, "dx": "largura - 0,06"}),
    ], description="Origem no centro do assento.")
    return _types(defn, ("Cadeira", {}))


def mesa_jantar() -> list[dict]:
    rect = 'tampo = "retangular"'
    round_ = 'tampo = "redondo"'
    defn = _defn("Mesa de jantar", "furniture", "TABLE", [
        P("comprimento", "length", "occurrence", 1.80, min=0.80, max=4.0,
          label="Comprimento", handle={"axis": "x", "side": "end"}),
        P("largura", "length", "type", 0.90, min=0.60, label="Largura"),
        P("altura", "length", "type", 0.75, min=0.60, label="Altura"),
        P("tampo", "choice", "type", "retangular", options=["retangular", "redondo"],
          label="Tampo"),
        P("cadeira", "object_type", "type", "Cadeira", label="Cadeira",
          accepts={"category": "furniture", "predefined_type": "CHAIR"}),
        P("lugares", "integer", "occurrence",
          formula='se(tampo = "redondo"; 4; arred_baixo(comprimento / 0,60) * 2)',
          label="Lugares"),
    ], [
        B("box", name="Tampo", z="altura - 0,03", width="comprimento", depth="largura",
          height=0.03, role="Frame", material="Madeira", visible=rect),
        B("cylinder", name="Tampo redondo", x="largura / 2", y="largura / 2",
          z="altura - 0,03", radius="largura / 2", height=0.03, role="Frame",
          material="Madeira", visible=round_),
        B("box", name="Pé", x=0.05, y=0.05, width=0.06, depth=0.06, height="altura - 0,03",
          role="Frame", material="Madeira", visible=rect,
          repeat={"count": 2, "dx": "comprimento - 0,16"}),
        B("box", name="Pé de trás", x=0.05, y="largura - 0,11", width=0.06, depth=0.06,
          height="altura - 0,03", role="Frame", material="Madeira", visible=rect,
          repeat={"count": 2, "dx": "comprimento - 0,16"}),
        B("cylinder", name="Coluna", x="largura / 2", y="largura / 2", radius=0.06,
          height="altura - 0,03", role="Frame", material="Madeira", visible=round_),
        B("object", name="Cadeiras da frente", type={"param": "cadeira"},
          x="comprimento / lugares", y=-0.10, rotation=180, visible=rect,
          repeat={"count": "lugares / 2", "dx": "comprimento / (lugares / 2)"}),
        B("object", name="Cadeiras de trás", type={"param": "cadeira"},
          x="comprimento / lugares", y="largura + 0,10", visible=rect,
          repeat={"count": "lugares / 2", "dx": "comprimento / (lugares / 2)"}),
        B("object", name="Cadeira da frente", type={"param": "cadeira"}, x="largura / 2",
          y=-0.10, rotation=180, visible=round_),
        B("object", name="Cadeira de trás", type={"param": "cadeira"}, x="largura / 2",
          y="largura + 0,10", visible=round_),
        B("object", name="Cadeira da esquerda", type={"param": "cadeira"}, x=-0.10,
          y="largura / 2", rotation=90, visible=round_),
        B("object", name="Cadeira da direita", type={"param": "cadeira"},
          x="largura + 0,10", y="largura / 2", rotation=-90, visible=round_),
    ])
    return _types(defn,
                  ("Mesa de jantar 4 lugares", {"largura": 0.80}, {"comprimento": 1.20}),
                  ("Mesa de jantar 6 lugares", {}, {"comprimento": 1.80}),
                  ("Mesa de jantar 8 lugares", {}, {"comprimento": 2.40}),
                  ("Mesa de jantar redonda", {"largura": 1.10, "tampo": "redondo"},
                   {"comprimento": 1.10}))


def mesa_centro() -> list[dict]:
    defn = _defn("Mesa de centro", "furniture", "TABLE", [
        P("comprimento", "length", "type", 1.00, min=0.40, label="Comprimento"),
        P("largura", "length", "type", 0.60, min=0.30, label="Largura"),
        P("altura", "length", "type", 0.40, min=0.25, label="Altura"),
    ], [
        B("box", name="Tampo", z="altura - 0,03", width="comprimento", depth="largura",
          height=0.03, role="Frame", material="Madeira"),
        B("box", name="Base", x=0.10, y=0.10, width="comprimento - 0,20",
          depth="largura - 0,20", height="altura - 0,03", role="Frame", material="Madeira"),
    ])
    return _types(defn, ("Mesa de centro 1,00 × 0,60", {}))


def estante() -> list[dict]:
    defn = _defn("Estante", "furniture", "SHELF", [
        P("largura", "length", "occurrence", 0.80, min=0.40, max=3.0, label="Largura",
          handle={"axis": "x", "side": "end"}),
        P("profundidade", "length", "type", 0.30, min=0.20, label="Profundidade"),
        P("altura", "length", "type", 1.80, min=0.60, label="Altura"),
        P("prateleiras", "integer", "type", 5, min=2, max=10, label="Prateleiras"),
    ], [
        B("box", name="Lateral", width=0.02, depth="profundidade", height="altura",
          role="Frame", material="Madeira", repeat={"count": 2, "dx": "largura - 0,02"}),
        B("box", name="Prateleira", x=0.02, z=0.05, width="largura - 0,04",
          depth="profundidade", height=0.02, role="Frame", material="Madeira",
          repeat={"count": "prateleiras", "dz": 1, "length": "altura - 0,07"}),
    ])
    return _types(defn, ("Estante 0,80", {}, {"largura": 0.80}),
                  ("Estante 1,20", {}, {"largura": 1.20}))


def escrivaninha() -> list[dict]:
    defn = _defn("Escrivaninha", "furniture", "DESK", [
        P("largura", "length", "type", 1.20, min=0.60, label="Largura"),
        P("profundidade", "length", "type", 0.60, min=0.40, label="Profundidade"),
        P("altura", "length", "type", 0.75, min=0.65, label="Altura"),
        P("gaveteiro", "bool", "type", True, label="Gaveteiro"),
    ], [
        B("box", name="Tampo", z="altura - 0,025", width="largura", depth="profundidade",
          height=0.025, role="Frame", material="Madeira MDF branca"),
        B("box", name="Lateral", width=0.025, depth="profundidade", height="altura - 0,025",
          role="Frame", material="Madeira MDF branca",
          repeat={"count": 2, "dx": "largura - 0,025"}),
        B("box", name="Gaveteiro", x="largura - 0,45", y=0.02, width=0.40,
          depth="profundidade - 0,06", height="altura - 0,10", role="Frame",
          material="Madeira", visible="gaveteiro"),
    ])
    return _types(defn, ("Escrivaninha 1,00", {"largura": 1.00}),
                  ("Escrivaninha 1,20", {"largura": 1.20}))


# --- mobiliário: cozinha ------------------------------------------------------------------------


def armario_baixo() -> list[dict]:
    defn = _defn("Armário de cozinha baixo", "furniture", "USERDEFINED", [
        P("largura", "length", "occurrence", 0.60, min=0.20, max=3.0, label="Largura",
          handle={"axis": "x", "side": "end"}),
        P("profundidade", "length", "type", 0.55, min=0.30, label="Profundidade"),
        P("altura", "length", "type", 0.85, min=0.60, label="Altura"),
        P("portas", "integer", "type", 2, min=1, max=4, label="Portas"),
    ], [
        B("box", name="Rodapé", y=0.05, width="largura", depth="profundidade - 0,05",
          height=0.10, role="Frame", material="Madeira MDF branca"),
        B("box", name="Corpo", y=0.02, z=0.10, width="largura", depth="profundidade - 0,02",
          height="altura - 0,10", role="Frame", material="Madeira MDF branca"),
        B("box", name="Porta", x=0.003, z=0.11, width="largura / portas - 0,006", depth=0.02,
          height="altura - 0,12", role="Finish", material="Madeira MDF branca",
          repeat={"count": "portas", "dx": "largura / portas"}),
    ], element_type="Armário de cozinha")
    return _types(defn, ("Armário baixo 0,40", {"portas": 1}, {"largura": 0.40}),
                  ("Armário baixo 0,60", {}, {"largura": 0.60}),
                  ("Armário baixo 0,80", {}, {"largura": 0.80}))


def armario_alto() -> list[dict]:
    defn = _defn("Armário de cozinha alto", "furniture", "USERDEFINED", [
        P("largura", "length", "occurrence", 0.80, min=0.20, max=3.0, label="Largura",
          handle={"axis": "x", "side": "end"}),
        P("profundidade", "length", "type", 0.35, min=0.20, label="Profundidade"),
        P("altura", "length", "type", 0.70, min=0.30, label="Altura"),
        P("portas", "integer", "type", 2, min=1, max=4, label="Portas"),
    ], [
        B("box", name="Corpo", y=0.02, width="largura", depth="profundidade - 0,02",
          height="altura", role="Frame", material="Madeira MDF branca"),
        B("box", name="Porta", x=0.003, z=0.01, width="largura / portas - 0,006", depth=0.02,
          height="altura - 0,02", role="Finish", material="Madeira MDF branca",
          repeat={"count": "portas", "dx": "largura / portas"}),
    ], element_type="Armário de cozinha", hosting="wall", elevation=1.50)
    return _types(defn, ("Armário alto 0,60", {}, {"largura": 0.60}),
                  ("Armário alto 0,80", {}, {"largura": 0.80}),
                  ("Armário alto 1,20", {"portas": 3}, {"largura": 1.20}))


# --- louças e metais -------------------------------------------------------------------------------


def _oval(cx: str, cy: str, rx: str, ry: str, steps: int = 16) -> list[list[str]]:
    out = []
    for k in range(steps):
        a = 360.0 * k / steps
        out.append([f"{cx} + {rx} * cos({_f(round(a, 1))})",
                    f"{cy} + {ry} * sen({_f(round(a, 1))})"])
    return out


def bacia() -> list[dict]:
    defn = _defn("Bacia sanitária com caixa acoplada", "sanitary", "TOILETPAN", [
        P("assento", "length", "type", 0.40, min=0.35, max=0.50, label="Altura do assento"),
    ], [
        B("extrusion", name="Bacia", plane="xy", thickness="assento - 0,02",
          points=_oval("0", "0,26", "0,18", "0,26"), role="Body", material="Louça"),
        B("extrusion", name="Assento", plane="xy", offset="assento - 0,02", thickness=0.02,
          points=_oval("0", "0,26", "0,18", "0,25"), role="Finish", material="Louça"),
        B("box", name="Caixa acoplada", x=-0.19, y=0.50, width=0.38, depth=0.18,
          height="assento + 0,40", role="Body", material="Louça"),
    ], description="Origem no centro da frente da bacia; o fundo encosta na parede. "
                   "Altura do assento da bacia acessível a conferir na NBR 9050.")
    return _types(defn, ("Bacia com caixa acoplada", {}),
                  ("Bacia com caixa acoplada acessível", {"assento": 0.46}))


def lavatorio_coluna() -> list[dict]:
    defn = _defn("Lavatório de coluna", "sanitary", "WASHHANDBASIN", [
        P("largura", "length", "type", 0.55, min=0.40, label="Largura"),
        P("altura", "length", "type", 0.85, min=0.70, label="Altura"),
    ], [
        B("box", name="Cuba", x="-largura / 2", z="altura - 0,18", width="largura",
          depth=0.45, height=0.18, role="Body", material="Louça"),
        B("box", name="Coluna", x=-0.09, y=0.20, width=0.18, depth=0.25,
          height="altura - 0,18", role="Body", material="Louça"),
    ], symbol={"mode": "drawn", "items": [
        C("rect", x="-largura / 2", width="largura", depth=0.45),
        C("polyline", points=_oval("0", "0,20", "largura / 2 - 0,06", "0,15"), closed=True),
        C("circle", x=0, y=0.20, radius=0.02),
    ]})
    return _types(defn, ("Lavatório de coluna", {}))


def lavatorio_suspenso() -> list[dict]:
    defn = _defn("Lavatório suspenso", "sanitary", "WASHHANDBASIN", [
        P("largura", "length", "type", 0.50, min=0.40, label="Largura"),
    ], [
        B("box", name="Cuba", x="-largura / 2", width="largura", depth=0.42, height=0.18,
          role="Body", material="Louça"),
    ], hosting="wall", elevation=0.70, symbol={"mode": "drawn", "items": [
        C("rect", x="-largura / 2", width="largura", depth=0.42),
        C("polyline", points=_oval("0", "0,19", "largura / 2 - 0,06", "0,14"), closed=True),
        C("circle", x=0, y=0.19, radius=0.02),
    ]})
    return _types(defn, ("Lavatório suspenso", {}))


def bancada() -> list[dict]:
    defn = _defn("Bancada com cuba", "sanitary", "SINK", [
        P("comprimento", "length", "occurrence", 1.20, min=0.60, max=4.0,
          label="Comprimento", handle={"axis": "x", "side": "end"}),
        P("profundidade", "length", "type", 0.55, min=0.40, label="Profundidade"),
        P("altura", "length", "type", 0.90, min=0.70, label="Altura"),
        P("espessura", "length", "type", 0.03, min=0.01, label="Espessura do tampo"),
        P("cuba", "length", "occurrence", 0.60, min=0.25, label="Centro da cuba"),
        P("tampo", "material", "type", "Granito", label="Material do tampo"),
    ], [
        B("box", name="Tampo", z="altura - espessura", width="comprimento",
          depth="profundidade", height="espessura", role="Finish",
          material={"param": "tampo"}),
        B("box", name="Cuba", x="cuba - 0,20", y=0.10, z="altura - espessura - 0,15",
          width=0.40, depth="profundidade - 0,20", height=0.15, role="Body",
          material="Inox"),
    ], symbol={"mode": "drawn", "items": [
        C("rect", width="comprimento", depth="profundidade"),
        C("rect", x="cuba - 0,20", y=0.10, width=0.40, depth="profundidade - 0,20"),
        C("circle", x="cuba", y="profundidade / 2", radius=0.025),
    ]})
    return _types(defn,
                  ("Bancada de banheiro", {"altura": 0.80}, {"comprimento": 1.20}),
                  ("Bancada de cozinha", {"profundidade": 0.60},
                   {"comprimento": 1.80, "cuba": 0.90}))


def tanque() -> list[dict]:
    defn = _defn("Tanque", "sanitary", "SINK", [
        P("largura", "length", "type", 0.55, min=0.40, label="Largura"),
    ], [
        B("box", name="Tanque", x="-largura / 2", z=0.55, width="largura", depth=0.50,
          height=0.30, role="Body", material="Louça"),
        B("box", name="Coluna", x=-0.10, y=0.20, width=0.20, depth=0.28, height=0.55,
          role="Body", material="Louça"),
    ], hosting="wall", symbol={"mode": "drawn", "items": [
        C("rect", x="-largura / 2", width="largura", depth=0.50),
        C("rect", x="-largura / 2 + 0,05", y=0.05, width="largura - 0,10", depth=0.30),
        C("circle", x=0, y=0.20, radius=0.025),
    ]})
    return _types(defn, ("Tanque", {}))


def chuveiro() -> list[dict]:
    defn = _defn("Chuveiro com box", "sanitary", "SHOWER", [
        P("largura", "length", "occurrence", 0.90, min=0.70, max=2.0, label="Largura",
          handle={"axis": "x", "side": "end"}),
        P("profundidade", "length", "occurrence", 0.90, min=0.70, max=2.0,
          label="Profundidade"),
        P("box", "choice", "type", "box de correr",
          options=["sem box", "box de correr", "box de abrir"], label="Box"),
    ], [
        B("box", name="Piso", width="largura", depth="profundidade", height=0.02,
          role="Finish", material="Louça"),
        B("cylinder", name="Ducha", x="largura / 2", y="profundidade - 0,25", z=2.10,
          radius=0.10, height=0.03, role="Body", material="Inox"),
        B("box", name="Vidro fixo", y=-0.01, z=0.02, width="largura / 2 + 0,05", depth=0.01,
          height=1.90, role="Finish", material="Vidro", visible='box = "box de correr"'),
        B("box", name="Vidro de correr", x="largura / 2 - 0,05", y=-0.03, z=0.02,
          width="largura / 2 + 0,05", depth=0.01, height=1.90, role="Finish",
          material="Vidro", visible='box = "box de correr"'),
        B("box", name="Porta de vidro", y=-0.01, z=0.02, width="largura", depth=0.01,
          height=1.90, role="Finish", material="Vidro", visible='box = "box de abrir"'),
    ], symbol={"mode": "drawn", "items": [
        C("rect", width="largura", depth="profundidade"),
        C("line", points=[[0, 0], ["largura", "profundidade"]]),
        C("line", points=[["largura", 0], [0, "profundidade"]]),
        C("circle", x="largura / 2", y="profundidade / 2", radius=0.04),
        C("line", points=[[0, -0.02], ["largura", -0.02]], visible='box <> "sem box"'),
    ]})
    return _types(defn, ("Chuveiro sem box", {"box": "sem box"}),
                  ("Chuveiro com box de correr", {"box": "box de correr"}),
                  ("Chuveiro com box de abrir", {"box": "box de abrir"}))


def mictorio() -> list[dict]:
    defn = _defn("Mictório", "sanitary", "URINAL", [], [
        B("extrusion", name="Mictório", plane="xy", offset=0, thickness=0.60,
          points=_oval("0", "0,15", "0,18", "0,15", 12), role="Body", material="Louça"),
    ], hosting="wall", elevation=0.45)
    return _types(defn, ("Mictório", {}))


# --- eletrodomésticos -----------------------------------------------------------------------------


def _appliance(name, predefined, width, depth, height, doors_param=None, elevation=0.0,
               **extra) -> dict:
    params = [
        P("largura", "length", "type", width, min=0.2, label="Largura"),
        P("profundidade", "length", "type", depth, min=0.2, label="Profundidade"),
        P("altura", "length", "type", height, min=0.2, label="Altura"),
    ]
    pieces = [B("box", name="Corpo", y=0.02, width="largura", depth="profundidade - 0,02",
                height="altura", role="Body", material="Eletrodoméstico"),
              B("box", name="Frente", width="largura", depth=0.02, height="altura",
                role="Finish", material="Eletrodoméstico")]
    return _defn(name, "appliance", predefined, params + (doors_param or []), pieces,
                 elevation=elevation, **extra)


def geladeira() -> list[dict]:
    defn = _appliance("Geladeira", "REFRIGERATOR", 0.70, 0.72, 1.80)
    defn["params"].append(P("portas", "choice", "type", "duas portas",
                            options=["uma porta", "duas portas", "lado a lado"],
                            label="Portas"))
    defn["pieces"][1].update(visible='portas = "uma porta"')
    defn["pieces"] += [
        B("box", name="Porta do freezer", z="altura * 0,70 + 0,005", width="largura",
          depth=0.02, height="altura * 0,30 - 0,005", role="Finish",
          material="Eletrodoméstico", visible='portas = "duas portas"'),
        B("box", name="Porta do refrigerador", width="largura", depth=0.02,
          height="altura * 0,70 - 0,005", role="Finish", material="Eletrodoméstico",
          visible='portas = "duas portas"'),
        B("box", name="Porta do lado a lado", width="largura / 2 - 0,005", depth=0.02,
          height="altura", role="Finish", material="Eletrodoméstico",
          visible='portas = "lado a lado"', repeat={"count": 2, "dx": "largura / 2 + 0,005"}),
    ]
    return _types(defn,
                  ("Geladeira uma porta", {"largura": 0.60, "profundidade": 0.68,
                                           "altura": 1.60, "portas": "uma porta"}),
                  ("Geladeira duas portas", {}),
                  ("Geladeira lado a lado", {"largura": 0.90, "profundidade": 0.75,
                                             "portas": "lado a lado"}))


def fogao() -> list[dict]:
    defn = _defn("Fogão", "appliance", "ELECTRICCOOKER", [
        P("bocas", "choice", "type", "4", options=["4", "5", "6"], label="Bocas"),
        P("largura", "length", "type",
          formula='se(bocas = "4"; 0,50; se(bocas = "5"; 0,76; 0,80))', label="Largura"),
        P("profundidade", "length", "type", 0.60, min=0.45, label="Profundidade"),
        P("altura", "length", "type", 0.85, min=0.80, label="Altura"),
        P("por_fila", "integer", "type", formula='se(bocas = "6"; 3; 2)',
          label="Bocas por fila"),
    ], [
        B("box", name="Corpo", width="largura", depth="profundidade", height="altura",
          role="Body", material="Eletrodoméstico"),
        B("cylinder", name="Boca da frente", x="largura / (por_fila + 1)", y=0.17,
          z="altura", radius=0.05, height=0.02, role="Finish", material="Inox",
          repeat={"count": "por_fila", "dx": "largura / (por_fila + 1)"}),
        B("cylinder", name="Boca de trás", x="largura / (por_fila + 1)",
          y="profundidade - 0,17", z="altura", radius=0.05, height=0.02, role="Finish",
          material="Inox", repeat={"count": "por_fila", "dx": "largura / (por_fila + 1)"}),
        B("cylinder", name="Boca do centro", x="largura / 2", y="profundidade / 2",
          z="altura", radius=0.06, height=0.02, role="Finish", material="Inox",
          visible='bocas = "5"'),
    ])
    return _types(defn, ("Fogão 4 bocas", {"bocas": "4"}), ("Fogão 5 bocas", {"bocas": "5"}),
                  ("Fogão 6 bocas", {"bocas": "6"}))


def micro_ondas() -> list[dict]:
    return _types(_appliance("Micro-ondas", "MICROWAVE", 0.50, 0.40, 0.30, elevation=0.92),
                  ("Micro-ondas", {}))


def lavadora() -> list[dict]:
    defn = _appliance("Máquina de lavar roupa", "WASHINGMACHINE", 0.60, 0.65, 1.00)
    defn["symbol"] = {"mode": "drawn", "items": [
        C("rect", width="largura", depth="profundidade"),
        C("circle", x="largura / 2", y="profundidade / 2", radius="largura / 2 - 0,08"),
    ]}
    return _types(defn, ("Máquina de lavar roupa", {}))


def lava_loucas() -> list[dict]:
    return _types(_appliance("Lava-louças", "DISHWASHER", 0.60, 0.60, 0.85),
                  ("Lava-louças", {}))


# --- vegetação ----------------------------------------------------------------------------------


def _crown(r: str, z0: str, top: str) -> list[list[str]]:
    """Perfil da copa (meia elipse) para a revolução, de ``z0`` a ``top``."""
    h = f"({top} - {z0})"
    return [["0", z0], [f"{r} * 0,65", f"{z0} + {h} * 0,05"],
            [f"{r}", f"{z0} + {h} * 0,40"], [f"{r} * 0,85", f"{z0} + {h} * 0,75"],
            [f"{r} * 0,40", f"{z0} + {h} * 0,97"], ["0", top]]


def arvore() -> list[dict]:
    defn = _defn("Árvore", "vegetation", "VEGETATION", [
        P("copa", "length", "occurrence", 4.0, min=0.5, max=30.0, label="Diâmetro da copa"),
        P("altura", "length", "occurrence", 6.0, min=1.0, max=40.0, label="Altura"),
        P("tronco", "number", "type", 0.40, min=0.1, max=0.8, label="Fração do tronco"),
        P("altura_tronco", "length", "occurrence", formula="altura * tronco",
          label="Altura do tronco"),
    ], [
        B("cylinder", name="Tronco", radius="máx(copa * 0,03; 0,08)",
          height="altura_tronco + 0,10", role="Trunk", material="Madeira"),
        B("revolution", name="Copa", points=_crown("copa / 2", "altura_tronco", "altura"),
          role="Canopy", material="Folhagem"),
    ], symbol={"mode": "drawn", "items": [
        C("circle", radius="copa / 2"),
        C("polyline", points=_wavy("copa / 2 * 0,90"), closed=True),
        C("circle", radius="máx(copa * 0,03; 0,08)"),
    ]})
    return _types(defn, ("Árvore pequena", {}, {"copa": 2.0, "altura": 4.0}),
                  ("Árvore média", {}, {"copa": 4.0, "altura": 6.0}),
                  ("Árvore grande", {}, {"copa": 6.0, "altura": 9.0}))


def palmeira() -> list[dict]:
    defn = _defn("Palmeira", "vegetation", "VEGETATION", [
        P("altura", "length", "occurrence", 6.0, min=1.5, max=30.0, label="Altura"),
        P("copa", "length", "type", 3.0, min=1.0, label="Diâmetro da copa"),
    ], [
        B("cylinder", name="Estipe", radius=0.15, height="altura - 0,40", role="Trunk",
          material="Madeira"),
        B("revolution", name="Folhas", points=[
            ["0", "altura - 0,60"], ["copa / 2", "altura - 1,0"], ["copa / 2", "altura - 0,90"],
            ["0,20", "altura"], ["0", "altura"]], role="Canopy", material="Folhagem"),
    ], symbol={"mode": "drawn", "items": [
        C("circle", radius=0.15),
        *[C("line", points=[[0, 0], [f"copa / 2 * cos({a})", f"copa / 2 * sen({a})"]])
          for a in range(0, 360, 45)],
    ]})
    return _types(defn, ("Palmeira", {}))


def arbusto() -> list[dict]:
    defn = _defn("Arbusto", "vegetation", "VEGETATION", [
        P("diametro", "length", "occurrence", 1.0, min=0.2, max=5.0, label="Diâmetro"),
        P("altura", "length", "type", 0.80, min=0.2, label="Altura"),
    ], [
        B("revolution", name="Arbusto", points=_crown("diametro / 2", "0", "altura"),
          role="Canopy", material="Folhagem"),
    ], symbol={"mode": "drawn", "items": [
        C("polyline", points=_wavy("diametro / 2", 14, 0.85), closed=True),
    ]})
    return _types(defn, ("Arbusto", {}))


def vaso() -> list[dict]:
    defn = _defn("Vaso com planta", "vegetation", "VEGETATION", [
        P("diametro", "length", "type", 0.40, min=0.15, label="Diâmetro do vaso"),
        P("altura_vaso", "length", "type", 0.40, min=0.10, label="Altura do vaso"),
        P("planta", "length", "type", 0.60, min=0.10, label="Altura da planta"),
    ], [
        B("revolution", name="Vaso", points=[["0", "0"], ["diametro / 2 * 0,75", "0"],
                                            ["diametro / 2", "altura_vaso"],
                                            ["0", "altura_vaso"]],
          role="Trunk", material="Barro"),
        B("revolution", name="Planta",
          points=_crown("diametro / 2 * 1,2", "altura_vaso", "altura_vaso + planta"),
          role="Canopy", material="Folhagem"),
    ], symbol={"mode": "drawn", "items": [
        C("circle", radius="diametro / 2"),
        C("polyline", points=_wavy("diametro / 2 * 1,2", 10, 0.8), closed=True),
    ]})
    return _types(defn, ("Vaso com planta", {}))


# --- arquivos -------------------------------------------------------------------------------------

FILES = {
    "mobiliario/quarto.ifc": (cama, criado_mudo, guarda_roupa),
    "mobiliario/sala.ifc": (sofa, poltrona, mesa_centro, estante),
    "mobiliario/jantar.ifc": (mesa_jantar, cadeira),
    "mobiliario/escritorio.ifc": (escrivaninha,),
    "mobiliario/cozinha.ifc": (armario_baixo, armario_alto),
    "loucas/banheiro.ifc": (bacia, lavatorio_coluna, lavatorio_suspenso, bancada, chuveiro,
                            mictorio),
    "loucas/area-de-servico.ifc": (tanque,),
    "eletrodomesticos/cozinha.ifc": (geladeira, fogao, micro_ondas, lava_loucas),
    "eletrodomesticos/area-de-servico.ifc": (lavadora,),
    "vegetacao/vegetacao.ifc": (arvore, palmeira, arbusto, vaso),
}


def all_states() -> list[dict]:
    return [s for makers in FILES.values() for make in makers for s in make()]

