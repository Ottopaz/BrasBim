# Complemento: exportar glTF/OBJ para apresentação (2026‑11‑05)

Item I2 da revisão geral (`reports/Revisao geral antes do instalador (2026-10-30).md`):
"levar o modelo para programas de render e apresentação". Só fontes públicas.

## 1. O que já estava na pesquisa (`visualizacao_apresentacao.md`)
- A estratégia mais barata é não competir com os motores de render e **exportar bem**:
  glTF (ou FBX) com materiais, para Blender/Cycles, Twinmotion, D5 e um visualizador web
  (three.js ou ThatOpen) — um "BIMx aberto".
- O IFC não carrega textura de forma prática: a apresentação sai em glTF/FBX/USD.

## 2. Archicad (fórum Graphisoft, via busca)
- Pedido de exportação glTF na lista de desejos; a Graphisoft respondeu que **não
  planejava** o formato; há complementos de terceiros (um comercial e um de código
  aberto em beta, que exporta os corpos visíveis da janela 3D com transparência). —
  [Wish: glTF export](https://community.graphisoft.com/t5/Wishes/Wish-glTF-export/td-p/337972);
  [lista de desejos (2024)](https://community.graphisoft.com/t5/Wishlist/Wish-glTF-export/idc-p/608772/highlight/true);
  [archicad-glb-exporter](https://github.com/hildgyorgy/archicad-glb-exporter/releases)

## 3. Revit
- Não pesquisado nesta rodada (a busca só cobriu o Archicad). Lacuna.

## 4. O que levar para o BrasBim (vai para a spec/ui 48)
1. **Arquivo > Exportar 3D (glTF/OBJ)**, nativo: GLB num arquivo só (padrão) ou OBJ +
   MTL (o formato que todo programa abre).
2. Como o complemento do Archicad: **o que está visível** (camadas e situação).
3. **Cores dos materiais do BrasBim** (as mesmas do 3D), vidro transparente.
4. Melhor que os dois: cada elemento é um nó com nome, **GlobalId, classe e tipo** nos
   `extras`, agrupado por pavimento — o visualizador web acha o elemento e volta ao IFC.
5. Eixo para cima convertido (o IFC tem z para cima; o glTF, y).

## 5. Lacunas
- Revit não pesquisado; texturas (PBR com mapas) ficam para quando o BrasBim tiver
  texturas.
