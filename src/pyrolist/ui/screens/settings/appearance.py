from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QVBoxLayout, QWidget

from pyrolist.ui.screens.settings.components import AccentColorPicker, SettingsRow, SettingsSection, page_title
from pyrolist.ui.widgets.animated_toggle import AnimatedToggle


class AppearanceSettingsScreen(QWidget):
    def __init__(self, settings, on_changed):
        super().__init__()
        self.settings = settings
        self.on_changed = on_changed
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(page_title("Apariencia"))

        theme = SettingsSection("Tema")
        picker = AccentColorPicker(self.settings.appearance.accent_color)
        picker.color_changed.connect(self._on_accent_changed)
        theme.add_row(SettingsRow("Color de acento", "Color principal de la interfaz", picker))

        dynamic = AnimatedToggle()
        dynamic.setChecked(self.settings.appearance.use_dynamic_color)
        dynamic.toggled.connect(lambda checked: self._set_appearance("use_dynamic_color", checked))
        theme.add_row(SettingsRow("Color dinámico", "Cambia el acento según el artwork actual", dynamic))

        mode = QComboBox()
        mode.addItems(["dark", "light", "system"])
        mode.setCurrentText(self.settings.appearance.theme_mode)
        mode.currentTextChanged.connect(lambda value: self._set_appearance("theme_mode", value))
        mode.setStyleSheet("""
            QComboBox {
                background-color: #1E1E38;
                color: #F1F0FF;
                border: 1px solid #2A2A4E;
                border-radius: 8px;
                padding: 6px 12px;
                font-family: Inter;
                font-size: 13px;
                min-width: 120px;
            }
            QComboBox:focus {
                border: 1px solid #A78BFA;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #1A1A2E;
                color: #F1F0FF;
                border: 1px solid #2A2A4E;
                border-radius: 8px;
                selection-background-color: #A78BFA;
                selection-color: #10101E;
            }
        """)
        theme.add_row(SettingsRow("Tema", "Modo visual preferido", mode))
        layout.addWidget(theme)

        interface = SettingsSection("Interfaz")
        compact = AnimatedToggle()
        compact.setChecked(self.settings.appearance.compact_sidebar)
        compact.toggled.connect(lambda checked: self._set_appearance("compact_sidebar", checked))
        interface.add_row(SettingsRow("Sidebar compacta", "Reduce la barra lateral a iconos", compact))

        blur = AnimatedToggle()
        blur.setChecked(self.settings.appearance.show_artwork_blur_bg)
        blur.toggled.connect(lambda checked: self._set_appearance("show_artwork_blur_bg", checked))
        interface.add_row(SettingsRow("Fondo difuminado", "Usa el artwork como atmósfera del reproductor", blur))
        layout.addWidget(interface)
        layout.addStretch()

    def _on_accent_changed(self, color: str) -> None:
        self.settings.appearance.accent_color = color
        self.on_changed(self.settings)

    def _set_appearance(self, key: str, value) -> None:
        setattr(self.settings.appearance, key, value)
        self.on_changed(self.settings)

