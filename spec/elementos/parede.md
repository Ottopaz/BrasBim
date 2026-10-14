---
elemento: Parede
entidade_ifc: IfcWall (PredefinedType via IfcWallType)
requisito: RF-ELE-01
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-14
status: aprovado
revisor: OTTO (aprovado em 2026-10-14)
---

# Parede

## 1. Propósito
Elemento construtivo vertical que delimita ou subdivide espaços, portante ou não.
Tem espessura constante ao longo do seu caminho, composta por camadas de material
(ex.: reboco + bloco + reboco). [IFC-WALL]

## 2. Mapeamento IFC

### 2.1 Entidade e tipo
- Ocorrência: `IfcWall` **com** `IfcMaterialLayerSetUsage` (o antigo
  `IfcWallStandardCase` foi descontinuado; esta é a forma atual). [IFC-WALL]
- Tipo: `IfcWallType` via `IfcRelDefinesByType` (RF-TIP-01). O `PredefinedType` fica no
  tipo; na ocorrência fica vazio. [IFC-WALL, *CorrectPredefinedType*]
- Valores de `IfcWallTypeEnum` oferecidos no MVP: `SOLIDWALL` (alvenaria/concreto),
  `PARTITIONING` (divisória, não portante), `PARAPET` (platibanda/mureta),
  `PLUMBINGWALL` (shaft/enchimento hidráulico), `USERDEFINED` (exige `ObjectType`).
  `STANDARD` e `POLYGONAL` estão obsoletos e **não** são gravados. [IFC-WALLENUM]
- Paredes de espessura variável, inclinadas ou de seção não retangular estão **fora** do
  escopo desta spec (seriam `IfcWall` sem `IfcMaterialLayerSetUsage`; ver §11).

### 2.2 Representações
| Identificador | Tipo | Conteúdo |
|---|---|---|
| `Axis` (contexto `Plan`) | `Curve2D` | Reta: `IfcPolyline` de 2 pontos sobre o eixo x local, no sentido +x. Curva: `IfcTrimmedCurve` sobre `IfcCircle`, tangente inicial em +x. [IFC-WALL] |
| `Body` (contexto `Model`) | `SweptSolid` | `IfcExtrudedAreaSolid` de `IfcArbitraryClosedProfileDef` (planta da parede **já com as junções resolvidas**), extrudado em +z local. [IFC-WALL] |
| `Body` | `Clipping` | Quando o topo é recortado (V1, RF-ELE-17): `IfcBooleanClippingResult` do sólido acima com `IfcHalfSpaceSolid`/`IfcPolygonalBoundedHalfSpace`. [IFC-WALL] |

- `ObjectPlacement`: `IfcLocalPlacement` relativo ao pavimento; origem no ponto inicial da
  linha de referência; eixo x local na direção do desenho; z = vertical do pavimento.

### 2.3 Material
- `IfcMaterialLayerSet` (composição reutilizável, RF-TIP-02) associado ao `IfcWallType`;
  `IfcMaterialLayerSetUsage` associado à ocorrência, ambos por `IfcRelAssociatesMaterial`.
  [IFC-MLSU]
- `LayerSetDirection = AXIS2` (sempre, para paredes). [IFC-WALL, IFC-MLSU]
- `IfcMaterialLayer`: `Material`, `LayerThickness`, `Name`, `Category`
  (`LoadBearing`, `Insulation`, `Finish`…), `Priority` [0..100], `IsVentilated`
  (câmara de ar). [IFC-ML]
- Espessura da parede = `IfcMaterialLayerSet.TotalThickness` (soma das camadas, sem
  vazios nem sobreposição). [IFC-WALL]

### 2.4 Propriedades e quantidades
- `Pset_WallCommon` (ver §3.3). [IFC-PSET]
- `Qto_WallBaseQuantities` via `IfcElementQuantity` (ver §8). [IFC-QTO]

