---
documento: Requisitos funcionais (levantamento a partir de fontes públicas)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-14
status: rascunho
revisor: Otávio
---

# Requisitos funcionais do BrasBim

## 0. Sobre este documento

- Lista **o que** o BrasBim deve fazer, sem dizer **como**. Cada item vira, depois,
  uma spec própria em `spec/` (modelo em `spec/elementos/_MODELO.md`).
- **Nenhum material de `_restrito/` foi usado.** Vocabulário próprio ou do IFC; não
  usamos nomes de comandos, menus ou recursos de outros softwares.

### Como foi produzido (procedência)

1. **Rascunho inicial** escrito a partir de conhecimento geral de BIM, sem consulta
   a páginas.
2. **Verificação em 2026‑10‑14:** cada área foi conferida nas fontes públicas da §15.
   - IFC 4.3: o site `ifc43-docs.standards.buildingsmart.org` bloqueia acesso
     automatizado (HTTP 403). Os textos foram lidos no **repositório oficial da
     buildingSMART** que gera essa documentação (`IFC4.x-development`, ramo
     `ifc4.3-main`).
   - As ajudas públicas da Graphisoft e da Autodesk foram consultadas só para
     confirmar que a funcionalidade existe. Nada foi copiado.
   - As normas ABNT foram confirmadas por título, edição e escopo em fontes
     secundárias (catálogos, material didático). O texto das normas não foi lido.
3. Correções feitas na verificação: título da NBR 6492:2021; norma de tipos de linha
   (NBR 16861, a confirmar); propriedade de fase da obra em IFC 4.3.

### Coluna "Fonte"

Códigos da §15. **CG** = conhecimento geral de arquitetura/BIM, sem fonte específica
verificada nesta etapa. Itens CG devem ganhar fonte quando virarem spec.

### Prioridade

| Sigla | Significado |
|---|---|
| **MVP** | Necessário para modelar uma casa térrea e entregar planta, corte, fachada, tabela e IFC |
| **V1** | Primeira versão para uso profissional em projetos reais |
| **V2** | Recursos avançados |
| **F** | Futuro / exploratório |

**Identificador:** `RF-<área>-<nº>`, para rastrear da spec ao teste.

---

## 1. Projeto e estrutura espacial

| ID | Requisito | IFC | Prior. | Fonte |
|---|---|---|---|---|
| RF-PRJ-01 | Criar, abrir e salvar projeto; o arquivo nativo é IFC 4.3 (`.ifc`) | `IfcProject` | MVP | IFC |
| RF-PRJ-02 | Unidades do projeto (padrão SI: metro, m², m³, grau) e precisão de exibição | `IfcUnitAssignment` | MVP | IFC |
| RF-PRJ-03 | Hierarquia terreno → edificação → pavimentos, editável | `IfcSite`, `IfcBuilding`, `IfcBuildingStorey`, `IfcRelAggregates` | MVP | IFC |
| RF-PRJ-04 | Pavimentos com nome, cota e altura; criar, renomear, reordenar, excluir | `IfcBuildingStorey.Elevation` | MVP | IFC |
| RF-PRJ-05 | Georreferenciamento: SIRGAS 2000 / UTM, norte verdadeiro, ponto de base | `IfcMapConversion`, `IfcProjectedCRS` | V1 | IFC |
| RF-PRJ-06 | Informações do projeto (endereço, cliente, responsável técnico, ART/RRT) | `IfcPostalAddress`, Psets | V1 | IFC, CG |
| RF-PRJ-07 | Várias edificações no mesmo terreno | `IfcBuilding` | V2 | IFC |
| RF-PRJ-08 | Situação do elemento na obra (novo, existente, a demolir, temporário) com filtros de exibição | `Pset_<Elemento>Common.Status` (`PEnum_ElementStatus`) | V1 | IFC |

## 2. Núcleo de edição

