# Plano: funções das barras e do navegador (prints de 2026‑10‑29)

O revisor pôs três prints em `feedback/prints/`:
- `ferramentas superiores.png`: barras de cima;
- `ferramentas inferiores.png`: barra de baixo da vista;
- `barraslaterais.png`: painel lateral com a árvore do projeto.

São de um programa comercial. Pela regra de clean‑room (`cleanroom/PROCESSO.md`), os prints
valem só como **descrição de função**. Daqui não saem nomes, ícones, textos nem disposição.
Abaixo, cada função recebe nome próprio do BrasBim. A coluna "Pesquisa" diz se a pesquisa
pública (`research_notes/Pesquisa Archicad Revit AutoCAD/`) já cobre a função. Onde
não cobre, a spec só começa depois da pesquisa complementar (Fase 0).

Legenda: ✅ temos · ◐ temos em parte · ✗ não temos · ? função incerta no print.

## 1. Inventário

### 1.1 Barra de cima: edição, atração e organização

| # | Função (vocabulário BrasBim) | BrasBim hoje | Pesquisa |
|---|---|---|---|
| 1 | Desfazer / refazer | ✅ | — |
| 2 | **Localizar e selecionar** por critérios (classe, tipo, camada, pavimento, propriedade; somar ou tirar da seleção) | ◐ só "Selecionar semelhantes" (spec/ui 23 §7) | ◐ `interface_e_interacao.md` §2 (filtros do Revit, critérios IFC) |
| 3 | **Pegar ajustes** de um elemento para a ferramenta e **aplicar ajustes** a outros elementos | ✗ | ✅ `complemento_barras_e_navegacao.md` §9 |
| 4 | Linhas‑guia liga/desliga | ✅ spec/ui 37 | ✅ |
| 5 | Pontos de atração e seus tipos | ✅ spec/ui 23 | ✅ |
| 6 | **Assentar** o elemento novo sobre laje, cobertura ou terreno (a base segue a superfície) | ✗ | ✅ `archicad_modelagem.md` (assentar só na criação; "reassentar" é melhoria) |
| 7 | Grade: atrair, mostrar e **escolher o passo** | ◐ passo fixo de 0,10 m | ◐ |
| 8 | **Pavimento de referência**: ver outro pavimento (ou vista) por baixo, em cinza | ◐ só as paredes do pavimento de baixo | ✅ `complemento_barras_e_navegacao.md` §10 |
| 9 | **Travar elementos** um a um (não editáveis) e destravar todos | ✗ só a camada inteira (spec/ui 18) | ✅ `complemento_barras_e_navegacao.md` §1 |
| 10 | **Agrupar / desagrupar** e pausar os grupos (selecionar só um membro) | ✗ | ◐ comparação: `IfcGroup` simples (RF‑NUC‑07) |
| 11 | **Varinha**: contorno detectado num clique, para laje, cobertura, hachura, área… | ◐ laje, cobertura e ambiente por clique dentro do cômodo | ✅ `interface_e_interacao.md` §1 |
| 12 | Área de seleção, esticar, 3D da área, exportar/imprimir a área | ✅ spec/ui 38 | ✅ |
| 13 | **Operações de sólidos**: subtrair, somar, intersectar um elemento com outro, associativo | ✗ | ✅ `archicad_modelagem.md` |
| 14 | Dividir, aparar/estender, concordar, deslocar paralela | ✅ spec/ui 23 e 0.2 | ✅ |
| 15 | **Escalar** (redimensionar por fator ou por referência) | ✗ | ◐ comparação (esticar/escala por referência) |
| 16 | **Recortar pela cobertura ou laje**: parede e pilar terminam na face de baixo da cobertura | ◐ topo "pavimento de cima" e inclinação; não segue a cobertura | ✅ `complemento_barras_e_navegacao.md` §2 |
| 17 | Marcador de alteração | ✅ (Alteração) | — |
| 18 | **Questões de coordenação** (marcar um problema numa vista, trocar por BCF) | ✗ | ✅ `interoperabilidade_openbim.md` |
| 19 | Equipe: enviar, receber, reservar, liberar, sair | ✅ spec/ui 33 (envio automático) | ✅ |

### 1.2 Barra de cima: exibição e 3D

