---
documento: Estrutura, refinamento 1 — recortes por prioridade, aberturas na laje, laje pelo contorno das paredes, etiquetas de pilar e viga
requisito: RF-ELE-01, RF-ELE-02, RF-ELE-03, RF-ELE-04, RF-UI-01
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-16
status: aprovado
revisor: OTTO (aprovado em 2026-10-16)
---

# Estrutura: refinamento 1 (pacote 5)

## 1. Propósito
O pacote 4 entregou o básico de laje, pilar e viga, com os elementos sobrepostos no 3D e
nos volumes (spec/ui 10 §7, pontos de revisão (b)). Este pacote faz deles um modelo que
serve para quantitativo e para mostrar ao cliente:

1. **Recortes por prioridade** (§2): o elemento mais importante corta o menos importante,
   no 3D, nos volumes e no IFC. A viga termina na face do pilar, a laje se apoia nas
   vigas e a parede para embaixo da viga e da laje.
2. **Aberturas na laje** (§3): vãos de escada, shafts e poços.
3. **Laje pelo contorno das paredes** (§4): um clique dentro de um cômodo fechado.
4. **Etiquetas de pilar e viga** na planta (§5).

Fica para o pacote seguinte: alças de pilar, viga e laje no 3D; laje inclinada; viga
curva.

## 2. Recortes por prioridade

### 2.1 Regra
Ordem de prioridade, da mais alta para a mais baixa *(decisão do projeto, CG)*:

**pilar > viga > laje > parede**

Onde dois elementos ocupam o mesmo espaço, o de prioridade mais alta fica inteiro e o
outro perde a parte comum. Entre dois elementos da mesma classe não há recorte (dois
pilares encostados continuam como estão).

Consequências, na convenção usual dos projetos de concreto no Brasil *(CG)*:
- O pilar atravessa a laje e a viga; a viga termina na face do pilar.
- A altura h da viga é a altura total, com a laje: a laje é cortada pela viga (a laje
  "fica entre as vigas"). Com a viga de topo no nível da laje, o volume da viga inclui a
  faixa da laje sobre ela.
- A parede que sobe até o nível do pavimento de cima para embaixo da laje e da viga, e é
  recortada pelos pilares (como a planta já faz, spec/ui 10 §6.2).

**Ponto de revisão (a):** a ordem pilar > viga > laje > parede.

### 2.2 Quem é comparado com quem
Elementos do mesmo pavimento e dos pavimentos imediatamente abaixo e acima, cujas
plantas se cruzam e cujas faixas de cota (base–topo, no sistema da edificação) se
sobrepõem mais que 1 mm. Assim o pilar do Térreo, que sobe até 2,80, corta a laje do
Superior, que vai de 2,68 a 2,80.

Elementos de outra origem (sem o Pset do BrasBim) **cortam** os outros pela prioridade da
classe, mas **não são cortados** (o corpo deles é preservado; laje.md §3.1).

### 2.3 Como o recorte é gravado no IFC
O corpo continua um sólido extrudado; o recorte entra como diferença com semiespaços,
que o IFC aceita no `Body` de laje, pilar, viga e parede (representação **`Clipping`**:
`IfcBooleanClippingResult` com `IfcHalfSpaceSolid`) [IFC-SLAB; IFC-SHAPEREP]. Cada
recorte é um **`IfcPolygonalBoundedHalfSpace`**: um plano horizontal limitado, em planta,
pelo contorno do elemento que corta, nas coordenadas do elemento cortado. A parede já
usa esse recurso no topo inclinado (spec/ui 08 §4.2).

Seja C o elemento que corta e E o cortado, com cotas [c₀, c₁] e [e₀, e₁]:

| Situação | Semiespaço retirado de E | Exemplo |
|---|---|---|
| c₀ ≤ e₀ e c₁ ≥ e₁ (C atravessa E) | tudo dentro do contorno de C | pilar na laje; pilar na viga; pilar na parede |
| c₀ > e₀ e c₁ ≥ e₁ (C ocupa o alto de E) | acima de c₀, dentro do contorno de C | viga sobre a parede; laje sobre a parede; viga na laje (a laje perde a faixa da viga) |
| c₀ ≤ e₀ e c₁ < e₁ (C ocupa o baixo de E) | abaixo de c₁, dentro do contorno de C | viga baldrame dentro da parede |
| C inteiro dentro de E na altura | **sem recorte** nesta etapa; aviso em Mensagens | viga no meio de uma parede alta |

