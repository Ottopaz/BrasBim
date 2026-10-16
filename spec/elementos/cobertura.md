---
elemento: Cobertura
entidade_ifc: IfcRoof (agregado) + IfcSlab (ROOF, via IfcSlabType)
requisito: RF-ELE-07 (MVP, simples)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-16
status: aprovado
revisor: OTTO (aprovado em 2026-10-16)
---

# Cobertura

Spec da cobertura **simples**: plana, uma água, duas águas e quatro águas, com beiral,
gerada a partir de um contorno e de poucos parâmetros. Telhados de forma livre
(L, T, mansarda), madeiramento, calhas e o ajuste das paredes ao telhado ficam para o
V1 (§11).

## 1. Propósito
A cobertura fecha a edificação por cima e a protege da chuva. No BrasBim, ela é um
elemento só para o usuário (seleciona, edita e exclui de uma vez), formado por uma peça
para cada água. [IFC-ROOF]

## 2. Mapeamento IFC

### 2.1 Entidades
- **`IfcRoof`**: o conjunto. Ele usa a representação por **montagem**: agrega as peças
  por `IfcRelAggregates` e **não tem geometria própria**. A forma dele é a soma das
  peças. [IFC-ROOF, *Element Decomposition*]
- `IfcRoof.PredefinedType` fica na ocorrência, sem `IfcRoofType` no MVP: `FLAT_ROOF`
  (plana), `SHED_ROOF` (uma água), `GABLE_ROOF` (duas águas), `HIP_ROOF` (quatro águas)
  e `PAVILION_ROOF` (quatro águas sobre um quadrado, em pirâmide). [IFC-ROOFENUM;
  *CorrectPredefinedType*: sem tipo associado, o valor fica na ocorrência]
- **Peças:** uma `IfcSlab` por água. O tipo de cada uma é um `IfcSlabType` com
  `PredefinedType = ROOF`. Todas as peças de uma cobertura usam o mesmo tipo, o tipo da
  cobertura. [IFC-ROOF, *IfcSlab*: "uma laje por face"; IFC-SLABENUM]
- **Contenção:** só a `IfcRoof` fica no pavimento (`IfcRelContainedInSpatialStructure`).
  As peças pertencem ao pavimento através dela, sem contenção própria. [IFC-ROOF,
  *Spatial Containment*]
- **Posicionamento:** a cobertura é posicionada em relação ao pavimento e as peças em
  relação à cobertura. Mover a cobertura move as peças. [IFC-ROOF, *Product Local
  Placement*]

### 2.2 Geometria de cada peça
- `Body`, `SweptSolid`: `IfcExtrudedAreaSolid` de um `IfcArbitraryClosedProfileDef`
  (polígono da água). [IFC-SLAB, *Body SweptSolid Geometry*]
- O sistema local da peça fica **no plano da água**: a origem é um vértice do beiral, o
  eixo x corre ao longo do beiral e o eixo z é a normal da água, para cima. O perfil é o
  polígono da água desenhado nesse plano, e a extrusão é **perpendicular à água**, para
  baixo, com a espessura do tipo. Assim as faces de cima de duas águas se encontram
  exatamente na cumeeira e nos espigões, e as camadas continuam valendo
  (`AXIS3`, espessura medida perpendicular ao plano da peça). *(decisão do projeto,
  dentro do que [IFC-SLAB] permite)*
- **Ponto de revisão:** o IFC também aceita perfil horizontal com extrusão inclinada e
  corte no beiral (figura de [IFC-SLAB]). Com o perfil no plano da água, a borda do
  beiral sai em esquadro com a telha e não fica vertical. Isso é suficiente no MVP; o
  corte vertical do beiral fica para o V1.
- Sem `Axis` nem `FootPrint`: a planta é calculada.

### 2.3 Material
Como na laje (laje.md §2.3): `IfcMaterialLayerSet` no tipo e
`IfcMaterialLayerSetUsage` em cada peça (`AXIS3`, `POSITIVE`), com
`TotalThickness` = `Depth`. A interface lista as camadas de cima para baixo.

