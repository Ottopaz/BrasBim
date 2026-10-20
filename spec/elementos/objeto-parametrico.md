---
elemento: Objeto paramétrico (definição, tipos e ocorrências) e biblioteca de objetos
entidade_ifc: IfcFurnitureType / IfcSanitaryTerminalType / IfcElectricApplianceType / IfcGeographicElementType (tipos) + IfcFurniture / IfcSanitaryTerminal / IfcElectricAppliance / IfcGeographicElement (ocorrências), via IfcRelDefinesByType
requisito: RF-TIP-01, RF-TIP-04, RF-TIP-05 (parcial), RF-TIP-06 (básica), RF-TIP-07 (parcial), RF-ELE-14
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-20
status: em revisão
revisor: OTTO
---

# Objeto paramétrico (pacote 13)

Na interface, o recurso se chama **objeto paramétrico**. Nos menus e botões aparece só
**Objeto** (decisão do revisor, 2026-10-20). No código o nome é `objects`
(`core/objects/`).

## 1. Propósito
Um objeto paramétrico é uma peça de projeto reutilizável, como uma cama, uma bacia
sanitária, uma geladeira ou uma árvore. A forma dele é descrita **uma vez**, em função de
parâmetros, e é usada muitas vezes no projeto com medidas diferentes. O revisor pediu
que funcione como as famílias do Revit. Daquele programa veio **só a função**, descrita
com palavras próprias a partir da ajuda pública (§10): tipos com valores próprios,
ocorrências que herdam do tipo, parâmetros de tipo e de ocorrência, fórmulas,
visibilidade condicional, objetos dentro de objetos e carregar ou trocar tipos no
projeto.

Três níveis, com os nomes do IFC:

| Nível | O que é | Exemplo | No IFC |
|---|---|---|---|
| **Definição** | Parâmetros, fórmulas, peças 3D e símbolo 2D | "Cama" | JSON no Pset `BrasBim_DefinicaoObjeto` de cada tipo (§2.2) |
| **Tipo** | Uma definição com um conjunto de valores dos parâmetros de tipo | "Cama casal 1,38 × 1,88" | `IfcFurnitureType` (ou outra classe da §2.1) |
| **Ocorrência** | Um exemplar posto no projeto, com posição e os parâmetros de ocorrência | a cama do quarto 1 | `IfcFurniture` ligada ao tipo por `IfcRelDefinesByType` |

Mudar um valor do **tipo** muda todas as ocorrências dele. Mudar um valor da
**ocorrência** muda só aquele exemplar. Mudar a **definição** (no editor, §5.3) muda
todos os tipos dela e todas as ocorrências.

Entram na primeira versão: tipos, ocorrências, parâmetros de tipo e de ocorrência,
fórmulas entre parâmetros, parâmetros de escolha, visibilidade condicional, objetos
presos à parede (com vão opcional), objetos aninhados, editor por formulário com
prévia, biblioteca em arquivos, carregar e trocar tipos, e uma biblioteca inicial de
mobiliário, louças, eletrodomésticos e vegetação (decisões do revisor). O editor
gráfico com restrições e as outras extensões ficam para depois (§11).

Porta, janela, parede, laje, pilar e viga **continuam** com os tipos próprios. O objeto
paramétrico é um recurso novo e não substitui esses tipos no pacote 13 (ponto de
revisão (a)).

## 2. Mapeamento IFC

### 2.1 Classes
A definição diz qual é a **classe IFC** do objeto. A classe vale para todos os tipos e
ocorrências daquela definição.

| Categoria na interface | Tipo | Ocorrência | `PredefinedType` usados na biblioteca | Pset comum |
|---|---|---|---|---|
| Mobiliário | `IfcFurnitureType` | `IfcFurniture` | `BED`, `CHAIR`, `TABLE`, `DESK`, `SOFA`, `SHELF`, `FILECABINET`, `USERDEFINED` | `Pset_FurnitureTypeCommon` |
| Louças e metais | `IfcSanitaryTerminalType` | `IfcSanitaryTerminal` | `TOILETPAN`, `WASHHANDBASIN`, `SINK`, `SHOWER`, `BATH`, `URINAL`, `BIDET` | `Pset_SanitaryTerminalTypeCommon` |
| Eletrodomésticos | `IfcElectricApplianceType` | `IfcElectricAppliance` | `REFRIGERATOR`, `FRIDGE_FREEZER`, `ELECTRICCOOKER`, `MICROWAVE`, `WASHINGMACHINE`, `DISHWASHER`, `TUMBLEDRYER` | `Pset_ElectricApplianceTypeCommon` |
| Vegetação | `IfcGeographicElementType` | `IfcGeographicElement` | `VEGETATION` | `Pset_VegetationCommon` |
| Genérico | `IfcBuildingElementProxyType` | `IfcBuildingElementProxy` | `NOTDEFINED` | — |

- Com `USERDEFINED`, o `ElementType` do tipo leva o nome em português
  ("Criado-mudo"), como pede a regra *CorrectPredefinedType*. [IFC-FURN, IFC-GEO]
- O `PredefinedType` fica no **tipo**, e a ocorrência fica sem ele. A regra
  *CorrectTypeAssigned* exige que o tipo seja da classe certa: um `IfcFurniture` só
  recebe um `IfcFurnitureType`. [IFC-FURN, IFC-GEO]
- O Pset comum vai no tipo, com `Reference` = código do tipo (§3.4).
  `NominalLength`/`NominalDepth`/`NominalHeight` (mobiliário) e `NominalLength`/
  `NominalWidth`/`NominalDepth` (louças) vêm da caixa que envolve o objeto. Quando uma
  ocorrência tem medidas diferentes por causa de um parâmetro de ocorrência, ela ganha
  o mesmo Pset com os valores dela, e o valor da ocorrência vale sobre o do tipo
  (§2.3). `IsBuiltIn` é verdadeiro no objeto preso à parede (§6.3). [IFC-PSET-F,
  IFC-PSET-S]

### 2.2 Definição e valores
- **Definição:** JSON no Pset `BrasBim_DefinicaoObjeto` **de cada tipo**
  (`Parametros`, uma `IfcText`), como as tabelas e as camadas (spec/ui 17 e 18). Ela
  traz o código da definição (`object_id`, no formato do GlobalId, que continua o
  mesmo quando o objeto é renomeado), a versão (inteiro que sobe a cada gravação no
  editor), o nome, a categoria, a classe, os parâmetros, as peças, o símbolo 2D e a
  hospedagem (§3). Os tipos da mesma definição têm o mesmo JSON. O JSON repetido ocupa
  pouco espaço, e cada tipo pode ser lido ou levado para outro arquivo sozinho (ponto
  de revisão (b)).