### 2.5 Relações
| Relação | Uso |
|---|---|
| `IfcRelContainedInSpatialStructure` | Parede contida em um `IfcBuildingStorey` (padrão); `IfcBuilding` ou `IfcSite` só se não houver pavimento. [IFC-WALL] |
| `IfcRelConnectsPathElements` | Junções L/T/X (§6.2). [IFC-RCPE, IFC-CTE] |
| `IfcRelVoidsElement` | Parede → `IfcOpeningElement` (1:1 por abertura). [IFC-RVE] |
| `IfcRelFillsElement` | `IfcOpeningElement` → `IfcDoor`/`IfcWindow` (1:1). [IFC-RFE] |
| `IfcRelDefinesByType` | Parede → `IfcWallType`. |
| `IfcRelDefinesByProperties` | Psets e `IfcElementQuantity`. |

## 3. Parâmetros

### 3.1 Geometria
| Parâmetro | Tipo | Unidade | Padrão | Regras |
|---|---|---|---|---|
| Forma do caminho | enum `reta` \| `arco` | — | `reta` | Parede "poligonal" = cadeia de paredes retas ligadas em L (§4) |
| Ponto inicial / final | ponto 2D | m | — | Comprimento > 0,001 m |
| Arco: raio, sentido | real, enum | m | — | Raio ≥ espessura/2 + 0,001 m |
| Linha de referência | enum `eixo` \| `face esquerda` \| `face direita` | — | `face esquerda` | Esquerda/direita em relação ao sentido do desenho |
| Inverter camadas | bool | — | falso | Ver §3.2 |
| Pavimento base | ref. `IfcBuildingStorey` | — | pavimento ativo | — |
| Deslocamento da base | real | m | 0,00 | Em relação à cota do pavimento base |
| Topo | enum `ligado a pavimento` \| `altura fixa` | — | `ligado a pavimento` | — |
| Pavimento do topo | ref. `IfcBuildingStorey` | — | pavimento imediatamente acima | Se não houver, topo = `altura fixa` |
| Deslocamento do topo | real | m | 0,00 | — |
| Altura fixa | real | m | 2,80 | > 0 |
| Altura resultante | real (calculado) | m | — | Deve ser > 0; senão a operação é rejeitada |

Os vínculos com pavimentos (base, topo, deslocamentos, linha de referência) não têm
atributo IFC próprio; ficam no Pset próprio **`BrasBim_Parede`** (prefixo `Pset_` é
reservado à buildingSMART). Ao reabrir, a geometria é recalculada a partir deles; se o
Pset faltar (IFC de outra origem), a parede é lida como `altura fixa`. *(decisão do projeto)*

### 3.2 Linha de referência → `IfcMaterialLayerSetUsage`
`T` = espessura total. A linha desenhada é sempre a curva `Axis`. Camada 1 = primeira
da lista `MaterialLayers`. Eixo +y local = lado esquerdo de quem percorre a parede.

| Linha de referência | Inverter | `DirectionSense` | `OffsetFromReferenceLine` | Camada 1 fica na |
|---|---|---|---|---|
| face direita | não | `POSITIVE` | 0 | face direita |
| eixo | não | `POSITIVE` | −T/2 | face direita |
| face esquerda | não | `POSITIVE` | −T | face direita |
| face direita | sim | `NEGATIVE` | +T | face esquerda |
| eixo | sim | `NEGATIVE` | +T/2 | face esquerda |
| face esquerda | sim | `NEGATIVE` | 0 | face esquerda |

Fonte da semântica: [IFC-MLSU] (`OffsetFromReferenceLine` positivo = +y; `DirectionSense`
POSITIVE = camadas crescem para +y a partir da base). A tabela é decisão do projeto.

