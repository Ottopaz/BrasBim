# Comparação: o que o BrasBim já faz × o que a pesquisa levantou

*2026‑10‑23. Base: `reports/Pesquisa Archicad Revit AutoCAD.md` e as 15 notas em
`research_notes/Pesquisa Archicad Revit AutoCAD/` (fontes públicas acessadas em
2026‑10‑21), cruzadas com o `CONTEXTO.md`, `spec/REQUISITOS.md` e o código atual.*

> **Clean-room.** Nada de `_restrito/` nem de `tools/` foi lido. Os nomes de recursos dos
> concorrentes aparecem só para identificar a função; não são para usar na interface.
> Achados que na pesquisa vieram só de trecho de busca continuam valendo como "conferir"
> antes de virar spec (seção 5).

## 1. Resumo

O BrasBim já cobre o esqueleto de um BIM de arquitetura: paredes com camadas e junções,
esquadrias, estrutura básica, cobertura, escada, terreno, ambientes, cotas, cortes,
pranchas, tabelas, camadas, objetos paramétricos, salvamento automático e assistente. Em
alguns pontos ele já está **à frente** do que os usuários reclamam nos três (seção 2). As
maiores distâncias não estão nos elementos, e sim em três frentes:

1. **Desenho de precisão e edição 2D.** O snap só atrai pontas, meio e eixo das paredes,
   vértices conhecidos e a grade. Faltam interseção, perpendicular, centro e tangente
   (o próprio `REQUISITOS.md` põe isso no MVP, RF‑DES‑02), e faltam as edições que quem
   vem do CAD usa toda hora: deslocar paralela, aparar/estender, concordar, matriz.
   Digitar a medida exige Tab.
2. **Saída para os outros.** Não há export DXF, export IFC de compatibilidade, BCF, IDS,
   IFC de referência nem georreferência. O arquivo é IFC 4.3, mas ainda não "conversa"
   com Revit, Archicad, Eberick e QiBuilder de forma testada.
3. **Projeto legal.** Status de intervenção, perfil municipal, quadro de áreas com
   CA/TO/permeabilidade e memorial ainda não existem (é o item 1 do roteiro).

Recomendação: manter o pacote "projeto legal" como próximo, mas **antecipar um pacote
curto de precisão** (snaps que faltam + edições 2D básicas + número digitado sem Tab),
porque ele pesa em todas as outras ferramentas e é o que decide a migração de quem vem do
AutoCAD (seção 4).

## 2. Onde o BrasBim já está à frente (manter e divulgar)

| O que temos | Queixa ou limite dos três que isso responde |
|---|---|
| Salvamento automático com recuperação (spec/ui 21) | O Revit não tem de verdade; usuários relatam horas perdidas e pedem "autosave local" há anos |
| IFC 4.3 como o próprio arquivo, validado por teste a cada recurso | Archicad e Revit traduzem para IFC na exportação, e é aí que perdem dados; o Revit ainda corrigia quantidades e vazios em 2026 |
| Topo da parede inclinado, em empena ou livre, e parede tombada (spec/ui 08) | Parede de topo inclinado está na lista de desejos antiga do Archicad |
| Prioridade de camada nas junções feita no modelo (planta, 3D e corte coerentes) | É o ponto forte do Archicad; o Revit só separou prioridade de função em 2026 |
| Anotação medida em mm de papel e escalada pela vista (pacote 6) | No AutoCAD a escala de anotação é gerida objeto por objeto e confunde |
| Pilar e viga com b × h digitados, gerando o tipo sozinho (pacote 4) | Evita o "um tipo por tamanho" das famílias |
| Escada que acompanha a altura do pavimento e avisa espelho, piso e Blondel (pacote 17) | No Revit é preciso apagar e refazer a escada quando a regra muda |
| Tipos e objetos viajam dentro do arquivo IFC (pacote 13) | "Parte faltando" e objeto que não abre em versão anterior no Archicad |
| Barra Opções que muda o conteúdo, não a posição; mini‑barra junto à seleção | Faixa de opções do Revit criticada desde 2010 por esconder e mover ferramentas |
| Assistente que agrupa o pedido num só passo de desfazer (pacote 9) | O assistente do Revit 2027 "disse que fez e não fez" na maioria das tarefas testadas |
| Custo zero e licença livre | Preço e licença são a queixa número um contra os três |

