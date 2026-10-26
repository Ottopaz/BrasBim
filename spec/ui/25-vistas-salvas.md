---
documento: Vistas salvas (planta, corte e 3D) e como pô-las na prancha
requisito: RF-DOC-09 (complemento), pendência "pôr vista na prancha" e "câmera salva"
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-26
status: em revisão (implementado para teste, fluxo do MVP)
revisor: OTTO
---

# Vistas salvas

## 1. Propósito
Hoje a prancha recebe "a planta do pavimento" e o desenho sai com a escala do pavimento e
com as camadas do jeito que estiverem na janela, ou com uma combinação escolhida depois.
O revisor pediu um botão que **guarde a vista como ela está na tela** (camadas e escala)
para depois pô-la nas pranchas. A vista salva é o passo entre o modelo e a prancha:
modelo → **vista salva** (o que mostrar e como) → prancha (onde fica no papel).

## 2. O que a vista salva guarda
| Campo | Planta | Corte/fachada | 3D |
|---|---|---|---|
| Nome | sim | sim | sim |
| Origem | pavimento | vista de corte ou fachada | câmera (alvo, distância, giro, inclinação, proporção da janela) |
| Escala | sim (1:20 … 1:500) | sim | não (perspectiva) |
| Camadas | estado de cada camada (visível, bloqueada), uma cópia, não um vínculo com a combinação | idem | idem |
| Opções de desenho | detalhe (simplificado ou por camadas), acima do corte, etiquetas, espessuras, símbolos de corte | espessuras | — |
| Recorte | opcional: retângulo da área visível na hora de salvar | — | — |
| Tabela de penas | reservado para a spec/ui 27 | idem | — |

As camadas são **copiadas** para a vista: mudar depois uma combinação não muda a vista
salva (para mudar, abre-se a vista, muda-se e usa-se **Atualizar com a janela**).

## 3. Salvar
- Botão **Salvar vista** no canto da barra de abas (à direita das abas Planta/3D/…),
  valendo para a aba à frente: planta, 3D ou corte. Também em **Exibir > Salvar vista…**
  (Ctrl+Alt+S), na paleta e na linha de comando (apelido `SV`).
- Abre um quadro curto: **nome** (sugestão: "Térreo 1:50", "Corte A 1:50", "3D 1"), um
  resumo do que será guardado (pavimento, escala, camadas: nome da combinação ou
  "alterada") e, na planta, **Recortar pela área visível** (desligado).
- Grava uma transação "Salvar vista" (desfazer desfaz).

## 4. Abrir, atualizar, excluir
- O painel **Projeto** ganha a lista **Vistas salvas** (a lista "Vistas" passa a se chamar
  "Cortes e fachadas"). Clique duplo **abre** a vista: troca o pavimento, aplica as
  camadas, as opções e a escala na janela (planta), ou leva a câmera ao lugar (3D), ou
  abre a aba do corte com a escala dela.
- A escala aberta pela vista vale **só para a janela** (não muda a escala gravada no
  pavimento). A barra de estado mostra a escala com o nome da vista; escolher outra
  escala na barra, com a vista aberta, muda só a janela.
- Botão direito na vista salva: **Abrir**, **Atualizar com a janela** (regrava o que está
  na tela, mesma origem), **Renomear**, **Pôr na prancha ▸** (lista as pranchas),
  **Excluir**.
- Excluir a vista tira-a das pranchas onde ela está, na mesma transação.
- Mudar de pavimento ou de aba "fecha" a vista: a janela volta à escala do pavimento.

## 5. Pôr na prancha
- **Arrastar** a vista salva da lista para a aba da prancha aberta: ela fica com o centro
  onde foi solta.
- **Botão direito no papel** da prancha: **Pôr vista salva ▸** com a lista; entra com o
  centro no ponto clicado.
- **Pôr na prancha ▸** no botão direito da vista salva (§4): entra no primeiro lugar livre.
- Na prancha a vista salva é **viva**: desenha o modelo atual com a escala, as camadas,
  as opções e o recorte guardados nela. A escala aparece no carimbo como antes.
