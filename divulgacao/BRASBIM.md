# BrasBim — descrição completa para conteúdos de divulgação

> Documento de referência para produzir textos, posts, roteiros e apresentações sobre o
> BrasBim. Estado em **29/10/2026**. Tudo o que está em "O que já funciona" existe no
> código e tem teste automático; o que está em "Em desenvolvimento" e "No roteiro" **não
> deve ser anunciado como pronto**. Ao fim há regras de comunicação (§12) e um glossário
> (§13): siga‑os.

---

## 1. Em uma frase

**O BrasBim é um software BIM de arquitetura, gratuito e de código aberto, feito no Brasil
para o projetista brasileiro, que usa o formato aberto IFC como arquivo nativo.**

### Variações curtas (para títulos, bio, chamadas)
- "BIM aberto, em português, do jeito que o Brasil projeta."
- "Projete em BIM sem pagar licença e sem ficar preso a um formato fechado."
- "Do modelo 3D à prancha da prefeitura, num software livre e brasileiro."
- "Seu projeto é seu: o arquivo do BrasBim é IFC, o padrão aberto internacional."

### Parágrafo de apresentação (≈80 palavras)
O BrasBim é um software de modelagem da informação da construção (BIM) para arquitetos,
engenheiros e estudantes. Você desenha paredes, lajes, portas, janelas, coberturas,
escadas e ambientes num modelo 3D, e o programa gera plantas, cortes, fachadas, tabelas e
pranchas em PDF. O arquivo do projeto é IFC 4.3, o formato aberto da buildingSMART (ISO
16739), e não um formato proprietário. É gratuito, de código aberto, em português, e
pensado para as normas e a prática brasileiras, incluindo o projeto legal para a prefeitura.

---

## 2. O problema que o BrasBim resolve

1. **Custo.** As licenças de BIM comerciais custam caro, todo ano, em dólar ou euro. Para
   o escritório pequeno, o profissional autônomo e o estudante, isso trava a adoção.
2. **Aprisionamento.** Nos programas comerciais, o projeto fica num formato fechado. Para
   abrir o próprio trabalho daqui a dez anos, é preciso continuar pagando. O IFC existe para
   troca, mas costuma ser uma exportação secundária, com perdas.
3. **Distância da realidade brasileira.** Os programas são pensados para outros mercados.
   O que a prefeitura brasileira pede (cores por situação da obra, quadro de áreas com taxa
   de ocupação e coeficiente de aproveitamento, memória de cálculo) costuma sair de uma
   tabela exportada para o Excel e preenchida à mão.
4. **Exigência pública de BIM.** A Estratégia BIM BR e as compras públicas cada vez mais
   pedem entregas em IFC. Quem trabalha com IFC nativo já entrega no formato pedido.

---

## 3. Para quem é

| Público | O que ganha |
|---|---|
| **Arquitetos e escritórios pequenos e médios** | BIM completo sem custo de licença, com documentação no padrão brasileiro e o projeto legal para a prefeitura |
| **Engenheiros civis e projetistas** | Modelo IFC aberto, que conversa com programas de estrutura e instalações; estrutura básica (pilares, vigas, lajes) |
| **Estudantes e professores** | Ferramenta gratuita e em português para aprender BIM e IFC, sem licença educacional que vence |
| **Órgãos públicos e prefeituras** | Software livre (auditável, sem custo por estação) que gera e lê IFC, o formato das contratações públicas |
| **Desenvolvedores e pesquisadores** | Núcleo BIM em Python, sem interface, testável e reaproveitável (LGPL); integração com IA por protocolo aberto (MCP) |

---

## 4. Os pilares (diferenciais)

### 4.1 IFC nativo: o arquivo é seu
- O arquivo do projeto **é** um `.ifc` (IFC 4.3, ISO 16739‑1). Não há formato próprio
  escondido e "exportar IFC" não é uma etapa à parte, com perdas.