## 3. Comparação por área

Legenda da coluna "Situação": ✅ temos · ◐ temos em parte · ✗ não temos.
Prioridade: **A** = fazer logo (valor alto, esforço baixo ou médio); **B** = próximo ciclo;
**C** = depois.

### 3.1 Entrada de geometria e precisão

| Função (o que os concorrentes oferecem) | BrasBim hoje | Situação | Melhoria proposta | Prior. |
|---|---|---|---|---|
| Atração a pontos: ponta, meio, interseção, perpendicular, centro, tangente, ponto mais próximo em qualquer elemento (AutoCAD, Archicad) | `core/snap.py`: pontas, meio e eixo das paredes, vértices extras, grade | ◐ | Snap genérico por "arestas e pontos" de todos os elementos visíveis (lajes, pilares, linhas 2D, desenho importado, eixos), com interseção, perpendicular, centro e tangente. Fecha o RF‑DES‑02 (MVP) | **A** |
| Marcador visual do tipo de snap (forma ou cor diferente por tipo) | nome do tipo junto ao cursor (`snap.KIND_LABEL`) | ◐ | Um símbolo por tipo de atração, além do nome | B |
| Rastreamento: linhas de alinhamento a partir de pontos adquiridos por pausa (AutoCAD, Archicad) | `acquire` por pausa de 0,4 s, linhas 0/90° e cruzamento com o ponto anterior | ◐ | Alinhamento também a 45° e ângulos configuráveis; vários pontos adquiridos ao mesmo tempo; paralela/perpendicular a uma aresta | B |
| Digitar o número a qualquer momento, sem clicar em campo, aplicado na direção inferida (SketchUp, AutoCAD) | o primeiro algarismo já abre o quadro de medidas no campo principal, sem Tab (`ToolInput.tool_key`; corrigido em 2026‑10‑23, a versão anterior desta tabela dizia "por Tab") | ✅ | — (spec/ui 23 §1) | — |
| Travar o eixo por tecla (setas, Shift) | Shift prende em passos de 45° (`snap.constrain`); Alt desliga a atração | ◐ | Setas travam X/Y; Shift segura a direção atual, inclusive a de uma aresta | **A** |
| Aritmética no campo ("2*", "+0,15") e coordenadas relativas/absolutas (Archicad, SketchUp) | não | ✗ | Aceitar expressões simples no quadro de medidas (o analisador de fórmulas dos objetos já existe) | B |
| Linhas‑guia persistentes e pontos de divisão (metade, n partes) | não | ✗ | Guias arrastadas da borda da vista; snap em divisões da aresta | B |
| Cota viva editável no elemento recém‑criado ou selecionado (Revit) | cotas permanentes associativas; não há cota temporária | ✗ | Ao criar ou selecionar, mostrar distâncias às vizinhas; clicar no número e digitar move o elemento | B |
| Traçar elemento novo pelo contorno de outros (laje, ambiente, cobertura por clique numa região) | laje e ambiente pelo cômodo, cobertura pelas paredes | ✅ | Diferencial possível: opção de **manter ligado** ao contorno de origem (o Archicad não liga) — ver 3.4 | B |
| Assentar na superfície (elemento novo pega a cota da laje, cobertura ou terreno embaixo) | não | ✗ | Objetos, pilares e vegetação assentam no terreno ou laje; opção de reassentar depois (o Archicad só faz na criação) | C |
| Girar 90° com uma tecla | girar pede ângulo | ✗ | Atalho de giro rápido da seleção | **A** |

### 3.2 Seleção, edição e organização

