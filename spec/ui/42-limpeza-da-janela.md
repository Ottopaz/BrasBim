---
documento: Limpeza da janela — títulos dos painéis, coluna de ferramentas, barras de baixo e balão de mensagem
requisito: RF-NUC-05 (interface); pedido do revisor em 2026-10-29, noite (feedback/prints/barras.png)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-29
status: em revisão (§1–§4 implementados para teste)
revisor: OTTO
---

# Limpeza da janela

## 1. Propósito
O revisor marcou no print `feedback/prints/barras.png` o que polui a janela e pediu:
tirar os botões dos títulos dos painéis encaixados; tirar a barra de rolagem da coluna de
ferramentas; espalhar a barra da vista e a linha de comando pela largura da vista; e um
balão com a mensagem da última ação. O print vale só como descrição de função; o desenho
e os textos são do BrasBim.

## 2. Títulos dos painéis
- **Encaixado**, o painel mostra só o nome, na mesma faixa de antes: sem os botões de
  soltar e fechar. Vale para todos os painéis (Ferramentas, Pavimentos, Navegador,
  Propriedades, Mensagens, Assistente, Camadas, Biblioteca, Equipe).
- **Solto (flutuando)**, a faixa ganha o botão de fechar (ícone ×, dica "Fechar o painel
  (volta por Exibir > Painéis)"). Não há botão de soltar: solta-se arrastando a faixa.
- Continua igual: arrastar a faixa solta e encaixa; clique duplo na faixa alterna entre
  solto e encaixado; Exibir > Painéis mostra e esconde; o nome some se não couber inteiro
  (spec/ui 40 §2), agora com mais espaço, porque não há botões.
- O painel solto passa a usar a moldura do BrasBim (a do sistema mostraria os próprios
  botões); ele continua redimensionável pelas bordas.

## 3. Coluna de ferramentas e barras de baixo
- **Coluna de ferramentas:** sem barra de rolagem; quando os ícones não cabem, a roda do
  mouse rola a coluna, como antes.
- **Barra da vista:** os grupos (zoom · giro · escala · camadas · detalhe · penas ·
  situação) ficam com o mesmo vão entre si e ocupam a largura da vista; o cadeado
  "Escolher travados" fica na ponta direita. Sai a linha divisória depois do zoom (o vão
  separa). Itens que não valem na vista à frente (ex.: escala no 3D) somem, e os outros
  se redistribuem.
- **Linha de comando:** sem opções da ferramenta, o campo vai até o Histórico. Com opções
  (ex.: Parede), a divisão é a de antes: campo à esquerda, opções à direita.

## 4. Balão de mensagem
- Toda mensagem que entra no painel Mensagens também aparece num **balão** no canto de
  baixo, à esquerda da vista, logo acima da barra da vista (sem a barra, acima da linha de
  comando).
- Fundo branco, borda fina e uma faixa à esquerda na cor do tipo: roxo (informação),
  âmbar (aviso), vermelho (recusa). Largura conforme o texto, até 520 px; texto longo
  quebra em linhas.
- Fica na tela por 3 s mais um pouco por palavra; avisos e recusas, 2 s a mais; no
  máximo 10 s. Depois esmaece (0,4 s). Uma mensagem nova toma o lugar da anterior e
  recomeça o tempo.
- Não pega o mouse: o clique passa para a vista. Para copiar ou rever, o painel Mensagens
  continua com tudo (spec/ui 30 §7).
- A recusa continua também na barra de estado, como antes.

## 5. Testes
- **LJ01:** todos os painéis visíveis têm a faixa própria; encaixados, nenhum botão de
  soltar ou fechar à vista; o nome aparece.
- **LJ02:** solto, o painel mostra o fechar; o fechar esconde o painel e desmarca o item
  em Exibir > Painéis; encaixado de novo, o fechar some.
- **LJ03:** clique duplo na faixa solta o painel; outro clique duplo encaixa.
- **LJ04:** a coluna de ferramentas não tem barra de rolagem vertical.
- **LJ05:** com a janela larga, o último grupo da barra da vista passa de 60% da largura,
  há vão entre os grupos e o cadeado fica na ponta.
- **LJ06:** sem opções, o rótulo das opções está escondido e o campo encosta no Histórico;
  com a Parede, as opções aparecem.
- **LJ07:** uma mensagem abre o balão à esquerda, acima da barra da vista, com o tempo
  correndo; a seguinte toma o lugar, com a cor da recusa; o balão não pega o mouse; some
  depois de esmaecer; o painel Mensagens guarda as duas. O tempo cresce com o texto e o
  tipo, até 10 s.

## 6. Fontes
- Pedido e print do revisor: `feedback/prints/barras.png` (2026‑10‑29).
- Qt 6, `QDockWidget::setTitleBarWidget` (documentação pública do Qt): com uma faixa
  própria, os botões e a moldura do sistema não são usados; o arrasto e o clique duplo
  na faixa continuam com o painel.
