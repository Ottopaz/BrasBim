# Bibliotecas, objetos/conteúdo e criação de objetos paramétricos — Archicad, Revit, AutoCAD (2026)

Data de acesso de todas as fontes: 2026-10-21. Fontes só públicas (help oficial, fóruns, sites de fabricantes, buscadores). Resumo nas minhas palavras; citações curtas quando indicado. Nada foi lido de `_restrito/` ou `tools/`.
Observação de método: várias informações vieram de trechos de busca (snippets) e não da leitura completa da página. Isso está marcado como "(snippet)" quando relevante. A página do artigo da USP deu erro de redirecionamento no WebFetch, então os números dele vêm de snippets do buscador.

## 1. Archicad: biblioteca padrão, GDL, Library Part Maker, BIMcomponents, gestão de bibliotecas, portas/janelas

### Takeaway
Os objetos do Archicad são "library parts" GDL (parâmetros + scripts 2D/3D/parâmetros/interface + hotspots). Desde o Archicad 28 a biblioteca monolítica por versão deu lugar a uma "Global Library" em pacotes. Criar objetos sem programar é possível com o add-on Library Part Maker ou salvando elementos de construção como objeto. A dor histórica é a gestão de bibliotecas: partes faltando, bibliotecas de migração por versão e objetos incompatíveis com versões anteriores.

