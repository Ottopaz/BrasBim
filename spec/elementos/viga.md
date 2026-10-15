---
elemento: Viga
entidade_ifc: IfcBeam (PredefinedType via IfcBeamType)
requisito: RF-ELE-04
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-15
status: em revisão
revisor: OTTO
---

# Viga

Spec do **básico**: viga reta, horizontal, de seção retangular, com o topo ligado a um
pavimento. Viga curva, perfis metálicos e apoio calculado em pilares vêm depois (§11).

## 1. Propósito
Elemento horizontal (ou quase) que vence um vão entre apoios e trabalha principalmente
à flexão. Pode também ser só arquitetônico. [IFC-BEAM]

## 2. Mapeamento IFC

### 2.1 Entidade e tipo
- Ocorrência `IfcBeam`; tipo `IfcBeamType` via `IfcRelDefinesByType`. O
  `PredefinedType` fica no tipo. [IFC-BEAM, *CorrectPredefinedType*]
- `IfcBeamTypeEnum` no MVP: `BEAM`. `LINTEL` (verga) fica para V1, com as aberturas.
  [IFC-BEAMENUM]

### 2.2 Material e perfil
Como no pilar (`pilar.md` §2.2): `IfcMaterialProfileSet` no tipo com um
`IfcMaterialProfile` (`IfcRectangleProfileDef`, `XDim` = largura b, `YDim` = altura h,
`Position` vazio) e `IfcMaterialProfileSetUsage` na ocorrência. [IFC-BEAM, *Material
Profile Set Usage*; IFC-MPSU]

### 2.3 Representações e posicionamento
- `IfcLocalPlacement` relativo ao pavimento, origem no ponto inicial do eixo na cota do
  **topo** da viga; eixo z local = direção da viga (do início ao fim, horizontal); eixo
  y local = para cima; eixo x local = horizontal, à **esquerda** de quem anda do início
  para o fim. [IFC-BEAM, *Axis 3D Geometry*: o eixo fica sobre o z do elemento]
- `Axis` (`Curve3D`): `IfcPolyline` de (0,0,0) a (0,0,L).
- `Body` (`SweptSolid`): `IfcExtrudedAreaSolid` do perfil do tipo, extrudado em +z,
  profundidade L, perpendicular ao perfil, com o y do perfil para cima (rotação 0°).
  O `Position` desloca o perfil de acordo com o `CardinalPoint`. [IFC-BEAM, *Body
  SweptSolid Geometry*]

### 2.4 Linha de referência → `CardinalPoint`
O topo da viga fica sempre na cota de referência; a linha desenhada pode ser uma face ou
o eixo, como na parede. Olhando na direção da extrusão, a "esquerda" do perfil é o +x do
perfil [IFC-CARD, *Figure 2*], que coincide com a esquerda de quem anda ao longo da viga.

| Linha de referência | `CardinalPoint` |
|---|---|
| face esquerda | 7 (topo, esquerda) |
| eixo | 8 (topo, centro) |
| face direita | 9 (topo, direita) |

### 2.5 Propriedades, quantidades e relações
- `Pset_BeamCommon` (§3.3), `Qto_BeamBaseQuantities` (§8) e o Pset próprio `BrasBim_Viga`
  com os vínculos (§3.1).
- `IfcRelContainedInSpatialStructure` com o pavimento em que foi desenhada.
- Ligação viga–pilar (`IfcRelConnectsElements`) e análise estrutural: V1.

## 3. Parâmetros

### 3.1 Ocorrência
| Parâmetro | Tipo | Unidade | Padrão | Regras |
|---|---|---|---|---|
| Ponto inicial / final | ponto 2D | m | — | Comprimento > 0,01 m |
| Linha de referência | `eixo` \| `face esquerda` \| `face direita` | — | `eixo` | §2.4 |
| Pavimento | ref. `IfcBuildingStorey` | — | pavimento ativo | — |
| Topo | `ligado a pavimento` \| `cota fixa` | — | `ligado a pavimento` | — |
| Pavimento do topo / deslocamento | ref., real | —, m | o de cima, 0,00 | Como na parede |
| Cota fixa do topo | real | m | 2,80 | Em relação ao pavimento da viga |
| Nome | texto | — | V1, V2… | Próximo número livre. Editável |

