import asyncio
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QFrame
)
from PySide6.QtCore import Qt, QSize, QEasingCurve, QPropertyAnimation
from qasync import asyncSlot
from loguru import logger
from pyrolist.config.settings import AppSettings
from pyrolist.api.youtube_music import YouTubeMusicClient
from pyrolist.api.stream_extractor import StreamExtractor
from pyrolist.api.lyrics import LyricsClient
from pyrolist.api.lastfm import LastFmScrobbler
from pyrolist.api.discord_rpc import DiscordRPC
from pyrolist.audio.player import MusicPlayer, PlayerState
from pyrolist.audio.queue import PlayQueue, QueueItem
from pyrolist.system.mpris import MprisPlayer
from pyrolist.system.tray import SystemTray
from pyrolist.ui.widgets.nav_sidebar import NavSidebar
from pyrolist.ui.widgets.mini_player import MiniPlayerWidget
from pyrolist.ui.widgets.fade_stack import FadeStackedWidget
from pyrolist.ui.widgets.toast import ToastNotification


class MainWindow(QMainWindow):
    ROUTES = {
        "home": 0,
        "library": 1,
        "history": 2,
        "downloads": 3,
        "settings": 4,
        "playlist": 5,
        "album": 6,
        "artist": 7,
        "now_playing": 8,
        "search": 9,
    }

    def __init__(self, settings: AppSettings, event_loop=None):
        super().__init__()
        self.settings = settings
        self._loop = event_loop
        self._pending_tasks: set[asyncio.Task] = set()

        self.yt = YouTubeMusicClient(settings)
        self.extractor = StreamExtractor(settings)
        
        from pyrolist.services.download_manager import DownloadManager
        self.download_manager = DownloadManager.get_instance()
        self.download_manager.start()
        self.download_manager.download_completed.connect(self._on_download_finished)
        self.download_manager.download_error.connect(self._on_download_error)
        
        self.lyrics_client = LyricsClient()
        self.player = MusicPlayer()
        self.queue = PlayQueue()
        self.mpris = MprisPlayer(self.player, self.queue)
        self.scrobbler: LastFmScrobbler | None = None
        self.discord: DiscordRPC | None = None

        self._setup_window()
        self._build_ui()
        self._connect_player_callbacks()
        self._setup_integrations()

        if self._loop:
            self._init_task = self._loop.create_task(self._initialize())
            self._track_task(self._init_task)
        else:
            self._init_task = asyncio.ensure_future(self._initialize())
            self._track_task(self._init_task)

    def _setup_close_handler(self) -> None:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.aboutToQuit.connect(self._cleanup_on_close)

    def _setup_window(self) -> None:
        from pyrolist.ui.design.fonts import load_fonts
        load_fonts()
        self.setWindowTitle("Pyrolist")
        self.setMinimumSize(QSize(960, 640))
        self.resize(1300, 820)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        content_area = QWidget()
        content_area.setObjectName("contentArea")
        h_layout = QHBoxLayout(content_area)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        self.sidebar = NavSidebar(on_navigate=lambda r: self._run_async(self._navigate(r)))
        self.sidebar.on_login_click.connect(self._show_login)
        self.sidebar.auth_changed.connect(self._on_auth_changed)
        
        if self.yt.is_authenticated:
            from pyrolist.config.paths import AppDirs
            import json
            name = "YouTube Music"
            avatar = ""
            profile_file = AppDirs.config / "user_profile.json"
            if profile_file.exists():
                try:
                    with open(profile_file, "r") as f:
                        data = json.load(f)
                        name = data.get("name", "YouTube Music") or "YouTube Music"
                        avatar = data.get("avatar_url", "")
                except Exception:
                    pass
            self.sidebar.update_auth_state(True, name, avatar)
        h_layout.addWidget(self.sidebar)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        from pyrolist.ui.widgets.global_search import GlobalSearchBar
        self.search_bar = GlobalSearchBar(self.yt, self._play_song_sync)
        self.search_bar.search_submitted.connect(self._on_search_submitted)
        right_layout.addWidget(self.search_bar)

        self.stack = FadeStackedWidget()
        self.stack.setObjectName("screenStack")

        from pyrolist.ui.screens.welcome import WelcomeScreen
        from pyrolist.ui.screens.home import HomeScreen
        from pyrolist.ui.screens.library import LibraryScreen
        from pyrolist.ui.screens.history import HistoryScreen
        from pyrolist.ui.screens.downloads import DownloadsScreen
        from pyrolist.ui.screens.settings import SettingsScreen

        from pyrolist.ui.screens.playlist import PlaylistScreen
        from pyrolist.ui.screens.album import AlbumScreen
        from pyrolist.ui.screens.artist import ArtistScreen

        from pyrolist.ui.screens.now_playing import NowPlayingScreen
        from pyrolist.ui.screens.search import SearchScreen

        self.home_screen = HomeScreen(self.yt, self._play_song_sync, self._navigate_to)
        self.library_screen = LibraryScreen(self.yt, self._play_song_sync, self._navigate_to)
        self.history_screen = HistoryScreen(self.yt, self._play_song_sync)
        self.downloads_screen = DownloadsScreen(self.extractor, self._play_local)
        self.settings_screen = SettingsScreen(
            self.yt,
            self.settings,
            on_settings_changed=self._on_settings_changed
        )
        self.playlist_screen = PlaylistScreen(self.yt, self._play_song_sync)
        self.album_screen = AlbumScreen(self.yt, self._play_song_sync)
        self.artist_screen = ArtistScreen(self.yt, self._play_song_sync, self._navigate_to)
        self.now_playing_screen = NowPlayingScreen(self.player, self.queue, self.yt, self._play_queue_item)
        self.search_screen = SearchScreen(self.yt, self._play_song_sync)

        for screen in [
            self.home_screen,
            self.library_screen,
            self.history_screen,
            self.downloads_screen,
            self.settings_screen,
            self.playlist_screen,
            self.album_screen,
            self.artist_screen,
            self.now_playing_screen,
            self.search_screen,
        ]:
            self.stack.addWidget(screen)
            # Connect all context-menu signals if they exist
            if hasattr(screen, 'download_requested'):
                screen.download_requested.connect(self._on_download_requested)
            if hasattr(screen, 'play_next_requested'):
                screen.play_next_requested.connect(self._on_play_next_requested)
            if hasattr(screen, 'add_to_queue_requested'):
                screen.add_to_queue_requested.connect(self._on_add_to_queue_requested)
            if hasattr(screen, 'add_to_playlist_requested'):
                screen.add_to_playlist_requested.connect(self._on_add_to_playlist_requested)
            if hasattr(screen, 'download_playlist_requested'):
                screen.download_playlist_requested.connect(self._on_download_playlist_requested)
            if hasattr(screen, 'like_requested'):
                screen.like_requested.connect(self._on_like_requested)

        if hasattr(self.now_playing_screen, 'queue_tab'):
            self.now_playing_screen.queue_tab.like_requested.connect(self._on_like_requested)

        right_layout.addWidget(self.stack)

        h_layout.addWidget(right_panel)
        
        root_layout.addWidget(content_area)

        self.mini_player = MiniPlayerWidget(
            player=self.player,
            queue=self.queue,
            on_expand=self._show_full_player,
            on_prev=self._on_prev,
            on_play_pause=self._on_play_pause,
            on_next=self._on_next,
            on_seek=self._on_seek,
        )
        root_layout.addWidget(self.mini_player)

        self.statusBar().setObjectName("appStatusBar")
        self.statusBar().setStyleSheet("color: #888899; font-family: Inter; font-size: 11px;")

        self.tray = SystemTray(
            parent=self,
            on_show=self.show,
            on_play_pause=self._on_play_pause,
            on_next=self._on_next,
            on_quit=self.close,
        )

    def _connect_player_callbacks(self) -> None:
        self.player.on("track_ended", self._on_track_ended_callback)
        self.player.on("state_changed", self._on_state_changed_callback)
        self.player.on("position_changed", self._on_position_changed_callback)

    def _on_track_ended_callback(self, status) -> None:
        self._run_async(self._advance_queue())

    def _on_state_changed_callback(self, status) -> None:
        self.mini_player.update_state(status)
        self.now_playing_screen.update_state(status)

    def _on_position_changed_callback(self, status) -> None:
        self.mini_player.update_position(
            status.position_ms, status.duration_ms
        )
        self.now_playing_screen.update_position(
            status.position_ms, status.duration_ms
        )

    def _setup_integrations(self) -> None:
        if self.settings.integrations.mpris_enabled:
            self.mpris.start()
        if self.settings.integrations.lastfm_enabled:
            self.scrobbler = LastFmScrobbler(
                self.settings.integrations.lastfm_api_key,
                self.settings.integrations.lastfm_api_secret,
                self.settings.integrations.lastfm_session_key,
            )
        if self.settings.integrations.discord_rpc_enabled:
            self.discord = DiscordRPC()
            task = self._run_async(self.discord.connect())

    def _track_task(self, task: asyncio.Task) -> None:
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    def _run_async(self, coro) -> asyncio.Task:
        if self._loop:
            task = self._loop.create_task(coro)
        else:
            task = asyncio.ensure_future(coro)
        self._track_task(task)
        return task

    def _play_song_sync(self, video_id: str, title: str, artist: str, album: str, duration_ms: int, thumbnail_url: str) -> None:
        self._run_async(self._play_song(video_id, title, artist, album, duration_ms, thumbnail_url))

    def _on_download_requested(self, video_id, title, artist, thumb_url):
        logger.info(f"Download requested: {title} by {artist}")
        if self.download_manager.add_download(video_id, title, artist, thumb_url):
            self.statusBar().showMessage(f"Descargando: {title}", 3000)
            ToastNotification.show(self, f"Descargando: {title}", "info")
        else:
            self.statusBar().showMessage(f"Ya en cola: {title}", 3000)

    def _on_download_finished(self, video_id, file_path):
        self.statusBar().showMessage(f"Descarga completa!", 5000)
        ToastNotification.show(self, "Descarga completa", "success")

    def _on_download_playlist_requested(self, playlist_id, title, thumbnail_url):
        self._run_async(self._download_playlist_async(playlist_id, title, thumbnail_url))

    async def _download_playlist_async(self, playlist_id, title, thumbnail_url):
        self.statusBar().showMessage(f"Iniciando descarga de playlist: {title}", 3000)
        ToastNotification.show(self, f"Iniciando descarga de playlist", "info")
        
        try:
            data = await self.yt.get_playlist(playlist_id)
            tracks = data.get('tracks', [])
            
            queued = 0
            for track in tracks:
                vid = track.get('videoId')
                if not vid:
                    continue
                t_title = track.get('title', 'Unknown')
                artists = track.get('artists', [])
                artist_names = ", ".join([a.get('name', '') for a in artists]) if isinstance(artists, list) else str(artists)
                track_thumbnails = track.get('thumbnails', [])
                track_thumb = track_thumbnails[-1].get('url', '') if track_thumbnails else ''
                
                if self.download_manager.add_download(vid, t_title, artist_names, track_thumb, playlist_id, title):
                    queued += 1
            
            self.statusBar().showMessage(f"{queued} canciones añadidas a cola", 4000)
        except Exception as e:
            logger.error(f"Error downloading playlist: {e}")
            self.statusBar().showMessage("Error al iniciar descarga de playlist", 4000)

    def _on_download_error(self, video_id, error):
        self.statusBar().showMessage(f"Error en descarga: {error}", 5000)
        ToastNotification.show(self, f"Error en descarga: {error}", "error")

    def _on_play_next_requested(self, video_id, title, artist, thumb_url):
        item = QueueItem(
            video_id=video_id, title=title, artist=artist,
            album="", duration_ms=0, thumbnail_url=thumb_url,
        )
        self.queue.add_next(item)
        self._update_queue_panel()
        self.statusBar().showMessage(f"Siguiente: {title}", 2000)

    def _on_add_to_queue_requested(self, video_id, title, artist, thumb_url):
        item = QueueItem(
            video_id=video_id, title=title, artist=artist,
            album="", duration_ms=0, thumbnail_url=thumb_url,
        )
        self.queue.add_to_end(item)
        self._update_queue_panel()
        self.statusBar().showMessage(f"Añadido a la cola: {title}", 2000)

    def _on_add_to_playlist_requested(self, video_id, title):
        self._run_async(self._show_add_to_playlist_dialog(video_id, title))

    async def _show_add_to_playlist_dialog(self, video_id, title):
        if not self.yt.is_authenticated:
            self.statusBar().showMessage("Inicia sesión para añadir a playlists", 3000)
            return

        playlists = await self.yt.get_library_playlists()
        if not playlists:
            self.statusBar().showMessage("No tienes playlists creadas", 3000)
            return

        from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QScrollArea, QWidget
        from pyrolist.ui.design.fonts import AppFont
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Añadir a Playlist")
        dialog.setFixedWidth(400)
        dialog.setStyleSheet("background-color: #10101E; color: #F1F0FF;")
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        
        header = QLabel(f"Añadir '{title}' a...")
        header.setFont(AppFont.heading(16))
        layout.addWidget(header)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(8)
        
        for pl in playlists:
            pid = pl.get('playlistId')
            p_title = pl.get('title', 'Unknown')
            if not pid:
                continue
                
            btn = QPushButton(p_title)
            btn.setStyleSheet("""
                QPushButton {
                    background: #1E1E38; color: #F1F0FF; border: none; border-radius: 8px; padding: 12px; text-align: left;
                }
                QPushButton:hover { background: #2A2A4A; }
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Using partial or lambda properly capturing loop variable
            def on_click(playlist_id=pid, p_name=p_title):
                dialog.accept()
                self._run_async(self._add_to_yt_playlist(playlist_id, video_id, p_name))
                
            btn.clicked.connect(on_click)
            content_layout.addWidget(btn)
            
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # Determine suitable height
        dialog.setFixedHeight(min(600, 100 + len(playlists) * 50))
        dialog.exec()

    async def _add_to_yt_playlist(self, playlist_id: str, video_id: str, playlist_name: str):
        try:
            res = await self.yt.add_playlist_items(playlist_id, [video_id])
            if res and res.get('status') == 'STATUS_SUCCEEDED':
                self.statusBar().showMessage(f"Añadido a '{playlist_name}'", 3000)
            else:
                self.statusBar().showMessage("Error al añadir a playlist", 3000)
        except Exception as e:
            logger.error(f"Failed to add to playlist: {e}")
            self.statusBar().showMessage("Error al añadir a playlist", 3000)

    def _on_like_requested(self, video_id, btn_like):
        self._run_async(self._toggle_like_async(video_id, btn_like))

    async def _toggle_like_async(self, video_id, btn_like):
        from pyrolist.db.repository import SongRepository
        repo = SongRepository()
        
        # Ensure song exists in DB before liking
        song = await repo.get_song(video_id)
        if not song:
            # If not in DB, create a minimal entry to save the like
            await repo.upsert_song(video_id=video_id, title="Unknown", artist="Unknown")
            
        liked = await repo.toggle_like(video_id)
        
        from pyrolist.ui.design.icons import Icon
        btn_like.setText(Icon.get("favorite"))
        if liked:
            btn_like.setStyleSheet("QPushButton { color: #F472B6; background: transparent; border: none; }")
            btn_like.setFont(Icon.font(20, filled=True))
            btn_like.set_active(True)
            self.statusBar().showMessage("Añadido a Favoritas", 2000)
        else:
            btn_like.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #9B9BC0;
                    border: none;
                    border-radius: 18px;
                }
                QPushButton:hover {
                    background-color: rgba(244,114,182,0.15);
                    color: #F472B6;
                }
            """)
            btn_like.setFont(Icon.font(20, filled=False))
            btn_like.set_active(False)
            self.statusBar().showMessage("Eliminado de Favoritas", 2000)
        
        self._update_queue_panel()

    def _cleanup_on_close(self) -> None:
        for task in list(self._pending_tasks):
            if not task.done():
                task.cancel()
        if self._init_task and not self._init_task.done():
            self._init_task.cancel()
        if self.mpris:
            self.mpris.stop()

    async def _initialize(self) -> None:
        await self._navigate("home")

    async def _navigate(self, route: str) -> None:
        if route != "search":
            self.search_bar.input.blockSignals(True)
            self.search_bar.input.clear()
            self.search_bar.input.blockSignals(False)
            
        index = self.ROUTES.get(route, 0)
        self._set_stack_index(index)
        
        # Wait for the FadeStackedWidget animation (260ms) to complete before blocking thread with UI updates
        import asyncio
        await asyncio.sleep(0.3)
        await self._load_screen(route)

    def _navigate_to(self, path: str) -> None:
        if "?" in path:
            route, query = path.split("?", 1)
            if route == "search" and "query=" in query:
                query_param = query.split("=", 1)[1]
                self.search_bar.input.setText(query_param)
                self._on_search_submitted(query_param)
            elif route == "playlist" and "id=" in query:
                playlist_id = query.split("=", 1)[1]
                index = self.ROUTES.get(route, 0)
                self._set_stack_index(index)
                self._run_async(self.playlist_screen.load(playlist_id))
            elif route == "album" and "id=" in query:
                album_id = query.split("=", 1)[1]
                index = self.ROUTES.get(route, 0)
                self._set_stack_index(index)
                self._run_async(self.album_screen.load(album_id))
            elif route == "artist" and "id=" in query:
                artist_id = query.split("=", 1)[1]
                index = self.ROUTES.get(route, 0)
                self._set_stack_index(index)
                self._run_async(self.artist_screen.load(artist_id))
        else:
            self._run_async(self._navigate(path))

    def _show_login(self) -> None:
        if not self.yt or not self.yt.is_authenticated:
            from pyrolist.ui.dialogs.login_dialog import WebLoginDialog
            dialog = WebLoginDialog(self)
            dialog.login_successful.connect(self._on_web_login_success)
            dialog.exec()
        else:
            self._run_async(self._navigate("settings"))

    def _on_web_login_success(self, avatar_url: str) -> None:
        self.yt = YouTubeMusicClient(self.settings)
        self._update_screens_yt_client()
        if self.yt.is_authenticated:
            from pyrolist.config.paths import AppDirs
            import json
            name = "YouTube Music"
            profile_file = AppDirs.config / "user_profile.json"
            if profile_file.exists():
                try:
                    with open(profile_file, "r") as f:
                        data = json.load(f)
                        name = data.get("name", "YouTube Music") or "YouTube Music"
                except Exception:
                    pass
            self.sidebar.update_auth_state(True, name, avatar_url)
            logger.info(f"Post-login: yt client propagated, name={name}, avatar={avatar_url}")
        self._run_async(self._navigate("home"))

    def _on_auth_changed(self, is_authenticated: bool) -> None:
        if is_authenticated:
            self.yt = YouTubeMusicClient(self.settings)
            self._update_screens_yt_client()
            # The sidebar should already have the avatar if it triggered the login
            logger.info("Auth changed: yt client propagated to all screens")
            
            # Auto-refresh home and library if we just logged in
            self.home_screen.force_reload()
            self._run_async(self.library_screen.load())
        else:
            self.yt = YouTubeMusicClient(self.settings)
            self._update_screens_yt_client()
            self.sidebar.update_auth_state(False, "", "")
            logger.info("Auth changed (logout): yt client reset and sidebar updated")
            
            # Auto-refresh home and library for unauthenticated session
            self.home_screen.force_reload()
            self._run_async(self.library_screen.load())

    def _update_screens_yt_client(self) -> None:
        """Propagate the current yt client reference to all screens that use it."""
        self.search_bar.yt = self.yt
        for screen in [self.home_screen, self.library_screen, self.playlist_screen, 
                       self.album_screen, self.artist_screen, self.search_screen,
                       self.history_screen, self.settings_screen]:
            screen.yt = self.yt

    def _on_search_submitted(self, query: str) -> None:
        """Called when user presses Enter or picks a suggestion."""
        if query:
            # Navigate to search screen (won't clear the bar because route IS 'search')
            index = self.ROUTES.get("search", 0)
            self._set_stack_index(index)
            self.search_screen.search(query)

    def _set_stack_index(self, index: int) -> None:
        if hasattr(self.stack, "setCurrentIndexAnimated"):
            self.stack.setCurrentIndexAnimated(index)
        else:
            self.stack.setCurrentIndex(index)

    async def _load_screen(self, route: str) -> None:
        screens = {
            "home": self.home_screen,
            "library": self.library_screen,
            "history": self.history_screen,
            "search": self.search_screen,
        }
        screen = screens.get(route)
        if screen and hasattr(screen, "load"):
            await screen.load()

    async def _play_song(
        self,
        video_id: str,
        title: str,
        artist: str,
        album: str,
        duration_ms: int,
        thumbnail_url: str,
        queue_items: list[QueueItem] | None = None,
        queue_index: int = 0,
    ) -> None:
        logger.info(f"_play_song called: {title[:30]} video_id={video_id}")
        if queue_items:
            self.queue.set_queue(queue_items, queue_index)
        else:
            item = QueueItem(
                video_id=video_id, title=title, artist=artist,
                album=album, duration_ms=duration_ms,
                thumbnail_url=thumbnail_url,
            )
            self.queue.set_queue([item], 0)

        self._update_queue_panel()
        await self._play_current()

    async def _play_current(self) -> None:
        item = self.queue.current
        if not item:
            return

        self.mini_player.update_track_info(
            item.title, item.artist, item.thumbnail_url
        )
        self.now_playing_screen.update_track_info(
            item.title, item.artist, item.thumbnail_url
        )

        try:
            logger.info(f"Getting fresh stream for: {item.title}")
            stream_info = await self.extractor.get_stream_info(item.video_id)
            
            # Check if user clicked another song while we were extracting
            if self.queue.current is not item:
                logger.info("Song changed during extraction. Aborting play.")
                return
                
            item.stream_url = stream_info.get("url", "")
            
            if not item.thumbnail_url and stream_info.get("thumbnail"):
                item.thumbnail_url = stream_info.get("thumbnail")
                self.mini_player.update_track_info(item.title, item.artist, item.thumbnail_url)
                self.now_playing_screen.update_track_info(item.title, item.artist, item.thumbnail_url)
                
            import time
            item.stream_expires_at = time.time() + 21600

            if item.stream_url:
                logger.info(f"Playing: {item.title} - URL length: {len(item.stream_url)}, format: {stream_info.get('format', 'unknown')}")
                success = await self.player.play_url(item.stream_url, item.video_id)
                if success:
                    self._run_async(self._save_play_history(item))
                else:
                    logger.error(f"Player failed for {item.title}, trying alternative format...")
                    alt_url = await self.extractor.get_alternative_stream(item.video_id)
                    if alt_url:
                        logger.info(f"Retrying with alternative format")
                        await self.player.play_url(alt_url, item.video_id)
            else:
                logger.error(f"No stream URL for {item.title}")

            self._run_async(self._load_lyrics(item))
            self._run_async(self._load_related(item))

            if getattr(getattr(self.settings, 'network', None), 'preload_next', True):
                self._run_async(self._preload_next())

            if self.scrobbler:
                await self.scrobbler.update_now_playing(
                    item.artist, item.title, item.album
                )
            if self.discord:
                await self.discord.update(
                    item.title, item.artist, item.album, True
                )
            if self.mpris:
                self.mpris.update_metadata(
                    item.title, item.artist, item.album,
                    item.duration_ms * 1000, item.thumbnail_url
                )

        except Exception as e:
            logger.error(f"Failed to play {item.video_id}: {e}")

    async def _load_lyrics(self, item: QueueItem) -> None:
        try:
            lyrics = await self.lyrics_client.get_lyrics(
                item.title, item.artist, item.album
            )
            self.now_playing_screen.set_lyrics(lyrics)
        except Exception as e:
            logger.error(f"Error loading lyrics: {e}")
            self.now_playing_screen.set_lyrics(None)

    async def _load_related(self, item: QueueItem) -> None:
        """Load related/similar tracks for the SIMILARES tab."""
        try:
            if self.yt and self.yt.is_authenticated:
                watch_data = await self.yt.get_watch_playlist(video_id=item.video_id, limit=15)
                tracks = watch_data.get('tracks', [])
                # Skip the first track (it's the current song)
                related = [t for t in tracks if t.get('videoId') != item.video_id]
                self.now_playing_screen.set_related(related, self._play_song_sync)
            else:
                self.now_playing_screen.set_related([], None)
        except Exception as e:
            logger.error(f"Error loading related: {e}")
            self.now_playing_screen.set_related([], None)

    async def _save_play_history(self, item: QueueItem) -> None:
        try:
            from pyrolist.db.repository import HistoryRepository, SongRepository
            history_repo = HistoryRepository()
            song_repo = SongRepository()
            
            await history_repo.add_entry(
                video_id=item.video_id,
                title=item.title,
                artist=item.artist,
                duration_ms=item.duration_ms
            )
            
            await song_repo.upsert_song(
                video_id=item.video_id,
                title=item.title,
                artist=item.artist,
                album=item.album,
                duration_ms=item.duration_ms,
                thumbnail_url=item.thumbnail_url,
            )
            
            await song_repo.record_play(item.video_id)
            logger.debug(f"Saved play history for: {item.title}")
        except Exception as e:
            logger.debug(f"Failed to save play history: {e}")

    async def _preload_next(self) -> None:
        next_item = self.queue.next_item
        if next_item and not next_item.stream_url:
            try:
                info = await self.extractor.get_stream_info(next_item.video_id)
                next_item.stream_url = info["url"]
            except Exception:
                pass

    async def _advance_queue(self) -> None:
        item = self.queue.advance()
        if item:
            if item.stream_url:
                import time
                if time.time() < item.stream_expires_at:
                    self._update_queue_panel()
                    await self.player.play_url(item.stream_url, item.video_id)
                    return
            self._update_queue_panel()
            await self._play_current()
        else:
            current = self.queue.current
            if current:
                try:
                    watch = await self.yt.get_watch_playlist(current.video_id)
                    new_items = [
                        QueueItem(
                            video_id=t["videoId"],
                            title=t.get("title", ""),
                            artist=t.get("artists", [{}])[0].get("name", ""),
                            album="",
                            duration_ms=0,
                            thumbnail_url=(t.get("thumbnail") or [{}])[0].get("url",""),
                        )
                        for t in watch.get("tracks", [])[1:]
                    ]
                    if new_items:
                        for ni in new_items:
                            self.queue.add_to_end(ni)
                        self.queue.advance()
                        self._update_queue_panel()
                        await self._play_current()
                except Exception as e:
                    logger.warning(f"Autoplay failed: {e}")

    def _play_local(self, path: str, metadata: dict) -> None:
        title = metadata.get("title", "Unknown")
        artist = metadata.get("artist", "Unknown")
        thumbnail_url = metadata.get("thumbnail_url", "")
        
        # Update player UI track info
        self.mini_player.update_track_info(title, artist, thumbnail_url)
        self.now_playing_screen.update_track_info(title, artist, thumbnail_url)
        
        # Set queue to a single local item so queue controls and state work properly
        item = QueueItem(
            video_id="local",
            title=title,
            artist=artist,
            album="Local",
            duration_ms=0,
            thumbnail_url=thumbnail_url
        )
        self.queue.set_queue([item], 0)
        self._update_queue_panel()
        
        self._run_async(self.player.play_url(path, "local"))

    def _on_play_pause(self) -> None:
        self._run_async(self._toggle_play_pause())

    async def _toggle_play_pause(self) -> None:
        if self.player.status.state == PlayerState.PLAYING:
            await self.player.pause()
        else:
            await self.player.resume()

    def _on_next(self) -> None:
        self._run_async(self._advance_queue())

    def _on_prev(self) -> None:
        self._run_async(self._go_prev())

    async def _go_prev(self) -> None:
        if self.player.status.position_ms > 3000:
            await self.player.seek(0)
        else:
            item = self.queue.go_back()
            if item:
                await self._play_current()

    def _on_seek(self, position_ms: int) -> None:
        self._run_async(self.player.seek(position_ms))

    def _update_queue_panel(self) -> None:
        """Update the queue tab in the NowPlayingScreen."""
        self._run_async(self._update_queue_panel_async())

    async def _update_queue_panel_async(self) -> None:
        if hasattr(self, 'now_playing_screen') and hasattr(self.now_playing_screen, 'queue_tab'):
            from pyrolist.db.repository import SongRepository
            repo = SongRepository()
            liked_ids = await repo.get_liked_video_ids()
            self.now_playing_screen.queue_tab.set_queue(self.queue.items, liked_ids)

    def _play_queue_item(self, index: int) -> None:
        if 0 <= index < len(self.queue.items):
            self.queue.current_index = index - 1
            self._run_async(self._advance_queue())

    def _show_full_player(self) -> None:
        self._navigate_to("now_playing")

    def _on_settings_changed(self, settings: AppSettings) -> None:
        self.settings = settings
        from pyrolist.config.paths import AppDirs
        settings.save(AppDirs.settings_file)
        if settings.equalizer.enabled:
            self.player.apply_equalizer(
                settings.equalizer.preamp,
                settings.equalizer.bands,
            )
        
        # Apply appearance changes in real-time
        if hasattr(settings, 'appearance'):
            # Compact sidebar toggle
            if hasattr(self, 'sidebar'):
                if settings.appearance.compact_sidebar and not self.sidebar._collapsed:
                    self.sidebar.toggle_collapse()
                elif not settings.appearance.compact_sidebar and self.sidebar._collapsed:
                    self.sidebar.toggle_collapse()
            
            # Accent color change — regenerate stylesheet dynamically
            accent = getattr(settings.appearance, 'accent_color', '#A78BFA')
            if accent:
                self._apply_accent_color(accent)

    def _apply_accent_color(self, accent: str) -> None:
        """Regenerate QSS with new accent color and apply with fade."""
        # Guard against redundant applications
        if hasattr(self, '_last_accent') and self._last_accent == accent:
            return
        self._last_accent = accent
        
        from pyrolist.ui.stylesheet import PYROLIST_QSS
        
        new_qss = PYROLIST_QSS
        
        # Calculate variants and RGB components
        try:
            from PySide6.QtGui import QColor
            c = QColor(accent)
            if c.isValid():
                # Primary color hex replacement
                new_qss = new_qss.replace('#A78BFA', accent)
                new_qss = new_qss.replace('#a78bfa', accent.lower())
                
                # Brighter hover variant
                bright = c.lighter(125)
                bright_hex = bright.name()
                new_qss = new_qss.replace('#BBA4FC', bright_hex)
                new_qss = new_qss.replace('#bba4fc', bright_hex.lower())
                
                # Darker pressed variant
                dark = c.darker(120)
                dark_hex = dark.name()
                new_qss = new_qss.replace('#8B5CF6', dark_hex)
                new_qss = new_qss.replace('#8b5cf6', dark_hex.lower())
                
                # RGB component replacement for rgba scrollbars/borders
                r, g, b, _ = c.getRgb()
                new_qss = new_qss.replace('167,139,250', f"{r},{g},{b}")
                new_qss = new_qss.replace('167, 139, 250', f"{r}, {g}, {b}")
                
                # Also replace the darker rgb if it is used in scrollbar or anywhere
                dark_r, dark_g, dark_b, _ = dark.getRgb()
                new_qss = new_qss.replace('139,92,246', f"{dark_r},{dark_g},{dark_b}")
                new_qss = new_qss.replace('139, 92, 246', f"{dark_r}, {dark_g}, {dark_b}")
        except Exception as e:
            logger.error(f"Error calculating accent color variants: {e}")
        
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.setStyleSheet(new_qss)
            logger.info(f"Accent color applied successfully: {accent}")

    def closeEvent(self, event) -> None:
        if self.settings.player.stop_on_close:
            self._run_async(self.player.stop())
        self.player.release()
        if self.discord:
            self._run_async(self.discord.disconnect())
        self.tray.hide()
        event.accept()
