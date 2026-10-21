# Interoperabilidade openBIM entre Archicad, Revit, AutoCAD e outras ferramentas (2026)

> Pesquisa clean-room: só fontes públicas da web. Todas as fontes foram acessadas em **2026-10-21**.
> Os textos estão resumidos com palavras próprias. Ao lado de cada fato está o que foi tirado da fonte.
> **Limitação desta rodada:** o orçamento de buscas web da sessão acabou depois de cerca de 13 buscas.
> Várias páginas primárias responderam 403 ou 429: a lista de software certificado da buildingSMART, a página IDS da buildingSMART, o fórum da Graphisoft e o site do LibreDWG.
> Por isso há lacunas grandes, listadas em cada seção. Afirmações sem fonte foram para "Gaps".

## 1. Qualidade de export/import IFC no Archicad e no Revit (certificação, problemas, round-trip, "IFC como formato nativo")

### Takeaway
Archicad tem a certificação buildingSMART mais completa entre as ferramentas grandes de arquitetura: export IFC4 Reference View desde 2019 e import desde a versão 27, em 2023. O Revit tem certificação IFC4 de export (arquitetura e estrutura), mas não foi confirmada a de import. Os relatos de round-trip Revit↔Archicad mostram perdas recorrentes: elementos que somem, janelas, eixos de referência de paredes e lentidão do Revit ao abrir IFC. A raiz é que nenhum dos dois usa IFC como modelo interno. Nenhuma fonte encontrada confirma IFC 4.3 certificado em ferramenta comercial.

