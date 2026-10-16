---
elemento: Pilar
entidade_ifc: IfcColumn (PredefinedType via IfcColumnType)
requisito: RF-ELE-03
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-15
status: aprovado
revisor: OTTO (aprovado em 2026-10-15)
---

# Pilar

Spec do **básico**: pilar vertical, reto, de seção retangular ou circular, com base e
topo ligados aos pavimentos como a parede. Perfis metálicos e pilar inclinado vêm depois
(§11).

## 1. Propósito
Elemento vertical e esbelto que leva ao que está embaixo as cargas da estrutura de cima,
em geral num cruzamento de eixos. Pode também ser só arquitetônico (sem função
estrutural). [IFC-COL]

## 2. Mapeamento IFC

### 2.1 Entidade e tipo
- Ocorrência `IfcColumn`; tipo `IfcColumnType` via `IfcRelDefinesByType`. O
  `PredefinedType` fica no tipo. [IFC-COL, *CorrectPredefinedType*]
- `IfcColumnTypeEnum` no MVP: `COLUMN`. `PILASTER` (pilar embutido na parede) fica para
  V1. [IFC-COLENUM]

### 2.2 Material e perfil
- `IfcMaterialProfileSet` no tipo, com **um** `IfcMaterialProfile` (material + perfil):
  `IfcRectangleProfileDef` (`XDim` = b, `YDim` = h) ou `IfcCircleProfileDef`
  (`Radius` = d/2), com `Position` vazio (centro na origem). [IFC-COL, *Material
  Profile Set Usage*; IFC-MPS; IFC-MP]
- `IfcMaterialProfileSetUsage` na ocorrência com `CardinalPoint` = ponto de inserção
  (§3.1). O perfil é **compartilhado** entre o tipo e todas as ocorrências. [IFC-COL;
  IFC-MPSU; IFC-CARD]

### 2.3 Representações
- `Axis` (`Curve3D`): `IfcPolyline` de dois pontos sobre o eixo z do elemento, de z = 0
  a z = altura, passando pelo ponto de inserção. [IFC-COL, *Axis 3D Geometry*]
- `Body` (`SweptSolid`): `IfcExtrudedAreaSolid` do perfil do tipo, em +z, profundidade =
  altura. O `Position` do sólido desloca o perfil para que o ponto de inserção caia no
  eixo, coerente com o `CardinalPoint`. [IFC-COL, *Body SweptSolid Geometry*,
  *Figure CALAXCARPOINT*]
- Posicionamento: `IfcLocalPlacement` relativo ao pavimento base, origem no ponto de
  inserção na cota da base, eixo x girado pelo ângulo do pilar.

### 2.4 Propriedades, quantidades e relações
- `Pset_ColumnCommon` (§3.3), `Qto_ColumnBaseQuantities` (§8) e o Pset próprio
  `BrasBim_Pilar` com os vínculos (§3.1).
- `IfcRelContainedInSpatialStructure` com o pavimento base. [IFC-COL]

## 3. Parâmetros

### 3.1 Ocorrência
| Parâmetro | Tipo | Unidade | Padrão | Regras |
|---|---|---|---|---|
| Ponto de inserção (posição) | ponto 2D | m | — | — |
| Ponto de inserção (na seção) | enum: centro, 4 cantos, meio dos 4 lados | — | centro | Mapeado para `CardinalPoint` 1–9 [IFC-CARD]; circular só centro |
| Ângulo | real | ° | 0 | Rotação em planta, anti‑horária, do lado b em relação ao eixo x do pavimento |
| Pavimento base | ref. `IfcBuildingStorey` | — | pavimento ativo | — |
| Deslocamento da base | real | m | 0,00 | — |
| Topo | `ligado a pavimento` \| `altura fixa` | — | `ligado a pavimento` | Como na parede (`parede.md` §3.1) |
| Pavimento do topo / deslocamento do topo | ref., real | —, m | o de cima, 0,00 | — |
| Altura fixa | real | m | 2,80 | > 0 |
| Altura resultante | real (calculado) | m | — | > 0; senão a operação é recusada |
| Nome | texto | — | P1, P2… | Próximo número livre no projeto. Editável |

Correspondência do ponto de inserção com o `CardinalPoint`, vista de cima com ângulo 0
(b ao longo de x, h ao longo de y): canto inferior esquerdo = 1, meio de baixo = 2,
canto inferior direito = 3, meio esquerdo = 4, centro = 5, meio direito = 6, canto
superior esquerdo = 7, meio de cima = 8, canto superior direito = 9. [IFC-CARD]
`BrasBim_Pilar` guarda os vínculos (base, topo, deslocamentos, altura fixa) e o ângulo,
como `BrasBim_Parede`. *(decisão do projeto)*

