---
documento: Projeto compartilhado na rede local (reserva de elementos)
requisito: RF-COL-01 a RF-COL-05 (spec/REQUISITOS.md §11); pedido do revisor em 2026-10-28 ("quero testar o trabalho em equipe, pelo menos 2 PCs no BrasBim editando o mesmo projeto"), com as escolhas "mesma rede local" e "reserva + envio automático"
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-28
status: em revisão (fluxo do MVP: implementada junto, §9)
revisor: OTTO
---

# Projeto compartilhado na rede local

## 1. Propósito
Duas ou mais pessoas, cada uma no seu computador, editam o mesmo projeto ao mesmo tempo.
Um computador **compartilha** o projeto; os outros **entram** nele pela rede local. Cada
alteração vai para todos na hora. Para que duas pessoas não mexam no mesmo elemento, o
elemento fica **reservado** para quem começou a editá-lo.

A pesquisa descreve o modelo de reserva assim [AC-COL]: qualquer usuário cria elementos
sem reservar, mas alterar ou excluir exige reserva. O estado das reservas fica sempre
atualizado enquanto se está conectado, e a reserva é automática ao começar a editar. Se o
elemento é de outra pessoa, aparece um aviso e dá para pedir a liberação. O Revit faz o
mesmo pelo empréstimo de elementos: o sem dono é emprestado automaticamente, e o que tem
dono exige pedido ou espera [REV-COL]. A decisão do projeto (2026‑10‑14) já era servidor
com reserva, sobre as operações serializáveis do núcleo (RF-NUC-02). O desenho é próprio.
O recurso se chama "Projeto compartilhado", e o menu se chama **Equipe**.

## 2. Arquitetura
- O **servidor** é parte do BrasBim (`brasbim/core/collab/server.py`, sem Qt). Ele roda
  numa thread do computador que compartilha, sem instalar nada. Ele guarda uma cópia do
  projeto (um `Document`), aplica as transações na ordem em que chegam e numera cada uma.
  Ele também guarda as reservas e repassa os avisos.
- O **cliente** (`core/collab/client.py`) liga o histórico (`History`) ao servidor. Quem
  compartilha também é cliente, ligado ao próprio servidor.
- **Transporte:** TCP na porta 47815 (ou a próxima livre), com mensagens JSON, uma por
  linha. **Descoberta:** quem procura pergunta por UDP em broadcast na porta 47816, e cada
  servidor responde com o nome do projeto, o anfitrião e a porta. Se a rede bloquear o
  broadcast, dá para digitar o endereço (nome ou IP do computador).
- **Entrada:** o servidor manda o IFC atual inteiro, a numeração e as reservas. A partir
  daí só trafegam transações.
- **Aplicação local imediata:** quem edita vê a mudança na hora e envia a transação.
  - Se chega uma transação de outra pessoa antes da confirmação, as pendentes são
    desfeitas, a outra é aplicada e as pendentes são reaplicadas. Todos ficam na mesma
    ordem do servidor.
  - Transação recusada pelo servidor sai da tela e do desfazer, com uma mensagem.
  - Se a cópia local divergir (falha ao aplicar), o cliente pede o projeto inteiro de
    novo.

## 3. Reserva
- **Criar não exige reserva.** O que é criado fica reservado para quem criou (RF-COL-03).
- **Autorreserva:** editar ou excluir um elemento livre o reserva para quem editou, na
  mesma transação. Elemento reservado por outra pessoa não pode ser editado nem
  excluído: a ação é recusada antes de ser aplicada, com a mensagem "<elemento> está
  reservado por <nome>; peça a liberação (Equipe > Pedir liberação)".
- Vale para toda operação com `id` (elementos, tipos, pavimentos, camadas, pranchas…).
  Exceção: as junções de paredes (`path_connection.*`) são consequência da edição das
  paredes e não são reservadas. Efeitos derivados (recortes, vizinhas refeitas) também
  não exigem reserva.
- **Pedir liberação:** com elementos de outra pessoa selecionados, Equipe > Pedir
  liberação. A dona recebe o pedido no painel Equipe, com **Liberar** (a reserva passa
  para quem pediu) ou **Recusar**. Quem pediu recebe a resposta como mensagem.
- **Liberar:** Equipe > Liberar minhas reservas (todas) ou Liberar a seleção. Ao sair do
  projeto compartilhado ou desconectar, as reservas da pessoa são liberadas.
- **Ver as reservas:** na planta, o elemento reservado por outra pessoa ganha um contorno
  na cor dela. O que é seu não muda (Equipe > Mostrar reservas liga e desliga). No
  painel Equipe, cada pessoa aparece com a cor e o número de reservas.

## 4. Fluxos
- **Equipe > Compartilhar este projeto na rede…:** pede o seu nome (vem o nome do
  usuário do Windows) e mostra o endereço para os colegas (`nome-do-pc:47815` e o IP).
  O projeto continua no seu computador: **Salvar** grava o arquivo como sempre.
- **Equipe > Entrar num projeto da rede…:** lista os projetos achados na rede (botão
  Procurar de novo), com um campo de endereço e o seu nome. Ao entrar, o projeto abre sem
  arquivo; Salvar grava uma cópia local.
