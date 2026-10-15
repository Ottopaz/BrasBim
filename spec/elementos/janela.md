---
elemento: Janela
entidade_ifc: IfcWindow (PredefinedType e PartitioningType via IfcWindowType)
requisito: RF-ELE-06
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-14
status: aprovado
revisor: OTTO (aprovado em 2026-10-14)
---

# Janela

A janela segue tudo o que `porta.md` marca como **(comum)**: posição na parede,
alinhamento na espessura, sentido de abertura, variantes de mão, Psets próprios,
operações sobre a abertura, exclusão em cascata e IFC de outra origem. Esta spec
descreve só o que é diferente.

## 1. Propósito
Elemento que fecha um vão para dar luz e, em geral, ventilação. É formado por um marco
e um ou mais caixilhos (folhas), fixos ou móveis, normalmente envidraçados. [IFC-WIN]
No MVP a janela fica sempre num vão de parede reta.

## 2. Mapeamento IFC

### 2.1 Entidade e tipo
- Ocorrência: `IfcWindow`. Tipo: `IfcWindowType` via `IfcRelDefinesByType`.
  `PredefinedType` e `PartitioningType` ficam no tipo; na ocorrência ficam vazios.
  [IFC-WIN, *CorrectPredefinedType*]
- `IfcWindowType.ParameterTakesPrecedence = TRUE` (substitui o antigo
  `IfcWindowStandardCase`). [IFC-WIN, IFC-WINTYPE]
- `IfcWindowTypeEnum` no MVP: `WINDOW`. `SKYLIGHT` e `LIGHTDOME` (aberturas zenitais,
  citadas em RF-ELE-06) ficam para V1 porque dependem da laje e da cobertura.
  [IFC-WINENUM]

### 2.2 Divisão em caixilhos (`PartitioningType`)
No IFC, o tipo diz **como o vão é dividido** e cada caixilho diz **como opera**.
[IFC-WINPART, IFC-WPP]

| Divisão no BrasBim | `PartitioningType` | Posições dos caixilhos |
|---|---|---|
| 1 caixilho | `SINGLE_PANEL` | — |
| 2 lado a lado | `DOUBLE_PANEL_VERTICAL` (montante) | `LEFT`, `RIGHT` |
| 2 um sobre o outro | `DOUBLE_PANEL_HORIZONTAL` (travessa) | `TOP`, `BOTTOM` |
| 3 lado a lado | `TRIPLE_PANEL_VERTICAL` | `LEFT`, `MIDDLE`, `RIGHT` |
| 3 um sobre o outro | `TRIPLE_PANEL_HORIZONTAL` | `TOP`, `MIDDLE`, `BOTTOM` |

Posições e ordem: [IFC-WPPOS]. `TRIPLE_PANEL_BOTTOM/TOP/LEFT/RIGHT` ficam para V1.
**Quatro ou mais caixilhos** (ex.: janela de correr de 4 folhas, muito comum no Brasil)
não têm divisão paramétrica no IFC: só como `USERDEFINED` com geometria explícita.
[IFC-WINPART] Fica para V1, com proposta de `UserDefinedPartitioningType` próprio.
**Ponto de revisão** (pela frequência no mercado brasileiro).

### 2.3 Operação de cada caixilho
`IfcWindowPanelOperationEnum`, com nome em pt‑BR *(CG)*:

| Nome no BrasBim | `OperationType` do caixilho | Tem mão? |
|---|---|---|
| Fixo | `FIXEDCASEMENT` | não |
| De abrir (giro lateral) | `SIDEHUNGLEFTHAND` / `SIDEHUNGRIGHTHAND` | sim |
| Oscilobatente | `TILTANDTURNLEFTHAND` / `TILTANDTURNRIGHTHAND` | sim |
| Maxim‑ar (eixo no topo, projeta para fora) | `TOPHUNG` | não |
| Tombar (eixo na base) | `BOTTOMHUNG` | não |
| Basculante (eixo horizontal no meio) | `PIVOTHORIZONTAL` | não |
| Pivotante (eixo vertical no meio) | `PIVOTVERTICAL` | não |
| De correr | `SLIDINGHORIZONTAL` | não |
| Guilhotina | `SLIDINGVERTICAL` | não |

