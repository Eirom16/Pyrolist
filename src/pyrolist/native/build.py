# src/pyrolist/native/build.py
"""
Compila fast_image.so para Pyrolist.
Uso: python -m pyrolist.native.build
  o: python src/pyrolist/native/build.py
"""
import subprocess
import shutil
import sys
from pathlib import Path

NATIVE_DIR = Path(__file__).parent


def check_gcc() -> bool:
    return shutil.which("gcc") is not None


def compile_native() -> bool:
    print("Compilando módulos nativos de Pyrolist...")

    if not check_gcc():
        print("✗ gcc no encontrado.")
        print("  Instala con:")
        print("    Arch/CachyOS: sudo pacman -S gcc")
        print("    Debian/Ubuntu: sudo apt install build-essential")
        print("    Fedora: sudo dnf install gcc")
        return False

    result = subprocess.run(
        ["make", "all"],
        cwd=NATIVE_DIR,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("✓ Módulos nativos compilados")
        print("  Reinicia Pyrolist para activar la aceleración")
        return True
    else:
        print("✗ Error de compilación:")
        print(result.stderr)
        print("  Pyrolist seguirá funcionando con Python puro")
        return False


if __name__ == "__main__":
    success = compile_native()
    sys.exit(0 if success else 1)
