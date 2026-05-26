from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QPushButton
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QFont, QPixmap, QPainter, QPen, QColor
from functools import partial
from loguru import logger
import asyncio
from pyrolist.ui.widgets.song_card import SongCard
from pyrolist.ui.widgets.icon_button import IconButton
from pyrolist.ui.design.icons import Icon
from pyrolist.utils.image_cache import ImageCache

_image_cache = ImageCache()

class CircularProgress(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self._progress = 0.0 # 0.0 to 100.0

    def set_progress(self, progress: float):
        self._progress = max(0.0, min(100.0, progress))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background circle
        bg_pen = QPen(QColor(40, 40, 50, 80), 2)
        painter.setPen(bg_pen)
        painter.drawEllipse(2, 2, 20, 20)
        
        # Draw progress arc (green matching premium theme)
        from pyrolist.ui.design import tokens
        accent_color = QColor(tokens.CURRENT.accent)
        fg_pen = QPen(accent_color, 2.5)
        fg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(fg_pen)
        
        span_angle = -int(self._progress * 3.6 * 16) # negative for clockwise
        painter.drawArc(2, 2, 20, 20, 90 * 16, span_angle)

class PlaylistScreen(QWidget):
    download_playlist_requested = Signal(str, str, str) # playlist_id, title, thumbnail_url
    download_requested = Signal(str, str, str, str)
    play_next_requested = Signal(str, str, str, str)
    add_to_queue_requested = Signal(str, str, str, str)
    add_to_playlist_requested = Signal(str, str)
    like_requested = Signal(str, object)
    delete_download_requested = Signal(str)
    
    def __init__(self, yt_client, on_play_song, on_play_local_playlist=None, on_back=None):
        super().__init__()
        self.yt = yt_client
        self.on_play_song = on_play_song
        self.on_play_local_playlist = on_play_local_playlist
        self.on_back = on_back
        self._playlist_id = None
        self._current_load_task = None
        self._build_ui()
        
        # Wire up DownloadManager signals for real-time progress update
        try:
            from pyrolist.services.download_manager import DownloadManager
            dm = DownloadManager.get_instance()
            dm.download_progress.connect(self._on_download_progress)
            dm.download_completed.connect(self._on_download_completed)
            dm.download_error.connect(self._on_download_error)
        except Exception as e:
            logger.debug(f"Could not connect to DownloadManager signals: {e}")

    def _build_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(24, 24, 24, 112)
        self.content_layout.setSpacing(16)
        
        self.scroll.setWidget(self.content_widget)
        self.layout.addWidget(self.scroll)

    def _clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())

    async def load(self, playlist_id: str):
        if not playlist_id:
            return
            
        if self._current_load_task and not self._current_load_task.done():
            self._current_load_task.cancel()
            
        self._current_load_task = asyncio.create_task(self._load_async(playlist_id))
        try:
            await self._current_load_task
        except asyncio.CancelledError:
            raise

    async def _load_async(self, playlist_id: str):
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
            
            # Check which tracks are already downloaded in the database
            from pyrolist.db.repository import DownloadRepository
            repo = DownloadRepository()
            downloads = await repo.get_downloads()
            downloaded_vids = {d.video_id for d in downloads}
            
            tracks = data.get('tracks', [])
            if tracks:
                downloaded_count = sum(1 for t in tracks if t.get('videoId') in downloaded_vids)
                if downloaded_count == len(tracks):
                    data['is_fully_downloaded'] = True
                elif downloaded_count > 0:
                    data['is_partially_downloaded'] = True
                    data['downloaded_count'] = downloaded_count
            
            await self._display_playlist(data)
        except asyncio.CancelledError:
            raise
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
            from pyrolist.ui.design import tokens
            msg = QLabel("Esta playlist no contiene canciones descargadas.")
            msg.setStyleSheet(f" font-size: 16px; padding: 40px; background: transparent;")
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_layout.addWidget(msg)
            return
            
        playlist_title = playlist_tracks[0].parent_playlist_title or "Playlist Local"
        playlist_thumb = getattr(playlist_tracks[0], "parent_playlist_thumbnail_url", "") or playlist_tracks[0].thumbnail_url
        
        simulated_data = {
            "title": playlist_title,
            "author": "Biblioteca Local",
            "trackCount": len(playlist_tracks),
            "thumbnails": [{"url": playlist_thumb}] if playlist_thumb else [],
            "is_local_playlist": True,
            "tracks": []
        }
        
        self._local_tracks_meta = []
        for t in playlist_tracks:
            track_meta = {
                "video_id": t.video_id,
                "title": t.title,
                "artist": t.artist,
                "thumbnail_url": t.thumbnail_url,
                "file_path": t.file_path,
                "duration_ms": t.duration_ms
            }
            self._local_tracks_meta.append(track_meta)
            
            simulated_data["tracks"].append({
                "title": t.title,
                "videoId": t.video_id,
                "artists": [{"name": t.artist}],
                "duration": "",
                "thumbnails": [{"url": t.thumbnail_url}] if t.thumbnail_url else []
            })
            
        await self._display_playlist(simulated_data)

    async def _display_playlist(self, data: dict):
        self._clear_content()
        
        if not data:
            self.content_layout.addWidget(QLabel("Playlist no encontrada"))
            return
            
        # Back button row
        from pyrolist.ui.design import tokens
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
        self.cover.setObjectName("playlistCover")
        header_layout.addWidget(self.cover)
        
        if thumbnail_url:
            asyncio.ensure_future(self._load_cover(thumbnail_url))
            
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)
        
        type_lbl = QLabel("PLAYLIST")
        type_lbl.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        type_lbl.setObjectName("playlistType")
        info_layout.addWidget(type_lbl)
        
        title_lbl = QLabel(data.get('title', 'Unknown'))
        title_lbl.setFont(QFont("Inter", 32, QFont.Weight.Bold))
        title_lbl.setObjectName("playlistTitle")
        title_lbl.setWordWrap(True)
        info_layout.addWidget(title_lbl)
        
        author = data.get('author', {}).get('name', 'Unknown Author') if isinstance(data.get('author'), dict) else str(data.get('author', 'Unknown Author'))
        track_count = data.get('trackCount', 0)
        
        meta_lbl = QLabel(f"{author} • {track_count} canciones")
        meta_lbl.setFont(QFont("Inter", 11))
        meta_lbl.setObjectName("playlistMeta")
        info_layout.addWidget(meta_lbl)
        
        # Create a container layout for download actions/badges
        dl_layout = QHBoxLayout()
        dl_layout.setSpacing(12)
        dl_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        dl_layout.setContentsMargins(0, 8, 0, 0)
        
        # Create the label in advance so we can show/hide it dynamically
        from pyrolist.ui.design import tokens
        self.label_offline_status = QLabel("📥 Disponible sin conexión")
        self.label_offline_status.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        self.label_offline_status.setStyleSheet(f"color: {tokens.CURRENT.accent}; background: transparent;")
        
        # Circular Progress loader
        self.progress_circle = CircularProgress()
        self.progress_circle.hide()
        
        # Check if there are active tasks in the manager for this playlist
        from pyrolist.services.download_manager import DownloadManager
        dm = DownloadManager.get_instance()
        active_tasks = [t for t in dm._tasks.values() if t.parent_playlist_id == self._playlist_id]
        
        if data.get('is_local_playlist', False) or data.get('is_fully_downloaded', False):
            self.label_offline_status.show()
            dl_layout.addWidget(self.label_offline_status)
        else:
            self.label_offline_status.hide()
            
            btn_label = " Descargar Playlist"
            if data.get('is_partially_downloaded', False):
                btn_label = f" Descargar restantes ({data.get('downloaded_count')}/{track_count} completas)"
                
            self.btn_dl = QPushButton(btn_label)
            self.btn_dl.setIcon(Icon.icon("download", color="#0A0A14"))
            self._update_dl_button_style()
            self.btn_dl.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Setup clicked handler
            def on_dl_click():
                self.btn_dl.setText(" Descargando... 0%")
                self.btn_dl.setIcon(Icon.icon("hourglass_empty", color="#0A0A14"))
                self.btn_dl.setEnabled(False)
                self.progress_circle.set_progress(0.0)
                self.progress_circle.show()
                self.download_playlist_requested.emit(
                    self._playlist_id, 
                    data.get('title', 'Unknown'),
                    thumbnail_url
                )
                
            self.btn_dl.clicked.connect(on_dl_click)
            
            dl_layout.addWidget(self.btn_dl)
            dl_layout.addWidget(self.progress_circle)
            dl_layout.addWidget(self.label_offline_status)
            
            # If there are active tasks, show the downloading state immediately!
            if active_tasks:
                total_progress = sum(t.progress for t in active_tasks)
                overall_pct = total_progress / len(active_tasks)
                self.btn_dl.setText(f" Descargando... {int(overall_pct)}%")
                self.btn_dl.setIcon(Icon.icon("hourglass_empty", color="#0A0A14"))
                self.btn_dl.setEnabled(False)
                self.progress_circle.set_progress(overall_pct)
                self.progress_circle.show()
            
        info_layout.addLayout(dl_layout)
        info_layout.addStretch()
        
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        self.content_layout.addLayout(header_layout)
        
        self.content_layout.addSpacing(24)
        
        self.tracks_layout = QVBoxLayout()
        self.tracks_layout.setSpacing(16)
        self.tracks_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.addLayout(self.tracks_layout)
        self.content_layout.addStretch()
        
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
                card.download_requested.connect(self.download_requested.emit)
                card.play_next_requested.connect(self.play_next_requested.emit)
                card.add_to_queue_requested.connect(self.add_to_queue_requested.emit)
                card.add_to_playlist_requested.connect(self.add_to_playlist_requested.emit)
                card.like_requested.connect(self.like_requested.emit)
                card.delete_download_requested.connect(self.delete_download_requested.emit)
                self.tracks_layout.addWidget(card)

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

    def _update_dl_button_style(self) -> None:
        if hasattr(self, 'btn_dl') and isinstance(self.btn_dl, QPushButton):
            from pyrolist.ui.design import tokens
            from PySide6.QtGui import QColor
            accent = tokens.CURRENT.accent
            c = QColor(accent)
            bright_hex = c.lighter(125).name()
            self.btn_dl.setStyleSheet(f"""
                QPushButton {{
                    background-color: {accent};
                    
                    border: none;
                    border-radius: 16px;
                    padding: 8px 16px;
                    font-weight: bold;
                    margin-top: 12px;
                }}
                QPushButton:hover {{ background-color: {bright_hex}; }}
            """)

    def changeEvent(self, event) -> None:
        from PySide6.QtCore import QEvent
        if event.type() in (QEvent.Type.PaletteChange,):
            if not getattr(self, '_in_style_change', False):
                self._in_style_change = True
                try:
                    self._update_dl_button_style()
                finally:
                    self._in_style_change = False
        super().changeEvent(event)

    def _on_download_progress(self, video_id: str, progress: float, speed: str) -> None:
        self._update_playlist_download_status()

    def _on_download_completed(self, video_id: str, filepath: str) -> None:
        self._update_playlist_download_status()

    def _on_download_error(self, video_id: str, error_msg: str) -> None:
        self._update_playlist_download_status()

    def _update_playlist_download_status(self) -> None:
        if not self._playlist_id:
            return
            
        from pyrolist.services.download_manager import DownloadManager
        dm = DownloadManager.get_instance()
        
        # Get tasks for this playlist
        playlist_tasks = [t for t in dm._tasks.values() if t.parent_playlist_id == self._playlist_id]
        if not playlist_tasks:
            return
            
        # Calculate overall progress
        total_progress = sum(t.progress for t in playlist_tasks)
        overall_pct = total_progress / len(playlist_tasks)
        
        # Update UI
        if hasattr(self, 'btn_dl') and isinstance(self.btn_dl, QPushButton) and self.btn_dl.isVisible():
            self.btn_dl.setText(f" Descargando... {int(overall_pct)}%")
            self.btn_dl.setIcon(Icon.icon("hourglass_empty", color="#0A0A14"))
            self.btn_dl.setEnabled(False)
            
            if hasattr(self, 'progress_circle'):
                self.progress_circle.set_progress(overall_pct)
                self.progress_circle.show()
                
            # If all completed, hide download button and circle, and show online badge
            all_done = all(t.status == "completed" for t in playlist_tasks)
            if all_done:
                self.btn_dl.hide()
                self.progress_circle.hide()
                if hasattr(self, 'label_offline_status'):
                    self.label_offline_status.show()