---
documento: Documentação 1 — anotação da planta (ambientes, cotas, cota de nível, textos, linhas, hachuras, norte, escala, espessuras)
requisito: RF-AMB-01, RF-AMB-02, RF-AMB-03, RF-DOC-03, RF-DOC-04, RF-DOC-05, RF-DOC-06, RF-DOC-07
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-16
status: em revisão
revisor: OTTO
---

# Documentação 1: anotação da planta (pacote 6)

## 1. Propósito
Primeiro dos três pacotes de documentação do desenho técnico (pedido do revisor,
2026‑10‑16): tudo o que se escreve **sobre a planta** para ela virar desenho de
arquitetura. Cortes e fachadas (pacote 7) e pranchas e PDF (pacote 8) vêm depois.

| § | Recurso | Requisito |
|---|---|---|
| 2 | Escala da planta e tamanhos no papel | RF-DOC-04 |
| 3 | Ambientes, com etiqueta de nome e área | RF-AMB-01 a 03 |
| 4 | Cotas lineares associativas e cota automática de parede | RF-DOC-05 |
| 5 | Cota de nível | RF-DOC-05, RF-DOC-07 |
| 6 | Textos, linhas e hachuras 2D | RF-DOC-06 |
| 7 | Norte | RF-DOC-07 |
| 8 | Espessuras de linha por categoria | RF-DOC-03 |

Fica de fora (V1): detalhe por escala (RF-DOC-08), cota angular, de raio e de
coordenada, chamadas com linha de chamada (`LEADER`), símbolos de biblioteca, critérios de
área para prefeitura (RF-AMB-04), zonas (RF-AMB-05).

## 2. Escala da planta
- Cada pavimento tem a sua escala de desenho: 1:20, 1:25, 1:50, 1:75, 1:100, 1:200 ou
  1:500. Padrão **1:50** *(CG)*. Fica no Pset `BrasBim_Pavimento`, propriedade `Escala`
  (o denominador, inteiro; sem gravar quando é o padrão), como o plano de corte (spec/ui
  06 §3.1). Operação: `storey.edit` com `scale`.
- Onde se escolhe: coluna **Escala** no painel do projeto e uma lista na barra de estado
  (a do pavimento ativo).
- **Tamanhos no papel:** textos, etiquetas, cotas e símbolos têm tamanho em milímetros
  de papel; no modelo, medem *tamanho × escala*. Ex.: texto de 2,5 mm a 1:50 = 12,5 cm.
  Mudar a escala muda o tamanho de todos no pavimento, sem mexer no que eles anotam.
- A planta na tela mostra esses tamanhos no zoom (aproximar aumenta o texto como o resto
  do desenho). As etiquetas que já existem (esquadrias, pilar e viga) passam a seguir a
  escala *(decisão do projeto: hoje elas têm tamanho fixo na tela)*.

## 3. Ambientes

### 3.1 IFC
- `IfcSpace`, `PredefinedType` `INTERNAL`, **agregado** ao pavimento
  (`IfcRelAggregates`) [IFC-SPACE].
- `Name` = **número** ("01", "02"…), `LongName` = **nome** ("Sala", "Cozinha")
  [IFC-SPACE, *Name/LongName*].
- Representações: `FootPrint` (`IfcPolyline` fechada, contexto `Plan`) e `Body`
  `SweptSolid` (o contorno extrudado na vertical, com o pé-direito) [IFC-SPACE].
- `Qto_SpaceBaseQuantities`: `NetFloorArea` e `GrossFloorArea` (área do contorno; sem
  descontos nesta etapa), `GrossPerimeter`, `Height` (pé-direito) [IFC-SPACE].
- Pset `BrasBim_Ambiente`: `PeDireitoFixo` (vazio = calculado) e a posição da etiqueta.

### 3.2 Parâmetros e operações
| Parâmetro | Padrão | Regras |
|---|---|---|
| Contorno | — | Polígono simples, anti-horário (como a laje) |
| Número | próximo livre: 01, 02… | Texto; único no pavimento |
| Nome | "Ambiente" | Texto livre |
| Pé-direito | calculado | Da cota do pavimento até o fundo da laje que cobre o centro do ambiente; sem laje, até o pavimento de cima; sem pavimento de cima, 2,80. Pode ser fixado |
| Etiqueta | centro do contorno | Ponto; arrastável (alça) |

| `op` | Dados |
|---|---|
| `space.create` / `.delete` | `storey`, `outline[]`, `number`, `name`, `height` (`None` = calculado), `label_at` |
| `space.edit` | campos alterados (antes/depois) |

