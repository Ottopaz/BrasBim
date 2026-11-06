# SPDX-License-Identifier: GPL-3.0-or-later
"""Monta o instalador do BrasBim para macOS (spec/ui 50 §4). Só roda num Mac; sem Mac, o
GitHub Actions monta (``.github/workflows/instalador-mac.yml``).

Uso, na raiz do repositório, com o ambiente de desenvolvimento ativo e o PyInstaller:

    python instalador/construir_mac.py           # tudo
    python instalador/construir_mac.py --sem-dmg  # só dist/BrasBim.app

Passos: (1) PyInstaller com instalador/brasbim_mac.spec em dist/BrasBim.app, (2)
``BrasBim.app/Contents/MacOS/BrasBim --verificar``, (3) conferência da assinatura ad hoc,
(4) imagem de disco ``dist/BrasBim-<versão>-macOS-<arquitetura>.dmg`` (hdiutil) com o
aplicativo, o atalho para Aplicativos, as licenças e o LEIA-ME.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "instalador"
ARCHS = {"arm64": "apple-silicon", "x86_64": "intel"}

README = """BrasBim {versao} para macOS ({arquitetura})

Instalar
  Arraste o BrasBim para a pasta Aplicativos.

Primeira abertura
  Esta versão ainda não é assinada nem autenticada pela Apple. Na primeira vez, o macOS
  avisa que não pode verificar o desenvolvedor. Para abrir:
  1. Abra o BrasBim uma vez (o aviso aparece; feche-o).
  2. Ajustes do Sistema > Privacidade e Segurança > role até "Segurança" e clique em
     "Abrir Mesmo Assim" ao lado do BrasBim. Confirme com a senha.
  Nas próximas vezes ele abre direto.

  Alternativa pelo Terminal:
    xattr -dr com.apple.quarantine /Applications/BrasBim.app

O que muda em relação ao Windows
  - DWG: importar e exportar DWG ainda é só no Windows (o conversor LibreDWG que o
    BrasBim usa é o do Windows). No Mac, use DXF.
  - Abrir um .ifc com clique duplo no Finder ainda não funciona; use Arquivo > Abrir.

Licença: GPL-3.0-or-later (aplicativo) e LGPL-3.0-or-later (núcleo); ver COPYING,
COPYING.LESSER e THIRD_PARTY_NOTICES.md.
Código, problemas e sugestões: https://github.com/Ottopaz/BrasBim
"""


def version() -> str:
    sys.path.insert(0, str(ROOT))
    from brasbim import __version__

    return __version__


def arch_name(machine: str | None = None) -> str:
    machine = machine or platform.machine()
    return ARCHS.get(machine, machine)


def dmg_name(number: str, machine: str | None = None) -> str:
    return f"BrasBim-{number}-macOS-{arch_name(machine)}.dmg"


def readme(number: str, machine: str | None = None) -> str:
    label = "Apple Silicon" if arch_name(machine) == "apple-silicon" else "Intel"
    return README.format(versao=number, arquitetura=label)


def run(*args, **kwargs) -> None:
    print("»", " ".join(str(a) for a in args), flush=True)
    subprocess.run([str(a) for a in args], check=True, **kwargs)


def main() -> int:
    if sys.platform != "darwin":
        print("construir_mac.py só roda no macOS (no GitHub: workflow instalador-mac).",
              file=sys.stderr)
        return 2
    number = version()
    print(f"BrasBim {number} · macOS {platform.mac_ver()[0]} · {platform.machine()}")
    # 1. PyInstaller
    run(sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--distpath", ROOT / "dist", "--workpath", ROOT / "build" / "pyinstaller-mac",
        HERE / "brasbim_mac.spec", cwd=ROOT)
    app = ROOT / "dist" / "BrasBim.app"
    # 2. teste de fumaça do programa congelado
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    result = subprocess.run([str(app / "Contents" / "MacOS" / "BrasBim"), "--verificar"],
                            env=env, timeout=600, check=False)
    if result.returncode != 0:
        print("a verificação do BrasBim.app falhou", file=sys.stderr)
        return 1
    print("BrasBim.app --verificar: ok")
    # 3. assinatura ad hoc (o PyInstaller assina; sem ela o Apple Silicon não abre)
    run("codesign", "--verify", "--deep", "--strict", "--verbose=2", app)
    if "--sem-dmg" in sys.argv[1:]:
        return 0
    # 4. imagem de disco
    out = ROOT / "dist" / dmg_name(number)
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "BrasBim"
        stage.mkdir()
        run("ditto", app, stage / "BrasBim.app")  # ditto preserva links e assinatura
        (stage / "Applications").symlink_to("/Applications")
        for name in ("COPYING", "COPYING.LESSER", "THIRD_PARTY_NOTICES.md"):
            shutil.copy2(ROOT / name, stage / name)
        (stage / "LEIA-ME.txt").write_text(readme(number), encoding="utf-8")
        out.unlink(missing_ok=True)
        run("hdiutil", "create", "-volname", f"BrasBim {number}", "-srcfolder", stage,
            "-fs", "HFS+", "-format", "UDZO", "-ov", out)
    run("hdiutil", "verify", out)
    print(f"pronto: dist/{out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
