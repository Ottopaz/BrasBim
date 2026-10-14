---
documento: Interface — edição de elementos, pavimentos e tipos (versão 0.2)
requisito: RF-NUC-04, RF-NUC-05, RF-UI-02, RF-PRJ-04, RF-TIP-01, RF-TIP-02
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-14
status: aprovado
revisor: OTTO (aprovado em 2026-10-14)
---

# Edição de elementos, pavimentos e tipos

## 1. Propósito
Completa a versão 0.1 (`spec/ui/01-janela-e-ferramentas.md`) com o que falta para
**modificar** um modelo sem precisar refazê-lo: alças de parede, dividir, mover, copiar,
girar, seleção por janela, pavimentos, tipos e edição de vários elementos de uma vez
(§11 da spec 0.1).

Valem os princípios da 0.1: a interface só chama comandos do núcleo; cada ação é **uma**
transação com desfazer; o que não depende de Qt fica no núcleo, com testes; sem ícones e
sem atalhos de uma letra.

**Nenhuma operação nova** entra no diário: mover, girar e alças viram `wall.edit` (caminho
novo) e `opening.edit`; copiar vira `wall.create`, `opening.create` e as operações de
criação da porta; dividir usa `wall.split`. As junções são recalculadas pela
`connections.sync_ops` na mesma transação. *(decisão do projeto: o formato de
`spec/01-modelo-de-dados.md` não muda)*

O refino geral da experiência de uso (aparência, organização da janela, fluxo das
ferramentas) **não** faz parte desta versão. Ele entra conforme as observações registradas
em `feedback/` (§9 da spec 0.1).

## 2. Barra de ferramentas

```
[Selecionar] [Parede] [Parede em arco] [Retângulo] [Porta] [Dividir] │ [Mover] [Copiar] [Girar] │ [Desfazer] [Refazer]
```
Mover, Copiar e Girar ficam desativados sem seleção. Novo menu **Projeto**: Tipos de
parede…, Tipos de porta… (§7).

## 3. Seleção (RF-NUC-04)

### 3.1 Janela e cruzamento
Na ferramenta Selecionar, arrastar a partir de um ponto vazio (ou de um elemento não
selecionado) por mais de 4 px desenha um retângulo:

| Sentido do arrasto | Retângulo | Seleciona |
|---|---|---|
| Da esquerda para a direita | Linha contínua | Elementos **inteiramente** dentro |
| Da direita para a esquerda | Linha tracejada | Elementos que **tocam** o retângulo |

- "Inteiramente dentro" e "tocam" usam o desenho do elemento na planta (`core/plan.py`).
- Sem Ctrl, o resultado substitui a seleção; com Ctrl, soma à seleção. *(CG)*
- Só elementos do pavimento ativo.

### 3.2 Arrastar a seleção
Arrastar um elemento **já selecionado** (fora das alças, §4) move a seleção inteira, como a
ferramenta Mover (§6.1), com o ponto pressionado como ponto de base. Quando a seleção é
uma porta só, vale o comportamento da 0.1 (deslizar na parede, mudar de parede).

## 4. Alças de parede (parede §5.1)
Cada parede selecionada mostra alças, quadrados pequenos de tamanho fixo na tela:

| Alça | Onde | Arrastar faz |
|---|---|---|
| Extremidade | início e fim do caminho | move só aquela extremidade |
| Meio (parede reta) | meio do caminho | desloca a parede paralelamente a si mesma |
| Meio (parede em arco) | meio do arco | muda a curvatura: o arco passa a passar pelo cursor |

A alça sob o cursor fica em destaque. Durante o arrasto, a pré‑visualização mostra a
parede e as vizinhas que acompanham, com o comprimento (extremidade) ou a distância
(meio) junto ao cursor. Soltar gera **uma** transação; Esc durante o arrasto cancela.

### 4.1 Extremidade
- O ponto segue o *snap* da 0.1; Shift prende a direção a múltiplos de 45° a partir da
  outra extremidade; um número digitado define o **comprimento** na direção atual.
- Parede em arco: o arco é refeito pelos três pontos (extremidade fixa, meio atual do
  arco, novo ponto).
- **Vizinhas em L acompanham:** a extremidade de outra parede que coincidia com a
  arrastada vai junto, e a junção se mantém. Com Ctrl pressionado ao soltar, só esta
  parede muda e a junção se desfaz. *(CG)*
