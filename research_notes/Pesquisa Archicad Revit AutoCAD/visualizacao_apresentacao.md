# Visualização, renderização e apresentação ao cliente (Archicad, Revit, AutoCAD) — 2026

Notas de pesquisa clean-room: só fontes públicas da web, acesso em 2026-10-21. Nada foi lido de `_restrito/` nem de `tools/`. Os textos foram resumidos com palavras próprias.
**Aviso de método:** o limite de buscas da sessão acabou no meio da pesquisa. Por isso, AutoCAD (estilos visuais), detalhes dos estilos 3D do Archicad, VR/AR e preferências no Brasil ficaram com pouca ou nenhuma fonte (ver "Lacunas"). Três páginas oficiais devolveram HTTP 403 (licença do Twinmotion, blog da Autodesk e artigo da comunidade Graphisoft). Nesses casos foram usados só os trechos que apareceram nos resultados de busca.

## 1. Recursos nativos (Archicad, Revit, AutoCAD)

### Conclusão
Os três programas têm modos de vista do tipo sombreado, linhas ocultas e realista, e o Archicad e o Revit têm um render embutido. Em 2025–2026, porém, a novidade veio de duas frentes: geração de imagem por IA (AI Visualizer no Archicad, Veras via Chaos) e aceleração por GPU da navegação (Revit 2026 Accelerated Graphics). O render fotorrealista "sério" continua sendo feito em ferramentas externas.

