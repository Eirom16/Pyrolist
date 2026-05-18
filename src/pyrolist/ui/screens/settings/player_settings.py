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
        
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 200)
        self.volume.setValue(self.settings.player.volume)
        self.volume.setMinimumWidth(180)
        self.volume.valueChanged.connect(self._on_volume_changed)

        row_widget = QWidget()
        from PySide6.QtWidgets import QHBoxLayout
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)
        row_layout.addWidget(self.volume)
        row_layout.addWidget(self.volume_value)
        audio.add_row(SettingsRow("Volumen", "Volumen inicial del reproductor", row_widget))

        audio.add_row(self._toggle_row("Normalizar volumen", "Iguala el volumen entre canciones", "normalize_audio"))
        audio.add_row(self._toggle_row("Saltar silencios", "Omite fragmentos silenciosos", "skip_silence"))
        audio.add_row(self._toggle_row("Crossfade", "Transicion suave entre canciones", "crossfade_enabled"))
        audio.add_row(self._toggle_row("Reproduccion sin gaps", "Evita pausas entre canciones compatibles", "gapless_playback"))
        audio.add_row(self._toggle_row("Reanudar al iniciar", "Continua la ultima sesion al abrir la app", "resume_on_startup"))
        audio.add_row(self._toggle_row("Parar al cerrar", "Detiene la reproduccion al cerrar Pyrolist", "stop_on_close"))

        # Sleep Timer combobox using GlassComboBox
        from pyrolist.ui.widgets.glass_combobox import GlassComboBox
        self.sleep_timer_combo = GlassComboBox()
        self.sleep_timer_combo.addItems([
            "Apagado",
            "5 minutos",
            "15 minutos",
            "30 minutos",
            "45 minutos",
            "60 minutos"
        ])
        self.sleep_timer_map = {
            0: "Apagado",
            5: "5 minutos",
            15: "15 minutos",
            30: "30 minutos",
            45: "45 minutos",
            60: "60 minutos"
        }
        self.sleep_timer_reverse_map = {v: k for k, v in self.sleep_timer_map.items()}
        
        current_min = getattr(self.settings.player, "sleep_timer_minutes", 0)
        self.sleep_timer_combo.setCurrentText(self.sleep_timer_map.get(current_min, "Apagado"))
        self.sleep_timer_combo.currentTextChanged.connect(self._on_sleep_timer_changed)
        audio.add_row(SettingsRow("Temporizador de apagado", "Pausa la musica despues del tiempo seleccionado", self.sleep_timer_combo))

        layout.addWidget(audio)
        layout.addStretch()
        
        self._update_player_styles()

    def _on_sleep_timer_changed(self, text: str) -> None:
        mins = self.sleep_timer_reverse_map.get(text, 0)
        self._set_player("sleep_timer_minutes", mins)

    def update_fields(self) -> None:
        current_min = getattr(self.settings.player, "sleep_timer_minutes", 0)
        self.sleep_timer_combo.blockSignals(True)
        self.sleep_timer_combo.setCurrentText(self.sleep_timer_map.get(current_min, "Apagado"))
        self.sleep_timer_combo.blockSignals(False)

        # Re-read volume setting
        self.volume.blockSignals(True)
        self.volume.setValue(self.settings.player.volume)
        self.volume_value.setText(f"{self.settings.player.volume}%")
        self.volume.blockSignals(False)

    def _toggle_row(self, title: str, description: str, key: str) -> SettingsRow:
        toggle = AnimatedToggle()
        toggle.setChecked(getattr(self.settings.player, key))
        toggle.toggled.connect(lambda checked, k=key: self._set_player(k, checked))
        return SettingsRow(title, description, toggle)

    def _update_player_styles(self) -> None:
        from pyrolist.ui.design import tokens
        if hasattr(self, "volume_value") and self.volume_value:
            self.volume_value.setStyleSheet(f"color: {tokens.CURRENT.accent}; min-width: 48px; background: transparent;")

    def changeEvent(self, event) -> None:
        from PySide6.QtCore import QEvent
        if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
            if not getattr(self, '_in_style_change', False):
                self._in_style_change = True
                try:
                    self._update_player_styles()
                finally:
                    self._in_style_change = False
        super().changeEvent(event)

    def _on_volume_changed(self, value: int) -> None:
        self.volume_value.setText(f"{value}%")
        self._set_player("volume", value)

    def _set_player(self, key: str, value) -> None:
        setattr(self.settings.player, key, value)
        self.on_changed(self.settings)

