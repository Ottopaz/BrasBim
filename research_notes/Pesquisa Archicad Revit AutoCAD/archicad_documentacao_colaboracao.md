# Archicad (27/28/29): documentação, colaboração, interoperabilidade e experiência de uso

> Pesquisa clean-room, só com fontes públicas na web. Data de acesso de todas as URLs: **2026-10-21**.
> Tudo foi resumido com palavras próprias. Nomes de comandos aparecem só para identificar a função descrita.
> Nada foi lido de `_restrito/` nem de `tools/`, e nenhum binário foi inspecionado.
> Observação de método: várias páginas do help oficial do AC28/AC29 trazem só índices (títulos e links), sem texto. Onde isso aconteceu, a nota registra apenas o título do recurso. A comunidade Graphisoft e o G2 responderam HTTP 403 ao fetch direto. Desses sites só aproveitei os trechos que vieram nos resultados de busca.

## 1. Vistas e documentação (plantas, cortes, folhas, revisões, anotação, tabelas, sobreposições gráficas, keynotes)

### Takeaway
A documentação do Archicad se organiza assim: modelo → vista salva (com camadas, escala, filtro de reforma e sobreposições gráficas) → desenho colocado em layout (folha). Tudo isso fica num navegador em árvore com quatro mapas (projeto, vistas, livro de layouts, conjuntos de publicação). Sobre essa base há revisões rastreadas por "changes" e "transmittal sets", tabelas interativas bidirecionais e, desde o AC28, um sistema de keynotes com banco hierárquico. Os lançamentos recentes (AC28/29) refinaram esses pontos sem mudar a arquitetura.