- **Valores:** os parâmetros também são gravados como **propriedades IFC de
  verdade**. Assim outro programa lê "Largura = 1,38". Ficam no Pset
  `BrasBim_Parametros`:
  - no **tipo**: os parâmetros de tipo, incluindo os calculados por fórmula;
  - na **ocorrência**: os parâmetros de ocorrência, também com os calculados.
  O IFC já diz que, numa propriedade com o mesmo nome no tipo e na ocorrência, o valor
  da ocorrência prevalece. [IFC-TYPEOBJ] Por isso um programa qualquer que junte os
  dois Psets vê os valores certos daquele exemplar.
- Tipos IFC das propriedades: comprimento → `IfcPositiveLengthMeasure` ou
  `IfcLengthMeasure`; ângulo → `IfcPlaneAngleMeasure`; número → `IfcReal`; inteiro →
  `IfcInteger`; sim/não → `IfcBoolean`; texto → `IfcLabel`; escolha →
  `IfcPropertyEnumeratedValue` com `IfcPropertyEnumeration` (§3.1); material → `IfcLabel`
  com o nome do material; tipo de objeto → `IfcLabel` com o nome do tipo.
- O nome da propriedade é o **rótulo** do parâmetro ("Largura"), não o identificador
  usado nas fórmulas (`largura`).

### 2.3 Geometria: o corpo fica na ocorrência
- Pela regra do IFC, se o tipo tem `RepresentationMaps`, toda ocorrência precisa usar
  essas mesmas formas por `IfcMappedItem`, com no máximo uma transformação.
  [IFC-TYPEPROD; IfcOpenShell `assign_type`] Um parâmetro de ocorrência que muda a forma
  (o comprimento de uma bancada) não cabe nisso.
- Por isso o tipo do objeto paramétrico **não tem `RepresentationMaps`**, e cada
  ocorrência tem o próprio `Body`, gerado da definição com os valores dela, como já
  fazem a porta e a janela. `assign_type` é chamado com `should_map_representations =
  False`.
- `Body`: `IfcShapeRepresentation` `SweptSolid`. Caixa e extrusão viram
  `IfcExtrudedAreaSolid`, o cilindro é uma extrusão de `IfcCircleProfileDef` e a
  revolução é um `IfcRevolvedAreaSolid`. Cada peça é
  um item com `IfcStyledItem` do estilo do material dela (como as peças da porta,
  `materials.ensure_style`).
- `Annotation` (planta, `Plan`/`Annotation`): o símbolo 2D (§7), gravado como as
  anotações (`IfcGeometricCurveSet`, `IfcAnnotationFillArea`).
- `Box` (caixa que envolve) para a escolha rápida e para as medidas nominais.
- **Material:** `IfcMaterialConstituentSet` no tipo, com um constituinte por papel das
  peças. Os papéis de mobiliário seguem o IFC: `Frame` (estrutura), `Finish`
  (acabamento), `Hardware` (ferragens), `Padding` (estofado), `Panel` (vidro e
  painéis). Os de louça e eletrodoméstico são `Body` e `Finish`, e os de vegetação são
  `Trunk` e `Canopy`. [IFC-FURN] O material de uma peça pode ser parâmetro (§3.1). Nesse
  caso o constituinte do tipo leva o valor do tipo, e a ocorrência com outro material
  ganha o próprio `IfcMaterialConstituentSet`.

### 2.4 Posição, contenção e relações
- Contenção no pavimento (`IfcRelContainedInSpatialStructure`) e posicionamento em
  relação ao pavimento: ponto de inserção (x, y), **elevação** a partir do piso do
  pavimento e rotação em torno de z. Espelhar inverte o eixo x local (§5.2).
- **Preso à parede** (§6.3): o posicionamento é relativo ao da parede. Uma
  `IfcRelConnectsElements` liga o objeto à parede. Com vão, um `IfcOpeningElement` (`RECESS`
  ou `OPENING`) entra na parede por `IfcRelVoidsElement`, pelo mesmo caminho dos nichos
  (`walls/openings.py`), e o objeto **não** preenche o vão (sem `IfcRelFillsElement`,
  que é para porta e janela). [IFC-OPEN]
- **Aninhado** (§6.4): cada objeto de dentro é uma ocorrência de verdade (por exemplo,
  um `IfcFurniture` "Cadeira" com o próprio tipo). A ocorrência de fora o agrega por
  `IfcRelAggregates`, e ele é posicionado em relação a ela, sem contenção própria, como
  as águas da cobertura. [IFC-AGG] Assim as cadeiras da mesa aparecem nas tabelas como
  cadeiras.
- **Biblioteca em arquivo** (§4.1): `IfcProjectLibrary` declarada no projeto por
  `IfcRelDeclares`, com os tipos declarados nela também por `IfcRelDeclares`.
  [IFC-LIB]
- O tipo carregado de uma biblioteca guarda a origem por `IfcRelAssociatesLibrary` →
  `IfcLibraryReference` (nome do arquivo, `object_id` e versão). Assim *Atualizar da
  biblioteca* (§4.3) sabe de onde ele veio. [IFC-TYPEOBJ, *HasAssociations*]

### 2.5 Camadas (spec/ui 18)
Camada padrão por categoria, na chave `defaults` de `BrasBim_Camadas`, com
`object:furniture`, `object:sanitary`, `object:appliance`, `object:vegetation` e
`object:proxy`. Mobiliário vai para Interiores › Mobiliário e vegetação para
Entorno › Vegetação. Louças, eletrodomésticos e genéricos vão para uma camada nova,
Interiores › **Equipamentos**, criada na primeira vez em que é usada (ponto de revisão
(c)). O objeto aninhado segue a camada do objeto de fora.

## 3. Parâmetros

### 3.1 Parâmetros da definição
| Campo | Valores | Regras |
|---|---|---|
| Identificador | letras sem espaço, dígitos e `_` (`largura`, `n_cadeiras`) | Único na definição, começa por letra, sem diferenciar maiúsculas. É o nome usado nas fórmulas. Acentos são aceitos |
| Rótulo | texto ("Largura", "Nº de cadeiras") | Nome mostrado no painel e gravado no IFC. Único na definição |
| Tipo do valor | comprimento, ângulo, número, inteiro, sim/não, texto, escolha, material, tipo de objeto | **Escolha** traz a lista de opções (ex.: "redondo", "retangular"). **Tipo de objeto** traz a categoria aceita (§6.4) |
| Nível | **tipo** ou **ocorrência** | O de tipo é igual em todas as ocorrências do tipo. O de ocorrência pode mudar em cada exemplar |
| Valor ou fórmula | valor do tipo do parâmetro, ou `= expressão` (§3.2) | Com fórmula o parâmetro é **calculado**: aparece no painel sem poder ser editado |
| Limites | mínimo e máximo (opcionais) | Um valor fora dos limites é recusado com mensagem. Uma fórmula que dá um valor fora dos limites também é recusada |
| Grupo | Dimensões, Materiais, Visibilidade, Outros | Só organiza o painel |
| Alça | nenhuma, ou eixo (x, y, z) e lado (início, fim, simétrico) | Só para comprimento de ocorrência sem fórmula. Desenha a alça na planta (§5.1) |

