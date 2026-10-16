---
documento: Modelo de dados — operações serializáveis
requisito: RF-NUC-01, RF-NUC-02
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-14
status: rascunho (aguarda revisão)
---

# Operações serializáveis

Formato das operações que alteram o modelo IFC. Origem: rascunho da spec da parede
(`spec/elementos/parede.md` §5.2), já implementado em `brasbim/core/ops`.

## 1. Operação
Registro JSON, unidades SI (m, rad), coordenadas no plano do pavimento:

```json
{"op": "wall.edit", "id": "<GlobalId>", "before": {"base_offset": 0.0}, "after": {"base_offset": 0.1}}
```

| Campo | Uso |
|---|---|
| `op` | Nome da operação (`<objeto>.<ação>`) |
| `id` | GlobalId do objeto criado, alterado ou excluído |
| `data` | Estado completo (criar/excluir). Excluir guarda o estado para poder desfazer |
| `before` / `after` | Só os campos alterados (editar). `before` serve para detectar conflito: a edição é rejeitada se o estado atual for outro |

Toda operação é invertível sozinha: `create` ↔ `delete` (mesmo `data`), e `edit` troca
`before` com `after`.

## 2. Transação
`{"label": "Criar parede", "ops": [...]}`. Uma ação do usuário é uma transação, aplicada
inteira ou não aplicada (se uma operação falha, as anteriores são desfeitas). Desfazer
aplica a inversa (operações invertidas, em ordem reversa). O diário registra tudo o que
foi aplicado, inclusive desfazer e refazer. Reaplicado num modelo vazio com o mesmo
projeto, o diário reproduz o mesmo IFC.

## 3. Efeitos derivados
Não são registrados. Quem aplica a operação os recalcula: corpo, recortes de junção,
`IfcMaterialLayerSetUsage` e quantidades. Entidades derivadas recebem GlobalId
determinístico (UUID v5 do GlobalId do dono + papel, ex.: `"<parede>/pset/BrasBim_Parede"`),
para que refazer e reaplicar produzam os mesmos GlobalIds. *(decisão do projeto)*

