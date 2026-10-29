---
documento: Interação — linhas-guia a partir de pontos de referência e do ponto anterior
requisito: RF-DES-02 (atração a pontos); amplia spec/ui 09 §2.1 e spec/ui 23 §10
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-29
status: em revisão (pedido urgente do revisor: implementado na sequência)
revisor: OTTO
---

# Linhas-guia

## 1. Propósito
Pedido do revisor em 2026‑10‑29: parar o cursor sobre um vértice cria uma referência e,
ao desenhar qualquer coisa, aparecem linhas-guia na horizontal, na vertical e na
diagonal, que **prendem** o cursor e ajudam a alinhar sem linha auxiliar.

Já havia (spec/ui 09 §2.1) um ponto de referência por parada do cursor, só com 0° e 90°,
um ponto por vez, só nos vértices de paredes e vãos, e só nas ferramentas de traço
(parede, laje, linha…). Esta spec o generaliza; o que não for dito aqui continua igual
(distância digitada no balão, porta e janela medidas ao longo da parede, Shift a 45°,
setas que travam o eixo, Alt sem atração).

## 2. Pontos de referência
- **Pegar:** com uma ferramenta de criação ou de edição por pontos (Mover, Copiar,
  Girar, Espelhar), parar o cursor cerca de 0,4 s sobre um ponto de atração do tipo
  **extremidade, interseção, meio ou centro** de qualquer elemento visível do pavimento
  (parede, laje, pilar, linha 2D, desenho importado, eixos…). O ponto ganha um x.
- **Vários:** até **3** ao mesmo tempo; o quarto tira o mais antigo. Parar de novo sobre
  um ponto que já é referência não muda nada.
- **Duram** até o **Esc** (o primeiro Esc solta todos; o seguinte faz o que fazia antes)
  ou a troca de ferramenta. **Não** caem ao clicar: servem para vários pontos seguidos
  (antes caíam ao confirmar o ponto). *Ponto de revisão (a).*
- São da sessão, compartilhados pela planta e pelo 3D, e nunca vão para o IFC.

## 3. Linhas-guia
- Saem de cada ponto de referência e do **ponto anterior** da ferramenta (o último
  clicado na parede, linha, laje, mover…) nas direções **0°, 45°, 90° e 135°** do
  pavimento (as duas pontas de cada reta). *Ponto de revisão (b).*
- **Prender:** com o cursor a menos da distância de atração (a mesma dos pontos, em
  pixels de tela) de uma guia, o ponto vai para a projeção dele na guia, que aparece
  tracejada do ponto de origem até um pouco além do cursor.
- **Cruzamentos prendem mais forte** (até 1,5 × a distância de atração) e são marcados
  como interseção:
  - duas guias de origens diferentes (por exemplo, alinhar com um canto em X e com outro
    em Y, ou com a referência e com o ponto anterior);
  - uma guia e uma aresta existente (por exemplo, levar a parede até a face de outra,
    alinhada com um canto).
- **Prioridade:** extremidade, interseção, meio, centro, perpendicular e tangente
  continuam a vencer; se o ponto atraído já estiver sobre uma guia, ela aparece também.
  Na borda e na parede cedem à guia. **Grade:** o ponto da grade que já está sobre uma
  guia fica (sobre duas, é marcado como interseção); fora disso, sobre a guia a
  distância à origem dela segue o passo da grade (0,10 m), para não sair de valores
  redondos.
- Shift (direção a 45° do ponto anterior), seta (trava de eixo) e Alt (sem atração)
  desligam as guias enquanto valem.
- **Distância:** com o cursor numa guia que sai de um ponto de referência, o balão
  mostra a distância a ele; o número digitado trava a guia e marca o ponto (como na
  spec/ui 09 §2.1.1).

## 4. Liga e desliga
Exibir > Atração > **Linhas-guia** (ligada por padrão), preferência do usuário (não do
projeto). "Desligar toda a atração" também as desliga.

## 5. Onde está
- Núcleo sem Qt: `brasbim/core/guides.py` (guias, projeção, cruzamentos).
- `PlanContext` (`ui/tools.py`): pontos de referência, `acquire`, guias dentro de
  `snap` (todas as ferramentas que pedem ponto passam por ele) e as marcas, desenhadas
  pela planta e pelo 3D.

## 6. Fica para depois
Guias paralela e perpendicular a uma aresta, prolongamento de aresta, ângulos
configuráveis (30°, 15°), guias persistentes arrastadas da borda da vista, cota até a
referência nas ferramentas de ponto único (texto, nível…).

## 7. Critérios de aceite (testes)
- **LG01** Núcleo: guia a 0°, 90° e 45° prende pela projeção; longe dela, nada.
- **LG02** Cruzamento de duas guias e de guia com aresta vence a guia só.
- **LG03** Pegar referência no canto de uma laje e no meio de uma linha 2D; até 3, o
  quarto tira o mais antigo; Esc solta todas.
- **LG04** Parede: guia diagonal a partir do ponto anterior; parede alinhada com um canto
  de outra pelo cruzamento da guia da referência com a do ponto anterior; a parede no
  IFC termina no ponto alinhado.
- **LG05** A referência continua depois do clique; ponto atraído (extremidade) vence a
  guia; Linhas-guia desligada não prende.
- **LG06** Mover com referência: o deslocamento usa o ponto da guia.

## 8. Fontes
- Pesquisa: `research_notes/Pesquisa Archicad Revit AutoCAD/interface_e_interacao.md` §1
  (Archicad: referências de atração ativadas ao passar o cursor, várias ao mesmo tempo,
  e guias temporárias em X/Y e a cada 45°; AutoCAD 2026: pontos adquiridos por pausa e
  caminhos de alinhamento horizontais, verticais e polares, com distância digitada sobre
  o caminho; SketchUp: pausa dá prioridade ao ponto) e `archicad_modelagem.md` (guias de
  atração AC28 temporárias, linhas-guia persistentes AC25) e `autocad.md` §1
  (rastreamento por snap e polar).
- CG: projeção de ponto em reta, interseção de retas.
- Nada de `_restrito/`. "Linhas-guia" e "ponto de referência" são termos comuns em pt‑BR.

## 9. Pontos de revisão
(a) Referências duram até Esc ou troca de ferramenta (antes caíam ao clicar).
(b) Ângulos 0°, 45°, 90° e 135°, também a partir do ponto anterior; até 3 referências.