### 2.4 Propriedades e quantidades
- **Na cobertura:** `Pset_RoofCommon` (`Reference` = nome do tipo, `Status = NEW`,
  `IsExternal = TRUE`, os demais só se preenchidos) [IFC-PSET-R];
  `Qto_RoofBaseQuantities` (§8) [IFC-QTO-R]; Pset próprio `BrasBim_Cobertura` com os
  parâmetros (§3.1), em JSON, como nas vistas.
- **Em cada peça:** `Pset_SlabCommon` com `PitchAngle` (inclinação da água na unidade
  de ângulo do projeto, que é o radiano; 0 na plana) e `IsExternal = TRUE`;
  `Qto_SlabBaseQuantities` (§8). [IFC-PSET-S] A interface mostra a inclinação em % e
  em graus.
- As peças não têm `BrasBim_Laje`: o estado delas vem da cobertura, e elas são
  refeitas a partir dela.

## 3. Parâmetros

### 3.1 Cobertura
| Parâmetro | Tipo | Unidade | Padrão *(CG)* | Regras |
|---|---|---|---|---|
| Contorno | lista de pontos 2D | m | — | O **contorno de apoio**: por onde a cobertura passa sobre as paredes, normalmente a face externa delas. Mesmas regras do contorno da laje (laje.md §3.1); anti-horário |
| Forma | `flat` \| `shed` \| `gable` \| `hip` | — | `gable` | `gable` e `hip` só com contorno **retangular** (pode estar girado) |
| Inclinação | real | % | 30 | 0 na plana; de 1 a 100 nas outras. A interface também mostra em graus |
| Beiral | real | m | 0,60 | De 0 a 2; igual em todos os lados no MVP |
| Altura de apoio | real | m | topo das paredes do pavimento; sem paredes, 2,80 | Cota da **face de baixo** da cobertura sobre o contorno de apoio, em relação ao pavimento |
| Lado | inteiro | — | ver §4 | Índice do lado do contorno: na uma água, o lado **mais baixo**; na duas águas, um lado **paralelo à cumeeira** |
| Tipo | ref. `IfcSlabType` (`ROOF`) | — | último usado | — |
| Pavimento | ref. `IfcBuildingStorey` | — | ativo | — |

O beiral desce com a água: a borda fica abaixo da altura de apoio
(beiral × inclinação). Na plana, a borda fica na própria altura de apoio.

### 3.2 Tipos de peça (biblioteca inicial, *CG, a revisar*)
Os tipos usam `IfcSlabType` com `PredefinedType = ROOF` e são editados no diálogo de
tipos de laje, como os outros (spec/ui 10). A espessura representa o volume do telhado
no desenho e no 3D, não a da telha isolada.

| Nome | Camadas (de cima para baixo) | Inclinação usual (só informativa) |
|---|---|---|
| Telha cerâmica | telha cerâmica 5 cm | 30 a 35 % |
| Telha de fibrocimento | telha de fibrocimento 3 cm | 10 a 15 % |
| Telha metálica sanduíche | telha metálica 5 cm | 5 a 10 % |
| Laje impermeabilizada 12 cm | impermeabilização 2 + concreto 10 | 1 a 2 % (plana) |

A inclinação usual não é verificada no MVP: depende do fabricante da telha. A
verificação pela inclinação mínima fica para o V1, junto com a verificação por norma.

## 4. Criação
Ferramenta **Cobertura**, logo depois da Laje. A barra de opções tem forma, tipo,
inclinação (%), beiral e altura de apoio. Há três modos de contorno *(CG)*:
- **Retângulo:** dois cantos opostos.
- **Polígono:** como na laje (clique nos vértices; Enter, duplo-clique ou o primeiro
  ponto fecham; Esc desfaz o último ponto).
