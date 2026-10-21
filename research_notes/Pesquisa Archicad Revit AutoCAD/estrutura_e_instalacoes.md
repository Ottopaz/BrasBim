# Estrutura e Instalações (MEP) em ferramentas BIM centradas em arquitetura: Archicad, Revit (e AutoCAD MEP/Plant, brevemente)

Data de acesso de todas as fontes: 2026-10-21. Só fontes públicas da web. Nenhum material local (`_restrito/`, `tools/`) foi consultado.
O texto resume as fontes com palavras próprias. Citações literais, quando há, são curtas.

**Limitação da coleta:** o orçamento de buscas web da sessão (compartilhado entre agentes) acabou na metade da pesquisa. Várias páginas oficiais (Autodesk Help/blogs, padrões buildingSMART, Graphisoft Community, Workana) devolveram HTTP 403 ao WebFetch. Por isso parte dos achados vem de resumos de resultados de busca, não da página completa. Cada item indica isso quando é o caso. Itens sem fonte verificada ficaram em "Lacunas".

---

## 1. Archicad: modelo analítico estrutural, exportação SAF, MEP Modeler/MEP Designer, roteamento e conexões, limitações

### Takeaway
O Archicad trata estrutura de forma "leve": o modelo físico arquitetônico gera membros analíticos, exportados em SAF (formato aberto baseado em planilha .xlsx, iniciativa da Nemetschek), com conexões diretas a Frilo e SCIA. Não há armadura detalhada nem análise interna. Em MEP, o antigo add-on "MEP Modeler" virou o "MEP Designer", integrado desde o Archicad 28. Ele faz roteamento de dutos e tubos com especificações de rota, System Browser com cálculos básicos (vazão/velocidade de ar, hidrônico com resfriamento a partir de 2026) e elétrica ainda experimental. Usuários relatam histórico de bugs e regressões (AC27).