### 3.3 `Pset_WallCommon` (MVP)
| Propriedade | Tipo IFC | Padrão | Observação |
|---|---|---|---|
| `Reference` | IfcIdentifier | nome do tipo | — |
| `Status` | `PEnum_ElementStatus` | `NEW` | RF-PRJ-08 (V1 para filtros) |
| `IsExternal` | IfcBoolean | falso | Inferido na criação de ambientes (RF-AMB-01, V1); editável |
| `LoadBearing` | IfcBoolean | do tipo | `SOLIDWALL` → verdadeiro; `PARTITIONING` → falso |
| `FireRating`, `AcousticRating`, `ThermalTransmittance`, `Combustible`, `SurfaceSpreadOfFlame`, `ExtendToStructure`, `Compartmentation` | conforme [IFC-PSET] | vazio | Só gravadas se preenchidas |

### 3.4 Composições iniciais (biblioteca, RF-TIP-06)
Exemplos, a revisar: alvenaria cerâmica 14 cm (reboco 2,5 + bloco 9 + reboco 2,5);
alvenaria 19 cm (2,5 + 14 + 2,5); concreto 12 cm; drywall 9,5 cm (gesso 1,25 + montante
7 + gesso 1,25). Prioridades: estrutura 100 > bloco 80 > isolamento 40 > acabamento 20.
*(CG)*

## 4. Criação (interação do usuário)
1. Usuário escolhe o tipo de parede e a linha de referência (painel de propriedades).
2. Clica o ponto inicial e o final; snaps, restrições e entrada numérica de RF-DES-01..04.
3. **Cadeia:** após o 1º segmento, cada novo clique cria outra parede começando no fim da
   anterior, com junção L automática. Fechar no ponto inicial cria a última junção L.
   Duplo clique ou Esc encerra.
4. **Arco:** modo por 3 pontos (início, ponto no arco, fim).
5. **Retângulo:** 2 cantos opostos geram 4 paredes com 4 junções L.
6. Pré‑visualização mostra a espessura real, o lado das camadas e as junções que serão
   criadas.
7. Toda a criação (cadeia inteira, retângulo) é **uma** transação (RF-NUC-01).

## 5. Edição

### 5.1 Interações
- Alças: extremidades (esticar/encurtar; mover só a extremidade), ponto médio (mover a
  parede paralelamente), alça de arco (raio).
- Mover, copiar, girar, espelhar (RF-NUC-05). Espelhar inverte o sentido do caminho e
  mantém as faces das camadas no mesmo lado físico.
- Edição numérica de comprimento, ângulo, alturas, deslocamentos.
- Trocar o tipo: atualiza camadas e espessura, mantendo a linha de referência fixa.
- Inverter camadas (§3.2) sem mover a linha de referência.
- Dividir parede num ponto: gera duas paredes com junção L colinear entre elas;
  aberturas vão para a parede que as contém (aberturas cortadas pelo ponto de divisão
  impedem a operação, com aviso).
- Alterar a cota ou excluir um pavimento recalcula as paredes ligadas a ele; excluir o
  pavimento do topo converte a parede para `altura fixa` com a altura atual.

### 5.2 Operações serializáveis (RF-NUC-02)
Cada operação é um registro com `op`, `GlobalId` dos objetos afetados e parâmetros em
unidades SI, suficiente para reproduzir e desfazer a alteração em outra máquina.
Rascunho (formato final em `spec/01-modelo-de-dados.md`):

| `op` | Dados |
|---|---|
| `wall.create` | `GlobalId` novo, tipo (`GlobalId`), pavimento, caminho, parâmetros de §3.1 |
| `wall.edit` | `GlobalId`, parâmetros alterados (antes/depois) |
| `wall.delete` | `GlobalId` (inclui em cascata as aberturas e junções; ver §6.4) |
| `wall.split` | `GlobalId` original, ponto, `GlobalId` da nova parede |
| `wall_type.edit` | `GlobalId` do tipo, camadas antes/depois |
| `path_connection.create` / `.delete` | `GlobalId` da relação, das duas paredes e tipos de conexão |
| `opening.create` / `.edit` / `.delete` | `GlobalId` da abertura e da parede, posição, dimensões |
| `filling.attach` / `.detach` | `GlobalId` da abertura e do elemento de preenchimento |