| Função | BrasBim hoje | Situação | Melhoria proposta | Prior. |
|---|---|---|---|---|
| Seleção por janela e por cruzamento | sim (`in_rect`, direção do arraste) | ✅ | — | — |
| Selecionar semelhantes por critério (mesmo tipo, classe, material, pavimento) | "Selecionar todos deste tipo" só para objetos | ◐ | Mesmo comando para paredes, esquadrias, estrutura; menu com critérios IFC (classe, tipo, PredefinedType, material, pavimento, camada). RF‑NUC‑09 | **A** |
| Deslocar paralela (offset) | não | ✗ | Para paredes, linhas, contornos de laje e ambiente | **A** |
| Aparar / estender até outro elemento; concordar com raio (0 = canto vivo) | não; paredes têm "unir" e junções | ◐ | Para linhas 2D e paredes (estender até a face de outra parede é pedido comum) | **A** |
| Matriz linear e polar, opcionalmente associativa | não (RF‑NUC‑06, V1) | ✗ | Copiar em série com número e distância no quadro de medidas | B |
| Esticar por janela, escala por referência, alinhar | alças por elemento | ◐ | Esticar vários elementos por janela de cruzamento | C |
| Pegar e aplicar configurações de um elemento (conjuntos salvos de configurações por ferramenta) | não | ✗ | "Pegar" o estado de um elemento para a ferramenta e "aplicar" a outros; conjuntos salvos por ferramenta | B |
| Menu sob o cursor com a última ação e 3–5 propriedades editáveis | mini‑barra junto à seleção | ◐ | Acrescentar à mini‑barra campos rápidos (altura, espessura, cota) | C |
| Edição de nós e arestas de contorno (deslocar aresta, curvar, somar/subtrair polígono) | alças de vértice na laje e ambiente | ◐ | Deslocar aresta inteira; somar/subtrair um polígono ao contorno | B |
| Paleta de comandos com busca aproximada em pt‑BR e sinônimos IFC | não | ✗ | Ctrl+K com busca em todas as ações dos menus e ferramentas | **A** |
| Repetir a última ferramenta (Enter ou espaço) | não encontrado | ✗ | Enter no vazio reativa a última ferramenta | **A** |
| Agrupar elementos | não (RF‑NUC‑07) | ✗ | `IfcGroup` simples | C |

### 3.3 Navegação e vistas 3D

| Função | BrasBim hoje | Situação | Melhoria proposta | Prior. |
|---|---|---|---|---|
| Planta, 3D e lado a lado; órbita, deslocamento, zoom | sim | ✅ | — | — |
| Vistas 3D padrão (topo, frente, isométricas) e câmera salva | não (pendência do MVP) | ✗ | Já no roteiro (item 7); é barato | **A** |
| Caixa de corte 3D com tampa preenchida; corte pela seleção sem sobrescrever a vista do usuário | não (RF‑UI‑05) | ✗ | Caixa de corte com tampa; "isolar seleção" cria vista temporária | B |
| Estilos de exibição (sombreado, arestas, raio‑X, cor por propriedade) | sombreado com cores de material | ◐ | Arestas e cor por propriedade (útil para status de intervenção) | B |
| Desempenho com modelo grande (instancing, cache por tipo, carregamento por pavimento) | não medido; várias pendências "medir em projeto grande" | ◐ | Benchmark aberto com um projeto de referência e metas de FPS e tempo de edição | B |

### 3.4 Elementos