Com o padrão, a viga desenhada no Térreo fica com o topo no nível do Superior, sob a
laje dele, e as paredes do Térreo chegam até o mesmo nível. `BrasBim_Viga` guarda os
vínculos e a linha de referência. *(decisão do projeto)*

### 3.2 Tipo
| Parâmetro | Atributo IFC | Padrão *(CG)* | Regras |
|---|---|---|---|
| Nome | `IfcBeamType.Name` | — | Único entre tipos de viga |
| b × h | `XDim`, `YDim` | 0,14 × 0,40 | > 0,01 m |
| Material | `IfcMaterialProfile.Material` | Concreto | — |
| Representação na planta | `BrasBim_RepresentacaoPlanta` | sem fundo | — |

### 3.3 `Pset_BeamCommon` (MVP) [IFC-PSET-B]
| Propriedade | Tipo IFC | Padrão | Observação |
|---|---|---|---|
| `Reference` | IfcIdentifier | nome do tipo | — |
| `Status` | `PEnum_ElementStatus` | `NEW` | — |
| `LoadBearing` | IfcBoolean | verdadeiro | — |
| `IsExternal` | IfcBoolean | falso | — |
| `FireRating`, `ThermalTransmittance` | conforme [IFC-PSET-B] | vazio | Só gravadas se preenchidas |
| `Span`, `Slope`, `Roll` | — | não gravadas | `Span` (vão entre apoios) em V1, com a ligação aos pilares |

### 3.4 Biblioteca inicial *(CG, a revisar)*
Concreto 12 × 30, 14 × 40, 15 × 40, 20 × 50. Nome do tipo = "Viga b×h" em centímetros.

## 4. Criação
Como a parede reta: clique no início e no fim; a ferramenta continua a partir do último
ponto (cadeia) até Esc ou duplo‑clique. Tab abre o quadro com comprimento e ângulo.
Pontos de atração incluem o centro e os cantos dos pilares e as faces e pontas das
paredes. Barra Opções: tipo, linha de referência e topo. Transação:
(`beam_type.create`, se faltar) → `beam.create`.

## 5. Edição

### 5.1 Interações
- Mover, copiar, girar, espelhar (troca face esquerda ↔ direita para manter o lado),
  excluir.
- Alças na planta: as pontas (arrastar estica ou encurta) e o meio (move).
- Painel: tipo, linha de referência, topo, comprimento e ângulo, nome, propriedades
  comuns.

### 5.2 Operações serializáveis
| `op` | Dados |
|---|---|
| `beam_type.create` / `.delete` | `name`, `predefined_type`, `section` (`b`, `h`), `material`, `plan` |
| `beam_type.edit` | campos alterados (antes/depois) |
| `beam.create` / `.delete` | `guid`, `name`, `type`, `storey`, `start`, `end`, `ref_line`, `top` (`storey`, `offset` \| `elevation`), `common` |
| `beam.edit` | campos alterados (antes/depois) |

## 6. Comportamento e regras geométricas
- Corpo: seção do tipo varrida ao longo do eixo, com o topo na cota de referência.
- Mudar a cota do pavimento do topo recalcula a viga.
- **Sem recortes no básico:** a viga pode se sobrepor ao pilar, à parede e à laje no 3D
  e nos volumes; cortes nas pontas (viga que termina na face do pilar) e prioridades
  ficam para o próximo refinamento. **Ponto de revisão.**
- Excluir a viga não afeta outros elementos.

## 7. Representação 2D
| Situação na planta | Desenho |
|---|---|
| Inteira acima do plano de corte (caso comum) | Duas linhas tracejadas (as faces); **sempre** visível, mesmo com "Elementos acima do plano de corte" desligado |
| Cortada pelo plano | Seção cortada com fundo do material e contorno grosso |
| Inteira abaixo do plano | Linhas finas de projeção |

A convenção de mostrar as vigas tracejadas sob a laje é usual nas plantas de arquitetura
*(CG)*. Onde a viga passa sobre uma parede, as linhas tracejadas continuam visíveis.
**Etiqueta** opcional: "V1 14×40" ao longo da viga *(CG)*.

## 8. Quantitativos
`Qto_BeamBaseQuantities`, recalculado a cada alteração. [IFC-QTO-B]

