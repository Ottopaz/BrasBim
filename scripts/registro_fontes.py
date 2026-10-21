# SPDX-License-Identifier: GPL-3.0-or-later
"""Gera cleanroom/REGISTRO-DE-FONTES.md a partir das specs e do anexo da pesquisa."""
import re
from pathlib import Path

root = Path(".")
specs = sorted(p for p in root.glob("spec/**/*.md") if not p.name.startswith("_"))
out = []
out.append("""# Registro de fontes consultadas

Índice das fontes **efetivamente lidas** para escrever specs e código do BrasBim
(`PROCESSO.md` §4). As categorias permitidas e proibidas estão em `FONTES.md`; o acesso
ao material restrito, em `REGISTRO-DE-ACESSO.md`.

- **Parte A**: fontes citadas em cada spec (a seção "Fontes" de cada documento é a
  referência; aqui ela é reunida para consulta e auditoria).
- **Parte B**: pesquisa ampla de 2026‑10‑21 sobre Archicad, Revit e AutoCAD (758 fontes
  públicas), cuja lista completa está no Anexo A de
  `reports/Pesquisa Archicad Revit AutoCAD.md`, com as notas brutas em
  `research_notes/Pesquisa Archicad Revit AutoCAD/`.

**Como acrescentar**: cada spec nova ou revisada mantém a sua seção "Fontes" (URL, data
de acesso, o que foi usado) e o autor regenera este arquivo com
`scripts/registro_fontes.py` no mesmo commit. Fonte que só apareceu em trecho de
resultado de busca é marcada "conferir" e não sustenta sozinha uma decisão de spec.

Gerado a partir do repositório; não edite à mão as partes A e B.
""")
out.append("\n## Parte A: fontes citadas nas specs\n")
heading = re.compile(r"^#{2,3}\s+(?:\d+\.\s*)?(Fontes.*)$", re.IGNORECASE)
for path in specs:
    text = path.read_text(encoding="utf-8")
    meta = {}
    if text.startswith("---"):
        for line in text.split("---", 2)[1].splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if heading.match(l)), None)
    title = meta.get("documento") or meta.get("elemento") or path.stem
    out.append(f"\n### `{path.as_posix()}`\n")
    out.append(f"*{title}*; data {meta.get('data', '—')}; situação "
               f"{meta.get('status', '—')}.\n")
    if start is None:
        out.append("\n> **Sem seção \"Fontes\"**: conferir antes da primeira versão pública "
                   "(PROCESSO.md §6).\n")
        continue
    level = len(lines[start]) - len(lines[start].lstrip("#"))
    body = []
    for line in lines[start + 1:]:
        m = re.match(r"^(#+)\s", line)
        if m and len(m.group(1)) <= level:
            break
        body.append(line)
    body = "\n".join(body).strip()
    urls = sorted(set(re.findall(r"https?://[^\s)>\]|`]+", body)))
    out.append("\n" + body + "\n")
    if urls:
        out.append(f"\nEndereços citados ({len(urls)}): " + "; ".join(urls) + "\n")

out.append("\n## Parte B: pesquisa de 2026‑10‑21 (Archicad, Revit, AutoCAD)\n")
report = (root / "reports" / "Pesquisa Archicad Revit AutoCAD.md").read_text(encoding="utf-8")
annex = report.split("## Anexo A", 1)[1]
sections = re.split(r"^### ", annex, flags=re.MULTILINE)[1:]
out.append("""
Fontes públicas acessadas em 2026‑10‑21 por 15 frentes de pesquisa, só na web, sem
`_restrito/` nem `tools/`. "Página lida" = conteúdo aberto e lido; "trecho de busca" =
só o resumo do buscador (fórum da Graphisoft, G2 e blogs da Autodesk responderam HTTP 403;
Reddit inacessível): **conferir antes de citar numa spec**. A coluna "usado para" do
anexo foi gerada por script a partir das notas e precisa de revisão ao virar spec.

| Tema | Fontes | Página lida | Trecho de busca (conferir) | Notas brutas |
|---|---|---|---|---|
""")
notes = {
    "Usuários": "usuarios_e_mercado_brasil.md", "Archicad: modelagem": "archicad_modelagem.md",
    "Archicad: documentação": "archicad_documentacao_colaboracao.md",
    "Revit: modelagem": "revit_modelagem_familias.md",
    "Revit: documentação": "revit_documentacao_colaboracao.md", "AutoCAD": "autocad.md",
    "Interface": "interface_e_interacao.md", "Normas": "normas_e_projeto_legal_brasil.md",
    "Quantitativos": "quantitativos_orcamento_sustentabilidade.md",
    "Terreno": "terreno_e_implantacao.md", "Estrutura": "estrutura_e_instalacoes.md",
    "Bibliotecas": "bibliotecas_e_objetos.md", "Interoperabilidade": "interoperabilidade_openbim.md",
    "Visualização": "visualizacao_apresentacao.md", "Ferramentas": "ferramentas_emergentes.md",
}
total = 0
for sec in sections:
    title = sec.splitlines()[0]
    name = re.sub(r"^A\.\d+\s+", "", title)
    name = re.sub(r"\s*\(\d+ fontes\)", "", name)
    rows = [l for l in sec.splitlines() if l.startswith("| F")]
    search = sum(1 for r in rows if "trecho de busca" in r.split("|")[-3])
    total += len(rows)
    note = next((v for k, v in notes.items() if name.startswith(k)), "—")
    out.append(f"| {name} | {len(rows)} | {len(rows) - search} | {search} | "
               f"`research_notes/Pesquisa Archicad Revit AutoCAD/{note}` |\n")
out.append(f"| **Total** | **{total}** | | | |\n")
out.append("""
Fontes **proibidas** que apareceram e **não foram usadas**: um endereço que parecia
hospedar o texto integral pago da ABNT NBR 6492:2021 (marcado "NÃO USAR" no anexo). Normas
ABNT só entram por título, escopo e resumo públicos, ou por exemplar legítimo.
""")
Path("cleanroom/REGISTRO-DE-FONTES.md").write_text("".join(out), encoding="utf-8")
print(len(specs), "specs;", total, "fontes da pesquisa")