Parâmetros que **toda** definição tem, criados sozinhos e com o nível fixo:

| Identificador | Rótulo | Nível | Padrão |
|---|---|---|---|
| `elevacao` | Elevação | ocorrência | 0 (ou o da definição) |
| `codigo` | Código | tipo | vazio. Vai para `Reference` (§3.4) |
| `descricao` | Descrição | tipo | vazio |

Rotação, espelho, posição e parede de apoio **não** são parâmetros: são o
posicionamento da ocorrência (§2.4).

### 3.2 Fórmulas
Linguagem própria, simples e **sem execução de código** (um analisador próprio em
`core/objects/formula.py`, sem `eval`):
- números com **vírgula decimal** (`0,60`) e argumentos separados por **ponto e
  vírgula**, como nas planilhas em português: `máx(largura - 2 * braco; 0,40)`;
- operadores `+ - * / ^`, parênteses, comparações `= <> < <= > >=` e `e`, `ou`,
  `não`;
- funções `se(condição; então; senão)`, `mín`, `máx`, `arred`, `arred_baixo`,
  `arred_cima`, `abs`, `raiz`, `sen`, `cos`, `tg` (em graus) e `pi()`. As funções
  também aceitam o nome sem acento (`min`, `max`);
- `sim`/`não` (também `verdadeiro`/`falso`) e texto entre aspas para comparar escolhas:
  `tampo = "redondo"`;
- **unidades:** comprimentos em metros, ângulos em graus. `n_cadeiras = arred_baixo(
  comprimento / 0,60) * 2`.

Regras:
- A fórmula pode usar parâmetros dos **dois** níveis. Um parâmetro de **tipo**, porém,
  só pode depender de outros parâmetros de tipo: senão o valor dele mudaria de um
  exemplar para outro. O editor recusa a fórmula com a mensagem "parâmetro de tipo não
  pode depender de parâmetro de ocorrência (comprimento)".
- O editor recusa ciclos ("largura → assento → largura"), nomes desconhecidos e tipos
  incompatíveis (texto onde se espera comprimento) ao gravar, apontando a linha.
- A avaliação segue a ordem das dependências. Um erro que só aparece com certos valores
  (divisão por zero, raiz de negativo, medida ≤ 0 numa peça) **recusa a operação** que
  levou a ele, com a mensagem da recusa (`OpError`). O modelo nunca fica com um objeto
  quebrado.
- Inteiro recebe o resultado arredondado. Sim/não aceita uma comparação.

### 3.3 Peças (geometria 3D)
A geometria é uma **lista de peças** no sistema local do objeto: origem no ponto de
inserção, x para a direita, y para trás (a "frente" do objeto olha para −y) e z para
cima. Cada medida é um número ou uma fórmula.

| Peça | Campos | IFC |
|---|---|---|
| Caixa | x, y, z do canto, largura (x), profundidade (y), altura (z), rotação em z | `IfcExtrudedAreaSolid` de `IfcRectangleProfileDef` |
| Cilindro | centro (x, y, z), raio, altura, eixo (z, x ou y) | `IfcExtrudedAreaSolid` de `IfcCircleProfileDef` |
| Extrusão | perfil (lista de pontos, cada coordenada uma fórmula) num plano (planta xy, frente xz, lado yz), deslocamento e espessura | `IfcExtrudedAreaSolid` de `IfcArbitraryClosedProfileDef` |
| Revolução | perfil no plano xz (pontos com x ≥ 0), ângulo (padrão 360°), centro | `IfcRevolvedAreaSolid` em torno do eixo z local |
| Objeto aninhado | tipo de objeto (fixo ou parâmetro "tipo de objeto"), posição, rotação, espelho e ligação de parâmetros (§6.4) | ocorrência agregada (§2.4) |

Todos os itens da lista também têm:
- **Material:** papel (§2.3) e material, fixo ou dado por um parâmetro do tipo
  material.
- **Visível quando:** fórmula de sim/não (vazio = sempre). A peça com a condição falsa
  não é gravada. Ex.: os braços do sofá têm `com_braco`, e a gaveta tem `n_gavetas >= 1`.
- **Repetir:** quantidade (fórmula inteira, 1 por padrão) e passo (dx, dy, dz) ou,
  no modo "distribuir", o comprimento total. Ex.: as prateleiras da estante, ou as
  cadeiras de um lado da mesa.
- **Vão na parede** (só nas definições presas à parede, §6.3): marca uma caixa como o
  volume do vão. Ela não entra no corpo do objeto.

As peças podem se sobrepor: o corpo é a reunião dos itens, sem booleano entre eles
(a escolha e as quantidades usam a caixa que envolve tudo).

### 3.4 Tipo
| Campo | Regras |
|---|---|
| Nome | Único entre os tipos da mesma classe. Padrão: nome da definição e as medidas principais ("Cama casal 1,38 × 1,88") |
| Código | `Reference` do Pset comum e etiqueta na planta (opcional, §7). Ex.: "M1", "L3" |
| Valores dos parâmetros de tipo | Um por parâmetro de tipo sem fórmula |
| Padrões dos parâmetros de ocorrência | O valor que a ocorrência nova recebe. A ocorrência guarda o próprio valor, e mudar o padrão do tipo não mexe nas ocorrências que já existem (ponto de revisão (d)) |

## 4. Criação (interação do usuário)

### 4.1 Biblioteca em arquivos
- Um **arquivo de biblioteca** é um `.ifc` com uma `IfcProjectLibrary` e os tipos
  declarados nela (§2.4), com as mesmas unidades do BrasBim (m, graus). Um arquivo pode
  ter **várias definições** e vários tipos de cada uma. Ex.: `mobiliario-quarto.ifc` traz
  Cama (4 tipos), Criado-mudo e Guarda-roupa (3 tipos).
- Como o tipo não tem geometria (§2.3), o arquivo também traz uma **ocorrência de
  amostra** por tipo, num pavimento "Amostras". Qualquer visualizador de IFC mostra o
  objeto, e a miniatura da biblioteca sai dela (ponto de revisão (e)).
