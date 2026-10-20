# SPDX-License-Identifier: LGPL-3.0-or-later
"""Fórmulas e definição dos objetos paramétricos (objeto-parametrico.md §3, OB01, OB06–OB08
no núcleo)."""

import math

import pytest

from brasbim.core.objects import definition as od
from brasbim.core.objects import formula as fm
from brasbim.core.objects.formula import FormulaError


def calc(text, **values):
    return fm.calc(text, values)


# --- OB01 ------------------------------------------------------------------------------


def test_ob01_numeros_com_virgula_e_funcoes():
    assert calc("máx(1,20 - 2 * 0,10; 0,40)") == pytest.approx(1.0)
    assert calc("max(1.2 - 0.2; 0,4)") == pytest.approx(1.0)
    assert calc("mín(3; 2; 5)") == 2
    assert calc("arred_baixo(2,40 / 0,60) * 2") == 8
    assert calc("arred(1,256; 2)") == pytest.approx(1.26)
    assert calc("arred_cima(2,01)") == 3
    assert calc("2 ^ 3 ^ 2") == 512  # potência à direita
    assert calc("-2 ^ 2") == -4
    assert calc("raiz(16) + abs(-1)") == 5
    assert calc("sen(30)") == pytest.approx(0.5)
    assert calc("tg(45)") == pytest.approx(1.0)
    assert calc("pi()") == pytest.approx(math.pi)
    assert calc("= largura / 2", largura=1.38) == pytest.approx(0.69)


def test_ob01_logica_e_texto():
    assert calc('se(tampo = "redondo"; 1; 0)', tampo="redondo") == 1
    assert calc('se(tampo = "redondo"; 1; 0)', tampo="retangular") == 0
    assert calc("com_braco = não", com_braco=False) is True
    assert calc("não com_braco", com_braco=False) is True
    assert calc("n >= 1 e n <= 3", n=2) is True
    assert calc("n < 1 ou sim", n=2) is True
    assert calc("Largura * 2", largura=1) == 2  # sem diferenciar maiúsculas


def test_ob01_se_nao_avalia_o_outro_caso():
    assert calc("se(n = 0; 0; 1 / n)", n=0) == 0


@pytest.mark.parametrize("text", [
    '__import__("os")', "1 +", "(1", "largura largura", "2 $ 3", '"aberto',
    "foo(1)", "max()", "se(1; 2)", "",
])
def test_ob01_sintaxe_invalida(text):
    with pytest.raises(FormulaError):
        fm.calc(text, {"largura": 1.0})


def test_ob01_erros_de_calculo():
    with pytest.raises(FormulaError, match="divisão por zero"):
        calc("1 / (a - a)", a=1)
    with pytest.raises(FormulaError, match="raiz"):
        calc("raiz(-1)")
    with pytest.raises(FormulaError, match="desconhecido"):
        calc("b + 1", a=1)


def test_ob01_tipos():
    types = {"largura": fm.NUMBER, "tampo": fm.TEXT, "braco": fm.BOOL}
    assert fm.infer(fm.parse('se(tampo = "x"; largura; 0)'), types) == fm.NUMBER
    for bad in ('largura + tampo', 'tampo < "a"', 'se(largura; 1; 2)', "não largura",
                "braco + 1", 'se(braco; 1; "a")'):
        with pytest.raises(FormulaError):
            fm.infer(fm.parse(bad), types)


def _defn(**extra):
    params = [
        od.new_param("largura", "length", "type", 1.2, min=0.4, max=3.0),
        od.new_param("braco", "length", "type", 0.10),
        od.new_param("assento", "length", "type", formula="largura - 2 * braco"),
        od.new_param("comprimento", "length", "occurrence", 1.8, min=0.6),
    ]
    return od.new_definition("Teste", params=params, **extra)


def _where(found):
    return [(p.where, p.message) for p in found]


def test_ob01_definicao_valida_e_problemas_por_linha():
    defn = _defn()
    assert od.problems(defn) == []
    # ciclo
    bad = _defn()
    bad["params"][0]["formula"] = "assento + 0,2"
    found = od.problems(bad)
    assert any("ciclo" in m for _, m in _where(found))
    assert all(w[0] == "param" for w, _ in _where(found))
    # nome desconhecido
    bad = _defn()
    bad["params"][2]["formula"] = "largura - profundidade"
    assert [w for w, m in _where(od.problems(bad)) if "desconhecido" in m] == [("param", 2)]
    # tipo dependendo de ocorrência
    bad = _defn()
    bad["params"][2]["formula"] = "comprimento / 2"
    assert any("não pode depender de parâmetro de ocorrência (comprimento)" in m
               for _, m in _where(od.problems(bad)))
    # texto onde se espera comprimento
    bad = _defn()
    bad["params"].append(od.new_param("tampo", "choice", "type", "redondo",
                                      options=["redondo", "retangular"]))
    bad["params"][2]["formula"] = "tampo"
    assert any("esperado número" in m for _, m in _where(od.problems(bad)))
    # identificador inválido, repetido e palavra reservada
    bad = _defn()
    bad["params"].append(od.new_param("2x", "length", "type", 1.0, label="Dois"))
    bad["params"].append(od.new_param("Largura", "length", "type", 1.0, label="Outra"))
    bad["params"].append(od.new_param("se", "length", "type", 1.0, label="Se"))
    messages = [m for _, m in _where(od.problems(bad))]
    assert any("inválido" in m for m in messages)
    assert any("repetido" in m for m in messages)
    assert any("reservada" in m for m in messages)