| Elemento / função | BrasBim hoje | Situação | Melhoria proposta | Prior. |
|---|---|---|---|---|
| **Parede** reta, curva, camadas, linha de referência, junções L/T/X, topo inclinado, tombada | sim | ✅ | — | — |
| Parede trapezoidal (espessura diferente em cada ponta) e poligonal | não | ✗ | Tratar como opções independentes, sem as restrições cruzadas que o Archicad tem | C |
| Nó com 3 ou mais paredes compostas previsível | prioridade por camada; sem teste específico de 3+ | ◐ | Teste de nó com 3 e 4 paredes de tipos diferentes; regra visível e editável no nó (queixa clássica do Archicad) | B |
| Revestimento como camada que soma na espessura vista pelas aberturas | camadas no tipo; caixilho usa a espessura total | ✅ | Garantir por teste (o Revit 2027 falha nisso) | — |
| Ajustar parede ao telhado ou à laje (RF‑ELE‑17) | não (pendência da cobertura) | ✗ | Topo da parede preso à água da cobertura | B |
| **Laje** poligonal, camadas, aberturas, pelo cômodo | sim | ✅ | — | — |
| Laje inclinada ou de espessura variável | não | ✗ | O Archicad não tem (usuários pedem); o IFC permite. Bom diferencial | B |
| Laje ligada às paredes do cômodo (acompanha quando a parede muda) | não (pendência) | ✗ | Opção "manter ligada ao contorno" | B |
| **Pilar/viga** retangular, circular, recortes por prioridade | sim | ✅ | Seção cônica e perfil metálico | C |
| **Porta/janela** com tipos, caixilhos, peitoril, etiqueta | sim | ✅ | Inserir esquadria também no corte e na fachada (o Archicad 29 acabou de fazer) | C |
| Abertura que atravessa vários elementos (shaft, passagem de tubulação) e "criar abertura pela seleção" | vão na parede e abertura na laje, separados | ◐ | Abertura única que corta parede, laje, viga e cobertura; base para furos e passagens da coordenação | B |
| **Cobertura** 1, 2 e 4 águas sobre retângulo ou paredes | sim | ◐ | Telhado em L/T, beiral e inclinação por lado (o Archicad assume beiral único) | B |
| **Escada** reta, L, U; avisos de espelho, piso, Blondel | sim | ◐ | Degraus em leque; regras vindas de um perfil (norma ou código de obras) em vez de constantes; propor alternativas quando a regra não fecha | B |
| **Guarda‑corpo** ao longo da escada e do patamar | sim | ◐ | Guarda‑corpo de vidro com painel de largura variável (queixa nos dois) | B |
| **Terreno** por contorno e curvas pegas do desenho | sim | ◐ | Ver 3.6 | — |
| **Fachada‑cortina** | não (RF‑ELE‑11; pacote 20 na fila) | ✗ | Começar já sobre caminho curvo (o Archicad só aceita plano ou esfera) | C |
| Rampa (RF‑ELE‑09), revestimentos por ambiente (`IfcCovering`, RF‑ELE‑12), fundação (RF‑ELE‑13) | não | ✗ | Rampa com limite de inclinação da NBR 9050 (conferir); revestimento ligado a quantitativos (3.8) | B/C |
| Forma livre e operações sólidas associativas | não (V2) | ✗ | Manter no V2 | C |

### 3.5 Ambientes e áreas

| Função | BrasBim hoje | Situação | Melhoria proposta | Prior. |
|---|---|---|---|---|
| Ambiente por clique no cômodo ou por polígono, com etiqueta | sim | ✅ | — | — |
| Atualizar sozinho quando as paredes mudam | só quando a IA move a parede | ◐ | Ambiente pelo cômodo se refaz quando as paredes de contorno mudam. O Archicad exige atualização manual: diferencial barato | **A** |
| Várias definições de área (até o eixo, até a face, com descontos de pilares) | área útil e área construída | ◐ | Critérios por perfil municipal (computável, não computável, sacadas até X m²) | **A** (projeto legal) |
| Zonas e agrupamentos (unidade, apartamento) | não (RF‑AMB‑05) | ✗ | `IfcZone`, necessário para os quadros da NBR 12721 | B |

### 3.6 Terreno

| Função | BrasBim hoje | Situação | Melhoria proposta | Prior. |
|---|---|---|---|---|
| Superfície por pontos e curvas; curvas pegas do DWG uma a uma, com a cota do DWG | sim (TR01–TR08) | ✅ | Pegar todas as curvas de uma camada de uma vez (pendente) | **A** |
| Curvas e linhas de quebra como arestas obrigatórias da triangulação | não (hoje ponto no meio do patamar) | ✗ | Delaunay com restrições; evita o erro de volume que usuários do Archicad relatam | B |
| Furos e contorno que exclui triângulos | contorno sim; furos não | ◐ | Furos | B |
| Terreno natural × projetado, corte e aterro, platô com talude, muro de arrimo | não | ✗ | Item 6 do roteiro | B |
| Curvas rotuladas na planta | não | ✗ | Rótulo por linha de rótulo ou intervalo | B |
| CSV/XYZ e LandXML | não | ✗ | Leitura de pontos XYZ é barata | B |
| Georreferência SIRGAS 2000 e deslocamento automático de DWG em UTM | não (RF‑PRJ‑05) | ✗ | Um só "ponto de referência do terreno" gravado em `IfcMapConversion` | B |
| Varredura de pontas soltas e vãos no desenho importado | não | ✗ | Antes de pegar curvas e contornos | C |