### Cited Findings
**Navegador e estrutura de vistas/folhas**
- O Navigator é uma árvore com quatro abas: Project Map (pontos de vista do modelo), View Map (vistas salvas), Layout Book (folhas) e Publisher Sets (conjuntos de publicação). Alterações no modelo se propagam para as vistas, os layouts e os conjuntos ligados. — [Graphisoft Community, "Archicad Basic Concepts - The Navigator"](https://community.graphisoft.com/t5/Getting-started/Archicad-Basic-Concepts-The-Navigator/ta-p/303987) (via resultado de busca; a página deu 403 no fetch)
- O master layout define o tamanho da folha e fica numa pasta "Masters" dentro do Layout Book. O que se desenha no master aparece em todos os layouts que o usam. O carimbo é desenhado com as ferramentas 2D, e a ferramenta de texto insere campos automáticos (AutoText). O master é atribuído pelas configurações de cada layout. — mesma fonte acima
- Publisher Sets são coleções de itens que apontam para vistas ou layouts. Ficam salvos no projeto, então podem ser republicados depois. Pastas inteiras do Layout Book ou do View Map podem entrar como atalho. — [Publisher Function (AC25 help)](https://help.graphisoft.com/AC/25/INT/_AC25_Help/070_Documentation/070_Documentation-125.htm)

**Revisões (changes, revision IDs, transmittal sets)**
- O módulo Revision Management acompanha como o projeto muda entre os conjuntos de layouts emitidos. Os subtemas do help são: fluxo de trabalho, esquemas padrão no template, trabalhar com changes, feedback de revisões de layout, Revision IDs, gestão de transmittal sets, lista de changes e histórico de emissões, revisões no Publisher e changes vindos de arquivos externos. — [Revision Management (AC28 help)](https://help.graphisoft.com/AC/28/INT/_AC28_Help/070_Documentation/070_Documentation-97.htm)
- A numeração automática de revisões só funciona se os changes estiverem associados a elementos. Quando um change novo aparece num layout depois do último transmittal set, uma nova revisão do layout é criada sozinha. Só a revisão mais recente pode ser editada, e as já emitidas ficam travadas. Para cada emissão, o fluxo é atualizar os desenhos de todo o Layout Book e então criar o próximo transmittal set, que inclui os layouts com revisão nova e os layouts novos. — [Revision Management Workflow (AC25 help)](https://help.graphisoft.com/AC/25/INT/_AC25_Help/070_Documentation/070_Documentation-106.htm) (resumido do resultado de busca)
- Problema típico relatado por usuário: ao criar um layout novo a partir de uma planta existente, as nuvens e marcas de changes antigos vieram junto. A solução da comunidade foi uma combinação de ocultar a 1ª revisão no objeto de histórico com um transmittal set separado configurado sem marcadores. É uma gambiarra, não um recurso. — [Graphisoft Community, "Hide Change Marker for new layouts"](https://community.graphisoft.com/t5/Project-data-BIM/Hide-Change-Marker-for-new-layouts/m-p/354462) (via resultado de busca)

**Sobreposições gráficas e filtro de reforma**
- Uma Graphic Override Combination é uma lista ordenada de regras (critério → aparência). O filtro de reforma (Renovation Filter) é outra via, baseada no status do elemento (Novo, Existente, A demolir). As regras da combinação têm prioridade, e o filtro de reforma fica por último. Os dois são salvos por vista. Não podem ser aplicados em vistas de corte/elevação do tipo "drawing" ou de reconstrução manual. — [Graphic Overrides (MEP Designer 29 help, mesma base do Archicad)](https://help.graphisoft.com/MEP/29/INT/_MEP_Designer_Help/050_ViewsVB/050_ViewsVB-119.htm); [Graphic Overrides by Renovation Status (AC21 help)](https://help.graphisoft.com/AC/21/INT/AC21Help/03_2_Views_Virtual_Building/03_2_Views_Virtual_Building-144.htm) (via resultado de busca)
- As regras de sobreposição substituíram as antigas opções de preenchimento do Model View Options a partir do Archicad 20, e os três estilos de reforma viraram regras predefinidas. — [Migration Guide AC27: Model View Fill Options Replaced by Graphic Overrides](https://help.graphisoft.com/AC/27/INT/_AC27_Help/010_MigrationGuide/010_MigrationGuide-14.htm) (via resultado de busca)
- AC29: os marcadores de corte, elevação, elevação interna, detalhe e worksheet passaram a ter status de reforma próprio, para não aparecerem em vistas erradas (ex.: marcador de corte de uma ala nova escondido nas vistas de "existente"). Por padrão o marcador herda o status do elemento associado. Arquivos antigos recebem o status automaticamente na migração. Quando nenhum filtro mostra o marcador, o sistema cria marcadores "vinculados" e avisa numa central de notificações (Action Center). — [AC29 New Features: Renovation Status for Markers](https://help.graphisoft.com/AC/29/INT/_AC29_Help/005_NewFeatures/005_NewFeatures-24.htm)

**Tabelas e quantitativos**
- A Interactive Schedule é uma lista editável nos dois sentidos, ligada aos elementos do projeto. Ela fica no Project Map, pode ser salva como vista e colocada em layout. Há listas de elementos (cada elemento com seus parâmetros) e listas de componentes (para levantamento de materiais, quantitativos e listas de preço). — [Interactive Schedule (AC22 help)](https://help.graphisoft.com/AC/22/INT/_AC22_Help/070_Documentation/070_Documentation-128.htm) (via resultado de busca)
- A antiga função Calculation é considerada legada até no help do AC29 e não suporta, por exemplo, escadas e guarda-corpos (desde o AC21). — [Calculation (Legacy), AC29 help](https://help.graphisoft.com/AC/29/INT/_AC29_Help/070_Documentation/070_Documentation-124.htm)
- AC29 lista "Schedule Format Improvements" (mais formatação, cor e opções de exibição para visualização de dados), além de setas diferentes no início e no fim de linhas e a ampliação das opções "Show on Story" de lajes. — [AC29 New Features: Documentation](https://help.graphisoft.com/AC/29/INT/_AC29_Help/005_NewFeatures/005_NewFeatures-17.htm); [Architosh, out/2025](https://architosh.com/2025/10/graphisoft-releases-archicad-29-with-game-changing-tools/)

**Keynotes (AC28 em diante)**
- AC28 introduziu Keynotes: um banco de chaves de identificação (cada chave com título, descrição e referência) em pastas hierárquicas num painel próprio, com favoritos. Os rótulos de keynote são colocados direto do painel ou aplicados por autotexto a vários elementos de uma vez. Uma legenda de keynotes no layout lista as keynotes visíveis nos desenhos ou todas as do projeto, com filtro por pasta. O banco pode ser exportado e reimportado em XML ou Excel. — [AC28 New Features: Keynotes](https://help.graphisoft.com/AC/28/INT/_AC28_Help/005_NewFeatures/005_NewFeatures-3.htm)
- AC29 melhorou a legenda: formatação separada por campo, separador configurável em colunas mescladas, cores de fundo para keynotes e pastas, e o texto-placeholder deixou de aparecer em layouts sem keynotes. — [AC29 New Features: Keynote Legend Improvements](https://help.graphisoft.com/AC/29/INT/_AC29_Help/005_NewFeatures/005_NewFeatures-23.htm)

**Outros itens recentes de documentação/produtividade**
- AC28, grupo "Smart Design": Keynotes, aberturas em telhados, guias de distância melhoradas, Design Options aprimoradas, PBR, mais opções de rótulos de texto, conexão Rhino-Grasshopper, AI Visualizer, Avaliação de Ciclo de Vida (LCA) e BIMm Tool para nuvem de pontos (só títulos). — [AC28 New Features: Smart Design](https://help.graphisoft.com/AC/28/INT/_AC28_Help/005_NewFeatures/005_NewFeatures-2.htm)
- Design Options (introduzidas no AC27): alternativas de projeto em Options e Option Sets, cada set com uma opção padrão. Há um painel para criar, renomear e buscar. Os critérios "nome da opção" e "nome do set" existem em Find & Select, sobreposições gráficas e tabelas. O tooltip mostra a opção do elemento, e elementos com opção ausente ficam destacados em cor. No Teamwork o painel é reservável. — [Enhanced Design Options (AC28 help)](https://help.graphisoft.com/AC/28/INT/_AC28_Help/005_NewFeatures/005_NewFeatures-6.htm)
- AC29: rotação de 90° por atalho; aberturas inseridas direto em corte e elevação (inclusive em elementos não paralelos); filtro e seleção de vistas não usadas; resolução/DPI configurável da vista 3D; modo escuro no macOS. — [Architosh, out/2025](https://architosh.com/2025/10/graphisoft-releases-archicad-29-with-game-changing-tools/)

### Inferences
- O modelo "vista salva = configuração de exibição + recorte do modelo" e "layout = composição de vistas" é o núcleo a reproduzir. No BrasBim isso pode virar entidades próprias, persistidas no IFC via IfcAnnotation/IfcGroup/Psets próprios ou num sidecar.
- O status de reforma em todas as entidades, inclusive marcadores e anotações, foi uma correção tardia no Archicad (só no AC29). Projetar isso desde o início é um ganho fácil, e mapeia para `Pset_*Common.Status` do IFC (NEW/EXISTING/DEMOLISH/TEMPORARY).
- As revisões no Archicad dependem de "changes" amarrados a elementos e têm gambiarras conhecidas (nuvens herdadas). Um modelo mais simples e explícito (revisão por folha + nuvens como anotações ligadas à revisão) tende a ser menos confuso.
- Keynotes com banco hierárquico exportável para planilha são ponto de partida natural para integrar com SINAPI/especificações brasileiras.

### Gaps
- Não obtive páginas oficiais atualizadas sobre plano de corte da planta (Floor Plan Cut Plane), Model View Options, pen sets, tipos de linha, hachuras, superfícies e materiais de construção (Building Materials com prioridade de interseção), cotas associativas, carimbos de zona (Zone Stamp), elevações internas, detalhes/worksheets e documentos 3D. Esses recursos existem há muitas versões (conhecimento prévio), mas não foram confirmados por fonte nesta rodada e precisam de pesquisa complementar antes de entrar em spec.
- As páginas "Schedule Format Improvements" (AC29) e "Improved Text Label options" (AC28) não foram abertas em detalhe.

## 2. Organização do projeto (camadas, pavimentos, atributos, templates, hotlinks, referências externas, biblioteca)

### Takeaway
Esta rodada confirmou pouco desse tema em fonte primária. Os pontos confirmados: o Navigator como espinha do projeto, translators de IFC guardados no template/projeto, hotlink de modelos RVT e, desde o AC28, a "Global Library", com pacotes de biblioteca universais em vez da biblioteca única por versão.

### Cited Findings
- AC28 "Global Library": pacotes (libpacks) universais substituem a biblioteca única de cada versão. O conteúdo vem em todas as versões localizadas (ex.: portas alemãs usáveis em qualquer mercado), o template define tamanhos e atributos padrão por norma local, as atualizações ficam mais frequentes e há 136 novas peças em "Objects and Annotation Tools". — [AC28 New Features: Global Library](https://help.graphisoft.com/AC/28/INT/_AC28_Help/005_NewFeatures/005_NewFeatures-20.htm)
- AC28, grupo "Smooth user experience": nova tela inicial, onboarding, atualização facilitada e Global Library (só títulos). — [AC28 New Features: Smooth user experience](https://help.graphisoft.com/AC/28/INT/_AC28_Help/005_NewFeatures/005_NewFeatures-16.htm)
- Hotlink de modelo RVT: arquivo > conteúdo externo > hotlink. Só importa objetos de uma vista 3D do Revit, e é recomendado manter a estrutura de pavimentos da origem. O resultado vira objetos GDL na biblioteca embutida do projeto. — [Hotlink 3D RVT Model (AC25 help)](https://help.graphisoft.com/AC/25/INT/_AC25_Help/120_Interoperability/120_Interoperability-44.htm) (via resultado de busca)
- Os translators de IFC podem ser importados de arquivos PLN/PLA/TPL (projeto/arquivo/template). Arquivos de translator em XML deixaram de ser aceitos. — [IFC Translators: Overview (AC28 help)](https://help.graphisoft.com/AC/28/INT/_AC28_Help/121_IFC/121_IFC-23.htm)

### Inferences
- A Global Library mostra que separar o conteúdo de norma local (template) do conteúdo paramétrico (biblioteca) é uma direção que o próprio Archicad adotou. No BrasBim, o template "ABNT" deve carregar padrões de dimensão e atributos, e os objetos paramétricos devem ser neutros.
- O hotlink RVT converte tudo em objetos GDL "mudos", sem semântica. Uma referência externa IFC que preserve a semântica é um diferencial natural de um app IFC-nativo.

### Gaps
- Sem fonte confirmada nesta rodada para: camadas e combinações de camadas (incluindo interseção de camadas), pavimentos e "show on stories", Attribute Manager, módulos/hotlinks de PLN, gestão de XREF DWG, Drawing Manager e referências PDF. Pesquisa complementar necessária.

## 3. Colaboração (Teamwork/BIMcloud, BCF/Issues, Bluebeam, Bimplus, BIMx)

### Takeaway
O Teamwork do Archicad é colaboração por reserva de elementos num servidor (BIMcloud). Criar algo novo não exige reserva, mas editar ou excluir exige. O status das reservas é ao vivo, e o envio/recebimento é incremental, com conflitos evitados por construção. As integrações recentes (AC28/29) giram em torno de issues: BCF 3.0, ligação bidirecional com o Bluebeam Studio e publicação para o Bimplus.

### Cited Findings
- Teamwork: qualquer usuário cria elementos novos sem reservar, mas para modificar ou excluir um elemento, atributo ou outro dado compartilhado é preciso reservar antes. O status das reservas fica sempre atualizado enquanto se está online, sem precisar sincronizar. — [Teamwork Functions at a Glance (AC27 help)](https://help.graphisoft.com/START/27/INT/_AC27_Help/080_Collaboration/080_Collaboration-3.htm); [Overview of Teamwork Reservation (AC24 help)](https://help.graphisoft.com/AC/24/INT/_AC24_Help/080_Collaboration/080_Collaboration-26.htm) (via resultado de busca)
- Autorreserva: na maioria dos casos o elemento é reservado ao ser selecionado e começar a ser editado (exceto no BIMcloud Basic). Se o elemento é de outro usuário ou se há mudanças a receber primeiro, aparece um aviso. Quando os itens selecionados estão todos indisponíveis, o comando de reservar vira "pedir", e começa um fluxo de solicitação de posse. — mesmas fontes
- Send envia as alterações locais feitas desde a última sincronização, e Receive traz as do servidor. Existe um comando combinado, que aceita um comentário registrado no log de atividades do BIMcloud Manager. Só os dados alterados trafegam. Como a reserva é obrigatória, conflitos entre edição local e servidor não deveriam ocorrer. — mesmas fontes
- AC28: importação e exportação de BCF 3.0 (mais controle sobre o conteúdo das issues). — [AC28 New Features: New and updated file formats](https://help.graphisoft.com/AC/28/INT/_AC28_Help/005_NewFeatures/005_NewFeatures-15.htm)
- O Issue Manager existe desde o AC24, e a conexão com o Solibri foi alinhada a ele. — [Graphisoft Community, Archicad 24 Update 2](https://community.graphisoft.com/t5/Getting-started/Archicad-Keeps-Getting-Better-Archicad-24-Update-2/ta-p/304109) (via resultado de busca)
- AC29, conexão Bluebeam Studio (add-on incluído no pacote principal): cria sessões e projetos do Bluebeam Studio com a documentação 2D do Archicad sem abrir o Revu, e traz as anotações dos revisores de volta como issues. Os revisores precisam de conta Bluebeam. A Graphisoft já tinha demonstrado a ligação bidirecional entre markups e o Issue Manager no lançamento do AC28. — [AC29 New Features: Collaboration/Interoperability](https://help.graphisoft.com/AC/29/INT/_AC29_Help/005_NewFeatures/005_NewFeatures-26.htm); [Architosh, out/2024](https://architosh.com/2024/10/budapest-part-2-details-from-the-graphisoft-launch-event-press-conference/)
- AC29, conexão Bimplus (plataforma da Allplan/Nemetschek): publica modelos e documentos no Bimplus com revisões. É só de ida (não traz dados do Bimplus) e exige conta. — [AC29 New Features: Collaboration/Interoperability](https://help.graphisoft.com/AC/29/INT/_AC29_Help/005_NewFeatures/005_NewFeatures-26.htm)
- O AC29 anunciou integração reforçada com BIMcloud e BIMx, sem detalhes nas fontes consultadas. — [Graphisoft Community, "Archicad 29 – A glance at the new features"](https://community.graphisoft.com/t5/Getting-started/Archicad-29-A-Glance-at-the-New-Features/ta-p/672706) (via resultado de busca)
- Ponto do AC27 relevante para o Teamwork: o painel de Design Options pode ser reservado, e elementos com opção ausente geram notificação em projetos Teamwork. — [Enhanced Design Options](https://help.graphisoft.com/AC/28/INT/_AC28_Help/005_NewFeatures/005_NewFeatures-6.htm)

### Inferences
- O modelo de reserva (criar livre, editar exige reserva, reserva ao vivo, sincronização incremental com comentário) coincide com a direção já decidida no BrasBim (memória "Colaboração por reserva"). Vale copiar o comportamento de autorreserva ao começar a editar e o fluxo de "pedir posse". A reserva granular de recursos não geométricos (atributos, painéis como o de Design Options) também precisa entrar no desenho.
- O BCF 3.0 com issues ligadas a elementos e a vistas é hoje o mínimo esperado. O BrasBim pode usar o suporte a BCF do IfcOpenShell (`bcf` do ecossistema IfcOpenShell/BlenderBIM) desde o início.

### Gaps
- Não confirmei preços/edições do BIMcloud (Basic vs. completo vs. SaaS), mensagens internas do Teamwork nem detalhes atuais do BIMx (apresentação web/mobile do modelo e das folhas).

## 4. Interoperabilidade (IFC, IDS, DWG, RVT, Rhino/Grasshopper, PDF, OBJ)

### Takeaway
O IFC no Archicad funciona por "translators" configuráveis (import/export separados) com mapeamento de tipos e propriedades. Um translator especial de "Preview" define quais propriedades IFC aparecem em buscas, tabelas e rótulos. O suporte nativo a leitura e escrita de IFC 4.3 chegou no AC29, e a importação de IDS (que gera propriedades, classificações e mapeamentos automaticamente) no AC28. Rhino/Grasshopper tem conexão ao vivo, e RVT entra por hotlink como GDL.

### Cited Findings
- Translators definem quais elementos são convertidos e como são interpretados. Os grupos de importação e exportação não são intercambiáveis. Vários vêm de fábrica para fins específicos. Open/Hotlink usam o translator de importação de um template externo escolhido, e Merge usa os do projeto atual. É obrigatório manter ao menos um de cada tipo. — [IFC Translators: Overview (AC28 help)](https://help.graphisoft.com/AC/28/INT/_AC28_Help/121_IFC/121_IFC-23.htm)
- O Preview Translator fornece o mapeamento de tipos (cada elemento recebe uma IFC Type, que determina as propriedades disponíveis) e o mapeamento de propriedades. Este último define as propriedades IFC usadas em Find & Select, tabelas interativas, rótulos, IFC Project Manager e configurações de elementos. Pode ser trocado, por exemplo, para um translator COBie 2. Alguns mapeamentos podem ser importados de arquivos externos (BIM Content ou IDS). No AC28 o filtro de translators listava IFC2x3 ou IFC4. — mesma fonte
- Mapeamento de propriedades na exportação: diálogo próprio que atribui propriedades IFC aos elementos exportados, com filtro por esquema e domínio (estrutural/MEP). Permite importar os Psets personalizados do projeto. Algumas regras são predefinidas (ex.: nome/descrição do projeto → IfcProject). Uma propriedade de um tipo de elemento ainda inexistente no projeto não aparece nos diálogos até existir uma instância. — [Property Mapping for IFC Export (AC25 help)](https://help.graphisoft.com/AC/25/INT/_AC25_Help/121_IFC/121_IFC-38.htm) (via resultado de busca)
- AC29: leitura e escrita nativas de IFC 4.3. — [AC29 New Features: Collaboration/Interoperability](https://help.graphisoft.com/AC/29/INT/_AC29_Help/005_NewFeatures/005_NewFeatures-26.htm); [Architosh, out/2025](https://architosh.com/2025/10/graphisoft-releases-archicad-29-with-game-changing-tools/)
- AC28: importação de IDS, com criação automática das propriedades, classificações e mapeamentos IFC exigidos. — [AC28 New Features: New and updated file formats](https://help.graphisoft.com/AC/28/INT/_AC28_Help/005_NewFeatures/005_NewFeatures-15.htm)
- AC28: o Rhino In-Out nativo suporta Rhino 8, e a conexão Grasshopper-Archicad suporta Rhino 7 e 8. — mesma fonte
- AC29: importação nativa de OBJ, com diálogo de opções. — [AC29 New Features: Collaboration/Interoperability](https://help.graphisoft.com/AC/29/INT/_AC29_Help/005_NewFeatures/005_NewFeatures-26.htm)
- RVT: hotlink nativo de modelos Revit (só a vista 3D, convertida em objetos GDL). Antes existia um add-on gratuito de terceiros (BIM6x), focado em comparar modelos, não em substituir o IFC. — [Hotlink 3D RVT Model (AC25 help)](https://help.graphisoft.com/AC/25/INT/_AC25_Help/120_Interoperability/120_Interoperability-44.htm); [Architosh, 2017](https://architosh.com/2017/12/bim6x-announces-revit-families-and-revit-geometry-exchange-add-on-for-archicad/amp)

### Inferences
- A separação entre o "modelo interno" e o "mapeamento IFC" via translators é justamente a fonte de complexidade e de perdas no round-trip do Archicad. Num app IFC-nativo o mapeamento é a identidade, e esse é o principal argumento técnico do BrasBim. Mesmo assim, perfis de exportação (filtros, MVD, subconjuntos de Psets para órgãos ou clientes) continuam úteis.
- O IDS como fonte de requisitos que gera Psets e classificações automaticamente é um recurso a igualar desde cedo (o IfcOpenShell tem `ifctester`).
- Rhino/Grasshopper ao vivo é um diferencial do Archicad. Para o BrasBim, uma API Python aberta cobre parte disso.

### Gaps
- Não obtive documentação atual sobre translators DWG/DXF (mapeamento de camadas e penas, XREF) nem sobre exportação/importação de PDF.
- Não achei relatos públicos confiáveis e recentes sobre problemas específicos de round-trip IFC (ex.: perda de parametria ao reimportar). Pesquisa complementar em fóruns é necessária.

## 5. Automação e extensibilidade (GDL, APIs, add-ons, IA)

### Takeaway
O Archicad oferece três níveis de extensão: GDL para objetos paramétricos, a API C++ para add-ons e uma interface JSON por HTTP (desde o AC24) com binding Python oficial. A IA entrou como AI Visualizer (geração de imagens, versão 2.0 no AC29) e AI Assistant (beta, chatbot embutido no AC29).

### Cited Findings
- A interface JSON surgiu no AC24: comunicação de um programa externo para o Archicad via HTTP com mensagens JSON. Há um binding Python oficial no PyPI (`archicad`) que esconde a camada JSON, com funções de mesmo nome dos comandos JSON. O pacote 24.x exigia AC24 beta 3 ou posterior. — [PyPI: archicad 24.3000](https://pypi.org/project/archicad/24.3000/); [PyPI: archicad 25.1100](https://pypi.org/project/archicad/25.1100)
- Existe um servidor MCP comunitário (não oficial), "archicad-mcp", que liga assistentes de IA ao Archicad via a API JSON "Tapir". — [glama.ai](https://glama.ai/mcp/servers/fkd7ijbx9l) (via resultado de busca)
- Novidades da API C++ no AC29: entrada por polígono para a ferramenta de abertura; criar, modificar e excluir Design Options, Sets e combinações; controle de arestas de Morph; balões de notificação na tela; menu e atalho próprios do add-on; setas distintas em ferramentas de linha. — [AC29 New Features: Collaboration/Interoperability](https://help.graphisoft.com/AC/29/INT/_AC29_Help/005_NewFeatures/005_NewFeatures-26.htm)
- AI Assistant (beta, AC29): chatbot dentro da janela do Archicad (também no DDScad e no MEP Designer). Responde com base nos guias do produto, artigos de suporte, Community e cursos do Graphisoft Learn. A Graphisoft afirma que dados do cliente não são usados para treinar agentes da Nemetschek. — [Architosh, out/2025](https://architosh.com/2025/10/graphisoft-releases-archicad-29-with-game-changing-tools/)
- AI Visualizer: usa Stable Diffusion para gerar imagens a partir do modelo. A versão experimental do AC27 teve fim de serviço em 31/12/2024, e a do AC28 é 100% em nuvem, com controles de criatividade e upscaling. A 2.0 (AC29) gera imagens por prompt, ajusta materiais, fundo, janelas e forma, tem slider antes/depois e pincel para edição local, e salva os resultados no Archicad. — [AI Visualizer Guide (PDF)](https://assets.graphisoft.com/guides/AI_Visualizer/AI_Visualizer-Guide.pdf); [Architosh, out/2025](https://architosh.com/2025/10/graphisoft-releases-archicad-29-with-game-changing-tools/)
- AC29 também traz o MEP Designer integrado (layouts 2D/3D de sistemas, cortes, tabelas e listas de peças, Windows e Mac). Ele também existe como app independente e vem incluído no plano Archicad Collaborate. — [Architosh, out/2025](https://architosh.com/2025/10/graphisoft-releases-archicad-29-with-game-changing-tools/)
- AC28 inclui Avaliação de Ciclo de Vida (LCA) como recurso. — [AC28 New Features: Smart Design](https://help.graphisoft.com/AC/28/INT/_AC28_Help/005_NewFeatures/005_NewFeatures-2.htm)

### Inferences
- Como o BrasBim é Python, o "nível JSON/Python" do Archicad vem de graça: scripts podem rodar dentro do processo, com acesso ao `ifcopenshell.api`. Isso é mais poderoso do que uma API HTTP de mão única.
- O AI Assistant do Archicad é essencialmente um RAG sobre a documentação. Um assistente equivalente no BrasBim seria viável com a documentação pt-BR e as specs.

### Gaps
- Não pesquisei a fundo o GDL (sintaxe, scripts 2D/3D/parâmetros, editor). É conhecimento prévio, sem fonte nesta rodada.

## 6. Experiência de uso: pontos fortes e dores

### Takeaway
As avaliações são boas no geral (Capterra 4,4/5 com 279 avaliações; facilidade de uso 4,2). Os elogios vão para a ligação 2D/3D e para a curva de aprendizado comparada à concorrência. As queixas recorrentes são preço e licenciamento (incluindo a migração para assinatura), desempenho em projetos grandes ou ricos em dados, interface considerada datada e problemas antigos não resolvidos. As fontes são opiniões individuais, não uma amostra sistemática.

### Cited Findings
- Capterra: nota geral 4,4 (279 avaliações), facilidade de uso 4,2. Há relatos opostos sobre a curva de aprendizado ("intensa, anos para dominar" vs. "íngreme mas superável com prática", ou "fácil de pegar"). — [Capterra, ARCHICAD Reviews](https://capterra.com/p/2018/ArchiCAD/reviews/) (via resultado de busca)
- Elogios: ligação 2D/3D muito prática; um avaliador diz que roda bem até em máquina modesta. — mesma fonte
- Queixas: exige máquina robusta e muita RAM (sobretudo para renderizar); fica lento com arquivos ricos em dados; precisa de app externo para bons renders; licenças caras, renovações frequentes e plugins/pacotes caros; mudanças de licença tornam inviável para pequenos escritórios; interface datada e seleção de objetos trabalhosa. — mesma fonte; [GetApp, ARCHICAD reviews](https://www.getapp.com/construction-software/a/archicad/reviews/) (via resultado de busca)
- Há relatos de problemas de otimização em projetos grandes, com travamentos ou lentidão. Um avaliador do G2 diz que em projetos hospitalares e institucionais grandes a colaboração e a automação são limitadas em relação ao Revit. — [GetApp](https://www.getapp.com/construction-software/a/archicad/reviews/); [G2](https://www.g2.com/products/archicad) (via resultado de busca; o G2 deu 403 no fetch)
- No fórum oficial, um usuário com licença perpétua há três anos se diz decepcionado: não sabia da mudança posterior para assinatura e diz que muitos problemas discutidos há anos no fórum e no Reddit seguem sem solução. — [Graphisoft Community, "After 3 years with Archicad I'm honestly disappointed"](https://community.graphisoft.com/t5/General-discussions/After-3-years-with-Archicad-I-m-honestly-disappointed/m-p/717239) (via resultado de busca; a página deu 403)
- Sobre custo, há opiniões divergentes: alguns acham a assinatura cara, outros citam custo total menor que o da concorrência. — [TrustRadius, pricing](https://www.trustradius.com/products/archicad/pricing) (via resultado de busca)
- A própria Graphisoft investiu em onboarding no AC28 (nova tela inicial, onboarding, atualização facilitada) e no AC29 (Learning Center com tours e tutoriais, AI Assistant). Isso sugere que a curva de aprendizado é reconhecida como problema. — [AC28 Smooth user experience](https://help.graphisoft.com/AC/28/INT/_AC28_Help/005_NewFeatures/005_NewFeatures-16.htm); [AC29 New Features](https://help.graphisoft.com/AC/29/INT/_AC29_Help/005_NewFeatures/005_NewFeatures-1.htm)

### Inferences
- Para o BrasBim, as oportunidades mais claras são três: custo zero e licença aberta (ataca a principal queixa), desempenho previsível em modelos grandes (carregamento parcial e por pavimento) e uma UI limpa e moderna, coerente com as diretrizes de UX já registradas.
- O onboarding guiado e a ajuda contextual em pt-BR são baratos e respondem a uma dor reconhecida até pelo fornecedor.

### Gaps
- Não acessei threads do Reddit r/ArchiCAD diretamente (a busca não trouxe resultados), nem o conteúdo integral do G2 e da Community (403). As queixas sobre estabilidade e crashes vêm de agregadores e precisam de confirmação.
- Não encontrei preços oficiais atuais (2026) nem a estrutura de planos (ex.: "Archicad Collaborate" foi citado sem valores).
