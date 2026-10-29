---
documento: Barra de ferramentas — ícones isométricos, grupos e ferramentas de vista e documentação
requisito: pedido do revisor de 2026-10-29 (feedback/prints/barra de ferramentas.png, só como descrição de função)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-29
status: em revisão; §2 e §3 feitos, §4 a fazer
revisor: OTTO
---

# Barra de ferramentas

## 1. Propósito
O revisor achou os ícones de modelagem difíceis de reconhecer (desenhos em planta) e a
barra lateral comprida demais, sem separação entre modelar, gerar vistas e documentar.
Pedido: ícones isométricos simples, grupos separados (vistas à parte da documentação) e
as ferramentas que faltam em cada grupo, conferidas com o que Archicad, Revit e AutoCAD
fazem, para fazer do nosso jeito e melhor.

## 2. Ícones isométricos (feito)
- As ferramentas de modelagem (parede, porta, janela, vão, pilar, viga, laje, abertura de
  laje, cobertura, claraboia, escada, guarda‑corpo, terreno, objeto) passam a ter ícone em
  isometria; as de desenho 2D, vista e documentação continuam como símbolos planos.
- Regras de desenho, decididas com o revisor sobre prévias: o mínimo de linhas; porta =
  só a folha fechada com a maçaneta; janela e vão = parede plana de quatro linhas com a
  abertura, a janela com montante e travessa; cobertura = só as duas águas em trapézio,
  com inclinação baixa (na isometria uma água mais íngreme que a vista some atrás da
  cumeeira); escada = só pisos e espelhos; guarda‑corpo = corrimão, montantes e uma barra
  em linhas finas; faces laterais levemente sombreadas com `currentColor` (funciona no
  estado marcado, sobre o cobalto).
- Gerador próprio: `scripts/icones_isometricos.py` (sólidos e faces em 3D, projeção
  isométrica, linhas escondidas removidas com `shapely`), chamado por
  `scripts/gerar_icones.py`. Nenhum ícone de outro programa foi copiado ou decalcado: o
  print serviu só para a ideia de "ícone em isometria" e "porta = folha com maçaneta".

## 3. Barra dimensionável, com grupos (feito)
- A barra Ferramentas virou um **painel encaixável** (`ToolsBar`, `QDockWidget`, nome
  `barra_ferramentas`): puxar a borda muda quantos ícones ficam lado a lado (grade que
  acompanha a largura, `_Flow`); pode ir para qualquer borda ou flutuar; Exibir > Barras a
  mostra ou esconde. Começa à esquerda, numa coluna própria ao lado dos painéis da
  esquerda, com largura para dois ícones; com pouca altura aparece a barra de rolagem.
- **Selecionar** fica sempre no topo; depois os grupos recolhíveis **Modelagem | Vistas |
  Documentação | Edição** (Vistas = Corte e Fachada, que saíram da Documentação). Clicar no
  título recolhe ou mostra o grupo; os recolhidos ficam nas preferências
  (`ferramentas/recolhidos`). Abaixo de 90 px de largura o título vira só a seta (o nome
  fica na dica).
- A paleta de comandos ganhou o grupo Vistas.
- Testes UI29 (painel encaixável, lembrado), UI30 e UI34 (colunas pela largura, recolher,
  Vistas) em `tests/test_interface_barras.py`. A janela dos testes ficou 60 px mais larga
  (a coluna da barra estreitou a planta).

## 4. Ferramentas que faltam (a fazer, depois da pesquisa complementar)
- **Vistas:** já existem Corte e Fachada. Faltam Elevação interna, Detalhe, Folha de
  trabalho e Câmera (posicionar na planta e abrir em 3D).
- **Documentação:** já existem Cota, Nível, Cota de raio, Cota de ângulo, Texto, Rótulo,
  Hachura, Linha (em cadeia), Círculo, Arco, Curva, Norte e Alteração. Faltam Polilinha
  com arcos, Hotspot, Figura (imagem) e Desenho (pôr desenho na prancha como
  ferramenta).
- A pesquisa clean‑room não cobre esses temas (lacunas declaradas em
  `research_notes/.../archicad_documentacao_colaboracao.md`, linha 50;
  `revit_documentacao_colaboracao.md`, linha 55; `autocad.md`, linhas 132–135): antes da
  spec de cada ferramenta, fazer a pesquisa complementar dirigida em fontes públicas e
  registrar numa nota nova em `research_notes/`.

## 5. Fontes
Conhecimento geral (CG): projeção isométrica. Pedido e print do revisor
(`feedback/prints/barra de ferramentas.png`), usado só como descrição de função. Nada de
`_restrito/`.

## 6. Pontos de revisão
(a) Isometria só na modelagem; desenho 2D, vistas e documentação em símbolo plano (§2).
(b) Cobertura com inclinação baixa no ícone (§2).
(c) Nomes dos grupos: Modelagem, Vistas, Documentação, Edição (§3).
(d) Largura inicial de dois ícones; título do grupo só com a seta abaixo de 90 px (§3).
