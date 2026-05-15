from __future__ import annotations

import asyncio

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontMetrics, QPixmap
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QLabel, QVBoxLayout, QWidget

from pyrolist.ui.design.fonts import AppFont
from pyrolist.ui.design.icons import Icon
from pyrolist.utils.image_cache import ImageCache

_image_cache = ImageCache()


class AlbumCard(QWidget):
    clicked = Signal()

    def __init__(self, title: str, artist: str, thumbnail_url: str = "", year: str = ""):
        super().__init__()
        self._title = title
        self._artist = artist
        self._year = year
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
                self.thumbnail.setStyleSheet("background: transparent; border-radius: 12px;")

    def _build_ui(self) -> None:
        self.setObjectName("albumCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(168, 218)
        self.setStyleSheet("""
            #albumCard {
                background-color: #16162A;
                border-radius: 12px;
                border: 1px solid rgba(167,139,250,0.08);
            }
            #albumCard:hover {
                background-color: #1E1E38;
                border-color: rgba(167,139,250,0.26);
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 8)
        shadow.setColor(Qt.GlobalColor.transparent)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.thumbnail = QLabel(Icon.get("album"))
        self.thumbnail.setFixedSize(148, 148)
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail.setFont(Icon.font(56))
        self.thumbnail.setStyleSheet("""
            background: #1E1E38;
            color: #4A4A6A;
            border-radius: 12px;
        """)
        layout.addWidget(self.thumbnail)

        self.title_label = QLabel(self._elide(self._title, 148))
        self.title_label.setFont(AppFont.title(11))
        self.title_label.setStyleSheet("color: #F1F0FF; background: transparent;")
        self.title_label.setToolTip(self._title)
        layout.addWidget(self.title_label)

        subtitle = self._artist if not self._year else f"{self._artist} - {self._year}"
        self.artist_label = QLabel(self._elide(subtitle, 148))
        self.artist_label.setFont(AppFont.label(10))
        self.artist_label.setStyleSheet("color: #9B9BC0; background: transparent;")
        self.artist_label.setToolTip(subtitle)
        layout.addWidget(self.artist_label)
        layout.addStretch()

    def _elide(self, text: str, width: int) -> str:
        return QFontMetrics(AppFont.label(10)).elidedText(text, Qt.TextElideMode.ElideRight, width)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