Significado dos valores: [IFC-WPOP]. A correspondência com os nomes brasileiros é
*(CG)*, **ponto de revisão** (ex.: "basculante" com várias palhetas é, a rigor, vários
caixilhos pivotantes; no MVP é um caixilho só).

### 2.4 Mão e sentido de abertura
Iguais aos da porta (`porta.md` §2.2): o caixilho abre para o +y local; "mão esquerda"
quer dizer dobradiças à esquerda vistas do lado oposto ao da abertura. [IFC-WIN,
*Window Attributes*; IFC-WPOP] Aqui a mão fica em cada caixilho (`OperationType`), mas
continua sendo do **tipo**. Um tipo tem variantes de mão quando algum caixilho tem mão
e o tipo não é simétrico (ex.: 1 folha de abrir). Duas folhas de abrir, uma esquerda e
outra direita, formam um tipo simétrico, sem variante. A variante espelha as posições
(`LEFT` ↔ `RIGHT`) e as mãos.

Para caixilhos sem sentido de abertura (fixo, correr, guilhotina), "abre para" indica o
**lado interno** da janela (é o que orienta o posicionamento). Padrão: o lado em que
estava o cursor na criação. *(decisão do projeto)*

### 2.5 Representações, material, parâmetros no tipo
- `Profile` (`Curve3D`, retângulo no plano xz) e `Body` (`SweptSolid`, peça por peça),
  na ocorrência, como na porta. [IFC-WIN, *Profile 3D Geometry*]
- `IfcMaterialConstituentSet` no tipo com `Lining`, `Framing` e `Glazing`; um
  `IfcMaterial` único vale para marco e caixilhos. [IFC-WIN, *Material Set*;
  IFC-WINTYPE]
- `IfcWindowLiningProperties` (1) e `IfcWindowPanelProperties` (1 por caixilho) em
  `IfcWindowType.HasPropertySets`, com a mesma decisão da porta sobre as entidades
  descontinuadas no 4.3.2 (`porta.md` §2.5): gravar as entidades e aceitar, ao ler,
  `Pset_WindowLiningProperties`/`Pset_WindowPanelProperties`. [IFC-WLP, IFC-WPP,
  IOS-PSET]
- Posicionamento relativo ao `IfcOpeningElement`. [IFC-WIN, *Product Local Placement*]
- Relações: as mesmas da porta (`porta.md` §2.7), com `IfcWindow`. A janela também é
  contida no pavimento da parede. [IFC-WIN, *Spatial Containment*]
- `Pset_WindowCommon` (§3.3), `Qto_WindowBaseQuantities` (§8), `BrasBim_Esquadria` e
  `BrasBim_EsquadriaTipo` (`porta.md` §3.4).

## 3. Parâmetros

### 3.1 Ocorrência
Os mesmos da porta (`porta.md` §3.1), com estas diferenças:

| Parâmetro | Padrão | Regras |
|---|---|---|
| Peitoril (base do vão) | do tipo (ex.: 1,10 m) | Em relação à base da parede (= `sill` da abertura). A interface mostra também a cota em relação ao piso do pavimento quando a base da parede tem deslocamento |
| Altura da verga | calculada | Peitoril + altura; editar a verga muda a altura, mantendo o peitoril |
| Abre para | lado do cursor | Para fixo/correr/guilhotina, é o lado interno (§2.4) |
| Alinhamento na espessura | `eixo` | Como na porta; a profundidade do marco é fixa no tipo (§3.2) |

