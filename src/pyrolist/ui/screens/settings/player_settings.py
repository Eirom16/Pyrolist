from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QSlider, QVBoxLayout, QWidget

from pyrolist.ui.design.fonts import AppFont
from pyrolist.ui.screens.settings.components import SettingsRow, SettingsSection, page_title
from pyrolist.ui.widgets.animated_toggle import AnimatedToggle


class PlayerSettingsScreen(QWidget):
    def __init__(self, settings, on_changed):
        super().__init__()
        self.settings = settings
        self.on_changed = on_changed
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(page_title("Reproductor"))

        audio = SettingsSection("Audio")
        self.volume_value = QLabel(f"{self.settings.player.volume}%")
        self.volume_value.setFont(AppFont.mono(12))
        self.volume_value.setStyleSheet("color: #A78BFA; min-width: 48px; background: transparent;")
        volume = QSlider(Qt.Orientation.Horizontal)
        volume.setRange(0, 200)
        volume.setValue(self.settings.player.volume)
        volume.setMinimumWidth(180)
        volume.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none;
                height: 6px;
                background: #1E1E38;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #A78BFA;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                border: 2px solid #A78BFA;
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #A78BFA;
                border-color: #FFFFFF;
            }
        """)
        volume.valueChanged.connect(self._on_volume_changed)
        row_widget = QWidget()
        from PySide6.QtWidgets import QHBoxLayout
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)
        row_layout.addWidget(volume)
        row_layout.addWidget(self.volume_value)
        audio.add_row(SettingsRow("Volumen", "Volumen inicial del reproductor", row_widget))

        audio.add_row(self._toggle_row("Normalizar volumen", "Iguala el volumen entre canciones", "normalize_audio"))
        audio.add_row(self._toggle_row("Saltar silencios", "Omite fragmentos silenciosos", "skip_silence"))
        audio.add_row(self._toggle_row("Crossfade", "Transicion suave entre canciones", "crossfade_enabled"))
        audio.add_row(self._toggle_row("Reproduccion sin gaps", "Evita pausas entre canciones compatibles", "gapless_playback"))
        audio.add_row(self._toggle_row("Reanudar al iniciar", "Continua la ultima sesion al abrir la app", "resume_on_startup"))
        audio.add_row(self._toggle_row("Parar al cerrar", "Detiene la reproduccion al cerrar Pyrolist", "stop_on_close"))
        layout.addWidget(audio)
        layout.addStretch()

    def _toggle_row(self, title: str, description: str, key: str) -> SettingsRow:
        toggle = AnimatedToggle()
        toggle.setChecked(getattr(self.settings.player, key))
        toggle.toggled.connect(lambda checked, k=key: self._set_player(k, checked))
        return SettingsRow(title, description, toggle)

    def _on_volume_changed(self, value: int) -> None:
        self.volume_value.setText(f"{value}%")
        self._set_player("volume", value)

    def _set_player(self, key: str, value) -> None:
        setattr(self.settings.player, key, value)
        self.on_changed(self.settings)

