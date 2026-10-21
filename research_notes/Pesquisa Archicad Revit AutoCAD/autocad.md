# AutoCAD (2025/2026/2027), AutoCAD Architecture e superfícies do Civil 3D: funcionalidade, uso no Brasil, pontos fortes e fracos

> Notas de pesquisa clean-room. Só fontes públicas da web, todas acessadas em **2026-10-21**. Nada de `_restrito/` ou `tools/`. Nenhum binário inspecionado. Os nomes de comandos aparecem só para identificar a função descrita e não devem ser copiados para a UI do BrasBim. Os textos são resumos próprios. As citações literais são curtas.
>
> **Aviso de método:** foram cerca de 20 buscas e buscas de página. Os blogs da Autodesk (autodesk.com/blogs) responderam HTTP 403 à busca de página, então o conteúdo deles veio só dos trechos do buscador. Os itens marcados **[sem fonte nesta sessão]** são conhecimento geral do pesquisador sobre o AutoCAD. Eles não foram verificados aqui e precisam de fonte antes de entrar em uma spec.

## 1. Interação central de desenho 2D (linha de comando, entrada dinâmica, snaps, rastreamento, grips, seleção, ferramentas de edição, hachuras, restrições)

### Resumo
A fluidez do AutoCAD vem de vários mecanismos que se combinam:
- a linha de comando com apelidos curtos;
- a entrada dinâmica junto ao cursor;
- os snaps a objetos somados ao rastreamento polar e ao rastreamento por snap, que acham pontos sem geometria auxiliar;
- os grips multifuncionais, que editam no lugar.

Hachura com tolerância de vão e restrições paramétricas completam o conjunto. Para o BrasBim, o que mais vale copiar como conceito é a combinação "snap + rastreamento + valor digitado".

