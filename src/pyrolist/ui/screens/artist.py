from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QGridLayout, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
from functools import partial
from loguru import logger
import asyncio
from pyrolist.ui.widgets.song_card import SongCard
from pyrolist.ui.widgets.album_card import AlbumCard
from pyrolist.utils.image_cache import ImageCache

_image_cache = ImageCache()

class ArtistScreen(QWidget):
    download_requested = Signal(str, str, str, str)
    play_next_requested = Signal(str, str, str, str)
    add_to_queue_requested = Signal(str, str, str, str)
    like_requested = Signal(str, object)
    add_to_playlist_requested = Signal(str, str)
    delete_download_requested = Signal(str)

    def __init__(self, yt_client, on_play_song, on_navigate=None, on_back=None):
        super().__init__()
        self.yt = yt_client
        self.on_play_song = on_play_song
        self.on_navigate = on_navigate
        self.on_back = on_back
        self._channel_id = None
        self._current_load_task = None
        self._build_ui()

    def _build_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        self.content_widget = QWidget()
        self._content_wrapper_layout = QVBoxLayout(self.content_widget)
        self._content_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(24, 24, 24, 112)
        self.content_layout.setSpacing(16)
        
        self._content_wrapper_layout.addLayout(self.content_layout)
        self._content_wrapper_layout.addStretch()
        
        self.scroll.setWidget(self.content_widget)
        self.layout.addWidget(self.scroll)

    def _clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                sub_layout = item.layout()
                self._clear_layout(sub_layout)
                sub_layout.deleteLater()

    def _clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                sub_layout = child.layout()
                self._clear_layout(sub_layout)
                sub_layout.deleteLater()

    async def load(self, channel_id: str):
        if not channel_id:
            return
            
        if self._current_load_task and not self._current_load_task.done():
            self._current_load_task.cancel()
            
        self._current_load_task = asyncio.create_task(self._load_async(channel_id))
        try:
            await self._current_load_task
        except asyncio.CancelledError:
            raise

    async def _load_async(self, channel_id: str):
        self._channel_id = channel_id
        self._clear_content()
        
        from pyrolist.ui.widgets.skeleton_loader import SkeletonListLoader
        skeleton = SkeletonListLoader(row_count=8)
        self.content_layout.addWidget(skeleton)
        
        try:
            data = await self.yt.get_artist(channel_id)
            await self._display_artist(data)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Error loading artist: {e}")
            self._clear_content()
            self.content_layout.addWidget(QLabel("Error cargando artista"))

    async def _display_artist(self, data: dict):
        self._clear_content()
        
        if not data:
            self.content_layout.addWidget(QLabel("Artista no encontrado"))
            return
            
        # Back button row
        from pyrolist.ui.design import tokens
        from pyrolist.ui.design.icons import Icon
        back_row = QHBoxLayout()
        back_row.setContentsMargins(0, 0, 0, 8)
        btn_back = QPushButton()
        btn_back.setIcon(Icon.icon("arrow_back", tokens.CURRENT.text_secondary, 16))
        btn_back.setText("Volver")
        btn_back.setFont(QFont("Inter", 11, QFont.Weight.Medium))
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                
                border: none;
                padding: 6px 12px;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background: {tokens.CURRENT.bg_elevated};
                
            }}
        """)
        btn_back.setFixedHeight(36)
        if self.on_back:
            btn_back.clicked.connect(self.on_back)
        back_row.addWidget(btn_back)
        back_row.addStretch()
        self.content_layout.addLayout(back_row)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(24)
        
        thumbnail_url = ""
        thumbnails = data.get('thumbnails', [])
        if thumbnails:
            thumbnail_url = thumbnails[-1].get('url', '')
            
        self.cover = QLabel()
        self.cover.setFixedSize(200, 200)
        self.cover.setObjectName("artistCover")
        header_layout.addWidget(self.cover)
        
        if thumbnail_url:
            asyncio.ensure_future(self._load_cover(thumbnail_url))
            
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)
        
        type_lbl = QLabel("ARTISTA")
        type_lbl.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        type_lbl.setObjectName("artistType")
        info_layout.addWidget(type_lbl)
        
        name = data.get('name', 'Unknown')
        title_lbl = QLabel(name)
        title_lbl.setFont(QFont("Inter", 32, QFont.Weight.Bold))
        title_lbl.setObjectName("artistTitle")
        title_lbl.setWordWrap(True)
        info_layout.addWidget(title_lbl)
        
        subscribers = data.get('subscribers', '')
        if subscribers:
            meta_lbl = QLabel(subscribers)
            meta_lbl.setFont(QFont("Inter", 11))
            meta_lbl.setObjectName("artistMeta")
            info_layout.addWidget(meta_lbl)
        
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        self.content_layout.addLayout(header_layout)
        
        self.content_layout.addSpacing(24)
        
        # Songs
        songs = data.get('songs', {}).get('results', [])
        if songs:
            songs_header = QLabel("Top Canciones")
            songs_header.setFont(QFont("Inter", 16, QFont.Weight.Bold))
            songs_header.setObjectName("artistSectionHeader")
            self.content_layout.addWidget(songs_header)
            
            for i, track in enumerate(songs[:5]):
                title = track.get('title', 'Unknown')
                video_id = track.get('videoId', '')
                
                artists = track.get('artists', [])
                artist_names = ", ".join([a.get('name', '') for a in artists]) if isinstance(artists, list) else str(artists)
                
                # Default to artist name if empty
                if not artist_names or artist_names == "Unknown":
                    artist_names = name
                
                duration = track.get('duration', '')
                
                track_thumbnails = track.get('thumbnails', [])
                track_thumbnail_url = track_thumbnails[-1].get('url', '') if track_thumbnails else ''
                
                if video_id:
                    card = SongCard(
                        title=title,
                        artist=artist_names,
                        duration=duration,
                        thumbnail_url=track_thumbnail_url,
                        on_play=partial(self._handle_play, video_id, title, artist_names, track_thumbnail_url)
                    )
                    card.download_requested.connect(lambda *a: self.download_requested.emit(*a))
                    card.play_next_requested.connect(lambda *a: self.play_next_requested.emit(*a))
                    card.add_to_queue_requested.connect(lambda *a: self.add_to_queue_requested.emit(*a))
                    card.like_requested.connect(lambda *a: self.like_requested.emit(*a))
                    card.add_to_playlist_requested.connect(lambda *a: self.add_to_playlist_requested.emit(*a))
                    card.delete_download_requested.connect(lambda *a: self.delete_download_requested.emit(*a))
                    
                    self.content_layout.addWidget(card)
        
        self.content_layout.addSpacing(16)
        
        # Albums
        albums = data.get('albums', {}).get('results', [])
        if albums:
            albums_header = QLabel("Álbumes")
            albums_header.setFont(QFont("Inter", 16, QFont.Weight.Bold))
            albums_header.setObjectName("artistSectionHeader_2")
            self.content_layout.addWidget(albums_header)
            
            grid = QGridLayout()
            grid.setSpacing(16)
            
            for i, album in enumerate(albums):
                title = album.get("title", "Unknown")
                year = album.get("year", "")
                browse_id = album.get("browseId", "")
                
                album_thumbnails = album.get("thumbnails", [])
                album_thumbnail_url = album_thumbnails[-1].get("url", "") if album_thumbnails else ""
                
                card = AlbumCard(title=title, artist=name, year=year, thumbnail_url=album_thumbnail_url)
                if browse_id and self.on_navigate:
                    card.clicked.connect(partial(self.on_navigate, f"album?id={browse_id}"))
                grid.addWidget(card, i // 4, i % 4)
                
            self.content_layout.addLayout(grid)
            
        self.content_layout.addStretch()

    async def _load_cover(self, url: str):
        path = await _image_cache.download(url)
        import shiboken6
        if not shiboken6.isValid(self):
            return
        if path:
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                self.cover.setPixmap(pixmap)
                self.cover.setStyleSheet("background: transparent; border-radius: 100px;")

    def _handle_play(self, video_id, title, artists, thumbnail_url):
        if self.on_play_song:
            self.on_play_song(video_id, title, artists, "", 0, thumbnail_url)