| ID | Requisito | Prior. | Fonte |
|---|---|---|---|
| RF-NUC-01 | Toda alteração é uma transação: desfazer e refazer ilimitados na sessão | MVP | CG |
| RF-NUC-02 | Cada transação é serializável (lista de operações com `GlobalId`), base para colaboração (§11) | MVP | CG, decisão do projeto |
| RF-NUC-03 | Identidade estável dos elementos (`GlobalId`) ao salvar, reabrir e exportar | MVP | IFC |
| RF-NUC-04 | Selecionar por clique, janela, cruzamento; filtros por tipo, pavimento, camada | MVP | CG |
| RF-NUC-05 | Transformações: mover, copiar, girar, espelhar, arrastar alças, edição numérica | MVP | CG |
| RF-NUC-06 | Cópia em série (linear, polar) | V1 | CG |
| RF-NUC-07 | Agrupar elementos | V1 | CG |
| RF-NUC-08 | Camadas de organização (visibilidade, bloqueio) e combinações salvas | MVP | CG |
| RF-NUC-09 | Busca e seleção por critérios (tipo, propriedade, material) | V1 | CG |
| RF-NUC-10 | Salvamento automático e recuperação após falha | MVP | CG |

## 3. Interface e navegação

| ID | Requisito | Prior. | Fonte |
|---|---|---|---|
| RF-UI-01 | Janela principal com navegador do projeto (estrutura espacial, vistas, pranchas) | MVP | CG |
| RF-UI-02 | Painel de propriedades do(s) elemento(s) selecionado(s), com edição em lote | MVP | CG |
| RF-UI-03 | Vista de planta 2D por pavimento e vista 3D, lado a lado ou em abas | MVP | CG |
| RF-UI-04 | Navegação 3D: órbita, pan, zoom, vistas padrão, perspectiva/ortogonal | MVP | CG |
| RF-UI-05 | Caixa de corte 3D e planos de corte | V1 | CG |
| RF-UI-06 | Estilos de exibição 3D: sombreado, arestas, raio‑X, por material | V1 | CG |
| RF-UI-07 | Interface em pt‑BR, preparada para tradução | MVP | decisão do projeto |
| RF-UI-08 | Atalhos de teclado configuráveis | V1 | CG |
| RF-UI-09 | Temas claro/escuro | V2 | CG |

## 4. Desenho de precisão

| ID | Requisito | Prior. | Fonte |
|---|---|---|---|
| RF-DES-01 | Grade com espaçamento configurável | MVP | CG |
| RF-DES-02 | Atração a pontos: extremidade, meio, interseção, perpendicular, centro, tangente | MVP | CG |
| RF-DES-03 | Restrições ortogonais e angulares; dicas visuais de alinhamento com pontos já existentes | MVP | CG |
| RF-DES-04 | Entrada numérica de comprimento, ângulo e coordenadas (absolutas e relativas) | MVP | CG |
| RF-DES-05 | Linhas e planos auxiliares temporários | V1 | CG |
| RF-DES-06 | Eixos de projeto nomeados (A, B, C… / 1, 2, 3…) | V1 | IFC (`IfcGrid`) |
| RF-DES-07 | Plano de trabalho 3D arbitrário | V2 | CG |
| RF-DES-08 | Criar elementos a partir de contornos fechados detectados automaticamente | V1 | CG |

## 5. Elementos construtivos

