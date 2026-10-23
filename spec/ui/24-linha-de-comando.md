---
documento: Linha de comando (barra fixa sob as vistas, apelidos, dica e opções da ferramenta, histórico, coordenadas)
requisito: RF-NUC-05 (edição), RF-DES-02 (entrada de pontos com exatidão)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-23
status: em revisão (fluxo do MVP: implementado na sequência)
revisor: OTTO
---

# Linha de comando

## 1. Propósito
Pedido do revisor (2026‑10‑23): uma **linha de comando** fixa sob a planta, para quem
desenha com uma mão no teclado. Ela junta o que já existe e está espalhado: a busca da
paleta (spec/ui 23 §9), a dica da ferramenta (hoje na barra de estado), as opções da
barra Opções e a entrada de números. Acrescenta apelidos curtos, histórico e coordenadas
digitadas.

Já existe e **não muda**: o quadro de medidas junto ao cursor abre ao digitar o primeiro
algarismo quando a ferramenta espera um número (spec/ui 07 §2); Enter na seleção vazia
repete a última ferramenta (spec/ui 23 §3.2); a paleta Ctrl+K continua.

## 2. Onde fica
Uma barra de uma linha **sob as vistas** (planta, 3D, lado a lado e as abas), dentro da
área central, em toda a largura. Da esquerda para a direita:
1. **Campo** de digitação. Vazio, ele mostra em texto-fantasma a **dica** da ferramenta
   ativa seguida de "comando, apelido ou x;y" (a dica que antes ia para a barra de
   estado; com a linha visível, a barra de estado não a repete). A dica some ao digitar,
   o que deixa a linha curta mesmo com os painéis abertos;
2. **Opções** da ferramenta ativa, como palavras clicáveis (§5);
3. botão **Histórico** (abre a lista do §6).

Campo e opções encolhem com a janela (cortados à direita); a linha nunca alarga a
janela.

Exibir > Barras > **Linha de comando** mostra ou esconde (preferência do usuário, não do
projeto). Escondida, a dica volta para a barra de estado e as teclas voltam a ser só da
vista.

## 3. O teclado vai para ela sozinho
Com o foco na planta ou no 3D, uma tecla de **texto** que a vista não usa vai para o
campo da linha de comando, que recebe o foco já com essa letra:
- letras, `@`, `;` e os demais sinais;
- algarismos, vírgula, ponto e menos **só quando a ferramenta não espera um número** (se
  espera, abrem o quadro de medidas, como hoje);
- digitando `;` ou `@` no quadro de medidas, o que já foi digitado passa para a linha de
  comando ("3" e depois ";" vira "3;"), porque é uma coordenada.

Não vão para a linha: barra de espaço (desloca a vista ou gira o elemento, como hoje),
Tab, Enter, Esc, setas, teclas com Ctrl ou Alt (atalhos dos menus). Campos dos painéis,
diálogos e da barra Opções continuam recebendo suas teclas normalmente.

No campo:
- **Enter** executa (§4); campo vazio = o mesmo Enter da vista (encerra a ferramenta ou
  repete a última, spec/ui 23 §3.2).
- **Esc** limpa o campo e devolve o foco à vista; com o campo já vazio, é o Esc da vista.
- **↑ / ↓** escolhem na lista de sugestões; sem sugestões, percorrem o que já foi
  digitado (histórico).
- Depois de executar, o foco volta à vista (o cursor continua desenhando).

## 4. O que o Enter faz
O texto é lido nesta ordem; a primeira que servir vale:

| Texto | Exemplo | Efeito |
|---|---|---|
| vazio | | Enter da vista |
| coordenada absoluta | `3,5;2` `-1;0` | ponto (x; y) do pavimento ativo, em metros, para a ferramenta |
| coordenada relativa | `@4;0` `@0;-2,5` | ponto deslocado (dx; dy) do ponto anterior |
| número | `2,40` | o mesmo que digitar no quadro: fixa o primeiro campo e confirma |
| apelido exato | `pd` | executa o comando do apelido |
| opção da ferramenta | `cop` | escolhe a opção cujo nome começa assim (§5) |
| busca | `parede curva` | executa o primeiro resultado da busca da paleta |
| nada serve | `xyz` | mensagem "comando não encontrado: xyz" (recusa) |

**Coordenadas.** Separador `;` entre x e y (a vírgula é o decimal do pt‑BR; ponto também
é aceito como decimal). Espaços são ignorados. O ponto digitado **não sofre atração** e
ignora a trava de eixo e os valores fixados no quadro: vale exatamente o que foi digitado.
Ele chega à ferramenta como um clique (`move` + `press`), então serve a toda ferramenta
que pede pontos: parede, viga, laje, linha, cota, mover, copiar etc. Na ferramenta
Selecionar, coordenada é recusada ("a ferramenta não espera um ponto").

**Ponto anterior** (para `@`): o ponto anterior da ferramenta em andamento (o mesmo da
trava de eixo, spec/ui 23 §3.1); se não houver, o último ponto informado por clique na
planta ou digitado na linha. Sem nenhum, `@` é recusado ("não há ponto anterior").

Coordenada polar (`@5<30`), cota z e coordenadas em outro sistema ficam para depois (§9).

**Sugestões.** Enquanto se digita (texto que não é coordenada nem número), uma lista de
até 8 linhas abre logo acima do campo, na mesma ordem que o Enter usa: apelido exato,
opções da ferramenta, comandos cujo apelido começa com o texto, resultados da busca. Cada
linha mostra o nome, o apelido e o menu de onde vem. A primeira já vem marcada; Enter
executa a marcada (as setas trocam); clique também executa.

## 5. Dica e opções da ferramenta
A dica é a de sempre (`Tool.hint`). As opções são as **escolhas** da barra Opções da
mesma ferramenta (botões de escolha e listas curtas): Copiar / Mover o original no
Deslocar paralela, Polígono / Retângulo na laje, Raio / Diâmetro na cota de raio,
Alinhada / Horizontal / Vertical na cota etc. Cada grupo aparece como palavras clicáveis
lado a lado, a atual em destaque. Clicar numa palavra ou digitar o começo do nome e dar
Enter escolhe; a barra Opções acompanha (são a mesma opção).

Grupos com até 6 escolhas aparecem inteiros; grupos maiores (em geral a camada, os objetos e
listas de tipos compridas) aparecem como **uma** palavra "Nome: atual ▾" que abre a lista num
menu e não respondem ao texto digitado, para não roubar a busca de comandos.
Números (raio, largura…) continuam na barra Opções; o número digitado na linha vai para o
quadro da ferramenta (§4).

## 6. Histórico
Cada Enter acrescenta uma linha ao histórico da sessão (até 100): o que foi digitado e o
resultado ("PD → Parede", "3;4 → ponto 3,00; 4,00", "xyz → comando não encontrado"). O
botão Histórico abre a lista acima da linha; clicar numa linha devolve o texto ao campo.
↑/↓ no campo vazio percorrem os textos digitados. O histórico não vai para o projeto.

## 7. Apelidos
Apelidos curtos, **próprios do BrasBim**, em pt‑BR. Regra de formação: 2 ou 3 letras que
aparecem **na ordem** no nome em português do comando (PD em **P**are**d**e, LJ em
**L**a**j**e). Não foram tirados de tabela de nenhum outro programa e não há apelido de
uma letra só. Maiúsculas e minúsculas tanto faz.