### 3.2 Tipo
| Parâmetro | Atributo IFC | Padrão *(CG, a revisar)* | Regras |
|---|---|---|---|
| Nome | `IfcWindowType.Name` | — | Único entre tipos de janela |
| Divisão | `PartitioningType` | `DOUBLE_PANEL_VERTICAL` | §2.2 |
| Operação de cada caixilho | `IfcWindowPanelProperties.OperationType` | correr / correr | §2.3; uma por posição |
| Profundidade do marco | `LiningDepth` | 0,05 m | > 0. Na janela é **fixa** (não acompanha a parede) |
| Espessura do marco | `LiningThickness` | 0,03 m | ≥ 0 |
| Montante: espessura e posição | `MullionThickness`, `FirstMullionOffset`, `SecondMullionOffset` | 0,03 m; 1/2 (ou 1/3 e 2/3) | Posição como fração da largura, 0 < f < 1, crescente |
| Travessa: espessura e posição | `TransomThickness`, `FirstTransomOffset`, `SecondTransomOffset` | 0,03 m; 1/2 (ou 1/3 e 2/3) | Fração da altura, a partir da base |
| Caixilho: profundidade e largura do perfil | `FrameDepth`, `FrameThickness` | 0,03 m; 0,04 m | Por caixilho |
| Folga marco–caixilho | `LiningToPanelOffsetX/Y` | 0 | — |
| Materiais | `Lining`/`Framing`/`Glazing` | alumínio, alumínio, vidro | — |
| Dimensões padrão | `BrasBim_EsquadriaTipo` | 1,20 × 1,00, peitoril 1,10 | Usadas ao inserir |

Uma montante com espessura 0 divide sem peça física, como o IFC prevê. [IFC-WLP]

### 3.3 `Pset_WindowCommon` (MVP)
| Propriedade | Tipo IFC | Padrão | Observação |
|---|---|---|---|
| `Reference` | IfcIdentifier | código do tipo (ex.: `J1`) | Etiquetas e tabela de esquadrias |
| `Status` | `PEnum_ElementStatus` | `NEW` | — |
| `IsExternal` | IfcBoolean | **verdadeiro** | Janelas são em geral externas; inferido em V1. *(decisão do projeto)* |
| `HasSillExternal`, `HasSillInternal` | IfcBoolean | vazio | Peitoril de pedra / pingadeira; só a informação (geometria em V1) |
| `GlazingAreaFraction` | IfcPositiveRatioMeasure | vazio | Cálculo automático em V1 (útil para iluminação e ventilação) |
| `FireRating`, `AcousticRating`, `SecurityRating`, `ThermalTransmittance`, `Infiltration`, `FireExit`, `SmokeStop`, `HasDrive`, `*LoadRating`, `WaterTightnessRating` | conforme [IFC-PSET-W] | vazio | Só gravadas se preenchidas |

### 3.4 Biblioteca inicial (RF-TIP-06)
Exemplos a revisar *(CG)*: correr 2 folhas 1,20 × 1,00 e 1,50 × 1,20 (peitoril 1,10);
maxim‑ar 0,60 × 0,60 (peitoril 1,50, banheiro); basculante 0,60 × 0,40 (peitoril 1,70);
de abrir 2 folhas 1,00 × 1,20; fixa 1,00 × 1,00.

## 4. Criação
Como a porta (`porta.md` §4), com estas diferenças: o peitoril padrão vem do tipo; a
pré‑visualização mostra a cota do peitoril e da verga; a transação é `opening.create` →
(`window_type.create` da variante, se faltar) → `window.create` → `filling.attach`.

## 5. Edição

### 5.1 Interações
As da porta (`porta.md` §5.1), mais: alças de peitoril (base) e verga (topo) na vista
3D, corte e fachada; edição numérica de peitoril e verga.

### 5.2 Operações serializáveis
| `op` | Dados |
|---|---|
| `window_type.create` / `.delete` | `name`, `predefined_type`, `partitioning`, `lining` (`depth`, `thickness`, `mullion_thickness`, `mullion_offsets[]`, `transom_thickness`, `transom_offsets[]`), `panels[]` (`operation`, `position`, `frame_depth`, `frame_thickness`), `materials`, `defaults` (`width`, `height`, `base`), `variant` |
| `window_type.edit` | campos alterados (antes/depois) |
| `window.create` / `.delete` / `.edit` | `name`, `type`, `opens_to`, `align`, `offset`, `common` |
| `opening.*`, `filling.*` | já existentes |

As mesmas regras de efeitos derivados e reserva da porta (`porta.md` §5.2).

## 6. Comportamento e regras geométricas

### 6.1 Posição
Fórmula da faixa do marco e do posicionamento: `porta.md` §6.1, com `d` = `LiningDepth`
do tipo (sempre preenchido). Quando a espessura da parede muda, a janela mantém o
alinhamento e o deslocamento, então a profundidade do marco não muda e a posição é
recalculada. Marco mais profundo que a parede: aviso.