No último caso o IFC precisaria de um furo (dois semiespaços combinados), o que o
`Clipping` não expressa; fica para V1 com `IfcOpeningElement`. **Ponto de revisão (b).**

O corpo sem recortes continua `SweptSolid`; com recortes vira `Clipping`, com os
semiespaços encadeados por GlobalId do elemento que corta (ordem estável).

**Relação:** cada par cortado gera uma `IfcRelInterferesElements` com
`RelatingElement` = o cortado, `RelatedElement` = o que corta, `ImpliedOrder` = verdadeiro
("o resultado é o `RelatingElement` menos a interferência") e `InterferenceType` =
"Recorte" [IFC-INTERF]. É derivada (GlobalId determinístico), refeita a cada mudança, e
não vira operação no diário.

### 2.4 Parede
- Recortes só em parede reta ou em arco **de topo plano e sem inclinação**. Parede com
  topo inclinado ou tombada continua sem recorte (aviso); V1.
- O recorte do topo (viga/laje acima) não muda os parâmetros da parede: a altura no
  painel continua a do vínculo; as quantidades mostram o líquido.
- As aberturas continuam como hoje (`IfcOpeningElement`).

### 2.5 Quantidades
O `NetVolume` passa a descontar a parte retirada; o `GrossVolume` não muda. Como todos os
elementos são prismas verticais (pilar, laje, parede) ou caixas (viga), a parte comum é
a área da interseção das plantas × a sobreposição das cotas, calculada com
`core/clip.py`. Nas lajes, `NetArea` desconta o que a atravessa na espessura toda, os
pilares e as vigas de topo no nível dela (§3.4 para as aberturas; ajuste da
implementação, 2026‑10‑16: a viga também atravessa a laje pela regra de §2.1). Na parede, `NetSideArea` e `NetFootprintArea` não mudam nesta etapa.

### 2.6 Planta e 3D
- 3D: os corpos já vêm recortados do IFC (o `ifcopenshell.geom` aplica o `Clipping`); a
  parede por camadas continua com a cor de cada camada.
- Planta: nada muda para pilar, viga e parede (a planta já recortava a parede pelo pilar
  cortado e o tracejado da viga no pilar). A laje cortada pelo pilar mostra o contorno do
  pilar como um furo no contorno dela.

## 3. Aberturas na laje

### 3.1 IFC
`IfcOpeningElement` (`PredefinedType` `OPENING`) ligado à laje por `IfcRelVoidsElement`
[IFC-SLAB, *Openings*]. Corpo: contorno extrudado na vertical, do fundo ao topo da laje,
com 1 cm a mais para cada lado (o vazio atravessa a laje inteira). Posicionamento relativo
ao da laje. Contido no mesmo pavimento.

### 3.2 Parâmetros e operações
| Parâmetro | Regras |
|---|---|
| Contorno | Polígono simples, ≥ 3 pontos, anti-horário, **inteiro dentro** da laje |
| Laje | A que ele fura |

| `op` | Dados |
|---|---|
| `slab_opening.create` / `.delete` | `slab`, `outline[]` (coordenadas do pavimento) |
| `slab_opening.edit` | `outline` (antes/depois) |

Mover, girar, espelhar e copiar a laje levam as aberturas junto (um `slab_opening.edit`
ou `.create` por abertura, na mesma transação). Excluir a laje exclui as aberturas antes.
Mudar o contorno da laje de modo que uma abertura saia dela é recusado.

### 3.3 Interface
- **Mini-barra** da laje selecionada sozinha: ação **Abertura** (ícone próprio). Abre a
  ferramenta de abertura, com os modos **Polígono** e **Retângulo** na barra Opções, como
  a ferramenta Laje (spec/ui 10 §2.3). Fora da laje, a pré-visualização fica vermelha e o
  clique é recusado.
- A abertura é escolhida pelo clique no contorno dela (antes da laje) e tem alças nos
  vértices e no meio dos lados, como a laje. Mover, Excluir e Copiar valem para ela; Girar
  e Espelhar só junto com a laje.
- Painel: **Abertura na laje**: Área, Perímetro, Laje (nome do tipo), Identificação.

### 3.4 Quantidades da laje
`NetArea` = área do contorno − aberturas − pilares que atravessam; `NetVolume` = volume do
contorno − aberturas − recortes (§2.5). `GrossArea` e `GrossVolume` não descontam.

