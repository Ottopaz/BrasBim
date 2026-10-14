---
documento: Interface — janela principal e primeiras ferramentas (versão 0.1 testável)
requisito: RF-UI-01, RF-UI-02, RF-UI-03, RF-UI-04, RF-UI-07, RF-NUC-01, RF-NUC-04, RF-DES-01..04, RF-PRJ-01
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-14
status: aprovado
revisor: OTTO (aprovado em 2026-10-14)
---

# Janela principal e primeiras ferramentas

## 1. Propósito
Primeira versão do aplicativo que o revisor consegue **usar** para modelar e testar
paredes e portas, e dar retorno de usabilidade. Não é a interface final: cada versão
seguinte (§11) entra conforme o retorno recebido.

Princípios:
- A interface só **chama comandos do núcleo** (`brasbim/core/*/commands.py`) e mostra o
  resultado. Nenhuma regra de modelagem fica em `brasbim/ui`. *(decisão do projeto, RNF-02)*
- Cada ação do usuário é **uma transação** do núcleo, com desfazer (RF-NUC-01). Enquanto a
  ação não termina (ex.: cadeia de paredes em andamento), só existe pré‑visualização.
- Cálculos que não dependem de Qt (desenho da planta, *snap*, achar a parede sob o cursor)
  ficam no núcleo, com testes. *(decisão do projeto)*
- Vocabulário próprio, em pt‑BR. **Sem ícones** na versão 0.1: botões com texto, para não
  correr o risco de imitar ícones de outros programas e para facilitar o retorno
  ("o botão X"). *(decisão do projeto, cleanroom/PROCESSO.md §3.4)*