O pé-direito calculado e as quantidades são derivados: mudar a laje de cima ou a cota
de um pavimento refaz o ambiente.

### 3.3 Interface
- Ferramenta **Ambiente** na barra Ferramentas, depois de Laje. Modos na barra Opções:
  **Pelo cômodo** (um clique dentro de um cômodo fechado por paredes; contorno na face
  interna, `rooms.py` do pacote 5) e **Polígono** (como a laje). Barra Opções: Nome
  (com sugestões: Sala, Cozinha, Quarto, Banheiro, Área de serviço, Varanda, Circulação,
  Garagem) e Pé-direito (vazio = calculado).
- Painel: Número, Nome, Pé-direito (vazio = calculado; mostra o valor), Área, Perímetro,
  Identificação.
- Mover, Copiar, Girar, Espelhar, Excluir e alças (vértices, meio dos lados, e a da
  etiqueta) como a laje.

### 3.4 Planta
- Etiqueta *(CG)*: **nome** em cima e a **área** embaixo ("12,50 m²"); com Exibir >
  Número dos ambientes, o número antes do nome ("01 · Sala"). Altura do nome 3 mm e da
  área 2,5 mm de papel.
- O contorno não é desenhado (as paredes já o mostram); só aparece realçado na seleção.
  Fundo opcional por ambiente: V1.
- O ambiente fica sob as paredes na escolha (prioridade logo acima da laje): clicar no
  meio do cômodo escolhe o ambiente, se houver um.

## 4. Cotas

### 4.1 IFC
`IfcAnnotation` `DIMENSION`, contida no pavimento (`IfcRelContainedInSpatialStructure`)
[IFC-ANNOT]. Representação `Annotation` no contexto `Plan` com um
`IfcGeometricCurveSet`: a linha de cota, as linhas de chamada, os traços inclinados
(tiques) e um `IfcTextLiteral` por medida. Pset `BrasBim_Cota` com o que a refaz: pontos
(e as referências, §4.3), direção e afastamento. A geometria é derivada.

### 4.2 Parâmetros
| Parâmetro | Regras |
|---|---|
| Pontos | 2 ou mais (cota em cadeia), cada um livre ou preso a um elemento (§4.3) |
| Direção | **Alinhada** (paralela aos dois primeiros pontos), **Horizontal** ou **Vertical** |
| Afastamento | Distância da linha de cota até o primeiro ponto, perpendicular à direção |
| Texto | Medida em metros, 2 casas, vírgula ("3,15") *(CG)*; acima da linha, legível de baixo ou da direita |

Desenho *(CG)*: tique a 45°, de 3 mm; linhas de chamada começando 2 mm depois do ponto e
passando 2 mm da linha de cota; texto de 2,5 mm. Espessura 0,13 mm (§8).

### 4.3 Associativa
Um ponto clicado com atração num elemento fica **preso** a ele e a cota se refaz quando o
elemento muda (move, gira, estica, muda de seção ou de espessura):

| Elemento | Ponto preso |
|---|---|
| Parede | Ponta (início/fim) × face (esquerda, direita) ou eixo |
| Abertura de porta ou janela | Borda (início/fim do vão) × face da parede |
| Pilar | Canto ou meio de lado da seção (em fração de b e h) |
| Viga | Ponta × face ou eixo |
| Laje, ambiente | Vértice do contorno |

Se o elemento some (excluído), o ponto fica livre onde estava (aviso em Mensagens).

### 4.4 Operações
| `op` | Dados |
|---|---|
| `dimension.create` / `.delete` | `storey`, `points[]` (cada um `{"at": [x, y]}` ou `{"ref": {...}}`), `direction` (`aligned`/`horizontal`/`vertical`), `offset` |
| `dimension.edit` | campos alterados |

### 4.5 Interface
- Ferramenta **Cota**: clique o primeiro ponto, os seguintes (cadeia), e um clique fora
  (ou Enter) para a posição da linha. Barra Opções: Direção. Tab: o afastamento.
- **Cota automática de parede:** ação **Cotar** na mini-barra de uma parede reta
  selecionada: cota em cadeia na face externa, com as pontas da parede e as bordas de
  cada vão, afastada 60 cm (papel 12 mm a 1:50) *(CG)*. Uma transação.
- Alças: a linha de cota (afastamento) e cada ponto livre.

## 5. Cota de nível
- `IfcAnnotation` `SYMBOL` com `ObjectType` = "CotaDeNivel" [IFC-ANNOT]; símbolo
  *(CG)*: triângulo com o vértice para baixo sobre uma linha curta, e o valor ao lado,
  com sinal ("+0,00", "+2,80", "−0,15").
