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
        layout.addWidget(self.thumbnail)

        self.title_label = QLabel(self._elide(self._title, 148))
        self.title_label.setFont(AppFont.title(11))
        self.title_label.setToolTip(self._title)
        layout.addWidget(self.title_label)

        subtitle = self._artist if not self._year else f"{self._artist} - {self._year}"
        self.artist_label = QLabel(self._elide(subtitle, 148))
        self.artist_label.setFont(AppFont.label(10))
        self.artist_label.setToolTip(subtitle)
        layout.addWidget(self.artist_label)
        layout.addStretch()
        
        self._update_card_styles()

    def _update_card_styles(self) -> None:
        from pyrolist.ui.design import tokens
        accent = tokens.CURRENT.accent
        text_primary = tokens.CURRENT.text_primary
        text_secondary = tokens.CURRENT.text_secondary
        bg_surface = tokens.CURRENT.bg_surface
        bg_elevated = tokens.CURRENT.bg_elevated
        bg_high = tokens.CURRENT.bg_high
        border_color = tokens.CURRENT.border
        
        self.setStyleSheet(f"""
            #albumCard {{
                background-color: {bg_surface};
                border-radius: 12px;
                border: 1px solid {border_color};
            }}
            #albumCard:hover {{
                background-color: {bg_elevated};
                border-color: {accent}55;
            }}
        """)
        
        if not self.thumbnail.pixmap():
            self.thumbnail.setStyleSheet(f"""
                background: {bg_high};
                color: {text_secondary};
                border-radius: 12px;
            """)
        else:
            self.thumbnail.setStyleSheet("background: transparent; border-radius: 12px;")
            
        self.title_label.setStyleSheet(f"color: {text_primary}; background: transparent;")
        self.artist_label.setStyleSheet(f"color: {text_secondary}; background: transparent;")

    def _elide(self, text: str, width: int) -> str:
        return QFontMetrics(AppFont.label(10)).elidedText(text, Qt.TextElideMode.ElideRight, width)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def changeEvent(self, event) -> None:
        from PySide6.QtCore import QEvent
        if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
            if not getattr(self, '_in_style_change', False):
                self._in_style_change = True
                try:
                    self._update_card_styles()
                finally:
                    self._in_style_change = False
        super().changeEvent(event)
