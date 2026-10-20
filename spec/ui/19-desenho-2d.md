---
documento: Desenho 2D (círculo, arco, curva livre, cota de raio e de ângulo, rótulo, marcador de alteração)
requisito: RF-DOC-05 (cotas), RF-DOC-06 (desenho 2D), RF-DOC-07 (símbolos), RF-DOC-13 (revisões, parcial)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-20
status: em revisão (implementado para teste, fluxo do MVP)
revisor: OTTO
---

# Desenho 2D (pacote 14)

## 1. Propósito
Completar o desenho técnico da planta com o que falta para o MVP: **círculo**, **arco**,
**curva livre**, **cota de raio** (e de diâmetro), **cota de ângulo**, **rótulo** (texto
com linha de chamada, que pode mostrar dados do elemento apontado) e **marcador de
alteração** (nuvem de revisão com número). Todos são anotações da planta, como o texto,
a linha e a hachura da spec/ui 13.

## 2. Mapeamento IFC
Cada um é uma `IfcAnnotation` contida no pavimento, com o estado em JSON no Pset
`BrasBim_Anotacao` e a geometria (`Annotation`, `IfcGeometricCurveSet` e
`IfcTextLiteralWithExtent`) refeita a partir do estado, pelo mesmo caminho das outras
anotações (`annotations.base`). [IFC-ANNOT]

| Elemento | Prefixo | `PredefinedType` | `ObjectType` | Estado |
|---|---|---|---|---|
| Círculo | `circle2d` | — | `Circulo` | `center`, `radius`, `weight`, `dash` |
| Arco | `arc2d` | — | `Arco` | `center`, `radius`, `start`, `end` (graus, anti-horário), `weight`, `dash` |
| Curva livre | `spline2d` | — | `Curva` | `points` (pontos por onde a curva passa), `closed`, `weight`, `dash` |
| Cota de raio | `radius_dim` | `DIMENSION` | `CotaDeRaio` | `center`, `radius`, `angle` (direção da chamada), `diameter` (sim/não), `ref` (GlobalId do círculo, arco ou parede em arco) |
| Cota de ângulo | `angle_dim` | `DIMENSION` | `CotaDeAngulo` | `vertex`, `a`, `b` (um ponto em cada lado), `radius` (do arco da cota) |
| Rótulo | `label` | `TEXT` | `Rotulo` | `at` (ponta da seta), `text_at`, `text`, `ref` (elemento apontado), `field` (`free`, `type`, `name`, `code`) |
| Marcador de alteração | `revision` | `SYMBOL` | `Alteracao` | `outline` (polígono), `number` (texto curto: "1", "A"), `note` |

- A curva livre passa pelos pontos clicados (curva de Catmull-Rom, CG) e é gravada como
  polilinha fina (24 trechos entre dois pontos).
- A cota de raio presa (`ref`) acompanha o raio e o centro do elemento quando ele muda:
  círculo e arco 2D, e parede em arco (pelo eixo). Se o elemento some, a cota fica livre
  com a última medida (como a cota linear, spec/ui 13 §4.3).
- O rótulo preso mostra, conforme `field`, o nome do tipo, o nome ou o código
  (`Reference`) do elemento, e acompanha o elemento quando ele muda de tipo. Com `free`,
  é o texto digitado.

## 3. Criação (interação)
Grupo Documentação da barra Ferramentas, depois da Linha, com ícones próprios.

| Ferramenta | Cliques | Tab |
|---|---|---|
| Círculo | centro e um ponto do círculo | Raio |
| Arco | início, um ponto do arco e fim | — |
| Curva livre | os pontos; Enter, clique duplo ou botão direito encerra; clicar no primeiro fecha | — |
| Cota de raio | um ponto sobre o círculo, o arco ou a parede em arco, e onde vai o texto | — |
| Cota de ângulo | o vértice, um ponto em cada lado e a posição do arco | Ângulo (só mostra) |
| Rótulo | a ponta da seta (sobre o elemento) e onde vai o texto; pede o texto quando não há elemento | — |
| Marcador de alteração | retângulo por dois cantos (ou polígono, na barra Opções) | — |

