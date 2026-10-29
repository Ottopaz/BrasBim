---
documento: Documentação — polilinha com arcos, ponto de apoio, figura e desenho
requisito: spec/ui 34 §4 (grupo Documentação); RF-DOC-06, RF-DOC-14, RF-INT-07 (imagem)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-29
status: em revisão
revisor: OTTO
---

# Documentação: polilinha, ponto de apoio, figura e desenho

## 1. Propósito
Completar o grupo **Documentação** da barra Ferramentas (spec/ui 34 §3) com:

| Ferramenta | Para quê |
|---|---|
| **Polilinha** | uma linha única com trechos retos **e em arco** (a Linha de hoje só tem retas) |
| **Ponto de apoio** | uma cruzinha que serve de alvo para a atração do cursor e não sai no papel |
| **Figura** | uma imagem (PNG, JPG; foto, planta escaneada, logotipo) posta na planta, numa vista ou na prancha |
| **Desenho** | pôr na prancha, num gesto, uma vista do projeto ou um arquivo de fora (PDF, imagem), com número e título |

"Hotspot" (nome do pedido na spec/ui 34 §4) é o termo do Archicad. Aqui o nome é
**Ponto de apoio**.

A base é a pesquisa complementar
(`research_notes/Pesquisa Archicad Revit AutoCAD/complemento_vistas_e_documentacao.md`,
§5–§8).

Fica de fora: largura variável de polilinha (polilinha "grossa"), DWF, vínculo vivo com
DWG na prancha (o DWG entra por folha de trabalho, spec/ui 35 §5), ajuste de brilho e
contraste da imagem.

## 2. Polilinha

### 2.1 Elemento
- É o mesmo elemento da Linha (`line2d`, spec/ui 13 §6), com um campo novo:
  `bulges`, uma lista com um valor por trecho. 0 = reta; ≠ 0 = arco, com o valor sendo a
  tangente de ¼ do ângulo do arco, positivo no sentido anti‑horário *(CG: é a forma usual
  de guardar arco em polilinha, a mesma do DXF; a exportação DXF fica direta)*.
- Arquivos antigos (sem `bulges`) são lidos como todas as retas.
- IFC: a geometria passa a ser `IfcIndexedPolyCurve` com `IfcLineIndex` e `IfcArcIndex`
  (três pontos por arco: início, meio e fim). Assim o arco sai como arco de verdade para
  quem abre o IFC, e não em pedaços.
- Comprimento, área (fechada) e hachura por contorno (spec/ui 30) passam a considerar os
  arcos.

### 2.2 Criação
- Ferramenta **Polilinha** (grupo Documentação, depois da Linha). Cliques como na Linha:
  cada clique fecha um trecho, e Enter, clique duplo ou o botão direito encerra. Clicar no
  primeiro ponto fecha a polilinha.
- Barra Opções: **Trecho** = *Reta* | *Arco* (o botão alterna), espessura e tipo de linha.
  Tecla **A** passa para arco e **R** volta para reta, durante o desenho.
- *Arco:* por padrão, o arco sai **tangente** ao trecho anterior e o clique dá o fim
  dele. Com **Shift**, o arco passa por três pontos: o próximo clique é um ponto do arco e o
  seguinte, o fim. *(Do AutoCAD ficam as duas formas mais usadas, tangente e por três
  pontos; as outras, por ângulo, centro ou raio, ficam de fora para a barra não encher.)*
- **Backspace** tira o último trecho. Tab digita o comprimento (reta) ou o raio (arco).
- A Linha continua igual (só retas). Com uma linha escolhida, **Continuar** (botão
  direito numa ponta) volta a desenhar a partir dela, com arcos se quiser. *(Do
  Archicad.)*

### 2.3 Edição
- Alças nos vértices (mover) e no **meio de cada trecho**. Arrastar a alça do meio
  **curva o trecho**: a reta vira arco que passa pelo ponto arrastado. Arrastar até
  alinhar com as pontas volta a reta, com atração.
- Botão direito num vértice: **Arredondar canto…** (raio; troca o canto por um arco
  tangente) e **Remover vértice**.
