---
documento: Assistente — pedido em texto, desenhado por uma IA instalada no PC
requisito: RF-IA-01 a RF-IA-04 (novos, ver §9)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-16
status: em revisão (protótipo implementado para teste)
revisor: OTTO
---

# Assistente (pacote 9)

## 1. Propósito
O usuário escreve um pedido dentro do BrasBim ("casa térrea de 3 quartos, uns 100 m²") e
uma **IA instalada no PC** desenha no modelo aberto, que é atualizado na tela enquanto a IA
trabalha. O resultado é um estudo inicial editável, feito com os mesmos elementos e
transações do desenho manual: paredes, portas, janelas, lajes e ambientes.

A IA fica fora do BrasBim: o usuário a instala e paga por ela. O BrasBim oferece
**ferramentas** com nome, descrição e argumentos, por um protocolo aberto (MCP). Assim,
qualquer IA compatível pode usá-las.

Fica de fora deste pacote (V1): outros conectores (modelo local como Ollama, chave de
API), verificação por norma (NBR 9050, código de obras), pavimentos, estrutura e
cobertura pela IA.

## 2. Fluxo
1. Exibir > Painéis > **Assistente** (Ctrl+Shift+A) abre o painel. Por padrão ele fica fechado
   (interface limpa).
2. O usuário escreve o pedido e clica em **Enviar**.
3. O BrasBim abre o **servidor MCP local** (§3.1), se ainda não estiver aberto, e inicia
   o **conector** (§3.2) com o pedido.
4. A IA chama as ferramentas (§4). Cada chamada roda na thread da interface como uma
   transação comum (`History.commit`): a planta, o 3D, os cortes e o painel são
   atualizados na hora. O painel lista o andamento ("• Desenhando os ambientes"; recusas
   em vermelho, com o motivo).
5. No fim, aparece a resposta da IA (texto simples) e "Concluído em N s". As transações
   do pedido viram **um passo de desfazer** ("Assistente: <começo do pedido>"), e a
   mensagem diz quantas alterações foram feitas. Se outra transação entrar no meio, nada é
   juntado.
6. **Parar** encerra a IA. O que já foi feito fica no modelo e, como no passo 5, entra
   num passo de desfazer.

### 2.1 Memória e contexto
- **Conversa:** o primeiro pedido abre uma conversa e o painel guarda o código dela (vem
  nos eventos do conector, `session_id`). Os pedidos seguintes continuam a mesma conversa
  (`--resume`): "agora aumenta a sala" se refere ao que foi feito antes. O status mostra
  "continuando a conversa".
- **Nova conversa** (botão) esquece os pedidos anteriores; o modelo fica como está.
  Abrir ou criar outro projeto também começa uma conversa nova, para a memória de um
  projeto não passar para outro.
- Se a conversa não puder ser retomada (o conector recusa), o painel avisa e o próximo
  pedido começa outra.
- **Contexto da tela:** cada pedido vai com uma linha antes do texto do usuário, com o
  pavimento ativo e o que está selecionado (tipo, id e, na parede, o eixo), por exemplo
  `[BrasBim] Pavimento ativo: "Térreo". Selecionado na tela: parede <id>, tipo
  Alvenaria 14, de [0.0, 4.0] a [5.0, 4.0].` "Essa parede" e "esta porta" se referem a
  isso. O painel mostra só o texto do usuário.
- O modelo é a memória que vale: o usuário pode ter mudado o desenho à mão entre os
  pedidos, então a IA relê o modelo (`describe_model`) antes de editar.
- **Seleção do resultado:** ao terminar, ficam selecionados os elementos que o pedido
  criou ou alterou no pavimento ativo (paredes, portas, janelas, lajes, pilares, vigas,
  ambientes), para o usuário ver o que mudou.

## 3. Conexão e segurança
### 3.1 Servidor MCP local
- JSON-RPC 2.0 sobre HTTP ("Streamable HTTP" na forma mais simples: resposta em
  `application/json`, sem fluxo SSE), métodos `initialize`, `tools/list`, `tools/call` e
  `ping`. Notificações recebem 202.
- Escuta **só em 127.0.0.1**, numa porta livre sorteada. Exige `Authorization: Bearer
  <token>`, com o token sorteado a cada abertura, e recusa `Origin` de fora do PC
  (proteção contra DNS rebinding). Sem token, a resposta é 401.
