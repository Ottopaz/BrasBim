# Revit: ferramentas de modelagem e sistema de famílias (versões 2025, 2026 e 2027)

> Pesquisa clean-room feita em 2026-10-21. Só fontes públicas da web. Os textos são resumos em palavras próprias. Nomes de comandos aparecem só para identificar o recurso. **Todas as fontes têm data de acesso 2026-10-21.**
> Ressalvas de método:
> - Várias páginas oficiais deram erro de acesso: o blog da Autodesk de 2026 e o quadro Revit Ideas responderam HTTP 403, e o wiki revit.miraheze respondeu 503.
> - Por isso parte dos dados vem de blogs de revendas (BIMpure, Symetri, Arkance) e de páginas antigas da Ajuda da Autodesk, de 2014 a 2020.
> - O comportamento atual pode ser diferente. Itens sem fonte foram para "Lacunas".

## Paredes, pisos, coberturas, forros, pilares, escadas, guarda-corpos, rampas, aberturas, ambientes, terreno e massas

### Takeaway
Nas versões 2025 a 2027, a modelagem do Revit mudou em quatro frentes:
- **Toposolid** (terreno sólido): ganhou ferramenta de escavação, subdivisões rebaixadas e snaps em Z.
- **Estruturas compostas:** passaram a aceitar elementos sem camada de núcleo e uma prioridade de camada separada da função.
- **Criação de paredes:** ganhou modos "por ambiente" e "por segmento", e na 2027 paredes hospedadas em outras paredes (revestimentos).
- **Interface:** a barra de opções migrou para a faixa de opções (ribbon).

Escadas e guarda-corpos são montados por componentes (lances, patamares, suportes). Os usuários reclamam muito deles, sobretudo de guarda-corpos de vidro e de escadas fora do padrão.

### Cited Findings

