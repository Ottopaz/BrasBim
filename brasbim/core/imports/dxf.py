# SPDX-License-Identifier: LGPL-3.0-or-later
"""Importar desenho DXF ou DWG como referência 2D (``spec/ui/22-importar-desenho.md``).

O DXF é lido com o ezdxf (formato com especificação pública). O DWG é convertido para
DXF por um programa à parte: o ``dwg2dxf`` do GNU LibreDWG que vem com o BrasBim
(``libredwg``, baixado na primeira vez) ou, se o usuário já tiver, o ODA File Converter
(§2, §8).

Fluxo: ``read`` (arquivo → ``Drawing``, nas unidades do arquivo) e ``import_drawing``
(→ transação com uma anotação ``reference2d`` por camada, em metros).
"""

from __future__ import annotations

import glob
import logging
import math
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from brasbim.core import guid
from brasbim.core.document import Document, OpError
from brasbim.core.imports import libredwg
from brasbim.core.ops import Op, Transaction

log = logging.getLogger(__name__)

# $INSUNITS do cabeçalho do DXF → metros por unidade (só as de obra).
UNITS = {"mm": 0.001, "cm": 0.01, "m": 1.0}
_INSUNITS = {4: "mm", 5: "cm", 6: "m"}
FAR = 10_000.0  # m: desenho mais longe que isso da origem vem para perto dela (§3)
CHORD = 0.01  # m: desvio máximo ao trocar arcos e curvas por segmentos
CURVES = ("LINE", "LWPOLYLINE", "POLYLINE", "ARC", "CIRCLE", "ELLIPSE", "SPLINE")


@dataclass
class Layer:
    lines: list = field(default_factory=list)  # {"points", "closed", "z"}
    texts: list = field(default_factory=list)  # {"at", "text", "height", "angle"}
    points: list = field(default_factory=list)  # {"at", "z"}

    def __len__(self) -> int:
        return len(self.lines) + len(self.texts) + len(self.points)


@dataclass
class Drawing:
    source: str
    unit: str | None  # do cabeçalho; None = sem unidade
    layers: dict[str, Layer]

    def bounds(self) -> tuple[float, float, float, float] | None:
        xs, ys = [], []
        for layer in self.layers.values():
            for line in layer.lines:
                xs += [p[0] for p in line["points"]]
                ys += [p[1] for p in line["points"]]
            for item in (*layer.texts, *layer.points):
                xs.append(item["at"][0])
                ys.append(item["at"][1])
        return (min(xs), min(ys), max(xs), max(ys)) if xs else None


# --- DWG → DXF -------------------------------------------------------------------------------


def _oda_path() -> str | None:
    """ODAFileConverter.exe na instalação padrão (a pasta tem a versão no nome)."""
    import ezdxf

    configured = ezdxf.options.get("odafc-addon", "win_exec_path").strip('"')
    if configured and Path(configured).is_file():
        return configured
    for root in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")):
        found = sorted(glob.glob(os.path.join(root, "ODA", "ODAFileConverter*",
                                              "ODAFileConverter.exe")))
        if found:
            return found[-1]
    return shutil.which("ODAFileConverter")


def _system_dwg2dxf() -> str | None:
    return shutil.which("dwg2dxf")


def converter() -> str | None:
    """Nome do conversor de DWG disponível, ou None (§8: o ODA só se já instalado)."""
    if _oda_path():
        return "ODA File Converter"
    if libredwg.find() or _system_dwg2dxf():
        return "LibreDWG"
    return None


class MissingConverter(OpError):
    """Não há conversor: a interface oferece baixar o LibreDWG (§8)."""


NO_CONVERTER = (f"para abrir DWG, o BrasBim usa o conversor livre LibreDWG, que ainda não "
                f"foi baixado ({libredwg.SIZE_MB} MB); ou salve o arquivo como DXF no "
                "programa de CAD")


def dwg_to_dxf(path: str, folder: str) -> str:
    """Converte o DWG para um DXF em ``folder`` com o conversor à parte (§2)."""
    out = str(Path(folder) / (Path(path).stem + ".dxf"))
    oda = _oda_path()
    exe = None if oda else (libredwg.find() or _system_dwg2dxf())
    if not oda and not exe:
        raise MissingConverter(NO_CONVERTER)
    try:
        if oda:
            import ezdxf
            from ezdxf.addons import odafc

            ezdxf.options.set("odafc-addon", "win_exec_path", oda)
            ezdxf.options.set("odafc-addon", "unix_exec_path", oda)
            odafc.convert(path, out, version="R2018", replace=True)
        else:
            libredwg.convert(exe, path, out)
    except Exception as e:  # erros do conversor (arquivo inválido, versão não lida)
        raise OpError(f"o conversor não conseguiu abrir {Path(path).name}: {e}") from e
    if not Path(out).is_file():
        raise OpError(f"o conversor não gerou o DXF de {Path(path).name}")
    return out


# --- leitura ---------------------------------------------------------------------------------


def _constant_z(zs) -> float | None:
    zs = list(zs)
    if zs and max(zs) - min(zs) < 1e-6:
        return float(zs[0])
    return None


def _clean(points) -> list[list[float]]:
    out = []
    for p in points:
        q = [float(p[0]), float(p[1])]
        if not out or math.dist(q, out[-1]) > 1e-9:
            out.append(q)
    return out


