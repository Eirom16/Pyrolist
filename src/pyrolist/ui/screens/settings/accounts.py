from __future__ import annotations

from PySide6.QtWidgets import QLineEdit, QVBoxLayout, QWidget

from pyrolist.config.paths import AppDirs
from pyrolist.ui.screens.settings.components import SettingsRow, SettingsSection, page_title
from pyrolist.ui.widgets.animated_toggle import AnimatedToggle
from pyrolist.ui.widgets.ripple_button import RippleButton


class AccountsSettingsScreen(QWidget):
    def __init__(self, yt_client, settings, on_changed):
        super().__init__()
        self.yt = yt_client
        self.settings = settings
        self.on_changed = on_changed
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(page_title("Cuentas"))

        yt_section = SettingsSection("YouTube Music")
        login = RippleButton("Conectar cuenta", "primary")
        login.clicked.connect(self._on_browser_login)
        logout = RippleButton("Cerrar sesion", "danger")
        logout.clicked.connect(self._on_logout)
        yt_section.add_row(SettingsRow("Cuenta de Google", "Autoriza YouTube Music en el navegador", login))
        yt_section.add_row(SettingsRow("Sesion local", "Elimina credenciales guardadas en este equipo", logout))
        layout.addWidget(yt_section)

        lastfm = SettingsSection("Last.fm")
        enabled = AnimatedToggle()
        enabled.setChecked(self.settings.integrations.lastfm_enabled)
        enabled.toggled.connect(lambda checked: self._set_integration("lastfm_enabled", checked))
        lastfm.add_row(SettingsRow("Scrobbling", "Registra las canciones escuchadas", enabled))
        self.lastfm_api_key = self._line_edit(self.settings.integrations.lastfm_api_key, "API Key")
        self.lastfm_api_key.editingFinished.connect(lambda: self._set_integration("lastfm_api_key", self.lastfm_api_key.text()))
        lastfm.add_row(SettingsRow("API Key", "Credencial publica de Last.fm", self.lastfm_api_key))
        self.lastfm_api_secret = self._line_edit(self.settings.integrations.lastfm_api_secret, "API Secret")
        self.lastfm_api_secret.editingFinished.connect(lambda: self._set_integration("lastfm_api_secret", self.lastfm_api_secret.text()))
        lastfm.add_row(SettingsRow("API Secret", "Credencial privada de Last.fm", self.lastfm_api_secret))
        layout.addWidget(lastfm)

        discord = SettingsSection("Discord")
        rpc = AnimatedToggle()
        rpc.setChecked(self.settings.integrations.discord_rpc_enabled)
        rpc.toggled.connect(lambda checked: self._set_integration("discord_rpc_enabled", checked))
        discord.add_row(SettingsRow("Rich Presence", "Muestra lo que escuchas en tu perfil", rpc))
        layout.addWidget(discord)
        layout.addStretch()

    def _line_edit(self, value: str, placeholder: str) -> QLineEdit:
        line = QLineEdit()
        line.setText(value)
        line.setPlaceholderText(placeholder)
        line.setMinimumWidth(220)
        return line

    def _on_browser_login(self) -> None:
        from pyrolist.ui.dialogs.login_dialog import WebLoginDialog
        dialog = WebLoginDialog(self)
        dialog.login_successful.connect(self._handle_login_success)
        dialog.exec()

    def _handle_login_success(self, avatar_url: str = "") -> None:
        if self.yt:
            self.yt.reload_auth()

    def _on_logout(self) -> None:
        auth_file = AppDirs.config / "headers_auth.json"
        if auth_file.exists():
            auth_file.unlink()
        self.on_changed(self.settings)

    def _set_integration(self, key: str, value) -> None:
        setattr(self.settings.integrations, key, value)
        self.on_changed(self.settings)

