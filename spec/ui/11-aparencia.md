---
documento: Interface — aparência (tema, cores, fonte, espaçamento, planta e 3D)
requisito: RF-UI-01
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-15
status: em revisão
revisor: OTTO
---

# Aparência

## 1. Propósito
O revisor achou a interface feia (2026‑10‑15). O problema principal era que ela não tinha
um tema próprio. O Qt seguia o modo escuro do Windows na moldura, enquanto a planta era uma
folha creme e o 3D um cinza azulado: eram três ambientes diferentes. Além disso, as
cores fixas pensadas para fundo claro (#444, #666, #777) ficavam quase ilegíveis
sobre o fundo escuro, e a grade de 10 cm competia com o desenho.

Esta spec define um tema único, num só arquivo (`brasbim/ui/theme.py`), aplicado antes
de criar a janela.

## 2. Direção
**A folha é o que importa; a moldura recua.** É uma prancheta de trabalho para sessões
longas de quem projeta. A moldura é cinza‑concreto claro, o desenho fica em branco frio
com traço grafite, e uma única cor de destaque marca o que está ativo ou selecionado.
Nada de decoração: a única peça marcante é a placa da ferramenta ativa, que se repete na
seleção da planta e do 3D. Desde 2026‑10‑29 o destaque é o **roxo jabuticaba** da logo
(§8), e os neutros ganharam um leve tom arroxeado; antes era um azul cobalto.

| Papel | Nome | Cor |
|---|---|---|
| Folha da planta | papel | `#F8F7F8` |
| Moldura (janela, barras) | concreto | `#E6E3E6` |
| Painéis encaixados | painel | `#EFEDEF` |
| Campos | campo | `#FFFFFF` |
| Texto e traço | grafite | `#26222A` |
| Rótulos, secundário | grafite suave | `#5C5661` |
| Desativado, dicas | grafite claro | `#918A95` |
| Bordas, divisões | régua | `#CBC6CC` / `#DCD8DC` |
| Ativo, seleção, foco | jabuticaba | `#6B1F5A` (fundo suave `#EEDDEA`) |
| Marca (logo) | jabuticaba escuro / magenta | `#3A0D2C` / `#E2336F` |
| Aviso / recusa / cruzamento | — | `#8A5A00` / `#B3261E` / `#2F7D4A` |
| Fundo do 3D | — | `#EBE8EB` |

O tema é sempre **claro** e não segue o modo escuro do sistema. Um tema escuro coerente,
com as mesmas regras, pode vir depois como opção em Exibir. **Ponto de revisão (a).**

## 3. Fonte, ícones e espaçamento
- **Archivo** (Omnibus‑Type, licença SIL OFL 1.1, distribuída em `brasbim/ui/fonts/`
  com a licença): uma grotesca técnica, com eixo de largura. Corpo 9,5 pt, algarismos
  de largura fixa (`tnum`) para as medidas se alinharem. O painel de propriedades usa
  largura 92 % (mais denso sem diminuir o corpo). Uma família só; os títulos dos grupos
  usam peso semibold. **Ponto de revisão (b).**
- Ícones das barras com 20 px (antes 16), botões com 5 px de folga e cantos de 5 px. O
  ícone da ferramenta ativa fica branco sobre a placa jabuticaba.
- Abas Planta/3D: texto com um traço jabuticaba embaixo da aba ativa, sem caixas.
- Painel em pé: rótulos à esquerda (quebram linha se forem longos), campos ocupando o
  resto. Nomes longos de tipo não alargam o painel; largura mínima 310 px.
- Mini‑barra: placa branca com borda fina e cantos de 6 px.

## 4. Desenho

### 4.1 Planta
- Folha `papel`; grade de 1 m sempre que couber. A grade de 10 cm **aparece aos poucos**
  com o zoom (transparente até 7 px entre linhas, plena a partir de 24 px), para não
  competir com as paredes. Longe, a grade passa a ser de 10 m com a de 1 m sumindo.
- Traço, portas e etiquetas em grafite; seleção, pré‑visualização e alças em jabuticaba;
  inválido em vermelho de recusa.
- As cores de materiais e tipos (fundo, hachura) são dados do modelo e não mudam.

### 4.2 3D
Fundo `#EBE8EB`, próximo da moldura. A seleção continua em jabuticaba.

## 5. Código
- `brasbim/ui/theme.py`: as cores (constantes), `palette()`, folha de estilo `STYLE`,
  `font(size, weight, width)`, `apply(app)` (estilo Fusion, fonte, paleta, folha).
- Nenhum outro módulo de interface tem cor de interface fixa; todos usam `theme.*`
  (teste AP02).

## 6. Critérios de aceite (testes)
- [x] **AP01** `theme.apply`: fonte Archivo; paleta clara (moldura com luminosidade
      > 200 e texto < 60) mesmo com o sistema em modo escuro; destaque jabuticaba.
- [x] **AP02** Nenhum `setStyleSheet` com cor fixa fora dos módulos de desenho e de
      materiais.
- [x] **AP03** A fonte é distribuída com a licença OFL.

## 8. Marca (2026‑10‑29)
- A logo é do revisor (`logoBrasBim.png`, na raiz): um B de fitas do jabuticaba escuro ao
  magenta, com "Bras" em grafite e "Bim" em magenta. O tema tira dela o destaque.
- `scripts/gerar_logo.py` (Qt, sem outras bibliotecas) gera em `brasbim/ui/logo/`: a logo
  com fundo transparente (`logo.png`, 480 px; o branco vira transparência, e as frestas
  entre as fitas ficam vazadas), o **símbolo** (só o B, quadrado) em 16–256 px e
  `brasbim.ico` (um PNG por tamanho). Refazer sempre que a logo mudar.
- Ícones pequenos usam só o símbolo: o nome não se lê abaixo de ~64 px.
- Onde aparece: ícone da janela e da barra de tarefas (no Windows com
  `AppUserModelID` próprio, para não mostrar o ícone do Python), Ajuda > Sobre (logo
  inteira), atalho da Área de Trabalho da pasta do pendrive (`brasbim.ico`; atalhos
  antigos ganham o ícone na próxima abertura) e o README.
- A logo foi desenhada para fundo claro: num tema escuro futuro, o "Bras" e as fitas
  mais escuras somem; vai precisar de uma variante.
- `theme.app_icon()` e `theme.logo(largura)` entregam os dois.

## 7. Fontes públicas
- **Archivo**: `github.com/google/fonts/tree/main/ofl/archivo` (arquivo da fonte e
  `OFL.txt`), licença SIL OFL 1.1, compatível com a distribuição junto ao aplicativo GPL.
- **CG**: conhecimento geral de desenho de interfaces (contraste, hierarquia
  tipográfica, uma cor de destaque) e do ofício de desenho técnico (folha, grafite,
  grade).

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhuma cor, ícone ou layout
de outro software foi copiado.

## 8. Pontos de revisão
(a) Sempre claro, sem seguir o modo escuro do sistema; tema escuro como opção futura.
(b) Fonte Archivo no aplicativo e na planta (etiquetas).
(c) Cobalto como única cor de destaque.
(d) A grade de 10 cm aparece aos poucos com o zoom.
