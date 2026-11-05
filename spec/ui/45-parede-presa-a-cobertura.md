---
documento: Parede e pilar presos à cobertura (recorte pela cobertura)
requisito: RF-ELE-17; item M2 da revisão geral (2026-10-30)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-11-05
status: aprovado com as respostas de 2026-11-05 e implementado (RC01–RC08)
revisor: OTTO
---

# Parede até a cobertura

## 1. Propósito
Toda casa com telhado aparente tem paredes que terminam na cobertura: o oitão das duas
águas, a parede interna que sobe até o forro inclinado, o pilar da varanda. Hoje isso se
faz à mão, pelo topo inclinado (spec/ui 08) ou por uma operação de sólido (spec/ui 41
§3), calculando antes a altura do ponto mais alto. Esta spec dá à parede e ao pilar um
**topo preso à cobertura**: a altura sai sozinha, o que passa do telhado é recortado, e
tudo acompanha quando a cobertura muda.

Pesquisa: `research_notes/Pesquisa Archicad Revit AutoCAD/complemento_parede_e_cobertura.md`.
Pontos para o revisor no §7.

## 2. Uso
- **Modo de topo "Cobertura"**, ao lado de "Pavimento" e "Altura fixa", na barra Opções
  da Parede e do Pilar e na ficha. Escolhido na ferramenta, a parede nova prende‑se à
  cobertura que estiver em cima dela quando é criada.
- **Prender à cobertura** (Editar e botão direito): com paredes e pilares
  selecionados, o comando pede um clique numa cobertura (planta ou 3D). Sem seleção,
  clica‑se primeiro nos elementos e Enter, como nas operações de sólidos.
- **Soltar da cobertura** (mesmos lugares): volta ao modo de topo e à altura que o
  elemento tinha antes de ser preso (guardados no elemento).
- **Ao criar uma cobertura** (ponto (c)): as paredes e pilares do pavimento que ficam
  sob o contorno dela, com o topo até 0,50 m abaixo ou acima da face de baixo, são
  presos nela na mesma transação; o balão avisa "N paredes presas à cobertura" com
  "Desfazer".
- **Ficha:** em "Altura", o modo Cobertura mostra a cobertura (clicar seleciona) e a
  altura resultante, só leitura. A seção "Recortado por" (sólidos) lista a cobertura com
  a operação "presa ao topo"; o botão Tirar dela é o mesmo que Soltar.

## 3. Regra da forma
1. **Coberturas da parede:** as que o elemento prendeu (uma ou mais; prender numa
   segunda não solta da primeira — elas recortam juntas, como um corpo só).
2. **Altura do elemento** = a maior cota da **face de baixo** das coberturas sobre a
   projeção do elemento em planta, menos a cota da base. A face de baixo é a superfície
   que a cobertura já calcula (a mais baixa das águas em cada ponto, `roofs`), descontado
   o beiral só fora do contorno de apoio.
3. **Recorte:** tira‑se do corpo o que fica acima da face de baixo de cada água
   (operação `SUBTRACT_UP` das operações de sólidos, já implementada). O topo da parede
   fica com a inclinação da água, também na espessura.
4. **Onde não há cobertura em cima** (parede que sai do telhado, ponto (b)): o trecho
   descoberto fica com a altura do topo de reserva — por proposta, a do pavimento de
   cima, como a parede de antes; a parede inteira descoberta é recusada ao prender
   ("a cobertura não passa sobre esta parede").
5. **Parede de altura menor que a cobertura** (parede interna baixa sob telhado alto): o
   modo Cobertura sobe a parede até o telhado; quem quer a parede baixa usa altura fixa.
6. **Associativo:** mudar inclinação, cota, beiral, contorno ou forma da cobertura,
   mover a parede ou mudar a base refaz a altura e o recorte. Apagar a cobertura solta
   os elementos presos, com aviso (como apagar o operador de um sólido, ponto (g) da
   spec/ui 41), e eles voltam ao topo de antes.
7. **Fora desta entrega**, recusados com mensagem: parede tombada, parede de perfil do
   projeto, parede com topo inclinado à mão (o modo Cobertura substitui o topo
   inclinado: escolher um tira o outro), viga, laje. Prender a **base** (parede sobre a
   cobertura) também fica para depois.

## 4. Planta, cortes e quantidades
- **Planta:** sem mudança no desenho de quem é cortado pelo plano de corte. A parte da
  parede acima do plano não aparece (como hoje). Pilar preso: igual.
- **Cortes e fachadas:** o corpo recortado (já é o que o corte lê).
- **Quantidades:** `Height` = a altura do item 2 do §3; `NetVolume` e as áreas de face
  descontam o recorte (as operações de sólidos já descontam o volume; as áreas passam a
  ser medidas no corpo recortado).