- Valor = cota do pavimento + topo da laje sob o ponto, se houver (senão só a do
  pavimento); derivado. Pode ser fixado (texto livre, ex. "+0,05 acabado").
- Ferramenta **Nível** (um clique). Operações `level_mark.create`/`.delete`/`.edit`
  (`storey`, `at`, `fixed`).

## 6. Textos, linhas e hachuras 2D
| Recurso | IFC | Parâmetros | Ferramenta |
|---|---|---|---|
| Texto | `IfcAnnotation` `TEXT`, `IfcTextLiteral` [IFC-ANNOT] | texto (várias linhas), altura no papel (2, 2,5, 3, 3,5, 5 mm; padrão 2,5), ângulo, alinhamento (esquerda, centro, direita) | **Texto**: um clique e digita; clique duplo num texto edita |
| Linha | `IfcAnnotation` (sem tipo), `IfcGeometricCurveSet` com `IfcPolyline`; estilo `IfcCurveStyle` | pontos, aberta/fechada, espessura (§8), tipo: contínua, tracejada, traço e ponto | **Linha**: como a parede reta |
| Hachura | `IfcAnnotation`, `IfcAnnotationFillArea`; estilo `IfcFillAreaStyle` | contorno (polígono), padrão (sólido, linhas, cruzada, como os materiais, spec/ui 06 §4), cor, ângulo, espaçamento no papel | **Hachura**: polígono ou retângulo |

Operações `text.*`, `line2d.*`, `hatch.*` com `storey` e os parâmetros da tabela. Mover,
Copiar, Girar, Espelhar (o texto espelhado continua legível) e Excluir valem para todos.

## 7. Norte
- `IfcAnnotation` `SYMBOL`, `ObjectType` = "Norte": seta com "N", 15 mm de papel
  *(CG)*, com o ângulo dele (o norte verdadeiro do projeto é RF-PRJ-05, V1).
- Ferramenta **Norte** (clique a posição e a direção). Operações `north.*`.

## 8. Espessuras de linha por categoria
Série da NBR 8403 (já usada nos tipos de parede, spec/ui 03 §6) *(CG; conferência com a
norma pendente, `REQUISITOS.md` RF-DOC-03)*:

| Categoria | Espessura (mm) |
|---|---|
| Elemento cortado (parede, pilar, laje cortada) | 0,50 (ou a do tipo) |
| Elemento em vista (abaixo do plano) | 0,25 |
| Acima do plano (tracejado) | 0,18 |
| Esquadrias | 0,25 |
| Cotas, linhas de chamada | 0,13 |
| Textos e etiquetas | 0,18 |
| Linha 2D | a escolhida (padrão 0,25) |

As espessuras ficam numa tabela só (`core/plan.py`), usada pela planta e, depois, pelo
PDF (pacote 8). Na tela, Exibir > **Espessuras de linha** liga o desenho com as
espessuras do papel na escala (padrão ligado); desligado, tudo fino.

## 9. Núcleo e interface: o que muda
- `core/annotations/` (novo, sem Qt): `spaces.py`, `dimensions.py` (referências e
  geometria), `level_marks.py`, `drafting.py` (texto, linha, hachura, norte), `rebuild.py`
  (derivação: refaz cotas, níveis e ambientes quando o que eles anotam muda), `commands.py`.
- `core/storeys.py`: `scale`. `core/plan.py`: papéis novos (`space`, `dimension`,
  `level_mark`, `text`, `line2d`, `hatch`, `north`) e tabela de espessuras.
- `core/transform.py`: mover, girar, espelhar e copiar as anotações e os ambientes; as
  cotas presas acompanham os elementos pela derivação.
- Interface: ferramentas Ambiente, Cota, Nível, Texto, Linha, Hachura e Norte, num grupo
  **Documentação** da barra Ferramentas *(decisão do projeto: separa desenho de modelo)*;
  ícones próprios; desenho dos papéis novos na planta; painel de cada um.
- Atualizar `spec/01-modelo-de-dados.md` com as operações.

## 10. Critérios de aceite (testes)
Térreo (0,00) e Superior (2,80); retângulo de paredes de 14 cm por dentro de
(0, 0)–(5, 4); escala 1:50.

**Escala**
- [ ] **DO01** Mudar a escala do Térreo para 1:100: o Pset guarda 100; a altura de um
      texto de 2,5 mm vai de 0,125 m para 0,25 m no modelo; desfazer volta.

