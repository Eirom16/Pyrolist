# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path

block_cipher = None

# Detección de plataforma
is_win = sys.platform.startswith('win')
is_linux = sys.platform.startswith('linux')

# Configuración dinámica de compilación
# Linux: onefile = False (AppImage requiere estructura de carpeta para empaquetarse con appimagetool)
# Windows: onefile = True (ejecutable .exe standalone portable)
onefile = True if is_win else False
console_mode = False  # console = False / windowed = True (sin ventana de consola negra)

# Recolección segura de recursos (datas)
# Estructura del proyecto:
# assets/ -> recursos compartidos
# src/pyrolist/ -> paquete de código fuente
datas = [
    ("src/pyrolist/", "pyrolist"),
]

if os.path.exists("assets/icon.png"):
    datas.append(("assets/icon.png", "assets"))
if os.path.exists("assets/icon.ico"):
    datas.append(("assets/icon.ico", "assets"))
if os.path.exists("assets/fonts"):
    datas.append(("assets/fonts/", "assets/fonts"))

# Incluir archivos de localización de Python (locale/translations)
# ytmusicapi usa internamente gettext y necesita los archivos .mo/.po de locale.
# Sin estos archivos, la inicialización del cliente público falla con:
#   "[Errno 2] No translation file found for domain: 'base'"
# lo que causa que el home muestre "Explorar por género" en vez del feed real.
import importlib.util
_ytm_spec = importlib.util.find_spec("ytmusicapi")
if _ytm_spec and _ytm_spec.submodule_search_locations:
    _ytm_pkg = Path(_ytm_spec.submodule_search_locations[0])
    _ytm_locales = _ytm_pkg / "locales"
    if _ytm_locales.exists():
        datas.append((str(_ytm_locales), "ytmusicapi/locales"))
        
# Locale estándar de Python (fallback)
import locale as _locale_mod
_locale_dir = Path(_locale_mod.__file__).parent
_py_locale = _locale_dir.parent / "locale"  # Lib/locale en la stdlib
if not _py_locale.exists():
    # En algunos sistemas el directorio se llama 'localedata'
    _py_locale = _locale_dir.parent / "localedata"
if _py_locale.exists() and _py_locale.is_dir():
    datas.append((str(_py_locale), "locale"))

# Recolección dinámica de binarios (binaries)
# Copiamos explícitamente las librerías nativas de VLC que el workflow o usuario colocan en vlc_libs/
binaries = []
vlc_libs_dir = Path("vlc_libs")
if vlc_libs_dir.exists():
    # 1. Archivos en el directorio raíz de vlc_libs/ (.so o .dll)
    for f in vlc_libs_dir.glob("*"):
        if f.is_file() and (f.suffix in (".so", ".dll") or ".so." in f.name):
            binaries.append((str(f), "vlc_libs"))
    
    # 2. Plugins de VLC de forma recursiva (vlc_libs/plugins/*)
    plugins_dir = vlc_libs_dir / "plugins"
    if plugins_dir.exists():
        for f in plugins_dir.rglob("*"):
            if f.is_file() and (f.suffix in (".so", ".dll") or ".so." in f.name):
                # Mantener la estructura interna relativa a vlc_libs/
                rel_path = f.relative_to(vlc_libs_dir)
                binaries.append((str(f), str(Path("vlc_libs") / rel_path.parent)))

# Importaciones ocultas necesarias debido a carga dinámica en PySide6, SQLAlchemy, etc.
hiddenimports = [
    "vlc",
    "PySide6.QtSvg",
    "PySide6.QtMultimedia",
    "sqlalchemy.dialects.sqlite",
    "aiosqlite",
    "qasync",
    "pystray._xorg",
    "pystray._win32"
]

a = Analysis(
    ['src/pyrolist/main.py'],
    pathex=['src'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if onefile:
    # Windows EXE portable
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='Pyrolist',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=console_mode,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None,
    )
else:
    # Linux (One-Folder, que luego empaquetamos como AppImage)
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='Pyrolist',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=console_mode,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon='assets/icon.png' if os.path.exists('assets/icon.png') else None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='Pyrolist',
    )