| Apelido | Comando | Apelido | Comando |
|---|---|---|---|
| SL | Selecionar | CT | Cota |
| PD | Parede | CTR | Cota de raio |
| PA | Parede em arco | CTA | Cota de ângulo |
| RP | Retângulo de paredes | NV | Nível |
| PT | Porta | TX | Texto |
| JN | Janela | RT | Rótulo |
| VA | Vão | LN | Linha |
| PI | Pilar | CV | Curva |
| VG | Viga | CI | Círculo |
| LJ | Laje | AC | Arco |
| CB | Cobertura | HC | Hachura |
| CLB | Claraboia | NT | Norte |
| ED | Escada | AT | Alteração |
| GC | Guarda-corpo | CE | Corte |
| OB | Objeto | FC | Fachada |
| EI | Eixos | DP | Deslocar paralela |
| TN | Terreno | AE | Aparar/estender |
| AM | Ambiente | CD | Concordar |
| MV | Mover | CPR | Copiar |
| GR | Girar | EP | Espelhar |
| DV | Dividir | EQ | Enquadrar tudo |

**Editar:** Editar > **Apelidos da linha de comando…** abre uma tabela com todos os
comandos (os da paleta) e o apelido de cada um; a célula do apelido é editável. Regras:
1 a 6 caracteres, letras e algarismos, começa por letra, sem repetir (sem distinção de
caixa). Vazio = sem apelido. "Restaurar padrões" volta à tabela acima. Os apelidos
ficam nas preferências do usuário (só as diferenças do padrão), não no projeto.

## 8. Arquitetura
- `ui/command_input.py`, **sem Qt**: `DEFAULT_ALIASES`, `validate_aliases`,
  `merge_aliases`/`diff_aliases`, `parse_point`, `interpret` (texto → `Entry`:
  vazio, ponto, número, opção, comando, desconhecido, erro), `candidates` (sugestões na
  ordem do Enter), `History`, `Option`.
- `ui/command_line.py`: a barra (`CommandLine`) e o diálogo de apelidos
  (`AliasesDialog`).
- `ui/command_palette.py`: `collect` (comandos dos menus e das ferramentas, com os
  alvos) e `execute`, usados pela paleta e pela linha.
- `OptionsBar` passa a guardar as escolhas que montou (`choices`: nome, rótulos, atual,
  escolher) para a linha mostrar; as opções da linha são um rótulo só, com links.
- `ToolInput` ganha `press_enter`, `press_escape` e `forward_text` (tecla de texto que a
  vista não usou); `PlanContext.last_point` guarda o último ponto clicado ou digitado.

## 9. Fica para depois
Coordenada polar (`@d<ângulo`) e cota z; comandos com argumentos ("pd 0,15");
apelidos para opções; espaço como Enter; histórico gravado entre sessões; busca também
em nomes de tipos, camadas e vistas.

## 10. Critérios de aceite (testes)
- **LC01** `parse_point`: "3,5;2", "3.5; 2", "-1;0", "@4;0" com ponto anterior;
  "@1;1" sem ponto anterior recusa; "3;" e "a;b" são erro; "3,5" não é coordenada.
- **LC02** `interpret` na ordem do §4: coordenada, número, apelido exato, opção, busca,
  desconhecido; apelido vence opção; caixa e acento não importam.
- **LC03** Apelidos padrão: únicos, 2–3 letras, letras na ordem no nome do comando; todo
  apelido aponta para um comando que existe na janela.
- **LC04** `validate_aliases` recusa repetido, vazio de letras, começar por algarismo,
  mais de 6 caracteres; `diff_aliases`/`merge_aliases` guardam só as diferenças.
- **LC05** `History`: limite, ↑/↓, não repete entrada igual seguida.
- **LC06** Na janela: letra digitada na planta vai para a linha; "PD" + Enter ativa a
  Parede; "3" com a parede aguardando abre o quadro e ";" passa "3;" para a linha.
- **LC07** Parede por coordenadas: "0;0", "@4;0", "@0;3" e Enter vazio → duas paredes no
  IFC com os pontos exatos (eixo de 4 m e de 3 m), sem atração.