- Botão direito num trecho: **Inserir vértice aqui**, **Tornar reta**/**Tornar arco** e
  **Abrir aqui** (abre a fechada; corta a aberta em duas).
- Com várias linhas, arcos e polilinhas escolhidos que se tocam pelas pontas: **Unir em
  polilinha** (Editar). As propriedades vêm do primeiro escolhido. **Separar em trechos**
  faz o caminho inverso.
- Tudo numa transação cada, com desfazer.

## 3. Ponto de apoio

### 3.1 Elemento e criação
- Ferramenta **Ponto de apoio** (grupo Documentação). Um clique põe um ponto. Na barra
  Opções, **Modo** = *Clique* (padrão) | *Dividir* | *Pé da perpendicular*:
  - *Dividir:* clique numa linha, polilinha, arco ou parede (pelo eixo) e digite N. Nascem
    N − 1 pontos que dividem o elemento em partes iguais. *(Ideia do dividir do AutoCAD.)*
  - *Pé da perpendicular:* clique num ponto e depois num elemento. Nasce o ponto no pé da
    perpendicular. *(Do Archicad.)*
- Na tela, é uma cruz de 3 mm (tamanho de tela, não de papel) em cor de apoio.
- **Não sai no papel** por padrão. A opção **Imprimir** no painel faz o ponto sair como cruz
  de 2 mm de papel.

### 3.2 Uso
- A atração do cursor ganha o tipo **Ponto** (spec/ui 23), ligado por padrão, que pega o
  ponto de apoio.
- **Editar > Escolher todos os pontos de apoio** (do pavimento ou da vista) e Excluir.
  *(O fórum do Archicad mostra que é o uso mais pedido: apagar todos de uma vez.)*
- Vale na planta, no corte, no detalhe e na folha de trabalho (spec/ui 35 §6).

### 3.3 IFC
`IfcAnnotation` com `PredefinedType` **`ASSUMEDPOINT`** e `ObjectType` "PontoDeApoio"
(prefixo `point2d`), com o estado `at`, `print` e representação `Annotation` com um
`IfcCartesianPoint` (o ponto, para outros programas) e a cruz.

## 4. Figura (imagem)

### 4.1 Criação
- Ferramenta **Figura** (grupo Documentação). Abre a escolha do arquivo (PNG, JPG, BMP,
  TIFF; e a 1ª página de um PDF, com escolha da página quando há várias). Depois o
  contorno da imagem acompanha o cursor, preso a nós e bordas, e um clique a põe.
- **Colar** uma imagem da área de transferência (Ctrl+V) na planta, numa vista ou na
  prancha também cria uma figura, com o centro no cursor.
- Tamanho inicial: na prancha, 100 mm de largura ou o tamanho da imagem a 150 ppi (o
  menor). No modelo, 10 m de largura. A proporção é sempre mantida; **Shift** solta a
  proporção ao arrastar uma alça. *(Ao contrário do Archicad, onde o Shift prende a
  proporção: aqui o comum é manter.)*

### 4.2 Calibrar a escala
Botão direito na figura: **Calibrar pela medida…** Clicam‑se dois pontos sobre a imagem
e digita‑se a distância real entre eles (ou, na prancha, a distância no papel), e a figura
é redimensionada mantendo o primeiro ponto no lugar. *(Nenhum dos três programas tem isso
na ferramenta. É o caso mais comum no Brasil: planta de prefeitura escaneada, levantamento
em papel, foto aérea do lote.)*

### 4.3 Edição
- Alças: cantos (tamanho), meio dos lados (recorte; o lado oposto fica parado, como o
  limite do desenho na prancha, spec/ui 29 §3) e giro.
- Painel: largura, altura, manter proporção, giro, **Opacidade** (0–100 %), **Branco
  transparente** (os pixels brancos não cobrem o que está atrás), espelhar, **Atrás /
  À frente** (ordem de desenho em relação às outras anotações; padrão: atrás),
  **Recortar**/**Tirar recorte**, **Substituir imagem…** e **Salvar imagem como…**.
- Camadas (spec/ui 18): a figura fica numa camada como as outras anotações.

### 4.4 Dentro do arquivo do projeto *(decisão do projeto)*
- A imagem fica **dentro do IFC**, para o projeto continuar num arquivo só, como no
  Archicad. A representação `Annotation` é um retângulo (`IfcTriangulatedFaceSet` de 2
  triângulos, z = 0) com `IfcIndexedTriangleTextureMap` para uma **`IfcBlobTexture`**
  (PNG em binário). Outros programas que leem textura mostram a imagem no lugar, e os
  que não leem mostram o retângulo.