### 3.5 Planta
A abertura aparece como furo no contorno da laje (linha fina) e com as duas diagonais
(um X), convenção usual para vazio na laje *(CG)*. **Ponto de revisão (c).**

## 4. Laje pelo contorno das paredes
- Terceiro modo na ferramenta Laje: **Pelo cômodo**. Um clique dentro de um cômodo
  fechado por paredes cria a laje com o contorno dele.
- O cômodo é o furo da união das plantas das paredes do pavimento (as faixas inteiras,
  sem o plano de corte) que contém o ponto clicado. Sem cômodo fechado ali: recusa com a
  mensagem "o ponto não está num cômodo fechado por paredes".
- **Até onde vai a laje** (barra Opções, lista "Contorno"): **Face interna** (o vão livre),
  **Eixo das paredes** ou **Face externa**. Padrão: **Face externa** *(decisão do projeto:
  a laje se apoia em toda a espessura das paredes)*. Para o eixo e a face externa, cada
  lado do furo é afastado pela metade ou pela espessura toda da parede que o forma, e os
  cantos são refeitos pelo cruzamento dos lados vizinhos. **Ponto de revisão (d).**
- A pré-visualização mostra o contorno ao passar o cursor dentro do cômodo.
- O resultado é uma laje comum (`slab.create` com o contorno); ela não fica ligada às
  paredes (mover a parede depois não muda a laje). Ligação às paredes: V1.

## 5. Etiquetas de pilar e viga
- **Exibir > Etiquetas de estrutura** (ligada por padrão; guardada em `QSettings`
  `etiquetas_estrutura`), separada das etiquetas de esquadrias (pilar.md §7 previa o
  mesmo menu; separar foi pedido como V1 e entra agora).
- **Pilar:** "P1" e, abaixo, "20×40" (ou "Ø30"), junto ao canto superior direito da seção
  *(CG)*.
- **Viga:** "V1 14×40" no meio da viga, **ao longo dela** (girada com a viga, sempre de
  leitura da esquerda para a direita ou de baixo para cima), do lado de fora da faixa
  *(CG)*.
- Só para os elementos do pavimento mostrado; o nome é o `Name` e a seção é a do tipo.

## 6. Núcleo: o que muda
- `core/structure/cuts.py` (novo): candidatos (§2.2), classificação (§2.3), semiespaços,
  volumes e `IfcRelInterferesElements`.
- `core/structure/rebuild.py` e `core/walls/rebuild.py`: corpo com os recortes; derivação
  que também refaz os elementos que este corta (e os que o cortam) quando ele muda.
- `core/structure/slab_openings.py` (novo): estado, operações e corpo das aberturas;
  `commands`, `transform` e `delete` passam a levar as aberturas da laje.
- `core/structure/rooms.py` (novo): furos da união das paredes, contorno pelo eixo e pela
  face externa.
- `core/plan.py`: furos da laje (pilares e aberturas), símbolo da abertura, etiquetas.
- Atualizar `spec/01-modelo-de-dados.md` (operações `slab_opening.*`).

## 7. Critérios de aceite (testes)
Pavimentos Térreo (0,00) e Superior (2,80), plano de corte 1,50; pilar 20×40, viga 14×40
e laje maciça de 10 cm da biblioteca.

**Recortes**
- [ ] **RC01** Viga de (0, 0) a (5, 0), eixo, e pilares centrados em (0, 0) e (5, 0): o
      corpo da viga é `Clipping` com 2 semiespaços; o volume líquido da viga é
      0,14 × 0,40 × (5 − 0,20) = 0,2688 (o pilar de 20 cm em x tira 0,10 de cada ponta).
- [ ] **RC02** O pilar fica inteiro (`SweptSolid`, `NetVolume` = 0,08 × 2,80).
- [ ] **RC03** Laje do Superior de 5 × 4 com um pilar do Térreo num canto: a laje perde a
      seção do pilar (0,08 m² × 0,10 m) em `NetVolume`, e `NetArea` desconta 0,08 m².
- [ ] **RC04** Viga com topo em 2,80 sob a laje do Superior: a laje perde a faixa da viga
      (largura 0,14 × comprimento sob ela × 0,10); a viga fica inteira.
- [ ] **RC05** Parede de 14 cm de (0, 0) a (5, 0), topo no Superior, com viga 14×40 por
      cima no mesmo eixo: a parede perde a faixa de 2,40 a 2,80; `NetVolume` = 0,14 × 5 ×
      2,40 (sem pilares).