- Pastas da biblioteca:
  1. a **biblioteca do BrasBim**, que vem com o programa (`brasbim/library/objetos/`,
     licença CC BY 4.0, §4.5) e só pode ser lida;
  2. as **pastas do usuário**, escolhidas em Projeto > Biblioteca de objetos… > Pastas
     (gravadas em `QSettings`). É nelas que se grava o objeto novo.
- Ao abrir a biblioteca, o BrasBim lê as pastas e guarda um índice em cache (nome,
  categoria, tipos, miniatura e data do arquivo). Ele só relê o arquivo que mudou.

### 4.2 Painel Biblioteca de objetos
Painel solto (Exibir > Painéis > Biblioteca de objetos, Ctrl+Shift+B), separado dos
outros como o painel Camadas:
- **Busca** pelo nome do objeto e do tipo. Abaixo dela, a árvore de **categorias**
  (Mobiliário › Quarto, Sala, Cozinha, Escritório; Louças e metais; Eletrodomésticos;
  Vegetação; e as pastas do usuário), com a pasta como subcategoria.
- Lista de objetos com **miniatura** (planta ou 3D, alternáveis) e, ao abrir um
  objeto, os tipos dele com as medidas.
- Um objeto já carregado no projeto aparece marcado, e um tipo com versão mais nova na
  biblioteca mostra "atualização disponível".
- **Clique duplo** num tipo (ou arrastar para a planta) carrega o tipo, se ainda não
  estiver no projeto, e ativa a ferramenta Objeto com ele (§4.4).
- Botão **Carregar no projeto**: carrega os tipos marcados (um ou vários) sem inserir
  nada.

### 4.3 Carregar, atualizar e levar para a biblioteca
- **Carregar** copia a definição e os tipos escolhidos para o projeto numa transação
  (`object_type.create`, um por tipo). Outra classe com o mesmo nome não conflita, e um
  tipo da mesma classe com nome repetido ganha " (2)". Carregar de novo um tipo que já
  está no projeto pergunta:
  *Manter o do projeto*, *Substituir pelo da biblioteca* (com os valores da biblioteca) ou
  *Carregar como novo tipo*.
- **Atualizar da biblioteca** (Objetos do projeto, §5.4): troca a **definição** pela
  da biblioteca em todos os tipos daquela definição e **mantém os valores** de cada tipo
  e de cada ocorrência quando o parâmetro tem o mesmo identificador e o mesmo tipo do
  valor. Parâmetro novo recebe o padrão, e parâmetro que sumiu sai dos Psets. A
  mensagem resume: "Cama: 2 tipos e 5 ocorrências atualizados; parâmetro 'cabeceira'
  novo (padrão sim)".
- **Gravar na biblioteca**: grava a definição e os tipos escolhidos num arquivo de uma
  pasta do usuário, novo ou existente. Na mesma definição (o mesmo `object_id`), a
  versão gravada substitui a anterior no arquivo. A biblioteca do BrasBim não pode ser
  gravada: para mudar um objeto dela, o usuário grava uma cópia na pasta dele.
- **Arquivo IFC qualquer** como biblioteca (RF-TIP-07, parcial): Projeto > Biblioteca
  de objetos… > *Carregar de um arquivo IFC…* lista os tipos de objeto do BrasBim que o
  arquivo tem, os que têm `BrasBim_DefinicaoObjeto`. Tipos de outra origem (sem a
  definição) ficam para o V1 (§11).

### 4.4 Ferramenta Objeto
No grupo Modelagem da barra Ferramentas, depois da Cobertura, com um ícone próprio
(uma cadeira estilizada, desenhada em `scripts/gerar_icones.py`).

Barra **Opções**:
- **Objeto e tipo:** um campo com busca que abre uma lista dos tipos **carregados no
  projeto**, agrupados por definição e categoria, com miniatura. No fim da lista,
  *Mais na biblioteca…* abre o painel (§4.2).
- **Rotação** (°), **Espelhar** (botão de alternar) e **Elevação** (m), com o padrão do
  tipo.
- **Parâmetros de ocorrência** do tipo, no máximo os três primeiros do grupo
  Dimensões. Os outros ficam em *Mais…*, um menu com o formulário. O exemplar seguinte
  sai com esses valores.
- **Camada** (spec/ui 18 §3.2).

Inserção do objeto **livre**:
1. O fantasma do objeto (símbolo 2D na planta, sólido no 3D) segue o cursor com snap
   ao ponto de inserção.
2. **Clique** põe o objeto com a rotação da barra. Barra de espaço gira o fantasma 90°
   antes do clique. **Tab** abre o quadro de medidas com *Rotação* (como Girar).
3. Com **Shift** + clique, um segundo clique dá a direção da frente (a rotação fica na
   direção do segundo ponto), com as linhas de 0/90° e o ponto de referência das
   outras ferramentas.
4. A ferramenta continua ativa para pôr outro. Esc encerra.
5. No 3D, o ponto é o da superfície atingida (elevação = altura da superfície em
   relação ao piso do pavimento quando o objeto cai sobre uma laje ou outro objeto;
   ponto de revisão (f)).

Inserção do objeto **preso à parede** (definição com hospedagem "parede", §6.3):
1. Perto de uma parede, o fantasma encosta na **face** mais próxima do cursor, com a
   frente para fora da parede. Longe de qualquer parede, não há fantasma e o cursor
   mostra "proibido".
2. **Tab** abre *Distância* (da ponta da parede ou do ponto de referência, como a
   porta) e *Altura* (= elevação).
3. Clique põe o objeto. Se ele tiver vão (§3.3), `openings.check_fits` confere se o
   vão cabe na parede, sem sair dela nem cair sobre outro vão. Se não couber, a
   inserção é recusada com a mensagem.

O objeto vai para a camada padrão da categoria (§2.5). Cada inserção é uma transação
"Inserir objeto" (`object.create`, e `opening.create` se houver vão).

### 4.5 Biblioteca inicial (CC BY 4.0)
Feita do zero no BrasBim, sem copiar objeto nenhum de outra biblioteca. As medidas são
as **usuais no mercado brasileiro** (CG), arredondadas, e entram como ponto de partida
(ponto de revisão (g)). A tabela usa "**(o)**" para parâmetro de ocorrência, "**(t)**"
para parâmetro de tipo e "**→**" para objeto aninhado.

