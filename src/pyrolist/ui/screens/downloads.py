import asyncio
from pathlib import Path
from loguru import logger
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame, QPushButton, QProgressBar, QGridLayout
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QFont, QPixmap

from pyrolist.config.paths import AppDirs
from pyrolist.ui.design.icons import Icon
from pyrolist.ui.widgets.icon_button import IconButton
from pyrolist.services.download_manager import DownloadManager
from pyrolist.db.repository import DownloadRepository


class DownloadItemWidget(QFrame):
    like_requested = Signal(str, object)

    def __init__(self, video_id, title, artist, thumbnail_url, parent_playlist_title=None, on_play_local=None):
        super().__init__()
        self.video_id = video_id
        self.title = title
        self.artist = artist
        self.thumbnail_url = thumbnail_url
        self.parent_playlist_title = parent_playlist_title
        self.on_play_local = on_play_local
        self.file_path = None
        self._build_ui()
        if self.thumbnail_url:
            asyncio.create_task(self._load_thumbnail(self.thumbnail_url))
        asyncio.create_task(self._check_like_state())

    def _build_ui(self):
        self.setObjectName("downloadCard")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        
        self.thumb = QLabel()
        self.thumb.setFixedSize(48, 48)
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setText(Icon.get("music_note"))
        self.thumb.setFont(Icon.font(24))
        layout.addWidget(self.thumb)
        
        info = QVBoxLayout()
        self.title_lbl = QLabel(self.title)
        
        artist_text = self.artist
        if self.parent_playlist_title:
            artist_text += f" • {self.parent_playlist_title}"
        self.artist_lbl = QLabel(artist_text)
        
        info.addWidget(self.title_lbl)
        info.addWidget(self.artist_lbl)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        info.addWidget(self.progress_bar)
        
        layout.addLayout(info)
        layout.addStretch()
        
        self.status_lbl = QLabel("")
        layout.addWidget(self.status_lbl)
        
        # Like button
        self.btn_like = IconButton(size=36, active_color="#F472B6")
        self.btn_like.setText(Icon.get("favorite"))
        self.btn_like.setFont(Icon.font(20, filled=False))
        self.btn_like.setFixedSize(36, 36)
        self.btn_like.clicked.connect(self._on_like)
        layout.addWidget(self.btn_like)
        
        self.play_btn = IconButton(size=36)
        self.play_btn.setText(Icon.get("play_arrow"))
        self.play_btn.setFont(Icon.font(20))
        self.play_btn.setFixedSize(36, 36)
        self.play_btn.clicked.connect(self._on_play)
        self.play_btn.hide()
        layout.addWidget(self.play_btn)
        
        self._update_item_styles()

    def _update_item_styles(self) -> None:
        from pyrolist.ui.design import tokens
        accent = tokens.CURRENT.accent
        text_primary = tokens.CURRENT.text_primary
        text_secondary = tokens.CURRENT.text_secondary
        bg_surface = tokens.CURRENT.bg_surface
        bg_elevated = tokens.CURRENT.bg_elevated
        bg_high = tokens.CURRENT.bg_high
        border = tokens.CURRENT.border
        
        self.setStyleSheet(f"""
            QFrame#downloadCard {{
                background-color: {bg_surface};
                border-radius: 12px;
                border: 1px solid {border};
            }}
            QFrame#downloadCard:hover {{
                background-color: {bg_elevated};
            }}
        """)
        
        if not self.thumb.pixmap():
            self.thumb.setStyleSheet(f"background-color: {bg_high}; color: {text_secondary}; border-radius: 6px;")
        else:
            self.thumb.setStyleSheet("background: transparent; border-radius: 6px;")
            
        self.title_lbl.setStyleSheet(f"color: {text_primary}; font-weight: 600; font-size: 14px; background: transparent; border: none;")
        self.artist_lbl.setStyleSheet(f"color: {text_secondary}; font-size: 12px; background: transparent; border: none;")
        self.status_lbl.setStyleSheet(f"color: {text_secondary}; font-size: 12px; background: transparent; border: none;")
        
        is_liked = getattr(self.btn_like, '_active', False)
        if is_liked:
            self.btn_like.setStyleSheet("QPushButton { color: #F472B6; background: transparent; border: none; }")
        else:
            self.btn_like.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {text_secondary};
                    border: none;
                    border-radius: 18px;
                }}
                QPushButton:hover {{
                    background-color: rgba(244,114,182,0.15);
                    color: #F472B6;
                }}
            """)
            
        self.play_btn.setStyleSheet(f"background: transparent; color: {text_primary}; border: none;")
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{ background: {bg_high}; border-radius: 2px; }}
            QProgressBar::chunk {{ background: {accent}; border-radius: 2px; }}
        """)

    def _on_like(self):
        self.like_requested.emit(self.video_id, self.btn_like)

    async def _check_like_state(self):
        try:
            from pyrolist.db.repository import SongRepository
            repo = SongRepository()
            song = await repo.get_song(self.video_id)
            is_liked = song.is_liked if song else False
            
            # Apply initial style
            self.btn_like.setFont(Icon.font(20, filled=is_liked))
            self.btn_like.set_active(is_liked)
            self._update_item_styles()
        except Exception as e:
            logger.error(f"Error checking like state for {self.video_id}: {e}")

    def set_downloading(self):
        self.progress_bar.show()
        self.status_lbl.setText("Descargando...")
        self.play_btn.hide()

    def update_progress(self, percent, speed):
        self.progress_bar.setValue(int(percent))
        self.status_lbl.setText(f"{percent}% • {speed}")

    def set_completed(self, filepath):
        self.file_path = filepath
        self.progress_bar.hide()
        self.status_lbl.setText("Completado")
        self.status_lbl.hide()
        self.play_btn.show()

    def set_error(self, msg):
        self.progress_bar.hide()
        self.status_lbl.setText("Error")
        self.status_lbl.setStyleSheet("color: #EF4444; font-size: 12px; background: transparent; border: none;")
        self.play_btn.hide()

    def _on_play(self):
        if self.file_path and self.on_play_local:
            metadata = {
                "title": self.title,
                "artist": self.artist,
                "thumbnail_url": self.thumbnail_url
            }
            self.on_play_local(self.file_path, metadata)

    async def _load_thumbnail(self, url: str):
        from pyrolist.utils.image_cache import ImageCache
        cache = ImageCache()
        path = await cache.download(url)
        if path:
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                pixmap = pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                self.thumb.setPixmap(pixmap)
                self._update_item_styles()

    def changeEvent(self, event) -> None:
        from PySide6.QtCore import QEvent
        if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
            if not getattr(self, '_in_style_change', False):
                self._in_style_change = True
                try:
                    self._update_item_styles()
                finally:
                    self._in_style_change = False
        super().changeEvent(event)