**Ambientes**
- [ ] **AM01** Ambiente pelo cômodo em (2, 2): `IfcSpace` `INTERNAL` agregado ao Térreo,
      `Name` "01", `LongName` "Ambiente"; `NetFloorArea` 4,72 × 3,72 = 17,5584;
      `FootPrint` e `Body` presentes.
- [ ] **AM02** Laje de 10 cm no Superior sobre o cômodo: pé-direito 2,70; sem a laje,
      2,80; fixado em 2,60, fica 2,60.
- [ ] **AM03** Dois ambientes: números 01 e 02; excluir o 01 e criar outro dá 01.
- [ ] **AM04** Etiqueta "Sala" / "17,56 m²" no centro; arrastar a alça move só a
      etiqueta.
- [ ] **AM05** Mover e girar o ambiente; desfazer e o diário reproduzem o IFC.

**Cotas**
- [ ] **CT01** Cota horizontal de (0, 0) a (5, 0), afastamento −0,6: `IfcAnnotation`
      `DIMENSION` contida no Térreo; texto "5,00".
- [ ] **CT02** Cota presa às pontas da face externa de uma parede: esticar a parede para
      6 m muda o texto para "6,00".
- [ ] **CT03** Cota presa ao canto de um pilar: mover o pilar move o ponto da cota.
- [ ] **CT04** Excluir o pilar: o ponto fica livre no lugar; aviso em Mensagens; desfazer
      volta a prender.
- [ ] **CT05** Cotar a parede com uma porta de 0,80 a 1,00 do início: cadeia "1,00 · 0,80
      · …" até o fim, numa transação.
- [ ] **CT06** Cota em cadeia com 4 pontos: 3 textos.

**Nível, textos, linhas, hachuras, norte**
- [ ] **NV01** Nível sobre uma laje de topo −0,05 no Térreo: "−0,05"; mudar a laje para
      0,00 muda para "+0,00".
- [ ] **TX01** Texto "PLANTA BAIXA" de 5 mm: `IfcAnnotation` `TEXT` com `IfcTextLiteral`
      e altura 0,25 m a 1:50; girar 90° e espelhar: continua legível.
- [ ] **LH01** Linha tracejada de 0,35 mm: `IfcCurveStyle` com a espessura e o padrão.
- [ ] **HC01** Hachura sólida cinza num retângulo: `IfcAnnotationFillArea` com
      `IfcFillAreaStyle`.
- [ ] **NO01** Norte a 30°: o símbolo aponta para 30°; o arquivo passa na validação de
      esquema.

**Gerais**
- [ ] **DO02** Todas as anotações e ambientes passam na validação de esquema do
      IfcOpenShell e os diários reaplicados reproduzem o IFC.
- [ ] **DO03** Exibir > Espessuras de linha liga e desliga as espessuras na tela.

## 11. Fontes públicas
IFC 4.3 no repositório oficial da buildingSMART, ramo `ifc4.3-main`, consultado em
2026‑10‑16, e o esquema EXPRESS `IFC4X3_ADD2` distribuído com o IfcOpenShell
(enumerações `IfcAnnotationTypeEnum`, `IfcSpaceTypeEnum`; atributos de `IfcAnnotation`,
`IfcSpace`, `IfcTextLiteral`).

| Código | Documento |
|---|---|
| IFC-ANNOT | `docs/schemas/core/IfcProductExtension/Entities/IfcAnnotation.md` (contenção no pavimento; `IfcGeometricCurveSet`, `IfcAnnotationFillArea`, `IfcTextLiteral`) |
| IFC-SPACE | `docs/schemas/core/IfcProductExtension/Entities/IfcSpace.md` (agregação ao pavimento; `Name` = número, `LongName` = nome; `FootPrint` e `Body`; `Qto_SpaceBaseQuantities`) |

Outras:
- **NBR 8403** (espessuras de linha) e **NBR 6492** (representação de projetos de
  arquitetura): como nas specs anteriores, **texto não lido**; os valores são
  conhecimento geral e ficam para conferência.
- **CG**: convenções usuais do desenho de arquitetura no Brasil (cotas em metros com duas
  casas, tique a 45°, etiqueta de ambiente com nome e área, símbolo de nível, escalas
  usuais).

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

## 12. Pontos de revisão
(a) Escala por pavimento, padrão 1:50, e as etiquetas existentes passando a seguir a
    escala (§2).
(b) Pé-direito calculado até o fundo da laje de cima (§3.2).
(c) Etiqueta do ambiente: nome e área; número só com a opção (§3.4).
(d) Cotas em metros com duas casas e tique a 45° (§4.2).
(e) Cota automática na face externa, a 60 cm (§4.5).
(f) Grupo Documentação na barra Ferramentas, com 7 ferramentas (§9).
