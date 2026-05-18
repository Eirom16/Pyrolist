from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from pyrolist.ui.design.fonts import AppFont
from pyrolist.ui.design.icons import Icon
from pyrolist.ui.widgets.glass_panel import GlassPanel


class SongContextMenu(GlassPanel):
    play_next = Signal()
    add_to_queue = Signal()
    add_to_playlist = Signal()
    download = Signal()
    delete_download = Signal()

    def __init__(self, parent=None, is_downloaded: bool = False):
        super().__init__(parent)
        self.is_downloaded = is_downloaded
        self.setMinimumWidth(250)
        self._build()

    def _build(self) -> None:
        layout = self.layout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(2)

        actions = [
            ("play_arrow", "Reproducir a continuacion", "play_next"),
            ("queue_music", "Anadir a la cola", "add_to_queue"),
            ("playlist_add", "Anadir a playlist", "add_to_playlist"),
            None,
        ]
        
        if self.is_downloaded:
            actions.append(("delete", "Borrar descarga", "delete_download"))
        else:
            actions.append(("download", "Descargar", "download"))

        for action in actions:
            if action is None:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setStyleSheet("color: rgba(167,139,250,0.08); max-height: 1px; margin: 4px 8px;")
                layout.addWidget(sep)
                continue
            icon_name, label, signal_name = action
            layout.addWidget(self._action_button(icon_name, label, signal_name))

    def _action_button(self, icon_name: str, label: str, signal_name: str) -> QPushButton:
        button = QPushButton()
        button.setFixedHeight(40)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        if icon_name == "delete":
            button.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    border-radius: 10px;
                    text-align: left;
                    padding: 0;
                }
                QPushButton:hover {
                    background: rgba(239, 68, 68, 0.15);
                }
            """)
        else:
            button.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    border-radius: 10px;
                    text-align: left;
                    padding: 0;
                }
                QPushButton:hover {
                    background: rgba(167,139,250,0.10);
                }
            """)
            
        row = QHBoxLayout(button)
        row.setContentsMargins(10, 0, 10, 0)
        row.setSpacing(12)
        
        text = QLabel(label)
        text.setFont(AppFont.body(13))
        
        if icon_name == "delete":
            icon = Icon.label(icon_name, 16, "#EF4444")
            text.setStyleSheet("color: #EF4444; background: transparent;")
        else:
            icon = Icon.label(icon_name, 16, "#9B9BC0")
            text.setStyleSheet("color: #F1F0FF; background: transparent;")
            
        icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        text.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        row.addWidget(icon)
        row.addWidget(text)
        row.addStretch()

        signal = getattr(self, signal_name)
        button.clicked.connect(lambda checked=False, sig=signal: (sig.emit(), self.dismiss()))
        return button
