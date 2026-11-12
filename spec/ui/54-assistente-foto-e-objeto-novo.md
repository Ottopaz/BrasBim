---
documento: Assistente — anexar imagem e criar objeto a partir dela (etapa 1)
requisito: pedido do revisor em 2026-11-12 ("anexar fotos na IA dentro do BrasBim: enviar a foto de um fogão e pedir à IA para criar o objeto conforme a foto e adicionar no projeto")
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-11-12
status: aprovado (implementado; "ok, podemos prosseguir", revisor em 2026-11-12)
revisor: OTTO
versão: 0.0.2
---

# Assistente: anexar imagem e criar objeto a partir dela

## 1. Propósito
Hoje o Assistente (spec/ui 16) recebe só texto e só insere objetos que já estão na
biblioteca. O revisor quer mandar a **foto** de uma peça (um fogão, por exemplo) com a
especificação dela e receber no projeto um **objeto paramétrico** novo, parecido com a
foto e nas medidas certas.

O trabalho foi dividido em duas etapas, para testar cedo:

- **Etapa 1 (esta spec):** anexar imagens ao pedido; a IA cria a definição do objeto,
  olha uma prévia dele, compara com a foto, corrige e insere. As medidas vêm do que o
  usuário escreveu ou de medidas típicas.
- **Etapa 2 (spec futura):** a IA pesquisa na web a ficha do fabricante (ligado pelo
  usuário). Fica fora daqui porque muda a regra de segurança do conector (§3.2 da
  spec/ui 16: nenhuma ferramenta própria).

O que esperar: um **objeto BIM simplificado**, feito das peças do objeto paramétrico
(caixa, cilindro, extrusão, revolução; `spec/elementos/objeto-parametrico.md` §3.3).
Peças de linhas retas (fogão, geladeira, armário, mesa) saem bem; formas orgânicas
(poltrona curva, torneira) saem reconhecíveis, sem os detalhes. Não é cópia fiel da
foto, não tem textura e não usa malha.

## 2. Anexar imagem no painel

### 2.1 Como anexar
- Botão **Anexar imagem** (ícone próprio `image`, só ícone, com dica), à esquerda de
  Nova conversa. Abre o seletor de arquivos: PNG, JPEG e WebP.
- **Colar** (Ctrl+V) no campo do pedido, com uma imagem na área de transferência.
- **Arrastar** arquivos de imagem para o painel.
- Até **4 imagens** por pedido. A quinta é recusada com mensagem ("no máximo 4 imagens
  por pedido"). Arquivo que não é imagem, ou que não abre, é recusado com o nome dele.

### 2.2 Antes de enviar
- As imagens anexadas aparecem numa faixa entre o andamento e o campo do pedido:
  miniatura de 48 px, com um × para tirar. Sem anexos, a faixa não aparece.
- Cada imagem é reduzida para caber em **1568 px** no lado maior e regravada (JPEG de
  qualidade 85; PNG se tiver transparência). Assim uma foto de celular de 12 MP não
  estoura o tamanho do pedido nem gasta a cota do usuário à toa.
- Enviar aceita texto, imagem ou os dois. Só imagem, sem texto: o pedido vai com o
  texto "Veja a imagem anexada." e a IA pergunta o que fazer com ela.

### 2.3 Envio
- O conector passa a mandar o pedido como **mensagem estruturada**
  (`--input-format stream-json`): as imagens em base64, depois a linha de contexto
  `[BrasBim]` e o texto do usuário. Vale para todo pedido, com ou sem imagem (um caminho
  só). O resto do conector fica igual: `--tools ""`, só as ferramentas do BrasBim.
- No andamento, o pedido aparece com o texto e as miniaturas.
- As imagens **não são gravadas no IFC** nem em disco: ficam na memória do painel até o
  envio. A conversa guarda as imagens do lado da IA: "agora faça o da segunda foto"
  funciona enquanto a conversa durar; Nova conversa as esquece.
- Viabilidade conferida em 2026-11-12 com Claude Code 2.1.322: imagem PNG enviada por
  `stream-json` com `--tools ""`, descrita corretamente na resposta.

### 2.4 Privacidade
A imagem vai para o fornecedor da IA, como já vão o pedido e o que as ferramentas
devolvem (spec/ui 16 §3.3). A dica do botão diz isso: "Anexar imagem (é enviada à IA
junto com o pedido)".

## 3. Ferramentas novas

### 3.1 `create_object`
Cria no projeto a definição de um objeto e um tipo dela; com `at`, insere uma
ocorrência.