### 3.7 Documentação

| Função | BrasBim hoje | Situação | Melhoria proposta | Prior. |
|---|---|---|---|---|
| Planta com cortado, em vista e acima do plano; detalhe simplificado ou por camadas | sim | ✅ | Mostrar visualmente o plano de corte e a profundidade ao editar (o conceito confunde no Revit) | C |
| Cotas associativas, cota automática de paredes, nível, raio, ângulo | sim | ✅ | Cota presa também em parede curva e em pilares, lajes e eixos | B |
| Etiquetas por propriedade, numeração por regra, etiquetagem em lote | etiquetas fixas por categoria e rótulo | ◐ | Numeração por regra (pavimento, ambiente, tipo) aplicada sozinha a elementos novos; etiquetar todos os de uma categoria | B |
| Regras gráficas por critério (cor e hachura por propriedade, salvas por vista) | camadas e combinações por vista | ◐ | Base para as cores de intervenção do perfil municipal | **A** (projeto legal) |
| Cortes e fachadas gerados do modelo | sim | ✅ | Cotas e textos dentro do corte (pendência) | B |
| Pranchas com várias vistas, carimbo, PDF vetorial | sim | ◐ | Pôr vista na prancha com grade e alinhamento entre folhas (pedido mais votado do Revit; pendência do revisor) | **A** |
| Revisões ligadas à prancha, com nuvens | marcador de alteração (nuvem) | ◐ | Revisão por prancha, com a lista no carimbo | B |
| Tabela na prancha; tabela editável como planilha | não (RF‑QTD‑04, 06) | ✗ | Pedidos mais votados do Revit | B |
| Exportar DXF | não (RF‑DOC‑11) | ✗ | Muitas prefeituras e escritórios pedem DWG/DXF junto do PDF | **A** |
| Exportar DWF (São Paulo) | não | ✗ | Conferir se a exigência continua | C |
| Perspectiva e vista 3D na prancha | não (RF‑DOC‑14) | ✗ | Depende da câmera salva | B |

### 3.8 Tabelas e quantitativos

| Função | BrasBim hoje | Situação | Melhoria proposta | Prior. |
|---|---|---|---|---|
| Tabelas por categoria com filtros, agrupamento, totais, CSV/XLSX | sim | ✅ | — | — |
| Quadro de esquadrias | modelo de tabela "esquadrias" | ✅ | Código curto também nas portas da biblioteca (pendência) | **A** |
| Área de parede com desconto de vãos por regra de serviço (limiar), revestimento por ambiente | `Qto_*BaseQuantities` padrão | ◐ | Critério por serviço com limiar, memória de cálculo por elemento (item 5 do roteiro) | B |
| Classificação NBR 15965 e código SINAPI | não (RF‑TIP‑09, RF‑QTD‑07) | ✗ | `IfcClassificationReference` | B |

### 3.9 Interoperabilidade e coordenação

| Função | BrasBim hoje | Situação | Melhoria proposta | Prior. |
|---|---|---|---|---|
| IFC 4.3 nativo; abrir IFC de outra origem | sim | ✅ | — | — |
| Export IFC4 / IFC2x3 de compatibilidade testado contra Revit, Archicad, Eberick, QiBuilder | não (RF‑INT‑01) | ✗ | Item 3 do roteiro; usar como testes os casos que o exportador do Revit corrige | B |
| IFC de outra disciplina como referência somente leitura | não (RF‑INT‑03) | ✗ | Análogo ao desenho importado (spec/ui 22) | B |
| BCF 3.0 | não (RF‑INT‑04) | ✗ | — | B |
| Validação IDS embutida, IDS dos cadernos brasileiros | não (RF‑INT‑05) | ✗ | Valor alto e esforço baixo, se o validador do IfcOpenShell servir (conferir) | **A** |
| Comparar versões e destacar alterações | não (RF‑INT‑06) | ✗ | O diário de operações já é a base | C |
| glTF para render externo | não (RF‑INT‑08) | ✗ | Item 7 do roteiro | C |

