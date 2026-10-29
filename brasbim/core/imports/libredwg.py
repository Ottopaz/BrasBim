# SPDX-License-Identifier: LGPL-3.0-or-later
"""Conversor de DWG que vem com o BrasBim: o ``dwg2dxf`` do GNU LibreDWG
(``spec/ui/22-importar-desenho.md`` §2 e §8), sem Qt.

O LibreDWG é software livre (GPL‑3.0‑or‑later), feito a partir de especificação pública
do formato. O BrasBim não o liga ao seu código: chama o ``dwg2dxf.exe`` como programa à
parte. Os binários não ficam no repositório (a biblioteca tem 31 MB): ``install`` baixa
o pacote **oficial** da versão fixada em ``VERSION``, confere o SHA‑256 e guarda só os
três arquivos necessários (mais a licença) numa pasta do BrasBim. Nada é instalado no
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
BUNDLED = Path(__file__).resolve().parents[2] / "vendor" / "libredwg"
NOTICE = f"""GNU LibreDWG {VERSION} — dwg2dxf (conversor de DWG para DXF)

Licença: GNU General Public License, versão 3 ou posterior (GPL-3.0-or-later),
https://www.gnu.org/licenses/gpl-3.0.html. libiconv: GNU LGPL 2.1 ou posterior.

Estes arquivos vêm sem alteração do pacote oficial:
  {URL}
  SHA-256 {SHA256}
Código-fonte correspondente:
  {SOURCE_URL}
  https://www.gnu.org/software/libredwg/

O BrasBim chama o dwg2dxf.exe como programa separado (spec/ui 22 §2).
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
        for name in FILES:
            (folder / name).write_bytes(package.read(names[name]))
    (folder / "LEIA-ME.txt").write_text(NOTICE, encoding="utf-8")
    return str(folder / EXE)


def convert(exe: str, path: str, out: str) -> None:
    """``dwg2dxf`` de ``path`` para ``out``. O LibreDWG pula objetos que não sabe ler e
    avisa no stderr; vale o DXF gerado. Levanta ``RuntimeError`` se não gerou nada."""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with tempfile.TemporaryFile() as err:
        try:
            done = subprocess.run([exe, "-y", "-o", out, path], stdout=subprocess.DEVNULL,
                                  stderr=err, timeout=600, creationflags=flags,
                                  check=False)
        except (OSError, subprocess.SubprocessError) as e:
            raise RuntimeError(str(e)) from e
        if not Path(out).is_file() or Path(out).stat().st_size == 0:
            err.seek(0)
            lines = [t for t in err.read().decode("utf-8", "replace").splitlines()
                     if t.strip()]
            detail = lines[-1] if lines else f"código {done.returncode}"
            raise RuntimeError(detail)