### Fontes e o que foi extraído
- **Archicad: motores embutidos.** A central de ajuda da Graphisoft lista CineRender (Maxon) e Redshift (Maxon) como motores integrados. O Redshift é escolhido dentro das Configurações de Fotorrenderização: motor "Cineware by Maxon" e depois renderizador "Redshift". A mesma página cita integrações externas com Enscape, Twinmotion, NVIDIA Omniverse e Lumion. Fonte: trecho da busca em [Graphisoft Help Center – Visualization](https://helpcenter.graphisoft.com/category/visualization/) e [Comunidade Graphisoft – Streamlined Visualization](https://community.graphisoft.com/t5/Visualization/Streamlined-Visualization/ta-p/396969). O 403 impediu a leitura completa.
- **Archicad: CineRender está "obsoleto"?** Em um tópico da comunidade, usuários dizem que, com o Direct Link para Twinmotion ou Enscape, quase não precisam mais do CineRender, e que o Redshift o deixa um pouco mais rápido. É opinião de usuários. Não encontrei anúncio de remoção do CineRender. Fonte: [Comunidade Graphisoft – Is Cinerender obsolete?](https://community.graphisoft.com/t5/Visualization/Archicad-Cinerender-Is-Cinerender-obsolete/m-p/680142)
- **Archicad: o Redshift já vem na assinatura**, com aceleração por GPU e boa relação entre qualidade e velocidade, mas é mais difícil de aprender para iniciantes em 3D. A fonte é um fornecedor concorrente (serviço de render por IA), então vale tratar com cautela. Fonte: [MyArchitectAI (pt) – Renderizadores para Archicad 2026](https://www.myarchitectai.com/pt/blog/archicad-rendering-software)
- **Archicad: AI Visualizer.** Apareceu no Archicad 28 (2024). Fonte: trecho de [Comunidade Graphisoft – Archicad versions](https://community.graphisoft.com/t5/Let-s-get-started/Archicad-versions/ta-p/304207)
- **Archicad 30: AI Visualizer, segundo a ajuda oficial.**
  - Gera imagens só a partir de texto, ou parte da vista 3D ou do desenho atual para testar variações de estilo, cor, forma e fundo.
  - Edita a imagem por inpainting e por máscara (modelos "Nano-Banana").
  - Gera texturas, objetos de imagem recortados, imagens de plantas e fundos.
  - Adiciona pessoas e objetos e amplia a imagem até 4K.
  - Exige licença por assinatura.
  - Prompts e imagens ficam guardados 7 dias e não são usados para treinar o modelo.
  - Manter fielmente os materiais do modelo pode exigir combinar prompt de texto e prompt de imagem, e o resultado não é garantido.

  Fonte: [Ajuda Archicad 30 (DE) – AI Visualizer](https://help.graphisoft.com/AC/30/GER/Topics/100_Visualization/generating_ai_images.html)
- **Archicad 29** (lançado em 7/10/2025): AI Visualizer 2.0, com refinamento por prompts seguidos (troca de materiais, fundo, esquadrias, forma), controle deslizante de antes e depois, pincel para editar áreas e gravação direta da imagem no Archicad. Também trouxe configuração de DPI da vista 3D para saídas mais nítidas e modo escuro no macOS. Fonte: [Architosh – Archicad 29](https://architosh.com/2025/10/graphisoft-releases-archicad-29-with-game-changing-tools/). O AI Assistant (beta) se conecta ao AI Visualizer para gerar imagens a partir de texto. Fonte: trecho de [BauNetz Wissen – Archicad 29](https://www.baunetzwissen.de/drucken/archicad-29-neue-programmversion-10077269)
- **BIMx (Graphisoft): o hipermodelo é a ferramenta de apresentação ao cliente.**
  - Junta vistas 2D e 3D com hiperlinks.
  - Tem visualizador rápido da documentação 2D e navegação 3D no estilo de jogo.
  - Faz corte 3D em tempo real, mede no contexto do modelo e mostra dados BIM por elemento.
  - No celular: modelo de tamanho ilimitado por streaming e vista fotorrealista com iluminação em tempo real.
  - No desktop: posição do sol por data e hora, com sombras.
  - **Web Viewer:** abre o hipermodelo no navegador, sem instalar nada. O compartilhamento é por link no site BIMx Model Transfer, e incorporar o modelo em sites é só para assinantes.
  - **BIMx Desktop** (Windows e Mac): mesmas funções do Web Viewer, com suporte a mouse 3Dconnexion. Instala e atualiza junto com o Archicad.
  - Alguns recursos (criar issues, ocultar elementos 3D) eram "Pro". As fontes indicam que muitos passaram a ser liberados com conta Graphisoft gratuita, mas a divisão atual não foi confirmada.

  Fontes: [Graphisoft – BIMx](https://graphisoft.com/solutions/BIMx), [App Store – BIMx Desktop](https://apps.apple.com/app/bimx/id6446137693), [Graphisoft Help – BIMx Web Viewer](https://helpcenter.graphisoft.com/knowledgebase/76004/), [Ajuda AC24 – Novidades](https://help.graphisoft.com/AC/24/INT/_AC24_Help/005_NewFeatures/005_NewFeatures-41.htm). As informações vêm dos resumos dos resultados de busca.
- **Revit 2026: Accelerated Graphics (tech preview).**
  - Novo motor gráfico que passa para a GPU parte do trabalho de exibição, que antes ficava sobretudo na CPU. Liga e desliga por vista, num botão ao lado do ViewCube.
  - Promete navegação 3D e 2D bem mais rápida em modelos grandes. Nenhuma fonte deu números.
  - **Não suporta:** os estilos Realista e Texturas; sombras, depth cueing, linhas esboçadas, meio-tom e underlay; padrões e espessuras de linha; vínculos de coordenação e nuvens de pontos; folhas e viewports de folha. Na exportação, o Revit volta ao gráfico normal.
  - O autor do blog diz que muitos usuários comentaram que foi "o melhor recurso da versão".

  Fontes: [BIMpure – Accelerated Graphics](https://www.bimpure.com/blog/new-revit-2026-feature-accelerated-graphics); [Arkance – Revit 2026 New Features](https://emea.support.arkance.world/hc/lt/articles/36466797454226-Revit-2026-New-Features-Part-1) (trecho: folhas, viewports ativados, vistas de desenho, legendas, Realista e Sombras ainda não suportados); [Autodesk Blog](https://www.autodesk.com/blogs/aec/2025/04/09/accelerated-graphics-tech-preview-revit-2026/) (só o trecho da busca; a página deu 403). Um fórum (fonte secundária) cita recomendação da Autodesk de 64 GB de RAM e GPU de 8 GB: [AnandTech](https://forums.anandtech.com/threads/amd-soc-halo-series-gpu-discussion.2624449/post-41516194)
- **Revit: estilos visuais e sombras em vistas 2D.** O Revit gera sombras em elevações sem passar pelo Photoshop. As sombras ambientes dão aparência de céu nublado, mas sem controle de intensidade; as sombras projetadas são ajustadas nas configurações de iluminação. Silhuetas (Graphic Display Options) e depth cueing dão profundidade a elevações que, por padrão, ficam "chapadas". Fontes: [BIMpure – 10 ferramentas do Revit para estudantes](https://www.bimpure.com/blog/10-revit-tools-students-should-use-in-the-studio); [Novedge – Revit visual styles](https://novedge.com/blogs/design-news/revit-tip-optimizing-revit-visual-styles-for-clearer-views-and-efficient-workflows); [Novedge – Realistic views](https://novedge.com/blogs/design-news/revit-tip-optimizing-revit-realistic-views-for-presentations)
- **Revit: render na nuvem.** O "Render in Cloud" do Revit 2018.2 e anteriores parou de funcionar em 15/07/2022. A ajuda ainda documenta o fluxo a partir do 2018.3 (aba Vista > painel Gráficos > Render in Cloud), e os renders antigos continuam no portal "My Renderings". Para o Revit LT, a recomendação é usar a vista realista ou exportar FBX. O Revit Live foi descontinuado em 30/03/2020. Fontes: [Autodesk Help – Autodesk Rendering in Revit](https://help.autodesk.com/cloudhelp/ENU/ARENDERING/files/GUID-CF9A3100-D15E-4515-A518-BCECB9FB4365.htm); [Autodesk BR – Revit Live](https://www.autodesk.com/br/products/revit-live)
- **AutoCAD:** não houve fonte nesta sessão (o limite de buscas acabou). Ver lacunas.

### Inferências
- O padrão do mercado em 2026 tem três camadas: (a) vistas técnicas nativas (linhas ocultas, sombreado, sombras) feitas no próprio BIM; (b) render em tempo real externo com sincronização ao vivo; (c) IA generativa por cima de uma vista 3D para explorar conceitos. Para o BrasBim, (a) é obrigatório, e (c) pode ser integração opcional e plugável, porque depende de serviço na nuvem.
- O Accelerated Graphics mostra que até a Autodesk escolheu primeiro a velocidade de navegação em modelos grandes, deixando efeitos (sombras, realista) de fora no início. É uma ordem de prioridades que o viewport OpenGL do BrasBim pode copiar: primeiro FPS com modelo grande, depois efeitos.
- O BIMx é a referência de "entregável ao cliente": 2D e 3D ligados, corte em tempo real, medição, sol e link web sem instalação. Um equivalente aberto seria exportar glTF ou IFC junto com um visualizador web.

### Lacunas
- AutoCAD: lista de estilos visuais (Conceitual, Realista, Sombreado com arestas, Raio-X, Esboço etc.). Não foi verificada nesta sessão.
- Archicad: detalhes dos estilos 3D (motor de contornos, modo esboço "Sketch Rendering", estudo solar). A página oficial não foi acessada.
- Revit: Sun Path, walkthrough e estilos visuais (Wireframe, Linhas ocultas, Sombreado, Cores consistentes, Texturas, Realista, Ray Trace). Essa lista é conhecimento prévio meu, sem fonte desta sessão; confirmar em help.autodesk.com.
- Não encontrei números oficiais de desempenho do Accelerated Graphics.

## 2. Ecossistema externo de tempo real e IA (Twinmotion, Enscape, Lumion, D5, V-Ray, Vantage, Veras) e escolhas no Brasil

### Conclusão
Os renderizadores em tempo real com GPU dominam a apresentação. O Enscape funciona como plugin dentro do BIM; Lumion, Twinmotion e D5 são programas separados com sincronização ao vivo. O custo e a exigência de GPU (placa RTX) são os critérios citados com mais frequência. Em maio de 2026, a Chaos passou a incluir a IA Veras em todos os planos de Enscape, V-Ray e Corona.

### Fontes e o que foi extraído
- **Preços (USD; as fontes divergem, então confirmar nos sites oficiais):**
  - **Twinmotion:** grátis para estudantes e para empresas com receita anual abaixo de US$ 1 mi; US$ 445 por assento por ano. Fontes: [Rendair – Twinmotion alternatives 2026](https://rendair.ai/blog/top-6-twinmotion-alternatives-for-architects-in-2026); [MyArchitectAI](https://www.myarchitectai.com/pt/blog/archicad-rendering-software). A página oficial deu 403.
  - **D5 Render:** versão Community grátis; Pro a US$ 360 por ano (licença flutuante) segundo o [G2](https://www.g2.com/products/d5-render/pricing), ou US$ 38 por mês segundo a [MyArchitectAI](https://www.myarchitectai.com/pt/blog/archicad-rendering-software).
  - **Enscape:** Solo a US$ 574,80 por ano ([Illustrarch](https://illustrarch.com/articles/design-softwares/78294-enscape-alternatives.html)) contra "a partir de US$ 85 por mês" ([MyArchitectAI](https://www.myarchitectai.com/pt/blog/archicad-rendering-software)). O [Capterra](https://capterra.com/compare/207052-10005615/Enscape-vs-D5-Render) mostra um valor inicial inconsistente.
  - **Lumion:** Pro a US$ 1.149 por ano ([LearnArchitecture](https://learnarchitecture.net/3d-visualization/34089-enscape-vs-lumion.html)) ou € 1.299 por ano ([Capterra](https://capterra.com/compare/174874-10005615/Lumion-vs-D5-Render)), contra "a partir de US$ 749 por ano" (MyArchitectAI).
  - **V-Ray:** a partir de US$ 85 por mês. **Corona:** a partir de US$ 60 por mês, só CPU. Fonte: MyArchitectAI.
- **Posicionamento:**
  - Enscape é plugin dentro do programa de modelagem e dá o retorno mais rápido às mudanças de projeto. Lumion é programa separado, com biblioteca de ativos maior e pós-processamento mais forte, e só roda em Windows. Enscape roda em Windows e macOS. Fonte: [LearnArchitecture – Enscape vs Lumion](https://learnarchitecture.net/3d-visualization/34089-enscape-vs-lumion.html)
  - Twinmotion usa a Unreal Engine e tem Path Tracer, bom para interiores (luz indireta, sombras suaves). Fonte: [Rendair](https://rendair.ai/blog/top-6-twinmotion-alternatives-for-architects-in-2026)
  - D5 seria um meio-termo: qualidade próxima à do Lumion com fluxo parecido com o do Enscape, e versão grátis sem marca d'água. Depende de placa RTX, o que deixa de fora notebooks comuns e Macs com Apple Silicon. Fontes: [Rendair – D5 alternatives](https://rendair.ai/blog/top-6-d5-render-alternatives-for-architects-in-2026); [Maverickframe – D5 vs Lumion](https://maverickframe.com/blog/d5-render-vs-lumion/) (opinião de estúdio: D5 "mais forte e muito mais barato" para interiores e paisagismo)
  - No D5, Twinmotion e Lumion, o desempenho depende quase só da potência de uma GPU. Fonte: [DEV/iRender](https://dev.to/irender_gpu_render_farm/top-5-3d-software-work-best-with-single-gpu-4m76)
  - O Twinmotion mantém o modelo sincronizado com o Archicad em tempo real pelo Direct Link. Fonte: trecho de [Graphisoft Help Center](https://helpcenter.graphisoft.com/category/visualization/)
- **Notas no Capterra (2026, amostras pequenas):** D5 4,8 (cerca de 390 avaliações), Lumion 4,7 (157), Enscape 4,4 (72). Fonte: [Capterra](https://capterra.com/compare/207052-10005615/Enscape-vs-D5-Render)
- **Chaos Veras (27/05/2026):**
  - Passa a vir integrado em todas as versões e planos de Enscape, V-Ray e Corona, nos hosts Revit, Archicad, SketchUp, Rhino, Vectorworks e 3ds Max.
  - Transforma esboços, imagens 2D e modelos 3D em imagens e animações para explorar conceitos.
  - Vem com licenciamento híbrido baseado em créditos, para render na nuvem e serviços de IA.
  - Outras novidades: Envision Live Link, mais de 2.500 ativos Cosmos e Cloud Video Collaboration.

  Fonte: [Chaos – press release](https://www.chaos.com/press/veras-ai-architecture-enscape-vray-corona). Segundo o [AEC Magazine](https://aecmag.com/news/veras-included-with-enscape-v-ray-corona/), o Veras usa o Nano Banana Pro do Google.
- **Enscape 4.18 (maio/2026):**
  - Suporta Revit 2027, SketchUp 2026, Archicad 29 e Vectorworks 2026.
  - Acabou o limite de cena de 2 GB.
  - Gera materiais por IA no Material Editor e amplia imagens com o AI Upscaler.
  - Veras 4.0 gera animações curtas a partir de imagens paradas e várias perspectivas a partir de uma vista.
  - A Chaos também oferece streaming na nuvem, para o cliente navegar no 3D ou anotar uma animação por link web.
  - V-Ray 7 trouxe cáusticas em GPU, Profiler e suporte a Gaussian Splats.

  Fonte: [Architosh – AIA26 Chaos](https://architosh.com/2026/07/aia26-expo-show-floor-report-4-chaos/)
- **Brasil:** a única fonte em português encontrada é a MyArchitectAI (pt), que é fornecedor concorrente e dá preços em USD. Há também um resumo, sem leitura completa, de um vídeo comparando D5, Twinmotion e Lumion: [lilys.ai](https://lilys.ai/pt/notes/d5-render-20260202/d5-twinmotion-lumion-render-battle).

### Inferências
- No Brasil, com câmbio e hardware caros, as ferramentas grátis ou baratas (Twinmotion grátis abaixo de US$ 1 mi de receita, D5 Community, Redshift incluído) devem pesar muito. Isso é inferência; não há dado brasileiro que confirme.
- Para o BrasBim, a estratégia mais barata é não competir com esses motores e oferecer boa exportação: glTF ou FBX com materiais PBR, Datasmith, ou um "live link" que só precise de um formato aberto como glTF, USD ou IFC. Blender/Cycles (de código aberto) seria o render offline de referência.

### Lacunas
- Não há pesquisa de mercado sobre qual renderizador domina no Brasil (Lumion e Enscape são populares em cursos brasileiros, mas sem fonte nesta sessão).
- Chaos Vantage, VR/AR (Enscape VR, Twinmotion VR, Revizto, Autodesk Workshop XR) e visualizadores móveis do Revit/ACC não foram pesquisados.
- Preços oficiais em BRL não foram obtidos.

## 3. Desenhos de apresentação (sombras em elevações, plantas coloridas, axonometrias, explodidas, cortes perspectivados, diagramas)

### Conclusão
Mesmo com os recursos nativos de sombra e silhueta, o fluxo comum é exportar várias versões da mesma vista (linhas, sombras, cores) e compor tudo no Photoshop. A dor é refazer esse trabalho a cada revisão do projeto.

### Fontes e o que foi extraído
- Um profissional exporta três versões da mesma elevação com view templates diferentes e as sobrepõe no Photoshop como smart objects, para que as alterações sejam recarregadas. Para profundidade, recomenda algumas árvores com sombras projetadas na fachada. Fontes: [ArchVision – estilos de apresentação (MVE Partners)](https://archvision.com/presentation-styles-of-corbin-savopoulos-mve-partners/); [AUGI forum](https://forums.augi.com/archive/index.php/t-44119.html)
- Um fluxo baseado no Photoshop parte só de linhas (CAD ou 3D com a perspectiva desligada) e faz o resto no Photoshop, sem motor de render. Fonte: [Visualizing Architecture](https://visualizingarchitecture.com/?p=859)
- Corte perspectivado exportado do Revit em linhas ocultas com sombras, e depois acabado no Photoshop com textura grunge, céu, brilhos e poché. Fonte: [CGarchitect – Revit Conceptual Workflow](https://cgarchitect.com/images/802aca84)
- A demanda existe a ponto de haver cursos para fazer pranchas de apresentação "só no Revit, sem Photoshop" e uma palestra do Autodesk University sobre gráficos de apresentação no Revit. Fontes: [Udemy](https://www.udemy.com/course/create-stunning-drawing-using-only-revit-without-photoshop/); [AU – Revit for presentations](https://static.au-uw2-prd.autodesk.com/AB4564_v2_ab4564_20-_20revit_20for_20presentations_20graphics_20that_20pop_20presentation.pdf)
- O Archicad 29 permite definir o DPI da vista 3D, e um beta tester destacou a melhora na qualidade da saída 3D. Fonte: [Architosh](https://architosh.com/2025/10/graphisoft-releases-archicad-29-with-game-changing-tools/)

### Inferências
- Oportunidade para o BrasBim: "estilos de apresentação" nativos e reaproveitáveis (sombras em elevação com controle de intensidade, poché e preenchimento por categoria, cor por zona ou ambiente em planta, axonometria e explodida por pavimento, corte perspectivado com plano de corte preenchido), que sejam regenerados quando o modelo muda. Isso evita o retrabalho no Photoshop.
- Exportar camadas separadas (linhas, sombras, cores, máscaras por categoria) em PNG, SVG ou PSD já resolveria boa parte do fluxo atual.

### Lacunas
- Não houve fontes de Reddit nem de canais brasileiros (a busca não as trouxe e o limite acabou).
- Vistas explodidas e diagramas: nenhuma fonte específica coletada.

## 4. Expectativas de tecnologia do viewport e motores de código aberto integráveis

### Conclusão
Os usuários esperam navegação fluida em modelos grandes, que é a prioridade da própria Autodesk em 2026. Esperam também caixas de corte em tempo real, transparência, sombras do sol por data e hora e materiais realistas. No mundo aberto existem Bonsai (Blender, com IfcOpenShell) e o stack web ThatOpen (web-ifc e three.js), que já resolvem streaming e culling de modelos grandes.

### Fontes e o que foi extraído
- **Corte 3D e sol:** o BIMx tem corte 3D em tempo real, sol por data e hora com sombras e vista fotorrealista com iluminação em tempo real no celular. Fonte: [Graphisoft – BIMx](https://graphisoft.com/solutions/BIMx); [App Store](https://apps.apple.com/app/bimx/id6446137693)
- **Desempenho:** no Revit 2026, a GPU passou a assumir a navegação, sem sombras nem realista nesse modo. Fonte: [BIMpure](https://www.bimpure.com/blog/new-revit-2026-feature-accelerated-graphics). O Enscape 4.18 removeu o limite de cena de 2 GB, sinal de que modelos grandes travavam. Fonte: [Architosh](https://architosh.com/2026/07/aia26-expo-show-floor-report-4-chaos/)
- **Bonsai (ex-BlenderBIM):** plataforma BIM de código aberto dentro do Blender, mantida pela comunidade IfcOpenShell, com geração de desenhos entre outras funções. Fonte: [Build Up (UE)](https://build-up.ec.europa.eu/de/node/69539). Um usuário do fórum Graphisoft comenta que, ao abrir IFC no Bonsai, os recursos de render do Blender ficam disponíveis. Ele desaconselha usar IFC como formato para render porque há problemas com objetos de vários materiais e o IFC não exporta texturas; recomenda FBX ou OBJ. Outro usuário observa que o Blender 5.0 deixou de suportar oficialmente o DAE (Collada). Fonte: [Comunidade Graphisoft – Archicad-Blender Connection](https://community.graphisoft.com/t5/Collaboration-with-other/Archicad-Blender-Connection/m-p/686852)
- **ThatOpen (web):** o `web-ifc-viewer` foi descontinuado em favor de `@thatopen/components`, com web-ifc (WASM) e three.js. Um IfcStreamer carrega a geometria aos poucos, com LOD, e um culler oculta e descarrega a geometria fora da tela. Cada modelo aberto ocupa bastante memória WASM. Fontes: [awesome.ecosyste.ms – web-ifc-viewer](https://awesome.ecosyste.ms/projects/github.com%2FThatOpen%2Fweb-ifc-viewer); [mintlify – AI-BIM-APP](https://mintlify.com/bnares/AI-BIM-APP/features/ifc-viewer) (fonte secundária). Alternativa: **ifc-lite**, com renderização WebGPU e camada de servidor em Rust ou Tauri para arquivos grandes; os benchmarks não foram verificados. Fonte: [awesome.ecosyste.ms – ifc-lite](https://awesome.ecosyste.ms/projects/github.com%2Flouistrue%2Fifc-lite)

### Inferências
Recomendações para o BrasBim:
- **Prioridade 1 (viewport OpenGL):** desempenho com modelo grande, com instancing, culling por frustum, LOD e geometria em cache por tipo. Planos e caixa de corte com tampa preenchida (poché), transparência e raio-X por categoria.
- **Prioridade 2:** estilos de exibição (sombreado, linhas ocultas, sombreado com arestas, cor por classe ou propriedade, esboço) e sombra do sol por data, hora e local (latitude e longitude do IfcSite).
- **Prioridade 3:** materiais PBR simples e exportação glTF com materiais, para Blender/Cycles, Twinmotion, D5 e visualizador web (three.js ou ThatOpen) como "BIMx aberto".
- O IFC em si não carrega texturas de forma prática, segundo o comentário no fórum. Por isso a exportação de apresentação deve sair em glTF/FBX/USD, não em IFC.
- Godot como motor embutido: sem fonte nesta sessão.

### Lacunas
- Não há benchmarks públicos (FPS ou número de triângulos) de viewports BIM comparáveis.
- Integração com Godot e uso do Cycles de forma independente (fora do Blender): não pesquisados por causa do limite de buscas.
- PBR e sombras em tempo real nos viewports nativos do Archicad e do Revit: não confirmados por fonte oficial nesta sessão.
