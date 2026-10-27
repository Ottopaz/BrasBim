---
documento: Ajustes curtos do pente fino (bloco 1)
requisito: reports/Pente fino BrasBim x pesquisa.md §5 ("Ajustes curtos, a qualquer momento")
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-27
status: em revisão (§2–§9 implementados para teste)
revisor: OTTO
---

# Ajustes curtos do pente fino

## 1. Propósito
O revisor aprovou (2026‑10‑27) fazer primeiro o bloco de ajustes curtos do pente fino e
depois o pacote do projeto legal. São oito ajustes, cada um conferido com a pesquisa
pública (`reports/Pesquisa Archicad Revit AutoCAD.md` e notas em `research_notes/`).

## 2. Código curto das portas
- O tipo de porta ganha o campo **Código** (`code`), como o da janela (spec/ui 09): vai no
  `Reference` do `Pset_DoorCommon` do tipo e das portas; vazio = nome sem o sufixo de mão
  (comportamento de antes). A variante de mão recebe o mesmo código.
- Biblioteca do projeto novo: P1, P2, P3. Diálogo de tipos de porta: campo Código.
- Mudar o código (ou o nome, sem código) do tipo de porta **ou de janela** troca o
  `Reference` das esquadrias que usavam o código antigo; as com código próprio ficam
  (antes, as já colocadas ficavam com o código velho — falha que valia também para as
  janelas).

## 3. Clique duplo maximiza a vista no lado a lado
- No Exibir > Lado a lado, cada vista tem uma faixa de título ("Planta", "3D"). **Clique
  duplo na faixa** maximiza aquela vista; outro clique duplo volta às duas metades.
- Não é dentro da vista porque lá o clique duplo já é das ferramentas (fechar polígono,
  editar texto). Padrão do Rhino [RHINO-WIN]; a pesquisa aponta que é barato e ajuda a
  alternar entre 2D e 3D (interface §viewports).

## 4. Vistas 3D padrão
- Exibir > **Vista 3D padrão**: Topo, Frente (sul), Fundos (norte), Lateral esquerda
  (oeste), Lateral direita (leste) e as quatro isométricas (sudoeste, sudeste, nordeste,
  noroeste, a 35,26°). Cada uma enquadra tudo; com a planta à frente, passa para o 3D.
- Botão direito no vazio do 3D: Enquadrar tudo, Vista de topo, Isométrica.
- A projeção continua em perspectiva; projeção paralela fica para depois (ponto (c)).
- Nomes próprios em pt‑BR, pelos pontos cardeais (o norte do projeto é +Y).

## 5. Arrastar objeto da biblioteca para a planta
- Arrastar um tipo do painel Biblioteca de objetos e soltar na planta carrega o tipo (se
  ainda não estiver no projeto) e insere o objeto no ponto solto, com a atração de
  sempre; a ferramenta Objeto fica ativa com esse tipo, para inserir outros.
- Sem fantasma durante o arrasto (ponto (d)). O clique duplo continua como antes.

## 6. Pegar todas as curvas de uma camada (terreno)
- Na mini-barra do terreno, Pegar linhas com **Shift** pega todas as linhas da camada da
  linha sob o cursor, cada uma com a cota que veio do DWG; a prévia destaca todas e o
  rótulo diz "N linhas da camada". Uma transação só (um desfazer).
- Camada = a anotação do desenho importado (uma por camada do arquivo, spec/ui 22); para
  linhas desenhadas no BrasBim, a camada de exibição (spec/ui 18).
- Linhas que já estão no terreno ficam de fora (como antes).

## 7. Ferramenta Medir
- Grupo **Edição** da barra, Editar > **Medir**, apelido `MD`.
- Cliques fazem uma cadeia de pontos, com atração; a prévia mostra cada trecho e, junto
  ao cursor, o total e, a partir de três pontos, a área e o perímetro do polígono. Tab
  digita distância e ângulo do próximo ponto.
- **Enter**, clique duplo ou botão direito encerra: "Medida: 7,00 m (4,00 + 3,00)".
  Clicar no **primeiro ponto** fecha: "Medida: área 12,00 m², perímetro 14,00 m".
- **Shift+clique** num elemento (sem cadeia em andamento) mede o contorno dele: o maior
  contorno fechado na planta (área e perímetro) ou, numa anotação aberta, o comprimento.
- O resultado vai para a barra de estado (junto da dica) e para o painel Mensagens. O
  painel ganhou **Copiar** (Ctrl+C e botão direito): copia as mensagens escolhidas, ou a
  última, sem a hora. Não cria nada no modelo.
- É o "medir" dos auxílios de tela do Archicad [AC-TRACKER]; nomes e textos próprios.

## 8. Contas e coordenadas no quadro de medidas
- Os campos aceitam contas, analisadas pelo analisador das fórmulas dos objetos
  (`core/objects/formula.py`, sem `eval`): `1,20+0,15`, `(3-0,15)/2`.
