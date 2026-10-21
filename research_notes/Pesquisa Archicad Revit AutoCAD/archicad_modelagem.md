# Archicad: catálogo das funções de MODELAGEM (versões 27/28/29), só de fontes públicas

> Pesquisa clean-room para o BrasBim. Todas as fontes são páginas públicas da web, acessadas em **2026-10-21**.
> Não foi lido nada de `_restrito/` nem de `tools/`, e nenhum binário foi inspecionado. O texto é resumo próprio
> (citações literais mínimas). Nomes de ferramentas e comandos aparecem só para identificar o que está sendo descrito.
> **Não** devem ser copiados para a UI do BrasBim.
>
> **Como ler a confiabilidade:**
> - [H] = página oficial do Help Center (help.graphisoft.com) lida por inteiro com WebFetch.
> - [S] = só trecho de resultado de busca. O fórum community.graphisoft.com devolveu HTTP 403 ao WebFetch, então as
>   opiniões de usuários vêm dos trechos que o buscador mostrou e não foram conferidas na página inteira.
> - O orçamento de buscas acabou no meio do trabalho. Numa segunda rodada (mesma data, depois que o limite foi
>   renovado), foram preenchidos: cascas, zonas, perfis complexos, objetos/GDL/PARAM-O, Favorites, Graphic Overrides,
>   propriedades/classificações, operações sólidas (SEO), laje inclinada e guarda-corpo associativo.
> - O Reddit não está acessível à ferramenta de busca (domínio bloqueado). Por isso não há fontes do Reddit.

---

## 1. Paredes: geometria, compostas, perfis complexos, linha de referência, junções e extremidades

### Takeaway
A parede do Archicad combina três escolhas independentes:
- **estrutura**: básica (um material), composta (camadas) ou perfil complexo (seção 2D extrudada);
- **método de geometria em planta**: reta, curva, trapezoidal ou poligonal;
- **inclinação**: vertical, inclinada ou duplamente inclinada.

Há várias restrições cruzadas entre essas escolhas. A limpeza das junções depende de quatro coisas: as linhas de referência precisam se encontrar, a prioridade de interseção do material de construção decide quem corta quem, um número de "Junction Order" desempata, e grupos de interseção por layer impedem a junção. Juntas em T/L com três ou mais paredes compostas são a queixa clássica.

### Cited Findings
**Métodos e tipos**
- Em planta, a parede pode ser reta, curva, trapezoidal ou poligonal. Há também modos de entrada em cadeia e em retângulo de paredes, parede inclinada e duplamente inclinada, e parede de toras (log). Curtain wall é uma ferramenta separada. — [H] [Walls AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-6.htm)
- Estruturas possíveis: básica (um componente, definido pelo material de construção), composta (várias camadas) e perfil complexo (forma livre, pode reunir vários componentes). — [H] [Walls AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-6.htm)
- Restrições cruzadas, segundo o painel de configurações da parede:
  - o método de geometria (reta/trapézio/polígono) não existe para perfil complexo;
  - a parede poligonal não aceita composta;
  - a espessura da composta vem da definição da composta e não pode ser editada na parede;
  - a espessura da parede poligonal não é editável;
  - o trapézio tem uma espessura em cada ponta;
  - os controles de inclinação não valem para trapézio nem polígono.
  — [H] [Wall Tool Settings AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/150_UserInterfaceToolSettings/150_UserInterfaceToolSettings-3.htm)