class DownloadPlaylistItemWidget(QFrame):
    def __init__(self, playlist_id, title, tracks, on_play_local=None, on_play_local_playlist=None):
        super().__init__()
        self.playlist_id = playlist_id
        self.title = title
        self.tracks = tracks
        self.on_play_local = on_play_local
        self.on_play_local_playlist = on_play_local_playlist
        self.is_expanded = False
        self._build_ui()

    def _build_ui(self):
        self.setObjectName("playlistCard")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header Widget (contains thumbnail, title, stats, play and expand buttons)
        self.header = QFrame()
        self.header.setObjectName("playlistHeader")
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(12, 12, 12, 12)
        
        # Thumbnail
        self.thumb = QLabel()
        self.thumb.setFixedSize(64, 64)
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setText(Icon.get("library_music"))
        self.thumb.setFont(Icon.font(32))
        header_layout.addWidget(self.thumb)
        
        # Metadata Info
        info_layout = QVBoxLayout()
        self.title_lbl = QLabel(self.title)
        
        count = len(self.tracks)
        tracks_text = f"1 canción" if count == 1 else f"{count} canciones"
        self.stats_lbl = QLabel(f"Playlist Offline • {tracks_text}")
        
        info_layout.addWidget(self.title_lbl)
        info_layout.addWidget(self.stats_lbl)
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        
        # Play Playlist Button
        self.play_btn = IconButton(size=40)
        self.play_btn.setText(Icon.get("play_arrow"))
        self.play_btn.setFont(Icon.font(24))
        self.play_btn.setFixedSize(40, 40)
        self.play_btn.clicked.connect(self._on_play_all)
        header_layout.addWidget(self.play_btn)
        
        # Expand/Collapse Arrow
        self.expand_btn = IconButton(size=40)
        self.expand_btn.setText(Icon.get("chevron_right"))
        self.expand_btn.setFont(Icon.font(24))
        self.expand_btn.setFixedSize(40, 40)
        self.expand_btn.clicked.connect(self.toggle_expand)
        header_layout.addWidget(self.expand_btn)
        
        main_layout.addWidget(self.header)
        
        # Contenedor para las canciones (colapsable)
        self.tracks_container = QFrame()
        self.tracks_container.setObjectName("tracksContainer")
        
        container_layout = QVBoxLayout(self.tracks_container)
        container_layout.setContentsMargins(12, 8, 12, 12)
        container_layout.setSpacing(6)
        
        # Agregar los widgets de canciones individuales dentro de la playlist agrupada
        for t in self.tracks:
            widget = DownloadItemWidget(
                video_id=t.video_id,
                title=t.title,
                artist=t.artist,
                thumbnail_url=t.thumbnail_url,
                parent_playlist_title=None,
                on_play_local=self.on_play_local
            )
            widget.set_completed(t.file_path)
            # Make the card style slightly more compact inside the group
            widget.setStyleSheet("QFrame#downloadCard { border-radius: 8px; }")
            container_layout.addWidget(widget)
            
        self.tracks_container.hide()
        main_layout.addWidget(self.tracks_container)
        
        # Permitir expandir haciendo clic en toda la cabecera (excepto si pulsas el botón play)
        self.header.mousePressEvent = self._on_header_clicked
        
        self._update_playlist_item_styles()
        
        # Cargar miniatura de la primera canción si está disponible
        if self.tracks and self.tracks[0].thumbnail_url:
            import asyncio
            asyncio.create_task(self._load_thumbnail(self.tracks[0].thumbnail_url))

    def _update_playlist_item_styles(self) -> None:
        from pyrolist.ui.design import tokens
        accent = tokens.CURRENT.accent
        text_primary = tokens.CURRENT.text_primary
        text_secondary = tokens.CURRENT.text_secondary
        bg_surface = tokens.CURRENT.bg_surface
        bg_elevated = tokens.CURRENT.bg_elevated
        bg_high = tokens.CURRENT.bg_high
        border = tokens.CURRENT.border
        
        self.setStyleSheet(f"""
            QFrame#playlistCard {{
                background-color: {bg_surface};
                border-radius: 12px;
                border: 1px solid {border};
            }}
        """)
        
        radius_style = "border-radius: 12px;" if not self.is_expanded else "border-top-left-radius: 12px; border-top-right-radius: 12px; border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;"
        
        self.header.setStyleSheet(f"""
            QFrame#playlistHeader {{
                background-color: transparent;
                {radius_style}
            }}
            QFrame#playlistHeader:hover {{
                background-color: {bg_elevated};
            }}
        """)
        
        if not self.thumb.pixmap():
            self.thumb.setStyleSheet(f"background-color: {bg_high}; color: {accent}; border-radius: 8px;")
        else:
            self.thumb.setStyleSheet("background: transparent; border-radius: 8px;")
            
        self.title_lbl.setStyleSheet(f"color: {text_primary}; font-weight: 600; font-size: 16px; background: transparent; border: none;")
        self.stats_lbl.setStyleSheet(f"color: {text_secondary}; font-size: 12px; background: transparent; border: none;")
        
        self.play_btn.setStyleSheet(f"""
            QPushButton {{
                background: {accent}1F; 
                color: {accent}; 
                border: none;
                border-radius: 20px;
            }}
            QPushButton:hover {{
                background: {accent};
                color: {bg_surface};
            }}
        """)
        
        self.expand_btn.setStyleSheet(f"background: transparent; color: {text_secondary}; border: none;")
        
        self.tracks_container.setStyleSheet(f"""
            QFrame#tracksContainer {{
                background-color: {bg_elevated};
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
                border-top: 1px solid {border};
            }}
        """)

    def _on_header_clicked(self, event):
        pos = event.position().toPoint()
        child = self.header.childAt(pos)
        if child in [self.play_btn, self.expand_btn] or (child and child.parent() in [self.play_btn, self.expand_btn]):
            return
        self.toggle_expand()

    def toggle_expand(self):
        self.is_expanded = not self.is_expanded
        if self.is_expanded:
            self.tracks_container.show()
            self.expand_btn.setText(Icon.get("expand_more"))
        else:
            self.tracks_container.hide()
            self.expand_btn.setText(Icon.get("chevron_right"))
        self._update_playlist_item_styles()

    def _on_play_all(self):
        if self.tracks and self.on_play_local_playlist:
            tracks_meta = []
            for t in self.tracks:
                tracks_meta.append({
                    "title": t.title,
                    "artist": t.artist,
                    "thumbnail_url": t.thumbnail_url,
                    "file_path": t.file_path,
                    "duration_ms": t.duration_ms
                })
            self.on_play_local_playlist(tracks_meta, 0)

    async def _load_thumbnail(self, url: str):
        from pyrolist.utils.image_cache import ImageCache
        cache = ImageCache()
        path = await cache.download(url)
        if path:
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                pixmap = pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                self.thumb.setPixmap(pixmap)
                self._update_playlist_item_styles()

    def changeEvent(self, event) -> None:
        from PySide6.QtCore import QEvent
        if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
            if not getattr(self, '_in_style_change', False):
                self._in_style_change = True
                try:
                    self._update_playlist_item_styles()
                finally:
                    self._in_style_change = False
        super().changeEvent(event)

