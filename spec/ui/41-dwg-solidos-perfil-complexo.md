---
documento: Exportar DWG/DXF, operações de sólidos e perfil complexo
requisito: RF-DOC (exportação 2D), RF-ELE (modelagem); pedido do revisor em 2026-10-29
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-29
status: em revisão
revisor: OTTO
---

# Exportar DWG/DXF, operações de sólidos e perfil complexo

## 1. Propósito
Três funções pedidas pelo revisor, a partir da pesquisa
`research_notes/Pesquisa Archicad Revit AutoCAD/complemento_dwg_solidos_perfis.md`.
(A spec do 3D prevista no plano das barras como "41" passa a ser a 42.) Ordem proposta de
entrega: §2 DWG (usa o que já existe) → §3 sólidos (núcleo pronto em parte) → §4 perfil
complexo (o maior). Pontos para o revisor no §6.

## 2. Exportar DWG/DXF
**O quê:** Arquivo > Exportar DWG/DXF abre um quadro com a lista do Navegador: plantas
(pavimentos), cortes e fachadas, vistas salvas e pranchas, com caixas para marcar; formato
**DWG** (padrão) ou **DXF**; pasta; um arquivo por item, com o nome do item. Botão direito
numa vista ou prancha do Navegador: "Exportar DWG". A exportação da área (spec/ui 38 §5)
ganha DWG também.

**Como fica o desenho:**
- O mesmo desenho da tela e do PDF (penas, hachuras, textos, cotas, situação, camadas
  visíveis da vista), pelo gravador DXF da área (`_DxfPainter`), que sai da exportação da
  área para um módulo próprio.
- Vista (planta, corte, vista salva): espaço do modelo, em **metros**, na posição real do
  projeto (0,0 do projeto). Opção: coordenadas do terreno (georreferência, se houver).
- Prancha: espaço do papel, em **milímetros**, um layout com o nome da prancha; cada
  desenho posto vira um **bloco** escalado e recortado pelo limite; carimbo e moldura em
  linhas. (Espaço do modelo com viewport e XREF ficam para depois de testar num CAD.)
- **Camadas do DWG = camadas do BrasBim** (o nome e a ordem); anotações na camada delas.
  Cor = cor da pena (cor verdadeira; opção "cores do AutoCAD" pela mais próxima).
  **Espessura = a da pena** em cada objeto (o DWG imprime igual ao PDF).
- Cotas e textos em linhas e textos simples na primeira entrega (sem entidades de cota
  associativas). Hachuras: sólidas e de linhas, como na tela.
- DXF: versão 2018 (ezdxf). DWG: o DXF passa pelo `dxf2dwg` do GNU LibreDWG, que grava a
  versão **2000** (abre em qualquer AutoCAD). O conversor é o mesmo pacote oficial já usado
  para abrir DWG (spec/ui 22), baixado com conferência do SHA‑256 e chamado como programa à
  parte; o aviso de licença GPL acompanha.

**Teste:** DG01 (planta com paredes, porta, cota e hachura → DXF com as camadas, cores e
espessuras certas; DWG relido pelo `dwg2dxf` com as mesmas entidades); DG02 (prancha →
layout em mm com os blocos); DG03 (sem conversor: oferece DXF e o download).

## 3. Operações de sólidos
**O quê:** um elemento (**alvo**) é modificado pela forma de outro (**operador**), que não
muda. É **associativo**: mexer em qualquer um refaz o resultado. Operações:
1. **Subtrair** — tira do alvo o volume do operador;
2. **Subtrair para cima** — tira o operador e tudo acima dele (cobertura aparando
   paredes, viga sob laje);
3. **Subtrair para baixo** — tira o operador e tudo abaixo dele (laje abrindo o terreno);
4. **Interseção** — o alvo fica só com a parte dentro do operador.
(Somar fica de fora: o operador continua existindo e o volume contaria duas vezes.)

**Como se usa:** ferramenta **Recortar por elemento** (grupo Edição e menu Editar): com
os alvos selecionados, a barra Opções escolhe a operação; clica-se no operador (ou em
vários, Enter termina). Sem seleção, primeiro clica nos alvos. Na ficha do alvo, a seção
**Recortado por** lista "Cobertura 1 · subtrair para cima" com botão para tirar; na do
operador, **Recorta**. Botão direito: "Tirar recortes". Um operador pode ficar numa camada
escondida e continua cortando (como no Archicad).

**No IFC:**
- A relação: `IfcRelInterferesElements` com `RelatingElement` = alvo, `RelatedElement` =
  operador, `ImpliedOrder` = verdadeiro, `InterferenceType` = `SUBTRACT`,
  `SUBTRACT_UP`, `SUBTRACT_DOWN` ou `INTERSECT`. É o que o esquema 4.3 prevê para "de
  quem se subtrai a interferência".
- O resultado também vai na forma do alvo (`IfcBooleanClippingResult` /
  `IfcBooleanResult` sobre o corpo de antes), para quem lê o IFC ver a forma certa sem
  conhecer a relação. Para cima e para baixo usam semiespaços pelos planos do operador
  (o mesmo mecanismo dos recortes pilar/viga/laje/parede, `structure/cuts.py`); subtrair e
  intersectar usam o corpo do operador posto no lugar do alvo.
- Apagar o operador tira a relação e devolve a forma do alvo, **com aviso** na barra de
  mensagens. Copiar só o alvo: a cópia não leva o recorte; copiar os dois juntos leva.
  Operações viram ops serializáveis (colaboração, desfazer).