### Cited Findings
- O editor de objetos GDL organiza o objeto em Parâmetros, Componentes, Descritores, Scripts e Símbolo 2D. O 3D é gerado pelo script 3D a partir dos valores dos parâmetros, e o símbolo 2D depende da escala. — [Graphisoft Help AC21, GDL Object Editor](https://help.graphisoft.com/AC/21/INT/AC21Help/Appendix_Settings/Appendix_Settings-90.htm) (snippet)
- Hotspots: há hotspots automáticos (caixa envolvente) e hotspots por script (comandos HOTSPOT/HOTSPOT2). Basta um hotspot no script para os automáticos sumirem. Cada hotspot precisa de um ID único para que as cotas associativas continuem presas quando o tamanho muda. Os hotspots também servem para edição gráfica dos parâmetros. — [GDL Center, "Hotspots, graphical editing"](https://gdl.graphisoft.com/gdl-basics/hotspots-graphical-editing) (snippet)
- O script de parâmetros usa o comando VALUES para criar listas suspensas de valores (ex.: posição Esquerda/Centro/Direita). — [Graphisoft Community, GDL Parameter with text](https://community.graphisoft.com/t5/Libraries-objects/GDL-Parameter-with-text/td-p/139778) (snippet)
- Problema relatado por usuários: hotspots do símbolo 2D aparecem no 3D. O controle fica num parâmetro geralmente oculto (AC_Show2DHotspotsin3D), e mudar o valor padrão não altera instâncias já colocadas. — [Graphisoft Community, GDL 2D Symbol Hotspots in 3D](https://community.graphisoft.com/t5/GDL/GDL-2D-Symbol-Hotspots-in-3D/m-p/667883); [Libraries & objects, turn off 2D hotspots in 3D](https://community.graphisoft.com/t5/Libraries-objects/turn-off-2D-hotspots-in-3D/m-p/201305)
- Segundo a comunidade Graphisoft Brasil, o Archicad 27 trouxe um Editor GDL renovado. — [Graphisoft Community BR, Bibliotecas e objetos](https://community.graphisoft.com/t5/Bibliotecas-e-objetos/tkb-p/tkb-library-br/label-name/library%20part%20maker) (snippet)
- Global Library (Archicad 28 e posteriores): o template passa a carregar vários pacotes de biblioteca em vez de uma biblioteca única por versão. A ajuda do AC29 fala em centenas de objetos pré-configurados e editáveis, e outros pacotes podem ser carregados a partir da pasta de instalação. Objetos antigos da "Monolithic Library" continuam editáveis, mas as novas colocações e atualizações saem só da Global Library. Objetos colocados da Global Library não são compatíveis com versões anteriores. — [AC29 Help, Global Library](https://help.graphisoft.com/AC/29/INT/_AC29_Help/020_Configuration/020_Configuration-42.htm); [AC29 Migration Guide, New Global Library](https://help.graphisoft.com/AC/29/INT/_AC29_Help/010_MigrationGuide/010_MigrationGuide-5.htm)
- A comunidade brasileira registra que alguns elementos antigos das bibliotecas monolíticas ainda são necessários para padrões regionais. — [Graphisoft Community BR, biblioteca global](https://community.graphisoft.com/t5/Bibliotecas-e-objetos/tkb-p/tkb-library-br/label-name/biblioteca%20global) (snippet)
- Library Part Maker (LPM) 29: add-on que cria library parts GDL sem programar. Tipos: objetos genéricos, portas, janelas, claraboias, luminárias e peças MEP (estas exigem a MEP Library). A versão para AC29 foi modificada em 01/10/2025, tem builds para macOS e Windows e é liberada para quem tem contrato de assinatura ativo em certos países, além de licenças trial e educacionais. — [Graphisoft, Library Part Maker download](https://graphisoft.com/downloads/addons/lpm)
- Na comunidade, o LPM é indicado para montar portas customizadas a partir de paredes, lajes, vigas, pilares e morphs e salvar como porta. Um consultor o descreve como imperfeito, mas uma alternativa viável ao GDL. — [Graphisoft Community, Pivot doors / custom doors](https://community.graphisoft.com/t5/Libraries-objects/Pivot-doors-custom-doors-jambs-doors-with-no-head-jambs/m-p/640824)
- Na ajuda oficial: modelar um formato com elementos de construção e salvá-lo como componente customizado (ex.: folha de porta). O componente vai para a biblioteca embutida do projeto e é redimensionado para caber na abertura. Só achei páginas das versões 17 a 20. — [AC20 Help, Creating Custom Components for Doors, Windows, Curtain Walls](https://help.graphisoft.com/AC/20/INT/AC20Help/03_1_Elements_Virtual_Building/03_1_Elements_Virtual_Building-209.htm)
- Um usuário do AC29 que modelava portas históricas relatou que nem as peças padrão nem as da Cadimage deixam variar cada dimensão de forma independente. Outro comentou que os tutoriais paramétricos focam mais em mobiliário do que em portas e janelas. — [Graphisoft Community, Modeling Historic Door Details](https://community.graphisoft.com/t5/Libraries-objects/Modeling-Historic-Door-Details/td-p/687071)
- O guia oficial "a forma mais fácil de criar objetos é graficamente, com as ferramentas do Archicad" (salvar seleção 3D como objeto). — [Graphisoft Help Center](https://helpcenter.Graphisoft.com/?p=76697) (snippet)
- BIMcomponents.com: portal público de objetos GDL e superfícies. Navegar e baixar é grátis e não exige licença Archicad. Para enviar, comentar ou avaliar é preciso se registrar. A licença é escolhida pelo autor de cada objeto, no estilo Creative Commons (Public Domain 1.0, CC BY 4.0, CC BY-SA 4.0, CC BY-ND 4.0). Objetos com copyright comercial não podem ser publicados. O autor pode proteger o script com senha, exceto em objetos de domínio público. — [AC29 Help, BIM Components](https://help.graphisoft.com/AC/29/INT/_AC29_Help/040_ElementsVB/040_ElementsVB-281.htm); [AC30 Help, BIM Components](https://help.graphisoft.com/AC/30/INT/Topics/040_ElementsVB/040_ElementsVB-281.html)
- Partes faltando: o procedimento oficial é abrir o Library Manager e usar "Migrate Libraries", que adiciona as bibliotecas de migração da pasta de instalação. Partes vindas do Archicad 9 ou anterior não têm biblioteca de migração. Em BIMcloud as bibliotecas podem estar num servidor. — [Graphisoft Help Center, missing library parts](https://helpcenter.graphisoft.com/?p=84856); [AC25 Help, Migrating Libraries from AC12 and earlier](https://help.graphisoft.com/AC/25/INT/_AC25_Help/011_MigrationGuideOlderVersions/011_MigrationGuideOlderVersions-20.htm); [Community, How to detect and clear missing Library Parts](https://community.graphisoft.com/t5/Project-Management-articles/How-to-detect-and-clear-missing-Library-Parts/ta-p/303817)
- Um usuário explica que o objeto é referenciado por um GUID oculto, não pelo nome. Peças com GUID diferente só são trocadas automaticamente se houver um script de migração. Isso é explicação de usuário, não documentação oficial. — [Community, Changed part names in library](https://community.graphisoft.com/t5/Design-forum/Changed-part-names-in-library/td-p/240082)
- Mobiliário brasileiro em GDL nativo com parâmetros editáveis: biblioteca "Mula Preta", divulgada pela Graphisoft. — [Graphisoft Insights, Baixe a biblioteca Mula Preta](https://community.graphisoft.com/t5/Graphisoft-Insights/Baixe-a-biblioteca-Mula-Preta-para-Archicad/ba-p/702002) (snippet)

### Inferences
- O GDL junta, num só objeto, a geometria 3D, um símbolo 2D próprio e sensível à escala, a interface de parâmetros e os pontos de edição (hotspots). Para o BrasBim, o equivalente seria guardar uma definição paramétrica num IfcTypeProduct (parâmetros em Psets e representações 2D/3D por tipo) e ter um gerador de geometria versionado.
- O vínculo por GUID e as bibliotecas de migração mostram que identidade e versionamento do objeto são pontos críticos. Uma biblioteca IFC‑nativa embutida no próprio arquivo IFC (os tipos viajam com o modelo) elimina o problema de "parte faltando".
- O ecossistema mistura CC e conteúdo comercial. Uma biblioteca open source precisa de licença explícita por objeto, como faz o BIMcomponents.

### Gaps
- Não achei a lista oficial de objetos novos da biblioteca do AC29/AC30 nem confirmação de um "construtor de portas/janelas" novo nas versões 28–30 (além do LPM e dos componentes customizados).
- Não consegui ler discussões brasileiras específicas sobre objetos fora da ABNT (as páginas da comunidade BR só mostraram índices).

## 2. Revit: famílias carregáveis, templates, conteúdo por localidade, type catalogs, qualidade

### Takeaway
O conteúdo do Revit são famílias .rfa criadas a partir de templates (.rft). O conteúdo da Autodesk vem em pacotes por idioma/região e, desde o 2021.1, pode ser carregado da nuvem sob demanda. Type catalogs (.txt) evitam carregar todos os tipos. A queixa recorrente é a qualidade das famílias de fabricantes: pesadas, com parâmetros demais, modelagem excessiva e às vezes quebradas.

### Cited Findings
- Revit 2021.1 em diante pode carregar famílias da biblioteca padrão da nuvem com o comando "Load Autodesk Family". Também é possível baixar a biblioteca local. Do 2022 em diante, o download é feito pela conta Autodesk (Products and Services > Revit > View Details > Libraries) e o conteúdo é extraído em C:\ProgramData\Autodesk\RVT <versão>. Até o 2020, templates e famílias eram instalados junto com o programa. — [Autodesk Support, Where to find Revit Content Libraries](https://knowledge.autodesk.com/article/Where-to-find-Revit-Content-Libraries-to-download)
- Os pacotes de conteúdo (templates de família, templates de projeto e bibliotecas) vêm separados por idioma/localidade (ex.: chinês simplificado, francês, tcheco). — [Autodesk, Revit 2021 Content](https://knowledge.autodesk.com/support/revit/troubleshooting/caas/downloads/content/autodesk-revit-2021-content.html)
- Autodesk Content Catalog: ferramenta em nuvem para gerenciar famílias Revit, sem custo extra para quem tem assinatura com Forma Data Management (antigo Autodesk Docs/ACC). — [Autodesk, Content Catalog](https://www.autodesk.com/products/autodesk-docs/features/content-catalog); [Arkance blog](https://www.arkance.us/blog/content-catalog-for-autodesk-docs)
- Type catalog: arquivo .txt na mesma pasta do .rfa, com a primeira linha declarando os parâmetros no formato Nome##Tipo##Unidade e uma linha por tipo. O "Export Family Types" gera a base, mas não existe no Revit LT. Ao carregar, o usuário escolhe quais tipos quer. Arrastar e soltar pode trazer um tipo placeholder. — [Autodesk Help 2024, Create a Type Catalog](https://help.autodesk.com/cloudhelp/2024/ENU/Revit-Customize/files/GUID-FFA71D72-D4C5-416D-BF65-1757657C3CE9.htm); [BIMsmith, How to Use a Type Catalog](https://bimsmith.com/help/learning-revit/How-to-Use-a-Type-Catalog)
- Críticas à qualidade (blog de consultor): a maioria das famílias de fabricantes seria de baixa qualidade, com excesso de modelagem e de parâmetros, arquivos acima de ~1 MB e geração por script. Um exemplo de janela tinha 239 parâmetros compartilhados, ~10 MB, nenhuma instrução e travava ao mover. O autor atribui isso ao fato de o cliente ser o fabricante, que prioriza o marketing. — [BIMpure, This is the worst Revit family ever](https://www.bimpure.com/blog/this-is-the-worst-revit-family-ever); [BIMpure, 13 tips to organize Revit families](https://www.bimpure.com/blog/13-tips-to-understand-and-organize-revit-families) (opinião)
- Autodesk Community (Revit Ideas "Better built-in Revit families"): usuários dizem que muitas famílias de fabricantes são mal construídas, que a maioria dos produtos nem tem modelo BIM e que a edição falha em algumas famílias (ex.: escadas rolantes). Sugerem ter alguém na equipe para ajustar conteúdo de terceiros. — [Autodesk Forums, Better built-in Revit families](https://forums.autodesk.com/t5/revit-ideas/better-built-in-revit-families/idc-p/8526257/highlight/true)
- Ferramentas comerciais verificam a "saúde" do conteúdo (desempenho, padrões, famílias corrompidas, geometria não nativa). — [Kinship docs, Content health reports](https://docs.kinship.io/reference-content-health-reports)
- O BIMsmith afirma que suas famílias são feitas internamente ou passam por QA para ter geometria enxuta (afirmação do próprio fornecedor). — [BIMsmith FAQ](https://bimsmith.com/help/FAQ/Are-Revit-families-on-BIMsmith-high-quality)
- Lista brasileira de sites para baixar famílias Revit grátis (2026). — [FireBIM/EstúdioBIM, 26 melhores sites para baixar famílias Revit](https://estudiobim.com.br/26-melhores-sites-para-baixar-familias-revit-gratis-em-2022) (não lida em detalhe)

### Inferences
- O type catalog separa a definição paramétrica (família) da tabela de tipos (dados). Em IFC isso se traduz bem como um "tipo base" mais variantes de IfcTypeProduct geradas de uma tabela, carregando só o que for usado.
- Peso e excesso de parâmetros são os principais incômodos. Uma biblioteca de qualidade precisaria de limites de tamanho e complexidade e de validação automática (IDS + checagens de geometria), como fazem os relatórios de saúde comerciais.

### Gaps
- Não verifiquei se existe pacote de conteúdo Revit oficial em pt‑BR e quão adaptado ele é às normas brasileiras.
- Não acessei RevitCity em detalhe (termos de licença, qualidade).

## 3. AutoCAD: blocos, blocos dinâmicos, paletas, DesignCenter

### Takeaway
No AutoCAD, o conteúdo são blocos DWG. Uma biblioteca é tipicamente um DWG com várias definições de bloco. Os blocos dinâmicos acrescentam parâmetros e ações (esticar, girar, espelhar, visibilidade, tabela de consulta). A distribuição é feita por Tool Palettes (Ctrl+3) e pelo DesignCenter.

### Cited Findings
- Uma biblioteca de blocos é um conjunto de definições de bloco guardado num único desenho. Pode vir da Autodesk ou de terceiros, ou ser criada pelo usuário. — [Autodesk Help AutoCAD LT 2018, About Organizing Blocks](https://help.autodesk.com/cloudhelp/2018/ENU/AutoCAD-LT/files/GUID-9C9FF3BC-7275-44E8-93D4-00A2F50BC96D.htm)
- Tool Palettes guardam blocos, blocos dinâmicos e comandos (Ctrl+3 / TP) e podem ser exportadas e compartilhadas na equipe. O DesignCenter procura blocos em bibliotecas sem abrir cada desenho. — [Engineering.com, Managing Blocks with Tool Palettes](https://www.engineering.com/?p=14682); [Arkance UK, Tool Palettes – An Underused Resource](https://ukcommunity.arkance.world/hc/en-us/articles/21546722774162-Tool-Palettes-An-Underused-AutoCAD-Resource)
- Blocos dinâmicos são feitos no Block Editor (BEDIT) com parâmetros (linear, rotação, espelhamento, visibilidade, lookup), cada um ligado a ações. Tabelas de lookup restringem as medidas a padrões. — [Novedge, Dynamic Blocks for Standards‑Compliant Libraries](https://novedge.com/blogs/design-news/autocad-tip-dynamic-blocks-for-efficient-standards-compliant-autocad-libraries) (conteúdo de revendedor)
- O DraftSight (Dassault) declara compatibilidade com blocos dinâmicos do AutoCAD, o que indica que o formato virou padrão de fato. — [SolidWorks Help 2025, Libraries of Dynamic Blocks](https://help.solidworks.com/2025/English/WhatsNew/c_wn2025_draftsight_libraries_dynamic_blocks.htm)

### Inferences
- No Brasil, os fabricantes (Deca, Tramontina etc.) ainda distribuem muitos blocos DWG 2D. O BrasBim já importa DXF/DWG como referência e poderia converter blocos 2D em símbolos de planta de tipos IFC (representação "Plan/Annotation").
- O modelo do bloco dinâmico (visibilidades + lookup) é um bom padrão de UX para objetos simples: poucos parâmetros com valores padronizados.

### Gaps
- Não encontrei documentação Autodesk atual (2026) sobre conteúdo de blocos fornecido com o AutoCAD.

## 4. Marketplaces e conteúdo de fabricantes (internacional e brasileiro)

### Takeaway
Os grandes marketplaces (BIMobject, NBS National BIM Library, BIMsmith, ARCAT, bimstore, Polantis) são gratuitos para o usuário e pagos pelo fabricante. RFA domina, seguido de GSM, SKP, DWG e IFC. No Brasil a adoção é incipiente: um estudo da USP/UFSC com 238 fabricantes encontrou só 36 com biblioteca própria, 3 com plugins e 22 no BIMobject. Os formatos priorizam Revit e SketchUp.

### Cited Findings
- BIMobject: acesso grátis para profissionais. Os formatos citados no FAQ são Revit, Archicad, SketchUp, AutoCAD e IFC. Quem paga é o fabricante, por assinatura (página da marca, hospedagem, analytics). — [BIMobject Business FAQ](https://business.bimobject.com/faq/)
- Uma reportagem antiga da AEC Magazine diz que o fabricante pagava por formato, por isso plataformas menos populares podiam ficar sem objetos. — [AEC Magazine, bimobject.com](https://aecmag.com/news/bimobject-com/)
- Não encontrei o texto da licença de uso do BIMobject. O ARCAT oferece conteúdo grátis (RFA, RVT, SKP, DWG/IFC/GLB) sob um acordo de licença próprio. — [ARCAT](https://www.arcat.com/content-type/bim/15)
- NBS National BIM Library (Reino Unido): biblioteca grátis, neutra em plataforma, com objetos genéricos e de fabricantes certificados pelo "NBS BIM Object Standard". Tem plug-in para Revit. — [NBS, The NBS BIM Library](https://www.thenbs.com/knowledge/the-nbs-bim-library?hsLang=en); [NBS, lançamento da National BIM Library](https://www.thenbs.com/news-and-press/chairman-of-uk-government-bim-group-opens-launch-of-the-national-bim-library)
- Polantis e bimstore: só encontrei listagens comparativas, sem detalhes confiáveis. — [G2, NBS National BIM Library alternatives](https://www.g2.com/products/nbs-national-bim-library/competitors/alternatives)
- Estudo brasileiro "Survey of BIM objects provided by the construction materials manufacturers in Brazil" (Gestão & Tecnologia de Projetos, USP): de 238 empresas, 36 têm biblioteca própria, 3 oferecem plugins e 22 usam o BIMobject. Conclusão: a indústria está em estágio inicial de adoção de BIM. — [Revista USP, artigo 232179](https://revistas.usp.br/gestaodeprojetos/en/article/view/232179) (snippet; a página não abriu no fetch); repositório relacionado: [UFSC](https://repositorio.ufsc.br/handle/123456789/254358)
- Portobello: página oficial "Downloads de Objetos 3D" com arquivos separados para Revit e SketchUp, filtrados por linha de produto. — [Portobello, Objetos 3D](https://www.portobello.com.br/produtos/downloads/objetos-3d)
- Deca: biblioteca de arquivos 2D e 3D no site (deca.com.br/biblioteca/arquivos-2d-e-3d-para-projetos/) e página da marca no BIMobject. — [BIMobject, Deca](https://www.bimobject.com/en-us/deca?location=us); [Erik Cavalcanti, Bibliotecas BIM hidrossanitárias](https://erikcavalcanti.com.br/bibliotecas-bim-para-projetos-hidrossanitarios-no-revit-que-voce-deve-conhecer/) (snippet)
- Docol: "DocolBIM", biblioteca de metais sanitários. O suporte da Docol também cita produtos na "Galeria BIM". — [Docol Responde, Produtos DOCOL na Galeria BIM](https://docolresponde.zendesk.com/hc/pt-br/articles/360036247433-Produtos-DOCOL-na-Galeria-BIM); [HashtagBIM, DocolBIM](https://hashtagbim.wordpress.com/tag/docolbim/)
- Tigre: conteúdo distribuído via plugin (TigreCAD/Tigre BIM, desenvolvido pela OFCDesk) para AutoCAD e Revit MEP, que instala um template com as famílias. — [Erik Cavalcanti](https://erikcavalcanti.com.br/bibliotecas-bim-para-projetos-hidrossanitarios-no-revit-que-voce-deve-conhecer/) (snippet)
- Eliane: página eliane.com/bim citada em listas; formato não confirmado. — [Pixel+ blog, Bibliotecas BIM para download (2018)](https://pixelmaisblog.wordpress.com/2018/12/20/bibliotecas-bim-para-download/) (pode estar desatualizado)
- Tramontina: biblioteca 2D/3D (sobretudo cozinha e mobiliário) em DWG, DXF, RFA e SKP, com download de até 5 arquivos ou de um zip completo. — [Tramontina, BIM files](https://global.tramontina.com/en/bim-files)
- Gerdau: biblioteca BIM própria, desenvolvida para Revit. — [OrçaFascio, Biblioteca BIM](https://www.orcafascio.com/papodeengenheiro/biblioteca-bim) (snippet)
- Suvinil (BASF): biblioteca BIM de cores/materiais para Archicad e Revit desde 2020. Tinha 49 opções e mais de 7.000 downloads em quatro meses. — [BASF, BIM Suvinil supera 7000 downloads](https://www.basf.com/br/pt/media/news-releases/2020/02/BIM_Suvinil_supera_7000_downloads)
- Plataforma pública brasileira: Biblioteca Nacional BIM (ABDI / Plataforma BIM BR), com regulamento técnico próprio. — [OrçaFascio, Biblioteca BIM](https://www.orcafascio.com/papodeengenheiro/biblioteca-bim) (snippet)
- Sites comunitários brasileiros de famílias, por exemplo "Família BIM". — [familiabim.com.br](https://www.familiabim.com.br/)

### Inferences
- Os fabricantes brasileiros publicam sobretudo RFA, SKP e DWG. GSM e IFC são minoria, e o conteúdo fica espalhado entre sites próprios, plugins e o BIMobject. Isso abre espaço para o BrasBim oferecer um conversor/importador de IFC de fabricantes e um repositório aberto com fichas de dados normalizadas.
- Como o modelo de negócio é o fabricante pagando por formato, um formato aberto e único (IFC + data template) reduz o custo do fabricante. Esse é um argumento para atrair fabricantes brasileiros.

### Gaps
- Não confirmei bibliotecas de Sasazaki, Brasilit ou Eternit, nem os formatos atuais de Deca/Eliane (os links das listas podem estar desatualizados).
- Não obtive os termos de licença do BIMobject nem da Biblioteca Nacional BIM.

## 5. Padrões abertos para conteúdo: IfcTypeProduct, bSDD, ISO 23386/23387

### Takeaway
A ISO 23387 (edição 2025) define a estrutura de "data templates" para objetos (não o conteúdo), ligada a dicionários de dados (ISO 12006‑3, ISO 23386). O bSDD da buildingSMART hospeda classificações e propriedades consultáveis por API, filtráveis por classe IFC e já usadas pelo IfcOpenShell. Há pouco dado real de fabricantes publicado nesses padrões.

### Cited Findings
- ISO 23387:2025 (2ª edição, substitui a de 2020): data templates para objetos ao longo do ciclo de vida. Traz conceitos, implementação via ISO 12006‑3, manutenção em dicionários de dados e um esquema XSD. Não fornece o conteúdo dos templates. — [ISO 23387:2025](https://www.iso.org/standard/85391.html)
- A edição 2020 tratava das regras de ligação entre data templates e classes IFC dentro de um dicionário. — [iTeh, ISO 23387:2020](https://iteh.es/catalog/standards/iso/3004ba32-013a-4332-82ac-b798d6c40713/iso-23387-2020) (snippet)
- No fórum da buildingSMART, um usuário diz que se fala muito em data templates, mas que esses dados não existem na prática. Outro aponta o bSDD como o único recurso gratuito que atende aos requisitos. — [buildingSMART Forums, Sample files for DataTemplates ISO 23387](https://forums.buildingsmart.org/t/sample-files-or-data-for-datatemplates-according-to-iso-23387-2020-available/3817)
- Argumento de fornecedor: o IFC precisa ser combinado com um dicionário como o bSDD para ser realmente interoperável. — [Cobuilder, IFC plus Data Templates](https://cobuilder.com/en/knowledge/article/ifc-plus-data-templates/) (fonte comercial)
- bSDD: serviço da buildingSMART com classificações, propriedades e unidades, acessado principalmente por API. A busca pode ser filtrada por classe IFC, e uma classificação pode exigir propriedades padrão. O IfcOpenShell tem cliente bSDD que aplica as propriedades padrão de uma classificação a um elemento. Os IDS podem referenciar definições do bSDD. — [buildingSMART, bSDD](https://www.buildingsmart.org/users/services/buildingsmart-data-dictionary-old/); [IfcOpenShell docs bsdd.rst (espelho)](https://dev.glassvision.dedyn.io/Glassvision/IfcOpenShell/src/commit/a8a82450a594b7d95407c6e80d6b30613a3ef60e/src/ifcopenshell-python/docs/bsdd.rst); [abcdblog, novo bSDD](https://www.abcdblog.fr/openbim-buildingsmart-international-launches-the-new-buildingsmart-data-dictionary-bsdd/)

### Inferences
- Uma biblioteca IFC‑nativa poderia ser: arquivos IFC (ou IFC "de biblioteca", com IfcProjectLibrary) contendo IfcTypeProduct com RepresentationMaps 2D (símbolo ABNT) e 3D em vários níveis de detalhe, Psets padrão + Psets de fabricante ligados ao bSDD, e uma definição paramétrica própria (regras/parâmetros) guardada em Pset ou em arquivo anexo. A validação seria feita por IDS. Isso é proposta minha, não fato verificado.
- Publicar no bSDD um dicionário brasileiro (ex.: classes de louças/metais com propriedades ABNT e códigos SINAPI) daria aos fabricantes um template de dados concreto. Hoje esse tipo de dado praticamente não existe.

### Gaps
- Não encontrei mapeamento oficial ISO 23387 ↔ IfcTypeProduct, nem um dicionário brasileiro publicado no bSDD.
- Não pesquisei a ISO 23386 em detalhe.

## 6. O que os usuários querem das bibliotecas e do que reclamam

### Takeaway
As queixas convergem: objetos pesados, com parâmetros demais e mal construídos; falta de objetos para muitos produtos; incompatibilidade de versões ou partes faltando (Archicad); dificuldade de criar portas/janelas realmente paramétricas; símbolos 2D que não seguem padrões regionais. Os usuários pedem conteúdo leve, curado, com metadados úteis e regras claras de licença.

### Cited Findings
- Peso, excesso de parâmetros e geração por script nas famílias de fabricantes. — [BIMpure](https://www.bimpure.com/blog/this-is-the-worst-revit-family-ever)
- Famílias de fabricantes mal construídas e produtos sem modelo. — [Autodesk Forums, Better built-in Revit families](https://forums.autodesk.com/t5/revit-ideas/better-built-in-revit-families/idc-p/6897941)
- Empresas restringem downloads a bibliotecas internas aprovadas. — [BIMpure, 13 tips](https://www.bimpure.com/blog/13-tips-to-understand-and-organize-revit-families)
- Partes faltando e migração entre versões no Archicad. Objetos da Global Library não abrem em versões anteriores. — [Graphisoft Help Center](https://helpcenter.graphisoft.com/?p=84856); [AC29 Migration Guide](https://help.graphisoft.com/AC/29/INT/_AC29_Help/010_MigrationGuide/010_MigrationGuide-5.htm)
- Limitações das portas paramétricas padrão no AC29. — [Graphisoft Community, Historic Door Details](https://community.graphisoft.com/t5/Libraries-objects/Modeling-Historic-Door-Details/td-p/687071)
- Padrões regionais dependem de objetos antigos da biblioteca monolítica. — [Graphisoft Community BR](https://community.graphisoft.com/t5/Bibliotecas-e-objetos/tkb-p/tkb-library-br/label-name/biblioteca%20global) (snippet)
- Licença clara é critério para escolher biblioteca. — [Guideflow, BIM objects](https://www.guideflow.com/blog/bim-objects) (fonte secundária)

### Inferences
- Requisitos sugeridos para o BrasBim: (1) objetos leves, com orçamento de polígonos e níveis de detalhe; (2) símbolos 2D por norma brasileira (ABNT NBR 6492 etc.) separados do 3D; (3) poucos parâmetros bem nomeados em pt‑BR, mais tabela de tipos; (4) metadados para quantitativos e orçamento (código SINAPI, classificação, fabricante, ficha técnica) ligados ao bSDD; (5) licença explícita por objeto (CC0/CC BY); (6) objetos embutidos no IFC do projeto, sem "parte faltando"; (7) validação IDS automática na publicação.

### Gaps
- Não achei pesquisas quantitativas com usuários brasileiros sobre bibliotecas, nem fontes diretas sobre símbolos 2D fora da ABNT nas bibliotecas internacionais. Fóruns e vídeos brasileiros não foram analisados em profundidade.
