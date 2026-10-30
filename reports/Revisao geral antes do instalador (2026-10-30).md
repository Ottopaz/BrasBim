# Revisão geral antes do instalador

*2026‑10‑30. Pedido do revisor: antes de fazer o instalador `.exe`, revisar o código
inteiro, tirar o que não é usado, conferir os erros e passar um pente fino no que o
BrasBim já faz e no que ainda falta de ferramenta básica (inclusive operações de
sólidos). Base: o código (≈ 60 mil linhas em `brasbim/`), `ruff`, `vulture`, a suíte de
testes, `spec/REQUISITOS.md`, o `CONTEXTO.md` e o pente fino de 2026‑10‑26
(`reports/Pente fino BrasBim x pesquisa.md`), que continua valendo para a comparação
com a pesquisa clean‑room.*

Legenda: ✅ temos · ◐ em parte · ✗ não temos (conferido no código).

---

## 1. Código: o que foi limpo e corrigido

**Saúde geral: boa.** `ruff` limpo; nenhum `except` que engole erro em silêncio (35
`except` genéricos, todos registram ou mostram a falha); nenhum TODO/FIXME esquecido;
todos os módulos são usados.

**Erros corrigidos**
- `tests/test_precisao.py` (PR08, PR09): `pytest.approx` com listas de pares de pontos;
  o pytest 9 recusa estrutura aninhada. As comparações passaram a usar a lista plana
  (`_flat`). Defeito do teste, não do programa.
- `tests/test_barra_da_vista.py` (VB09, pendência antiga "teste instável"): depois de
  "Mandar para trás" as outras duas linhas empatam na ordem, e o resultado do "Um passo à
  frente" dependia do desempate por GlobalId, que é aleatório. O passo agora é testado com
  uma só vizinha sobreposta (como acontece no uso); 8 execuções seguidas passaram.
- `ui/view_bar.py`: linha inalcançável depois de um `return`.

**Código sem uso removido** (≈ 120 linhas; nada era chamado nem pelos testes):
`annotations.rebuild.annotations_of`, `drawings.sheets.remove_from_sheet`,
`edits.OFFSETTABLE`, `fillings.commands.edit_windows`, `fillings.params.PANEL_POSITIONS`,
`grids.is_grid`, `materials.add_library_styles`, `objects.builtin.all_states`,
`objects.definition._field_text`, `objects.elements.label_of`, `objects.hosting.wall_of`,
`objects.library.Index.folder_of`, `plan.DETAILS`, `snap.SnapIndex.add_polyline`,
`linework.Lines.polylines`, `structure.commands.create_roof_rectangle`,
`structure.roofs.all_roofs`, `structure.types.PROFILE_KINDS` e `profile_kind`,
`terrain.delaunay`, `walls.commands.detach_filling`, `ui.assistant.tool_label`.

**Ficou de propósito:** funções do núcleo usadas só pelos testes e exemplos
(`create_wall`, `create_window`, `create_slab_rectangle`…; são a API do núcleo), métodos
do painel de propriedades chamados pelo nome (`_stair`, `_railing`, `_terrain`) e as
cores da logo em `theme.py` (`BRAND_DARK`, `BRAND_PINK`: único registro da paleta da
marca).

**Pendências de código que continuam** (já no `CONTEXTO.md`): janelas vazando nos testes
de interface (fixture `window`); medições em projeto grande (cortes, 3D, `hidden_ids`).

---

## 2. O que o BrasBim já faz

| Área | Ferramentas e recursos |
|---|---|
| **Modelagem** | Parede reta, em arco e por retângulo (camadas, junções L/T/X, topo inclinado/empena, tombada); pilar retangular e circular; viga; laje (contorno, pelo cômodo, inclinada, abertura); cobertura plana, 1, 2 e 4 águas; claraboia; escada reta, L e U; guarda‑corpo; terreno por contorno, pontos e curvas do DWG; porta, janela e vão livre na parede; objetos paramétricos da biblioteca (mobiliário, louças, eletrodomésticos, vegetação) com editor |
| **Recortes entre elementos** | ◐ Automáticos (spec/ui 12): estrutura recorta o que encosta, gravado em `IfcRelInterferesElements`. Sem ferramenta para o usuário escolher alvo e operador |
| **Edição** | Selecionar (clique, janela, laço, semelhantes), mover, copiar, cópia em série linear, girar, espelhar, dividir, deslocar paralela, aparar/estender, concordar, área de seleção com esticar, alças na planta e no 3D, travar, ocultar/isolar, ordem de desenho, desfazer ilimitado |
| **Precisão** | Atração em todos os pontos, linhas‑guia, quadro de medidas com contas e coordenadas, linha de comando com apelidos, paleta de comandos, medir |
| **Documentação** | Ambientes que acompanham as paredes, cotas (linear, raio, ângulo, nível, automática), textos, rótulos, hachuras, linhas, círculos, arcos, spline, norte, eixos, nuvem de revisão, cortes e fachadas, camadas, penas, vistas salvas, pranchas com folhas mestras, PDF, DXF/DWG |
| **Projeto legal** | Situação (existente/demolir/novo), perfil municipal (5 cidades), quadro de áreas com memória de cálculo e índices |
| **Quantidades** | Tabelas configuráveis, CSV/XLSX |
| **Interoperabilidade** | IFC 4.3 nativo, importar DXF/DWG (LibreDWG embutido) |
| **Outros** | Trabalho em equipe na rede local, assistente de IA, salvamento automático |

