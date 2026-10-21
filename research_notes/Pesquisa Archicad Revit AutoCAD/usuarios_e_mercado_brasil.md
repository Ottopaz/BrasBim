# Usuários e mercado: Archicad x Revit x AutoCAD, dores, desejos e contexto brasileiro (2026)

Notas de pesquisa clean-room. Só fontes públicas da web, todas acessadas em **2026-10-21**. Nada foi lido de `_restrito/` nem de `tools/`. Os textos são resumos com palavras próprias; as citações literais são curtas. Cada item traz entre colchetes o que foi tirado da fonte, para lançar no registro de fontes (`cleanroom/FONTES.md`).

Limitações gerais desta rodada: os fóruns da Autodesk e da Graphisoft (painéis "Top Voted" e "Most kudoed") e algumas páginas do gov.br devolveram 401/403 na leitura automática. O Reddit não apareceu nas buscas. Por isso a contagem de votos ao vivo e as citações diretas de usuários do Reddit ficaram como lacunas.

---

## 1. Comparações diretas entre Archicad, Revit e AutoCAD feitas por usuários

### Takeaway
O consenso (blogs, profissionais e o próprio relato de um escritório brasileiro) é este. O Revit vence em projetos grandes e multidisciplinares, na coordenação e no ecossistema. O Archicad vence na curva de aprendizado, na qualidade gráfica da documentação com pouca pós-produção, no macOS e no hardware modesto, e no preço por posto. O AutoCAD continua sendo a ferramenta de desenho 2D e o formato (DWG) que órgãos públicos e prefeituras usam e exigem.