### 3.2 Tipo
| Parâmetro | Atributo IFC | Padrão *(CG)* | Regras |
|---|---|---|---|
| Nome | `IfcColumnType.Name` | — | Único entre tipos de pilar |
| Seção | perfil | retangular | retangular \| circular |
| b × h / diâmetro | `XDim`, `YDim` / `Radius` × 2 | 0,20 × 0,40 | > 0,01 m |
| Material | `IfcMaterialProfile.Material` | Concreto | — |
| Representação na planta | `BrasBim_RepresentacaoPlanta` | do material (fundo sólido) | Como na parede |

### 3.3 `Pset_ColumnCommon` (MVP) [IFC-PSET-C]
| Propriedade | Tipo IFC | Padrão | Observação |
|---|---|---|---|
| `Reference` | IfcIdentifier | nome do tipo | — |
| `Status` | `PEnum_ElementStatus` | `NEW` | — |
| `LoadBearing` | IfcBoolean | verdadeiro | — |
| `IsExternal` | IfcBoolean | falso | — |
| `FireRating`, `ThermalTransmittance` | conforme [IFC-PSET-C] | vazio | Só gravadas se preenchidas |
| `Slope`, `Roll` | — | não gravadas | O IFC as trata como informação redundante, só de saída; a geometria manda |

### 3.4 Biblioteca inicial *(CG, a revisar)*
Concreto 14 × 30, 20 × 20, 20 × 40, 25 × 50 (retangulares); concreto Ø 30 (circular).
Nome do tipo = "Pilar b×h" em centímetros (ex.: "Pilar 20×40").

## 4. Criação
Um clique posiciona o pilar no ponto de inserção. Antes do clique, a barra Opções escolhe
o tipo, o ponto de inserção na seção e o ângulo. Durante a pré‑visualização, a barra de
espaço gira 90° *(CG)*. Os pontos de atração incluem os vértices e cruzamentos das
paredes, para pôr o pilar no canto ou no meio de uma parede. Transação:
(`column_type.create`, se faltar) → `column.create`.

## 5. Edição

### 5.1 Interações
- Mover, copiar, girar (muda posição e ângulo), espelhar (espelha a posição e o ângulo;
  a seção é simétrica) e excluir.
- Alça na planta: o ponto de inserção (arrastar move o pilar).
- Painel: tipo, ponto de inserção, ângulo, base e topo, nome, propriedades comuns.

### 5.2 Operações serializáveis
| `op` | Dados |
|---|---|
| `column_type.create` / `.delete` | `name`, `predefined_type`, `section` (`rect` com `b`, `h` \| `circle` com `d`), `material`, `plan` |
| `column_type.edit` | campos alterados (antes/depois) |
| `column.create` / `.delete` | `guid`, `name`, `type`, `storey`, `point`, `cardinal`, `angle`, `base_offset`, `top` (`storey`, `offset` \| `height`), `common` |
| `column.edit` | campos alterados (antes/depois) |

## 6. Comportamento e regras geométricas
- Corpo: perfil do tipo extrudado da base ao topo. Mudar a cota de um pavimento
  recalcula os pilares ligados a ele, como as paredes.
- **Com a parede (só na planta):** onde o pilar corta a parede, a mancha e as linhas
  da parede são recortadas pela seção do pilar e o contorno do pilar fica por cima
  (o pilar tem prioridade). O IFC da parede não muda. *(CG)*
- **No 3D e nos volumes, sem recortes no básico:** pilar, parede, viga e laje podem se
  sobrepor. Os recortes por prioridade ficam para V1. **Ponto de revisão.**
- Excluir o pilar não afeta outros elementos.

## 7. Representação 2D
| Situação | Planta |
|---|---|
| Cortado pelo plano (base < plano < topo) | Seção com fundo do material e contorno grosso de corte; desenhado acima das paredes |
| Inteiro abaixo do plano | Contorno em linha fina de projeção |
| Inteiro acima do plano | Contorno tracejado, com "Elementos acima do plano de corte" |

- Por camadas (spec/ui 06): a seção usa o fundo e a hachura do material do perfil.
- **Etiqueta** opcional, junto ao pilar: "P1" e, abaixo, "20×40" *(CG)*. Ligada pelo
  mesmo menu das etiquetas de esquadrias (V1 separar).

## 8. Quantitativos
`Qto_ColumnBaseQuantities`, recalculado a cada alteração. [IFC-QTO-C]

| Quantidade | Cálculo |
|---|---|
| `Length` | altura resultante |
| `CrossSectionArea` | b × h ou π d²/4 |
| `OuterSurfaceArea` | perímetro da seção × altura (só a face lateral) |
| `GrossVolume` = `NetVolume` | área da seção × altura (sem recortes no básico) |

## 9. Critérios de aceite (testes)
- [ ] **PI01** Pilar 20×40 em (2, 3) no Térreo (0,00), topo no Superior (2,80):
      `IfcColumn` + `IfcColumnType` `COLUMN`; `Axis` de z = 0 a 2,80; `Body`
      `IfcExtrudedAreaSolid` com profundidade 2,80; contido no Térreo.
