# Normas brasileiras de documentação arquitetônica e prática de projeto legal (aprovação), executivo e as-built, e como os usuários as produzem em Archicad/Revit/AutoCAD

> Pesquisa clean-room, só com fontes públicas da web. Acesso a todas as fontes em **2026-10-21**.
> Não foi lido nenhum texto pago da ABNT. Uma URL que parece hospedar o PDF integral da NBR 6492:2021 (arquivos.ufrrj.br) apareceu na busca e **foi deliberadamente ignorada**: usá-la violaria a regra de não obter textos pagos.
> **Limitação importante:** o orçamento de buscas web da sessão (compartilhado entre os agentes) acabou no meio da pesquisa. Vários tópicos ficaram sem fonte e estão listados como lacunas. Recomenda-se uma segunda rodada de pesquisa só para eles (ver "Gaps" em cada seção).

## 1. ABNT NBR 6492:2021 e normas de desenho correlatas (10068, 10582, 8196, 8403, 13142)

### Takeaway
A NBR 6492 está na 2ª edição, de 16/06/2021. O título mudou de "Representação de projetos de arquitetura" para "Documentação técnica para projetos arquitetônicos e urbanísticos — Requisitos": a norma deixou de tratar só de *representação gráfica* e passou a tratar de *documentação* (conteúdo por etapa, identificação de folhas). Não achei fonte pública confiável que liste o que mudou ponto a ponto.