### 6.2 Corpo
- Marco: quatro peças (com base, diferente da porta) de seção `LiningThickness × d`
  por dentro do `Profile`; montantes e travessas na profundidade do marco, centrados
  nas posições do tipo. [IFC-WLP, *Table 1*]
- Caixilhos: moldura de `FrameThickness × FrameDepth` em cada espaço do marco, com
  vidro no meio (placa fina, 0,006 m *(CG)*), desenhados **fechados**. [IFC-WPP]
- Caixilhos de correr: em planos paralelos (trilhos), deslocados na profundidade do
  marco, sobrepostos na largura do montante. *(CG)*
- Nada de peitoril de pedra, pingadeira, verga ou contraverga como geometria no MVP.

### 6.3 Relação com a parede, exclusão, IFC de outra origem
Iguais à porta (`porta.md` §6.3, §6.4 e §6.6), com `window.*` no lugar de `door.*`.
Excluir a parede com porta e janela gera a cascata de cada uma, em ordem de `GlobalId`
das aberturas.

### 6.4 Verificações (V1, RF-BR)
Área de iluminação e ventilação por ambiente (códigos de obras municipais) e peitoril
mínimo de segurança. Precisa de ambientes (RF-AMB) e de fontes normativas; não faz
parte do MVP.

## 7. Representação 2D
Convenções gerais do desenho arquitetônico brasileiro *(CG)*; conferência com a
NBR 6492 pendente.

| Situação | Planta |
|---|---|
| Vão cortado pelo plano (peitoril < plano de corte < verga) | Parede interrompida; marco cortado; linhas dos caixilhos/vidro; peitoril em projeção (linha da parede abaixo) |
| Janela inteira acima do plano de corte (ex.: basculante alto) | Contorno tracejado, como elemento acima do plano |
| Janela inteira abaixo do plano de corte | Linhas de projeção |

- Correr: caixilhos em linhas paralelas deslocadas; de abrir: folha aberta e arco em
  linha fina, como a porta; maxim‑ar/basculante: só as linhas do caixilho.
- Fachada/vista: marco, montantes, travessas e caixilhos; símbolo de abertura
  (triângulo apontando para o eixo de giro; seta para correr), com convenção
  configurável, vista de fora ou de dentro (o IFC avisa que cada país usa uma).
  [IFC-WIN, *Window Attributes*]
- Corte: marco e caixilho cortados; peitoril e verga da parede.
- **Etiqueta:** `Reference` (ex.: `J1`) e, opcional, "largura × altura / peitoril"
  (ex.: `1,20 × 1,00 / 1,10`). Formato configurável. *(CG)*
- Níveis de detalhe como na porta.

## 8. Quantitativos
`Qto_WindowBaseQuantities`, recalculado a cada alteração. [IFC-QTO-W] Mesmas
definições da porta: `Width`, `Height`, `Area = Width × Height`,
`Perimeter = 2 × (Width + Height)`, sobre o contorno externo do marco (= vão).

## 9. Critérios de aceite (testes)
Mesma base da porta (parede reta de 5 m, 14 cm, 2,80 m).

- [x] **JA01** Janela de correr 2 folhas 1,20 × 1,00, peitoril 1,10, a 1,50 m do início:
      `IfcWindow` com `OverallWidth/Height`; `IfcOpeningElement` com z = 1,10 no
      posicionamento; `IfcRelVoidsElement`, `IfcRelFillsElement` e contenção no
      pavimento.
- [x] **JA02** Tipo: `WINDOW`, `DOUBLE_PANEL_VERTICAL`, `ParameterTakesPrecedence =
      TRUE`; 1 `IfcWindowLiningProperties` (`LiningDepth = 0,05`,
      `FirstMullionOffset = 0,5`); 2 `IfcWindowPanelProperties` (`LEFT`/`RIGHT`,
      `SLIDINGHORIZONTAL`).
- [x] **JA03** Maxim‑ar 0,60 × 0,60 abrindo para a face direita: `SINGLE_PANEL`,
      `TOPHUNG`; posicionamento girado 180° (+y da janela = −y da parede).