- Estado em `BrasBim_Anotacao` (prefixo `figure`, `ObjectType` "Figura"): `at`, `width`,
  `height`, `angle`, `mirror`, `crop`, `opacity`, `white_transparent`, `order`,
  `name` (nome do arquivo de origem, só informação), `pixels` [largura, altura].
- **Tamanho:** ao pôr uma imagem com mais de 4 milhões de pixels, o BrasBim pergunta se
  quer reduzir (padrão: reduzir para 2 400 px no lado maior). Acima de 20 MB de arquivo, a
  redução é obrigatória. *(O help do Archicad avisa que imagens embutidas incham o
  arquivo; aqui o aviso aparece na hora.)*
- A imagem é decodificada uma vez e guardada em memória (`QImage`) para o desenho.

## 5. Desenho (pôr na prancha)

### 5.1 Ferramenta
- Ferramenta **Desenho** (grupo Documentação). Na aba da prancha:
  1. Abre um quadro de escolha com duas abas. **Do projeto** traz plantas por pavimento,
     cortes, fachadas, elevações internas, detalhes, folhas de trabalho, câmeras e vistas
     salvas, com busca e miniatura. **Arquivo** traz PDF (com a página) ou imagem.
  2. O desenho acompanha o cursor no tamanho real do papel, com atração às bordas e aos
     centros dos desenhos já postos e às margens do quadro *(alinhamento entre desenhos: o
     Revit pede há anos)*, e um clique o põe.
- Fora da prancha, a ferramenta fica apagada. A dica diz "abra uma prancha".
- Os caminhos que já existem continuam: arrastar da lista e o botão direito no papel
  (spec/ui 25 §5).

### 5.2 Arquivo de fora
- **PDF:** a página escolhida entra como **figura vinculada**: imagem gerada a 300 ppi
  (Qt PDF), no tamanho real da página na escala 1:1 do papel. Ela guarda o caminho do
  arquivo (relativo ao projeto, quando possível) e a data dele.
- **Imagem:** igual, vinculada.
- **Atualizar** (botão direito, ou sozinho ao abrir a prancha se a data do arquivo mudou):
  gera a imagem de novo. Se o arquivo sumiu, fica a última imagem guardada e um aviso no
  painel. *(Vínculo atualizável, do Archicad e do AutoCAD; a cópia guardada no IFC
  mantém o projeto abrindo em outro PC sem o arquivo.)*
- Dados: os da figura (§4.4) mais `link` {`path`, `page`, `mtime`}.

### 5.3 Número e título do desenho
- Todo desenho posto na prancha (vista ou arquivo) recebe um **número** na ordem em que
  entrou (1, 2…), que se pode trocar no painel. É esse número que os marcadores de detalhe
  e de elevação interna mostram (spec/ui 35 §4.4).
- **Título** embaixo do desenho, opcional (botão direito > **Título**; padrão ligado nas
  vistas, desligado nos arquivos): uma linha com o número num círculo, o nome da vista e a
  escala ("2 — DETALHE DO PEITORIL — ESC. 1:10") *(CG)*. Ele substitui o título que o
  corte desenha sozinho quando está na prancha, para não sair duas vezes.
- Item da prancha (Pset `BrasBim_Prancha`): ganha `number` e `title` {`show`, `text`
  (vazio = nome da vista)}; o tipo de item novo é `file` (arquivo de fora).