- Qualquer programa que lê IFC abre o projeto do BrasBim, hoje ou daqui a 20 anos.
- Os elementos usam as classes e propriedades do IFC: `IfcWall`, `IfcDoor`, `IfcSpace`,
  conjuntos de propriedades padrão (`Pset_WallCommon` e outros), quantidades
  (`Qto_*BaseQuantities`), situação da obra no campo `Status`.
- Cada elemento tem identidade estável (`GlobalId`) ao salvar, reabrir e trocar arquivos.

### 4.2 Livre e gratuito
- Código aberto: núcleo sob **LGPL‑3.0‑or‑later**, aplicativo sob **GPL‑3.0‑or‑later**,
  biblioteca de objetos sob **CC BY 4.0**.
- Sem licença, sem assinatura, sem limite de instalações. O código pode ser lido,
  estudado, auditado e melhorado por qualquer pessoa.
- Código no GitHub: <https://github.com/Ottopaz/BrasBim>.

### 4.3 Feito para o Brasil
- Interface, documentação e biblioteca em **português do Brasil**.
- Documentação orientada pela **NBR 6492** (projetos arquitetônicos), pela **NBR 16752**
  (folhas de desenho: formatos A0–A4, margens, dobra, legenda) e pelas normas de linhas de
  desenho técnico.
- **Projeto legal (projeto para licenciamentos)**: situação de cada elemento (a
  construir, existente, a demolir, a regularizar, a transformar, temporário) com as cores
  e hachuras de cada prefeitura, **perfil municipal** e **quadro de áreas** automático,
  com memória de cálculo (§5.9).
- Unidades e formatos brasileiros: metro, vírgula decimal, escalas usuais (1:50, 1:100,
  1:200…), CSV com ponto e vírgula, que abre direto no Excel em português.