| Categoria | Objeto | Tipos | Parâmetros de destaque |
|---|---|---|---|
| Mobiliário | Cama | solteiro 0,88 × 1,88; casal 1,38 × 1,88; queen 1,58 × 1,98; king 1,93 × 2,03 | largura, comprimento, altura do colchão (t); cabeceira sim/não (t) |
| | Criado-mudo | 0,45 × 0,40 | gavetas (inteiro, t) |
| | Guarda-roupa | 2, 3 e 4 portas | largura (o, com alça); portas de abrir/correr (escolha, t); altura (t) |
| | Sofá | 2 e 3 lugares | lugares (t) → largura por fórmula; com braço (t); profundidade (t) |
| | Poltrona | 1 | com braço (t) |
| | Mesa de jantar | 4, 6 e 8 lugares | tampo retangular/redondo (escolha, t); comprimento (o, com alça); `n_cadeiras` por fórmula; → Cadeira (tipo de objeto, t) |
| | Cadeira | 1 | altura do assento (t) |
| | Mesa de centro | 1 | comprimento, largura (t) |
| | Escrivaninha | 1,00 e 1,20 | gaveteiro sim/não (t) |
| | Estante | 0,80 e 1,20 | prateleiras (inteiro, t, repetição); largura (o, com alça) |
| | Armário de cozinha baixo | 0,40 / 0,60 / 0,80 | largura (o, com alça); portas (t) |
| | Armário de cozinha alto | 0,60 / 0,80 / 1,20 | **preso à parede**; altura de instalação = elevação (o) |
| Louças e metais | Bacia sanitária com caixa acoplada | comum; acessível | altura do assento (t; tipo acessível a conferir na NBR 9050) |
| | Lavatório | de coluna; suspenso (**preso à parede**) | largura (t) |
| | Bancada com cuba | banheiro; cozinha | comprimento (o, com alça); posição da cuba (o); espessura do tampo (t) |
| | Tanque | 1 | **preso à parede** |
| | Chuveiro com box | sem box; box de correr; box de abrir | largura e profundidade do box (o) |
| | Mictório | 1 | **preso à parede** |
| Eletrodomésticos | Geladeira | uma porta; duas portas; lado a lado | largura, profundidade, altura (t) |
| | Fogão | 4, 5 e 6 bocas | bocas (escolha, t) → largura |
| | Micro-ondas | 1 | — |
| | Máquina de lavar roupa | 1 | — |
| | Lava-louças | 1 | — |
| Vegetação | Árvore | pequena; média; grande | diâmetro da copa (o), altura (o), altura do tronco (t) |
| | Palmeira | 1 | altura (o) |
| | Arbusto | 1 | diâmetro (o) |
| | Vaso com planta | 1 | diâmetro do vaso (t) |

Cada objeto tem o símbolo 2D próprio (§7) e materiais da `materials.LIBRARY`, com os
materiais novos que precisar (Tecido, Louça, Inox, Folhagem, Madeira MDF branca).

## 5. Edição

### 5.1 Ocorrência
- **Mover, copiar, girar e espelhar** usam as ferramentas e transformações que já
  existem (`core/transform.py`), com o objeto como mais um caso, junto da estrutura.
  Espelhar inverte o x local (`Mirror`), sem trocar o tipo.
- **Painel de propriedades:**
  - **Tipo:** a lista dos tipos carregados **da mesma classe IFC** (com busca e
    miniatura). Trocar o tipo é a operação *trocar tipo* (§5.4).
  - **Posição:** elevação, rotação, espelhado e, no objeto preso à parede, distância e
    face.
  - **Parâmetros da ocorrência:** editáveis, nos grupos da definição. Os calculados
    aparecem em cinza, com a fórmula na dica (*tooltip*).
  - **Parâmetros do tipo:** só leitura, com o botão *Editar tipo…* (§5.4). A dica
    lembra que a mudança vale para as N ocorrências.
  - **Organização:** camada (spec/ui 18) e propriedades comuns.
  - Com vários objetos selecionados, aparecem os parâmetros que todos têm (o mesmo
    identificador e o mesmo tipo do valor) e "vários" onde os valores diferem.
- **Alças na planta:** o parâmetro de comprimento com alça (§3.1) ganha uma alça no lado
  indicado. Arrastar muda o valor, e Tab digita a medida. A alça simétrica muda o valor
  e mantém o centro. As alças vêm do `SelectTool`, como as da estrutura.
- **Mini-barra:** *Trocar tipo*, *Editar tipo…*, *Selecionar todos deste tipo*.

### 5.2 Operações (serializáveis)
| Operação | Faz |
|---|---|
| `object_type.create` / `.delete` | tipo com o estado completo: classe, `PredefinedType`, nome, código, definição (JSON), valores dos parâmetros de tipo, padrões dos de ocorrência, origem na biblioteca |
| `object_type.edit` | `before`/`after` dos campos do tipo, **incluindo a definição**. Mudar a definição é um `object_type.edit` para cada tipo dela, na mesma transação |
| `object.create` / `.delete` | ocorrência: tipo (GlobalId), pavimento, x, y, elevação, rotação, espelho, valores dos parâmetros de ocorrência, hospedagem (parede, face, distância), GlobalIds dos aninhados e do vão, Pset comum |
| `object.edit` | `before`/`after` dos campos da ocorrência |

- **Derivação** (`register_derive`): o tipo que mudou refaz todas as ocorrências dele.
  A parede que mudou refaz os objetos presos a ela (§6.3). A ocorrência refaz o corpo, o
  símbolo, os Psets de valores e os aninhados. Os GlobalIds dos aninhados ficam no estado
  e continuam os mesmos entre refazer e desfazer, como as águas da cobertura.
- Desfazer, refazer e o diário de sessão funcionam como nas outras operações.
- Na colaboração por reserva, editar o **tipo** ou a **definição** reserva o tipo e
  todas as ocorrências dele. Editar uma ocorrência reserva só ela.

### 5.3 Editor do objeto
Diálogo próprio. Abre com *Editar objeto…* (Objetos do projeto, ou o botão direito num
objeto) ou com *Novo objeto…* (em branco ou a partir de uma cópia). Organização da
tela, própria do BrasBim:

- **Coluna da esquerda, em abas:**
  - **Parâmetros:** tabela com identificador, rótulo, tipo do valor, nível,
    valor ou fórmula, limites, grupo e alça. Botões para acrescentar, excluir,
    subir e descer (ícones `up`/`down`). Cada erro (ciclo, nome desconhecido, tipo
    incompatível) aparece **na própria linha**, com a mensagem embaixo da tabela.
  - **Peças:** árvore das peças e dos aninhados na ordem da lista. Escolher uma peça
    mostra o formulário dela (campos da §3.3, cada um aceitando número ou fórmula,
    com o resultado calculado ao lado em cinza). Botões para acrescentar (caixa,
    cilindro, extrusão, revolução, objeto aninhado), duplicar, excluir e reordenar.
    O perfil da extrusão e da revolução é uma tabela de pontos (x; y) com fórmulas.
  - **Símbolo 2D:** *Automático* ou *Desenhado*. No desenhado, a lista de primitivas da
    §7 com formulário, visível quando e repetição.
  - **Objeto:** nome, categoria, classe, `PredefinedType`, hospedagem (livre ou
    parede), elevação padrão, papéis de material e descrição.
  - **Tipos:** a lista de tipos da definição, com os valores dos parâmetros de tipo em
    colunas (uma linha por tipo). Duplicar, renomear e excluir tipo.
- **Coluna da direita, a prévia:** planta (o símbolo 2D) e 3D (o sólido, com órbita),
  lado a lado ou alternadas. Acima, a escolha do **tipo de teste**. Os parâmetros de
  ocorrência aparecem num formulário "valores de teste" para ver o objeto mudar. Na
  planta da prévia, as alças da §3.1 funcionam. A peça escolhida na árvore aparece
  realçada.
- A prévia é refeita a cada mudança (com um atraso de 300 ms durante a digitação) pelo
  mesmo código do núcleo que gera o corpo, sem gravar no modelo.
- **Aplicar ao projeto** grava a definição (versão + 1) em todos os tipos dela numa
  transação ("Editar objeto Cama") e refaz as ocorrências. Se alguma ocorrência não
  aceitar os valores novos (fora dos limites, medida ≤ 0), nada é gravado e a mensagem
  lista quais e por quê. **Gravar na biblioteca…** faz o mesmo que a §4.3.
- Editar uma definição que veio da biblioteca do BrasBim é permitido **no projeto**. A
  origem continua registrada, e *Atualizar da biblioteca* avisa que as mudanças locais
  serão perdidas.

A geometria é editada **pelo formulário e pela prévia**: no pacote 13 não se desenha
na prévia nem há planos de referência com restrições (decisão do revisor; editor gráfico
no V2, §11).

### 5.4 Objetos do projeto e troca de tipos
Painel Projeto, lista nova **Objetos** (agrupada por categoria e definição, com os tipos
e a contagem de ocorrências):
- *Editar tipo…* abre um formulário pequeno (nome, código e parâmetros de tipo), ou o
  editor na aba Tipos. *Duplicar tipo* cria um tipo da mesma definição com os mesmos
  valores, e *Renomear* também está aqui.
- *Excluir tipo:* sem ocorrências, exclui. Com ocorrências, pede o tipo substituto (da
  mesma classe) na mesma transação, como os tipos de pilar e viga.
- *Excluir objeto:* exclui todos os tipos da definição, com a mesma regra.
- *Editar objeto…*, *Atualizar da biblioteca*, *Gravar na biblioteca…*, *Selecionar
  ocorrências*.
- **Trocar tipo** de ocorrências escolhidas, pelo painel de propriedades ou pela
  mini-barra:
  - Na **mesma definição**: os parâmetros de ocorrência ficam como estão.
  - Para **outra definição** da mesma classe: o valor passa quando o identificador e o
    tipo do valor coincidem, e os outros recebem os padrões do tipo novo. Posição,
    rotação, espelho, elevação e camada ficam. Se o tipo novo é preso à parede e o
    antigo não (ou o contrário), a troca é recusada com a mensagem.
- **Trocar em todas:** *Substituir tipo…* troca, numa transação, todas as ocorrências
  de um tipo por outro.

### 5.5 Assistente (spec/ui 16)
- `list_objects` (só leitura): os tipos carregados e os da biblioteca, com os
  parâmetros e o nível de cada um.
- `insert_object` (tipo, x, y, rotação, elevação, valores de ocorrência; parede e
  distância no objeto preso à parede), que carrega da biblioteca quando preciso.
- `edit_object` (posição, valores, tipo). `describe_model` lista os objetos com tipo e
  posição.

## 6. Comportamento e regras geométricas

### 6.1 Geração
`core/objects/build.py`:
1. Junta os valores: os do tipo, os da ocorrência e os calculados, em ordem de
   dependência (§3.2).
2. Para cada peça visível, expande a repetição, calcula as medidas e gera o item IFC
   com o estilo.
3. Gera o símbolo 2D (§7) e a caixa que envolve.
4. Para cada aninhado: calcula o tipo e os valores ligados, e cria ou refaz a
   ocorrência agregada (§6.4).

A mesma função serve à prévia do editor, que trabalha num documento temporário.

### 6.2 Objetos e o resto do modelo
- O objeto **não corta** nem é cortado por paredes, lajes e estrutura, e não entra nas
  junções. Ele também não entra em `cuts.nearby`.
- Snap: cantos da caixa que envolve e ponto de inserção, na planta e no 3D.
- Excluir o pavimento exclui os objetos dele, como os outros elementos.
- Os objetos podem se sobrepor livremente (sem aviso de colisão no pacote 13).

### 6.3 Preso à parede
- A definição com hospedagem **parede** põe a face de trás do objeto (y = 0 local,
  depois da rotação) **na face** da parede escolhida, com a frente para fora.
- Estado: parede (GlobalId), face (`left`/`right`, como no nicho), distância ao longo
  do eixo (como a porta) e elevação.
- A parede que **se move, gira ou muda de espessura** leva o objeto junto. O objeto
  continua na mesma distância e na mesma face. Uma parede encurtada a ponto de deixar o
  objeto fora dela não é recusada: o objeto fica na última posição válida e aparece um
  aviso em Mensagens (ponto de revisão (h)).
- **Excluir a parede** exclui os objetos presos a ela, na mesma transação. A mensagem
  conta quantos ("1 parede e 2 objetos"), como as esquadrias.
- **Vão:** a peça marcada como vão vira um `IfcOpeningElement` na parede, nicho
  (`RECESS`, com profundidade) ou passante (`OPENING`). Ele é refeito com o objeto e entra
  nos cortes, na planta e nas quantidades da parede, como os nichos. O vão de um objeto
  não pode cair sobre uma porta, uma janela ou outro vão (`check_fits`).
- **Mover o objeto** com as ferramentas (Mover, alça) o desliza **ao longo da parede**:
  o movimento é projetado na direção da parede. Arrastar para longe da parede não o
  solta. Para soltar, há *Soltar da parede* no menu do botão direito, que o deixa livre
  no mesmo lugar e tira o vão.
- Girar ou espelhar um objeto preso à parede sozinho, sem a parede, é recusado com
  mensagem. Junto com a parede, ele acompanha.

