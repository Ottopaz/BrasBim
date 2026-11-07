---
documento: Forro e piso como revestimento (IfcCovering)
requisito: RF-ELE-12; item M3 da revisão geral (2026-10-30)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-11-05
status: aprovado (2026-11-05: "pode fazer o que julgar melhor") e implementado (FP01–FP08)
revisor: OTTO
---

# Forro e piso

## 1. Propósito
Forro de gesso e piso por ambiente estão em todo projeto e em todo orçamento. Hoje o
BrasBim não tem como modelá‑los, a não ser com uma laje fina, que sai errada no IFC (é
laje, não revestimento) e nos quantitativos. Esta spec cria o **forro** e o **piso** como
revestimentos (`IfcCovering`), postos **por ambiente num clique** e presos a ele: quando
as paredes mudam, o ambiente se refaz e o forro e o piso vão junto.

Pesquisa: `research_notes/Pesquisa Archicad Revit AutoCAD/complemento_forro_e_piso.md`.
Pontos para o revisor no §8.

## 2. Tipos
- **Tipos de forro e de piso** (`IfcCoveringType` `CEILING`/`FLOORING`) com camadas
  (`IfcMaterialLayerSet`), editados em Projeto > Tipos de forro / Tipos de piso, como os
  da laje. Espessura = soma das camadas.
- Biblioteca inicial (ponto (a)):
  - forro: **Forro de gesso** (gesso 1,25 cm), **Forro de PVC** (PVC 1 cm),
    **Forro de madeira** (madeira 2 cm);
  - piso: **Porcelanato** (porcelanato 1 cm + argamassa 0,5 cm),
    **Cerâmica** (cerâmica 0,8 cm + argamassa 0,5 cm), **Piso vinílico** (0,3 cm),
    **Cimentado** (argamassa 3 cm).
- O material de cima do piso (o que se vê) dá a hachura da planta e a cor do 3D.

## 3. Uso
- **Ferramentas Forro e Piso** (grupo Modelagem). Dois modos na barra Opções:
  - **Ambiente** (padrão): passar o mouse sobre um ambiente mostra o contorno dele; um
    clique põe o revestimento. O contorno fica **preso ao ambiente**.
  - **Contorno**: desenhar o polígono (retângulo ou pontos), como a laje; fica livre.
- Barra Opções: tipo; no forro, a **altura** (padrão 2,60 m acima do pavimento, ponto
  (b)); no piso, nada além do tipo (o topo fica no nível do pavimento, ponto (c)).
- **Em todos os ambientes** (botão na barra Opções e Projeto > Forro e piso em todos os
  ambientes): põe o tipo escolhido em cada ambiente do pavimento que ainda não tem esse
  revestimento; o balão diz quantos, com Desfazer.
- **Ficha:** tipo, altura (forro), ambiente (clicar seleciona; "Soltar do ambiente" deixa o
  contorno livre, como está), área e espessura.
- **Ambiente com forro:** o pé‑direito calculado do ambiente passa a ser o do forro
  (até a face de baixo dele). Pé‑direito fixo continua fixo.

## 4. Regra da forma
- Contorno: o do ambiente (com os furos dos pilares que ele já desconta? ponto (d)) ou o
  desenhado. **Forro:** a face de baixo na altura escolhida, a espessura para cima. **Piso:**
  o topo no nível do pavimento + deslocamento (padrão 0), a espessura para baixo
  (ponto (c)).
- **Preso ao ambiente:** o contorno é refeito quando o ambiente muda (paredes movidas,
  contorno editado); apagar o ambiente solta o revestimento, que fica com o último
  contorno (aviso no balão).
- Vários revestimentos no mesmo ambiente são aceitos (forro rebaixado parcial por
  contorno, dois pisos); dois do mesmo tipo presos ao mesmo ambiente, não.
