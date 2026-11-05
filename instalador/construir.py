# SPDX-License-Identifier: GPL-3.0-or-later
"""Monta o instalador do BrasBim para Windows (spec/ui 49 §4).

Uso, na raiz do repositório, com o ambiente de desenvolvimento ativo:

    python instalador/construir.py            # tudo
    python instalador/construir.py --sem-setup  # só a pasta dist/BrasBim

Passos: (1) conversor de DWG em brasbim/vendor (scripts/baixar_libredwg.py), (2)
PyInstaller com instalador/brasbim.spec em dist/BrasBim, (3) BrasBim.exe --verificar,
(4) Inno Setup (ISCC.exe), se estiver instalado, em dist/BrasBim-<versão>-Setup.exe.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "instalador"


def version() -> str:
    sys.path.insert(0, str(ROOT))
    from brasbim import __version__

    return __version__


def version_file(path: Path, number: str) -> None:
    """Recurso de versão do .exe (Propriedades > Detalhes no Windows)."""
    parts = [int(p) if p.isdigit() else 0 for p in number.split(".")][:4]
    parts += [0] * (4 - len(parts))
    t = tuple(parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={t}, prodvers={t}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('041604b0', [
    StringStruct('CompanyName', 'Contribuidores do BrasBim'),
    StringStruct('FileDescription', 'BrasBim - BIM livre e IFC-nativo'),
    StringStruct('FileVersion', '{number}'),
    StringStruct('InternalName', 'BrasBim'),
    StringStruct('LegalCopyright', 'GPL-3.0-or-later / LGPL-3.0-or-later'),
    StringStruct('OriginalFilename', 'BrasBim.exe'),
    StringStruct('ProductName', 'BrasBim'),
    StringStruct('ProductVersion', '{number}')])]),
        VarFileInfo([VarStruct('Translation', [0x0416, 1200])])]
)
""", encoding="utf-8")


def find_iscc() -> str | None:
    found = shutil.which("ISCC") or shutil.which("iscc")
    if found:
        return found
    for base in (os.environ.get("LOCALAPPDATA", ""), os.environ.get("ProgramFiles(x86)", ""),
                 os.environ.get("ProgramFiles", "")):
        for sub in ("Programs/Inno Setup 6", "Inno Setup 6"):
            path = Path(base) / sub / "ISCC.exe"
            if base and path.exists():
                return str(path)
    return None


def run(*args, **kwargs) -> None:
    print("»", " ".join(str(a) for a in args), flush=True)
    subprocess.run([str(a) for a in args], check=True, **kwargs)


def main() -> int:
    number = version()
    print(f"BrasBim {number}")
    # 1. conversor de DWG
    if not (ROOT / "brasbim" / "vendor" / "libredwg").exists():
        run(sys.executable, ROOT / "scripts" / "baixar_libredwg.py", cwd=ROOT)
    # 2. PyInstaller
    version_file(ROOT / "build" / "versao.txt", number)
    run(sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--distpath", ROOT / "dist", "--workpath", ROOT / "build" / "pyinstaller",
        HERE / "brasbim.spec", cwd=ROOT)
    exe = ROOT / "dist" / "BrasBim" / "BrasBim.exe"
    # 3. teste de fumaça do programa congelado
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    result = subprocess.run([str(exe), "--verificar"], env=env, cwd=exe.parent,
                            timeout=600, check=False)
    if result.returncode != 0:
        print("a verificação do BrasBim.exe falhou", file=sys.stderr)
        return 1
    print("BrasBim.exe --verificar: ok")
    # 4. Inno Setup
    if "--sem-setup" in sys.argv[1:]:
        return 0
    iscc = find_iscc()
    if iscc is None:
        print("Inno Setup 6 não encontrado: a pasta dist/BrasBim está pronta, mas o Setup "
              "não foi gerado (instale o Inno Setup 6 e rode de novo).", file=sys.stderr)
        return 2
    run(iscc, f"/DVersao={number}", HERE / "brasbim.iss", cwd=HERE)
    print(f"pronto: dist/BrasBim-{number}-Setup.exe")
    return 0


if __name__ == "__main__":
    sys.exit(main())
