---
documento: Interface — painel de propriedades deitado (em blocos lado a lado)
requisito: RF-UI-02
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-14
status: aprovado
revisor: OTTO (aprovado em 2026-10-14)
---

# Painel de propriedades deitado

## 1. Propósito
Retorno de uso do revisor (2026‑10‑14): com o painel Propriedades encaixado no topo (ou na
base) da janela, ele fica largo e baixo, e os campos de baixo só aparecem rolando. Pedido:
redistribuir as propriedades em **blocos lado a lado** quando o painel está deitado.

O revisor mostrou, como ideia, a captura de outro programa com propriedades em blocos
numa faixa. Desta captura vale só o **conceito funcional** (grupos de campos lado a lado
numa faixa baixa), que é conhecimento geral de interfaces. O agrupamento, os nomes, a
ordem e o desenho dos blocos são os do BrasBim (specs 0.1 §7, 0.2 §9, 0.3 §4.3); nada do
layout daquele programa é copiado. *(cleanroom/PROCESSO.md §2 e §3.4)*

O **conteúdo** do painel não muda: só a disposição.

## 2. Dois arranjos
| Arranjo | Quando | Como |
|---|---|---|
| **Em pé** (atual) | Painel nas laterais, ou solto mais alto que largo | Grupos um abaixo do outro, campo com o nome à esquerda; rolagem vertical se precisar |
| **Deitado** (novo) | Painel no topo ou na base, ou solto com largura ≥ 2 × altura | Grupos em **blocos lado a lado**; rolagem horizontal se precisar |

O arranjo é escolhido sozinho, pela proporção do painel, e muda na hora ao encaixar o
painel em outra borda ou redimensioná-lo. *(decisão do projeto)*

## 3. Arranjo deitado
```
┌ Parede ────────────┬ Altura ──────────────────┬ Geometria e quantidades ─────────────────┬ Identificação ─┐
│ Tipo [Alvenaria ▾] │ Base   [0,00]            │ Comprimento 6,00   Área bruta 16,80      │ GlobalId …     │
│ Ref. [Face esq. ▾] │ Topo   [Pav. de cima ▾]  │ Espessura   0,14   Área líquida 15,10    │ Origem BrasBim │
│ ☐ Inverter camadas │ Desloc. [0,00]           │ Altura      2,80   Volume 2,11           │                │
└────────────────────┴──────────────────────────┴──────────────────────────────────────────┴────────────────┘
```
(desenho esquemático)

- Cada grupo do arranjo em pé vira um **bloco**: título em cima, campos embaixo, com o nome
  do campo à esquerda, como no arranjo em pé.
- **Linhas por bloco:** quantas couberem na altura do painel (no mínimo 1). Um bloco com
  mais campos que linhas se divide em **colunas** dentro do próprio bloco (o 4º campo vai
  para a 2ª coluna quando cabem 3 linhas), em vez de crescer para baixo.
- Blocos separados por uma linha vertical fina; a ordem é a dos grupos no arranjo em pé.
- O primeiro bloco leva o título do painel (ex.: "Parede", "3 elementos selecionados") e os
  campos que vêm antes do primeiro grupo.
- Botões (ex.: Inverter sentido, Editar tipo…) ocupam uma linha do bloco, como um campo.
- Avisos longos (ex.: porta de outro programa) ficam num bloco próprio, com quebra de
  linha.
- Campos de edição com largura compacta (números: cerca de 8 caracteres; listas: o maior
  item, até 22 caracteres) para os blocos não ficarem largos demais.
- Mudar o tamanho do painel refaz a divisão em linhas e colunas sem perder o que está
  sendo digitado (a reorganização espera o campo perder o foco).

## 4. Organização do código *(decisão do projeto)*
Em `brasbim/ui/properties.py`, os campos passam a ser montados primeiro como uma lista de
grupos (título + linhas) e depois desenhados num dos dois arranjos. A conta de linhas e
colunas por bloco fica numa função sem Qt (`block_grid(n_campos, linhas)`), com teste.

## 5. Critérios de aceite (testes)
- [ ] **UI37** Com o painel na lateral, a parede selecionada aparece em pé, como antes
      (os testes UI07 e UI27 continuam passando).
- [ ] **UI38** Encaixar o painel no topo com uma parede selecionada: os grupos ficam lado a
      lado, sem rolagem vertical; com altura para 3 linhas, o bloco "Quantidades"
      (6 campos) tem 2 colunas de 3.
- [ ] **UI39** No arranjo deitado, mudar a base da parede no campo gera o mesmo
      `wall.edit` do arranjo em pé.
- [ ] **UI40** `block_grid`: 6 campos em 3 linhas → posições (0,0) (1,0) (2,0) (0,1) (1,1)
      (2,1); 2 campos em 3 linhas → 1 coluna; altura para 0 linhas → 1 linha.

## 6. Fontes públicas
- **RF** — `spec/REQUISITOS.md` (RF-UI-02).
- **UI01–UI03** — specs 0.1 §7, 0.2 §9 e 0.3 §4.3 (aprovadas).
- **QT** — documentação pública do Qt for Python 6: `QDockWidget.dockLocationChanged`,
  `QGridLayout`, `QScrollArea`.
- **CG** — conhecimento geral de aplicativos de desktop: painéis que se reorganizam
  conforme a borda em que estão encaixados.

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

## 7. Pontos de revisão
(a) Troca automática pela proporção do painel (§2), sem opção manual.
(b) Divisão em colunas dentro do bloco, em vez de blocos inteiros empilhados (§3).