**Paredes: estrutura composta, empilhadas, frisos e rebaixos**
- Frisos (sweeps) e rebaixos (reveals) podem ser definidos no tipo de parede, na edição da montagem. Assim valem para todas as instâncias daquele tipo. — [Autodesk Help 2014, Sweeps and Reveals Tools](https://help.autodesk.com/cloudhelp/2014/ENU/Revit/files/GUID-75E875FB-C31C-4D02-8500-273CBBA91CB4.htm). Retirado: onde se configuram frisos e rebaixos.
- Parâmetros de um friso ou rebaixo no tipo de parede:
  - perfil e material;
  - distância medida a partir do topo ou da base;
  - lado (interno ou externo) e deslocamento;
  - espelhar;
  - recuo junto a portas e janelas;
  - se corta ou não a parede hospedeira.

  — [Autodesk Help 2014, Sweeps and Reveals Tools](https://help.autodesk.com/cloudhelp/2014/ENU/Revit/files/GUID-75E875FB-C31C-4D02-8500-273CBBA91CB4.htm). Retirado: a lista de parâmetros.
- Parede composta na vertical: o tipo é dividido em camadas e em regiões verticais. As linhas de locação do núcleo são definidas pela espessura do núcleo na base da parede. — [Autodesk Help 2014, Working with Compound Walls](https://help.autodesk.com/cloudhelp/2014/ENU/Revit/files/GUID-91584C23-7FB5-46DD-82D1-48F36F3B4804.htm). Retirado: o conceito de região e a regra do núcleo.
- Relato antigo, de 2007: frisos, rebaixos e camadas divididas não funcionam em faces não verticais, ou seja, em paredes inclinadas ou curvas em perfil. — [AUGI forum (2007)](https://forums.augi.com/archive/index.php/t-63363.html). Retirado: a limitação. Pode estar desatualizado.
- Na API, o friso de uma estrutura composta vertical é marcado como "fixo". A classe WallSweepInfo expõe distância, lado da parede e se o friso corta a parede. — [rvtdocs.com, WallSweepInfo 2025](https://rvtdocs.com/2025/Autodesk.Revit.DB.WallSweepInfo). Retirado: o modelo de dados do friso.
- **Novidades da 2025:**
  - Ícone para ligar ou desligar o "envolvimento" (wrap) das camadas em cada extremidade da parede. Não vale para o envolvimento junto a aberturas.
  - Opções "Auto Join" e "Auto Join & Lock": paredes de acabamento encostadas são unidas automaticamente, e as aberturas cortam todas. A segunda opção também cria uma restrição de travamento. O autor alerta que muitas restrições deixam o projeto lento.

  — [BIMpure, Revit 2025](https://www.bimpure.com/blog/revit-2025). Retirado: envolvimento por extremidade e união automática.
- **Novidades da 2026:**
  - Paredes, pisos, forros e coberturas podem não ter camada de núcleo. Isso ajuda em variações de acabamento e em uniões mais limpas.
  - Nova coluna "Priority" define a prioridade da camada, independente da função. É ela que governa uniões e a limpeza gráfica.

  — [BIMpure, Revit 2026](https://www.bimpure.com/blog/revit-2026); [Microsol Resources, What's New with Revit 2026](https://microsolresources.com/?p=16900). Retirado: elementos sem núcleo e prioridade de camada.
- **Novos modos de criar paredes (2026):**
  - "Walls by Room": cria paredes em todo o perímetro de um ambiente selecionado. A tecla Tab alterna entre incluir ou não os pilares.
  - "Walls by Segment": cria paredes clicando em segmentos individuais.

  — [BIMpure, Revit 2026](https://www.bimpure.com/blog/revit-2026). Retirado: os dois modos.
- **Revit 2027, paredes hospedadas em paredes:**
  - Ao criar a parede, escolhe-se "Hosted Wall" e clica-se numa parede hospedeira. Com união automática ligada, as aberturas cortam a parede nova e as linhas se limpam.
  - Pela faixa de opções dá para trocar o hospedeiro, desfazer a hospedagem e aplicar um deslocamento. Deslocamentos acima de cerca de 152 mm (6") fazem a parede deixar de receber o corte das aberturas.
  - Limitação: a parede hospedada não entra na espessura total da parede. Por isso caixilhos e guarnições podem conflitar com ela.

  — [BIMpure, Revit 2027](https://www.bimpure.com/blog/revit-2027). Retirado: o fluxo, o limite de deslocamento e a limitação.
- **Revit 2027, outras mudanças em paredes:**
  - A barra de opções sumiu. "Place by Room" e "Place by Segment" ficam junto das ferramentas de esboço e de "By Face".
  - A hospedagem substitui o "Auto Join & Lock".
  - O deslocamento em relação ao hospedeiro representa uma câmara de ar, e a parede acompanha o hospedeiro quando ele se move.
  - Há escolha do lado (interno ou externo) e a propriedade "Room Bounding" pode ser ajustada na criação.

  — [Symetri, What's New in Revit Architecture 2027](https://www.symetri.co.uk/insights/blog/what-s-new-in-revit-architecture-2027-a-guide-to-the-latest-features/). Retirado: os detalhes do fluxo.
- Na 2027, as opções de criação de paredes e escadas saíram da barra de opções e foram para a faixa de opções. Com isso termina uma migração que vinha de versões anteriores. — [BIMpure, Revit 2027](https://www.bimpure.com/blog/revit-2027).

**Pisos e coberturas**
- Cobertura por perímetro (footprint): cada aresta do esboço pode ser marcada como "define inclinação" e ter seu próprio valor. A inclinação se ajusta pelas Propriedades ou na área de desenho. — [Autodesk Help 2020, Video: Create a Sloped Roof](https://help.autodesk.com/cloudhelp/2020/ENU/RevitLT-Model/files/GUID-04327676-8E4D-4AF1-A550-3FB72CF3EDA6.htm); [CAD-Notes, Creating complex roof in Revit](https://www.cad-notes.com/creating-complex-roof-in-revit/). Retirado: as arestas que definem inclinação.
- Seta de inclinação (slope arrow):
  - Antes de usá-la, é preciso desmarcar "define inclinação" nas arestas envolvidas. Senão aparece erro de conflito.
  - A seta recebe altura ou inclinação nas Propriedades.
  - É usada para águas furtadas e oitões de quatro lados.

  — [Autodesk Help 2020, Create a Roof Slope Using Slope Arrows](https://help.autodesk.com/cloudhelp/2020/ENU/Revit-Model/files/GUID-98A54E99-6889-4BA6-8483-CE67990A49C7.htm); [CAD-Notes](https://www.cad-notes.com/creating-complex-roof-in-revit/). Retirado: o fluxo e o erro.
- Para coberturas complexas, a recomendação é modelar cada massa de telhado separada e uni-las com "Join/Unjoin Roof". Isso facilita a edição depois. — [Novedge, Modeling Complex Roofs](https://novedge.com/blogs/design-news/revit-tip-modeling-complex-roofs-with-roof-by-footprint-in-revit). Retirado: a boa prática.
- Na 2026 dá para copiar e colar pontos e linhas ao editar toposolids, coberturas e pisos. — [BIMpure, Revit 2026](https://www.bimpure.com/blog/revit-2026).

**Fachada-cortina (curtain wall e curtain system)**
- Os montantes ficam hospedados nas linhas de grade da cortina. Por isso a grade deve ser definida primeiro. Montantes podem ir em todas as linhas ou em segmentos isolados. — [Novedge, Strategic Curtain Wall Mullion Placement](https://novedge.com/blogs/design-news/revit-tip-strategic-curtain-wall-mullion-placement-in-revit). Retirado: a ordem de trabalho.
- "Curtain systems" e superfícies divididas servem para faces de massa e geometria complexa. A parede-cortina comum serve para fachadas ortogonais. — [Novedge, Curtain Panel and Patterning Workflow](https://novedge.com/blogs/design-news/revit-tip-curtain-panel-and-patterning-workflow-for-scheduleable-facades). Retirado: quando usar cada um.
- Em faces planas, aplicar "Curtain System" direto na face da massa é mais robusto. O espaçamento da grade vale para o sistema todo, e segmentos podem ser adicionados com a ferramenta de grade. — [Autodesk forum, Curtain system from mass](https://forums.autodesk.com/t5/revit-architecture-forum/curtain-system-from-mass-horizontal-segments/m-p/6803334/highlight/true).
- Problemas relatados com cortina sobre massa:
  - montantes duplicados nas juntas;
  - grade que "abre em leque" em faces curvas;
  - montantes de canto que falham entre face curva e parede reta.

  — [AUGI (2010), Mullions on Mass](https://forums.augi.com/archive/index.php/t-114992.html); [Autodesk forum, grid rotation on mass](https://forums.autodesk.com/t5/revit-architecture-forum/curtain-system-grid-rotation-on-mass/m-p/6831711); [AUGI (2009), Corner Mullion Limitation](https://forums.augi.com/archive/index.php/t-100295.html). Fóruns antigos.
- Na 2025, o perfil de montante pode ter vários laços (loops), aninhados ou desconectados. Todos os laços de um mesmo perfil usam o mesmo material. — [BIMpure, Revit 2025](https://www.bimpure.com/blog/revit-2025).

**Escadas e guarda-corpos**
- Escada por componentes: montada com lances, patamares, suportes e guarda-corpos, que podem ser gerados automaticamente ou colocados depois. Formas de criar patamares:
  - automaticamente entre lances;
  - escolhendo dois lances;
  - por esboço personalizado.

  — [Autodesk Help 2014, Stair by Component](https://help.autodesk.com/cloudhelp/2014/ENU/Revit/files/GUID-B1B305DF-8DBE-44A7-A7C6-16B70A3B580E.htm). Retirado: a composição da escada.
- Opções da ferramenta de lance:
  - "Patamar automático" vem ligado. Dois lances separados até o próximo nível geram um patamar entre eles.
  - Largura real do lance, sem contar os suportes.
  - Linha de locação (por exemplo, centro do lance) com deslocamento lateral.

  — [Autodesk Help 2020, Select the Run Component Tool](https://help.autodesk.com/cloudhelp/2020/ENU/Revit-Model/files/GUID-26053199-6B08-44B9-907C-F5D9AA7CEC81.htm). Retirado: as opções.
- Guarda-corpo da escada:
  - É criado por padrão com o lance, mas pode-se escolher "nenhum".
  - Pode ficar sobre os degraus ou sobre a longarina.
  - Só aparece depois de sair do modo de edição da montagem da escada.

  — [Autodesk Help 2020, Run Component Tool](https://help.autodesk.com/cloudhelp/2020/ENU/Revit-Model/files/GUID-26053199-6B08-44B9-907C-F5D9AA7CEC81.htm).
- Na 2027, a numeração de degraus e espelhos usa parâmetros de tipo:
  - fonte, cor e estilo separados acima e abaixo da linha de corte;
  - tipos duplicados dão estilos diferentes;
  - entra no "Tag All Not Tagged".

  — [Symetri 2027](https://www.symetri.co.uk/insights/blog/what-s-new-in-revit-architecture-2027-a-guide-to-the-latest-features/); [BIMpure, Revit 2027](https://www.bimpure.com/blog/revit-2027).

**Toposolid, terreno e implantação**
- **Revit 2025:**
  - Ferramenta "Excavate": escava um toposolid com piso, plataforma (building pad), cobertura ou outro toposolid, sem modelar vazios. Aceita vários elementos escavadores.
  - O volume escavado vira um parâmetro agendável do elemento que corta ("Excavation Volume on Toposolid"). Existe o comando para desfazer a escavação.
  - Snap em Z durante a edição de pontos, com deslocamento (por exemplo, 3 pés abaixo do topo de uma parede). Há um controle à parte para o snap nos pontos e cristas do próprio terreno.
  - A conversão de toposurface antiga para toposolid passou a incluir as plataformas. Para isso a toposurface original precisa ser mantida.
  - Shaft corta o toposolid só até o fundo do shaft.
  - Sombreamento suave, apenas visual.
  - Toposolid a partir de face de massa, com curvas de nível.
  - Famílias baseadas em face reconhecem as faces cortadas (por exemplo, árvores dentro de cavas).

  — [BIMpure, Revit 2025](https://www.bimpure.com/blog/revit-2025). Retirado: todos esses itens.
- **Revit 2026:**
  - Subdivisões aceitam deslocamento negativo (rebaixo), o que serve para vias e lagos.
  - Subdivisões podem receber um tipo de toposolid, não só um material.
  - Subdivisões viraram subcategoria do toposolid. Assim aparecem em visibilidade, filtros, tabelas e exportação.
  - A conversão de toposurface gera subdivisões rebaixadas a partir das sub-regiões.
  - Cálculo de corte e aterro mais preciso.
  - Opção "Cut Void Stability" para melhorar o sucesso dos booleanos.
  - O limite padrão de pontos subiu de 10.000 para 20.000, configurável até 50.000 no Revit.ini.

  — [BIMpure, Revit 2026](https://www.bimpure.com/blog/revit-2026); [Microsol Resources, Revit 2026](https://microsolresources.com/?p=16900). Retirado: esses itens. O limite de pontos vem da Microsol.
- Revit 2027: o "Forma Connected Client" entrou como prévia de tecnologia. Ele vincula terreno e edifícios do entorno vindos do Forma e roda análise de vento. — [Symetri, What's New in Revit 2027](https://www.symetri.co.uk/insights/blog/what-s-new-in-revit-2027-a-guide-to-the-latest-features/) (snippet de busca). Retirado: a existência do recurso.

**Ambientes, numeração e opções de projeto**
- Na 2025, o perímetro do ambiente passou a incluir os laços internos. — [BIMpure, Revit 2025](https://www.bimpure.com/blog/revit-2025).
- Na 2027 chegou a numeração por regras: a "Mark" de instância é preenchida por critérios como nível, departamento, ambiente ou tipo (por exemplo, número da porta conforme o ambiente). Elementos novos seguem a regra automaticamente. — [BIMpure, Revit 2027](https://www.bimpure.com/blog/revit-2027).
- Opções de projeto na 2027:
  - Vistas atribuídas a uma opção não podem ser selecionadas no modelo principal sem ativar a opção.
  - Os botões "Active Only" e "Exclude Options" persistem durante a sessão.

  — [BIMpure, Revit 2027](https://www.bimpure.com/blog/revit-2027).

### Inferences
- A Autodesk está levando para dentro do produto recursos que antes exigiam gambiarras ou add-ins: paredes de revestimento hospedadas, escavação de terreno, subdivisões rebaixadas e numeração por regras. Para o BrasBim, revestimento como camada ou objeto ligado à parede e numeração automática são requisitos de base, não diferenciais.
- A separação entre função e prioridade de camada, mais a possibilidade de não ter núcleo, indica que o modelo rígido "núcleo + camadas" do Revit não dava conta. No IFC, IfcMaterialLayerSet com prioridade explícita (o IFC4 tem o atributo Priority em IfcMaterialLayer) oferece uma base natural.
- A limitação de 2027 (a parede hospedada não soma na espessura para caixilhos) mostra o risco de modelar revestimento como objeto separado. Vale cuidar de como aberturas e caixilhos "enxergam" a espessura total.

### Gaps
- Faltaram fontes atuais sobre:
  - forros e pilares ou vigas estruturais;
  - rampas;
  - aberturas (shaft, em parede, em face);
  - áreas;
  - massas conceituais e componentes in-place.
- Não foram consultados os detalhes de "Modify Sub Elements" (edição de forma de piso), o anexar topo/base de paredes e a edição de perfil de parede. A página oficial da Ajuda 2026 não foi acessada nesse ponto.
- Sobre a estrutura do guarda-corpo (trilhos, padrão de balaústres), há só referência indireta.
- Não consegui acessar a página oficial "What's New in Revit 2026" da Autodesk (HTTP 403).

## Sistema de famílias

### Takeaway
As famílias do Revit se dividem em três grupos:
- **de sistema:** paredes, pisos e outros, definidas no projeto;
- **carregáveis:** arquivos .rfa, criados no Editor de Famílias a partir de modelos (templates) por categoria;
- **in-place:** feitas dentro do projeto.

A parametrização usa:
- **parâmetros:** de tipo ou de instância, de família, compartilhados (arquivo de texto externo), de projeto e globais;
- **fórmulas;**
- **tabelas de consulta (lookup) em CSV;**
- **catálogos de tipos.**

Nas versões recentes houve poucas mudanças diretas no Editor de Famílias.

### Cited Findings
- Tabelas de consulta guardam dados de muitos tamanhos de peça sem criar um tipo de família para cada um. A função `size_lookup` lê valores de um CSV, e a página diz que ela se destina a parâmetros de instância. Para dados tabulares com valores únicos por tipo, a recomendação é usar catálogo de tipos. — [Autodesk Help 2026, Lookup Tables (Revit-Customize)](https://help.autodesk.com/cloudhelp/2026/ENU/Revit-Customize/files/GUID-91270AEF-225A-49D7-BF84-1F44D1E3E216.htm) (conteúdo visto via snippet de busca). Retirado: o propósito, `size_lookup` e a relação com catálogos.
- A tabela de consulta é importada para dentro da família por um diálogo de importação e exportação e referenciada por um parâmetro de texto. — [AUGI, Lookup Tables: A Formula for Success](https://augi.com/articles/detail/lookup-tables-a-formula-for-success).
- Catálogos de tipos só controlam parâmetros de família, não de projeto. Há exemplo de fórmula que dimensiona o colarinho de um difusor a partir da vazão. — [AUGI, Revit formulas v. type catalogs v. lookup tables](https://augi.com/articles/detail/revit-formulas-v.-type-catalogs-v.-lookup-tables).
- Parâmetros globais pertencem a um único projeto e não são atribuídos a categorias. Guardam valores simples ou resultados de equações, e um mesmo global pode controlar várias cotas não adjacentes. — [ATG USA, Types of Revit Parameters](https://atgusa.com/types-of-revit-parameters/). Retirado: a definição.
- Parâmetros compartilhados ficam num arquivo externo e são reutilizáveis entre famílias e projetos. São necessários para etiquetar, entrar em tabelas multicategoria e exportar para IFC ou COBie. Um exemplo: para "Espessura" aparecer numa só coluna da tabela vindo de duas famílias de sapata, ela tem de ser compartilhada nas duas. — [ATG USA](https://atgusa.com/types-of-revit-parameters/); [Novedge, Shared Parameter Standards and Governance](https://novedge.com/blogs/design-news/revit-tip-revit-shared-parameter-standards-and-governance).
- Parâmetros de projeto valem para um projeto e podem abranger várias categorias. — [ATG USA](https://atgusa.com/types-of-revit-parameters/).
- Na 2025, matrizes (arrays) com 0 ou 1 elemento deixaram de quebrar a família. O editor mostra linhas de prévia cinza que ficam invisíveis no projeto. Isso só vale dentro de famílias. — [BIMpure, Revit 2025](https://www.bimpure.com/blog/revit-2025). Retirado: o fim de uma limitação antiga.
- Na 2026, parâmetros compartilhados de instância podem ser adicionados a marcadores de vista (chamada, elevação, corte). — [BIMpure, Revit 2026](https://www.bimpure.com/blog/revit-2026).
- Na 2027:
  - O mapeamento de propriedades para exportação IFC passou a ser feito por menu, sem arquivo de texto.
  - Materiais ganharam um ativo de carbono com valores EC3.
  - "Extended Properties" trazem parâmetros de modelos de coordenação e do ACC.

  — [BIMpure, Revit 2027](https://www.bimpure.com/blog/revit-2027).
- Ferramentas de terceiros (Family Type Manager) existem para editar em lote catálogos e tabelas, o que mostra uma lacuna nativa. Os anúncios indicam compatibilidade antiga (2019 a 2024). — [Autodesk Marketplace, Family Type Manager Pro](https://marketplace.autodesk.com/apps/fa54d43e-edd8-4fba-959f-18d986792227).

### Inferences
- O BrasBim pode oferecer o equivalente a famílias com parâmetros, fórmulas e catálogos usando tipos IFC (IfcTypeObject com PropertySets), o que já é nativo em IFC. Tabelas de consulta poderiam ser CSV ligados ao tipo, sem precisar de um "editor de famílias" separado para casos simples.
- A obrigação de usar parâmetros "compartilhados" com GUID para etiquetar ou exportar é um atrito típico do Revit. Num app IFC-nativo, Psets padronizados (e Psets nacionais ABNT) resolvem isso de saída.

### Gaps
- Não obtive fontes atuais e confiáveis sobre:
  - componentes adaptativos (pontos adaptativos, padrões em superfícies divididas);
  - famílias aninhadas e "compartilhadas";
  - parâmetros de visibilidade e tipos de família;
  - a lista de modelos e categorias;
  - sintaxe completa de fórmulas (if, and, or, round etc.).

  O wiki revit.miraheze deu 503.
- Não consegui uma lista de ideias mais votadas sobre o Editor de Famílias (quadro Revit Ideas com HTTP 403).

## Modelo de interação: cotas temporárias, alinhamento, snaps, planos de trabalho e ferramentas de modificação

### Takeaway
A interação gira em torno de quatro mecanismos:
- cotas temporárias editáveis, com troca de referência pela tecla Tab ou por controle na linha de chamada;
- alinhamento com cadeado, que cria restrições paramétricas;
- cotas permanentes com trava e igualdade (EQ);
- Propriedades e seletor de tipo.

Nas versões 2026 e 2027, as opções de criação saíram da barra de opções e foram para a faixa de opções contextual.

### Cited Findings
- Cotas temporárias:
  - A tecla Tab percorre as referências possíveis quando a linha de chamada pega o alvo errado.
  - Um pequeno controle junto à linha de chamada alterna entre referências, por exemplo face acabada ou núcleo da parede.
  - Arrastar as alças azuis troca o alvo.

  — [Novedge, Master Revit Modeling with Temporary Dimensions](https://novedge.com/blogs/design-news/revit-tip-master-revit-modeling-with-temporary-dimensions); [Novedge, Convert Temporary Dimensions to Persistent Constraints](https://novedge.com/blogs/design-news/revit-tip-convert-temporary-dimensions-to-persistent-constraints-in-revit).
- A ferramenta Alinhar (AL), com clique no cadeado, cria uma restrição paramétrica. A recomendação é travar em planos de referência, não em arestas de geometria, porque as arestas são menos estáveis. — [Novedge, Efficient Use of Constraints](https://novedge.com/blogs/design-news/revit-tip-efficient-use-of-constraints-and-dimensions-in-revit-for-accurate-bim-modelling); [Novedge, Preserve Design Intent](https://novedge.com/blogs/design-news/revit-tip-preserve-design-intent-with-deliberate-revit-constraints).
- Cota permanente travada fixa a distância entre as referências e precisa ser destravada para mudar o valor. A igualdade de espaçamento se faz ligando "EQ" na cadeia de cotas. — [Autodesk Help 2014, Locking Permanent Dimensions](https://help.autodesk.com/cloudhelp/2014/ENU/Revit/files/GUID-BD91C1BE-4FBC-41F0-AC82-5C60A545EAC6.htm).
- Na 2025, o toposolid ganhou snaps em Z com deslocamento durante a edição de pontos. — [BIMpure, Revit 2025](https://www.bimpure.com/blog/revit-2025).
- Na 2027, as configurações de criação de paredes e escadas foram para a faixa de opções, encerrando a migração da barra de opções. — [BIMpure, Revit 2027](https://www.bimpure.com/blog/revit-2027); [Symetri 2027](https://www.symetri.co.uk/insights/blog/what-s-new-in-revit-architecture-2027-a-guide-to-the-latest-features/).
- Na 2025 entrou o alinhamento e a distribuição uniforme de textos, etiquetas e notas-chave, que não funciona em elementos 3D. — [BIMpure, Revit 2025](https://www.bimpure.com/blog/revit-2025).
- Na 2027 chegou o "Autodesk Assistant", em linguagem natural (consultas ao modelo, geração de vistas e folhas). As avaliações são mistas: um testador viu a maioria das tarefas falhar, e análises posteriores relatam melhora nas versões 2027.1 e 2027.2. — Snippets de busca de [BIMpure, Top 5 features 2027.1/2027.2](https://www.bimpure.com/blog/top-5-new-features-in-revit-2027-1-and-revit-2027-2) e [Autodesk blog 2027.1](https://www.autodesk.com/blogs/aec/2026/06/16/whats-new-in-revit-2027-1/). Não lido na íntegra.

### Inferences
- O conjunto "cota temporária editável + troca de referência + cadeado" é o coração da precisão no Revit. O BrasBim tem duas vias para oferecer algo equivalente: entrada numérica direta durante o desenho e escolha da referência (face acabada, núcleo, eixo).
- A migração da barra de opções para a faixa contextual confirma a direção de uma barra de opções contextual compacta, que já está nas preferências de UX do projeto.

### Gaps
- Não encontrei fontes atuais sobre:
  - planos de trabalho (definir, mostrar, escolher linha);
  - filtro de seleção e IDs de elemento (selecionar por ID);
  - snaps em geral;
  - ferramentas Offset, Trim/Extend, Split, Array e Mirror.

  São comportamentos conhecidos do produto, mas ficaram sem citação nesta rodada.

## Limitações conhecidas e reclamações frequentes

### Takeaway
As reclamações mais citadas são:
- escadas pouco intuitivas, que é preciso refazer ao mudar as regras de cálculo;
- guarda-corpos de vidro e uniões de corrimão difíceis;
- elementos fora do padrão (laje ou parede afunilada, escada apoiada em viga) que exigem famílias in-place ou massas;
- fragilidade da cortina sobre massas;
- ausência nativa de edição em lote de catálogos e tabelas.

### Cited Findings
- No Revit Ideas, um comentário chama a ferramenta de escadas de uma das menos intuitivas do Revit: ao mudar as regras de cálculo, é preciso apagar e refazer a escada, quando ela deveria se atualizar sozinha. — [Autodesk Revit Ideas, Structural stairs and railings families](https://forums.autodesk.com/t5/revit-ideas/structural-stairs-and-railings-families/idc-p/10979430) (via snippet).
- Famílias de guarda-corpo de vidro nativas costumam ter largura fixa. A gambiarra com parede-cortina não funciona em escadas, e condições complexas exigem família personalizada. — [Autodesk forum, Glass railing for stairs?](https://forums.autodesk.com/t5/revit-architecture-forum/glass-railing-for-stairs/td-p/13731552); [Autodesk forum, railings with glass panels](https://forums.autodesk.com/t5/revit-architecture-forum/how-do-you-model-railings-with-glass-panels/td-p/11263558).
- Avisos de "referência superior abaixo da inferior" em balaústres de vidro no patamar. A solução é dividir o guarda-corpo em várias peças e tipos. — [AUGI (2014), railing at landing](https://forums.augi.com/archive/index.php/t-156716.html).
- Relatos antigos de corrimão contínuo que não se une bem e de longarina que não desce até a laje. — [AUGI (2006)](https://forums.augi.com/archive/index.php/t-52531.html).
- Escada apoiada em viga pode levar horas de tentativa e erro. Afunilar laje ou parede exige família in-place ou massa. — [Graphisoft Community (post de usuário sobre o Revit)](https://community.graphisoft.com/t5/Modeling/What-do-you-think-should-be-done-to-get-Archicad-a-bigger-market/td-p/285226/page/15). Opinião de usuário.
- Pedido no Revit Ideas: editar uma família "como nova" sem precisar salvar antes. — [Revit Ideas, Family Edit as New](https://forums.autodesk.com/t5/revit-ideas/family-edit-as-new/idc-p/10348849).
- O pedido de ocultar cotas ou extrusões específicas no Editor de Famílias foi arquivado por falta de votos. — [Revit Ideas, Hide in View in family editor](https://forums.autodesk.com/t5/revit-ideas/hide-in-view-in-family-editor/idi-p/6563696).
- Muitas restrições de travamento ("Auto Join & Lock") deixam o projeto lento. — [BIMpure, Revit 2025](https://www.bimpure.com/blog/revit-2025).
- Antes da 2025, matrizes de 0 ou 1 elemento quebravam famílias. Antes da 2026, subdivisões não podiam ser rebaixadas e as paredes eram obrigadas a ter núcleo. As correções recentes revelam essas limitações antigas. — [BIMpure 2025](https://www.bimpure.com/blog/revit-2025); [BIMpure 2026](https://www.bimpure.com/blog/revit-2026).
- O toposolid tem limite de pontos: 20.000 por padrão, até 50.000 via Revit.ini. Booleanos de corte falhavam o bastante para justificar a nova opção de estabilidade. — [Microsol Resources, Revit 2026](https://microsolresources.com/?p=16900).

### Inferences
- Para o mercado brasileiro, onde escadas e guarda-corpos (NBR 9077 e NBR 9050) e lajes de vários tipos são comuns, uma ferramenta de escada que recalcula sozinha ao mudar as regras é um diferencial claro. O mesmo vale para guarda-corpo de vidro com largura de painel variável.
- Elementos afunilados ou de espessura variável (lajes, paredes) são uma lacuna antiga. O IFC permite representá-los via IfcExtrudedAreaSolidTapered ou geometria livre, e isso pode ser exposto como opção de parâmetro.

### Gaps
- Não houve acesso ao Reddit r/Revit nem ao RevitForum.org: as buscas não retornaram esses domínios.
- Não houve acesso a um ranking de votos do Revit Ideas (HTTP 403).
- Faltam relatos atuais (2025 a 2026) de reclamações sobre famílias: desempenho de famílias aninhadas, fragilidade de restrições, ausência de versionamento.
