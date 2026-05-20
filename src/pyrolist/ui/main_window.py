import asyncio
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QFrame
)
from PySide6.QtCore import Qt, QSize, QEasingCurve, QPropertyAnimation, Property
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
from pyrolist.audio.sleep_timer import SleepTimer
from pyrolist.audio.crossfade import CrossfadeManager


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
        "stats": 10,
    }

    def __init__(self, settings: AppSettings, event_loop=None):
        super().__init__()
        self.settings = settings
        self._loop = event_loop
        self._pending_tasks: set[asyncio.Task] = set()
        self._current_play_id = 0

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
        self.sleep_timer = SleepTimer()
        self.crossfade_manager = CrossfadeManager(
            enabled=settings.player.crossfade_enabled,
            duration_sec=settings.player.crossfade_duration_sec
        )

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
            
            # Try fresh account info from API
            try:
                if hasattr(self.yt, '_ytmusicapi') and self.yt._ytmusicapi:
                    account_info = self.yt._ytmusicapi.get_account_info()
                    name = account_info.get("accountName", "") or name
                    avatar = account_info.get("accountPhotoUrl", "")
                    # Update saved profile
                    profile_file = AppDirs.config / "user_profile.json"
                    with open(profile_file, "w") as f:
                        json.dump({"name": name, "avatar_url": avatar}, f, indent=4)
            except Exception:
                pass
            
            # Fallback: read from saved profile
            if name == "YouTube Music":
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
        from pyrolist.ui.screens.stats import StatsScreen

        self.home_screen = HomeScreen(self.yt, self._play_song_sync, self._navigate_to)
        self.library_screen = LibraryScreen(self.yt, self._play_song_sync, self._navigate_to)
        self.history_screen = HistoryScreen(self.yt, self._play_song_sync)
        self.downloads_screen = DownloadsScreen(self.extractor, self._play_local, self._play_local_playlist, self._navigate_to)
        self.settings_screen = SettingsScreen(
            self.yt,
            self.settings,
            on_settings_changed=self._on_settings_changed,
            on_auth_changed=self._on_auth_changed
        )
        self.playlist_screen = PlaylistScreen(self.yt, self._play_song_sync, self._play_local_playlist)
        self.album_screen = AlbumScreen(self.yt, self._play_song_sync)
        self.artist_screen = ArtistScreen(self.yt, self._play_song_sync, self._navigate_to)
        self.now_playing_screen = NowPlayingScreen(self.player, self.queue, self.yt, self._play_queue_item, self.settings)
        self.search_screen = SearchScreen(self.yt, self._play_song_sync)
        self.stats_screen = StatsScreen(self.yt, self._play_song_sync)

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
            self.stats_screen,
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
            if hasattr(screen, 'delete_download_requested'):
                screen.delete_download_requested.connect(self._on_delete_download_requested)
            if hasattr(screen, 'delete_playlist_requested'):
                screen.delete_playlist_requested.connect(self._on_delete_playlist_requested)

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
        self._run_async(self._on_download_requested_async(video_id, title, artist, thumb_url))

    async def _on_download_requested_async(self, video_id, title, artist, thumb_url):
        existing = await self.download_manager._repo.get_download(video_id)
        if existing:
            self.statusBar().showMessage(f"Ya descargada: {title}", 3000)
            self.show_notification(f"Ya descargada: {title}", "success")
            return
        
        if self.download_manager.add_download(video_id, title, artist, thumb_url):
            self.statusBar().showMessage(f"Descargando: {title}", 3000)
            self.show_notification(f"Descargando: {title}", "info")
        else:
            self.statusBar().showMessage(f"Ya en cola: {title}", 3000)

    def _on_download_finished(self, video_id, file_path):
        self.statusBar().showMessage(f"Descarga completa!", 5000)

    def _on_download_playlist_requested(self, playlist_id, title, thumbnail_url):
        self._run_async(self._download_playlist_async(playlist_id, title, thumbnail_url))

    async def _download_playlist_async(self, playlist_id, title, thumbnail_url):
        self.statusBar().showMessage(f"Iniciando descarga de playlist: {title}", 3000)
        self.show_notification(f"Iniciando descarga de playlist: {title}", "info")
        
        try:
            data = await self.yt.get_playlist(playlist_id)
            playlist_thumbnails = data.get('thumbnails', [])
            if playlist_thumbnails:
                high_res_thumb = playlist_thumbnails[-1].get('url', '')
                if high_res_thumb:
                    thumbnail_url = high_res_thumb
            tracks = data.get('tracks', [])
            
            queued = 0
            already_downloaded = 0
            for track in tracks:
                vid = track.get('videoId')
                if not vid:
                    continue
                
                # Check if already downloaded
                existing = await self.download_manager._repo.get_download(vid)
                if existing:
                    already_downloaded += 1
                    continue
                
                t_title = track.get('title', 'Unknown')
                artists = track.get('artists', [])
                artist_names = ", ".join([a.get('name', '') for a in artists]) if isinstance(artists, list) else str(artists)
                track_thumbnails = track.get('thumbnails', [])
                track_thumb = track_thumbnails[-1].get('url', '') if track_thumbnails else ''
                
                if self.download_manager.add_download(vid, t_title, artist_names, track_thumb, playlist_id, title, thumbnail_url):
                    queued += 1
            
            if already_downloaded > 0:
                self.statusBar().showMessage(f"{queued} añadidas a cola • {already_downloaded} ya descargadas", 5000)
                self.show_notification(f"{queued} añadidas, {already_downloaded} omitidas (ya descargadas).", "success")
            else:
                self.statusBar().showMessage(f"{queued} canciones añadidas a cola", 4000)
                self.show_notification(f"{queued} canciones añadidas a la cola", "success")
        except Exception as e:
            logger.error(f"Error downloading playlist: {e}")
            self.statusBar().showMessage("Error al iniciar descarga de playlist", 4000)

    def _on_download_error(self, video_id, error):
        self.statusBar().showMessage(f"Error en descarga: {error}", 5000)

    def _on_delete_download_requested(self, video_id: str):
        self._run_async(self._delete_download_async(video_id))

    async def _delete_download_async(self, video_id: str):
        from pathlib import Path
        from pyrolist.db.repository import DownloadRepository
        repo = DownloadRepository()
        d = await repo.get_download(video_id)
        if d:
            title = d.title
            if d.file_path:
                try:
                    p = Path(d.file_path)
                    if p.exists():
                        p.unlink()
                        lrc_path = p.with_suffix(".lrc")
                        if lrc_path.exists():
                            lrc_path.unlink()
                except Exception as e:
                    logger.error(f"Error deleting file {d.file_path}: {e}")
            await repo.remove_download(video_id)
            self.statusBar().showMessage(f"Descarga eliminada: {title}", 3000)
            self.show_notification(f"Descarga eliminada: {title}", "info")
            
            # Reload current screen
            current_screen = self.stack.currentWidget()
            if current_screen == self.downloads_screen:
                await self.downloads_screen.load()
            elif current_screen == self.playlist_screen:
                await self.playlist_screen.load(self.playlist_screen._playlist_id)
            elif current_screen == self.library_screen:
                await self.library_screen.load()

    def _on_delete_playlist_requested(self, playlist_id: str):
        self._run_async(self._delete_playlist_async(playlist_id))

    async def _delete_playlist_async(self, playlist_id: str):
        from pathlib import Path
        from pyrolist.db.repository import DownloadRepository
        repo = DownloadRepository()
        downloads = await repo.get_downloads()
        
        count = 0
        playlist_title = ""
        for d in downloads:
            if d.parent_playlist_id == playlist_id:
                playlist_title = d.parent_playlist_title or playlist_title
                if d.file_path:
                    try:
                        p = Path(d.file_path)
                        if p.exists():
                            p.unlink()
                            lrc_path = p.with_suffix(".lrc")
                            if lrc_path.exists():
                                lrc_path.unlink()
                    except Exception as e:
                        logger.error(f"Error deleting file {d.file_path}: {e}")
                await repo.remove_download(d.video_id)
                count += 1
                
        self.statusBar().showMessage(f"Playlist eliminada: {playlist_title or playlist_id} ({count} canciones)", 4000)
        self.show_notification(f"Playlist local eliminada: {playlist_title or playlist_id}", "info")
        await self._navigate("downloads")

    def show_notification(self, message: str, kind: str = "info"):
        if hasattr(self, "search_bar") and hasattr(self.search_bar, "notif_dropdown"):
            self.search_bar.notif_dropdown.add_custom_notification(message, kind)
        else:
            ToastNotification.show(self, message, kind)

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
        from pyrolist.db.repository import SongRepository, DownloadRepository
        repo = SongRepository()
        
        # Ensure song exists in DB before liking
        song = await repo.get_song(video_id)
        if not song:
            dl_repo = DownloadRepository()
            dl = await dl_repo.get_download(video_id)
            if dl:
                await repo.upsert_song(
                    video_id=video_id,
                    title=dl.title or "Unknown",
                    artist=dl.artist or "Unknown",
                    thumbnail_url=dl.thumbnail_url or ""
                )
            else:
                await repo.upsert_song(video_id=video_id, title="Unknown", artist="Unknown")
            
        liked = await repo.toggle_like(video_id)
        
        from pyrolist.ui.design import tokens
        from pyrolist.ui.design.icons import Icon
        btn_like.setText(Icon.get("favorite"))
        if liked:
            btn_like.setStyleSheet("QPushButton { color: #F472B6; background: transparent; border: none; }")
            btn_like.setFont(Icon.font(20, filled=True))
            btn_like.set_active(True)
            self.statusBar().showMessage("Añadido a Favoritas", 2000)
        else:
            btn_like.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {tokens.CURRENT.text_secondary};
                    border: none;
                    border-radius: 18px;
                }}
                QPushButton:hover {{
                    background-color: rgba(244,114,182,0.15);
                    color: #F472B6;
                }}
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
        self._on_auth_changed(True, avatar_url)
        self._run_async(self._navigate("home"))

    def _on_auth_changed(self, is_authenticated: bool, avatar_url: str = "") -> None:
        if is_authenticated:
            self.yt = YouTubeMusicClient(self.settings)
            self._update_screens_yt_client()
            
            from pyrolist.config.paths import AppDirs
            import json
            name = "YouTube Music"
            
            # Try to get account info from ytmusicapi
            try:
                if self.yt.is_authenticated and hasattr(self.yt, '_ytmusicapi') and self.yt._ytmusicapi:
                    account_info = self.yt._ytmusicapi.get_account_info()
                    name = account_info.get("accountName", "") or name
                    if not avatar_url:
                        avatar_url = account_info.get("accountPhotoUrl", "")
                    # Save updated profile
                    profile_file = AppDirs.config / "user_profile.json"
                    with open(profile_file, "w") as f:
                        json.dump({"name": name, "avatar_url": avatar_url}, f, indent=4)
            except Exception as e:
                logger.debug(f"Could not fetch account info: {e}")
            
            # Fallback: read from saved profile
            if name == "YouTube Music":
                profile_file = AppDirs.config / "user_profile.json"
                if profile_file.exists():
                    try:
                        with open(profile_file, "r") as f:
                            data = json.load(f)
                            name = data.get("name", "YouTube Music") or "YouTube Music"
                            if not avatar_url:
                                avatar_url = data.get("avatar_url", "")
                    except Exception:
                        pass
            
            self.sidebar.update_auth_state(True, name, avatar_url)
            logger.info(f"Post-login: yt client propagated, name={name}, avatar={avatar_url}")
            
            # Auto-refresh home and library if we just logged in
            self.home_screen.force_reload()
            self._run_async(self.library_screen.load())
        else:
            # Delete user profile file on logout so it's clean
            from pyrolist.config.paths import AppDirs
            profile_file = AppDirs.config / "user_profile.json"
            if profile_file.exists():
                try:
                    profile_file.unlink()
                except Exception:
                    pass
            
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
                       self.history_screen, self.settings_screen, self.stats_screen]:
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
            "stats": self.stats_screen,
            "search": self.search_screen,
            "downloads": self.downloads_screen,
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

        # Check if downloaded and play local instead of streaming
        try:
            from pyrolist.db.repository import DownloadRepository
            dl_repo = DownloadRepository()
            download = await dl_repo.get_download(item.video_id)
            if download and download.file_path:
                import os
                if os.path.exists(download.file_path):
                    item.is_local = True
                    item.local_path = download.file_path
        except Exception as e:
            logger.debug(f"Error checking download status in _play_current: {e}")

        self.mini_player.update_track_info(
            item.title, item.artist, item.thumbnail_url
        )
        self.now_playing_screen.update_track_info(
            item.title, item.artist, item.thumbnail_url
        )

        self._current_play_id += 1
        play_id = self._current_play_id

        # Immediate visual feedback for lyrics and related suggestions
        self.now_playing_screen.set_lyrics_loading()
        self.now_playing_screen.set_related([], None)
        self._run_async(self._load_lyrics(item, play_id))
        self._run_async(self._load_related(item, play_id))

        if item.is_local:
            logger.info(f"Playing local track: {item.title}")
            if self.settings.player.crossfade_enabled and self.player.status.state == PlayerState.PLAYING:
                await self.crossfade_manager.fade_out(self.player, duration_sec=1.2)
            
            success = await self.player.play_url(item.local_path, item.video_id)
            if success:
                self._run_async(self._save_play_history(item))
                if self.settings.player.crossfade_enabled:
                    self._run_async(self.crossfade_manager.fade_in(self.player, self.settings.player.volume, duration_sec=1.2))
            return

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
                if self.settings.player.crossfade_enabled and self.player.status.state == PlayerState.PLAYING:
                    await self.crossfade_manager.fade_out(self.player, duration_sec=1.2)

                success = await self.player.play_url(item.stream_url, item.video_id)
                if success:
                    self._run_async(self._save_play_history(item))
                    if self.settings.player.crossfade_enabled:
                        self._run_async(self.crossfade_manager.fade_in(self.player, self.settings.player.volume, duration_sec=1.2))
                else:
                    logger.error(f"Player failed for {item.title}, trying alternative format...")
                    alt_url = await self.extractor.get_alternative_stream(item.video_id)
                    if alt_url:
                        logger.info(f"Retrying with alternative format")
                        success = await self.player.play_url(alt_url, item.video_id)
                        if success and self.settings.player.crossfade_enabled:
                            self._run_async(self.crossfade_manager.fade_in(self.player, self.settings.player.volume, duration_sec=1.2))
            else:
                logger.error(f"No stream URL for {item.title}")

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

    async def _load_lyrics(self, item: QueueItem, play_id: int) -> None:
        self.now_playing_screen.set_lyrics_loading()
        try:
            lyrics = None
            if item.is_local and item.local_path:
                import os
                lrc_path = os.path.splitext(item.local_path)[0] + ".lrc"
                if os.path.exists(lrc_path):
                    try:
                        with open(lrc_path, "r", encoding="utf-8") as f:
                            lyrics = f.read()
                        logger.info(f"Loaded offline lyrics from: {lrc_path}")
                    except Exception as e:
                        logger.error(f"Error reading offline lyrics file: {e}")
            
            if not lyrics:
                lyrics = await self.lyrics_client.get_lyrics(
                    item.title, item.artist, item.album
                )
            
            if self._current_play_id == play_id:
                self.now_playing_screen.set_lyrics(lyrics)
            else:
                logger.info(f"Discarded stale lyrics for {item.title} (current song changed)")
        except Exception as e:
            logger.error(f"Error loading lyrics: {e}")
            if self._current_play_id == play_id:
                self.now_playing_screen.set_lyrics(None)

    async def _load_related(self, item: QueueItem, play_id: int) -> None:
        """Load related/similar tracks for the SIMILARES tab."""
        try:
            video_id = item.video_id
            
            # If it's a local/imported track or we don't have a valid ID, search for it
            if not video_id or video_id == "local" or len(video_id) < 5:
                if self.yt and item.title and item.artist:
                    logger.info(f"Local track: searching YTM for similar tracks using query: {item.title} - {item.artist}")
                    search_results = await self.yt.search(f"{item.title} {item.artist}", filter="songs", limit=1)
                    if search_results:
                        video_id = search_results[0].get("videoId")
            
            related = []
            if self.yt and video_id and video_id != "local" and len(video_id) >= 5:
                try:
                    watch_data = await self.yt.get_watch_playlist(video_id=video_id, limit=15)
                    tracks = watch_data.get('tracks', [])
                    # Skip the current song
                    related = [t for t in tracks if t.get('videoId') != video_id]
                except Exception as e:
                    logger.warning(f"Failed to load related tracks with direct video_id: {e}")
                    # Try search fallback as last resort
                    if item.title and item.artist:
                        search_results = await self.yt.search(f"{item.title} {item.artist}", filter="songs", limit=1)
                        if search_results:
                            fallback_id = search_results[0].get("videoId")
                            if fallback_id and fallback_id != video_id:
                                watch_data = await self.yt.get_watch_playlist(video_id=fallback_id, limit=15)
                                tracks = watch_data.get('tracks', [])
                                related = [t for t in tracks if t.get('videoId') != fallback_id]
            
            if self._current_play_id == play_id:
                self.now_playing_screen.set_related(related, self._play_song_sync)
        except Exception as e:
            logger.error(f"Error loading related: {e}")
            if self._current_play_id == play_id:
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
                except Exception as e:
                    logger.warning(f"Autoplay failed: {e}")

    def _play_local(self, path: str, metadata: dict) -> None:
        title = metadata.get("title", "Unknown")
        artist = metadata.get("artist", "Unknown")
        thumbnail_url = metadata.get("thumbnail_url", "")
        video_id = metadata.get("video_id", "local")
        
        # Set queue to a single local item so queue controls and state work properly
        item = QueueItem(
            video_id=video_id,
            title=title,
            artist=artist,
            album="Local",
            duration_ms=0,
            thumbnail_url=thumbnail_url,
            is_local=True,
            local_path=path
        )
        self.queue.set_queue([item], 0)
        self._update_queue_panel()
        
        self._run_async(self._play_current())
 
    def _play_local_playlist(self, tracks_metadata: list[dict], start_index: int = 0) -> None:
        queue_items = []
        for m in tracks_metadata:
            item = QueueItem(
                video_id=m.get("video_id", "local"),
                title=m.get("title", "Unknown"),
                artist=m.get("artist", "Unknown"),
                album=m.get("album", "Local"),
                duration_ms=m.get("duration_ms", 0),
                thumbnail_url=m.get("thumbnail_url", ""),
                is_local=True,
                local_path=m.get("file_path", "")
            )
            queue_items.append(item)
            
        if queue_items:
            self.queue.set_queue(queue_items, start_index)
            self._update_queue_panel()
            self._run_async(self._play_current())

    def _on_play_pause(self) -> None:
        self._run_async(self._toggle_play_pause())

    async def _toggle_play_pause(self) -> None:
        from pyrolist.audio.player import PlayerState
        is_vlc_playing = False
        try:
            is_vlc_playing = self.player._player.is_playing()
        except Exception:
            pass

        if self.player.status.state in (PlayerState.PLAYING, PlayerState.LOADING) or is_vlc_playing:
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
        if hasattr(self, 'now_playing_screen'):
            self.now_playing_screen.settings = settings
            self.now_playing_screen.update_lyrics_style()
        from pyrolist.config.paths import AppDirs
        settings.save(AppDirs.settings_file)
        if settings.equalizer.enabled:
            self.player.apply_equalizer(
                settings.equalizer.preamp,
                settings.equalizer.bands,
            )
        
        # Update crossfade settings dynamically
        if hasattr(self, 'crossfade_manager'):
            self.crossfade_manager.enabled = settings.player.crossfade_enabled
            self.crossfade_manager.duration_sec = settings.player.crossfade_duration_sec

        # Update sleep timer dynamically
        if hasattr(self, 'sleep_timer'):
            sleep_mins = getattr(settings.player, 'sleep_timer_minutes', 0)
            if sleep_mins > 0:
                logger.info(f"Setting sleep timer for {sleep_mins} minutes")
                self._run_async(self.sleep_timer.start(sleep_mins * 60, self._on_sleep_timer_expired))
                self.statusBar().showMessage(f"Temporizador de apagado activado: {sleep_mins} min", 3000)
            else:
                if self.sleep_timer._task and not self.sleep_timer._task.done():
                    logger.info("Cancelling sleep timer")
                    self.sleep_timer._task.cancel()
                    self.statusBar().showMessage("Temporizador de apagado desactivado", 3000)

        # Apply appearance changes in real-time
        if hasattr(settings, 'appearance'):
            # Compact sidebar toggle
            if hasattr(self, 'sidebar'):
                if settings.appearance.compact_sidebar and not self.sidebar._collapsed:
                    self.sidebar.toggle_collapse()
                elif not settings.appearance.compact_sidebar and self.sidebar._collapsed:
                    self.sidebar.toggle_collapse()
            
            # Theme mode and accent color change — regenerate stylesheet dynamically
            accent = getattr(settings.appearance, 'accent_color', '#A78BFA')
            theme_mode = getattr(settings.appearance, 'theme_mode', 'dark')
            self._apply_theme_and_accent(theme_mode, accent)

    def _on_sleep_timer_expired(self) -> None:
        logger.info("Sleep timer expired! Pausing music player...")
        self._run_async(self.player.pause())
        self.statusBar().showMessage("Temporizador de apagado finalizado. Pyrolist en pausa.", 5000)
        
        # Reset the sleep timer in settings and notify
        self.settings.player.sleep_timer_minutes = 0
        self._on_settings_changed(self.settings)

        # Refresh PlayerSettingsScreen combobox dynamically if it's currently loaded
        try:
            from pyrolist.ui.screens.settings.player_settings import PlayerSettingsScreen
            player_settings_page = self.settings_screen.stack.findChild(PlayerSettingsScreen)
            if player_settings_page:
                player_settings_page.update_fields()
        except Exception as e:
            logger.debug(f"Failed to refresh settings page fields: {e}")

    def _apply_accent_color(self, accent: str) -> None:
        """Helper for legacy calls or quick updates."""
        theme_mode = getattr(self.settings.appearance, 'theme_mode', 'dark')
        self._apply_theme_and_accent(theme_mode, accent)

    def _apply_theme_and_accent(self, theme_mode: str, accent: str) -> None:
        """Regenerate QSS with custom theme colors and dynamic accent, applying it with a beautiful diagonal wipe transition."""
        theme_key = (theme_mode, accent)
        if hasattr(self, '_last_theme_key') and self._last_theme_key == theme_key:
            return
        
        # Capture current screen pixmap before changing styling for transition animation
        old_pixmap = None
        try:
            old_pixmap = self.grab()
        except Exception as e:
            logger.error(f"Failed to grab screenshot: {e}")

        self._last_theme_key = theme_key
        self._last_accent = accent

        from pyrolist.ui.design import tokens
        
        # Resolve active theme mode base colors
        active_mode = theme_mode
        if active_mode == "system":
            import subprocess
            try:
                res = subprocess.run(
                    ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                    capture_output=True, text=True, timeout=0.5
                )
                if "prefer-light" in res.stdout:
                    active_mode = "light"
                else:
                    active_mode = "dark"
            except Exception:
                active_mode = "dark"

        base_scheme = tokens.LIGHT if active_mode == "light" else tokens.DARK

        from pyrolist.ui.stylesheet import PYROLIST_QSS
        new_qss = PYROLIST_QSS

        # Compute dynamic accent color variants
        bright_hex = "#BBA4FC"
        dark_hex = "#8B5CF6"
        r, g, b = 167, 139, 250
        dark_r, dark_g, dark_b = 139, 92, 246
        
        try:
            from PySide6.QtGui import QColor
            c = QColor(accent)
            if c.isValid():
                bright = c.lighter(125)
                bright_hex = bright.name()
                dark = c.darker(120)
                dark_hex = dark.name()
                r, g, b, _ = c.getRgb()
                dark_r, dark_g, dark_b, _ = dark.getRgb()
        except Exception as e:
            logger.error(f"Error calculating accent color variants: {e}")

        # Update dynamic design tokens globally in memory
        tokens.CURRENT = tokens.ColorScheme(
            bg_base=base_scheme.bg_base,
            bg_surface=base_scheme.bg_surface,
            bg_elevated=base_scheme.bg_elevated,
            bg_high=base_scheme.bg_high,
            bg_overlay=base_scheme.bg_overlay,
            accent=accent,
            accent_bright=bright_hex,
            accent_dim=f"rgba({r},{g},{b},0.15)",
            secondary=base_scheme.secondary,
            secondary_dim=base_scheme.secondary_dim,
            text_primary=base_scheme.text_primary,
            text_secondary=base_scheme.text_secondary,
            text_disabled=base_scheme.text_disabled,
            text_on_accent="#FFFFFF" if active_mode == "light" else "#0A0A14",
            border=f"rgba({r},{g},{b},0.12)",
            border_focus=f"rgba({r},{g},{b},0.50)",
            success=base_scheme.success,
            warning=base_scheme.warning,
            error=base_scheme.error,
            info=base_scheme.info,
            like_color=base_scheme.like_color,
        )

        # Replace accent colors in stylesheet
        new_qss = new_qss.replace('#A78BFA', accent)
        new_qss = new_qss.replace('#a78bfa', accent.lower())
        new_qss = new_qss.replace('#BBA4FC', bright_hex)
        new_qss = new_qss.replace('#bba4fc', bright_hex.lower())
        new_qss = new_qss.replace('#8B5CF6', dark_hex)
        new_qss = new_qss.replace('#8b5cf6', dark_hex.lower())
        new_qss = new_qss.replace('167,139,250', f"{r},{g},{b}")
        new_qss = new_qss.replace('167, 139, 250', f"{r}, {g}, {b}")
        new_qss = new_qss.replace('139,92,246', f"{dark_r},{dark_g},{dark_b}")
        new_qss = new_qss.replace('139, 92, 246', f"{dark_r}, {dark_g}, {dark_b}")

        # Replace base dark background & text colors with dynamic values
        new_qss = new_qss.replace('#0A0A14', tokens.CURRENT.bg_base)
        new_qss = new_qss.replace('#0a0a14', tokens.CURRENT.bg_base.lower())
        new_qss = new_qss.replace('#10101E', tokens.CURRENT.bg_surface)
        new_qss = new_qss.replace('#10101e', tokens.CURRENT.bg_surface.lower())
        new_qss = new_qss.replace('#16162A', tokens.CURRENT.bg_elevated)
        new_qss = new_qss.replace('#16162a', tokens.CURRENT.bg_elevated.lower())
        new_qss = new_qss.replace('#1E1E38', tokens.CURRENT.bg_high)
        new_qss = new_qss.replace('#1e1e38', tokens.CURRENT.bg_high.lower())
        new_qss = new_qss.replace('#F1F0FF', tokens.CURRENT.text_primary)
        new_qss = new_qss.replace('#f1f0ff', tokens.CURRENT.text_primary.lower())
        new_qss = new_qss.replace('#9B9BC0', tokens.CURRENT.text_secondary)
        new_qss = new_qss.replace('#9b9bc0', tokens.CURRENT.text_secondary.lower())
        new_qss = new_qss.replace('#6B6B9B', tokens.CURRENT.text_secondary)
        new_qss = new_qss.replace('#6b6b9b', tokens.CURRENT.text_secondary.lower())
        new_qss = new_qss.replace('#4A4A6A', tokens.CURRENT.text_disabled)
        new_qss = new_qss.replace('#4a4a6a', tokens.CURRENT.text_disabled.lower())
        
        groove_color = "#D0D0DF" if active_mode == "light" else "#2A2A4A"
        new_qss = new_qss.replace('#2A2A4A', groove_color)
        new_qss = new_qss.replace('#2a2a4a', groove_color.lower())

        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.setStyleSheet(new_qss)
            logger.info(f"Theme applied successfully: {active_mode} mode, accent {accent}")

        # Create overlay to sweep and fade out old design state
        if old_pixmap:
            try:
                ThemeTransitionOverlay(self, old_pixmap)
            except Exception as e:
                logger.error(f"Failed to trigger theme change transition: {e}")

    def closeEvent(self, event) -> None:
        if self.settings.player.stop_on_close:
            self._run_async(self.player.stop())
        self.player.release()
        if self.discord:
            self._run_async(self.discord.disconnect())
        self.tray.hide()
        event.accept()