### Cited Findings
- **Preços no Brasil, maio de 2026, plano anual por usuário, sem impostos:** Revit R$ 10.735/ano (R$ 895/mês; R$ 1.350/mês no plano mensal). AEC Collection R$ 13.125/ano. AutoCAD sozinho R$ 7.480/ano. Archicad Studio R$ 8.205/ano. Archicad Collaborate R$ 9.652/ano. O Archicad Studio sai cerca de 24% mais barato que o Revit. Já Archicad + AutoCAD (R$ 15.685) custa mais que a AEC Collection. — [CURA, "Archicad ou Revit? Um comparativo honesto e a nossa escolha #49"](https://cursocura.com.br/curadoria/archicad-ou-revit) [preços em BRL e a comparação]
- **Facilidade de uso no Capterra 2025, citada pelo CURA:** Archicad 4,2 e Revit 4,0. Quem vem do SketchUp ou do AutoCAD fica produtivo no Archicad "em poucas semanas", segundo o autor. O Revit tem o maior ecossistema de plugins, fóruns e tutoriais. — [CURA](https://cursocura.com.br/curadoria/archicad-ou-revit) [notas e argumento de aprendizado]
- **Documentação:** no Archicad dá para controlar a representação por escala, o que reduz a pós-produção. O risco é que ajustes gráficos manuais deixem de acompanhar o modelo. No Revit as plantas refletem sempre o 3D. — [CURA](https://cursocura.com.br/curadoria/archicad-ou-revit) [trade-off entre documentação e modelo]
- **Interoperabilidade:** o Revit trabalha todas as disciplinas num formato só, com rastreio de mudanças. O Archicad depende de IFC e de ferramentas externas de coordenação, o que o autor considera "funcional, mas menos automático". — [CURA](https://cursocura.com.br/curadoria/archicad-ou-revit) [coordenação]
- **Hardware e plataforma:** o escritório do autor roda projetos de 36 pavimentos e mais de 20.000 m² em Mac Mini M4 com 16 GB. A Autodesk recomenda 32 GB para o Revit (64 GB em projetos grandes). O Revit só roda no Windows. — [CURA](https://cursocura.com.br/curadoria/archicad-ou-revit) [requisitos e plataforma]
- **Fraquezas reconhecidas do Archicad:** fachadas incomuns, coberturas não ortogonais e guarda-corpos especiais pedem gambiarras (por exemplo, uma cobertura feita com a ferramenta de pele de vidro sobre uma malha). A coordenação com estrutura e instalações também é menos automática. — [CURA](https://cursocura.com.br/curadoria/archicad-ou-revit) [limitações]
- **Conclusão do autor:** Revit para escritórios grandes com produção multidisciplinar. Archicad para escritórios pequenos e médios de arquitetura autoral, em especial em Mac. — [CURA](https://cursocura.com.br/curadoria/archicad-ou-revit)
- **Comparativos genéricos:** Revit para projetos grandes e multidisciplinares, com mais força em worksharing e detecção de conflitos. Archicad mais fácil de aprender e mais adequado a escritórios menores. Os preços em dólar divergem entre as fontes (Archicad ~US$ 2.250–3.005/ano; Revit ~US$ 2.414–2.910/ano). — [SelectHub](https://www.selecthub.com/building-information-modeling-software/revit-vs-archicad/); [MyArchitectAI](https://www.myarchitectai.com/blog/revit-vs-archicad); [fórum SketchUp](https://forums.sketchup.com/t/archicad-vs-revit/63815) [consenso qualitativo; os preços em USD são conflitantes]
- **AutoCAD no setor público:** um estudo técnico do TRE-MG descreve o AutoCAD como a ferramenta usada nos projetos de arquitetura e engenharia do órgão. Licenças de AutoCAD LT e SketchUp são compradas por 1 ou 3 anos. — [TRE-MG, ETP pregão 49/2021](https://www.tre-mg.jus.br/transparencia-e-prestacao-de-contas/licitacoes/pagina-de-aquivos-2021/tre-mg-pregao-eletronico-49-2021-etp) [AutoCAD como padrão no setor público]
- **Prefeitura comprando Revit e SketchUp em 2026:** existe um ETP para isso (Campo Bom/RS). — [ETP Autodesk Revit SketchUp, Campo Bom](https://portallicitacoes.campobom.rs.gov.br/wp-content/uploads/2026/03/ETP-Autodesk-Revti-SketchUp.pdf) [só o título e a existência; o conteúdo não foi lido]

### Inferences
- Para o BrasBim, a cunha competitiva mais clara está no segmento do escritório pequeno e médio de arquitetura. O preço importa ali (R$ 8–13 mil/ano por posto é muito para um autônomo brasileiro), e também uma prancha bonita "de saída", rodar em hardware modesto e em vários sistemas operacionais.
- O ponto fraco que a IFC-nativo precisa resolver é a coordenação com estrutura e instalações, que é o argumento do Revit. Um BrasBim que abra e referencie IFC de outros projetistas com fidelidade, junto com BCF, ataca justamente essa vantagem.
- Representação por escala com garantia de vínculo ao modelo (sem "override" que fica desatualizado) é um diferencial possível contra os dois.

### Gaps
- Não encontrei threads do Reddit (r/Architects, r/Revit, r/ArchiCAD) nas buscas, então faltam citações diretas e contagens de upvotes.
- Não encontrei benchmark independente de velocidade de modelagem ou de estabilidade (travamentos) entre os três.

---

## 2. Desejos mais votados e reclamações recorrentes

### Takeaway
As queixas mais documentadas e quantificadas são contra a Autodesk e o Revit: custo de propriedade (alta de até 70%), modelos de licença instáveis, desenvolvimento estagnado e um núcleo que não aproveita multicore nem GPU. Elas foram formalizadas em cartas abertas de 2020 (Reino Unido, mais de 200 firmas) e 2022 (associações nórdicas que representam 14 mil arquitetos). Os pedidos de usuários nos fóruns de ideias concentram-se em documentação e anotação: tabelas, tipos de linha, posicionamento de vistas na prancha, verificação ortográfica. Os desejos do Archicad incluem tema escuro, controle de visibilidade e múltiplas fases de reforma.

### Cited Findings
- **Carta aberta do Reino Unido (julho de 2020):** 17 escritórios assinaram publicamente, entre eles Zaha Hadid Architects, Grimshaw e AHMM. Cerca de 25 participaram da elaboração. Pontos principais:
  - o custo de propriedade subiu até 70% até o fim de 2019;
  - pelo menos cinco modelos de licença entre 2015 e 2019;
  - US$ 22 milhões gastos em cinco anos pelos signatários;
  - o Revit é baseado em código de cerca de 20 anos, sem uso de multicore nem de GPU, com falta de escalabilidade e desempenho que força gambiarras;
  - pedem um roteiro transparente e preços estáveis.

  — [Dezeen, 28/07/2020](https://www.dezeen.com/2020/07/28/autodesk-revit-bim-software-criticism/); [The Architect's Newspaper](https://www.archpaper.com/2020/07/leading-architecture-firms-pen-open-letter-to-autodesk/); [GfxSpeak](https://gfxspeak.com/featured/architects-demand-autodesk/) [lista de queixas e números]
- **Carta das associações nórdicas (setembro de 2022):** associações da Dinamarca, Noruega, Finlândia e Islândia, que somam 14 mil arquitetos, com apoio do Architects Council of Europe (mais de 600 mil arquitetos). Afirmam que nada mudou desde 2020 e que o núcleo do Revit precisa ser refeito. Pedem previsibilidade de licenças e ferramentas de gestão de licenças. A carta de 2020 chegou a mais de 200 firmas, mais uma associação de construção que cobre o Brasil. — [AEC Magazine](https://www.aecmag.com/bim/nordic-architectural-associations-demand-better-value-from-autodesk) [números e demandas; a menção ao Brasil está no artigo, sem nome da entidade]
- **Top 10 do Revit Ideas em fevereiro de 2021 (categoria "Gathering Support"):** inclui verificação ortográfica automática, tipos de linha complexos, configuração de tabelas e mais controle do posicionamento de vistas nas pranchas. — [Autodesk AEC Blog, 23/02/2021 (snippet de busca; a página deu 403)](https://www.autodesk.com/blogs/aec/2021/02/23/gathering-support-top-10-revit-ideas/) [temas do top 10; as contagens de votos não foram obtidas]
- **Escala do painel Revit Ideas:** um retrato mostrou cerca de 11.006 ideias em "Gathering Support", 128 aceitas, 405 implementadas e 1.490 arquivadas. — [Autodesk Forums, Revit Ideas (snippet)](https://forums.autodesk.com/t5/revit-ideas/idb-p/302/status-key/5) [contagem por status; data do retrato incerta]
- **Wishlist da Graphisoft, página 2 de "most kudoed":** tema escuro (macOS e Windows), opções de plano de referência para coberturas, controle de visibilidade de elementos, planta de forro refletida, múltiplas fases de reforma, vista simbólica de paredes de perfil complexo. Outras páginas citam "Show on Stories" para todas as ferramentas, um comando de esticar, isolar objetos e conflitos de reserva no Teamwork. — [Graphisoft Community Wishlist (snippet)](https://community.graphisoft.com/t5/Wishlist/idb-p/wishlist/tab/most-kudoed/page/2) [temas; sem contagem de kudos]
- **Fidelidade IFC:** um revisor da OSArch apontou um IFC exportado pelo Revit como inválido (contexto de geometria de anotação errado), o que impede a ida e volta. O problema foi reportado no GitHub revit-ifc. — [OSArch Community thread 167](https://community-test.osarch.org/thread/167) [exemplo de IFC inválido]
- O importador IFC do Archicad rejeitou um IFC do Revit por não conformidade com o schema. Portas exportadas do Archicad com abertura 2D ficam invisíveis ou difíceis de selecionar no Revit. — [Graphisoft Community, "IFC inconsistency"](https://community.graphisoft.com/t5/Collaboration-with-other/IFC-inconsistency/td-p/127061); [Graphisoft Community, "Collaboration Revit Support"](https://community.graphisoft.com/t5/Collaboration-with-other/Collaboration-Revit-Support/td-p/580900) [problemas de interoperabilidade]
- Com o fluxo novo "Link IFC" do Revit, abrir um IFC de 30 pavimentos pode cair de "um dia" para "uma hora", segundo usuário do fórum Graphisoft. A base de conhecimento da Autodesk lista modelos deslocados após a exportação IFC e conexões que não exportam. — [Graphisoft Community](https://community.graphisoft.com/t5/Collaboration-with-other/Collaboration-Revit-Support/m-p/581028); [Autodesk Forums, KB 2022](https://forums.autodesk.com/t5/revit-architecture-forum/2022-new-knowledge-support-articles-revit/td-p/10938077) [desempenho e erros de IFC]

### Inferences
- Mensagens que o BrasBim pode sustentar com evidência: (a) sem assinatura e sem auditoria de licença; (b) núcleo moderno, com cuidado de desempenho (multithread na geometria); (c) IFC válido por construção, validado por teste a cada recurso, o que já é regra do projeto.
- As ideias mais votadas são sobre documentação, não sobre modelagem: tabelas configuráveis, tipos de linha, prancha, ortografia. Isso reforça a prioridade dos pacotes de desenho 2D, prancha e quadro.
- Tema escuro, isolar objetos e fases de reforma (existente, demolir, construir) são desejos baratos e de alto valor percebido. Fases de reforma são muito relevantes no Brasil, onde reforma é um mercado grande.

### Gaps
- Não consegui as contagens de votos atuais (páginas "Top Voted" com 403). Não há lista de 2025–2026.
- Não pesquisei a fundo o AutoCAD Ideas.
- Não achei pesquisa quantitativa recente sobre estabilidade ou falhas.

---

## 3. Pesquisas e dados de mercado (mundo, Brasil, América Latina)

### Takeaway
Não existe pesquisa pública recente e confiável com a participação de mercado de Revit, Archicad e AutoCAD entre arquitetos brasileiros. Os dados disponíveis mostram adoção ampla mas imatura do BIM: só cerca de 2,5% das empresas estão no nível máximo de integração e 59% estão nos níveis 0–1, e a falta de capacitação é a principal barreira (48%). A presença do Archicad entre escritórios autorais é maior do que se supõe. O Revit domina em projetos complementares e grandes escritórios. AutoCAD e SketchUp seguem onipresentes, inclusive em compras públicas.

### Cited Findings
- **Estudo Sienge/Grant Thornton (com apoio da ABDI):** 2,51% das organizações chegam ao nível mais alto de integração BIM e 59,42% estão nos níveis 0 e 1. A barreira principal é a falta de capacitação, citada por 48,1%. — [CBIC, "Sienge e Grant Thornton Brasil lideram estudo sobre BIM na construção" (2020)](https://cbic.org.br/inovacao/2020/07/01/sienge-e-grant-thornton-brasil-lideram-estudo-sobre-bim-na-construcao-2/); [IT Forum](https://itforum.com.br/?p=9538201) [percentuais; ano provável 2020]
- **Visão BIM 20/20 LATAM:** 79% das empresas (incorporadoras, construtoras, projetistas) já usavam BIM e 21% não. — [CBIC, "Pesquisa sobre BIM indica que 79% das empresas já utilizam a ferramenta"](https://cbic.org.br/pesquisa-sobre-bim-indica-que-79-das-empresas-ja-utilizam-a-ferramenta/) [percentual; dado de 2019–2020, amostra autosselecionada]
- **BIM Fórum Brasil, Pesquisa Nacional de Maturidade Digital (dezembro de 2025):** coleta em set–out/2025, 130 incorporadoras e construtoras, com apoio da CBIC. Os percentuais não estavam nos trechos acessíveis. — [CBIC](https://cbic.org.br/?p=105561) [existência e amostra]
- **AsBEA:** abriu em 2018 uma pesquisa nacional sobre BIM em escritórios de arquitetura. Não achei os resultados publicados. — [CAU/BR](https://caubr.gov.br/participe-pesquisa-nacional-verifica-uso-do-bim-em-escritorios-de-arquitetura/) [existência]
- **Amostra antiga (cerca de 2008, 13 escritórios RJ/SP/Curitiba):** 7 usavam Revit e 2 Archicad, e 69% tinham até 15 funcionários. — [Revista Gestão & Tecnologia de Projetos, USP](https://revistas.usp.br/gestaodeprojetos/en/article/download/50958/55043/63437) [dado histórico apenas]
- **Brasil, levantamento informal:** o Archicad é mais comum do que o discurso sugere entre escritórios autorais que adotaram BIM (exemplos: Bernardes, FGMF, Jacobsen). Exemplos de usuários de Revit: Arthur Casas, Triptyque, mf+. — [CURA](https://cursocura.com.br/curadoria/archicad-ou-revit) [qualitativo, não estatístico]
- **Blogs brasileiros:** dizem que o Revit é o software BIM mais usado no país, sobretudo em projetos complementares, mas sem números verificáveis. — [Inovacivil](https://inovacivil.com.br/os-principais-softwares-bim-e-suas-funcoes/); [A Arquiteta](https://www.aarquiteta.com.br/blog/programas-para-arquitetos-mais-exigidos/) [opinião]
- **NBS Digital Construction Report 2025 (novembro de 2025, mais de 550 respondentes, Reino Unido):** cobre IA, BIM, nuvem e sustentabilidade. A divisão por software não ficou acessível sem download. Um blog atribui ao relatório "7 em cada 10 usam BIM", sem confirmação na página da NBS. — [NBS](https://www.thenbs.com/knowledge/digital-construction-report-2025) [escopo]
- **Ensino:** a Resolução CNE/CES nº 1 (julho de 2025) exige domínio de ferramentas BIM nos cursos de Arquitetura sem nomear software. — [CURA](https://cursocura.com.br/curadoria/archicad-ou-revit) [conferir no texto oficial do MEC]

### Inferences
- A falta de capacitação (48%) é a barreira número 1, à frente do custo. Isso favorece um app em pt-BR com curva de aprendizado curta e vocabulário de obra brasileiro.
- A nova diretriz curricular (BIM obrigatório, software livre de escolha) abre uma porta para um BIM gratuito e open source em universidades, onde licenças educacionais podem ser instáveis.

### Gaps
- Não há participação de mercado por software no Brasil nem na América Latina vinda de fonte primária.
- Não achei pesquisa do CAU/BR sobre software usado (o Censo do CAU não apareceu).
- Não confirmei o ano exato do estudo Sienge/Grant Thornton.
- Os percentuais da NBS 2025 por software não foram obtidos.

---

## 4. Contexto brasileiro: legislação, normas, prefeituras, pirataria, bibliotecas, sistemas construtivos

### Takeaway
O BIM no setor público brasileiro tem base legal: Lei 14.133/2021, art. 19 §3º ("preferencialmente"), Decreto 10.306/2020 e Decreto 11.888/2024 (nova Estratégia BIM BR, com plano 2025–2027 e metas para 2026). As exigências práticas do dia a dia, porém, ainda são municipais e em 2D: pranchas padronizadas com carimbo, quadro de áreas, DWG mais PDF, PDF com limite de tamanho e carimbo digital aplicado pelo sistema. As normas-chave são NBR 6492:2021, NBR 15965 e a série NBR 16636. A biblioteca nacional (BNBIM) existe com regulamento, mas os fabricantes nacionais ainda estão no começo.

### Cited Findings
- **Decreto 11.888, de 22/01/2024:** institui a nova Estratégia BIM BR e o Comitê Gestor, e substitui o Decreto 9.983/2019. Entre os objetivos está propor atos normativos para compras públicas com BIM (art. 2º, VI). — [Planalto, D11888](https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2024/decreto/D11888.htm); [Lex](https://www.lex.com.br/decreto-no-11-888-de-22-de-janeiro-de-2024); [Caderno BIM GovRS](https://planejamento.rs.gov.br/upload/arquivos/202607/28105928-rs-01-bimgovrs-caderno-bim-r06.pdf) [vigência e objetivos]
- **Metas da nova estratégia (apresentação do MDIC):** 49 órgãos federais com BIM implantado ou contratações em BIM em 2026, e 30% dos contratos de análise e monitoramento de obras com projetos em BIM em 2026. — [gov.br, apresentação "Nova Estratégia BIM BR" (snippet; o PDF deu 401)](https://www.gov.br/transferegov/pt-br/noticias/eventos/fntu/x-fntu/apresentacoes/evento-171-nova-estrategia-bim-br-transformacao-digital-para-a-construcao.pdf) [metas]
- **Plano de Trabalho da Estratégia BIM BR 2025–2027:** existe e usa o art. 19 da Lei 14.133 como premissa. A Lei 14.133 é a única norma de licitações desde 30/12/2023. — [gov.br/obrasgov (snippet)](https://www.gov.br/obrasgov/pt-br/estrategia-bim-br/plano-de-trabalho-da-estrategia-bim-br-2025-2027) [premissas]
- **Lei 14.133/2021, art. 19 §3º:** em obras e serviços de engenharia e arquitetura, adota-se "preferencialmente" o BIM, ou tecnologia similar ou mais avançada, sempre que adequado ao objeto. — [LegJur](https://www.legjur.com/legislacao/art/lei_00141332021-19); [Zênite](https://zenite.blog.br/?p=20020) [texto do dispositivo]
- **Decreto 10.306/2020:** define BIM (art. 3º, II) e previa BIM em projetos de arquitetura e engenharia de obras federais a partir de 01/01/2021. — [CONARA/Unifesspa](https://conara.unifesspa.edu.br/images/II_CONARA_2020/ARTIGOSARQ/BIM_no_ensino_de_Arquitetura_e_Urbanismo_em_instituies_pblicas_brasileiras_1.pdf); [Zênite](https://zenite.blog.br/obras-e-servicos-de-engenharia-o-que-e-building-information-modelling-bim-e-quais-os-seus-beneficios/) [1ª fase]
- **Cartilha do BIM Fórum Brasil (junho de 2026):** orientação para implantar BIM na administração pública. — [BIM Fórum Brasil](https://bimforum.org.br/wp-content/uploads/2026/06/Cartilha-Orientacao-para-implementacao-BIM-na-administracao-publica.pdf) [existência; conteúdo não lido]
- **NBR 6492:2021, 2ª edição (16/06/2021):** título "Documentação técnica para projetos arquitetônicos e urbanísticos — Requisitos". Trata das etapas (Estudo Preliminar, Anteprojeto, Projeto para Licenciamento, Projeto Executivo). Segundo material de concurso, o projeto executivo não substitui automaticamente o projeto para licenciamento. É citada junto com a NBR 16636-1/-2. — UFRRJ (só título e edição) (endereço de cópia não autorizada omitido; NÃO USAR); [Gran Cursos](https://questoes.grancursosonline.com.br/questoes-de-concursos/arquitetura-nbr-6492-representacao-de-projetos-de-arquitetura-429878); [LabBIM FAU-USP](https://labbim.fau.usp.br/) [título, edição, etapas]. Observação clean-room: não ler nem copiar o texto integral da norma, que tem direitos da ABNT. Usar só títulos e resumos.
- **NBR 15965 e o comitê ABNT/CEE-134:** a NBR 15965 é o sistema de classificação da informação da construção. O CEE-134 tinha 14 NBRs e 1 PR em vigor e 3 NBRs em revisão (agosto de 2024). Está em desenvolvimento um sistema de gestão de termos para a 15965. — [CBIC, apresentação do sistema 15965 (agosto de 2024)](https://cbic.org.br/wp-content/uploads/2024/08/240826-cbic-apresentacao-do-sistema-15965-joao-gaspar-1.pdf); [OrçaFascio](https://orcafascio.com/papodeengenheiro/nbr-15965/) [status do comitê]
- **Biblioteca Nacional BIM (BNBIM):** tem regulamento técnico com requisitos obrigatórios e recomendados para aceitar objetos na Plataforma BIM BR (ABDI). — [Regulamento Técnico BNBIM](https://plataformabimbr.abdi.com.br/docs/Regulamento_Tecnico_Biblioteca_Nacional_BIM.pdf) [existência e escopo]
- **Fabricantes:** estudo de 2025 com 238 fabricantes brasileiros de materiais. Só 36 têm biblioteca própria, 3 oferecem plugin e 22 usam o BIMobject. Conclusão: adoção ainda inicial. — [Gestão & Tecnologia de Projetos, USP, artigo 232179](https://revistas.usp.br/gestaodeprojetos/article/view/232179) [números]
- **Prefeituras:**
  - Belo Horizonte publica um modelo de carimbo em DWG, com área reservada à prefeitura e um quadro de dados do projeto (áreas, vagas, unidades) que precisa bater com o portal. — [PBH, Cartilha de Representação (2025)](https://prefeitura.pbh.gov.br/sites/default/files/estrutura-de-governo/politica-urbana/2025/cartilharepresentacaopbh_smpu_r5.pdf)
  - Curitiba exige pranchas padronizadas porque o sistema aplica o carimbo de aprovação com certificação digital na última prancha. — [Curitiba](https://mid.curitiba.pr.gov.br/2021/00311966.pdf)
  - São Paulo também aplica o selo eletrônico pelo sistema, no canto inferior direito, e já usou DWF por ser formato não editável. — [Prefeitura de SP](https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/subprefeituras/sp_mais_facil/arquivos/publicacao-2013-05-28.pdf)
  - São Gonçalo do Amarante/RN exige DWG além do PDF, com PDF de no máximo 5 MB. — [Portaria SEMURB 01/2018](https://saogoncalo.rn.gov.br/wp-content/uploads/2018/03/Portaria-SEMURB-SGA-n.º-01-2018.pdf)
  - Francisco Beltrão/PR exige folha de rosto com campos padrão inalterados. — [Francisco Beltrão](https://franciscobeltrao.pr.gov.br/wp-content/uploads/2020/08/TEXTO-EXPLICATIVO-NOVOS-MODELOS-DE-APROVA%C3%87%C3%83O-DE-PROJETO-2020-2.pdf)

  [requisitos de prancha, carimbo, quadro e formatos]
- **Pirataria:** dados da BSA citados pela ABES apontam um índice brasileiro em torno de 50%, o menor da América Latina (dado antigo, sem ano confirmado). A Autodesk notifica empresas suspeitas e oferece parcelamento para regularizar. A BSA, da qual a Autodesk é membro, contatou 722 empresas no Brasil num trimestre (sem data). — [ABES](https://abes.org.br/?p=1219); [Baguete](https://www.baguete.com.br/noticias/autodesk-vendera-pela-internet); [Baguete, BSA 722 empresas](https://www.baguete.com.br/public/noticias/bsa-contatou-722-empresas) [números antigos; usar com ressalva]

### Inferences
- **Prioridade alta:** um gerador de pranchas para aprovação municipal. Isso inclui carimbo configurável por prefeitura (modelos), quadro de áreas automático a partir de `IfcSpace`/`IfcZone`, exportação DWG e PDF com controle de tamanho e espaço reservado para o selo digital. É o que todo escritório pequeno precisa entregar, e nenhum dos três resolve "de fábrica" para cada prefeitura.
- **Classificação NBR 15965** como propriedade e classificação IFC (`IfcClassificationReference`) nativa, para atender contratações públicas e a BNBIM.
- **Etapas da NBR 6492** (EP, AP, PL, PE) como estado do projeto ou conjunto de pranchas.
- **Biblioteca:** o vazio dos fabricantes (só 36 de 238 têm objetos) é uma oportunidade para objetos IFC genéricos brasileiros (bloco cerâmico, bloco de concreto, drywall, steel frame, esquadrias padrão de mercado) e para aceitar o formato da BNBIM.
- **Pirataria:** um app gratuito elimina o risco jurídico de notificação para pequenos escritórios. É um argumento de adoção forte, mas os números de pirataria encontrados são antigos.

### Gaps
- Não confirmei por fonte primária as fases 2 e 3 do Decreto 10.306 (execução de obra e ciclo de vida). Lembro de 2024 e 2028, mas é preciso conferir no Planalto. Também não confirmei se o Decreto 11.888 revogou ou alterou essas fases.
- O resumo oficial das mudanças da NBR 6492:2021 em relação a 1994 não foi obtido. NBR 13531/13532 não foram pesquisadas (provavelmente substituídas pela série 16636, ainda por confirmar).
- Não encontrei estudo público sobre a qualidade da tradução pt-BR do Revit, Archicad ou AutoCAD.
- Os sistemas construtivos brasileiros (alvenaria, concreto armado, steel frame, drywall) e suas necessidades de modelagem não foram pesquisados nesta rodada.
- Não achei índice de pirataria recente (2024–2026) específico para software CAD/BIM.

---

## 5. Ferramentas alternativas e open source: recepção e lições

### Takeaway
O Bonsai (antigo BlenderBIM) é bem recebido por entusiastas: avaliações positivas, comunidade acolhedora e IFC nativo. As críticas históricas são a geração de documentação (pranchas e desenhos), que só recentemente amadureceu, e a curva de aprendizado. O SketchUp é popular no Brasil, mas não é BIM e tem pouca parametrização. Não achei avaliações recentes e confiáveis do FreeCAD BIM.

### Cited Findings
- **Crítica de 2022 ao Bonsai:** a maior queixa dos arquitetos era a falta de geração de documentação, e o suporte a desenhos ainda era "não perfeito". — [Blender 3D Architect](https://www.blender3darchitect.com/?p=66364) [crítica]
- **Bonsai em 2026:** um workshop ensina plantas, cortes, fachadas, tabelas e pranchas (18 aulas, mais de 20 h), voltado a quem quer evitar licença de Revit/Archicad. Um curso de 2026 reconhece que "o problema sempre foi a curva de aprendizado". — [BlenderNation, set/2026](https://www.blendernation.com/2026/09/03/blender-for-architecture-with-bonsaibim-workshop/); [BlenderNation, abr/2026](https://www.blendernation.com/2026/04/03/learn-bonsaibim-with-a-full-project-a-course-by-architect-ryan-schultz/) [capacidades e curva; é material de curso]
- **Avaliações no site de extensões do Blender:** positivas ("game-changer"), elogiando a comunidade que ajuda iniciantes. — [Blender Extensions, Bonsai reviews](https://extensions.blender.org/add-ons/bonsai/reviews/?page=3) [percepção autosselecionada]
- **Bonsai v0.8.1 (março de 2025):** melhorias de modelagem, geometria mais rápida e orçamento. — [BlenderNation](https://www.blendernation.com/2025/03/13/bonsai-v0-8-1-released-with-more-bim-features/) [evolução]
- **SketchUp:** sem render integrado e com parametrização limitada. Preço anual de US$ 119 (Go), US$ 349 (Pro) e US$ 749 (Studio). Órgãos públicos brasileiros o compram por ser amplamente usado e importar DWG. — [ClickUp](https://clickup.com/pt-BR/blog/133833); [TJAC, ETP PE 117/2022](https://www.tjac.jus.br/wp-content/uploads/2023/01/0007295-21.2022-Estudo-tecnico-preliminar-PE-117-2022-TJAC.pdf) [limitações e uso]

### Inferences
- **Lição 1:** ser IFC-nativo não basta. Sem desenho 2D e prancha de qualidade, arquitetos não adotam (essa foi a crítica número 1 ao Bonsai). O BrasBim deve tratar documentação como recurso de primeira classe desde cedo.
- **Lição 2:** a curva de aprendizado de ferramentas montadas sobre outro programa (o Blender) é uma barreira. Um app próprio, focado em arquitetura e com UI em pt-BR, é um diferencial direto.
- **Lição 3:** o SketchUp mostra que simplicidade e velocidade de modelagem conquistam o mercado brasileiro. Um BrasBim com modelagem rápida estilo "empurrar e puxar" sobre objetos BIM pode atrair a base de usuários do SketchUp.

### Gaps
- FreeCAD BIM, BricsCAD BIM, Vectorworks, Allplan e Chief Architect não tiveram recepção pesquisada nesta rodada (as buscas não trouxeram resultados úteis).
- Não achei dados de uso de SketchUp ou de plugins BIM para SketchUp no Brasil.
