# Fontes permitidas e proibidas para a especificação

Este arquivo diz **que tipo** de fonte pode ser usada. **Quais** fontes foram de fato
lidas fica na seção "Fontes" de cada spec, reunida em `REGISTRO-DE-FONTES.md`
(gerado por `scripts/registro_fontes.py`). A base de mercado e concorrência é a pesquisa
de 2026‑10‑21 (`reports/Pesquisa Archicad Revit AutoCAD.md`, 758 fontes públicas).

*Atualizado em 2026‑10‑21.*

## ✅ Permitidas (citar na seção "Fontes" de cada spec)

**Padrões abertos (base principal)**
- IFC 4.3 / ISO 16739‑1:2024: buildingSMART (ifc43‑docs.standards.buildingsmart.org; o
  site bloqueia leitura automatizada, então ler o repositório
  github.com/buildingSMART/IFC4.x-development)
- BCF 3.0 e BCF API (OpenCDE), IDS 1.0, bSDD: buildingSMART
- SAF (Structural Analysis Format), formato aberto em planilha, para estrutura (futuro)
- Model Context Protocol (modelcontextprotocol.io) e JSON-RPC 2.0, para o assistente (spec/ui 16)
- RFC 4180 (CSV) e ECMA-376 / ISO/IEC 29500 (Office Open XML), para exportar tabelas (spec/ui 17)
- DXF Reference (Autodesk, documentação pública do formato), para importar desenhos (spec/ui 22)
- EPSG / SIRGAS 2000 (IBGE), para georreferenciamento

**Normas e legislação brasileiras**
- Normas ABNT (NBR 6492, 16636, 12721, 15965, 15575, 15220, 9050, 13133…): só **título,
  escopo e resumos públicos** (catálogo da ABNT, normas.com.br, Target, material
  didático) ou **exemplar adquirido legitimamente**. Marcar "texto não lido" quando for o
  caso.
- Leis, decretos e portarias (planalto.gov.br, gov.br, diários oficiais), códigos de obras
  e manuais de aprovação das prefeituras, cadernos BIM estaduais, instruções técnicas dos
  Corpos de Bombeiros, SINAPI/SICRO (Caixa, DNIT), PBE Edifica (Inmetro).

**Documentação pública de produtos**
- Manuais e ajudas públicas (help.graphisoft.com, help.autodesk.com, Vectorworks etc.) e
  notas de versão, *para entender a funcionalidade esperada*. Descreva o comportamento
  com palavras próprias e não copie texto.
- GDL Reference Guide (público): permitido para implementar compatibilidade com a
  linguagem. Linguagem e funcionalidade não são protegidas, mas o texto do manual é.
- Documentação pública de APIs (Archicad API DevKit, JSON API, Revit API), só para
  compatibilidade de automação.

**Opinião e uso**
- Fóruns oficiais (Graphisoft Community, Autodesk Community, quadros de ideias), Reddit,
  OSArch, avaliações (G2, Capterra), blogs, revendas, imprensa do setor, vídeos (título,
  descrição e transcrição): **como evidência do que usuários fazem, querem e reclamam**.
  Citar curto, resumir com palavras próprias. O que veio só de trecho de resultado de
  busca é marcado "conferir" e não sustenta sozinho uma decisão de spec.
- Usar qualquer software como usuário e descrever *o que* ele faz (entradas, saídas,
  comportamento visível). Relatos do revisor e prints em `feedback/prints/` valem como
  descrição de função.
- Artigos acadêmicos (SciELO, ENTAC, Ambiente Construído, ITcon), TCCs e livros de BIM,
  arquitetura e geometria computacional.

**Projetos open source (respeitando as licenças; ver `THIRD_PARTY_NOTICES.md`)**
- IfcOpenShell (LGPL‑3.0), Bonsai (GPL‑3.0), FreeCAD BIM, That Open Engine, xBIM,
  OpenCascade, Speckle, xeokit: ler documentação e código só se a licença for compatível
  com a parte do BrasBim onde a ideia vai entrar (núcleo LGPL, aplicativo GPL); conferir o
  arquivo LICENSE do repositório, não fontes secundárias.
- ezdxf (MIT), shapely (BSD), pyclipr (BSL‑1.0): bibliotecas usadas.
- Conversores externos de DWG instalados pelo usuário (ODA File Converter, gratuito;
  LibreDWG, GPL), chamados como programas à parte.

## ❌ Proibidas

- Qualquer coisa em `_restrito/` ou `tools/` (símbolos, nomes internos, estruturas de
  arquivo, schemas extraídos de binários)
- Descompilação, desmontagem, depuração ou leitura do formato interno de software e
  arquivos proprietários (`.pln`, `.rvt`, `.dwg` lido por conta própria, `.gsm`, `.rfa`)
- Contornar proteção (CodeMeter etc.) ou descumprir a licença de uso (EULA) aceita
- Copiar textos, ícones, imagens, nomes de comandos, organização de menus, diálogos ou
  objetos de biblioteca sem licença compatível
- **Cópias não autorizadas de normas pagas** (PDF integral da ABNT fora do canal legítimo)
  e qualquer código ou documento vazado ou de origem duvidosa. Se aparecerem numa busca,
  não abrir e registrar como "não usar"
- Código de projeto open source com licença incompatível com a do BrasBim
