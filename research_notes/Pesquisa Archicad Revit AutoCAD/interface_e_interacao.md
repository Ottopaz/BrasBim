# Interface e interação: Archicad, Revit, AutoCAD e outros (SketchUp, Rhino, BricsCAD)

> Notas de pesquisa clean-room, feitas só com fontes públicas da web. Todas as fontes foram acessadas em **2026-10-21**.
> Os textos foram resumidos com palavras próprias. Não há cópia de texto, de ícones nem de layout de diálogos.
> **Limitação desta rodada:** a cota de buscas web da sessão acabou depois de cerca de 16 buscas. Alguns
> temas ficaram sem fonte e estão listados como lacunas: AutoCAD Dynamic Input em detalhe, Smart Blocks,
> atalhos do Revit, apps "tipo Figma" de AEC (Arcol, Snaptrude, Forma), acessibilidade e queixas recentes
> no Reddit. Duas páginas da comunidade Graphisoft retornaram 403.

## 1. Entrada de geometria (linha de comando × ferramenta primeiro × objeto primeiro; entrada dinâmica; inferência/snap; digitar distâncias; repetir comando)

### Takeaway
Há quatro escolas:
- **AutoCAD e Rhino:** linha de comando com autocompletar, mais rastreamento por alinhamento (AutoTrack ou SmartTrack).
- **Archicad:** ferramenta primeiro, com Tracker flutuante junto ao cursor, guias de snap e "pet palette" de modos geométricos.
- **Revit:** ferramenta primeiro, com cotas temporárias editáveis e linhas de alinhamento.
- **SketchUp:** motor de inferência com cores, travamento de eixo por teclado e digitação de valores *depois* de iniciar o gesto, sem campo focado.

O ponto em comum dos mais rápidos: o usuário digita um número a qualquer momento sem clicar em campo, e esse número é aplicado na direção que a inferência sugere.

