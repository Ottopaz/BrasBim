---
documento: Eixos de projeto, vão e nicho na parede, claraboia
requisito: RF-ELE-01 (aberturas), RF-ELE-06 (aberturas zenitais), RF-DOC-01 (eixos na planta)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-20
status: em revisão (implementado para teste, fluxo do MVP)
revisor: OTTO
---

# Eixos, vãos e claraboia (pacotes 15 e 16)

## 1. Propósito
- **Eixos de projeto**: a malha de referência (1, 2, 3… × A, B, C…) que organiza a
  estrutura e a planta e aparece em todos os pavimentos.
- **Vão e nicho na parede**: a ferramenta que faltava para o que o núcleo já fazia
  (`walls.openings`, `parede.md` §6.3): vão passante sem esquadria e nicho.
- **Claraboia**: abertura com caixilho de vidro numa laje ou numa água da cobertura.

## 2. Eixos (`IfcGrid`)
- Um `IfcGrid` contido na **edificação** (aparece em todos os pavimentos), com
  `UAxes` (eixos numerados, na direção y do eixo, espaçados em x) e `VAxes` (eixos com
  letras, espaçados em y). Cada eixo é um `IfcGridAxis` com `AxisTag` e `AxisCurve`
  (`IfcPolyline` no sistema do eixo). [IFC-GRID] Representação `FootPrint`
  (`GeometricCurveSet`) com as linhas, para outros programas.
- Estado em JSON no Pset `BrasBim_Eixos`: `origin` (x, y), `angle` (graus), `u` e `v`
  (lista de `{"tag": "1", "offset": 0.0}`), `extent` (quanto a linha passa do último eixo,
  m) e `bubbles` (`both`, `start`, `end`).
- Operações `grid.create` / `grid.delete` / `grid.edit`.
- **Planta**: traço e ponto fino (0,13 mm), círculo de 8 mm de papel com o nome na
  ponta. Os cruzamentos são pontos de atração do snap.
- **Ferramenta Eixos** (grupo Modelagem, depois do Objeto): clique a origem e a direção
  do primeiro eixo. Barra Opções: espaçamentos em x e em y ("5; 4; 4" = quatro eixos),
  primeiro número e primeira letra.
- Painel de propriedades: os espaçamentos, a origem, o ângulo e as pontas com círculo.

## 3. Vão e nicho (`IfcOpeningElement` na parede)
- **Ferramenta Vão** (grupo Modelagem, depois da Janela): como a porta, passe o cursor
  sobre uma parede reta e clique; Tab digita a distância. Barra Opções: vão passante ou
  nicho, largura, altura, peitoril, profundidade e face (no nicho).
- Na planta o vão passante aparece como a parede aberta; o nicho, como o rebaixo na
  face (já desenhados). O vão sem esquadria passa a ser **escolhível** (caixa do vão) e
  tem painel próprio (largura, altura, peitoril, profundidade, face, distância).
- Excluir o vão pela seleção (Delete). Mover a parede leva o vão (já era assim).

## 4. Claraboia (`IfcWindow` `SKYLIGHT`)
- A claraboia é uma `IfcWindow` com `PredefinedType = SKYLIGHT`, sem tipo no MVP, que
  preenche (`IfcRelFillsElement`) um `IfcOpeningElement` que fura (`IfcRelVoidsElement`)
  a **laje** ou a **água da cobertura** sob o ponto. [IFC-WINDOW, IFC-OPEN]
- Estado em JSON no Pset `BrasBim_Claraboia`: `host` (a laje ou a cobertura), `center`
  (planta), `width`, `length`, `angle`, `frame` (largura do caixilho) e `code` ("CL1").
  Na cobertura, a água é a que contém o centro, refeita a cada mudança.
- Corpo: caixilho (quatro barras de alumínio) e vidro, no plano do topo da laje ou da
  água; o vão é o retângulo extrudado na espessura, perpendicular ao plano.
- Operações `skylight.create` / `.delete` / `.edit`. A laje ou a cobertura que muda
  refaz a claraboia; excluir a laje ou a cobertura exclui a claraboia; mover, girar ou
  copiar a laje ou a cobertura leva a claraboia.
- **Planta**: retângulo do caixilho e o do vidro, linha fina; escolhe-se pela caixa,
  como as esquadrias.
- **Ferramenta Claraboia** (grupo Modelagem, depois da Cobertura): clique o centro sobre
  uma laje ou cobertura. Barra Opções: largura, comprimento e ângulo (Tab: ângulo).
- Tabelas: entra nas janelas (código, largura, comprimento como altura, área).

## 5. Critérios de aceite (testes)
- [x] **EV01** Eixos 3 × 2: `IfcGrid` na edificação com 3 `UAxes` e 2 `VAxes`, tags
      1–3 e A–B, curvas certas; editar os espaçamentos; desfazer; IFC válido.
- [x] **EV02** Eixos na planta de dois pavimentos; os cruzamentos atraem o snap.
- [x] **EV03** Vão passante e nicho pela ferramenta; o vão é escolhível, o painel
      muda a largura, Delete exclui.
- [x] **EV04** Claraboia numa laje: `IfcWindow` `SKYLIGHT`, vão na laje, corpo no topo;
      mexer na laje refaz; excluir a laje exclui a claraboia; IFC válido.
- [x] **EV05** Claraboia numa cobertura de duas águas: fura a água certa, o corpo fica
      no plano inclinado; mover a cobertura leva a claraboia.
- [x] **EV06** Interface: as três ferramentas criam pelos cliques da §2–§4.

## 6. Fontes públicas
IFC 4.3 (buildingSMART): `IfcGrid`, `IfcGridAxis` (`AxisTag`, `AxisCurve`) [IFC-GRID];
`IfcWindow`/`IfcWindowTypeEnum` `SKYLIGHT` [IFC-WINDOW]; `IfcOpeningElement`,
`IfcRelVoidsElement`, `IfcRelFillsElement` [IFC-OPEN]. NBR 6492 (eixos e claraboia em
planta): texto não lido, a conferir. CG: malha de eixos numerados × letrados.

Nenhum material de `_restrito/` nem de `tools/` foi usado.

## 7. Pontos de revisão
(a) eixos na edificação (todos os pavimentos), sem escolher pavimentos no MVP;
(b) eixos retos e ortogonais entre si (radiais ficam para o V1);
(c) claraboia sem tipo, com caixilho fixo de alumínio e vidro (tipos de claraboia: V1);
(d) eixos não aparecem nos cortes no MVP.