### 3.10 Colaboração, histórico e IA

| Função | BrasBim hoje | Situação | Melhoria proposta | Prior. |
|---|---|---|---|---|
| Colaboração por reserva de elementos | operações serializáveis prontas; servidor não | ◐ | Mantém a decisão; sincronizar por operação, não por arquivo | C |
| Histórico com autoria, opções de projeto | diário de sessão | ◐ | Item 8 do roteiro | C |
| Assistente com plano antes de agir e diff depois | executa e agrupa no desfazer | ◐ | Mostrar o plano, aplicar e listar o que mudou (seleção já existe) | B |
| Scripts em Python sobre o núcleo | API interna existe; sem console | ◐ | Console ou execução de script que grava operações (equivalente aberto ao Lisp) | C |

### 3.11 Aprendizado e robustez

| Função | BrasBim hoje | Situação | Melhoria proposta | Prior. |
|---|---|---|---|---|
| Onboarding guiado, dicas contextuais | dica da ferramenta na barra de estado | ◐ | Tutorial curto "primeira casa"; a falta de capacitação é a barreira número 1 no Brasil | B |
| Atalhos configuráveis (RF‑UI‑08) | não | ✗ | — | C |
| E/S fora da linha da interface | gravação do salvamento automático roda na linha da interface | ◐ | Medir e mover para outra linha se travar (a pesquisa mostra travamentos do Revit por E/S síncrona) | B |

## 4. Proposta de ordem

O roteiro de 2026‑10‑21 continua certo no conteúdo. A comparação sugere duas mudanças de
ordem e alguns ajustes rápidos.

**Pacote curto de precisão, antes ou junto do projeto legal** (é o item 2 do roteiro, que
sobe):
1. Snap em todos os elementos e no desenho importado, com interseção, perpendicular,
   centro, tangente e marcador por tipo (RF‑DES‑02, que o `REQUISITOS.md` já põe no MVP).
2. Número digitado sem Tab, setas travando o eixo, Enter repetindo a última ferramenta.
3. Deslocar paralela, aparar/estender e concordar, para linhas 2D e paredes.
4. Selecionar semelhantes por critérios IFC em todas as categorias.
5. Girar 90° por atalho e paleta de comandos (Ctrl+K).

**Pacote "projeto legal"** (item 1, como estava), aproveitando:
- as regras gráficas por critério (3.7) como o mecanismo das cores de intervenção;
- o ambiente que se atualiza sozinho (3.5), sem o qual o quadro de áreas fica errado
  depois de qualquer mudança de parede;
- o refazer do fluxo de pôr vista na prancha, com grade e alinhamento;
- o export DXF, porque a prancha de aprovação muitas vezes vai também em DWG/DXF.

**Ajustes pequenos que podem entrar a qualquer momento:** vistas 3D padrão e câmera
salva; pegar todas as curvas de uma camada no terreno; código curto nas portas da
biblioteca; teste de nó com 3+ paredes compostas; validador IDS se o do IfcOpenShell
servir.

**Depois, na ordem do roteiro:** coordenação openBIM (export de compatibilidade, IFC de
referência, BCF), documentação por regras, quantitativos por serviço, refino dos elementos
(laje inclinada, cobertura em L/T e beiral por lado, escada com leque e regras por perfil,
guarda‑corpo de vidro, terreno com linhas de quebra e platô), desempenho e benchmark.

## 5. A conferir antes de especificar

- Os itens que a pesquisa marcou "trecho de busca, conferir", em especial as queixas de
  fórum (escada, nós de parede, laje sempre plana, zonas que não se atualizam no Archicad).
- Os recursos clássicos do AutoCAD citados aqui (deslocar paralela, aparar, concordar,
  matriz, repetir comando) entraram na pesquisa como conhecimento geral, sem fonte; a spec
  do pacote de precisão precisa citar a ajuda pública ou ficar como CG.
- Se o validador IDS do IfcOpenShell (`ifctester`) está disponível na versão instalada.
- Valores de `Status` nos Psets comuns do IFC 4.3 (para o status de intervenção).
- Limites da NBR 9050 e 9077 para escada e rampa (texto não lido).