## 4. Operações existentes
| `op` | Dados | Situação |
|---|---|---|
| `storey.create` / `.delete` / `.edit` | `name`, `elevation`, `cut_height` | Provisória (sem spec de pavimento); `cut_height` (plano de corte acima da cota; `None` = padrão 1,50, Pset `BrasBim_Pavimento`): spec/ui 06 §3.1 |
| `material.edit` | `id` = nome do material; `style` (`color`, `cut`: `pattern`, `background`, `angle`, `spacing`, `line_color`; `None` = sem estilo) | spec/ui 06 §4.3; vale para todos os `IfcMaterial` com o nome |
| `wall_type.create` / `.delete` | `name`, `predefined_type`, `object_type`, `layers[]`, `plan_style` | `create` provisória (RF-TIP-01); `plan_style`: spec/ui 03 §6 |
| `wall_type.edit` | `name`, `predefined_type`, `object_type`, `layers`, `plan_style` | parede §5.2; spec/ui 02 §8.1 e 03 §6 |
| `wall.create` / `.delete` / `.edit` | `name`, `type`, `storey`, `path`, `ref_line`, `flip_layers`, `base_offset`, `top_mode`, `top_storey`, `top_offset`, `fixed_height`, `common`, `no_join`, `top_shape`, `top_profile`, `tilt` | parede §5.2; `no_join` (junções desfeitas): spec/ui 05 §7.1; `top_shape` (`flat`/`slope`/`gable`/`free`), `top_profile` (lista de [posição, altura a partir da base]; vazia no plano; `wall.edit` que muda só `path` reposiciona os pontos proporcionalmente) e `tilt` (graus, −45..45, + para a esquerda): spec/ui 08 §4–§5 |
| `wall.split` / `wall.merge` | `path` (caminho original), `at` (ponto), `new` (GlobalId da 2ª parte) | parede §5.1, §5.2; `wall.merge` é só a inversa |
| `path_connection.create` / `.delete` | `relating`, `related` (GlobalIds das paredes), `relating_type`, `related_type` (`ATSTART` \| `ATEND` \| `ATPATH`) | parede §5.2, §6.2 |
| `opening.create` / `.delete` / `.edit` | `wall`, `kind` (`OPENING` \| `RECESS`), `distance`, `width`, `height`, `sill`, `depth`, `side` (`left` \| `right`) | parede §5.2, §6.3 |
| `filling.attach` / `.detach` | `id` = GlobalId do elemento que preenche; `opening` | parede §5.2, §6.3 |
| `door_type.create` / `.delete` / `.edit` | `name`, `predefined_type`, `operation_type`, `lining` (`thickness`, `depth`, `casing_thickness`, `casing_depth`, `threshold_thickness`), `panels[]` (`operation`, `position`, `width`, `depth`), `materials` (`lining`, `framing`, `glazing`), `defaults` (`width`, `height`, `base`), `variant` | porta §5.2 |
| `door.create` / `.delete` / `.edit` | `name`, `type`, `opens_to` (`left` \| `right`), `align` (`left_face` \| `axis` \| `right_face`), `offset`, `common`, `foreign` | porta §5.2 |
| `window_type.create` / `.delete` / `.edit` | `name`, `code`, `predefined_type`, `partitioning`, `lining` (`depth`, `thickness`, `mullion_thickness`, `mullion_offsets[]`, `transom_thickness`, `transom_offsets[]`), `panels[]` (`operation`, `position`, `frame_depth`, `frame_thickness`), `materials`, `defaults`, `variant` | janela §5.2 |
| `window.create` / `.delete` / `.edit` | os mesmos campos de `door.*` (na janela, `foreign.operation_type` guarda o `PartitioningType`) | janela §5.2 |
| `column_type.create` / `.delete` / `.edit` | `name`, `predefined_type`, `section` (`{"shape": "rect", "b", "h"}` \| `{"shape": "circle", "d"}`), `material`, `plan_style` | pilar §5.2 |
| `column.create` / `.delete` / `.edit` | `name`, `type`, `storey`, `point`, `cardinal`, `angle` (graus), `base_offset`, `top_mode`, `top_storey`, `top_offset`, `fixed_height`, `common`, `foreign`, `placement` | pilar §5.2 |
| `beam_type.create` / `.delete` / `.edit` | `name`, `predefined_type`, `section` (`{"shape": "rect", "b", "h"}`), `material`, `plan_style` | viga §5.2 |
| `beam.create` / `.delete` / `.edit` | `name`, `type`, `storey`, `start`, `end`, `ref_line`, `top_mode`, `top_storey`, `top_offset`, `top_elevation`, `common`, `foreign`, `placement` | viga §5.2 |
| `slab_type.create` / `.delete` / `.edit` | `name`, `predefined_type` (`FLOOR` \| `BASESLAB`), `layers[]` (`material`, `thickness`; de cima para baixo), `plan_style` | laje §5.2 |
| `slab.create` / `.delete` / `.edit` | `name`, `type`, `storey`, `outline[]`, `top_offset`, `common`, `foreign`, `placement` | laje §5.2 |
| `slab_opening.create` / `.delete` / `.edit` | `slab`, `outline[]` (coordenadas do pavimento, anti-horário; Pset `BrasBim_AberturaLaje`) | spec/ui 12 §3.2; mover, girar, espelhar e copiar a laje geram um `slab_opening.*` por abertura; excluir a laje exclui antes as aberturas |
| `roof.create` / `.delete` / `.edit` | `name`, `type` (`IfcSlabType` `ROOF`), `storey`, `outline[]` (contorno de apoio), `shape`, `slope` (%), `overhang`, `base_height`, `side`, `parts[]` (GlobalIds das águas), `common` | cobertura §5.1; `IfcRoof` agrega uma `IfcSlab` por água; Pset `BrasBim_Cobertura` |
| `storey.edit` com `scale` | denominador da escala da planta (`None` = 1:50, Pset `BrasBim_Pavimento`, `Escala`) | spec/ui 13 §2 |
| `space.create` / `.delete` / `.edit` | `storey`, `outline[]`, `number` (`Name`), `name` (`LongName`), `height` (`None` = calculado), `label_at` | spec/ui 13 §3.2 |
| `dimension.*`, `level_mark.*`, `text.*`, `line2d.*`, `hatch.*`, `north.*` | `storey` e os parâmetros de cada tipo (spec/ui 13 §4–§7), guardados em JSON no Pset `BrasBim_Anotacao` (`Tipo`, `Parametros`); na cota, cada ponto `{"at", "ref"}` | spec/ui 13; a geometria `Annotation` é derivada; a posição dos pontos presos (`at`, `lost`) é atualizada pela derivação |
| `view.create` / `.delete` / `.edit` | `name`, `letter`, `kind` (`section`/`elevation`), `a`, `b`, `side` (`left`/`right`), `depth`, `zmin`, `zmax`, `scale` (JSON no Pset `BrasBim_Vista`; `IfcAnnotation` na edificação) | spec/ui 14 §3; o desenho do corte é calculado, não gravado |
| `sheet.create` / `.delete` / `.edit` | `number`, `title`, `format` (A0–A4), `orientation`, `views[]` (`{"kind": "plan", "storey"}` ou `{"kind": "view", "view"}`, com `at` em mm do papel) — JSON no Pset `BrasBim_Prancha`; `IfcAnnotation` "Prancha" na edificação | spec/ui 15 §4; excluir uma vista ou um pavimento gera antes o `sheet.edit` que a tira das pranchas |
| `project.edit` | `name` (`IfcProject.Name`), `address`, `owner`, `responsible`, `registration` (Pset `BrasBim_Projeto`) | spec/ui 15 §4 (parte de RF-PRJ-06) |