| # | Função | BrasBim hoje | Pesquisa |
|---|---|---|---|
| 20 | **Ordem de desenho** na planta (trazer para frente, mandar para trás) | ✗ | ✅ `complemento_barras_e_navegacao.md` §3 |
| 21 | **Ocultar elementos selecionados** e "mostrar tudo de novo" | ◐ só por camada (ocultar/isolar a camada) | ✅ `complemento_barras_e_navegacao.md` §4 |
| 22 | Ver a seleção ou a área no 3D | ✅ "Mostrar no 3D", "3D da área" | ✅ |
| 23 | **Projeção paralela** × perspectiva no 3D | ✗ só perspectiva; vistas padrão ✅ | ✅ `complemento_barras_e_navegacao.md` §5 |
| 24 | **Andar pelo modelo** (navegação em primeira pessoa, altura dos olhos) | ✗ | ✅ `complemento_barras_e_navegacao.md` §6 |
| 25 | **Estilos do 3D**: sombreado com arestas, linhas ocultas, raio‑x, cor por propriedade | ◐ só sombreado | ◐ `visualizacao_apresentacao.md` |
| 26 | **Filtro do 3D**: tipos de elemento e pavimentos que aparecem; **caixa de corte** livre | ◐ 3D da área | ✅ comparação §3.3 |
| 27 | Situação na vista (existente/demolir/construir) | ✅ spec/ui 31 §3 | ✅ |
| 28 | **Regras de aparência**: mudar hachura, pena ou cor por critério, sem mudar o elemento | ✗ | ✅ `archicad_modelagem.md` |
| 29 | **Imagem da vista 3D** (exportar PNG; depois, render) | ◐ 3D vira imagem na prancha | ✅ `visualizacao_apresentacao.md` (glTF / exportar em vez de render próprio) |
| 30 | **Publicar em lote** (conjunto de pranchas/vistas → PDF, DXF, IFC de uma vez) | ✗ um PDF por vez | ✅ `archicad_documentacao_colaboracao.md` |

### 1.3 Barra de baixo da vista (seletores rápidos)