Barra Opções: espessura e tipo de linha (círculo, arco, curva); diâmetro em vez de raio
(cota de raio); o que o rótulo mostra (texto, tipo, nome, código); número da alteração
(marcador; o próximo livre por padrão).

## 4. Edição
- Mover, copiar, girar e espelhar, como as outras anotações (`mapped`). O texto do
  rótulo e o número do marcador continuam legíveis.
- Painel de propriedades: os campos do estado (raio, ângulos, espessura, texto, número).
- Clique duplo no rótulo edita o texto (como o texto da spec/ui 13 §6).

## 5. Representação 2D
- Linhas finas por padrão (0,18 mm círculo, arco e curva; 0,13 mm cotas e rótulo,
  NBR 8403, a conferir).
- Cota de raio: linha do centro (ou de dentro) até o arco, seta na ponta sobre o arco e
  o texto "R 1,20" (ou "Ø 2,40") ao lado, legível.
- Cota de ângulo: arco entre os dois lados, com setas nas pontas e o texto "45,0°".
- Rótulo: seta (ponta cheia), linha até o texto e um traço horizontal sob o texto.
- Marcador: nuvem (arcos ao longo do contorno, de 4 mm de papel) e um triângulo com o
  número no primeiro vértice.

## 6. Camadas (spec/ui 18)
Círculo, arco e curva vão para Linhas e hachuras; as cotas para Cotas; o rótulo para
Textos e rótulos; o marcador para Símbolos. Em arquivo antigo sem a camada padrão
desses elementos, vale a da ferramenta parecida (linha, cota, texto, norte).

## 7. Critérios de aceite (testes)
- [x] **D2D01** Círculo: `circle2d` com centro e raio; a planta tem a polilinha fechada
      com o raio certo; mover e copiar; o IFC passa na validação.
- [x] **D2D02** Arco por três pontos: centro e raio certos e o arco passa pelo ponto do
      meio; espelhar troca o sentido sem mudar o desenho.
- [x] **D2D03** Curva livre passa por todos os pontos clicados; fechada fecha.
- [x] **D2D04** Cota de raio presa a um círculo: mudar o raio do círculo muda o texto;
      presa a uma parede em arco, acompanha a parede; desfazer volta.
- [x] **D2D05** Cota de ângulo de 90° e de 45°: o texto e o arco certos.
- [x] **D2D06** Rótulo preso a uma parede mostra o nome do tipo; trocar o tipo da
      parede troca o texto; rótulo livre mostra o texto digitado.
- [x] **D2D07** Marcador de alteração: nuvem e número; o próximo marcador sai com o
      número seguinte.
- [x] **D2D08** Interface: as ferramentas criam pelos cliques da tabela §3 e ficam na
      camada certa.

## 8. Fontes públicas
- **IFC 4.3**: `IfcAnnotation` (`PredefinedType` `DIMENSION`, `TEXT`, `SYMBOL`),
  `IfcGeometricCurveSet`, `IfcTextLiteralWithExtent` [IFC-ANNOT, como na spec/ui 13].
- **NBR 8403** (espessuras de linha) e **NBR 6492** (cotas e convenções): texto não lido,
  a conferir, como nas specs anteriores.
- **CG**: curva de Catmull-Rom (passa pelos pontos de controle); nuvem de revisão e
  rótulo com linha de chamada são convenções gerais de desenho técnico.

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

## 9. Pontos de revisão
(a) curva por Catmull-Rom (passa pelos pontos) em vez de uma curva de controle por fora;
(b) cota de raio presa só a círculo, arco e parede em arco (pilar circular fica para
    depois);
(c) rótulo com quatro conteúdos (texto, tipo, nome, código);
(d) marcador sem tabela de revisões na prancha (RF-DOC-13 completo é V1);
(e) espessuras padrão da §5.
