from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont, QPixmap
import asyncio
from pyrolist.utils.image_cache import ImageCache
from pyrolist.ui.design.icons import Icon
from pyrolist.ui.widgets.icon_button import IconButton
from pyrolist.ui.widgets.song_context_menu import SongContextMenu

_image_cache = ImageCache()

class SongCard(QWidget):
    clicked = Signal()
    download_requested = Signal(str, str, str, str)  # video_id, title, artist, thumbnail_url
    play_next_requested = Signal(str, str, str, str)  # video_id, title, artist, thumbnail_url
    add_to_queue_requested = Signal(str, str, str, str)  # video_id, title, artist, thumbnail_url
    add_to_playlist_requested = Signal(str, str) # video_id, title
    like_requested = Signal(str, object)  # video_id, button_instance
    delete_download_requested = Signal(str)  # video_id

    def __init__(self, title, artist, duration, thumbnail_url="", on_play=None, video_id="", is_liked=False):
        super().__init__()
        self._title = title
        self._artist = artist
        self._duration = duration
        self._thumbnail_url = thumbnail_url
        self._on_play = on_play
        self._video_id = video_id
        self._is_liked = is_liked
        self._build_ui()
        if self._thumbnail_url:
            asyncio.ensure_future(self._load_thumbnail())

    async def _load_thumbnail(self):
        path = await _image_cache.download(self._thumbnail_url)
        if path:
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                pixmap = pixmap.scaled(
                    48, 48,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.thumbnail.setPixmap(pixmap)
                self.thumbnail.setStyleSheet("background: transparent; border-radius: 8px;")

    def _build_ui(self):
        self.setObjectName("songCard")
        self.setFixedHeight(64)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)

        self.thumbnail = QLabel()
        self.thumbnail.setFixedSize(48, 48)
        self.thumbnail.setText(Icon.get("music_note"))
        self.thumbnail.setFont(Icon.font(22))
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.thumbnail)

        info = QVBoxLayout()
        info.setSpacing(2)
        info.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_label = QLabel(self._title)
        self.title_label.setFont(QFont("Inter", 12, QFont.Weight.Medium))
        
        # Elide long text
        metrics = self.title_label.fontMetrics()
        elided_title = metrics.elidedText(self._title, Qt.TextElideMode.ElideRight, 240)
        self.title_label.setText(elided_title)
        info.addWidget(self.title_label)

        self.artist_label = QLabel(self._artist)
        self.artist_label.setFont(QFont("Inter", 10))
        elided_artist = metrics.elidedText(self._artist, Qt.TextElideMode.ElideRight, 240)
        self.artist_label.setText(elided_artist)
        info.addWidget(self.artist_label)

        layout.addLayout(info)
        layout.addStretch()

        self.duration_label = QLabel(self._duration)
        self.duration_label.setFont(QFont("Inter", 10))
        self.duration_label.setFixedWidth(50)
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.duration_label)

        # Like button
        from pyrolist.ui.design import tokens
        self.btn_like = IconButton(size=36, active_color=tokens.CURRENT.like_color)
        self.btn_like.setText(Icon.get("favorite"))
        self.btn_like.setFont(Icon.font(20, filled=self._is_liked))
        self.btn_like.setFixedSize(36, 36)
        if self._is_liked:
            self.btn_like.set_active(True)
        self.btn_like.clicked.connect(self._on_like_clicked)
        layout.addWidget(self.btn_like)

        # Play button
        self.btn_play = IconButton(size=36)
        self.btn_play.setText(Icon.get("play_arrow"))
        self.btn_play.setFont(Icon.font(22))
        self.btn_play.setFixedSize(36, 36)
        if self._on_play:
            self.btn_play.clicked.connect(self._on_play)
        self.btn_play.setVisible(self._on_play is not None)
        layout.addWidget(self.btn_play)

        # Context menu trigger
        self.menu_btn = QToolButton()
        self.menu_btn.setText(Icon.get("more_vert"))
        self.menu_btn.setFont(Icon.font(20))
        self.menu_btn.setFixedSize(32, 32)
        self.menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_btn.clicked.connect(self._show_context_menu)
        layout.addWidget(self.menu_btn)

        self._update_card_styles()

        # Allow clicking anywhere on card
        self.mousePressEvent = self._handle_click

    def _update_card_styles(self) -> None:
        from pyrolist.ui.design import tokens
        accent = tokens.CURRENT.accent
        text_primary = tokens.CURRENT.text_primary
        text_secondary = tokens.CURRENT.text_secondary
        bg_high = tokens.CURRENT.bg_high
        
        self.setStyleSheet(f"""
            #songCard {{
                background-color: transparent;
                border-radius: 12px;
                padding: 6px;
            }}
            #songCard:hover {{
                background-color: {accent}14;
            }}
        """)
        
        if not self.thumbnail.pixmap():
            self.thumbnail.setStyleSheet(f"background: {bg_high}; color: {text_secondary}; border-radius: 8px;")
        else:
            self.thumbnail.setStyleSheet("background: transparent; border-radius: 8px;")
            
        self.title_label.setStyleSheet(f"color: {text_primary}; background: transparent;")
        self.artist_label.setStyleSheet(f"color: {text_secondary}; background: transparent;")
        self.duration_label.setStyleSheet(f"color: {text_secondary}; background: transparent;")
        
        from PySide6.QtGui import QColor
        like_c = QColor(tokens.CURRENT.like_color)
        lr, lg, lb = like_c.red(), like_c.green(), like_c.blue()
        
        if self._is_liked:
            self.btn_like.setStyleSheet(f"QPushButton {{ color: {tokens.CURRENT.like_color}; background: transparent; border: none; }}")
        else:
            self.btn_like.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {text_secondary};
                    border: none;
                    border-radius: 18px;
                }}
                QPushButton:hover {{
                    background-color: rgba({lr},{lg},{lb},0.15);
                    color: {tokens.CURRENT.like_color};
                }}
            """)
            
        self.btn_play.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {text_primary};
                border: none;
                border-radius: 18px;
            }}
            QPushButton:hover {{
                background-color: {accent}26;
                color: {accent};
            }}
        """)
        
        self.menu_btn.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                color: {text_secondary};
                border: none;
                border-radius: 16px;
            }}
            QToolButton:hover {{
                background: {accent}1E;
                color: {accent};
            }}
            QToolButton::menu-indicator {{
                image: none;
            }}
        """)
        
    def _handle_click(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if self._on_play:
                self._on_play()
            self.clicked.emit()

    def _on_download_clicked(self):
        if self._video_id:
            self.download_requested.emit(
                self._video_id, self._title, self._artist, self._thumbnail_url
            )

    def _on_like_clicked(self):
        if self._video_id:
            self.like_requested.emit(self._video_id, self.btn_like)

    def _on_play_next_clicked(self):
        if self._video_id:
            self.play_next_requested.emit(
                self._video_id, self._title, self._artist, self._thumbnail_url
            )

    def _on_add_to_queue_clicked(self):
        if self._video_id:
            self.add_to_queue_requested.emit(
                self._video_id, self._title, self._artist, self._thumbnail_url
            )

    def _on_add_to_playlist_clicked(self):
        if self._video_id:
            self.add_to_playlist_requested.emit(self._video_id, self._title)

    def _on_delete_download_clicked(self):
        if self._video_id:
            self.delete_download_requested.emit(self._video_id)

    def _show_context_menu(self):
        asyncio.create_task(self._show_context_menu_async())

    async def _show_context_menu_async(self):
        from pyrolist.db.repository import DownloadRepository
        repo = DownloadRepository()
        existing = await repo.get_download(self._video_id) if self._video_id else None
        is_downloaded = existing is not None
        
        self._current_menu = SongContextMenu(parent=self.window(), is_downloaded=is_downloaded)
        self._current_menu.play_next.connect(self._on_play_next_clicked)
        self._current_menu.add_to_queue.connect(self._on_add_to_queue_clicked)
        self._current_menu.add_to_playlist.connect(self._on_add_to_playlist_clicked)
        
        if is_downloaded:
            self._current_menu.delete_download.connect(self._on_delete_download_clicked)
        else:
            self._current_menu.download.connect(self._on_download_clicked)
            
        pos = self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomLeft())
        self._current_menu.popup_at(pos)

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