- **Pelas paredes** (modo inicial): um clique dentro da edificação usa o contorno
  **externo** da união das paredes em volta do ponto (`rooms.building_outline`). É a
  face externa da edificação inteira, não a de um cômodo.

Depois do contorno:
- **Plana e quatro águas:** a cobertura é criada na hora.
- **Uma água:** o usuário clica no lado que fica mais baixo. O lado sob o cursor fica
  destacado, e Enter aceita o lado maior.
- **Duas águas:** o usuário clica num lado paralelo à cumeeira. Enter aceita a
  cumeeira paralela ao lado maior, que é o mais comum.

Pré-visualização: o contorno do beiral, a cumeeira e os espigões em linha fina, com a
seta da água. Uma forma que não serve para o contorno (duas ou quatro águas em contorno
não retangular) é recusada com a mensagem "Duas e quatro águas só com contorno
retangular; use uma água, plana ou várias coberturas". Transação:
(`slab_type.create`, se faltar) → `roof.create`.

## 5. Edição
- Selecionar uma peça seleciona a cobertura inteira, e é ela que move, copia, gira,
  espelha e exclui.
- **Painel de propriedades:** forma, tipo, inclinação, beiral, altura de apoio e lado.
  O lado aparece como "Lado mais baixo" ou "Cumeeira paralela a", com os lados
  numerados no desenho enquanto o campo está em foco. Também mostra as propriedades
  comuns e as quantidades (§8), só para leitura.
- **Alças na planta:** os vértices do contorno de apoio, como na laje (laje.md §5.1).
  Mover um vértice de uma cobertura de duas ou quatro águas a deixa fora do retângulo;
  nesse caso a edição é recusada e a mensagem explica por quê.
- Mudar qualquer parâmetro refaz as peças. Quando a quantidade de águas não muda, as
  peças mantêm o `GlobalId`.

### 5.1 Operações serializáveis
| `op` | Dados |
|---|---|
| `roof.create` / `.delete` | `guid`, `parts[]` (GlobalIds das peças, na ordem das águas), `name`, `type`, `storey`, `outline[]`, `shape`, `slope`, `overhang`, `base_height`, `side`, `common` |
| `roof.edit` | campos alterados (antes/depois), inclusive `parts` quando a quantidade de águas muda |

Mover, girar e espelhar geram `roof.edit` do contorno (girar e espelhar também
recalculam o `side` para o mesmo lado físico). Desfazer restaura os mesmos `GlobalId`s
da cobertura e das peças.

## 6. Comportamento e regras geométricas
Sejam C o contorno de apoio, h a altura de apoio, i = inclinação/100, b o beiral e B o
contorno do beiral, que é C afastado b para fora (cantos em esquadro). Cada água é um
plano que passa por um lado de C na cota h e sobe para dentro com a declividade i.
A face de baixo de cada peça fica nesse plano, e a face de cima fica uma espessura
acima, na direção da normal.

| Forma | Águas |
|---|---|
| Plana | Uma peça horizontal: o polígono B, com a face de baixo em h |
| Uma água | Uma peça: B, no plano que passa pelo lado escolhido (o mais baixo) |
| Duas águas | Duas peças, retângulos separados pela cumeeira, que fica no meio e paralela ao lado escolhido; os oitões ficam nas pontas |
| Quatro águas | Retângulo de lados L ≥ W. A cumeeira tem comprimento L − W e fica no centro, na cota h + i·W/2. São dois trapézios e dois triângulos; num quadrado, quatro triângulos (`PAVILION_ROOF`) |

- A divisão em águas é feita em B, e as linhas de cumeeira e espigão são as interseções
  dos planos. Com o beiral, nada muda nos planos, só na borda.
- **Sem recorte nem ajuste das paredes no MVP:** as paredes continuam com o topo que
  tinham. O usuário pode usar o topo em empena ou inclinado da parede (spec/ui 08) para
  fechar o oitão. O ajuste automático fica para o V1 (RF-ELE-17). **Ponto de revisão.**