### Achados citados
- **Rastreamento por snap (object snap tracking):** funciona junto com os snaps. A partir de pontos de snap já "adquiridos", o programa projeta linhas de alinhamento temporárias para achar pontos exatos. Exemplo da ajuda: achar o centro de um retângulo cruzando o rastreamento a partir de dois pontos médios. — [Autodesk Help, Object Snap Tracking (2022)](https://help.autodesk.com/cloudhelp/2022/ENU/AutoCAD-DidYouKnow/files/GUID-6FB309A8-2696-4383-8277-950E9E2756A8.htm)
- **Rastreamento polar:** limita o cursor a ângulos com incremento configurável (90, 45, 30, 15° ou qualquer valor digitado). Existe a opção de rastrear com snap só na horizontal e na vertical ("Track Orthogonally Only"). — [Autodesk Help, Polar Tracking Tab (LT 2018)](https://help.autodesk.com/cloudhelp/2018/ENU/AutoCAD-LT/files/GUID-D7CBB7B0-9140-4C53-88EF-08EAA09FA9D7.htm)
- **Teclas de alternância e entrada dinâmica:**
  - F3 liga e desliga os snaps; F8, o modo ortogonal; F10, o rastreamento polar; F11, o rastreamento por snap; F12, a entrada dinâmica.
  - A entrada dinâmica mostra distância e ângulo junto ao cursor.
  - Orto e polar são mutuamente exclusivos.
  - Fontes: [Autodesk Help, AutoCAD for Mac Getting Started 2025](https://help.autodesk.com/cloudhelp/2025/ENU/AutoCAD-MAC-GettingStarted/files/GUID-85D8C41C-9C3E-440F-BD60-61848DD27219.htm); [Autodesk Help, To Specify a Precise Point Location (LT 2027)](https://help.autodesk.com/cloudhelp/2027/ENU/AutoCAD-LT/files/GUID-392167BC-8032-44D9-B4A9-DF4AC00DF5C4.htm)
- **Grips multifuncionais em polilinhas:**
  - Ao passar o mouse sobre um grip, abre um menu contextual. No grip de vértice, ele oferece esticar, adicionar vértice e remover vértice.
  - No grip do meio de um segmento reto, oferece converter em arco.
  - As opções mudam conforme o local do grip (vértice ou meio), o tipo de segmento (reta ou arco) e o tipo de polilinha.
  - Fonte: [Autodesk Help, To Modify Polylines With Grips (LT Mac 2024)](https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-LT-MAC/files/GUID-2070C02C-E18A-4333-BDC4-240F49F1C102.htm)
- **Limite conhecido dos grips:** o "adicionar vértice" no último grip insere o vértice antes do fim, não depois. O contorno é inverter a direção da polilinha (REVERSE). — [Autodesk Blog, Cool AutoCAD Grip Tips](https://www.autodesk.com/blogs/autocad/cool-autocad-grip-tips/) (via trecho do buscador)
- **Edição de vários grips de uma vez:** com Shift é possível selecionar vários grips de vértice e esticá-los ou apagá-los juntos. Isso está documentado no clone nanoCAD, e o comportamento é análogo ao do AutoCAD. — [nanoCAD Help, multifunctional grips](https://nanocad.com/support/online-help/editing-objects-using-multifunctional-grips)
- **Hachura com tolerância de vão:**
  - A variável HPGAPTOL deixa hachurar uma área cujo contorno tem aberturas menores que a tolerância.
  - O padrão é zero, e daí vem a "regra" de que o contorno precisa ser fechado.
  - O controle aparece na aba contextual da faixa de opções ao criar a hachura, ou no diálogo expandido.
  - Uso típico: hachurar um ambiente com o vão da porta aberto, ajustando a tolerância para a largura da porta.
  - Fontes: [Autodesk Blog, Tuesday Tips with Frank – Hatch Gap Tolerance](https://www.autodesk.com/blogs/autocad/hatch-gap-tolerance-autocad-tuesday-tips-frank/); [The CAD Geek, Hatching Open Areas](https://thecadgeek.com/blog/autocad-hatch-gap/); [Arkance, Gap Tolerance – AutoCAD](https://ukcommunity.arkance.world/hc/en-us/articles/21549311247762-Gap-Tolerance-AutoCAD)
- **Limpeza de geometria (2027):** o recurso novo "Geometry Cleanup" varre o desenho atrás de vãos, sobras (overshoots), faltas (undershoots), entidades desconectadas e desvios dos ângulos de snap. Ele sugere correções e dá zoom em cada erro. — [Architosh, Autodesk 2027 adds strong new features](https://architosh.com/2026/04/autodesk-2027-adds-strong-new-features/); [Hagerman, What's new in AutoCAD 2027](https://blog.hagerman.com/draw-smarter-deliver-faster-whats-new-in-autocad-2027)
- **Lengthen (2027.1):** a versão 2027.1 trouxe uma opção nova no comando de alongar. — trecho do buscador de [Autodesk Blog, AutoCAD 2027.1](https://www.autodesk.com/blogs/autocad/autocad-2027-1/) (página com 403; o detalhe da opção não foi confirmado)

### Inferências
- O modelo "snap + rastreamento + distância digitada" (o usuário aponta a direção com o cursor e digita o comprimento) é o núcleo da velocidade do AutoCAD. A barra de Opções e a entrada numérica do BrasBim devem permitir isso sem diálogo.
- Hachura com tolerância de vão é diretamente aplicável ao preenchimento de ambientes e de zonas IfcSpace a partir de paredes com aberturas. O "Geometry Cleanup" sugere uma ferramenta útil para o DXF/DWG importado como referência (spec/ui 22): achar vãos e pontas soltas antes de usar o desenho para pegar contornos (terreno TR01–TR08).
- **[sem fonte nesta sessão]** Funcionalidades clássicas que um usuário de AutoCAD espera, todas a confirmar na Ajuda do AutoCAD antes de especificar:
  - apelidos de comando editáveis em arquivo de configuração, com Enter ou espaço repetindo o último comando;
  - seleção por janela (esquerda→direita, só o que está inteiro dentro) e por cruzamento (direita→esquerda, o que toca), além de cerca, laço e seleção rápida por propriedade;
  - edição: deslocar paralela a uma distância (offset); aparar e estender até a aresta mais próxima; concordar com raio, que com raio 0 vira canto vivo (fillet/chamfer);
  - matriz retangular, polar ou ao longo de caminho, com opção associativa editável depois;
  - esticar por janela de cruzamento, escala por referência, alinhar por pares de pontos, unir, quebrar no ponto;
  - polilinhas com largura e arcos, splines por pontos de ajuste ou de controle;
  - região e contorno a partir de área fechada;
  - restrições geométricas (paralelo, perpendicular, tangente, coincidente, etc.) e dimensionais com expressões.

### Lacunas
- Não busquei as páginas da Ajuda sobre offset/trim/fillet/array associativo/restrições paramétricas. As buscas focaram hachura e voltaram sem resultado sobre matrizes e restrições.
- Não confirmei o comportamento atual (2025+) do "trim/extend" no modo rápido (padrão desde 2021) em fonte oficial.

## 2. Organização: camadas, blocos dinâmicos, xrefs, espaço modelo e papel, viewports, escala de anotação, estilos de plotagem, paletas, modelos

### Resumo
A organização do AutoCAD se apoia em:
- camadas, com estados e sobreposições por viewport;
- blocos, inclusive dinâmicos com parâmetros, ações, estados de visibilidade e tabelas de lookup;
- referências externas;
- a separação entre modelo (1:1) e papel (folhas com viewports em escala);
- objetos anotativos que mudam de tamanho conforme a escala de cada viewport.

As versões 2026–2027 levaram arquivos de suporte e referências para a nuvem.

### Achados citados
- **Blocos dinâmicos e visibilidade:**
  - Um bloco pode ter só **um** parâmetro de visibilidade, mas muitos estados de visibilidade.
  - Esse parâmetro não precisa de ação associada. No desenho, um grip abre a lista de estados.
  - Para controlar a visibilidade de vários grupos de forma independente, a comunidade recorre ao truque de "double lookup".
  - Fontes: [Autodesk Community, Multiple visibility parameters in a dynamic block](https://forums.autodesk.com/t5/dynamic-blocks-forum/multiple-visibilty-parameters-in-a-dynamic-block/m-p/12530601); [Novedge, Visibility States tip](https://novedge.com/blogs/design-news/autocad-tip-using-visibility-states-in-autocad-dynamic-blocks)
- **Parâmetros e ações:**
  - Os parâmetros definem propriedades personalizadas; as ações (inseridas com BACTION) operam sobre elas.
  - O parâmetro de lookup escolhe um valor de uma tabela e muda a geometria. Ele aparece no painel Propriedades, na seção "Custom".
  - Tudo é feito em um editor de blocos dedicado.
  - Fontes: [Autodesk Help, Block Editor (LT 2026)](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-LT/files/GUID-B69D58AD-7920-4198-AB2A-0E24B944F6CD.htm); [Autodesk Help, Work With Action Parameters in Blocks (LT Mac 2026)](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-LT-MAC/files/GUID-A38D5B3E-6DCA-4AFE-AF79-B7E0DEAB1920.htm); [Properties for Action Parameters Reference](https://help.autodesk.com/cloudhelp/2018/ENU/AutoCAD-LT/files/GUID-B5F9BF95-7CDA-4647-B70A-A31A25AC48B1.htm)
- **Escala de anotação:**
  - Um objeto anotativo guarda várias "representações de escala", cada uma com posição própria (o ponto base do texto, por exemplo).
  - Altura no modelo = altura no papel × escala de anotação.
  - O objeto só aparece no viewport cuja escala ele contém. Escalas se adicionam ou removem por objeto (OBJECTSCALE), e ANNOALLVISIBLE=1 mostra todos os objetos para diagnóstico.
  - Fontes: [Autodesk Help, About Annotation Scales and Viewports (ACA 2027)](https://help.autodesk.com/cloudhelp/2027/ENU/AutoCAD-Architecture/files/GUID-4335105B-F200-4FC7-A5B7-EA9205C2BC4E.htm); [Novedge, Managing Viewport Annotation Scales](https://novedge.com/blogs/design-news/autocad-tip-managing-viewport-annotation-scales-in-autocad)
- **Boas práticas de viewport:** definir a escala do viewport, travá-lo para que o zoom não a altere e manter no modelo (DWT) só as escalas publicadas de fato (1:20, 1:50, 1:100), junto com os estilos anotativos. — [Novedge, Annotative scaling tip](https://novedge.com/blogs/design-news/autocad-tip-autocad-annotative-scaling-for-consistent-annotation-sizes)
- **Referências conectadas (2027):** quando um arquivo referenciado é movido ou renomeado, o AutoCAD detecta a mudança e sugere o reparo na paleta de referências. — [Architosh 2027](https://architosh.com/2026/04/autodesk-2027-adds-strong-new-features/)
- **Arquivos de suporte na nuvem:**
  - Desde 2026, fontes e configurações podem ser centralizadas no Autodesk Docs.
  - Em 2027, paletas de ferramentas e personalizações CUI carregam automaticamente por projeto.
  - Fontes: [Architosh 2026](https://architosh.com/2025/04/whats-new-in-autocad-2026/); [Architosh 2027](https://architosh.com/2026/04/autodesk-2027-adds-strong-new-features/)
- **Smart Blocks:**
  - A IA acha geometria repetida (por exemplo, portas iguais em uma planta vinda de outro programa) e sugere convertê-la em um bloco existente ou novo (BCONVERT). Também há substituição de blocos sugerindo blocos parecidos de uma paleta.
  - Na 2026.1 entrou o status em tempo real da detecção e a opção de jogar as definições de bloco na camada 0.
  - Em 2027, "Detect and Convert" chegou também ao Mac.
  - Fontes: [Architosh 2026](https://architosh.com/2025/04/whats-new-in-autocad-2026/); [Digital Engineering, What's new in AutoCAD 2025](https://www.digitalengineering247.com/article/whats-new-in-autocad-2025/design); trecho do buscador de [Autodesk Blog 2026.1](https://www.autodesk.com/blogs/autocad/autocad-2026-1/); [Architosh 2027](https://architosh.com/2026/04/autodesk-2027-adds-strong-new-features/)
- **Desempenho:** a 2026 anunciou abertura de arquivos até 11× mais rápida e inicialização até 4× mais rápida. A 2027 anunciou troca de layout mais rápida. — [Architosh 2026](https://architosh.com/2025/04/whats-new-in-autocad-2026/); [Arkance, AutoCAD 2026 brings 11x faster file opens](https://arkance.world/gb-en/resources/read/blogs/autocad-2026-brings-11x-faster-file-opens-and-new-ai-tools); trecho do buscador de [Graitec 2027](https://graitec.com/ca-en/blog/autocad-2027-whats-new-key-features-and-business-benefits/)

### Inferências
- Os blocos dinâmicos (geometria + parâmetros + estados de visibilidade + lookup) são o "objeto paramétrico do pobre" no CAD. O BrasBim já tem objetos paramétricos (pacote 13) e pode oferecer o equivalente via IfcTypeObject + conjuntos de propriedades. A dor de "um só parâmetro de visibilidade" mostra que vale permitir vários conjuntos de variantes independentes.
- A escala de anotação resolve um problema que o BIM também tem: texto e cota com tamanho de papel constante em vistas de escalas diferentes. No BrasBim, a anotação deveria ser definida em mm de papel e escalada pela vista, sem que o usuário tenha de adicionar escalas por objeto. Essa gestão manual é uma fonte conhecida de confusão (daí existir ANNOALLVISIBLE).
- **[sem fonte nesta sessão]** Recursos clássicos a confirmar antes de especificar:
  - gerenciador de camadas: congelar, desligar, travar, congelar só em um viewport, sobrepor cor/espessura por viewport, filtros e estados de camada salvos e restaurados;
  - xrefs anexadas ou sobrepostas, com recorte (clip);
  - Sheet Set Manager, com folhas, numeração e campos;
  - estilos de plotagem CTB (por cor) e STB (por nome);
  - paletas de ferramentas e DesignCenter para arrastar blocos e estilos de outros arquivos;
  - modelos DWT.

### Lacunas
- Não busquei páginas próprias sobre o Layer Properties Manager, os estados de camada, o Sheet Set Manager, o CTB/STB ou o DesignCenter.
- A 2027.1 cita "edição de propriedades de várias folhas no Sheet Set Manager" e "Ctrl+A no editor de atributos", mas só pelo trecho do buscador (página 403).

## 3. Documentação: cotas, multileaders, tabelas, campos, texto, PDF/DWF, folhas

### Resumo
A documentação no AutoCAD é toda manual e baseada em estilos: estilos de cota, de texto, de multileader e de tabela, além de campos que atualizam texto. As versões recentes focaram em importar marcações de PDF e em plotagem e PDF na nuvem.

### Achados citados
- **Importação de marcações (2025/2026):**
  - PDFs, JPEGs e outras imagens marcadas no papel ou em PDF são importados e as marcações viram elementos ativos.
  - Marcações criadas no Autodesk Docs são convertidas automaticamente e postas na Trace Layer.
  - A Markup Assist ajuda a aplicar as alterações pedidas.
  - Fontes: [Architosh 2026](https://architosh.com/2025/04/whats-new-in-autocad-2026/); [Hagerman, AutoCAD 2025](https://blog.hagerman.com/discover-whats-new-in-autocad-2025)
- **Plotagem (2027):** salvar a plotagem direto na nuvem e pré-visualizar o PDF. — [Architosh 2027](https://architosh.com/2026/04/autodesk-2027-adds-strong-new-features/)
- **Linhas de centro e marcas de centro:** citadas como ferramentas de anotação nas novidades recentes (não confirmado em fonte primária). — trecho do buscador de [IMAGINiT, What's New in AutoCAD 2026](https://resources.imaginit.com/whats-new-in-autodesk-2026-software/what-s-new-in-autocad-2026-top-features-enhancements-with-imaginit-expert-ryan-wunderlich)
- **DWF na aprovação municipal:** a Prefeitura de São Paulo (SMUL) pede documentos em PDF e as plantas a aprovar em **DWF**, não em DWG. Um tutorial municipal de 2013 justifica o DWF por ser um arquivo fechado, que não pode ser editado. — [Prefeitura de SP, SMUL Licenciamento](https://prefeitura.sp.gov.br/web/licenciamento/w/servicos/365490); [Prefeitura de SP, publicação 2013](https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/subprefeituras/sp_mais_facil/arquivos/publicacao-2013-05-28.pdf)

### Inferências
- Para o mercado brasileiro, exportar um PDF vetorial fiel, com espessuras de pena e camadas, é essencial. **Exportar DWF pode ser exigência real** em São Paulo, o que merece verificação e possível suporte (DWF/DWFx é formato da Autodesk, mas há documentação pública do DWFx/XPS).
- **[sem fonte nesta sessão]** Recursos a confirmar: cotas associativas que acompanham a geometria; estilos de cota com sobreposições; cota contínua e de base; multileader com estilos e alinhamento; tabelas com fórmulas e extração de dados de atributos para tabela ou Excel; campos (área de um objeto, nome da folha, data); estilos de texto com fontes SHX e TTF; publicação em lote (PUBLISH).

### Lacunas
- Não busquei as páginas da Ajuda sobre estilos de cota, multileader, DATAEXTRACTION e campos.

## 4. Automação e personalização, incluindo os recursos de IA recentes

### Resumo
A personalização do AutoCAD tem várias camadas:
- AutoLISP/Visual LISP, também no LT para Windows desde 2024, com limites;
- scripts (.scr), macros CUI e o gravador de ações;
- .NET e ObjectARX (C++), só na versão completa.

A IA chegou em três ondas:
- 2025: Smart Blocks e Markup Assist;
- 2026: o Autodesk Assistant conversacional e Activity Insights mais completo;
- 2027: o Assistant consulta normas e faz seleções por texto e integra MCP em prévia técnica.

### Achados citados
- **AutoLISP no AutoCAD LT para Windows:**
  - Desde a versão 2024, o LT roda AutoLISP e DCL, mas sem funções de automação COM (vlax-create-object, vlax-get-object, vla-GetInterfaceObject).
  - entmake e entmod só tratam objetos que o LT suporta.
  - Fontes: [Autodesk Help, What's New or Changed with AutoLISP (2024)](https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-AutoLISP/files/GUID-037BF4D4-755E-4A5C-8136-80E85CCEDF3E.htm); [Autodesk developer update for 2024](https://blog.autodesk.io/autocad-developer-update-for-2024/)
- **Lisp e scripts como motivo de produtividade:** avaliações agregadas do G2 citam o suporte a Lisp e scripts como fator de produtividade, junto com precisão e facilidade no 2D. — [G2, AutoCAD Reviews](https://www.g2.com/products/autocad/reviews_and_filters); [G2, AutoCAD vs FreeCAD](https://www.g2.com/compare/autocad-vs-freecad)
- **Activity Insights:**
  - Registra atividades no arquivo. Em 2025, ganhou um painel de propriedades da atividade (quantos objetos de cada tipo o PURGE removeu, por exemplo) e mostra versões de arquivos salvos na nuvem.
  - Em 2026, passou a mostrar "o que mudou" desde a última vez que o usuário abriu o arquivo, inclusive mudanças feitas por outras pessoas.
  - Fontes: [Digital Engineering 2025](https://www.digitalengineering247.com/article/whats-new-in-autocad-2025/design); [Architosh 2026](https://architosh.com/2025/04/whats-new-in-autocad-2026/)
- **Autodesk Assistant:**
  - Em 2026, assistente conversacional para ajuda.
  - Em 2027, consulta em linguagem natural para verificar o desenho contra um arquivo de normas, extrair informação e criar seleções por texto. Parte disso está em prévia técnica.
  - Usa o Model Context Protocol (MCP) para ler o contexto do desenho. Segundo o Architosh, o objetivo é ler o contexto e não comandar o programa por texto.
  - Em 2027.1, a "assistência por IA" ficou mais inteligente, sem detalhes confirmados.
  - Fontes: [Architosh 2027](https://architosh.com/2026/04/autodesk-2027-adds-strong-new-features/); trecho do buscador de [ProtoTech, AutoCAD 2027](https://blog.prototechsolutions.com/autocad-2027-new-features/); [Autodesk, Key features](https://www.autodesk.com/products/AutoCAD/features)
- **Edição multiusuário por reserva (2027):**
  - O "Checkout" reserva objetos ou regiões de um DWG para edição simultânea.
  - Cada participante edita em um ambiente separado e envia o resultado como uma Trace para revisão.
  - Só o dono principal (leitura e escrita) consolida as Traces no arquivo mestre.
  - Depende do Forma Data Management, o novo nome do Autodesk Docs.
  - Fonte: [Architosh 2027](https://architosh.com/2026/04/autodesk-2027-adds-strong-new-features/)

### Inferências
- O "Checkout" da 2027 confirma o modelo de colaboração por **reserva de elementos** já escolhido para o BrasBim (memória "Colaboração por reserva"). A diferença: no AutoCAD a consolidação é revisada pelo dono do arquivo. Isso vale como referência conceitual, sem copiar o fluxo nem os nomes.
- A API em Python do BrasBim (IfcOpenShell) é o equivalente natural do AutoLISP. Uma macro/script aberta, que grave operações serializáveis, atende ao mesmo público e combina com a exigência de transações serializáveis.
- "Seleção por texto" e "verificar contra normas" mapeiam bem para IDS (verificação de requisitos IFC) e para filtros de seleção por propriedade IFC.
- **[sem fonte nesta sessão]** A confirmar: gravador de ações (grava e reproduz sequências); CUI (faixa de opções, menus, atalhos, duplo clique por tipo de objeto); arquivo de apelidos editável; ObjectARX em C++ e API .NET em C#/VB.

### Lacunas
- Não confirmei se o gravador de ações existe no LT.
- Não achei documentação primária detalhada das funções exatas do Assistant 2027.1 (página bloqueada).

## 5. AutoCAD Architecture (toolset)

### Resumo
O AutoCAD Architecture (ACA) acrescenta objetos de arquitetura (paredes, portas, janelas, etc.) sobre o AutoCAD. A aparência deles é controlada por estilos e por "representações de exibição" geridas em um Display Manager. É poderoso para controlar a exibição, mas pesado de configurar e pouco interoperável com o Revit. As fontes desta sessão não explicam diretamente por que é menos usado.

### Achados citados
- **Estilos e exibição:**
  - No ACA, um estilo reúne propriedades que definem a visibilidade e a forma dos componentes do objeto, a camada, o tipo de linha, etc.
  - A planta da parede tem os componentes contorno e hachura controlados "por material".
  - Para achatar a exibição de um tipo de objeto, basta sobrepor a representação por objeto no Display Manager.
  - Fontes: [Autodesk Community, Display walls as 2d outline](https://forums.autodesk.com/t5/revit-architecture-forum/display-walls-as-2d-outline-in-a-3d-view/m-p/5479096); [Autodesk Community, Component plan hatch and display representation issue](https://forums.autodesk.com/t5/autocad-architecture/component-plan-hatch-and-display-representation-issue/td-p/11813146)
- **Interoperabilidade com o Revit:**
  - O Revit não lê o modelo ACA de forma nativa. Recomenda-se exportar para DWG simples ou IFC.
  - Paredes ACA importadas no Revit mantêm comprimento, largura, altura e nome do estilo, mas viram um único símbolo de importação, não paredes Revit.
  - Fontes: [Autodesk Community, Import 3D AutoCAD content into Revit](https://forums.autodesk.com/t5/revit-architecture-forum/import-3d-autocad-content-into-revit/m-p/8065986); [Autodesk Help, Revit Import Walls](https://help.autodesk.com/cloudhelp/2023/ENU/Revit-DocumentPresent/files/GUID-0805BFCA-44E1-4DF4-9875-8238C7AB406E.htm)
- **Posicionamento da Autodesk:** o AutoCAD segue a abordagem CAD tradicional, com BIM limitado, e o Revit é a ferramenta paramétrica BIM (texto de fornecedor de treinamento, com viés comercial). — [CADD Centre blog](https://caddcentre.com/blog/wp-json/wp/v2/posts/889); [Autodesk, Compare AutoCAD vs Revit](https://www.autodesk.com/compare/autocad-vs-revit)

### Inferências
- O conceito de "representação de exibição por tipo de vista" (planta, 3D, corte, com componentes e cores por material) é útil para o BrasBim. No IFC isso corresponde aos contextos de representação (Plan/Body/Axis) e aos estilos de material. O peso do Display Manager do ACA mostra que padrões ABNT prontos, com pouca configuração, são essenciais.
- Provável motivo do baixo uso do ACA (inferência, não fonte): a Autodesk direciona o BIM de arquitetura para o Revit, o ACA vem "incluso" no AutoCAD como toolset e não é o produto principal, e o seu modelo não se transfere bem para o Revit.

### Lacunas
- Não achei fonte sobre a participação de mercado, o roteiro ou a descontinuação do ACA. Também não achei discussão direta de usuários sobre por que o abandonaram.

## 6. Superfícies do Civil 3D (referência para terreno)

### Resumo
O Civil 3D monta superfícies TIN a partir de pontos e de curvas de nível (polilinhas 2D ou 3D com cota). Elas são refinadas com linhas de quebra de quatro tipos e com contornos que limitam a triangulação, e as curvas são rotuladas por linha de rótulo ou em intervalos.

### Achados citados
- **TIN:** a superfície é formada pelos triângulos de uma rede irregular. Curvas de nível como polilinhas 2D ou 3D com X, Y, Z podem alimentá-la. — [Autodesk Help, Tutorial: Creating and Adding Data to a Surface (2025)](https://help.autodesk.com/cloudhelp/2025/ENU/Civil3D-Tutorials/files/GUID-899731B5-0B6A-451E-9CF2-0DCF00FA9B64.htm)
- **Contornos (boundaries):**
  - São polilinhas fechadas.
  - O contorno externo deixa visíveis só os triângulos de dentro.
  - As áreas ocultas ficam fora dos cálculos de área e volume.
  - Fonte: mesmo tutorial.
- **Linhas de quebra (4 tipos):**
  - *padrão*: cada vértice vira ponto e os triângulos em volta são refeitos;
  - *proximidade*: usa os pontos da superfície mais próximos dos vértices, sem criar pontos novos;
  - *muro*: guarda o lado do deslocamento e o desnível por vértice;
  - *não destrutiva*: só acrescenta triângulos, sem desfazer arestas existentes.
  - Só se aplicam a superfícies de triangulação, e todos os tipos pedem uma distância de meia-ordenada para discretizar curvas.
  - Fontes: [Autodesk Help, About Breaklines (Civil 3D 2024)](https://help.autodesk.com/cloudhelp/2024/ENG/Civil3D-UserGuide/files/GUID-FCCAF28A-506B-4773-9706-DD1F1F8CC933.htm); [Civil 3D DevGuide, Adding a Breakline to a TIN Surface](https://help.autodesk.com/cloudhelp/2024/ENU/Civil3D-DevGuide/files/GUID-4C3A98F1-B429-4052-9ACE-AFBB55E0E60A.htm); [Arkance, Standard vs Non-Destructive Breaklines](https://emea.support.arkance.world/hc/nl/articles/36468594621842-Standard-vs-Non-Destructive-Breaklines-in-Civil-3D-2015)
- **Comandos de superfície:**
  - adicionar contorno, linha de quebra e curvas a uma superfície existente;
  - rotular curvas nas interseções com uma linha de rótulo (AddContourLabeling);
  - rotular curvas em intervalo fixo (AddContourLabelingGroup).
  - Fonte: [Autodesk Help, Civil 3D Surfaces Command Reference (2026)](https://help.autodesk.com/cloudhelp/2026/ENU/Civil3D-UserGuide/files/GUID-DB28F66C-41F2-4171-8F9A-BB549DF3362E.htm)

### Inferências
- Para a ferramenta de terreno do BrasBim (já feita: contorno + curvas pegas do desenho, TR01–TR08), os próximos passos naturais em termos de conceito são:
  1. linhas de quebra (pelo menos a padrão), para muros de arrimo e meios-fios;
  2. contornos internos que escondem triângulos (furos);
  3. rótulos de cota de curva por linha de rótulo;
  4. discretização de arcos por meia-ordenada.

### Lacunas
- Não verifiquei como o Civil 3D trata curvas de nível com simplificação ou remoção de pontos redundantes (opções de "weeding/supplementing").

## 7. Por que escritórios brasileiros ainda usam AutoCAD, pontos mais elogiados e criticados, percepção da passagem de CAD para BIM

### Resumo
No Brasil, o AutoCAD segue forte pela familiaridade, pela oferta de cursos, pelo DWG como formato de troca e pela entrega em 2D (DWG/PDF/DWF) que as prefeituras pedem. A adoção do BIM é desigual: os estudos regionais mostram maioria de escritórios sem BIM, com barreiras de capacitação e de bibliotecas, e o Decreto 10.306/2020 empurra o BIM nas obras públicas federais. As críticas mais citadas são o preço e o modelo de assinatura, a curva de aprendizado e o desempenho com arquivos grandes. Os elogios mais citados são a precisão no 2D, a personalização (Lisp) e a compatibilidade universal do DWG.

### Achados citados
- **Familiaridade:** um estudo acadêmico brasileiro escolheu o AutoCAD por ser o mais usado em projetos, ter confiabilidade no mercado e grande oferta de cursos. — [UniCEUB, publicação PIC](https://publicacoes.uniceub.br/pic/article/download/5547/3892) (via trecho do buscador; ano não confirmado)
- **Adoção do BIM em Juiz de Fora:** 66,7% dos escritórios entrevistados não usavam BIM e só 25% pretendiam implantar nos 12 meses seguintes (amostra pequena e regional). — [UniAcademia, Juiz de Fora](https://seer.uniacademia.edu.br/index.php/ANL/article/download/2346/1566)
- **Barreiras em Curitiba:** falta de profissionais capacitados e de bibliotecas adaptadas, com tendência gradual de migração de CAD para BIM. — [UTFPR, repositório](https://portaldeinformacao.utfpr.edu.br/Record/riut-1-18782/Description)
- **Diferença conceitual:** no CAD, cada mudança exige alterar os objetos à mão; no BIM, modelos paramétricos propagam a mudança para todos os desenhos associados. — [Revista ABENGE](https://revista.abenge.org.br:443/index.php/abenge/article/download/454/290/1055)
- **Decreto 10.306/2020:** prevê BIM nas obras da administração pública federal a partir de 2021, em fases. — citado em [Revista ABENGE](https://revista.abenge.org.br:443/index.php/abenge/article/download/454/290/1055) e outros trabalhos da mesma busca (verificar o texto do decreto em planalto.gov.br)
- **Prefeituras:**
  - São Paulo pede PDF e plantas em DWF.
  - Santos e Santana de Parnaíba pedem PDF.
  - Anúncios de freelancers pedem "projeto para aprovação" em AutoCAD, com entrega em DWG e PDF e as pranchas no Layout. O formato varia por município.
  - Não achei regra oficial que **exija DWG**.
  - Fontes: [Prefeitura de SP, SMUL](https://prefeitura.sp.gov.br/web/licenciamento/w/servicos/365490); [Santana de Parnaíba, Relação de documentos](https://www.santanadeparnaiba.sp.gov.br/obras/2025/RELAÇÃO-DE-DOCUMENTOS-PROJETO-NOVO-SIMPLIFICADO.pdf); [Workana, projeto para aprovação 2D](https://www.workana.com/pt/job/desenvolvimento-de-projetos-arquitetonicos-para-aprovacao-e-execucao-em-2d)
- **Órgãos públicos:** estudos técnicos de prefeituras tratam CAD e BIM como ferramentas internas indispensáveis, por exemplo um ETP de Itapevi para a AEC Collection. — [Itapevi, ETP AEC Collection](https://licitacoes.itapevi.sp.gov.br/filemanager/files/shares/Estudo%20T%C3%A9cnico%20Preliminar_AEC%20Collection_R01.pdf)
- **Elogios (G2):** facilidade de uso e de desenho 2D/3D são os pontos mais citados, seguidos de precisão e confiabilidade no 2D, personalização via Lisp e scripts e o fato de quase todos na área entenderem os formatos. — [G2, AutoCAD vs FreeCAD (resumo de avaliações)](https://www.g2.com/compare/autocad-vs-freecad); [G2, AutoCAD Reviews](https://www.g2.com/products/autocad/reviews_and_filters)
- **Preço de entrada no G2:** US$ 2.940 por 2 anos. — [G2 compare](https://www.g2.com/compare/autocad-vs-freecad)
- **Críticas:**
  - custo da assinatura alto, sobretudo para autônomos e pequenas empresas;
  - interface difícil para iniciantes;
  - lentidão com arquivos grandes ou complexos.
  - Fonte: [G2, AutoCAD Reviews](https://www.g2.com/products/autocad/reviews_and_filters)
- **Fórum da Autodesk sobre preço:**
  - um paisagista relata aumento anual de US$ 300 para US$ 420 e a mudança do escritório para outro software;
  - outra pessoa reclama da conversão forçada da licença perpétua em assinatura;
  - há relato de pirataria disseminada por causa do custo (Grécia).
  - Fonte: [Autodesk Community, AutoCAD's high pricing debate](https://forums.autodesk.com/t5/autocad-forum/autocad-s-high-pricing-debate/m-p/12874158)

### Inferências
- O BrasBim precisa, para competir com o AutoCAD no Brasil:
  1. desenho 2D tão rápido quanto o dele (snaps, rastreamento, valor digitado, grips);
  2. pranchas e layout com PDF fiel e, possivelmente, DWF para São Paulo;
  3. exportação DXF/DWG para quem recebe;
  4. custo zero, que ataca a principal crítica (assinatura) e a pirataria.
- O argumento "BIM sem perder o 2D" responde à barreira de capacitação: começar desenhando em 2D e "promover" o desenho a elementos IFC (o que os Smart Blocks fazem com blocos) seria uma ponte forte de migração.

### Lacunas
- Não achei threads do r/AutoCAD (a busca não retornou o Reddit) nem o quadro AutoCAD Ideas com os pedidos mais votados.
- Não achei pesquisa nacional recente (ASBEA, CAU/BR) sobre a fatia de escritórios em CAD contra BIM, nem o preço atual da assinatura no Brasil em R$.
- Não verifiquei blogs ou canais brasileiros de YouTube específicos sobre AutoCAD.
