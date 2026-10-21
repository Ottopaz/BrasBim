---
elemento: Escada, guarda-corpo e terreno
entidade_ifc: IfcStair (agrega IfcStairFlight, IfcSlab LANDING e IfcRailing), IfcRailing, IfcGeographicElement TERRAIN
requisito: RF-ELE-08 (escada), RF-ELE-10 (guarda-corpo/corrimão), terreno (CG)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-20
status: em revisão (implementado para teste, fluxo do MVP)
revisor: OTTO
---

# Escada, guarda-corpo e terreno (pacotes 17 e 18)

## 1. Propósito
- **Escada** reta, em L ou em U entre dois níveis, com o número de degraus calculado
  pela altura e o piso pela fórmula de Blondel; guarda-corpo opcional dos lados.
- **Guarda-corpo** solto ao longo de um caminho (borda de laje, varanda, mezanino).
- **Terreno** por pontos com cota, como uma malha triangulada, com curvas de nível na
  planta do pavimento mais baixo.

## 2. Escada
### 2.1 IFC
- `IfcStair` sem corpo próprio, que agrega (`IfcRelAggregates`) os lances
  (`IfcStairFlight` com `NumberOfRisers`, `NumberOfTreads`, `RiserHeight`,
  `TreadLength`), os patamares (`IfcSlab` `LANDING`) e os guarda-corpos (`IfcRailing`
  `GUARDRAIL`), como a cobertura agrega as águas. Só a escada fica contida no
  pavimento. GlobalIds das peças derivados da escada. [IFC-STAIR, IFC-FLIGHT, IFC-RAIL]
- `PredefinedType`: `STRAIGHT_RUN_STAIR`, `QUARTER_TURN_STAIR` (L) e `HALF_TURN_STAIR` (U).
- Pset `BrasBim_Escada` (JSON) e `Pset_StairCommon` (`NumberOfRiser`,
  `NumberOfTreads`, `RiserHeight`, `TreadLength`).

### 2.2 Parâmetros
| Campo | Padrão | Regras |
|---|---|---|
| Forma | reta | reta, L, U |
| Início e direção | — | o ponto é o canto direito (de quem sobe) do primeiro degrau; o lance fica à esquerda dele; a direção é a de subida |
| Largura | 1,20 m | > 0,60 |
| Altura | até o pavimento de cima (2,80 sem ele) | > 0 |
| Espelhos | calculado: menor número com espelho ≤ 18 cm | ≥ 2 |
| Piso | calculado: 63 cm − 2 × espelho (Blondel), entre 25 e 32 cm | — |
| Giro (L e U) | à esquerda | esquerda ou direita |
| Divisão (L e U) | metade dos espelhos no primeiro lance | 1 ≤ n < total |
| Espessura (laje da escada) | 12 cm | > 0 |
| Guarda-corpo | dos dois lados | nenhum, esquerda, direita, os dois; em L e U o do lado de fora contorna o patamar |
| Altura do guarda-corpo | 1,10 m | > 0 |

Fora dos limites usuais (espelho 16–18 cm, piso ≥ 28 cm, Blondel 63–64 cm; NBR 9077 e
código de obras, **a conferir**) o BrasBim avisa em Mensagens, sem recusar.

### 2.3 Planta
Contorno dos lances e patamares, linhas dos degraus, linha de corte inclinada no degrau
que cruza o plano de corte, degraus acima dele tracejados, e a linha de percurso com
a seta no fim (sobe). Guarda-corpos como linha fina.

### 2.4 Interação
Ferramenta **Escada** (Modelagem, depois da Laje): clique o início e a direção de
subida. Barra Opções: forma, largura, giro e guarda-corpo. Painel: todos os campos, com
o espelho, o piso e o Blondel calculados.

## 3. Guarda-corpo solto
`IfcRailing` (`GUARDRAIL`) contido no pavimento, por um caminho (polilinha) na cota de
base (a do piso por padrão), com montantes a cada 1,20 m no máximo, corrimão e uma barra
intermediária. Pset `BrasBim_GuardaCorpo` (JSON: `points`, `base`, `height`,
`spacing`). Ferramenta **Guarda-corpo**: clique os pontos; Enter encerra.

## 4. Terreno
### 4.1 IFC
- `IfcGeographicElement` `TERRAIN` contido no **sítio** (`IfcSite`), com o corpo
  `IfcTriangulatedFaceSet` (`Tessellation`) da superfície. [IFC-GEO]
- Pset `BrasBim_Terreno` (JSON): `points` [x, y, z], `interval` das curvas finas
  (padrão 1 m), `boundary` (contorno, ou nada), `boundary_z` (cota do contorno, ou nada =
  calculada) e `curves` (cada uma com os pontos, se é fechada e a cota, que pode faltar).

### 4.2 Superfície (revisada em 2026‑10‑21, pedido do revisor)
- Amostras: os pontos cotados, as curvas **com cota** adensadas a cada 1 m e o contorno
  adensado. O contorno sem cota tira a de cada ponto das amostras vizinhas (média
  ponderada pelo inverso do quadrado da distância, 8 vizinhas). Só vale o que está dentro
  do contorno; onde a curva cruza o contorno entra um ponto com a cota dela.
