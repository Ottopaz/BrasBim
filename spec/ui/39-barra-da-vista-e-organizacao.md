---
documento: Interação — barra da vista, girar a vista, ocultar, travar, ordem de desenho e situação em um clique
requisito: RF-NUC-05 (edição), RF-DES-01 (planta); Fase 1 do plano das barras (2026-10-29)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-29
status: em revisão
revisor: OTTO
---

# Barra da vista e organização rápida

## 1. Propósito
Fase 1 do plano `reports/Plano barras e navegador (prints 2026-10-29).md` (itens 9, 20,
21, 31–41 e 46): o que se usa toda hora para olhar e organizar a planta, sem abrir
diálogo. Decisões do revisor (2026‑10‑29): travar **vai para o IFC**; ocultar fica **só
na sessão**; a ordem das fases é a proposta.

## 2. Barra da vista
- Faixa fina **sob a planta**, acima da linha de comando (spec/ui 24), da largura da
  vista. Também sob os cortes e fachadas (só os seletores que valem lá). Liga e desliga
  em Exibir > Barras, como as outras.
- Da esquerda para a direita, cada item é um botão com ícone próprio e o valor atual em
  texto; o clique abre a mesma lista do menu:
  1. **Zoom:** anterior, seguinte, enquadrar tudo e o valor em % (§2.1);
  2. **Giro da vista** (§3);
  3. **Escala** (sai da barra de estado; mesma regra de hoje com vista salva aberta);
  4. **Combinação de camadas** (spec/ui 18 §6);
  5. **Detalhe** da planta (Exibir > Detalhe);
  6. **Tabela de penas** (spec/ui 27);
  7. **Situação na vista** (spec/ui 31 §3);
  8. à direita, só quando há: **"N ocultos · Mostrar tudo"** (§4) e a chave
     **Escolher travados** (§5).
- Estilo de cotas, pavimento de referência e passo da grade entram na barra depois
  (plano, Fases 5 e seguintes).

### 2.1 Zoom anterior e seguinte
- Cada aba guarda até **20** enquadramentos (escala da tela + centro + giro). Um
  enquadramento novo entra quando o zoom ou o deslocamento param por 0,4 s (não a cada
  passo da roda), e também ao enquadrar tudo, enquadrar a seleção e mostrar na planta.
- **Anterior** e **seguinte** andam por essa lista; um enquadramento novo depois de voltar
  apaga os seguintes (como desfazer). Também no botão de trás/frente do mouse.
- **%**: 100% é o desenho do tamanho do papel na escala da vista, pelos pontos por
  polegada do monitor. A lista tem 25, 50, 100, 200 e 400%; digitar outro valor vale.
- É estado da janela: não vai para o IFC.

## 3. Girar a vista da planta
- O botão mostra o ângulo atual (ex.: "↻ 12,5°"). A lista tem **Definir por dois
  cliques** (os dois pontos dão a direção que fica horizontal na tela; atração e guias
  valem), **digitar o ângulo** e **Voltar a 0°**.
- Gira **só a tela**: o modelo não muda. Seguem a tela: a grade, as linhas-guia
  (0/45/90/135°, spec/ui 37), o Shift a 45° e as setas que travam o eixo. Assim, desenhar
  "na horizontal" numa vista girada dá uma parede alinhada ao desenho torto.
- Textos, etiquetas e cotas ficam legíveis: o ângulo de leitura na tela vai de −90° a
  +90° (nunca de cabeça para baixo). O texto guardado não muda.
- O ângulo é de cada pavimento na janela (sessão) e **vai junto na vista salva**
  (`rotation` no estado dela). Na prancha, a vista salva girada entra girada, e o título
  do desenho fica na horizontal.
- O 3D não gira com a planta; cortes e fachadas não têm giro.

## 4. Ocultar, isolar e mostrar tudo
- Exibir e botão direito da seleção: **Ocultar selecionados**, **Isolar selecionados**
  (oculta todo o resto) e **Mostrar tudo**. Também na mini‑barra da seleção (ícone de
  olho).
- Valem na **planta e no 3D** (e na aba 3D da área). O oculto não aparece, não atrai, não
  é escolhido e não estica. Cortes, fachadas, pranchas, tabelas e o PDF das pranchas não
  mudam. A exportação da área (spec/ui 38 §5) segue a tela, então também não leva o
  oculto.
- Enquanto há algo oculto, a barra da vista mostra "N ocultos · Mostrar tudo".
- **Só da sessão**: não vai para o IFC, nem para o diário, nem para a vista salva.
  Elemento excluído sai da lista; desfazer a exclusão não o oculta de novo. Abrir outro
  projeto limpa a lista.

## 5. Travar e destravar elementos
- Editar > **Travar** e **Destravar** (a seleção), **Destravar tudo** (o projeto todo);
  também no botão direito e na mini‑barra (ícone de cadeado).
- Vale para qualquer elemento do modelo e para as anotações. É gravado no IFC, no Pset
  próprio `BrasBim_Edicao`, propriedade `Travado` (booleano); destravar remove a
  propriedade (e o Pset, se ficar vazio). Travar e destravar são uma transação (desfaz
  com Ctrl+Z) e passam pela equipe como qualquer edição (spec/ui 33).
- O travado **pode ser escolhido**, **atrai** o cursor e serve de referência (guias,
  medir, cotar). Não pode ser editado: mover, copiar sobre si, girar, espelhar, esticar,
  excluir, mudar propriedades, tipo, camada ou situação. O **núcleo** recusa a operação
  inteira com "elemento travado: <nome>" (nada muda; vale também para o assistente e a
  equipe). A interface recusa **antes** de começar a arrastar, com a mesma mensagem.
