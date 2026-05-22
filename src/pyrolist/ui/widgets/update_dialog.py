# src/pyrolist/ui/widgets/update_dialog.py
"""
Diálogo de actualización de Pyrolist.
Se muestra cuando check_for_updates() devuelve un ReleaseInfo.
Muestra: versión actual vs nueva, notas del release, barra de progreso,
botones Actualizar / Posponer / Ver en GitHub.
"""
from __future__ import annotations

import asyncio
import webbrowser
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QFrame, QWidget, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QColor
from qasync import asyncSlot

from pyrolist.ui.design.fonts import AppFont
from pyrolist.ui.design.icons import Icon
from pyrolist.ui.widgets.ripple_button import RippleButton
from pyrolist.ui.widgets.animated_progress import AnimatedProgressBar
from pyrolist.utils.updater import (
    ReleaseInfo, download_update, install_update, CURRENT_VERSION
)


class UpdateDialog(QDialog):
    """
    Diálogo modal de actualización.

    Uso:
        release = await check_for_updates()
        if release:
            dlg = UpdateDialog(release, parent=main_window)
            dlg.show()   # NO bloquea — usa show() no exec()
    """

    update_installed = Signal()
    _active_instance: UpdateDialog | None = None

    def __init__(self, release: ReleaseInfo, parent=None):
        super().__init__(parent)
        self.release = release
        self._downloading = False

        if UpdateDialog._active_instance is not None:
            if getattr(UpdateDialog._active_instance, "_downloading", False):
                QTimer.singleShot(0, self.reject)
                return
            try:
                UpdateDialog._active_instance.close()
            except Exception:
                pass
        UpdateDialog._active_instance = self

        self.setWindowTitle("Actualización disponible — Pyrolist")
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setMinimumWidth(520)

        self._build()
        self._center_on_parent()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._center_on_parent()

    def hideEvent(self, event) -> None:
        if UpdateDialog._active_instance is self:
            UpdateDialog._active_instance = None
        super().hideEvent(event)

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # ── Panel principal con fondo ──────────────────────────────────
        panel = QFrame()
        panel.setObjectName("updatePanel")
        panel.setStyleSheet("""
            #updatePanel {
                background-color: #16162A;
                border-radius: 20px;
                border: 1px solid rgba(167,139,250,0.25);
            }
        """)

        # Sombra exterior
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(48)
        shadow.setOffset(0, 12)
        shadow.setColor(QColor(0, 0, 0, 120))
        panel.setGraphicsEffect(shadow)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # ── Cabecera: ícono + título ───────────────────────────────────
        header_row = QHBoxLayout()
        update_icon = Icon.label("new_releases", size=32, color="#A78BFA")

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        title_lbl = QLabel("Nueva versión disponible")
        title_lbl.setFont(AppFont.heading(18))
        title_lbl.setStyleSheet("color: #F1F0FF;")

        version_lbl = QLabel(
            f"{CURRENT_VERSION}  →  {self.release.version}"
        )
        version_lbl.setFont(AppFont.mono(13))
        version_lbl.setStyleSheet("color: #A78BFA;")

        title_col.addWidget(title_lbl)
        title_col.addWidget(version_lbl)

        header_row.addWidget(update_icon)
        header_row.addSpacing(12)
        header_row.addLayout(title_col)
        header_row.addStretch()

        # Botón cerrar
        close_btn = RippleButton("", variant="ghost")
        close_btn.setText(Icon.get("close"))
        close_btn.setFont(Icon.font(18))
        close_btn.setFixedSize(36, 36)
        close_btn.clicked.connect(self.reject)
        header_row.addWidget(close_btn)

        layout.addLayout(header_row)

        # ── Separador ─────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(167,139,250,0.10);")
        layout.addWidget(sep)

        # ── Notas del release ──────────────────────────────────────────
        notes_label = QLabel("Novedades en esta versión:")
        notes_label.setFont(AppFont.label(12))
        notes_label.setStyleSheet("color: #6B6B9B;")
        layout.addWidget(notes_label)

        notes_box = QTextEdit()
        notes_box.setReadOnly(True)
        notes_box.setPlainText(self.release.release_notes or "Sin notas de versión.")
        notes_box.setFont(AppFont.body(13))
        notes_box.setFixedHeight(140)
        notes_box.setStyleSheet("""
            QTextEdit {
                background: #10101E;
                border: 1px solid rgba(167,139,250,0.08);
                border-radius: 12px;
                color: #9B9BC0;
                padding: 10px;
            }
        """)
        layout.addWidget(notes_box)

        # ── Barra de progreso (oculta hasta que empieza la descarga) ───
        self._progress_container = QWidget()
        prog_layout = QVBoxLayout(self._progress_container)
        prog_layout.setContentsMargins(0, 0, 0, 0)
        prog_layout.setSpacing(6)

        self._progress_bar = AnimatedProgressBar()
        self._progress_bar.set_value(0.0, animated=False)

        self._progress_label = QLabel("Preparando descarga...")
        self._progress_label.setFont(AppFont.label(12))
        self._progress_label.setStyleSheet("color: #6B6B9B;")

        prog_layout.addWidget(self._progress_bar)
        prog_layout.addWidget(self._progress_label)
        self._progress_container.setVisible(False)
        layout.addWidget(self._progress_container)

        # ── Botones de acción ──────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._github_btn = RippleButton("Ver en GitHub", variant="ghost")
        self._github_btn.setText(
            Icon.get("open_in_new") + "  Ver en GitHub"
        )
        self._github_btn.setFont(AppFont.body(13))
        self._github_btn.clicked.connect(
            lambda: webbrowser.open(self.release.html_url)
        )

        self._postpone_btn = RippleButton("Posponer", variant="secondary")
        self._postpone_btn.clicked.connect(self.reject)

        self._update_btn = RippleButton(
            f"  Actualizar a {self.release.version}", variant="primary"
        )
        self._update_btn.setText(
            Icon.get("download") + f"  Actualizar a {self.release.version}"
        )
        self._update_btn.setFont(AppFont.body(14))
        self._update_btn.setMinimumHeight(44)
        self._update_btn.clicked.connect(self._on_update_clicked)

        btn_row.addWidget(self._github_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._postpone_btn)
        btn_row.addWidget(self._update_btn)

        layout.addLayout(btn_row)
        root.addWidget(panel)

    def _center_on_parent(self) -> None:
        parent = self.parent()
        if parent and parent.isVisible():
            parent_geo = parent.geometry()
            x = parent_geo.x() + (parent_geo.width()  - self.width())  // 2
            y = parent_geo.y() + (parent_geo.height() - self.height()) // 2
            self.move(x, y)
        else:
            from PySide6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen()
            if screen:
                screen_geo = screen.geometry()
                x = screen_geo.x() + (screen_geo.width()  - self.width())  // 2
                y = screen_geo.y() + (screen_geo.height() - self.height()) // 2
                self.move(x, y)

    @asyncSlot()
    async def _on_update_clicked(self) -> None:
        asset = self.release.get_asset_for_platform()
        if not asset:
            self._progress_label.setText(
                "No hay paquete disponible para esta plataforma. "
                "Descarga manualmente desde GitHub."
            )
            self._progress_container.setVisible(True)
            return

        # Bloquear botones durante la descarga
        self._update_btn.setEnabled(False)
        self._postpone_btn.setEnabled(False)
        self._progress_container.setVisible(True)
        self._progress_label.setText("Iniciando descarga...")
        self._downloading = True

        def _progress(pct: float, msg: str) -> None:
            self._progress_bar.set_value(pct / 100.0)
            self._progress_label.setText(msg)

        pkg_path = await download_update(asset, _progress)

        if not pkg_path:
            self._progress_label.setText(
                "Error en la descarga. Comprueba tu conexión e inténtalo de nuevo."
            )
            self._update_btn.setEnabled(True)
            self._postpone_btn.setEnabled(True)
            return

        self._progress_bar.set_value(1.0)
        self._progress_label.setText(
            "Descarga completada. Instalando actualización..."
        )

        success = install_update(pkg_path)
        if success:
            self._progress_label.setText(
                "Instalación iniciada. Cerrando Pyrolist en breve para aplicar los cambios..."
            )
            self._update_btn.setText(
                Icon.get("check_circle") + "  Cerrando..."
            )
            self.update_installed.emit()
            QTimer.singleShot(1500, QApplication.quit)
        else:
            self._progress_label.setText(
                f"No se pudo instalar automáticamente.\n"
                f"Archivo descargado en: {pkg_path}"
            )