| Quantidade | Cálculo |
|---|---|
| `Length` | comprimento do eixo |
| `CrossSectionArea` | b × h |
| `OuterSurfaceArea` | perímetro da seção × comprimento (sem as pontas) |
| `GrossVolume` = `NetVolume` | b × h × comprimento (sem recortes no básico) |

## 9. Critérios de aceite (testes)
- [ ] **VI01** Viga 14×40 de (0, 0) a (5, 0) no Térreo, topo no Superior (2,80), eixo:
      `IfcBeam` + `IfcBeamType` `BEAM`; `Axis` de comprimento 5; o corpo ocupa
      x ∈ [0; 5], y ∈ [−0,07; 0,07], z ∈ [2,40; 2,80].
- [ ] **VI02** `IfcMaterialProfileSetUsage` com `CardinalPoint = 8`; o perfil do `Body`
      é a mesma entidade do `IfcMaterialProfile` do tipo.
- [ ] **VI03** Linha de referência face esquerda: `CardinalPoint = 7` e o corpo ocupa
      y ∈ [−0,14; 0] (a viga fica à direita da linha, que é sua face esquerda).
- [ ] **VI04** Viga a 30° de (1, 1): corpo e `Axis` girados; comprimento mantido.
- [ ] **VI05** Topo em cota fixa 2,60: z do topo = 2,60; mudar a cota do Superior não a
      altera.
- [ ] **VI06** Mudar a cota do Superior para 3,00: a viga ligada sobe para 3,00.
- [ ] **VI07** `Qto_BeamBaseQuantities` da VI01: `Length` 5, `CrossSectionArea` 0,056,
      `OuterSurfaceArea` 5,4, `GrossVolume` 0,28.
- [ ] **VI08** `Pset_BeamCommon` (`Reference`, `Status = NEW`, `LoadBearing = TRUE`);
      `BrasBim_Viga` gravado; reabrir reproduz a viga.
- [ ] **VI09** Nomes automáticos V1, V2…
- [ ] **VI10** Planta do Térreo com o plano de corte a 1,50: a viga aparece com duas
      linhas tracejadas, também com "Elementos acima do plano de corte" desligado.
- [ ] **VI11** Esticar a ponta, mover, girar e espelhar: `beam.edit`; desfazer/refazer
      e o diário reproduzem o mesmo IFC; excluir e desfazer restaura os `GlobalId`s.
- [ ] **VI12** IFC de outra origem (viga sem `BrasBim_Viga`): corpo preservado; mover
      funciona.
- [ ] **VI13** Arquivo passa na validação de esquema do IfcOpenShell.

## 10. Fontes públicas
Mesmo repositório, ramo e data de `laje.md` §10 (`S`, `M` e `P` idem).

| Código | Documento |
|---|---|
| IFC-BEAM | `S/Entities/IfcBeam.md` |
| IFC-BEAMTYPE | `S/Entities/IfcBeamType.md` |
| IFC-BEAMENUM | `S/Types/IfcBeamTypeEnum.md` |
| IFC-MPSU | `M/Entities/IfcMaterialProfileSetUsage.md` |
| IFC-CARD | `M/Types/IfcCardinalPointReference.md` |
| IFC-PSET-B | `S/PropertySets/Pset_BeamCommon.md` e `P/Pset_BeamCommon.xml` |
| IFC-QTO-B | `S/QuantitySets/Qto_BeamBaseQuantities.md` e `P/Qto_BeamBaseQuantities.xml` |

Outras:
- **CG**: conhecimento geral (seções usuais de vigas de concreto, numeração V1, V2…,
  vigas tracejadas na planta de arquitetura).

Nenhum material de `_restrito/` nem de `tools/` foi usado.

## 11. Fora do escopo / pendências
- **Próximo refinamento:** viga termina na face do pilar e recortes por prioridade com
  laje e parede; etiqueta de vigas.
- V1: viga curva; viga inclinada; perfis metálicos e de madeira; `LINTEL` (verga sobre
  porta e janela); `Span` e ligação aos pilares (`IfcRelConnectsElements`); análise
  estrutural (`IfcStructuralCurveMember`).
- Pontos de revisão: (a) a viga pertence ao pavimento em que é desenhada, com o topo no
  pavimento de cima (§3.1); (b) vigas sempre visíveis, tracejadas, na planta (§7);
  (c) sobreposições aceitas no básico (§6); (d) nomes V1, V2…; (e) biblioteca (§3.4).
