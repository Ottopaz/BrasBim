---
elemento: Porta
entidade_ifc: IfcDoor (PredefinedType e OperationType via IfcDoorType)
requisito: RF-ELE-05
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-14
status: aprovado
revisor: OTTO (aprovado em 2026-10-14)
---

# Porta

Esta spec define também o que é **comum às esquadrias** (porta e janela): posição na
parede, alinhamento na espessura, variantes de mão, operações e exclusão em cascata.
A spec da janela (`janela.md`) remete a estas seções e trata só do que é diferente.
As seções comuns estão marcadas com **(comum)**.

## 1. Propósito
Elemento que fecha um vão e controla a passagem de pessoas, cargas ou veículos. É
formado por um marco (batente) e uma ou mais folhas que giram, correm ou dobram.
[IFC-DOOR] No MVP a porta fica sempre num vão de parede (RF-ELE-01 §6.3).

## 2. Mapeamento IFC

### 2.1 Entidade e tipo
- Ocorrência: `IfcDoor`. Tipo: `IfcDoorType` via `IfcRelDefinesByType` (RF-TIP-01).
  `PredefinedType` e `OperationType` ficam no tipo; na ocorrência ficam vazios.
  [IFC-DOOR, *CorrectPredefinedType*; `OperationType` da ocorrência só se usa sem tipo]
- `IfcDoorType.ParameterTakesPrecedence = TRUE`: os parâmetros de marco e folhas
  definem a geometria (substitui o antigo `IfcDoorStandardCase`). [IFC-DOOR, IFC-DOORTYPE]
- `IfcDoorTypeEnum` no MVP: `DOOR`. `GATE` (portão), `TRAPDOOR` (alçapão, depende da
  laje) e os demais ficam para V1. [IFC-DOORENUM]
- `IfcDoorTypeOperationEnum` oferecidos no MVP, com nome em pt‑BR *(CG)*:

| Nome no BrasBim | `OperationType` | Folhas |
|---|---|---|
| Giro, 1 folha | `SINGLE_SWING_LEFT` / `_RIGHT` | 1 |
| Giro, 2 folhas | `DOUBLE_DOOR_SINGLE_SWING` | 2 |
| Giro com folha fixa | `SWING_FIXED_LEFT` / `_RIGHT` | 1 móvel + 1 fixa |
| Vaivém, 1 folha | `DOUBLE_SWING_LEFT` / `_RIGHT` | 1 |
| Vaivém, 2 folhas | `DOUBLE_DOOR_DOUBLE_SWING` | 2 |
| Correr, 1 folha | `SLIDING_TO_LEFT` / `_RIGHT` | 1 |
| Correr, 2 folhas | `DOUBLE_DOOR_SLIDING` | 2 |
| Camarão (dobrável), 1 folha | `FOLDING_TO_LEFT` / `_RIGHT` | 1 |
| Camarão, 2 folhas | `DOUBLE_DOOR_FOLDING` | 2 |
| Enrolar | `ROLLINGUP` | 1 |
| Só marco (vão com batente, sem folha) | `NOTDEFINED` | 0 |

  Fonte dos valores e do significado: [IFC-DOOROP]. Pivotante, giratória, basculante
  de garagem e as opções `LIFTING_*`/`REVOLVING*` ficam para V1 (pivotante não tem
  valor próprio no IFC e exigiria `USERDEFINED`).

### 2.2 Mão (lado das dobradiças) e sentido de abertura **(comum)**
O IFC separa duas informações independentes: [IFC-DOOR, IFC-DOOROP]
- **Sentido de abertura**: a folha abre sempre para o **+y local da ocorrência**.
  Abrir para o outro lado = girar o posicionamento da porta 180° em torno de z.
- **Mão**: `..._LEFT` = dobradiças à esquerda **de quem olha no sentido +y**, ou seja,
  de quem está do lado oposto ao da abertura e empurra a folha. Fica no **tipo**.