### Cited Findings
- **Archicad, export:** em junho de 2019 a buildingSMART concedeu à Graphisoft a certificação IFC4 Reference View 1.2 de export (Architectural Reference Exchange). Foi uma das primeiras certificações IFC4 RV — [Architosh](https://architosh.com/2019/06/aia-archicad-users-among-first-to-benefit-from-ifc4-reference-view-export-certification) (data e escopo da certificação); [buildingSMART, notícia de certificação IFC4](https://www.buildingsmart.org/?p=17501) (anúncio do marco da certificação IFC4).
- **Archicad, import:** o Archicad 27 recebeu no verão de 2023 a certificação IFC4 Architectural Reference Exchange de import, e manteve a de export de 2019 — [Graphisoft Help AC27, Novidades](https://help.graphisoft.com/AC/27/INT/_AC27_Help/005_NewFeatures/005_NewFeatures-17.htm) (versão e ano da certificação de import; informação do fornecedor). Há também um tópico de roadmap sobre certificação de import IFC4 no fórum da Graphisoft — [Graphisoft Community](https://community.graphisoft.com/t5/Product-Roadmap/IFC-4-Import-Certification/idi-p/632958) (só o título; a página não foi lida).
- **Revit:** a Autodesk anunciou em jan/2021 que o Revit obteve certificação IFC4 Reference Exchange para **export** de arquitetura e estrutura. Export MEP e import de arquitetura eram "esperados" para depois — [Autodesk AEC blog, 2021-01-07](https://www.autodesk.com/blogs/aec/2021/01/07/smarter-infrastructure-with-open-data-standards/) (escopo da certificação e pendências). Não confirmei se essas pendências foram concluídas.
- **BricsCAD:** recebeu em janeiro de 2025 a certificação IFC4 Architectural Reference Exchange de export. Também suporta import e export IFC4 RV — [Bricsys](https://www.bricsys.com/news/bricscad-is-officially-ifc4-certified) (data e escopo). Isso mostra que fornecedores menores e "DWG-like" usam a certificação como argumento de venda.
- **Fornax (Nova-Hub):** também anunciou certificação IFC4 — [Nova-Hub](https://www.nova-hub.com/novanews/fornax-achieves-ifc4-certification/) (só o anúncio, sem detalhes).
- **Programa de certificação:** a buildingSMART mantém um processo contínuo para verificar se aplicativos importam e exportam IFC com confiabilidade. Publica uma visão geral do software certificado com o status de import, export e "em desenvolvimento" — [buildingSMART, IFC Software Certification](https://info.buildingsmart.org/compliance/software-certification/ifc/) (existência e forma do programa).
- **IFC 4.3:** aprovado pela ISO em jan/2024 e publicado como **ISO 16739-1:2024** em abr/2024. A versão oficial mais recente é a 4.3.2.0, e o IFC está sendo refatorado para o IFC 5 — [buildingSMART, IFC](https://www.buildingsmart.org/standards/bsi-standards/industry-foundation-classes/); [buildingSMART, aprovação](https://www.buildingsmart.org/ifc-4-3-approved-as-a-final-standard/); [buildingSMART, publicação ISO](https://www.buildingsmart.org/?p=29521) (datas e número da norma).
- **Certificação IFC 4.3:** um artigo da Nordic BIM, sem data, diz que nenhum software estava certificado em IFC 4.3 e que a certificação começaria em breve — [Nordic BIM](https://www.nordicbim.com/knowledge/en/ifc-4.3) (situação da certificação). Pode estar desatualizado.
- **Revit e IFC 4.3:** uma tabela da Newforma (terceiro) indica que o add-in IFC do Revit 2025–2027 **não** suporta IFC 4.3 de forma recomendada. A variante "ADD2" aparece como suportada, mas talvez inconsistente. IFC 2x3 aparece como o schema mais recomendado para export. O Revit 2023–2025 permitiria export manual em IFC 4.3 — [Newforma Konekt Help](https://konekt.help.newforma.com/?p=463715) (status por versão; fonte secundária, não confirmada pela Autodesk).
- **Revit 2026, export:** usuários relatam falhas de export IFC depois de migrar do 2024 para o 2026. Uma das causas citadas é o conflito entre o exportador IFC embutido e o plugin IFC recomendado; desabilitar um add-in resolveu. Também foi relatada perda do export via rede — [Autodesk Forums, "REVIT 2026 Won't export to IFC?"](https://forums.autodesk.com/t5/revit-architecture-forum/revit-2026-won-t-export-to-ifc/td-p/13807489) (relatos anedóticos).
- **Archicad→Revit, elementos somem:** paredes e outros objetos somem ao importar no Revit, embora o mesmo IFC abra corretamente no Solibri. A perda acontece no lado do Revit — [Graphisoft Community, "IFC Translator to Revit lots of problems"](https://community.graphisoft.com/t5/Collaboration-with-other/IFC-Translator-to-Revit-lots-of-problems/m-p/216337) (relato de usuário; versão antiga).
- **Round-trip antigo (Archicad 12, via Solibri):** as janelas não sobreviveram. Paredes de perfil composto trocaram a linha de referência e ficaram fora do edifício — mesmo tópico [Graphisoft Community](https://community.graphisoft.com/t5/Collaboration-with-other/IFC-Translator-to-Revit-lots-of-problems/m-p/216335/highlight/true) (exemplo concreto de perda).
- **Causa estrutural, segundo um usuário do mesmo tópico:** a troca é bidirecional e o round-trip é ainda mais difícil, porque as lógicas internas diferem. O usuário descreve o Revit como "banco de dados procedural" e o Archicad como "relacional". Diz ainda que o Archicad importa IFC razoavelmente bem e que usuários de Revit costumam ter tempos muito longos para abrir IFCs complexos — [Graphisoft Community](https://community.graphisoft.com/t5/Collaboration-with-other/IFC-Translator-to-Revit-lots-of-problems/m-p/216334/highlight/true) (opinião).
- **Visão contrária:** um artigo da AUGI defende que o Revit exporta qualquer geometria para IFC sem perder geometria. É um texto opinativo pró-Revit e não trata de round-trip — [AUGI, "Myth Buster: Revit & IFC"](https://augi.com/articles/detail/myth-buster-revit-ifc) (contraponto).
- **Graphisoft e o fluxo Revit:** a Graphisoft publica um guia próprio, "IFC Model Exchange with Archicad for Revit 2026". Ele aponta para o repositório revit-ifc da Autodesk — [Graphisoft PDF](https://help.graphisoft.com/Revit/INT/IFC_Model_Exchange_with_Archicad_for_Revit_2026.pdf) (existência do guia; o conteúdo detalhado não foi lido). O fórum da Graphisoft também tem um tópico "Upcoming updates for IFC 4.3 support" — [Graphisoft Community](https://community.graphisoft.com/t5/Project-data-BIM/Upcoming-updates-for-IFC-4-3-support/m-p/683774) (só o título; retornou 403).
- **Mapeamento de Psets:** o Archicad usa um arquivo de configuração para Property Sets customizados no IFC. O tema aparece em tópico próprio — [Graphisoft Community, "IFC Custom Property Set Configuration File"](https://community.graphisoft.com/t5/Collaboration-with-other/IFC-Custom-Property-Set-Configuration-File/m-p/146586) (existência do mecanismo de mapeamento manual).

### Inferences
- A certificação buildingSMART cobre só a **Reference View**, que é geometria majoritariamente "congelada" (malhas e extrusões simples). Ela não garante round-trip editável. Para a BrasBim, a oportunidade está justamente no que as certificações não medem: IFC que o arquiteto continua editando (Design Transfer View e parametria preservada).
- O fato de Archicad e Revit usarem IFC só como formato de troca explica as perdas recorrentes (Psets mapeados à mão, eixos de parede e aberturas). Um app em que o IFC é o próprio modelo elimina a etapa de tradução na origem. As perdas continuam possíveis na importação feita pelo outro software.
- O IFC 4.3 ainda parece mal suportado pelos fornecedores comerciais de edificações: o Revit recomenda 2x3, e no Archicad o 4.3 aparece como "upcoming". Um app nativo em 4.3 precisa de um **export de compatibilidade IFC2x3/IFC4 RV**, ou não será lido pelos parceiros que usam Revit.

### Gaps
- Não foi possível ler a lista oficial de software certificado da buildingSMART (HTTP 403). Faltam o status atual do Revit (import IFC4, MEP), do Archicad 28/29 e de Tekla, Allplan e Vectorworks.
- Não há evidência primária sobre problemas específicos de **faceting** (curvas virando malha), escadas, curtain walls, espaços/zonas e georreferenciamento (IfcMapConversion) no Archicad e no Revit em 2026. As buscas acabaram antes de cobrir esses pontos. Não foi encontrado artigo acadêmico sobre o tema nesta rodada.
- O debate "IFC como formato nativo" não foi coberto por fontes além do OSArch (seção 5).

## 2. BCF, BCF API/cloud, IDS 1.0, bSDD, ISO 19650 e CDEs

### Takeaway
O BCF 3.0 existe e é suportado por CDEs como o Trimble Connect, que funciona como servidor BCF 2.1/3.0. A BCF API faz parte da família OpenCDE. O IDS 1.0 virou padrão final da buildingSMART em junho de 2024, com mais de uma dúzia de implementações já no lançamento. A lista de implementações é autodeclarada pelos fornecedores, e não há certificação.

### Cited Findings
- **BCF 3.0:** a buildingSMART publicou o BCF 3.0 — [buildingSMART, BCF 3.0](https://www.buildingsmart.org/bim-collaboration-format-bcf-3-0/) (existência da versão). O repositório BCF-API diz que o BCF 3.0 se baseia no 2.1 e que a BCF API pertence à família **OpenCDE API**, cuja base comum é a OpenCDE Foundation API — [BCF-API no GitHub (fork do repositório oficial)](https://github.com/ehtick/BCF-API) (arquitetura das APIs).
- **Trimble Connect:** a ajuda, modificada em 9/jul/2026, lista compatibilidade com BCF 2.1 e 3.0, BCF API e import/export de BCF-XML. O Trimble Connect atua como servidor BCF — [Trimble Connect Help, BCF Topics](https://help.trimble.com/doc/trimble-connect/trimble-connect/connect-for-browser/bcf-topics) (versões suportadas). O serviço de Topics é uma API REST com SDK .NET — [Trimble Developer](https://developer.trimble.com/docs/connect/topics) (forma da API). A documentação antiga descrevia a Topics API como compatível com BCF 2.1 — [docs.browser.connect.trimble.com](https://docs.browser.connect.trimble.com/bcf-topics/topics-api).
- **BIMcollab:** lançou uma BCF-API para conectar ferramentas BIM e planejava extensões além do padrão, como campos customizados e fluxos de aprovação — [BIMcollab](https://www.bimcollab.com/nl/?p=19731) (anúncio sem data; não menciona 3.0 nem OpenCDE).
- **IDS 1.0:** a buildingSMART anunciou o status de padrão final em 4/jun/2024. A página oficial cita 1/jun/2024, uma pequena discrepância. Já havia "mais de uma dúzia" de implementações estáveis — [buildingSMART, anúncio IDS 1.0](https://www.buildingsmart.org/?p=30065); [buildingSMART, página IDS](https://www.buildingsmart.org/standards/bsi-standards/information-delivery-specification-ids/) (datas e adoção inicial).
- **Lista de implementações IDS:** a lista no site técnico da buildingSMART classifica as entradas como "IDS 1.0 authoring" e "IDS 1.0 IFC check". Na consulta havia 58 entradas, por exemplo HiveDrive/SilentWave e The Hard Code. A buildingSMART diz que as entradas são mantidas pelos fornecedores e que **não** se trata de uma lista de ferramentas certificadas — [buildingSMART, IDS software implementations](https://technical.buildingsmart.org/ids-software-implementations/?pagenum=3) (contagem e ressalva).
- **CDE com IDS:** uma revista técnica alemã cita o Pave (PMG) como um dos primeiros CDEs a suportar IDS na prática — [ingenieur.de](https://www.ingenieur.de/fachmedien/bauingenieur/digitalisierung-bauingenieur/neuer-standard-ids-v1-0-von-buildingsmart/) (exemplo de adoção).
- **Biblioteca IDS em Rust:** existe a crate open source `openbim-ids` — [docs.rs](https://docs.rs/openbim-ids) (existência).
- **Explicação didática do IDS (ACCA):** — [BibLus ACCA](https://biblus.acca.it/ids-cose-e-a-cosa-serve/) (referência geral; não usada para fatos).

### Inferences
- A BrasBim pode diferenciar-se com **validação IDS embutida e em tempo real** enquanto o usuário modela, em vez de checar só no fim. O IfcOpenShell já tem um módulo IDS (ifctester), mas isso não foi verificado nesta rodada (ver Gaps). Também pode oferecer um **cliente BCF API 3.0** compatível com Trimble Connect e BIMcollab.
- Como a lista IDS não é certificada, a buildingSMART tem casos de teste públicos. Passar nesses testes e publicar o resultado seria um argumento de confiança barato de obter.

### Gaps
- bSDD: nenhuma fonte foi coletada sobre a integração do bSDD em Archicad e Revit nem sobre a API do bSDD (as buscas acabaram).
- ISO 19650 e CDEs no Brasil: sem fontes nesta rodada.
- Não confirmei se Revit e Archicad têm BCF nativo ou só via plugins (BIMcollab Zoom e conectores). Não confirmei o suporte do BIMcollab a BCF 3.0 e OpenCDE.
- A página IDS da buildingSMART retornou 403. Não foi possível listar facets nem o validador oficial (IDS Audit tool).

## 3. Ferramentas de coordenação/clash e exigências das licitações BIM brasileiras

### Takeaway
Há cadernos BIM estaduais e institucionais (SC 2018, Goiás 2024, UFF 2024, Prefeitura de SP, SENAC-SP) que servem de anexo de edital. O caderno de SC é referência para outros. O Decreto 11.888/2024 (Estratégia BIM BR) não cita IFC nos trechos recuperados. A exigência de IFC aparece nos cadernos e na adoção do IFC como norma ABNT em 2023. Não foram coletadas fontes sobre Navisworks, Solibri, Dalux etc. no Brasil.

### Cited Findings
- **Caderno de SC:** o "Caderno de Apresentação de Projetos em BIM" da Secretaria de Estado do Planejamento de SC padroniza os projetos BIM de edificações entregues ao Estado e serve de anexo de editais — [SES-SC, download do caderno](https://saude.sc.gov.br/index.php/pt/servicos/projetos-e-obras-orientacoes/cadernos/caderno-de-apresentacao-projetos-em-bim/download) (finalidade). Segundo um estudo apresentado no SIGraDi 2023, os cadernos catarinenses são de 2018 — [Blucher/SIGraDi 2023](https://pdf.blucher.com.br/designproceedings/sigradi2023/342.pdf) (data).
- **Caso prático em SC:** em uma licitação de projetos executivos em BIM do Instituto de Cardiologia de SC, o caderno foi anexado ao edital e definiu o formato das entregas, inclusive entregas eletrônicas quinzenais — [CBIC](https://cbic.org.br/instituto-de-cardiologia-de-santa-catarina-apresenta-caso-pratico-de-licitacao-em-bim-em-agenda-previa-do-90o-enic/) (uso em licitação).
- **Influência:** o anexo de diretrizes de projeto da SEINFRA-GO (Concorrência 02/2024) cita o caderno catarinense como referência — [Goiás SEINFRA](https://goias.gov.br/seinfra/wp-content/uploads/sites/6/2024/07/Anexo-1-Diretrizes-para-Elaboracao-de-Projetos-Concorrencia-02-2024.pdf). A UFF também o usa como base do seu "Caderno de Diretrizes de Modelagem BIM" (PE 90.057/24) — [UFF](https://www.uff.br/wp-content/uploads/2024/11/4.-Anexo-IV-PE-90.057.24-Caderno-de-Diret.-de-Mod.-BIM-2.pdf).
- **IFC como norma ABNT:** um documento da Prefeitura de São Paulo registra que o IFC virou norma ABNT em 2023 e é formato de entrega de modelos — [Participe+ Prefeitura SP](https://participemais.prefeitura.sp.gov.br/system/documents/attachments/000/004/156/original/6f4036de81ce4187bfa997464eac68f2b2e38a45.pdf) (afirmação sobre a ABNT; não confirmei o número da NBR).
- **SENAC-SP:** tem especificação técnica própria para contratação de projetos BIM (Anexo XIX) — [SENAC-SP](https://www1.sp.senac.br/hotsites/sites/licitacao/wp-content/uploads/2023/10/ANEXO-XIX-Esp.Tec_.Contratacao.Projetos.BIM_-1.pdf) (existência; conteúdo não lido).
- **Decreto 11.888, de 22/01/2024:** institui a Estratégia BIM BR e seu Comitê Gestor. O art. 2º prevê propor atos com parâmetros para compras e contratações públicas em BIM (inciso VI) e aperfeiçoar a Plataforma e a Biblioteca Nacional BIM (inciso VIII). Nos trechos recuperados não aparece exigência de IFC ou de formato aberto — [Planalto, Decreto 11.888](https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2024/decreto/d11888.htm); [Câmara, dados da norma](https://www2.camara.leg.br/legin/fed/decret/2024/decreto-11888-22-janeiro-2024-795274-norma-pe.html) (escopo; sem revogação expressa).

### Inferences
- O mercado público brasileiro tende a pedir IFC como entregável e a ter cadernos com regras de nomenclatura, Psets e níveis de desenvolvimento. Uma BrasBim que traga **templates prontos dos cadernos brasileiros**, como arquivos IDS para checar a conformidade com o caderno de SC, GO etc., atacaria uma dor concreta.

### Gaps
- Não li o conteúdo dos PDFs dos cadernos. Faltam os requisitos exatos de IFC: versão do schema, MVD, Psets obrigatórios, classificação.
- Os cadernos do Paraná, do DNIT e do Exército (OPUS) e os decretos estaduais não foram cobertos (busca esgotada).
- Navisworks, Solibri, BIMcollab, Dalux e Trimble Connect: sem dados de participação de mercado ou de uso no Brasil.
- Não confirmei o número da norma ABNT que adota o IFC (provavelmente NBR ISO 16739, não verificado).

## 4. Lock-in DWG/DXF/RVT/PLN: formatos abertos, exportador IFC open source do Revit, barreiras legais

### Takeaway
O exportador e importador IFC do Revit é **open source** (LGPLv2, Autodesk/revit-ifc no GitHub), mas depende do Revit e embute uma DLL proprietária. No DWG, o histórico Autodesk × ODA mostra barreiras de marca (TrustedDWG e a marca "DWG"), não de interoperabilidade em si: o acordo de 2010 preservou o direito da ODA de desenvolver software interoperável e de usar a extensão .dwg.

### Cited Findings
- **revit-ifc:** é o código .NET open source da Autodesk para IFC no Revit e Revit LT 2019+ (Link IFC, export e interface de export). A versão open source substitui o add-in que vem com o Revit. Recebe manutenção a versão anual corrente e as duas anteriores. A licença é **LGPLv2**, com ANTLR 4 (BSD). Inclui uma DLL proprietária (Autodesk.SteelConnections.ASIFC.DLL) sob os Termos de Uso da Autodesk. As branches seguem o padrão `Release_27.x.x`, para o Revit 2027 — [GitHub Autodesk/revit-ifc](https://github.com/Autodesk/revit-ifc) (licença, escopo, política de versões). O README não informa os schemas suportados.
- **Autodesk × ODA:** em nov/2006 a Autodesk processou a ODA por marca e concorrência desleal, alegando que as bibliotecas DWGdirect gravavam o código TrustedDWG nos arquivos. O processo foi retirado em abr/2007: a Autodesk suavizou o aviso no AutoCAD 2008 e a ODA removeu o TrustedDWG. Em 2010 houve acordo: a ODA cancelou suas marcas baseadas em "DWG" e deixou de usá-las no marketing. O acordo não impede a ODA de criar software interoperável nem de usar a extensão .dwg. Os termos são confidenciais. Em abr/2010 o DWGdirect passou a se chamar Teigha — [Wikipedia, Open Design Alliance](https://en.wikipedia.org/wiki/Open_Design_Alliance) (cronologia); [RTTNews](https://www.rttnews.com/1265276/autodesk-agrees-to-settle-dwg-trademark-disputes-with-open-design-alliance-update.aspx) (acordo); [stress-free.co.nz](https://stress-free.co.nz/node/355) (data do processo; as fontes divergem entre 13 e 22/nov/2006).

### Inferences
- Para a BrasBim, ler e gravar DWG/DXF via bibliotecas abertas é juridicamente viável quanto à marca, desde que não se use "DWG" como marca nem se imitem selos de autenticidade. A BrasBim já importa DXF/DWG como referência (commit 2f115ec).
- O RVT e o PLN continuam fechados. O caminho realista é o IFC (e o export IFC do Revit, que é open source, pode ser estudado como código público LGPL). Qualquer leitura direta de RVT/PLN viola a regra clean-room do projeto e está fora de escopo.

### Gaps
- LibreDWG: o site da GNU retornou 429. Faltam o status (alpha/beta), as versões de DWG suportadas e a licença (GPLv3, não confirmado nesta rodada).
- Import de RVT no Archicad (conector Graphisoft e BimRv da ODA): sem fonte (busca esgotada).
- Licenciamento ODA (membros pagos e restrições ao uso em open source): não coberto.

## 5. IfcOpenShell/Bonsai com IFC como formato nativo de autoria: desempenho, limites, o que funciona

### Takeaway
O Bonsai (antigo BlenderBIM) prova que é viável editar IFC nativamente, com acesso total a propriedades e relações. O gargalo é a escala: a documentação oficial alerta para arquivos acima de 750 MB, objetos acima de 100 mil polígonos e cenas com mais de 50 mil elementos. Usuários relatam que a autoria interativa fica inviável entre 30 mil e 80 mil objetos, por limitação do Blender. Para modelos grandes, a recomendação é **vincular** (link) em vez de abrir para edição.

### Cited Findings
- **Documentação oficial do Bonsai:** diz que o Bonsai lida com modelos grandes ou federados (muitos GB, centenas de milhares de objetos). Alerta para arquivos acima de ~750 MB (problemas de memória), mais de 100 mil polígonos por objeto e mais de 50 mil elementos carregados (lentidão, falhas de seleção, viewport travando). Por padrão o Bonsai abre o IFC para **autoria**, com edição completa. Para coordenação ou só geometria, recomenda **vincular**, o que é muito mais eficiente — [Bonsai docs, Dealing with large models](https://docs.bonsaibim.org/guides/viewing/dealing_with_large_models.html) (limites e recomendação; a URL agora redireciona para `/studio/guides/viewing/...`; o conteúdo veio do resumo da busca).
- **Relato no OSArch:** um IFC com 108.012 elementos não abriu e mostrou o aviso de modelo grande. Um usuário experiente respondeu que o Blender costuma sofrer acima de ~30 mil objetos e fica inutilizável perto de 60–80 mil. Concluiu que o Bonsai ainda não serve para autoria gráfica de modelos tão grandes: vincular funciona, e editar por script é mais adequado — [OSArch, "How to open large IFC files in Bonsai"](https://community.osarch.org/discussion/2821/how-to-open-large-ifc-files-in-bonsai) (números anedóticos).
- **Bonsai v0.8.1 (mar/2025):** o processamento de geometria ficou cerca de 2× mais rápido, com kernels híbridos CGAL/OpenCASCADE — [BlenderNation](https://www.blendernation.com/2025/03/13/bonsai-v0-8-1-released-with-more-bim-features/) (ganho declarado).

### Inferences
- O limite de ~30–80 mil objetos vem em boa parte do **Blender** (um objeto do Blender por elemento IFC), não necessariamente do IfcOpenShell. Uma aplicação própria em PySide6/OpenGL, como a BrasBim, pode evitar esse teto com instancing, batching por tipo ou material e carregamento sob demanda. Este ponto merece um benchmark próprio.
- O padrão "abrir para editar × vincular para coordenar" deve existir na BrasBim desde cedo: modelos federados de outras disciplinas entram como link somente leitura.

### Gaps
- Não foram coletados relatos sobre o tempo de gravação de IFC grande, a estabilidade de GUIDs entre salvamentos, diffs e controle de versão de IFC (ifcmerge, git), nem a interoperabilidade de IFCs gerados pelo Bonsai abertos no Revit e no Archicad.
- Não há benchmark publicado comparando IfcOpenShell com outros toolkits (por exemplo web-ifc e xBIM).
