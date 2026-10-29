# SPDX-License-Identifier: LGPL-3.0-or-later
"""Exportação das tabelas para planilha (spec/ui 17 §5).

- **CSV** (RFC 4180): separador ``;``, vírgula decimal, UTF-8 com BOM, números sem
  separador de milhar.
- **XLSX** (ECMA-376, SpreadsheetML): o mínimo do pacote, escrito com a biblioteca padrão:
  tipos de conteúdo, relações, pasta, uma planilha, estilos (negrito e "0.00") e cadeias
  compartilhadas. Números vão como número.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from xml.sax.saxutils import escape

from brasbim.core.quantities.tables import Result, format_value


def csv_text(result: Result) -> str:
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";", lineterminator="\r\n")
    writer.writerow([c.title for c in result.columns])
    for row in result.rows:
        writer.writerow([format_value(v) for v in row.cells])
    return out.getvalue()


def write_csv(path: str, result: Result) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(csv_text(result))


# --- XLSX ------------------------------------------------------------------------------------

_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_TYPES = "http://schemas.openxmlformats.org/package/2006/content-types"
_DOC = "application/vnd.openxmlformats-officedocument.spreadsheetml"
_HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
# Estilos: 0 normal, 1 negrito, 2 número "0.00", 3 número "0.00" em negrito.
_STYLES = (
    f'{_HEAD}<styleSheet xmlns="{_MAIN}">'
    '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
    '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
    '<fills count="2"><fill><patternFill patternType="none"/></fill>'
    '<fill><patternFill patternType="gray125"/></fill></fills>'
    '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>'
    '</cellStyleXfs>'
    '<cellXfs count="4"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
    '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
    '<xf numFmtId="2" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
    '<xf numFmtId="2" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1" '
    'applyNumberFormat="1"/></cellXfs>'
    '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
    '</styleSheet>')
_INVALID_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f]")


def sheet_name(name: str) -> str:
    """Nome de planilha válido: até 31 caracteres, sem ``[]:*?/\\``."""
    clean = re.sub(r"[\[\]:*?/\\]", " ", name or "").strip().strip("'")
    return (clean or "Tabela")[:31]


def _column(index: int) -> str:
    letters = ""
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        letters = chr(65 + rest) + letters
    return letters


def xlsx_bytes(result: Result) -> bytes:
    strings: dict[str, int] = {}

    def shared(text: str) -> int:
        return strings.setdefault(_INVALID_XML.sub("", text), len(strings))

    lines = [[(c.title, True) for c in result.columns]]
    lines += [[(v, row.bold) for v in row.cells] for row in result.rows]
    xml_rows = []
    for r, line in enumerate(lines, start=1):
        cells = []
        for c, (value, bold) in enumerate(line):
            ref = f"{_column(c)}{r}"
            if value is None:
                continue
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                style = (3 if bold else 2) if isinstance(value, float) else (1 if bold else 0)
                cells.append(f'<c r="{ref}" s="{style}"><v>{value!r}</v></c>')
            else:
                cells.append(f'<c r="{ref}" t="s" s="{1 if bold else 0}">'
                             f'<v>{shared(format_value(value))}</v></c>')
        xml_rows.append(f'<row r="{r}">{"".join(cells)}</row>')
    sheet = (f'{_HEAD}<worksheet xmlns="{_MAIN}" xmlns:r="{_REL}">'
             f'<sheetData>{"".join(xml_rows)}</sheetData></worksheet>')
    sst = (f'{_HEAD}<sst xmlns="{_MAIN}" count="{len(strings)}" '
           f'uniqueCount="{len(strings)}">'
           + "".join(f'<si><t xml:space="preserve">{escape(s)}</t></si>' for s in strings)
           + "</sst>")
    name = escape(sheet_name(result.name), {'"': "&quot;"})
    workbook = (f'{_HEAD}<workbook xmlns="{_MAIN}" xmlns:r="{_REL}"><sheets>'
                f'<sheet name="{name}" sheetId="1" r:id="rId1"/></sheets></workbook>')
    workbook_rels = (
        f'{_HEAD}<Relationships xmlns="{_PKG_REL}">'
        f'<Relationship Id="rId1" Type="{_REL}/worksheet" Target="worksheets/sheet1.xml"/>'
        f'<Relationship Id="rId2" Type="{_REL}/styles" Target="styles.xml"/>'
        f'<Relationship Id="rId3" Type="{_REL}/sharedStrings" Target="sharedStrings.xml"/>'
        '</Relationships>')
    rels = (f'{_HEAD}<Relationships xmlns="{_PKG_REL}">'
            f'<Relationship Id="rId1" Type="{_REL}/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>')
    types = (
        f'{_HEAD}<Types xmlns="{_TYPES}">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
        'relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        f'<Override PartName="/xl/workbook.xml" ContentType="{_DOC}.sheet.main+xml"/>'
        f'<Override PartName="/xl/worksheets/sheet1.xml" '
        f'ContentType="{_DOC}.worksheet+xml"/>'
        f'<Override PartName="/xl/styles.xml" ContentType="{_DOC}.styles+xml"/>'
        f'<Override PartName="/xl/sharedStrings.xml" '
        f'ContentType="{_DOC}.sharedStrings+xml"/>'
        '</Types>')
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
        z.writestr("xl/styles.xml", _STYLES)
        z.writestr("xl/sharedStrings.xml", sst)
    return out.getvalue()


def write_xlsx(path: str, result: Result) -> None:
    with open(path, "wb") as f:
        f.write(xlsx_bytes(result))