- [x] **JA04** `Profile`: retângulo 1,20 × 1,00 no plano xz, y = 0.
- [x] **JA05** `Body`: marco com profundidade 0,05 dentro da parede, centrado no eixo;
      trocar a parede para 19 cm mantém a profundidade 0,05 e recentraliza.
- [x] **JA06** Tipo com marco de 0,20 numa parede de 0,14: aviso, janela criada.
- [x] **JA07** De abrir 1 folha: inverter a mão cria a variante
      (`SIDEHUNGRIGHTHAND`) uma vez só. De abrir 2 folhas (esquerda + direita): sem
      variante.
- [x] **JA08** Editar o peitoril para 1,30 → `opening.edit` (`sill`); verga acima do
      topo da parede é recusada pelo comando.
- [x] **JA09** `Qto_WindowBaseQuantities`: `Area = 1,20`, `Perimeter = 4,40`.
- [x] **JA10** `Pset_WindowCommon` com `Status = NEW`, `IsExternal = TRUE`, `Reference`
      do tipo.
- [x] **JA11** Excluir a parede com uma porta e uma janela: nenhuma entidade órfã;
      desfazer restaura os mesmos `GlobalId`s.
- [x] **JA12** Cada ação gera as operações de §5.2; desfazer/refazer e reaplicar o
      diário reproduzem o mesmo IFC.
- [x] **JA13** IFC de outra origem (janela com `Body` próprio): corpo preservado;
      mover funciona.
- [x] **JA14** Arquivo passa na validação de esquema do IfcOpenShell.

## 10. Fontes públicas
Mesmo repositório, ramo e data de `porta.md` §10 (`S` e `A` idem).

| Código | Documento |
|---|---|
| IFC-WIN | `S/Entities/IfcWindow.md` |
| IFC-WINTYPE | `S/Entities/IfcWindowType.md` |
| IFC-WINENUM | `S/Types/IfcWindowTypeEnum.md` |
| IFC-WINPART | `S/Types/IfcWindowTypePartitioningEnum.md` |
| IFC-WLP | `A/Entities/IfcWindowLiningProperties.md` |
| IFC-WPP | `A/Entities/IfcWindowPanelProperties.md` |
| IFC-WPOP | `A/Types/IfcWindowPanelOperationEnum.md` |
| IFC-WPPOS | `A/Types/IfcWindowPanelPositionEnum.md` |
| IFC-PSET-W | `S/PropertySets/Pset_WindowCommon.md` e `reference_schemas/psd/Pset_WindowCommon.xml` |
| IFC-QTO-W | `S/QuantitySets/Qto_WindowBaseQuantities.md` e `reference_schemas/psd/Qto_WindowBaseQuantities.xml` |

Outras:
- **IOS** — IfcOpenShell 0.9: existência de `geometry.add_window_representation`.
- **IOS-PSET** — modelos `IFC4X3` do IfcOpenShell 0.9: `Pset_WindowLiningProperties` e
  `Pset_WindowPanelProperties` substituem as entidades a partir do 4.3.2.0.
- **NBR6492** — como na parede; **texto não lido**.
- **CG** — tipos de janela usuais no Brasil e seus nomes, dimensões e peitoris comuns,
  convenções de planta e etiqueta.

Nenhum material de `_restrito/` nem de `tools/` foi usado.

## 11. Fora do escopo / pendências
- V1: janelas zenitais (`SKYLIGHT`, `LIGHTDOME`); `TRIPLE_PANEL_BOTTOM/TOP/LEFT/RIGHT`;
  4 ou mais caixilhos; janela em parede em arco; peitoril de pedra, pingadeira,
  veneziana, grade; `GlazingAreaFraction` e `IsExternal` automáticos; verificações de
  iluminação e ventilação.
- V2: janela em fachada‑cortina.
- Pontos de revisão, aceitos pelo revisor em 2026‑10‑14: (a) nomes brasileiros × `IfcWindowPanelOperationEnum` (§2.3);
  (b) janela de correr de 4 folhas fora do MVP (§2.2); (c) `IsExternal` verdadeiro por
  padrão; (d) "abre para" como lado interno nos caixilhos sem giro (§2.4); (e) os
  pontos comuns de `porta.md` §11.