### 4.4 IA no seu computador, por protocolo aberto
- O painel **Assistente** recebe um pedido em português ("casa térrea de 3 quartos, uns
  100 m²") e uma IA **instalada pelo usuário** desenha no modelo aberto, enquanto ele vê a
  planta e o 3D se formarem.
- O BrasBim não embute nem revende IA: ele oferece **ferramentas** por um protocolo
  aberto (MCP, Model Context Protocol), que qualquer IA compatível pode usar.
- O resultado é um estudo inicial **editável**, feito com os mesmos elementos do desenho
  manual, e desfazível num passo só.
- Situação: **protótipo** em avaliação (ver §6).

### 4.5 Trabalho em equipe na rede do escritório
- **Projeto compartilhado** (menu Equipe): um computador compartilha o projeto e os outros
  entram pela rede local, sem servidor nem nuvem para instalar. Cada alteração chega a
  todos na hora.
- Para duas pessoas não mexerem na mesma coisa, o elemento fica **reservado** para quem
  começou a editá‑lo. Dá para pedir a liberação a quem reservou.

### 4.6 Sem ficar preso ao DWG, mas falando com ele
- **Importa DWG e DXF** como referência (levantamento topográfico, planta de outro
  escritório) para desenhar por cima e criar o terreno a partir das curvas de nível.
- **Exporta DWG e DXF** de plantas, cortes, fachadas, vistas e pranchas, com as camadas
  do BrasBim e em centímetros.
- O DWG passa por um conversor livre (GNU LibreDWG), que vem junto. Nada de engenharia
  reversa: o BrasBim não abre os formatos fechados por conta própria.

### 4.7 Feito com método (confiança)
- **Cada recurso tem teste automático** que confere o IFC gerado: são **845 testes**
  passando hoje.
- Cada recurso nasce de uma **especificação escrita e revisada** antes do código. Há mais
  de 40 especificações públicas no repositório.
- Desenvolvimento **clean‑room**: nenhum código, texto, ícone ou nome de comando de
  software proprietário é copiado, e nada é obtido por engenharia reversa. A
  especificação usa só fontes públicas (normas, documentação do IFC, ajudas públicas
  consultadas apenas para entender *que* uma função existe), e cada spec cita as suas.
- Ícones, nomes de comandos e telas são próprios do BrasBim.

---

## 5. O que já funciona

> Tudo abaixo existe hoje e tem testes. A versão ainda é de desenvolvimento (§7).

### 5.1 Modelagem
- **Paredes**: retas, em arco, retangulares (quatro de uma vez); tipos com composição em
  camadas (ex.: reboco + bloco + reboco); junções em L, T e X automáticas e editáveis;
  unir, desfazer junção, dividir, espelhar; topo plano, inclinado, em duas águas ou livre;
  parede tombada (inclinada).
- **Portas e janelas**: tipos com código curto (P1, J2…), largura, altura, peitoril, lado
  e sentido de abertura, folhas; abrem o vão na parede sozinhas; etiqueta na planta.
- **Lajes**: contorno poligonal, espessura em camadas, aberturas, laje a partir do ambiente.
- **Pilares e vigas**: seções e perfis, ligados aos pavimentos.
- **Coberturas**: plana, uma água, duas águas, quatro águas, com beirais; claraboias.
- **Escadas e guarda‑corpos.**
- **Terreno**: por pontos ou pelas **curvas de nível** pegas de um desenho importado.
- **Ambientes** (`IfcSpace`): criados por contorno ou detectados pelas paredes em volta,
  com nome, número, área e perímetro, e etiqueta automática na planta.
- **Eixos de projeto** nomeados (A, B, C… / 1, 2, 3…); vãos em parede e em laje.
- **Pavimentos**: criar, renomear, cota, plano de corte e escala de cada um.
- **Situação na obra** de cada elemento (a construir, existente, a demolir…), com botões de
  um clique.

### 5.2 Objetos paramétricos e biblioteca
- **Objetos** reutilizáveis (cama, bacia sanitária, geladeira, árvore…) descritos uma vez
  em função de parâmetros: tipos, ocorrências, fórmulas entre parâmetros, listas de
  escolha, partes que aparecem conforme o valor, objetos dentro de objetos e objetos
  presos à parede (com vão opcional).
- **Editor por formulário com prévia** em 3D e 2D.
- **Biblioteca inicial** de mobiliário, louças e metais, eletrodomésticos e vegetação,
  em formato aberto (CC BY 4.0).

### 5.3 Desenho de precisão
- Grade, atração a pontos (extremidade, meio, interseção, perpendicular, centro…), linhas
  guia, travas ortogonais e angulares.
- **Quadro de medidas junto ao cursor**: Tab para digitar comprimento, ângulo, largura,
  distância.
- **Linha de comando** com comandos e apelidos em português, coordenadas (x;y) e
  histórico.
- Mover, copiar, girar, espelhar, esticar por área de seleção; desfazer e refazer
  ilimitados.
- Seleção por clique, janela e laço; selecionar semelhantes; ocultar e mostrar.

### 5.4 Planta e 3D
- Planta gerada do modelo, com o que está cortado, em projeção e acima do plano de corte;
  **nível de detalhe** simplificado ou por camadas de material.
- Vista 3D com órbita, seleção, **edição direta no 3D** (alças de parede, as mesmas
  ferramentas da planta), vistas padrão e controle de orientação no canto.
- Planta e 3D em abas ou lado a lado; vistas salvas; giro da vista da planta.
- **Camadas** de organização com combinações salvas, travamento e visibilidade.
- **Tabela de penas**: espessuras e cores de impressão por categoria.

### 5.5 Desenho 2D e anotação
- Linhas, arcos, círculos, polilinhas, curvas, hachuras e textos.
- Cotas lineares que acompanham as paredes, cotas de ângulo e raio, cotas de nível e
  marcas de nível.
- Símbolos de corte, fachada e norte.

### 5.6 Cortes, fachadas e pranchas
- **Cortes e fachadas** gerados do 3D e atualizados com o modelo.
- **Pranchas** A0–A4, vertical ou horizontal, com várias vistas, margens, dobra e
  **folhas mestras** (carimbo/legenda reutilizável).
- **Exportação PDF vetorial** (uma ou várias pranchas) e impressão.
- **Exportar DWG/DXF** de vistas e pranchas (§4.6).

### 5.7 Quantitativos e tabelas
- Tabelas configuráveis por tipo, com filtros, agrupamento e totais; modelos prontos
  (esquadrias, áreas, paredes por tipo, estrutura).
- Quantidades no padrão IFC (comprimento, área, volume, contagem).
- Exportar tabela para **CSV e XLSX**; clicar numa linha mostra o elemento na planta.

### 5.8 Interoperabilidade
- Arquivo nativo **IFC 4.3**.
- **Importar DXF e DWG** como referência; **exportar DXF e DWG**.
- PDF vetorial; CSV e XLSX.

### 5.9 Projeto legal (prefeitura) — etapas 1 a 3 de 5
- **Situação** de cada elemento e anotação, gravada no IFC (`Status`) e num conjunto de
  propriedades próprio, para os casos que o IFC não prevê (a regularizar, a transformar).
- **Vista por situação**, com as cores e hachuras do **perfil municipal**; impressão em
  preto com hachura.
- **Perfil municipal**: arquivo aberto com cores, escalas, regras do quadro de áreas,
  campos do selo e notas obrigatórias, cada um com a fonte da prefeitura. O perfil
  escolhido vai **dentro do IFC**, para o projeto abrir igual em outra máquina. Perfis que
  vêm prontos: **Genérico, Araras/SP, Jacareí/SP, São Paulo/SP e Curitiba/PR**.
- **Quadro de áreas automático**: áreas por pavimento e por situação, construída,
  computável e não computável (com o motivo), descoberta, permeável, área do terreno
  (levantada e de escritura), projeção e área livre; índices **TO**, **CA** e **taxa de
  permeabilidade** comparados com os limites do lote; **memória de cálculo** (cada número
  abre os ambientes e a conta); exporta para CSV e XLSX.

### 5.10 Equipe e IA
- **Projeto compartilhado** na rede local, com reserva de elementos e pedido de liberação.
- **Assistente** com IA por MCP (protótipo).

### 5.11 Segurança do trabalho
- **Salvamento automático** e recuperação depois de uma falha.
- Diário da sessão para relatar problemas.

---

## 6. Em desenvolvimento (não anunciar como pronto)

- **Projeto legal, etapas 4 e 5**: peças na prancha (legenda e selo da prefeitura,
  quadro de esquadrias, notas obrigatórias, limite de tamanho do PDF) e **memorial
  descritivo**; planta simplificada (sem compartimentação), como pede São Paulo.
- **Operações com sólidos** (subtrair, unir, interceptar) e **perfil complexo**.
- **Elevação interna, detalhe ampliado, câmera/perspectiva na prancha**, polilinha e
  figuras de desenho (especificações aprovadas, a implementar).
- **Assistente**: o protótipo funciona e está em revisão; outros conectores de IA (modelo
  local, chave de API) e verificação por norma ficam para depois.

## 7. Maturidade (dizer com honestidade)

- **Versão 0.0.1, em desenvolvimento ativo.** Ainda não há versão estável para download
  público. Quem testa hoje usa uma pasta portátil (roda de um pendrive) ou instala a partir
  do código.
- Desenvolvido e testado no **Windows**. A tecnologia (Python e Qt) é multiplataforma e o
  objetivo é Windows, Linux e macOS, mas Linux e macOS ainda não foram validados.
- Cresce em ciclos curtos: especificação → revisão → implementação com testes → uso
  real → ajustes, guiado pelo retorno de quem usa.

## 8. No roteiro (visão, sem data)

- Georreferenciamento (SIRGAS 2000 / UTM).
- Verificações de **acessibilidade (NBR 9050)**: vãos, rampas, sanitários, áreas de giro.
- Classificação pela **NBR 15965**; dados de desempenho (**NBR 15575**).
- Parâmetros do código de obras por município (recuos, TO, CA) verificados no modelo.
- Orçamento preliminar com **SINAPI**.
- **BCF** (apontamentos de revisão), **IDS** (validação de requisitos de informação),
  comparação de versões do IFC, detecção de interferências.
- Modelos federados (IFC de estrutura e instalações como referência).
- Exportar IFC 2x3 e IFC 4; exportar glTF/OBJ para renderização.
- Revestimentos, rampas, fundações, pele de vidro, forma livre.
- API Python pública para scripts e plugins.

**Fora do escopo**: abrir ou gravar formatos proprietários de outros programas BIM
(`.pln`, `.rvt` e outros); renderização fotorrealista própria; cálculo estrutural,
energético ou luminotécnico (esses ficam com outros programas, via IFC).

---

## 9. Como funciona por dentro (para público técnico)

- **Linguagem**: Python 3.12+.
- **Modelo em memória**: IFC, pelo **IfcOpenShell** (biblioteca livre de referência para
  IFC). Toda edição é uma transação serializável, com desfazer/refazer e base para a
  colaboração.
- **Geometria**: OpenCascade (via IfcOpenShell); booleanos 2D com Clipper2; Shapely.
- **Interface**: Qt 6 (PySide6), com viewport 3D em OpenGL.
- **Núcleo separado da interface**: `brasbim/core` não depende de Qt, pode ser testado
  sozinho e reaproveitado em scripts, servidores e outras ferramentas.
- **Testes**: pytest, um teste por recurso, conferindo o IFC gerado.
- **DWG**: GNU LibreDWG (livre), como conversor externo.
- **Contribuição**: especificação aprovada antes do código, só fontes públicas, commits
  assinados (DCO, `git commit -s`).

---

## 10. Identidade

- **Nome**: BrasBim (B maiúsculo, "bim" minúsculo, uma palavra). Não escrever "BrasBIM",
  "Bras BIM" ou "Brasbim".
- **Logo**: arquivo `brasbim/ui/logo/logo.png`; símbolo em `brasbim/ui/logo/simbolo-*.png`.
- **Cores**: roxo jabuticaba `#6B1F5A` (destaque, cor da marca); moldura cinza levemente
  arroxeada `#E6E3E6`; folha quase branca `#F8F7F8`; grafite `#26222A` no texto. Tema
  claro.
- **Tipografia**: Archivo.
- **Tom de voz**: direto, técnico sem ser pedante, brasileiro, sem anglicismos
  desnecessários. Fala de igual para igual com o arquiteto e o engenheiro. Prefere mostrar
  o que o programa faz a usar adjetivos. Nada de "revolucionário", "o melhor" ou "mata o
  concorrente".

## 11. Mensagens‑chave e perguntas frequentes

**Mensagens‑chave**
1. *Seu projeto é seu.* O arquivo é IFC aberto, e não refém de uma licença.
2. *BIM sem licença.* Gratuito para sempre, código aberto.
3. *Feito para o Brasil.* Em português, nas normas brasileiras, com o projeto legal da
   prefeitura.
4. *Feito com cuidado.* Especificado, testado, desenvolvido às claras.

**Perguntas frequentes**
- *É de graça mesmo?* Sim. É software livre: sem licença, sem assinatura, sem limite.
- *Abre arquivos de outros programas BIM?* Abre e grava IFC, o formato aberto que
  todos os programas BIM leem e exportam. Formatos fechados de outros programas, não.
- *Abre DWG?* Importa DWG e DXF como referência e exporta DWG e DXF, por um conversor
  livre que vem junto.
- *Já dá para usar num projeto real?* Está em desenvolvimento, versão 0.0.1. Já modela e
  documenta uma casa (plantas, cortes, fachadas, tabelas, pranchas em PDF, quadro de
  áreas), mas ainda não tem versão estável. É uma boa hora para testar e dar retorno.
- *Funciona no Mac e no Linux?* O objetivo é rodar nos três sistemas. Hoje é testado no
  Windows.
- *A IA vem junto? Tem custo?* Não vem junto. O BrasBim oferece as ferramentas por um
  protocolo aberto (MCP); o usuário conecta a IA que já tem.
- *Como contribuir?* Pelo GitHub: testando e relatando problemas, sugerindo recursos,
  escrevendo especificações, código ou objetos para a biblioteca.

---

## 12. Regras para quem escreve sobre o BrasBim

1. **Não anunciar como pronto** o que está em §6 ou §8. Na dúvida, "em desenvolvimento"
   ou "no roteiro".
2. **Não comparar com nomes de produtos comerciais** em peças de divulgação, não dizer que
   o BrasBim é "o [produto X] gratuito" ou "um clone de", e não usar telas, ícones ou
   marcas de outros programas. O BrasBim tem desenho próprio. Para a categoria, use
   "programas BIM comerciais" ou "software proprietário".
3. **Normas**: dizer que a documentação "segue" ou "é orientada por" NBR 6492 e NBR
   16752. Nunca dizer "certificado pela ABNT" ou "aprovado pela prefeitura". O BrasBim
   ajuda a montar as peças, e a aprovação é da prefeitura.
4. **Perfis municipais**: citar só as cidades com perfil pronto (Araras/SP, Jacareí/SP, São
   Paulo/SP, Curitiba/PR, além do Genérico). Para as outras, "o perfil é um arquivo
   aberto, fácil de criar".
5. **IA**: deixar claro que a IA é do usuário, conectada por protocolo aberto, e que o
   recurso é um protótipo. Não prometer "projeto completo feito por IA".
6. **Números**: "845 testes automáticos" e "mais de 40 especificações" valem para
   29/10/2026. Conferir antes de reutilizar.
7. **Formatos**: o arquivo nativo é IFC 4.3. Não dizer que o BrasBim abre `.pln`, `.rvt`
   ou outros formatos fechados de BIM.
8. **Licenças**: núcleo LGPL‑3.0, aplicativo GPL‑3.0, biblioteca CC BY 4.0. Não dizer
   "domínio público" nem "MIT".

## 13. Glossário (vocabulário do BrasBim)

| Termo | Significado |
|---|---|
| **IFC** | Industry Foundation Classes: formato aberto e internacional (ISO 16739) para modelos BIM, mantido pela buildingSMART. No BrasBim, é o próprio arquivo do projeto |
| **Pavimentos** | Painel com os andares do projeto (nome, cota, plano de corte, escala) |
| **Navegador** | Painel com cortes e fachadas, vistas salvas, pranchas, folhas mestras, tabelas e objetos |
| **Propriedades** | Painel que mostra e edita o que está selecionado |
| **Barra da vista** | Faixa sob a planta: zoom, giro, escala, camadas, detalhe, penas, situação |
| **Linha de comando** | Campo para digitar comandos, apelidos e coordenadas |
| **Objeto** | Peça paramétrica reutilizável (mobiliário, louças, eletrodomésticos, vegetação) |
| **Tipo** | Conjunto de valores compartilhado por vários elementos (ex.: "Alvenaria 14"); mudar o tipo muda todos |
| **Situação** | Condição do elemento na obra: a construir, existente, a demolir, a regularizar, a transformar, temporário |
| **Perfil municipal** | Arquivo com as regras de apresentação de uma prefeitura (cores, escalas, quadro de áreas, selo, notas) |
| **Quadro de áreas** | Tabela automática de áreas e índices urbanísticos (TO, CA, permeabilidade), com memória de cálculo |
| **Folha mestra** | Moldura e carimbo reutilizáveis das pranchas |
| **Tabela de penas** | Espessuras e cores de impressão por categoria de elemento |
| **Camadas** | Organização para ligar, desligar e travar grupos de elementos; combinações salvas |
| **Projeto compartilhado** | Edição simultânea pela rede local, com reserva de elementos (menu Equipe) |
| **Assistente** | Painel em que uma IA do usuário desenha no modelo a partir de um pedido em texto |
| **Clean‑room** | Método de desenvolvimento sem copiar nem fazer engenharia reversa de software proprietário |