def _exploded(entities, parent: str | None = None, depth: int = 0):
    """(entidade, camada) com os blocos explodidos; o que está na camada "0" dentro de um
    bloco fica na camada da inserção (convenção do DXF)."""
    for e in entities:
        layer = e.dxf.get("layer", "0")
        if parent is not None and layer == "0":
            layer = parent
        if e.dxftype() in ("INSERT", "DIMENSION") and depth < 16:
            import ezdxf

            try:
                yield from _exploded(e.virtual_entities(), layer, depth + 1)
            except (ezdxf.DXFError, ValueError, TypeError, AttributeError) as error:
                log.debug("bloco não explodido (%s): %s", e.dxftype(), error)
        else:
            yield e, layer


def read(path: str) -> Drawing:
    """Lê o DXF (ou converte o DWG e lê): linhas, polilinhas, arcos, círculos, elipses e
    curvas viram polilinhas; textos e pontos ficam; blocos são explodidos (§3)."""
    import ezdxf
    from ezdxf import path as ezpath
    from ezdxf import recover

    source = Path(path).name
    with tempfile.TemporaryDirectory() as folder:
        dxf_path = dwg_to_dxf(path, folder) if path.lower().endswith(".dwg") else path
        try:
            doc, _ = recover.readfile(dxf_path)
        except (OSError, ezdxf.DXFStructureError) as e:
            raise OpError(f"não foi possível ler {source}: {e}") from e
    unit = _INSUNITS.get(int(doc.header.get("$INSUNITS", 0) or 0))
    chord = CHORD / UNITS.get(unit or "m", 1.0)
    layers: dict[str, Layer] = {}
    for e, name in _exploded(doc.modelspace()):
        kind = e.dxftype()
        layer = layers.setdefault(name, Layer())
        try:
            if kind in CURVES:
                p = ezpath.make_path(e)
                pts = list(p.flattening(chord))
                closed = bool(p.is_closed) or bool(getattr(e, "closed", False)) or \
                    kind in ("CIRCLE",)
                xy = _clean(pts)
                if closed and len(xy) > 2 and math.dist(xy[0], xy[-1]) < 1e-9:
                    xy.pop()
                if len(xy) >= 2:
                    layer.lines.append({"points": xy, "closed": closed and len(xy) > 2,
                                        "z": _constant_z(v.z for v in pts)})
            elif kind in ("TEXT", "MTEXT"):
                text = e.plain_text() if kind == "MTEXT" else e.dxf.text
                if text and text.strip():
                    at = e.dxf.insert
                    height = e.dxf.get("char_height" if kind == "MTEXT" else "height", 1.0)
                    layer.texts.append({"at": [float(at.x), float(at.y)],
                                        "text": text.strip(), "height": float(height),
                                        "angle": float(e.dxf.get("rotation", 0.0))})
            elif kind == "POINT":
                at = e.dxf.location
                layer.points.append({"at": [float(at.x), float(at.y)],
                                     "z": float(at.z)})
        except (AttributeError, ValueError, TypeError, ezdxf.DXFError):
            continue  # entidade que não dá para trazer: segue com as outras
    return Drawing(source, unit, {k: v for k, v in layers.items() if len(v)})


def default_offset(drawing: Drawing, unit: str) -> tuple[float, float]:
    """Desenho longe da origem (coordenadas UTM de levantamento) vem para perto dela:
    o canto inferior esquerdo vai para (0, 0) (§3)."""
    box = drawing.bounds()
    if box is None:
        return (0.0, 0.0)
    scale = UNITS[unit]
    if max(abs(c) for c in box) * scale > FAR:
        return (box[0], box[1])
    return (0.0, 0.0)


def import_drawing(doc: Document, storey, drawing: Drawing, unit: str,
                   offset: tuple[float, float] = (0.0, 0.0), layers=None,
                   group: str = "Levantamento") -> Transaction:
    """Uma anotação ``reference2d`` por camada escolhida, em metros, com ``offset`` (nas
    unidades do arquivo) levado para a origem do pavimento."""
    if unit not in UNITS:
        raise OpError(f"unidade inválida: {unit!r}")
    scale = UNITS[unit]
    ox, oy = offset

    def m(p):
        return [round((p[0] - ox) * scale, 6), round((p[1] - oy) * scale, 6)]

    def z(value):
        return None if value is None else round(value * scale, 6)

    storey_id = storey if isinstance(storey, str) else storey.GlobalId
    doc.get(storey_id, "IfcBuildingStorey")
    ops = []
    for name in sorted(drawing.layers):
        if layers is not None and name not in layers:
            continue
        layer = drawing.layers[name]
        data = {"storey": storey_id, "name": f"{group} – {name}", "source": drawing.source,
                "layer": name,
                "lines": [{"points": [m(p) for p in line["points"]],
                           "closed": line["closed"], "z": z(line["z"])}
                          for line in layer.lines],
                "texts": [{**t, "at": m(t["at"]), "height": round(t["height"] * scale, 6)}
                          for t in layer.texts],
                "points": [{"at": m(p["at"]), "z": z(p["z"])} for p in layer.points]}
        ops.append(Op("reference2d.create", guid.new(), data=data))
    if not ops:
        raise OpError("nenhuma camada escolhida tem linhas, textos ou pontos")
    return Transaction(f"Importar {drawing.source}", ops)