def test_ob01_parametros_embutidos():
    defn = _defn(elevation=0.42)
    names = [p["name"] for p in defn["params"]]
    assert {"elevacao", "codigo", "descricao"} <= set(names)
    assert od.param(defn, "elevacao")["value"] == pytest.approx(0.42)
    assert od.param(defn, "elevacao")["level"] == "occurrence"


def test_ob01_avaliacao_em_ordem_e_niveis():
    defn = _defn()
    v = od.evaluate(defn, {"largura": 1.6}, {"comprimento": 2.0})
    assert v["assento"] == pytest.approx(1.4)
    assert v["comprimento"] == pytest.approx(2.0)
    only_type = od.evaluate(defn, {"largura": 1.6}, level="type")
    assert "comprimento" not in only_type and only_type["assento"] == pytest.approx(1.4)


# --- OB06 a OB08 no núcleo ---------------------------------------------------------------


def _sofa():
    params = [
        od.new_param("largura", "length", "type", 1.80),
        od.new_param("com_braco", "bool", "type", True),
        od.new_param("tampo", "choice", "type", "retangular",
                     options=["retangular", "redondo"]),
    ]
    pieces = [
        od.new_piece("box", name="Assento", x="se(com_braco; 0,15; 0)", width=
                     "largura - se(com_braco; 0,30; 0)", depth=0.8, height=0.45),
        od.new_piece("box", name="Braço esquerdo", width=0.15, depth=0.8, height=0.65,
                     visible="com_braco"),
        od.new_piece("box", name="Braço direito", x="largura - 0,15", width=0.15,
                     depth=0.8, height=0.65, visible="com_braco"),
        od.new_piece("cylinder", name="Tampo redondo", x=0.4, y=0.4, radius=0.4,
                     height=0.03, z=0.7, visible='tampo = "redondo"'),
        od.new_piece("box", name="Tampo", width=0.8, depth=0.8, height=0.03, z=0.7,
                     visible='tampo = "retangular"'),
    ]
    return od.new_definition("Sofá", params=params, pieces=pieces)


def test_ob06_visibilidade_e_escolha():
    defn = _sofa()
    assert od.problems(defn) == []
    with_arms = od.solids(defn, od.evaluate(defn))
    assert [s.name for s in with_arms] == ["Assento", "Braço esquerdo", "Braço direito",
                                           "Tampo"]
    without = od.solids(defn, od.evaluate(defn, {"com_braco": False, "tampo": "redondo"}))
    assert [s.name for s in without] == ["Assento", "Tampo redondo"]
    assert without[0].dims["width"] == pytest.approx(1.80)


def test_ob07_repeticao_distribuida():
    params = [od.new_param("prateleiras", "integer", "type", 5, min=1),
              od.new_param("altura", "length", "type", 1.80)]
    pieces = [od.new_piece("box", name="Prateleira", width=0.8, depth=0.3, height=0.02,
                           repeat={"count": "prateleiras", "dz": 1,
                                   "length": "altura - 0,02"})]
    defn = od.new_definition("Estante", params=params, pieces=pieces)
    shelves = od.solids(defn, od.evaluate(defn))
    zs = [s.origin[2] for s in shelves]
    assert len(zs) == 5
    steps = [b - a for a, b in zip(zs, zs[1:])]
    assert all(step == pytest.approx(steps[0]) for step in steps)
    assert zs[-1] == pytest.approx(1.78)
    assert len(od.solids(defn, od.evaluate(defn, {"prateleiras": 3}))) == 3
    box = od.bounds(shelves)
    assert box[5] == pytest.approx(1.80)


def test_ob08_limites_e_medidas_invalidas():
    defn = _defn()
    with pytest.raises(FormulaError, match="abaixo do mínimo"):
        od.evaluate(defn, {}, {"comprimento": 0.3})
    defn["pieces"] = [od.new_piece("box", width="assento - 1,5", depth=1, height=1)]
    assert od.problems(defn) == []  # válida em si; o erro aparece com esses valores
    with pytest.raises(FormulaError, match="medida ≤ 0"):
        od.solids(defn, od.evaluate(defn))


def test_alca_mantem_o_lado_oposto():
    params = [od.new_param("largura", "length", "occurrence", 1.0,
                           handle={"axis": "x", "side": "start"})]
    pieces = [od.new_piece("box", width="largura", depth=0.6, height=0.9)]
    defn = od.new_definition("Armário", params=params, pieces=pieces)
    assert od.problems(defn) == []
    assert od.handle_shift(defn, {}, {"largura": 1.0}, "largura", 1.4)[0] == \
        pytest.approx(-0.4)
    defn["params"][0]["handle"]["side"] = "symmetric"
    assert od.handle_shift(defn, {}, {"largura": 1.0}, "largura", 1.4)[0] == \
        pytest.approx(-0.2)
    defn["params"][0]["handle"]["side"] = "end"
    assert od.handle_shift(defn, {}, {"largura": 1.0}, "largura", 1.4)[0] == \
        pytest.approx(0.0)