| ID | Elemento | Requisitos principais | IFC | Prior. | Fonte |
|---|---|---|---|---|---|
| RF-ELE-01 | **Parede** | Reta, curva, poligonal; altura ligada a pavimentos; camadas de material; linha de referência (face/eixo); junções L/T/X automáticas e editáveis | `IfcWall`, `IfcMaterialLayerSetUsage`, `IfcRelConnectsPathElements` | MVP | IFC |
| RF-ELE-02 | **Laje / piso** | Contorno poligonal, espessura em camadas, aberturas, inclinação | `IfcSlab` | MVP | IFC |
| RF-ELE-03 | **Pilar** | Seção retangular, circular, perfil; altura entre pavimentos | `IfcColumn`, `IfcMaterialProfileSetUsage` | MVP | IFC |
| RF-ELE-04 | **Viga** | Reta/curva, seção por perfil, apoio em pilares | `IfcBeam` | MVP | IFC |
| RF-ELE-05 | **Porta** | Hospedada em parede, abre vão automaticamente; folhas, sentido de abertura, batente | `IfcDoor`, `IfcOpeningElement`, `IfcRelVoidsElement`, `IfcRelFillsElement` | MVP | IFC |
| RF-ELE-06 | **Janela** | Idem porta; peitoril; tipos de abertura; inclui aberturas zenitais | `IfcWindow` | MVP | IFC |
| RF-ELE-07 | **Cobertura** | Plana e de uma/duas/múltiplas águas, beirais; a cobertura agrega suas partes (lajes de cobertura, peças) | `IfcRoof` + `IfcSlab` (`ROOF`) via `IfcRelAggregates` | MVP (simples) / V1 | IFC |
| RF-ELE-08 | **Escada** | Reta, em L, em U; cálculo de degraus (fórmula de Blondel) e limites do código de obras | `IfcStair`, `IfcStairFlight` | V1 | IFC, CG |
| RF-ELE-09 | **Rampa** | Inclinação limitada conforme NBR 9050 (ex.: até 8,33% = 1:12, com limites de desnível por segmento) | `IfcRamp` | V1 | IFC, NBR9050 |
| RF-ELE-10 | **Guarda‑corpo / corrimão** | Ao longo de caminho ou borda | `IfcRailing` | V1 | IFC |
| RF-ELE-11 | **Pele de vidro / fachada‑cortina** | Grade de montantes e painéis | `IfcCurtainWall`, `IfcMember`, `IfcPlate` | V2 | IFC |
| RF-ELE-12 | **Revestimentos e acabamentos** | Pisos, forros, revestimento de parede por ambiente | `IfcCovering` | V1 | IFC |
| RF-ELE-13 | **Fundação** | Sapata, radier, estaca | `IfcFooting`, `IfcPile` | V1 | IFC |
| RF-ELE-14 | **Mobiliário e equipamentos** | Inseridos da biblioteca | `IfcFurniture`, `IfcSanitaryTerminal` | MVP (básico) | IFC |
| RF-ELE-15 | **Forma livre** | Sólido editável por faces/arestas, extrusão, revolução, varredura | `IfcBuildingElementProxy` | V2 | IFC, CG |
| RF-ELE-16 | **Operações sólidas** | Subtrair/unir/interceptar elementos, com associação mantida | `IfcBooleanResult` | V2 | IFC |
| RF-ELE-17 | Recortar elementos por plano/cobertura (ex.: parede sob telhado) | — | — | V1 | CG |

**Regras gerais para elementos (MVP):**
- Todo elemento pertence a um único nível da estrutura espacial
  (`IfcRelContainedInSpatialStructure`). Fonte: IFC.
- Topo e base podem ser presos a pavimentos com deslocamento. Fonte: CG.
- Prioridade de interseção entre materiais (ex.: concreto corta alvenaria) definida
  por material. Fonte: CG.

## 6. Ambientes e áreas

| ID | Requisito | Prior. | Fonte |
|---|---|---|---|
| RF-AMB-01 | Ambiente criado por contorno ou detectado automaticamente pelas paredes ao redor | MVP (`IfcSpace`) | IFC, CG |
| RF-AMB-02 | Nome, número, área, perímetro, pé‑direito, acabamentos | MVP (`Qto_SpaceBaseQuantities`: `NetFloorArea`, `GrossFloorArea`, `GrossPerimeter`, `Height`) | IFC |
| RF-AMB-03 | Etiqueta automática na planta | MVP | CG |
| RF-AMB-04 | Critérios de área configuráveis (útil, construída, computável) para prefeituras | V1 | CG |
| RF-AMB-05 | Zonas e agrupamentos de ambientes (unidade, apartamento, setor) | V1 (`IfcZone`) | IFC |
| RF-AMB-06 | Verificação de ventilação e iluminação mínimas por ambiente | V2 | CG |

## 7. Tipos, materiais e biblioteca

| ID | Requisito | Prior. | Fonte |
|---|---|---|---|
| RF-TIP-01 | Tipos de elemento: alterar o tipo atualiza todas as ocorrências | MVP (`IfcTypeProduct`, `IfcRelDefinesByType`) | IFC |
| RF-TIP-02 | Composições em camadas (ex.: reboco + bloco + reboco) reutilizáveis | MVP | IFC (`IfcMaterialLayerSetUsage`) |
| RF-TIP-03 | Materiais com cor, textura, hachura de corte e propriedades físicas | MVP | CG |
| RF-TIP-04 | Objetos paramétricos em formato próprio e aberto (parâmetros, geometria 3D, símbolo 2D) | V1 | CG, decisão do projeto |
| RF-TIP-05 | Editor de objetos paramétricos | V2 | CG |
| RF-TIP-06 | Biblioteca inicial brasileira (blocos, esquadrias, louças, mobiliário), licença CC BY 4.0 | MVP (básica) | decisão do projeto |
| RF-TIP-07 | Importar tipos e objetos de outro arquivo IFC | V1 | CG |
| RF-TIP-08 | Integração com bSDD para propriedades e classificações | V2 | BSDD, IOS |
| RF-TIP-09 | Classificação dos elementos | V1 | IFC (`IfcClassificationReference`), NBR15965 |