- A mesma vista salva pode estar em várias pranchas; numa prancha, uma vez só.
- Vista 3D na prancha: sai como **imagem** do 3D (como na tela, com as cores e as linhas
  de contorno), gerada na hora de desenhar a prancha e de exportar o PDF. Tamanho no
  papel: largura padrão 160 mm, proporção da janela da hora em que foi salva; a largura
  se muda no botão direito sobre a vista na prancha (**Largura no papel…**).
- O que já existe continua: a planta do pavimento e os cortes postos pelo painel de
  propriedades da prancha seguem funcionando (arquivos antigos abrem iguais).

## 6. IFC
- Vista salva = `IfcAnnotation` com `ObjectType` "VistaSalva", contida na edificação, com
  o estado em JSON no Pset `BrasBim_VistaSalva` (`Parametros`), no mesmo padrão das
  pranchas e das vistas de corte. Não tem representação geométrica.
- Operações serializáveis: `saved_view.create` / `.delete` (estado completo) e
  `saved_view.edit` (antes/depois dos campos mudados).
- Item da prancha: `{"kind": "saved", "saved": "<GlobalId>", "at": [x, y]}`, mais
  `"width"` (mm) para a vista 3D.

## 7. Critérios de aceite (testes)
- [ ] **VS01** Criar, editar e excluir vista salva (planta, corte, 3D) grava o Pset certo;
      desfazer volta ao IFC anterior; o arquivo salvo e reaberto mantém tudo.
- [ ] **VS02** A vista guarda uma cópia das camadas: mudar a combinação depois não muda a
      vista; a planta desenhada pela vista esconde as camadas que ela esconde.
- [ ] **VS03** A escala da vista vale no desenho (tamanho do texto e da cota no papel) e
      não muda a escala do pavimento.
- [ ] **VS04** Recorte: a vista na prancha tem o tamanho do retângulo na escala.
- [ ] **VS05** Pôr na prancha: item `saved` com o centro dado; repetir na mesma prancha é
      recusado; excluir a vista tira-a das pranchas (e desfazer devolve).
- [ ] **VS06** Interface: botão Salvar vista na planta e no 3D; abrir a vista troca o
      pavimento, as camadas, a escala da janela e a câmera; Atualizar com a janela
      regrava.
- [ ] **VS07** Interface: arrastar da lista para a prancha e "Pôr vista salva" no botão
      direito do papel; a vista 3D sai como imagem na prancha e no PDF.

## 8. Fontes
- Pesquisa do projeto, `research_notes/.../archicad_documentacao_colaboracao.md` §1: no
  Archicad, vista salva guarda camadas, escala, filtros e sobreposições gráficas, e o
  desenho posto na folha é composto a partir dela ("modelo → vista salva → desenho na
  folha"); o mapa de vistas é uma árvore no navegador. Fonte citada lá:
  [Graphisoft Community, "Archicad Basic Concepts - The Navigator"](https://community.graphisoft.com/t5/Getting-started/Archicad-Basic-Concepts-The-Navigator/ta-p/303987)
  (trecho de busca; **conferir**).
- `revit_documentacao_colaboracao.md`: modelos de vista guardam propriedades aplicáveis
  em lote ([Autodesk Help 2024 – View Template Properties](https://help.autodesk.com/cloudhelp/2024/ENU/Revit-Customize/files/GUID-66D789A8-AB92-4AF0-B884-DF3A3302E117.htm)).
- Pedido do revisor (2026‑10‑26) e pendências do `CONTEXTO.md` (câmera salva; fluxo de
  pôr vista na prancha "não está bom ainda").
- Nenhum material de `_restrito/` nem de `tools/` foi usado. Nomes e quadros próprios.

## 9. Pontos de revisão
(a) camadas **copiadas** na vista (não um vínculo com a combinação): mudar a combinação
    não mexe nas pranchas já montadas;
(b) a escala aberta pela vista vale só para a janela, sem mudar o pavimento;
(c) 3D na prancha como imagem (vetor fica para depois, se precisar);
(d) recorte só pela área visível na hora de salvar (sem editar o retângulo depois, por
    enquanto);
(e) nome "Cortes e fachadas" para a lista antiga "Vistas".