- **Equipe > Sair do projeto compartilhado:** desconecta. O projeto continua aberto como
  cópia local. Se quem compartilhou sair, os outros recebem o aviso e continuam com a
  cópia.
- **Painel Equipe** (Exibir > Painéis): pessoas conectadas, pedidos de liberação e os
  últimos eventos (entrou, saiu, reservou, liberou).
- **Barra de estado:** "Compartilhado · 2 pessoas" enquanto conectado.

## 5. Desfazer
Cada um desfaz só as próprias transações. Desfazer é uma transação comum, com a mesma
regra de reserva. Se outra pessoa mudou o elemento depois (por exemplo, depois de
liberado), o desfazer é recusado pela verificação de estado (`check_before`) e o passo é
descartado.

## 6. Firewall
Na primeira vez em que o BrasBim compartilha, o Windows pergunta se permite o acesso na
rede. É preciso marcar **Redes privadas** e permitir; sem isso, os outros não acham nem
conectam. Sem senha nesta versão: só para rede de confiança (RF-COL-08 fica para depois).

## 7. Fora desta etapa
Trabalho offline com sincronização ao reconectar (RF-COL-06), histórico de envios com
reversão (RF-COL-07), papéis e permissões (RF-COL-08), internet, reserva por pavimento
ou zona, cores de reserva no 3D.

## 8. Testes (EQ)
- EQ01 Dois clientes: parede criada em A aparece em B, com o mesmo GlobalId e IFC
  equivalente.
- EQ02 Criar reserva para quem criou; B não edita nem exclui (recusa antes de aplicar).
- EQ03 Autorreserva: editar um elemento livre o reserva.
- EQ04 Pedir e liberar: a reserva passa para quem pediu; depois B edita.
- EQ05 Transações simultâneas: os dois aplicam na ordem do servidor e terminam iguais.
- EQ06 Recusa do servidor desfaz a transação local e a tira do desfazer.
- EQ07 Entrada tardia recebe o estado atual; saída libera as reservas.
- EQ08 Descoberta por UDP acha o servidor.
- EQ09 Desfazer passa por todos.
- Interface: compartilhar, entrar e ver as reservas na planta.

## 9. Como ficou
- Núcleo em `brasbim/core/collab/`: `protocol.py` (mensagens, `reservable`, `discover`,
  `local_addresses`), `server.py` e `client.py`. O `History` ganhou `guards` (recusa
  antes de aplicar, também no desfazer e no refazer), `replay` (aplica fora das pilhas,
  só no diário) e `notify`. As transações de outras pessoas avisam com o tipo `remote`.
- Também não são reservadas as operações cujo `id` é o `IfcProject` (camadas padrão,
  penas, perfil municipal, informações do projeto): se não ficassem livres, quem mexesse
  nas penas travaria as camadas de todos. Conflito nelas é recusado pela verificação de
  estado do servidor.
- `Session`: `share`, `join`, `leave`, `poll`, `request_release`, `release`,
  `answer_request`. Novo, Abrir e Recuperar saem antes do compartilhamento.
- Janela: menu **Equipe** (Compartilhar…, Entrar…, Pedir liberação da seleção, Liberar a
  seleção, Liberar minhas reservas, Mostrar reservas, Sair); painel **Equipe**;
  "Compartilhado · n pessoas" na barra de estado; título "(projeto) (compartilhado)"
  para quem entrou; **Pedir liberação a <nome>** no botão direito sobre o elemento de
  outra pessoa; contorno na cor da dona na planta (`PlanView._draw_reservations`). O
  nome digitado fica guardado nas preferências.
- A rede é lida a cada 40 ms (`QTimer`), na thread da interface. O servidor roda em
  threads do mesmo processo de quem compartilha.
- Medido nesta máquina, com dois processos e o IP da rede (192.168.x): descoberta em
  ~1 s, entrada em 0,02 s, parede de um aparece no outro no ciclo seguinte.
- Testes: `tests/test_projeto_compartilhado.py` (EQ01–EQ10, rede de verdade em
  127.0.0.1) e `tests/test_interface_projeto_compartilhado.py` (duas janelas).

## 10. Pontos para revisão
(a) Liberar ao desconectar, e não guardar a reserva para quando a pessoa voltar.
(b) Pedido atendido passa a reserva direto para quem pediu.
(c) Junções de paredes e configurações do projeto não são reservadas.
(d) Sem senha; só rede local.
(e) O servidor roda dentro do BrasBim de quem compartilha: se essa pessoa fechar, todos
    ficam com cópias. Um servidor separado (sem janela) fica para depois, se fizer
    falta.

## Fontes
| Código | Documento | Uso |
|---|---|---|
| AC-COL | Graphisoft Help, visão geral da reserva (spec/REQUISITOS.md §13); nota `research_notes/.../archicad_documentacao_colaboracao.md` §3 (F203, F204 no relatório) | criar livre, editar exige reserva, autorreserva, pedido, estado ao vivo |
| REV-COL | Autodesk Revit Help, empréstimo de elementos (spec/REQUISITOS.md §13); nota `revit_documentacao_colaboracao.md` §3 | empréstimo automático do sem dono, pedido ao dono |
| RFC 8259 | JSON, https://www.rfc-editor.org/rfc/rfc8259 | formato das mensagens |