- As peças não entram nos recortes entre elementos estruturais (spec/ui 12).
- Excluir a cobertura exclui as peças. Excluir uma peça sozinha não é possível, porque
  a seleção pega a cobertura.

## 7. Representação 2D
Convenção geral *(CG)*; conferência com a NBR 6492 pendente.

| Planta | Desenho |
|---|---|
| Do próprio pavimento, com a cobertura acima do plano de corte (caso comum: paredes e cobertura no Térreo) | Só o **contorno do beiral**, tracejado, como os outros elementos acima do plano |
| Do próprio pavimento, com a cobertura abaixo do plano de corte (ex.: um pavimento "Cobertura" acima das paredes) | **Planta de cobertura:** contorno do beiral, cumeeira e espigões em linha contínua fina, e uma seta em cada água apontando para baixo com o texto `i = 30%` |
| Do pavimento de baixo | Contorno do beiral tracejado, como projeção da cobertura. **Ponto de revisão** |

- A seta e o texto seguem o tamanho em papel das anotações (spec/ui 13) e a escala
  da vista.
- **Cortes e fachadas:** as peças entram como os outros elementos (spec/ui 14). A
  cobertura cortada recebe o preenchimento do tipo, e a vista fica em projeção.
- **3D:** as peças aparecem com o material do tipo.

## 8. Quantitativos
Recalculados a cada alteração.

| Onde | Quantidade | Cálculo |
|---|---|---|
| Peça (`Qto_SlabBaseQuantities`) | `Width` | espessura do tipo |
| | `GrossArea` = `NetArea` | área **inclinada** da água (área em planta ÷ cos α) |
| | `Perimeter` | perímetro da água, no plano dela |
| | `GrossVolume` = `NetVolume` | área × espessura |
| Cobertura (`Qto_RoofBaseQuantities`) | `GrossArea` = `NetArea` | soma das áreas das peças [IFC-QTO-R] |

A área **em planta** (projeção horizontal de B) é útil para tabelas e orçamento. Como o
`Qto_RoofBaseQuantities` não tem esse campo, ela fica em `BrasBim_Cobertura`
(`AreaProjecao`), calculada e só para leitura. As tabelas do próximo pacote leem esse
valor.

## 9. Assistente
O assistente ganha `create_roof` (contorno, ou `over_walls: true` para usar o contorno
externo das paredes, forma, inclinação, beiral, altura de apoio, lado e tipo) e
`edit_roof` (os mesmos campos). `describe_model` passa a listar as coberturas. As
instruções para a IA dizem que a cobertura só é feita quando o pedido fala em telhado
ou cobertura, ou quando o pedido é de uma edificação inteira, que o padrão é duas águas
de telha cerâmica a 30 % com beiral de 60 cm, e que o contorno das paredes é usado por
padrão.

## 10. Critérios de aceite (testes)
- [x] **CB01** Duas águas sobre o retângulo 10 × 6 (cumeeira paralela ao lado de 10),
      h = 2,80, i = 30 %, b = 0,60: `IfcRoof` `GABLE_ROOF` no pavimento, sem `Body`;
      `IfcRelAggregates` com duas `IfcSlab` de tipo `ROOF`, sem contenção própria;
      cumeeira na cota 2,80 + 0,30 × 3 = 3,70 (face de baixo); beiral na cota
      2,80 − 0,18 = 2,62.
- [x] **CB02** As peças são posicionadas em relação à cobertura; cada uma tem
      `IfcExtrudedAreaSolid` perpendicular ao plano da água, com
      `IfcMaterialLayerSetUsage` `AXIS3` e `TotalThickness` = `Depth`.
- [x] **CB03** Quatro águas sobre 10 × 6: dois trapézios e dois triângulos, cumeeira de
      4 m; sobre 6 × 6: quatro triângulos e `PAVILION_ROOF`.
- [x] **CB04** Uma água em polígono em L, com o lado mais baixo escolhido: uma peça,
      com as áreas certas; a plana dá uma peça horizontal com `PitchAngle` 0.