## 2. Janela principal (RF-UI-01, RF-UI-03)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Arquivo  Editar  Exibir  Ajuda                                           │
├──────────────────────────────────────────────────────────────────────────┤
│ [Selecionar] [Parede] [Parede em arco] [Retângulo] [Porta] │ [Desfazer] [Refazer] │
├────────────┬───────────────────────────────────────────┬─────────────────┤
│ Projeto    │  ┌ Planta ┐┌ 3D ┐   (abas, ou lado a lado) │ Propriedades    │
│            │  │                                      │  │                 │
│ ▸ Térreo ● │  │                                      │  │ (ferramenta ou  │
│ ▸ Superior │  │                                      │  │  seleção)       │
│            │  │                                      │  │                 │
├────────────┴──┴──────────────────────────────────────┴──┴─────────────────┤
│ Mensagens: avisos e recusas do núcleo, com hora                          │
├──────────────────────────────────────────────────────────────────────────┤
│ Clique o ponto inicial da parede        x 3,25  y 1,40   Grade 0,10 m    │
└──────────────────────────────────────────────────────────────────────────┘
```
Desenho próprio, com a organização usual de aplicativos de desktop (menus, barra de
ferramentas, painéis laterais, barra de estado). *(CG)*

| Área | Conteúdo |
|---|---|
| Menus | **Arquivo**: Novo, Abrir…, Salvar, Salvar como…, Sair. **Editar**: Desfazer, Refazer, Excluir. **Exibir**: Planta, 3D, Lado a lado, Enquadrar tudo. **Ajuda**: Registrar observação… (§9), Sobre |
| Barra de ferramentas | Ferramentas (§5) e Desfazer/Refazer, com o nome da transação na dica ("Desfazer Criar porta") |
| Projeto (esquerda) | Pavimentos em ordem de cota, com nome e cota. Clique duplo torna o pavimento **ativo** (●): é o que a planta mostra e onde as ferramentas criam elementos. Criar/renomear/excluir pavimento: versão 0.2 |
| Centro | Abas **Planta** e **3D**; "Lado a lado" divide a área em duas |
| Propriedades (direita) | §7 |
| Mensagens (embaixo) | Avisos do núcleo (ex.: "abertura fora da parede", "porta convertida") e recusas de comando, com hora. Não abre janela modal |
| Barra de estado | Instrução da ferramenta, coordenadas do cursor no pavimento, grade |

Painéis laterais e de mensagens podem ser fechados e movidos (comportamento padrão do
Qt). A posição deles é lembrada entre sessões.

### 2.1 Unidades e números (RF-PRJ-02, RF-UI-07)
- Comprimentos em metros, exibidos com 2 casas e **vírgula decimal** (`0,86`).
- Campos aceitam vírgula ou ponto. Valores inválidos ficam marcados e não geram transação.

### 2.2 Projeto novo
"Novo" cria um projeto com Térreo (0,00) e Superior (2,80) e uma biblioteca mínima: tipos
de parede "Alvenaria 14" e "Drywall 9,5" e tipos de porta "P1 – giro 80", "P2 – giro 70" e
"P3 – correr 2 folhas" (valores de porta §3.5). Esse conteúdo inicial não entra na pilha
de desfazer. *(CG, a revisar)*

### 2.3 Abrir e salvar (RF-PRJ-01)
- Abrir e salvar `.ifc`. O título da janela mostra o arquivo e `*` se houver alteração não
  salva. Fechar com alteração pede confirmação.
- IFC de outra origem abre como está (spec da parede P16, porta §6.6).

## 3. Planta (RF-UI-03, RF-DOC-01 simplificado)
Mostra o pavimento ativo visto de cima, gerado do modelo a cada transação.

| Elemento | Desenho na versão 0.1 |
|---|---|
| Parede | Contorno do corpo (após as junções) com preenchimento cinza; vãos interrompem o contorno |
| Porta de giro | Marco cortado; folha aberta a 90° e arco de giro em linha fina, do lado para onde abre |
| Porta de correr | Folhas no trilho, com seta no sentido de correr |
| Outras operações | Contorno do marco e linha da folha fechada |
| Pavimento de baixo | Paredes em cinza claro, sem preenchimento (referência; pode ser desligado) |

- Corte simplificado: todo elemento do pavimento ativo aparece cortado. Plano de corte,
  linhas de projeção e níveis de detalhe seguem RF-DOC-01/08 em versão posterior.
- Seleção em destaque (cor de seleção) e pré‑visualização em linha tracejada.
- Desenho na tela não é gravado no IFC (parede §7, porta §7).

### 3.1 Navegação
| Ação | Entrada |
|---|---|
| Aproximar/afastar no cursor | Roda do mouse |
| Arrastar a vista | Botão do meio, ou barra de espaço + botão esquerdo |
| Enquadrar tudo | Menu Exibir, ou tecla Home |

### 3.2 Precisão (RF-DES-01..04, versão mínima)
- **Grade** de 0,10 m (linhas a cada 1,00 m mais fortes), visível conforme o zoom.
- ***Snap*** (atração), em ordem de prioridade, dentro de 10 px: extremidades de caminho
  de parede; meio de parede; ponto do caminho mais próximo; grade. O ponto atraído
  aparece com marcador e nome curto ("extremidade", "meio", "na parede", "grade").
- **Ortogonal**: com Shift pressionado, o segmento fica preso a múltiplos de 45°.
- **Entrada numérica**: durante o desenho de um segmento, digitar um número abre um campo
  junto ao cursor; Enter usa esse comprimento na direção atual do cursor.
- Tecla Alt pressionada desliga o *snap* temporariamente.

## 4. Vista 3D (RF-UI-04)
- Só visualização na versão 0.1: paredes e portas de todos os pavimentos, sombreadas, com
  cor por material (constituinte ou camada principal) e arestas finas.
- Navegação: botão esquerdo gira em torno do centro do modelo; botão do meio arrasta;
  roda aproxima. Home enquadra tudo. Projeção em perspectiva.
- Elemento selecionado na planta aparece destacado no 3D.
- Atualização **incremental**: depois de cada transação, só os elementos alterados são
  triangulados de novo (o núcleo informa os `GlobalId`s alterados, §10).
- Geometria: triangulação do `ifcopenshell.geom` (a mesma do visualizador de exemplos).

## 5. Ferramentas
Uma ferramenta fica ativa por vez. Esc cancela o que estiver em andamento e, sem nada em
andamento, volta para **Selecionar**. As opções da ferramenta (tipo, linha de referência…)
aparecem no painel de propriedades enquanto ela está ativa (§7.1).

### 5.1 Selecionar (RF-NUC-04, versão mínima)
- Clique seleciona a parede ou porta sob o cursor (a porta tem prioridade sobre a parede
  que a contém). Ctrl+clique soma ou retira da seleção. Clique no vazio limpa.
- Tecla Delete ou Editar > Excluir: exclui a seleção numa transação. Parede com porta
  pede confirmação, dizendo quantas portas saem junto (parede §6.4, porta §6.4).
- **Arrastar porta selecionada**: move ao longo da parede, com a distância ao início
  mostrada junto ao cursor; soltar sobre outra parede reta muda a porta de parede
  (porta §5.1, PO10/PO11). Posição que não cabe aparece em vermelho e é recusada ao soltar.
- Seleção por janela/cruzamento e alças de parede: versão 0.2.

### 5.2 Parede (parede §4)
1. Clique: ponto inicial. Instrução: "Clique o ponto inicial da parede".
2. Cada clique seguinte fecha um segmento e começa o próximo no mesmo ponto (cadeia),
   com pré‑visualização na espessura real e o lado das camadas.
3. Termina com clique duplo, Enter ou clique direito. Clicar no ponto inicial fecha a
   cadeia. Esc descarta a cadeia inteira.
4. A cadeia inteira vira **uma** transação (`create_chain`), com as junções L.
5. Opções: tipo de parede, linha de referência, altura (topo no pavimento de cima ou
   altura fixa).

### 5.3 Parede em arco
Três cliques: início, um ponto do arco, fim (`create_arc_wall`). Pré‑visualização do arco
a partir do 2º clique. Mesmas opções da 5.2.

### 5.4 Retângulo
Dois cliques em cantos opostos (`create_rectangle`). Mesmas opções da 5.2.

### 5.5 Porta (porta §4)
1. Com o cursor sobre uma parede reta, a pré‑visualização mostra a porta centrada no
   ponto mais próximo do caminho, com o arco de giro do lado em que está o cursor.
2. A distância das bordas do vão até as extremidades da parede aparece junto ao cursor.
   *Snap* ao meio da parede.
3. **Tab** alterna o lado das dobradiças antes do clique (porta §4, "tecla de alternar").
4. Clique cria a porta (`create_door`, com `opens_to` e `hinges`). Posição que não cabe
   aparece em vermelho; o clique mostra o motivo em Mensagens, sem criar nada.
5. Parede em arco: a pré‑visualização não aparece e a barra de estado diz que porta em
   parede em arco ainda não é suportada (PO19).
6. Opções: tipo de porta, largura e altura (padrão do tipo), base, alinhamento e
   deslocamento.

## 6. Teclado e mouse
Só convenções gerais de desktop e escolhas próprias; atalhos configuráveis ficam para V1
(RF-UI-08). *(CG)*

| Tecla | Ação |
|---|---|
| Ctrl+N, Ctrl+O, Ctrl+S, Ctrl+Shift+S | Novo, Abrir, Salvar, Salvar como |
| Ctrl+Z, Ctrl+Y (e Ctrl+Shift+Z) | Desfazer, Refazer |
| Delete | Excluir seleção |
| Esc | Cancelar / voltar a Selecionar |
| Enter | Encerrar cadeia; confirmar entrada numérica |
| Tab | Alternar dobradiças (ferramenta Porta) |
| Shift (segurado) | Ortogonal / 45° |
| Alt (segurado) | Desligar *snap* |
| Home | Enquadrar tudo |

Ferramentas não têm atalho de uma letra na versão 0.1.

## 7. Painel de propriedades (RF-UI-02)
Cada campo alterado gera **uma** transação ao confirmar (Enter ou sair do campo). Campos
somente leitura aparecem em cinza. Se o núcleo recusar, o campo volta ao valor anterior e
o motivo vai para Mensagens.

### 7.1 Ferramenta ativa, nada selecionado
Opções da próxima criação (§5.2–5.5). Valem até serem mudadas na sessão.

### 7.2 Parede selecionada
| Grupo | Campos |
|---|---|
| Geral | Tipo (lista), linha de referência, inverter camadas (caixa) |
| Altura | Base (deslocamento), topo: pavimento de cima ou altura fixa, com valor |
| Geometria (leitura) | Comprimento, espessura |
| Quantidades (leitura) | Área lateral bruta e líquida, volume (`Qto_WallBaseQuantities`) |
| Identificação (leitura) | `GlobalId`, origem (BrasBim ou outro programa) |

### 7.3 Porta selecionada
| Grupo | Campos |
|---|---|
| Geral | Tipo (lista), código (`Reference`) |
| Vão | Largura, altura, base, distância ao início da parede |
| Abertura | Abre para (face esquerda/direita da parede), dobradiças (esquerda/direita) e os botões **Inverter sentido** e **Inverter dobradiças** |
| Posição no marco | Alinhamento, deslocamento |
| Quantidades (leitura) | Largura, altura, área (`Qto_DoorBaseQuantities`) |
| Identificação (leitura) | `GlobalId`, origem; para porta de outra origem, aviso de que mudar tamanho, tipo, sentido, dobradiças ou alinhamento a converte (porta §6.6) |

### 7.4 Vários elementos
Versão 0.1: mostra só a quantidade selecionada por classe. Edição em lote: versão 0.2.

### 7.5 Tipos
Na versão 0.1 os tipos vêm da biblioteca mínima (§2.2) e dos arquivos abertos. Criar e
editar tipos de parede e porta pela interface: versão 0.2.

## 8. Erros e avisos
- **Recusa de comando** (`OpError`): nada muda no modelo; mensagem em Mensagens e na barra
  de estado. Sem janela modal.
- **Aviso do núcleo** (registro `logging` de nível aviso): vai para Mensagens.
- **Erro inesperado**: o aplicativo não fecha. Mostra uma janela com o resumo, grava o
  relatório técnico e o diário da sessão (§9.2) e mantém o modelo no último estado
  consistente (a transação é toda ou nada).

## 9. Retorno de uso (feedback)

### 9.1 Registrar observação
Ajuda > Registrar observação… abre uma caixa de texto. Ao confirmar, o BrasBim acrescenta a
`feedback/AAAA-MM-DD.md` (na pasta do repositório; configurável) uma entrada com:
- hora, versão do BrasBim (commit) e o texto digitado;
- contexto automático: ferramenta ativa, seleção (classe e `GlobalId`), pavimento ativo,
  as 5 últimas transações (rótulo e operações) e as últimas mensagens.

Assim cada observação já chega com o que eu preciso para reproduzir. *(decisão do projeto)*

### 9.2 Diário da sessão
O diário de transações (`History.journal`) é gravado continuamente em
`feedback/diarios/<data-hora>.json`. Reaplicado num projeto novo, reproduz a sessão
(PO17), o que permite reproduzir um problema exatamente como aconteceu.

## 10. Organização do código *(decisão do projeto)*

| Onde | O quê |
|---|---|
| `brasbim/core/plan.py` | Desenho 2D de um pavimento como primitivas (polígonos, linhas, arcos) com o `GlobalId` de origem; sem Qt |
| `brasbim/core/snap.py` | Pontos de atração e elemento sob um ponto; sem Qt |
| `brasbim/core/ops/history.py` | Passa a avisar quem escuta: transação aplicada/desfeita/refeita e `GlobalId`s alterados |
| `brasbim/ui/session.py` | Documento, histórico, seleção, pavimento ativo, arquivo; único ponto que chama `History.commit` |
| `brasbim/ui/main_window.py` | Janela, menus, barra, painéis |
| `brasbim/ui/plan_view.py` | Planta (QWidget + QPainter) |
| `brasbim/ui/view3d.py` | Vista 3D (`QOpenGLWidget`) |
| `brasbim/ui/tools/` | Selecionar, Parede, Arco, Retângulo, Porta |
| `brasbim/ui/properties.py` | Painel de propriedades |
| `brasbim/ui/feedback.py` | §9 |

Dependências novas (extra `ui`): PySide6 (LGPL‑3.0) e PyOpenGL (licença BSD), ambas
compatíveis com a GPL‑3.0 do aplicativo. Comando: `brasbim` ou `python -m brasbim.ui.app`.

## 11. Versões seguintes (a ordenar pelo retorno)
- **0.2**: alças de parede (extremidades e meio), dividir parede, mover/copiar/girar,
  seleção por janela, criar/editar pavimentos e tipos, edição em lote.
- **0.3**: janela (RF-ELE-06) com ferramenta própria; cotas temporárias e cotas fixas.
- Depois: laje, pilar, viga; plano de corte da planta e níveis de detalhe; pranchas.

## 12. Critérios de aceite (testes)
Testes com o Qt em modo sem tela (`QT_QPA_PLATFORM=offscreen`), acionando as ferramentas
por eventos simulados de mouse e teclado, e verificando o IFC resultante. As partes do
núcleo (`plan`, `snap`, avisos do histórico) têm testes próprios, sem Qt.

- [ ] **UI01** "Novo" cria Térreo, Superior e a biblioteca mínima; pilha de desfazer vazia.
      Salvar e reabrir preserva os `GlobalId`s.
- [ ] **UI02** Parede: 4 cliques e Enter → 1 transação com 3 `wall.create` e 2 junções L;
      Desfazer remove as 3 paredes; Esc no meio da cadeia não cria nada.
- [ ] **UI03** Retângulo e parede em arco criam o mesmo que `create_rectangle` e
      `create_arc_wall` com os pontos clicados.
- [ ] **UI04** *Snap*: clique perto (≤ 10 px) da extremidade de uma parede usa exatamente
      aquele ponto e cria a junção; com Alt, não.
- [ ] **UI05** Entrada numérica: digitar `3,5` + Enter cria segmento de 3,50 m.
- [ ] **UI06** Porta: clique com o cursor do lado esquerdo da parede → `opens_to = left`;
      Tab antes do clique → variante com dobradiças à direita; parede em arco → nada criado
      e mensagem.
- [ ] **UI07** Painel: alterar a largura da porta gera `opening.edit`; botão Inverter
      dobradiças gera a troca de variante (PO08).
- [ ] **UI08** Arrastar porta ao longo da parede e para outra parede gera um único
      `opening.edit` (PO10/PO11); soltar fora dos limites não altera nada.
- [ ] **UI09** Excluir parede com porta pede confirmação; confirmar gera a cascata de PO15.
- [ ] **UI10** Depois de cada transação, a planta e o 3D mostram o modelo atual, e só os
      elementos alterados são triangulados de novo.
- [ ] **UI11** Abrir o IFC de outra origem de PO18: a porta aparece e pode ser movida
      arrastando.
- [ ] **UI12** Registrar observação grava a entrada com o contexto de §9.1; o diário da
      sessão reaplicado num projeto novo reproduz o mesmo IFC.
- [ ] **UI13** Erro inesperado numa ferramenta não fecha o aplicativo e grava o relatório.

## 13. Fontes públicas
- **RF** — `spec/REQUISITOS.md` (RF-UI, RF-NUC, RF-DES, RF-PRJ).
- **PAREDE**, **PORTA** — `spec/elementos/parede.md` §4–§7 e `porta.md` §4–§7 (interações e
  desenho 2D já aprovados).
- **QT** — documentação pública do Qt for Python 6 (`https://doc.qt.io/qtforpython-6/`):
  `QMainWindow`, `QDockWidget`, `QOpenGLWidget`, `QPainter`, modo `offscreen`.
- **PYOPENGL** — `https://pyopengl.sourceforge.net/` (licença).
- **IOS** — `ifcopenshell.geom` para a triangulação do 3D.
- **CG** — conhecimento geral de aplicativos de desktop e de CAD (menus, painéis,
  navegação com roda e botão do meio, grade, *snap*, tecla Esc).

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

## 14. Pontos de revisão
(a) Planta, 3D, painel de Projeto à esquerda e Propriedades à direita (§2).
(b) Sem ícones e sem atalhos de uma letra na versão 0.1 (§1, §6).
(c) Tab para alternar dobradiças na ferramenta Porta (§5.5).
(d) Biblioteca mínima do projeto novo (§2.2).
(e) Observações em `feedback/` versionadas; diários em `feedback/diarios/` fora do git (§9).
(f) Escopo da versão 0.1 e ordem das seguintes (§11).