- O token vai ao conector num arquivo de configuração temporário, apagado ao fim do
  pedido.
- `initialize` devolve as **instruções** (§4.1), que valem para qualquer cliente MCP.
- Núcleo sem Qt (`brasbim/core/assistant/`): o mesmo servidor serve para uso sem
  interface (testes, outros clientes).

### 3.2 Conector Claude Code
- Programa `claude` encontrado no PATH. Se não houver, o painel diz "Claude Code não
  encontrado neste PC" e Enviar fica desativado.
- Modo não interativo: `claude -p` com o pedido pela entrada padrão,
  `--output-format stream-json`, `--strict-mcp-config --mcp-config <arquivo>`,
  `--allowedTools mcp__brasbim` e, a partir do segundo pedido, `--resume <conversa>`.
  As conversas ficam guardadas pelo próprio Claude Code, na pasta do usuário.
- **`--tools ""`**: nenhuma ferramenta própria do Claude Code. A IA não tem terminal nem
  acesso a arquivos e só mexe no modelo pelas ferramentas do BrasBim.
- Pasta de trabalho: a pasta temporária do sistema, para não ler instruções de projeto
  de outra pasta.
- Eventos lidos: `system/init` (modelo; avisa se o servidor `brasbim` não conectou),
  `assistant` (texto da IA) e `result` (erro e duração).

### 3.3 Privacidade *(ponto de revisão (c))*
O pedido e o que as ferramentas devolvem (descrição do modelo, imagem da planta) vão para
o fornecedor da IA escolhida. O modelo inteiro nunca é enviado, só o que a IA pede.
Modelos locais (V1) evitam isso.

## 4. Ferramentas
Coordenadas em metros, no sistema do pavimento (x para a direita, y para cima). Sem
`storey`, vale o pavimento ativo na tela. Tipos são escolhidos pelo nome, pelo começo do
nome ("P1", "J2") ou por um trecho dele; sem tipo, vale o primeiro em ordem alfabética.
Recusas do núcleo voltam para a IA como erro (`isError`) com o texto da recusa, para ela
corrigir.

| Ferramenta | Faz | Notas |
|---|---|---|
| `describe_model` | Lê o pavimento: tipos disponíveis, paredes (eixo, espessura), esquadrias (centro, largura, peitoril), ambientes (nome, área útil, contorno), lajes | Não altera |
| `layout_rooms` | Planta por ambientes (§4.2): paredes e ambientes | 1 transação por grupo de tipo de parede + 1 por ambiente |
| `create_walls` | Paredes retas soltas, pelo eixo por padrão; junções automáticas | `walls.commands.create_walls` |
| `insert_door` / `insert_window` | Porta ou janela pelo **centro**, na parede que passa pelo ponto (até 25 cm além da face); `opens_toward` = ponto do lado para onde a folha abre; janela com `sill` | Os mesmos comandos do desenho manual |
| `create_slab` | Laje pelo contorno | |
| `create_space` | Ambiente pelo cômodo fechado que contém um ponto, ou por contorno | |
| `delete_elements` | Exclui por id; paredes levam as esquadrias delas | `core/delete.py` (o mesmo da tecla Del) |
| `view_plan` | PNG da planta como na tela, com grade de 1 m e coordenadas nas bordas | Só no aplicativo (precisa do Qt) |

### 4.3 Edição
Para mudar o que existe, a IA edita em vez de apagar e refazer, e a identidade dos
elementos (`GlobalId`) se mantém:

| Ferramenta | Faz | Usa |
|---|---|---|
| `move_wall` | Desloca uma parede reta paralela a si mesma, `distance` na direção do ponto `toward`; as vizinhas em L e T esticam ou encurtam (`carry`, padrão sim). **Os ambientes acompanham:** os vértices deles que estão numa face da parede andam junto (ambientes não seguem paredes sozinhos) | `walls.commands.offset_wall` + `space.edit` na mesma transação |
| `edit_wall` | Tipo, altura fixa, pontas (`start`/`end`, levando as paredes ligadas) | `edit_wall`, `move_wall_end` |
| `edit_opening` | Novo centro (`at`, inclusive em outra parede), largura (o centro fica), altura, peitoril, tipo, lado de abertura, mão. Tipo novo sem largura e altura dadas: valem as do tipo novo | `fillings.commands.edit_door` |
| `edit_space` | Nome, número; `refit` redesenha o contorno pelas paredes em volta | `annotations.commands.edit_element`, `rooms.room_outline` |
| `set_type` | Troca o tipo de vários elementos de uma classe só | edições em lote de sempre |
| `move_elements` | Move ou copia (`copy`) pelo vetor | `transform.move_elements` / `copy_elements` |
| `rotate_elements` / `mirror_elements` | Gira (graus, anti-horário) ou espelha (com `copy`, mantém o original) | `transform` |