## 8. Documentação (padrão ABNT)

| ID | Requisito | Prior. | Fonte |
|---|---|---|---|
| RF-DOC-01 | Planta gerada do modelo: elementos cortados, em projeção e acima do plano de corte | MVP | CG, NBR6492 |
| RF-DOC-02 | Cortes e fachadas gerados do 3D com remoção de linhas ocultas, atualizados automaticamente | MVP | CG, NBR6492 |
| RF-DOC-03 | Tipos e espessuras de linha por categoria de elemento | MVP | NBR16861 (a confirmar), NBR6492 |
| RF-DOC-04 | Escala por vista; textos e símbolos se ajustam à escala | MVP | CG |
| RF-DOC-05 | Cotas lineares associativas (seguem o elemento), cotas de nível, cota automática de paredes e vãos | MVP | CG, NBR6492 |
| RF-DOC-06 | Textos, etiquetas automáticas por propriedade, hachuras, linhas e símbolos 2D | MVP | IFC (`IfcAnnotation`) |
| RF-DOC-07 | Símbolos de corte, fachada, norte e indicação de nível | MVP | CG, NBR6492 |
| RF-DOC-08 | Níveis de detalhe por escala (ex.: 1:100 simplificado, 1:50 com camadas) | V1 | CG |
| RF-DOC-09 | Pranchas A0–A4 (vertical ou horizontal), margens e marcas de dobra, legenda/carimbo editável, várias vistas por prancha | MVP | NBR16752, REV-SHEETS |
| RF-DOC-10 | Exportação PDF vetorial (uma ou várias pranchas) | MVP | CG |
| RF-DOC-11 | Exportação DXF; importação de DXF/DWG como referência | V1 | CG |
| RF-DOC-12 | Vistas de detalhe ampliado e desenhos 2D livres | V1 | CG |
| RF-DOC-13 | Indicação de revisões nas pranchas | V1 | CG |
| RF-DOC-14 | Perspectivas, vistas 3D e tabelas na prancha | V1 | REV-SHEETS |
| RF-DOC-15 | Conjuntos de pranchas por etapa de projeto (estudo, anteprojeto, executivo), incluindo implantação, plantas, cortes e elevações | V1 | NBR6492 |
| RF-DOC-16 | Modelos de pranchas para aprovação em prefeitura (quadro de áreas, situação) | V1 | CG |

## 9. Quantitativos e tabelas

| ID | Requisito | Prior. | Fonte |
|---|---|---|---|
| RF-QTD-01 | Quantidades calculadas por elemento (comprimento, área, volume, contagem) | MVP (`IfcElementQuantity`, `Qto_*BaseQuantities`) | IFC |
| RF-QTD-02 | Tabelas configuráveis por tipo, com filtros, agrupamento e totais | MVP | CG |
| RF-QTD-03 | Tabela de esquadrias e quadro de áreas | MVP | CG |
| RF-QTD-04 | Tabelas inseridas em pranchas | V1 | REV-SHEETS |
| RF-QTD-05 | Exportar tabelas para CSV/XLSX | MVP | CG, IOS (IfcCSV) |
| RF-QTD-06 | Edição de propriedades pela tabela | V1 | CG |
| RF-QTD-07 | Vínculo com composições SINAPI (referência oficial, gratuita, mensal, por UF) para orçamento preliminar | V2 | SINAPI |

## 10. Interoperabilidade

| ID | Requisito | Prior. | Fonte |
|---|---|---|---|
| RF-INT-01 | IFC 4.3 nativo; exportar também IFC 2x3 e IFC 4 | MVP (4.3) / V1 (outros) | IFC, IOS |
| RF-INT-02 | Abrir IFC de qualquer origem e editar elementos reconhecidos | MVP | CG |
| RF-INT-03 | Referenciar modelos IFC externos (estrutura, instalações) como modelos federados | V1 | CG |
| RF-INT-04 | BCF: criar, ler e responder apontamentos com ponto de vista | V1 | BCF, IOS |
| RF-INT-05 | IDS: validar o modelo contra requisitos de informação | V1 | IDS, IOS (IfcTester) |
| RF-INT-06 | Comparar versões do IFC e destacar alterações | V1 | IOS (IfcDiff) |
| RF-INT-07 | Importar imagens, PDF e nuvem de pontos como referência | V2 | CG |
| RF-INT-08 | Exportar OBJ/glTF para visualização e renderização | V2 | CG |
| RF-INT-09 | Detecção de interferências entre elementos e modelos | V2 | IOS (IfcClash) |

