from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
from functools import partial
from loguru import logger
import asyncio
from pyrolist.ui.widgets.song_card import SongCard
from pyrolist.utils.image_cache import ImageCache

_image_cache = ImageCache()

class AlbumScreen(QWidget):
    download_requested = Signal(str, str, str, str)
    play_next_requested = Signal(str, str, str, str)
    add_to_queue_requested = Signal(str, str, str, str)
    like_requested = Signal(str, object)
    add_to_playlist_requested = Signal(str, str)
    delete_download_requested = Signal(str)

    def __init__(self, yt_client, on_play_song):
        super().__init__()
        self.yt = yt_client
        self.on_play_song = on_play_song
        self._browse_id = None
        self._build_ui()

    def _build_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(24, 24, 24, 24)
        self.content_layout.setSpacing(16)
        
        self.scroll.setWidget(self.content_widget)
        self.layout.addWidget(self.scroll)

    def _clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    async def load(self, browse_id: str):
        if not browse_id:
            return
            
        self._browse_id = browse_id
        self._clear_content()
        
        from pyrolist.ui.widgets.skeleton_loader import SkeletonListLoader
        skeleton = SkeletonListLoader(row_count=8)
        self.content_layout.addWidget(skeleton)
        
        try:
            data = await self.yt.get_album(browse_id)
            self._display_album(data)
        except Exception as e:
            logger.error(f"Error loading album: {e}")
            self._clear_content()
            self.content_layout.addWidget(QLabel("Error cargando álbum"))

    def _display_album(self, data: dict):
        self._clear_content()
        
        if not data:
            self.content_layout.addWidget(QLabel("Álbum no encontrado"))
            return
            
        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(24)
        
        thumbnail_url = ""
        thumbnails = data.get('thumbnails', [])
        if thumbnails:
            thumbnail_url = thumbnails[-1].get('url', '')
            
        self.cover = QLabel()
        from pyrolist.ui.design import tokens
        self.cover.setFixedSize(200, 200)
        self.cover.setStyleSheet(f"background: {tokens.CURRENT.bg_elevated}; border-radius: 8px;")
        header_layout.addWidget(self.cover)
        
        if thumbnail_url:
            asyncio.ensure_future(self._load_cover(thumbnail_url))
            
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)
        
        type_lbl = QLabel(data.get('type', 'ÁLBUM').upper())
        type_lbl.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        type_lbl.setStyleSheet(f"color: {tokens.CURRENT.accent}; background: transparent;")
        info_layout.addWidget(type_lbl)
        
        title_lbl = QLabel(data.get('title', 'Unknown'))
        title_lbl.setFont(QFont("Inter", 32, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {tokens.CURRENT.text_primary}; background: transparent;")
        title_lbl.setWordWrap(True)
        info_layout.addWidget(title_lbl)
        
        artists = data.get('artists', [])
        artist_names = ", ".join([a.get('name', '') for a in artists]) if isinstance(artists, list) else str(artists)
        
        year = data.get('year', '')
        track_count = data.get('trackCount', 0)
        
        meta_str = f"{artist_names}"
        if year:
            meta_str += f" • {year}"
        if track_count:
            meta_str += f" • {track_count} canciones"
            
        meta_lbl = QLabel(meta_str)
        meta_lbl.setFont(QFont("Inter", 11))
        meta_lbl.setStyleSheet(f"color: {tokens.CURRENT.text_secondary}; background: transparent;")
        info_layout.addWidget(meta_lbl)
        
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        self.content_layout.addLayout(header_layout)
        
        self.content_layout.addSpacing(24)
        
        # Tracks
        tracks = data.get('tracks', [])
        for i, track in enumerate(tracks):
            title = track.get('title', 'Unknown')
            video_id = track.get('videoId', '')
            
            # Use album artists if track doesn't specify
            track_artists = track.get('artists', [])
            if not track_artists:
                track_artist_names = artist_names
            else:
                track_artist_names = ", ".join([a.get('name', '') for a in track_artists]) if isinstance(track_artists, list) else str(track_artists)
            
            duration = track.get('duration', '')
            
            if video_id:
                card = SongCard(
                    title=title,
                    artist=track_artist_names,
                    duration=duration,
                    thumbnail_url=thumbnail_url, # Usually same as album
                    on_play=partial(self._handle_play, video_id, title, track_artist_names)
                )
                card.download_requested.connect(lambda *a: self.download_requested.emit(*a))
                card.play_next_requested.connect(lambda *a: self.play_next_requested.emit(*a))
                card.add_to_queue_requested.connect(lambda *a: self.add_to_queue_requested.emit(*a))
                card.like_requested.connect(lambda *a: self.like_requested.emit(*a))
                card.add_to_playlist_requested.connect(lambda *a: self.add_to_playlist_requested.emit(*a))
                card.delete_download_requested.connect(lambda *a: self.delete_download_requested.emit(*a))
                
                self.content_layout.addWidget(card)
                
        self.content_layout.addStretch()

    async def _load_cover(self, url: str):
        path = await _image_cache.download(url)
        if path:
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                self.cover.setPixmap(pixmap)
                self.cover.setStyleSheet("background: transparent; border-radius: 8px;")

    def _handle_play(self, video_id, title, artists):
        if self.on_play_song:
            self.on_play_song(video_id, title, artists, "", 0, "")