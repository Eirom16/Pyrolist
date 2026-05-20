from __future__ import annotations

from PySide6.QtWidgets import QLineEdit, QVBoxLayout, QWidget

from pyrolist.config.paths import AppDirs
from pyrolist.ui.screens.settings.components import SettingsRow, SettingsSection, page_title
from pyrolist.ui.widgets.animated_toggle import AnimatedToggle
from pyrolist.ui.widgets.ripple_button import RippleButton


class AccountsSettingsScreen(QWidget):
    def __init__(self, yt_client, settings, on_changed, on_auth_changed=None):
        super().__init__()
        self._yt = yt_client
        self.settings = settings
        self.on_changed = on_changed
        self.on_auth_changed = on_auth_changed
        self._build_ui()

    @property
    def yt(self):
        return self._yt

    @yt.setter
    def yt(self, client):
        self._yt = client
        self._update_yt_row()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(page_title("Cuentas"))

        self.yt_section = SettingsSection("YouTube Music")
        layout.addWidget(self.yt_section)
        self._update_yt_row()

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

    def _update_yt_row(self) -> None:
        if not hasattr(self, "yt_section"):
            return
        
        # Clear existing items in yt_section's card layout
        card_layout = self.yt_section.card_layout
        while card_layout.count():
            item = card_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        is_auth = self._yt and self._yt.is_authenticated
        if is_auth:
            logout = RippleButton("Cerrar sesión", "danger")
            logout.clicked.connect(self._on_logout)
            row = SettingsRow("Cuenta Conectada", "Has iniciado sesión en YouTube Music", logout)
            card_layout.addWidget(row)
        else:
            login = RippleButton("Conectar cuenta", "primary")
            login.clicked.connect(self._on_browser_login)
            row = SettingsRow("Cuenta de Google", "Autoriza YouTube Music en el navegador", login)
            card_layout.addWidget(row)

    def _line_edit(self, value: str, placeholder: str) -> QLineEdit:
        line = QLineEdit()
        line.setText(value)
        line.setPlaceholderText(placeholder)
        line.setMinimumWidth(220)
        if not hasattr(self, "_line_edits"):
            self._line_edits = []
        self._line_edits.append(line)
        self._update_line_edit_style(line)
        return line

    def _update_line_edit_style(self, line: QLineEdit) -> None:
        from pyrolist.ui.design import tokens
        line.setStyleSheet(f"""
            QLineEdit {{
                background-color: {tokens.CURRENT.bg_elevated};
                color: {tokens.CURRENT.text_primary};
                border: 1px solid {tokens.CURRENT.border};
                border-radius: 8px;
                padding: 6px 12px;
                font-family: Inter;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid {tokens.CURRENT.accent};
            }}
        """)

    def _on_browser_login(self) -> None:
        from pyrolist.ui.dialogs.login_dialog import WebLoginDialog
        dialog = WebLoginDialog(self)
        dialog.login_successful.connect(self._handle_login_success)
        dialog.exec()

    def _handle_login_success(self, avatar_url: str = "") -> None:
        if self._yt:
            self._yt.reload_auth()
        self._update_yt_row()
        if self.on_auth_changed:
            self.on_auth_changed(True, avatar_url)

    def _on_logout(self) -> None:
        try:
            from PySide6.QtWebEngineCore import QWebEngineProfile
            QWebEngineProfile.defaultProfile().cookieStore().deleteAllCookies()
        except Exception:
            pass

        auth_file = AppDirs.config / "headers_auth.json"
        if auth_file.exists():
            auth_file.unlink()
            
        profile_file = AppDirs.config / "user_profile.json"
        if profile_file.exists():
            profile_file.unlink()
            
        if self._yt:
            self._yt.reload_auth()
        self._update_yt_row()
        self.on_changed(self.settings)
        if self.on_auth_changed:
            self.on_auth_changed(False, "")

    def _set_integration(self, key: str, value) -> None:
        setattr(self.settings.integrations, key, value)
        self.on_changed(self.settings)

    def changeEvent(self, event) -> None:
        from PySide6.QtCore import QEvent
        if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
            if not getattr(self, '_in_style_change', False):
                self._in_style_change = True
                try:
                    if hasattr(self, "_line_edits"):
                        for line in self._line_edits:
                            self._update_line_edit_style(line)
                finally:
                    self._in_style_change = False
        super().changeEvent(event)