- **Aberturas ficam no lugar:** ao mover o início, a distância de cada abertura ao início
  é corrigida para que ela não se desloque ao longo da parede. Se uma abertura deixar de
  caber, a pré‑visualização fica vermelha e o soltar é recusado, com o motivo em
  Mensagens. **Ponto de revisão (a):** parede §6.3 permite abertura fora dos limites
  com aviso; aqui a interface impede, como no arrasto da porta.

### 4.2 Meio (parede reta)
- O deslocamento é sempre perpendicular à parede; um número digitado define a distância.
- **Vizinhas acompanham sem mudar de direção:**
  - vizinha em L: a extremidade comum vai para o cruzamento da linha da vizinha com a
    nova linha da parede (a vizinha estica ou encurta); se as duas forem colineares, a
    extremidade comum só acompanha o deslocamento;
  - vizinha em T que **chega** nesta parede: estica ou encurta pela própria direção até
    a nova linha;
  - com Ctrl ao soltar, nenhuma vizinha acompanha e as junções se desfazem.
- Se alguma vizinha ficasse com comprimento nulo ou invertido, ou deixasse uma abertura
  fora dos limites, o soltar é recusado.
- As aberturas da parede mantêm a distância ao início.

### 4.3 Meio (parede em arco)
O arco passa pelas duas extremidades (fixas) e pelo ponto do cursor. Ponto alinhado com
as extremidades é recusado (arco degenerado). Sem entrada numérica nesta versão.

## 5. Dividir parede (parede §5.1)
Ferramenta **Dividir**:
1. Com o cursor sobre uma parede, um marcador mostra o ponto de divisão (projeção do
   cursor no caminho, com o *snap* da 0.1) e as distâncias até as duas extremidades.
2. Um número digitado define a distância ao **início** da parede.
3. O clique divide (`split_wall`). Ponto que corta uma abertura fica em vermelho e o
   clique é recusado, com o motivo em Mensagens.
4. A ferramenta continua ativa para outras divisões; Esc volta para Selecionar.

## 6. Mover, copiar e girar (RF-NUC-05)
Agem sobre a seleção, no pavimento ativo. A pré‑visualização desenha o contorno dos
elementos na posição nova, em tracejado.

### 6.1 Mover
1. Clique o ponto de base; 2. clique o destino. *Snap*, Shift (45°) e entrada numérica
(distância na direção do cursor) como no desenho de parede.
- Paredes vão com suas aberturas e portas.
- As junções são recalculadas pela geometria nova: a parede movida se solta das vizinhas
  que ficaram e se liga às que passar a tocar. As vizinhas **não** esticam (para isso
  existe a alça de meio, §4.2). *(CG)*
- **Porta selecionada sem a sua parede:** o centro do vão desloca pelo mesmo vetor e a
  porta vai para a parede reta sob esse ponto (como soltar sobre outra parede, PO11).
  Sem parede ali, ou sem caber, a operação inteira é recusada.

### 6.2 Copiar
Igual a Mover, mas cada clique de destino cria uma cópia, numa transação por clique. A
ferramenta continua com o mesmo ponto de base até Esc.
- Cópias têm `GlobalId`s novos e usam os **mesmos tipos** do original.
- Parede copiada leva cópias das suas portas e aberturas.
- Porta copiada sem a sua parede vai para a parede reta sob o destino (como em §6.1).
- **Porta de outra origem** não é copiada: a operação é recusada com mensagem (o núcleo
  não sabe recriar o corpo dela numa porta nova). **Ponto de revisão (b).**

### 6.3 Girar
1. Clique o centro; 2. clique um ponto que dá a direção de referência; 3. clique a
direção final. Shift prende o ângulo a múltiplos de 15°; um número digitado é o ângulo
em graus (positivo no sentido anti‑horário).
- Paredes giram com suas aberturas e portas; junções como em Mover.
- Seleção só de portas: recusado ("gire a parede que contém a porta").
- Girar com cópia: fora desta versão.

### 6.4 Espelhar
Fora desta versão (pendência da porta: espelhar a parede preservando o lado físico das
camadas e o sentido das portas).

## 7. Pavimentos (RF-PRJ-04, parede §5.1)
O painel **Projeto** vira uma tabela com as colunas **Nome** e **Cota**, em ordem de cota,
e os botões **Novo pavimento** e **Excluir pavimento**.