Efeitos derivados (recalcular `Body`, recortes de junção, quantidades) **não** são
registrados: são recalculados por quem aplica a operação. Para reserva de elementos
(RF-COL-02), uma operação que altera junções exige a reserva das duas paredes.
*(decisão do projeto)*

## 6. Comportamento e regras geométricas

### 6.1 Corpo
- Perfil = faces paralelas à linha de referência, afastadas conforme §3.2, recortadas
  pelas junções; extrudado da base ao topo. [IFC-WALL]
- Paredes em arco: faces concêntricas ao eixo. [IFC-WALL]

### 6.2 Junções
Detecção automática quando, no mesmo pavimento e com faixas de altura que se sobrepõem,
uma extremidade de uma parede coincide (tolerância 1 mm) com a extremidade ou o caminho
de outra. *(CG)*

| Junção | Situação | `RelatingConnectionType` | `RelatedConnectionType` | Fonte |
|---|---|---|---|---|
| L | fim de A com início de B | `ATEND` | `ATSTART` | [IFC-CTE] |
| L | início de A com início de B | `ATSTART` | `ATSTART` | [IFC-CTE] |
| L | fim de A com fim de B | `ATEND` | `ATEND` | decisão do projeto (não listada na tabela do IFC) |
| T | extremidade de B no meio de A | `ATPATH` (A) | `ATSTART`/`ATEND` (B) | [IFC-CTE] |
| X | A e B se cruzam pelo meio | `ATPATH` | `ATPATH` | decisão do projeto (não listada na tabela do IFC) — **ponto de revisão** |

- Em T, a parede que atravessa (A) é `RelatingElement`; a que chega (B) é
  `RelatedElement` e é recortada na face de A. [IFC-WALL, *Path Connectivity*]
- Em L: recorte em meia‑esquadria (bissetriz) quando as espessuras são iguais; com
  espessuras diferentes, cada parede é estendida até a face externa da outra. *(CG)*
- Em X: as paredes não são divididas; no 3D os corpos se sobrepõem; na planta, a de maior
  prioridade é desenhada contínua e a outra é interrompida. *(CG)*
- **Prioridade por camada** (V1): na junção, a camada de maior `IfcMaterialLayer.Priority`
  avança sobre a de menor; `RelatingPriorities`/`RelatedPriorities` sobrescrevem por
  junção. [IFC-ML, IFC-RCPE] No MVP, o recorte é feito pela espessura total e as
  prioridades só afetam a planta (§7).
- `ConnectionGeometry` (`IfcConnectionCurveGeometry`): não gravado no MVP (opcional no
  IFC); V1. [IFC-RCPE]
- Usuário pode: desfazer uma junção (paredes ficam com topo reto, sem relação); forçar
  junção entre paredes próximas; trocar qual parede é contínua num T/X.

### 6.3 Aberturas
- Cada abertura é um `IfcOpeningElement` com `IfcRelVoidsElement` para a parede. Não
  participa de `IfcRelContainedInSpatialStructure`. [IFC-OPEN, IFC-RVE]
- `PredefinedType`: `OPENING` (atravessa a parede) ou `RECESS` (nicho, profundidade <
  espessura). [IFC-OPENENUM]
- `ObjectPlacement` relativo ao da parede. [IFC-OPEN]
- `Body`/`SweptSolid`: `IfcRectangleProfileDef` (XDim = largura, YDim = altura, posição
  centrada) extrudado perpendicularmente à parede. Profundidade de `OPENING` = espessura
  + 0,01 m de folga para cada lado; de `RECESS` = valor informado. [IFC-OPEN]
- Parâmetros: distância ao início da parede (ao longo do eixo), largura, altura,
  peitoril (base em relação à base da parede), profundidade (só nicho), lado de
  entrada do nicho.
- Vão livre (sem preenchimento) é permitido. Portas e janelas (RF-ELE-05/06) criam sua
  abertura e se ligam a ela por `IfcRelFillsElement`; detalhes nas specs de porta e
  janela. [IFC-RFE]