- [ ] **RC06** `IfcRelInterferesElements` com o cortado em `RelatingElement`, o que corta
      em `RelatedElement` e `ImpliedOrder` verdadeiro; um por par; somem quando o recorte
      some.
- [ ] **RC07** Mover o pilar para longe da viga: a viga volta a `SweptSolid` e ao volume
      bruto; desfazer volta o recorte. O diário reaplicado reproduz o IFC.
- [ ] **RC08** Viga inteira dentro da altura de uma parede de 4 m: sem recorte e com aviso
      em Mensagens.
- [ ] **RC09** Pilar de outra origem corta a viga do BrasBim; a viga de outra origem não é
      cortada.
- [ ] **RC10** O arquivo passa na validação de esquema; o 3D mostra a viga encurtada
      (malha sem triângulos dentro do pilar).

**Aberturas na laje**
- [ ] **AL01** Abertura 1 × 2 numa laje 5 × 4: `IfcOpeningElement` `OPENING` com
      `IfcRelVoidsElement`; `NetArea` 18, `GrossArea` 20, `NetVolume` 1,8.
- [ ] **AL02** Abertura que sai da laje: recusada.
- [ ] **AL03** Mover, girar e espelhar a laje levam a abertura; excluir a laje exclui a
      abertura; desfazer restaura os GlobalIds.
- [ ] **AL04** Planta: furo e X da abertura; o clique no contorno da abertura a escolhe.
- [ ] **AL05** Interface: Abertura pela mini-barra, modo Retângulo, dois cliques dentro
      da laje.

**Laje pelo cômodo**
- [ ] **LC01** Retângulo de paredes de 14 cm por dentro de (0, 0)–(5, 4) (face externa no
      retângulo): clique em (2, 2) com Face externa → laje (0, 0)–(5, 4); com Face
      interna → (0,14, 0,14)–(4,86, 3,86); com Eixo → (0,07, 0,07)–(4,93, 3,93).
- [ ] **LC02** Cômodo em L de 6 paredes: laje de 6 vértices.
- [ ] **LC03** Clique fora de cômodo fechado (parede faltando): recusa com a mensagem.

**Etiquetas**
- [ ] **ET01** Planta com P1 e V1: etiquetas "P1"/"20×40" e "V1 14×40"; a da viga a 90°
      fica girada.
- [ ] **ET02** Exibir > Etiquetas de estrutura desligada: nenhuma; a preferência fica
      guardada.

## 8. Fontes públicas
IFC 4.3 no repositório oficial da buildingSMART, ramo `ifc4.3-main`, consultado em
2026‑10‑16 (`S`, `M` como em `laje.md` §10; `C` = `docs/schemas/core/IfcProductExtension`;
`G` = `docs/schemas/resource/IfcGeometricModelResource`; `R` =
`docs/schemas/resource/IfcRepresentationResource`).

| Código | Documento |
|---|---|
| IFC-SLAB | `S/Entities/IfcSlab.md` (aberturas por `IfcRelVoidsElement`; `Body` `SweptSolid` ou `Clipping`) |
| IFC-INTERF | `C/Entities/IfcRelInterferesElements.md` (`ImpliedOrder`) |
| IFC-BOOL | `G/Entities/IfcBooleanResult.md` (diferença entre sólidos) |
| IFC-SHAPEREP | `R/Entities/IfcShapeRepresentation.md` (tipos `Clipping` e `CSG`) |
| IFC-COL, IFC-BEAM | como em `pilar.md` e `viga.md` §10 |

Outras:
- **CG**: conhecimento geral de projeto de concreto armado e de desenho arquitetônico no
  Brasil (altura da viga com a laje, pilar contínuo, X no vazio da laje, etiquetas P1 e
  V1 14×40).
- Specs já aprovadas: `laje.md`, `pilar.md`, `viga.md`, spec/ui 08 (semiespaços limitados
  no topo da parede) e spec/ui 10.

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

## 9. Pontos de revisão
(a) Ordem pilar > viga > laje > parede, e a altura da viga incluindo a laje (§2.1).
(b) Elemento inteiro dentro da altura do outro fica sem recorte nesta etapa (§2.3).
(c) X nas aberturas da laje na planta (§3.5).
(d) Laje pelo cômodo até a face externa das paredes, por padrão (§4).
(e) Etiquetas ligadas por padrão, em menu próprio (§5).
