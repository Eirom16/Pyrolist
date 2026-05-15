from functools import partial
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QHBoxLayout, QPushButton, QGridLayout, QGraphicsOpacityEffect
from qasync import asyncSlot
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
import asyncio
from loguru import logger
from pyrolist.ui.design.fonts import AppFont
from pyrolist.ui.widgets.song_card import SongCard
from pyrolist.ui.widgets.album_card import AlbumCard
from pyrolist.ui.widgets.artist_card import ArtistCard
from pyrolist.ui.widgets.playlist_card import PlaylistCard
from pyrolist.ui.widgets.skeleton_loader import SkeletonListLoader


class LibraryScreen(QWidget):
    download_requested = Signal(str, str, str, str)  # video_id, title, artist, thumb
    play_next_requested = Signal(str, str, str, str)
    add_to_queue_requested = Signal(str, str, str, str)
    add_to_playlist_requested = Signal(str, str) # video_id, title
    like_requested = Signal(str, object)

    def __init__(self, yt_client, on_play_song, on_navigate=None):
        super().__init__()
        self.yt = yt_client
        self.on_play_song = on_play_song
        self.on_navigate = on_navigate
        self._current_tab = "songs"
        self._build_ui()
    
    def _connect_card_signals(self, card):
        """Wire up all context-menu signals from a SongCard."""
        card.download_requested.connect(lambda *a: self.download_requested.emit(*a))
        card.play_next_requested.connect(lambda *a: self.play_next_requested.emit(*a))
        card.add_to_queue_requested.connect(lambda *a: self.add_to_queue_requested.emit(*a))
        card.add_to_playlist_requested.connect(lambda *a: self.add_to_playlist_requested.emit(*a))
        card.like_requested.connect(lambda *a: self.like_requested.emit(*a))

    def _handle_download(self, vid, title, artist, thumb):
        self.download_requested.emit(vid, title, artist, thumb)

    def _handle_play(self, video_id, title, artists):
        try:
            if self.on_play_song:
                self.on_play_song(video_id, title, artists, "", 0, "")
        except Exception as e:
            logger.error(f"Play error: {e}")

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)

        header = QLabel("Biblioteca")
        header.setFont(AppFont.display(24))
        header.setStyleSheet("color: #F1F0FF;")
        layout.addWidget(header)

        self.tabs = QWidget()
        tabs_layout = QHBoxLayout(self.tabs)
        tabs_layout.setSpacing(16)

        tab_names = [
            ("songs", "Favoritas"),
            ("albums", "Álbumes"),
            ("artists", "Artistas"),
            ("playlists", "Playlists"),
        ]

        for key, name in tab_names:
            btn = QPushButton(name)
            btn.setObjectName(f"tab_{key}")
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #888899;
                    padding: 8px 16px;
                    border: none;
                    border-radius: 20px;
                }
                QPushButton:hover {
                    background: #2A2A3E;
                    color: #FFFFFF;
                }
            """)
            if key == self._current_tab:
                btn.setStyleSheet("""
                    QPushButton {
                        background: #2D1B69;
                        color: #BB86FC;
                        padding: 8px 16px;
                        border-radius: 20px;
                    }
                """)
            btn.clicked.connect(lambda _, k=key: self._switch_tab(k))
            tabs_layout.addWidget(btn)

        layout.addWidget(self.tabs)

        self.content = QScrollArea()
        self.content.setWidgetResizable(True)
        self.content.setStyleSheet("background: transparent; border: none;")

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)

        self.content.setWidget(self.content_widget)
        layout.addWidget(self.content)

    def _switch_tab(self, key):
        self._current_tab = key

        for btn in self.tabs.findChildren(QPushButton):
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #888899;
                    padding: 8px 16px;
                    border: none;
                    border-radius: 20px;
                }
                QPushButton:hover {
                    background: #2A2A3E;
                    color: #FFFFFF;
                }
            """)

        clicked_btn = self.tabs.findChild(QPushButton, f"tab_{key}")
        if clicked_btn:
            clicked_btn.setStyleSheet("""
                QPushButton {
                    background: #2D1B69;
                    color: #BB86FC;
                    padding: 8px 16px;
                    border-radius: 20px;
                }
            """)

        asyncio.ensure_future(self._load_tab(key))

    async def load(self):
        await self._load_tab(self._current_tab)

    async def _load_tab(self, tab):
        self._clear_content()
        self.content_layout.addWidget(SkeletonListLoader(row_count=7))

        if not self.yt or not self.yt.is_authenticated:
            self._clear_content()
            self.content_layout.addWidget(QLabel("Inicia sesión para ver tu biblioteca"))
            self.content_layout.addStretch()
            return

        try:
            self._clear_content()
            
            if tab == "songs":
                await self._load_liked_songs()
            elif tab == "albums":
                await self._load_albums()
            elif tab == "artists":
                await self._load_artists()
            elif tab == "playlists":
                await self._load_playlists()
        except Exception as e:
            from loguru import logger
            logger.error(f"Error loading {tab}: {e}")
            self._show_no_auth_message()

        self.content_layout.addStretch()
        self._fade_in_content()

    def _clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _fade_in_content(self):
        """Smooth fade-in animation when content finishes loading."""
        effect = QGraphicsOpacityEffect(self.content_widget)
        self.content_widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(300)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: self.content_widget.setGraphicsEffect(None))
        anim.start()

    def _show_no_auth_message(self):
        self.content_layout.addWidget(QLabel(""))
        msg = QLabel("Biblioteca no disponible.\nLa API de YouTube Music requiere autenticación.")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet("color: #B0B0C0; font-size: 14px; padding: 40px;")
        self.content_layout.addWidget(msg)

    async def _load_liked_songs(self):
        if self.yt and self.yt.is_authenticated:
            liked_result = await self.yt.get_liked_songs(limit=50)
            tracks = liked_result.get('tracks', [])
            
            if tracks:
                header = QLabel("Canciones que te gustan")
                header.setFont(AppFont.heading(16))
                header.setStyleSheet("color: #F1F0FF;")
                self.content_layout.addWidget(header)
                
                for track in tracks:
                    title = track.get('title', 'Unknown')
                    artists = track.get('artists', [])
                    artist_names = ", ".join([a.get('name', '') for a in artists]) if isinstance(artists, list) and artists else 'Unknown'
                    video_id = track.get('videoId', '')
                    duration_str = track.get('duration', '')  # ytmusicapi returns "3:45" string
                    thumbnails = track.get('thumbnails', [])
                    thumbnail_url = thumbnails[-1].get('url', '') if thumbnails else ''
                    
                    if video_id:
                        card = SongCard(
                            title=title,
                            artist=artist_names,
                            duration=duration_str,
                            thumbnail_url=thumbnail_url,
                            on_play=partial(self._handle_play, video_id, title, artist_names),
                            video_id=video_id,
                            is_liked=True,
                        )
                        self._connect_card_signals(card)
                        self.content_layout.addWidget(card)
                return

        from pyrolist.db.repository import SongRepository
        repo = SongRepository()
        songs = await repo.get_liked_songs()

        if not songs:
            msg = QLabel("No tienes canciones guardadas\n\nLas canciones que reproduzcas apareceran aqui")
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg.setStyleSheet("color: #888899; font-size: 14px; padding: 40px;")
            self.content_layout.addWidget(msg)
            return

        header = QLabel("Canciones que te gustan")
        header.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        header.setStyleSheet("color: #FFFFFF;")
        self.content_layout.addWidget(header)

        for song in songs:
            card = SongCard(
                title=song.title,
                artist=song.artist,
                duration=self._format_duration(song.duration_ms),
                thumbnail_url=song.thumbnail_url or "",
                on_play=partial(self._handle_play, song.video_id, song.title, song.artist),
                video_id=song.video_id,
                is_liked=True
            )
            self._connect_card_signals(card)
            self.content_layout.addWidget(card)

    def _format_duration(self, ms):
        if not ms:
            return ""
        seconds = ms // 1000
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins}:{secs:02d}"

    async def _load_albums(self):
        albums = await self.yt.get_library_albums()
        if not albums:
            msg = QLabel("No tienes albumes guardados")
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg.setStyleSheet("color: #888899; font-size: 14px; padding: 40px;")
            self.content_layout.addWidget(msg)
            return

        header = QLabel("Tus Álbumes")
        header.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        header.setStyleSheet("color: #FFFFFF;")
        self.content_layout.addWidget(header)

        grid = QGridLayout()
        grid.setSpacing(16)
        
        for i, album in enumerate(albums):
            title = album.get("title", "Unknown")
            artists = album.get("artists", [])
            artist_names = ", ".join([a.get('name', '') for a in artists]) if isinstance(artists, list) else str(artists)
            year = album.get("year", "")
            thumbnails = album.get('thumbnails', [])
            thumbnail_url = thumbnails[-1].get('url', '') if thumbnails else ''
            browse_id = album.get('browseId', '')
            
            card = AlbumCard(title=title, artist=artist_names, year=year, thumbnail_url=thumbnail_url)
            if browse_id and self.on_navigate:
                card.clicked.connect(partial(self.on_navigate, f"album?id={browse_id}"))
            grid.addWidget(card, i // 4, i % 4)

        self.content_layout.addLayout(grid)

    async def _load_artists(self):
        artists = await self.yt.get_library_artists()
        if not artists:
            msg = QLabel("No sigues a ningun artista")
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg.setStyleSheet("color: #888899; font-size: 14px; padding: 40px;")
            self.content_layout.addWidget(msg)
            return

        header = QLabel("Tus Artistas")
        header.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        header.setStyleSheet("color: #FFFFFF;")
        self.content_layout.addWidget(header)

        grid = QGridLayout()
        grid.setSpacing(16)
        
        for i, artist in enumerate(artists):
            name = artist.get("artist", "Unknown")
            thumbnails = artist.get('thumbnails', [])
            thumbnail_url = thumbnails[-1].get('url', '') if thumbnails else ''
            browse_id = artist.get('browseId', '')
            
            card = ArtistCard(name=name, thumbnail_url=thumbnail_url)
            if browse_id and self.on_navigate:
                card.clicked.connect(partial(self.on_navigate, f"artist?id={browse_id}"))
            grid.addWidget(card, i // 4, i % 4)

        self.content_layout.addLayout(grid)

    async def _load_playlists(self):
        playlists = await self.yt.get_library_playlists()
        
        header_layout = QHBoxLayout()
        header = QLabel("Tus Playlists")
        header.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        header.setStyleSheet("color: #FFFFFF;")
        header_layout.addWidget(header)
        
        btn_create = QPushButton("➕ Crear Playlist")
        btn_create.setStyleSheet("""
            QPushButton {
                background-color: #2D1B69;
                color: #F1F0FF;
                border: none;
                border-radius: 16px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3B2A85; }
        """)
        btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_create.clicked.connect(self._on_create_playlist_clicked)
        header_layout.addWidget(btn_create)
        header_layout.addStretch()
        
        self.content_layout.addLayout(header_layout)

        if not playlists:
            msg = QLabel("No tienes playlists")
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg.setStyleSheet("color: #888899; font-size: 14px; padding: 40px;")
            self.content_layout.addWidget(msg)
            return

        grid = QGridLayout()
        grid.setSpacing(16)
        
        for i, playlist in enumerate(playlists):
            title = playlist.get("title", "Unknown")
            count = playlist.get("count", "")
            desc = f"{count} canciones" if count else ""
            thumbnails = playlist.get('thumbnails', [])
            thumbnail_url = thumbnails[-1].get('url', '') if thumbnails else ''
            playlist_id = playlist.get('playlistId', '')
            
            card = PlaylistCard(title=title, description=desc, thumbnail_url=thumbnail_url)
            if playlist_id and self.on_navigate:
                card.clicked.connect(partial(self.on_navigate, f"playlist?id={playlist_id}"))
            grid.addWidget(card, i // 4, i % 4)

        self.content_layout.addLayout(grid)

    def _on_create_playlist_clicked(self):
        from PySide6.QtWidgets import QDialog, QLineEdit, QDialogButtonBox, QVBoxLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Crear Nueva Playlist")
        dialog.setFixedWidth(400)
        dialog.setStyleSheet("background-color: #10101E; color: #F1F0FF;")
        
        layout = QVBoxLayout(dialog)
        
        title_input = QLineEdit()
        title_input.setPlaceholderText("Nombre de la playlist")
        title_input.setStyleSheet("""
            QLineEdit {
                background: #1E1E38; border: none; border-radius: 8px; padding: 12px;
                color: #F1F0FF; font-size: 14px;
            }
        """)
        layout.addWidget(title_input)
        
        desc_input = QLineEdit()
        desc_input.setPlaceholderText("Descripción (opcional)")
        desc_input.setStyleSheet("""
            QLineEdit {
                background: #1E1E38; border: none; border-radius: 8px; padding: 12px;
                color: #F1F0FF; font-size: 14px;
            }
        """)
        layout.addWidget(desc_input)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Crear")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        button_box.setStyleSheet("""
            QPushButton {
                background: #A78BFA; color: #0A0A14; border: none; border-radius: 8px; padding: 8px 16px; font-weight: bold;
            }
            QPushButton:hover { background: #BBA4FC; }
        """)
        layout.addWidget(button_box)
        
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            title = title_input.text().strip()
            desc = desc_input.text().strip()
            if title:
                asyncio.ensure_future(self._create_playlist_async(title, desc))

    async def _create_playlist_async(self, title: str, description: str):
        try:
            pid = await self.yt.create_playlist(title, description)
            if pid:
                # Reload the playlists tab to show the new one
                self._switch_tab("playlists")
        except Exception as e:
            from loguru import logger
            logger.error(f"Error creating playlist: {e}")