No BrasBim o usuário escolhe as duas coisas na própria porta: "abre para a face
esquerda/direita da parede" e "dobradiças à esquerda/direita (vista de quem empurra)".
Como a mão fica no tipo, cada tipo de porta com mão tem duas **variantes** de
`IfcDoorType`, iguais exceto pelo `OperationType` (`_LEFT`/`_RIGHT`) e pelo nome (sufixo
" (E)"/" (D)"). A variante que falta é criada quando alguém precisa dela. Trocar a mão de
uma porta = trocar o tipo dela pela variante. As variantes se reconhecem pela propriedade
`Variante` de `BrasBim_EsquadriaTipo` (§3.4). Tipos sem mão (2 folhas simétricas,
enrolar, só marco) não têm variante. *(decisão do projeto, **ponto de revisão**)*

Não se usam os termos "porta esquerda/direita" sozinhos na interface, porque cada país
os define de um jeito (o IFC avisa disso). [IFC-DOOR]

### 2.3 Representações
| Identificador | Tipo | Conteúdo |
|---|---|---|
| `Profile` (contexto `Model`) | `Curve3D` | `IfcPolyline` fechada, retângulo `OverallWidth × OverallHeight` no plano xz local (y = 0). Exigida para porta paramétrica. [IFC-DOOR, *Profile 3D Geometry*] |
| `Body` (contexto `Model`) | `SweptSolid` | Marco, guarnições, soleira e folhas como `IfcExtrudedAreaSolid` (um por peça), gerados dos parâmetros (§6.2). *(decisão do projeto)* |

- Geometria **na ocorrência**, não em `RepresentationMaps` do tipo, porque depende da
  largura, da altura e da espessura da parede de cada porta. *(decisão do projeto)*
- `FootPrint` (símbolo 2D com o arco de giro) não é gravado no MVP; a planta é gerada do
  modelo (§7). V1. [IFC-DOOR cita `FootPrint` como comum, não obrigatório]
- `ObjectPlacement` **(comum)**: `IfcLocalPlacement` relativo ao posicionamento do
  `IfcOpeningElement` que a porta preenche. [IFC-DOOR, *Product Local Placement*]
  Detalhes em §6.1.

### 2.4 Material
`IfcMaterialConstituentSet` no tipo, por `IfcRelAssociatesMaterial`, com constituintes
de nome `Lining` (marco), `Framing` (folhas; se faltar, vale o do marco) e, se houver
vidro, `Glazing`. [IFC-DOOR, *Material Set*] As cores e hachuras vêm do material
(RF-TIP-03).

### 2.5 Parâmetros de marco e folhas (no tipo)
- `IfcDoorLiningProperties` (1 por tipo) e `IfcDoorPanelProperties` (1 por folha), em
  `IfcDoorType.HasPropertySets`. [IFC-DLP, IFC-DPP]
- No IFC 4.3.2.0 (esquema `IFC4X3_ADD2`, o que o BrasBim grava) essas entidades estão
  **descontinuadas** (*deprecated*) em favor de `Pset_DoorLiningProperties` e
  `Pset_DoorPanelProperties`. [IFC-DLP, IFC-DPP, IOS-PSET] Um Pset só pode aparecer uma
  vez por objeto, então não descreve as duas folhas de uma porta de 2 folhas no mesmo
  tipo. **Decisão proposta:** gravar as entidades (válidas no esquema, lidas pela maioria
  dos programas, aceitam N folhas) e, ao ler, aceitar também os Psets. **Ponto de
  revisão.**

### 2.6 Propriedades e quantidades
- `Pset_DoorCommon` (§3.3). [IFC-PSET-D]
- `Qto_DoorBaseQuantities` (§8). [IFC-QTO-D]
- Pset próprio `BrasBim_Esquadria` na ocorrência e `BrasBim_EsquadriaTipo` no tipo
  (§3.4).

### 2.7 Relações **(comum)**
| Relação | Uso |
|---|---|
| `IfcRelFillsElement` | `IfcOpeningElement` → `IfcDoor` (1:1). [IFC-RFE] |
| `IfcRelVoidsElement` | Parede → `IfcOpeningElement` (spec da parede §6.3). |
| `IfcRelContainedInSpatialStructure` | Porta contida **no mesmo pavimento da parede**, mesmo preenchendo uma abertura (o IFC exige as duas relações). [IFC-DOOR, *Spatial Containment*] |
| `IfcRelDefinesByType` | Porta → `IfcDoorType`. |
| `IfcRelDefinesByProperties` | Psets e `IfcElementQuantity`. |