- **O piso rebaixa a laje** (revisão de 2026‑11‑07): a laje que fica sob o piso perde, no
  contorno do piso, a parte acima da base dele. O nível do pavimento continua sendo o piso
  acabado; a laje bruta fica abaixo do piso de cada ambiente, com a espessura de cada um.
  Entra nos recortes por prioridade (spec/ui 12 §2) entre a viga e a laje, mas o piso só
  corta laje: não corta parede nem é cortado (o corpo dele já desconta os pilares). O
  forro não corta nada. Acompanha o piso (criar, mudar o tipo ou o contorno, excluir,
  Desfazer). O `NetVolume` da laje desconta o rebaixo; a `NetArea`, não.

## 5. Planta, 3D, cortes e tabelas
- **Planta:** o **piso** aparece com a hachura de desenho do material de cima, abaixo das
  paredes e dos móveis, ligada por padrão (ponto (e)); o **forro** fica acima do plano de
  corte: aparece como **projeção tracejada** do contorno (revisão de 2026‑11‑07),
  categoria de pena própria "Projeção do forro" (pena 1, 0,13 mm); escolhe‑se o forro
  clicando na linha, para não tampar o piso e o ambiente. A planta de forro (vista de
  baixo, com paginação e luminárias) fica para depois.
- **3D e cortes:** os dois aparecem, com a cor e a hachura de corte das camadas.
- **Tabelas:** nova lista "Revestimentos" (tipo, ambiente, pavimento, área, espessura) e
  as colunas "Forro" e "Piso" (tipo e área) na tabela de ambientes.

## 6. No IFC
- `IfcCovering` com `PredefinedType` `CEILING`/`FLOORING`, tipado por `IfcCoveringType`
  com `IfcMaterialLayerSet`; na ocorrência, `IfcMaterialLayerSetUsage` (`AXIS3`;
  sentido para cima no forro, para baixo no piso).
- Contido no pavimento (`IfcRelContainedInSpatialStructure`) e ligado ao ambiente por
  `IfcRelCoversSpaces` (só os presos).
- `Body`: extrusão do contorno; `FootPrint` 2D.
- `Qto_CoveringBaseQuantities`: `Width` (espessura), `GrossArea` (contorno), `NetArea`
  (desconta furos). `Pset_CoveringCommon` com `Reference` = nome do tipo.
- Pset `BrasBim_Revestimento`: `Ambiente` (GlobalId ou vazio), `Altura` (forro),
  `Deslocamento` (piso).
- Rebaixo da laje: o `Body` da laje vira `Clipping` (`IfcBooleanClippingResult` com
  `IfcPolygonalBoundedHalfSpace` no contorno do piso) e uma `IfcRelInterferesElements`
  `Recorte` liga a laje (`RelatingElement`) ao piso (`RelatedElement`), como nos outros
  recortes (spec/ui 12 §2.3). No IFC 2x3 os recortes saem (spec/ui 47).

## 7. Testes
- **FP01** forro num ambiente de 4 × 3: `IfcCovering` `CEILING`, tipo com camadas,
  `IfcRelCoversSpaces`, corpo de 2,60 a 2,6125, quantidades; reabre igual.
- **FP02** piso no mesmo ambiente: `FLOORING`, topo no nível, espessura para baixo.
- **FP03** mover uma parede refaz o ambiente, o forro e o piso; desfazer volta.
- **FP04** em todos os ambientes: um de cada por ambiente, sem duplicar; recusa o mesmo
  tipo duas vezes no mesmo ambiente.
- **FP05** pé‑direito do ambiente com forro = altura do forro.
- **FP06** apagar o ambiente solta o revestimento; contorno livre editável.
- **FP07** planta com a hachura do piso; tabela de revestimentos e colunas na de
  ambientes.
- **FP08** interface: ferramentas Forro e Piso (ambiente e contorno), barra Opções, ficha,
  Em todos os ambientes com Desfazer no balão.

