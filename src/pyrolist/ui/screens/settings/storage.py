from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from pyrolist.config.paths import AppDirs
from pyrolist.ui.screens.settings.components import SettingsRow, SettingsSection, page_title
from pyrolist.ui.widgets.ripple_button import RippleButton


class StorageSettingsScreen(QWidget):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(page_title("Almacenamiento"))

        usage = SettingsSection("Uso")
        usage.add_row(SettingsRow("Base de datos", "Historial y biblioteca local", self._metric(AppDirs.database)))
        usage.add_row(SettingsRow("Cache", "Imagenes y datos temporales", self._metric(AppDirs.cache)))
        usage.add_row(SettingsRow("Descargas", "Canciones guardadas offline", self._metric(AppDirs.downloads)))
        layout.addWidget(usage)

        actions = SettingsSection("Limpieza")
        clear_cache = RippleButton("Limpiar cache", "secondary")
        clear_cache.clicked.connect(self._clear_cache)
        actions.add_row(SettingsRow("Cache", "Elimina archivos temporales", clear_cache))
        clear_downloads = RippleButton("Eliminar descargas", "danger")
        clear_downloads.clicked.connect(self._clear_downloads)
        actions.add_row(SettingsRow("Descargas", "Elimina los archivos descargados", clear_downloads))
        layout.addWidget(actions)
        layout.addStretch()

    def _metric(self, path: Path) -> QLabel:
        label = QLabel(self._get_size(path))
        label.setStyleSheet("color: #A78BFA; background: transparent; font-weight: 700;")
        return label

    def _get_size(self, path: Path) -> str:
        if not path.exists():
            return "0 MB"
        total = sum(file.stat().st_size for file in path.rglob("*") if file.is_file())
        return f"{total / (1024 * 1024):.1f} MB"

    def _clear_cache(self) -> None:
        for file in AppDirs.cache.glob("*"):
            if file.is_file():
                file.unlink()

    def _clear_downloads(self) -> None:
        for file in AppDirs.downloads.glob("*"):
            if file.is_file():
                file.unlink()