| # | Função | BrasBim hoje | Pesquisa |
|---|---|---|---|
| 31 | **Zoom anterior / seguinte** e zoom em % | ✗ (só enquadrar) | ✅ `complemento_barras_e_navegacao.md` §7 |
| 32 | **Girar a vista da planta** (trabalhar com o desenho torto na tela) | ✗ | ✅ `complemento_barras_e_navegacao.md` §8 |
| 33 | Escala da vista | ✅ (seletor na barra de estado) | — |
| 34 | Combinação de camadas | ✅ spec/ui 18 §6, só pelo painel/menu | — |
| 35 | Detalhe da planta (opções de exibição do modelo) | ✅ Exibir > Detalhe | — |
| 36 | Tabela de penas | ✅ spec/ui 27 | — |
| 37 | Regras de aparência (= #28) | ✗ | ✅ |
| 38 | Situação na vista (= #27) | ✅ | — |
| 39 | **Exibir só a estrutura** (esconder revestimentos e o que não é portante) | ✗ | ◐ `estrutura_e_instalacoes.md` |
| 40 | **Estilo de cotas** escolhido na vista | ◐ cotas com um estilo só | ◐ |
| 41 | **A própria barra**: seletores de 31–40 juntos sob a vista, cada um abre a lista | ◐ estão espalhados em menus | ◐ `interface_e_interacao.md` §4 (modos visíveis na barra de estado, padrão Rhino) |

### 1.4 Painel lateral: árvore do projeto

| # | Função | BrasBim hoje | Pesquisa |
|---|---|---|---|
| 42 | **Navegador em árvore única**: pavimentos, cortes, fachadas, elevações internas, detalhes, folhas de trabalho, 3D, tabelas, com **busca** | ◐ painel Projeto com listas separadas (pavimentos, vistas salvas, cortes, pranchas, tabelas) | ✅ `archicad_documentacao_colaboracao.md` (árvore como espinha do projeto) |
| 43 | Abas do navegador: o que o modelo gera / vistas salvas / pranchas / publicação | ◐ abas Vistas salvas, Pranchas e Folhas mestras | ✅ |
| 44 | Novo / ajustes / excluir na base da árvore + nome e número do item selecionado | ◐ botões por lista | — |
| 45 | Pavimento marcado em negrito como o ativo; duplo clique abre | ✅ | — |
| 46 | **Situação em um clique**: três botões (existente / a demolir / novo) que marcam a seleção (resposta do revisor) | ◐ Editar > Situação já marca a seleção (spec/ui 31); faltam os botões à mão | ✅ `complemento_barras_e_navegacao.md` §11 |

**Resumo:** das 46 funções, **15 já temos** (✅), **15 temos em parte** (◐) e **16 não temos**
(✗). O item 46 foi explicado pelo revisor. Várias das ✗ e ◐ já são pedidos antigos (comparação de
2026‑10‑23 §3.2 e §3.3). As elevações internas, detalhes e folhas de trabalho que a árvore
lista já estão especificadas e aprovadas (specs 35 e 36), mas falta implementar.

## 2. Plano

Ordem proposta: primeiro o que é barato e se usa toda hora, depois o 3D, depois a
modelagem pesada. O que já está na fila continua antes: spec/ui 38 §5 (exportar a área) e
as specs 35/36 aprovadas (Câmera → Elevação interna → Folha → Detalhe; Ponto de apoio →
Polilinha → Figura → Desenho).

### Fase 0: pesquisa complementar (antes das specs) *(feita em 2026‑10‑29)*
Fontes públicas (help oficial Graphisoft/Autodesk/Bricsys/McNeel, fóruns) para os itens sem
cobertura: 9 (travar elemento), 16 (recortar pela cobertura), 20 (ordem de desenho),
21 (ocultar seleção), 23 (paralela), 24 (andar), 31 (zoom anterior), 32 (girar a vista),
3 (pegar/aplicar ajustes), 8 (escolher a referência). Nota nova em `research_notes/`,
como em `complemento_vistas_e_documentacao.md`, com as lacunas declaradas.
- Feita: `research_notes/Pesquisa Archicad Revit AutoCAD/complemento_barras_e_navegacao.md`
  (também cobre o item 46). Os achados vêm de resumos de busca: abrir as páginas oficiais
  ao fechar cada spec. O que muda no plano: o elemento travado **continua escolhível e
  atraível** (Archicad e Revit fazem assim), e a recusa vem antes de arrastar; ocultar
  ganha **isolar** e um aviso na vista; pegar/aplicar ajustes não passa as medidas
  próprias por padrão; os botões de situação, sem seleção, escolhem a situação dos
  próximos elementos.

### Fase 1: barra de vista e organização rápida (spec/ui 39)
1. **Barra da vista** (#41) sob a planta: zoom anterior/seguinte e % (#31), escala,
   combinação de camadas, detalhe, penas, situação e estilo de cotas. Cada seletor abre a
   mesma lista que o menu. Ela substitui o seletor de escala atual da barra de estado.
2. **Girar a vista da planta** (#32): ângulo na barra. A grade, as guias e as setas seguem
   a vista, e o desenho fica igual. É estado da vista; vai junto na vista salva.
3. **Ocultar selecionados / isolar / mostrar tudo** (#21): estado da sessão, como a área
   de seleção, e não vai para o IFC. Vale na planta e no 3D; a vista avisa enquanto há
   algo oculto.
4. **Travar / destravar elementos** (#9): `Pset_BrasBim_Edicao.Travado`. O travado é
   escolhido e atrai, mas não é editado; o núcleo recusa a edição ("elemento travado")
   antes de começar a arrastar, e a equipe também respeita. Destravar tudo fica no menu
   Editar; uma chave na barra da vista desliga a escolha dos travados.
5. **Ordem de desenho** (#20) para anotações, hachuras e figuras: propriedade de ordem na
   anotação. O plano de corte do modelo não muda.
6. **Situação em um clique** (#46): três botões (existente, a demolir, novo) na mini‑barra
   da seleção ou no topo do painel; com seleção, usam a mesma transação de Editar >
   Situação; sem seleção, escolhem a situação dos próximos elementos criados.
- Testes: VB01… (zoom, giro, ocultar, travar, ordem) com o IFC conferido quando grava.

### Fase 2: seleção e ajustes (spec/ui 40)
1. **Localizar e selecionar** (#2): diálogo não modal com linhas de critério (classe IFC,
   tipo, camada, pavimento, situação, propriedade com =, <, >, contém). Botões somar e tirar
   da seleção. Critérios salvos por nome no projeto. Aproveita `select_similar`.
2. **Pegar ajustes / aplicar ajustes** (#3): Alt+clique num elemento põe os ajustes dele na
   ferramenta (tipo, alturas, linha de referência…). Aplicar a uma seleção é uma
   transação. Depois, **ajustes salvos** por ferramenta (favoritos com nome nosso).
3. **Agrupar** (#10): `IfcGroup` + `IfcRelAssignsToGroup`. Clicar num membro seleciona o
   grupo; a pausa dos grupos (na barra) seleciona só o membro. Mover, copiar e girar levam
   o grupo inteiro.
- Testes: LS01…, AJ01…, GR01… (grupo exportado e lido de volta).

### Fase 3: 3D (spec/ui 41)
1. **Projeção paralela** (#23) e alternância com perspectiva; as vistas padrão ficam em
   paralela.
2. **Filtro do 3D** (#26): tipos e pavimentos (de–até). **Caixa de corte** com alças,
   aproveitando o recorte e as tampas do 3D da área (`scene3d.area_scene`, `_caps`), agora
   com tampo e fundo.
3. **Estilos** (#25): sombreado com arestas (já existe), linhas ocultas, raio‑x e cor por
   propriedade (situação, camada, classe).
4. **Imagem do 3D** (#29): Arquivo > Exportar imagem (PNG, com a resolução escolhida).
   Render fica fora; exportar glTF entra como item da interoperabilidade.
5. **Andar** (#24): W/A/S/D e mouse, altura dos olhos de 1,60 m, sobe e desce pelos
   pavimentos e não atravessa paredes (opcional).
- Testes: V3D01… (projeção, filtro, caixa de corte, PNG gerado).

### Fase 4: modelagem (spec/elementos e spec/ui 42)
1. **Assentar** (#6): opção nas ferramentas de pilar, objeto, escada e guarda‑corpo, que pegam a
   cota da face de cima da laje, cobertura ou terreno sob o ponto. Mais o comando "reassentar"
   para elementos já criados.
2. **Recortar pela cobertura/laje** (#16): parede e pilar com o topo "até a face de baixo de…".
   No IFC, `IfcBooleanClippingResult` com meio‑espaço, refeito quando a cobertura muda.
3. **Escalar** (#15): por fator ou por duas medidas de referência; anotações mantêm o
   texto.
4. **Varinha** (#11): contorno por clique (região fechada pelas linhas e paredes, com
   `pyclipr`) para laje, cobertura, hachura, ambiente e área de seleção.
5. **Operações de sólidos** (#13): subtrair (vira `IfcOpeningElement` +
   `IfcRelVoidsElement` com a forma do elemento operador), somar e intersectar como
   representação booleana. Associativo: mexer no operador refaz o resultado. É o mais
   caro da lista.
- Testes por item, sempre validando o IFC.

### Fase 5: documentação e organização (spec/ui 43)
1. **Navegador em árvore** (#42–44): o painel Projeto vira uma árvore com busca,
   por partes: o que o modelo gera (pavimentos, cortes, fachadas, elevações internas,
   detalhes, folhas, 3D), vistas salvas, pranchas, tabelas. A base fica com novo, ajustes e
   excluir, e a ficha do item. Entra depois das specs 35/36, que criam os itens novos.
2. **Regras de aparência** (#28/#37): regra = critério (do Localizar, Fase 2) + o que muda
   (pena, hachura, cor). Regras ficam em conjuntos aplicados por vista (seletor na barra da
   vista). A situação na vista vira um conjunto pronto.
3. **Exibir só a estrutura** (#39): um conjunto pronto de regras + camadas.
4. **Publicar em lote** (#30): conjuntos de pranchas/vistas com formato e pasta; um botão
   gera tudo.
5. **Questões de coordenação / BCF** (#18): marcador numa vista com a câmera e a seleção;
   importar e exportar BCF 3.0.
6. **Pavimento de referência** escolhido (#8) e **passo da grade** (#7): itens pequenos que
   entram na barra da vista.

## 3. Estimativa e ordem sugerida

| Fase | Tamanho | Depende de |
|---|---|---|
| 0 Pesquisa | feita | — |
| 1 Barra da vista e organização | 1–2 sessões | Fase 0 (itens 9, 20, 21, 31, 32) |
| 2 Seleção e ajustes | 2 sessões | — |
| 3 3D | 2–3 sessões | 3D da área (feito) |
| 4 Modelagem | 3–4 sessões (sólidos sozinhos ~2) | Fase 2 (varinha usa a seleção) |
| 5 Documentação | 3 sessões | specs 35/36 implementadas; Fase 2 (critérios) |

Recomendação (aceita pelo revisor): **Fase 0 → 1 → 2**, com a spec/ui 38 §5 já feita, e
encaixar as specs 35/36 antes da Fase 5.

## 4. Respostas do revisor (2026‑10‑29)
(a) **Ordem:** "tanto faz, pode propor". Fica a proposta: Fase 0 → 1 → 2 → 3 → 4, specs
    35/36 antes da Fase 5.
(b) **Item 46:** os três botões são *existente*, *a demolir* e *novo*: escolhe‑se um
    elemento, aperta‑se um botão e ele passa a essa situação (o filtro de reforma).
    Entra na Fase 1 (item 6).
(c) **Travar:** o revisor pediu recomendação. Recomendado: **vai para o IFC**, em
    `Pset_BrasBim_Edicao.Travado`, para valer ao reabrir o arquivo e para a equipe.
    Decidir na revisão da spec/ui 39.
(d) **Ocultar selecionados:** o revisor pediu recomendação. Recomendado: **só da
    sessão**, como a área de seleção. A vista salva continua guardando camadas e
    combinação, que são o jeito durável de esconder. Decidir na revisão da spec/ui 39.
(e) **Operações de sólidos:** entram **associativas** (o resultado se refaz quando o
    elemento operador muda).