**Onde aparece:** 3D, cortes e fachadas (pela geometria), quantitativos (volume e áreas do
resultado) e **planta**: o alvo cujo recorte cruza o plano de corte é desenhado pela
seção da forma resultante (fatia no plano de corte), em vez do desenho por camadas.

**Teste:** SO01 subtrair (volume do alvo cai o do pedaço comum; relação no IFC; reabrir o
arquivo mantém); SO02 cobertura aparando parede (para cima); SO03 mover o operador refaz
o alvo; SO04 apagar o operador devolve e avisa; SO05 interseção; SO06 na interface
(ferramenta, ficha, botão direito, planta cortada).

## 4. Perfil complexo
**O quê:** uma seção desenhada à mão, com várias partes, cada uma com seu material e papel
(núcleo ou acabamento), usada para **paredes** (retas e curvas), **vigas** e **pilares**.
Ex.: muro com capa e pingadeira, platibanda com rufo, viga com mísula, pilar em L, parede
com rodapé e moldura.

**Editor de perfis** (Projeto > Perfis): lista dos perfis do projeto (com "serve para":
parede, viga, pilar) e uma área de desenho em escala real com grade e as ferramentas de
desenho 2D que já existem (retângulo, polilinha com arcos, círculo). Cada região fechada é
uma **parte**: material (da lista de materiais, que dá a hachura e a cor do 3D) e papel.
Marcas: o **ponto de inserção** (a linha de referência da parede, o eixo da viga e do
pilar) e as **faixas de esticar** (uma horizontal e uma vertical, opcionais): o que está
além da linha anda quando a largura ou a altura do elemento mudam. Sem faixa, o perfil
tem tamanho fixo.

**No elemento:** o tipo do elemento ganha a estrutura **Perfil** (além de camadas, para
parede; e de retângulo/círculo, para viga e pilar). Na ficha: o perfil, a largura e a
altura nominais (só se o perfil tem faixa de esticar) e o espelhar.

**No IFC:**
- O perfil do projeto: `IfcMaterialProfileSet` com um `IfcMaterialProfile` por parte
  (perfil `IfcArbitraryClosedProfileDef` ou `...WithVoids`, material, categoria
  `LoadBearing`/`Finish`), associado ao **tipo**; o nome e as faixas de esticar num Pset
  `BrasBim_Perfil`.
- A forma do elemento: viga e pilar, `IfcExtrudedAreaSolid` do perfil resolvido
  (`IfcCompositeProfileDef` das partes); parede reta, a mesma extrusão deitada ao longo do
  eixo; parede curva, varredura pela diretriz do eixo. Uma forma por parte (assim cortes e
  3D pintam cada material).
- Uso de material: viga e pilar com `IfcMaterialProfileSetUsage` (como hoje); parede
  conforme o ponto (h).

**Planta:** a parede de perfil é desenhada pela fatia do perfil na altura do plano de corte
(as partes cortadas com a hachura do material) e o que está abaixo, em projeção.
Portas e janelas cortam o perfil inteiro (ponto (i)). Junções em L e T entre paredes de
perfil: esquadria pela bissetriz; entre perfil e camadas, a de camadas para na face.

**Teste:** PC01 perfil com duas partes → `IfcMaterialProfileSet` no tipo e formas no
elemento, reabre igual; PC02 esticar (altura 3,00 → 3,50 move só o que está acima da
faixa); PC03 parede reta e curva com perfil (volume por material na tabela); PC04 viga e
pilar com perfil; PC05 planta da parede de perfil no plano de corte; PC06 editor de
perfis na interface.

## 5. Ordem e tamanho
1. §2 DWG/DXF: 1 sessão (o desenho já existe).
2. §3 sólidos: 2 sessões (núcleo e IFC; interface e planta).
3. §4 perfil complexo: 3 sessões (núcleo e IFC; editor; planta e junções).

## 6. Pontos para o revisor
- (a) DWG: unidade da vista em **metros** (proposta), centímetros ou milímetros?
- (b) DWG: prancha no espaço do papel com os desenhos como blocos (proposta), ou já
  tentar viewport no espaço do modelo?
- (c) DWG: cor verdadeira da pena (proposta) ou as 255 cores do AutoCAD?
- (d) DWG 2000 é o único que o conversor livre grava bem. Serve? (Senão, só DXF 2018.)
- (e) Você pode abrir o primeiro DWG gerado no AutoCAD (ou outro CAD) para validar?
- (f) Sólidos: deixar **Somar** de fora (proposta)?
- (g) Sólidos: apagar o operador desfaz o recorte com aviso (proposta), ou impedir apagar
  enquanto recorta algo?
- (h) Perfil na parede: se o IFC 4.3 não aceitar o conjunto de perfis na parede, o conjunto
  fica só no tipo (proposta) — confirmar ao implementar.
- (i) Portas e janelas em parede de perfil: cortam a seção inteira (proposta) ou só o
  núcleo?
- (j) Primeira entrega do perfil só com as faixas de esticar (proposta); os deslocamentos
  nomeados por parte (como "espessura do reboco") ficam para depois?
- (k) Frisos ao longo da parede (rodapé, moldura, pingadeira como objeto à parte, à moda
  dos frisos do Revit) ficam para depois do perfil?

## 7. Fontes
`research_notes/Pesquisa Archicad Revit AutoCAD/complemento_dwg_solidos_perfis.md` (§1–§3,
com as URLs da Graphisoft, Autodesk, GNU LibreDWG, ODA, OSArch e buildingSMART);
`archicad_modelagem.md` (SEO, perfis complexos, laje e cobertura);
`revit_modelagem_familias.md` (frisos e rebaixos); `autocad.md` (DWG/DWF no Brasil).
