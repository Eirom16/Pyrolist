from __future__ import annotations
import json
from pathlib import Path
from loguru import logger
from PySide6.QtCore import QObject, Signal

class TranslationManager(QObject):
    language_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_language = "es"
        self.translations: dict[str, str] = {}
        self.load_translations(self.current_language)

    def load_translations(self, lang_code: str) -> None:
        self.current_language = lang_code
        self.translations.clear()

        base_dir = Path(__file__).parent.parent
        locale_path = base_dir / "locales" / f"{lang_code}.json"

        if locale_path.exists():
            try:
                with open(locale_path, "r", encoding="utf-8") as f:
                    self.translations = json.load(f)
                logger.info(f"Idioma de Pyrolist cargado: {lang_code}")
            except Exception as e:
                logger.error(f"Error cargando idioma {lang_code}: {e}")
        else:
            logger.warning(f"No se encontró archivo de traducción para '{lang_code}' en: {locale_path}")

        self.language_changed.emit(lang_code)

    def translate(self, text: str) -> str:
        if not text:
            return ""
        return self.translations.get(text, text)


_manager = TranslationManager()


def _(text: str) -> str:
    """Translate the given text dynamically."""
    return _manager.translate(text)


def set_language(lang_code: str) -> None:
    """Switch active translation dictionary and emit signal."""
    _manager.load_translations(lang_code)