class DownloadsScreen(QWidget):
    like_requested = Signal(str, object)

    def __init__(self, extractor, on_play_local, on_play_local_playlist=None, on_navigate=None):
        super().__init__()
        self.extractor = extractor
        self.on_play_local = on_play_local
        self.on_play_local_playlist = on_play_local_playlist
        self.on_navigate = on_navigate
        self._current_tab = "songs"
        self._items = {} # video_id -> DownloadItemWidget
        self._repo = DownloadRepository()
        self._build_ui()
        self._connect_manager()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(20)

        from pyrolist.ui.design import tokens
        self.header = QLabel("Descargas")
        self.header.setFont(QFont("Inter", 24, QFont.Weight.Bold))
        self.header.setStyleSheet(f"color: {tokens.CURRENT.text_primary};")
        layout.addWidget(self.header)

        # Tabs
        self.tabs = QWidget()
        tabs_layout = QHBoxLayout(self.tabs)
        tabs_layout.setSpacing(16)
        
        tab_names = [
            ("songs", "Canciones"),
            ("playlists", "Playlists Completas")
        ]
        
        self.tab_btns = {}
        for key, name in tab_names:
            btn = QPushButton(name)
            btn.setObjectName(f"tab_{key}")
            btn.setStyleSheet(self._tab_style(key == self._current_tab))
            btn.clicked.connect(lambda _, k=key: self._switch_tab(k))
            tabs_layout.addWidget(btn)
            self.tab_btns[key] = btn
        
        tabs_layout.addStretch()
        layout.addWidget(self.tabs)

        self.content_area = QScrollArea()
        self.content_area.setWidgetResizable(True)
        self.content_area.setStyleSheet("background: transparent; border: none;")
        
        self.scroll_content = QWidget()
        self.content_layout = QVBoxLayout(self.scroll_content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        self.content_layout.addStretch()
        
        self.content_area.setWidget(self.scroll_content)
        layout.addWidget(self.content_area)

    def _tab_style(self, active: bool):
        from pyrolist.ui.design import tokens
        accent = tokens.CURRENT.accent
        accent_dim = tokens.CURRENT.accent_dim
        text_primary = tokens.CURRENT.text_primary
        text_secondary = tokens.CURRENT.text_secondary
        bg_elevated = tokens.CURRENT.bg_elevated
        if active:
            return f"""
                QPushButton {{
                    background: {accent_dim};
                    color: {accent};
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-weight: bold;
                    border: none;
                }}
            """
        return f"""
            QPushButton {{
                background: transparent;
                color: {text_secondary};
                padding: 8px 16px;
                border: none;
                border-radius: 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {bg_elevated};
                color: {text_primary};
            }}
        """

    def _switch_tab(self, key):
        self._current_tab = key
        for k, btn in self.tab_btns.items():
            btn.setStyleSheet(self._tab_style(k == key))
        asyncio.ensure_future(self.load())

    def _connect_manager(self):
        mgr = DownloadManager.get_instance()
        mgr.download_queued.connect(self._on_download_queued)
        mgr.download_started.connect(self._on_download_started)
        mgr.download_progress.connect(self._on_download_progress)
        mgr.download_completed.connect(self._on_download_completed)
        mgr.download_error.connect(self._on_download_error)

    def _on_download_queued(self, task):
        # Add to UI if matches current tab
        is_playlist = task.parent_playlist_id is not None
        if (self._current_tab == "playlists" and is_playlist) or (self._current_tab == "songs" and not is_playlist):
            self._add_item_to_ui(task.video_id, task.title, task.artist, task.thumbnail_url, task.parent_playlist_title)
            self._items[task.video_id].set_downloading()

    def _on_download_started(self, video_id):
        if video_id in self._items:
            self._items[video_id].set_downloading()

    def _on_download_progress(self, video_id, percent, speed):
        if video_id in self._items:
            self._items[video_id].update_progress(percent, speed)

    def _on_download_completed(self, video_id, filepath):
        if video_id in self._items:
            self._items[video_id].set_completed(filepath)

    def _on_download_error(self, video_id, error_msg):
        if video_id in self._items:
            self._items[video_id].set_error(error_msg)

    def _add_item_to_ui(self, vid, title, artist, thumb_url, parent_playlist_title=None):
        if vid in self._items:
            return
        widget = DownloadItemWidget(vid, title, artist, thumb_url, parent_playlist_title, self.on_play_local)
        widget.like_requested.connect(self.like_requested.emit)
        self.content_layout.insertWidget(0, widget)
        self._items[vid] = widget

    async def load(self):
        while self.content_layout.count() > 1:
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._items.clear()

        downloads = await self._repo.get_downloads()
        
        if self._current_tab == "playlists":
            # Group downloaded items by parent_playlist_id
            playlist_groups = {}
            for d in downloads:
                if d.parent_playlist_id:
                    pid = d.parent_playlist_id
                    if pid not in playlist_groups:
                        playlist_groups[pid] = {
                            "title": d.parent_playlist_title or "Playlist Local",
                            "tracks": []
                        }
                    playlist_groups[pid]["tracks"].append(d)
            
            if not playlist_groups:
                msg = QLabel("No hay playlists descargadas.")
                msg.setStyleSheet("color: #888899; font-size: 16px; padding: 40px;")
                msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.content_layout.insertWidget(0, msg)
            else:
                from pyrolist.ui.widgets.playlist_card import PlaylistCard
                grid_widget = QWidget()
                grid_layout = QGridLayout(grid_widget)
                grid_layout.setSpacing(24)
                grid_layout.setContentsMargins(0, 0, 0, 0)
                grid_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
                
                columns = 4
                for index, (pid, info) in enumerate(playlist_groups.items()):
                    row = index // columns
                    col = index % columns
                    
                    tracks = info["tracks"]
                    first_thumb = tracks[0].thumbnail_url if tracks else ""
                    
                    card = PlaylistCard(
                        title=info["title"],
                        description=f"{len(tracks)} canciones",
                        thumbnail_url=first_thumb
                    )
                    if self.on_navigate:
                        card.clicked.connect(lambda p=pid: self.on_navigate(f"playlist?id=local_{p}"))
                        
                    grid_layout.addWidget(card, row, col)
                
                self.content_layout.insertWidget(0, grid_widget)
        else:
            # "songs" tab: Show all downloads individually (both completed and active)
            if not downloads:
                msg = QLabel("No hay descargas aquí.")
                msg.setStyleSheet("color: #888899; font-size: 16px; padding: 40px;")
                msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.content_layout.insertWidget(0, msg)
            
            for d in reversed(downloads):
                self._add_item_to_ui(d.video_id, d.title, d.artist, d.thumbnail_url, d.parent_playlist_title)
                if d.video_id in self._items:
                    self._items[d.video_id].set_completed(d.file_path)
                
            # Add active downloads from manager
            mgr = DownloadManager.get_instance()
            for vid, task in mgr._tasks.items():
                if vid not in self._items:
                    self._add_item_to_ui(task.video_id, task.title, task.artist, task.thumbnail_url, task.parent_playlist_title)
                    if task.status == "downloading":
                        self._items[vid].set_downloading()
                    elif task.status == "error":
                        self._items[vid].set_error("Error")

    def _update_downloads_styles(self) -> None:
        from pyrolist.ui.design import tokens
        if hasattr(self, "header"):
            self.header.setStyleSheet(f"color: {tokens.CURRENT.text_primary};")
        if hasattr(self, "tab_btns"):
            for key, btn in self.tab_btns.items():
                btn.setStyleSheet(self._tab_style(key == self._current_tab))
        
        for label in self.findChildren(QLabel):
            if label != getattr(self, "header", None) and label.parent() == getattr(self, "scroll_content", None):
                label.setStyleSheet(f"color: {tokens.CURRENT.text_secondary}; font-size: 16px; padding: 40px; background: transparent; border: none;")

    def changeEvent(self, event) -> None:
        from PySide6.QtCore import QEvent
        if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
            if not getattr(self, '_in_style_change', False):
                self._in_style_change = True
                try:
                    self._update_downloads_styles()
                finally:
                    self._in_style_change = False
        super().changeEvent(event)
