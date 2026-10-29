# Registro de fontes consultadas

Índice das fontes **efetivamente lidas** para escrever specs e código do BrasBim
(`PROCESSO.md` §4). As categorias permitidas e proibidas estão em `FONTES.md`; o acesso
ao material restrito, em `REGISTRO-DE-ACESSO.md`.

- **Parte A**: fontes citadas em cada spec (a seção "Fontes" de cada documento é a
  referência; aqui ela é reunida para consulta e auditoria).
- **Parte B**: pesquisa ampla de 2026‑10‑21 sobre Archicad, Revit e AutoCAD (758 fontes
  públicas), cuja lista completa está no Anexo A de
  `reports/Pesquisa Archicad Revit AutoCAD.md`, com as notas brutas em
  `research_notes/Pesquisa Archicad Revit AutoCAD/`.

**Como acrescentar**: cada spec nova ou revisada mantém a sua seção "Fontes" (URL, data
de acesso, o que foi usado) e o autor regenera este arquivo com
`scripts/registro_fontes.py` no mesmo commit. Fonte que só apareceu em trecho de
resultado de busca é marcada "conferir" e não sustenta sozinha uma decisão de spec.

Gerado a partir do repositório; não edite à mão as partes A e B.

## Parte A: fontes citadas nas specs

### `spec/01-modelo-de-dados.md`
*Modelo de dados — operações serializáveis*; data 2026-10-14; situação rascunho (aguarda revisão).

Seção acrescentada em 2026‑10‑23, sem leitura nova: lista os documentos em que este
rascunho se apoia. O formato das operações e da transação é decisão do projeto; os
campos de cada operação vêm das specs citadas na coluna "Situação" do §4, cada uma
com as suas fontes.

IFC 4.3 no repositório oficial da buildingSMART, ramo `ifc4.3-main`. Base:
`https://github.com/buildingSMART/IFC4.x-development/blob/ifc4.3-main/`
(`K` = `docs/schemas/core/IfcKernel`, `U` = `docs/schemas/resource/IfcUtilityResource`,
`M` = `docs/schemas/resource/IfcMaterialResource`, `S` =
`docs/schemas/shared/IfcSharedBldgElements`).

| Código | Documento | Uso |
|---|---|---|
| IFC-GUID | `U/Types/IfcGloballyUniqueId.md` | `id` das operações (§1) e GlobalIds derivados (§3) |
| IFC-ROOT | `K/Entities/IfcRoot.md` | todo objeto identificado tem GlobalId |
| IFC-RCPE | `S/Entities/IfcRelConnectsPathElements.md` | junções (§4) |
| IFC-MLSU | `M/Entities/IfcMaterialLayerSetUsage.md` | efeito derivado (§3) |

Outras:
- **RFC 9562** (UUID, que substitui a RFC 4122), `https://www.rfc-editor.org/rfc/rfc9562`:
  UUID versão 5 por nome (SHA‑1) para os GlobalIds derivados (§3).
- **RFC 8259** (JSON), `https://www.rfc-editor.org/rfc/rfc8259`: formato das operações e
  do diário.
- **IfcOpenShell** (LGPL‑3.0), `ifcopenshell.guid.compress`: conversão do UUID para os
  22 caracteres do GlobalId.
- **CG**: conhecimento geral de engenharia de software (operações invertíveis, desfazer
  e refazer por inversa, transação tudo ou nada, diário reaplicável).

Nenhum material de `_restrito/` nem de `tools/` foi usado.

Endereços citados (3): https://github.com/buildingSMART/IFC4.x-development/blob/ifc4.3-main/; https://www.rfc-editor.org/rfc/rfc8259; https://www.rfc-editor.org/rfc/rfc9562

### `spec/elementos/cobertura.md`
*Cobertura*; data 2026-10-16; situação aprovado.

IFC 4.3 lido no repositório oficial da buildingSMART, ramo `ifc4.3-main`, consultado em
2026-10-16. Base: `https://github.com/buildingSMART/IFC4.x-development/blob/ifc4.3-main/`
(`S` = `docs/schemas/shared/IfcSharedBldgElements`, `P` = `reference_schemas/psd`).

| Código | Documento |
|---|---|
| IFC-ROOF | `S/Entities/IfcRoof.md` |
| IFC-ROOFTYPE | `S/Entities/IfcRoofType.md` |
| IFC-ROOFENUM | `S/Types/IfcRoofTypeEnum.md` |
| IFC-PSET-R | `S/PropertySets/Pset_RoofCommon.md` e `P/Pset_RoofCommon.xml` |
| IFC-QTO-R | `S/QuantitySets/Qto_RoofBaseQuantities.md` |
| IFC-SLAB, IFC-SLABENUM, IFC-PSET-S | como na laje (laje.md §10) |

Outras:
- **NBR6492**: representação da cobertura em planta; **texto não lido**, a conferir.
- **CG**: conhecimento geral sobre telhados no Brasil: inclinação em %, beirais usuais
  e inclinações usuais por tipo de telha, que variam com o fabricante.

Nenhum material de `_restrito/` nem de `tools/` foi usado.

Endereços citados (1): https://github.com/buildingSMART/IFC4.x-development/blob/ifc4.3-main/

### `spec/elementos/escada-terreno.md`
*Escada, guarda-corpo e terreno*; data 2026-10-20; situação em revisão (implementado para teste, fluxo do MVP).

IFC 4.3 (buildingSMART): `IfcStair`/`IfcStairTypeEnum` [IFC-STAIR], `IfcStairFlight`
[IFC-FLIGHT], `IfcRailing`/`IfcRailingTypeEnum` [IFC-RAIL], `IfcGeographicElement`
`TERRAIN`, `IfcTriangulatedFaceSet` [IFC-GEO]. Fórmula de Blondel (2e + p = 63 a 64 cm),
NBR 9077 e NBR 9050 (escadas, guarda-corpo): texto não lido, a conferir. CG:
triangulação de Delaunay (Bowyer–Watson) e curvas de nível por interpolação nas arestas.

Nenhum material de `_restrito/` nem de `tools/` foi usado.

### `spec/elementos/janela.md`
*Janela*; data 2026-10-14; situação aprovado.

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

### `spec/elementos/laje.md`
*Laje*; data 2026-10-15; situação aprovado.

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

Endereços citados (1): https://github.com/buildingSMART/IFC4.x-development/blob/ifc4.3-main/

### `spec/elementos/objeto-parametrico.md`
*Objeto paramétrico (definição, tipos e ocorrências) e biblioteca de objetos*; data 2026-10-20; situação aprovado (implementado).

IFC 4.3 lido no repositório oficial da buildingSMART, ramo `ifc4.3-main`, consultado em
2026-10-20. Base: `https://github.com/buildingSMART/IFC4.x-development/blob/ifc4.3-main/docs/schemas/`
(`K` = `core/IfcKernel`, `PE` = `core/IfcProductExtension`, `F` =
`shared/IfcSharedFacilitiesElements`, `PL` = `domain/IfcPlumbingFireProtectionDomain`,
`EL` = `domain/IfcElectricalDomain`; Psets também em
`reference_schemas/psd/*.xml`).

| Código | Documento |
|---|---|
| IFC-TYPEOBJ | `K/Entities/IfcTypeObject.md`: propriedades do tipo compartilhadas, regra "a propriedade da ocorrência prevalece", `HasAssociations` |
| IFC-TYPEPROD | `K/Entities/IfcTypeProduct.md`: `RepresentationMaps` usadas pelas ocorrências por `IfcMappedItem` |
| IFC-LIB | `K/Entities/IfcProjectLibrary.md` e `IfcRelDeclares` |
| IFC-AGG | `K/Entities/IfcRelAggregates.md` (tipos ou ocorrências como todo e partes) e `IfcRelNests.md` |
| IFC-FURN | `F/Entities/IfcFurniture.md`, `F/Types/IfcFurnitureTypeEnum.md` (constituintes Finish, Frame, Hardware, Padding, Panel) |
| IFC-PSET-F | `F/PropertySets/Pset_FurnitureTypeCommon.md` e `psd/Pset_FurnitureTypeCommon.xml` (`IsBuiltIn`, nominais) |
| IFC-SAN | `PL/Types/IfcSanitaryTerminalTypeEnum.md`, `PL/PropertySets/Pset_SanitaryTerminalTypeCommon.md`, `PL/QuantitySets/Qto_SanitaryTerminalBaseQuantities.md` |
| IFC-PSET-S | `psd/Pset_SanitaryTerminalTypeCommon.xml` |
| IFC-ELE | `EL/Types/IfcElectricApplianceTypeEnum.md`, `EL/PropertySets/Pset_ElectricApplianceTypeCommon.md`, `EL/QuantitySets/Qto_ElectricApplianceBaseQuantities.md` |
| IFC-GEO | `PE/Entities/IfcGeographicElement.md`, `PE/Types/IfcGeographicElementTypeEnum.md` (`VEGETATION`), `PE/PropertySets/Pset_VegetationCommon.md` |
| IFC-OPEN | `PE/Entities/IfcOpeningElement.md` (vão em qualquer elemento, `IfcRelVoidsElement`) |

Outras:
- **IfcOpenShell** (LGPL): `ifcopenshell.api.type.assign_type` (docstring: tipo com
  representação obriga as ocorrências a usá-la; `should_map_representations`),
  `ifcopenshell.api.pset`, `ifcopenshell.api.aggregate`, conforme o código e a
  documentação públicos.
- **Ajuda pública do Autodesk Revit** (help.autodesk.com), lida só para entender a
  função esperada, sem copiar texto, nome de comando nem layout de diálogo:
  *Creating Family Parameters* (parâmetro de tipo × de ocorrência), *Family Types*
  (valores e fórmulas por tipo), *Use Visibility Parameters in Families* (vídeo:
  visibilidade por sim/não e fórmula), *Associate Family Parameters* (ligar parâmetros
  de um objeto aninhado aos do objeto de fora) e *Workflow: Creating Loadable Families*.
  O que veio daí são só as ideias da §1. O vocabulário (definição, tipo, ocorrência,
  peça, aninhado, preso à parede), a linguagem de fórmulas, o editor por formulário e
  a biblioteca em IFC são do BrasBim.