### 6.4 Objetos aninhados
- Uma peça "objeto aninhado" aponta para um **tipo** de outro objeto. O tipo é fixo
  (escolhido no editor) ou vem de um parâmetro **tipo de objeto**, que aceita os tipos
  de uma categoria. Ex.: na mesa, o parâmetro `cadeira` aceita os tipos de Mobiliário
  com `PredefinedType = CHAIR`.
- **Ligação de parâmetros:** cada parâmetro de **ocorrência** do aninhado pode receber
  uma fórmula do objeto de fora (`altura_assento = altura_mesa - 0,30`). Os parâmetros de
  tipo do aninhado vêm do tipo dele. A posição, a rotação e a repetição dos aninhados
  aceitam fórmulas: as cadeiras da mesa se repetem por `n_cadeiras / 2` em cada lado.
- O tipo aninhado entra no projeto junto com o tipo de fora (carregar a mesa carrega a
  cadeira). Na biblioteca, os dois ficam no mesmo arquivo, ou no índice das pastas.
- **Seleção:** o clique escolhe sempre o objeto de **fora**. O aninhado não tem alça,
  painel nem operação própria. Ele é refeito pelo de fora.
- **Tabelas:** o aninhado conta na própria categoria (as cadeiras da mesa entram como
  cadeiras), com a coluna "parte de" mostrando o objeto de fora.
- **Profundidade máxima: 3 níveis.** Um ciclo (A dentro de B dentro de A) é recusado
  no editor.
- Excluir o tipo aninhado que está em uso pede o substituto, como na §5.4.

## 7. Representação 2D
- **Planta:** o objeto é desenhado pelo **símbolo 2D**, sempre em **vista** (sem corte),
  com linha fina, e o pavimento de baixo e acima do plano de corte seguem as regras da
  spec/ui 06, conforme a convenção usual de desenho de mobiliário e equipamentos da NBR
  6492 (texto a conferir, como nas outras specs).
  - **Automático** (padrão): para cada peça visível, o contorno da peça vista de cima.
    Os contornos são unidos com `clip.union` por **nível** de altura e desenhados um
    sobre o outro. Para um objeto feito de caixas basta e dá o desenho simples de
    sempre.
  - **Desenhado:** primitivas próprias no sistema local, com fórmulas, "visível quando"
    e repetição: linha, polilinha, retângulo, círculo, arco e preenchimento (com o
    material ou uma cor do tema). Ex.: a árvore é um círculo com o raio da copa e um
    traço irregular, e a bacia sanitária é o contorno oval mais a caixa.
  - Objetos de vegetação são desenhados **por cima** das paredes e lajes, e os outros
    por baixo das paredes cortadas.
- Etiqueta opcional (Exibir > Etiquetas de objetos): o **código** do tipo junto ao
  objeto, como as esquadrias.
- Alças (§5.1) e realce da seleção como nos outros elementos.
- **Corte e fachada:** pelo 3D, como os outros elementos (`section.draw` usa os
  triângulos). O objeto não tem hachura de corte: ele aparece com linha de vista
  (ponto de revisão (i)).
- **3D:** cor por peça pelos `IfcStyledItem`, com vidro transparente (`Mesh.glass`).
- **Camadas:** segue a camada do objeto (§2.5).

## 8. Quantitativos
- **Tabelas (spec/ui 17):** categorias novas **Mobiliário**, **Louças e metais**,
  **Eletrodomésticos**, **Vegetação** e **Objetos** (todas as classes). Campos:
  código, objeto (definição), tipo, classe, pavimento, "parte de", quantidade (soma
  de 1 por ocorrência), medidas nominais e **qualquer parâmetro** da definição. A
  coluna do parâmetro aparece quando a tabela filtra uma definição só, ou quando os
  tipos escolhidos têm o mesmo identificador.
- Modelo de tabela novo: **Lista de mobiliário e equipamentos** (agrupada por objeto e
  tipo, com contagem).
- O IFC 4.3 não traz `Qto_FurnitureBaseQuantities`. Os conjuntos
  `Qto_SanitaryTerminalBaseQuantities` e `Qto_ElectricApplianceBaseQuantities` existem,
  mas a documentação não lista as quantidades. Por isso o pacote 13 **não grava
  `Qto_*`**: as medidas ficam nas propriedades nominais do Pset comum (§2.1), e a
  contagem é o número de ocorrências (ponto de revisão (j)).

## 9. Critérios de aceite (testes)
Projeto de teste: Térreo com o retângulo de paredes (0, 0)–(6, 4) de 15 cm e a
biblioteca do BrasBim. Testes em `tests/test_objetos.py` (núcleo),
`test_objetos_formula.py`, `test_objetos_biblioteca.py` e `test_interface_objetos.py`.

- [ ] **OB01** Fórmulas: `máx(1,20 - 2 * 0,10; 0,40)` dá 1,00; `se(tampo = "redondo";
      1; 0)`; vírgula decimal e `;`. Ciclo, nome desconhecido, tipo de parâmetro
      dependendo de ocorrência e texto onde se espera comprimento são recusados com
      a mensagem certa. A expressão `__import__("os")` é recusada como erro de sintaxe
      (sem `eval`).
- [ ] **OB02** Carregar "Cama casal": `IfcFurnitureType` `BED` com
      `BrasBim_DefinicaoObjeto`, `BrasBim_Parametros` (Largura 1,38, Comprimento 1,88)
      e `Pset_FurnitureTypeCommon` (`Reference`, nominais). Sem `RepresentationMaps`. O
      arquivo passa na validação de esquema do IfcOpenShell.
- [ ] **OB03** Inserir duas camas: cada `IfcFurniture` tem o próprio `Body` com um
      `IfcStyledItem` por peça, ligado ao tipo por `IfcRelDefinesByType`, no pavimento,
      na camada Mobiliário. A caixa que envolve mede 1,38 × 1,88.
- [ ] **OB04** Parâmetro de **tipo**: mudar a largura do tipo para 1,58 refaz as duas
      camas numa transação. Desfazer volta as duas, e o diário reaplicado reproduz o
      IFC.
- [ ] **OB05** Parâmetro de **ocorrência**: o comprimento da bancada numa ocorrência
      (2,40) não muda a outra (1,80). O `BrasBim_Parametros` da ocorrência tem 2,40, e
      a leitura "tipo + ocorrência" pela regra do IFC dá 2,40 para uma e 1,80 para a
      outra.
- [ ] **OB06** Visibilidade e escolha: o sofá sem braço não tem as peças dos braços. A
      mesa com tampo "redondo" tem o tampo em cilindro, e "retangular" em caixa.
