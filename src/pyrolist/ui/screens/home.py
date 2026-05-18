from functools import partial
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QGridLayout, QPushButton, QGraphicsOpacityEffect
from qasync import asyncSlot
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from loguru import logger
from pyrolist.ui.design.fonts import AppFont
from pyrolist.ui.widgets.album_card import AlbumCard
from pyrolist.ui.widgets.playlist_card import PlaylistCard
from pyrolist.ui.widgets.song_card import SongCard
from pyrolist.ui.widgets.artist_card import ArtistCard
from pyrolist.ui.widgets.ripple_button import RippleButton
from pyrolist.ui.widgets.skeleton_loader import SkeletonListLoader


class HomeScreen(QWidget):
    download_requested = Signal(str, str, str, str)
    play_next_requested = Signal(str, str, str, str)
    add_to_queue_requested = Signal(str, str, str, str)
    like_requested = Signal(str, object)
    add_to_playlist_requested = Signal(str, str)
    delete_download_requested = Signal(str)

    def __init__(self, yt_client, on_play_song, on_navigate=None):
        super().__init__()
        self.yt = yt_client
        self.on_play_song = on_play_song
        self.on_navigate = on_navigate
        self._sections = {}
        self._loaded = False
        self._genres = [
            ("Rock", "rock"),
            ("Pop", "pop"),
            ("Reggaeton", "reggaeton"),
            ("Salsa", "salsa"),
            ("Clasica", "classical"),
            ("Electronica", "electronic"),
            ("Jazz", "jazz"),
            ("R&B", "r&b"),
            ("Reggae", "reggae"),
            ("Hip Hop", "hip hop"),
            ("Latina", "latin music"),
            ("Colombia", "colombian music"),
        ]
        self._build_ui()
    
    def _connect_card_signals(self, card):
        """Wire up all context-menu signals from a SongCard."""
        card.download_requested.connect(lambda *a: self.download_requested.emit(*a))
        card.play_next_requested.connect(lambda *a: self.play_next_requested.emit(*a))
        card.add_to_queue_requested.connect(lambda *a: self.add_to_queue_requested.emit(*a))
        card.like_requested.connect(lambda *a: self.like_requested.emit(*a))
        card.add_to_playlist_requested.connect(lambda *a: self.add_to_playlist_requested.emit(*a))
        card.delete_download_requested.connect(lambda *a: self.delete_download_requested.emit(*a))

    def _handle_download(self, vid, title, artist, thumb):
        self.download_requested.emit(vid, title, artist, thumb)
    
    def _handle_play(self, video_id, title, artists, thumbnail_url=""):
        try:
            artist_str = ", ".join([a.get("name", "") for a in artists]) if isinstance(artists, list) else str(artists)
            if self.on_play_song:
                self.on_play_song(video_id, title, artist_str, "", 0, thumbnail_url)
        except Exception as e:
            logger.error(f"Play error: {e}")

    def _on_genre_click(self, query):
        if self.on_navigate:
            self.on_navigate(f"search?query={query}")

    def _create_genre_card(self, name, query):
        card = RippleButton(name, "secondary")
        card.setFixedSize(150, 80)
        from pyrolist.ui.design import tokens
        card.setStyleSheet(f"""
            QPushButton {{
                background: {tokens.CURRENT.bg_elevated};
                color: {tokens.CURRENT.text_primary};
                border: 1px solid {tokens.CURRENT.border};
                border-radius: 12px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {tokens.CURRENT.bg_high};
                border-color: {tokens.CURRENT.accent}55;
            }}
        """)
        card.clicked.connect(lambda: self._on_genre_click(query))
        return card

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)

        header = QLabel("Inicio")
        header.setFont(AppFont.display(24))
        header.setStyleSheet("color: #F1F0FF;")
        layout.addWidget(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setSpacing(24)

        self._create_loading_state()

        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll)

    def _create_loading_state(self):
        self.content_layout.addWidget(SkeletonListLoader(row_count=7))

    def _clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _fade_in_content(self):
        """Smooth fade-in animation when content finishes loading."""
        effect = QGraphicsOpacityEffect(self.content)
        self.content.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(300)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: self.content.setGraphicsEffect(None))
        anim.start()

    async def load(self):
        if self._loaded:
            return
        self._clear_content()
        self._create_loading_state()

        try:
            from pyrolist.db.repository import DownloadRepository
            dl_repo = DownloadRepository()
            downloads = await dl_repo.get_downloads()
            self.downloaded_playlist_ids = {d.parent_playlist_id for d in downloads if d.parent_playlist_id}
        except Exception as e:
            logger.debug(f"Error fetching downloaded playlists for badge checks: {e}")
            self.downloaded_playlist_ids = set()

        from loguru import logger
        logger.info(f"Home load: yt={self.yt}, is_auth={getattr(self.yt, 'is_authenticated', False) if self.yt else 'No yt'}")

        if self.yt:
            # Always try YouTube home — get_home/get_charts now work via public client
            logger.info("Loading YouTube home content...")
            await self._load_youtube_home()
        else:
            logger.info("No yt client — loading genres view")
            self._clear_content()
            self._load_genres_view()
        
        self._loaded = True

    def force_reload(self):
        """Force a full reload of the home content (e.g. after login)."""
        self._loaded = False
        import asyncio
        asyncio.ensure_future(self.load())

    async def _load_youtube_home(self):
        try:
            from loguru import logger
            logger.info("Loading YouTube home recommendations...")
            
            home_data = await self.yt.get_home()
            
            # get_home() returns a list of sections (unauthenticated)
            # or a dict with 'contents' key (authenticated)
            contents = None
            if isinstance(home_data, list) and home_data:
                contents = home_data
            elif isinstance(home_data, dict) and home_data.get('contents'):
                contents = home_data.get('contents', [])

            if contents:
                self._clear_content()
                title = QLabel("Para ti")
                title.setFont(AppFont.display(24))
                title.setStyleSheet("color: #F1F0FF;")
                self.content_layout.addWidget(title)
                
                # Fetch liked video IDs for heart state
                from pyrolist.db.repository import SongRepository
                liked_ids = await SongRepository().get_liked_video_ids()
                
                self._display_home_content(contents, liked_ids)
                self._fade_in_content()
            else:
                # Fallback to charts
                charts_data = await self.yt.get_charts()
                has_charts = False
                if isinstance(charts_data, dict):
                    has_charts = bool(charts_data.get('items') or charts_data.get('tracks'))
                elif isinstance(charts_data, list):
                    has_charts = bool(charts_data)

                if has_charts:
                    self._clear_content()
                    title = QLabel("Top Charts")
                    title.setFont(AppFont.display(24))
                    title.setStyleSheet("color: #F1F0FF;")
                    self.content_layout.addWidget(title)
                    
                    self._display_charts(charts_data)
                    self._fade_in_content()
                else:
                    self._clear_content()
                    self._load_genres_view()
        except Exception as e:
            logger.error(f"Error loading YouTube home: {e}")
            self._clear_content()
            self._load_genres_view()

    def _display_home_content(self, contents, liked_ids=None):
        if liked_ids is None:
            liked_ids = set()
        for section in contents[:6]:
            if not isinstance(section, dict):
                continue

            section_widget = QWidget()
            section_layout = QVBoxLayout(section_widget)
            section_layout.setSpacing(12)
            
            # Title can be string or dict with 'text' key
            section_title = section.get('title', 'Sección')
            if isinstance(section_title, dict):
                section_title = section_title.get('text', 'Sección')
            
            header = QLabel(str(section_title))
            header.setFont(AppFont.heading(16))
            header.setStyleSheet("color: #F1F0FF;")
            section_layout.addWidget(header)
            
            # Items can be in 'contents' or direct in section
            items = section.get('contents', section.get('items', []))
            if not isinstance(items, list):
                items = []

            has_cards = False
            
            # Use QGridLayout for this section
            grid = QGridLayout()
            grid.setSpacing(16)
            
            # Determine if this section is mostly songs (videoId) or playlists/albums (browseId/playlistId)
            has_songs = any('videoId' in item for item in items[:6] if isinstance(item, dict))
            columns = 2 if has_songs else 4
            
            card_index = 0
            for item in items[:8]:  # show up to 8 items per section
                if not isinstance(item, dict):
                    continue

                title = item.get('title', 'Unknown')
                if isinstance(title, dict):
                    title = title.get('text', 'Unknown')

                video_id = item.get('videoId', '')
                playlist_id = item.get('playlistId', '')
                browse_id = item.get('browseId', '')
                
                artists = item.get('artists', [])
                if isinstance(artists, list):
                    artist_names = ", ".join([a.get('name', '') for a in artists if isinstance(a, dict)]) or 'Unknown'
                elif isinstance(artists, str):
                    artist_names = artists
                else:
                    artist_names = 'Unknown'

                duration = item.get('duration', item.get('lengthText', ''))
                thumbnails = item.get('thumbnails', [])
                thumbnail_url = thumbnails[-1].get('url', '') if thumbnails else ''
                    
                card = None
                if video_id:
                    card = SongCard(
                        title=str(title),
                        artist=artist_names,
                        duration=str(duration) if duration else '',
                        thumbnail_url=thumbnail_url,
                        on_play=partial(self._handle_play, video_id, str(title), artist_names, thumbnail_url),
                        video_id=video_id,
                        is_liked=video_id in liked_ids,
                    )
                    self._connect_card_signals(card)
                elif playlist_id:
                    card = PlaylistCard(
                        title=str(title),
                        description=artist_names,
                        thumbnail_url=thumbnail_url,
                        is_downloaded=playlist_id in getattr(self, "downloaded_playlist_ids", set())
                    )
                    if self.on_navigate:
                        card.clicked.connect(partial(self.on_navigate, f"playlist?id={playlist_id}"))
                elif browse_id:
                    # Could be artist or album. Just use AlbumCard as a generic square card.
                    card = AlbumCard(title=str(title), artist=artist_names, thumbnail_url=thumbnail_url)
                    if self.on_navigate:
                        # Sometimes browseId is artist, sometimes album. We route to album, but if it starts with UC it's an artist
                        if str(browse_id).startswith("UC"):
                            card.clicked.connect(partial(self.on_navigate, f"artist?id={browse_id}"))
                        else:
                            card.clicked.connect(partial(self.on_navigate, f"album?id={browse_id}"))

                if card:
                    grid.addWidget(card, card_index // columns, card_index % columns)
                    card_index += 1
                    has_cards = True
            
            if has_cards:
                section_layout.addLayout(grid)
                self.content_layout.addWidget(section_widget)
            else:
                section_widget.deleteLater()
        
        self.content_layout.addStretch()

    def _display_charts(self, charts):
        """Display charts data - handles both list and dict formats."""
        # Handle dict format from get_charts() API
        if isinstance(charts, dict):
            section = QWidget()
            section_layout = QVBoxLayout(section)
            section_layout.setSpacing(12)

            chart_playlists = charts.get("playlists", [])
            if chart_playlists:
                grid = QGridLayout()
                grid.setSpacing(12)
                for i, playlist in enumerate(chart_playlists[:4]):
                    title = playlist.get("title", "Chart")
                    thumbnails = playlist.get("thumbnails", [])
                    thumbnail_url = thumbnails[-1].get("url", "") if thumbnails else ""
                    playlist_id = playlist.get("playlistId", "")
                    
                    playlist_card = PlaylistCard(
                        title=title,
                        thumbnail_url=thumbnail_url,
                        is_downloaded=playlist_id in getattr(self, "downloaded_playlist_ids", set())
                    )
                    if playlist_id and self.on_navigate:
                        playlist_card.clicked.connect(partial(self.on_navigate, f"playlist?id={playlist_id}"))
                    grid.addWidget(playlist_card, 0, i)
                section_layout.addLayout(grid)

            tracks = charts.get("tracks", charts.get("items", []))
            if tracks:
                for track in tracks[:10]:
                    title = track.get("title", "Unknown")
                    artists = track.get("artists", [])
                    artist_names = ", ".join([a.get("name", "") for a in artists]) if isinstance(artists, list) else str(artists)
                    video_id = track.get("videoId", "")
                    duration = track.get("lengthText", "")
                    thumbnails = track.get('thumbnails', [])
                    thumbnail_url = thumbnails[-1].get('url', '') if thumbnails else ''

                    if video_id:
                        card = SongCard(
                            title=title,
                            artist=artist_names,
                            duration=duration,
                            thumbnail_url=thumbnail_url,
                            on_play=partial(self._handle_play, video_id, title, artist_names, thumbnail_url),
                            video_id=video_id
                        )
                        card.download_requested.connect(self._handle_download)
                        section_layout.addWidget(card)

            self.content_layout.addWidget(section)

        # Handle list format (direct items list)
        elif isinstance(charts, list):
            for item in charts[:10]:
                title = item.get('title', 'Unknown')
                video_id = item.get('videoId', '')
                artists = item.get('artists', [])
                artist_names = ", ".join([a.get('name', '') for a in artists]) if artists else 'Unknown'
                duration = item.get('lengthText', '')
                thumbnails = item.get('thumbnails', [])
                thumbnail_url = thumbnails[-1].get('url', '') if thumbnails else ''

                if video_id:
                    card = SongCard(
                        title=title,
                        artist=artist_names,
                        duration=duration,
                        thumbnail_url=thumbnail_url,
                        on_play=partial(self._handle_play, video_id, title, artist_names, thumbnail_url)
                    )
                    self.content_layout.addWidget(card)

        self.content_layout.addStretch()


    def _load_genres_view(self):
        title = QLabel("Explorar por género")
        title.setFont(AppFont.display(24))
        title.setStyleSheet("color: #F1F0FF;")
        self.content_layout.addWidget(title)

        genres_section = QWidget()
        genres_layout = QGridLayout(genres_section)
        genres_layout.setSpacing(16)

        for i, (name, query) in enumerate(self._genres):
            card = self._create_genre_card(name, query)
            genres_layout.addWidget(card, i // 4, i % 4)

        self.content_layout.addWidget(genres_section)

        section = QWidget()
        section_layout = QVBoxLayout(section)
        section_layout.setSpacing(12)

        header = QLabel("Sugerencias")
        header.setFont(AppFont.heading(18))
        header.setStyleSheet("color: #F1F0FF;")
        section_layout.addWidget(header)

        hint = QLabel("Haz clic en un genero para buscar")
        hint.setStyleSheet("color: #888899; font-size: 14px; padding: 10px;")
        section_layout.addWidget(hint)

        self.content_layout.addWidget(section)
        self.content_layout.addStretch()

    def _show_search_prompt(self):
        from pyrolist.ui.design import tokens
        self._clear_content()
        title = QLabel("Bienvenido a Pyrolist")
        title.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {tokens.CURRENT.text_primary}; padding: 20px; background: transparent;")
        self.content_layout.addWidget(title)

        search_hint = QLabel("Ve a Buscar y escribe el nombre de una cancion")
        search_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        search_hint.setStyleSheet(f"color: {tokens.CURRENT.text_secondary}; font-size: 14px; padding: 10px; background: transparent;")
        self.content_layout.addWidget(search_hint)

        self.content_layout.addStretch()

    def _display_explore(self, explore):
        from pyrolist.ui.design import tokens
        section = QWidget()
        section_layout = QVBoxLayout(section)
        section_layout.setSpacing(12)

        header = QLabel("Explorar")
        header.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {tokens.CURRENT.text_primary}; background: transparent;")
        section_layout.addWidget(header)

        mood_cats = explore.get("moodCategories", [])
        if mood_cats:
            grid = QGridLayout()
            grid.setSpacing(12)

            for i, cat in enumerate(mood_cats[:6]):
                title = cat.get("title", "Moods")
                playlist_card = PlaylistCard(title=title)
                grid.addWidget(playlist_card, i // 3, i % 3)

            section_layout.addLayout(grid)

        self.content_layout.addWidget(section)

    def _display_home(self, home):
        from pyrolist.ui.design import tokens
        for item in home:
            section = QWidget()
            section_layout = QVBoxLayout(section)
            section_layout.setSpacing(12)

            title = item.get("title", {}).get("text", "Sección")
            header = QLabel(title)
            header.setFont(QFont("Inter", 16, QFont.Weight.Bold))
            header.setStyleSheet(f"color: {tokens.CURRENT.text_primary}; background: transparent;")
            section_layout.addWidget(header)

            contents = item.get("contents", [])
            if contents:
                grid = QGridLayout()
                grid.setSpacing(12)

                for i, content in enumerate(contents[:6]):
                    content_type = content.get("contentType", "")

                    if "album" in content_type.lower():
                        album = content.get("album", {})
                        title_text = album.get("title", "Album")
                        artist_text = album.get("artist", {}).get("name", "Artist")
                        card = AlbumCard(title=title_text, artist=artist_text)
                        grid.addWidget(card, i // 3, i % 3)

                    elif "playlist" in content_type.lower():
                        playlist = content.get("playlist", {})
                        title_text = playlist.get("title", "Playlist")
                        playlist_id = playlist.get("playlistId", "")
                        card = PlaylistCard(
                            title=title_text,
                            is_downloaded=playlist_id in getattr(self, "downloaded_playlist_ids", set())
                        )
                        if playlist_id and self.on_navigate:
                            card.clicked.connect(partial(self.on_navigate, f"playlist?id={playlist_id}"))
                        grid.addWidget(card, i // 3, i % 3)

                    elif "song" in content_type.lower() or "video" in content_type.lower():
                        video = content.get("video", {}) or content.get("musicVideo", {})
                        title_text = video.get("title", {}).get("text", "Title")
                        artists = video.get("artist", {})
                        if isinstance(artists, list):
                            artists_text = ", ".join([a.get("name", "") for a in artists])
                        else:
                            artists_text = artists.get("name", "Artist") if artists else "Artist"
                        video_id = video.get("videoId", "")

                        if video_id:
                            card = SongCard(
                                title=title_text,
                                artist=artists_text,
                                duration="",
                                on_play=partial(self._handle_play, video_id, title_text, artists_text, "") # Thumbnail might be missing here but fixed others
                            )
                            section_layout.addWidget(card)

                if grid.count() > 0:
                    section_layout.addLayout(grid)

            self.content_layout.addWidget(section)

    def _update_home_styles(self) -> None:
        from pyrolist.ui.design import tokens
        for label in self.findChildren(QLabel):
            font_size = label.font().pointSize()
            if font_size >= 14:
                label.setStyleSheet(f"color: {tokens.CURRENT.text_primary}; background: transparent;")
            else:
                label.setStyleSheet(f"color: {tokens.CURRENT.text_secondary}; background: transparent;")
        
        for btn in self.findChildren(QPushButton):
            if hasattr(self, "_genres") and any(btn.text() == name for name, _ in self._genres):
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {tokens.CURRENT.bg_elevated};
                        color: {tokens.CURRENT.text_primary};
                        border: 1px solid {tokens.CURRENT.border};
                        border-radius: 12px;
                        font-size: 14px;
                        font-weight: 700;
                    }}
                    QPushButton:hover {{
                        background: {tokens.CURRENT.bg_high};
                        border-color: {tokens.CURRENT.accent}55;
                    }}
                """)

    def changeEvent(self, event) -> None:
        from PySide6.QtCore import QEvent
        if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
            if not getattr(self, '_in_style_change', False):
                self._in_style_change = True
                try:
                    self._update_home_styles()
                finally:
                    self._in_style_change = False
        super().changeEvent(event)