- **NBR 9050** (altura da bacia acessível) e **NBR 6492** (desenho de mobiliário em
  planta): **texto não lido**, a conferir.
- **CG:** medidas usuais de colchões, móveis e eletrodomésticos no Brasil (variam com o
  fabricante); linguagem de fórmulas no estilo das planilhas em português (vírgula
  decimal, `;` entre argumentos).

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando, layout de diálogo ou objeto de biblioteca de outro software foi copiado.

Endereços citados (1): https://github.com/buildingSMART/IFC4.x-development/blob/ifc4.3-main/docs/schemas/

### `spec/elementos/parede.md`
*Parede*; data 2026-10-14; situação aprovado.

Documentação IFC 4.3 lida no repositório oficial da buildingSMART (o site
`ifc43-docs.standards.buildingsmart.org` bloqueia acesso automatizado), ramo `ifc4.3-main`,
consultado em 2026‑10‑14. Base: `https://github.com/buildingSMART/IFC4.x-development/blob/ifc4.3-main/`

| Código | Documento |
|---|---|
| IFC-WALL | `docs/schemas/shared/IfcSharedBldgElements/Entities/IfcWall.md` |
| IFC-EAS | `docs/schemas/resource/IfcGeometricModelResource/Entities/IfcExtrudedAreaSolid.md` (consultado em 2026‑10‑15) |
| IFC-WALLENUM | `docs/schemas/shared/IfcSharedBldgElements/Types/IfcWallTypeEnum.md` |
| IFC-RCPE | `docs/schemas/shared/IfcSharedBldgElements/Entities/IfcRelConnectsPathElements.md` |
| IFC-CTE | `docs/schemas/shared/IfcSharedBldgElements/Types/IfcConnectionTypeEnum.md` |
| IFC-MLSU | `docs/schemas/resource/IfcMaterialResource/Entities/IfcMaterialLayerSetUsage.md` (+ `Types/IfcDirectionSenseEnum.md`, `Types/IfcLayerSetDirectionEnum.md`) |
| IFC-ML | `docs/schemas/resource/IfcMaterialResource/Entities/IfcMaterialLayer.md` |
| IFC-OPEN | `docs/schemas/core/IfcProductExtension/Entities/IfcOpeningElement.md` |
| IFC-OPENENUM | `docs/schemas/core/IfcProductExtension/Types/IfcOpeningElementTypeEnum.md` |
| IFC-RVE | `docs/schemas/core/IfcProductExtension/Entities/IfcRelVoidsElement.md` |
| IFC-RFE | `docs/schemas/core/IfcProductExtension/Entities/IfcRelFillsElement.md` |
| IFC-PSET | `docs/schemas/shared/IfcSharedBldgElements/PropertySets/Pset_WallCommon.md` e `reference_schemas/psd/Pset_WallCommon.xml` |
| IFC-QTO | `docs/schemas/shared/IfcSharedBldgElements/QuantitySets/Qto_WallBaseQuantities.md` e `reference_schemas/psd/Qto_WallBaseQuantities.xml` |

