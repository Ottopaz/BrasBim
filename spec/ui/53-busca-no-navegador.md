---
documento: Campo de busca no Navegador
requisito: pedido do revisor em 2026-11-12 ("adicionar uma barra de pesquisas em nosso navegador")
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-11-12
status: em revisão (fluxo do MVP: implementada junto, §5)
revisor: OTTO
versão: 0.0.2
---

# Campo de busca no Navegador

## 1. Propósito
Com muitas pranchas, vistas e tipos de objeto, achar um item no Navegador obriga a rolar a
lista e abrir grupo por grupo. O revisor pediu um campo de busca no Navegador, como o que
existe no navegador em árvore de outro programa [NAV-AC]. A função é filtrar a árvore
pelo nome enquanto se digita; textos, ícone e comportamento abaixo são próprios.

## 2. Campo
- Fica entre o nome da seção e a lista, ocupando a largura do painel, com ícone de lupa
  próprio à esquerda, o texto de ajuda **"Filtrar pelo nome"** e o botão de limpar à
  direita (aparece quando há texto).
- **Ctrl+F** leva o cursor ao campo (abre o painel Navegador, se estiver fechado, e
  seleciona o texto que já houver). **Esc** no campo limpa o filtro; com o campo vazio,
  devolve o foco à vista.
- **Enter** no campo abre o primeiro item encontrado, como o clique duplo nele.
- O texto vale para todas as seções: trocar de seção mantém o filtro e o aplica à nova.
  É estado da janela (não vai para o IFC) e some ao fechar o projeto.

## 3. Filtro
- Filtra enquanto se digita. Não distingue maiúsculas nem acentos ("fachada" acha
  "Fachada Sul"; "terreo" acha "Térreo"). Várias palavras: o item precisa ter todas, em
  qualquer ordem ("sul 1:50").
- Nas árvores (cortes e fachadas, pranchas, objetos): um item cujo nome casa aparece com
  tudo o que está dentro dele (buscar "Fachadas" mostra todas as fachadas; buscar o nome
  de uma prancha mostra os desenhos postos nela). Um item que não casa aparece só se algo
  dentro dele casar, e então é aberto para mostrar o achado. Ao limpar o filtro, o que foi
  aberto pela busca volta a ficar fechado; o que o usuário abriu continua aberto.
- Nas listas (vistas salvas, folhas mestras, tabelas): fica só o que casa.
- O título da seção dá a contagem filtrada: **"Pranchas (2 de 5)"**; sem filtro, como
  hoje, "Pranchas (5)". As dicas da fileira de seções também mostram "x de n", para se
  ver em que outra seção há achados.
- Sem nenhum achado, aparece sob o campo **"Nada encontrado com «texto»."**.
- Mudanças no modelo (desfazer, criar, renomear) refazem a lista e o filtro continua
  aplicado.

## 4. Fora do escopo
- Busca no conteúdo dos elementos do modelo (paredes, portas): o Navegador lista vistas,
  documentos e tipos. A seleção por critério já tem a sua ferramenta (spec/ui 28).
- Expressões, curingas ou busca por propriedade.

## 5. Testes (`tests/test_busca_navegador.py`)
- **BN01:** com dois cortes e uma fachada, "fachada" deixa só o grupo Fachadas com a
  fachada; "FACHADA" e "fáchada" dão o mesmo; o título fica "Cortes e fachadas (1 de 3)";
  limpar volta tudo e o título a "(3)".
- **BN02:** a prancha fechada com um desenho que casa é aberta pela busca e volta a
  fechar ao limpar; a que o usuário abriu continua aberta.
- **BN03:** o filtro vale ao trocar de seção, sobrevive a `refresh()` (desfazer) e,
  sem achados, mostra o aviso; Enter abre o primeiro achado; Esc limpa.
- **BN04:** várias palavras precisam estar todas; Ctrl+F põe o foco no campo.

## 6. Fontes
- `research_notes/Pesquisa Archicad Revit AutoCAD/archicad_documentacao_colaboracao.md` §1
  (navegador em árvore com mapas) [NAV-AC].
- Pedido do revisor em 2026-11-12 (descrição de função, sem imagem nem texto de outro
  programa).