- [ ] **OB07** Repetição: a estante com 5 prateleiras tem 5 itens de prateleira com
      espaçamento igual. Mudar para 3 deixa 3.
- [ ] **OB08** Limites e erros: comprimento abaixo do mínimo e uma fórmula que dá
      medida ≤ 0 recusam a operação (`OpError`), e o modelo fica como antes.
- [ ] **OB09** Aninhados: a mesa de 6 lugares agrega 6 `IfcFurniture` Cadeira
      (`IfcRelAggregates`) posicionadas em relação a ela. Mudar o comprimento para 8
      lugares dá 8 cadeiras, desfazer volta a 6 com os mesmos GlobalIds, e trocar o
      parâmetro `cadeira` por outro tipo troca as 6.
- [ ] **OB10** Preso à parede: o lavatório suspenso na face interna da parede sul fica
      com o fundo na face, `IsBuiltIn` verdadeiro e `IfcRelConnectsElements`. Mover a
      parede 0,50 leva o objeto, e excluir a parede exclui o objeto (desfazer devolve
      os dois).
- [ ] **OB11** Vão: o armário com nicho cria um `IfcOpeningElement` `RECESS` na parede
      por `IfcRelVoidsElement`, sem `IfcRelFillsElement`. Pôr o objeto sobre uma janela
      é recusado. *Soltar da parede* tira o vão.
- [ ] **OB12** Trocar tipo: trocar a "Mesa 6 lugares" por "Mesa 4 lugares" mantém
      posição, rotação e camada. Trocar uma cama por uma bacia (outra classe) não
      aparece na lista. Excluir um tipo em uso pede o substituto.
- [ ] **OB13** Transformações: mover, copiar, girar e espelhar um objeto livre (o
      espelho troca o sinal do eixo x local). Girar sozinho um objeto preso à parede é
      recusado.
- [ ] **OB14** Biblioteca: gravar "Cama" numa pasta do usuário gera um `.ifc` com
      `IfcProjectLibrary`, os tipos declarados por `IfcRelDeclares` e uma ocorrência
      de amostra por tipo. Ele passa na validação. Carregar de volta num projeto vazio
      dá os mesmos valores.
- [ ] **OB15** Atualizar da biblioteca: a definição v2 com o parâmetro novo
      `cabeceira` mantém a largura dos tipos e o comprimento das ocorrências, e o
      parâmetro novo entra com o padrão. Desfazer volta à v1.
- [ ] **OB16** Planta: o símbolo automático da cama é o contorno da caixa, mais o
      travesseiro. O símbolo desenhado da árvore é um círculo com o raio da copa, que
      muda com o parâmetro. Exibir > Etiquetas de objetos mostra o código.
- [ ] **OB17** Tabelas: "Lista de mobiliário e equipamentos" conta 2 camas casal, 1
      mesa e 6 cadeiras (as cadeiras "parte de" Mesa). A coluna Largura aparece quando
      a tabela filtra só Cama.
- [ ] **OB18** Editor: um objeto novo com dois parâmetros (largura de tipo, altura de
      ocorrência) e uma caixa dá a prévia certa. Gravar com ciclo é recusado na linha.
      *Aplicar ao projeto* sobe a versão e refaz as ocorrências. Valores que deixam uma
      ocorrência inválida não gravam nada e listam a ocorrência.
- [ ] **OB19** Interface: dar clique duplo num tipo da biblioteca ativa a ferramenta.
      O fantasma segue o cursor, a barra de espaço gira 90°, o clique insere, e Tab dá
      a rotação. No objeto preso à parede, o fantasma encosta na face e Tab dá distância
      e altura. A alça de largura do guarda-roupa muda o valor.
- [ ] **OB20** Assistente: `insert_object` com "Cama casal" em (2, 2) cria o objeto e
      `describe_model` o lista. `list_objects` mostra os parâmetros com o nível.
- [ ] **OB21** Biblioteca inicial: todos os objetos e tipos da §4.5 carregam, geram
      corpo e símbolo sem erro e passam na validação de esquema (um teste
      parametrizado por tipo).

## 10. Fontes públicas
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

## 11. Fora do escopo / pontos de revisão
- **V1:** importar como objeto um tipo de outra origem (sem `BrasBim_DefinicaoObjeto`;
  hoje fica como está, sem parâmetros); catálogo de tipos por planilha (CSV com um tipo
  por linha); objeto preso a laje, forro ou bancada; aviso de colisão; outras
  categorias (luminárias, `IfcLightFixture`; tomadas e pontos elétricos; acessórios de
  banheiro); bSDD e classificação (RF-TIP-08 e 09); detalhe por escala no símbolo
  (simplificado × detalhado); peças por varredura num caminho e booleanos entre peças;
  objetos que cortam a laje (ralo, shaft).
- **V2:** editor gráfico (desenhar peças na prévia com planos de referência, cotas que
  viram parâmetros e restrições, RF-TIP-05 completo); compatibilidade com outras
  linguagens de objeto paramétrico; levar porta e janela para o sistema de objetos.
- **Ordem de implementação proposta** (um pacote, em etapas com commit e testes):
  (1) fórmula e definição no núcleo (OB01, OB06–OB08); (2) tipos, ocorrências,
  operações e planta (OB02–OB05, OB13, OB16); (3) biblioteca em arquivo, painel e
  ferramenta (OB14, OB15, OB19); (4) aninhados e presos à parede (OB09–OB11); (5) troca
  de tipos, tabelas e assistente (OB12, OB17, OB20); (6) editor (OB18); (7) biblioteca
  inicial (OB21).
- **Pontos de revisão:**
  (a) porta e janela continuam com os tipos próprios, sem virar objetos paramétricos
      (§1);
  (b) a definição repetida em cada tipo da mesma definição, e não guardada uma vez no
      projeto (§2.2);
  (c) camada nova Interiores › Equipamentos para louças e eletrodomésticos (§2.5);
  (d) o padrão do tipo para um parâmetro de ocorrência vale só para o exemplar novo, e
      mudar o padrão não mexe nos que já existem (§3.4);
  (e) ocorrência de amostra no arquivo de biblioteca, para outros programas verem o
      objeto (§4.1);
  (f) no 3D, a elevação vem da superfície atingida (§4.4);
  (g) a lista e as medidas da biblioteca inicial (§4.5);
  (h) a parede encurtada que deixa o objeto fora só gera aviso, sem recusar (§6.3);
  (i) objeto cortado sem hachura no corte (§7);
  (j) sem `Qto_*` nos objetos; as medidas ficam nas nominais (§8);
  (k) o clique sempre escolhe o objeto de fora, e o aninhado não se edita sozinho
      (§6.4).