| Ação | Comportamento |
|---|---|
| Ativar | Clique numa linha torna o pavimento ativo (●) |
| Renomear / mudar a cota | Clique duplo na célula; Enter confirma (`storey.edit`). A tabela se reordena pela cota. Paredes ligadas ao pavimento são refeitas (já previsto no núcleo) |
| Novo pavimento | Cria "Pavimento N" com cota = maior cota + 2,80 m e o torna ativo |
| Excluir pavimento | Só pavimento **vazio**; o último pavimento não pode ser excluído. Paredes de outros pavimentos com topo nele passam a **altura fixa** com a altura atual, na mesma transação (parede §5.1). Pavimento com elementos: recusado, com a quantidade de elementos na mensagem |

Altura própria do pavimento (RF-PRJ-04, "altura") fica para versão posterior.

## 8. Tipos (RF-TIP-01, RF-TIP-02)
Menu **Projeto > Tipos de parede…** e **Tipos de porta…** abrem uma janela com a lista de
tipos à esquerda (nome e quantidade de elementos que usam o tipo) e o editor à direita.

- Botões: **Novo**, **Duplicar**, **Excluir** (só tipo sem uso; o que estiver em uso
  mostra a quantidade e não é excluído), **Aplicar**.
- **Aplicar** grava todas as mudanças do tipo em **uma** transação (`wall_type.edit` ou
  `door_type.edit`); os elementos que usam o tipo são refeitos (RF-TIP-01).
- Fechar com mudanças não aplicadas pergunta se aplica ou descarta.

### 8.1 Tipo de parede
| Campo | Observação |
|---|---|
| Nome | Único entre os tipos de parede |
| Uso | Lista do `IfcWallTypeEnum` com nomes em pt‑BR (ex.: `SOLIDWALL` "parede maciça", `PARTITIONING` "divisória") |
| Camadas | Tabela da face esquerda para a direita: material (lista editável; nome novo cria o material), espessura, função (estrutural, acabamento, isolamento, sem função), prioridade. Botões para acrescentar, remover, subir e descer camada. Espessura total em leitura |

Mudar espessuras mantém a linha de referência de cada parede (parede §5.1).

### 8.2 Tipo de porta
Campos de porta §3.5: nome, operação (lista das operações suportadas, em pt‑BR), largura,
altura e base padrão, marco (espessura, profundidade), guarnição (espessura,
profundidade), espessura da folha e material do marco. A lista mostra só o tipo de
origem; a variante de mão (sufixo " (E)"/" (D)") acompanha as mudanças (porta §2.2) e não
aparece separada.

## 9. Edição em lote (RF-UI-02)
Com vários elementos selecionados, o painel de propriedades mostra uma seção por classe,
com a quantidade: "Paredes (3)", "Portas (2)".

- Cada seção tem os campos **editáveis** da 0.1 para a classe (§7.2 e §7.3 da spec 0.1),
  sem os de leitura e sem "distância ao início".
- Campo com o mesmo valor em todos os elementos mostra o valor; com valores diferentes,
  fica vazio com o texto "vários".
- Confirmar um campo aplica o valor a **todos** os elementos da classe numa transação só
  ("Editar 3 paredes"). Se o núcleo recusar para um deles, nada muda e a mensagem diz
  qual elemento e por quê.
- Botões Inverter sentido e Inverter dobradiças agem em cada porta.
- Leitura: comprimento total das paredes e quantidade por tipo.

## 10. Organização do código *(decisão do projeto)*
| Onde | O quê |
|---|---|
| `brasbim/core/transform.py` (novo) | `move_elements`, `copy_elements`, `rotate_elements`: montam as transações de §6 a partir de operações existentes; sem Qt |
| `brasbim/core/walls/commands.py` | `move_wall_end`, `offset_wall`, `bend_arc_wall` (§4), `edit_walls` (lote), `delete_storey` |
| `brasbim/core/fillings/commands.py` | `edit_doors` (lote) |
| `brasbim/core/plan.py` | Teste de "dentro" e "toca" retângulo para a seleção por janela |
| `brasbim/ui/tools.py` | Alças e janela na Selecionar; ferramentas Dividir, Mover, Copiar, Girar |
| `brasbim/ui/types_dialog.py` (novo) | §8 |
| `brasbim/ui/main_window.py`, `properties.py` | §7 e §9 |

## 11. Critérios de aceite (testes)
Mesmo método da 0.1: Qt sem tela, eventos simulados, verificação do IFC; partes do núcleo
com testes próprios, sem Qt.

