from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from qasync import asyncSlot
import asyncio
from pyrolist.ui.widgets.ripple_button import RippleButton
from pyrolist.ui.design import tokens


class WelcomeScreen(QWidget):
    def __init__(self, on_credentials_saved, yt_client=None):
        super().__init__()
        self.on_credentials_saved = on_credentials_saved
        self.yt_client = yt_client
        self._build_ui()

    def set_yt_client(self, yt_client):
        self.yt_client = yt_client

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(80, 40, 80, 40)
        layout.setSpacing(20)

        from PySide6.QtGui import QPixmap
        from pyrolist.config.paths import AppDirs
        logo_path = AppDirs.root / "assets" / "logo.png"
        
        self._title = QLabel("Pyrolist")
        self._title.setFont(QFont("Inter", 32, QFont.Weight.Bold))
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if logo_path.exists():
            logo = QLabel()
            pixmap = QPixmap(str(logo_path))
            logo.setPixmap(pixmap.scaledToWidth(180, Qt.TransformationMode.SmoothTransformation))
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(logo)

        self._subtitle = QLabel("Cliente de YouTube Music para Linux")
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self._title)
        layout.addWidget(self._subtitle)
        layout.addSpacing(20)

        self._card = QFrame()
        card_layout = QVBoxLayout(self._card)
        card_layout.setSpacing(20)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._welcome_text = QLabel("Bienvenido a Pyrolist")
        self._welcome_text.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        self._welcome_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self._welcome_text)

        self._desc_text = QLabel(
            "Para escuchar tu música favorita necesitas\niniciar sesión con tu cuenta de Google."
        )
        self._desc_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self._desc_text)

        self._login_btn = RippleButton("Iniciar sesión con Google", "primary")
        self._login_btn.setMinimumHeight(56)
        self._login_btn.clicked.connect(self._on_login_clicked)
        card_layout.addWidget(self._login_btn)

        self._status_label = QLabel("")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self._status_label)

        self._progress = QLabel("")
        self._progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self._progress)

        card_layout.addStretch()

        layout.addWidget(self._card)
        layout.addStretch()

        self._apply_theme_styles()

    def _apply_theme_styles(self) -> None:
        t = tokens.CURRENT
        self._title.setStyleSheet(f"color: {t.accent}; background: transparent;")
        self._subtitle.setStyleSheet(f"color: {t.text_secondary}; font-size: 14px; background: transparent;")
        self._card.setStyleSheet(f"""
            background-color: {t.bg_elevated};
            border-radius: 16px;
            border: 1px solid {t.border};
            padding: 32px;
        """)
        self._welcome_text.setStyleSheet(f"color: {t.text_primary}; background: transparent;")
        self._desc_text.setStyleSheet(f"color: {t.text_secondary}; font-size: 14px; background: transparent;")
        self._status_label.setStyleSheet(f"color: {t.text_secondary}; font-size: 13px; background: transparent;")
        self._progress.setStyleSheet(f"color: {t.text_disabled}; font-size: 12px; background: transparent;")

    def changeEvent(self, event) -> None:
        from PySide6.QtCore import QEvent
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.StyleChange, QEvent.Type.ApplicationPaletteChange):
            if not getattr(self, '_in_style_change', False):
                self._in_style_change = True
                try:
                    self._apply_theme_styles()
                finally:
                    self._in_style_change = False
        super().changeEvent(event)

    @asyncSlot()
    async def _on_login_clicked(self) -> None:
        self._login_btn.setEnabled(False)
        self._login_btn.setText("  Iniciando...")
        self._status_label.setText("Abriendo ventana de inicio de sesion...")
        
        try:
            from pyrolist.ui.dialogs.login_dialog import WebLoginDialog
            dialog = WebLoginDialog(self)
            
            # Since exec() is blocking for the dialog, we need to handle the signal
            # for when login is successful.
            dialog.login_successful.connect(lambda avatar: asyncio.create_task(self._handle_login_success()))
            dialog.exec()
            
            # After dialog closes, if not authenticated, reset button
            if self.yt_client and not self.yt_client.is_authenticated:
                self._login_btn.setEnabled(True)
                self._login_btn.setText("  Iniciar sesión con Google")
                self._status_label.setText("")
        except Exception as e:
            from loguru import logger
            logger.error(f"Error in login: {e}")
            self._login_btn.setEnabled(True)
            self._login_btn.setText("  Reintentar")
            self._status_label.setText(f"Error: {str(e)}")

    async def _handle_login_success(self):
        self._status_label.setText("Autorizacion exitosa")
        self._progress.setText("Cargando Pyrolist...")
        if self.yt_client:
            self.yt_client.reload_auth()
        await asyncio.sleep(1.0)
        await self.on_credentials_saved("", "")