## 3. Parâmetros

### 3.1 Ocorrência
| Parâmetro | Tipo | Unidade | Padrão | Regras |
|---|---|---|---|---|
| Tipo | ref. `IfcDoorType` | — | último usado | Define operação, mão, marco e folhas |
| Largura do vão | real | m | do tipo (§3.4) | > 0; = `OverallWidth` = largura da abertura |
| Altura do vão | real | m | do tipo | > 0; = `OverallHeight` = altura da abertura |
| Distância ao início da parede | real | m | — | Ao longo do caminho, até o começo do vão (abertura §6.3) |
| Base | real | m | 0,00 | Em relação à base da parede (= `sill` da abertura) |
| Abre para | enum `face esquerda` \| `face direita` | — | lado do cursor na criação | Face da parede (em relação ao sentido dela) para onde a folha abre |
| Dobradiças | enum `esquerda` \| `direita` | — | `esquerda` | Vista de quem empurra a folha; escolhe a variante do tipo (§2.2) |
| Alinhamento na espessura | enum `face esquerda` \| `eixo` \| `face direita` | — | `eixo` | Referência para posicionar o marco (§6.1) |
| Deslocamento | real | m | 0,00 | A partir da referência, para dentro da parede |

Largura, altura, distância e base são **da abertura** (`opening.*`); a porta copia
largura e altura em `OverallWidth`/`OverallHeight` (§6.1). *(decisão do projeto)*

### 3.2 Tipo
| Parâmetro | Atributo IFC | Padrão | Regras |
|---|---|---|---|
| Nome | `IfcDoorType.Name` | — | Único entre tipos de porta |
| Operação | `OperationType` | `SINGLE_SWING_LEFT` | Tabela de §2.1 |
| Espessura do marco | `LiningThickness` | 0,03 m | ≥ 0; 0 = sem marco |
| Profundidade do marco | `LiningDepth` | vazio | Vazio = acompanha a espessura da parede [IFC-DLP] |
| Guarnição (largura × espessura) | `CasingThickness`, `CasingDepth` | 0,05 × 0,01 m | As duas ou nenhuma (WR34) [IFC-DLP] |
| Soleira (espessura) | `ThresholdThickness` | 0 (sem soleira) | Profundidade acompanha a parede |
| Bandeira (altura e espessura da travessa) | `TransomOffset`, `TransomThickness` | sem bandeira | V1 (vidro acima da folha) |
| Espessura da folha | `PanelDepth` | 0,035 m | > 0 |
| Proporção de cada folha | `PanelWidth` | 1 / n | Soma = 1 |
| Folga entre marco e folha | `LiningToPanelOffsetX/Y` | 0 | — |
| Materiais | constituintes `Lining`/`Framing`/`Glazing` | madeira | §2.4 |

Valores padrão: conhecimento geral de portas de madeira no Brasil *(CG, a revisar)*.

### 3.3 `Pset_DoorCommon` (MVP)
| Propriedade | Tipo IFC | Padrão | Observação |
|---|---|---|---|
| `Reference` | IfcIdentifier | código do tipo (ex.: `P1`) | Usado nas etiquetas e na tabela de esquadrias (RF-QTD-03) |
| `Status` | `PEnum_ElementStatus` | `NEW` | Como na parede |
| `IsExternal` | IfcBoolean | falso | Inferido em V1 (RF-AMB-01); editável |
| `HandicapAccessible` | IfcBoolean | vazio | Verificação NBR 9050 em V1 (§6.5) |
| `FireExit`, `SelfClosing`, `SmokeStop`, `FireRating`, `AcousticRating`, `SecurityRating`, `ThermalTransmittance`, `GlazingAreaFraction`, `HasDrive` | conforme [IFC-PSET-D] | vazio | Só gravadas se preenchidas |

### 3.4 Psets próprios **(comum)**
Prefixo `Pset_` é reservado à buildingSMART, como na parede. *(decisão do projeto)*

