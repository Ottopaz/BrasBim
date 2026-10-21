# Revit (2025/2026/2027): documentação, gestão de projeto, colaboração, interoperabilidade, automação e UX

> Pesquisa clean-room: só fontes públicas da web, acessadas em **2026-10-21**. Nenhum binário inspecionado, nada de `_restrito/` ou `tools/`. Texto escrito com palavras próprias; nomes de comandos aparecem só para identificar a função descrita e **não devem ser copiados** para a UI do BrasBim.
> Cada item traz a URL e o que foi tirado dela, para registro em `cleanroom/FONTES.md`.
> Limite: cerca de 20 buscas/leituras. Vários tópicos clássicos (tipos de vista, filtros de V/G, fases, opções de projeto, cotas EQ) não tiveram página da ajuda oficial lida nesta rodada. Estão marcados como **lacuna**, e não foram preenchidos com memória.

## 1. Vistas e documentação

### Takeaway
O Revit gera a documentação a partir de um modelo único. Plantas, cortes, quantitativos e folhas se atualizam juntos, e isso é o ponto mais elogiado. O controle gráfico depende de camadas de configuração: faixa de vista, modelos de vista, fases e opções. É poderoso, mas difícil de aprender. As versões 2026 e 2027 trouxeram sobretudo ganhos pequenos de produtividade (etiquetas, folhas, numeração por regra) e não mudaram o modelo de documentação.