### Cited Findings
- 2ª edição datada de 16.06.2021, título "Documentação técnica para projetos arquitetônicos e urbanísticos — Requisitos". Algumas ementas de disciplina ainda usam o título antigo ("Representação de projetos de arquitetura"). Fonte: snippet de resultado de busca que mostra a capa; o PDF em si **não foi aberto**, por ser texto pago hospedado por terceiros. — resultado de busca: arquivos.ufrrj.br, NBR_6492_2021 (endereço de cópia não autorizada omitido; NÃO USAR) (só o título/data do snippet); [Ementa IFPB Expressão Gráfica II](https://estudante.ifpb.edu.br/media/cursos/357/disciplina/EXPRESS%C3%83O_GR%C3%81FICA_II.pdf)
- Segundo bancos de questões de concurso, a identificação mínima de cada folha (carimbo/selo) inclui: empresa, cliente, título do desenho, sequência do projeto (número ou letra), escala, local e data, autoria, responsável técnico e indicação de revisão. — [Gran Cursos – questões NBR 6492](https://questoes.grancursosonline.com.br/questoes-de-concursos/arquitetura-nbr-6492-representacao-de-projetos-de-arquitetura-429878) (via snippet de busca; a página dá 403 ao WebFetch)
- Também segundo bancos de questões, o Estudo Preliminar (sigla EP-ARQ) deve trazer implantação, plantas de todos os pavimentos e cortes longitudinal e transversal com dimensões gerais e níveis principais. — [Gran Cursos (snippet)](https://questoes.grancursosonline.com.br/questoes-de-concursos/arquitetura-nbr-6492-representacao-de-projetos-de-arquitetura-429878)
- Corte definido como plano secante vertical que divide o edifício em duas partes (longitudinal ou transversal). Alguns itens desses bancos sobre altura do plano de corte e regras de cota **se contradizem**, então não devem ser tomados como texto da norma. — [Gran Cursos (snippet)](https://questoes.grancursosonline.com.br/questoes-de-concursos/arquitetura-nbr-6492-representacao-de-projetos-de-arquitetura-429878)
- Prefeituras citam a NBR 6492 como referência obrigatória de representação. Jacareí-SP exige plantas "conforme normas técnicas vigentes (em especial NBR-ABNT 6492)" e textos e cotas "em tamanho legível, conforme NBR-ABNT 6492". — [Jacareí – Anexo XII Manual Técnico](https://www.jacarei.sp.gov.br/wp-content/uploads/2018/11/12-Anexo-XII-Manual-Técnico.pdf)
- Artigo do Sienge cita a NBR 8196 como norma dos princípios gerais de representação em desenho técnico e a NBR 6492 para projetos de arquitetura. — [Sienge – Projeto executivo](https://sienge.com.br/blog/projeto-executivo-o-que-e-como-fazer/)

### Inferences
- A mudança de título sugere que a edição de 2021 se alinha à NBR 16636 (etapas e documentos por etapa) e usa siglas por etapa e disciplina, como "EP-ARQ". Isso favorece um template do BrasBim que organize folhas por **etapa + disciplina** e gere o selo a partir de metadados do IFC (IfcProject/IfcOwnerHistory/propriedades da folha).
- Os campos mínimos do selo (empresa, cliente, título, sequência, escala, local/data, autoria, RT, revisão) podem virar um conjunto de propriedades padrão no BrasBim, preenchidas automaticamente.

### Gaps
- Lista oficial das mudanças entre a NBR 6492:1994 e a de 2021: não achei resumo público confiável (a busca não retornou comparativo; orçamento de busca esgotado).
- Espessuras de pena, tipos de linha, simbologia (norte, cortes, níveis, portas) e escalas recomendadas na 6492:2021: sem fonte pública verificada nesta rodada.
- NBR 10068 (formatos A0–A4 e margens), NBR 10582 (posição da legenda), NBR 8403 (tipos e larguras de linha), NBR 13142 (dobramento de cópias) e NBR 8196 (escalas): nesta rodada não consegui fontes públicas com o conteúdo. São normas clássicas de desenho técnico. Valores amplamente conhecidos (A-series ISO 216; dobra final em A4 com a legenda visível; escalas 1:1, 1:2, 1:5, 1:10, 1:20, 1:50, 1:100, 1:200, 1:500…) precisam de confirmação em fonte pública antes de entrar na spec.

## 2. NBR 16636 (etapas de projeto) e NBR 13532 (histórica)

### Takeaway
A NBR 16636 tem três partes. A Parte 2 (projeto arquitetônico) organiza a sequência levantamento → estudo preliminar → anteprojeto → projeto para licenciamentos ("projeto legal") → projeto executivo → projeto completo de edificação → documentação *as built*. A Parte 3 (urbanístico) é de 2020. A NBR 13532 é a norma anterior de elaboração de projetos de arquitetura e ainda aparece em concursos.

### Cited Findings
- Material de aula da USP (snippet de busca) lista as etapas da NBR 16636-2: estudo preliminar, anteprojeto, projeto para licenciamentos, projeto executivo, projeto completo de edificação e documentação "as built". Também informa que a Parte 3 (projeto urbanístico) foi publicada em 2020. — [USP e-Disciplinas – Gestão do Processo de Projeto (PDF)](https://edisciplinas.usp.br/pluginfile.php/5809393/mod_resource/content/2/GEST%C3%83O%20PROCESSO%20PROJETO.pdf) (o WebFetch devolveu só a página de login do Moodle; o dado vem do snippet)
- Banco de questões: a NBR 16636-2 divide o processo em duas fases, a preparação e a elaboração e desenvolvimento de projetos técnicos, e o projeto para licenciamentos fica na segunda. Há uma questão que põe o "as built" na fase de preparação, mas como alternativa incorreta. — [Gran Cursos – NBR 16636-2](https://questoes.grancursosonline.com.br/questoes-de-concursos/arquitetura-nbr-16636-2-elaboracao-e-desenvolvimento-de-servicos-tecnicos-especializados-de-projetos-arquitetonicos-e-urbanisticos-parte-2-projeto-arquitetonico-432681) (snippet)
- Nome completo da Parte 2, segundo o título da página do banco de questões: "Elaboração e desenvolvimento de serviços técnicos especializados de projetos arquitetônicos e urbanísticos — Parte 2: Projeto arquitetônico". — [Gran Cursos](https://questoes.grancursosonline.com.br/questoes-de-concursos/arquitetura-nbr-16636-2-elaboracao-e-desenvolvimento-de-servicos-tecnicos-especializados-de-projetos-arquitetonicos-e-urbanisticos-parte-2-projeto-arquitetonico-432681)
- Blog do setor (Sienge) descreve a sequência estudo preliminar → anteprojeto → projeto legal (que chama de "projeto básico") → executivo. O projeto legal é a etapa que prepara os documentos de aprovação e verifica zoneamento e código de obras. **Atenção:** em obras públicas (Lei 14.133/2021), "projeto básico" é outra coisa, então equiparar projeto legal a projeto básico é impreciso. — [Sienge – Projeto executivo](https://sienge.com.br/blog/projeto-executivo-o-que-e-como-fazer/)
- A NBR 13532 ("Elaboração de projetos de edificações – Arquitetura") ainda tem categoria própria em bancos de questões. — [Gran Cursos – NBR 13532](https://questoes.grancursosonline.com.br/questoes-de-concursos/arquitetura-nbr-13532-elaboracao-de-projetos-de-edificacoes-arquitetura-429876)

### Inferences
- O BrasBim pode modelar a **etapa** como propriedade de projeto e de folha: LV, EP, AP, PL/licenciamento, PE, as built. Cada etapa teria um conjunto padrão de pranchas e um nível de informação esperado, o que permite checklists automáticos ("faltam cortes para EP").
- "Projeto legal" é o nome usado no mercado. "Projeto para licenciamentos" é o nome da norma. A UI deve mostrar os dois.

### Gaps
- Anos de publicação das Partes 1 e 2 da NBR 16636 e status formal da NBR 13532 (cancelada ou substituída?): sem confirmação pública nesta rodada.
- Siglas oficiais de cada etapa na 16636: não verificadas.

## 3. Peças exigidas pelas prefeituras para aprovação (projeto legal)

### Takeaway
Não existe padrão nacional. Cada município define peças, escalas, selo, quadro de áreas e **cores convencionais**, e as cores **chegam a se inverter entre cidades**: em Araras, vermelho é "a construir" e amarelo é "a demolir"; em Londrina, amarelo é construir e vermelho é demolir. São Paulo capital aprova um "projeto simplificado" (implantação, plantas sem compartimentação interna, corte esquemático, 1:100). O envio digital em PDF com certificado digital ICP-Brasil já é realidade em capitais como Curitiba.

### Cited Findings

**São Paulo (capital)**
- O COE (Lei 16.642/2017, arts. 16–17) exige "peças gráficas do projeto simplificado assinadas por profissional habilitado": implantação, planta de todos os pavimentos e corte esquemático. O detalhamento fica na Portaria SMUL 221/17 (Anexo, cap. 3, seção 3.A), e o Decreto 57.776/17, art. 17, remete à portaria. — [Prefeitura de SP – Peças gráficas de projeto (LOE 16.642/17)](https://prefeitura.sp.gov.br/web/licenciamento/w/servicos/264982)
- Nas plantas do projeto simplificado **não se mostram compartimentação interna nem aberturas**. Elas indicam áreas computáveis e não computáveis (PDE, LPUOS, COE), acessos de pedestres e veículos e a extensão do rebaixamento de guia. — [Prefeitura de SP](https://prefeitura.sp.gov.br/web/licenciamento/w/servicos/264982)
- O corte esquemático mostra todos os níveis (térreo, subsolos, ático), muros de divisa e suas alturas, o gabarito pela LPUOS, as cotas de nível e as alturas usadas nos cálculos de aeração e insolação. — [Prefeitura de SP](https://prefeitura.sp.gov.br/web/licenciamento/w/servicos/264982)
- Escala 1:100, folha de rosto no "padrão Prefeitura", texto legível. Há uma figura com critérios de cálculo de áreas, e os modelos são ilustrativos. — [Prefeitura de SP](https://prefeitura.sp.gov.br/web/licenciamento/w/servicos/264982)
- A SMUL é quem define por portaria os modelos de projeto simplificado, quadros e legendas. O decreto de 2013 (54.202, revogado) definia projeto simplificado como peças com dimensões externas, implantação, volumetria, movimento de terra e índices, sem detalhes internos. — [snippets de busca: Prefeitura SP / Legisweb Decreto 54.202](https://www.legisweb.com.br/legislacao/?id=257465)

**Curitiba (PR)**
- O licenciamento de alvará é eletrônico (portal e-Cidadão / Serviço Digital). **Todos os profissionais precisam de certificado digital A1 ou A3**, e os profissionais assinam termos com e-CPF. Pessoa jurídica proprietária assina com e-CNPJ, e pessoa física pode assinar à mão e digitalizar. — [Curitiba – Manual do Autor do Projeto, Aprovação de Projeto Simplificado, 2ª ed., set/2020 (PDF)](https://mid.curitiba.pr.gov.br/2020/00304554.pdf)
- As pranchas do projeto simplificado seguem os padrões da PMC, "em formato ABNT", em **arquivo .pdf de no máximo 3 MB**. O autor informa o tamanho da **última prancha** para que o sistema insira o carimbo de aprovação. As áreas declaradas no formulário servem para calcular as taxas. — [Curitiba – Manual do Autor (PDF)](https://mid.curitiba.pr.gov.br/2020/00304554.pdf)
- Só o autor do projeto pode cadastrar o pedido. O manual fixa o formato do registro profissional: CAU "A.001234-1", CREA "PR-0000012345/D", CFT "RNP…". Os documentos emitidos saem assinados digitalmente pela PMC, com chave de validação pública. — [Curitiba – Manual do Autor (PDF)](https://mid.curitiba.pr.gov.br/2020/00304554.pdf)
- Para protocolos após 05/08/2020 vale outro manual, o "Manual do Autor do Projeto – Aprovação Integrada – Lei 15.511/2019". — [Curitiba – Manual do Autor (PDF)](https://mid.curitiba.pr.gov.br/2020/00304554.pdf)

**Araras (SP), exemplo de cidade média com aprovação online (POP 001/21)**
- Conteúdo mínimo:
  - ART/RRT/TRT em todas as vias.
  - Plantas cotadas de cada pavimento em 1:50 ou 1:100.
  - Fachada(s) para a via pública em 1:50 ou 1:100.
  - Planta de situação em 1:50 a 1:500, com perfil do terreno tendo o meio-fio como referência de nível.
  - Cortes longitudinal e transversal em 1:50 ou 1:100.
  - Quadro de áreas por pavimento e edificação, com área livre, área permeável, taxa de ocupação (TO) e coeficiente de aproveitamento (CA).
  - [Araras – POP 001/21 Alvará de Construção (PDF)](https://araras.sp.gov.br/servicos_ao_cidadao/arquivos_urbanismo/aprovacao_online/PROCEDIMENTO_OPERACIONAL_PADRAO_-_ALVARA_DE_CONSTRUCAO.pdf)
- **Cores convencionais** em Araras: preto ou azul = conservar; **vermelho = construir**; **amarelo = demolir**; linhas vazias = paredes baixas e muros; **verde = áreas a transformar**. Se houver várias edificações, pode-se usar outras cores. — [Araras POP 001/21](https://araras.sp.gov.br/servicos_ao_cidadao/arquivos_urbanismo/aprovacao_online/PROCEDIMENTO_OPERACIONAL_PADRAO_-_ALVARA_DE_CONSTRUCAO.pdf)
- Todas as peças levam:
  - assinaturas do proprietário, do autor e do RT;
  - perímetro legal do lote;
  - perímetro da construção e projeções;
  - **legenda das áreas a construir, regularizar, demolir, existente e a transformar**;
  - legenda de usos mistos, varanda e garagem;
  - perímetro da área permeável e cobertura vegetal;
  - planta de cobertura;
  - cortes e elevações para análise de recuos e gabarito;
  - cotas de recuos;
  - quadro de áreas com índices;
  - detalhe do poço de infiltração;
  - detalhe de rotas acessíveis com níveis, inclinação de rampas e pisos táteis;
  - detalhe do passeio com rebaixamento de guia, piso tátil e abertura para árvore;
  - endereço da obra e pranchas numeradas.
  - [Araras POP 001/21](https://araras.sp.gov.br/servicos_ao_cidadao/arquivos_urbanismo/aprovacao_online/PROCEDIMENTO_OPERACIONAL_PADRAO_-_ALVARA_DE_CONSTRUCAO.pdf)
- A aprovação exige ainda **memorial descritivo** com dados da obra, fundação, estrutura, paredes, esquadrias, cobertura, impermeabilização, revestimentos, soleiras e peitoris, forro, pintura, pavimentação, louças e metais, instalações, mobiliário e limpeza. Também exige projeto aprovado no Corpo de Bombeiros quando a lei pedir e a nota de que a aprovação não reconhece a propriedade. — [Araras POP 001/21](https://araras.sp.gov.br/servicos_ao_cidadao/arquivos_urbanismo/aprovacao_online/PROCEDIMENTO_OPERACIONAL_PADRAO_-_ALVARA_DE_CONSTRUCAO.pdf)

**Jacareí (SP), exemplo de manual técnico detalhado**
- O selo segue um modelo fixo (Anexo XIV) com:
  - título: Projeto de Implantação, de Arquitetura ou Completo;
  - nº do processo substituído;
  - "assunto" em fórmulas padronizadas ("Projeto para construção/regularização/ampliação/adequação de…");
  - dados do requerente;
  - endereço com quadra, lote, loteamento e inscrição imobiliária;
  - zoneamento;
  - **planta de situação sem escala com lote, norte e pelo menos 3 logradouros**;
  - declaração de que a aprovação não reconhece posse ou propriedade;
  - assinaturas do requerente, do autor e do RT, com CAU/CREA, inscrição municipal, ART/RRT e contatos;
  - quadro de áreas.
  - [Jacareí – Anexo XII Manual Técnico](https://www.jacarei.sp.gov.br/wp-content/uploads/2018/11/12-Anexo-XII-Manual-Técnico.pdf)
- O quadro de áreas traz:
  - área do terreno (real e de escritura);
  - áreas construídas por pavimento e por uso ou tipo;
  - área total;
  - piscina indicada à parte, fora do total e dos índices;
  - CA, TO e taxa de permeabilidade.
  - [Jacareí](https://www.jacarei.sp.gov.br/wp-content/uploads/2018/11/12-Anexo-XII-Manual-Técnico.pdf)
- Projeto de Implantação em **1:200**:
  - contornos das projeções de cada pavimento no lote;
  - cotas de nível nos vértices do lote em relação ao ponto médio da guia (passeio mais baixo se houver mais de uma testada);
  - perímetro cotado conforme a matrícula, com medidas "R" (real) e "E" (escritura) quando divergirem;
  - passeios com nome do logradouro e cota;
  - rebaixamento de guia;
  - **perímetro da edificação com linha mais espessa que cotas e auxiliares**;
  - memória de cálculo de áreas;
  - área permeável cotada (piso drenante com % e laudo);
  - reservatório de retenção pluvial com cálculo;
  - fossa, filtro e sumidouro locados;
  - **hachuras e legendas para áreas existentes regulares (com nº de habite-se ou projeto aprovado), a construir, a regularizar, a adequar**;
  - vagas cotadas e numeradas;
  - cobertura com caimento e inclinação.
  - [Jacareí](https://www.jacarei.sp.gov.br/wp-content/uploads/2018/11/12-Anexo-XII-Manual-Técnico.pdf)
- Projeto de Arquitetura em **1:100**:
  - plantas de todos os pavimentos;
  - no mínimo 2 cortes (transversal e longitudinal);
  - no mínimo 1 fachada;
  - cobertura.
  - Nas plantas, no mínimo: dimensões internas, nome e área de cada ambiente, layout das áreas molhadas, dimensões das esquadrias (podem ir em quadro à parte), numeração dos degraus e sentido da escada, recuos, projeção dos pavimentos superiores, níveis, muros de divisa e linhas de corte.
  - [Jacareí](https://www.jacarei.sp.gov.br/wp-content/uploads/2018/11/12-Anexo-XII-Manual-Técnico.pdf)

**Outras cidades e variação das cores**
- Londrina-PR (Código de Obras, segundo snippet de busca): preto ou cor normal = manter; **amarelo = construir**; **vermelho = demolir**. É o oposto de Araras. — snippet de busca da consulta "cores convencionais amarelo demolir vermelho construir" (fonte primária não aberta; tratar como não verificado)
- Arroio do Sal-RS (questão de concurso, snippet): vermelho = demolir, azul = construir, amarelo = existente. — snippet de busca (não verificado)
- Barcelos (Portugal) usa vermelho = construir, amarelo = demolir, preto = manter, azul = legalizar. Serve só de contraste, pois não é Brasil. — [formularios.barcelos.pt (snippet)](https://formularios.barcelos.pt/)

**Quadro de áreas e incorporação**
- O quadro de áreas para incorporação segue a **ABNT NBR 12721:2006**, com oito quadros (I a VIII): áreas globais por pavimento, unidades, custo pelo CUB, identificação das unidades etc. Ele é pré-requisito do Registro de Incorporação. Tipos de área: privativa, privativa acessória, comum, útil, total, equivalente de custo. A área global precisa bater com o CA aprovado e com o alvará, senão pode travar o habite-se. — [Sienge – Quadro de áreas](https://sienge.com.br/blog/quadro-de-areas/)

### Inferences
- O BrasBim precisa de um sistema de **"status de intervenção"** por elemento (existente/manter, a construir, a demolir, a regularizar, a transformar/adequar) com **tabela de cores e hachuras configurável por município**, porque as cores se contradizem entre cidades. O IFC já tem um ponto de apoio: a propriedade `Status` dos Psets comuns (`Pset_WallCommon.Status` etc.), com valores NEW / EXISTING / DEMOLISH / TEMPORARY. Os valores brasileiros extras, como "a regularizar" e "a transformar", exigiriam um Pset próprio. Isso deve ser confirmado na documentação do IFC 4.3.
- Um **perfil municipal** (arquivo de configuração) pode guardar: escalas exigidas (1:100 arquitetura, 1:200 implantação), modelo de selo e campos, notas obrigatórias, cores, limite de tamanho de PDF (Curitiba: 3 MB), conteúdo do quadro de áreas (CA, TO, permeabilidade, piscina fora do total) e se a planta é simplificada, sem compartimentação (SP), ou completa (Jacareí).
- Cálculos que os incumbentes não fazem nativamente para o padrão brasileiro e que viram automações vencedoras:
  - quadro de áreas com CA, TO, taxa de permeabilidade, área computável e não computável;
  - memória de cálculo de áreas (Jacareí exige a combinação dos cálculos);
  - cotas R/E do lote;
  - níveis em relação à guia;
  - quadros da NBR 12721.
- O selo com mini planta de situação "sem escala" (lote, norte, 3 logradouros) é um elemento recorrente e pode ser gerado automaticamente a partir do terreno do modelo.

### Gaps
- Rio de Janeiro, Belo Horizonte, Porto Alegre, Brasília e Fortaleza: não consegui fontes desta vez (orçamento de busca esgotado). Falta confirmar para cada uma o sistema de licenciamento digital, as peças, as cores e os formatos.
- Aprova Digital (SP): o portal existe, mas as URLs que tentei deram 404. Não verifiquei formatos aceitos, PDF/A, DWG nem assinatura.
- Exigência de **PDF/A** e **DWG** em prefeituras: não encontrei fonte nesta rodada. Curitiba exige PDF ≤ 3 MB, sem menção a PDF/A no manual de 2020.
- Assinatura via gov.br (assinatura eletrônica avançada) como alternativa ao ICP-Brasil: não verificado.

## 4. Conteúdo do projeto executivo e do as-built

### Takeaway
As fontes públicas obtidas descrevem o executivo só de forma genérica: desenhos detalhados de todas as disciplinas, detalhes construtivos, especificações, memorial descritivo e quantitativos. Para quadro de esquadrias, paginação e tabelas de acabamento faltaram fontes primárias nesta rodada. O que há de concreto vem de exigências municipais: dimensões de esquadrias em quadro à parte (Jacareí) e memorial descritivo por item (Araras).

### Cited Findings
- Executivo: plantas e desenhos de arquitetura, estrutura, elétrica e hidrossanitário, com cotas, detalhes construtivos e especificação de materiais. Inclui memorial descritivo (materiais, técnicas, requisitos de desempenho), cronograma e quantitativo de materiais e equipamentos. — [Sienge – Projeto executivo](https://sienge.com.br/blog/projeto-executivo-o-que-e-como-fazer/)
- Já na aprovação, Jacareí aceita que as "dimensões de todas as esquadrias" venham "em quadro à parte", o que mostra o quadro de esquadrias como peça usual. — [Jacareí](https://www.jacarei.sp.gov.br/wp-content/uploads/2018/11/12-Anexo-XII-Manual-Técnico.pdf)
- O memorial descritivo exigido em Araras segue uma estrutura por sistemas construtivos (lista na seção 3), que serve de esqueleto para um modelo de memorial. — [Araras POP 001/21](https://araras.sp.gov.br/servicos_ao_cidadao/arquivos_urbanismo/aprovacao_online/PROCEDIMENTO_OPERACIONAL_PADRAO_-_ALVARA_DE_CONSTRUCAO.pdf)
- A NBR 16636-2 inclui a "documentação as built" como etapa própria. — [USP (snippet)](https://edisciplinas.usp.br/pluginfile.php/5809393/mod_resource/content/2/GEST%C3%83O%20PROCESSO%20PROJETO.pdf)

### Inferences
- Um **memorial descritivo gerado do modelo IFC** (materiais e tipos por sistema, na ordem fundação → estrutura → paredes → esquadrias → cobertura → … → limpeza) é uma automação com demanda clara: é exigido até na aprovação de cidades médias.
- O quadro de esquadrias (código, dimensões L × H, peitoril, tipo, material, quantidade) sai direto de IfcDoor/IfcWindow e seus tipos.

### Gaps
- Conteúdo típico de paginação de piso e revestimento, tabela de acabamentos por ambiente e escalas de detalhamento (1:20, 1:10, 1:5…) segundo fontes públicas brasileiras: sem fonte nesta rodada.
- Exigências formais de as-built (prefeitura no habite-se? incorporação?): sem fonte.

## 5. Como os brasileiros configuram Archicad, Revit e AutoCAD (templates, plugins, dores)

### Takeaway
As evidências públicas obtidas são fracas. O Archicad tem ajuda oficial em pt-BR e um mecanismo de "template online" que o parceiro local pode atualizar, mas não confirmei um template "BRA/ABNT" oficial. A OFCDesk é uma desenvolvedora brasileira de plugins Autodesk, com foco forte em hidrossanitário via fabricantes (TigreBIM, KronaBIM). Não encontrei fonte sobre MaxBIM nem sobre "ArqTools".

### Cited Findings
- Ajuda do Archicad em pt-BR (versões 22 a 29): o template é um arquivo .tpl somente leitura com preferências, elementos e configurações de ferramentas. Há um template padrão embutido na pasta "Originais". Desde o AC 28/29, algumas versões trazem um **template online (ícone de globo) que o parceiro Graphisoft local pode atualizar**. — [Graphisoft Help AC29 BRA – Arquivos Template](https://help.graphisoft.com/AC/29/BRA/_AC29_Help/020_Configuration/020_Configuration-28.htm)
- A Graphisoft tem histórico no Brasil: versão em português desde o Archicad 6.0 (1999), distribuição pela PINI anunciada em 2007 e abertura de subsidiária no Brasil. — [Graphisoft press release PINI](https://www.graphisoft.com/press-releases/pini-brazil); [Graphisoft press release Brazil subsidiary](https://graphisoft.com/press-releases/brazil) (via snippet)
- A OFCDesk se apresenta como desenvolvedora de software de modelagem desde 1994 e integradora/desenvolvedora certificada Autodesk APS. Diz ter desenvolvido centenas de plugins para AutoCAD, Revit e SketchUp, entre eles IDC (divisórias e painéis de parede), uma ferramenta de auditórios e os plugins gratuitos TigreBIM e KronaBIM (hidrossanitário). Segundo a própria empresa, o TigreBIM é usado em 70% dos projetos hidráulicos de pequeno porte no Brasil (dado autodeclarado). — [OFCDesk – arquitetura e design](https://ofcdesk.com/architecture-and-design); [OFCDesk – desenvolvimento de plugins](https://ofcdesk.com/architecture-and-design/development-of-plugins-and-extensions) (via snippet)
- O Sienge cita AutoCAD e Revit para extrair áreas e menciona um plugin Revit do Construmanager (Sienge) para controle de documentos. Dores listadas no quadro de áreas:
  - versões desatualizadas;
  - classificação errada de varandas e garagens;
  - descompasso com o projeto aprovado;
  - quadro não atualizado após mudanças;
  - várias versões circulando;
  - CUB desatualizado.
  - [Sienge – Quadro de áreas](https://sienge.com.br/blog/quadro-de-areas/)
- Um TCC do IFSC (snippet) menciona o plugin "BIM One" e o preenchimento automatizado de quadros de áreas. — [Repositório IFSC](https://repositorio.ifsc.edu.br/bitstreams/33c4fa27-9164-4514-852b-f1eafd785802/download)
- O que se oferece como "template ABNT" em sites de blocos (DesignsCAD) é conjunto de blocos de detalhamento para CAD, não template BIM. — [designscad.com tag template](https://designscad.com/downloads/tag/template)

### Inferences
- O mercado brasileiro depende de templates de terceiros e de plugins de fabricantes. As dores recorrentes (quadro de áreas inconsistente com o aprovado, várias versões) apontam para uma vantagem do BrasBim: **um único modelo IFC como fonte do quadro de áreas, do selo e das peças legais**, com recálculo automático e trilha de versões.
- Template online atualizável pelo parceiro (Archicad) é um modelo interessante: o BrasBim pode distribuir **perfis municipais versionados**, abertos e mantidos pela comunidade.

### Gaps
- MaxBIM, ArqTools/Arqsoft, templates Revit brasileiros (gratuitos ou pagos), conteúdo da "Biblioteca Brasil" do Archicad e a forma como os usuários fazem cores de reforma (Renovation filters no Archicad, Phases no Revit, layers no AutoCAD): **sem fontes nesta rodada**, porque o orçamento de busca acabou.
- Dores específicas com espessura de pena no plot (CTB/STB do AutoCAD, pen sets do Archicad) no contexto ABNT: sem fonte.
- Vídeos e fóruns brasileiros (YouTube, fóruns Graphisoft, Autodesk Community pt-BR): não pesquisados.

## 6. Acessibilidade (NBR 9050) e segurança contra incêndio (Corpo de Bombeiros) no projeto

### Takeaway
A acessibilidade já entra na aprovação municipal: Araras exige detalhe de rotas acessíveis (níveis, inclinação de rampas, piso tátil) e do passeio (rebaixamento de guia, piso tátil). O projeto de incêndio é um processo à parte no Corpo de Bombeiros, e a prefeitura pode exigir a aprovação dele, como Araras exige "Projeto Aprovado pelo Corpo de Bombeiros, nos casos previstos em lei", citando o Decreto estadual SP 56.819/2011.

### Cited Findings
- Araras exige nas peças o detalhe das áreas de circulação e rotas acessíveis com cotas de nível, inclinação de rampas e posição de pisos táteis, além do detalhe do passeio público com rebaixamento de guias, piso tátil e abertura para árvore. — [Araras POP 001/21](https://araras.sp.gov.br/servicos_ao_cidadao/arquivos_urbanismo/aprovacao_online/PROCEDIMENTO_OPERACIONAL_PADRAO_-_ALVARA_DE_CONSTRUCAO.pdf)
- Araras exige o projeto aprovado pelo Corpo de Bombeiros nos casos previstos em lei. A legislação citada é o Decreto estadual SP 56.819/2011 (Regulamento de Segurança contra Incêndio). — [Araras POP 001/21](https://araras.sp.gov.br/servicos_ao_cidadao/arquivos_urbanismo/aprovacao_online/PROCEDIMENTO_OPERACIONAL_PADRAO_-_ALVARA_DE_CONSTRUCAO.pdf)
- SP capital pede indicação de acessos de pedestres e veículos e do rebaixamento de guia nas plantas do projeto simplificado. — [Prefeitura de SP](https://prefeitura.sp.gov.br/web/licenciamento/w/servicos/264982)

### Inferences
- Um verificador NBR 9050 baseado no modelo (inclinação de rampas, larguras de passagem, giro de cadeira de rodas, piso tátil no passeio) e um gerador do "detalhe de passeio" atendem exigência explícita de prefeituras.
- Para incêndio, um conjunto de símbolos gráficos e uma camada de prancha "segurança contra incêndio" (extintores, saídas, iluminação de emergência, sinalização) seriam o mínimo. A simbologia oficial do CBPMESP fica numa Instrução Técnica própria e precisa ser verificada.

### Gaps
- Instruções Técnicas do CBPMESP (simbologia gráfica, apresentação de projeto, PTS/PT) e Normas Técnicas de outros estados (CBMMG, CBMERJ, CBMPR…): a tentativa de abrir o PDF da IT de símbolos do CBPMESP falhou por erro de certificado TLS. Sem fonte.
- Conteúdo gráfico específico da NBR 9050 (símbolos, áreas de manobra 1,20 × 1,50 m etc.) exigido em planta: não verificado em fonte pública nesta rodada.
- RRT: a página do CAU/BR confirma que o RRT vincula o profissional ao serviço e é emitido no SICCAU, que terá nova versão a partir de 2025. Não confirma regra de exibição do nº do RRT na prancha, mas Araras e Jacareí exigem o nº de ART/RRT no selo e em todas as vias. — [CAU/BR – RRT](https://caubr.gov.br/rrt/); [Araras](https://araras.sp.gov.br/servicos_ao_cidadao/arquivos_urbanismo/aprovacao_online/PROCEDIMENTO_OPERACIONAL_PADRAO_-_ALVARA_DE_CONSTRUCAO.pdf); [Jacareí](https://www.jacarei.sp.gov.br/wp-content/uploads/2018/11/12-Anexo-XII-Manual-Técnico.pdf)
