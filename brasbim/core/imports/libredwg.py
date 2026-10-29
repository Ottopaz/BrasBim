# SPDX-License-Identifier: LGPL-3.0-or-later
"""Conversor de DWG que vem com o BrasBim: o ``dwg2dxf`` do GNU LibreDWG
(``spec/ui/22-importar-desenho.md`` §2 e §8) e, para exportar, o ``dxf2dwg`` do mesmo
pacote (``spec/ui/41-dwg-solidos-perfil-complexo.md`` §2), sem Qt.

O LibreDWG é software livre (GPL‑3.0‑or‑later), feito a partir de especificação pública
do formato. O BrasBim não o liga ao seu código: chama o ``dwg2dxf.exe`` como programa à
parte. Os binários não ficam no repositório (a biblioteca tem 31 MB): ``install`` baixa
o pacote **oficial** da versão fixada em ``VERSION``, confere o SHA‑256 e guarda só os
arquivos necessários (os dois programas, as duas bibliotecas e a licença) numa pasta do
BrasBim. Nada é instalado no
sistema.

Pastas procuradas (``folders``): ``brasbim/vendor/libredwg`` (o instalador do BrasBim põe
ali, com ``scripts/baixar_libredwg.py``) e a pasta de dados do usuário
(``%LOCALAPPDATA%/BrasBim/libredwg``), onde o aplicativo baixa quando falta.
"""

from __future__ import annotations

import hashlib
import io
import os
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

VERSION = "0.14"
URL = (f"https://github.com/LibreDWG/libredwg/releases/download/{VERSION}/"
       f"libredwg-{VERSION}-win64.zip")
SHA256 = "1ad7e15344d20b3426c3435b078d82fb84b35062815946b2cca9c5fc9810fea8"
SOURCE_URL = (f"https://github.com/LibreDWG/libredwg/releases/download/{VERSION}/"
              f"libredwg-{VERSION}.tar.xz")
SIZE_MB = 12  # tamanho do download, para o aviso
FILES = ("dwg2dxf.exe", "libredwg-0.dll", "libiconv-2.dll")
EXE = FILES[0]
WRITER = "dxf2dwg.exe"  # grava DWG 2000 (AC1015), o que o LibreDWG grava bem
BUNDLED = Path(__file__).resolve().parents[2] / "vendor" / "libredwg"
NOTICE = f"""GNU LibreDWG {VERSION} — dwg2dxf e dxf2dwg (conversores entre DWG e DXF)

Licença: GNU General Public License, versão 3 ou posterior (GPL-3.0-or-later),
https://www.gnu.org/licenses/gpl-3.0.html. libiconv: GNU LGPL 2.1 ou posterior.

Estes arquivos vêm sem alteração do pacote oficial:
  {URL}
  SHA-256 {SHA256}
Código-fonte correspondente:
  {SOURCE_URL}
  https://www.gnu.org/software/libredwg/

O BrasBim chama o dwg2dxf.exe e o dxf2dwg.exe como programas separados (spec/ui 22
§2 e spec/ui 41 §2).
"""


def user_folder() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME") \
        or str(Path.home() / ".local" / "share")
    return Path(base) / "BrasBim" / "libredwg"


def folders() -> list[Path]:
    return [BUNDLED, user_folder()]


def supported() -> bool:
    """Só há pacote pronto para Windows; nos outros sistemas usa-se o ``dwg2dxf`` do
    sistema (pacote ``libredwg`` das distribuições)."""
    return sys.platform == "win32"


def find() -> str | None:
    """Caminho do ``dwg2dxf.exe`` do BrasBim, se já estiver numa das pastas."""
    for folder in folders():
        if all((folder / name).is_file() for name in FILES):
            return str(folder / EXE)
    return None


def find_writer() -> str | None:
    """Caminho do ``dxf2dwg.exe`` do BrasBim (para exportar DWG), se já estiver numa das
    pastas. Quem baixou antes da exportação tem só o ``dwg2dxf``: baixa de novo."""
    for folder in folders():
        if all((folder / name).is_file() for name in (WRITER, *FILES[1:])):
            return str(folder / WRITER)
    return None


def install(folder: Path | None = None, data: bytes | None = None) -> str:
    """Baixa o pacote oficial (ou usa ``data``), confere o SHA‑256 e extrai os arquivos
    para ``folder`` (padrão: a pasta do usuário). Devolve o caminho do ``dwg2dxf.exe``.
    Levanta ``RuntimeError`` com a explicação se algo falhar."""
    folder = Path(folder or user_folder())
    if data is None:
        try:
            with urllib.request.urlopen(URL, timeout=60) as response:
                data = response.read()
        except OSError as e:
            raise RuntimeError(f"não foi possível baixar o LibreDWG ({e}); confira a "
                               "conexão com a internet") from e
    digest = hashlib.sha256(data).hexdigest()
    if digest != SHA256:
        raise RuntimeError("o pacote do LibreDWG baixado não confere com o esperado "
                           f"(SHA-256 {digest}); nada foi instalado")
    with zipfile.ZipFile(io.BytesIO(data)) as package:
        names = {Path(n).name: n for n in package.namelist()}
        missing = [n for n in FILES if n not in names]
        if missing:
            raise RuntimeError(f"o pacote do LibreDWG não tem {', '.join(missing)}")
        folder.mkdir(parents=True, exist_ok=True)
        for name in (*FILES, WRITER):
            if name in names:  # o pacote oficial tem o dxf2dwg; sem ele, só se lê DWG
                (folder / name).write_bytes(package.read(names[name]))
    (folder / "LEIA-ME.txt").write_text(NOTICE, encoding="utf-8")
    return str(folder / EXE)


def _run(args: list[str], out: str) -> None:
    """Roda o conversor; levanta ``RuntimeError`` com a última linha do stderr se não
    gerou ``out``."""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with tempfile.TemporaryFile() as err:
        try:
            done = subprocess.run(args, stdout=subprocess.DEVNULL, stderr=err, timeout=600,
                                  creationflags=flags, check=False)
        except (OSError, subprocess.SubprocessError) as e:
            raise RuntimeError(str(e)) from e
        if not Path(out).is_file() or Path(out).stat().st_size == 0:
            err.seek(0)
            lines = [t for t in err.read().decode("utf-8", "replace").splitlines()
                     if t.strip()]
            detail = lines[-1] if lines else f"código {done.returncode}"
            raise RuntimeError(detail)


def write_dwg(exe: str, dxf_path: str, out: str) -> None:
    """``dxf2dwg`` de ``dxf_path`` para ``out`` (DWG 2000). Apaga ``out`` antes: o
    programa não sobrescreve sem ``-y`` e, se falhar, não fica o arquivo velho."""
    Path(out).unlink(missing_ok=True)
    _run([exe, "-y", "--as", "r2000", "-o", out, dxf_path], out)


def convert(exe: str, path: str, out: str) -> None:
    """``dwg2dxf`` de ``path`` para ``out``. O LibreDWG pula objetos que não sabe ler e
    avisa no stderr; vale o DXF gerado. Levanta ``RuntimeError`` se não gerou nada."""
    _run([exe, "-y", "-o", out, path], out)