- **Operador no início** faz a conta com o valor medido (o do cursor, ou o fixado):
  `+0,15`, `-0,15`, `*2`, `/3`. **Operador no fim** também: `2*` dobra o medido.
- `-` no início é número, não conta, nos campos que aceitam valor negativo: ângulos,
  X/Y do pilar, cotas e afastamento da cota (`Field.negative`).
- **`x5 y3`** (também `x5;y3`) em qualquer campo é um ponto absoluto do pavimento: vale
  como clique exato, sem atração (o mesmo da linha de comando `5;3`, spec/ui 24).
- O campo único das alças (sem Tab) aceita contas e `x5 y3` também.
- Padrão do Tracker do Archicad (operadores + − * / e atalhos X/Y) [AC-TRACKER].

## 9. Cópia em série
- Em Copiar, depois do ponto de base, o quadro de medidas tem três campos: Distância,
  Ângulo e **Cópias**. Com Cópias = N, o clique (ou Enter) faz N cópias com o mesmo passo:
  a k‑ésima deslocada k × o vetor (`transform.copy_series`, uma transação só). A prévia
  mostra as N (até 50).
- `x5` no campo de distância fixa 5 cópias sem confirmar o ponto; o próximo clique faz
  as cópias. O número vale para os próximos cliques até Esc. Máximo 1000.
- Matriz polar e ao longo de caminho ficam para depois. Matriz é recurso clássico do
  AutoCAD; a pesquisa não trouxe a página da Ajuda, então fica como conhecimento geral
  (CG).

## 10. Critérios de aceite (testes)
- [x] **PO21** Tipo de porta com código P1: `Reference` P1 no tipo e na porta; mudar para
      PA troca o da porta; desfazer volta; a variante de mão leva o código.
- [x] **AJ02** Lado a lado: clique duplo na faixa do 3D deixa a planta com largura 0; de
      novo, duas metades; voltar às abas e ao lado a lado funciona.
- [x] **AJ03** Vista de topo: câmera na vertical sobre o centro do modelo; Frente: olha
      do sul; Isométrica nordeste: as três direções iguais; menu do vazio no 3D.
- [x] **AJ04** Soltar a "Cama de casal" na planta em (3, 2): objeto criado no ponto,
      ferramenta Objeto ativa.
- [x] **AJ05** Terreno: Shift sobre uma curva do DWG destaca as 3 da camada CURVAS; o
      clique põe as 3 com as cotas 100, 101 e 102; um desfazer tira as 3.
- [x] **AJ06** Medir: cadeia (0,0)–(4,0)–(4,3) + Enter dá "7,00 m (4,00 + 3,00)";
      fechar o retângulo 4 × 3 dá área 12,00 m² e perímetro 14,00 m; Shift+clique numa
      parede mede o contorno; nada entra no histórico; Copiar devolve o texto sem a hora.
- [x] **AJ07** `parse_entry`: `1,20+0,15`, `2*`, `+0,15`, `-0,15`, `-30` em campo com
      sinal, `/3`, `*2`, `x5 y3`, `x5`; recusa `2+` sem medida, texto, divisão por zero e
      comparação. Na parede: `2*` com 2 m medidos dá 4 m; `1,20+0,15`; `x5 y3` termina
      em (5, 3).
- [x] **AJ08** Copiar com Distância 2, Ângulo 90 e Cópias 3: paredes em y = 0, 2, 4, 6;
      um desfazer volta a uma; `x4` só fixa e o clique a 1,5 m faz 4 cópias.

## 11. Fontes
| Código | Documento |
|---|---|
| RHINO-WIN | McNeel, *The Rhino window* (Rhino 8, docs.mcneel.com), citado em `research_notes/.../interface_e_interacao.md` |
| AC-TRACKER | Graphisoft, *Tracker* (Archicad 28, help.graphisoft.com), citado em `research_notes/.../archicad_modelagem.md` |

Conhecimento geral (CG): matriz/cópia em série, vistas ortogonais e isométricas. Nenhum
material de `_restrito/` nem de `tools/` foi usado; nomes, textos e layout são próprios.

## 12. Pontos de revisão
(a) Código curto: vazio continua sendo o nome sem o sufixo de mão (§2).
(b) Maximizar pela faixa de título, não por clique duplo dentro da vista (§3).
(c) Vistas padrão em perspectiva; projeção paralela depois (§4).
(d) Arrastar sem fantasma; o objeto entra no ponto solto (§5).
(e) Camada das linhas desenhadas no BrasBim = camada de exibição (§6).
(f) Medir mede o maior contorno fechado do elemento (numa parede, o contorno do trecho
    cortado na planta), não as quantidades do IFC (§7).
(g) `-` no início é conta nos campos sem sinal e número nos com sinal (§8); `x5` sozinho
    só vale em Copiar (fora dele, a recusa sugere `x5 y3`).
(h) O número de cópias continua valendo nos próximos cliques até Esc (§9).
