# Complemento: forro e piso como revestimento (2026‑11‑05)

Item M3 da revisão geral (`reports/Revisao geral antes do instalador (2026-10-30).md`):
"forro e piso como revestimento (`IfcCovering`)", RF‑ELE‑12. Só fontes públicas; descreve
**funções**, sem copiar nomes de comandos nem diálogos. As páginas oficiais de ajuda do
Revit e do Archicad sobre o assunto não abriram para leitura automática (404/403); o que
segue vem do resumo do buscador e de tutoriais, marcado **(via busca)**, e do esquema
IFC 4.3 que vem com o IfcOpenShell (lido aqui, offline).

## 1. Revit: forro como elemento próprio (via busca)
- O forro é um elemento **de nível**: fica a uma distância acima do nível em que está
  (ex.: 3 m acima do Nível 1). Nas versões novas, a distância é da **ocorrência**
  ("deslocamento do nível"), e não do tipo, como dizia a ajuda de 2014. —
  [About Ceilings (2014)](https://help.autodesk.com/cloudhelp/2014/ENU/Revit/files/GUID-15615B41-B1B2-4B72-86CA-3ECF8729A730.htm);
  [ajuda 2015, parâmetro de deslocamento](https://help.autodesk.com/cloudhelp/2015/ENU/Revit-Model/files/GUID-3A26F511-C3E7-4561-820C-62AD520F1358.htm)
- **Forro automático:** passando o mouse sobre um espaço fechado por paredes, aparece o
  contorno; um clique põe o forro. É o caminho rápido em sala retangular; contorno
  desenhado à mão para formas irregulares. — [CADdetails: introdução aos forros](https://caddetailsblog.com/post/revit-architecture-an-introduction-to-ceilings)
- Fórum: o forro pode aparecer pelo ambiente do nível de cima (o nível associado conta);
  recomenda‑se pôr a altura padrão do forro no modelo de projeto. —
  [Fórum: automatic ceiling not working](https://forums.autodesk.com/t5/revit-architecture-forum/automatic-ceiling-tool-not-working/m-p/12299558);
  [Fórum: ceilings showing second floor](https://forums.autodesk.com/t5/revit-architecture-forum/ceilings-are-showing-second-floor-not-first/m-p/12926836)
- O piso de acabamento costuma ser feito com o próprio elemento de piso (laje) fino, com
  deslocamento — não há elemento próprio de revestimento de piso.

## 2. Archicad: forro e piso com laje (via busca, fórum)
- Não há ferramenta de forro: forro e piso acabado são **lajes**, em geral criadas com a
  "varinha mágica" sobre o carimbo da zona (ambiente), que copia o contorno dela. Os
  usuários citam: laje de piso acabado, rebaixo de forro num cômodo, hachura do piso. —
  [Fórum: Magic Wand polygons onto zones](https://community.graphisoft.com/t5/Modeling/Magic-Wand-Polygons-onto-Zones-Using-the-Stamp/m-p/94016)
- Um assistente de interiores cria forros **ligados às zonas** (a altura da zona define
  a do forro); um tópico antigo diz que uma ferramenta de forro por zona foi
  descontinuada. — [Fórum: Ceiling objects](https://community.graphisoft.com/t5/Modeling/Ceiling-objects/td-p/25777)
- Clicar dentro do cômodo pega a linha de parede mais próxima e pode dar uma laje
  pequena demais. — [Fórum: slab using the inner edge of a wall](https://community.graphisoft.com/t5/Modeling/Is-there-a-way-to-create-a-slab-using-the-inner-edge-of-a-wall/m-p/367054)
- Paginação: dar ao material da laje uma hachura de desenho (e não um preenchimento
  simples). — mesmo tópico da varinha.

## 3. Quantitativos (já na pesquisa)
- **Reboco acima do forro:** um formador certificado recomenda modelar o forro como
  operação de sólidos que subtrai das paredes, para tirar do quantitativo o reboco que
  fica escondido (`quantitativos_orcamento_sustentabilidade.md`, F426–F427).
- Revestimentos por ambiente (piso, forro, faces de parede) são, nas três ferramentas, o
  caso que exige modelagem extra (mesmo arquivo).

## 4. IFC 4.3 (esquema e modelos do IfcOpenShell)
- `IfcCovering` (subtipo de `IfcBuiltElement`), `PredefinedType` entre `CEILING`,
  `FLOORING`, `CLADDING`, `COPING`, `INSULATION`, `MEMBRANE`, `MOLDING`, `ROOFING`,
  `SKIRTINGBOARD`, `SLEEVING`, `TOPPING`, `WRAPPING`, `USERDEFINED`, `NOTDEFINED`.
- Ligação com o ambiente: `IfcRelCoversSpaces` (`RelatingSpace`, `RelatedCoverings`); com
  um elemento: `IfcRelCoversBldgElements` (`RelatingBuildingElement`, `RelatedCoverings`).
- `Pset_CoveringCommon`: `Reference`, `Status`, `AcousticRating`, `FlammabilityRating`,
  `FragilityRating`, `Combustible`, `SurfaceSpreadOfFlame`, `Finish`, `IsExternal`,
  `ThermalTransmittance`, `FireRating`. `Pset_CoveringFlooring` (só `FLOORING`):
  `HasNonSkidSurface`, `HasAntiStaticSurface`.
- `Qto_CoveringBaseQuantities`: `Width` (espessura), `GrossArea`, `NetArea`.

## 5. O que o BrasBim já tem
- **Ambientes** (`IfcSpace`, spec/ui 13 §3) que **se refazem pelas paredes** (semente do
  cômodo), com pé‑direito calculado (até o fundo da laje de cima) ou fixo, e
  `NetFloorArea` que desconta pilares.
- Lajes com camadas e tipos; operações de sólidos (para o reboco acima do forro, depois).

## 6. O que levar para o BrasBim (vai para a spec/ui 46)
1. **Elemento próprio** de forro e de piso (`IfcCovering` `CEILING`/`FLOORING`), e não
   laje fina como nos outros dois: o quantitativo e o IFC ficam certos sem truque.
2. **Por ambiente, num clique** (como o forro automático), e **o contorno acompanha o
   ambiente**, que já acompanha as paredes — o que o Archicad perde (a varinha copia o
   contorno uma vez) e o Revit só faz na criação.
3. **Forro e piso em todos os ambientes do pavimento** de uma vez (o assistente de
   interiores do Archicad, simplificado).
4. **Tipos com camadas** (forro de gesso; porcelanato + argamassa + contrapiso), como os
   da parede e da laje.
5. Forro com **altura do pavimento** (ocorrência), e o **pé‑direito do ambiente passa a
   ser o do forro** quando há forro.
6. `Qto_CoveringBaseQuantities` e as tabelas por ambiente; o reboco acima do forro fica
   para a entrega de quantitativos.

## 7. Lacunas
- As páginas oficiais de forro e piso do Revit e do Archicad não foram lidas (bloqueadas);
  conferir no navegador antes de citar como regra.