- **Portas e janelas:** a que passa do telhado recebe o aviso "ultrapassa o topo da
  parede" que já existe, pelo topo recortado no trecho dela.

## 5. No IFC
- A ligação é a mesma das operações de sólidos: `IfcRelInterferesElements` com
  `RelatingElement` = parede ou pilar, `RelatedElement` = a `IfcRoof`,
  `InterferenceType` `SUBTRACT_UP`, `ImpliedOrder` verdadeiro. Quem lê o IFC não precisa
  saber do modo de topo.
- No Pset da parede (`BrasBim_Parede`) e do pilar (`BrasBim_Pilar`): `TipoTopo` =
  `COBERTURA` e `TopoAntes` (JSON: modo, pavimento, deslocamento e altura de antes, para
  soltar). O `Body` é o recortado, como já é com os sólidos.

## 6. Testes
- **RC01** parede sob duas águas, perpendicular à cumeeira (oitão): presa, a altura é a
  da cumeeira menos a base; o corpo tem o triângulo do oitão (volume = retângulo da
  altura do beiral + triângulo); o IFC tem a relação `SUBTRACT_UP`; reabre igual.
- **RC02** parede paralela à cumeeira sob uma água: o topo acompanha a inclinação na
  espessura (face de cima inclinada).
- **RC03** associatividade: mudar a inclinação, a cota de apoio e o contorno da
  cobertura refaz altura e recorte; desfazer volta.
- **RC04** soltar devolve o modo e a altura de antes; apagar a cobertura solta com aviso.
- **RC05** parede que sai do telhado: o trecho descoberto fica no topo de reserva;
  parede toda fora é recusada; parede tombada, de perfil e de topo inclinado recusadas.
- **RC06** pilar preso sob uma água; duas coberturas sobre a mesma parede.
- **RC07** criar uma cobertura sobre quatro paredes prende as quatro (ponto (c)); a
  janela acima do telhado recebe o aviso.
- **RC08** interface: modo Cobertura na barra Opções e na ficha, Prender e Soltar pelo
  botão direito.

## 7. Pontos para o revisor
**Respostas (2026‑11‑05):** (a) **"Até a cobertura"**; (b) como proposto: pavimento de
cima (o topo de antes); (c) prende sozinho, com **Desfazer no balão** (transação à parte:
desfaz só o prender); (d) **o usuário escolhe** a face — "Até a face": de baixo (telhado
apoiado, padrão) ou de cima (platibanda); (e) **só parede** nesta entrega (pilar depois).

**Ajustes ao implementar:** a relação `SUBTRACT_UP` leva o nome
`BrasBim: topo até a cobertura` e fica fora das operações de sólidos do usuário (não
aparece em "Recortado por"); a ficha mostra a cobertura em "Altura", com "Soltar da
cobertura". O topo de antes não vai num JSON: são os próprios `top_storey`/`fixed_height`
da parede, mantidos no modo cobertura (Pset `PavimentoTopo`/`AlturaFixa`), mais
`CoberturasTopo` e `FaceCobertura`. A ferramenta Parede com "Até a cobertura" acha
sozinha a cobertura de cima; sem nenhuma, a parede fica no topo de reserva.

- (a) Nome do modo de topo: **"Cobertura"** (proposta) ou "Até a cobertura"?
- (b) Trecho da parede **sem cobertura em cima**: topo de reserva no pavimento de cima
  (proposta), ou na altura do beiral (cota de apoio da cobertura)?
- (c) **Prender sozinho ao criar a cobertura** as paredes e pilares de baixo (proposta,
  com "Desfazer" no balão), ou só pelo comando Prender?
- (d) A parede sobe até a **face de baixo** da cobertura (proposta: o telhado apoia na
  parede, e a madeira/telha fica por cima), ou até a face de cima (parede que atravessa
  o telhado, como platibanda)?
- (e) Pilar junto com a parede nesta entrega (proposta), ou só a parede?

## 8. Ordem
Uma sessão: núcleo e IFC (RC01–RC07), depois a interface (RC08).

## 9. Fontes
Ver o complemento da pesquisa, §1 e §2. Graphisoft: Trim Elements to Roof or Shell,
Define Trimming Bodies, Automatic Trim, Manual Trim, Managing Element Connections, Crop
to Single-plane Roof (ajuda AC28). Autodesk: Attach Walls to Other Elements (ajuda
Revit 2016). Base própria: spec/ui 41 §3 (operações de sólidos), spec/ui 08 (topo
inclinado), `spec/elementos/cobertura.md`.
