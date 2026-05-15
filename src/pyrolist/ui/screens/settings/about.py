from __future__ import annotations

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

        name = QLabel("Pyrolist")
        name.setFont(AppFont.display(32))
        name.setStyleSheet("color: #A78BFA; background: transparent;")
        layout.addWidget(name)

        version = QLabel("Version 1.0.0")
        version.setFont(AppFont.body(14))
        version.setStyleSheet("color: #9B9BC0; background: transparent;")
        layout.addWidget(version)

        description = QLabel(
            "Cliente de escritorio para YouTube Music construido con Python, PySide6 y VLC.\n"
            "Incluye streaming, descargas offline, letras sincronizadas, ecualizador e integraciones."
        )
        description.setFont(AppFont.body(14))
        description.setWordWrap(True)
        description.setStyleSheet("color: #9B9BC0; background: transparent;")
        layout.addWidget(description)

        github = RippleButton("Ver proyecto", "secondary")
        layout.addWidget(github)
        layout.addStretch()