### Cited Findings
**Archicad**
- O Archicad separa três coisas:
  - **Snap Points**, antes "Special Snap Points": pontos como meio ou divisões ao longo do elemento.
  - **Snap References**: arestas ou pontos "ativados" ao passar o cursor, destacados em azul. Várias podem ficar ativas ao mesmo tempo.
  - **Snap Guides**: linhas temporárias nos eixos X/Y e a cada 45°. Também indicam tangente, paralela, perpendicular e bissetriz.

  — [Resumo de busca sobre ajuda Graphisoft: Snap Points/Guide Lines AC19](https://help.graphisoft.com/AC/19/INT/AC19Help/NewFeatures/NewFeatures-5.htm); [Snap References (comunidade Graphisoft)](https://community.graphisoft.com:443/t5/Let-s-get-started/Snap-References/ta-p/303967)
- No Archicad, o usuário pode medir uma distância a partir de uma Snap Reference: passa o cursor sobre ela (ou usa a tecla Q) e digita o valor no **Tracker**. A distância passa a contar daquele ponto. — [Snap References (comunidade Graphisoft)](https://community.graphisoft.com:443/t5/Let-s-get-started/Snap-References/ta-p/303967) (via resumo de busca)
- O Archicad tem **Guide Lines permanentes**. O usuário as arrasta da borda da janela para o modelo, presas a um ponto ou aresta ou soltas no espaço vazio, e elas ficam até serem removidas. É algo distinto das guias temporárias. — [Guide Lines and Snap Points Migration AC21](https://help.graphisoft.com/AC/21/INT/AC21Help/MigrationGuide/MigrationGuide-10.htm)
- **Pet palette** do Archicad: um mini-painel aparece junto ao cursor depois do 1º clique e oferece variações geométricas (por exemplo reta, arco, poligonal). Um guia de terceiros diz que a tecla F alterna as opções e que a tecla G alterna os ícones da Info Box. — [macinteract (guia de terceiros)](https://smart.macinteract.com/?p=2405)
- **Varinha mágica** (segurar Espaço) do Archicad: um clique dentro de um contorno detecta a região, e um clique numa aresta detecta o contorno do objeto. Com muitos elementos na tela o controle é menor, então é preciso conferir o resultado. — [macinteract](https://smart.macinteract.com/?p=2405)
- No Archicad, a **Info Box** (Ctrl/Cmd+T) é a barra contextual de parâmetros da ferramenta ativa. — [curso Lynda/LinkedIn Archicad 24](https://www.lynda.com/ArchiCAD-tutorials/Info-Box/2862042/2396571-4.html)

**Revit**
- As **cotas temporárias** do Revit aparecem logo depois de colocar o elemento e somem ao colocar o próximo. Para revê-las, o usuário seleciona o elemento de novo. Elas se prendem ao elemento perpendicular mais próximo e variam em incrementos configuráveis. Arrastar a linha de chamada troca a referência. Para manter uma cota visível sempre, o usuário cria uma cota permanente, que vale só para aquela vista. — [Autodesk: About Temporary Dimensions (2018)](https://help.autodesk.com/cloudhelp/2018/ENU/Revit-DocumentPresent/files/GUID-74FFB00B-FB29-44B7-8FEA-613DBE010AD4.htm)
- **Snaps no Revit 2026:**
  - Os pontos aparecem como formas (triângulo, quadrado, losango) e as linhas de snap como tracejadas.
  - Há "jump snaps" fora do cursor quando Nearest está desligado.
  - O usuário pode forçar um único tipo de snap por clique digitando dois caracteres (por exemplo SC para centro) ou pelo menu de contexto.
  - Os incrementos de cota diminuem ao aproximar o zoom e aumentam ao afastar.
  - As configurações valem para a sessão, não são salvas no projeto e se aplicam a todos os arquivos abertos.

  — [Autodesk: About Snaps, Revit 2026](https://help.autodesk.com/cloudhelp/2026/ENU/Revit-Customize/files/GUID-A3947840-1F30-41D7-AF75-B61687952A07.htm)
- Para paredes no Revit, a barra de opções define a que a cota temporária se refere (eixo, face, núcleo). A tecla Tab durante a colocação alterna para outras referências, segundo um mentor no fórum. — [Fórum Autodesk: Wall dimensions](https://forums.autodesk.com/t5/revit-architecture-forum/wall-dimensions/m-p/6051498/highlight/true)
- Limitação relatada no Revit: a cota alinhada só se prende a nós e linhas, não a pontos médios (o contorno é usar EQ). Há pedidos antigos de usuários por mais pontos de snap em cotas. — [Revit Ideas: dimension to snap points](https://forums.autodesk.com/t5/revit-ideas/dimension-to-snap-points/idc-p/13723830); [Revit Ideas: dimension snapping](https://forums.autodesk.com/t5/revit-ideas/dimension-snapping/idi-p/7780631)

**AutoCAD**
- **Object Snap Tracking no AutoCAD 2026:**
  - Pontos são "adquiridos" automaticamente ao passar sobre um osnap e marcados com "+". Shift evita a aquisição em áreas apertadas.
  - Com a aquisição feita, surgem caminhos de alinhamento horizontais, verticais ou polares.
  - Com o caminho visível, digitar uma distância coloca o ponto exatamente sobre ele.
  - "tt" cria um ponto de rastreamento temporário.

  — [Autodesk: About Tracking Points Automatically Using Object Snaps (AutoCAD LT 2026)](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-LT/files/GUID-665DC37F-8C3E-414A-9369-72A13C0BE07A.htm)
- No AutoCAD, F10 liga o rastreamento polar, F11 o rastreamento por osnap e F12 a entrada dinâmica. Ortho (F8) e Polar são mutuamente exclusivos. As variáveis POLARMODE, TRACKPATH e POLARANG controlam o comportamento (POLARANG vem com 90 por padrão). — [Autodesk Did You Know: Object Snap Tracking (2022)](https://help.autodesk.com/cloudhelp/2022/ENU/AutoCAD-DidYouKnow/files/GUID-6FB309A8-2696-4383-8277-950E9E2756A8.htm) (valores a confirmar na versão 2026)
- No AutoCAD, a entrada dinâmica (F12) põe os campos de valor junto ao cursor. Uma dica de terceiros cita DYNMODE=3 para ter entrada de ponteiro e de cota ao mesmo tempo. — [Novedge: Dynamic Input F12](https://novedge.com/blogs/design-news/autocad-tip-dynamic-input-f12-heads-up-cursor-entry-for-faster-precise-drafting) (fonte secundária, de revendedor)

**SketchUp**
- O motor de inferência do SketchUp tem três tipos:
  - **Pontos:** extremidade, meio, interseção, centro, ponto na face ou aresta.
  - **Lineares:** eixos vermelho, verde e azul; paralela ou perpendicular (magenta); prolongamento.
  - **Formas:** quadrado, retângulo áureo, frações de círculo.

  Cada tipo tem cor e dica próprias. — [SketchUp Help: Drawing basics and concepts](https://help.sketchup.com/en/sketchup/introducing-drawing-basics-and-concepts)
- **Travamento no SketchUp:**
  - Setas → eixo vermelho, ← eixo verde, ↑ eixo azul.
  - ↓ trava paralela ou perpendicular a uma aresta ou face.
  - Shift segura a direção ou o plano atual.
  - Pausar sobre um ponto dá prioridade a ele.
  - Com a ferramenta Linha, Alt/Cmd alterna entre todas as inferências, nenhuma ou só paralela/perpendicular.

  — [SketchUp Help](https://help.sketchup.com/en/sketchup/introducing-drawing-basics-and-concepts)
- No SketchUp, o usuário digita o comprimento e dá Enter **depois** de iniciar a linha, sem clicar em campo nenhum. A caixa Measurements aceita coordenadas absolutas `[x,y,z]` e relativas `<x,y,z>`. A ajuda recomenda orbitar de vez em quando para conferir alinhamentos que parecem certos numa vista só. — [SketchUp Help](https://help.sketchup.com/en/sketchup/introducing-drawing-basics-and-concepts)
- Usuários do SketchUp contam que Shift transforma a linha de inferência fina em grossa e "desliga" as outras inferências que atrapalham. — [O'Reilly: Google SketchUp, the Missing Manual, cap. 4](https://www.oreilly.com/library/view/google-sketchup-the/9780596804060/ch04.html); [SketchUcation](https://community.sketchucation.com/post/978086)

**Rhino**
- **Linha de comando do Rhino 8:**
  - Autocompletar com **busca aproximada (fuzzy)**, com os comandos mais usados no topo.
  - O comando completa sozinho quando as letras digitadas já o identificam.
  - As opções do comando são clicáveis ou acionadas pela letra sublinhada.
  - O botão direito no histórico mostra os comandos recentes.
  - O teclado vai para a linha de comando sempre que a janela está ativa, exceto dentro de campos de painel.

  — [McNeel: The Rhino window (Rhino 8)](https://docs.mcneel.com/rhino/8/help/en-us/user_interface/rhino_window.htm); [Rhino Options: Appearance](https://docs.mcneel.com/rhino/9/help/en-us/options/appearance.htm)
- No Rhino, Osnap, SmartTrack e Gumball são painéis da barra de status: clique liga ou desliga, botão direito abre as opções. — [McNeel: The Rhino window](https://docs.mcneel.com/rhino/8/help/en-us/user_interface/rhino_window.htm)

**BricsCAD**
- Os snaps de entidade do BricsCAD ficam num menu acionado por Shift+botão direito no meio do comando. — [Resumo de busca: Bricsys help](https://help.bricsys.com/en-us/document/bricscad-shape/basic-concepts-of-modeling-in-bricscad-shape)

### Inferences
- Melhor combinação para o BrasBim:
  - Inferência visual por cores, ao estilo SketchUp.
  - Aquisição de ponto por pausa do cursor, como no AutoCAD/Archicad.
  - Digitação "cega" de distância a qualquer momento, sem foco em campo, como no SketchUp e no OTRACK do AutoCAD.
  - Travamento de eixo por tecla (setas ou Shift).

  Juntar os quatro supera cada concorrente isolado, porque nenhum deles reúne todos.
- A cota temporária do Revit é muito elogiada como modelo mental ("clique no número e digite"). Copiar a *ideia* (cota viva editável junto ao elemento recém-criado ou selecionado) é compatível com clean-room se o desenho e o vocabulário forem próprios.
- A dependência de dezenas de modos (F8–F12, variáveis de sistema) no AutoCAD é poderosa, mas pouco descobrível. Vale preferir poucos modos visíveis na barra de status, com clique para ligar/desligar e botão direito para opções (padrão Rhino).
- Busca fuzzy de comandos (Rhino) é um bom modelo para uma paleta de comandos estilo Ctrl+K em pt-BR, com sinônimos do IFC (por exemplo "parede", "IfcWall", "muro").

### Gaps
- Documentação oficial atual (2026) da entrada dinâmica do AutoCAD e da repetição do último comando (Enter/Espaço): a cota de buscas acabou.
- Repetição do último comando no Revit (Enter) e no Archicad: sem fonte coletada.
- Detalhes atuais do Tracker do Archicad 29 (campos, Tab entre campos, coordenadas polares): as páginas da comunidade Graphisoft retornaram 403.

## 2. Seleção e edição (janela/cruzamento, filtros, selecionar semelhantes, menus contextuais, grips, manipulação direta em 3D, multi-edição de propriedades)

### Takeaway
- **Revit:** seleção por categoria (Filtro) e "Selecionar todas as instâncias" do mesmo tipo, na vista ou no projeto.
- **Archicad:** pet palette para editar nós e arestas, com Info Box contextual.
- **BricsCAD:** o "Quad" junta menu contextual, comando recente e propriedades editáveis direto sob o cursor, e o Manipulator faz mover/girar/escalar/espelhar em 3D.
- **Rhino:** Gumball parecido com o Manipulator, com alinhamento configurável.

### Cited Findings
- No Revit, o botão direito sobre o elemento selecionado oferece **Selecionar todas as instâncias**, visíveis na vista ou no projeto inteiro, filtrando pelo mesmo tipo de família. — [CAD Notes: selectively select objects in Revit](https://www.cad-notes.com/how-to-selectively-select-objects-in-revit/); [IMAGINiT: Options when selecting in Revit](https://resources.imaginit.com/how-tos/options-when-selecting-in-revit)
- O **Filtro** do Revit (aba Modificar) refina a seleção por categoria marcando ou desmarcando caixas. Um blog o critica por funcionar só no nível de categoria. — [Archistar Academy: Filter Selection](https://academy.archistar.ai/using-filter-selection-to-find-objects-in-revit)
- Plugins de terceiros (por exemplo OneFilter) existem para suprir filtros mais finos de seleção no Revit, o que indica uma lacuna nativa. — [DiRoots OneFilter](https://docs.dirootsone.diroots.com/docs/pages/OneFilter/OF-Selections.html)
- **Quad do BricsCAD:**
  - Aparece ao passar o cursor sobre uma entidade (ou com o botão direito no vazio) e serve de alternativa à linha de comando e às barras.
  - Mostra a ferramenta usada por último para aquele tipo de entidade, e o botão direito a relança.
  - Com Rollover Tips, exibe propriedades editáveis ali mesmo: comprimento, inclinação e elevação de arestas, área de faces, perímetro e área de contornos, cor, camada e elevação de sólidos.

  — [Bricsys help: Quad cursor](https://help.bricsys.com/en-us/document/bricscad-bim/getting-started/quad-cursor)
- O **Manipulator** do BricsCAD move, gira, escala e espelha, com opção de copiar. Clicar num eixo move ao longo dele, clicar num plano move no plano. Ele abre pelo Quad ou segurando o botão esquerdo um pouco mais ao selecionar. — [Bricsys help: Basic concepts of modeling (Shape)](https://help.bricsys.com/en-us/document/bricscad-shape/basic-concepts-of-modeling-in-bricscad-shape)
- O **Gumball** do Rhino tem alinhamento CPlane/Objeto/Mundo/Vista, força de arraste e arraste "com snap" ou suave, configuráveis pelo botão direito no painel de status. — [McNeel: The Rhino window](https://docs.mcneel.com/rhino/8/help/en-us/user_interface/rhino_window.htm)
- No Archicad, a pet palette aparece ao clicar num nó ou aresta de um elemento selecionado e oferece operações contextuais. A Info Box mostra os parâmetros da seleção. — [macinteract](https://smart.macinteract.com/?p=2405)

### Inferences
- Um "mini-menu de seleção" sob o cursor, como o Quad, com a última ação para aquele tipo de elemento IFC e 3 a 5 propriedades editáveis (altura, espessura, nível), é coerente com a preferência de UX já registrada no BrasBim: mini-barra de seleção e barra de Opções contextual.
- Para "Selecionar semelhantes", o IFC dá critérios naturais: mesma classe, mesmo IfcTypeObject, mesmo PredefinedType, mesmo material, mesmo andar. Isso vai além do Filtro por categoria do Revit, que recebe críticas.
- Um gizmo 3D ao estilo Gumball/Manipulator, com snap ligado por padrão e entrada numérica durante o arraste, cobriria a manipulação direta em 3D.

### Gaps
- Comportamento de seleção janela/cruzamento (esquerda→direita × direita→esquerda) em cada app: sem fonte nesta rodada, embora seja convenção conhecida no AutoCAD.
- Multi-edição de propriedades com valores "variados" no painel de Propriedades do Revit e nos diálogos do Archicad: sem fonte coletada.

## 3. Navegação (2D/3D, vistas divididas, cubo de vista, caixa de corte, orbitar/pan/zoom, navegador de projeto, abas)

### Takeaway
- **Revit:** navegação centrada no Navegador de Projeto e em vistas nomeadas. A "Selection Box" cria rapidamente uma caixa de corte 3D em volta da seleção, mas sobrescreve a vista 3D padrão.
- **Rhino:** viewports múltiplos com abas, clique no título para ativar sem perder a seleção e duplo clique para maximizar.

### Cited Findings
- A **Selection Box** do Revit (desde 2016) vai para a vista 3D padrão, liga a caixa de corte e a ajusta à extensão dos elementos selecionados. Um blog alerta que isso sobrescreve a vista {3D} padrão, então o usuário precisa duplicá-la para não perdê-la. — [Hagerman: Revit 2016 Selection Box](https://blog.hagerman.com/2015/07/21/revit-2016-selection-box/)
- **Viewports do Rhino:**
  - Clicar no título ativa o viewport sem perder a seleção.
  - Duplo clique maximiza ou restaura.
  - O botão direito no título abre os comandos de vista.
  - Abas embaixo alternam entre vistas.

  — [McNeel: The Rhino window](https://docs.mcneel.com/rhino/8/help/en-us/user_interface/rhino_window.htm)
- No Revit, a vista 3D criada pela Selection Box pode ser renomeada no Navegador de Projeto. — [Hagerman](https://blog.hagerman.com/2015/07/21/revit-2016-selection-box/)

### Inferences
- Um "isolar seleção em 3D com caixa de corte" deve criar uma vista **temporária** ou nova, nunca sobrescrever uma vista do usuário, para evitar a armadilha do Revit.
- O padrão do Rhino (ativar viewport sem perder seleção, duplo clique para maximizar) é barato de implementar em Qt e ajuda a alternar entre 2D e 3D.

### Gaps
- Convenções de mouse para orbitar/pan/zoom em cada app (botão do meio, Shift+meio etc.), detalhes do ViewCube/SteeringWheels, o Navegador do Archicad (mapa de projeto, vistas, layouts, editor) e a navegação "2D/3D lado a lado" do Archicad: a cota de buscas acabou antes desses tópicos.

## 4. Personalização e aprendizado (workspaces, atalhos, ribbon × menus × caixas de ferramentas, descobribilidade, onboarding, ajuda, mensagens de erro, desfazer, acessibilidade)

### Takeaway
As queixas históricas contra o ribbon do Revit são lentidão, ferramentas que mudam de lugar e mais cliques, e elas persistem em relatos de suporte recentes. O Archicad 29 investiu em consistência e redimensionamento de diálogos (sinal de que os diálogos eram ponto fraco) e em modo escuro no macOS. O Rhino e o BricsCAD apostam na linha de comando ou no menu sob o cursor como alternativa ao ribbon.

### Cited Findings
- Usuários do AUGI (2009–2010), na estreia do ribbon no Revit 2010: o ribbon era lento, as ferramentas "mudam de lugar", muitas ficavam escondidas, e havia "muito mais cliques e movimentos de mouse". — [AUGI t-103233](https://forums.augi.com/archive/index.php/t-103233.html); [AUGI t-107877](https://forums.augi.com/archive/index.php/t-107877.html); [AUGI: Application Menu lento](https://forums.augi.com/archive/index.php/t-103032.html)
- Num artigo de suporte da Autodesk (jan/2025), clicar na aba Arquivo do Revit travava o ribbon por 20 a 40 s. A causa eram modelos na lista de arquivos recentes. — [Autodesk Support: Hang-up when clicking the File tab](https://autodesk.com/es/support/technical/article/Hang-up-in-Revit-when-clicking-the-File-Ribbon-Tab)
- Segundo um artigo de suporte de revendedor, usuários novos minimizam o ribbon do Revit sem querer com duplo clique e precisam alternar o estado para recuperá-lo. — [Arkance: Revit Ribbon display issues](https://emea.support.arkance.world/hc/cs/articles/36466380220050-Revit-Ribbon-display-issues)
- Relato de 2012: a aba Modificar do Revit mostrava ferramentas desatualizadas, obrigando a fechar e reabrir o ribbon. — [Fórum Autodesk 2012](https://forums.autodesk.com/t5/revit-architecture-forum/revit-architecture-2012-edit-boundary-ribbon-issue/m-p/3330457/highlight/true)
- **Archicad 29:**
  - Vários diálogos ficaram mais consistentes em tamanho e layout, e vários podem ser redimensionados na horizontal.
  - Os botões de Canetas e Cores foram alinhados aos demais atributos.
  - O macOS ganhou modo escuro.
  - Um resumo de novidades cita assistente de IA embutido, atalho Ctrl/Cmd+R para girar elementos e colocação de aberturas em cortes e elevações.

  — [Graphisoft Help AC29 (pt-BR): Redimensionamento e atualização da interface de várias caixas de diálogo](https://help.graphisoft.com/AC/29/BRA/_AC29_Help/005_NewFeatures/005_NewFeatures-15.htm); [Comunidade Graphisoft: Archicad 29 – A glance at the new features](https://community.graphisoft.com/t5/Getting-started/Archicad-29-A-Glance-at-the-New-Features/ta-p/672706) (só via resumo de busca, a página deu 403)
- No Revit, atalhos de duas letras forçam snaps (SE extremidade, SC centro). — [Autodesk: About Snaps 2026](https://help.autodesk.com/cloudhelp/2026/ENU/Revit-Customize/files/GUID-A3947840-1F30-41D7-AF75-B61687952A07.htm); [Fórum Autodesk](https://forums.autodesk.com/t5/revit-architecture-forum/wall-dimensions/m-p/6051118/highlight/true)
- A Bricsys apresenta o Quad como alternativa compacta à linha de comando e às barras de ferramentas. As abas do Quad mudam conforme a entidade e o workspace. — [Bricsys help: Quad cursor](https://help.bricsys.com/en-us/document/bricscad-bim/getting-started/quad-cursor)

### Inferences
- Ribbon com abas contextuais que "trocam de lugar" é uma fonte documentada de frustração. Barras fixas e previsíveis, mais uma barra de Opções contextual (que muda o *conteúdo*, não a *posição*), mais uma paleta de comandos com busca, tendem a ser mais rápidas e descobríveis.
- Diálogos grandes e modais aparecem como ponto fraco (o próprio fornecedor do Archicad gastou uma versão em consistência de diálogos). Painéis não modais e acopláveis com edição imediata são preferíveis.
- Snaps "por sessão, não salvos no projeto" (Revit) é decisão razoável: preferências do usuário ficam fora do IFC.

### Gaps
- Onboarding (tutoriais in-app, dicas), qualidade das mensagens de erro, modelo de desfazer (por exemplo, desfazer de mudanças de vista) e acessibilidade (leitor de tela, contraste, teclado) dos três produtos: nenhuma fonte coletada antes do fim da cota de buscas.
- Workspaces e personalização de atalhos (CUI do AutoCAD, Work Environment do Archicad, Keyboard Shortcuts do Revit): sem fonte nesta rodada.

## 5. Desempenho percebido, travamentos e salvamento automático

### Takeaway
O Revit não tem salvamento automático nativo de verdade, só um lembrete de salvar e arquivos de recuperação em parte das falhas. Isso gera relatos de horas de trabalho perdidas e pedidos antigos de "Autosave Local". Os travamentos de UI documentados vêm de E/S síncrona (lista de recentes).

### Cited Findings
- Fórum Autodesk: um usuário perdeu horas de trabalho depois de ignorar lembretes de salvar no Revit 2017. O journal mostrou que os lembretes pararam no meio do dia e que a sincronização com o arquivo central travou o programa. — [Fórum Autodesk: Where did the Save reminders go?](https://forums.autodesk.com/t5/revit-architecture-forum/where-did-the-save-reminders-go/m-p/8022323)
- Usuários do Revit relatam que ele costuma oferecer arquivo de recuperação na maioria das falhas, mas não nas graves. Recuperar pelo journal foi considerado impraticável (arquivo enorme). — [Fórum Autodesk (mesmo tópico)](https://forums.autodesk.com/t5/revit-architecture-forum/where-did-the-save-reminders-go/m-p/8653541)
- A ideia "Autosave Local" no Revit Ideas pede salvamento automático em segundo plano, só das mudanças desde o último save/sync, com frequência configurável e opção de desligar. — [Revit Ideas: Autosave Local](https://forums.autodesk.com/t5/revit-ideas/autosave-local/idi-p/6567074)
- Existem add-ins de terceiros de autosave para o Revit. Um consultor diz salvar a cada cerca de 20 minutos por hábito. — [Arkance: Revit AutoSave Add-in](https://emea.support.arkance.world/hc/cs/articles/36465177610130-Revit-AutoSave-Add-in)
- Um artigo de suporte da Autodesk (2025) documenta o congelamento de 20 a 40 s na aba Arquivo do Revit ligado a arquivos recentes. — [Autodesk Support](https://autodesk.com/es/support/technical/article/Hang-up-in-Revit-when-clicking-the-File-Ribbon-Tab)

### Inferences
- O BrasBim já tem autosave e recuperação (spec/ui 21). Esse é um diferencial real contra o Revit e vale destacar. Salvar incrementalmente, sem bloquear a UI, atende exatamente ao pedido "Autosave Local".
- Toda E/S (lista de recentes, miniaturas, links) deve sair da thread da UI. Os travamentos do Revit mostram o custo de não fazer isso.

### Gaps
- Se o Revit 2026/2027 introduziu autosave nativo: não verificado.
- Percepções de lentidão de regeneração no AutoCAD e de geração de vistas no Archicad (por exemplo, atualização de cortes): sem fonte coletada.

## 6. Estudos de usabilidade/HCI comparando ferramentas BIM e queixas de UI

### Takeaway
A literatura acadêmica encontrada é fraca para usabilidade de interação. Os comparativos Archicad × Revit são, em geral, matrizes de critérios ponderados ou levantamentos de percepção, não testes controlados com tarefas e SUS. Não achei estudo com participantes que meça tempo de tarefa entre Archicad, Revit e AutoCAD.

### Cited Findings
- Alfalah (2021/2022) compara Archicad e Revit do ponto de vista arquitetônico e de satisfação do usuário, usando média ponderada de fatores tirados da literatura. Há duas versões com títulos parecidos (uma na revista NVEO, vol. 8, n. 5, p. 4268–4277). Não consegui abrir o resumo completo (conexão recusada). — [KSU faculty: An Extensive Comparison between ArchiCAD and Revit](https://fac.ksu.edu.sa/en/galfalah/publication/388743); [KSU faculty pub. 360084](https://faculty.ksu.edu.sa/ar/galfalah/publication/360084)
- Kim (2014, Coreia) comparou Revit e Archicad no projeto preliminar. O Revit saiu melhor em estudo de massa e alternativas, o Archicad em programa de espaços, e nenhum dos dois atendia bem a estudos de normas. — [earticle A241646](https://www.earticle.net/Article/A241646)
- Um levantamento com 227 estudantes e profissionais iniciantes (Mimar Sinan, Turquia) sobre facilidade de uso percebida e utilidade de ferramentas BIM concluiu que ter feito treinamento de certificação BIM foi o fator mais influente. — [MSGSÜ repositório](https://acikerisim.msgsu.edu.tr/xmlui/handle/20.500.14124/10357?show=full)
- Um artigo de Loughborough defende abordagens formais de usabilidade para aplicações BIM, envolvendo partes interessadas multidisciplinares. — [Loughborough: Towards formal usability approach for BIM applications](https://repository.lboro.ac.uk/articles/conference_contribution/Towards_formal_usability_approach_for_BIM_applications/9401126)
- O SUS é um questionário de 10 itens em escala de 1 a 5, tratado como "padrão de fato" embora nunca tenha sido formalmente padronizado. — [UXPA: SUS – A Retrospective](https://uxpa.org/?p=3799)

### Inferences
- A falta de testes controlados é uma oportunidade: o BrasBim pode publicar o próprio benchmark aberto, com tarefas padrão (por exemplo, "parede de 5,00 m a 30° partindo de um canto existente", "selecionar todas as portas do pavimento 2 e mudar a largura"), medindo tempo, cliques e SUS. É também uma forma de comprovar a meta "mais rápido que os três".
- O dado turco sugere que a facilidade percebida depende muito de treinamento. Onboarding embutido (dicas contextuais, tutoriais curtos) pode ter impacto desproporcional.

### Gaps
- Artigos do ITcon / Automation in Construction com testes de tarefas: não foi possível buscar (cota esgotada).
- Queixas recentes (2024–2026) no Reddit (r/Revit, r/ArchiCAD, r/AutoCAD): nenhuma thread coletada. Os resultados vieram de fóruns antigos (AUGI) e do fórum da Autodesk.
- Apps de AEC "tipo Figma" (Arcol, Snaptrude, Autodesk Forma, Motif) e Vectorworks: não pesquisados por falta de cota.
