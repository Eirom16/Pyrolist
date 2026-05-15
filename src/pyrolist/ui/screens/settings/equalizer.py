from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget

from pyrolist.config.themes import EQ_BAND_LABELS, EQ_PRESETS
from pyrolist.ui.design.fonts import AppFont
from pyrolist.ui.screens.settings.components import SettingsRow, SettingsSection, page_title
from pyrolist.ui.widgets.animated_toggle import AnimatedToggle
from pyrolist.ui.widgets.ripple_button import RippleButton


class EqBandSlider(QWidget):
    value_changed = Signal(int, float)

    def __init__(self, band_index: int, label: str, parent=None):
        super().__init__(parent)
        self.band_index = band_index
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.value_label = QLabel("0 dB")
        self.value_label.setFont(AppFont.caption(10))
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setStyleSheet("color: #6B6B9B; background: transparent;")
        layout.addWidget(self.value_label)

        self.slider = QSlider(Qt.Orientation.Vertical)
        self.slider.setRange(-120, 120)
        self.slider.setFixedSize(28, 180)
        self.slider.valueChanged.connect(self._on_value)
        layout.addWidget(self.slider, alignment=Qt.AlignmentFlag.AlignHCenter)

        freq = QLabel(label)
        freq.setFont(AppFont.caption(9))
        freq.setAlignment(Qt.AlignmentFlag.AlignCenter)
        freq.setStyleSheet("color: #4A4A6A; background: transparent;")
        layout.addWidget(freq)

    def _on_value(self, value: int) -> None:
        db = value / 10.0
        self.value_label.setText(f"{'+' if db > 0 else ''}{db:.1f} dB")
        self.value_label.setStyleSheet(f"color: {'#A78BFA' if db else '#6B6B9B'}; background: transparent;")
        self.value_changed.emit(self.band_index, db)

    def set_value(self, db: float) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(int(db * 10))
        self.slider.blockSignals(False)
        self._on_value(int(db * 10))


class EqualizerSettingsScreen(QWidget):
    def __init__(self, settings, on_changed):
        super().__init__()
        self.settings = settings
        self.on_changed = on_changed
        self.band_sliders: list[EqBandSlider] = []
        self._build_ui()
        self._load_from_settings()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(page_title("Ecualizador"))

        controls = SettingsSection("Control")
        enabled = AnimatedToggle()
        enabled.setChecked(self.settings.equalizer.enabled)
        enabled.toggled.connect(self._on_enabled_changed)
        controls.add_row(SettingsRow("Activado", "Aplica el ecualizador de 10 bandas", enabled))

        preset = QComboBox()
        preset.addItems(list(EQ_PRESETS.keys()))
        preset.setCurrentText(self.settings.equalizer.preset_name)
        preset.currentTextChanged.connect(self._on_preset_changed)
        controls.add_row(SettingsRow("Preset", "Curva base para ajustar rapido", preset))
        layout.addWidget(controls)

        preamp_section = SettingsSection("Ganancia")
        preamp_row = QWidget()
        row = QHBoxLayout(preamp_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        self.preamp_slider = QSlider(Qt.Orientation.Horizontal)
        self.preamp_slider.setRange(-120, 120)
        self.preamp_slider.valueChanged.connect(lambda value: (self._update_preamp_label(value), self._emit_eq()))
        self.preamp_value = QLabel("0.0 dB")
        self.preamp_value.setFont(AppFont.mono(12))
        self.preamp_value.setStyleSheet("color: #A78BFA; min-width: 60px; background: transparent;")
        row.addWidget(self.preamp_slider)
        row.addWidget(self.preamp_value)
        preamp_section.add_row(SettingsRow("Preamp", "Nivel general antes de las bandas", preamp_row))
        layout.addWidget(preamp_section)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: #16162A;
                border-radius: 18px;
                border: 1px solid rgba(167,139,250,0.08);
            }
        """)
        band_layout = QHBoxLayout(card)
        band_layout.setContentsMargins(24, 20, 24, 20)
        band_layout.setSpacing(12)
        for i, label in enumerate(EQ_BAND_LABELS):
            slider = EqBandSlider(i, label)
            slider.value_changed.connect(lambda index, db: self._emit_eq())
            self.band_sliders.append(slider)
            band_layout.addWidget(slider)
        layout.addWidget(card)

        reset = RippleButton("Reiniciar", "ghost")
        reset.clicked.connect(self._reset)
        layout.addWidget(reset, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addStretch()

    def _load_from_settings(self) -> None:
        eq = self.settings.equalizer
        self.preamp_slider.setValue(int(eq.preamp * 10))
        for i, gain in enumerate(eq.bands[:10]):
            self.band_sliders[i].set_value(gain)

    def _on_enabled_changed(self, checked: bool) -> None:
        self.settings.equalizer.enabled = checked
        self._emit_eq()

    def _on_preset_changed(self, preset_name: str) -> None:
        preamp, bands = EQ_PRESETS.get(preset_name, (0.0, [0.0] * 10))
        self.settings.equalizer.preset_name = preset_name
        self.preamp_slider.setValue(int(preamp * 10))
        for i, gain in enumerate(bands[:10]):
            self.band_sliders[i].set_value(gain)
        self._emit_eq()

    def _reset(self) -> None:
        self._on_preset_changed("Flat")

    def _update_preamp_label(self, value: int) -> None:
        db = value / 10.0
        self.preamp_value.setText(f"{'+' if db > 0 else ''}{db:.1f} dB")

    def _emit_eq(self) -> None:
        self.settings.equalizer.preamp = self.preamp_slider.value() / 10.0
        self.settings.equalizer.bands = [slider.slider.value() / 10.0 for slider in self.band_sliders]
        self.on_changed(self.settings)