| Pset | Onde | Propriedade | Conteúdo |
|---|---|---|---|
| `BrasBim_Esquadria` | ocorrência | `Alinhamento` | `face_esquerda` \| `eixo` \| `face_direita` |
| | | `Deslocamento` | m |
| `BrasBim_EsquadriaTipo` | tipo | `LarguraPadrao`, `AlturaPadrao`, `BasePadrao` | m; usados ao inserir |
| | | `Variante` | GlobalId do tipo com a outra mão (vazio se não houver) |

O sentido de abertura não precisa de propriedade: é lido da rotação do posicionamento.
Porta sem `BrasBim_Esquadria` (IFC de outra origem) é tratada como em §6.6.

### 3.5 Biblioteca inicial (RF-TIP-06)
Exemplos a revisar *(CG)*: giro 1 folha com folha de 0,60 / 0,70 / 0,80 / 0,90 × 2,10 m
(o vão soma 2 × espessura do marco na largura e 1 × na altura); giro 2 folhas 1,20 ×
2,10; correr 1 folha 0,80 × 2,10; correr 2 folhas 1,60 × 2,10; camarão 0,80 × 2,10.

## 4. Criação (interação do usuário)
1. Usuário escolhe o tipo de porta (paleta/painel de propriedades).
2. Passa o cursor sobre uma parede reta: a pré‑visualização mostra a porta no ponto mais
   próximo do caminho, com o arco de giro do lado em que está o cursor.
3. Referência de inserção: centro do vão (padrão), lado esquerdo ou lado direito.
   *Snap* ao meio da parede, aos cantos e às faces de paredes que chegam (com cota
   temporária de distância); entrada numérica da distância (RF-DES-02, RF-DES-04).
4. Clique fixa a posição. O lado do cursor em relação à parede define "abre para"; a
   tecla de alternar (a definir na UI) troca as dobradiças antes do clique.
5. Uma transação **(comum)**: `opening.create` → (`door_type.create` da variante, se
   faltar) → `door.create` → `filling.attach`.
6. Porta que não cabe (fora dos limites da parede, altura maior que a da parede) é
   recusada com aviso. Sobreposição com outra abertura gera aviso, como na parede.
   Parede em arco: recusada (aberturas em arco são V1 na spec da parede).

## 5. Edição

### 5.1 Interações **(comum, com as diferenças indicadas)**
- Alças: mover ao longo da parede (ponto central), largura (laterais), altura (topo).
- Mover para outra parede (arrastar sobre ela): a abertura troca de parede
  (`opening.edit` com `wall`); a porta muda de pavimento se a parede for de outro.
- Inverter sentido de abertura: só muda o posicionamento (`door.edit`, `opens_to`).
- Inverter dobradiças: troca o tipo pela variante (§2.2), criando‑a se preciso.
- Trocar o tipo; editar alinhamento e deslocamento; editar Psets.
- Copiar/mover/espelhar a parede leva a porta junto (ela é relativa à abertura).
  Espelhar a parede preserva o lado físico da abertura e das dobradiças: o comando gera
  os `door.edit`/troca de variante necessários.
- Editar o tipo (`door_type.edit`) atualiza todas as portas dele (RF-TIP-01).

### 5.2 Operações serializáveis (RF-NUC-02)
Formato geral de `spec/01-modelo-de-dados.md`. Propostas:

| `op` | Dados |
|---|---|
| `door_type.create` / `.delete` | `name`, `predefined_type`, `operation_type`, `lining` (§3.2), `panels[]` (`operation`, `position`, `width`, `depth`), `materials`, `defaults` (`width`, `height`, `base`), `variant` |
| `door_type.edit` | campos alterados (antes/depois) |
| `door.create` / `.delete` | `name`, `type`, `opens_to` (`left` \| `right`), `align` (`left_face` \| `axis` \| `right_face`), `offset`, `common` (Pset_DoorCommon diferente do padrão) |
| `door.edit` | campos de `door.create` alterados (antes/depois) |
| `opening.*`, `filling.*` | já existentes (spec da parede §5.2) |