- Triangulação de Delaunay (GEOS, pelo shapely), só os triângulos dentro do contorno.
- **Patamar falso** (triângulo com os três vértices na mesma curva, área > 0,05 m²):
  ganha um ponto no meio. Com curvas vizinhas dos dois lados, a cota vem delas; só de um
  lado (bolsão de uma curva sinuosa), fica a meio caminho até elas; dentro de uma curva
  fechada com as vizinhas todas de um lado (topo de morro, fundo de vale), o patamar é de
  verdade e fica. Até 4 passadas.
- Curva sem cota ainda não entra.

### 4.3 Planta (pavimento mais baixo)
Contorno (linha cheia; sem contorno, a envoltória tracejada), curvas desenhadas (cheias,
com a cota no meio; **tracejadas enquanto não têm cota**) e as curvas finas da superfície
a cada `interval` (a cada cinco, mais grossa e com a cota), menos onde já há curva
desenhada.

### 4.4 Interação (fluxo do revisor, com o levantamento importado, spec/ui 22)
1. Ferramenta **Terreno**, modo **Contorno** (padrão): clique o contorno; clicar no
   primeiro ponto, Enter ou clique duplo fecha. Barra Opções: cota do contorno (vazio =
   pelas curvas) e o intervalo. O modo **Pontos cotados** é o de antes (Tab = cota).
2. Com o terreno selecionado, a mini-barra tem **Pegar linhas**: a linha do desenho
   importado (ou uma linha, curva, arco ou círculo 2D) sob o cursor fica destacada, com
   a cota que trouxe do arquivo; **clique ou Enter** a põe no terreno como curva de
   nível. Continua ativa para as próximas; Esc encerra. Linha repetida não entra.
3. **Cota das curvas** (mini-barra): as curvas sem cota aparecem destacadas; clique uma
   curva e digite a cota (Enter). Sem digitar, Enter aceita a sugestão: a cota que a
   curva já tem ou a última dada mais o intervalo.
4. Painel: nome, intervalo, cota do contorno, quantas curvas (e quantas sem cota), as
   cotas da superfície; os pontos cotados como texto.

## 5. Critérios de aceite (testes)
- [x] **ET01** Escada reta de 2,80 m: 16 espelhos de 17,5 cm e piso de 28 cm; `IfcStair`
      agrega um `IfcStairFlight` com os atributos certos; o último espelho chega a 2,80
      (o último piso do lance fica um espelho abaixo); IFC válido.
- [x] **ET02** Escada em L e em U: dois lances e um patamar na cota certa; giro à direita
      espelha a planta.
- [x] **ET03** Guarda-corpo dos dois lados acompanha a inclinação; sem guarda-corpo,
      nenhum `IfcRailing`.
- [x] **ET04** Planta: linha de corte e degraus acima tracejados; mover, girar e
      desfazer; excluir leva as peças.
- [x] **ET05** Aviso de espelho fora de 16–18 cm.
- [x] **ET06** Guarda-corpo solto: montantes a no máximo 1,20 m, altura certa.
- [x] **ET07** Terreno por 5 pontos: `IfcTriangulatedFaceSet` válido, no sítio; curvas
      de nível na planta do pavimento mais baixo.
- [x] **ET08** Interface: as ferramentas criam pelos cliques.
- [x] **TR01–TR08** Terreno por contorno e curvas (`tests/test_terreno_curvas.py`):
      contorno com cota; curvas dão a superfície e o contorno segue as vizinhas; curva
      sem cota tracejada e fora da superfície até ganhar cota; pegar as linhas do desenho
      importado com a cota do arquivo; patamar falso corrigido e topo de morro mantido;
      transformações; 400 m de curvas em menos de 5 s; o fluxo inteiro na interface.
- [x] **ET09** 3D: a escada numa malha só (concreto nos degraus, alumínio nos
      guarda-corpos), o guarda-corpo solto e o terreno (só o contorno nas arestas); editar
      refaz a malha.

## 6. Fontes públicas
IFC 4.3 (buildingSMART): `IfcStair`/`IfcStairTypeEnum` [IFC-STAIR], `IfcStairFlight`
[IFC-FLIGHT], `IfcRailing`/`IfcRailingTypeEnum` [IFC-RAIL], `IfcGeographicElement`
`TERRAIN`, `IfcTriangulatedFaceSet` [IFC-GEO]. Fórmula de Blondel (2e + p = 63 a 64 cm),
NBR 9077 e NBR 9050 (escadas, guarda-corpo): texto não lido, a conferir. CG:
triangulação de Delaunay (Bowyer–Watson) e curvas de nível por interpolação nas arestas.

Nenhum material de `_restrito/` nem de `tools/` foi usado.

## 7. Pontos de revisão
(a) escada sem degrau em leque (o patamar do L e do U é quadrado);
(b) espelho máximo de 18 cm para o cálculo automático;
(c) guarda-corpo com montantes, corrimão e uma barra (sem vidro nem tela);
(d) terreno sem corte e aterro (plataforma) no MVP; curvas só no pavimento mais baixo.
(e) patamar falso: ponto no meio do triângulo plano (regras de §4.2), não
    triangulação com as curvas como restrição;
(f) pegar várias linhas por janela fica para depois (hoje uma por clique ou Enter).