---

## 3. O que falta: ferramentas básicas

Ordem por importância para quem vai baixar o instalador e projetar uma casa do começo ao
fim. "Spec" diz se já existe especificação.

### 3.1 Modelagem: faltas que um projetista sente no primeiro projeto

| # | Falta | Por que é básico | Spec | Hoje |
|---|---|---|---|---|
| M1 | **Operações de sólidos** (subtrair, subtrair para cima/baixo, interseção) escolhidas pelo usuário, associativas | Nicho, rebaixo, recorte de laje por viga, peça especial: tudo que as ferramentas não preveem | spec/ui 41 §3 (SO01–SO06), pontos (e)–(k) sem resposta | ◐ só automático |
| M2 | **Recortar parede pela cobertura** (oitão, parede sob telhado) | Toda casa com telhado aparente; hoje o oitão é feito à mão no topo da parede | ✗ (RF‑ELE‑17) | ✗ |
| M3 | **Forro e piso como revestimento** (`IfcCovering`) | Forro de gesso e piso por ambiente estão em todo projeto e no quantitativo | ✗ (RF‑ELE‑12) | ✗ |
| M4 | **Rampa** (`IfcRamp`) com limite da NBR 9050 | Acessibilidade é exigida pela prefeitura | ✗ (RF‑ELE‑09) | ✗ |
| M5 | **Perfil complexo** (parede, viga, pilar com seção desenhada) | Muretas, platibandas com pingadeira, perfis metálicos | spec/ui 41 §4 | ✗ |
| M6 | **Forma livre**: extrusão, revolução e varredura de um contorno desenhado | Tudo que não é parede/laje/pilar (bancada, floreira, marquise curva) | ✗ (RF‑ELE‑15) | ✗ |
| M7 | **Escalar** e **cópia polar/matriz** | Básico de CAD; só há cópia em série linear | plano das barras, fase 4 | ✗ |
| M8 | **Agrupar** | Selecionar/mover conjuntos (cozinha montada, banheiro) | ✗ (RF‑NUC‑07) | ✗ |
| M9 | Fundação (sapata, radier) | Desenho de locação e corte; o cálculo fica com o engenheiro | ✗ (RF‑ELE‑13) | ✗ |
| M10 | Pele de vidro | Fachadas comerciais | ✗ (RF‑ELE‑11, V2) | ✗ |

### 3.2 Vistas e documentação

| # | Falta | Spec | Hoje |
|---|---|---|---|
| D1 | **Elevação interna, detalhe ampliado, folha de trabalho, câmera** | spec/ui 35, **aprovada** | ✗ |
| D2 | **Polilinha, ponto de apoio, figura (imagem), desenho na prancha** | spec/ui 36, **aprovada** | ✗ |
| D3 | **Caixa de corte no 3D** e estilos (arestas, raio‑X); vista 3D ortogonal | ✗ (RF‑UI‑05/06) | ✗ (só perspectiva) |
| D4 | Tabela na prancha | ✗ (RF‑QTD‑04) | ✗ |
| D5 | Dados do projeto (endereço, cliente, RT, ART/RRT) puxados pelo carimbo | ✗ (RF‑PRJ‑06) | ✗ |
| D6 | Projeto legal etapas 4–5 (peças na prancha, memorial) | spec/ui 31 | ✗ |

### 3.3 Troca de arquivos (o que o engenheiro e o render pedem)

| # | Falta | Por que | Hoje |
|---|---|---|---|
| I1 | **Exportar IFC 2x3 / IFC 4** | Programas de estrutura e instalações usados no Brasil ainda leem melhor o 2x3 | ✗ |
| I2 | **Exportar glTF/OBJ** | Levar o modelo para programas de render e apresentação | ✗ |
| I3 | Validação IDS (`ifctester`) | Cadernos BIM brasileiros; esforço baixo | ✗ |
| I4 | BCF (apontamentos) | Conversa com o engenheiro sobre o modelo | ✗ |
| I5 | IFC de outra disciplina como referência | Ver a estrutura do engenheiro junto | ✗ |

---

## 4. Recomendação

O BrasBim já cobre o fluxo de uma casa térrea ou sobrado: modelar, documentar e
imprimir para a prefeitura. Para a **primeira versão pública** (a do instalador),
sugiro fechar antes só o que um projetista sente falta logo no primeiro projeto:

1. **M1 Operações de sólidos** (spec 41 §3 pronta; falta o revisor responder (e)–(k)).
2. **M2 Recortar parede pela cobertura**, que conversa com M1: mesma base
   (`IfcRelInterferesElements`), alvo = parede, operador = cobertura.
3. **M3 Forro e piso** por ambiente.
4. **I1 Exportar IFC 2x3** e **I2 glTF**: são o que faz o arquivo sair do BrasBim e
   ser usado por outros programas.

Depois, o instalador `.exe`; e, na sequência, as specs já aprovadas (D1, D2), a rampa
(M4), o perfil complexo (M5), a forma livre (M6) e o resto, guiados pelo retorno de quem
baixar.
