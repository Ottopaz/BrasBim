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
| Guarda-corpo | dos dois lados | nenhum, esquerda, direita, os dois |
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
- `IfcGeographicElement` `TERRAIN` contido no **sítio** (`IfcSite`), com o corpo
  `IfcTriangulatedFaceSet` (`Tessellation`) da triangulação de Delaunay dos pontos.
  [IFC-GEO]
- Pset `BrasBim_Terreno` (JSON: `points` [x, y, z], `interval` das curvas de nível,
  padrão 1 m).
- Planta do pavimento mais baixo: contorno e curvas de nível (linha fina; a cada 5 a
  mais grossa) com a cota.
- Ferramenta **Terreno**: clique os pontos; Tab digita a cota de cada um; Enter encerra
  (pelo menos 3). Painel: os pontos ("x y z; …") e o intervalo.

## 5. Critérios de aceite (testes)
- [x] **ET01** Escada reta de 2,80 m: 16 espelhos de 17,5 cm e piso de 28 cm; `IfcStair`
      agrega um `IfcStairFlight` com os atributos certos; o topo do último degrau está
      em 2,80; IFC válido.
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