- **LC08** A linha mostra a dica e as opções da ferramenta; digitar "mover" com o
  Deslocar paralela ativo escolhe "Mover o original" (e a barra Opções acompanha);
  clicar na palavra da opção também; a camada aparece como lista num menu.
- **LC09** Histórico registra entrada e resultado; texto desconhecido dá mensagem de
  recusa; Esc limpa e devolve o foco.
- **LC10** Exibir > Barras > Linha de comando esconde a barra; escondida, letras não
  são desviadas e a dica volta à barra de estado.

## 11. Fontes públicas
Pesquisa do projeto: `reports/Pesquisa Archicad Revit AutoCAD.md` (seção "A velocidade
nasce de digitar sem foco"); notas `interface_e_interacao.md` §1 (linha de comando do
Rhino 8, caixa de medidas do SketchUp) e `autocad.md` §1 (apelidos curtos, marcado "sem
fonte" lá; as fontes abaixo cobrem). Ajuda pública lida para este pacote (trechos de
busca, **conferir** na página):
- Teclado vai para a linha de comando sempre que a janela está ativa; autocompletar com
  busca aproximada; opções clicáveis; histórico: [McNeel, The Rhino window (Rhino 8)](https://docs.mcneel.com/rhino/8/help/en-us/user_interface/rhino_window.htm)
  (F374 no registro).
- Coordenadas absolutas e relativas digitadas: [SketchUp Help, Drawing basics](https://help.sketchup.com/en/sketchup/introducing-drawing-basics-and-concepts);
  relativa ao último ponto com `@`: [Autodesk, About Entering 2D Cartesian Coordinates (LT 2018)](https://help.autodesk.com/cloudhelp/2018/ENU/AutoCAD-LT/files/GUID-F64F8008-E1C0-49CC-A268-A6B8C6E9B566.htm).
- Apelidos de comando editáveis pelo usuário, só para iniciar o comando:
  [Autodesk, To Manage Command Aliases (2025)](https://help.autodesk.com/cloudhelp/2025/ENU/AutoCAD-Customization/files/GUID-D4CACED6-DFBA-43C3-BC42-8D980AB3AE75.htm);
  [Autodesk, Command Aliases, Shortcut Keys, and AutoCorrect (LT 2025)](https://help.autodesk.com/cloudhelp/2025/ENU/AutoCAD-LT-DidYouKnow/files/GUID-D2B4BF16-B1F7-4EF2-89AF-88ACE85FAD73.htm).
- Lista de sugestões enquanto se digita, ordenada por uso: [Autodesk, To Work With the Command Line Suggestion List (LT 2026)](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-LT/files/GUID-74478DCE-92D4-49B1-93E9-DCF09D57FA0D.htm);
  [Input Search Options Dialog Box (LT 2026)](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-LT/files/GUID-3179393F-958F-42EA-8A92-E9975A1D160B.htm).

O que veio das fontes é só a **função** (linha de comando com sugestões, apelidos
editáveis, coordenada relativa ao último ponto). A tabela de apelidos (§7), o separador
`;`, a ordem de leitura do §4, os textos e o desenho da barra são deste projeto; nenhum
apelido, nome de comando, texto ou arquivo de configuração de outro programa foi
copiado. O arquivo de apelidos de outros programas **não** foi aberto.

Nenhum material de `_restrito/` nem de `tools/` foi usado.

## 12. Pontos de revisão
(a) tabela de apelidos do §7 (trocar os que soarem estranhos);
(b) separador `;` nas coordenadas (alternativa: espaço);
(c) ordem do §4 (apelido exato vence opção; opção vence busca);
(d) algarismos vão para o quadro quando a ferramenta espera número (e para a linha só
com `;`/`@`);
(e) a dica sai da barra de estado quando a linha está visível;
(f) coordenada digitada sem atração;
(g) local: sob as vistas, em toda a largura (alternativa: barra móvel do Qt).