- [ ] **UI14** Janela da esquerda para a direita seleciona só os elementos inteiros;
      da direita para a esquerda, também os que tocam; Ctrl soma.
- [ ] **UI15** Arrastar a extremidade de uma parede de um retângulo: a vizinha em L
      acompanha e as 4 junções L continuam; com Ctrl, a junção some. Desfazer volta tudo
      numa vez.
- [ ] **UI16** Arrastar o início de uma parede com porta: a porta não sai do lugar
      (distância corrigida); posição em que a porta não cabe é recusada.
- [ ] **UI17** Alça de meio num retângulo desloca um lado em 0,50 m (entrada numérica):
      os dois lados vizinhos esticam, as junções se mantêm e a parede movida tem o
      comprimento original.
- [ ] **UI18** Alça de meio de parede em arco: o arco passa pelo ponto solto; ponto
      alinhado é recusado.
- [ ] **UI19** Dividir: clique gera `wall.split`; digitar `1,2` divide a 1,20 m do início;
      ponto sobre a porta é recusado.
- [ ] **UI20** Mover duas paredes com porta por (2; 1): caminhos deslocados, porta com a
      mesma distância, junções com as paredes que ficaram removidas; 1 transação.
- [ ] **UI21** Copiar uma parede com porta duas vezes: 2 transações, `GlobalId`s novos,
      mesmos tipos; porta de outra origem recusa a cópia.
- [ ] **UI22** Girar um retângulo 90° em torno de um canto: junções mantidas, portas com a
      mesma distância; digitar `30` gira 30°.
- [ ] **UI23** Mover só uma porta para cima de outra parede reta troca a porta de parede;
      para o vazio, a operação é recusada.
- [ ] **UI24** Pavimentos: novo pavimento com cota maior + 2,80; mudar a cota refaz as
      paredes com topo nele; excluir pavimento vazio que é topo de paredes as converte em
      altura fixa com a mesma altura; pavimento com elementos não é excluído.
- [ ] **UI25** Tipo de parede: mudar a espessura de uma camada refaz as paredes do tipo
      numa transação, com a linha de referência no lugar; tipo em uso não é excluído;
      duplicar cria tipo com nome novo.
- [ ] **UI26** Tipo de porta: mudar a largura padrão não muda portas existentes; mudar a
      espessura do marco refaz as portas do tipo e da variante de mão.
- [ ] **UI27** Lote: 3 paredes com tipos diferentes mostram "vários"; escolher um tipo
      gera 1 transação com 3 `wall.edit`; altura fixa em 3 paredes idem.
- [ ] **UI28** Todos os diários de UI14–UI27, reaplicados num projeto novo, reproduzem o
      mesmo IFC (nenhuma operação nova, §1).

## 12. Fontes públicas
- **RF** — `spec/REQUISITOS.md` (RF-NUC-04, RF-NUC-05, RF-UI-02, RF-PRJ-04, RF-TIP-01/02).
- **PAREDE**, **PORTA** — `spec/elementos/parede.md` §5–§6 e `porta.md` §2–§6 (aprovadas).
- **UI01** — `spec/ui/01-janela-e-ferramentas.md` (aprovada).
- **IFC** — buildingSMART IFC 4.3: `IfcWallTypeEnum`, `IfcMaterialLayer` (`Category`,
  `Priority`), `IfcBuildingStorey`.
- **QT** — documentação pública do Qt for Python 6: `QTableWidget`, `QDialog`, eventos de
  mouse.
- **CG** — conhecimento geral de aplicativos de CAD: seleção por janela e por cruzamento
  conforme o sentido do arrasto, alças nas extremidades e no meio, mover/copiar/girar por
  ponto de base.

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

## 13. Pontos de revisão
(a) Alça de extremidade impede abertura fora dos limites, em vez de só avisar (§4.1).
(b) Porta de outra origem não pode ser copiada nesta versão (§6.2).
(c) Vizinhas em L e T acompanham as alças por padrão; Ctrl solta (§4.1, §4.2). Mover não
    estica vizinhas (§6.1).
(d) Janela × cruzamento pelo sentido do arrasto (§3.1).
(e) Ativar pavimento com um clique (na 0.1 era clique duplo) e cota do pavimento novo
    (§7).
(f) Girar sem cópia e espelhar fora desta versão (§6.3, §6.4).
(g) O que mais incomoda na experiência de uso da 0.1, para entrar antes ou depois destes
    recursos (§1).
