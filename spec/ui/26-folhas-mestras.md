---
documento: Folhas mestras (tamanho, margens e carimbo desenhado pelo usuário)
requisito: RF-DOC-09 (complemento); pré-requisito do "perfil municipal" (roteiro, item 2)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-26
status: em revisão (implementado para teste, fluxo do MVP)
revisor: OTTO
---

# Folhas mestras

## 1. Propósito
Hoje a prancha tem formato A0–A4, margens fixas e um carimbo fixo. Cada escritório e
cada prefeitura pede um carimbo diferente. A **folha mestra** guarda o que se repete
em todas as pranchas que a usam: tamanho do papel, margens, quadro, marcas de dobra e o
**carimbo desenhado pelo usuário**, com textos que se preenchem sozinhos. Ao criar uma
prancha, o usuário escolhe a folha mestra.

## 2. O que a folha mestra guarda
- **Nome** ("A1 escritório", "A3 Prefeitura de Curitiba").
- **Papel**: A0, A1, A2, A3, A4 ou **personalizado** (largura × altura em mm);
  orientação horizontal ou vertical (nos formatos da série A).
- **Margens** esquerda, inferior, direita e superior (mm). Padrão da série A: 25 mm à
  esquerda (furação) e 10 mm (A0, A1) ou 7 mm (A2–A4) nas outras.
- **Quadro** na linha das margens (ligado) e **marcas de dobra** para A4 (ligadas).
- **Desenho do carimbo**: linhas (abertas ou fechadas, com espessura) e textos (altura,
  alinhamento, negrito), em mm do papel. O que é desenhado aparece em todas as pranchas
  da folha mestra.
- **Campos** dentro dos textos, entre chaves, preenchidos em cada prancha:

