from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from loguru import logger


_LOADED = False


def _font_dirs() -> list[Path]:
    import sys
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        bundle_root = Path(sys._MEIPASS)
        return [
            bundle_root / "pyrolist" / "assets" / "fonts",
            bundle_root / "assets" / "fonts",
        ]
    root = Path(__file__).resolve().parents[4]
    package = Path(__file__).resolve().parents[2]
    return [
        package / "assets" / "fonts",  # Priorizar la ubicación correcta
        root / "assets" / "fonts",
    ]


def load_fonts() -> None:
    """Load bundled fonts if present, falling back to system fonts."""
    global _LOADED
    if _LOADED:
        return

    seen: set[Path] = set()
    for fonts_dir in _font_dirs():
        if not fonts_dir.exists():
            logger.debug(f"Font directory does not exist: {fonts_dir}")
            continue
        for path in sorted(fonts_dir.iterdir()):
            if path in seen or path.suffix.lower() not in {".ttf", ".otf"}:
                continue
            seen.add(path)
            fid = QFontDatabase.addApplicationFont(str(path))
            if fid == -1:
                logger.debug(f"Font failed to load: {path}")
            else:
                families = QFontDatabase.applicationFontFamilies(fid)
                logger.debug(
                    f"Loaded font {path.name}: {families}"
                )
                print(f"SUCCESS: Loaded font {path.name} -> {families}")

    _LOADED = True


class AppFont:
    FAMILY = "Nunito"
    FAMILY_BODY = "Inter"

    @staticmethod
    def display(size: int = 32) -> QFont:
        font = QFont(AppFont.FAMILY, size, QFont.Weight.ExtraBold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0)
        return font

    @staticmethod
    def heading(size: int = 20) -> QFont:
        return QFont(AppFont.FAMILY, size, QFont.Weight.Bold)

    @staticmethod
    def title(size: int = 16) -> QFont:
        return QFont(AppFont.FAMILY, size, QFont.Weight.Bold)

    @staticmethod
    def body(size: int = 14) -> QFont:
        return QFont(AppFont.FAMILY_BODY, size, QFont.Weight.Normal)

    @staticmethod
    def label(size: int = 12) -> QFont:
        return QFont(AppFont.FAMILY_BODY, size, QFont.Weight.Medium)

    @staticmethod
    def caption(size: int = 10) -> QFont:
        return QFont(AppFont.FAMILY_BODY, size, QFont.Weight.Normal)

    @staticmethod
    def mono(size: int = 13) -> QFont:
        font = QFont("JetBrains Mono", size, QFont.Weight.Medium)
        font.setStyleHint(QFont.StyleHint.Monospace)
        return font