## 11. Colaboração (servidor com reserva de elementos)

Decisão do projeto (2026‑10‑14). A funcionalidade (reservar antes de alterar, pedir
liberação a quem reservou, enviar e receber alterações) está documentada
publicamente em ferramentas comerciais (AC-COL, REV-COL). O desenho do BrasBim é
próprio.

| ID | Requisito | Prior. | Fonte |
|---|---|---|---|
| RF-COL-01 | Servidor de projeto: vários usuários abrem o mesmo projeto em computadores diferentes | V1 | AC-COL, REV-COL |
| RF-COL-02 | Reserva de elementos, pavimentos ou zonas; só quem reservou altera ou exclui | V1 | AC-COL, REV-COL |
| RF-COL-03 | Elementos novos podem ser criados sem reserva prévia e ficam reservados por quem os criou | V1 | AC-COL |
| RF-COL-04 | Enviar e receber alterações; reservar exige estar com o projeto atualizado | V1 | AC-COL, REV-COL |
| RF-COL-05 | Pedido de liberação a quem reservou, com aviso e resposta | V1 | AC-COL, REV-COL |
| RF-COL-06 | Trabalho offline com sincronização ao reconectar | V2 | CG |
| RF-COL-07 | Histórico de envios com autor, data e possibilidade de reverter | V1 | CG |
| RF-COL-08 | Permissões por papel (administrador, editor, leitor) | V2 | AC-COL |

## 12. Recursos para o Brasil

| ID | Requisito | Prior. | Fonte |
|---|---|---|---|
| RF-BR-01 | Interface, documentação e biblioteca em pt‑BR | MVP | decisão do projeto |
| RF-BR-02 | Representação e documentação conforme NBR 6492 e normas de desenho técnico (NBR 16752, NBR 16861) | MVP | NBR6492, NBR16752, NBR16861 |
| RF-BR-03 | Verificações de acessibilidade (NBR 9050): vãos, rampas, sanitários, áreas de giro | V1 | NBR9050 |
| RF-BR-04 | Apoio à NBR 15575: dados de desempenho por sistema | V2 | CG |
| RF-BR-05 | Classificação conforme a série NBR 15965 | V1 | NBR15965 |
| RF-BR-06 | Parâmetros de código de obras por município (recuos, taxa de ocupação, coeficiente de aproveitamento) | V2 | CG |
| RF-BR-07 | Orçamento com SINAPI (ver RF-QTD-07) | V2 | SINAPI |

## 13. Fora do escopo (por ora)

- Leitura/gravação de formatos proprietários (`.pln`, `.rvt`, `.rfa` etc.)
- Linguagem de objetos compatível com software proprietário
- Análise estrutural, energética e luminotécnica (integração via IFC com outras ferramentas)
- Renderização fotorrealista própria (exportar para ferramentas externas)
- Projeto de instalações (MEP) completo: F

## 14. Requisitos não funcionais

| ID | Requisito | Fonte |
|---|---|---|
| RNF-01 | Windows, Linux e macOS | decisão do projeto |
| RNF-02 | Núcleo (`brasbim/core`) sem dependência de Qt, testável isoladamente | decisão do projeto |
| RNF-03 | Todo recurso tem teste automático que valida o IFC gerado | decisão do projeto |
| RNF-04 | Modelo de 5.000 elementos abre em menos de 10 s e navega a 30 fps ou mais em hardware intermediário (meta a validar) | CG |
| RNF-05 | API Python pública para scripts e plugins | CG |
| RNF-06 | Licenças: núcleo LGPL‑3.0‑or‑later, aplicativo GPL‑3.0‑or‑later, biblioteca CC BY 4.0. Compatível com IfcOpenShell (LGPL‑3.0) e Bonsai (GPL‑3.0‑or‑later) | IOS, BON |

## 15. Fontes públicas (consultadas em 2026‑10‑14)