- Parede poligonal (PolyWall) é um bloco de forma livre, só com preenchimento simples. Uma opção ("cantos podem mudar") decide se o contorno do polígono se ajusta ao se ligar a paredes comuns. Por padrão, mantém o contorno original. — [H] [Wall Tool Settings](https://help.graphisoft.com/AC/28/INT/_AC28_Help/150_UserInterfaceToolSettings/150_UserInterfaceToolSettings-3.htm); [H] [Walls and Other Elements](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-18.htm); [S] [Create a Polygon Wall](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-13.htm)
- Paredes inclinadas:
  - na inclinada simples, as faces são paralelas e a espessura é medida perpendicular ao vetor de inclinação;
  - na duplamente inclinada, as faces não são paralelas e a espessura é a largura da base;
  - a altura é medida do ponto mais baixo ao mais alto;
  - o topo da duplamente inclinada tem largura mínima (pode ser zero na básica) e as faces podem se encontrar, mas não se cruzar;
  - na composta, o topo precisa caber todas as camadas;
  - em corte aparece como trapézio.
  — [H] [Create a Slanted or Double-Slanted Wall](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-15.htm)
- Parede de toras: só para parede básica reta. Opções:
  - começar com meia tora;
  - forma da tora: quadrada, arredondada fora, dentro ou nos dois lados;
  - raio;
  - superfície das arestas horizontais.

  Se a altura da tora passar da espessura da parede, as toras "não se apoiam". — [H] [Create a Log Wall](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-17.htm); [H] [Wall Tool Settings](https://help.graphisoft.com/AC/28/INT/_AC28_Help/150_UserInterfaceToolSettings/150_UserInterfaceToolSettings-3.htm)

**Altura e vínculo a pavimentos**
- A base fica ligada ao pavimento de origem (Home Story), com deslocamento opcional. O topo pode ser ligado a um pavimento acima, com deslocamento, ou ter altura fixa ("não ligado"). A elevação da base em relação a um nível de referência só é exibida e não cria vínculo. — [H] [Wall Tool Settings](https://help.graphisoft.com/AC/28/INT/_AC28_Help/150_UserInterfaceToolSettings/150_UserInterfaceToolSettings-3.htm)

**Linha de referência e direção**
- Toda parede tem uma linha de referência e uma direção, mostrada por uma seta e dada pela ordem dos cliques. A linha serve para:
  - conectar as paredes;
  - dar hotspots e arestas de edição (alguns comandos da paleta contextual só aparecem ao clicar nela);
  - definir o que é face "externa" e "interna", para as superfícies.

  Na parede curva e na poligonal, a direção não pode ser invertida. — [H] [Wall Reference Line](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-7.htm)
- Posições possíveis da linha:
  - básica: face externa (padrão), face interna ou centro;
  - composta: 6 opções (externa, centro e interna da parede ou do núcleo; as do núcleo só existem se houver núcleo);
  - trapézio: face externa ou face externa do núcleo;
  - polígono: movida graficamente;
  - perfil: dada pela origem definida no editor de perfis.

  A tecla "C" alterna entre as posições. — [H] [Wall Reference Line](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-7.htm)
- Deslocamento da linha:
  - só existe para linha externa ou interna, não para a de centro;
  - deslocar move o corpo da parede, e a linha fica no lugar;
  - um comando à parte reposiciona a linha mantendo a parede, com opção de espelhar as aberturas;
  - outro comando espelha o corpo para o outro lado da linha, mantendo o sentido das aberturas.

  Ligar a linha ao núcleo permite trocar os acabamentos sem mover o núcleo. — [H] [Wall Reference Line](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-7.htm)

**Interseções e junções**
- Os elementos se limpam quando colidem no espaço. A limpeza é feita no modelo (altera a geometria até o nível das camadas), então aparece igual em 3D, planta, corte e quantitativos. Exceção: a exibição simbólica em planta pode divergir do 3D. — [H] [Basic Intersection Principles AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-271.htm)
- Prioridade de interseção do material de construção: o elemento ou camada de maior prioridade corta o de menor. Vale para paredes, vigas, pilares, lajes, telhados, cascas e morphs, sejam básicos, perfil ou compostos. — [H] [Basic Intersection Principles](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-271.htm)
- Telhados, cascas (Shell) e Morph, além de colidir, precisam de um comando explícito de mesclar ou aparar (menu Connect). — [H] [Basic Intersection Principles](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-271.htm)
- Grupos de interseção por layer: elementos em layers com números de grupo diferentes nunca se intersectam. O número é só um rótulo, não uma prioridade. — [H] [Basic Intersection Principles](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-271.htm)
- "Junction Order" (número de prioridade da parede) só entra em dois casos: quando paredes de mesma prioridade de material se encontram, ou quando 3 ou mais paredes chegam no mesmo nó. Nesse caso, o nó é tratado como uma série de ligações de duas em duas, e o maior número se liga primeiro. — [H] [Wall Tool Settings](https://help.graphisoft.com/AC/28/INT/_AC28_Help/150_UserInterfaceToolSettings/150_UserInterfaceToolSettings-3.htm); [S] [KB Graphisoft sobre junções (redirecionada ao fórum)](https://helpcenter.graphisoft.com/knowledgebase/87136/)
- Paredes só se ligam se as linhas de referência se encontram ou se cruzam. Uma auto-interseção, ligada por padrão, estende as linhas que colidem até se encontrarem. — [S] [KB Graphisoft 87136](https://helpcenter.graphisoft.com/knowledgebase/87136/); [S] [How Walls are Connected in Archicad](https://community.graphisoft.com/t5/Getting-started/How-Walls-are-Connected-in-Archicad/ta-p/303922)
- Relação com outros elementos:
  - comandos Connect aparam a parede contra telhado ou casca;
  - um comando ajusta a parede ao topo ou à base de lajes;
  - a parede pode se ligar a curtain wall;
  - um controle diz se a parede é limite de zona, se desconta área/volume da zona ou se não afeta a zona.
  — [H] [Walls and Other Elements](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-18.htm)

**Superfícies e extremidades**
- As superfícies podem ser sobrescritas na face externa (lado da linha de referência), na face interna e nas bordas. Um "cadeado" aplica a mesma superfície a todas as faces. Há opções para alinhar a textura às arestas e para fazer a superfície da ponta herdar a da parede adjacente. — [H] [Wall Tool Settings](https://help.graphisoft.com/AC/28/INT/_AC28_Help/150_UserInterfaceToolSettings/150_UserInterfaceToolSettings-3.htm)
- Linhas de extremidade de parede solta em planta: 4 opções (mostrar ou ocultar uma ou ambas). "Wall Ends" são objetos paramétricos que só podem ser inseridos em paredes, como portas e janelas. — [H] [Wall Tool Settings](https://help.graphisoft.com/AC/28/INT/_AC28_Help/150_UserInterfaceToolSettings/150_UserInterfaceToolSettings-3.htm); [H] [Walls](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-6.htm)

**AC28: guias de distância e esticar**
- No AC28, as guias de distância podem ser ancoradas em qualquer aresta ou ponto, e portas e janelas ganharam pontos de referência (pontas do tamanho nominal e centro). Mover paredes ou vigas no sentido do comprimento com guias passou a esticar ou encurtar o elemento, sem relocá-lo, e as ligações não se quebram. — [S] [Improved Distance Guides AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/005_NewFeatures/005_NewFeatures-5.htm)

**Perfis complexos (Profile Manager)**
- Os perfis são criados no gerenciador de perfis (Opções > Atributos de elemento). O filtro "Use With" decide se o perfil serve para parede, viga, pilar etc. — [S] [Edit Complex Profile AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-54.htm); [S] [Profile Manager AC24](https://help.graphisoft.com/AC/24/INT/_AC24_Help/040_ElementsVB/040_ElementsVB-58.htm)
- Modificadores de estiramento:
  - o perfil pode ter estiramento em largura, em altura ou nos dois;
  - linhas de estiramento marcam a faixa da seção que cresce ou encolhe;
  - o "tamanho nominal" fica editável na parede, viga ou pilar;
  - só valem para paredes, vigas e pilares com perfil.
  — [S] [Stretch Modifiers AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-63.htm)
- Modificadores de deslocamento (offset modifiers): prendem trechos da seção a uma distância fixa de um ponto de ancoragem. Mudar o tamanho do elemento altera os estiramentos, mas não os offsets. O "tamanho total" é a caixa envolvente, incluindo os offsets. Restrição: arestas de hachura que não são horizontais nem verticais e cruzam linhas de estiramento não podem ser usadas em offset. — [S] [Stretch Modifiers](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-63.htm); [S] [Create New Offset Modifier - Example](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-65.htm); [S] [Offset Modifiers: Tips and Tricks](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-67.htm)

**Queixas de usuários**
- Paredes compostas: segundo um moderador, só 2 paredes se aparam bem entre si, e uma terceira complica. O contorno sugerido é fazer as linhas de referência coincidirem num ponto, usar Junction Order nas duas principais e baixar a prioridade da terceira. Outro usuário diz que o sistema de prioridades "não é flexível o bastante" para cobrir todas as interseções. — [S] [Fórum: wall priority help](https://community.graphisoft.com/t5/Modeling/wall-priority-help/m-p/89585/highlight/true); [S] [Fórum: Material Intersection Priority Composite Problem](https://community.graphisoft.com/t5/Modeling/Material-Intersection-Priority-Composite-Problem/m-p/688077)

### Inferences
- Para o BrasBim: a junção por prioridade de material é bem vista porque é feita no modelo e não só no desenho. O ponto fraco é o caso com 3 ou mais paredes compostas. Uma resolução de nó mais explícita (por exemplo, o usuário escolher a ordem das camadas no nó ou uma regra por camada) pode ser um diferencial. No IFC, isso se mapeia para IfcRelConnectsPathElements com ATSTART/ATEND/ATPATH e prioridades de camada (IfcMaterialLayer.Priority no IFC4).
- O excesso de restrições cruzadas (polígono sem composta, trapézio sem inclinação, perfil sem trapézio) sugere tratar essas combinações como **ortogonais** no BrasBim desde o início.

### Lacunas
- Perfis complexos: os modificadores de estiramento e de offset foram cobertos na segunda rodada, mas só por trechos de busca. Não li o editor de perfis por inteiro (hachuras por componente, superfícies por aresta).
- Detalhes oficiais da auto-interseção e da ferramenta "Wall End": só trechos de busca.

---

## 2. Lajes, telhados, cascas, curtain wall, pilares e vigas, escadas e guarda-corpos, malha e terreno, aberturas, objetos e zonas

### Takeaway
O Archicad cobre quase tudo com ferramentas hierárquicas:
- curtain wall, escada e guarda-corpo têm um "esquema" e subcomponentes editáveis num modo de edição próprio;
- pilar e viga são feitos de segmentos;
- o telhado se apoia em linha pivô, e o multiplano é um único elemento;
- a escada é regida por regras normativas e um "Solver";
- a malha (Mesh) é uma TIN com cumeeiras;
- o Morph é a modelagem livre.

A geometria de curtain wall é limitada a superfície plana ou esférica, e a de telhado multiplano assume um único beiral contínuo.

### Cited Findings
**Lajes (Slab)**
- A laje é o bloco horizontal básico (pisos, meios-níveis, forros). Tem plano de referência para controlar ligações. As superfícies de topo, fundo e lado vêm do material e podem ser sobrescritas, e cada aresta pode ter superfície e ângulo próprios. Subtópicos: furos, borda customizada, ajuste de elementos a lajes, gravidade. — [H] [Slabs AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-125.htm)
- Ângulo de borda customizado: selecionar a laje (ou o furo), clicar na aresta e escolher na paleta contextual. O escopo pode ser só a aresta clicada, o polígono selecionado ou todas as arestas, incluindo as dos furos. Uma caixa decide se mudanças no padrão se propagam às bordas customizadas. — [S] [Set Custom Slab Edge Angle AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-129.htm)
- A espessura da laje composta só se edita na definição da composta. — [S] [Set Custom Slab Edge Angle](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-129.htm)
- AC29: opções "Show on Story" ampliadas para lajes (em quais pavimentos a laje aparece). — [S] [AC29 Documentation](https://help.graphisoft.com/AC/29/INT/_AC29_Help/005_NewFeatures/005_NewFeatures-17.htm)
- **A laje é sempre plana.** Segundo um usuário veterano do fórum, a laje só faz placas planas, e placas inclinadas (com bordas em ângulo) se fazem com o telhado, que pode ser definido no 3D por três pontos. Contornos citados:
  - subtrair o topo da laje com um telhado usado como operador de SEO, o que preserva os dados associados (cotas, rótulos);
  - usar a malha para topo inclinado com fundo plano.

  Não é possível converter laje em telhado sem perder os vínculos. O pedido de uma opção "piso inclinado" na laje segue sem atendimento. — [S] [Fórum: Converting Slab to Roof Without Losing…](https://community.graphisoft.com/t5/Modeling/Converting-Slab-Decke-to-Roof-in-Archicad-Without-Losing/td-p/667755); [S] [Fórum: Sloping slabs etc](https://community.graphisoft.com/t5/Modeling/Sloping-slabs-etc/td-p/59382); [S] [Fórum: Sloping with slab tool](https://community.graphisoft.com/t5/Modeling/Sloping-with-slab-tool/td-p/198013)

**Telhados (Roof)**
- Dois métodos: plano único ou multiplano. O multiplano é um elemento só, pode atravessar níveis, e editar um plano reajusta os outros. Cada plano pode ter inclinação e superfície próprias. O multiplano pode ser dividido em telhados de plano único. — [H] [About Roofs AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-60.htm)
- A elevação é medida a partir de uma linha pivô (ou polígono pivô) que não imprime, em geral sobre a linha de referência da parede ou a borda da laje. A inclinação é medida a partir dela. Editar o pivô remodela o telhado. — [H] [About Roofs](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-60.htm)
- Formas de construir o multiplano: complexo, quatro águas, duas águas e versões rotacionadas. Fecha-se o polígono pivô. — [S] [Create a Multi-plane Roof](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-63.htm)
- Plano customizado: clicar no pivô do plano e abrir, pela paleta contextual, inclinação, beiral, superfície e hachura próprios. — [S] [Customize Roof Plane](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-81.htm)
- Telhados e cascas aparam outros elementos, e os comandos Connect mantêm a ligação após edições. A espessura do telhado composto é a soma das camadas, e a primeira camada é a de cima. Em planta, o padrão (desde o AC15) é a projeção 3D real, com uma exibição simbólica antiga como alternativa. — [H] [About Roofs](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-60.htm)
- Pela Magic Wand, clicar na aresta de uma parede cria um telhado multiplano com pivô seguindo o polígono da parede. — [H] [Magic Wand AC26](https://help.graphisoft.com/AC/26/INT/_AC26_Help/030_Interaction/030_Interaction-54.htm)
- AC28, aberturas em telhados:
  - aberturas em telhado de plano único ou multiplano (chaminé, poço de elevador);
  - exibição em planta projetada, que mostra onde a abertura corta o telhado, independente do plano de corte;
  - melhor alinhamento com elementos inclinados;
  - ao dividir o telhado, as aberturas são recriadas.
  — [H] [Openings in Roofs AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/005_NewFeatures/005_NewFeatures-4.htm)
- AC29: a edição de superfícies sobrescritas ligadas passou a funcionar de forma confiável em telhado e casca. — [H] [AC29 Additional Improvements](https://help.graphisoft.com/AC/29/INT/_AC29_Help/005_NewFeatures/005_NewFeatures-27.htm)
- Queixas:
  - o multiplano assume uma linha de beiral única no telhado todo, o que obriga a fazer plano por plano em arquitetura tradicional;
  - pedem camadas diferentes de isolamento no mesmo telhado (multi-composta);
  - lista de desejos antiga: telhados curvos "de verdade" e paredes com topo inclinado.
  — [S] [Fórum Wishes: Couple of improvement request](https://community.graphisoft.com:443/t5/Wishes/Couple-of-improvement-request/td-p/247259); [S] [Wishes AC16](https://community.graphisoft.com:443/t5/Wishes/Post-ur-ARCHICAD-16-Wishes-here/td-p/175202)

**Morph (modelagem livre)**
- O Morph cria sólidos livres sem importar. Formas de criar:
  - entrada normal;
  - "converter seleção em Morph" (junta elementos existentes num Morph só);
  - Magic Wand sobre uma superfície (por exemplo, uma malha);
  - Morph 2D (linhas e planos) no 3D;
  - Morph de revolução;
  - Morph caixa.
  — [H] [Morphs AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-230.htm)
- Edição:
  - mover qualquer vértice, aresta ou face no 3D, com retorno em tempo real e paleta contextual;
  - concordância (fillet) e chanfro;
  - seleção de subelementos;
  - arestas dura, suave ou oculta (as suaves fazem as faces vizinhas agirem como uma só);
  - comandos para suavizar e mesclar faces, curvar arestas e mudar a segmentação;
  - "offset de todas as arestas" de uma face, ao longo do plano de edição.
  — [H] [Morphs](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-230.htm); [S] [Offset Morph Edge AC29](https://help.graphisoft.com/AC/29/INT/_AC29_Help/040_ElementsVB/040_ElementsVB-241.htm)
- Limitações:
  - os booleanos de Morph **não são associativos** (o resultado é permanente), ao contrário das "Solid Element Operations";
  - não há parâmetros geométricos numéricos além da elevação;
  - o Morph só entra nas junções por prioridade depois de "Merge";
  - há comandos de verificar e solidificar para consertar erros de modelagem.
  — [H] [Morphs](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-230.htm)

**Cascas (Shell)**
- Criadas em planta ou no 3D a partir de três formas básicas: extrudada, de revolução ou regrada. Depois podem ser editadas graficamente, rotacionadas livremente, ter o contorno recortado em qualquer forma e receber furos e claraboias. — [H] [About Shells AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-100.htm)
- Parâmetros de cada forma:
  - extrudada: um perfil desenhado num plano (polígono livre ou forma padrão) é extrudado, com ângulos de início, de fim e de distorção;
  - de revolução: o perfil gira em torno de um eixo, com ângulo de revolução e de distorção e segmentação opcional da superfície curva;
  - regrada: superfície entre dois perfis em planos distintos, com regra de ligação dos nós "suave" ou "pareada".
  — [S] [Extruded Shells](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-101.htm); [S] [Revolved Shell example](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-112.htm); [S] [Ruled Shell example](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-114.htm)
- Estrutura: material de construção ou composta (a espessura é a soma das camadas). A casca é uma "membrana" (lado de referência, a primeira camada) com o corpo crescendo para um lado, que pode ser invertido. O lado de referência conta para o cálculo de área de superfície e para as sobrescritas de superfície. Em planta, mostra a geometria 3D real. É elemento de aparo associativo, como o telhado, e aceita Gravity. — [H] [About Shells](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-100.htm)

**Operações sólidas (Solid Element Operations, SEO)**
- Há dois papéis: o alvo (target), que é modificado, e o operador, que não muda. O resultado é **associativo**: editar os participantes atualiza o resultado. Tipos incluem subtração e "subtração com extrusão para cima" (remove também a projeção vertical do operador até o topo do alvo). Fluxo: escolher os alvos, escolher os operadores, escolher a operação e executar. — [S] [Solid Operation Types AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-328.htm); [S] [About Solid Element Operations AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-327.htm); [S] [Solid Operation Example AC26](https://help.graphisoft.com/AC/26/INT/_AC26_Help/040_ElementsVB/040_ElementsVB-328.htm)

**Curtain Wall (fachada-cortina)**
- Um elemento único feito de Frames (montantes e travessas), Panels, Accessories e Junctions, dispostos sobre uma superfície base segundo um esquema editável. Formas de entrada:
  - por contorno (o contorno define tudo);
  - por linha de referência, arco ou polilinha (extrudado).

  **A superfície base só pode ser plana ou esférica.** — [H] [Working with Curtain Walls AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-149.htm)
- Modo de edição:
  - edita ou adiciona membros individuais, mas não cria curtain walls novos;
  - customizar um membro o torna "Custom" e ele deixa de seguir o sistema.
  — [H] [Working with Curtain Walls](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-149.htm)
- Esquema:
  - a unidade do padrão é definida por colunas e linhas, com largura e altura, e se repete até preencher o contorno;
  - o preview permite selecionar e trocar a classe de frame ou painel e definir largura e altura de painéis;
  - adiciona ou remove linhas e colunas (a nova copia a selecionada);
  - rotação das linhas de painéis;
  - um frame diagonal por célula;
  - limpar o padrão;
  - "origem do padrão" com lógica de repetição.
  — [H] [Curtain Wall Scheme Settings AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-156.htm)
- Classes padrão de frame: canto, borda, montante (mullion) e travessa (transom). Todo frame liga-se a outro nas duas pontas. Classes padrão de painel: principal e distinto, mais as do usuário. Acessórios (brise, friso, marquise) se prendem a frames e são colocados um a um no modo de edição (documentado no AC26). — [S] [Curtain Wall Frames AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-151.htm); [S] [Accessories AC26](https://help.graphisoft.com/AC/26/INT/_AC26_Help/040_ElementsVB/040_ElementsVB-173.htm)
- AC28: frames e painéis passam a ter material de construção próprio. Os novos perfis se unem melhor nos cantos, e há opções de vista do modelo em três níveis: esquemático, simplificado e completo. — [S] [Migration Guide AC28: Replace CW Frames/Panels](https://help.graphisoft.com/AC/28/INT/_AC28_Help/010_MigrationGuide/010_MigrationGuide-10.htm)

**Pilares e vigas**
- Desde o AC23, pilar e viga são hierárquicos, com 1 ou mais **segmentos** empilhados num eixo. Cada segmento pode ser retangular, circular ou de perfil, extrudado ou **cônico (tapered)**. — [S] [Beam and Column Tool Renewal AC23](https://help.graphisoft.com/AC/23/int/_AC23_Help/005_NewFeatures/005_NewFeatures-3.htm)
- O comprimento do segmento pode ser fixo ou flexível. Os flexíveis são percentuais que somam 100% e esticam com o pilar. O cônico tem dimensões no topo e na base. Os perfis vêm do gerenciador de perfis, filtrados por "Use With". — [S] [Define Column/Segment Structure AC26](https://help.graphisoft.com/AC/26/INT/_AC26_Help/040_ElementsVB/040_ElementsVB-26.htm); [S] [Tapered Column or Segment AC26](https://help.graphisoft.com/AC/26/INT/_AC26_Help/040_ElementsVB/040_ElementsVB-28.htm)
- Para o modelo analítico: no AC25, a peça cônica ou multissegmento virava uma barra com um único "perfil de substituição". O AC26 passou a exportar seções variáveis no formato SAF. — [S] [SAF tapered AC26](https://help.graphisoft.com/AC/26/INT/_AC26_Help/005_NewFeatures/005_NewFeatures-20.htm)

**Escadas (Stair)**
- Escada para projeto e documentação até 1:50, inserida em planta ou no 3D como uma polilinha. É feita de Segments ligados por Turnings (nós), com retorno gráfico instantâneo, e pode ser ligada a pavimentos. É hierárquica, como o curtain wall. — [H] [About the Stair Tool AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-178.htm)
- Componentes:
  - degraus (pisos), espelhos e estruturas (monolítica, viga, em balanço, banzo/longarina), todos objetos GDL com materiais ou perfis;
  - estruturas e pisos podem ser diferentes para lances e patamares;
  - um modo de edição permite ajustar qualquer degrau ou espelho;
  - componentes customizados são salvos como subtipo;
  - 2D: marca de quebra, linha de piso e numeração, controlados por opções de vista do modelo.
  — [H] [About the Stair Tool](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-178.htm)
- Regras e padrões:
  - faixas permitidas para espelho, piso etc. (para atender norma local);
  - limitam o que se pode digitar;
  - em conflito, o sistema propõe alternativas (o "Solver" oferece várias soluções);
  - ficam no template (por empresa ou região);
  - se a altura de um pavimento mudar muito, as escadas afetadas ficam marcadas.
  — [S] [Stair Settings: Rules and Standards AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-188.htm); [H] [About the Stair Tool](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-178.htm)
- Geometria e posição:
  - largura;
  - número de espelhos e altura do espelho, interdependentes e limitados pelas regras;
  - profundidade do piso flexível (calculada) ou fixa;
  - espelho reto ou inclinado (ângulo ou recuo);
  - tipos de virada: patamar automático, leque com pisos iguais, leque com ângulos iguais;
  - linha de piso centrada por padrão, com deslocamento só no leque de pisos iguais (a largura tem de ser pelo menos 2 vezes esse deslocamento);
  - topo ligado a pavimento, altura fixa ou "flexível" (só antes da entrada);
  - começar e terminar com piso ou espelho;
  - posição da linha base;
  - apagar o pavimento de origem apaga a escada.
  — [H] [Stair Settings: Geometry and Positioning AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-187.htm)
- Histórico: a ferramenta atual substituiu o antigo StairMaker (reformulação no AC21). — [S] [Migrating to AC27](https://help.graphisoft.com/AC/27/INT/_AC27_Help/010_MigrationGuide/010_MigrationGuide-1.htm)
- Queixas:
  - interface "convoluta", com parâmetros aninhados, que leva dias para aprender; pedem retorno gráfico real em vez de uma interface reaproveitada do curtain wall;
  - um usuário de 20 anos diz que é a ferramenta menos intuitiva e que modela degraus como perfil de viga copiado;
  - leques com fundo sempre curvo (só o patamar tem fundo plano), contornado com escadas separadas;
  - relatos de que o método de leque escolhido é ignorado;
  - leques nas duas pontas de um lance simples são frustrantes;
  - truque para leque com número fixo de degraus: usar a paleta contextual nos pontos de virada.
  — [S] [Fórum: Stair tool nightmares](https://community.graphisoft.com/t5/Modeling/Stair-tool-nightmares/m-p/245062/highlight/true); [S] [Fórum: ArchiCAD Stair Tool](https://community.graphisoft.com/t5/Modeling/ArchiCAD-Stair-Tool/td-p/236077); [S] [Fórum: Why winder stairs don't work properly](https://community.graphisoft.com/t5/Modeling/Why-winder-stairs-dont-work-properly/m-p/353077); [S] [Fórum: U-Stair with winders](https://community.graphisoft.com/t5/Modeling/U-Stair-with-winders/m-p/261879); [S] [Central Innovation: U-Shape Stair with Winders](https://centralinnovation.com/?p=52762)

**Guarda-corpos (Railing)**
- Inserido como polilinha (nós e segmentos). Pode ser associado a escada, laje, parede, telhado e malha. — [H] [About the Railing Tool AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-205.htm)
- Hierarquia:
  - corrimão de topo (top rail);
  - até 2 corrimãos (handrails), cada um opcionalmente dos dois lados;
  - barras horizontais (rails) com deslocamento e altura livres;
  - conexões e terminações nas pontas dos horizontais;
  - montantes nos nós (posts);
  - montantes internos (inner posts);
  - balaústres (um padrão dentro do padrão);
  - painéis (limitados por corrimão, barras e montantes).

  Há um editor interativo de padrão por segmento e três níveis de detalhe (completo, simplificado, esquemático). — [H] [About the Railing Tool](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-205.htm)
- Nós:
  - 1, 2 ou 3 montantes por nó;
  - deslocamentos;
  - tratamento da ligação entre segmentos;
  - "continuidade do padrão" (recomeçar ou continuar no nó).
- Montantes internos:
  - o comprimento do padrão vai até o último montante interno;
  - montantes podem ser travados (pelo menos um tem de ficar livre);
  - na distribuição "dividir em divisões", eles se movem.
  — [S] [Node Settings](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-225.htm); [S] [Inner Post Settings](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-221.htm); [S] [Working with Railing Segments and Nodes](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-208.htm)

- Guarda-corpo associativo:
  - na barra de informações da escada, opções "adicionar guarda-corpo" à direita, à esquerda ou dos dois lados criam escada e guarda-corpo juntos;
  - associado à escada, o guarda-corpo segue as mudanças da borda (curvar ou endireitar aresta, inserir ou remover nó) e aparece nos mesmos pavimentos, com a mesma marca de quebra;
  - o espaçamento de balaústres pode seguir a largura do piso;
  - cada segmento é associativo por padrão, mas pode virar "estático";
  - "inverter segmento" não existe em guarda-corpo de escada.
  — [S] [Place Associative Railing AC24](https://help.graphisoft.com/AC/24/INT/_AC24_Help/040_ElementsVB/040_ElementsVB-214.htm); [S] [Stair Input AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-179.htm)

**Malha e terreno (Mesh)**
- O usuário desenha o contorno projetado no plano de referência da malha e depois eleva os pontos característicos. A ferramenta interpola entre eles e gera cumeeiras ("ridges") onde vizinhos têm alturas diferentes. Parâmetros:
  - altura (para baixo do plano de referência);
  - deslocamento do plano em relação ao pavimento;
  - estrutura: só superfície, superfície com "saia" lateral ou sólido;
  - material de construção;
  - 3D com todas as cumeeiras duras, só as do usuário duras ou tudo suave.
  — [H] [Mesh Tool Settings AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/150_UserInterfaceToolSettings/150_UserInterfaceToolSettings-6.htm)
- Ao adicionar pontos, duas opções de ajuste: "ajustar às cumeeiras do usuário" (preserva só essas e muda a triangulação) ou "ajustar a todas" (preserva todas, mas pode gerar muitas cumeeiras). — [S] [Add New Points to the Mesh](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-133.htm)
- Levantamento topográfico: um arquivo texto XYZ é convertido automaticamente em malha. É posicionado por clique ou pela origem do arquivo, e dá para definir a cota do zero do projeto acima do nível do mar. — [S] [Other Formats Opened by Archicad](https://help.graphisoft.com/AC/28/INT/_AC28_Help/120_Interoperability/120_Interoperability-7.htm)
- A malha também aceita furos. — [S] [Create a Hole in the Mesh](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-134.htm)

**Aberturas (Opening tool, desde o AC23)**
- Abertura vazia que corta paredes, lajes, malhas, telhados e vigas. Por padrão é **infinita** (o comprimento não depende do elemento cortado). Pode ser limitada:
  - de um lado: nicho ou rebaixo, com a face coincidindo com o plano de referência do hospedeiro, mais deslocamento;
  - dos dois lados: comprimento numérico ou gráfico.

  Pode ser invertida. — [S] [Openings AC24](https://help.graphisoft.com/AC/24/INT/_AC24_Help/040_ElementsVB/040_ElementsVB-318.htm); [S] [Use Limited Opening AC24](https://help.graphisoft.com/AC/24/INT/_AC24_Help/040_ElementsVB/040_ElementsVB-321.htm); [S] [New Opening Tool AC23](https://help.graphisoft.com/AC/23/INT/_AC23_Help/005_NewFeatures/005_NewFeatures-9.htm)
- "Criar aberturas a partir da seleção" converte em abertura um elemento que colide com parede, laje, malha, telhado ou viga. — [S] [Create Openings from Selection AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-268.htm)
- AC26: superfícies sobrescritas separadas para a extrusão e para a ponta da abertura. — [S] [Opening Tool Surface overrides AC26](https://help.graphisoft.com/AC/26/INT/_AC26_Help/005_NewFeatures/005_NewFeatures-11.htm)
- AC29: portas, janelas e aberturas podem ser inseridas diretamente em corte, elevação e elevação interna, com qualquer alinhamento ou método, mesmo quando o hospedeiro não é paralelo à linha de corte. Há também novas configurações padrão de porta e janela. — [H] [Directly Input Openings in Section/Elevation AC29](https://help.graphisoft.com/AC/29/INT/_AC29_Help/005_NewFeatures/005_NewFeatures-3.htm); [H] [AC29 Productivity](https://help.graphisoft.com/AC/29/INT/_AC29_Help/005_NewFeatures/005_NewFeatures-2.htm)
- Janela e porta em parede inclinada ou de perfil complexo têm um "plano da janela" configurável. — [S] [Setting the Window/Door Plane in Slanted or Complex Walls](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-309.htm)

**Objetos e móveis**
- Componentes de escada e guarda-corpo são objetos GDL. A Tracker mostra os valores de hotspots GDL durante a edição. — [H] [About the Stair Tool](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-178.htm); [H] [Tracker AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/030_Interaction/030_Interaction-40.htm)
- AC29, armários de cozinha: nova lógica "padrão" de pés, com a antiga mantida como "custom". — [S] [Kitchen Cabinet Improvements AC29](https://help.graphisoft.com/AC/29/INT/_AC29_Help/005_NewFeatures/005_NewFeatures-10.htm)
- Inserção de objeto:
  - escolher a ferramenta, navegar nas pastas da biblioteca, ajustar as configurações e clicar;
  - editar as configurações não altera o arquivo da biblioteca;
  - o hotspot principal é a âncora, mas qualquer outro hotspot (marcado com X) pode ser escolhido como ponto de inserção;
  - quatro métodos de geometria: ortogonal; diagonal e diagonal rotacionado (definem as dimensões A e B graficamente, se o objeto for esticável); e um quarto que a fonte não nomeia.
  — [S] [Placing an Object AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-283.htm); [S] [Stretching Objects](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-285.htm)
- Hotspots editáveis (losangos): clicar num deles abre a Tracker para digitar o valor do parâmetro, junto com os ícones de esticar ou mover nó da paleta contextual. — [S] [Graphical Editing Using Editable Hotspots AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-287.htm)
- Parâmetros de objeto: A e B são obrigatórios, e os demais podem ser criados ou apagados. Os valores definidos no editor GDL viram os padrões do diálogo. Objetos de bibliotecas vinculadas precisam ser extraídos antes de editar. Elementos 3D podem ser salvos como objeto. — [S] [Parameters AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/140_UserInterfaceDialogBoxes/140_UserInterfaceDialogBoxes-59.htm); [S] [Open and Edit Library Part](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-301.htm); [S] [Save 3D Elements as Objects](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-293.htm)
- PARAM-O:
  - ambiente de nós para criar objetos paramétricos sem escrever GDL, só para assinantes (SSA/Forward);
  - liga-se, por exemplo, um nó de comprimento à entrada "Size X" de um nó de bloco e marca-se "criar parâmetro" para expor o valor no diálogo do objeto;
  - o resultado é salvo como objeto comum na biblioteca embutida e funciona mesmo sem o PARAM-O instalado.
  — [S] [PARAM-O: Making an Object Parametric](https://help.graphisoft.com/AC/28/INT/_AC28_Help/065_PARAM-O/065_PARAM-O-7.htm); [S] [PARAM-O Reference Guide](https://help.graphisoft.com/AC/28/INT/_AC28_Help/065_PARAM-O/065_PARAM-O-1.htm); [S] [Creating an Object](https://help.graphisoft.com/AC/28/INT/_AC28_Help/065_PARAM-O/065_PARAM-O-6.htm)

**Zonas**
- A parede pode ser limite de zona, descontar a zona ou não afetar. — [H] [Walls and Other Elements](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-18.htm)
- Criação:
  - automática, por clique dentro de um contorno fechado de paredes ou curtain walls, em dois métodos: face interna (vai até as faces internas das paredes) ou linha de referência (vai até as linhas de referência);
  - manual, por polilinha, retângulo ou retângulo rotacionado, para quando não há contorno fechado (por exemplo, estudo de massas).
  — [S] [Creating Zones AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-137.htm)
- Vazamentos de contorno: usar o método manual, uma "porta de abertura vazia" na parede ou uma linha, arco ou spline marcada como limite de zona. O carimbo da zona guarda o ponto clicado, que serve de semente para as atualizações. **Zonas automáticas não se atualizam sozinhas**: é preciso rodar o comando de atualizar zonas. — [S] [Creating Zones](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-137.htm); [S] [Updating Zones](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-147.htm); [S] [Zone Stamps](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-142.htm)
- Áreas:
  - "área medida" vai até as linhas de referência das paredes limite;
  - "área líquida medida" vai até as faces internas;
  - "área reduzida" desconta elementos (paredes, pilares, curtain walls acima de uma área mínima configurável nas preferências);
  - "área calculada" aplica ainda uma redução percentual opcional.
  — [S] [Creating Zones](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-137.htm); [S] [Zones Preferences](https://help.graphisoft.com/AC/28/INT/_AC28_Help/140_UserInterfaceDialogBoxes/140_UserInterfaceDialogBoxes-27.htm)
- AC29: o painel de cálculo de área da zona foi reorganizado. — [H] [AC29 Additional Improvements](https://help.graphisoft.com/AC/29/INT/_AC29_Help/005_NewFeatures/005_NewFeatures-27.htm)

**Contexto de versões**
- AC27: Design Options integradas, edição manual do modelo analítico estrutural, importação e exportação FBX, gestão de atributos com pastas. — [S] [New Features AC27](https://help.graphisoft.com/AC/27/INT/_AC27_Help/005_NewFeatures/005_NewFeatures-1.htm)
- AC28 ("Smart Design"): Keynotes, aberturas em telhados, guias de distância melhoradas, Design Options melhoradas, PBR, ligação Rhino-Grasshopper, AI Visualizer, ACV (LCA). — [H] [AC28 Smart Design](https://help.graphisoft.com/AC/28/INT/_AC28_Help/005_NewFeatures/005_NewFeatures-2.htm)
- AC29: abertura em corte e elevação, rotação rápida, resolução de vistas 3D, armários, MEP Designer integrado, suporte a IFC 4.3, importação OBJ. — [H] [AC29 Productivity](https://help.graphisoft.com/AC/29/INT/_AC29_Help/005_NewFeatures/005_NewFeatures-2.htm); [S] [AC29 Collaboration/Interoperability](https://help.graphisoft.com/AC/29/INT/_AC29_Help/005_NewFeatures/005_NewFeatures-26.htm)
- Uma página de notícias de terceiros já anuncia o Archicad 30 (portfólio Graphisoft 2026), sem lista de funções de modelagem. — [H] [architosh (link do AC29 que redirecionou para conteúdo AC30)](https://architosh.com/2025/10/graphisoft-releases-archicad-29-with-game-changing-tools/amp)

### Inferences
- Curtain wall, escada e guarda-corpo compartilham o padrão "esquema do sistema + membro customizado no modo de edição". Para o BrasBim, isso sugere um mecanismo genérico de "elemento composto com overrides por instância" (no IFC: IfcElementAssembly ou IfcCurtainWall/IfcStair/IfcRailing com decomposição IfcRelAggregates).
- As regras de escada como "faixas + Solver que propõe alternativas" encaixam bem com a NBR 9050 e a NBR 9077 (fórmula de Blondel, altura máxima de espelho). Um template ABNT pronto seria um diferencial claro sobre o Archicad, que deixa as faixas para o usuário preencher.
- A malha do Archicad é uma TIN com pontos e cumeeiras. A importação XYZ é simples, e não vi menção a importar curvas de nível de DWG pela malha (ver Lacunas).

### Lacunas
- Cascas, zonas e objetos foram preenchidos na segunda rodada, quase tudo por trechos de busca [S]. Não foram cobertas as categorias de zona e as propriedades do carimbo.
- Laje inclinada: confirmado só pelo fórum [S]. A documentação oficial não diz explicitamente que a laje tem de ser plana.
- Páginas detalhadas dos tipos de virada da escada (opções de patamar e leque) e da associação guarda-corpo–escada.
- Curvas de nível de DWG para malha: não confirmado.

---

## 3. Modelo de entrada e interação

### Takeaway
A entrada do Archicad gira em torno de cinco coisas:
- um **cursor inteligente** que muda de forma conforme o que está embaixo (vértice, aresta, superfície);
- a **Tracker** (caixa de coordenadas que segue o cursor e aceita digitação direta, com atalhos X/Y/A/D e aritmética);
- **guias** (guias de snap temporárias, linhas-guia persistentes, pontos de snap por divisão, guias de distância);
- a **paleta contextual** ("pet palette"), que surge ao clicar em vértice ou aresta de um elemento selecionado com os comandos de edição cabíveis (offset de aresta, curvar, adicionar ou subtrair polígono);
- **Magic Wand** (barra de espaço: traça um polígono a partir de elementos existentes) e **Gravity** (assentar um elemento novo em laje, telhado, casca ou malha).

### Cited Findings
**Tracker**
- Mostra comprimento, ângulo e hotspots GDL ao lado do cursor. A tecla N exibe a Tracker na hora. — [H] [Tracker AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/030_Interaction/030_Interaction-40.htm)
- Formas de entrada:
  - digitar direto no campo padrão (o que está em negrito);
  - Tab entre os campos;
  - atalhos X, Y, Z, D/R ou A seguidos do valor, em qualquer ordem;
  - operadores + - * / (por exemplo, "2*" dobra a distância medida).

  Enter aplica e sai, Esc cancela. Um ícone de mira move o elemento à coordenada e mostra as guias. — [H] [Tracker](https://help.graphisoft.com/AC/28/INT/_AC28_Help/030_Interaction/030_Interaction-40.htm)
- Modos de coordenada:
  - XY ou distância/ângulo (polar), alternados com "/";
  - relativas (padrão, a partir da origem de edição) ou absolutas (a partir da origem do usuário, com linha tracejada);
  - ao "pegar" uma guia de snap, a origem do usuário vai temporariamente para o ponto de referência.

  Os campos visíveis dependem da ação: curvar uma aresta mostra o raio. — [H] [Tracker](https://help.graphisoft.com/AC/28/INT/_AC28_Help/030_Interaction/030_Interaction-40.htm)

**Guias e snaps**
- Auxílios de tela listados oficialmente:
  - cursor inteligente, destaque de seleção, Tracker, régua, medir;
  - grade de construção e grade de snap;
  - guias de snap, linhas-guia, pontos de snap;
  - plano de edição no 3D;
  - Magic Wand, Gravity;
  - restrições de mouse e de coordenadas;
  - métodos relativos de construção;
  - snap em elementos existentes e raio de snap do cursor.
  — [H] [On-Screen Input Aids AC26](https://help.graphisoft.com/AC/26/INT/_AC26_Help/030_Interaction/030_Interaction-38.htm)
- Guias de snap:
  - temporárias (somem quando o cursor sai) e podem ser fixadas;
  - "referências de snap" escolhem quais guias aparecem;
  - linhas-guia são persistentes, e Shift trava a entrada numa delas;
  - pontos de snap duram cerca de 5 s, com intervalos: metade, divisões, percentual, distância, "melhor divisão por distância".
  — [S] [Snap Guides AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/030_Interaction/030_Interaction-46.htm); [S] [Guide Lines AC25](https://help.graphisoft.com/AC/25/INT/_AC25_Help/030_Interaction/030_Interaction-52.htm); [S] [Snap Points AC26](https://help.graphisoft.com/AC/26/INT/_AC26_Help/030_Interaction/030_Interaction-49.htm)
- Guias de distância: experimentais no AC27, oficiais e melhoradas no AC28 (âncora em qualquer aresta ou ponto, referências de porta e janela, esticar em vez de mover). — [S] [Distance Guides experimental AC27](https://help.graphisoft.com/AC/27/INT/_AC27_Help/030_Interaction/030_Interaction-65.htm); [S] [Improved Distance Guides AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/005_NewFeatures/005_NewFeatures-5.htm)

**Paleta contextual e plano de edição**
- Clicar numa aresta de polígono e usar "offset de aresta" desloca o lado inteiro e estica as arestas vizinhas. Elementos em cadeia (por exemplo, paredes encadeadas) são tratados temporariamente como polígono, com todas as opções de remodelagem. — [S] [Reshaping Polygons and Chained Elements AC18](https://help.graphisoft.com/AC/18/INT/AC18Help/02_Interaction/02_Interaction-110.htm)
- Na edição gráfica 3D, o cursor se move sobre o "plano de edição", que pode ser reposicionado ou trocado. No Morph, só os planos adjacentes ficam disponíveis. — [S] [Reposition Editing Plane AC26](https://help.graphisoft.com/AC/26/INT/_AC26_Help/030_Interaction/030_Interaction-53.htm); [S] [Offset Morph Edge AC29](https://help.graphisoft.com/AC/29/INT/_AC29_Help/040_ElementsVB/040_ElementsVB-241.htm)

**Magic Wand**
- Atalho: barra de espaço. Comportamento:
  - clicar em aresta ou nó traça o elemento ou a cadeia;
  - clicar no vazio traça a área fechada formada pelos elementos mais próximos;
  - segurar a barra mostra um preview, e o cursor indica nó, aresta ou vazio;
  - curvas são aproximadas conforme configuração própria;
  - pré-selecionar elementos restringe a busca;
  - o elemento novo usa os padrões da ferramenta e **não fica ligado** ao original;
  - também serve para somar ou subtrair polígono (por exemplo, recortar uma laje pela forma de outro elemento) e combina com offset ou multi-offset.
  — [H] [Magic Wand AC26](https://help.graphisoft.com/AC/26/INT/_AC26_Help/030_Interaction/030_Interaction-54.htm)

**Gravity**
- Só para colocar elementos novos (paredes, pilares, vigas, objetos, cotas de nível), não para editar. O elemento assenta em laje, telhado, casca ou malha do mesmo pavimento e pega a cota da superfície. Árvores, por exemplo, seguem a malha ponto a ponto, e a cota de nível fica associada à superfície. Sem superfície embaixo, usa a cota das configurações. Pensado para a planta; no 3D, o "snap em superfície" faz o equivalente. — [H] [Gravity AC26](https://help.graphisoft.com/AC/26/INT/_AC26_Help/030_Interaction/030_Interaction-56.htm)

**Rotação rápida (AC29)**
- Gira a seleção 90° com atalho (Ctrl/Cmd+R, e com Shift no sentido contrário), personalizável. Está no menu Edit > Move e na barra de arrastar. A Graphisoft diz que poupa 4 passos em relação ao Rotate normal. — [H] [Quickly Rotate Elements AC29](https://help.graphisoft.com/AC/29/INT/_AC29_Help/005_NewFeatures/005_NewFeatures-6.htm)

**Favorites (configurações salvas)**
- Paleta própria para organizar, aplicar, criar, importar e exportar conjuntos de configurações por ferramenta. — [S] [Favorites Palette AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/020_Configuration/020_Configuration-62.htm)
- Criar e aplicar:
  - para criar, seleciona-se um elemento e escolhe-se "novo favorito";
  - aplicar com elementos selecionados os altera; aplicar sem seleção define o padrão da ferramenta;
  - um "conjunto de transferência" define quais parâmetros são aplicados.
  — [S] [Create New Favorite](https://help.graphisoft.com/AC/28/INT/_AC28_Help/020_Configuration/020_Configuration-58.htm); [S] [Apply a Favorite](https://help.graphisoft.com/AC/28/INT/_AC28_Help/020_Configuration/020_Configuration-56.htm)
- Manutenção: dá para editar vários favoritos da mesma ferramenta de uma vez (só pela paleta) e redefinir um favorito a partir de um elemento selecionado. — [S] [Edit Settings of One or More Favorites](https://help.graphisoft.com/AC/28/INT/_AC28_Help/020_Configuration/020_Configuration-60.htm); [S] [Redefine Favorite](https://help.graphisoft.com/AC/28/INT/_AC28_Help/020_Configuration/020_Configuration-59.htm)

**Graphic Overrides (sobrescritas gráficas)**
- Regras por critério mudam a aparência (hachuras, canetas, superfícies) dos elementos que atendem ao critério, sem alterar o elemento. O critério começa sempre pelo tipo de elemento, com condições extras de parâmetros e propriedades e controle e/ou. — [S] [Graphic Override Rules AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/050_ViewsVB/050_ViewsVB-138.htm); [S] [Define Element Criteria AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/030_Interaction/030_Interaction-29.htm)
- Ordem e critérios:
  - as regras são agrupadas em "combinações" e aplicadas de cima para baixo; em conflito, vence a de cima;
  - as regras do filtro de reforma ficam sempre por último;
  - desde o AC21, o status de reforma pode ser critério;
  - desde o AC26, é possível adicionar várias regras de uma vez.
  — [S] [Graphic Override Combinations](https://help.graphisoft.com/AC/28/INT/_AC28_Help/050_ViewsVB/050_ViewsVB-139.htm); [S] [Graphic Override Setup AC26](https://help.graphisoft.com/AC/26/INT/_AC26_Help/005_NewFeatures/005_NewFeatures-10.htm)

**Propriedades e classificações**
- Propriedades são dados opcionais definidos pelo usuário. A classificação do elemento decide quais propriedades ficam disponíveis para ele. Tipos de dado: texto, número, inteiro, área, comprimento, ângulo, volume, lista de tags, conjunto de opções, verdadeiro/falso. — [S] [Properties and Classification Systems AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/045_PropertiesClassifications/045_PropertiesClassifications-1.htm); [S] [Property Manager](https://help.graphisoft.com/AC/28/INT/_AC28_Help/045_PropertiesClassifications/045_PropertiesClassifications-5.htm)
- Propriedades por expressão: fórmulas sobre parâmetros e propriedades do próprio elemento, do ambiente (zona, hotlink pai) ou do projeto, com funções como CONCAT e arredondamentos. Aparecem em quantitativos, rótulos e carimbos. Lista de tags e conjunto de opções não podem ser definidos por expressão, e propriedades de materiais de construção não são avaliadas. — [S] [Expression-Defined Element Properties](https://help.graphisoft.com/AC/28/INT/_AC28_Help/045_PropertiesClassifications/045_PropertiesClassifications-9.htm); [S] [Expression examples](https://help.graphisoft.com/AC/28/INT/_AC28_Help/045_PropertiesClassifications/045_PropertiesClassifications-13.htm)

**Esticar entre pavimentos**
- Um usuário não achou forma de esticar paredes, telhados e lajes juntos entre níveis. O contorno é a seleção Marquee "grossa", que afeta todos os pavimentos (a fina afeta só o atual). — [S] [Fórum: Couple of questions about Archicad](https://community.graphisoft.com/t5/Modeling/Couple-of-questions-about-Archicad/td-p/113810)

### Inferences
- O que dá a sensação de velocidade é o trio digitação direta na Tracker + Magic Wand + paleta contextual por aresta e vértice. Para o BrasBim, isso conversa com a memória de UX do projeto (barra de opções contextual, mini-barra de seleção): a paleta contextual do Archicad é, na prática, uma mini-barra de seleção.
- Magic Wand gera elementos **sem vínculo** com a origem. Um diferencial possível é a opção de manter a associação (por exemplo, uma laje que segue o contorno das paredes).
- Gravity só vale na criação. Uma opção de "reassentar" um elemento já existente é uma melhoria simples.

### Lacunas
- Favorites, Graphic Overrides e propriedades/classificações foram cobertos na segunda rodada, só por trechos de busca [S].
- Detalhes das restrições de mouse e coordenadas e dos "métodos relativos de construção".

---

## 4. Limitações conhecidas e queixas frequentes (consolidado)

### Takeaway
As queixas recorrentes têm cinco focos: a ferramenta de escada (complexa, com leques problemáticos), os nós de 3 ou mais paredes compostas, o telhado multiplano rígido com beiral único, a falta de telhados curvos e paredes de topo inclinado, e a superfície de curtain wall limitada a plano ou esfera. Também chama atenção a perda de associatividade do Morph e da Magic Wand.

### Cited Findings
- Escada: interface aninhada, curva de aprendizado de dias, leques com fundo curvo e método de leque ignorado. — [S] [Stair tool nightmares](https://community.graphisoft.com/t5/Modeling/Stair-tool-nightmares/m-p/382249); [S] [Why winder stairs don't work properly](https://community.graphisoft.com/t5/Modeling/Why-winder-stairs-dont-work-properly/m-p/353077); [S] [half-landing stairs with winders](https://community.graphisoft.com/t5/Modeling/half-landing-stairs-with-winders/m-p/249615)
- Junções de compostas com 3 paredes e sistema de prioridade pouco flexível. — [S] [wall priority help](https://community.graphisoft.com/t5/Modeling/wall-priority-help/td-p/89562/page/3?p=82488); [S] [Lines in composite walls](https://community.graphisoft.com:443/t5/Modeling/Lines-in-composite-walls/m-p/340104/highlight/true)
- Telhado multiplano com beiral único, falta de multi-composta, desejo de telhado curvo e parede de topo inclinado. — [S] [Wishes: Couple of improvement request](https://community.graphisoft.com:443/t5/Wishes/Couple-of-improvement-request/td-p/247259); [S] [Wishes AC16](https://community.graphisoft.com:443/t5/Wishes/Post-ur-ARCHICAD-16-Wishes-here/td-p/175202)
- Curtain wall: superfície base só plana ou esférica. — [H] [Working with Curtain Walls](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-149.htm)
- Morph: booleanos não associativos, sem parâmetros numéricos, e só entra na prioridade de junção depois de Merge. — [H] [Morphs](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-230.htm)
- Restrições de parede: polígono sem composta, trapézio e polígono sem inclinação, toras só em parede básica reta. — [H] [Wall Tool Settings](https://help.graphisoft.com/AC/28/INT/_AC28_Help/150_UserInterfaceToolSettings/150_UserInterfaceToolSettings-3.htm); [H] [Create a Log Wall](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-17.htm)
- Planta: a exibição simbólica pode divergir do 3D. — [H] [Basic Intersection Principles](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-271.htm)
- Migração: arquivos de versões antigas precisam ser abertos e salvos em versões intermediárias (17–28 para abrir no 29). — [S] [Migrating to Archicad 29](https://help.graphisoft.com/AC/29/INT/_AC29_Help/010_MigrationGuide/010_MigrationGuide-1.htm)

### Inferences
- Ideias de "igual ou melhor" para o BrasBim, em ordem de impacto provável:
  1. escada com regras ABNT de fábrica e edição direta no 3D;
  2. junções multi-parede previsíveis, por camada;
  3. telhado com beirais em alturas diferentes por plano;
  4. curtain wall sobre superfícies mais gerais;
  5. Magic Wand e booleanos com opção associativa.

### Lacunas
- Laje só plana: o pedido de "piso inclinado" na laje não foi atendido, e os contornos (telhado ou SEO) quebram vínculos ou exigem passos extras. — [S] [Fórum: Converting Slab to Roof](https://community.graphisoft.com/t5/Modeling/Converting-Slab-Decke-to-Roof-in-Archicad-Without-Losing/td-p/667755)
- Zonas automáticas exigem atualização manual. — [S] [Creating Zones AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-137.htm)
- O Reddit r/ArchiCAD não está acessível (domínio bloqueado para a ferramenta de busca e de leitura).
- Não foi possível abrir as páginas do fórum oficial (HTTP 403). As citações de fórum vêm só dos trechos do buscador e devem ser conferidas antes de citar em spec.
- Não há dados quantitativos (votos na wishlist, frequência das queixas).
