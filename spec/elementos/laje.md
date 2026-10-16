---
elemento: Laje
entidade_ifc: IfcSlab (PredefinedType via IfcSlabType)
requisito: RF-ELE-02
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-15
status: aprovado
revisor: OTTO (aprovado em 2026-10-15)
---

# Laje

Spec do **básico**: laje plana, de espessura constante, com contorno poligonal. Aberturas
(furos), inclinação e laje por contorno de paredes vêm num refinamento (§11).

## 1. Propósito
Elemento horizontal que forma o piso de um pavimento (ou o teto do de baixo) e o separa
do espaço de cima. Só a parte construtiva é laje; piso e forro são revestimentos
(`IfcCovering`, V1). [IFC-SLAB]

## 2. Mapeamento IFC

### 2.1 Entidade e tipo
- Ocorrência `IfcSlab`; tipo `IfcSlabType` via `IfcRelDefinesByType`. O `PredefinedType`
  fica no tipo e a ocorrência fica vazia. [IFC-SLAB, *CorrectPredefinedType*]
- `IfcSlabTypeEnum` no MVP: `FLOOR` (laje de piso, padrão) e `BASESLAB` (laje apoiada no
  solo, radier). `ROOF` só com a cobertura (RF-ELE-07); `LANDING` só com a escada.
  [IFC-SLABENUM]

### 2.2 Representações
- `Body`, `SweptSolid`: `IfcExtrudedAreaSolid` de um `IfcArbitraryClosedProfileDef`
  (`OuterCurve` = `IfcPolyline` fechada com o contorno), extrudado em +z
  perpendicularmente. [IFC-SLAB, *Body SweptSolid Geometry*]
- Posicionamento: `IfcLocalPlacement` relativo ao pavimento, origem no primeiro vértice
  do contorno, z = **face superior** (deslocamento do topo, §3.1). O sólido tem
  `Position` em z = −T (T = espessura total) e profundidade T, de modo que o topo fica em
  z = 0 do elemento. *(decisão do projeto)*
- Sem `Axis` nem `FootPrint` no MVP (a planta é calculada a partir do `Body`).

### 2.3 Material
- `IfcMaterialLayerSet` no tipo; `IfcMaterialLayerSetUsage` na ocorrência com
  `LayerSetDirection = AXIS3`, `DirectionSense = POSITIVE` e
  `OffsetFromReferenceLine = 0`. O plano de referência é o do perfil extrudado (a face
  inferior), então a camada 1 é a **de baixo** e as camadas crescem para cima.
  [IFC-SLAB, *Material Layer Set Usage*; IFC-MLSU]
- `TotalThickness` = `Depth` do sólido (extrusão perpendicular). [IFC-SLAB]
- A interface lista as camadas **de cima para baixo** (como se lê um corte); a ordem
  gravada é a inversa. *(decisão do projeto)*

### 2.4 Propriedades, quantidades e relações
- `Pset_SlabCommon` (§3.3), `Qto_SlabBaseQuantities` (§8) e o Pset próprio
  `BrasBim_Laje` com os vínculos (§3.1).
- `IfcRelContainedInSpatialStructure` com o pavimento. [IFC-SLAB, *Spatial Containment*]
- `IfcRelAssociatesMaterial` (usage na ocorrência, layer set no tipo).

## 3. Parâmetros

### 3.1 Ocorrência
| Parâmetro | Tipo | Unidade | Padrão | Regras |
|---|---|---|---|---|
| Contorno | lista de pontos 2D | m | — | ≥ 3 pontos; polígono simples (sem autointerseção); área > 0,0001 m²; pontos repetidos ou alinhados são removidos |
| Pavimento | ref. `IfcBuildingStorey` | — | pavimento ativo | — |
| Deslocamento do topo | real | m | 0,00 | Cota da face superior em relação ao pavimento |
| Espessura | real (do tipo) | m | — | Soma das camadas; só leitura na ocorrência |

O contorno é gravado no sentido anti‑horário (a ferramenta corrige o sentido).
`BrasBim_Laje` guarda `DeslocamentoTopo`; sem o Pset (IFC de outra origem), a laje é lida
pelo que o `Body` mostra e não é refeita. *(decisão do projeto)*

### 3.2 Tipo
| Parâmetro | Atributo IFC | Padrão *(CG)* | Regras |
|---|---|---|---|
| Nome | `IfcSlabType.Name` | — | Único entre tipos de laje |
| Função | `PredefinedType` | `FLOOR` | `FLOOR` \| `BASESLAB` |
| Camadas | `IfcMaterialLayerSet` | — | ≥ 1 camada; espessura > 0 |
| Representação na planta | Pset `BrasBim_RepresentacaoPlanta` | linha fina, sem fundo | Como na parede (spec/ui 05) |