- `door.create` cria a porta sem posição; posição, `OverallWidth/Height`, contenção
  espacial e corpo são **efeitos derivados** do `filling.attach` e da abertura,
  recalculados depois de cada operação, como o corpo da parede. *(decisão do projeto)*
- Por isso uma porta pode existir sem abertura dentro de uma transação, mas o comando
  nunca termina uma transação deixando a porta solta (porta independente é V1).
- Reserva (RF-COL-02): editar a porta exige reservar a porta; mover ou redimensionar
  exige também a parede (a abertura é parte dela).

## 6. Comportamento e regras geométricas

### 6.1 Posição **(comum)**
Coordenadas no sistema da abertura, que tem origem no começo do vão, x ao longo da
parede, y = y da parede (+y à esquerda de quem percorre a parede) e z a partir da base
do vão. `ymin`/`ymax` = faces direita/esquerda da parede; `d` = profundidade do marco
(`LiningDepth`, ou espessura da parede se vazio).

1. Faixa do marco na espessura, `[a, a + d]`:
   - `face esquerda`: `a = ymax − deslocamento − d`
   - `eixo`: `a = (ymin + ymax − d) / 2 + deslocamento`
   - `face direita`: `a = ymin + deslocamento`
2. Abre para a face esquerda: posicionamento em `(0, a, 0)`, sem rotação (+y da porta =
   +y da parede). Abre para a face direita: posicionamento em `(largura, a + d, 0)`,
   girado 180° em z (+x da porta = −x da parede, +y da porta = −y da parede).
3. Em ambos os casos o marco ocupa `y ∈ [0, d]` no sistema da porta, e
   `LiningOffset = 0` no tipo: a posição fica no posicionamento, como o IFC permite.
   [IFC-DLP, nota sobre *LiningOffset*]
4. Marco mais profundo que a parede: aviso (o marco sobra para fora). *(decisão do
   projeto)*

Quando a parede muda (espessura, tipo, inverter camadas) ou a abertura muda (posição,
tamanho), o posicionamento e o corpo da porta são recalculados, sem mudar `GlobalId`.

### 6.2 Corpo
- Marco: três peças (laterais e superior) de seção `LiningThickness × d`, por dentro do
  retângulo do `Profile`. Soleira, se houver, na base. [IFC-DLP, *Figure 229*]
- Guarnição: peças de `CasingThickness × CasingDepth` nas duas faces da parede, por
  fora do vão. [IFC-DLP]
- Folhas: placas de espessura `PanelDepth`, com largura conforme `PanelWidth`, desenhadas
  **fechadas** no 3D, encostadas ao lado do marco para onde a folha abre (de giro) ou
  na face de abertura (de correr, sobre o trilho). *(CG)*
- Porta "só marco" (`NOTDEFINED`): só marco e guarnição. [IFC-DOOROP]
- Se a abertura sair da parede (aviso da spec da parede §6.3), a porta continua sendo
  desenhada na posição gravada.

### 6.3 Relação com a parede **(comum)**
- A porta não altera o corpo da parede: o vão vem do `IfcOpeningElement` (spec da parede
  §6.3). A abertura tem sempre `PredefinedType = OPENING` e o mesmo tamanho do vão da
  porta.
- Dividir a parede: a abertura vai para a parte que a contém (spec da parede §5.1) e a
  porta vai junto; a contenção espacial é recalculada.
- Mudar o pavimento da parede muda a contenção da porta.

### 6.4 Exclusão **(comum)**
- Excluir a porta: `filling.detach` → `door.delete` → `opening.delete`, numa transação.
  A abertura criada para a porta sai com ela. Quem quiser manter o vão vazio usa a ação
  "remover esquadria e manter vão" (só `filling.detach` + `door.delete`).
- Excluir a parede: a cascata de `spec/01-modelo-de-dados.md` §4 passa a incluir o
  elemento que preenche: `filling.detach` → `door.delete` → `opening.delete` →
  `path_connection.delete` → `wall.delete`, com confirmação (spec da parede §6.4). Isto
  resolve a pendência de `01-modelo-de-dados.md` §5.
- Excluir um tipo usado por portas é recusado (RF-TIP-01).