# ─── ThemeTransitionOverlay ───────────────────────────────────
from PySide6.QtGui import QBrush, QColor, QPainter, QPaintEvent, QPixmap, QLinearGradient

class ThemeTransitionOverlay(QWidget):
    def __init__(self, parent: QWidget, old_pixmap: QPixmap):
        super().__init__(parent)
        self.old_pixmap = old_pixmap
        self._progress = 0.0
        # Bypass mouse interaction so widgets underneath are immediately usable
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setGeometry(parent.rect())
        self.show()

        # Driving animation for a stunning 450ms diagonal wipe sweep
        self.anim = QPropertyAnimation(self, b"progress", self)
        self.anim.setDuration(450)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.anim.finished.connect(self.deleteLater)
        self.anim.start()

    def resizeEvent(self, event) -> None:
        self.setGeometry(self.parentWidget().rect())
        super().resizeEvent(event)

    def _get_progress(self) -> float:
        return self._progress

    def _set_progress(self, val: float) -> None:
        self._progress = val
        self.update()

    progress = Property(float, _get_progress, _set_progress)

    def paintEvent(self, event: QPaintEvent) -> None:
        if self._progress >= 1.0:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        p = self._progress

        # Draw the old theme state screenshot
        painter.drawPixmap(0, 0, self.old_pixmap)

        # Use DestinationOut composition to selectively erase parts of the old screen
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)

        # Slanted diagonal gradient mask
        gradient = QLinearGradient(0, 0, w, h)
        
        # Calculate dynamic stops sweeping the diagonal
        wipe_span = 0.35
        start_wipe = p * (1.0 + wipe_span) - wipe_span
        end_wipe = start_wipe + wipe_span
        
        s0 = max(0.0, start_wipe)
        s1 = min(1.0, end_wipe)
        
        gradient.setColorAt(0.0, QColor(0, 0, 0, 255))
        if s0 > 0.0:
            gradient.setColorAt(s0, QColor(0, 0, 0, 255))
        gradient.setColorAt(s1, QColor(0, 0, 0, 0))
        gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())
        
        # Superimpose a smooth flat transparency decay over time to guarantee 100% resolution
        painter.setOpacity(p)
        painter.setBrush(QColor(0, 0, 0, 255))
        painter.drawRect(self.rect())
        
        painter.end()
