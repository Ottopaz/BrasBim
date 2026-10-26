# Pente fino: cada funcionalidade do BrasBim × a pesquisa clean‑room

*2026‑10‑26. Pedido do revisor: "passa um pente fino em todas as nossas funcionalidades
com o nosso clean room". Base: as 15 notas de `research_notes/Pesquisa Archicad Revit
AutoCAD/` (lidas por inteiro nesta sessão), o relatório `reports/Pesquisa Archicad Revit
AutoCAD.md`, as specs `spec/ui/01–29` e `spec/elementos/`, o `CONTEXTO.md` e o código
atual (conferido por busca e leitura). Substitui, como retrato atual, a comparação de
2026‑10‑23 (`reports/Comparacao BrasBim x pesquisa.md`), que é anterior aos pacotes de
precisão, linha de comando e specs 25–29.*

> **Clean‑room.** Nada de `_restrito/` nem de `tools/`. Os nomes dos recursos dos outros
> programas aparecem só para identificar a função, nunca para usar na interface. A coluna
> "Pesquisa" cita a nota de onde veio o achado (por exemplo `autocad §1`); achados de
> fórum que a pesquisa marcou como trecho de busca continuam "conferir" antes de virar
> spec.

Legenda — **Hoje**: ✅ temos · ◐ em parte · ✗ não temos (conferido no código).
**Prior.**: **A** = ajuste pequeno ou de alto valor, fazer já; **B** = próximo ciclo;
**C** = depois. **★** = diferencial: nenhum dos três faz bem.

---

## 1. Resumo

**Onde já estamos à frente** (manter e testar sempre): IFC 4.3 como o próprio arquivo;
salvamento automático com recuperação (o Revit não tem); topo de parede inclinado, em
empena e parede tombada (desejo antigo no Archicad); prioridade de camadas resolvida no
modelo; anotação em mm de papel sem gestão de escala por objeto; escada que segue a
altura do pavimento; tipos e objetos dentro do arquivo; barra Opções que muda o
conteúdo e não a posição (o Revit 2027 fez o caminho contrário e tirou a barra);
seleção como no CAD em planta, 3D, prancha e folha mestra; linha de comando com apelidos
pt‑BR; tabela de penas; custo zero.

**Achados que pedem correção (não só evolução):**
1. **Ambiente não acompanha a parede movida à mão.** Só se refaz quando o próprio
   ambiente, uma laje ou o pavimento muda (`annotations/rebuild.py`). O Archicad tem a
   mesma falha e os usuários reclamam; com o quadro de áreas do item 2 isso vira erro de
   prefeitura. **A ★**
2. **Área bruta = área líquida.** `spaces.py` grava `GrossFloorArea` igual a
   `NetFloorArea`. A pesquisa mostra quatro áreas no Archicad (até a linha de
   referência, até a face, com descontos, com redução %) e o projeto legal depende disso.
   **A**
3. **Gravação do salvamento automático na linha da interface.** A pesquisa mostra os
   travamentos do Revit por E/S síncrona (`interface §5`). **B** (medir antes)
4. **Specs com texto velho** (Tab das dobradiças em 01/03/07; ver Pendências do
   CONTEXTO). **A** (só texto)

**As 12 ações de maior retorno** (detalhe nas seções 3–4):

| # | Ação | Por quê (pesquisa) | Prior. |
|---|---|---|---|
| 1 | Ambiente que se refaz quando as paredes do contorno mudam, com a área até a face, até o eixo e computável | Archicad exige atualizar à mão; base do quadro de áreas | **A ★** |
| 2 | Status de intervenção + regras gráficas por critério (cor/hachura/pena por propriedade, salvas na vista) | Cores invertidas entre cidades; Archicad usa regras ordenadas por vista | **A ★** (item 2) |
| 3 | Título da vista na prancha (nome, escala, linha) e grade/alinhamento entre folhas | Pedido muito votado no Revit; Revit 2026–27 só começou | **A** |
| 4 | Export DXF da prancha e da planta | Prefeituras e engenheiros pedem DWG/DXF junto do PDF | **A** |
| 5 | Ferramenta Medir (distância, área, perímetro) e matriz/cópia em série | Básico de CAD; não temos | **A** |
| 6 | Aritmética e coordenadas no quadro de medidas ("2*", "+0,15", "x5 y3") | Tracker do Archicad, caixa do SketchUp | **A** |
| 7 | Linhas‑guia e pontos de divisão (metade, n partes) | Archicad (guias, pontos de divisão), AutoCAD (rastreamento) | B |
| 8 | Cota viva: distâncias às vizinhas ao criar/selecionar, clicar e digitar | Coração da precisão do Revit | B |
| 9 | Validação IDS embutida (`ifctester`) + IDS dos cadernos brasileiros | Valor alto, esforço baixo; ninguém faz nativo e aberto | **A ★** |
| 10 | IFC de outra disciplina como referência + BCF | Fluxo arquiteto → Eberick/QiBuilder → compatibilização | B |
| 11 | Localização do projeto (SIRGAS 2000/UTM, `IfcMapConversion`) e deslocamento automático de DWG em UTM | Revit e Archicad confundem com 3 pontos; o BrasBim pode ter um só | B ★ |
| 12 | Escada com regras vindas de um perfil (norma/código de obras) e soluções alternativas quando a regra não fecha; degrau em leque | Queixa número 1 nos dois; o "Solver" do Archicad propõe alternativas | B ★ |

---

## 2. Método

Para cada área: o que a pesquisa diz que os três fazem (e do que os usuários
reclamam), o que o BrasBim tem **hoje** (conferido no código, não só na spec) e o ajuste
proposto. Itens já feitos nos pacotes recentes aparecem como ✅ para registrar que foram
conferidos.

---

## 3. Por área

### 3.1 Entrada de pontos e precisão

| Função | Pesquisa | Hoje | Ajuste proposto | Prior. |
|---|---|---|---|---|
| Atração em todos os elementos, com interseção, perpendicular, centro, tangente e marcador por tipo | interface §1, autocad §1 | ✅ spec 23 (`SnapIndex`) | Cor por tipo além da forma (inferência por cor do SketchUp) | C |
| Forçar um único tipo de atração no próximo clique | Revit (duas letras), AutoCAD | ✗ | Na linha de comando: "ce" centro, "pm" ponto médio… (apelidos próprios pt‑BR); menu Shift+botão direito | B |
| Rastreamento por pontos adquiridos (pausa) | autocad §1 | ◐ 0°/90° e cruzamento | Ângulos configuráveis (15/30/45°), vários pontos adquiridos ao mesmo tempo, paralela a uma aresta | B |
| Número digitado sem clicar em campo | interface §1 | ✅ | — | — |
| Trava de eixo por tecla | SketchUp (setas, Shift) | ✅ setas (spec 23) | Shift segura a direção atual, inclusive de uma aresta | C |
| Aritmética e coordenadas no quadro de medidas | Tracker do Archicad (X/Y/A/D, + − * /, relativo/absoluto) | ◐ coordenadas só na linha de comando (`x;y`, `@dx;dy`) | Expressões no quadro ("2*", "+0,15", "/3"); o analisador de fórmulas dos objetos já existe | **A** |
| Linhas‑guia persistentes | Archicad (arrastar da borda) | ✗ | Guias arrastadas da régua/borda, presas a ponto ou aresta | B |
| Pontos de divisão (metade, n partes, %) | Archicad | ✗ | Atração temporária em divisões da aresta sob o cursor | B |
| Medir a partir de uma referência | Archicad (Q), AutoCAD (tt) | ✅ ponto de referência (spec 09) | Estender a todas as ferramentas (pendência spec 09 (g)) | B |
| Cota temporária editável | Revit | ✗ | "Cota viva" ao criar/selecionar; Tab troca a referência (face, núcleo, eixo) | B |
| Ferramenta Medir | básico de CAD | ✗ | Distância, área e perímetro, com resultado copiável | **A** |
| Assentar na superfície (laje, terreno) | Archicad Gravity (só na criação) | ✗ | Pilar, objeto e vegetação pegam a cota da laje ou do terreno; "reassentar" depois (o Archicad não tem) | C ★ |

### 3.2 Seleção e edição

| Função | Pesquisa | Hoje | Ajuste proposto | Prior. |
|---|---|---|---|---|
| Janela/cruzamento, laço, soma/Shift tira, realce | autocad §1 | ✅ planta, 3D, prancha, folha mestra (28–29) | — | — |
| Selecionar semelhantes por critérios IFC | interface §2 (Filtro do Revit criticado) | ✅ spec 23 | Filtro da seleção atual por classe (tirar as portas de uma janela de seleção) | B |
| Mini‑menu sob o cursor com propriedades editáveis | BricsCAD Quad | ◐ mini‑barra com ações | 2–4 campos rápidos na mini‑barra (altura, espessura, cota) | C |
| Deslocar paralela, aparar/estender, concordar | autocad §1 | ✅ spec 23 | Prévia do aparar; arco entre paredes (spec 23 §10) | B |
| Matriz / cópia em série (linear, polar, ao longo de caminho) | autocad §1 | ✗ | Cópia em série no quadro de medidas ("x5" cópias); polar depois | **A** |
| Escala por referência, esticar por janela, alinhar por pares | autocad §1 | ✗ (só "esticar viga") | Esticar paredes/lajes por janela de cruzamento (estica sem quebrar junções, como as guias do Archicad 28) | B |
| Alças multifuncionais: vértice (acrescentar/tirar), meio do lado (virar arco), deslocar aresta | autocad §1, Archicad paleta contextual | ◐ alças de vértice | Menu na alça: acrescentar vértice, tirar, curvar, deslocar o lado inteiro | B |
| Somar/subtrair polígono ao contorno (laje, ambiente) | Archicad | ✗ | Recorte de laje pela forma de outro elemento | B |
| Pegar e aplicar configurações (favoritos) | Archicad Favorites | ✗ | "Pegar" o estado de um elemento para a ferramenta; "aplicar" a outros; conjuntos salvos | B |
| Alinhar e distribuir textos/etiquetas | Revit 2025 | ✗ | Comando para textos, etiquetas e cotas selecionados | C |
| Agrupar | RF‑NUC‑07 | ✗ | `IfcGroup` simples | C |
| Edição de vários elementos com "vários" no painel | interface §2 | ◐ (pilar/viga/laje só tipo; vários ambientes sem painel) | Painel comum com campos "vários" | B |

### 3.3 Navegação, vistas e 3D

| Função | Pesquisa | Hoje | Ajuste proposto | Prior. |
|---|---|---|---|---|
| Planta/3D/lado a lado, órbita, zoom | — | ✅ | — | — |
| Duplo clique maximiza uma vista do lado a lado | Rhino | ✗ | Barato em Qt | **A** |
| Vistas 3D padrão e câmera salva | pendência do MVP | ✅ vista 3D salva (25); ✗ topo/frente/isométricas | Botões de vistas padrão | **A** |
| Caixa de corte 3D com tampa; isolar a seleção sem sobrescrever vista do usuário | interface §3 (armadilha do Revit), visualização §4 | ✗ | Caixa de corte e "isolar" numa vista temporária | B |
| Estilos (arestas, linhas ocultas, raio‑X, cor por propriedade) | visualização §4 | ◐ sombreado | Arestas + cor por propriedade (mostra o status de intervenção no 3D) | B |
| Sol por data/hora/local | visualização §4 | ✗ | Depende da localização do projeto (3.9) | C |
| Desempenho com modelo grande (instancing, culling, cache por tipo) | visualização §4, interop §5 (limite do Bonsai vem do Blender) | ✗ não medido; várias pendências "medir em projeto grande" | **Benchmark aberto** com projeto de referência e metas (FPS, tempo de edição); depois otimizar | B ★ |

### 3.4 Parede

| Função | Pesquisa | Hoje | Ajuste proposto | Prior. |
|---|---|---|---|---|
| Reta, arco, camadas, junções L/T/X, topo inclinado/empena, tombada | archicad mod. §1 | ✅ | — | — |
| Linha de referência: face externa, interna, eixo **e faces do núcleo** | Archicad (6 posições, tecla alterna) | ◐ eixo e duas faces (`REF_LINES`) | Faces do núcleo; tecla que alterna a posição durante o traço; "reposicionar a linha mantendo a parede" | B |
| Topo ligado ao pavimento de cima com deslocamento | Archicad | ✅ (`PavimentoTopo`) | — | — |
| Nó com 3+ paredes compostas previsível | archicad mod. §1 (queixa clássica) | ◐ sem teste específico | Teste com 3 e 4 paredes de tipos diferentes; regra visível no nó | B ★ |
| Parede limita / não limita o ambiente | Archicad, Revit (Room Bounding) | ✗ | Propriedade da parede; muro baixo e guarda‑corpo não limitam | B |
| Acabamento diferente por face e nas pontas | Archicad (superfícies por face), Revit (wrap nas pontas) | ◐ camadas no tipo | Material de superfície por face da instância | C |
| Frisos e rebaixos no tipo; parede composta na vertical (barrado) | Revit | ✗ | Barrado/rodapé como região vertical do tipo (comum no Brasil) | C |
| Criar paredes em volta de um ambiente ou contorno | Revit 2026 | ✗ | "Paredes pelo contorno" (inverso da laje pelo cômodo) | B |
| Trapezoidal, poligonal, perfil complexo | Archicad (com restrições cruzadas criticadas) | ✗ | Opções independentes, sem as restrições cruzadas | C |
| Revestimento que soma na espessura vista pelas aberturas | Revit 2027 falha | ✅ camada do tipo | Manter teste | — |

### 3.5 Laje, pilar, viga

| Função | Pesquisa | Hoje | Ajuste proposto | Prior. |
|---|---|---|---|---|
| Laje poligonal, camadas, aberturas, pelo cômodo | — | ✅ | — | — |
| Laje ligada às paredes do cômodo | archicad mod. §3 (varinha não liga) | ✗ (pendência V1) | Opção "acompanhar o contorno" (mesmo mecanismo do ambiente, 3.8) | B ★ |
| Laje inclinada ou de espessura variável | Archicad não tem (pedido antigo); Revit exige in‑place | ✗ | Inclinação por seta ou por cota em dois pontos; o IFC permite | B ★ |
| Ângulo de borda por aresta | Archicad | ✗ | Para pingadeira/beiral de laje | C |
| Pilar/viga por segmentos, cônico, perfil metálico | Archicad (segmentos), estrutura §4 (`IfcMaterialProfileSet`) | ◐ retangular/circular | Perfil I/U/tubo do catálogo com `IfcMaterialProfileSet` (ajuda o engenheiro) | C |
| Cardinal point do pilar | pendência 0 do CONTEXTO | ◐ | Decisão do revisor | — |

### 3.6 Esquadrias, vãos e aberturas

| Função | Pesquisa | Hoje | Ajuste proposto | Prior. |
|---|---|---|---|---|
| Porta/janela com tipos, caixilhos, peitoril, etiqueta | — | ✅ | — | — |
| Código curto nas portas da biblioteca | — | ◐ (pendência) | "P1", "P2"… como nas janelas | **A** |
| Inserir esquadria no corte e na fachada | Archicad 29 | ✗ | Clique no corte com a ferramenta Porta/Janela | C |
| Abertura única que corta parede, laje, viga e cobertura (shaft, passagem) | Archicad Opening; estrutura §3 (coordenação: furos e passagens) | ◐ vão na parede e abertura na laje separados; **nicho e vão livre sem ferramenta** (pendência) | Ferramenta de abertura genérica; "criar abertura pela seleção" | B |
| Numeração das portas pelo ambiente | Revit 2027 (numeração por regra) | ✗ | Ver 3.11 | B |

### 3.7 Cobertura, escada, guarda‑corpo, terreno

| Função | Pesquisa | Hoje | Ajuste proposto | Prior. |
|---|---|---|---|---|
| Cobertura 1/2/4 águas, plana | — | ✅ (`SHAPES`) | — | — |
| Cobertura por contorno com inclinação por lado; beiral por lado; L/T | Revit (aresta define inclinação), Archicad (beiral único é queixa) | ✗ (pendência V1) | Inclinação e beiral **por aresta** do contorno | B ★ |
| Aberturas na cobertura (chaminé, poço) | Archicad 28 | ◐ claraboia | Abertura genérica (3.6) cortando a cobertura | C |
| Ajustar paredes ao telhado | RF‑ELE‑17 | ✗ | Topo da parede preso à água | B |
| Escada com regras de um perfil e soluções alternativas | archicad mod. §2 ("Solver"); Revit (refazer ao mudar regra) | ◐ constantes no código (`MAX_RISER`, `BLONDEL`) | Regras num perfil editável (norma ou código de obras) e lista de soluções quando a regra não fecha | B ★ |
| Degrau em leque | Archicad (leque problemático) | ✗ | Leque com pisos iguais na linha de piso | B |
| Numeração de degraus, linha de piso, marca de quebra na planta | Archicad, Revit 2027 | ◐ linha de piso (`walking_line`) e trecho acima do corte oculto; numeração não confirmada | Garantir os três na planta da escada | B |
| Guarda‑corpo de vidro com painel variável | queixa nos dois | ✗ | Painéis que se dividem pelo comprimento | B ★ |
| Guarda‑corpo associativo à borda de laje e parede | Archicad | ◐ só escada/patamar | Ao longo de borda de laje | C |
| Terreno por contorno e curvas pegas do DWG | terreno §1 | ✅ | Pegar **todas** as curvas de uma camada; ler cota de texto próximo | **A** |
| Curvas como arestas obrigatórias (linhas de quebra) | terreno §1 (erro de volume do Archicad), §3 | ✗ (Delaunay sem restrição) | Triangulação com restrições | B ★ |
| Furos no terreno | Civil 3D, Archicad | ✗ | Contornos internos | B |
| Terreno natural × projetado, platô com talude, muro de arrimo, corte/aterro | terreno §2, §5 (Archicad precisa de add‑on) | ✗ | Platô com talude de inclinação dada; volume entre as duas superfícies | B ★ |
| Recorte do terreno pela edificação | Revit Escavar | ✗ | Laje do térreo/subsolo escava o terreno | B |
| Terreno cortado na planta | Archicad não corta (queixa) | ◐ só contorno | Curvas e corte na planta com rótulos de cota | B |
| Pontos XYZ/CSV e LandXML | terreno §4 | ✗ | Leitura de XYZ é barata | B |

### 3.8 Ambientes e áreas

| Função | Pesquisa | Hoje | Ajuste proposto | Prior. |
|---|---|---|---|---|
| Ambiente por clique ou polígono, etiqueta | — | ✅ | — | — |
| Refazer quando as paredes do contorno mudam | Archicad não refaz (queixa) | ✗ só com a IA | Guardar o ponto‑semente e refazer na derivação quando paredes vizinhas mudam | **A ★** |
| Várias áreas (até a face, até o eixo, com descontos, computável) | Archicad (4 áreas) | ✗ `GrossFloorArea` = `NetFloorArea` | Área útil (face) e construída (eixo/externa) corretas; computável pelo perfil municipal | **A** |
| Perímetro com laços internos (pilar solto) | Revit 2025 | conferir | Teste | B |
| Zonas (unidade, apartamento) | Revit, NBR 12721 | ✗ | `IfcZone` | B |
| Pé‑direito mínimo e área mínima por uso | conferência por regras (emergentes §2) | ✗ | Aviso por regra (3.13) | B |

### 3.9 Documentação: planta, cortes, anotações

| Função | Pesquisa | Hoje | Ajuste proposto | Prior. |
|---|---|---|---|---|
| Plano de corte por pavimento, cortado/vista/acima | Revit (faixa de vista confunde) | ✅ | Mostrar o plano de corte num esquema ao editar | C |
| Cotas associativas, nível, raio, ângulo, cota automática | — | ✅ | Prender cota também em parede em arco, pilar, laje, eixo (pendência) | B |
| Cotas e textos dentro do corte | — | ✗ (pendência) | Cotas de nível e altura no corte | B |
| Etiquetas: ponto da chamada editável, encaixe em aresta, etiquetar todos, etiquetar por exemplo | Revit 2027 | ◐ etiquetas fixas | "Etiquetar todos desta categoria" e alças da chamada | B |
| Numeração por regra (portas pelo ambiente, ambientes por pavimento) | Revit 2027 | ✗ | Regra por categoria aplicada sozinha a elementos novos | B |
| Regras gráficas por critério salvas na vista | Archicad (sobrescritas ordenadas); AutoCAD (sobrepor cor por viewport) | ✗ só camadas | Lista ordenada critério → pena/cor/hachura por vista salva; base das cores de intervenção | **A** (item 2) |
| Status de intervenção também em marcadores e anotações | Archicad 29 corrigiu tarde | ✗ | Desde o início (item 2) | **A ★** |
| Tipos de linha | Revit (tipos complexos, pedido votado) | ◐ contínua, tracejada, traço‑ponto | Editor simples de padrão (traço, espaço, ponto) na tabela de penas | C |
| Rotação de padrão de hachura | Revit 2027.1 | conferir | Ângulo da hachura | C |
| Verificação ortográfica | Revit 2026 (pedido votado) | ✗ | Dicionário pt‑BR no texto | C |
| Notas‑chave hierárquicas exportáveis | Archicad 28 | ✗ | Ligadas ao memorial e ao SINAPI (depois) | C |

### 3.10 Pranchas, folhas mestras e PDF

| Função | Pesquisa | Hoje | Ajuste proposto | Prior. |
|---|---|---|---|---|
| Prancha com vistas vivas, folha mestra com campos, PDF vetorial, penas | archicad doc. §1 | ✅ 15, 25, 26, 27 | — | — |
| Seleção, limite tracejado, recorte e moldura | Archicad, Revit, AutoCAD | ✅ 29 | — | — |
| Título da vista (nome, escala, linha) | Revit 2026–27 | ✗ | Título automático por vista, com estilo na folha mestra | **A** |
| Grade da folha e alinhamento entre folhas; repetir a posição em outras folhas | Revit (pedido votado) | ✗ (pendência do revisor) | Encaixe numa grade e "mesma posição" em outras pranchas | **A** |
| Revisões por prancha com lista no carimbo; nuvens ligadas à revisão | Archicad (changes com gambiarras) | ◐ nuvem sem vínculo | Revisão por prancha, simples e explícita | B |
| Lista de pranchas, conjuntos de publicação | Archicad Publisher Sets | ✗ | Conjunto salvo de pranchas para exportar de novo | B |
| Tabela na prancha | Revit, Archicad | ✗ | Tabela como vista viva na prancha | B |
| Export DXF/DWG | autocad §7 (prefeituras, engenheiros) | ✗ | DXF com camadas e penas (ezdxf já está no projeto) | **A** |
| Limite de tamanho do PDF e espaço do carimbo digital | normas §3 (Curitiba 3 MB) | ✗ | Do perfil municipal (item 2) | **A** (item 2) |
| DWF (São Paulo) | conferido 2026‑10‑26: ainda pedido por e‑mail | ✗ | Esperar o Licencia Sampa; C | C |

### 3.11 Tabelas e quantitativos

| Função | Pesquisa | Hoje | Ajuste proposto | Prior. |
|---|---|---|---|---|
| Tabelas por categoria, filtros, totais, CSV/XLSX, quadro de esquadrias | — | ✅ | — | — |
| Tabela editável como planilha (bidirecional) | Revit (pedido votado), Archicad Interactive Schedule | ✗ células só leitura (`table_view.py`: `NoEditTriggers`) | Editar a propriedade na célula muda o elemento | B ★ |
| Fórmulas e filtro por propriedade | Revit, Archicad (propriedade por expressão) | ✗ (pendência V1) | Coluna calculada com o analisador de fórmulas existente | B |
| Regras de medição por serviço (desconto de vãos com limiar, faixa do forro) | quantitativos §1 | ✗ | Item 5 do roteiro | B ★ |
| Revestimento por ambiente (chapisco, reboco, pintura, cerâmica) | quantitativos §1 | ✗ | Faces de parede por ambiente com desconto de vãos | B ★ |
| NBR 15965 e código SINAPI (`IfcClassificationReference`) | quantitativos §2, mercado §4 | ✗ | Classificação no tipo; coluna nas tabelas | B |
| `Qto_*` dos objetos | pendência pacote 13 | ✗ | Gravar | B |

### 3.12 Camadas, objetos e biblioteca

| Função | Pesquisa | Hoje | Ajuste proposto | Prior. |
|---|---|---|---|---|
| Camadas com grupos, combinações, isolar, bloquear | — | ✅ 18 | — | — |
| Objetos paramétricos com fórmulas, dentro do arquivo | bibliotecas §1 | ✅ 13 | — | — |
| Tipo base + variantes geradas de uma tabela (catálogo) | Revit type catalog, lookup CSV | ✗ | Tabela de tipos importável de CSV | C |
| Vários conjuntos de variantes independentes | AutoCAD (um só parâmetro de visibilidade é queixa) | conferir | Garantir na definição | C |
| Arrastar da biblioteca para a planta | — | ✗ (pendência) | Arrastar e soltar | **A** |
| Símbolo 2D ABNT separado do 3D; limite de polígonos; licença por objeto; IDS na publicação | bibliotecas §6 | ◐ símbolo automático | Licença e validação ao publicar na biblioteca | C |
| Converter bloco DWG 2D repetido em tipo IFC | AutoCAD Smart Blocks; fabricantes distribuem DWG 2D | ✗ | Ponte 2D → BIM (roteiro item 19) | C ★ |
| Objetos genéricos brasileiros (bloco cerâmico, drywall, steel frame, esquadrias de mercado) | mercado §4 | ◐ | Ampliar a biblioteca padrão | B |

### 3.13 Interoperabilidade, validação e coordenação

| Função | Pesquisa | Hoje | Ajuste proposto | Prior. |
|---|---|---|---|---|
| IFC 4.3 nativo, validado por teste | interop §1 | ✅ | — | — |
| Validação IDS embutida e IDS dos cadernos brasileiros | interop §2–3, emergentes §2 | ✗ | `ifctester` (não instalado; existe no PyPI na 0.9.0, mesma versão do IfcOpenShell do projeto — conferir a licença antes de pôr nas dependências) + painel de conformidade | **A ★** |
| Conferência do modelo/prancha por regras com severidade | emergentes §2 (Autodesk anuncia) | ✗ | Regras declarativas: ambiente sem etiqueta, cota faltando, pé‑direito, vão acessível | B ★ |
| Export IFC4 RV / IFC2x3 de compatibilidade testado contra Revit, Archicad, Eberick, QiBuilder | interop §1, estrutura §3 | ✗ | Usar como testes os casos que o exportador do Revit corrige (Pset_Address, EPSG, quantidades base, vazios) | B |
| IFC de referência (somente leitura), inclusive IFC2x3 | estrutura §3, interop §5 | ✗ | Como o desenho importado (spec 22) | B |
| BCF 3.0 | archicad doc. §3 | ✗ | Ler/gravar com o pacote do ecossistema IfcOpenShell | B |
| Localização (SIRGAS 2000, EPSG, `IfcMapConversion`) | terreno §4 | ✗ | Um só "ponto de referência do terreno"; DWG em UTM deslocado sozinho | B ★ |
| Perfis de exportação (subconjunto de Psets para um órgão) | archicad doc. §4 | ✗ | Depois do IDS | C |
| glTF com materiais | visualização §2 | ✗ | Item 7 do roteiro | C |

### 3.14 Assistente, histórico e colaboração

| Função | Pesquisa | Hoje | Ajuste proposto | Prior. |
|---|---|---|---|---|
| Assistente por MCP com desfazer agrupado | revit doc. §5 (assistente da Autodesk "disse que fez e não fez") | ✅ protótipo (pacote 9) | **Plano antes** de agir e **lista do que mudou** depois | B |
| Assistente que responde dúvidas com a documentação pt‑BR | Archicad AI Assistant (RAG da ajuda) | ✗ | Usar specs e ajuda como base | C |
| Histórico com autoria, opções ramificadas, "o que mudou desde que abri" | AutoCAD Activity Insights, emergentes §2 | ◐ diário de sessão sem interface | Painel de histórico sobre o diário | C |
| Opções de projeto | Archicad 27+, Revit | ✗ | Depois do histórico | C |
| Colaboração por reserva (autorreserva ao editar, "pedir posse") | Archicad Teamwork, AutoCAD 2027 Checkout | ◐ operações serializáveis | Manter a decisão; sincronizar por operação | C |
| Console/scripts Python que gravam operações | AutoLISP, pyRevit | ✗ | Console com a API do núcleo | C |

### 3.15 Aprendizado, robustez e aparência

| Função | Pesquisa | Hoje | Ajuste proposto | Prior. |
|---|---|---|---|---|
| Onboarding / tutorial curto | Archicad 28–29 investiram; capacitação é a barreira 1 no Brasil (48%) | ✗ | Tutorial "primeira casa" guiado na própria janela | B ★ |
| Atalhos configuráveis | RF‑UI‑08 | ◐ apelidos da linha de comando editáveis | Editor de atalhos de teclado | C |
| E/S fora da linha da interface | interface §5 | ✗ salvamento automático na linha da UI | Medir; mover para thread se travar | B |
| Quadros modais grandes | interface §4 (Archicad gastou uma versão nisso) | ◐ tipos, materiais e penas são quadros modais | Preferir painéis não modais ao reformar esses quadros | C |
| Tema escuro | mercado §2 (desejo barato) | ✗ — **decisão do revisor: tema sempre claro** | Manter a decisão | — |

---

## 4. Projeto legal (item 2 do roteiro) — o que o pente fino acrescenta

Leitura prévia feita nesta sessão (ver CONTEXTO "Onde paramos"). O pente fino confirma o
escopo e acrescenta três dependências que convém resolver **dentro** do pacote:

1. **Ambiente que se refaz** e **áreas corretas** (3.8): sem isso o quadro de áreas sai
   errado depois de qualquer mudança de parede.
2. **Regras gráficas por critério** (3.9): é o mecanismo das cores de intervenção do
   perfil municipal, e serve depois para cor por propriedade no 3D.
3. **Título da vista e grade na prancha** (3.10): a prancha da prefeitura é a vitrine.

Valores de `Status` confirmados no esquema IFC 4.3 do IfcOpenShell: DEMOLISH, EXISTING,
NEW, TEMPORARY, OTHER, NOTKNOWN, UNSET (não existe em `Pset_SpaceCommon` nem em
anotações → Pset próprio para "a regularizar", "a transformar" e para ambientes e
anotações). Portas e janelas já gravam `Status = NEW` por padrão.

## 5. Proposta de ordem

**Ajustes curtos, a qualquer momento (A):** código curto das portas; duplo clique
maximiza a vista; vistas 3D padrão; arrastar objeto da biblioteca; pegar todas as curvas
de uma camada; ferramenta Medir; aritmética no quadro de medidas; cópia em série;
corrigir o texto das specs 01/03/07.

**Pacote "projeto legal" (item 2), com as três dependências da seção 4**, mais export
DXF e validação IDS (que conferem a entrega).

**Depois, na ordem do roteiro**, com os acréscimos deste pente fino: guias e pontos de
divisão, cota viva, esticar por janela, alças multifuncionais, favoritos (precisão 2);
coordenação openBIM (IFC de referência, BCF, export de compatibilidade, localização
SIRGAS); documentação por regras (etiquetar todos, numeração por regra, cotas no corte,
revisões por prancha, tabela na prancha e editável); quantitativos por serviço e
revestimento por ambiente; refino dos elementos (escada com perfil de regras e leque,
guarda‑corpo de vidro, cobertura por aresta, laje inclinada e ligada às paredes, terreno
com linhas de quebra, platô e escavação); benchmark de desempenho; tutorial.

## 6. A conferir antes de especificar

- Licença do `ifctester` (pacote à parte do IfcOpenShell, 0.9.0 no PyPI) antes de
  acrescentá‑lo às dependências e ao `THIRD_PARTY_NOTICES.md`.
- Numeração de degraus e marca de quebra na planta da escada.
- Perímetro do ambiente com pilar solto dentro.
- Rotação de hachura e vários conjuntos de variantes nos objetos.
- As queixas de fórum citadas (escada, nós de parede, laje plana, zonas) vieram de
  trecho de busca: conferir a página antes de citar em spec.
- Recursos clássicos do AutoCAD (matriz, esticar, escala, alinhar) entraram na pesquisa
  sem fonte: a spec precisa citar a ajuda pública ou ficar como conhecimento geral.