- [ ] **PI02** `IfcMaterialProfileSet` no tipo com `IfcRectangleProfileDef` 0,20 ×
      0,40; `IfcMaterialProfileSetUsage` com `CardinalPoint = 5`; o perfil do `Body` é
      a mesma entidade do material.
- [ ] **PI03** Ponto de inserção canto inferior esquerdo (`CardinalPoint = 1`): a seção
      ocupa x ∈ [2; 2,2], y ∈ [3; 3,4] (ângulo 0).
- [ ] **PI04** Ângulo 90°: a seção ocupa x ∈ [1,8; 2,2], y ∈ [2,9; 3,1] (centro).
- [ ] **PI05** Circular Ø 30: `IfcCircleProfileDef` com `Radius = 0,15`.
- [ ] **PI06** Mudar a cota do Superior para 3,00: altura 3,00 e `Length = 3,00`.
- [ ] **PI07** Topo abaixo da base: `column.create`/`.edit` recusado.
- [ ] **PI08** `Qto_ColumnBaseQuantities` do 20×40 de 2,80: `CrossSectionArea` 0,08,
      `OuterSurfaceArea` 3,36, `GrossVolume` 0,224.
- [ ] **PI09** `Pset_ColumnCommon`: `Reference`, `Status = NEW`, `LoadBearing = TRUE`;
      `BrasBim_Pilar` gravado; reabrir reproduz o pilar.
- [ ] **PI10** Nomes automáticos P1, P2; excluir P1 e criar outro dá P1 de novo.
- [ ] **PI11** Planta: pilar sobre uma parede de 14 cm recorta a região da parede
      (a área da parede na planta diminui da interseção).
- [ ] **PI12** Mover, girar, espelhar; desfazer/refazer e o diário reproduzem o mesmo
      IFC; excluir e desfazer restaura os `GlobalId`s.
- [ ] **PI13** IFC de outra origem (pilar sem `BrasBim_Pilar`): corpo preservado; mover
      funciona.
- [ ] **PI14** Arquivo passa na validação de esquema do IfcOpenShell.

## 10. Fontes públicas
Mesmo repositório, ramo e data de `laje.md` §10 (`S`, `M` e `P` idem).

| Código | Documento |
|---|---|
| IFC-COL | `S/Entities/IfcColumn.md` |
| IFC-COLTYPE | `S/Entities/IfcColumnType.md` |
| IFC-COLENUM | `S/Types/IfcColumnTypeEnum.md` |
| IFC-MPS | `M/Entities/IfcMaterialProfileSet.md` |
| IFC-MP | `M/Entities/IfcMaterialProfile.md` |
| IFC-MPSU | `M/Entities/IfcMaterialProfileSetUsage.md` |
| IFC-CARD | `M/Types/IfcCardinalPointReference.md` |
| IFC-PSET-C | `S/PropertySets/Pset_ColumnCommon.md` e `P/Pset_ColumnCommon.xml` |
| IFC-QTO-C | `S/QuantitySets/Qto_ColumnBaseQuantities.md` e `P/Qto_ColumnBaseQuantities.xml` |

Outras:
- **CG**: conhecimento geral (seções usuais de pilares de concreto em obras brasileiras,
  numeração P1, P2…, convenção de planta com o pilar por cima da alvenaria).

Nenhum material de `_restrito/` nem de `tools/` foi usado.

## 11. Fora do escopo / pendências
- **Próximo refinamento:** recortes por prioridade no 3D e nos volumes (pilar corta
  parede, viga e laje); etiqueta própria de pilares.
- V1: perfis metálicos e de madeira (`IfcIShapeProfileDef` etc.); pilar inclinado;
  `PILASTER`; seção variável; numeração automática por posição (da esquerda para a
  direita, de cima para baixo); pilar em vários pavimentos de uma vez.
- Pontos de revisão: (a) nomes P1, P2… automáticos (§3.1); (b) recorte da parede só na
  planta no básico (§6); (c) barra de espaço gira 90° na criação (§4); (d) biblioteca
  (§3.4).
- **(e) Correção na implementação (2026‑10‑16), a confirmar pelo revisor:** a tabela de §3.1
  e o PI03 numeram os pontos como vistos de cima, mas [IFC-CARD] define a "esquerda" como
  o +x do perfil **olhando na direção da extrusão** (texto do `IfcCardinalPointReference`,
  conferido no mesmo repositório da §10 nesta data). Num pilar, que é extrudado para cima,
  visto de cima a esquerda do IFC fica à direita. A implementação mantém o comportamento
  da interface (o canto escolhido no quadradinho cai no ponto clicado; no PI03 a seção
  ocupa x ∈ [2; 2,2], y ∈ [3; 3,4]) e grava o número do IFC: canto inferior esquerdo da
  planta = `CardinalPoint` **3**, inferior direito = 1, superior esquerdo = 9, superior
  direito = 7, meio esquerdo = 6, meio direito = 4 (meio de cima, meio de baixo e centro
  não mudam). Na viga, a tabela de
  `viga.md` §2.4 já segue o [IFC-CARD].