| Argumento | O que é |
|---|---|
| `name` | Nome do objeto ("Fogão de piso 5 bocas") |
| `category` | `furniture`, `sanitary`, `appliance`, `vegetation` ou `proxy` |
| `predefined_type` | Um dos valores do IFC para a categoria (objeto‑parametrico §2.1); sem ele, `USERDEFINED` |
| `params` | Lista de parâmetros: `name`, `label`, `kind`, `level`, `value` ou `formula`, `min`, `max`, `options` |
| `pieces` | Lista de peças no formato da definição (§3.3 do objeto paramétrico): `box`, `cylinder`, `extrusion`, `revolution`, com medidas em número ou fórmula, `role`, `material`, `visible`, `repeat` |
| `symbol` | Opcional: símbolo 2D desenhado; sem ele, automático (contorno das peças) |
| `type_name` | Nome do tipo; sem ele, o nome do objeto |
| `description` | Texto livre: de onde vieram as medidas ("medidas informadas pelo usuário", "medidas típicas"), marca e modelo se o usuário deu |
| `hosting`, `elevation` | Como na definição (solto ou preso à parede; altura do ponto de inserção) |
| `at`, `rotation`, `storey` | Opcionais: insere uma ocorrência, como `insert_object` |

- A definição passa pela **mesma validação do editor de objetos**
  (`definition.problems`). Cada problema volta à IA como erro, com o lugar ("peça 3
  'Puxador', campo altura: …"), para ela corrigir e tentar de novo. Nada entra no
  histórico numa recusa.
- Nome de objeto ou de tipo repetido no projeto ganha sufixo (" (2)"), como no editor.
- Peças do tipo `object` (aninhado) não são aceitas nesta etapa.
- Limite de **60 peças** (contando as repetições como uma): acima disso, recusa
  pedindo para simplificar.
- Devolve: nome do tipo criado, id do objeto, a caixa que o envolve (largura ×
  profundidade × altura, em metros) e, se inseriu, o id da ocorrência.
- Usa `objects.commands.create_type` e `create_object`: o resultado é igual ao de um
  objeto feito no editor (classe IFC da categoria, Pset `BrasBim_DefinicaoObjeto`, tipo
  ligado por `IfcRelDefinesByType`), e o usuário pode abri‑lo no editor e salvá‑lo na
  biblioteca pelos comandos de sempre.

### 3.2 `edit_object_definition`
Troca a definição de um objeto do projeto (pelo nome do objeto ou do tipo) por outra,
com os mesmos campos do `create_object`. Serve para a IA **corrigir** o que criou depois
de olhar a prévia, sem deixar objetos de rascunho para trás. As ocorrências são refeitas
(`objects.commands.edit_definition`); recusa se alguma ocorrência não aceitar os valores
novos, como no editor.

### 3.3 `view_object`
Imagem PNG de um tipo de objeto (pelo nome do tipo ou do objeto), para a IA comparar
com a foto. Vale para os do projeto e para os da biblioteca, que são mostrados **sem
ser carregados** (no teste de 2026-11-12 a IA carregou um da biblioteca só para olhar e
o tipo sobrou no projeto):

- Quatro vistas numa imagem só, com o nome embaixo de cada uma: **frente**, **lado**,
  **topo** e **perspectiva**, no desenho sombreado da prévia do editor
  (`object_preview.paint_3d`), com o contorno de cada peça marcado (peças do mesmo
  material não se fundem na vista de frente).
- Junto, em texto, a caixa que envolve (largura × profundidade × altura).
- Não altera o modelo. Só no aplicativo (precisa do Qt), como `view_plan`.

## 4. Instruções para a IA (acréscimo ao §4.1 da spec/ui 16)
- Com uma imagem de uma peça: primeiro `list_objects`. Se a biblioteca já tem um objeto
  que serve (ajustando parâmetros), usar esse. Só criar um novo se não houver.
- **Medidas:** usar as que o usuário escreveu. Na falta, medidas típicas da peça. A foto
  não tem escala: não medir pela imagem. Dizer na resposta e no `description` de onde
  veio cada medida, e pedir ao usuário para conferir as que foram supostas.
- **Sistema do objeto:** origem no ponto de inserção, x para a direita, y para trás (a
  frente olha para −y), z para cima; o objeto se apoia em z = 0.
- **Parâmetros:** largura, profundidade e altura como parâmetros de tipo, com as peças
  em fórmulas deles, para o usuário redimensionar depois. Poucos parâmetros.
- **Peças:** começar pelo volume principal e acrescentar o que identifica a peça (tampo,
  bocas, porta do forno, puxador, pés). Não modelar parafuso, logotipo nem textura.
- **Conferir:** depois de criar, chamar `view_object`, comparar com a foto e corrigir
  com `edit_object_definition` (no máximo três rodadas). Inserir no projeto só depois.
- **Marca:** não escrever marca nem logotipo na geometria. Marca e modelo, se o usuário
  informou, vão só no `description`.
- Sem posição pedida, inserir perto da seleção ou num lugar livre do pavimento ativo e
  dizer onde ficou.

## 5. Interface
- Faixa de anexos e botão Anexar imagem (§2). O exemplo do campo do pedido ganha uma
  segunda linha: "Ou anexe a foto de um móvel ou aparelho, diga as medidas e peça para
  criar o objeto."
- Andamento: "Criando objeto", "Corrigindo objeto", "Olhando o objeto".
- Como hoje, o pedido inteiro vira um passo de desfazer, e ao fim fica selecionado o que
  foi criado.

## 6. Limpeza de sala (clean‑room)
- A IA modela **a partir da foto do usuário e de medidas**, com as peças do BrasBim.
  Não importa nem copia blocos, famílias ou desenhos CAD de fabricantes ou de outros
  programas.
- Medidas de catálogo são fatos e podem ser usadas; desenhos, logotipos e nomes de
  modelo não entram na geometria.
- A responsabilidade pela foto enviada é do usuário (ele escolhe o que anexa).

## 7. Fora do escopo
- Pesquisa na web pela IA (etapa 2).
- Reconstrução por malha, fotogrametria, textura a partir da foto.
- Medir pela foto (referência de escala na imagem).
- Salvar automaticamente na biblioteca (o usuário salva pelo comando que já existe).
- Imagem como planta de base para a IA desenhar paredes por cima ("desenhe esta planta").
  É um uso provável do anexo e vai funcionar em parte só com esta etapa, mas sem
  ferramenta própria nem garantia de escala; merece spec própria.
- Outros conectores (o anexo depende de o conector aceitar imagem).

## 8. Critérios de aceite (testes)
| Teste | Verifica |
|---|---|
| AF01 | Anexar por arquivo, colar e arrastar; miniatura e ×; quinta imagem e arquivo inválido recusados com mensagem |
| AF02 | Imagem de 4000 × 3000 sai com 1568 px no lado maior; PNG com transparência continua PNG |
| AF03 | O conector é chamado com `--input-format stream-json` e ainda com `--tools ""`; a mensagem tem as imagens, a linha `[BrasBim]` e o texto; sem imagem, só texto; só imagem, texto padrão |
| AF04 | `create_object` com caixa + cilindros repetidos: o IFC tem o tipo da classe da categoria, o Pset da definição e, com `at`, a ocorrência ligada por `IfcRelDefinesByType` no pavimento; a caixa devolvida confere |
| AF05 | Definição com erro (fórmula com parâmetro que não existe, altura zero): erro com o lugar, nada no histórico; mais de 60 peças e peça aninhada recusadas |
| AF06 | `edit_object_definition` muda as peças e refaz a ocorrência, mantendo o `GlobalId` dela; nome que não existe é recusado |
| AF07 | `view_object` devolve PNG e a caixa em texto; não altera o modelo |
| AF08 | O pedido com `create_object` + `edit_object_definition` + inserção vira um passo de desfazer |

Teste de ponta a ponta feito em 2026-11-12 com Claude Code 2.1.322, pelo painel (sem
janela): desenho de um criado-mudo de 2 gavetas, puxadores redondos e 4 pés, com "50 cm
de largura, 40 de profundidade, 60 de altura total, pés de 12 cm". Em 36 s e 10
chamadas a IA viu que o da biblioteca não servia, criou "Criado-mudo com pés 0,50 × 0,40
× 0,60" (10 peças; largura, profundidade, altura e altura dos pés como parâmetros; altura
da gaveta por fórmula), olhou a prévia, inseriu e listou as medidas informadas e as
supostas. Um passo de desfazer.

Teste manual que falta, com o revisor: foto de verdade de um fogão de piso com "76 × 60
× 85 cm, 5 bocas, inox"; conferir a prévia e o objeto na planta e no 3D.

## 9. Fontes
- `spec/ui/16-assistente.md` (conector, segurança, ferramentas) e
  `spec/elementos/objeto-parametrico.md` §2, §3 e §5.5 (definição, peças, ferramentas de
  objeto do Assistente).
- Ajuda pública do Claude Code, modo não interativo (`claude --help`, opções
  `--input-format` e `--output-format stream-json`), e o teste de 2026-11-12 (§2.3).
- Pedido do revisor em 2026-11-12 (descrição de função).
