from __future__ import annotations

import asyncio

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontMetrics, QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from pyrolist.ui.design.fonts import AppFont
from pyrolist.ui.design.icons import Icon
from pyrolist.utils.image_cache import ImageCache

_image_cache = ImageCache()


class ArtistCard(QWidget):
    clicked = Signal()

    def __init__(self, name: str, thumbnail_url: str = ""):
        super().__init__()
        self._name = name
        self._thumbnail_url = thumbnail_url
        self._build_ui()
        if self._thumbnail_url:
            asyncio.ensure_future(self._load_thumbnail())

    async def _load_thumbnail(self) -> None:
        path = await _image_cache.download(self._thumbnail_url)
        if path:
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                self.thumbnail.setPixmap(
                    pixmap.scaled(
                        148,
                        148,
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                self.thumbnail.setStyleSheet("background: transparent; border-radius: 74px;")

    def _build_ui(self) -> None:
        self.setObjectName("artistCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(168, 210)
        self.setStyleSheet("""
            #artistCard {
                background-color: #16162A;
                border-radius: 12px;
                border: 1px solid rgba(167,139,250,0.08);
            }
            #artistCard:hover {
                background-color: #1E1E38;
                border-color: rgba(34,211,238,0.24);
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.thumbnail = QLabel(Icon.get("person"))
        self.thumbnail.setFixedSize(148, 148)
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail.setFont(Icon.font(58))
        self.thumbnail.setStyleSheet("""
            background: #1E1E38;
            color: #4A4A6A;
            border-radius: 74px;
        """)
        layout.addWidget(self.thumbnail, alignment=Qt.AlignmentFlag.AlignCenter)

        self.name_label = QLabel(self._elide(self._name, 148))
        self.name_label.setFont(AppFont.title(11))
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet("color: #F1F0FF; background: transparent;")
        self.name_label.setToolTip(self._name)
        layout.addWidget(self.name_label)
        layout.addStretch()

    def _elide(self, text: str, width: int) -> str:
        return QFontMetrics(AppFont.title(11)).elidedText(text, Qt.TextElideMode.ElideRight, width)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

