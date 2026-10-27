---
documento: Painel Projeto com ícones e abas que fecham
requisito: pedido do revisor em 2026-10-27 ("cortes e fachadas na barra lateral com ícones, para facilitar o acesso"; "fechar a aba depois de editar: a prancha 01 e a folha mestra ficam abertas e não há como fechar")
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-27
status: em revisão (fluxo do MVP: implementada junto, §6)
revisor: OTTO
---

# Painel Projeto com ícones e abas que fecham

## 1. Propósito
O painel Projeto já listava cortes, fachadas, vistas salvas, pranchas, folhas mestras e
tabelas, mas só como texto, numa lista única para cortes e fachadas. As abas da área
central só cresciam: abrir a prancha 01 e a folha mestra deixava as duas abertas para
sempre. Esta spec dá ícone e grupo a cada item do painel, mostra o que está posto em cada
prancha e faz as abas fecharem.

A pesquisa mostra os dois caminhos nos programas comparados: uma árvore única com
mapas de projeto, vistas, folhas e conjuntos [NAV-AC], e um navegador por abas que separa
tipos e só mostra os grupos que têm itens [RVT-26]. Em 2027 o navegador passou a mostrar,
dentro da folha, as vistas colocadas nela [RVT-27]. A nota da pesquisa sugere separar o
que é modelo do que é documentação [NOTA-RVT]. A solução aqui é própria: o painel
continua com as abas que já tinha, com grupos e ícones nos itens.

## 2. Painel Projeto
- **Cortes e fachadas** (aba ao lado de Vistas salvas) vira uma árvore com dois grupos,
  **Cortes (n)** e **Fachadas (n)**, cada um com o ícone da ferramenta. Grupo vazio não
  aparece [RVT-26]. Clique seleciona o símbolo na planta; clique duplo ou Enter abre a
  aba. Grupo fechado continua fechado quando o painel é atualizado.
- **Vistas salvas:** ícone pelo que a vista mostra (planta, 3D ou corte).
- **Pranchas:** cada prancha tem o ícone de prancha e, dentro dela, os desenhos postos
  nela, na ordem em que entraram: "Planta · <pavimento>", o nome do corte ou da fachada,
  o nome da vista salva, cada um com seu ícone. Desenho cuja origem foi apagada não
  aparece. Clique duplo na prancha abre a prancha; num desenho, abre a origem dele (a
  planta do pavimento, a aba do corte ou a vista salva). Prancha aberta na árvore continua
  aberta ao atualizar. "Excluir prancha" com um desenho marcado exclui a prancha dele.
- **Folhas mestras** e **Tabelas:** ícone próprio em cada item.
- **Ícones novos** (próprios, traço 1,5 em 24 × 24, `scripts/gerar_icones.py`):
  prancha (folha deitada com carimbo), folha mestra (carimbo cheio, miolo tracejado) e
  tabela (grade).
- Item que abre e fecha na árvore usa o ícone sem a versão "ligada": a árvore do Qt
  desenha o item aberto nesse estado, que nos ícones do tema é a cor sobre o destaque e
  sumiria no fundo branco.

## 3. Abas que fecham
- Corte, fachada, prancha, folha mestra e tabela abrem em aba com o botão **×**.
  **Planta** e **3D** não têm o botão e não fecham.
- Formas de fechar: o **×**; **clique do meio** na aba; **Ctrl+W** (ou Ctrl+F4) e
  **Exibir > Fechar aba**, que fecham a aba à frente; **botão direito na aba**: Fechar,
  Fechar as outras abas, Fechar todas as abas; **Exibir > Fechar todas as abas**.
- Fechar não perde nada: tudo o que se edita numa aba já é operação do projeto (desfazer
  continua valendo). Pedir para fechar a Planta ou o 3D avisa que eles ficam sempre
  abertos.
- Fechar a aba do corte da vista salva ativa volta a janela à escala do corte (como
  "fechar a vista salva").
- As abas podem ser arrastadas para mudar a ordem. Lado a lado e a volta mantêm Planta e
  3D sem o botão.

## 4. Critérios de aceite (testes)
| Teste | Verifica |
|---|---|
| NV01 | Cortes e Fachadas em grupos com contagem e ícone; grupo vazio some; clique seleciona, clique duplo abre, grupo não abre nada; grupo fechado continua fechado; o ícone do grupo aberto é o mesmo do fechado; tabela com ícone |
| NV02 | A prancha lista planta, corte e vista salva postos nela, com ícone; clique duplo abre a prancha e cada origem; prancha aberta continua aberta; excluir pelo desenho exclui a prancha; desenho de origem apagada some |
| NV03 | Planta e 3D sem ×, as outras com; × fecha a folha mestra; clique do meio fecha a prancha; Ctrl+W fecha a aba à frente e recusa na planta, com aviso; Fechar todas deixa só Planta e 3D; reabrir funciona; lado a lado preserva |

Testes em `tests/test_interface_navegacao.py`.

## 5. Fontes
| Código | Documento |
|---|---|
| NAV-AC | Graphisoft Community, *Archicad Basic Concepts – The Navigator* (F184 da pesquisa; trecho de busca), via `research_notes/.../archicad_documentacao_colaboracao.md` |
| RVT-26 | BIMsmith, *Revit 2026* (F268), via `research_notes/.../revit_documentacao_colaboracao.md` §2 |
| RVT-27 | BIMpure, *Revit 2027* (F228), idem, "Folhas, carimbos e posicionamento" |
| NOTA-RVT | Inferência da pesquisa em `revit_documentacao_colaboracao.md` §2 (separar modelo de documentação) |
| RHINO | McNeel, *The Rhino window* (F374): botão direito na aba de vista abre comandos, via `interface_e_interacao.md` §3 |

Conhecimento geral (CG): abas fecháveis com ×, clique do meio e Ctrl+W são convenção de
interfaces com abas (navegadores, editores). Nada de `_restrito/` nem de `tools/`; nomes,
ícones e organização do painel são próprios.

## 6. Pontos de revisão
- (a) A árvore ficou nas abas que o painel já tinha. Uma árvore única "modelo |
  documentação" ([NOTA-RVT]) seria uma reforma maior do painel: fazer agora ou depois?
- (b) Clique duplo num desenho da prancha abre a **origem**. A alternativa é abrir a
  prancha com o desenho selecionado. Qual é mais útil?
- (c) As abas fechadas não são lembradas ao reabrir o projeto (nunca foram). Reabrir as
  abas da última sessão?
- (d) Pavimentos continuam na tabela de cima (com cota e plano de corte), sem ícone.