### 6.5 Acessibilidade (V1, RF-BR-03)
Verificação do vão livre (largura útil com a folha aberta) contra o mínimo da NBR 9050
(0,80 m, segundo fontes secundárias; **a confirmar no texto da norma**) e preenchimento
automático de `HandicapAccessible`. Não faz parte do MVP.

### 6.6 IFC de outra origem **(comum)**
- Porta sem `BrasBim_Esquadria` ou com tipo `ParameterTakesPrecedence ≠ TRUE`: o corpo
  original é **preservado** (não regenerado) e a porta é gravada de volta sem perda.
  Pode‑se mover (com a abertura), trocar Psets e excluir; mudar tamanho ou tipo
  converte para porta paramétrica do BrasBim, com aviso.
- Porta sem tipo, com `OperationType` na ocorrência: lida normalmente; ao editar, o
  BrasBim cria um tipo com aqueles valores. [IFC-DOOR, atributo `OperationType`]
- Tipo com `Pset_DoorLiningProperties`/`Pset_DoorPanelProperties` em vez das entidades:
  lido (§2.5).

## 7. Representação 2D **(comum, com símbolos próprios da porta)**
Gerada do modelo (RF-DOC-01/02). Convenções gerais do desenho arquitetônico brasileiro
*(CG)*; conferência com a NBR 6492 fica pendente, como na parede.

| Vista | Desenho |
|---|---|
| Planta | Vão interrompe a parede; marco cortado. Folha de giro desenhada aberta a 90° e arco de giro em linha fina; vaivém com arco dos dois lados; correr com as folhas no trilho e seta; camarão em zigue‑zague; enrolar com linha tracejada do rolo. |
| Corte | Marco e folha cortados; verga da parede acima. |
| Fachada/vista | Contorno do marco, folhas e guarnição; símbolo de abertura opcional (linhas convergindo para o lado das dobradiças), com convenção configurável. |

- **Níveis de detalhe** (RF-DOC-08): 1:100 ou menor, marco simplificado (sem guarnição)
  e folha como linha; 1:50 ou maior, marco, guarnição e folha com espessura.
- **Etiqueta:** código (`Reference`, ex.: `P1`) e, opcional, "largura × altura" do vão.
  Formato configurável. *(CG)*
- Nada de 2D é gravado no IFC no MVP (§2.3).

## 8. Quantitativos
`Qto_DoorBaseQuantities`, recalculado a cada alteração. [IFC-QTO-D]

| Quantidade | Cálculo |
|---|---|
| `Width` | Largura do vão (`OverallWidth`) |
| `Height` | Altura do vão (`OverallHeight`) |
| `Area` | `Width × Height` |
| `Perimeter` | `2 × (Width + Height)` (retângulo externo do marco, como diz a definição) |

O IFC define essas medidas pelo contorno externo do marco, que no BrasBim coincide com o
vão. A guarnição fica fora. *(decisão do projeto)* A tabela de esquadrias (RF-QTD-03)
agrupa por tipo + dimensões e conta as unidades.

## 9. Critérios de aceite (testes)
Todos verificam o IFC gravado e relido com `ifcopenshell.open`. Base: parede reta de
5 m, 14 cm, 2,80 m de altura.

- [ ] **PO01** Porta de giro 1 folha, vão 0,86 × 2,13, a 1,00 m do início: 1 `IfcDoor`
      com `OverallWidth = 0,86` e `OverallHeight = 2,13`; 1 `IfcOpeningElement`
      (`OPENING`, mesmas dimensões); `IfcRelVoidsElement` e `IfcRelFillsElement` 1:1;
      porta contida no mesmo pavimento da parede.
- [ ] **PO02** Tipo: `IfcDoorType` com `PredefinedType = DOOR`, `OperationType =
      SINGLE_SWING_LEFT`, `ParameterTakesPrecedence = TRUE`; ocorrência com
      `PredefinedType` e `OperationType` vazios.
- [ ] **PO03** Tipo com 1 `IfcDoorLiningProperties` (`LiningDepth` vazio,
      `LiningThickness = 0,03`) e 1 `IfcDoorPanelProperties` (`SWINGING`); tipo de
      2 folhas: 2 `IfcDoorPanelProperties` (`LEFT`/`RIGHT`) com `PanelWidth` somando 1.