- [x] **CB05** Duas ou quatro águas sobre um contorno não retangular: recusado, modelo
      intacto.
- [x] **CB06** Quantidades: área inclinada de cada água = área em planta ÷ cos α;
      `Qto_RoofBaseQuantities.GrossArea` = soma; `AreaProjecao` = área de B;
      `PitchAngle` = atan(i) (radianos).
- [x] **CB07** Pelas paredes: quatro paredes formando 8 × 5 pelos eixos, espessura 14
      → contorno de apoio 8,14 × 5,14.
- [x] **CB08** Editar a inclinação ou o beiral: peças com os mesmos `GlobalId`s;
      mudar de duas para quatro águas: quatro peças; desfazer volta às duas peças
      originais, com os mesmos `GlobalId`s.
- [x] **CB09** Mover, girar e espelhar: `roof.edit`; a uma água continua baixa no mesmo
      lado físico; desfazer, refazer e reaplicar o diário reproduzem o mesmo IFC.
- [x] **CB10** Excluir e desfazer: cobertura e peças com os mesmos `GlobalId`s, sem
      entidades órfãs.
- [x] **CB11** Planta: acima do plano, só o contorno tracejado; abaixo do plano,
      cumeeira, espigões, setas e `i = 30%`. Corte transversal da duas águas mostra
      as duas peças cortadas.
- [x] **CB12** Assistente: `create_roof` com `over_walls` sobre uma casa gera a
      cobertura e `describe_model` a lista.
- [x] **CB13** O arquivo passa na validação de esquema do IfcOpenShell, e reabrir o
      arquivo reproduz a cobertura editável.
- [x] **CB14** Interface: a ferramenta pelas paredes mostra o contorno sob o cursor; o
      clique pede o lado e Enter aceita o maior; a altura de apoio padrão é o topo das
      paredes; acima do plano de corte só o beiral aparece e ele escolhe a cobertura.
- [x] **CB15** Uma água por retângulo com clique no lado mais baixo; duas águas em L é
      recusada antes de pedir o lado.
- [x] **CB16** Painel: inclinação e forma editáveis (as peças se mantêm quando a
      quantidade de águas não muda); a ferramenta Laje não lista os tipos de cobertura.
- [x] **CB17** 3D: a cobertura é uma malha só (as águas juntas), escolhida pelo clique e
      refeita quando a forma muda.

## 11. Fontes públicas
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

## 12. Fora do escopo / pendências
Implementado em 2026-10-16 (`brasbim/core/structure/roofs.py`, `tests/test_cobertura.py`,
`tests/test_interface_cobertura.py`). A água de cada lado é o plano mais baixo naquele
ponto; num contorno convexo, isso já dá cumeeira e espigões sem esqueleto reto.

- **V1:** telhados de forma livre em qualquer contorno (L, T, com várias cumeeiras, por
  esqueleto reto); mansarda, borboleta, meia-água encostada; beiral diferente por lado;
  águas com inclinações diferentes; ajuste e recorte automáticos das paredes sob o
  telhado (oitão, RF-ELE-17); platibanda; madeiramento (tesouras, terças, caibros e
  ripas como `IfcBeam`/`IfcMember`); calhas e rufos; claraboias e aberturas; beiral
  com corte vertical; verificação da inclinação mínima por telha.
- **Pontos de revisão:**
  (a) peças no plano da água, com o beiral em esquadro (§2.2);
  (b) altura de apoio pela **face de baixo** sobre o contorno de apoio, com o beiral
      descendo (§3.1);
  (c) a projeção tracejada da cobertura na planta do pavimento de baixo (§7);
  (d) paredes sem ajuste automático no MVP (§6);
  (e) biblioteca e espessuras dos tipos (§3.2);
  (f) cobertura no pavimento ativo; quem quiser uma "planta de cobertura" cria um
      pavimento acima das paredes (§7).