### 4.1 Instruções para a IA
Unidades, sentido dos eixos, paredes pelo eixo, ordem de trabalho (ler, ambientes,
portas e janelas, piso só quando o pedido é de uma edificação inteira), esquadrias pelo
centro, folga de 10 cm, portas abrindo para dentro do cômodo, editar em vez de refazer,
a linha de contexto `[BrasBim]`, reler o modelo antes de editar numa conversa
continuada, conferir antes de terminar e resposta curta em texto simples. O texto fica em `core/assistant/mcp.py`
(`INSTRUCTIONS`).

### 4.2 Planta por ambientes
- Cada cômodo é um retângulo **medido pelo eixo das paredes**: `x`, `y` (canto de menor
  x e y), `width` (em x) e `depth` (em y). Retângulos que se sobrepõem são recusados; os
  vizinhos se encostam *(ponto de revisão (b))*.
- A borda de um cômodo só vira parede **externa** (`exterior_type`). A borda dividida
  por dois cômodos vira parede **interna** (`interior_type`, padrão igual à externa) e
  entra uma vez. `open_between` lista pares de cômodos integrados, sem parede entre eles.
- Trechos alinhados e contíguos do mesmo tipo viram uma parede só, que passa pelas
  junções em T. Quando externa e interna têm o mesmo tipo, também se juntam.
- Ambiente: o retângulo recuado, em cada lado, da meia espessura da parede que está nele
  (área útil). Devolve a área de cada ambiente, a área construída e o contorno externo
  (face de fora), quando os cômodos formam um retângulo.

## 5. Interface
- Painel "Assistente" (encaixável, à direita, fechado por padrão): lista do andamento,
  campo do pedido com exemplo, status ("IA: Claude Code" / "Trabalhando… (modelo)" /
  "continuando a conversa") e os botões Nova conversa, Parar e Enviar.
- Cores só do tema: pedido em cobalto, resposta em grafite, ferramentas em cinza,
  recusas em vermelho.
- Ao terminar, se o desenho ficou fora da vista, a planta é enquadrada.
- Fechar o BrasBim encerra a IA e o servidor.

### 5.1 Ajustes da janela feitos junto (pedido do usuário, 2026-10-16)
- Exibir > **Painéis**: Projeto, Propriedades, Mensagens e Assistente. Antes, um painel
  fechado sem querer só voltava pelo botão direito na área das barras.
- Exibir > **Pavimento acima** (Page Up) e **Pavimento abaixo** (Page Down): trocam o
  pavimento ativo pelo teclado, sem passar do primeiro nem do último; a mensagem diz
  qual ficou ativo.
- Painel Projeto com largura mínima de 320 px: a coluna Nome aparecia cortada ("Su…",
  "T…"). A dica da linha explica o clique e as teclas.
- Diálogo de tipos: as linhas do formulário são apagadas pelo laço de eventos
  (`deleteLater`). O `removeRow` liberava duas vezes a memória de widgets em layouts
  aninhados, e a largura nova do painel Projeto fazia o UI91 cair de vez em quando.