- [ ] **PO04** `PlacementRelTo` = posicionamento da abertura. Abre para a face esquerda:
      +y da porta = +y da parede. Abre para a direita: origem em x = largura e +y da
      porta = −y da parede.
- [ ] **PO05** `Profile`: `IfcPolyline` fechada, retângulo 0,86 × 2,13 no plano xz,
      y = 0.
- [ ] **PO06** `Body`: caixa envolvente do marco com profundidade 0,14 (a da parede);
      trocar a parede para o tipo de 19 cm recalcula o corpo (profundidade 0,19) sem
      mudar `GlobalId` da porta.
- [ ] **PO07** Alinhamento: tipo com `LiningDepth = 0,07` e `face esquerda`,
      deslocamento 0,02 → faixa do marco `[ymax − 0,09, ymax − 0,02]` (§6.1).
- [ ] **PO08** Inverter dobradiças: a porta passa à variante `SINGLE_SWING_RIGHT`
      (criada uma única vez; a segunda inversão reaproveita a variante); nada mais muda.
- [ ] **PO09** Inverter sentido: só o posicionamento muda; o tipo é o mesmo.
- [ ] **PO10** Mover a porta para 2,00 m: `opening.edit`; a porta acompanha;
      `NetSideArea` da parede não muda. Mover para fora da parede é recusado pelo
      comando.
- [ ] **PO11** Mover para outra parede de outro pavimento: `IfcRelVoidsElement` e
      contenção espacial atualizados.
- [ ] **PO12** `Qto_DoorBaseQuantities`: `Width`, `Height`, `Area = 0,86 × 2,13`,
      `Perimeter = 2 × (0,86 + 2,13)`.
- [ ] **PO13** `Pset_DoorCommon` com `Status = NEW` e `Reference` do tipo;
      `BrasBim_Esquadria` e `BrasBim_EsquadriaTipo` conforme §3.4.
- [ ] **PO14** Excluir a porta: sem `IfcDoor`, `IfcOpeningElement`, `IfcRelFillsElement`
      nem `IfcRelVoidsElement` órfãos; `NetSideArea` da parede volta ao bruto.
      "Remover esquadria e manter vão" deixa a abertura.
- [ ] **PO15** Excluir a parede com porta: a transação contém, em ordem,
      `filling.detach`, `door.delete`, `opening.delete`, `path_connection.delete`,
      `wall.delete`; desfazer restaura os mesmos `GlobalId`s.
- [ ] **PO16** Dividir a parede depois da porta: a porta fica na parte que a contém,
      com posição física inalterada.
- [ ] **PO17** Cada ação gera as operações de §5.2; desfazer/refazer e reaplicar o
      diário num modelo vazio reproduzem o mesmo IFC.
- [ ] **PO18** IFC de outra origem (porta com `Body` próprio, sem `BrasBim_Esquadria`):
      corpo preservado na regravação; mover funciona; redimensionar avisa e converte.
- [ ] **PO19** Porta em parede em arco: recusada com mensagem.
- [ ] **PO20** Arquivo passa na validação de esquema do IfcOpenShell.

## 10. Fontes públicas
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

## 11. Fora do escopo / pendências
- V1: porta independente (sem parede) e em parede em arco; portão, alçapão; pivotante,
  giratória, basculante de garagem; bandeira; `FootPrint` gravado; verificação NBR 9050;
  `IsExternal` inferido.
- V2: porta em fachada‑cortina (`IfcRelAggregates`).
- Pontos de revisão, aceitos pelo revisor em 2026‑10‑14: (a) gravar `IfcDoorLiningProperties`/`IfcDoorPanelProperties`
  (descontinuadas no 4.3.2) em vez dos Psets (§2.5); (b) variantes de tipo por mão
  (§2.2); (c) excluir a porta exclui a abertura (§6.4); (d) dimensões do vão como
  parâmetro principal, e não da folha (§3.1, §3.5); (e) nomes dos Psets próprios;
  (f) símbolos e etiquetas frente à NBR 6492.
