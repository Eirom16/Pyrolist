from functools import partial
import asyncio
from loguru import logger

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QHBoxLayout, 
    QPushButton, QGridLayout, QGraphicsOpacityEffect, QGraphicsDropShadowEffect
)

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
    delete_download_requested = Signal(str)

    def __init__(self, yt_client, on_play_song, on_navigate=None):
        super().__init__()
        self.yt = yt_client
        self.on_play_song = on_play_song
        self.on_navigate = on_navigate
        self._current_tab = "songs"
        self._current_tab_task = None
        self._build_ui()

    def _connect_card_signals(self, card):
        """Wire up all context-menu signals from a SongCard."""
        card.download_requested.connect(lambda *a: self.download_requested.emit(*a))
        card.play_next_requested.connect(lambda *a: self.play_next_requested.emit(*a))
        card.add_to_queue_requested.connect(lambda *a: self.add_to_queue_requested.emit(*a))
        card.add_to_playlist_requested.connect(lambda *a: self.add_to_playlist_requested.emit(*a))
        card.like_requested.connect(lambda *a: self.like_requested.emit(*a))
        card.delete_download_requested.connect(lambda *a: self.delete_download_requested.emit(*a))

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

        self.header_label = QLabel("Biblioteca")
        self.header_label.setFont(AppFont.display(24))
        layout.addWidget(self.header_label)

        # Tab container
        self.tabs = QWidget()
        tabs_layout = QHBoxLayout(self.tabs)
        tabs_layout.setContentsMargins(0, 8, 0, 8)
        tabs_layout.setSpacing(12)

        tab_names = [
            ("songs", "Favoritas"),
            ("albums", "Álbumes"),
            ("artists", "Artistas"),
            ("playlists", "Playlists"),
        ]

        for key, name in tab_names:
            btn = QPushButton(name)
            btn.setObjectName(f"tab_{key}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Apply styling
            self._apply_tab_style(btn, key == self._current_tab)
            
            btn.clicked.connect(lambda _, k=key: self._switch_tab(k))
            tabs_layout.addWidget(btn)

        tabs_layout.addStretch()
        layout.addWidget(self.tabs)

        self.content = QScrollArea()
        self.content.setWidgetResizable(True)
        self.content.setStyleSheet("background: transparent; border: none;")

        self.content_widget = QWidget()
        self._content_wrapper_layout = QVBoxLayout(self.content_widget)
        self._content_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(24, 0, 24, 24)
        self.content_layout.setSpacing(16)
        
        self._content_wrapper_layout.addLayout(self.content_layout)
        self._content_wrapper_layout.addStretch()

        self.content.setWidget(self.content_widget)
        layout.addWidget(self.content)

        # Create Floating Action Button (FAB) for playlists
        self.fab = QPushButton("+", self)
        self.fab.setFixedSize(56, 56)
        self.fab.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fab.setToolTip("Crear Playlist")
        self.fab.clicked.connect(self._on_create_playlist_clicked)
        
        # Style the FAB
        self._update_fab_style()
        
        # Add elevation/shadow to FAB
        shadow = QGraphicsDropShadowEffect(self.fab)
        shadow.setBlurRadius(16)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.fab.setGraphicsEffect(shadow)
        
        # Hidden by default, shown only when playlists tab is active
        self.fab.hide()
        
        self._update_library_styles()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "fab"):
            # Place at bottom right with 24px margin
            self.fab.move(self.width() - self.fab.width() - 24, self.height() - self.fab.height() - 24)

    def _switch_tab(self, key):
        self._current_tab = key

        # Update button styles
        self._update_tab_styles()

        # Toggle FAB visibility depending on selected tab
        if key == "playlists":
            self.fab.show()
            self.fab.raise_()
        else:
            self.fab.hide()

        if self._current_tab_task and not self._current_tab_task.done():
            self._current_tab_task.cancel()
        self._current_tab_task = asyncio.create_task(self._load_tab(key))

    async def load(self):
        if self._current_tab_task and not self._current_tab_task.done():
            self._current_tab_task.cancel()
        self._current_tab_task = asyncio.create_task(self._load_tab(self._current_tab))
        try:
            await self._current_tab_task
        except asyncio.CancelledError:
            if self._current_tab_task and not self._current_tab_task.done():
                self._current_tab_task.cancel()
            raise

    async def _load_tab(self, tab):
        # 1. Clear content and show the skeleton loader
        self._clear_content()
        self.content_layout.addWidget(SkeletonListLoader(row_count=7))

        try:
            from pyrolist.db.repository import DownloadRepository
            dl_repo = DownloadRepository()
            downloads = await dl_repo.get_downloads()
            self.downloaded_playlist_ids = {d.parent_playlist_id for d in downloads if d.parent_playlist_id}
        except Exception as e:
            logger.debug(f"Error fetching downloads: {e}")
            self.downloaded_playlist_ids = set()

        if not self.yt or not self.yt.is_authenticated:
            self._clear_content()
            from pyrolist.ui.design import tokens
            msg = QLabel("Inicia sesión para ver tu biblioteca")
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg.setObjectName("libraryEmptyMessage")
            self.content_layout.addWidget(msg)
            self.content_layout.addStretch()
            return

        try:
            from pyrolist.ui.design import tokens
            # 2. Perform async fetch while skeleton is active
            if tab == "songs":
                liked_songs_data = None
                if self.yt and self.yt.is_authenticated:
                    liked_songs_data = await self.yt.get_liked_songs(limit=50)
                
                from pyrolist.db.repository import SongRepository
                repo = SongRepository()
                db_songs = await repo.get_liked_songs()
                
                # 3. Fetch completed: clear loader and render real data
                self._clear_content()
                
                tracks = liked_songs_data.get('tracks', []) if liked_songs_data else []
                if tracks:
                    header = QLabel("Canciones que te gustan")
                    header.setFont(AppFont.heading(16))
                    header.setObjectName("libraryHeader")
                    self.content_layout.addWidget(header)
                    
                    for i, track in enumerate(tracks):
                        title = track.get('title', 'Unknown')
                        artists = track.get('artists', [])
                        artist_names = ", ".join([a.get('name', '') for a in artists]) if isinstance(artists, list) and artists else 'Unknown'
                        video_id = track.get('videoId', '')
                        duration_str = track.get('duration', '')
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
                elif db_songs:
                    header = QLabel("Canciones que te gustan")
                    header.setFont(QFont("Inter", 16, QFont.Weight.Bold))
                    header.setObjectName("libraryHeader")
                    self.content_layout.addWidget(header)

                    for i, song in enumerate(db_songs):
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
                else:
                    msg = QLabel("No tienes canciones guardadas\n\nLas canciones que reproduzcas aparecerán aquí")
                    msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    msg.setObjectName("libraryEmptyMessage")
                    self.content_layout.addWidget(msg)

            elif tab == "albums":
                albums = await self.yt.get_library_albums()
                self._clear_content()

                if not albums:
                    msg = QLabel("No tienes álbumes guardados")
                    msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    msg.setObjectName("libraryEmptyMessage")
                    self.content_layout.addWidget(msg)
                else:
                    header = QLabel("Tus Álbumes")
                    header.setFont(QFont("Inter", 16, QFont.Weight.Bold))
                    header.setObjectName("libraryHeader")
                    self.content_layout.addWidget(header)

                    grid = QGridLayout()
                    grid.setSpacing(16)
                    for col in range(4):
                        grid.setColumnMinimumWidth(col, 178)
                    
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
                        
                        # Added alignment to prevent card expansion and overlaps
                        grid.addWidget(card, i // 4, i % 4, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
                        grid.setRowMinimumHeight(i // 4, 228)

                    self.content_layout.addLayout(grid)

            elif tab == "artists":
                artists = await self.yt.get_library_artists()
                self._clear_content()

                if not artists:
                    msg = QLabel("No sigues a ningún artista")
                    msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    msg.setObjectName("libraryEmptyMessage")
                    self.content_layout.addWidget(msg)
                else:
                    header = QLabel("Tus Artistas")
                    header.setFont(QFont("Inter", 16, QFont.Weight.Bold))
                    header.setObjectName("libraryHeader")
                    self.content_layout.addWidget(header)

                    grid = QGridLayout()
                    grid.setSpacing(16)
                    for col in range(4):
                        grid.setColumnMinimumWidth(col, 178)

                    for i, artist in enumerate(artists):
                        name = artist.get("artist", "Unknown")
                        thumbnails = artist.get('thumbnails', [])
                        thumbnail_url = thumbnails[-1].get('url', '') if thumbnails else ''
                        browse_id = artist.get('browseId', '')
                        
                        card = ArtistCard(name=name, thumbnail_url=thumbnail_url)
                        if browse_id and self.on_navigate:
                            card.clicked.connect(partial(self.on_navigate, f"artist?id={browse_id}"))
                        
                        grid.addWidget(card, i // 4, i % 4, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
                        grid.setRowMinimumHeight(i // 4, 220)

                    self.content_layout.addLayout(grid)

            elif tab == "playlists":
                playlists = await self.yt.get_library_playlists()
                self._clear_content()

                header = QLabel("Tus Playlists")
                header.setFont(QFont("Inter", 16, QFont.Weight.Bold))
                header.setObjectName("libraryHeader")
                self.content_layout.addWidget(header)

                if not playlists:
                    msg = QLabel("No tienes playlists")
                    msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    msg.setObjectName("libraryEmptyMessage")
                    self.content_layout.addWidget(msg)
                else:
                    grid = QGridLayout()
                    grid.setSpacing(16)
                    for col in range(4):
                        grid.setColumnMinimumWidth(col, 178)

                    for i, playlist in enumerate(playlists):
                        title = playlist.get("title", "Unknown")
                        count = playlist.get("count", "")
                        desc = f"{count} canciones" if count else ""
                        thumbnails = playlist.get('thumbnails', [])
                        thumbnail_url = thumbnails[-1].get('url', '') if thumbnails else ''
                        playlist_id = playlist.get('playlistId', '')
                        
                        card = PlaylistCard(
                            title=title,
                            description=desc,
                            thumbnail_url=thumbnail_url,
                            is_downloaded=playlist_id in getattr(self, "downloaded_playlist_ids", set())
                        )
                        if playlist_id and self.on_navigate:
                            card.clicked.connect(partial(self.on_navigate, f"playlist?id={playlist_id}"))
                        
                        grid.addWidget(card, i // 4, i % 4, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
                        grid.setRowMinimumHeight(i // 4, 228)

                    self.content_layout.addLayout(grid)

        except Exception as e:
            logger.error(f"Error loading {tab}: {e}")
            self._clear_content()
            self._show_no_auth_message()

        self.content_layout.addStretch()
        self._fade_in_content()

        # Bring FAB to top after updating layout to prevent overlap issues
        if hasattr(self, "fab") and self.fab.isVisible():
            self.fab.raise_()

    def _clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # Recursively delete layouts if present
                self._clear_sub_layout(item.layout())

    def _clear_sub_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    self._clear_sub_layout(item.layout())

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
        msg.setObjectName("libraryEmptyMessage")
        self.content_layout.addWidget(msg)

    def _format_duration(self, ms):
        if not ms:
            return ""
        seconds = ms // 1000
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins}:{secs:02d}"

    def _on_create_playlist_clicked(self):
        from PySide6.QtWidgets import QDialog, QLineEdit, QDialogButtonBox, QVBoxLayout
        from pyrolist.ui.design import tokens
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Crear Nueva Playlist")
        dialog.setFixedWidth(400)
        dialog.setStyleSheet(f"background-color: {tokens.CURRENT.bg_surface}; color: {tokens.CURRENT.text_primary};")
        
        layout = QVBoxLayout(dialog)
        
        title_input = QLineEdit()
        title_input.setPlaceholderText("Nombre de la playlist")
        title_input.setStyleSheet(f"""
            QLineEdit {{
                background: {tokens.CURRENT.bg_elevated}; border: 1px solid {tokens.CURRENT.border}; border-radius: 8px; padding: 12px;
                color: {tokens.CURRENT.text_primary}; font-size: 14px;
            }}
        """)
        layout.addWidget(title_input)
        
        desc_input = QLineEdit()
        desc_input.setPlaceholderText("Descripción (opcional)")
        desc_input.setStyleSheet(f"""
            QLineEdit {{
                background: {tokens.CURRENT.bg_elevated}; border: 1px solid {tokens.CURRENT.border}; border-radius: 8px; padding: 12px;
                color: {tokens.CURRENT.text_primary}; font-size: 14px;
            }}
        """)
        layout.addWidget(desc_input)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Crear")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        from PySide6.QtGui import QColor
        accent = tokens.CURRENT.accent
        c = QColor(accent)
        bright_hex = c.lighter(125).name()
        button_box.setStyleSheet(f"""
            QPushButton {{
                background: {accent}; color: {tokens.CURRENT.text_on_accent}; border: none; border-radius: 8px; padding: 8px 16px; font-weight: bold;
            }}
            QPushButton:hover {{ background: {bright_hex}; }}
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
            logger.error(f"Error creating playlist: {e}")

    def _apply_tab_style(self, btn, active: bool) -> None:
        from pyrolist.ui.design import tokens
        from PySide6.QtGui import QColor
        accent = tokens.CURRENT.accent
        c = QColor(accent)
        r, g, b, _ = c.getRgb()
        if active:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba({r}, {g}, {b}, 0.15);
                    color: {accent};
                    padding: 8px 18px;
                    border: 1px solid rgba({r}, {g}, {b}, 0.3);
                    border-radius: 18px;
                    font-family: 'Inter';
                    font-weight: bold;
                    font-size: 13px;
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {tokens.CURRENT.text_secondary};
                    padding: 8px 18px;
                    border: 1px solid transparent;
                    border-radius: 18px;
                    font-family: 'Inter';
                    font-weight: 600;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background: {tokens.CURRENT.bg_elevated};
                    color: {tokens.CURRENT.text_primary};
                }}
            """)

    def _update_tab_styles(self) -> None:
        for btn in self.tabs.findChildren(QPushButton):
            key = btn.objectName().replace("tab_", "")
            self._apply_tab_style(btn, key == self._current_tab)

    def _update_fab_style(self) -> None:
        if not hasattr(self, 'fab'):
            return
        from pyrolist.ui.design import tokens
        from PySide6.QtGui import QColor
        accent = tokens.CURRENT.accent
        c = QColor(accent)
        bright_hex = c.lighter(125).name()
        dark_hex = c.darker(120).name()
        self.fab.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: {tokens.CURRENT.text_on_accent};
                border: none;
                border-radius: 28px;
                font-family: 'Inter';
                font-size: 26px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {bright_hex};
            }}
            QPushButton:pressed {{
                background-color: {dark_hex};
            }}
        """)

    def _update_library_styles(self) -> None:
        from pyrolist.ui.design import tokens
        if hasattr(self, 'header_label'):
            self.header_label.setStyleSheet(f"color: {tokens.CURRENT.text_primary}; background: transparent;")
        self._update_tab_styles()
        self._update_fab_style()

    def changeEvent(self, event) -> None:
        from PySide6.QtCore import QEvent
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.StyleChange, QEvent.Type.ApplicationPaletteChange):
            if not getattr(self, '_in_style_change', False):
                self._in_style_change = True
                try:
                    self._update_library_styles()
                finally:
                    self._in_style_change = False
        super().changeEvent(event)