### 3.3 `Pset_SlabCommon` (MVP) [IFC-PSET-S]
| Propriedade | Tipo IFC | Padrão | Observação |
|---|---|---|---|
| `Reference` | IfcIdentifier | nome do tipo | — |
| `Status` | `PEnum_ElementStatus` | `NEW` | — |
| `LoadBearing` | IfcBoolean | verdadeiro | — |
| `IsExternal` | IfcBoolean | falso | — |
| `FireRating`, `AcousticRating`, `ThermalTransmittance`, `Combustible`, `SurfaceSpreadOfFlame`, `Compartmentation` | conforme [IFC-PSET-S] | vazio | Só gravadas se preenchidas |
| `PitchAngle` | IfcPlaneAngleMeasure | — | Só com a laje inclinada (§11) |

### 3.4 Biblioteca inicial *(CG, a revisar)*
- Laje maciça 10 cm: concreto 10.
- Laje 12 cm com contrapiso: contrapiso 3 + concreto 10 + reboco 1,5 (lista de cima para
  baixo; espessura 14,5).
- Laje pré‑moldada 12 cm (vigota e lajota, como camada única "Laje pré‑moldada").
- Radier 15 cm (`BASESLAB`): concreto 15.

## 4. Criação
Dois modos *(CG)*:
- **Polígono:** clique em cada vértice e feche clicando no primeiro ponto, com
  duplo‑clique ou com Enter. Esc desfaz o último ponto; com menos de 3 pontos, cancela.
- **Retângulo:** dois cantos opostos (como o retângulo da parede).

Pré‑visualização do contorno com as medidas do lado atual. Tab abre o quadro de medidas
com comprimento e ângulo do lado (polígono) ou largura e altura (retângulo), como na
parede (spec/ui 07). Atração (snap) e ponto de referência como nas outras ferramentas
(spec/ui 09 §2.1). Transação: (`slab_type.create`, se faltar) → `slab.create`.

## 5. Edição

### 5.1 Interações
- Mover, copiar, girar, espelhar e excluir (como os outros elementos).
- Alças na planta: vértices (arrastar move o vértice) e meio dos lados (arrastar
  desloca o lado paralelamente). Lado com um ponto no meio vira dois lados: V1.
- Painel: tipo, deslocamento do topo, propriedades comuns.

### 5.2 Operações serializáveis
| `op` | Dados |
|---|---|
| `slab_type.create` / `.delete` | `name`, `predefined_type`, `layers[]` (`material`, `thickness`), `plan` |
| `slab_type.edit` | campos alterados (antes/depois) |
| `slab.create` / `.delete` | `guid`, `name`, `type`, `storey`, `outline[]`, `top_offset`, `common` |
| `slab.edit` | campos alterados (antes/depois): `outline`, `top_offset`, `type`, `common` |

Mover, girar e espelhar geram `slab.edit` do contorno. Desfazer restaura os mesmos
`GlobalId`s.

## 6. Comportamento e regras geométricas
- Corpo = contorno extrudado com a espessura do tipo, para baixo a partir do topo.
- Trocar o tipo muda a espessura e mantém a face superior.
- **Sem recortes com outros elementos no básico:** a laje e a parede ou a viga que se
  encontram com ela podem se sobrepor no 3D. Em consequência, os volumes dos dois
  elementos contam a parte comum duas vezes. Os recortes por prioridade ficam para V1
  (§11). **Ponto de revisão.**
- Excluir a laje não afeta outros elementos.

## 7. Representação 2D
Convenção geral *(CG)*; conferência com a NBR 6492 pendente.

| Situação na planta do pavimento | Desenho |
|---|---|
| Laje do próprio pavimento (abaixo do plano de corte) | Contorno em linha fina de projeção; fundo do tipo, se houver (padrão: sem fundo) |
| Laje cortada pelo plano (topo acima do plano e fundo abaixo; ex.: laje rebaixada) | Contorno grosso de corte e fundo do tipo |
| Laje inteira acima do plano | Contorno tracejado, com "Elementos acima do plano de corte" |

- A laje fica **sob** as paredes, pilares e vigas no desenho (desenhada primeiro).
- A laje do pavimento de cima não aparece na planta do pavimento de baixo (V1, com a
  opção de mostrar o contorno da laje de cima).

## 8. Quantitativos
`Qto_SlabBaseQuantities`, recalculado a cada alteração. [IFC-QTO-S]

