# Complemento: perfil complexo no Archicad, estudo a fundo (2026‑11‑04)

> Pedido do revisor: "estude profundamente o perfil complexo do Archicad", antes de
> implementar a spec/ui 41 §4 (parede, viga e pilar). Só fontes públicas: a ajuda oficial
> da Graphisoft (AC18, 20, 24, 26, 28 e 29) e resumos de busca de tópicos do fórum. As
> páginas do fórum recusaram a leitura automática (HTTP 403); o que vem delas está marcado
> **(fórum, via busca)** e precisa ser conferido antes de virar regra. Este texto descreve
> **funções**. Nomes de comandos, textos e disposição de diálogos não são copiados.
> Complementa `complemento_dwg_solidos_perfis.md` §3 e `archicad_modelagem.md` §1.

## 1. O conceito
- Um perfil complexo é uma **seção 2D extrudada** perpendicular ao plano dela. Serve para
  paredes, pilares, vigas, componentes de guarda‑corpo e objetos que aceitam perfil (fachada
  cortina, escada). A estrutura básica vem do **material de construção** de cada parte. —
  [About Complex Profile Elements AC18](https://help.graphisoft.com/AC/18/INT/AC18Help/03_1_Elements_Virtual_Building/03_1_Elements_Virtual_Building-35.htm);
  [Complex Profiles AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-55.htm)
- O perfil é um **atributo do projeto**, com nome, como as hachuras e os materiais. Também
  dá para aplicar um perfil avulso a um elemento sem gravá‑lo como atributo (ver §8).
  Vêm perfis prontos com o programa e há um catálogo de perfis de aço padrão para pilar e
  viga. — mesmas fontes.

## 2. Gerenciador e editor
- Um **gerenciador** lista os perfis do projeto: criar, duplicar, renomear, apagar. Um
  filtro **"serve para"** (ícones das ferramentas) decide quais ferramentas podem usar o
  perfil, e a lista da ferramenta mostra só os perfis compatíveis. —
  [Profile Manager AC24](https://help.graphisoft.com/AC/24/INT/_AC24_Help/040_ElementsVB/040_ElementsVB-58.htm);
  [Profile Manager AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-53.htm)
- Editar abre uma **janela 2D separada** (o editor), com o gerenciador ao lado como
  painel. Também se chega a ela pelo botão direito sobre um elemento de perfil ("editar o
  perfil do selecionado"). Enquanto a janela ativa é a do modelo, os controles de edição do
  gerenciador ficam desligados. Gravar: botão no gerenciador, ou a pergunta ao trocar de
  perfil. — [Create or Edit Complex Profile AC24](https://help.graphisoft.com/AC/24/INT/_AC24_Help/040_ElementsVB/040_ElementsVB-59.htm);
  [Edit Complex Profile AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-54.htm);
  [Save Named Profile AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-55.htm)
- No editor só há ferramentas 2D. As **partes** são hachuras (regiões fechadas); cada uma
  leva um material de construção e um tipo de linha de corte. Só as hachuras e os pontos
  quentes são gravados. Linhas, cotas e outros desenhos ficam numa camada **de apoio**:
  são gravados com o perfil, mas não aparecem no elemento. — mesmas fontes.
- **Partes sobrepostas são aceitas.** No elemento, o que se sobrepõe é resolvido pela
  **prioridade de interseção do material** (a de maior prioridade corta a outra). — AC24
  acima; [Offset Modifiers: Tips and Tricks AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-67.htm)

### 2a. Camadas de desenho do editor
Interruptores de visibilidade no editor (uma área "camadas de projeto"): —
[Design Layers Panel AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-56.htm)
- **Construção**: as partes e os pontos quentes (o que vale no elemento);
- **Apoio**: o desenho de auxílio (não vai para o elemento);
- **Linhas de esticar** (§4);
- **Largura e altura nominais**: as cotas da medida nominal (§4);
- **Deslocamentos** (§5): cotas e destaques; o deslocamento escolhido na lista aparece
  sempre;
- **Referência das aberturas** (só parede): as linhas onde portas e janelas se apoiam.
  Podem ser editadas, estendidas e quebradas para seguir a forma. Sem elas, a abertura usa
  o retângulo envolvente do perfil (§6c).

### 2b. Cada parte (componente)
Com uma parte escolhida, o painel de componentes define: —
[Components Panel AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-58.htm)
- **papel**: núcleo, acabamento ou outro (usado pela exibição parcial, §9);
- **superfície própria** (sobrepõe a do material). "Várias" aparece quando arestas têm
  superfície própria;
- **linhas de fim de corte**: tipo e pena da linha quando o elemento é cortado na ponta;
- **como medir a área da parte** nas tabelas de componentes: por uma **linha‑base** ou por
  um **círculo‑base**, que se mostra na tela por uma opção de vista (§10).

Por aresta: —
[Apply Custom Surface or Line to Profile Edge AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-61.htm)
- superfície e linha próprias, na aresta clicada ou em todas;
- desligar a **linha de corte** daquela aresta (ex.: não desenhar a linha entre a placa e o
  montante).

**Contornos uniformes:** um tipo de linha e uma pena para todos os **contornos** (as
linhas de fora) e outro para todos os **separadores** (as linhas entre partes). Valem no
elemento posto, também depois dos deslocamentos. Separadores entre duas partes do **mesmo
material não somem**, e arestas com a linha desligada ficam como estão. —
[Uniform Contours Panel AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-59.htm)

### 2c. Origem
- A **origem não se move**: move‑se o desenho em relação a ela. Na parede ela é a **linha
  de referência**; no pilar e na viga, o **eixo**. Viga de escada: a origem no topo do
  perfil (ou o ponto de ancoragem no topo). Fachada cortina: regras próprias por peça. —
  [Profile Origin AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-62.htm);
  [Profile Origin AC24](https://help.graphisoft.com/AC/24/INT/_AC24_Help/040_ElementsVB/040_ElementsVB-63.htm)

## 3. Medida nominal e medida total
- **Nominal** (largura e altura): as cotas mostradas no editor. Por padrão seguem o
  retângulo envolvente das partes. Podem ser arrastadas, ter o comprimento mudado e ser
  alinhadas a qualquer parte do perfil, até fora do envolvente. As pontas podem ser presas
  a nós das partes, o que pode dar **excesso de restrição** (com aviso). —
  [Design Layers Panel AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-56.htm)
- No elemento, a nominal é um **parâmetro que entra em lista** e só é **editável se o
  perfil tem esticar** naquele sentido. A **total** é o envolvente do elemento já com os
  deslocamentos: aparece, mas não se edita. Ao passar o mouse sobre a medida, a ficha
  mostra a nominal e a total. — mesma fonte;
  [Stretch Modifiers AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-63.htm)

## 4. Esticar
- Liga‑se **esticar na largura** e/ou **na altura**. As **linhas de esticar** marcam onde
  a forma estica ou encolhe. Na parede, a largura é a espessura e a altura é a altura da
  parede. Na viga são a largura e a altura; no pilar, as duas medidas da seção. Só existe
  em parede, viga e pilar de perfil. — [Stretch Modifiers AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-63.htm);
  [Stretch Modifiers AC24](https://help.graphisoft.com/AC/24/INT/_AC24_Help/040_ElementsVB/040_ElementsVB-64.htm)
- Por padrão as linhas de esticar coincidem com as cotas nominais. —
  [Create New Offset Modifier – Example AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-65.htm)
- Mudar a medida do elemento muda a nominal e as linhas de esticar. Os **deslocamentos
  não mudam** e mantêm a distância à âncora. As linhas de esticar **partem** as arestas
  que não são horizontais nem verticais e as cruzam. — [Tips and Tricks AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-67.htm)
- Esticar pela tela: comandos próprios na paleta do elemento, "esticar o perfil na
  horizontal" e "na vertical", com as linhas de esticar mostradas como retorno. No pilar,
  esticar o núcleo pela aresta não muda o revestimento. —
  [Graphical Editing of Complex Profiles AC20](https://help.graphisoft.com/AC/20/INT/AC20Help/03_1_Elements_Virtual_Building/03_1_Elements_Virtual_Building-35.htm)
  (via busca); [Editing Columns AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-29.htm) (via busca)
- **O que a ajuda não diz:** a regra exata de que parte fica parada e qual anda. O que se
  lê, junto com a figura de exemplo, é que as linhas dividem o perfil e só a faixa entre
  elas muda de tamanho. O resto **anda junto**, sem deformar.

## 5. Deslocamentos (por elemento)
- Controles **opcionais com nome** que deslocam arestas escolhidas **em cada elemento**,
  para não ter de criar muitos perfis parecidos (ex.: "largura da sapata", "espessura do
  reboco"). Os valores se editam na ficha do elemento ou pela tela (planta, corte, 3D).
  Entram em listas, tabelas e propriedades por expressão. Só em parede, viga e pilar. —
  [Offset Modifiers AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-64.htm);
  [Offset Modifiers AC24](https://help.graphisoft.com/AC/24/INT/_AC24_Help/040_ElementsVB/040_ElementsVB-65.htm)
- Como se monta (exemplo da sapata de borda de laje): cria‑se o deslocamento com um nome
  (ou um nome já usado no projeto). Ele fica com aviso até ter uma cota. Depois se dá a
  cota de um destes jeitos: —
  [Create New Offset Modifier – Example AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-65.htm)
  1. **aresta com âncora num nó**: a âncora segue a forma (marca redonda);
  2. **aresta com âncora fixa**: um ponto qualquer, como a origem (marca quadrada);
  3. **duas arestas**: a cota acha os nós mais próximos e o valor move as duas (não
     precisam ser paralelas);
  4. **dois nós e a aresta vizinha**: a cota pode não ser perpendicular à aresta; a aresta
     anda na perpendicular, mas medida pela cota.
- Um deslocamento pode ter **várias cotas, todas com o mesmo valor**, e uma cota pode mover
  **várias arestas** juntas. Uma cota presa à aresta de outro deslocamento anda quando ele
  anda; com âncora própria, fica. A edição permite trocar a âncora, somar ou tirar arestas
  e somar cotas. Apagar o deslocamento leva as cotas. —
  [Edit Offset Modifier AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-66.htm)
- **Restrições:** —
  [Tips and Tricks AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-67.htm)
  - só arestas retas (arcos não);
  - arestas inclinadas que cruzam uma linha de esticar não servem;
  - duas arestas paralelas viradas para o mesmo lado travam o deslocamento: o perfil é
    gravado com aviso, e o remédio é inverter uma delas;
  - dois deslocamentos presos um ao outro: excesso de restrição, nenhum anda;
  - valor **zero** vale e some com a parte, mas, se o elemento todo sumir, a mudança é
    desfeita;
  - valor **negativo** vale e pode inverter a forma;
  - a aresta nova criada por um deslocamento herda as propriedades da parte.
- **Queixas (fórum, via busca):**
  - ao encolher o isolamento, o reboco cresceu: as duas arestas do reboco precisavam estar
    presas ao deslocamento do isolamento;
  - um deslocamento só empurra a aresta inteira: não gira a aresta, nem move um nó que é de
    duas arestas;
  - só um deslocamento por aresta;
  - a base de uma parte muda quando a altura da parede muda.

  Fontes: [Offset Modifiers in Walls – adjusting skins](https://community.graphisoft.com/t5/Modeling/Complex-Profile-Offset-Modifiers-in-Walls-adjusting-skins/td-p/651595);
  [Complex Profiles Offset Modifier](https://community.graphisoft.com/t5/Modeling/Complex-Profiles-Offset-Modifier/td-p/581092);
  [Profile Manager – Anchoring Edges](https://community.graphisoft.com/t5/Modeling/Profile-Manager-Anchoring-Edges/m-p/283558)

## 6. No elemento
### 6a. Parede
- Na estrutura da parede há três escolhas: básica, composta e **perfil**. Com perfil, uma
  lista dá os perfis que servem para parede. —
  [Walls AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-6.htm);
  [Wall Tool Settings AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/150_UserInterfaceToolSettings/150_UserInterfaceToolSettings-3.htm)
- Na parede de perfil **não há** método trapézio ou polígono. A espessura vem do perfil
  (a página não traz regra de espessura para o perfil; a ficha mostra a nominal). — mesmas
  fontes.
- **Curva** funciona (exemplo: duas paredes curvas com o perfil "muro com sapata"). —
  AC18 acima.
- **Mudar a linha de referência** (o comando que muda o lado sem mover a parede) **não tem
  efeito** na parede de perfil. A referência é a origem do perfil. —
  [Modify Wall Reference Line AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-19.htm)
- Superfícies no elemento: duas possibilidades, a **da extrusão (arestas)** e a **das
  pontas**. — Wall Tool Settings AC28 acima.

### 6b. Pilar e viga
- Pilar e viga têm **segmentos** (desde o AC23). Cada segmento pode ser retangular,
  circular ou de perfil; o comprimento do segmento é fixo ou flexível (em %). —
  [Column Segment Structure AC26](https://help.graphisoft.com/AC/26/INT/_AC26_Help/040_ElementsVB/040_ElementsVB-26.htm);
  [Beam and Column Tool Renewal AC23](https://help.graphisoft.com/AC/23/int/_AC23_Help/005_NewFeatures/005_NewFeatures-3.htm)
- **Girar o perfil:** na viga e no pilar, o girar comum gira o elemento com a direção da
  extrusão. "Girar o perfil" (pela paleta no 3D, ou um ângulo em graus na ficha) gira só a
  seção em torno do eixo. — AC20 acima (via busca);
  [Beam Tool Settings AC20](https://help.graphisoft.com/AC/20/INT/AC20Help/Appendix_Tools/Appendix_Tools-6.htm) (via busca)
- Para a análise estrutural, a peça de perfil (ou cônica, ou com vários segmentos) vira uma
  barra com um **perfil de substituição**. —
  [Replacement Profile AC25](https://help.graphisoft.com/AC/25/INT/_AC25_Help/090_StructuralAnalyticalModelTools/090_StructuralAnalyticalModelTools-6.htm)

### 6c. Portas e janelas na parede de perfil
- Portas e janelas entram em qualquer parede, inclusive de perfil. Na parede de perfil, a
  **inclinação da abertura** vem da **linha de referência das aberturas**, desenhada no
  editor (§2a). Sem ela, vale o envolvente. —
  [Window/Door Plane in Slanted or Complex Walls AC26](https://help.graphisoft.com/AC/26/INT/_AC26_Help/040_ElementsVB/040_ElementsVB-308.htm)
- **(fórum, via busca)** Queixas frequentes:
  - a janela aparece deslocada da parede; o remédio é pôr a referência das aberturas no
    corpo principal da parede;
  - um defeito conhecido faz a planta simbólica da janela não bater com o 3D em certos
    perfis;
  - o rodapé e a moldura ficam certos com a abertura ancorada no piso.

  Fontes: [Window appears offset from Complex Profile wall](https://community.graphisoft.com/t5/Modeling/Window-appears-offset-from-Complex-Profile-wall/td-p/372607);
  [Opening Reference Line problem](https://community.graphisoft.com/t5/Modeling/Complex-profile-Opening-Reference-Line-problem/td-p/255873)
- A ajuda lida não diz **que parte do perfil** a abertura corta. O que se lê é que ela
  corta o perfil todo e se apoia na linha de referência.

### 6d. Junções
- Não há regra própria para o perfil: valem as regras gerais. Parede com parede pede que as
  **linhas de referência se cruzem**. Entre as partes, a de **material com maior
  prioridade corta** a outra; com prioridade igual, decide a **ordem de junção**. Os outros
  pares (parede‑viga, parede‑pilar…) pedem **colisão** dos volumes. Nas linhas de corte e
  vista, perfis e compostas têm o controle de linhas que o usuário ajusta nos atributos. —
  [Specific Element Intersections and Junctions AC29](https://help.graphisoft.com/AC/29/INT/_AC29_Help/040_ElementsVB/040_ElementsVB-272.htm);
  [Basic Intersection Principles AC26](https://help.graphisoft.com/AC/26/INT/_AC26_Help/040_ElementsVB/040_ElementsVB-270.htm)
- **(fórum, via busca)** Queixas:
  - cantos de cornija ou capa ruins entre paredes de perfil;
  - um perfil que entra em outra parede sem querer; o remédio é pôr cada um numa camada com
    **grupo de interseção** diferente.

  Fonte: [problem with wall cornice corner details](https://community.graphisoft.com/t5/Design-forum/problem-with-wall-cornace-corner-details-complex-profiles/td-p/184566)

## 7. Planta
- A parede de perfil **não tem a exibição simbólica** na planta. O padrão é **"projetada
  com o que está acima"**; as outras opções são "projetada" e "só o corte". O resultado
  depende da **altura do plano de corte**. —
  [Define Element's Floor Plan Display](https://helpcenter.graphisoft.com/?p=55205) (via busca);
  [profile display in plan (fórum, via busca)](https://community.graphisoft.com/t5/Documentation/profile-display-in-plan/td-p/255990)
- Uma vista simbólica das paredes de perfil está entre os pedidos mais votados da lista de
  desejos. — `usuarios_e_mercado_brasil.md` (Wishlist)
- **(fórum, via busca)** Muro de arrimo ou fundação abaixo do piso com janela: os remédios
  são projeção com o que está acima, o elemento inteiro e um "mostrar até" negativo. Com o
  topo da parede abaixo do pavimento, só sai a projeção, sem o corte. —
  [complex wall w window below floor plane](https://community.graphisoft.com/t5/Modeling/complex-wall-w-window-below-floor-plane/td-p/295475)
- **(fórum, via busca)** A espessura das linhas não bate entre as partes. O remédio é pôr
  nós e desligar a linha de corte da aresta. —
  [line weight inconsistent](https://community.graphisoft.com/t5/Documentation/Complex-profile-line-weight-inconsistent/td-p/222786)

## 8. Capturar a seção de um elemento
- Com paredes, pilares ou vigas selecionados, "capturar" transforma a seção atual num
  perfil novo, "avulso", que se pode **gravar com nome** ou **aplicar só ao elemento**. O
  perfil avulso fica **guardado no elemento** e não aparece no gerenciador. —
  [Capture Selected Element as Custom Profile AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-60.htm);
  [Save Custom Profile AC24](https://help.graphisoft.com/AC/24/INT/_AC24_Help/040_ElementsVB/040_ElementsVB-61.htm)

## 9. Exibição parcial da estrutura
- Uma opção da vista mostra o modelo inteiro, **sem acabamentos**, **só o núcleo** ou
  **só o núcleo dos elementos portantes**. O papel núcleo/acabamento de cada parte do
  perfil decide o que aparece. Fica gravada em cada vista. —
  [Partial Structure Display AC24](https://help.graphisoft.com/AC/24/INT/_AC24_Help/050_ViewsVB/050_ViewsVB-109.htm)

## 10. Quantitativos
- As tabelas de componentes listam a **área** e o **volume** de cada parte. A área de uma
  parte é a projeção no plano que passa pelo meio dela (de onde vem a linha‑base ou o
  círculo‑base, §2b). Desde o AC25 há também os valores **brutos** (sem descontar furos)
  e **condicionais**, com regras nas preferências do projeto. —
  [New Features AC25 – component quantities](https://help.graphisoft.com/AC/25/INT/_AC25_Help/005_NewFeatures/005_NewFeatures-17.htm) (via busca);
  [Accurate Schedules and Quantity Takeoffs](https://community.graphisoft.com/t5/Project-data-BIM/Accurate-Schedules-and-Quantity-Takeoffs-with-Archicad/ta-p/304148) (via busca)
- **(fórum, via busca)** Queixas:
  - de uma parede de perfil só se tira o comprimento da parede inteira, sem a área de cada
    face;
  - o volume da parte não entra nas expressões;
  - foi preciso dividir as partes para a tabela sair certa;
  - na viga de perfil, a saída foi listar a área da seção na ponta.

  Fontes: [scheduling material of wall complex profile](https://community.graphisoft.com/t5/Collaboration-with-other/sheduling-material-of-wall-complex-profile/td-p/234146);
  [Column complex profile and schedules](https://community.graphisoft.com/t5/Documentation/Column-complex-profile-and-schedules/m-p/341092);
  [Component Schedule Expression Limitation](https://community.graphisoft.com/t5/Project-data-BIM/Component-Schedule-Expression-Limitation-Need-Help-plz/td-p/710708)

## 11. IFC (o que o Archicad faz e o que dá errado)
- **(fórum, via busca)** Uma opção do tradutor IFC exporta compostas e perfis **em
  partes**. O `IfcWall` fica como contêiner sem forma, e as partes (`IfcBuildingElementPart`)
  levam a forma e a cor de cada material. —
  [Complex Profile IFC export trouble](https://community.graphisoft.com/t5/Collaboration-with-other/Complex-Profile-IFC-export-trouble/td-p/248836);
  [exporting the wall/slab elements by components](https://community.graphisoft.com/t5/Collaboration-with-other/ifc-exporting-the-wall-slab-elements-by-components/m-p/196068)
- **(fórum, via busca)** Problemas relatados:
  - no Revit, a parede de perfil chega com cada parte solta e mal ligada;
  - "99%" das janelas que somem estão em paredes de perfil;
  - mudar o tipo IFC não ajuda (parede é sempre `IfcWall`);
  - as saídas foram exportar em partes e apagar as sobras, ou usar a troca direta com o
    Revit.

  Fontes: mesmos tópicos;
  [Consultant wants to use our IFC as backgrounds](https://community.graphisoft.com/t5/Collaboration-with-other/Consultant-wants-to-use-our-IFC-as-backgrounds-walls-are-acting/td-p/293350)
- A ajuda lida não diz se o Archicad grava `IfcMaterialProfileSet` para a parede de perfil
  (lacuna).

## 12. O que levar para o BrasBim (revisa a spec/ui 41 §4)
1. **Perfil = atributo do projeto** com "serve para" (parede, viga, pilar). No IFC é o
   `IfcMaterialProfileSet` (já na spec). A lista da ferramenta e a ficha mostram só os
   compatíveis. **Perfil avulso no elemento fica de fora**: ao capturar, sempre se grava
   com nome (evita perfis escondidos e é o que o IFC representa bem, ligado ao tipo).
2. **Partes sem sobreposição no arquivo.** O editor aceita desenhar sobreposto, mas ao
   gravar recorta pela prioridade do material (a mesma regra do Archicad, resolvida uma
   vez). Cada `IfcMaterialProfile` fica com uma região disjunta, e quem lê o IFC não
   precisa conhecer prioridades.
3. **Papel da parte:** núcleo, acabamento ou outro → `Category` do `IfcMaterialProfile`
   (`LoadBearing`, `Finish`, vazio). Prepara a "exibição sem acabamentos" e entra nos
   quantitativos.
4. **Origem fixa** = a linha de referência da parede, o eixo da viga e do pilar. No editor
   é o 0,0 com a marca, e move‑se o desenho, não a origem (como no Archicad). Mudar o lado
   da referência não se aplica à parede de perfil. **Espelhar** sim, porque o Archicad não
   trata disso e é pedido comum para muro e platibanda.
5. **Esticar:** uma faixa horizontal e uma vertical, opcionais, entre duas linhas. Só a
   faixa muda; o que está além anda junto. Nominal editável na ficha só com faixa; total
   só leitura. Arestas inclinadas que cruzam a faixa são partidas nela. (Igual à spec, agora
   com a regra explícita.)
6. **Deslocamentos nomeados ficam para a etapa 2** (ponto (j) confirmado). A pesquisa
   mostra que são a parte mais frágil: excesso de restrição, só arestas retas, uma por
   aresta, queixas no fórum. Quando vierem, começar pelo caso simples (cota com âncora
   fixa, arestas retas, valor ≥ 0) e recusar com mensagem os casos que travam, em vez de
   gravar com aviso.
7. **Referência das aberturas** na parede de perfil: uma linha opcional no editor. Sem ela,
   a esquadria fica no envolvente (como no Archicad). A abertura **corta a seção inteira**
   (ponto (i)). Isso evita a queixa nº 1 do fórum (janela deslocada) e, no IFC, uma
   `IfcOpeningElement` atravessando o `IfcWall` inteiro (§11).
8. **Linhas:** uma pena de contorno e uma de separador para o perfil. Por aresta, desligar
   a linha de corte. **Diferente do Archicad:** a linha entre duas partes do mesmo material
   some (proposta, ponto (o) da spec/ui 41).
9. **Planta:** cortar de verdade no plano de corte (fatia do perfil, com a hachura de cada
   parte) e projetar o resto, como já está na spec. Isso já é melhor que o Archicad, que
   não tem a vista simbólica. A vista simbólica (a seção no plano de corte trocada por um
   desenho simples, como a parede de camadas) fica como opção futura.
10. **Capturar a seção:** "Criar perfil a partir da seleção" para parede de camadas (cada
    camada vira um retângulo com o material e o papel), viga e pilar retangular ou
    circular. É barato e dá o ponto de partida mais comum.
11. **Viga e pilar:** o ângulo de giro do perfil na ficha (graus) e o espelhar. Sem
    segmentos (o BrasBim ainda não tem). Para a análise, o perfil de substituição é
    assunto da spec de estrutura.
12. **Quantitativos:** volume e área por parte e por material (PC03). A área de cada
    **face** da parede de perfil (o que falta no Archicad, pelo fórum) sai do comprimento
    das arestas de contorno × o comprimento da parede.
13. **IFC:** **sem** `IfcBuildingElementPart`. A forma do `IfcWall`, `IfcBeam` e
    `IfcColumn` é uma extrusão ou varredura **por parte**, cada uma com o estilo do seu
    material, num só corpo. O conjunto de perfis fica no tipo. Viga e pilar usam também
    `IfcMaterialProfileSetUsage`, e a parede segue o ponto (h). Teste novo: abrir o IFC
    gerado numa segunda leitura (IfcOpenShell) e conferir as aberturas no lugar e a parede
    inteira.
14. **Junções:** a regra geral de prioridade do material entre partes já vale. Proposta da
    spec mantida: entre perfis, esquadria pela bissetriz; entre perfil e camadas, a de
    camadas para na face. A queixa dos cantos de cornija confirma que a esquadria é o
    ponto sensível: teste próprio em L com capa e pingadeira.

## 13. Lacunas
- A regra exata de esticar (o que anda e o que deforma) não está escrita na ajuda. A
  leitura da figura e do exemplo está no §4.
- Não se achou, na ajuda, o que o Archicad grava no IFC para a parede de perfil
  (`IfcMaterialProfileSet` ou só a forma).
- Os tópicos do fórum não puderam ser abertos (HTTP 403 para leitura automática). Os
  pontos marcados **(fórum, via busca)** vêm do resumo do buscador; abrir no navegador
  antes de virar regra da spec.
- Não se leu a página "áreas de componentes de perfis complexos" (a regra da linha‑base e
  do círculo‑base em detalhe), nem as de exibição na planta (mostrar nos pavimentos,
  projeção, superfícies de corte: AC28 050_ViewsVB‑13 a ‑16).
- Não se confirmou se pilar cônico aceita perfil.
