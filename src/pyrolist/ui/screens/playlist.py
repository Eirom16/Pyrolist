from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
from functools import partial
from loguru import logger
import asyncio
from pyrolist.ui.widgets.song_card import SongCard
from pyrolist.ui.widgets.icon_button import IconButton
from pyrolist.ui.design.icons import Icon
from pyrolist.utils.image_cache import ImageCache

_image_cache = ImageCache()

class PlaylistScreen(QWidget):
    download_playlist_requested = Signal(str, str, str) # playlist_id, title, thumbnail_url
    
    def __init__(self, yt_client, on_play_song, on_play_local_playlist=None):
        super().__init__()
        self.yt = yt_client
        self.on_play_song = on_play_song
        self.on_play_local_playlist = on_play_local_playlist
        self._playlist_id = None
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

    async def load(self, playlist_id: str):
        if not playlist_id:
            return
            
        self._playlist_id = playlist_id
        self._clear_content()
        
        if playlist_id.startswith("local_"):
            await self._load_local_playlist(playlist_id)
            return
            
        from pyrolist.ui.widgets.skeleton_loader import SkeletonListLoader
        skeleton = SkeletonListLoader(row_count=8)
        self.content_layout.addWidget(skeleton)
        
        try:
            data = await self.yt.get_playlist(playlist_id)
            self._display_playlist(data)
        except Exception as e:
            logger.error(f"Error loading playlist: {e}")
            self._clear_content()
            self.content_layout.addWidget(QLabel("Error cargando playlist"))

    async def _load_local_playlist(self, playlist_id: str):
        actual_pid = playlist_id.replace("local_", "")
        from pyrolist.db.repository import DownloadRepository
        repo = DownloadRepository()
        downloads = await repo.get_downloads()
        
        playlist_tracks = [d for d in downloads if d.parent_playlist_id == actual_pid]
        if not playlist_tracks:
            msg = QLabel("Esta playlist no contiene canciones descargadas.")
            msg.setStyleSheet("color: #888899; font-size: 16px; padding: 40px;")
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_layout.addWidget(msg)
            return
            
        playlist_title = playlist_tracks[0].parent_playlist_title or "Playlist Local"
        first_thumb = playlist_tracks[0].thumbnail_url
        
        simulated_data = {
            "title": playlist_title,
            "author": "Biblioteca Local",
            "trackCount": len(playlist_tracks),
            "thumbnails": [{"url": first_thumb}] if first_thumb else [],
            "is_local_playlist": True,
            "tracks": []
        }
        
        self._local_tracks_meta = []
        for t in playlist_tracks:
            track_meta = {
                "title": t.title,
                "artist": t.artist,
                "thumbnail_url": t.thumbnail_url,
                "file_path": t.file_path,
                "duration_ms": t.duration_ms
            }
            self._local_tracks_meta.append(track_meta)
            
            simulated_data["tracks"].append({
                "title": t.title,
                "videoId": "local",
                "artists": [{"name": t.artist}],
                "duration": "",
                "thumbnails": [{"url": t.thumbnail_url}] if t.thumbnail_url else []
            })
            
        self._display_playlist(simulated_data)

    def _display_playlist(self, data: dict):
        self._clear_content()
        
        if not data:
            self.content_layout.addWidget(QLabel("Playlist no encontrada"))
            return
            
        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(24)
        
        thumbnail_url = ""
        thumbnails = data.get('thumbnails', [])
        if thumbnails:
            thumbnail_url = thumbnails[-1].get('url', '')
            
        self.cover = QLabel()
        self.cover.setFixedSize(200, 200)
        self.cover.setStyleSheet("background: #2A2A3E; border-radius: 8px;")
        header_layout.addWidget(self.cover)
        
        if thumbnail_url:
            asyncio.ensure_future(self._load_cover(thumbnail_url))
            
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)
        
        type_lbl = QLabel("PLAYLIST")
        type_lbl.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        type_lbl.setStyleSheet("color: #FFFFFF;")
        info_layout.addWidget(type_lbl)
        
        title_lbl = QLabel(data.get('title', 'Unknown'))
        title_lbl.setFont(QFont("Inter", 32, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #FFFFFF;")
        title_lbl.setWordWrap(True)
        info_layout.addWidget(title_lbl)
        
        author = data.get('author', {}).get('name', 'Unknown Author') if isinstance(data.get('author'), dict) else str(data.get('author', 'Unknown Author'))
        track_count = data.get('trackCount', 0)
        
        meta_lbl = QLabel(f"{author} • {track_count} canciones")
        meta_lbl.setFont(QFont("Inter", 11))
        meta_lbl.setStyleSheet("color: #888899;")
        info_layout.addWidget(meta_lbl)
        
        if data.get('is_local_playlist', False):
            btn_dl = QLabel("📥 Disponible sin conexión")
            btn_dl.setFont(QFont("Inter", 11, QFont.Weight.Bold))
            btn_dl.setStyleSheet("color: #BB86FC; margin-top: 12px;")
        else:
            btn_dl = QPushButton(" Descargar Playlist")
            btn_dl.setIcon(Icon.icon("download", color="#0A0A14"))
            btn_dl.setStyleSheet("""
                QPushButton {
                    background-color: #A78BFA;
                    color: #0A0A14;
                    border: none;
                    border-radius: 16px;
                    padding: 8px 16px;
                    font-weight: bold;
                    margin-top: 12px;
                }
                QPushButton:hover { background-color: #BBA4FC; }
            """)
            btn_dl.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_dl.clicked.connect(lambda: self.download_playlist_requested.emit(
                self._playlist_id, 
                data.get('title', 'Unknown'),
                thumbnail_url
            ))
        
        info_layout.addWidget(btn_dl)
        info_layout.addStretch()
        
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        self.content_layout.addLayout(header_layout)
        
        self.content_layout.addSpacing(24)
        
        # Tracks
        tracks = data.get('tracks', [])
        for i, track in enumerate(tracks):
            title = track.get('title', 'Unknown')
            video_id = track.get('videoId', '')
            
            artists = track.get('artists', [])
            artist_names = ", ".join([a.get('name', '') for a in artists]) if isinstance(artists, list) else str(artists)
            
            duration = track.get('duration', '')
            
            track_thumbnails = track.get('thumbnails', [])
            track_thumbnail_url = track_thumbnails[-1].get('url', '') if track_thumbnails else ''
            
            if video_id:
                card = SongCard(
                    title=title,
                    artist=artist_names,
                    duration=duration,
                    thumbnail_url=track_thumbnail_url,
                    on_play=partial(self._handle_play, video_id, title, artist_names, i),
                    video_id=video_id
                )
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

    def _handle_play(self, video_id, title, artists, index=0):
        if video_id == "local" or (hasattr(self, "_local_tracks_meta") and self._local_tracks_meta):
            if self.on_play_local_playlist:
                self.on_play_local_playlist(self._local_tracks_meta, index)
                return
        if self.on_play_song:
            self.on_play_song(video_id, title, artists, "", 0, "")