| Código | Fonte | O que foi verificado |
|---|---|---|
| **IFC** | buildingSMART, IFC 4.3 (ISO 16739‑1). Documentação: https://ifc43-docs.standards.buildingsmart.org/ (bloqueia acesso automatizado). Fonte lida: https://github.com/buildingSMART/IFC4.x-development (ramo `ifc4.3-main`, `docs/schemas/**/Entities/*.md`, `PropertySets`, `QuantitySets`, `PropertyEnumerations`) | Existência e definição de todas as entidades citadas; `Pset_WallCommon.Status` com `PEnum_ElementStatus` (NEW, EXISTING, DEMOLISH, TEMPORARY); `Qto_SpaceBaseQuantities`; `IfcRoof` como agregação de partes; `IfcDoor`/`IfcWindow` hospedados em aberturas |
| **BCF** | buildingSMART BCF: https://github.com/buildingSMART/BCF-XML | Página pública acessível |
| **IDS** | buildingSMART IDS: https://github.com/buildingSMART/IDS | Página pública acessível |
| **BSDD** | buildingSMART Data Dictionary: https://www.buildingsmart.org/users/services/buildingsmart-data-dictionary/ | Não acessível por ferramenta (HTTP 403); citado pela documentação do IfcOpenShell |
| **IOS** | IfcOpenShell: https://docs.ifcopenshell.org/ e https://github.com/IfcOpenShell/IfcOpenShell | Ferramentas IfcDiff, IfcTester, BCF, IfcCSV, IfcClash, bSDD; esquemas IFC2X3, IFC4 e IFC4X3; licença LGPL‑3.0 |
| **BON** | Bonsai: https://docs.bonsaibim.org/ e código em `src/bonsai` do repositório IfcOpenShell | Autoria IFC nativa sobre Blender; licença GPL‑3.0‑or‑later (cabeçalho do código) |
| **NBR6492** | ABNT NBR 6492:2021, *Documentação técnica para projetos arquitetônicos e urbanísticos — Requisitos*. Título e escopo via questões de concurso e catálogos | Título oficial (edição de 2021); etapas de projeto com implantação, plantas, cortes e elevações. Texto não lido |
| **NBR16752** | ABNT NBR 16752:2020, *Desenho técnico — Requisitos para apresentação em folhas de desenho*: https://www.normas.com.br/visualizar/abnt-nbr-nm/11569/ | Escopo (formatos, legenda, dobramento, escalas); formatos A0–A4. Texto não lido |
| **NBR16861** | ABNT NBR 16861:2020, linhas e escrita em desenho técnico (substitui NBR 8403), segundo material didático da UFRN: https://www.vetorial.design.ufrn.br/src/pdfs/Normas.pdf | **A confirmar no catálogo da ABNT** |
| **NBR9050** | ABNT NBR 9050 (acessibilidade). Rampas até 8,33% (1:12) com limites de desnível por segmento, segundo fontes secundárias | Edição vigente e valores a confirmar no texto oficial |
| **NBR15965** | ABNT NBR 15965 (série), *Sistema de classificação da informação da construção*. Partes 1, 2, 3 e 7 confirmadas em catálogos (normas.com.br, Target) | Número atual de partes a confirmar |
| **SINAPI** | CAIXA, SINAPI: https://www.caixa.gov.br/sinapi | Referência oficial, gratuita, atualizada mensalmente por UF (fontes secundárias; site da Caixa não acessível por ferramenta) |
| **AC-COL** | Graphisoft Help, visão geral da reserva em trabalho colaborativo: https://help.graphisoft.com/AC/25/INT/_AC25_Help/080_Collaboration/080_Collaboration-26.htm | Funcionalidade: reservar antes de alterar; elementos novos sem reserva; pedido a quem reservou; exige projeto atualizado |
| **REV-COL** | Autodesk Revit Help, empréstimo de elementos: https://help.autodesk.com/cloudhelp/2025/ENU/Revit-Collaborate/files/GUID-27E3B22D-79D3-44F5-A630-6E5F614585B4.htm | Funcionalidade: tornar elemento editável; pedido de edição ao detentor; liberação ao sincronizar |
| **REV-SHEETS** | Autodesk Revit Help, visão geral de pranchas (2014): https://help.autodesk.com/cloudhelp/2014/ENU/Revit/files/GUID-6D569C3B-B473-4AA9-BB2F-B93088D7D9A9.htm | Funcionalidade: prancha com várias vistas e tabelas |
| **CG** | Conhecimento geral de arquitetura, construção e BIM | Sem fonte específica nesta etapa |

> Observação de vocabulário: "reserva" é usada aqui como palavra comum do português,
> não como nome de comando. Ao nomear o recurso na interface, escolher termo próprio
> e revisar com o `revisor-cleanroom`.