- Abertura em parede de arco: V1.
- Regras: abertura deve ficar dentro dos limites da parede; ao editar a parede, a
  abertura mantém a distância ao início e a cota do peitoril; se sair dos limites,
  é marcada como inválida (aviso), não excluída. Aberturas não se sobrepõem (aviso).

### 6.4 Exclusão
Excluir uma parede exclui suas aberturas, os elementos que as preenchem (com
confirmação), suas junções e as relações de tipo/material/Psets exclusivos. Paredes
vizinhas têm o corpo recalculado (perdem o recorte).

## 7. Representação 2D
Gerada a partir do modelo (RF-DOC-01/02); nada de geometria 2D gravado no IFC no MVP.
Convenções gerais de desenho arquitetônico brasileiro *(CG)*; a conformidade com o
texto da NBR 6492:2021 e com a norma de linhas (NBR 16861, a confirmar) depende de
leitura das normas e fica como **pendência de revisão**.

| Situação | Planta | Corte |
|---|---|---|
| Parede cortada pelo plano | Contorno em linha grossa; preenchimento conforme nível de detalhe | Idem |
| Parede abaixo do plano (em vista) | Contorno em linha média/fina | Linha média/fina (fachada/vista) |
| Parede acima do plano | Linha tracejada fina (opcional por vista) | — |

- **Plano de corte da planta:** padrão 1,50 m acima do piso do pavimento, configurável
  por vista. *(CG, a confirmar na NBR 6492)*
- **Níveis de detalhe** (RF-DOC-08):
  - 1:100 ou menor: contorno externo da parede, preenchimento sólido ou sem
    preenchimento (configurável); junções sem linhas internas.
  - 1:50 ou maior: cada camada com seu contorno e a hachura do material (RF-TIP-03);
    junções desenhadas conforme a prioridade das camadas.
- **Aberturas:** vão interrompe as linhas da parede cortada; peitoril abaixo do plano de
  corte aparece em linha de projeção; nicho em planta aparece como recorte da face.
- **Situação na obra** (`Status`, V1): estilos distintos para existente, a construir e a
  demolir (ex.: a demolir em tracejado), configuráveis. *(CG)*
- Espessuras e tipos de linha vêm da configuração de RF-DOC-03, não desta spec.

## 8. Quantitativos
Gravados em `Qto_WallBaseQuantities` e recalculados a cada alteração. [IFC-QTO]
Definições de cálculo são decisão do projeto, salvo onde citado.

| Quantidade | Tipo | Cálculo |
|---|---|---|
| `Length` | comprimento | Ao longo do eixo central da parede (meio da espessura), mesmo que a linha de referência seja uma face; sem recortes de junção. [IFC-QTO] |
| `Width` | comprimento | `TotalThickness`. [IFC-QTO] |
| `Height` | comprimento | Altura resultante (constante no MVP). [IFC-QTO] |
| `GrossFootprintArea` | área | `Length × Width` |
| `NetFootprintArea` | área | Área do perfil do `Body` (após junções) menos aberturas `OPENING` que tocam a base |
| `GrossSideArea` | área | `Length × Height` (um lado) |
| `NetSideArea` | área | `GrossSideArea` − área frontal das aberturas `OPENING` |
| `GrossVolume` | volume | `GrossFootprintArea × Height` |
| `NetVolume` | volume | Volume do sólido após junções e após subtrair aberturas e nichos. [IFC-QTO] |
| `GrossWeight` / `NetWeight` | massa | Σ (volume da camada × densidade do material); gravados só se todos os materiais tiverem densidade (V1) |

Critérios de desconto de vãos para orçamento (ex.: SINAPI) são configuráveis nas tabelas
(RF-QTD-02, RF-QTD-07), não alteram o `Qto`.

## 9. Critérios de aceite (testes)
Todos verificam o IFC gravado e relido com `ifcopenshell.open`.

- [ ] **P01** Parede reta 5 m, tipo 14 cm, base pav. térreo (0,00), topo ligado ao pav.
      superior (2,80): 1 `IfcWall` contida no térreo; `Axis` = polilinha de 2 pontos com
      comprimento 5,000; `Body` = `IfcExtrudedAreaSolid` com profundidade 2,800.