## 6. Critérios de aceite (testes)
| Id | Teste |
|---|---|
| PL01 | Polilinha com reta, arco tangente e reta grava `bulges` [0, b, 0]; o IFC tem `IfcIndexedPolyCurve` com um `IfcArcIndex` |
| PL02 | Arco por três pontos (Shift) passa pelo ponto do meio clicado |
| PL03 | Arrastar a alça do meio de uma reta a curva; alinhar de volta a deixa reta |
| PL04 | Arredondar canto de 0,5 m troca o vértice por arco tangente aos dois trechos |
| PL05 | Unir duas linhas e um arco que se tocam dá uma polilinha só; Separar volta três peças |
| PL06 | Área de uma polilinha fechada com um arco é a do polígono mais o segmento circular |
| PL07 | Arquivo antigo com `line2d` sem `bulges` abre igual |
| PA01 | Ponto de apoio grava `ASSUMEDPOINT` e um `IfcCartesianPoint`; não sai no PDF; com Imprimir, sai |
| PA02 | Dividir uma parede de 6 m em 3 cria 2 pontos a 2 e 4 m no eixo |
| PA03 | A atração pega o ponto de apoio |
| FG01 | Figura posta grava `IfcBlobTexture` com o PNG e o retângulo com mapa de textura; reabrir o IFC mostra a mesma imagem |
| FG02 | Calibrar: dois pontos a 100 px um do outro, distância 5 m → a figura passa a ter 5 m entre eles |
| FG03 | Imagem de 6 000 × 4 000 px pergunta e reduz para 2 400 px no lado maior |
| FG04 | Opacidade 50 % e "Atrás": a linha que passa por baixo aparece na planta e no PDF |
| DS01 | Ferramenta Desenho põe um corte na prancha no ponto clicado, com número 1 e título "1 — CORTE A — ESC. 1:50" (e sem o título do próprio corte) |
| DS02 | Detalhe posto como desenho 2 na prancha 03: o marcador na planta mostra "2" e "03" |
| DS03 | PDF vinculado: trocar o arquivo e Atualizar muda a imagem; apagar o arquivo mantém a última |
| UI.. | Ferramentas no grupo Documentação da barra e na paleta; Desenho apagado fora da prancha |

## 7. Fontes
- Pesquisa complementar (2026‑10‑29):
  `research_notes/Pesquisa Archicad Revit AutoCAD/complemento_vistas_e_documentacao.md`
  §5 (polilinha: AutoCAD 2024 PLINE; Archicad AC28 polylines), §6 (ponto de apoio:
  Archicad hotspot; AutoCAD POINT/DIVIDE), §7 (figura: Archicad AC25 Figure; AutoCAD 2024
  IMAGEATTACH; Revit 2024 image), §8 (desenho: Archicad AC25 Drawing; Revit 2024 Add Views
  to a Sheet).
- IFC 4.3: `IfcIndexedPolyCurve`, `IfcArcIndex`, `IfcAnnotationTypeEnum.ASSUMEDPOINT`
  (conferido no esquema do IfcOpenShell instalado), `IfcBlobTexture`,
  `IfcIndexedTriangleTextureMap`, `IfcTriangulatedFaceSet` [IFC-ANNOT].
- Qt (LGPL): `QImage`, Qt PDF (`QPdfDocument`) para gerar a imagem da página. O Qt PDF
  vem no pacote à parte **`PySide6_Pdf`** (conferido no `.venv`), que a pasta do pendrive
  ainda não leva: entra em `scripts/pendrive/requisitos.txt` quando o §5.2 for feito. Sem
  ele, o Desenho aceita só imagem e avisa que falta o leitor de PDF.
- CG: arco de polilinha pela tangente de ¼ do ângulo (DXF); título de desenho com número
  em círculo e escala.
- Nada de `_restrito/`. Nenhum nome de comando de outro programa: "Polilinha", "Ponto de
  apoio", "Figura" e "Desenho" são palavras comuns em pt‑BR.

## 8. Pontos de revisão
(i) Polilinha como ferramenta separada da Linha, criando o mesmo elemento com arcos; a
alternativa é a própria Linha ganhar o modo Arco e não haver ícone novo (§2.2).
(j) Teclas A (arco) e R (reta) durante o desenho da polilinha (§2.2).
(k) Nome "Ponto de apoio" no lugar de "hotspot"; não sai no papel por padrão (§3).
(l) Imagem dentro do IFC (`IfcBlobTexture`), com redução a 2 400 px oferecida acima de 4
milhões de pixels (§4.4).
(m) Shift solta a proporção da figura (o padrão é manter) (§4.1).
(n) Todo desenho na prancha ganha número; título com número em círculo, nome e escala,
no lugar do título próprio do corte (§5.3).
(o) PDF na prancha como imagem a 300 ppi, e não vetorial (§5.2).
(p) Ordem de implementação proposta: Ponto de apoio → Polilinha → Figura → Desenho (o
Desenho usa a Figura para arquivos de fora e dá o número que os marcadores da spec/ui 35
usam).
