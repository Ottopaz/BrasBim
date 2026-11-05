# Complemento: unidades e casas decimais do projeto (2026‑11‑04)

Pedido do revisor: um campo de preferências do projeto na barra da vista para escolher a
unidade (m, cm, mm) e as casas decimais de cotas lineares, ângulo, raio, cota de nível,
cota em elevação e áreas, "estudando a forma como isso é aplicado no Archicad". Só fontes
públicas (ajuda oficial, documentação da API e fórum da Graphisoft). Descreve **funções**;
nomes, textos e layout de diálogo não são copiados.

## 1. O que o Archicad oferece (função)
- **Três ajustes separados, todos do projeto** (valem para quem abre o arquivo):
  1. **Unidades de trabalho**: unidade de comprimento e de ângulo, com casas decimais, das
     coordenadas, do quadro de medidas e das janelas de edição — o que se **digita e lê
     ao modelar**. Não muda as cotas. Versões mais novas separam a unidade do modelo e a
     das pranchas. Casas do ângulo de 0 a 4. Fontes: [Help AC19 – Working Units](https://help.graphisoft.com/AC/19/INT/AC19Help/Appendix_Settings/Appendix_Settings-23.htm),
     [Help AC18 – Working Units](https://help.graphisoft.com/AC/18/INT/AC18Help/Appendix_Settings/Appendix_Settings-24.htm),
     [API – unidades de trabalho](https://archicadapi.graphisoft.com/?p=2232),
     [Fórum – casas zero nas unidades de trabalho](https://community.graphisoft.com/t5/Modeling/Working-Units-accuracy-with-zero-decimals/td-p/372022).
  2. **Cotas**: uma unidade e casas **por tipo de cota** — linear, angular, raio, nível
     (na planta), elevação (cortes e fachadas), esquadria (porta/janela/claraboia),
     peitoril e área (que também vale para o carimbo do ambiente). Vale para cotas,
     carimbos de ambiente, textos de marcadores e rótulos; **não** muda valores
     calculados das tabelas. Opções: ocultar zeros finais; ocultar o zero inteiro
     (0,25 m → 25); precisão extra em sobrescrito (a casa seguinte arredondada a 5 ou
     25); arredondamento de área ao mais próximo ou a passos de 5/25; nos ângulos,
     graus/minutos/segundos com precisão própria. As duas opções de zero não valem juntas.
     O conjunto pode ser **gravado com nome** (padrão de cotas), escolhido na barra de
     opções rápidas e ligado a cada **vista** pelas configurações da vista. Fontes:
     [Help AC28 – Dimensions Preferences](https://help.graphisoft.com/AC/28/INT/_AC28_Help/140_UserInterfaceDialogBoxes/140_UserInterfaceDialogBoxes-24.htm),
     [Help AC24 – idem](https://help.graphisoft.com/AC/24/INT/_AC24_Help/130_UserInterfaceDialogBoxes/130_UserInterfaceDialogBoxes-25.htm),
     [Help AC20 – Dimensioning](https://help.graphisoft.com/AC/20/INT/AC20Help/04_Documentation/04_Documentation-40.htm),
     [API – preferências de cota](https://graphisoft.github.io/archicad-api-devkit/struct_a_p_i___dimension_prefs.html),
     [Fórum – unidades diferentes por tipo de cota numa vista](https://community.graphisoft.com/t5/Documentation/More-than-one-setting-for-working-units-in-a-view/m-p/249773).
  3. **Unidades de cálculo**: comprimento, área, volume e ângulo dos **valores calculados**
     (tabelas interativas, listas, textos automáticos), com casas (área de 0 a 4) e
     precisão extra; uma regra à parte diz se os totais somam o valor mostrado ou o exato.
     Fontes: [Help AC28 – Calculation Units](https://help.graphisoft.com/AC/28/INT/_AC28_Help/140_UserInterfaceDialogBoxes/140_UserInterfaceDialogBoxes-25.htm),
     [Help AC28 – Calculation Rules](https://help.graphisoft.com/AC/28/INT/_AC28_Help/140_UserInterfaceDialogBoxes/140_UserInterfaceDialogBoxes-26.htm),
     [Help AC19 – Calculation Units and Rules](https://help.graphisoft.com/AC/19/INT/AC19Help/Appendix_Settings/Appendix_Settings-26.htm).
- **Tudo é só apresentação**: o modelo guarda o valor exato; zero casas não arredonda a
  geometria (moderador no fórum acima).

## 2. Queixas de usuários (fórum)
- A área do carimbo do ambiente **não** segue as unidades de cálculo, e sim as de cota
  (área): quem muda um lugar só não vê efeito ([fórum – casas da área do ambiente](https://community.graphisoft.com/t5/Project-data-BIM/How-to-change-the-decimals-at-zones-area-calculation/m-p/374952)).
- Três lugares diferentes para "unidade" confundem; pedido para as unidades de trabalho
  irem para o ambiente de trabalho de cada um ([fórum](https://community.graphisoft.com/t5/Modeling/Working-Units-to-be-part-of-Work-Environment/td-p/194136)).

## 3. O que levar para o BrasBim
- **Um lugar só**, "Unidades do projeto", com uma linha por tipo de medida (cota linear,
  raio, ângulo, nível, elevação, esquadria, área) e as colunas unidade, casas, mostrar a
  unidade e ocultar zeros finais; aberto pela barra da vista. Evita a confusão dos três
  diálogos.
- Guardar no IFC do projeto (é do projeto, como no Archicad); o valor do modelo continua
  exato, em metros.
- Padrões prontos (metros 2 casas, centímetros sem casas) num clique, na barra.
- Depois: unidade de trabalho (o que se digita), unidades das tabelas, padrões com nome
  ligados à vista, precisão extra em sobrescrito.

## 4. Lacunas
- A lista exata de unidades de comprimento e área de cada versão não foi lida (a página
  diz só que muda entre métrico e imperial). A página de unidades de trabalho do AC28 não
  foi achada; valem a do AC18/AC19 e o resumo da busca.