- [ ] **P02** Material: `IfcMaterialLayerSetUsage` na ocorrência com `AXIS2`;
      `IfcMaterialLayerSet` no `IfcWallType` com 3 camadas somando 0,14.
- [ ] **P03** Para cada linha da tabela §3.2, `DirectionSense` e `OffsetFromReferenceLine`
      corretos e o perfil do `Body` do lado esperado da linha `Axis`.
- [ ] **P04** Alterar a cota do pavimento superior para 3,00 → `Height` = 3,00 e corpo
      recalculado, `GlobalId` inalterado.
- [ ] **P05** Cadeia de 3 segmentos → 3 `IfcWall` e 2 `IfcRelConnectsPathElements`
      (`ATEND`/`ATSTART`); fechando o retângulo → 4 paredes, 4 relações.
- [ ] **P06** Junção T → relação com `RelatingConnectionType = ATPATH` e a parede que
      chega termina na face da outra (verificado pelo volume do `Body`).
- [ ] **P07** Junção X → relação `ATPATH`/`ATPATH`, nenhuma parede dividida.
- [ ] **P08** Abertura 0,90 × 2,10 a 1,00 m do início: `IfcOpeningElement`
      (`OPENING`) sem contenção espacial, placement relativo à parede,
      `IfcRelVoidsElement` 1:1; `NetSideArea` = 5×2,8 − 0,9×2,1.
- [ ] **P09** Porta na abertura → `IfcRelFillsElement` ligando abertura e `IfcDoor`.
- [ ] **P10** Nicho → `RECESS`; `NetSideArea` não muda, `NetVolume` diminui.
- [ ] **P11** Excluir parede com abertura → sem `IfcOpeningElement`,
      `IfcRelVoidsElement` nem `IfcRelConnectsPathElements` órfãos.
- [ ] **P12** `Pset_WallCommon` com `Status = NEW`, `LoadBearing` conforme o tipo;
      Pset `BrasBim_Parede` com os vínculos de §3.1.
- [ ] **P13** Parede em arco: `Axis` = `IfcTrimmedCurve` sobre `IfcCircle`; `Length`
      = comprimento do arco do eixo central.
- [ ] **P14** Cada ação do usuário gera exatamente as operações de §5.2; desfazer e
      refazer reproduzem o mesmo IFC (comparando `GlobalId`s e atributos).
- [ ] **P15** Aplicar a lista de operações serializada num modelo vazio com os mesmos
      pavimentos reproduz o mesmo IFC.
- [ ] **P16** IFC sem `BrasBim_Parede` (outra origem): parede abre, é editável como
      `altura fixa`, e é gravada de volta sem perda de dados.
- [ ] **P17** Arquivo passa na validação de esquema do IfcOpenShell.

## 10. Fontes públicas
Documentação IFC 4.3 lida no repositório oficial da buildingSMART (o site
`ifc43-docs.standards.buildingsmart.org` bloqueia acesso automatizado), ramo `ifc4.3-main`,
consultado em 2026‑10‑14. Base: `https://github.com/buildingSMART/IFC4.x-development/blob/ifc4.3-main/`

| Código | Documento |
|---|---|
| IFC-WALL | `docs/schemas/shared/IfcSharedBldgElements/Entities/IfcWall.md` |
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

## 11. Fora do escopo / pendências
- Paredes de espessura variável, inclinadas, de seção não retangular, perfis compostos
  por partes (`IfcRelAggregates`, `ELEMENTEDWALL`) e parede com topo/base em rampa: V1/V2.
- Recorte por cobertura (RF-ELE-17, `Clipping`): V1.
- Pontos de revisão, aceitos pelo revisor em 2026‑10‑14: (a) junção X como `ATPATH`/`ATPATH`; (b) L `ATEND`/`ATEND`;
  (c) plano de corte e convenções gráficas frente à NBR 6492; (d) nome do Pset próprio.
