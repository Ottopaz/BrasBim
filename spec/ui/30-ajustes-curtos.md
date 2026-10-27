---
documento: Ajustes curtos do pente fino (bloco 1)
requisito: reports/Pente fino BrasBim x pesquisa.md §5 ("Ajustes curtos, a qualquer momento")
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-27
status: em revisão (§2–§5 implementados para teste; §6–§9 a implementar, fluxo do MVP)
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

## 6. Pegar todas as curvas de uma camada (terreno) — a implementar
Na mini-barra do terreno, Pegar linhas aceita também "todas as linhas desta camada" do
desenho importado (clique numa linha + Shift), cada uma com a cota que veio do DWG.

## 7. Ferramenta Medir — a implementar
Distância (cadeia de pontos, com total), área e perímetro de um contorno clicado ou de
um elemento escolhido; resultado na barra de estado e no painel Mensagens, copiável. Não
cria nada no modelo. É "medir" dos auxílios de tela do Archicad [AC-TRACKER].

## 8. Contas e coordenadas no quadro de medidas — a implementar
Nos campos do quadro de medidas: `2*` (dobra o valor medido), `+0,15`, `-0,15`, `/3`,
`*2`, e expressões como `1,20+0,15`, com o analisador de fórmulas dos objetos (sem
`eval`). Coordenadas `x5 y3` (absolutas) no campo de comprimento. Padrão do Tracker do
Archicad (operadores + − * / e atalhos X/Y) [AC-TRACKER].

## 9. Cópia em série — a implementar
Em Copiar, o campo **Cópias** no quadro de medidas (`x5` no campo de distância também
vale): N cópias com o mesmo passo. Matriz polar e ao longo de caminho ficam para depois.
Matriz é recurso clássico do AutoCAD; a pesquisa não trouxe a página da Ajuda, então
fica como conhecimento geral (CG).

## 10. Critérios de aceite (testes)
- [x] **PO21** Tipo de porta com código P1: `Reference` P1 no tipo e na porta; mudar para
      PA troca o da porta; desfazer volta; a variante de mão leva o código.
- [x] **AJ02** Lado a lado: clique duplo na faixa do 3D deixa a planta com largura 0; de
      novo, duas metades; voltar às abas e ao lado a lado funciona.
- [x] **AJ03** Vista de topo: câmera na vertical sobre o centro do modelo; Frente: olha
      do sul; Isométrica nordeste: as três direções iguais; menu do vazio no 3D.
- [x] **AJ04** Soltar a "Cama de casal" na planta em (3, 2): objeto criado no ponto,
      ferramenta Objeto ativa.

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