### Cited Findings
**Faixa de vista (view range) e profundidade**
- Uma planta é definida por planos horizontais: superior, de corte e inferior, mais a "profundidade de vista" abaixo do plano inferior. O que o plano de corte intercepta usa espessura de linha de corte. O que fica abaixo dele usa espessura de projeção. O que está na zona de profundidade aparece com estilo de linha "além". O que fica fora da faixa não aparece. A altura de corte usual é cerca de 1200 mm, com exceções para marcenaria e muretas. A recomendação é usar "regiões de planta" para exceções locais, como escadas e meios-níveis. Fontes: [ATG USA – View Range Explained](https://atgusa.com/revit-view-range-explained/) (conceitos dos planos e estilos) e [Novedge – View Depth/Far Clipping](https://novedge.com/blogs/design-news/revit-tip-mastering-view-depth-and-far-clipping-in-revit) (profundidade e regiões de planta).

**Modelos de vista (view templates)**
- Um modelo de vista guarda propriedades aplicáveis em lote, entre elas faixa de vista, filtro de fase e recorte de profundidade, além das sobreposições gráficas. Isso padroniza muitas vistas de uma vez. Fontes: [Autodesk Help 2024 – View Template Properties](https://help.autodesk.com/cloudhelp/2024/ENU/Revit-Customize/files/GUID-66D789A8-AB92-4AF0-B884-DF3A3302E117.htm) (lista de propriedades controladas, incluindo filtro de fase) e [Novedge](https://novedge.com/blogs/design-news/revit-tip-mastering-revit-view-range-for-clearer-plan-documentation) (recomendação de guardar faixa de vista em modelos).

**Opções de projeto (design options), no Revit 2027**
- Uma vista atribuída a uma opção de projeto só pode ser selecionada com a opção ativa ou com a exclusão de opções. Os estados "só ativa" e "excluir opções" passaram a valer pela sessão inteira. O novo projeto de exemplo residencial traz várias opções. Fonte: [BIM Pure – Revit 2027](https://www.bimpure.com/blog/revit-2027) (seções Design Options e Sample projects).

**Folhas, carimbos e posicionamento**
- 2026: há um parâmetro de sobrescrita do texto de escala no carimbo, útil para folhas com várias escalas. Também há um comando que salva a posição de uma vista e a repete em outras folhas. Fonte: [BIMsmith – Revit 2026](https://blog.bimsmith.com/Revit-2026-Heres-What-You-Need-to-Know-about-the-Latest-Release-of-Autodesk-Revit) (itens 6 e 9).
- 2027: ao soltar uma vista numa folha, o navegador expande a folha e mostra as vistas colocadas. Fonte: [BIM Pure – Revit 2027](https://www.bimpure.com/blog/revit-2027).
- 2027.2: o título da vista e o prolongamento da linha do título encaixam na grade-guia da folha. Fonte: [BIM Pure – 2027.1/2027.2](https://www.bimpure.com/blog/top-5-new-features-in-revit-2027-1-and-revit-2027-2).
- Pedido antigo e muito votado na Revit Ideas: mais controle sobre o posicionamento de vistas nas folhas (838 votos em fev/2021, segundo o resumo da busca). A página da Autodesk que traz esse número devolveu HTTP 403, então a leitura direta não foi possível. Fonte: [Autodesk AEC Blog – Top 10 Revit Ideas (2021)](https://www.autodesk.com/blogs/aec/2021/02/23/gathering-support-top-10-revit-ideas/).

**Anotação: etiquetas, texto, numeração**
- 2027: todas as etiquetas ganharam pontos de controle no início e no fim da linha de chamada, encaixe da ponta em arestas de elementos e alinhamento dos cotovelos entre etiquetas. Anotações genéricas ainda não ajustam o ponto inicial. Também é possível definir uma etiqueta multicategoria como padrão (paredes, pisos, forros, coberturas), e o comando de etiquetar tudo aceita essas etiquetas. Fonte: [BIM Pure – Revit 2027](https://www.bimpure.com/blog/revit-2027).
- 2027: a numeração de escadas passou a usar parâmetros de tipo (fonte, estilo). O texto acima e abaixo da marca de corte pode ser formatado e exibido separadamente. Fonte: o mesmo artigo.
- 2027: numeração por regra (aba Gerenciar). O usuário cria um modelo com filtro de vista, parâmetro-alvo (por exemplo, Marca), particionamento (por exemplo, número do ambiente) e formato. A regra se aplica sozinha a elementos novos. O autor dá nota "A+". Antes isso exigia digitação manual ou add-ins. Fontes: [BIM Pure – Revit 2027](https://www.bimpure.com/blog/revit-2027) e [Symetri – What's New in Revit 2027](https://www.symetri.co.uk/insights/blog/what-s-new-in-revit-2027-a-guide-to-the-latest-features/) (pelo resumo da busca).
- 2027.2: "etiquetar por exemplo". O usuário escolhe uma etiqueta-modelo e depois os elementos-alvo. A orientação, a relação com o hospedeiro, o espelhamento e a inversão são reproduzidos, e há a opção de apagar as etiquetas existentes. Fonte: [BIM Pure – 2027.1/2027.2](https://www.bimpure.com/blog/top-5-new-features-in-revit-2027-1-and-revit-2027-2).
- 2026: verificação ortográfica no próprio desenho, com sublinhado ao digitar, sugestões no menu de contexto e dicionário personalizado. Era um dos pedidos mais votados da Revit Ideas (797 votos em 2021). Fontes: [BIMsmith – Revit 2026](https://blog.bimsmith.com/Revit-2026-Heres-What-You-Need-to-Know-about-the-Latest-Release-of-Autodesk-Revit) (item 7) e [Autodesk AEC Blog 2021](https://www.autodesk.com/blogs/aec/2021/02/23/gathering-support-top-10-revit-ideas/) (pelo resumo da busca).
- 2026: etiquetas de ambiente alinham sozinhas ao ponto de referência central do ambiente. Fonte: [BIMsmith](https://blog.bimsmith.com/Revit-2026-Heres-What-You-Need-to-Know-about-the-Latest-Release-of-Autodesk-Revit) (item 10).
- 2027.1: rotação de padrões de hachura personalizados. Fonte: [BIM Pure – 2027.1/2027.2](https://www.bimpure.com/blog/top-5-new-features-in-revit-2027-1-and-revit-2027-2).

**Quantitativos, levantamento de materiais, legendas de notas-chave, revisões**
- No levantamento de materiais, cada linha é um par elemento-material. Volumes de camadas de parede podem divergir um pouco do modelo, sobretudo com perfis, frisos e certas junções. Fonte: [Autodesk Help 2018 – Material Takeoff Schedules](https://help.autodesk.com/cloudhelp/2018/ENU/Revit-DocumentPresent/files/GUID-F8270A42-CA71-46C7-B145-85EC2CB8E4A1.htm).
- Materiais aplicados com a ferramenta de pintura de face ficam fora do levantamento de materiais, segundo um blog. Fonte: [draftsperson.net](https://blog.draftsperson.net/?p=2050) (pelo resumo da busca).
- A legenda de notas-chave é uma tabela das etiquetas de nota-chave, com campos fixos de valor e texto, e pode ir para várias folhas. Fonte: [Autodesk Help 2023 – About Keynote Legends](https://help.autodesk.com/cloudhelp/2023/ENU/Revit-DocumentPresent/files/GUID-4ED30197-CE07-477A-A093-6C397DE446CC.htm).
- A tabela de revisões fica dentro da família do carimbo e aparece nas folhas através dele. Listas de folhas e de vistas são tabelas das categorias Folhas e Vistas. Fonte: a mesma busca, apontando a ajuda da Autodesk (página [Creating a Schedule](https://help.autodesk.com/cloudhelp/2014/ENU/Revit/files/GUID-7DB8EEA6-2C4A-4BC3-A783-1C85B6776D53.htm) e páginas relacionadas).
- Pedido muito votado na Revit Ideas: tabelas com comportamento de planilha, tipo Excel (808 votos em 2021). Fonte: [Autodesk AEC Blog 2021](https://www.autodesk.com/blogs/aec/2021/02/23/gathering-support-top-10-revit-ideas/) (pelo resumo da busca).
- Outro pedido muito votado: tipos de linha complexos personalizados (797 votos e 62 comentários em 2021). Fonte: a mesma.

**Detalhamento**
- Um usuário vindo do CAD acha o detalhamento desajeitado: as vistas parecem desconectadas umas das outras e não se pode encaixar numa elevação usada como fundo. Fonte: [r/Architects (espelho), out/2024](https://pol1.lr.ggtyler.dev/r/Architects/comments/1fuoiah/frustrated_with_revit/lq2zvkl/?context=3) (pelo resumo da busca; é um espelho não oficial do Reddit).

### Inferences
- O BrasBim pode superar o Revit em três pontos que estão entre os pedidos mais votados há anos: (a) tabelas editáveis como planilha, (b) posicionamento de vistas na folha com grade e alinhamento entre folhas, e (c) tipos de linha complexos. O Revit só começou a tratar (b) em 2026–2027.
- A numeração por regra e o "etiquetar por exemplo" são boas referências de UX para o BrasBim, que já tem barra de opções contextual e minibarra de seleção.
- A faixa de vista do Revit é um conceito que confunde iniciantes. No BrasBim ela pode ser mostrada visualmente, por exemplo com um corte esquemático dos planos ao editar.
- Levantamento de materiais por par elemento-material combina com `IfcMaterialLayerSet` e `IfcElementQuantity`. A divergência com perfis e junções é um alerta para calcular quantidades a partir da geometria final.

### Gaps
- Não li páginas oficiais sobre: tipos de vista (RCP, chamadas, vistas de desenho, legendas, câmeras), filtros de V/G e sobreposições, fases e filtros de fase em detalhe, visibilidade de worksets por vista, nuvens de revisão, cotas com EQ, cotas de nível, componentes de detalhe, esquemas de cores, plantas de área, exportação PDF/DWG. Tudo isso deve ser coberto numa próxima rodada pela ajuda `help.autodesk.com/view/RVT/2026/PTB/`.
- Não obtive a lista atual de ideias mais votadas da Revit Ideas: a página do fórum é dinâmica e o blog de 2021 devolveu 403. Os números de votos acima são de 2021 e vieram de resumo de busca.

## 2. Organização do projeto (navegador, modelos, parâmetros, coordenadas)

### Takeaway
O Revit organiza o projeto num navegador hierárquico (com abas desde 2026) e num gerenciador de vínculos renovado. O posicionamento usa três referências: origem interna, ponto base do projeto e ponto de levantamento. As coordenadas compartilhadas são publicadas ou adquiridas entre arquivos, num fluxo poderoso mas famoso por causar erros.

### Cited Findings
- 2026: navegador de projeto com abas. Os tipos de elemento ficam em abas separadas, uma aba "Todos" mantém o layout antigo, e vínculos, grupos e montagens só aparecem quando existem. Fonte: [BIMsmith – Revit 2026](https://blog.bimsmith.com/Revit-2026-Heres-What-You-Need-to-Know-about-the-Latest-Release-of-Autodesk-Revit) (item 4).
- 2026: novo diálogo de gestão de vínculos, com filtros avançados, busca e ordenação. Fonte: a mesma (item 5).
- 2026: botão para duplicar camadas na edição da composição de paredes, pisos, coberturas e forros. Fonte: a mesma (item 2).
- 2027: em vínculos, a espessura de linha pode seguir o modelo hospedeiro ou o modelo vinculado. Fonte: [BIM Pure – Revit 2027](https://www.bimpure.com/blog/revit-2027).
- 2027: materiais podem receber um ativo de carbono com valores do EC3 e ganham ícone de folha. As bibliotecas padrão ainda não trazem dados, e não há integração com o Forma Carbon Insights. Fonte: a mesma.
- Coordenadas: cada projeto tem um ponto base, que é a origem do sistema do projeto, e um ponto de levantamento, que é a origem do sistema compartilhado. Fonte: [Revit API 2026 – BasePoint Class](https://help.autodesk.com/cloudhelp/2026/ENU/Revit-API-MainReference/files/html/154074ae-d653-aaff-b84b-6336a1cbafaa.htm).
- A origem interna (0,0,0 fixo) é usada nos cálculos e não é exibida. O ponto base serve de referência local para cotas e locação. Fonte: [Novedge – Publish Shared Coordinates](https://novedge.com/blogs/design-news/revit-tip-publish-shared-coordinates-for-consistent-revit-model-alignment).
- Fluxo típico: vincular o DWG de levantamento num modelo de implantação, adquirir as coordenadas dele, publicá-las para cada modelo de edifício e depois vincular "por coordenadas compartilhadas". Boa prática: só o arquivo de levantamento civil é fonte de aquisição. Mover o ponto de levantamento sem prendê-lo (unclipped) não muda as coordenadas. Fontes: [Imaginit – Shared Coordinate Best Practice Part 1](https://resources.imaginit.com/revit/shared-coordinate-best-practice-part-1) e [Swinerton – Acquire and Publish](https://swinerton.freshservice.com/support/solutions/articles/1000015312).
- As fontes divergem sobre onde fica o ponto de levantamento em relação ao ponto base: no 0,0,0 ou deslocado. O sistema é o mesmo, mas a prática varia entre escritórios. Fontes: Imaginit e Swinerton (acima).

### Inferences
- O IFC já tem o equivalente direto: `IfcMapConversion` / `IfcProjectedCRS` (georreferência) mais o `ObjectPlacement` do `IfcSite`. O BrasBim pode ter só **um** conceito visível ("ponto de referência do terreno" com coordenadas SIRGAS 2000/UTM) e evitar a confusão de três pontos com aquisição e publicação.
- O navegador com abas por tipo mostra que separar "o que existe no modelo" de "vistas e folhas" ajuda. O BrasBim pode fazer o mesmo com a árvore espacial IFC e uma árvore de documentação.

### Gaps
- Não li fontes primárias sobre: modelos de projeto (.rte), estilos de objeto, espessuras e padrões de linha, parâmetros compartilhados, globais e de projeto. São conhecidos, mas ficaram sem citação nesta rodada.

## 3. Colaboração (worksharing, nuvem, issues, coordenação)

### Takeaway
A colaboração nativa usa um **modelo central** com cópias locais, worksets, empréstimo de elementos e sincronização. O modelo central pode estar num arquivo de rede, num Revit Server ou na nuvem (Revit Cloud Worksharing via BIM Collaborate Pro). A coordenação e a detecção de interferências acontecem fora do Revit (ACC Model Coordination, Navisworks). Desde 2027 as Issues do ACC são nativas no Revit.

### Cited Findings
- Termos oficiais: o modelo central guarda a propriedade (ownership) de todos os elementos e distribui as mudanças publicadas. Cada usuário trabalha numa cópia local e sincroniza. Workset é um conjunto funcional de elementos (interior, exterior, HVAC, elétrica). O workset ativo recebe os elementos novos. Emprestar um elemento sem dono é automático. Se outro usuário o está editando, é preciso pedir ou esperar que ele o libere. Há três modos: por arquivo (pasta de rede), por servidor (Revit Server, com Accelerator para WAN) e na nuvem (coautoria simultânea). Fonte: [Autodesk Help 2025 – Worksharing Terminology](https://help.autodesk.com/cloudhelp/2025/ENU/Revit-Collaborate/files/GUID-6ED32B4D-4BDE-4AB0-83A8-C2D284AD0950.htm).
- Sincronizar envia as mudanças ao central e traz as dos colegas. É também o momento de liberar elementos e worksets, e a prática recomendada é liberar com frequência para não travar a equipe. Quando o elemento tem dono, o usuário pede e o dono precisa sincronizar para conceder. Fontes: [AUGI – Collaboration with Revit Structure Work Sharing](https://augi.com/articles/detail/collaboration-with-revit-structure-work-sharing) e [LinkedIn Learning/lynda – Revit Worksharing](https://www.lynda.com/Revit-tutorials/Introduction-worksharing/435130/544611-4.html) (pelos resumos da busca).
- Recomenda-se organizar worksets por local, sistema ou tipo para reduzir conflitos. Fonte: [Novedge – Real-Time Collaboration](https://novedge.com/blogs/design-news/revit-tip-enhancing-team-workflow-with-real-time-collaboration-strategies-in-revit).
- O BIM Collaborate Pro inclui Model Coordination, com detecção automática de interferências entre modelos enviados a um espaço de coordenação, além de revisão e resolução. A versão Pro acrescenta coautoria na nuvem. Pacotes (packages) podem ser criados e consumidos entre disciplinas. Fontes: [Autodesk – BIM Collaborate Pro features](https://www.autodesk.com/products/bim-collaborate/features) e [Microsol – BIM Collaborate vs Pro](https://microsolresources.com/tech-resources/article/comparison-difference-of-bim-collaborate-and-bim-collaborate-pro).
- No fluxo de 2019 (BIM 360), os modelos enviados a uma pasta de coordenação passavam automaticamente pelo serviço de interferências. Fonte: [AU 2019 – BIM 360 Coordination](https://www.autodesk.com/autodesk-university/class/Understanding-BIM-360-Coordination-Clash-Detection-and-Issue-Management-Workflow-2019).
- 2027: as Issues do ACC podem ser vistas e criadas dentro do Revit sem add-in separado. "Propriedades estendidas" permitem que parâmetros do ACC ou do modelo de coordenação apareçam como parâmetros do Revit. Fonte: [BIM Pure – Revit 2027](https://www.bimpure.com/blog/revit-2027).
- 2027: o Forma Connected Client (prévia) exige que o modelo seja um **modelo de nuvem** ligado a um cenário do Forma. Fonte: [Symetri – Revit 2027](https://www.symetri.co.uk/insights/blog/what-s-new-in-revit-2027-a-guide-to-the-latest-features/) (pelo resumo da busca).
- Dores relatadas: arquivos que crescem rápido e atrasos de sincronização entre disciplinas. Trabalhar várias pessoas no mesmo modelo gera frustração com problemas de arquivo e permissão. Fontes: [G2 – Revit Reviews](https://www.g2.com/products/revit/reviews_and_filters) e [G2 – review 1081140](https://www.g2.com/survey_responses/revit-review-1081140) (pelos resumos da busca).

### Inferences
- O modelo de reserva do BrasBim (servidor e reserva de elemento, com operações serializáveis; ver memória do projeto) equivale ao empréstimo e à propriedade do Revit. A vantagem possível é sincronizar **por operação**, de forma contínua, e não por arquivo inteiro. Isso ataca a dor de "sync lento". Também é possível liberar reservas automaticamente quando a operação termina, sem depender da disciplina de "liberar com frequência".
- Issues dentro do autor e coordenação fora dele: o BrasBim pode fazer o mesmo com BCF nativo (aberto) e IDS, sem nuvem proprietária.
- Workset é um agrupamento de propriedade e visibilidade. No IFC não há equivalente direto. Pode virar `IfcGroup` ou uma propriedade de "zona de trabalho", ou ser tratado só na camada de colaboração.

### Gaps
- Não li detalhes de Navisworks (Clash Detective, TimeLiner) nem do fluxo de pacotes do Design Collaboration.
- Não encontrei dados de desempenho de sincronização (tempos, limites de tamanho de modelo).

## 4. Interoperabilidade (IFC, DWG, Rhino, Forma, Dynamo)

### Takeaway
A exportação e o vínculo IFC do Revit vêm de um add-in **open source** (Autodesk/revit-ifc no GitHub) que substitui o embutido e recebe atualizações frequentes. O IFC4.3 é suportado com ressalvas (Reference View adicionada entre 2025 e 2026). Em 2027 chegou o mapeamento de propriedades pela interface. O suporte a IFC é um complemento, não o modelo nativo.

### Cited Findings
- O repositório Autodesk/revit-ifc contém o vínculo IFC, a exportação IFC e a UI de exportação. Ele sobrescreve o add-in que vem com o Revit, e só a versão anual atual e as duas anteriores recebem correções. Fonte: [GitHub – Autodesk/revit-ifc](https://github.com/Autodesk/revit-ifc).
- Releases recentes: 27.0.1 (abr), primeira para o Revit 2027. Na 27.0.1.1, parâmetros compartilhados passam a poder entrar em psets definidos pelo usuário. Na 27.3.0.12 (13 ago), muitas correções: conexões de tubulação desalinhadas em IFC4x3, vazios de parede em IFC4, quantidades base de sapatas, lajes, patamares e paredes multicamada, elementos de fabricação MEP exportados em dobro, níveis importados de IFC vinculado, portas mal posicionadas ao abrir IFC de outros softwares. As versões 24.3.40, 25.4.40 e 26.4.1 acrescentaram os requisitos de troca **IFC4.3 Reference View**. A 25.4.3 trocou atributos obsoletos do IFC4.3 (LandTitleID, SiteAddress) por Pset_LandRegistration e Pset_Address, permitiu exportar grupos como qualquer tipo de IfcSystem, exportou fração de constituintes de material e ampliou o suporte a códigos EPSG e escala na map conversion. Fonte: [GitHub – revit-ifc Releases](https://github.com/Autodesk/revit-ifc/releases).
- Uma tabela de terceiros diz que a exportação IFC 4.3 é marcada como suportada até 2025, enquanto IFC 4.3 ADD2 em 2025–2027 tem resultados possivelmente inconsistentes. Fonte: [Newforma Konekt – IFC Schema Support](https://konekt.help.newforma.com/?p=463715) (pelo resumo da busca). Isso **conflita em parte** com as releases do GitHub, que seguem adicionando IFC4.3 em 2026 e 2027. Considere a fonte do GitHub como primária.
- 2027: na exportação IFC, o mapeamento de parâmetros para psets é feito no diálogo, sem arquivo de texto. Fonte: [BIM Pure – Revit 2027](https://www.bimpure.com/blog/revit-2027).
- A exportação IFC também roda na nuvem via APS (Model Derivative e Design Automation). Fonte: [APS blog – Export IFC from RVT using Design Automation](https://aps.autodesk.com/blog/export-ifc-rvt-using-design-automation-api-revit-part-i).
- 2026: famílias compatíveis podem ser substituídas por ativos do Twinmotion via parâmetro de tipo. Fonte: [BIMsmith – Revit 2026](https://blog.bimsmith.com/Revit-2026-Heres-What-You-Need-to-Know-about-the-Latest-Release-of-Autodesk-Revit) (item 8).
- 2026: plugin ReCap Pro Mesh para retrofit e reabilitação, e Accelerated Graphics em prévia. Fonte: [Autodesk AEC Blog – What's new in Revit 2026](https://www.autodesk.com/blogs/aec/2025/04/02/whats-new-in-revit-2026/) (pelo resumo da busca).
- 2027: Forma Connected Client (dados de contexto, análise de vento, carbono na aba Analisar). Dynamo 4.0.2 com gestão de pacotes melhorada e PythonNet 3. Fonte: [BIM Pure – Revit 2027](https://www.bimpure.com/blog/revit-2027).

### Inferences
- O próprio Revit depende de um exportador IFC que ainda corrige quantidades base, vazios e posicionamento em 2026. Isso indica que um app IFC-nativo como o BrasBim tem vantagem estrutural: não há tradução, e o arquivo é o modelo.
- O mapeamento de psets na UI (2027) mostra uma demanda real. No BrasBim, psets e propriedades são nativos, e o painel de propriedades já edita o IFC.
- Os casos que o exportador do Revit corrige (Pset_Address, EPSG, IfcSystem, fração de constituintes, quantidades de paredes multicamada) servem como **lista de teste** para o BrasBim.

### Gaps
- Não li fontes sobre importação e vínculo de DWG no Revit (camadas, unidades, "importar" versus "vincular"), nem sobre o conector Rhino.Inside.Revit.
- Não confirmei, em página oficial da Autodesk, a lista de esquemas IFC do diálogo nativo de 2027 (IFC2x3, IFC4 RV/DTV, IFC4.3).

## 5. Automação (API, Dynamo, pyRevit, add-ins, IA)

### Takeaway
O Revit tem uma API .NET madura (no .NET 10 a partir de 2027), Dynamo embutido e um grande ecossistema de terceiros (pyRevit, open source). Em 2027 chegou o Autodesk Assistant, uma IA em linguagem natural com ferramentas MCP. As avaliações iniciais foram fracas e as seguintes, melhores.

### Cited Findings
- O Revit 2027 migra para .NET 10, o que afeta os desenvolvedores de add-ins. Dynamo 4.0.2 com PythonNet 3. Fonte: [BIM Pure – Revit 2027](https://www.bimpure.com/blog/revit-2027).
- Autodesk Assistant (prévia em 2027): interface em linguagem natural para consultar e analisar o modelo, gerar vistas e folhas e orientar o usuário. Fonte: [Symetri – Revit 2027](https://www.symetri.co.uk/insights/blog/what-s-new-in-revit-2027-a-guide-to-the-latest-features/) (pelo resumo da busca).
- Teste do BIM Pure com cerca de uma dúzia de tarefas: a maioria falhou. O assistente declarou sucesso sem mudar nada, disse que não conseguia criar filtros de vista e criou um corte que não foi pedido. O autor desaconselha o uso em projetos reais. Fonte: [BIM Pure – Revit 2027](https://www.bimpure.com/blog/revit-2027).
- 2027.1 e 2027.2: respostas com data e hora, botão de parar, e logs das ferramentas MCP no journal do Revit. Num teste posterior, mais tarefas tiveram sucesso. O autor ainda o considera adequado só para iniciantes e recomenda o pyRevit MCP com Claude Code para usuários avançados. Fonte: [BIM Pure – 2027.1/2027.2](https://www.bimpure.com/blog/top-5-new-features-in-revit-2027-1-and-revit-2027-2).
- pyRevit: plataforma livre para escrever ferramentas em Python (IronPython ou CPython), C# ou VB.NET. Cria uma aba própria, recarrega scripts na sessão e traz CLI de implantação e servidor de telemetria para equipes. Fontes: [OSArch Wiki – pyRevit](https://wiki.osarch.org/pyrevit/) e [Autodesk dev blog – The pyRevit IronPython Script Library](https://blog.autodesk.io/the-pyrevit-ironpython-script-library/).
- RevitPythonShell, um projeto separado, dá console IronPython interativo com acesso à API. Fonte: [GitHub – revitpythonshell](https://github.com/jeremytammik/revitpythonshell).
- Na Revit Ideas, ideias de API recebem uma etiqueta própria e podem ser priorizadas com menos votos que as de interface. Fonte: [Autodesk Forum – Idea forum (API)](https://forums.autodesk.com/t5/revit-api-forum/idea-forum/m-p/7711739) (pelo resumo da busca).
- A numeração por regra de 2027 substitui algo que antes exigia add-ins. Fonte: [Symetri – Revit 2027](https://www.symetri.co.uk/insights/blog/what-s-new-in-revit-2027-a-guide-to-the-latest-features/) (pelo resumo da busca).

### Inferences
- Como o BrasBim é Python com IfcOpenShell, ele já tem o equivalente de "pyRevit nativo": o console Python e os scripts usam a mesma API do núcleo. Um servidor MCP sobre `brasbim/core` (operações serializáveis) daria ao BrasBim um assistente de IA mais confiável que o da Autodesk, porque toda operação é verificável no IFC gerado.
- A falha do assistente da Autodesk ("disse que fez, mas não fez") reforça uma regra para o BrasBim: toda ação de IA deve gerar uma transação visível e desfazível, com diff.

### Gaps
- Não li a documentação da Revit API (eventos, transações, updaters) nem a política da Autodesk App Store.

## 6. UX, pontos fortes e dores (desempenho, tamanho de arquivo, aprendizado, preço, Brasil)

### Takeaway
O ponto mais elogiado é a coordenação por modelo único: uma mudança atualiza plantas, cortes e tabelas. As maiores dores são lentidão em modelos grandes, arquivos pesados, curva de aprendizado íngreme, preço alto só por assinatura, exigência de hardware e incompatibilidade entre versões (não há como salvar para versão anterior). A Autodesk responde com aceleração por GPU (2026–2027) e abertura incremental (2027.2), com resultado ainda discutível.

### Cited Findings
- G2 (resumos agregados): lentidão em modelos grandes (9 menções), problemas com arquivos grandes (6), curva de aprendizado (10), preço alto, principalmente somando vários produtos Autodesk (6). Hardware exigente. Versões diferentes não abrem umas nas outras com facilidade e não há downgrade. O maior elogio é a mudança no 3D que se propaga para plantas, cortes e tabelas. Fontes: [G2 – Revit Reviews (953)](https://www.g2.com/products/revit/reviews_and_filters), [G2 – página 5](https://g2.com/products/revit/reviews?page=5) e [G2 – review 1081140](https://www.g2.com/survey_responses/revit-review-1081140) (pelos resumos da busca; os números variam entre páginas).
- Um freelancer critica o custo alto da assinatura sem opção de licença perpétua. Fonte: [G2 – Revit Reviews](https://www.g2.com/products/revit/reviews_and_filters) (pelo resumo da busca).
- Outras queixas: biblioteca de famílias e materiais limitada, renderização fraca, e o Revit não ser feito para projeto elétrico. Fonte: [G2 – review 4621794](https://www.g2.com/survey_responses/revit-review-4621794) (pelo resumo da busca).
- Fóruns antigos (AUGI, 2003–2005) já reclamavam de travamentos e da volta para a vista anterior após cancelar um comando. Isso mostra que as dores de estabilidade são antigas. Fonte: [AUGI forums – t-22710](https://forums.augi.com/archive/index.php/t-22710.html) (pelo resumo da busca).
- Preço (EUA, fonte não oficial, mai/2026): só assinatura de usuário nomeado. Anual cerca de US$ 3.005, mensal cerca de US$ 380, AEC Collection cerca de US$ 3.675/ano. Fonte: [MyArchitectAI – Preços do Revit 2026](https://www.myarchitectai.com/pt/blog/revit-pricing). O G2 informa "a partir de US$ 290/mês". Fonte: [G2 – Revit](https://www.g2.com/products/revit) (pelo resumo da busca). Os valores **divergem** entre as fontes.
- Brasil: não achei preço oficial em reais. Há licitações públicas de 2026 para Revit e AEC Collection: pregão do Superior Tribunal Militar estimado em R$ 752.071,00 com abertura em 04/08/2026, e CREA-RS estimado em R$ 26.989,00 para duas licenças anuais (cerca de R$ 13,5 mil por licença por ano, valor estimado do edital). Fontes: [Alerta Licitação – PE036/2026](https://alertalicitacao.com.br/!licitacao/DMSC-8676201) e [Alerta Licitação – Edital 90010/2026](https://alertalicitacao.com.br/!licitacao/PNCP-92695790000195-1-000040-2026) (pelo resumo da busca; não confirmei qual link corresponde a qual órgão). FAQ de assinatura em pt-BR: [Autodesk BR – Revit subscription FAQ](https://www.autodesk.com/br/solutions/revit-subscription-faq).
- Desempenho: o Accelerated Graphics (GPU) foi prévia em 2026 e saiu da prévia em 2027, com suporte a sobreposições, transparência, meio-tom e vínculos. Ainda faltavam sombras, e ele remove a espessura de linha em planta. Sombras ambientes chegaram depois. Fontes: [BIMsmith – Revit 2026](https://blog.bimsmith.com/Revit-2026-Heres-What-You-Need-to-Know-about-the-Latest-Release-of-Autodesk-Revit), [BIM Pure – Revit 2027](https://www.bimpure.com/blog/revit-2027) e [BIM Pure – 2027.1/2027.2](https://www.bimpure.com/blog/top-5-new-features-in-revit-2027-1-and-revit-2027-2).
- Abertura incremental de modelo (2027.2): no teste do BIM Pure, o modelo de exemplo abriu em 22 s com e sem a opção, ou seja, sem ganho medido. Fonte: [BIM Pure – 2027.1/2027.2](https://www.bimpure.com/blog/top-5-new-features-in-revit-2027-1-and-revit-2027-2).
- Interface 2027: a barra de opções foi removida e as opções de criação foram para a faixa de opções contextual. Fonte: [BIM Pure – Revit 2027](https://www.bimpure.com/blog/revit-2027).
- 2027: paredes hospedadas em paredes cortam abertura automaticamente, mas não com afastamento acima de 152 mm. Os marcos e guarnições de portas e janelas não consideram a espessura da parede hospedada, e o autor chama isso de "problema grave". Fonte: a mesma.
- Ritmo de versões: 2027.1 (jun) e 2027.2 (jul) saíram com cinco semanas de intervalo, e o autor pergunta se a cadência está acelerando. Fontes: [BIM Pure – 2027.1/2027.2](https://www.bimpure.com/blog/top-5-new-features-in-revit-2027-1-and-revit-2027-2) e [Autodesk AEC Blog – What's New in Revit 2027.1](https://www.autodesk.com/blogs/aec/2026/06/16/whats-new-in-revit-2027-1/) (pelo resumo da busca).
- Revit Ideas: um snapshot do quadro listava cerca de 12 mil ideias em "Gathering Support" e 170 aceitas. Fonte: [Autodesk Forums – Revit Ideas](https://forums.autodesk.com/t5/revit-ideas/idb-p/revit-ideas-en/status-key/2) (pelo resumo da busca; o número muda com o tempo).

### Inferences
- Lacunas que o BrasBim pode explorar: (1) custo zero contra cerca de R$ 13 mil por licença por ano em compras públicas, o que importa para prefeituras, órgãos públicos e escritórios pequenos (o BIM é exigido em obras públicas no Brasil desde o Decreto 10.306/2020; verificar a fonte em outra rodada); (2) formato aberto sem bloqueio de versão, porque um IFC abre em qualquer versão, ao contrário do .rvt que não volta para versão anterior; (3) desempenho em modelos médios no primeiro plano.
- A Autodesk tirou a barra de opções e levou tudo para a faixa de opções em 2027. O BrasBim fez o caminho inverso, com barra de opções contextual. Vale observar a reação dos usuários do Revit a essa mudança antes de mexer na decisão.
- A dor do detalhamento (vistas desconectadas, falta de snap no fundo) sugere que o desenho 2D do BrasBim (pacote 14) deve permitir encaixar em qualquer geometria visível, inclusive de fundo e de vínculos.

### Gaps
- Não consegui ler threads do r/Revit diretamente: a busca só trouxe um espelho de r/Architects. Também não li Capterra nem RevitForum.org.
- Não há preço oficial em reais nem informação sobre problemas específicos do Brasil (localização pt-BR, conteúdo ABNT, famílias brasileiras). Pesquisar em outra rodada.
- Não li a lista atual de ideias mais votadas (de 2022 a 2026).