Caminho (`path`):
- Reta: `{"kind": "line", "start": [x, y], "end": [x, y]}`
- Arco: `{"kind": "arc", "start", "end", "radius", "ccw": bool, "large": bool}`.
  `large` distingue o arco maior que meia volta, porque raio + sentido + extremidades não
  bastam. *(decisão do projeto)*

`ref_line`: `axis` | `left_face` | `right_face`. `top_mode`: `storey` | `fixed`.
`common`: propriedades de `Pset_WallCommon` que diferem do padrão.

Aberturas: `id` = GlobalId do `IfcOpeningElement`. `distance` vai do início da parede ao
começo da abertura, ao longo do caminho; `sill` é a base da abertura em relação à base da
parede; `depth` e `side` (face de entrada) só valem para nicho. *(decisão do projeto)*
Excluir uma parede gera, na mesma transação e nesta ordem: `filling.detach`,
`door.delete`, `opening.delete`, `path_connection.delete` e `wall.delete` (spec da
parede §6.4, porta §6.4). Elementos de outra origem que preenchem a abertura só são
desligados.

Portas: `id` = GlobalId do `IfcDoor`. Largura, altura, distância e base são da abertura
(`opening.*`). Criar uma porta gera `opening.create`, `door.create` e `filling.attach`;
excluir gera `filling.detach`, `door.delete` e `opening.delete` (este último só se o vão
não for mantido). Posição, `OverallWidth`/`OverallHeight`, contenção, corpo e
quantidades da porta são derivados. `opens_to` é gravado no sentido do eixo x do
posicionamento da porta; `align` e `offset` no Pset `BrasBim_Esquadria`.

Janelas: iguais às portas, com `window.*` e `window_type.*` (janela §5.2). O peitoril é o
`sill` da abertura. O código do tipo (`code`) é o `Reference` do `Pset_WindowCommon` do
`IfcWindowType`. Cada peça do `Body` de porta e janela tem um `IfcStyledItem` com o
`IfcSurfaceStyle` do material dela (marco, caixilho, vidro; spec/ui 09 §7); o estilo
padrão é gravado no material quando o tipo é gravado.

Dividir: `wall.split` encurta a parede até o ponto (projetado no caminho) e cria a 2ª
parte com o mesmo estado. Os comandos completam a ação na mesma transação: `opening.edit`
leva as aberturas depois do ponto para a nova parede, e `path_connection.*` refaz as
junções (inclusive a L colinear entre as duas partes). A inversa `wall.merge` exige que a
2ª parte já esteja sem aberturas e junções; a ordem invertida da transação garante isso.
*(decisão do projeto)*

Pilar, viga e laje: `id` = GlobalId do elemento. Os topos são planos, como na parede
(`top_mode`: `storey` | `fixed`); no pilar a altura fixa é `fixed_height`, na viga a cota
fixa do topo (a partir do pavimento dela) é `top_elevation`. `cardinal` é o
`CardinalPoint` do `IfcMaterialProfileSetUsage` (1–9; a "esquerda" do IFC é o +x do
perfil, olhando na direção da extrusão: visto de cima, o canto inferior esquerdo de um
pilar é o 3). O contorno da laje (`outline`) é gravado anti-horário, sem pontos repetidos
ou alinhados, começando pelo vértice da origem do posicionamento; os comandos já mandam o
contorno assim. As camadas do tipo de laje vêm de cima para baixo e são gravadas na
ordem inversa (camada 1 = a de baixo). Mover, girar, espelhar e copiar geram um
`*.edit` (ou `*.create`) por elemento. Elementos de outra origem (sem `BrasBim_Pilar`,
`BrasBim_Viga` ou `BrasBim_Laje`): `foreign` = `{"shape": representação}` e `placement` =
`{"rel", "location", "axis", "ref"}` do `IfcLocalPlacement`; mover e girar trocam só o
`placement`. Excluir um pavimento gera, antes do `storey.delete`, `column.edit` e
`beam.edit` que passam para altura (cota) fixa os que tinham o topo nele.
Pilar e viga com a seção digitada (spec/ui 10 §3): quando ainda não há tipo com essa
seção, a transação começa com `column_type.create`/`beam_type.create` e o elemento
aponta para ele (`type`); não há operação própria para a seção.

Junções: `id` = GlobalId da `IfcRelConnectsPathElements`. Os comandos detectam as junções e geram
estas operações na mesma transação da criação, edição ou exclusão da parede.

## 5. Pendências
- Janelas (RF-ELE-06) entram na cascata como as portas.
- Reserva de elementos (RF-COL-02): uma operação declara quais GlobalIds exige reservados.