### Achados citados
**Estrutura / SAF**
- A exportação SAF sai por *Arquivo > Salvar como* (formato SAF, *.xlsx), a partir da planta ou do 3D. Dá para escolher o projeto inteiro, só os elementos visíveis na vista ou só a seleção. Também sai por *Documento > Publicar*, que exporta os membros analíticos visíveis nas vistas publicadas. — [Graphisoft Help AC30: Export SAF File](https://help.graphisoft.com/AC/30/INT/Topics/091_StructuralAnalysisFormat/091_StructuralAnalysisFormat-2.html)
- A exportação usa os "SAF Translators" do projeto. O help recomenda preencher Nome do Projeto e do Edifício em Project Info, porque esses campos vão para as abas Project/Model Data do arquivo. Há conexões dedicadas: "Frilo Connection" (feita pela Graphisoft) e "SCIA Connection" (feita pela SCIA, distribuída na página de add-ons de parceiros). A página fala de "analytical members", mas não diz se apoios e cargas vão junto. — [Graphisoft Help AC30: Export SAF File](https://help.graphisoft.com/AC/30/INT/Topics/091_StructuralAnalysisFormat/091_StructuralAnalysisFormat-2.html)
- O procedimento aparece de forma igual nas versões AC24 a AC30 (há páginas de help equivalentes para cada versão). — [Graphisoft Help AC24](https://help.graphisoft.com/AC/24/INT/_AC24_Help/082_StructuralAnalysisFormat/082_StructuralAnalysisFormat-2.htm); [Graphisoft Help Center: Export SAF](https://helpcenter.graphisoft.com/user-guide/128749/) (resultado de busca)
- O SAF é uma iniciativa de formato aberto de troca entre softwares de análise estrutural. Vem do Grupo Nemetschek, tem coordenação atual da SCIA e é baseado no formato Excel. Existe um visualizador web gratuito. — [saf.guide: What is SAF](https://www.saf.guide/en/stable/getting-started/what-is-saf.html)
- O conteúdo do SAF inclui elementos de curva e de superfície, pavimentos, materiais, seções, conexões pontuais, apoios, rótulas, grupos, casos e combinações de carga, ações e até resultados (esforços internos). — [saf.guide (índice)](https://www.saf.guide/en/stable/)
- Suporte declarado pelos próprios parceiros (última atualização: agosto de 2022):
  - importam e exportam SAF: SCIA, RISA, Graphisoft, Allplan, Radimpex, AxisVM, Sofistik, Dlubal, mbAEC, D.I.E, InfoGraph, NextFEM, MasterSap, Prota;
  - só importam: FRILO, LIRA SAPR, FEM-Design, ConSteel, IDEA, MINEA;
  - importam via conversor: Robot e Dlubal.

  Nenhum software brasileiro (TQS, Eberick) aparece na lista. — [saf.guide: Who supports SAF](https://www.saf.guide/en/stable/getting-started/who-supports-saf.html)

**MEP Designer (AC28 em diante)**
- No AC28, o MEP Designer passou a vir integrado ao Archicad, com colaboração via Teamwork. Recursos:
  - "Route Specifications" (substituem as antigas Route Preferences): tamanhos de segmento (DN, diâmetro interno, descrição), curvas e tês predefinidos, para usar bitolas de mercado;
  - alinhamento e offset da rota (por exemplo, colar o duto na face inferior da laje ou manter distância de parede ou forro), definidos antes ou depois de traçar a rota, ou por segmento;
  - modelagem em corte e vista;
  - tubo flexível;
  - novos objetos: manifolds, radiadores, suportes de duto e tubo, take-offs. — [Graphisoft Help AC28: MEP Designer](https://help.graphisoft.com/AC/28/INT/_AC28_Help/005_NewFeatures/005_NewFeatures-14.htm)
- Sistemas e cálculos no AC28:
  - o MEP System Browser mostra os sistemas em árvore ou lista;
  - uma rota ligada a um objeto MEP herda o sistema e o tipo de conexão dele;
  - a opção "Open MEP Connections" marca na planta as conexões abertas (erros);
  - o browser calcula vazão e velocidade do ar por rota;
  - o "Duct Optimizer" redimensiona rotas ou sistemas a partir de limites definidos pelo usuário (dimensão, velocidade).

  A página não fala de eletrocalhas nem de IFC. — [Graphisoft Help AC28: MEP Designer](https://help.graphisoft.com/AC/28/INT/_AC28_Help/005_NewFeatures/005_NewFeatures-14.htm)
- Novidades do "MEP Designer 2026" (help AC30):
  - as rotas mantêm conectividade e alinhamento quando os elementos mudam;
  - detecção e reparo de conexões quebradas;
  - definições de sistema unificadas, com tipos de linha e cores por rota em 2D e 3D;
  - simbologia esquemática padronizada em planta;
  - cálculos hidrônicos e System Browser passam a cobrir resfriamento;
  - bibliotecas ampliadas;
  - "Import RFA", que permite escolher um produto de uma família RFA;
  - override que mostra a arquitetura transparente;
  - elétrica: "basic electrical power system design", marcada como **experimental**, sem compromisso de compatibilidade futura. — [Graphisoft Help AC30: New Features in MEP Design](https://help.graphisoft.com/AC/30/INT/Topics/005_NewFeatures/WelcometoMEP_Beta.html)
- Segundo o resumo de busca da página de produto do AC29, o kit MEP exige o plano de assinatura "Archicad Collaborate". O help de IFC MEP do AC30 também cita "Archicad Collaborate ou Archicad Max". O AC29 traria ainda um "AI Assistant (beta)" para o MEP Designer e a inserção de acessórios em rotas com um clique. — resultado de busca sobre [graphisoft.com whatsnew](https://graphisoft.com/de/whatsnew}}) (página não aberta); [Graphisoft Help AC30: MEP elements in IFC exchange](https://help.graphisoft.com/AC/30/INT/Topics/085_MEPDesigner/085_MEPDesigner-49.html)
- Configurações de rota do AC29: existe uma página "Route Settings" (não aberta). — [Graphisoft Help AC29: Route Settings](https://help.graphisoft.com/AC/29/INT/_AC29_Help/085_MEPDesigner/085_MEPDesigner-19.htm)

**MEP e IFC no Archicad**
- Importação: depende do tradutor de importação IFC (Geometry Conversion > Distribution elements: "MEP elements, otherwise Objects").
  - Conexões e take-offs viram conexões nativas.
  - Equipamentos com portas são convertidos conforme a posição da porta.
  - Quando o IFC não traz dados suficientes, o Archicad cria "MEP Equipment" não paramétrico. Com ainda menos dados, cria objeto genérico.
- Exportação: o tipo IFC sai do "IFC Type Mapping", por tipo de elemento ou por classificação (classificação → IFC Type, Type Product e PredefinedType).
- A página não explica como sistemas (IfcSystem) nem conexões entre portas são exportados. — [Graphisoft Help AC30: MEP elements in IFC exchange](https://help.graphisoft.com/AC/30/INT/Topics/085_MEPDesigner/085_MEPDesigner-49.html)

**Limitações relatadas por usuários** (resumo de busca dos fóruns; páginas com 403)
- Anos 2009–2010 (MEP Modeler antigo):
  - um usuário com experiência em projeto de instalações citou muitas limitações e bugs;
  - objetos 3D salvos perdiam os conectores de duto e tubo;
  - não dava para girar objetos nos eixos X e Y. — [Graphisoft Community: MEP Modeller](https://community.graphisoft.com/t5/Collaboration-with-other/MEP-Modeller/m-p/198750)
- AC26–27 (2024–2025):
  - elementos MEP não podiam ser destacados no Issue Manager, problema que um usuário diz persistir no AC27.2 — [Graphisoft Community: MEP 27 Issue manager not working](https://forum.graphisoft.de/t5/Project-data-BIM/MEP-27-Issue-manager-not-working/td-p/589903);
  - um tópico longo, "MEP 27 – The New Feature that never happened", relata usuários voltando ao AC26 para cumprir entregas de MEP e reclama da dificuldade de extrair quantitativos precisos de material — [Graphisoft Community: MEP 27 – The New Feature that never happened](https://community.graphisoft.com/t5/Modeling/MEP-27-The-New-Feature-that-never-happened/m-p/683282).
- Não foi encontrada resposta oficial da Graphisoft a esses tópicos.

### Inferências
- Para o Archicad, estrutura é "coordenação mais exportação analítica", não projeto estrutural: o cálculo e o detalhamento de armadura ficam em softwares de engenharia. O modelo do BrasBim pode seguir essa linha: elementos físicos IFC (IfcColumn, IfcBeam, IfcSlab, IfcFooting) com o mínimo de dados para virar modelo analítico (eixo, material, seção, apoio).
- O MEP do Archicad mira o arquiteto e o projetista de pequeno porte: traçado conectado, sistemas, cálculos simples. Mesmo assim, levou várias versões para ficar estável, e a elétrica ainda é experimental em 2026.
- A ausência de software brasileiro na lista SAF sugere que, no Brasil, IFC é o canal realista com TQS e Eberick, e não SAF.

### Lacunas
- Não confirmei se o SAF do Archicad exporta apoios e cargas, nem como o Archicad gera os membros analíticos (ajustes automáticos, "structural integrity"). A busca sobre o assunto não rodou porque o orçamento acabou.
- Não está claro se o MEP Designer 2026 tem cálculo hidráulico de água fria/quente ou esgoto (dimensionamento por peso ou UHC). As fontes falam só de ventilação e hidrônico (aquecimento e resfriamento).
- Não verifiquei se houve resposta ou correção para os problemas do AC27.

---

## 2. Revit: estrutura (pórticos, pilares, fundações, armadura, modelo analítico, conexões, Robot) e MEP (tubos, dutos, eletrocalhas, eletrodutos, sistemas, cálculos, fabricação); reclamações

### Takeaway
O Revit cobre estrutura e MEP em profundidade dentro de um único produto:
- estrutura: armadura paramétrica, com dobra ("cranking") nova no 2026, conexões de aço customizáveis, e modelo analítico separado do físico desde o 2023, com automação via Dynamo;
- MEP: sistemas com cálculos de perda de carga (override de coeficientes no 2026) e dimensionamento de condutores.

Usuários reclamam da regressão no redimensionamento conjunto de tubo e conexão no Revit 2027 e de exportações IFC4 que perdem informação de sistema.

### Achados citados
**Estrutura**
- Revit 2026, armadura:
  - "rebar cranking" paramétrico (barras com dobra para traspasse em pilares e regiões congestionadas), baseado em tipo, com override por instância, para armadura por forma ou livre;
  - a armadura se ajusta quando muda o cobrimento, a seção ou o layout do conjunto;
  - indicadores de início e fim nas barras. — [Arkance/CADD: Top new features in Revit Structure 2026](https://arkance.us/blog/top-new-features-in-revit-structure-2026) (resultado de busca); [Symetri: What's new in Revit 2026](https://www.symetri.co.uk/insights/blog/what-s-new-in-revit-2026-a-guide-to-the-latest-features/)
- Revit 2026, quantitativos de armadura: barras de geometria idêntica passam a ficar na mesma partição das tabelas de dobra. Antes, cada instância era tabelada sozinha, o que gerava tabelas ruins. O ajuste do comprimento da dobra fica num diálogo próprio. — [Symetri](https://www.symetri.co.uk/insights/blog/what-s-new-in-revit-2026-a-guide-to-the-latest-features/)
- Revit 2026, aço:
  - um ajuste global (Structural Settings > Structural Steel Elements) remove os recuos (setbacks/cutbacks) de todas as peças, que passam a ser modeladas ponto a ponto. Antes era preciso removê-los à mão para exportar IFC ou mandar ao Advance Steel;
  - conexões de aço customizadas: padrões de parafuso, furo, chumbador e conector de cisalhamento ficam editáveis no editor de esboço, e elementos removidos da conexão ficam no modelo como peças avulsas. — [Symetri](https://www.symetri.co.uk/insights/blog/what-s-new-in-revit-2026-a-guide-to-the-latest-features/); [Autodesk: What's new in Revit 2026](https://www.autodesk.com/blogs/aec/2025/04/02/whats-new-in-revit-2026/) (resultado de busca; página com 403)
- Modelo analítico (Revit 2023 em diante), segundo resumo de busca do blog Autodesk de 23/01/2023:
  - no modelo antigo, mover o elemento físico arrastava o analítico, o que era pouco flexível em estruturas complexas;
  - a nova abordagem separa os dois e oferece scripts Dynamo prontos: físico → analítico (com hierarquia de prioridade em 3 níveis, por exemplo pilar antes de viga, tolerância de distância para conectar nós e associação analítico↔físico) e analítico → físico. — [Autodesk Blog: Structural Analytical Model Automation](https://www.autodesk.com/blogs/aec/2023/01/23/structural-analytical-model-automation/) (resultado de busca; página com 403)
- Já em 2019 existia um pacote Dynamo "Analytical Modeling", com regras por tipo de edifício. — [Autodesk Blog 2019](https://www.autodesk.com/blogs/aec/2019/04/08/autodesk-analytical-modeling-2019-dynamo-package/) (resultado de busca)
- Revit 2026.3 (set/2025): multisseleção para condições de contorno e cargas, e "pin" de elementos analíticos. A fonte é uma listagem secundária (Product Hunt/hunted.space) e merece confirmação. — [hunted.space: Revit 2026.3](https://www.hunted.space/product/revit-2026-3)
- Robot: segundo o saf.guide, o Robot importa SAF só via conversor. — [saf.guide: Who supports SAF](https://www.saf.guide/en/stable/getting-started/who-supports-saf.html)

**MEP**
- Revit 2026, segundo a descrição de uma aula da Autodesk University:
  - override dos coeficientes de perda de carga de dutos e tubos, pedido antigo para cálculo de perda de pressão;
  - na elétrica, bitolas de condutor controláveis pelo usuário e atribuição de cabo a circuito;
  - automação via Dynamo. — [AU: Extending Automated MEP Analysis in Revit 2026/2025](https://www.autodesk.com/autodesk-university/class/Extending-Automated-MEP-Analysis-in-Revit-2026-2025) (resultado de busca; página com 403)
- Regressão no Revit 2027 (relato de usuário no Ideas Board): o redimensionamento conjunto de segmentos e conexões pela seleção múltipla foi removido, e agora é preciso redimensionar tubos e conexões em separado. — [Autodesk Ideas: Revit 2027 duct/pipe/conduit & tray sizing](https://forums.autodesk.com/t5/revit-ideas/revit-2027-duct-pipe-conduit-amp-tray-sizing/idi-p/14166334)
- Um pedido antigo (2015) de dimensionamento automático de grandes redes de tubulação com parâmetros customizáveis: não há evidência de que tenha sido atendido. — [AUGI Wish List](https://forums.augi.com/archive/index.php/t-162101.html)
- IFC4 a partir do Revit:
  - num caso de 2020, tubos (IfcPipeSegment) exportados em IFC2x3 mostravam o IfcSystem no Solibri, mas em IFC4 não. Outro usuário explicou que o IfcDistributionSystem agrupa qualquer IfcProduct via IfcRelAssignsToGroup, logo o esquema permite a associação. A causa da diferença (exportador, visualizador ou esquema) ficou sem resposta — [buildingSMART Forums: IfcSystem information related to pipes – IFC4 from Revit](https://forums.buildingsmart.org/t/ifcsystem-information-related-to-pipes-ifc4-from-revit/3178);
  - a Graphisoft oferece um add-in gratuito para o Revit ("IFC Model Exchange with Archicad"), atualizado todo ano, com versão para Revit 2026 marcada como entregue em dez/2025. Ele melhora a importação e a exportação IFC entre os dois. A Graphisoft recomenda que usuários de Revit MEP usem o add-in só para importação — [Graphisoft Community: IFC Model Exchange with Archicad for Revit 2026](https://community.graphisoft.com/t5/Product-Roadmap/IFC-Model-Exchange-with-Archicad-for-Revit-2026/idi-p/673186); [Graphisoft Downloads: Interoperability](https://www.graphisoft.com/downloads/interoperability) (resultados de busca).

**AutoCAD MEP / Plant 3D (breve)**
- Nenhuma fonte foi coletada nesta sessão (orçamento de busca esgotado).

### Inferências
- O Revit é a referência de "MEP completo" (sistemas, perdas de carga, circuitos, fabricação) e de "estrutura detalhada" (armadura com tabela de dobra). Copiar esse escopo seria inviável e desnecessário para o BrasBim. O diferencial possível é a qualidade do IFC (sistemas e portas corretos), não a profundidade de cálculo.
- O próprio Revit separou físico de analítico. Isso indica que o modelo analítico deve ser derivado do físico por regras (prioridades, tolerâncias) e não acoplado rigidamente a ele.
- Os cálculos internos do Revit seguem métodos genéricos e não normas brasileiras (NBR 5626, 8160, 10844, 5410). Daí o espaço de plugins e softwares locais como o QiBuilder. Essa leitura é inferência; não achei fonte que a confirme diretamente.

### Lacunas
- Não consegui abrir o help oficial do Revit (403) para listar com fonte as capacidades base de MEP: tubos, dutos, eletrocalhas, eletrodutos, peças hidrossanitárias, sistemas, dimensionamento automático e fabricação (MEP Fabrication/ITM). Também não confirmei fundações e as ferramentas de análise integradas (ex.: Robot Structural Analysis Link, análise na nuvem).
- Faltam reclamações sistemáticas (Reddit, Autodesk Community) sobre MEP e armadura no Revit. Não foram coletadas.
- Não pesquisei AutoCAD MEP nem Plant 3D.

---

## 3. Prática brasileira: ferramentas de estrutura (TQS, Eberick/AltoQi, CYPE) e instalações (QiBuilder/AltoQi, CYPE, Revit MEP), troca de IFC com arquitetos e problemas comuns

### Takeaway
No Brasil, quem calcula estrutura e projeta instalações usa softwares locais com normas ABNT: TQS e Eberick na estrutura, QiBuilder (AltoQi) e CYPE nas instalações. A troca com a arquitetura acontece por IFC e, em parte, por DWG. O arquiteto entrega o IFC, e o engenheiro devolve o IFC da estrutura ou das instalações para compatibilização (clash e BCF). Os problemas típicos são de mapeamento: elementos que chegam como Morph ou objeto genérico, ou opções de exportação erradas.

### Achados citados
- **Eberick (AltoQi):** software BIM de projeto estrutural com normas ABNT e suporte em português. Recursos:
  - lançamento em ambiente tipo CAD, que gera um modelo 3D;
  - análise integrada, dinâmica e por elementos finitos;
  - detalhamento automático de armadura e quantitativos;
  - IFC import/export, clash detection, notas BCF e furos automáticos;
  - módulo de programação visual com Python ("Axis Nodes");
  - sistemas: concreto armado, protendido e pré-moldado, alvenaria estrutural, perfis de aço e núcleos rígidos;
  - planos em níveis (Demo, Professional, Premium, Enterprise, Infinity) e pacotes "InBIM" (Eberick + Builder), com limites de área e de número de pavimentos.

  A página diz ter mais de 70 mil clientes numa seção e 84 mil em outra (inconsistência da própria fonte). Não cita Revit nem Archicad pelo nome. — [AltoQi Eberick](https://www.altoqi.com.br/eberick)
- Um artigo promocional diz que o Eberick importa arquivos arquitetônicos (DWG/DXF como via principal) e que o fluxo de compatibilização é sobrepor a estrutura e ajustar pilares e vigas às aberturas. É conteúdo de marketing, sem versão. — [Cursa: compatibilização com Eberick](https://cursa.app/pt/artigo/como-otimizar-a-compatibilizacao-de-projetos-arquitetonicos-e-estruturais-usando-o-eberick) (resultado de busca)
- **QiBuilder (AltoQi):** módulos de elétrica (NBR 5410), fotovoltaica, SPDA (NBR 5419/2015), cabeamento estruturado (NBR 14565, TIA/EIA 568-B), hidrossanitário (água fria e quente, esgoto, pluvial, ventilação), incêndio (sprinklers, hidrantes, extintores), gás (GLP e GN) e climatização (split, VRF). Faz importação e exportação IFC, verificação de interferências e notas BCF. A divisão por plano é Professional (elétrica, hidráulica, incêndio, gás, climatização), Premium (SPDA e cabeamento) e Enterprise (barramento). — [AltoQi QiBuilder](https://www.altoqi.com.br/qibuilder)
- Um estudo de licitação pública (TRE-SP, 2023) diz que a importação IFC é nativa no QiBuilder (pacote "Plena ESSENCIAL") e que o concorrente PRO-Elétrica não importa IFC. — [TRE-SP: estudos preliminares IL 013/2023](https://www.tre-sp.jus.br/transparencia-e-prestacao-de-contas/licitacoes/aquisicao-contratacao-direta-covid-19/inexigibilidade-de-licitacao-2023/estudos-preliminares-il-013-2023-pdf) (resultado de busca)
- Uma vaga freelance de complementares em QiBuilder para um sobrado de 260 m² pede o modelo das instalações exportado em IFC para revisão e compatibilização. O cliente fornece o IFC da estrutura. Isso ilustra o fluxo típico de pequeno porte. — [Workana: projetista de complementares QiBuilder](https://www.workana.com/pt/job/projetista-de-complementares-qibuilder-bim-para-sobrado-de-260m2) (resultado de busca; página com 403)
- **TQS:** empresa de São Paulo com software de engenharia estrutural e geotécnica. A home não fala de BIM nem de IFC na parte visível — [TQS](https://www.tqs.com.br/). Existe um "Plugin TQS" gratuito para Revit na Autodesk App Store (versões 2022 e 2023 nos resultados) que importa e exporta dados entre TQS e Revit — [Autodesk App Store (listagem)](https://apps.autodesk.com/RVT/pt/List/Search?page=47) (resultado de busca).
- Um TCC do Mackenzie (17/06/2021) analisou a interoperabilidade Revit↔TQS com plugins nativos e IFC, partindo de um modelo feito no TQS. O resumo não detalha perdas. — [Mackenzie: Análise da interoperabilidade REVIT e TQS](https://dspace.mackenzie.br/handle/10899/29031)
- Problema concreto TQS → Archicad: pilares, vigas e lajes chegavam como "Morph" ou "Objeto". A causa era a opção de exportação "Graphisoft" do TQS, que tem duas variantes (anterior e posterior a 2014). A variante antiga gera Morph, e a posterior evita o problema. — [Graphisoft Community (pt): Importação de IFC de modelo TQS](https://community.graphisoft.com/t5/Colabora%C3%A7%C3%A3o-com-outros-softwares/Importa%C3%A7%C3%A3o-de-IFC-de-modelo-TQS/m-p/659684) (resultado de busca; página com 403)
- **CYPE:** oferece um plugin "Open BIM" para Revit com "IFC Options", que sobrescreve as opções de importação e exportação IFC do Revit e mapeia classes IFC para categorias. — [CYPE Learning: Plugin Open BIM Revit – IFC options](https://learning.cype.com/en/video/open-bim-plugin-revit-ifc-options-configuration) (resultado de busca)

### Inferências
- O fluxo brasileiro de pequeno e médio porte é "arquiteto (Revit, Archicad ou SketchUp) → IFC → engenheiro (Eberick, TQS, QiBuilder, CYPE) → IFC de volta para compatibilização". Para o BrasBim, isso significa:
  1. exportar arquitetura IFC limpa (pavimentos, paredes, lajes, aberturas e espaços com classes corretas) que Eberick e QiBuilder consigam usar como base;
  2. importar e exibir como referência IFC de estrutura e de instalações, com classes nativas e não proxies, inclusive em IFC2x3, que esses softwares ainda podem gerar;
  3. ler e escrever BCF para o ciclo de compatibilização.
- Calcular estrutura ou dimensionar instalações por NBR dentro do BrasBim competiria com produtos locais maduros e bem estabelecidos. Faz mais sentido o BrasBim cuidar da coordenação: furos e passagens, shafts, reservas de espaço, verificação de interferências.
- Os problemas mais citados são de mapeamento de classes e opções de exportador (Morph, proxy, sistema perdido), e não de geometria. Validar o IFC gerado com testes, como o BrasBim já faz, ataca exatamente esse ponto.

### Lacunas
- Não confirmei a versão de IFC que Eberick, TQS e QiBuilder exportam (2x3 ou 4), nem se tubos e conexões do QiBuilder saem como IfcPipeSegment/IfcPipeFitting com portas e sistemas. Também não confirmei como cada um lê IFC de arquitetura (que classes aproveita para lançar pilares ou pontos de consumo).
- CYPE Brasil (CYPECAD, CYPEPLUMBING, BIMserver.center): a página pt-br deu 404 e não foi verificada.
- Não coletei, por falta de orçamento de busca, depoimentos de blogs e YouTube brasileiros sobre problemas de compatibilização (níveis, coordenadas, unidades, georreferência).

---

## 4. Entidades IFC e fluxos de troca para estrutura e MEP (IfcReinforcingBar, IfcPipeSegment, IfcDistributionSystem, MEP no IFC4): o que funciona e o que falha

### Takeaway
O IFC4/4.3 tem um modelo rico para MEP:
- segmentos e conexões tipados (IfcPipeSegment, IfcPipeFitting com PredefinedType);
- portas (IfcDistributionPort) aninhadas via IfcRelNests, com direção de fluxo e tipo de sistema;
- sistemas (IfcDistributionSystem) agrupando membros via IfcRelAssignsToGroup.

Na prática, exportadores perdem os sistemas (Revit IFC4), trocam classes por IfcBuildingElementProxy (SketchUp com agrupamento) ou não exportam as conexões entre portas (o help do Archicad nem descreve isso). Na volta, o importador cai para objetos genéricos quando faltam dados.

### Achados citados
- IfcDistributionPort (IFC4.x):
  - as portas se ligam ao produto por IfcRelNests;
  - IfcRelConnectsPortToElement fica reservado a portas anexadas dinamicamente;
  - uma porta com tipo de sistema definido só conecta a outra do mesmo tipo, e as duas pontas precisam ter direções de fluxo opostas. — [IFC4x2 (nibs.org): IfcDistributionPort](https://nibs.org/files/docs/IFC4x2_Bridge/schema/ifcsharedbldgserviceelements/lexical/ifcdistributionport.htm) (resultado de busca)
- IfcPipeFitting: tipos predefinidos como BEND, JUNCTION e CONNECTOR definem papéis específicos de entrada e saída das portas. Exportador que erra isso gera portas desconectadas ou com direção trocada. — [IFC4x2 (nibs.org): IfcPipeFitting](https://nibs.org/files/docs/IFC4x2_Bridge/schema/ifchvacdomain/lexical/ifcpipefitting.htm); [IfcPipeSegment](https://nibs.org/files/docs/IFC4x2_Bridge/schema/ifchvacdomain/lexical/ifcpipesegment.htm) (resultados de busca)
- O IfcDistributionSystem se comporta como grupo e pode conter qualquer IfcProduct via IfcRelAssignsToGroup. Mesmo assim, o Revit em IFC4 não mostrou o sistema dos tubos no Solibri (2020, sem solução no tópico). — [buildingSMART Forums](https://forums.buildingsmart.org/t/ifcsystem-information-related-to-pipes-ifc4-from-revit/3178)
- No SketchUp, tubos agrupados num sistema IFC saíram como IfcBuildingElementProxy em vez de IfcPipeSegment, e os sistemas não podiam atravessar pavimentos. — [SketchUp Forum: Group IfcPipeSegment elements as IfcSystem](https://forums.sketchup.com/t/group-ifcpipesegment-elements-as-ifcsystem/229471) (resultado de busca)
- Archicad: importa segmentos, conexões e equipamentos como MEP nativo quando há dados e cai para equipamento não paramétrico ou objeto genérico quando não há. Na exportação, o tipo IFC e o PredefinedType vêm do Type Mapping, por tipo de elemento ou por classificação. — [Graphisoft Help AC30: MEP elements in IFC exchange](https://help.graphisoft.com/AC/30/INT/Topics/085_MEPDesigner/085_MEPDesigner-49.html)
- Estrutura: o Revit 2026 removeu os recuos das peças de aço justamente para melhorar a exportação IFC e o envio ao Advance Steel. Isso indica que a geometria "de detalhamento" atrapalhava a troca. — [Symetri](https://www.symetri.co.uk/insights/blog/what-s-new-in-revit-2026-a-guide-to-the-latest-features/)
- Estrutura: elementos do TQS chegavam ao Archicad como Morph quando a variante de exportação estava errada (ver seção 3). — [Graphisoft Community (pt)](https://community.graphisoft.com/t5/Colabora%C3%A7%C3%A3o-com-outros-softwares/Importa%C3%A7%C3%A3o-de-IFC-de-modelo-TQS/m-p/659684) (resultado de busca)
- Para o modelo analítico, o canal aberto de fato usado pela Graphisoft e por vários softwares europeus é o SAF (.xlsx), não o domínio estrutural-analítico do IFC (IfcStructuralAnalysisModel). Nenhuma fonte desta coleta mostrou uso prático de IfcStructuralAnalysisModel. — [saf.guide](https://www.saf.guide/en/stable/getting-started/who-supports-saf.html); [Graphisoft Help AC30: SAF](https://help.graphisoft.com/AC/30/INT/Topics/091_StructuralAnalysisFormat/091_StructuralAnalysisFormat-2.html)

### Inferências
- Para o BrasBim, que já usa IFC 4.3 como modelo em memória:
  - MEP mínimo útil e "correto por construção":
    - IfcPipeSegment e IfcPipeFitting com PredefinedType;
    - IfcDistributionPort aninhada (IfcRelNests) com FlowDirection e SystemType coerentes, conectada por IfcRelConnectsPorts;
    - IfcDistributionSystem com PredefinedType para água fria, água quente, esgoto, pluvial e elétrica, agrupando via IfcRelAssignsToGroup e referenciado aos pavimentos.

    Os testes devem verificar portas opostas conectadas, sistemas presentes e nenhum proxy;
  - estrutura: exportar elementos físicos tipados com material e perfil (IfcMaterialProfileSet). IfcReinforcingBar é avançado e provavelmente deve ficar para os softwares de cálculo; o BrasBim pode só importar e exibir;
  - analítico: considerar exportar SAF (aberto, .xlsx) ou IfcStructuralAnalysisModel como recurso opcional futuro. Como TQS e Eberick não aparecem na lista SAF, no Brasil a prioridade é o IFC físico.
- Tolerar IFC2x3 na importação de referência é provavelmente necessário (inferência, sem confirmação das versões que os softwares brasileiros exportam).

### Lacunas
- As páginas oficiais IFC 4.3 da buildingSMART (IfcReinforcingBar, IfcDistributionSystem) devolveram 403. Não registrei com fonte a lista de PredefinedType de IfcDistributionSystem (ex.: DOMESTICCOLDWATER, DOMESTICHOTWATER, SEWAGE, STORMWATER...) nem os atributos e a geometria recomendada de IfcReinforcingBar (ex.: IfcSweptDiskSolid). Confirmar direto na documentação IFC 4.3 ou no esquema do IfcOpenShell antes de especificar.
- Não achei relatos práticos de uso de IfcStructuralAnalysisModel entre ferramentas comerciais.
- Não pesquisei IDS ou MVDs específicos de MEP (ex.: requisitos de troca para instalações) nem o ifcopenshell.api para sistemas e portas.