## 8. Pontos para o revisor
**Respostas (2026‑11‑05):** o revisor deixou a escolha comigo, para testar na prática;
valem as propostas, com Archicad e Revit como base. (a) biblioteca do §2 mais **Forro de
drywall**, **Piso laminado** e **Granito**; (b) **2,60 m**; (c) **topo no nível do
pavimento**, espessura para baixo; (d) **desconta os pilares** (também o pilar que nasce
no nível do piso); (e) a paginação sai **sempre** que o material de cima tiver hachura de
corte (Porcelanato 60 × 60, Cerâmica 45 × 45, vinílico e laminado em réguas); para
desligar, troca‑se a hachura do material; (f) rodapé e revestimento de parede **depois**.

**Ajustes ao implementar:**
- Um só diálogo, **Projeto > Tipos de forro e piso**, com a função Forro ou Piso; sem
  representação própria na planta (vale o material de cima).
- O uso (`CEILING`/`FLOORING`) fica no `IfcCoveringType`; a ocorrência deixa o
  `PredefinedType` vazio, como manda o IFC 4 quando o tipo já diz.
- `IfcMaterialLayerSetUsage` igual ao da laje (`AXIS3`, `POSITIVE`, camada 1 embaixo), no
  forro e no piso.
- Modo **Pelo ambiente** só pega ambientes que existem; fora de um ambiente, a ferramenta
  recusa e lembra da ferramenta Ambiente ou do modo Contorno (polígono ou retângulo).
- **Em todos os ambientes** pula o ambiente que já tem um revestimento **do mesmo uso**
  (um piso qualquer), não só do mesmo tipo.
- Mover ou copiar: o forro/piso movido junto com o ambiente segue o ambiente; movido
  sozinho, solta; a cópia sai solta.
- Na ficha do ambiente, a seção "Forro e piso" lista os presos (clicar seleciona).
- Tabelas: categoria "Revestimentos (forro e piso)" (uso, ambiente, área, área bruta,
  espessura) e o modelo pronto "Forro e piso por tipo"; na de ambientes, as colunas
  Forro, Área de forro, Piso, Área de piso.
- A planta de forro e o balão ao excluir o ambiente ficam para depois.

**Revisão do teste de uso (2026‑11‑07):** (1) o piso e a laje tinham o topo na mesma cota
e o 3D piscava (faces coincidentes) e o volume contava duas vezes. O revisor escolheu
**a laje rebaixa sozinha** (em vez de o piso por cima da laje): ver §4 e §6. Testes em
`tests/test_piso_rebaixa_laje.py`. (2) O forro passa a aparecer na planta como projeção
tracejada (§5). (3) O revisor pediu escolher o tipo de linha (contínua, tracejada,
traço‑ponto…) em cada elemento: spec própria.
- Atalhos: FR (forro) e PS (piso).

- (a) A biblioteca inicial de tipos do §2 serve? Falta algum comum (forro de gesso
  acartonado/drywall, piso laminado, granito)?
- (b) Altura padrão do forro: **2,60 m** (proposta) ou outra?
- (c) Piso com o **topo no nível do pavimento** e a espessura para baixo (proposta: o
  nível do pavimento é o piso acabado, e a laje fica abaixo), ou o piso em cima da laje
  (topo = nível + espessura)?
- (d) O contorno preso ao ambiente desconta os pilares (como a área líquida do ambiente)
  ou cobre por baixo deles (proposta: desconta, para a área sair certa)?
- (e) Hachura do piso na planta **ligada** por padrão (proposta) ou desligada?
- (f) Rodapé (`SKIRTINGBOARD`) e revestimento de parede (`CLADDING`) por ambiente ficam
  para depois (proposta)?

## 9. Ordem
Uma sessão: núcleo e IFC (FP01–FP06), depois planta, tabelas e interface (FP07–FP08).

## 10. Fontes
Complemento da pesquisa §1–§4; esquema IFC 4.3 (IfcOpenShell). Base própria: spec/ui 13
§3 (ambientes), `spec/elementos/laje.md` (camadas e tipos), spec/ui 17 (tabelas).
