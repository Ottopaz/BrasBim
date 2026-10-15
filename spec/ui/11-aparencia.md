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
com traço grafite, e uma única cor de destaque, o **cobalto**, marca o que está ativo ou
selecionado. Nada de decoração: a única peça marcante é a placa cobalto da ferramenta
ativa, que se repete na seleção da planta e do 3D.

| Papel | Nome | Cor |
|---|---|---|
| Folha da planta | papel | `#F7F8F6` |
| Moldura (janela, barras) | concreto | `#E3E6E4` |
| Painéis encaixados | painel | `#EDEFED` |
| Campos | campo | `#FFFFFF` |
| Texto e traço | grafite | `#23272A` |
| Rótulos, secundário | grafite suave | `#596064` |
| Desativado, dicas | grafite claro | `#8C9396` |
| Bordas, divisões | régua | `#C7CCC9` / `#D8DCD9` |
| Ativo, seleção, foco | cobalto | `#1F5FC4` (fundo suave `#D9E4F6`) |
| Aviso / recusa / cruzamento | — | `#8A5A00` / `#B3261E` / `#2F7D4A` |
| Fundo do 3D | — | `#E9ECEA` |

O tema é sempre **claro** e não segue o modo escuro do sistema. Um tema escuro coerente,
com as mesmas regras, pode vir depois como opção em Exibir. **Ponto de revisão (a).**

## 3. Fonte, ícones e espaçamento
- **Archivo** (Omnibus‑Type, licença SIL OFL 1.1, distribuída em `brasbim/ui/fonts/`
  com a licença): uma grotesca técnica, com eixo de largura. Corpo 9,5 pt, algarismos
  de largura fixa (`tnum`) para as medidas se alinharem. O painel de propriedades usa
  largura 92 % (mais denso sem diminuir o corpo). Uma família só; os títulos dos grupos
  usam peso semibold. **Ponto de revisão (b).**
- Ícones das barras com 20 px (antes 16), botões com 5 px de folga e cantos de 5 px. O
  ícone da ferramenta ativa fica branco sobre a placa cobalto.
- Abas Planta/3D: texto com um traço cobalto embaixo da aba ativa, sem caixas.
- Painel em pé: rótulos à esquerda (quebram linha se forem longos), campos ocupando o
  resto. Nomes longos de tipo não alargam o painel; largura mínima 310 px.
- Mini‑barra: placa branca com borda fina e cantos de 6 px.

## 4. Desenho

### 4.1 Planta
- Folha `papel`; grade de 1 m sempre que couber. A grade de 10 cm **aparece aos poucos**
  com o zoom (transparente até 7 px entre linhas, plena a partir de 24 px), para não
  competir com as paredes. Longe, a grade passa a ser de 10 m com a de 1 m sumindo.
- Traço, portas e etiquetas em grafite; seleção, pré‑visualização e alças em cobalto;
  inválido em vermelho de recusa.
- As cores de materiais e tipos (fundo, hachura) são dados do modelo e não mudam.

### 4.2 3D
Fundo `#E9ECEA`, próximo da moldura. A seleção continua em cobalto.

## 5. Código
- `brasbim/ui/theme.py`: as cores (constantes), `palette()`, folha de estilo `STYLE`,
  `font(size, weight, width)`, `apply(app)` (estilo Fusion, fonte, paleta, folha).
- Nenhum outro módulo de interface tem cor de interface fixa; todos usam `theme.*`
  (teste AP02).

## 6. Critérios de aceite (testes)
- [x] **AP01** `theme.apply`: fonte Archivo; paleta clara (moldura com luminosidade
      > 200 e texto < 60) mesmo com o sistema em modo escuro; destaque cobalto.
- [x] **AP02** Nenhum `setStyleSheet` com cor fixa fora dos módulos de desenho e de
      materiais.
- [x] **AP03** A fonte é distribuída com a licença OFL.

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
