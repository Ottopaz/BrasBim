---
documento: Tabela de penas (cores e espessuras do desenho)
requisito: RF-DOC-03 (complemento)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-26
status: em revisão (implementado para teste, fluxo do MVP)
revisor: OTTO
---

# Tabela de penas

## 1. Propósito
Hoje as espessuras e as cores do desenho estão fixas no programa (série da NBR 8403 por
tipo de linha). O revisor pediu um quadro para o usuário controlar **cores e espessuras
das penas**, como se faz no AutoCAD (estilo de plotagem) e no Archicad (conjunto de
penas). A tabela de penas dá esse controle sem mudar o modelo: é só a representação.

## 2. Conceitos
- **Pena**: número (1, 2, 3…), **cor** e **espessura** no papel (mm), com uma descrição
  livre ("corte grosso", "a demolir").
- **Categoria de linha**: o papel que a linha tem no desenho. Cada categoria aponta para
  uma pena:

| Categoria | Pena padrão |
|---|---|
| Elementos cortados (contorno) | 5 · 0,50 |
| Divisa entre camadas | 2 · 0,18 |
| Elementos em vista | 3 · 0,25 |
| Acima do plano de corte (tracejado) | 2 · 0,18 |
| Pavimento de baixo | 8 · 0,13 cinza |
| Portas e janelas | 3 · 0,25 |
| Giro de portas e folhas | 7 · 0,13 cinza escuro |
| Mobiliário e objetos | 7 · 0,13 cinza escuro |
| Cotas | 1 · 0,13 |
| Textos e etiquetas | 3 (só a cor) |
| Linhas e desenho 2D | 2 · 0,18 |
| Eixos de projeto | 1 · 0,13 |
| Símbolos (norte, nível, corte e fachada) | 4 · 0,35 |
| Projeção da cobertura | 2 · 0,18 |
| Terreno | 1 · 0,13 |
| Desenho importado | 8 · 0,13 cinza |

- **Tabela de penas**: as penas e as categorias, com nome ("Padrão", "Prefeitura — P&B")
  e a opção **Imprimir em preto** (pranchas e PDF saem só em preto; a tela continua com as
  cores). O projeto pode ter várias tabelas; uma é a **da janela**.
- A tabela padrão reproduz o desenho de hoje: abrir um arquivo antigo não muda nada.

## 3. Regras de desenho
- A linha de uma categoria sai com a **cor da pena**. A espessura sai **proporcional**: a
  categoria tem uma espessura de referência (a da tabela padrão); se a pena da categoria
  é o dobro dela, todas as linhas da categoria engrossam o dobro. Assim um símbolo com
  traços de espessuras diferentes (corte: 0,5 / 0,35 / 0,13) continua com as proporções.
- O que o usuário escolheu num elemento ou num tipo continua valendo na proporção: uma
  linha 2D de 0,35 mm desenhada à mão continua mais grossa que as de 0,18.
- Cor própria de um tipo de parede (diferente da cor padrão) vence a cor da pena.
- Hachuras e manchas de material seguem as cores do material e do tipo (não mudam com a
  tabela, por enquanto).
- Seleção, prévias e marcadores continuam nas cores da interface.
- Vale na planta (tela), nos cortes e fachadas, nas pranchas e no PDF. O 3D não muda.

## 4. Na interface
- **Projeto > Tabelas de penas…**: quadro com a tabela escolhida no alto (**Nova**,
  **Duplicar**, **Renomear**, **Excluir**, **Usar na janela**), a aba **Penas** (número,
  cor, espessura, descrição; **Adicionar pena**, **Tirar a última**) e a aba **Categorias**
  (cada categoria com a lista das penas). **Imprimir em preto**. OK grava tudo numa
  transação "Editar tabelas de penas".
- **Exibir > Tabela de penas ▸** troca a tabela da janela.
- A **vista salva** (spec/ui 25) guarda a tabela de penas; a prancha desenha a vista com
  ela. Planta e cortes postos direto na prancha usam a tabela da janela.

## 5. IFC
Pset `BrasBim_Penas` no `IfcProject`, `Parametros` em JSON::

    {"current": "<id>", "tables": [{"id": "<id>", "name": "Padrão", "print_black": false,
      "pens": {"1": {"color": "#23272A", "weight": 0.13, "note": ""}, ...},
      "categories": {"cut": 5, "layer": 2, "view": 3, ...}}]}

Operação `pens.edit` (antes/depois da configuração inteira; desfazer volta). Sem o Pset,
vale a tabela padrão (não é gravada até ser mudada).

## 6. Critérios de aceite (testes)
- [x] **PN01** Sem configuração, a tabela padrão; editar penas e categorias grava o Pset;
      desfazer volta; salvo e reaberto, igual; validação (cor, espessura > 0, pena
      existente).
- [x] **PN02** Planta: a cor e a espessura (proporcional) das paredes cortadas, das cotas e
      do desenho 2D seguem a pena da categoria; a tabela padrão dá o mesmo desenho de antes.
- [x] **PN03** Vista salva com outra tabela: a prancha usa a tabela da vista; "Imprimir em
      preto" deixa as linhas pretas na prancha.
- [x] **PN04** Interface: o quadro edita cor e espessura de uma pena e a pena de uma
      categoria; Exibir > Tabela de penas troca a tabela da janela.

## 7. Fontes
- Pesquisa do projeto: `autocad.md` (estilos de plotagem CTB por cor e STB por nome;
  espessura por camada); `normas_e_projeto_legal_brasil.md` (espessuras de pena no plot,
  CTB/STB e conjuntos de penas no contexto ABNT: **sem fonte** nesta rodada);
  `archicad_documentacao_colaboracao.md` (conjuntos de penas existem, sem página oficial
  lida: **conferir**); `revit_documentacao_colaboracao.md` (estilos de objeto e
  espessuras: sem fonte primária).
- Série de espessuras da NBR 8403 já usada no BrasBim (spec/ui 13 §8); conferência com o
  texto da norma continua pendente.
- Pedido do revisor (2026‑10‑26).
- Nenhum material de `_restrito/` nem de `tools/` foi usado. Nomes das categorias próprios.

## 8. Pontos de revisão
(a) espessura proporcional à de referência da categoria (em vez de trocar todas as linhas
    por uma espessura só);
(b) categorias da tabela (lista acima) e penas padrão;
(c) hachuras seguem o material, não a tabela;
(d) "Imprimir em preto" só nas pranchas e no PDF;
(e) penas por camada (como no AutoCAD) ficam para depois, junto com as regras gráficas
    por critério do item 2 do roteiro.