Outras:
- **IOS** — IfcOpenShell 0.9 (https://docs.ifcopenshell.org/): existência das funções
  `geometry.add_wall_representation`, `geometry.connect_path`, `feature.add_feature`,
  `feature.add_filling`, `material.add_material_set` (para a implementação).
- **NBR6492** — ABNT NBR 6492:2021, citada só por título/escopo (ver REQUISITOS §15).
  **Texto não lido**; §7 é CG até a revisão.
- **CG** — conhecimento geral de arquitetura e BIM (composições, recortes de junção,
  plano de corte de 1,50 m, níveis de detalhe).

Nenhum material de `_restrito/` nem de `tools/` foi usado.

Endereços citados (2): https://docs.ifcopenshell.org/; https://github.com/buildingSMART/IFC4.x-development/blob/ifc4.3-main/

### `spec/elementos/pilar.md`
*Pilar*; data 2026-10-15; situação aprovado.

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

### `spec/elementos/porta.md`
*Porta*; data 2026-10-14; situação aprovado.

IFC 4.3 lido no repositório oficial da buildingSMART, ramo `ifc4.3-main`, consultado em
2026‑10‑14. Base: `https://github.com/buildingSMART/IFC4.x-development/blob/ifc4.3-main/`
(`S` = `docs/schemas/shared/IfcSharedBldgElements`,
`A` = `docs/schemas/domain/IfcArchitectureDomain`).

| Código | Documento |
|---|---|
| IFC-DOOR | `S/Entities/IfcDoor.md` |
| IFC-DOORTYPE | `S/Entities/IfcDoorType.md` |
| IFC-DOORENUM | `S/Types/IfcDoorTypeEnum.md` |
| IFC-DOOROP | `S/Types/IfcDoorTypeOperationEnum.md` |
| IFC-DLP | `A/Entities/IfcDoorLiningProperties.md` |
| IFC-DPP | `A/Entities/IfcDoorPanelProperties.md` (+ `A/Types/IfcDoorPanelOperationEnum.md`, `A/Types/IfcDoorPanelPositionEnum.md`) |
| IFC-PSET-D | `S/PropertySets/Pset_DoorCommon.md` e `reference_schemas/psd/Pset_DoorCommon.xml` |
| IFC-QTO-D | `S/QuantitySets/Qto_DoorBaseQuantities.md` e `reference_schemas/psd/Qto_DoorBaseQuantities.xml` |
| IFC-RFE | `docs/schemas/core/IfcProductExtension/Entities/IfcRelFillsElement.md` |

Outras:
- **IOS** — IfcOpenShell 0.9: existência de `geometry.add_door_representation` e
  `feature.add_filling` (candidatas para a implementação).
- **IOS-PSET** — modelos de Pset `IFC4X3` do IfcOpenShell 0.9
  (`ifcopenshell.util.pset`): `Pset_DoorLiningProperties` e `Pset_DoorPanelProperties`,
  "novos no IFC 4.3.2.0 para substituir" as entidades.
- **NBR9050** — citada só pelo valor de vão livre de fontes secundárias; **texto não
  lido**.
- **NBR6492** — como na spec da parede; **texto não lido**.
- **CG** — conhecimento geral (tipos de porta usuais no Brasil, dimensões, símbolos em
  planta, etiquetas).

Nenhum material de `_restrito/` nem de `tools/` foi usado.

Endereços citados (1): https://github.com/buildingSMART/IFC4.x-development/blob/ifc4.3-main/

### `spec/elementos/viga.md`
*Viga*; data 2026-10-15; situação aprovado.

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

### `spec/README.md`
*README*; data —; situação —.

Este índice não especifica comportamento; cada spec tem a sua seção "Fontes", reunida em
`../cleanroom/REGISTRO-DE-FONTES.md`. A lista do MVP é decisão do projeto, com base em:
- **IFC 4.3** (buildingSMART, `https://github.com/buildingSMART/IFC4.x-development`):
  classes dos elementos do MVP (`IfcWall`, `IfcSlab`, `IfcColumn`, `IfcBeam`, `IfcRoof`,
  `IfcDoor`, `IfcWindow`, `IfcSpace`, `IfcBuildingStorey`).
- **CG**: conhecimento geral do projeto de arquitetura no Brasil (o que um projeto
  residencial precisa entregar).

Nenhum material de `_restrito/` nem de `tools/` foi usado.

Endereços citados (1): https://github.com/buildingSMART/IFC4.x-development

### `spec/REQUISITOS.md`
*Requisitos funcionais (levantamento a partir de fontes públicas)*; data 2026-10-14; situação rascunho.

| Código | Fonte | O que foi verificado |
|---|---|---|
| **IFC** | buildingSMART, IFC 4.3 (ISO 16739‑1). Documentação: https://ifc43-docs.standards.buildingsmart.org/ (bloqueia acesso automatizado). Fonte lida: https://github.com/buildingSMART/IFC4.x-development (ramo `ifc4.3-main`, `docs/schemas/**/Entities/*.md`, `PropertySets`, `QuantitySets`, `PropertyEnumerations`) | Existência e definição de todas as entidades citadas; `Pset_WallCommon.Status` com `PEnum_ElementStatus` (NEW, EXISTING, DEMOLISH, TEMPORARY); `Qto_SpaceBaseQuantities`; `IfcRoof` como agregação de partes; `IfcDoor`/`IfcWindow` hospedados em aberturas |
| **BCF** | buildingSMART BCF: https://github.com/buildingSMART/BCF-XML | Página pública acessível |
| **IDS** | buildingSMART IDS: https://github.com/buildingSMART/IDS | Página pública acessível |
| **BSDD** | buildingSMART Data Dictionary: https://www.buildingsmart.org/users/services/buildingsmart-data-dictionary/ | Não acessível por ferramenta (HTTP 403); citado pela documentação do IfcOpenShell |
| **IOS** | IfcOpenShell: https://docs.ifcopenshell.org/ e https://github.com/IfcOpenShell/IfcOpenShell | Ferramentas IfcDiff, IfcTester, BCF, IfcCSV, IfcClash, bSDD; esquemas IFC2X3, IFC4 e IFC4X3; licença LGPL‑3.0 |
| **BON** | Bonsai: https://docs.bonsaibim.org/ e código em `src/bonsai` do repositório IfcOpenShell | Autoria IFC nativa sobre Blender; licença GPL‑3.0‑or‑later (cabeçalho do código) |
| **NBR6492** | ABNT NBR 6492:2021, *Documentação técnica para projetos arquitetônicos e urbanísticos — Requisitos*. Título e escopo via questões de concurso e catálogos | Título oficial (edição de 2021); etapas de projeto com implantação, plantas, cortes e elevações. Texto não lido |
| **NBR16752** | ABNT NBR 16752:2020, *Desenho técnico — Requisitos para apresentação em folhas de desenho*: https://www.normas.com.br/visualizar/abnt-nbr-nm/11569/ | Escopo (formatos, legenda, dobramento, escalas); formatos A0–A4. Texto não lido |
| **NBR16861** | ABNT NBR 16861:2020, linhas e escrita em desenho técnico (substitui NBR 8403), segundo material didático da UFRN: https://www.vetorial.design.ufrn.br/src/pdfs/Normas.pdf | **A confirmar no catálogo da ABNT** |
| **NBR9050** | ABNT NBR 9050 (acessibilidade). Rampas até 8,33% (1:12) com limites de desnível por segmento, segundo fontes secundárias | Edição vigente e valores a confirmar no texto oficial |
| **NBR15965** | ABNT NBR 15965 (série), *Sistema de classificação da informação da construção*. Partes 1, 2, 3 e 7 confirmadas em catálogos (normas.com.br, Target) | Número atual de partes a confirmar |
| **SINAPI** | CAIXA, SINAPI: https://www.caixa.gov.br/sinapi | Referência oficial, gratuita, atualizada mensalmente por UF (fontes secundárias; site da Caixa não acessível por ferramenta) |
| **AC-COL** | Graphisoft Help, visão geral da reserva em trabalho colaborativo: https://help.graphisoft.com/AC/25/INT/_AC25_Help/080_Collaboration/080_Collaboration-26.htm | Funcionalidade: reservar antes de alterar; elementos novos sem reserva; pedido a quem reservou; exige projeto atualizado |
| **REV-COL** | Autodesk Revit Help, empréstimo de elementos: https://help.autodesk.com/cloudhelp/2025/ENU/Revit-Collaborate/files/GUID-27E3B22D-79D3-44F5-A630-6E5F614585B4.htm | Funcionalidade: tornar elemento editável; pedido de edição ao detentor; liberação ao sincronizar |
| **REV-SHEETS** | Autodesk Revit Help, visão geral de pranchas (2014): https://help.autodesk.com/cloudhelp/2014/ENU/Revit/files/GUID-6D569C3B-B473-4AA9-BB2F-B93088D7D9A9.htm | Funcionalidade: prancha com várias vistas e tabelas |
| **CG** | Conhecimento geral de arquitetura, construção e BIM | Sem fonte específica nesta etapa |

> Observação de vocabulário: "reserva" é usada aqui como palavra comum do português,
> não como nome de comando. Ao nomear o recurso na interface, escolher termo próprio
> e revisar com o `revisor-cleanroom`.

Endereços citados (14): https://docs.bonsaibim.org/; https://docs.ifcopenshell.org/; https://github.com/IfcOpenShell/IfcOpenShell; https://github.com/buildingSMART/BCF-XML; https://github.com/buildingSMART/IDS; https://github.com/buildingSMART/IFC4.x-development; https://help.autodesk.com/cloudhelp/2014/ENU/Revit/files/GUID-6D569C3B-B473-4AA9-BB2F-B93088D7D9A9.htm; https://help.autodesk.com/cloudhelp/2025/ENU/Revit-Collaborate/files/GUID-27E3B22D-79D3-44F5-A630-6E5F614585B4.htm; https://help.graphisoft.com/AC/25/INT/_AC25_Help/080_Collaboration/080_Collaboration-26.htm; https://ifc43-docs.standards.buildingsmart.org/; https://www.buildingsmart.org/users/services/buildingsmart-data-dictionary/; https://www.caixa.gov.br/sinapi; https://www.normas.com.br/visualizar/abnt-nbr-nm/11569/; https://www.vetorial.design.ufrn.br/src/pdfs/Normas.pdf

### `spec/ui/01-janela-e-ferramentas.md`
*Interface — janela principal e primeiras ferramentas (versão 0.1 testável)*; data 2026-10-14; situação aprovado.

- **RF** — `spec/REQUISITOS.md` (RF-UI, RF-NUC, RF-DES, RF-PRJ).
- **PAREDE**, **PORTA** — `spec/elementos/parede.md` §4–§7 e `porta.md` §4–§7 (interações e
  desenho 2D já aprovados).
- **QT** — documentação pública do Qt for Python 6 (`https://doc.qt.io/qtforpython-6/`):
  `QMainWindow`, `QDockWidget`, `QOpenGLWidget`, `QPainter`, modo `offscreen`.
- **PYOPENGL** — `https://pyopengl.sourceforge.net/` (licença).
- **IOS** — `ifcopenshell.geom` para a triangulação do 3D.
- **CG** — conhecimento geral de aplicativos de desktop e de CAD (menus, painéis,
  navegação com roda e botão do meio, grade, *snap*, tecla Esc).

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

Endereços citados (2): https://doc.qt.io/qtforpython-6/; https://pyopengl.sourceforge.net/

### `spec/ui/02-edicao.md`
*Interface — edição de elementos, pavimentos e tipos (versão 0.2)*; data 2026-10-14; situação aprovado.

- **RF** — `spec/REQUISITOS.md` (RF-NUC-04, RF-NUC-05, RF-UI-02, RF-PRJ-04, RF-TIP-01/02).
- **PAREDE**, **PORTA** — `spec/elementos/parede.md` §5–§6 e `porta.md` §2–§6 (aprovadas).
- **UI01** — `spec/ui/01-janela-e-ferramentas.md` (aprovada).
- **IFC** — buildingSMART IFC 4.3: `IfcWallTypeEnum`, `IfcMaterialLayer` (`Category`,
  `Priority`), `IfcBuildingStorey`.
- **QT** — documentação pública do Qt for Python 6: `QTableWidget`, `QDialog`, eventos de
  mouse.
- **CG** — conhecimento geral de aplicativos de CAD: seleção por janela e por cruzamento
  conforme o sentido do arrasto, alças nas extremidades e no meio, mover/copiar/girar por
  ponto de base.

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

### `spec/ui/03-barras-e-icones.md`
*Interface — barras móveis, ícones, barra de opções, mini-barra da seleção e representação da parede na planta (versão 0.3 da interface)*; data 2026-10-14; situação aprovado.

- **RF** — `spec/REQUISITOS.md` (RF-UI-01..03, RF-TIP-03, RF-DOC-02).
- **UI01**, **UI02** — specs 0.1 e 0.2 (aprovadas).
- **IFC** — buildingSMART IFC 4.3: `IfcPropertySet`, `IfcWallType`, `IfcFillAreaStyle`,
  `IfcFillAreaStyleHatching`, `IfcCurveStyle` (alternativa de §6.2).
- **NBR8403** — ABNT NBR 8403, série de espessuras de linha (0,13 a 2,0 mm).
- **QT** — documentação pública do Qt for Python 6: `QToolBar` (áreas permitidas,
  barras soltas), `QMainWindow.saveState`, `QIcon`, `QSvgRenderer`.
- **CG** — conhecimento geral de aplicativos de desktop: barras encaixáveis, dicas ao
  passar o mouse, barra de opções da ferramenta ativa, ações junto à seleção.

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

### `spec/ui/04-painel-de-propriedades.md`
*Interface — painel de propriedades deitado (em blocos lado a lado)*; data 2026-10-14; situação aprovado.

- **RF** — `spec/REQUISITOS.md` (RF-UI-02).
- **UI01–UI03** — specs 0.1 §7, 0.2 §9 e 0.3 §4.3 (aprovadas).
- **QT** — documentação pública do Qt for Python 6: `QDockWidget.dockLocationChanged`,
  `QGridLayout`, `QScrollArea`.
- **CG** — conhecimento geral de aplicativos de desktop: painéis que se reorganizam
  conforme a borda em que estão encaixados.

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

### `spec/ui/05-acabamento-parede-porta.md`
*Interface — acabamento de parede e porta (espelhar, medidas no painel, alças e etiqueta da porta, propriedades comuns, junções manuais)*; data 2026-10-14; situação aprovado.

- **PAREDE**, **PORTA** — `spec/elementos/parede.md` §3.3, §5.1, §6.2 e `porta.md` §2.2,
  §3.3, §5.1, §7 (aprovadas).
- **UI02**, **UI03** — specs de interface 0.2 e 03 (aprovadas).
- **IFC** — buildingSMART IFC 4.3: `Pset_WallCommon`, `Pset_DoorCommon`,
  `IfcRelConnectsPathElements`.
- **CG** — conhecimento geral de aplicativos de CAD: espelhar por eixo de dois pontos,
  estender até o cruzamento, etiquetas de esquadria.

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

### `spec/ui/06-planta-por-camadas.md`
*Interface — planta por nível de detalhe, estilos de material e cor por camada no 3D*; data 2026-10-14; situação aprovado.

Documentação IFC 4.3 no repositório oficial da buildingSMART, ramo `ifc4.3-main`,
consultada em 2026‑10‑14. Base:
`https://github.com/buildingSMART/IFC4.x-development/blob/ifc4.3-main/`

| Código | Documento |
|---|---|
| IFC-MDR | `docs/schemas/resource/IfcRepresentationResource/Entities/IfcMaterialDefinitionRepresentation.md` (estilos por contexto, só `IfcStyledRepresentation`) |
| IFC-FAS | `docs/schemas/resource/IfcPresentationAppearanceResource/Entities/IfcFillAreaStyle.md` (sólido, uma ou duas hachuras, no máximo uma cor; `ModelOrDraughting`) |
| IFC-FASH | `docs/schemas/resource/IfcPresentationAppearanceResource/Entities/IfcFillAreaStyleHatching.md` (aparência, espaçamento, ângulo; duas instâncias para cruzado) |
| IFC-ML | `docs/schemas/resource/IfcMaterialResource/Entities/IfcMaterialLayer.md` (`Priority`) |

Outras:
- **PAREDE** — `spec/elementos/parede.md` §2.3, §6.2, §7 (aprovada).
- **UI03**, **UI05** — specs de interface 03 §6 e 05 §1, §7.1 (aprovadas).
- **IOS** — IfcOpenShell 0.9: módulo `ifcopenshell.api.style` (`add_style`,
  `add_surface_style`, `assign_material_style`) e `ifcopenshell.geom` (para a
  implementação).
- **NBR8403** — série de espessuras de linha, como na spec 03. **NBR6492** citada só por
  título; texto não lido.
- **CG** — conhecimento geral de desenho arquitetônico: detalhe por escala, prioridade de
  camadas em junções, convenções de hachura por material, elementos acima do plano em
  tracejado.

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

Endereços citados (1): https://github.com/buildingSMART/IFC4.x-development/blob/ifc4.3-main/

### `spec/ui/07-medidas-e-edicao-no-3d.md`
*Interface — campos de medida ao desenhar (Tab), seleção e edição na vista 3D, mostrar a seleção na outra vista*; data 2026-10-15; situação aprovado.

- **QT** — documentação pública do Qt for Python 6: `QOpenGLWidget`, `QMenu`,
  `QWidget.event` (tecla Tab), `QLineEdit`.
- **MT97** — T. Möller e B. Trumbore, "Fast, Minimum Storage Ray/Triangle Intersection",
  *Journal of Graphics Tools* 2(1), 1997 (algoritmo de interseção raio–triângulo,
  publicado).
- **UI01**, **UI02**, **UI03**, **UI05** — specs de interface 01 §5.5, 02, 03 §5 e 05 §3
  (aprovadas).
- **CG** — conhecimento geral de aplicativos de CAD e modelagem: entrada numérica junto
  ao cursor com troca de campo pelo teclado, escolha de objetos por raio, menu de contexto
  para localizar o objeto em outra vista.

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

### `spec/ui/08-parede-no-3d-topo-e-inclinacao.md`
*Interface e núcleo — alças da parede no 3D, topo inclinado e empena, parede tombada; ponta de parede unida move só a parede*; data 2026-10-15; situação aprovado.

Documentação IFC 4.3 no repositório oficial da buildingSMART, ramo `ifc4.3-main`,
consultada em 2026‑10‑15. Base:
`https://github.com/buildingSMART/IFC4.x-development/blob/ifc4.3-main/`

| Código | Documento |
|---|---|
| IFC-WALL | `docs/schemas/shared/IfcSharedBldgElements/Entities/IfcWall.md` (parede com camadas: espessura constante, extrusão vertical, `LayerSetDirection = AXIS2`; parede sem camadas: extrusão fora do eixo z permitida; `Body Clipping Geometry` com `IfcBooleanClippingResult` e semiespaços, figuras do recorte por `IfcPolygonalBoundedHalfSpace` e `IfcHalfSpaceSolid`) |
| IFC-PBHS | `docs/schemas/resource/IfcGeometricModelResource/Entities/IfcPolygonalBoundedHalfSpace.md` (contorno 2D fechado no plano xy da posição, extrudado ao longo de z; limita o semiespaço nas diferenças booleanas) |
| IFC-EAS | `docs/schemas/resource/IfcGeometricModelResource/Entities/IfcExtrudedAreaSolid.md` (`ExtrudedDirection`: qualquer direção não perpendicular ao z da posição) |
| IFC-MLSU | `docs/schemas/resource/IfcMaterialResource/Entities/IfcMaterialLayerSetUsage.md` |

Outras:
- **PAREDE** — `spec/elementos/parede.md` §1, §2, §11 (aprovada).
- **UI02**, **UI05**, **UI07** — specs de interface 02 §4, 05 §3 e 07 §3 (aprovadas).
- **CG** — conhecimento geral de modelagem de edifícios: oitão/empena sob telhado,
  parede inclinada, alças de altura em vistas 3D.

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

Endereços citados (1): https://github.com/buildingSMART/IFC4.x-development/blob/ifc4.3-main/

### `spec/ui/09-janela.md`
*Interface — janela (ferramenta, opções, tipos, planta, 3D, painel, alças) e ponto de referência nas ferramentas de criação*; data 2026-10-15; situação aprovado.

- **JANELA**, **PORTA** — `spec/elementos/janela.md` e `porta.md` (aprovadas).
- **UI01–UI08** — specs de interface aprovadas, nas seções citadas.
- **IFC** — buildingSMART IFC 4.3: `IfcWindow`, `IfcWindowType`,
  `IfcWindowLiningProperties`, `IfcWindowPanelProperties`, `Pset_WindowCommon`,
  `Qto_WindowBaseQuantities`, `IfcStyledItem`, `IfcSurfaceStyle` (mesmas fontes de
  `janela.md` §10 e spec 06).
- **CG** — conhecimento geral de desenho arquitetônico brasileiro (símbolos de janela em
  planta, etiqueta com peitoril) e de aplicativos de CAD (alças nas bordas, desenho do tipo
  ao editar).

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

### `spec/ui/10-laje-pilar-viga.md`
*Interface — laje, pilar e viga (ferramentas, opções, tipos, painel, alças, planta e 3D), versão básica*; data 2026-10-15; situação aprovado.

- **LAJE**, **PILAR**, **VIGA**: `spec/elementos/laje.md`, `pilar.md`, `viga.md` (em
  revisão, com as fontes IFC de cada uma).
- **UI01–UI09**: specs de interface aprovadas, nas seções citadas.
- **CG**: conhecimento geral de desenho arquitetônico brasileiro (pilar preenchido por
  cima da alvenaria, vigas tracejadas, contorno de laje) e de aplicativos de CAD
  (polígono fechado no primeiro ponto, giro de 90° com a barra de espaço, ponto de
  inserção num quadradinho de 9 pontos).

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

### `spec/ui/11-aparencia.md`
*Interface — aparência (tema, cores, fonte, espaçamento, planta e 3D)*; data 2026-10-15; situação em revisão.

- **Archivo**: `github.com/google/fonts/tree/main/ofl/archivo` (arquivo da fonte e
  `OFL.txt`), licença SIL OFL 1.1, compatível com a distribuição junto ao aplicativo GPL.
- **CG**: conhecimento geral de desenho de interfaces (contraste, hierarquia
  tipográfica, uma cor de destaque) e do ofício de desenho técnico (folha, grafite,
  grade).

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhuma cor, ícone ou layout
de outro software foi copiado.

### `spec/ui/12-estrutura-refinamento.md`
*Estrutura, refinamento 1 — recortes por prioridade, aberturas na laje, laje pelo contorno das paredes, etiquetas de pilar e viga*; data 2026-10-16; situação aprovado.

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

### `spec/ui/13-documentacao-planta.md`
*Documentação 1 — anotação da planta (ambientes, cotas, cota de nível, textos, linhas, hachuras, norte, escala, espessuras)*; data 2026-10-16; situação aprovado.

IFC 4.3 no repositório oficial da buildingSMART, ramo `ifc4.3-main`, consultado em
2026‑10‑16, e o esquema EXPRESS `IFC4X3_ADD2` distribuído com o IfcOpenShell
(enumerações `IfcAnnotationTypeEnum`, `IfcSpaceTypeEnum`; atributos de `IfcAnnotation`,
`IfcSpace`, `IfcTextLiteral`).

| Código | Documento |
|---|---|
| IFC-ANNOT | `docs/schemas/core/IfcProductExtension/Entities/IfcAnnotation.md` (contenção no pavimento; `IfcGeometricCurveSet`, `IfcAnnotationFillArea`, `IfcTextLiteral`) |
| IFC-SPACE | `docs/schemas/core/IfcProductExtension/Entities/IfcSpace.md` (agregação ao pavimento; `Name` = número, `LongName` = nome; `FootPrint` e `Body`; `Qto_SpaceBaseQuantities`) |
| IFC-QTO-SPACE | `Qto_SpaceBaseQuantities` no modelo de propriedades do IFC 4.3 distribuído com o IfcOpenShell (`ifcopenshell.util.pset.get_template("IFC4X3")`): bruta inclui o que está dentro do espaço (pilares, paredes internas); líquida exclui |

Outras:
- **NBR 8403** (espessuras de linha) e **NBR 6492** (representação de projetos de
  arquitetura): como nas specs anteriores, **texto não lido**; os valores são
  conhecimento geral e ficam para conferência.
- **CG**: convenções usuais do desenho de arquitetura no Brasil (cotas em metros com duas
  casas, tique a 45°, etiqueta de ambiente com nome e área, símbolo de nível, escalas
  usuais).

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

### `spec/ui/14-cortes-e-fachadas.md`
*Documentação 2 — cortes e fachadas gerados do modelo*; data 2026-10-16; situação aprovado.

- IFC 4.3: `IfcAnnotation` (contenção na estrutura espacial, representação 2D), como em
  spec/ui 13 §11.
- **IfcOpenShell** (LGPL, `cleanroom/FONTES.md`): as malhas por elemento
  (`ifcopenshell.geom`), já usadas na vista 3D. O módulo de desenho dele não é usado
  *(decisão do projeto: o estilo das linhas e as hachuras dos materiais ficam com o
  BrasBim)*.
- **NBR 6492**: representação de cortes e fachadas, **texto não lido**; convenções de
  conhecimento geral, a conferir.
- **CG**: convenções usuais (linha de corte em traço e ponto com setas e letra, cotas de
  nível no corte, título com a escala, linha de piso).

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

### `spec/ui/15-pranchas-e-pdf.md`
*Documentação 3 — pranchas com carimbo e exportação em PDF*; data 2026-10-16; situação aprovado.

- IFC 4.3: `IfcAnnotation` e `IfcProject`, como em spec/ui 13 §11.
- **NBR 16752** (formatos, margens e legenda) e **NBR 13142** (dobramento): **texto não
  lido**; os valores acima são de conhecimento geral e ficam para conferência.
- **Qt** (`QPdfWriter`, licença LGPL do PySide6): geração do PDF.
- **CG**: carimbo no canto inferior direito, largura para dobra em A4, campos usuais
  (projeto, endereço, proprietário, responsável técnico, conteúdo, escala, data, folha).

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

### `spec/ui/16-assistente.md`
*Assistente — pedido em texto, desenhado por uma IA instalada no PC*; data 2026-10-16; situação em revisão (protótipo implementado para teste).

- Model Context Protocol, especificação aberta (modelcontextprotocol.io): mensagens
  `initialize`, `tools/list`, `tools/call`, transporte Streamable HTTP, recomendações de
  segurança (escutar em localhost, validar `Origin`).
- JSON-RPC 2.0 (jsonrpc.org/specification).
- Claude Code, ajuda da linha de comando (`claude --help`) e documentação pública:
  `-p`, `--output-format stream-json`, `--mcp-config`, `--strict-mcp-config`, `--tools`,
  `--allowedTools`.

### `spec/ui/17-tabelas.md`
*Quantitativos e tabelas (quadro de esquadrias, quadro de áreas, tabelas configuráveis)*; data 2026-10-16; situação aprovado.

- IFC 4.3 (`IfcElementQuantity` e os `Qto_*BaseQuantities` de cada elemento;
  `IfcAnnotation`; `IfcTable`, só para registrar por que não foi usado), no repositório
  oficial da buildingSMART, como nas specs dos elementos.
- **RFC 4180** (CSV) e **ECMA-376 / ISO/IEC 29500** (Office Open XML, SpreadsheetML),
  públicos: o mínimo para escrever o XLSX (pacote, planilha, estilos, cadeias
  compartilhadas).
- **NBR 12721** (áreas para incorporação) e normas municipais de quadro de áreas:
  **texto não lido**. O quadro de áreas daqui é de conhecimento geral (área útil por
  ambiente e área construída por pavimento).
- **CG**: quadro de esquadrias usual no Brasil (código, tipo, dimensões, peitoril,
  quantidade); CSV com `;` e vírgula decimal nas planilhas em português.

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

### `spec/ui/18-camadas.md`
*Camadas de organização (grupos, visibilidade, bloqueio e combinações)*; data 2026-10-20; situação aprovado (implementado).

- **IFC 4.3**: `IfcPresentationLayerAssignment` e `IfcPresentationLayerWithStyle`
  (atributos `Name`, `Identifier`, `AssignedItems` com pelo menos um item, `LayerOn`,
  `LayerFrozen`, `LayerBlocked`, `LayerStyles`) e `IfcLayeredItem`, no repositório
  oficial da buildingSMART (ifc43-docs.standards.buildingsmart.org).
- **IfcOpenShell** (LGPL): `ifcopenshell.api.layer` (`add_layer_with_style`,
  `assign_layer`, `unassign_layer`, `edit_layer`), conforme a documentação pública.
- **CG**: camadas para organizar desenho técnico existem nos programas de CAD e BIM em
  geral. O que vem daqui é só a função: ocultar, bloquear, agrupar e guardar estados com
  nome. Os nomes das camadas e dos grupos iniciais são próprios, em português.

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

### `spec/ui/19-desenho-2d.md`
*Desenho 2D (círculo, arco, curva livre, cota de raio e de ângulo, rótulo, marcador de alteração)*; data 2026-10-20; situação em revisão (implementado para teste, fluxo do MVP).

- **IFC 4.3**: `IfcAnnotation` (`PredefinedType` `DIMENSION`, `TEXT`, `SYMBOL`),
  `IfcGeometricCurveSet`, `IfcTextLiteralWithExtent` [IFC-ANNOT, como na spec/ui 13].
- **NBR 8403** (espessuras de linha) e **NBR 6492** (cotas e convenções): texto não lido,
  a conferir, como nas specs anteriores.
- **CG**: curva de Catmull-Rom (passa pelos pontos de controle); nuvem de revisão e
  rótulo com linha de chamada são convenções gerais de desenho técnico.

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

### `spec/ui/20-eixos-vaos-claraboia.md`
*Eixos de projeto, vão e nicho na parede, claraboia*; data 2026-10-20; situação em revisão (implementado para teste, fluxo do MVP).

IFC 4.3 (buildingSMART): `IfcGrid`, `IfcGridAxis` (`AxisTag`, `AxisCurve`) [IFC-GRID];
`IfcWindow`/`IfcWindowTypeEnum` `SKYLIGHT` [IFC-WINDOW]; `IfcOpeningElement`,
`IfcRelVoidsElement`, `IfcRelFillsElement` [IFC-OPEN]. NBR 6492 (eixos e claraboia em
planta): texto não lido, a conferir. CG: malha de eixos numerados × letrados.

Nenhum material de `_restrito/` nem de `tools/` foi usado.

### `spec/ui/21-salvamento-automatico.md`
*Salvamento automático e recuperação após falha*; data 2026-10-21; situação em revisão (implementado para teste, fluxo do MVP).

Conhecimento geral de software (CG): gravação atômica por troca de nome, arquivo de
sinal de vida. Nenhum material de `_restrito/` nem de `tools/` foi usado.

### `spec/ui/22-importar-desenho.md`
*Importar desenho DXF e DWG como referência*; data 2026-10-21; situação em revisão (implementado para teste, fluxo do MVP).

DXF Reference (Autodesk, documentação pública); ezdxf (MIT); IFC 4.3 `IfcAnnotation`,
`IfcIndexedPolyCurve`, `IfcCartesianPointList2D` [IFC-ANNOT]. Conversores externos
usados como programas à parte; código do ezdxf (MIT, aberto) lido para a regra do
deslocamento das cotas; GNU LibreDWG 0.14 (GPL‑3.0‑or‑later,
gnu.org/software/libredwg). Nenhum material de `_restrito/` nem de `tools/` foi usado.

### `spec/ui/23-precisao.md`
*Pacote de precisão (atração completa, teclado no traço, deslocar, aparar, concordar, semelhantes, giro rápido, paleta de comandos)*; data 2026-10-23; situação em revisão (fluxo do MVP: implementado na sequência).

Pesquisa do projeto: `reports/Pesquisa Archicad Revit AutoCAD.md` (seção "A velocidade
nasce de digitar sem foco") e notas `interface_e_interacao.md` §1–2, `autocad.md` §1,
`archicad_modelagem.md` §3. Ajuda pública lida para este pacote (trechos de busca,
**conferir** na página):
- Tipos de atração (extremidade, meio, centro, interseção, perpendicular, tangente,
  mais próximo): [Autodesk, Object Snap Tab (AutoCAD for Mac)](https://help.autodesk.com/cloudhelp/2018/ENU/AutoCAD-MAC-Core/files/GUID-A782462F-F85C-4496-85A5-3D9A54548489.htm);
  [AutoCAD Web Help, Object Snaps](https://help.autodesk.com/cloudhelp/ENU/AutoCAD-Web-Help/files/Drafting-and-Creating/AutoCAD_Web_Help_Drafting_and_Creating_Osnap_html.html).
  Formas por tipo de ponto: [Autodesk, About Snaps (Revit 2026)](https://help.autodesk.com/cloudhelp/2026/ENU/Revit-Customize/files/GUID-A3947840-1F30-41D7-AF75-B61687952A07.htm).
  Inferência por pontos, linhas e cores; setas travam o eixo: [SketchUp Help, Drawing basics](https://help.sketchup.com/en/sketchup/introducing-drawing-basics-and-concepts).
- Deslocar paralela (distância ou por ponto, concêntrico em círculos, repetir com a
  mesma distância): [Autodesk, OFFSET (AutoCAD LT 2021)](https://help.autodesk.com/cloudhelp/2021/ENU/AutoCAD-LT/files/GUID-C0E4246D-C420-42BD-A6FC-8B1852EFD005.htm);
  [About Offsetting Objects (2018)](https://help.autodesk.com/cloudhelp/2018/ENU/AutoCAD-Core/files/GUID-704C1ADE-A4AE-4A85-8822-454ACAC1345A.htm).
- Aparar/estender com todos os objetos como limite e Shift para inverter:
  [Autodesk, About Trimming and Extending Objects (LT 2026)](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-LT/files/GUID-725D3A7A-5E52-47F0-BA7A-7D15F9EF6D7F.htm).
- Concordar com raio 0 = canto vivo; Shift para raio 0 temporário:
  [Autodesk, FILLET (AutoCAD LT 2015)](https://help.autodesk.com/cloudhelp/2015/ENU/AutoCAD-LT/files/GUID-64F8B700-23B3-4BD6-8C03-66121AA13E8F.htm).
- Enter/espaço repetem o último comando: [Autodesk, AutoCAD 2026 Getting Started, Basics](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-GettingStarted/files/GUID-5B6347C1-B458-4336-AB2A-C16AF161B755.htm).
- Selecionar todas as instâncias do mesmo tipo e filtro só por categoria (criticado):
  [CAD Notes](https://www.cad-notes.com/how-to-selectively-select-objects-in-revit/);
  [Archistar Academy](https://academy.archistar.ai/using-filter-selection-to-find-objects-in-revit).
- Girar 90° por atalho: [Graphisoft, Quickly Rotate Elements (AC29)](https://help.graphisoft.com/AC/29/INT/_AC29_Help/005_NewFeatures/005_NewFeatures-6.htm).
- Busca aproximada de comandos: [McNeel, The Rhino window (Rhino 8)](https://docs.mcneel.com/rhino/8/help/en-us/user_interface/rhino_window.htm).

IFC 4.3: `IfcRelConnectsPathElements` (junções), `IfcTypeObject`, `PredefinedType`,
`IfcRelAssociatesMaterial`, `IfcPresentationLayerAssignment`. CG: Ctrl+K para paleta de
comandos e Ctrl+R para girar são convenções comuns de vários programas; marcadores,
nomes ("Deslocar paralela", "Aparar/estender", "Concordar", "Selecionar semelhantes") e
regras de clique são deste projeto. Nada de texto, ícone ou diálogo foi copiado.

Nenhum material de `_restrito/` nem de `tools/` foi usado.

Endereços citados (13): https://academy.archistar.ai/using-filter-selection-to-find-objects-in-revit; https://docs.mcneel.com/rhino/8/help/en-us/user_interface/rhino_window.htm; https://help.autodesk.com/cloudhelp/2015/ENU/AutoCAD-LT/files/GUID-64F8B700-23B3-4BD6-8C03-66121AA13E8F.htm; https://help.autodesk.com/cloudhelp/2018/ENU/AutoCAD-Core/files/GUID-704C1ADE-A4AE-4A85-8822-454ACAC1345A.htm; https://help.autodesk.com/cloudhelp/2018/ENU/AutoCAD-MAC-Core/files/GUID-A782462F-F85C-4496-85A5-3D9A54548489.htm; https://help.autodesk.com/cloudhelp/2021/ENU/AutoCAD-LT/files/GUID-C0E4246D-C420-42BD-A6FC-8B1852EFD005.htm; https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-GettingStarted/files/GUID-5B6347C1-B458-4336-AB2A-C16AF161B755.htm; https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-LT/files/GUID-725D3A7A-5E52-47F0-BA7A-7D15F9EF6D7F.htm; https://help.autodesk.com/cloudhelp/2026/ENU/Revit-Customize/files/GUID-A3947840-1F30-41D7-AF75-B61687952A07.htm; https://help.autodesk.com/cloudhelp/ENU/AutoCAD-Web-Help/files/Drafting-and-Creating/AutoCAD_Web_Help_Drafting_and_Creating_Osnap_html.html; https://help.graphisoft.com/AC/29/INT/_AC29_Help/005_NewFeatures/005_NewFeatures-6.htm; https://help.sketchup.com/en/sketchup/introducing-drawing-basics-and-concepts; https://www.cad-notes.com/how-to-selectively-select-objects-in-revit/

### `spec/ui/24-linha-de-comando.md`
*Linha de comando (barra fixa sob as vistas, apelidos, dica e opções da ferramenta, histórico, coordenadas)*; data 2026-10-23; situação em revisão (fluxo do MVP: implementado na sequência).

Pesquisa do projeto: `reports/Pesquisa Archicad Revit AutoCAD.md` (seção "A velocidade
nasce de digitar sem foco"); notas `interface_e_interacao.md` §1 (linha de comando do
Rhino 8, caixa de medidas do SketchUp) e `autocad.md` §1 (apelidos curtos, marcado "sem
fonte" lá; as fontes abaixo cobrem). Ajuda pública lida para este pacote (trechos de
busca, **conferir** na página):
- Teclado vai para a linha de comando sempre que a janela está ativa; autocompletar com
  busca aproximada; opções clicáveis; histórico: [McNeel, The Rhino window (Rhino 8)](https://docs.mcneel.com/rhino/8/help/en-us/user_interface/rhino_window.htm)
  (F374 no registro).
- Coordenadas absolutas e relativas digitadas: [SketchUp Help, Drawing basics](https://help.sketchup.com/en/sketchup/introducing-drawing-basics-and-concepts);
  relativa ao último ponto com `@`: [Autodesk, About Entering 2D Cartesian Coordinates (LT 2018)](https://help.autodesk.com/cloudhelp/2018/ENU/AutoCAD-LT/files/GUID-F64F8008-E1C0-49CC-A268-A6B8C6E9B566.htm).
- Apelidos de comando editáveis pelo usuário, só para iniciar o comando:
  [Autodesk, To Manage Command Aliases (2025)](https://help.autodesk.com/cloudhelp/2025/ENU/AutoCAD-Customization/files/GUID-D4CACED6-DFBA-43C3-BC42-8D980AB3AE75.htm);
  [Autodesk, Command Aliases, Shortcut Keys, and AutoCorrect (LT 2025)](https://help.autodesk.com/cloudhelp/2025/ENU/AutoCAD-LT-DidYouKnow/files/GUID-D2B4BF16-B1F7-4EF2-89AF-88ACE85FAD73.htm).
- Lista de sugestões enquanto se digita, ordenada por uso: [Autodesk, To Work With the Command Line Suggestion List (LT 2026)](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-LT/files/GUID-74478DCE-92D4-49B1-93E9-DCF09D57FA0D.htm);
  [Input Search Options Dialog Box (LT 2026)](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-LT/files/GUID-3179393F-958F-42EA-8A92-E9975A1D160B.htm).

O que veio das fontes é só a **função** (linha de comando com sugestões, apelidos
editáveis, coordenada relativa ao último ponto). A tabela de apelidos (§7), o separador
`;`, a ordem de leitura do §4, os textos e o desenho da barra são deste projeto; nenhum
apelido, nome de comando, texto ou arquivo de configuração de outro programa foi
copiado. O arquivo de apelidos de outros programas **não** foi aberto.

Nenhum material de `_restrito/` nem de `tools/` foi usado.

Endereços citados (7): https://docs.mcneel.com/rhino/8/help/en-us/user_interface/rhino_window.htm; https://help.autodesk.com/cloudhelp/2018/ENU/AutoCAD-LT/files/GUID-F64F8008-E1C0-49CC-A268-A6B8C6E9B566.htm; https://help.autodesk.com/cloudhelp/2025/ENU/AutoCAD-Customization/files/GUID-D4CACED6-DFBA-43C3-BC42-8D980AB3AE75.htm; https://help.autodesk.com/cloudhelp/2025/ENU/AutoCAD-LT-DidYouKnow/files/GUID-D2B4BF16-B1F7-4EF2-89AF-88ACE85FAD73.htm; https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-LT/files/GUID-3179393F-958F-42EA-8A92-E9975A1D160B.htm; https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-LT/files/GUID-74478DCE-92D4-49B1-93E9-DCF09D57FA0D.htm; https://help.sketchup.com/en/sketchup/introducing-drawing-basics-and-concepts

### `spec/ui/25-vistas-salvas.md`
*Vistas salvas (planta, corte e 3D) e como pô-las na prancha*; data 2026-10-26; situação em revisão (implementado para teste, fluxo do MVP).

- Pesquisa do projeto, `research_notes/.../archicad_documentacao_colaboracao.md` §1: no
  Archicad, vista salva guarda camadas, escala, filtros e sobreposições gráficas, e o
  desenho posto na folha é composto a partir dela ("modelo → vista salva → desenho na
  folha"); o mapa de vistas é uma árvore no navegador. Fonte citada lá:
  [Graphisoft Community, "Archicad Basic Concepts - The Navigator"](https://community.graphisoft.com/t5/Getting-started/Archicad-Basic-Concepts-The-Navigator/ta-p/303987)
  (trecho de busca; **conferir**).
- `revit_documentacao_colaboracao.md`: modelos de vista guardam propriedades aplicáveis
  em lote ([Autodesk Help 2024 – View Template Properties](https://help.autodesk.com/cloudhelp/2024/ENU/Revit-Customize/files/GUID-66D789A8-AB92-4AF0-B884-DF3A3302E117.htm)).
- Pedido do revisor (2026‑10‑26) e pendências do `CONTEXTO.md` (câmera salva; fluxo de
  pôr vista na prancha "não está bom ainda").
- Nenhum material de `_restrito/` nem de `tools/` foi usado. Nomes e quadros próprios.

Endereços citados (2): https://community.graphisoft.com/t5/Getting-started/Archicad-Basic-Concepts-The-Navigator/ta-p/303987; https://help.autodesk.com/cloudhelp/2024/ENU/Revit-Customize/files/GUID-66D789A8-AB92-4AF0-B884-DF3A3302E117.htm

### `spec/ui/26-folhas-mestras.md`
*Folhas mestras (tamanho, margens e carimbo desenhado pelo usuário)*; data 2026-10-26; situação em revisão (implementado para teste, fluxo do MVP).

- Pesquisa do projeto, `archicad_documentacao_colaboracao.md` §1: no Archicad, o *master
  layout* define o tamanho da folha; o que se desenha nele aparece em todos os layouts
  que o usam; o carimbo é desenhado com as ferramentas 2D e textos automáticos; cada
  layout escolhe o seu *master* — [Graphisoft Community, "Archicad Basic Concepts - The
  Navigator"](https://community.graphisoft.com/t5/Getting-started/Archicad-Basic-Concepts-The-Navigator/ta-p/303987)
  (trecho de busca; **conferir**).
- `normas_e_projeto_legal_brasil.md`: itens mínimos do carimbo segundo a NBR 6492
  (empresa, cliente, título, número, escala, local e data, autoria, responsável técnico,
  revisão) — [Gran Cursos – questões NBR 6492](https://questoes.grancursosonline.com.br/questoes-de-concursos/arquitetura-nbr-6492-representacao-de-projetos-de-arquitetura-429878)
  (trecho de busca; **conferir**). Carimbos por prefeitura: [PBH, Cartilha de
  Representação (2025)](https://prefeitura.pbh.gov.br/sites/default/files/estrutura-de-governo/politica-urbana/2025/cartilharepresentacaopbh_smpu_r5.pdf);
  [Curitiba – Manual do Autor](https://mid.curitiba.pr.gov.br/2020/00304554.pdf).
- `revit_documentacao_colaboracao.md`: carimbo como família própria com campos e
  sobrescrita do texto de escala em folhas com várias escalas.
- Pedido do revisor (2026‑10‑26). Formatos e margens da série A: spec/ui 15 §2 (CG).
- Nenhum material de `_restrito/` nem de `tools/` foi usado. Nomes dos campos próprios.

Endereços citados (4): https://community.graphisoft.com/t5/Getting-started/Archicad-Basic-Concepts-The-Navigator/ta-p/303987; https://mid.curitiba.pr.gov.br/2020/00304554.pdf; https://prefeitura.pbh.gov.br/sites/default/files/estrutura-de-governo/politica-urbana/2025/cartilharepresentacaopbh_smpu_r5.pdf; https://questoes.grancursosonline.com.br/questoes-de-concursos/arquitetura-nbr-6492-representacao-de-projetos-de-arquitetura-429878

### `spec/ui/27-tabela-de-penas.md`
*Tabela de penas (cores e espessuras do desenho)*; data 2026-10-26; situação em revisão (implementado para teste, fluxo do MVP).

- Pesquisa do projeto: `autocad.md` (estilos de plotagem CTB por cor e STB por nome;
  espessura por camada); `normas_e_projeto_legal_brasil.md` (espessuras de pena no plot,
  CTB/STB e conjuntos de penas no contexto ABNT: **sem fonte** nesta rodada);
  `archicad_documentacao_colaboracao.md` (conjuntos de penas existem, sem página oficial
  lida: **conferir**); `revit_documentacao_colaboracao.md` (estilos de objeto e
  espessuras: sem fonte primária).
- Série de espessuras da NBR 8403 já usada no BrasBim (spec/ui 13 §8); conferência com o
  texto da norma continua pendente.
- Pedido do revisor (2026‑10‑26).
- Nenhum material de `_restrito/` nem de `tools/` foi usado. Nomes das categorias próprios.

### `spec/ui/28-selecao.md`
*Seleção pelo cursor, como nos programas de CAD*; data 2026-10-26; situação em revisão (implementado para teste, fluxo do MVP).

- Pesquisa do projeto, `autocad.md` §1: seleção por janela (esquerda→direita, só o que
  está inteiro dentro) e por cruzamento (direita→esquerda, o que toca), além de cerca,
  laço e seleção rápida por propriedade (fonte citada lá). `interface_e_interacao.md`
  §2: comportamento janela/cruzamento em cada programa "sem fonte nesta rodada" —
  **conferir** na ajuda pública do AutoCAD (seleção por laço e PICKADD).
- Pedido e respostas do revisor (2026‑10‑26).
- Nenhum material de `_restrito/` nem de `tools/` foi usado. Cursor e cores próprios.

### `spec/ui/29-prancha-selecao-e-moldura.md`
*Seleção na prancha e na folha mestra; limite e moldura dos desenhos na prancha*; data 2026-10-26; situação em revisão (implementado para teste, fluxo do MVP).

- Pedido do revisor (2026‑10‑26).
- Seleção: spec/ui 28 e as fontes citadas lá (pesquisa do projeto, `autocad.md` §1).
- Limite e moldura — como os três resolvem (acesso em 2026‑10‑26, por resultado de busca:
  **conferir** na página inteira antes de citar como fato; sem copiar nomes de UI):
  - Archicad: o desenho na folha tem um contorno que só aparece na tela e se liga e
    desliga nas opções de exibição, separado de uma borda imprimível com pena e tipo de
    linha; o contorno pode acompanhar o desenho ou ser redimensionado à mão, recortando
    ([Graphisoft Community, bordas dos desenhos no layout](https://community.graphisoft.com/t5/Documentation/Border-lines-around-drawings-on-layout/m-p/212041/highlight/true);
    [moldura automática × manual](https://community.graphisoft.com/t5/Documentation/VIEW-EDGE-quot-AUTO-ADJUST-quot-OR-quot-MANUAL-quot-EXPLAIN/td-p/142401)).
    Queixa registrada lá: o usuário não controla a aparência do contorno de tela — aqui a
    moldura impressa tem pena e tipo de linha próprios.
  - Revit: a região de recorte da vista se mostra ou se oculta e se ajusta por alças
    ([Autodesk Help, Showing or Hiding Crop Regions](https://help.autodesk.com/cloudhelp/2023/ENU/Revit-DocumentPresent/files/GUID-47430A55-A8F0-4894-A636-14E0A29182D3.htm)).
  - AutoCAD: a borda da janela de papel não tem opção própria de ocultar; a prática é
    pô‑la numa camada que não imprime
    ([Autodesk Forums, ocultar a borda da viewport](https://forums.autodesk.com/t5/autocad-forum/viewport-border-showing-on-print/m-p/7979089);
    [Arkance, camada congelada e recorte](https://ukcommunity.arkance.world/hc/en-us/articles/21550812943762-AutoCAD-Tip-Freezing-Viewport-Layer-removes-clipping-boundary-from-viewport)).
    Aqui o limite de tela e a moldura impressa são coisas separadas desde o início.
- Nenhum material de `_restrito/` nem de `tools/` foi usado. Nomes, cursor e cores
  próprios.

Endereços citados (5): https://community.graphisoft.com/t5/Documentation/Border-lines-around-drawings-on-layout/m-p/212041/highlight/true; https://community.graphisoft.com/t5/Documentation/VIEW-EDGE-quot-AUTO-ADJUST-quot-OR-quot-MANUAL-quot-EXPLAIN/td-p/142401; https://forums.autodesk.com/t5/autocad-forum/viewport-border-showing-on-print/m-p/7979089; https://help.autodesk.com/cloudhelp/2023/ENU/Revit-DocumentPresent/files/GUID-47430A55-A8F0-4894-A636-14E0A29182D3.htm; https://ukcommunity.arkance.world/hc/en-us/articles/21550812943762-AutoCAD-Tip-Freezing-Viewport-Layer-removes-clipping-boundary-from-viewport

### `spec/ui/30-ajustes-curtos.md`
*Ajustes curtos do pente fino (bloco 1)*; data 2026-10-27; situação em revisão (§2–§9 implementados para teste).

| Código | Documento |
|---|---|
| RHINO-WIN | McNeel, *The Rhino window* (Rhino 8, docs.mcneel.com), citado em `research_notes/.../interface_e_interacao.md` |
| AC-TRACKER | Graphisoft, *Tracker* (Archicad 28, help.graphisoft.com), citado em `research_notes/.../archicad_modelagem.md` |

Conhecimento geral (CG): matriz/cópia em série, vistas ortogonais e isométricas. Nenhum
material de `_restrito/` nem de `tools/` foi usado; nomes, textos e layout são próprios.

### `spec/ui/31-projeto-legal.md`
*Projeto legal (projeto para licenciamentos)*; data 2026-10-27; situação em revisão (fluxo do MVP: implementar por etapas, §8; etapas 1–3 feitas, §12–§14).

| Código | Documento |
|---|---|
| ARARAS | Prefeitura de Araras, *POP 001/21 Alvará de Construção* (araras.sp.gov.br), via `research_notes/.../normas_e_projeto_legal_brasil.md` §3 |
| JACAREI | Prefeitura de Jacareí, *Anexo XII Manual Técnico* (jacarei.sp.gov.br), idem |
| SP-PECAS | Prefeitura de São Paulo, *Peças gráficas de projeto (LOE 16.642/17)* (prefeitura.sp.gov.br), idem |
| CURITIBA | Prefeitura de Curitiba, *Manual do Autor do Projeto*, 2ª ed., 2020 (mid.curitiba.pr.gov.br), idem |
| SIENGE-QA | Sienge, *Quadro de áreas* (blog), idem |
| IFSC-K22 | Repositório IFSC, Karkotli 2022, idem (trecho de busca) |
| USP-16636 | USP e‑Disciplinas, *Gestão do processo de projeto* (trecho de busca), idem §2 |
| IFC43 | Esquema IFC 4.3 do IfcOpenShell: enumeração do `Status` dos Psets comuns (conferido em 2026‑10‑26) |

Conhecimento geral (CG): TO, CA e taxa de permeabilidade como razões de áreas. Nada de
`_restrito/` nem de `tools/`; nomes, textos e layout são próprios. Os filtros de reforma
e as fases dos outros programas foram citados na pesquisa só como existência do recurso;
a solução aqui (situação + perfil) é própria.

### `spec/ui/32-navegacao-e-abas.md`
*Painel Projeto com ícones e abas que fecham*; data 2026-10-27; situação em revisão (fluxo do MVP: implementada junto, §6).

| Código | Documento |
|---|---|
| NAV-AC | Graphisoft Community, *Archicad Basic Concepts – The Navigator* (F184 da pesquisa; trecho de busca), via `research_notes/.../archicad_documentacao_colaboracao.md` |
| RVT-26 | BIMsmith, *Revit 2026* (F268), via `research_notes/.../revit_documentacao_colaboracao.md` §2 |
| RVT-27 | BIMpure, *Revit 2027* (F228), idem, "Folhas, carimbos e posicionamento" |
| NOTA-RVT | Inferência da pesquisa em `revit_documentacao_colaboracao.md` §2 (separar modelo de documentação) |
| RHINO | McNeel, *The Rhino window* (F374): botão direito na aba de vista abre comandos, via `interface_e_interacao.md` §3 |

Conhecimento geral (CG): abas fecháveis com ×, clique do meio e Ctrl+W são convenção de
interfaces com abas (navegadores, editores). Nada de `_restrito/` nem de `tools/`; nomes,
ícones e organização do painel são próprios.

### `spec/ui/33-projeto-compartilhado.md`
*Projeto compartilhado na rede local (reserva de elementos)*; data 2026-10-28; situação em revisão (fluxo do MVP: implementada junto, §9).

| Código | Documento | Uso |
|---|---|---|
| AC-COL | Graphisoft Help, visão geral da reserva (spec/REQUISITOS.md §13); nota `research_notes/.../archicad_documentacao_colaboracao.md` §3 (F203, F204 no relatório) | criar livre, editar exige reserva, autorreserva, pedido, estado ao vivo |
| REV-COL | Autodesk Revit Help, empréstimo de elementos (spec/REQUISITOS.md §13); nota `revit_documentacao_colaboracao.md` §3 | empréstimo automático do sem dono, pedido ao dono |
| RFC 8259 | JSON, https://www.rfc-editor.org/rfc/rfc8259 | formato das mensagens |

Endereços citados (1): https://www.rfc-editor.org/rfc/rfc8259

### `spec/ui/34-barra-de-ferramentas.md`
*Barra de ferramentas — ícones isométricos, grupos e ferramentas de vista e documentação*; data 2026-10-29; situação em revisão; §2 e §3 feitos, §4 especificado nas specs/ui 35 e 36.

Conhecimento geral (CG): projeção isométrica. Pedido e print do revisor
(`feedback/prints/barra de ferramentas.png`), usado só como descrição de função. Nada de
`_restrito/`.

### `spec/ui/35-elevacao-interna-detalhe-folha-camera.md`
*Vistas — elevação interna, detalhe, folha de trabalho e câmera*; data 2026-10-29; situação aprovada (pontos de revisão como propostos).

- Pesquisa complementar (2026‑10‑29):
  `research_notes/Pesquisa Archicad Revit AutoCAD/complemento_vistas_e_documentacao.md`
  §1 (elevação interna: Archicad AC27 050_ViewsVB‑48 a ‑55; Revit 2024 "About/Create
  Elevation Views"), §2 (detalhe: Archicad AC30 050_ViewsVB‑62 a ‑69; Revit LT 2023
  drafting/callout), §3 (folha de trabalho: Archicad AC28/AC30), §4 (câmera: Archicad AC29
  Camera Tool Settings; Revit 2024 perspective/camera).
- IFC 4.3: `IfcAnnotation`, `IfcRelAggregates`, `IfcRelContainedInSpatialStructure`
  [IFC-ANNOT].
- **NBR 6492**: símbolos de chamada de detalhe e de elevação. **Texto não lido.** Os
  marcadores seguem convenções usuais (CG) e serão conferidos quando a norma for lida.
- CG: escala usual 1:25 de elevação interna; círculo dividido "número / prancha".
- Nada de `_restrito/`. Os nomes das ferramentas são nossos ("Folha de trabalho" e
  "Elevação interna" são termos correntes em pt‑BR; "Detalhe" e "Câmera", palavras comuns).

### `spec/ui/36-polilinha-ponto-figura-desenho.md`
*Documentação — polilinha com arcos, ponto de apoio, figura e desenho*; data 2026-10-29; situação aprovada (pontos de revisão como propostos).

- Pesquisa complementar (2026‑10‑29):
  `research_notes/Pesquisa Archicad Revit AutoCAD/complemento_vistas_e_documentacao.md`
  §5 (polilinha: AutoCAD 2024 PLINE; Archicad AC28 polylines), §6 (ponto de apoio:
  Archicad hotspot; AutoCAD POINT/DIVIDE), §7 (figura: Archicad AC25 Figure; AutoCAD 2024
  IMAGEATTACH; Revit 2024 image), §8 (desenho: Archicad AC25 Drawing; Revit 2024 Add Views
  to a Sheet).
- IFC 4.3: `IfcIndexedPolyCurve`, `IfcArcIndex`, `IfcAnnotationTypeEnum.ASSUMEDPOINT`
  (conferido no esquema do IfcOpenShell instalado), `IfcBlobTexture`,
  `IfcIndexedTriangleTextureMap`, `IfcTriangulatedFaceSet` [IFC-ANNOT].
- Qt (LGPL): `QImage`, Qt PDF (`QPdfDocument`) para gerar a imagem da página. O Qt PDF
  vem no pacote à parte **`PySide6_Pdf`** (conferido no `.venv`), que a pasta do pendrive
  ainda não leva: entra em `scripts/pendrive/requisitos.txt` quando o §5.2 for feito. Sem
  ele, o Desenho aceita só imagem e avisa que falta o leitor de PDF.
- CG: arco de polilinha pela tangente de ¼ do ângulo (DXF); título de desenho com número
  em círculo e escala.
- Nada de `_restrito/`. Nenhum nome de comando de outro programa: "Polilinha", "Ponto de
  apoio", "Figura" e "Desenho" são palavras comuns em pt‑BR.

### `spec/ui/37-linhas-guia.md`
*Interação — linhas-guia a partir de pontos de referência e do ponto anterior*; data 2026-10-29; situação em revisão (pedido urgente do revisor: implementado na sequência).

- Pesquisa: `research_notes/Pesquisa Archicad Revit AutoCAD/interface_e_interacao.md` §1
  (Archicad: referências de atração ativadas ao passar o cursor, várias ao mesmo tempo,
  e guias temporárias em X/Y e a cada 45°; AutoCAD 2026: pontos adquiridos por pausa e
  caminhos de alinhamento horizontais, verticais e polares, com distância digitada sobre
  o caminho; SketchUp: pausa dá prioridade ao ponto) e `archicad_modelagem.md` (guias de
  atração AC28 temporárias, linhas-guia persistentes AC25) e `autocad.md` §1
  (rastreamento por snap e polar).
- CG: projeção de ponto em reta, interseção de retas.
- Nada de `_restrito/`. "Linhas-guia" e "ponto de referência" são termos comuns em pt‑BR.

### `spec/ui/38-area-de-selecao.md`
*Interação — área de seleção (esticar, 3D da área, exportar e imprimir a área)*; data 2026-10-29; situação em revisão (implementação por etapas: §3 núcleo feito; §2, §4, §5 a fazer).

- Ajuda pública Graphisoft (lida em 2026‑10‑29): Marquee Area (AC19,
  help.graphisoft.com/AC/19/INT/AC19Help/02_Interaction/02_Interaction-42.htm); Marquee
  Area Definition: Single Story or All Stories (AC18, …/AC18Help/02_Interaction/
  02_Interaction-47.htm); Show/View Marquee Area in 3D (AC18, …/02_Interaction-50.htm);
  Stretching with the Marquee Tool (AC20, …/AC20Help/02_Interaction/02_Interaction-88.htm);
  Copy/Paste Marquee Area (AC28, …/_AC28_Help/030_Interaction/030_Interaction-36.htm).
  Retirado: área retangular ou poligonal que não seleciona elementos; um pavimento ou
  todos; esticar pontos dentro e mover o que está todo dentro; arcos mantêm o ângulo
  central; 3D só do que toca a área; salvar o pedaço como PDF/DWG.
- Ajuda pública Autodesk: AutoCAD 2025 STRETCH por janela de cruzamento (objetos
  inteiros dentro se movem, os cortados esticam); Revit 2024/2025 Crop Region e Section
  Box (recorte da vista e caixa de corte 3D).
- Pesquisa: `research_notes/Pesquisa Archicad Revit AutoCAD/interface_e_interacao.md` §3
  (Selection Box do Revit sobrescreve o 3D padrão: aqui, aba temporária) e
  `archicad_modelagem.md` (área "grossa" para esticar em todos os pavimentos).
- Nada de `_restrito/`. "Área de seleção" e "Esticar" são termos comuns em pt‑BR.

## Parte B: pesquisa de 2026‑10‑21 (Archicad, Revit, AutoCAD)

Fontes públicas acessadas em 2026‑10‑21 por 15 frentes de pesquisa, só na web, sem
`_restrito/` nem `tools/`. "Página lida" = conteúdo aberto e lido; "trecho de busca" =
só o resumo do buscador (fórum da Graphisoft, G2 e blogs da Autodesk responderam HTTP 403;
Reddit inacessível): **conferir antes de citar numa spec**. A coluna "usado para" do
anexo foi gerada por script a partir das notas e precisa de revisão ao virar spec.

| Tema | Fontes | Página lida | Trecho de busca (conferir) | Notas brutas |
|---|---|---|---|---|
| Usuários e mercado brasileiro | 59 | 50 | 9 | `research_notes/Pesquisa Archicad Revit AutoCAD/usuarios_e_mercado_brasil.md` |
| Archicad: modelagem e interação | 124 | 23 | 101 | `research_notes/Pesquisa Archicad Revit AutoCAD/archicad_modelagem.md` |
| Archicad: documentação, colaboração e extensões | 37 | 18 | 19 | `research_notes/Pesquisa Archicad Revit AutoCAD/archicad_documentacao_colaboracao.md` |
| Revit: modelagem e famílias | 43 | 37 | 6 | `research_notes/Pesquisa Archicad Revit AutoCAD/revit_modelagem_familias.md` |
| Revit: documentação, colaboração e extensões | 41 | 22 | 19 | `research_notes/Pesquisa Archicad Revit AutoCAD/revit_documentacao_colaboracao.md` |
| AutoCAD, AutoCAD Architecture e Civil 3D | 54 | 42 | 12 | `research_notes/Pesquisa Archicad Revit AutoCAD/autocad.md` |
| Interface e interação | 42 | 38 | 4 | `research_notes/Pesquisa Archicad Revit AutoCAD/interface_e_interacao.md` |
| Normas e projeto legal no Brasil | 20 | 10 | 10 | `research_notes/Pesquisa Archicad Revit AutoCAD/normas_e_projeto_legal_brasil.md` |
| Quantitativos, orçamento e sustentabilidade | 57 | 41 | 16 | `research_notes/Pesquisa Archicad Revit AutoCAD/quantitativos_orcamento_sustentabilidade.md` |
| Terreno, topografia e implantação | 45 | 41 | 4 | `research_notes/Pesquisa Archicad Revit AutoCAD/terreno_e_implantacao.md` |
| Estrutura e instalações | 39 | 16 | 23 | `research_notes/Pesquisa Archicad Revit AutoCAD/estrutura_e_instalacoes.md` |
| Bibliotecas e objetos | 65 | 52 | 13 | `research_notes/Pesquisa Archicad Revit AutoCAD/bibliotecas_e_objetos.md` |
| Interoperabilidade openBIM | 44 | 37 | 7 | `research_notes/Pesquisa Archicad Revit AutoCAD/interoperabilidade_openbim.md` |
| Visualização e apresentação | 44 | 32 | 12 | `research_notes/Pesquisa Archicad Revit AutoCAD/visualizacao_apresentacao.md` |
| Ferramentas emergentes e IA | 44 | 43 | 1 | `research_notes/Pesquisa Archicad Revit AutoCAD/ferramentas_emergentes.md` |
| **Total** | **758** | | | |

Fontes **proibidas** que apareceram e **não foram usadas**: um endereço que parecia
hospedar o texto integral pago da ABNT NBR 6492:2021 (marcado "NÃO USAR" no anexo). Normas
ABNT só entram por título, escopo e resumo públicos, ou por exemplar legítimo.