| Quantidade | Cálculo |
|---|---|
| `Width` | espessura total (a quantidade tem esse nome no IFC) |
| `Perimeter` | perímetro do contorno |
| `GrossArea` = `NetArea` | área do contorno (sem aberturas no básico) |
| `GrossVolume` = `NetVolume` | área × espessura |
| `Length`, `Depth` | só para contorno retangular: lado maior e lado menor |

## 9. Critérios de aceite (testes)
- [x] **LA01** Retângulo 5 × 4 m no Térreo, tipo "Laje maciça 10 cm": `IfcSlab` com
      `IfcSlabType` `FLOOR`; `Body` `SweptSolid` com `IfcArbitraryClosedProfileDef`;
      topo em z = 0 e fundo em z = −0,10 (coordenadas do pavimento).
- [x] **LA02** `IfcMaterialLayerSetUsage` `AXIS3`, `POSITIVE`, deslocamento 0;
      `TotalThickness` = `Depth` = 0,10.
- [x] **LA03** Polígono em L com 6 vértices desenhado em sentido horário: contorno
      gravado anti‑horário; área e perímetro corretos.
- [x] **LA04** Polígono com autointerseção ou área nula: `slab.create` recusado,
      modelo intacto.
- [x] **LA05** Deslocamento do topo −0,05: topo em z = −0,05; `BrasBim_Laje`
      gravado; reabrir o arquivo reproduz a laje.
- [x] **LA06** Trocar para o tipo de 14,5 cm: topo mantido, fundo em −0,145; camadas na
      ordem contrapiso (em cima) … reboco (embaixo).
- [x] **LA07** `Qto_SlabBaseQuantities` do retângulo: `Width` 0,10, `Perimeter` 18,
      `GrossArea` 20, `GrossVolume` 2, `Length` 5, `Depth` 4.
- [x] **LA08** `Pset_SlabCommon`: `Reference`, `Status = NEW`, `LoadBearing = TRUE`.
- [x] **LA09** Mover, girar e espelhar: `slab.edit`; desfazer/refazer e reaplicar o
      diário reproduzem o mesmo IFC.
- [x] **LA10** Excluir e desfazer: mesmos `GlobalId`s, sem entidades órfãs.
- [x] **LA11** IFC de outra origem (laje sem `BrasBim_Laje`, com `Body` próprio): corpo
      preservado; mover funciona.
- [x] **LA12** Arquivo passa na validação de esquema do IfcOpenShell.

## 10. Fontes públicas
IFC 4.3 lido no repositório oficial da buildingSMART, ramo `ifc4.3-main`, consultado em
2026‑10‑15. Base: `https://github.com/buildingSMART/IFC4.x-development/blob/ifc4.3-main/`
(`S` = `docs/schemas/shared/IfcSharedBldgElements`, `M` =
`docs/schemas/resource/IfcMaterialResource`, `P` = `reference_schemas/psd`).

| Código | Documento |
|---|---|
| IFC-SLAB | `S/Entities/IfcSlab.md` |
| IFC-SLABTYPE | `S/Entities/IfcSlabType.md` |
| IFC-SLABENUM | `S/Types/IfcSlabTypeEnum.md` |
| IFC-MLSU | `M/Entities/IfcMaterialLayerSetUsage.md` |
| IFC-PSET-S | `S/PropertySets/Pset_SlabCommon.md` e `P/Pset_SlabCommon.xml` |
| IFC-QTO-S | `S/QuantitySets/Qto_SlabBaseQuantities.md` e `P/Qto_SlabBaseQuantities.xml` |

Outras:
- **NBR6492**: como na parede; **texto não lido**.
- **CG**: conhecimento geral (tipos de laje usuais no Brasil e espessuras, convenção de
  desenho da laje em planta).

Nenhum material de `_restrito/` nem de `tools/` foi usado.

## 11. Fora do escopo / pendências
- **Próximo refinamento:** aberturas na laje (`IfcOpeningElement` + `IfcRelVoidsElement`,
  RF-ELE-02); laje pelo contorno de paredes (clique dentro de um recinto fechado);
  recortes por prioridade com parede, viga e pilar; inserir vértice num lado.
- V1: laje inclinada (`PitchAngle`, extrusão não perpendicular); laje de cobertura
  (`ROOF`, com a cobertura); contorno da laje de cima na planta; revestimentos de piso e
  forro (`IfcCovering`); rebaixo.
- Pontos de revisão: (a) a laje pertence ao pavimento de que é o piso, com o topo na cota
  do pavimento (§2.2); (b) sobreposição com paredes e vigas aceita no básico (§6);
  (c) lista de camadas de cima para baixo na interface (§2.3); (d) biblioteca (§3.4).
