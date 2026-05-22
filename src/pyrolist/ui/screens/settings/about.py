from __future__ import annotations

import asyncio
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt

from pyrolist.ui.design.fonts import AppFont
from pyrolist.ui.screens.settings.components import page_title
from pyrolist.ui.widgets.ripple_button import RippleButton


class AboutScreen(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(page_title("Acerca de"))

        from PySide6.QtGui import QPixmap
        from pyrolist.config.paths import AppDirs
        logo_path = AppDirs.root / "assets" / "logo.png"
        if logo_path.exists():
            logo = QLabel()
            pixmap = QPixmap(str(logo_path))
            logo.setPixmap(pixmap.scaledToWidth(200, Qt.TransformationMode.SmoothTransformation))
            logo.setAlignment(Qt.AlignmentFlag.AlignLeft)
            logo.setStyleSheet("background: transparent; margin-bottom: 10px;")
            layout.addWidget(logo)

        self.name = QLabel("Pyrolist")
        self.name.setFont(AppFont.display(32))
        self._update_about_styles()
        layout.addWidget(self.name)

        try:
            from pyrolist import __version__ as ver
        except ImportError:
            try:
                from importlib.metadata import version as pkg_version
                ver = pkg_version("pyrolist")
            except Exception:
                ver = "1.1.3"
        self.version = QLabel(f"Versión {ver}")
        self.version.setFont(AppFont.body(14))
        layout.addWidget(self.version)

        self.description = QLabel(
            "Cliente de escritorio para YouTube Music construido con Python, PySide6 y VLC.\n"
            "Incluye streaming, descargas offline, letras sincronizadas, ecualizador e integraciones."
        )
        self.description.setFont(AppFont.body(14))
        self.description.setWordWrap(True)
        layout.addWidget(self.description)

        github = RippleButton("Ver proyecto", "secondary")
        github.clicked.connect(lambda: __import__('webbrowser').open("https://github.com/Eirom16/Pyrolist"))
        layout.addWidget(github)

        # ── Sección de actualizaciones ─────────────────────────────────
        from pyrolist.utils.updater import CURRENT_VERSION
        from pyrolist.ui.design.icons import Icon

        current_ver_lbl = QLabel(f"Versión instalada: {CURRENT_VERSION}")
        current_ver_lbl.setFont(AppFont.mono(13))
        current_ver_lbl.setStyleSheet("color: #6B6B9B;")
        layout.addWidget(current_ver_lbl)

        self._check_btn = RippleButton("  Buscar actualizaciones", variant="secondary")
        self._check_btn.setText(Icon.get("sync") + "  Buscar actualizaciones")
        self._check_btn.setFont(AppFont.body(14))
        self._check_btn.setMinimumHeight(44)
        self._check_btn.clicked.connect(lambda: asyncio.ensure_future(self._manual_check()))
        layout.addWidget(self._check_btn)

        self._update_status_lbl = QLabel("")
        self._update_status_lbl.setFont(AppFont.label(12))
        self._update_status_lbl.setStyleSheet("color: #6B6B9B;")
        layout.addWidget(self._update_status_lbl)

        layout.addStretch()
        
        self._update_about_styles()

    async def _manual_check(self) -> None:
        from pyrolist.utils.updater import check_for_updates, CURRENT_VERSION
        from pyrolist.ui.widgets.update_dialog import UpdateDialog
        from pyrolist.ui.design.icons import Icon

        self._check_btn.setEnabled(False)
        self._check_btn.setText(Icon.get("sync") + "  Comprobando...")

        release = await check_for_updates()

        self._check_btn.setEnabled(True)
        self._check_btn.setText(Icon.get("sync") + "  Buscar actualizaciones")

        if release:
            dlg = UpdateDialog(release, parent=self.window())
            dlg.show()
        else:
            main_win = self.window()
            if hasattr(main_win, 'show_notification'):
                main_win.show_notification(
                    f"Ya tienes la última versión ({CURRENT_VERSION})",
                    "success"
                )
            else:
                from pyrolist.ui.widgets.toast import ToastNotification
                ToastNotification.show(
                    main_win,
                    f"Ya tienes la última versión ({CURRENT_VERSION})",
                    kind="success"
                )

    def _update_about_styles(self) -> None:
        from pyrolist.ui.design import tokens
        self.name.setStyleSheet(f"color: {tokens.CURRENT.accent}; background: transparent;")
        if hasattr(self, "version") and self.version:
            self.version.setStyleSheet(f"color: {tokens.CURRENT.text_secondary}; background: transparent;")
        if hasattr(self, "description") and self.description:
            self.description.setStyleSheet(f"color: {tokens.CURRENT.text_secondary}; background: transparent;")

    def changeEvent(self, event) -> None:
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.Type.PaletteChange:
            if not getattr(self, '_in_style_change', False):
                self._in_style_change = True
                try:
                    self._update_about_styles()
                finally:
                    self._in_style_change = False
        super().changeEvent(event)