| Campo | Vira |
|---|---|
| `{projeto}` | nome do projeto |
| `{endereco}` | endereço da obra |
| `{proprietario}` | proprietário |
| `{responsavel}`, `{registro}` | responsável técnico e registro (CAU/CREA) |
| `{responsavel_tecnico}` | "responsável · registro", só o que existir |
| `{numero}`, `{titulo}` | número e título da prancha |
| `{escala}` | escalas das vistas da prancha ("1:50 / 1:100"; "—" sem vistas) |
| `{data}` | data da impressão |
| `{folha}`, `{total}` | posição da prancha e total de pranchas ("01", "05") |

  Texto com campos que ficaram todos vazios não aparece (assim "Proprietário:
  {proprietario}" some quando não há proprietário).

## 3. Folhas mestras prontas
**Nova folha mestra** começa de um formato (A0–A4, horizontal ou vertical, ou
personalizado) já com o **carimbo padrão** do BrasBim (o de hoje: 178 mm de largura,
para ficar à vista com a folha dobrada em A4) desenhado como linhas e textos com campos,
que o usuário apaga, move ou muda à vontade.

Prancha sem folha mestra continua como hoje (formato, orientação e carimbo padrão):
arquivos antigos abrem iguais.

## 4. Na interface
- Painel **Projeto**: a área das pranchas ganha abas **Pranchas | Folhas mestras**. Na
  aba Folhas mestras: **Nova…** (formato e orientação), **Duplicar**, **Excluir**;
  clique duplo abre a folha mestra numa aba de edição.
- **Nova prancha** pergunta o título e a **folha mestra** (as do projeto e, por último,
  "Padrão" A0–A4 sem folha mestra). No painel de propriedades da prancha, a folha mestra
  se troca a qualquer momento; formato e orientação só aparecem sem folha mestra.
- **Aba de edição da folha mestra**: o papel com o quadro e o tracejado das margens, e
  uma barra própria:
  - **Selecionar** (clique; Shift soma; arrastar move; Delete apaga; clique duplo num
    texto edita);
  - **Linha** (cliques nos pontos; Enter, clique direito ou clique duplo termina; Esc
    cancela) e **Retângulo** (dois cantos);
  - **Texto** (clique no lugar; o quadro pede o texto, a altura, o alinhamento, negrito e
    tem o botão **Inserir campo ▾**);
  - **Espessura** das linhas novas (série 0,13–0,7 mm);
  - **Papel e margens…** (nome, formato, tamanho, orientação, margens, quadro, marcas de
    dobra).
  - Os pontos atraem para a grade de 1 mm e para as pontas das linhas que já existem;
    a posição do cursor em mm aparece na barra.
- Excluir uma folha mestra em uso: as pranchas dela passam a ser "sem folha mestra", com o
  formato e a orientação da folha mestra (A3 se o papel era personalizado), na mesma
  transação; desfazer devolve.

## 5. IFC
- Folha mestra = `IfcAnnotation` "FolhaMestra" na edificação, sem representação, com o
  estado em JSON no Pset `BrasBim_FolhaMestra` (`Parametros`), como as pranchas.
- Operações: `sheet_master.create` / `.delete` (estado completo), `sheet_master.edit`
  (antes/depois dos campos). O desenho do carimbo é uma lista de itens no estado: mudar o
  desenho é um `sheet_master.edit` de `items` (desfazer desfaz o traço inteiro).
- Prancha: campo novo `master` (GlobalId ou `None`).

Estado::

    {"name": "A3 escritório", "format": "A3", "orientation": "landscape",
     "size": null, "margins": [25, 7, 7, 7], "frame": true, "fold_marks": true,
     "items": [{"kind": "line", "points": [[235, 7], [413, 7]], "closed": false,
                "weight": 0.25},
               {"kind": "text", "at": [238, 45], "text": "{projeto}", "height": 5.0,
                "align": "left", "bold": false}]}

## 6. Critérios de aceite (testes)
- [ ] **FM01** Criar, editar (papel, margens, itens) e excluir folha mestra; desfazer volta
      ao IFC anterior; salvo e reaberto, igual.
- [ ] **FM02** Folha mestra nova traz o carimbo padrão; numa prancha, os campos se
      preenchem (projeto, título, escala, folha/total, data) e o texto com campos vazios
      some; a prancha sem folha mestra mostra o mesmo carimbo de antes (PR04 continua).
- [ ] **FM03** Papel personalizado e margens: a prancha tem o tamanho e o quadro da folha
      mestra; a vista nova entra acima do desenho do carimbo.
- [ ] **FM04** Excluir folha mestra em uso: as pranchas ficam sem folha mestra na mesma
      transação; desfazer devolve.
- [ ] **FM05** Interface: Nova prancha com escolha da folha mestra; trocar a folha mestra
      no painel; PDF com o tamanho do papel da folha mestra.
- [ ] **FM06** Interface: na aba da folha mestra, desenhar linha e retângulo (atração na
      grade e nas pontas), texto com campo, mover, apagar e editar texto.

## 7. Fontes
- Pesquisa do projeto, `archicad_documentacao_colaboracao.md` §1: no Archicad, o *master
  layout* define o tamanho da folha; o que se desenha nele aparece em todos os layouts
  que o usam; o carimbo é desenhado com as ferramentas 2D e textos automáticos; cada
  layout escolhe o seu *master* — [Graphisoft Community, "Archicad Basic Concepts - The
  Navigator"](https://community.graphisoft.com/t5/Getting-started/Archicad-Basic-Concepts-The-Navigator/ta-p/303987)
  (trecho de busca; **conferir**).
- `normas_e_projeto_legal_brasil.md`: itens mínimos do carimbo segundo a NBR 6492
  (empresa, cliente, título, número, escala, local e data, autoria, responsável técnico,
  revisão) — [Gran Cursos – questões NBR 6492](https://questoes.grancursosonline.com.br/questoes-de-concursos/arquitetura-nbr-6492-representacao-de-projetos-de-arquitetura-429878)
  (trecho de busca; **conferir**). Carimbos por prefeitura: [PBH, Cartilha de
  Representação (2025)](https://prefeitura.pbh.gov.br/sites/default/files/estrutura-de-governo/politica-urbana/2025/cartilharepresentacaopbh_smpu_r5.pdf);
  [Curitiba – Manual do Autor](https://mid.curitiba.pr.gov.br/2020/00304554.pdf).
- `revit_documentacao_colaboracao.md`: carimbo como família própria com campos e
  sobrescrita do texto de escala em folhas com várias escalas.
- Pedido do revisor (2026‑10‑26). Formatos e margens da série A: spec/ui 15 §2 (CG).
- Nenhum material de `_restrito/` nem de `tools/` foi usado. Nomes dos campos próprios.

## 8. Pontos de revisão
(a) campos entre chaves com nomes em português sem acento;
(b) texto com todos os campos vazios some;
(c) excluir a folha mestra em uso deixa a prancha "sem folha mestra" (padrão A3 quando o
    papel era personalizado);
(d) logotipo (imagem) no carimbo fica para depois;
(e) coordenadas digitadas na aba da folha mestra (linha de comando) ficam para depois;
    por enquanto, grade de 1 mm e atração nas pontas.