- O que o programa refaz sozinho (junção de paredes, ambiente que acompanha as paredes)
  continua valendo: travar não congela a geometria derivada.
- Na planta, o travado escolhido mostra um cadeado pequeno junto das alças, e as alças
  ficam cinza. A ficha do elemento diz "Travado".
- A chave **Escolher travados** (barra da vista, ligada por padrão) desliga a escolha dos
  travados por clique e por janela. A atração continua.
- Camada travada (spec/ui 18) continua como está: trava pela camada, sem gravar nada no
  elemento.

## 6. Ordem de desenho
- Para **anotações** na planta: linhas 2D, polilinhas, textos, cotas, hachuras e
  figuras. Editar > Ordem de desenho: **Trazer para a frente**, **Mandar para trás**,
  **Um passo à frente**, **Um passo atrás** e **Ordem padrão**. Também no botão direito.
- Ordem padrão: hachuras embaixo, depois linhas, depois textos e cotas. As anotações são
  desenhadas por cima do modelo; o modelo (paredes cortadas, vistas) não entra na ordem.
- Gravada no IFC em `BrasBim_Edicao.Ordem` (inteiro; sem a propriedade = ordem padrão do
  tipo). "Trazer para a frente" põe acima da maior ordem do pavimento; "um passo" troca
  com a anotação seguinte que se sobrepõe a ela. Uma transação por comando.
- Vale na tela, nas pranchas, no PDF e no DXF da área (o DXF grava na ordem).

## 7. Situação em um clique
- Três botões juntos, no grupo **Edição** da barra Ferramentas: **Existente**, **A
  demolir** e **A construir** (ícones próprios nas cores da situação na vista Genérico).
  As outras situações (a regularizar, a transformar, temporário) continuam no menu.
- **Com seleção:** mudam a situação da seleção (mesma transação de Editar > Situação,
  spec/ui 31 §2).
- **Sem seleção:** escolhem a "situação dos novos elementos" de todas as ferramentas de
  criação (hoje uma opção por ferramenta, spec/ui 31 §2). O botão da situação dos novos
  fica marcado, para não esquecer. É preferência do projeto aberto (sessão).

## 8. Onde fica (a implementar)
- Núcleo sem Qt: `brasbim/core/edit_state.py` (Pset `BrasBim_Edicao`: travar, destravar,
  ordem; checagem `ensure_unlocked` chamada pelas operações que editam).
- Interface: `ViewBar` em `brasbim/ui/view_bar.py`; pilha de enquadramentos e giro em
  `PlanView` (`to_screen`/`to_world` com rotação); ocultos em `PlanContext.hidden` e na
  cena 3D; comandos em `main_window.py`.

## 9. Fica para depois
Estilo de cotas na barra, pavimento de referência e passo da grade (Fase 5), giro em
cortes e fachadas, "acima de/abaixo de" um objeto na ordem de desenho, salvar os ocultos
numa vista salva, senha para destravar.

## 10. Critérios de aceite (testes)
- **VB01** Barra da vista: os seletores mudam o mesmo estado do menu (escala, camadas,
  detalhe, penas, situação).
- **VB02** Zoom anterior/seguinte: 20 no máximo; novo depois de voltar apaga os seguintes.
- **VB03** Zoom %: 100% dá o tamanho do papel na escala.
- **VB04** Girar: `to_world(to_screen(p)) == p`; definir por dois cliques deixa a direção
  horizontal; parede desenhada "na horizontal" sai no ângulo; texto nunca de cabeça para
  baixo.
- **VB05** Giro na vista salva: gravado e lido de volta; na prancha, entra girada.
- **VB06** Ocultar/isolar/mostrar: oculto não aparece, não atrai, não é escolhido, some do
  3D; nada no IFC.
- **VB07** Travar: `BrasBim_Edicao.Travado` no IFC; mover, excluir e mudar propriedade
  recusados pelo núcleo sem mudar nada; destravar remove a propriedade; desfazer.
- **VB08** Travado escolhível e atraível; chave "Escolher travados" desliga a escolha.
- **VB09** Ordem de desenho: frente, trás, um passo; `BrasBim_Edicao.Ordem` no IFC; ordem
  padrão remove a propriedade.
- **VB10** Situação em um clique: com seleção muda a situação; sem seleção muda a dos
  novos elementos de todas as ferramentas.

## 11. Fontes
- Pesquisa: `research_notes/Pesquisa Archicad Revit AutoCAD/complemento_barras_e_navegacao.md`
  §1 (travar), §3 (ordem de desenho), §4 (ocultar), §7 (zoom anterior), §8 (girar a
  vista), §11 (situação em um clique), com as URLs públicas de lá (ajuda Graphisoft
  AC18–AC30, ajuda Autodesk AutoCAD LT/Revit, comunidade Graphisoft, Arkance, Bricsys).
  Os achados vieram dos resumos da busca; conferir nas páginas antes de fechar a revisão.
- `research_notes/Pesquisa Archicad Revit AutoCAD/interface_e_interacao.md` §4 (modos
  visíveis na barra de baixo).
- Nada de `_restrito/`. Nomes em pt‑BR próprios ("barra da vista", "travar", "situação
  em um clique").

## 12. Pontos de revisão
(a) A barra da vista fica sob a planta, acima da linha de comando, e a escala sai da barra
    de estado.
(b) O giro segue a grade, as guias, o Shift e as setas (desenhar "reto" na vista girada).
(c) Ocultar também vale na exportação da área (que segue a tela), mas não nas pranchas.
(d) Travado: escolhível e atraível; a chave "Escolher travados" vem ligada.
(e) Ordem de desenho só para anotações; o modelo fica sempre por baixo.
(f) Os três botões de situação ficam no grupo Edição da barra Ferramentas (não no
    painel); as outras três situações só no menu.