## 6. Critérios de aceite (testes)
| Teste | Verifica |
|---|---|
| AS01 | Bordas comuns viram uma parede só; `open_between` tira a parede; sobreposição recusada |
| AS02 | `layout_rooms` cria paredes pelo eixo, junções e ambientes com a área útil (meia parede descontada) |
| AS03 | Porta e janela pelo centro, na parede certa, com o peitoril e o lado da folha pedidos; recusas voltam como erro e não entram no histórico |
| AS04 | O pedido vira um passo de desfazer (desfazer volta ao IFC de antes, refazer ao de depois); excluir leva as esquadrias; `describe_model` |
| AS05 | Protocolo: `initialize` (versão, instruções), `tools/list`, `tools/call`, notificação sem resposta, erros JSON-RPC |
| AS06 | Servidor só em 127.0.0.1; sem token, token errado ou `Origin` de fora → 401 |
| AS07 | Chamada vinda de outra thread roda na interface; o andamento aparece no painel; agrupamento e desfazer |
| AS08 | Eventos do Claude Code: servidor não conectado, texto, fim |
| AS09 | `view_plan` devolve PNG |
| AS10 | O Claude Code é chamado sem ferramentas próprias, só com as do BrasBim; painéis em Exibir > Painéis; Assistente fechado por padrão |
| AS11 | Edição: deslocar parede leva vizinhas e ambientes (áreas certas); esquadria muda largura mantendo o centro, vai para outra parede, troca tipo com o tamanho dele, peitoril e altura; troca de tipo de uma classe só; altura; `refit` do ambiente; mover, copiar, girar e espelhar |
| AS12 | A linha de contexto traz o pavimento ativo e a seleção (parede com eixo, ambiente com nome) |
| AS13 | Conversa: o código vem dos eventos, `--resume` nos pedidos seguintes, Nova conversa e outro projeto esquecem; o contexto da tela vai junto; ao fim, o que mudou fica selecionado |
| AS14 | Page Up / Page Down trocam o pavimento ativo, sem passar dos extremos |

Teste manual, feito em 2026-10-16 com Claude Code 2.1.301: pedido "casa térrea de cerca de
100 m² com 3 quartos (um suíte), banheiro social, sala e cozinha integradas e área de
serviço, com portas, janelas e piso". Resultado em 78 s e 24 chamadas: 98,8 m², 9
ambientes, 8 portas, 9 janelas e piso. Quando viu na imagem que um banheiro tinha ficado
sem janela, a IA refez a faixa dos quartos sozinha.

Teste manual da conversa (2026-10-16): (1) "sala de 4 × 4 m e, ao norte, quarto de 4 × 3
m, porta P1 para fora e P2 entre os dois" em 10 s; (2) "aumente a sala 50 cm para o sul",
sem dizer qual sala: `move_wall` na parede sul, laterais esticadas, sala de 14,90 para
16,83 m², em 8 s; (3) com a porta interna selecionada, "troque essa porta por uma de
correr": P2 → P3, em 8 s. Três passos de desfazer, um por pedido. O teste mostrou que a
troca de tipo deixava o vão com a largura antiga; já corrigido (§4.3, `edit_opening`).

## 7. Dados e IFC
Nada novo no arquivo: a IA usa as operações existentes. Só o histórico ganha
`History.squash(n, label)`, que junta as n últimas transações da pilha de desfazer. O
diário continua com cada uma.

## 8. Fontes públicas
- Model Context Protocol, especificação aberta (modelcontextprotocol.io): mensagens
  `initialize`, `tools/list`, `tools/call`, transporte Streamable HTTP, recomendações de
  segurança (escutar em localhost, validar `Origin`).
- JSON-RPC 2.0 (jsonrpc.org/specification).
- Claude Code, ajuda da linha de comando (`claude --help`) e documentação pública:
  `-p`, `--output-format stream-json`, `--mcp-config`, `--strict-mcp-config`, `--tools`,
  `--allowedTools`.

## 9. Pontos de revisão
a. Painel fechado por padrão e aberto pelo menu (Ctrl+Shift+A), ou em aba junto das
   Propriedades?
b. Cômodos medidos de eixo a eixo (simples para a IA) ou pelas faces internas (como se
   fala do cômodo)? A área útil devolvida já desconta as paredes.
c. Aviso de privacidade antes do primeiro pedido ("o pedido e partes do modelo vão para
   o fornecedor da IA")?
d. Próximos conectores: modelo local (Ollama) e chave de API. Em que ordem?
e. ~~Conversa com memória~~: feita (§2.1). Falta decidir se a conversa deve ser
   guardada junto do projeto, para continuar depois de fechar o BrasBim (hoje dura
   enquanto o programa está aberto).
f. Bloquear a edição manual enquanto a IA trabalha? Hoje uma edição no meio só impede
   que o pedido seja juntado num passo de desfazer.
g. Requisitos novos em `REQUISITOS.md`: RF-IA-01 (pedido em texto desenhado por IA
   instalada no PC), RF-IA-02 (ferramentas por protocolo aberto, sem depender de
   fornecedor), RF-IA-03 (tudo como transações comuns, desfeitas num passo) e RF-IA-04
   (a IA só acessa o modelo, sem terminal nem arquivos).
