# Fontes permitidas e proibidas para a especificação

## ✅ Permitidas (citar na seção "Fontes" de cada spec)

**Padrões abertos (base principal)**
- IFC 4.3 / ISO 16739‑1: buildingSMART (ifc43‑docs.standards.buildingsmart.org)
- BCF 3.0, IDS 1.0, bSDD: buildingSMART
- Model Context Protocol (modelcontextprotocol.io) e JSON-RPC 2.0, para o assistente (spec/ui 16)
- RFC 4180 (CSV) e ECMA-376 / ISO/IEC 29500 (Office Open XML), para exportar tabelas (spec/ui 17)
- DXF Reference (Autodesk, documentação pública do formato), para importar desenhos (spec/ui 22)
- Normas ABNT pertinentes (NBR 6492 representação de projetos de arquitetura, NBR 15575, NBR 9050…), conforme acesso legítimo

**Documentação pública de produtos**
- Manuais e Help Center públicos de Archicad, Revit, Vectorworks etc. *para entender
  a funcionalidade esperada*. Descreva o comportamento com palavras próprias e
  não copie texto.
- GDL Reference Guide (público): permitido para implementar compatibilidade com a
  linguagem. Linguagem e funcionalidade não são protegidas, mas o texto do manual é.
- Documentação pública de APIs (Archicad API DevKit, JSON API docs), só para
  compatibilidade de automação.

**Projetos open source (respeitando as licenças)**
- IfcOpenShell, Bonsai (BlenderBIM), FreeCAD BIM, That Open Engine, xBIM, OpenCascade
- ezdxf (MIT), para ler DXF; conversores externos de DWG instalados pelo usuário
  (ODA File Converter, gratuito; LibreDWG, GPL), chamados como programas à parte

**Experiência de uso**
- Usar qualquer software como usuário e descrever *o que* ele faz (entradas, saídas,
  comportamento visível)
- Livros, cursos e artigos de BIM e de geometria computacional

## ❌ Proibidas

- Qualquer coisa em `_restrito/` (símbolos, nomes internos, estruturas de arquivo, schemas extraídos de binários)
- Descompilação, desmontagem ou depuração de software proprietário
- Contornar proteção (CodeMeter etc.)
- Copiar textos, ícones, imagens, diálogos ou objetos de biblioteca sem licença compatível
- Código vazado ou de origem duvidosa
- Código de projeto open source com licença incompatível com a do BrasBim
