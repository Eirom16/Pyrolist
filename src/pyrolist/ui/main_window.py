import asyncio
import json
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QFrame, QMessageBox
)
from PySide6.QtCore import QByteArray, Qt, QSize, QEasingCurve, QPropertyAnimation, Property, QTimer
from qasync import asyncSlot
from loguru import logger
from pyrolist.config.settings import AppSettings
from pyrolist.api.youtube_music import YouTubeMusicClient
from pyrolist.api.stream_extractor import StreamExtractor
from pyrolist.api.lyrics import LyricsClient
from pyrolist.api.lastfm import LastFmScrobbler
from pyrolist.api.discord_rpc import DiscordRPC
from pyrolist.audio.player import MusicPlayer, PlayerState
from pyrolist.audio.queue import PlayQueue, QueueItem, RepeatMode
from pyrolist.system.mpris import MprisPlayer
from pyrolist.system.tray import SystemTray
from pyrolist.ui.widgets.nav_sidebar import NavSidebar
from pyrolist.ui.widgets.mini_player import MiniPlayerWidget
from pyrolist.ui.widgets.fade_stack import FadeStackedWidget
from pyrolist.ui.widgets.toast import ToastNotification
from pyrolist.audio.sleep_timer import SleepTimer
from pyrolist.audio.crossfade import CrossfadeManager
from pyrolist.ui.theme_manager import ThemeManager


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
    ONLINE_ROUTES = {"home", "library", "playlist", "album", "artist", "search"}

    def __init__(self, settings: AppSettings, event_loop=None):
        super().__init__()
        self.settings = settings
        self._loop = event_loop
        self._pending_tasks: set[asyncio.Task] = set()
        self._current_nav_task: asyncio.Task | None = None
        self._current_play_id = 0
        self._nav_history: list[int] = []  # stack of previous screen indices for back navigation
        self.queue_panel = None
        self.theme_manager = ThemeManager(self)

        
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
        self.queue.shuffle_enabled = self.settings.player.shuffle_enabled
        try:
            self.queue.repeat_mode = RepeatMode(self.settings.player.repeat_mode)
        except ValueError:
            self.queue.repeat_mode = RepeatMode.OFF
        self.mpris = MprisPlayer(self.player, self.queue)
        self.scrobbler: LastFmScrobbler | None = None
        self._lastfm_track_key: tuple[str, str, str] | None = None
        self._lastfm_started_at: int | None = None
        self._lastfm_scrobbled = False
        self._lastfm_scrobble_pending = False
        self.discord: DiscordRPC | None = None
        self._force_close = False
        from pyrolist.config.paths import AppDirs
        self._queue_state_file = AppDirs.data / "queue_state.json"
        self._window_state_file = AppDirs.data / "window_state.json"
        self._resume_position_ms = 0
        self._current_route = "home"
        self._offline_blocked_path: str | None = None
        self._stream_recovery_attempts: set[str] = set()
        self.sleep_timer = SleepTimer()
        self.crossfade_manager = CrossfadeManager(
            enabled=settings.player.crossfade_enabled,
            duration_sec=settings.player.crossfade_duration_sec
        )

        self._setup_window()
        self._build_ui()
        self._connect_player_callbacks()
        self._setup_integrations()
        self._setup_shortcuts()
        
        # Apply initial theme properly (immediately on startup to prevent flash)
        theme_mode = getattr(settings.appearance, 'theme_mode', 'dark')
        accent = getattr(settings.appearance, 'accent_color', '#A78BFA')
        self.theme_manager.apply(theme_mode, accent, immediate=True)

    def _setup_shortcuts(self) -> None:
        from PySide6.QtGui import QShortcut, QKeySequence
        from PySide6.QtWidgets import QApplication, QLineEdit, QTextEdit, QAbstractSpinBox
        from PySide6.QtCore import QObject, QEvent, Qt

        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(self.search_bar.focus_search)
        
        slash_shortcut = QShortcut(QKeySequence("/"), self)
        slash_shortcut.activated.connect(self.search_bar.focus_search)

        class GlobalShortcutFilter(QObject):
            def __init__(self, main_window):
                super().__init__(main_window)
                self.mw = main_window

            def _close_escape_target(self) -> bool:
                search_bar = getattr(self.mw, "search_bar", None)
                dropdown = getattr(search_bar, "_dropdown", None)
                if dropdown is not None and dropdown.isVisible():
                    search_bar._hide_dropdown()
                    return True

                notification_panel = getattr(self.mw, "notification_panel", None)
                if notification_panel is not None and notification_panel.isVisible():
                    notification_panel._close_anim()
                    return True

                return False

            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.KeyPress:
                    focus_widget = QApplication.focusWidget()
                    if event.key() == Qt.Key.Key_Escape and self._close_escape_target():
                        return True

                    if isinstance(focus_widget, (QLineEdit, QTextEdit, QAbstractSpinBox)):
                        if event.key() == Qt.Key.Key_Escape:
                            focus_widget.clearFocus()
                            return True
                        return False
                        
                    key = event.key()
                    modifiers = event.modifiers()
                    if key == Qt.Key.Key_Space:
                        self.mw._on_play_pause()
                        return True
                    elif key == Qt.Key.Key_Right and modifiers & Qt.KeyboardModifier.ControlModifier:
                        self.mw._on_next()
                        return True
                    elif key == Qt.Key.Key_Left and modifiers & Qt.KeyboardModifier.ControlModifier:
                        self.mw._on_prev()
                        return True
                    elif key == Qt.Key.Key_Right:
                        if self.mw.player.status.duration_ms > 0:
                            p = self.mw.player.status.position_ms
                            self.mw._on_seek(p + 5000)
                        return True
                    elif key == Qt.Key.Key_Left:
                        if self.mw.player.status.duration_ms > 0:
                            p = self.mw.player.status.position_ms
                            self.mw._on_seek(max(0, p - 5000))
                        return True
                    elif key == Qt.Key.Key_Up:
                        v = self.mw.player.status.volume
                        self.mw.player.set_volume(min(100, v + 5))
                        return True
                    elif key == Qt.Key.Key_Down:
                        v = self.mw.player.status.volume
                        self.mw.player.set_volume(max(0, v - 5))
                        return True
                return False

        self._shortcut_filter = GlobalShortcutFilter(self)
        self.installEventFilter(self._shortcut_filter)

        # Verificar actualizaciones 10 segundos después de arrancar
        # (no al instante para no retrasar la carga inicial)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(10_000, lambda: asyncio.ensure_future(self._check_updates()))

        from pyrolist.services.lyrics_prefetcher import LyricsPrefetcher
        self._lyrics_prefetcher = LyricsPrefetcher()
        self._run_async(self._lyrics_prefetcher.run())

        # Connect cleanup handler to application quit
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.aboutToQuit.connect(self._cleanup_on_close)

        if self._loop:
            self._init_task = self._loop.create_task(self._initialize())
            self._track_task(self._init_task)
        else:
            self._init_task = asyncio.ensure_future(self._initialize())
            self._track_task(self._init_task)



    def _setup_window(self) -> None:
        self.setWindowTitle("Pyrolist")
        self.setMinimumSize(QSize(960, 640))
        self.resize(1300, 820)
        self._restore_window_state()

    def _restore_window_state(self) -> None:
        try:
            if not self._window_state_file.exists():
                return
            with open(self._window_state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            geometry_hex = data.get("geometry")
            if geometry_hex:
                self.restoreGeometry(QByteArray.fromHex(geometry_hex.encode("ascii")))
        except Exception as e:
            logger.debug(f"Failed to restore window state: {e}")

    def _save_window_state(self) -> None:
        try:
            self._window_state_file.parent.mkdir(parents=True, exist_ok=True)
            data = {"geometry": bytes(self.saveGeometry().toHex()).decode("ascii")}
            with open(self._window_state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.debug(f"Failed to save window state: {e}")

    def _build_ui(self) -> None:
        central = QWidget()
        self._central_widget = central
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        content_area = QWidget()
        content_area.setObjectName("contentArea")
        h_layout = QHBoxLayout(content_area)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        self.sidebar = NavSidebar(on_navigate=self._navigate_to)
        self.sidebar.on_login_click.connect(self._show_login)
        self.sidebar.auth_changed.connect(self._on_auth_changed)
        
        # Initialize Notification Service
        from pyrolist.services.notification_service import NotificationService
        self.notification_service = NotificationService(self.yt)
        
        if self.yt.is_authenticated:
            self.notification_service.start()
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
            except Exception as e:
                logger.debug(f"Could not refresh account info from API: {e}")
            
            # Fallback: read from saved profile
            if name == "YouTube Music":
                profile_file = AppDirs.config / "user_profile.json"
                if profile_file.exists():
                    try:
                        with open(profile_file, "r") as f:
                            data = json.load(f)
                            name = data.get("name", "YouTube Music") or "YouTube Music"
                            avatar = data.get("avatar_url", "")
                    except Exception as e:
                        logger.debug(f"Could not read saved user profile: {e}")
            self.sidebar.update_auth_state(True, name, avatar)
        h_layout.addWidget(self.sidebar)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        from pyrolist.ui.widgets.global_search import GlobalSearchBar
        self.search_bar = GlobalSearchBar(self.yt, self._play_song_sync)
        self.search_bar.search_submitted.connect(self._on_search_submitted)
        
        self.notification_service.unread_changed.connect(self.search_bar.notif_btn.set_unread)
        self._run_async(self.notification_service.check_unread())
        
        right_layout.addWidget(self.search_bar)

        # Add glassmorphic offline warning banner
        from pyrolist.ui.widgets.offline_banner import OfflineBannerWidget
        self.offline_banner = OfflineBannerWidget(self)
        right_layout.addWidget(self.offline_banner)

        # Container for stack and notification panel
        self.main_content_hbox = QHBoxLayout()
        self.main_content_hbox.setContentsMargins(0, 0, 0, 0)
        self.main_content_hbox.setSpacing(0)

        self.stack = FadeStackedWidget()
        self.stack.setObjectName("screenStack")
        self.main_content_hbox.addWidget(self.stack)

        from pyrolist.ui.widgets.notification_panel import NotificationPanel
        self.notification_panel = NotificationPanel(self)
        self.notification_panel.hide()
        self.main_content_hbox.addWidget(self.notification_panel)

        self.search_bar.notifications_requested.connect(self.notification_panel.toggle_panel)
        self.notification_panel.panel_toggled.connect(self.search_bar.notif_btn.set_panel_open)
        self.notification_panel.artist_clicked.connect(lambda a, a_id: self._navigate_to(f"artist?id={a_id}") if a_id else self.resolve_and_navigate_artist(a))
        self.notification_panel.song_clicked.connect(lambda v, t, a, u: self._play_song_sync(v, t, a, "", 0, u))



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
        from pyrolist.ui.widgets.error_state import ErrorStateWidget

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
        self.playlist_screen = PlaylistScreen(self.yt, self._play_song_sync, self._play_local_playlist, on_back=self._go_back)
        self.album_screen = AlbumScreen(self.yt, self._play_song_sync, on_back=self._go_back)
        self.artist_screen = ArtistScreen(self.yt, self._play_song_sync, self._navigate_to, on_back=self._go_back)
        self.now_playing_screen = NowPlayingScreen(self.player, self.queue, self.yt, self._play_queue_item, self.settings, on_back=self._go_back)
        self.search_screen = SearchScreen(self.yt, self._play_song_sync, self._navigate_to)
        self.stats_screen = StatsScreen(self.yt, self._play_song_sync)
        self.offline_state_screen = ErrorStateWidget(
            "No hay conexion. Puedes seguir escuchando tu musica descargada.",
            retry_callback=lambda: self._navigate_to("downloads"),
            action_text="Ir a Descargas",
        )

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
            if hasattr(screen, 'download_album_requested'):
                screen.download_album_requested.connect(self._on_download_album_requested)
            if hasattr(screen, 'like_requested'):
                screen.like_requested.connect(self._on_like_requested)
            if hasattr(screen, 'delete_download_requested'):
                screen.delete_download_requested.connect(self._on_delete_download_requested)
            if hasattr(screen, 'delete_playlist_requested'):
                screen.delete_playlist_requested.connect(self._on_delete_playlist_requested)
            if hasattr(screen, 'artist_clicked'):
                screen.artist_clicked.connect(self.resolve_and_navigate_artist)
            if hasattr(screen, 'album_clicked'):
                screen.album_clicked.connect(self.resolve_and_navigate_album)

        self._offline_state_index = self.stack.addWidget(self.offline_state_screen)

        if hasattr(self.now_playing_screen, 'queue_tab'):
            self.now_playing_screen.queue_tab.like_requested.connect(self._on_like_requested)
            self.now_playing_screen.queue_tab.artist_clicked.connect(self.resolve_and_navigate_artist)
            self.now_playing_screen.queue_tab.album_clicked.connect(self.resolve_and_navigate_album)
            
        # Connect queue panel artist
        if self.queue_panel:
            self.queue_panel.artist_clicked.connect(self.resolve_and_navigate_artist)

        right_layout.addLayout(self.main_content_hbox)

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
            parent=central,
        )
        self.mini_player.raise_()
        self.sidebar._width_anim.valueChanged.connect(lambda _value: self._position_mini_player())
        self.sidebar._max_anim.valueChanged.connect(lambda _value: self._position_mini_player())
        self._position_mini_player()

        if hasattr(self, 'mini_player'):
            self.mini_player.artist_clicked.connect(self.resolve_and_navigate_artist)

        self.statusBar().setObjectName("appStatusBar")
        self.statusBar().setStyleSheet("color: #888899; font-family: Inter; font-size: 11px;")
        self.statusBar().setFixedHeight(0)
        self.statusBar().hide()

        self.tray = SystemTray(
            parent=self,
            on_show=self._show_and_activate,
            on_play_pause=self._on_play_pause,
            on_prev=self._on_prev,
            on_next=self._on_next,
            on_quit=self._on_tray_quit,
        )

    def _position_mini_player(self) -> None:
        if not hasattr(self, "mini_player") or not self.mini_player:
            return
        central = getattr(self, "_central_widget", None) or self.centralWidget()
        if central is None:
            return

        margin = 12
        player_height = self.mini_player.height()
        sidebar_width = self.sidebar.width() if hasattr(self, "sidebar") and self.sidebar.isVisible() else 0
        
        right_panel_width = 0
        if hasattr(self, "notification_panel") and self.notification_panel.isVisible():
            right_panel_width = self.notification_panel.maximumWidth()
            
        x = sidebar_width + margin
        width = max(0, central.width() - x - margin - right_panel_width)
        y = central.height() - player_height - margin if player_height > 0 else central.height()
        self.mini_player.setGeometry(x, max(0, y), width, max(0, player_height))
        self.mini_player.raise_()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_mini_player()
        if hasattr(self, 'theme_manager'):
            self.theme_manager.on_main_window_resized()

    def _connect_player_callbacks(self) -> None:
        self.player.on("track_ended", self._on_track_ended_callback)
        self.player.on("state_changed", self._on_state_changed_callback)
        self.player.on("position_changed", self._on_position_changed_callback)
        self.player.on("error", self._on_player_error_callback)

    def _on_track_ended_callback(self, status) -> None:
        self._run_async(self._advance_queue())

    def _on_player_error_callback(self, status) -> None:
        self._run_async(self._recover_player_error(status))

    async def _recover_player_error(self, status) -> None:
        item = self.queue.current
        if not item:
            return

        if (
            item.video_id not in self._stream_recovery_attempts
            and not item.is_local
            and not self._should_show_offline_state("home")
        ):
            self._stream_recovery_attempts.add(item.video_id)
            logger.warning(f"Trying alternative stream after VLC error: {item.title}")
            alt_url = await self.extractor.get_alternative_stream(item.video_id)
            if alt_url and await self.player.play_url(alt_url, item.video_id):
                ToastNotification.show(self, "Reproduciendo formato alternativo", "info")
                return

        await self._handle_playback_failure(item, "No se pudo reproducir la pista. Saltando a la siguiente.")

    async def _handle_playback_failure(self, item: QueueItem, message: str) -> None:
        logger.error(f"Playback failed for {item.video_id}: {item.title}")
        ToastNotification.show(self, message, "error")
        if self.queue.next_item:
            await self._advance_queue()
        else:
            await self.player.stop()

    def _on_state_changed_callback(self, status) -> None:
        self.mini_player.update_state(status)
        self.now_playing_screen.update_state(status)
        from pyrolist.audio.player import PlayerState
        is_playing = status.state == PlayerState.PLAYING
        
        if self.mpris:
            self.mpris.update_playback_status(is_playing)
            
        if hasattr(self, "tray") and self.tray:
            self.tray.update_play_state(is_playing)
            
        if self.discord and self.queue.current:
            item = self.queue.current
            self._run_async(self.discord.update(
                item.title, item.artist, item.album, is_playing, item.thumbnail_url
            ))

    def _on_position_changed_callback(self, status) -> None:
        self.mini_player.update_position(
            status.position_ms, status.duration_ms
        )
        self.now_playing_screen.update_position(
            status.position_ms, status.duration_ms
        )
        self._maybe_scrobble_lastfm(status)
        if self.mpris:
            self.mpris.update_position(status.position_ms)
            self.mpris.update_volume(status.volume)

    def _reset_lastfm_scrobble_state(self, item: QueueItem) -> None:
        import time
        self._lastfm_track_key = (item.video_id, item.title, item.artist)
        self._lastfm_started_at = int(time.time())
        self._lastfm_scrobbled = False
        self._lastfm_scrobble_pending = False

    def _maybe_scrobble_lastfm(self, status) -> None:
        if (
            not self.scrobbler
            or self._lastfm_scrobbled
            or self._lastfm_scrobble_pending
            or status.duration_ms <= 0
        ):
            return

        item = self.queue.current
        if not item or self._lastfm_track_key != (item.video_id, item.title, item.artist):
            return

        threshold_ms = min(status.duration_ms * 0.5, 240_000)
        if status.position_ms < threshold_ms:
            return

        self._lastfm_scrobble_pending = True
        self._run_async(self._scrobble_current_lastfm(item, self._lastfm_started_at))

    async def _scrobble_current_lastfm(self, item: QueueItem, started_at: int | None) -> None:
        if not self.scrobbler or not started_at:
            self._lastfm_scrobble_pending = False
            return
        track_key = (item.video_id, item.title, item.artist)
        if self._lastfm_track_key != track_key:
            self._lastfm_scrobble_pending = False
            return
        try:
            success = await self.scrobbler.scrobble(
                item.artist, item.title, item.album, timestamp=started_at
            )
            if success:
                self._lastfm_scrobbled = True
                logger.info(f"Last.fm scrobbled: {item.artist} - {item.title}")
            else:
                logger.info(f"Last.fm scrobble queued for retry: {item.artist} - {item.title}")
        except Exception as e:
            logger.warning(f"Last.fm scrobble failed for {item.video_id}: {e}")
        finally:
            self._lastfm_scrobble_pending = False

    def _setup_integrations(self) -> None:
        # Initialize player parameters from settings
        self.player.set_volume(self.settings.player.volume)
        if self.settings.equalizer.enabled:
            self.player.apply_equalizer(
                self.settings.equalizer.preamp,
                self.settings.equalizer.bands,
            )
        else:
            self.player.reset_equalizer()

        if self.settings.integrations.mpris_enabled:
            # Wire MPRIS2 callbacks
            self.mpris.on_play_pause = self._on_play_pause
            self.mpris.on_play = lambda: self._run_async(self.player.resume())
            self.mpris.on_pause = lambda: self._run_async(self.player.pause())
            self.mpris.on_stop = lambda: self._run_async(self.player.stop())
            self.mpris.on_next = self._on_next
            self.mpris.on_prev = self._on_prev
            self.mpris.on_seek = lambda offset_us: self._on_seek(self.player.status.position_ms + int(offset_us / 1000))
            self.mpris.on_set_position = lambda track_id, position_us: self._on_seek(int(position_us / 1000))
            self.mpris.on_set_volume = lambda vol: (self.player.set_volume(int(vol * 100)), self._on_mpris_volume_changed(int(vol * 100)))
            self.mpris.on_set_shuffle = lambda shuffle: self._toggle_shuffle_from_mpris(shuffle)
            self.mpris.on_set_loop_status = self._set_repeat_from_mpris
            self.mpris.on_raise = lambda: (self.show(), self.raise_(), self.activateWindow())
            self.mpris.on_quit = self.close
            self.mpris.start()
            self.mpris.update_shuffle(self.queue.shuffle_enabled)
            self.mpris.update_loop_status()

        if self.settings.integrations.lastfm_enabled and self.settings.integrations.lastfm_session_key:
            self.scrobbler = LastFmScrobbler(
                self.settings.integrations.lastfm_api_key,
                self.settings.integrations.lastfm_api_secret,
                self.settings.integrations.lastfm_session_key,
            )
        if self.settings.integrations.discord_rpc_enabled:
            self.discord = DiscordRPC()
            task = self._run_async(self.discord.connect())

        # Setup and start network monitor
        from pyrolist.system.network import NetworkMonitor
        self.network_monitor = NetworkMonitor(on_connectivity_change=self._on_connectivity_change)
        self._run_async(self.network_monitor.start())

    def _on_mpris_volume_changed(self, volume: int) -> None:
        self.settings.player.volume = volume
        self._on_settings_changed(self.settings)
        try:
            from pyrolist.ui.screens.settings.player_settings import PlayerSettingsScreen
            player_settings_page = self.settings_screen.stack.findChild(PlayerSettingsScreen)
            if player_settings_page:
                player_settings_page.update_fields()
        except Exception as e:
            logger.debug(f"Could not sync player settings screen volume: {e}")

    def _on_connectivity_change(self, is_connected: bool) -> None:
        """Handle network status transitions dynamically."""
        if not is_connected:
            self.offline_banner.show_banner()
            ToastNotification.show(self, "Sin conexión: reproduciendo descargas locales", "warning")
            if self._current_route in self.ONLINE_ROUTES:
                self._offline_blocked_path = self._current_route
                self._show_offline_state(self._current_route)
        else:
            self.offline_banner.hide_banner()
            ToastNotification.show(self, "Conexión de red restablecida", "success")
            
            # Reload active static screen to resume online capabilities
            if self._offline_blocked_path:
                blocked_path = self._offline_blocked_path
                self._offline_blocked_path = None
                self._navigate_to(blocked_path)
            else:
                current_index = self.stack.currentIndex()
                active_route = next((k for k, v in self.ROUTES.items() if v == current_index), None)
                if active_route:
                    self._run_async(self._load_screen(active_route))

    def _toggle_shuffle_from_mpris(self, enable: bool) -> None:
        if enable != self.queue.shuffle_enabled:
            self.queue.toggle_shuffle()
            self._persist_queue_playback_settings()
            self.now_playing_screen.update_shuffle_repeat_state()
            self._update_queue_panel()
            if self.mpris:
                self.mpris.update_shuffle(enable)

    def _persist_queue_playback_settings(self) -> None:
        self.settings.player.shuffle_enabled = self.queue.shuffle_enabled
        self.settings.player.repeat_mode = self.queue.repeat_mode.value
        self._on_settings_changed(self.settings)

    def _set_repeat_from_mpris(self, loop_status: str) -> None:
        mapping = {
            "None": RepeatMode.OFF,
            "Playlist": RepeatMode.ALL,
            "Track": RepeatMode.ONE,
        }
        repeat_mode = mapping.get(loop_status, RepeatMode.OFF)
        if self.queue.repeat_mode == repeat_mode:
            return
        self.queue.repeat_mode = repeat_mode
        self._persist_queue_playback_settings()
        if hasattr(self, "now_playing_screen"):
            self.now_playing_screen.update_shuffle_repeat_state()
        if self.mpris:
            self.mpris.update_loop_status()

    def _track_task(self, task: asyncio.Task) -> None:
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

        def _log_task_result(t: asyncio.Task):
            try:
                t.result()
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.exception(f"Unhandled exception in background task: {e}")
        task.add_done_callback(_log_task_result)


    def _run_async(self, coro) -> asyncio.Task:
        if self._loop:
            task = self._loop.create_task(coro)
        else:
            task = asyncio.ensure_future(coro)
        self._track_task(task)
        return task

    def _play_song_sync(
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
        self._run_async(
            self._play_song(
                video_id,
                title,
                artist,
                album,
                duration_ms,
                thumbnail_url,
                queue_items,
                queue_index,
            )
        )

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
            
            def navigate_to_downloads():
                self._navigate_to("downloads")
                
            self.show_notification(f"Descargando: {title}", "info", action_text="VER", action_callback=navigate_to_downloads)
        else:
            self.statusBar().showMessage(f"Ya en cola: {title}", 3000)

    def _on_download_finished(self, video_id, file_path):
        self.statusBar().showMessage(f"Descarga completa!", 5000)

    def _on_download_playlist_requested(self, playlist_id, title, thumbnail_url):
        self._run_async(self._download_playlist_async(playlist_id, title, thumbnail_url))

    async def _download_playlist_async(self, playlist_id, title, thumbnail_url):
        self.statusBar().showMessage(f"Iniciando descarga de playlist: {title}", 3000)
        
        def navigate_to_downloads():
            self._navigate_to("downloads")
            
        self.show_notification(f"Descargando playlist: {title}", "info", action_text="VER", action_callback=navigate_to_downloads)
        
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

    def _on_download_album_requested(self, browse_id, title, thumbnail_url):
        self._run_async(self._download_album_async(browse_id, title, thumbnail_url))

    async def _download_album_async(self, browse_id, title, thumbnail_url):
        self.statusBar().showMessage(f"Iniciando descarga de álbum: {title}", 3000)
        def navigate_to_downloads():
            self._navigate_to("downloads")
        self.show_notification(f"Iniciando descarga de álbum: {title}", "info", action_text="VER", action_callback=navigate_to_downloads)

        try:
            data = await self.yt.get_album(browse_id)
            album_thumbnails = data.get('thumbnails', [])
            if album_thumbnails:
                high_res_thumb = album_thumbnails[-1].get('url', '')
                if high_res_thumb:
                    thumbnail_url = high_res_thumb

            tracks = data.get('tracks', [])
            artists = data.get('artists', [])
            album_artist = ", ".join([a.get('name', '') for a in artists]) if isinstance(artists, list) else str(artists)
            parent_id = f"album_{browse_id}"

            queued = 0
            already_downloaded = 0
            for track in tracks:
                vid = track.get('videoId')
                if not vid:
                    continue

                existing = await self.download_manager._repo.get_download(vid)
                if existing:
                    already_downloaded += 1
                    continue

                t_title = track.get('title', 'Unknown')
                track_artists = track.get('artists', [])
                if track_artists:
                    artist_names = ", ".join([a.get('name', '') for a in track_artists]) if isinstance(track_artists, list) else str(track_artists)
                else:
                    artist_names = album_artist
                track_thumbnails = track.get('thumbnails', [])
                track_thumb = track_thumbnails[-1].get('url', '') if track_thumbnails else thumbnail_url

                if self.download_manager.add_download(vid, t_title, artist_names, track_thumb, parent_id, title, thumbnail_url):
                    queued += 1

            if already_downloaded > 0:
                self.statusBar().showMessage(f"{queued} añadidas a cola • {already_downloaded} ya descargadas", 5000)
                self.show_notification(f"{queued} añadidas, {already_downloaded} omitidas (ya descargadas).", "success")
            else:
                self.statusBar().showMessage(f"{queued} canciones del álbum añadidas a cola", 4000)
                self.show_notification(f"{queued} canciones del álbum añadidas a la cola", "success")
        except Exception as e:
            logger.error(f"Error downloading album: {e}")
            self.statusBar().showMessage("Error al iniciar descarga de álbum", 4000)

    def _on_download_error(self, video_id, error):
        self.statusBar().showMessage(f"Error en descarga: {error}", 5000)

    def _on_delete_download_requested(self, video_id: str):
        self._run_async(self._delete_download_async(video_id))

    def _confirm_destructive_action(self, title: str, message: str) -> bool:
        result = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.Cancel,
        )
        return result == QMessageBox.StandardButton.Yes

    async def _delete_download_async(self, video_id: str):
        from pathlib import Path
        from pyrolist.db.repository import DownloadRepository
        repo = DownloadRepository()
        d = await repo.get_download(video_id)
        if d:
            title = d.title
            if not self._confirm_destructive_action(
                "Eliminar descarga",
                f"¿Eliminar la descarga local de \"{title}\"?",
            ):
                return
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

        playlist_downloads = [
            d for d in downloads if d.parent_playlist_id == playlist_id
        ]
        playlist_title = next(
            (d.parent_playlist_title for d in playlist_downloads if d.parent_playlist_title),
            playlist_id,
        )
        if not playlist_downloads:
            return
        if not self._confirm_destructive_action(
            "Eliminar playlist local",
            f"¿Eliminar \"{playlist_title}\" y sus {len(playlist_downloads)} canciones descargadas?",
        ):
            return
        
        count = 0
        for d in playlist_downloads:
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

    def show_notification(self, message: str, kind: str = "info", action_text: str = None, action_callback = None):
        if hasattr(self, "search_bar"):
            self.search_bar.notif_dropdown.add_custom_notification(message, kind)
        from pyrolist.ui.widgets.toast import ToastNotification
        ToastNotification.show(self, message, kind, action_text, action_callback)

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

        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
            QWidget, QLineEdit, QPushButton, QGraphicsDropShadowEffect
        )
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtGui import QColor, QPixmap
        from pyrolist.ui.design.fonts import AppFont
        from pyrolist.ui.design.icons import Icon
        from pyrolist.ui.design import tokens
        from pyrolist.ui.design.animations import fade_in

        dialog = QDialog(self)
        dialog.setWindowTitle("Añadir a Playlist")
        dialog.setFixedSize(440, 480)
        dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        shadow = QGraphicsDropShadowEffect(dialog)
        shadow.setBlurRadius(48)
        shadow.setOffset(0, 12)
        shadow.setColor(QColor(0, 0, 0, 140))
        dialog.setGraphicsEffect(shadow)

        root = QWidget(dialog)
        root.setFixedSize(440, 480)
        root.setObjectName("addToPlaylistRoot")
        root.setStyleSheet(f"""
            QWidget#addToPlaylistRoot {{
                background: {tokens.CURRENT.bg_surface};
                border-radius: 16px;
            }}
        """)

        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(80)
        header.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {tokens.CURRENT.accent},
                stop:1 {tokens.CURRENT.accent_bright});
            border-radius: 16px 16px 0 0;
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        icon_lbl = QLabel(Icon.get("playlist_add"))
        icon_lbl.setFont(Icon.font(28, filled=True))
        icon_lbl.setStyleSheet(f"color: {tokens.CURRENT.text_on_accent}; background: transparent;")
        header_layout.addWidget(icon_lbl)

        header_text = QLabel(f"Añadir a playlist")
        header_text.setFont(AppFont.heading(17))
        header_text.setStyleSheet(f"color: {tokens.CURRENT.text_on_accent}; background: transparent;")
        header_layout.addWidget(header_text)
        header_layout.addStretch()

        close_btn = QPushButton(Icon.get("close"))
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.15);
                color: {tokens.CURRENT.text_on_accent};
                border: none;
                border-radius: 16px;
                font-family: 'Material Symbols Rounded';
                font-size: 20px;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.25); }}
        """)
        close_btn.clicked.connect(dialog.reject)
        header_layout.addWidget(close_btn)

        root_layout.addWidget(header)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(16, 12, 16, 16)
        body_layout.setSpacing(8)

        search_input = QLineEdit()
        search_input.setPlaceholderText("Buscar playlist...")
        search_input.setStyleSheet(f"""
            QLineEdit {{
                background: {tokens.CURRENT.bg_elevated};
                color: {tokens.CURRENT.text_primary};
                border: 1px solid {tokens.CURRENT.border};
                border-radius: 10px;
                padding: 10px 14px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 2px solid {tokens.CURRENT.accent};
                padding: 9px 13px;
            }}
        """)
        body_layout.addWidget(search_input)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(6)

        for pl in playlists:
            pid = pl.get('playlistId')
            p_title = pl.get('title', 'Unknown')
            p_count = pl.get('count', '')
            p_thumbnails = pl.get('thumbnails', [])
            p_thumbnail_url = p_thumbnails[-1].get('url', '') if p_thumbnails else ''
            subtitle = f"{p_count} canciones" if p_count else ""

            row = QPushButton()
            row.setFixedHeight(60)
            row.setCursor(Qt.CursorShape.PointingHandCursor)
            row.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    border-radius: 8px;
                    text-align: left;
                    padding: 0;
                }}
                QPushButton:hover {{
                    background: {tokens.CURRENT.accent_dim};
                }}
            """)

            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 8, 10, 8)
            row_layout.setSpacing(12)

            thumb = QLabel()
            thumb.setFixedSize(44, 44)
            if p_thumbnail_url:
                thumb.setStyleSheet("background: transparent; border-radius: 8px;")
                asyncio.ensure_future(self._load_playlist_thumb(thumb, p_thumbnail_url))
            else:
                thumb.setFont(Icon.font(22))
                thumb.setText(Icon.get("playlist_play"))
                thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
                thumb.setStyleSheet(f"""
                    background: {tokens.CURRENT.bg_high};
                    color: {tokens.CURRENT.text_disabled};
                    border-radius: 8px;
                """)
            row_layout.addWidget(thumb)

            text_col = QVBoxLayout()
            text_col.setSpacing(2)
            name_lbl = QLabel(p_title)
            name_lbl.setFont(AppFont.title(13))
            name_lbl.setStyleSheet(f"color: {tokens.CURRENT.text_primary}; background: transparent;")
            text_col.addWidget(name_lbl)

            if subtitle:
                sub_lbl = QLabel(subtitle)
                sub_lbl.setFont(AppFont.caption(11))
                sub_lbl.setStyleSheet(f"color: {tokens.CURRENT.text_secondary}; background: transparent;")
                text_col.addWidget(sub_lbl)

            row_layout.addLayout(text_col)
            row_layout.addStretch()

            add_icon = QLabel(Icon.get("add"))
            add_icon.setFont(Icon.font(18))
            add_icon.setStyleSheet(f"color: {tokens.CURRENT.text_disabled}; background: transparent;")
            add_icon.setFixedSize(28, 28)
            add_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row_layout.addWidget(add_icon)

            row.clicked.connect(lambda _, pid=pid, p_title=p_title: (
                dialog.accept(),
                self._run_async(self._add_to_yt_playlist(pid, video_id, p_title))
            ))
            content_layout.addWidget(row)

        content_layout.addStretch()
        scroll.setWidget(content)
        body_layout.addWidget(scroll)

        root_layout.addWidget(body)

        def filter_playlists(text: str):
            for i in range(content_layout.count()):
                item = content_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    lbl = widget.findChildren(QLabel)
                    match = False
                    for l in lbl:
                        if text.lower() in l.text().lower():
                            match = True
                            break
                    widget.setVisible(match)

        search_input.textChanged.connect(filter_playlists)

        fade_in(root, 200)
        self._playlist_dialog = dialog
        dialog.open()

    async def _load_playlist_thumb(self, thumb_label, url):
        from PySide6.QtGui import QPixmap
        from pyrolist.utils.image_cache import ImageCache
        _image_cache = ImageCache()
        path = await _image_cache.download(url)
        import shiboken6
        if not shiboken6.isValid(thumb_label):
            return
        if path:
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                pixmap = pixmap.scaled(44, 44, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                       Qt.TransformationMode.SmoothTransformation)
                thumb_label.setPixmap(pixmap)
                thumb_label.setStyleSheet("background: transparent; border-radius: 8px;")

    async def _add_to_yt_playlist(self, playlist_id: str, video_id: str, playlist_name: str):
        try:
            res = await self.yt.add_playlist_items(playlist_id, [video_id])
            if res and (res.get('status') == 'STATUS_SUCCEEDED' or 'playlistItemId' in res):
                self.statusBar().showMessage(f"Añadido a '{playlist_name}'", 3000)
                self.show_notification(f"Se añadió la canción a '{playlist_name}'", "success")
            else:
                self.statusBar().showMessage("Error al añadir a playlist", 3000)
                self.show_notification("Error al añadir a playlist", "error")
        except Exception as e:
            logger.error(f"Failed to add to playlist: {e}")
            self.statusBar().showMessage("Error al añadir a playlist", 3000)
            self.show_notification("Error al añadir a playlist", "error")

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

        # Sync with YouTube Music in the background if authenticated
        if self.yt.is_authenticated:
            rating = "LIKE" if liked else "INDIFFERENT"
            self._run_async(self.yt.rate_song(video_id, rating))
            self.library_screen.invalidate_songs_cache()
        else:
            self.library_screen.invalidate_songs_cache()
        
        # If the library screen is currently active and the "songs" tab is active:
        # If unliked, animate it fading out and remove it locally to avoid reloading lag!
        current_screen = self.stack.currentWidget()
        if current_screen == self.library_screen and self.library_screen._current_tab == "songs" and not liked:
            card = btn_like.parent()
            if card and isinstance(card, QWidget):
                from PySide6.QtWidgets import QGraphicsOpacityEffect
                from PySide6.QtCore import QPropertyAnimation, QEasingCurve
                
                effect = QGraphicsOpacityEffect(card)
                card.setGraphicsEffect(effect)
                anim = QPropertyAnimation(effect, b"opacity")
                anim.setDuration(250)
                anim.setStartValue(1.0)
                anim.setEndValue(0.0)
                anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                
                def on_fade_finished():
                    self.library_screen.content_layout.removeWidget(card)
                    card.deleteLater()
                
                anim.finished.connect(on_fade_finished)
                card._fade_anim = anim  # prevent GC
                anim.start()
        
        if btn_like.objectName() == "nowPlayingLikeBtn":
            self.now_playing_screen.set_liked_state(liked)
            self.statusBar().showMessage("Añadido a Favoritas" if liked else "Eliminado de Favoritas", 2000)
            self._update_queue_panel()
            return
        
        # Update parent SongCard's internal state if applicable
        parent_card = btn_like.parent()
        if parent_card and hasattr(parent_card, "_is_liked"):
            parent_card._is_liked = liked
        
        from pyrolist.ui.design import tokens
        from pyrolist.ui.design.icons import Icon
        from PySide6.QtGui import QColor
        like_c = QColor(tokens.CURRENT.like_color)
        lr, lg, lb = like_c.red(), like_c.green(), like_c.blue()

        btn_like.setText(Icon.get("favorite"))
        if liked:
            btn_like.setStyleSheet(f"QPushButton {{ color: {tokens.CURRENT.like_color}; background: transparent; border: none; }}")
            btn_like.setFont(Icon.font(20, filled=True))
            btn_like.set_active(True)
            self.statusBar().showMessage("Añadido a Favoritas", 2000)
        else:
            btn_like.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    
                    border: none;
                    border-radius: 18px;
                }}
                QPushButton:hover {{
                    background-color: rgba({lr},{lg},{lb},0.15);
                    color: {tokens.CURRENT.like_color};
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
        self.notification_service.stop()
        if self.mpris:
            self.mpris.stop()
        if hasattr(self, 'network_monitor') and self.network_monitor:
            self._run_async(self.network_monitor.stop())

    async def _initialize(self) -> None:
        self._restore_playback_session()
        await self._navigate("home")
        if self.settings.player.resume_on_startup and self.queue.current:
            self._update_queue_panel()
            item = self.queue.current
            self.mini_player.update_track_info(item.title, item.artist, item.thumbnail_url)
            self.now_playing_screen.update_track_info(item.title, item.artist, item.thumbnail_url)
            self._run_async(self._resume_playback_after_startup())

    async def _resume_playback_after_startup(self) -> None:
        try:
            await self._play_current()
            if self._resume_position_ms > 0:
                await self.player.seek(self._resume_position_ms)
        except Exception as e:
            logger.warning(f"Failed to resume playback session: {e}")

    def _restore_playback_session(self) -> None:
        try:
            if not self._queue_state_file.exists():
                return
            with open(self._queue_state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            restored = PlayQueue.from_dict(data.get("queue", {}))
            if not restored.items:
                return
            self.queue = restored
            self.queue.shuffle_enabled = self.settings.player.shuffle_enabled
            try:
                self.queue.repeat_mode = RepeatMode(self.settings.player.repeat_mode)
            except ValueError:
                self.queue.repeat_mode = RepeatMode.OFF
            self.mpris.queue = self.queue
            self.mini_player.queue = self.queue
            self.now_playing_screen.queue = self.queue
            self.settings.last_video_id = data.get("last_video_id") or self.queue.current.video_id
            self._resume_position_ms = int(data.get("position_ms", 0))
            logger.info(f"Restored playback queue with {len(self.queue.items)} items")
        except Exception as e:
            logger.warning(f"Failed to restore playback session: {e}")

    def _save_playback_session(self) -> None:
        try:
            current = self.queue.current
            self.settings.last_video_id = current.video_id if current else None
            payload = {
                "queue": self.queue.to_dict(),
                "last_video_id": self.settings.last_video_id,
                "position_ms": self.player.status.position_ms,
            }
            self._queue_state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._queue_state_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            from pyrolist.config.paths import AppDirs
            self.settings.save(AppDirs.settings_file)
        except Exception as e:
            logger.warning(f"Failed to save playback session: {e}")

    async def _check_updates(self) -> None:
        """Comprueba actualizaciones silenciosamente al arrancar."""
        from pyrolist.utils.updater import check_for_updates
        from pyrolist.ui.widgets.update_dialog import UpdateDialog

        release = await check_for_updates()
        if release:
            # Mostrar el diálogo de actualización (no bloquea la UI)
            dlg = UpdateDialog(release, parent=self)
            dlg.show()

    async def _navigate(self, path: str) -> None:
        # Parse route and query
        route = path
        query = ""
        if "?" in path:
            route, query = path.split("?", 1)

        self._current_route = route
        if self._should_show_offline_state(route):
            self._offline_blocked_path = path
            self._show_offline_state(route)
            return
        if route not in self.ONLINE_ROUTES:
            self._offline_blocked_path = None
            
        if route != "search":
            self.search_bar.input.blockSignals(True)
            self.search_bar.input.clear()
            self.search_bar.input.blockSignals(False)
            
        index = self.ROUTES.get(route, 0)
        self._set_stack_index(index)
        
        # Wait for the FadeStackedWidget animation (260ms) to complete before blocking thread with UI updates
        import asyncio
        await asyncio.sleep(0.3)
        await self._load_screen_with_query(route, query)

    def _should_show_offline_state(self, route: str) -> bool:
        return (
            route in self.ONLINE_ROUTES
            and hasattr(self, "network_monitor")
            and not self.network_monitor.is_connected
        )

    def _show_offline_state(self, route: str) -> None:
        self._current_route = route
        self._set_stack_index(self._offline_state_index)

    def resolve_and_navigate_artist(self, artist_name: str) -> None:
        """Dynamically searches for the artist by name and navigates to their profile."""
        if not artist_name:
            return

        async def _resolve_task():
            try:
                results = await self.yt.search(artist_name, filter="artists")
                if results and len(results) > 0:
                    artist_id = results[0].get("browseId")
                    if artist_id:
                        self._navigate_to(f"artist?id={artist_id}")
                        return
                # Fallback to search screen if no ID found
                self._navigate_to(f"search?query={artist_name}")
            except Exception as e:
                from loguru import logger
                logger.error(f"Failed to resolve artist '{artist_name}': {e}")
                self._navigate_to(f"search?query={artist_name}")

        import asyncio
        asyncio.create_task(_resolve_task())

    def resolve_and_navigate_album(self, album_name: str) -> None:
        if not album_name:
            return

        async def _resolve_task():
            try:
                results = await self.yt.search(album_name, filter="albums")
                if results:
                    album_id = results[0].get("browseId")
                    if album_id:
                        self._navigate_to(f"album?id={album_id}")
                        return
                self._navigate_to(f"search?query={album_name}")
            except Exception as e:
                logger.error(f"Failed to resolve album '{album_name}': {e}")
                self._navigate_to(f"search?query={album_name}")

        asyncio.create_task(_resolve_task())

    def _navigate_to(self, path: str) -> None:
        if hasattr(self, '_current_nav_task') and self._current_nav_task and not self._current_nav_task.done():
            self._current_nav_task.cancel()
        self._current_nav_task = self._run_async(self._navigate(path))

    async def _load_screen_with_query(self, route: str, query: str) -> None:
        if route == "playlist" and "id=" in query:
            playlist_id = query.split("=", 1)[1]
            await self.playlist_screen.load(playlist_id)
        elif route == "album" and "id=" in query:
            album_id = query.split("=", 1)[1]
            await self.album_screen.load(album_id)
        elif route == "artist" and "id=" in query:
            artist_id = query.split("=", 1)[1]
            await self.artist_screen.load(artist_id)
        elif route == "search" and "query=" in query:
            query_param = query.split("=", 1)[1]
            self.search_bar.input.blockSignals(True)
            self.search_bar.input.setText(query_param)
            self.search_bar.input.blockSignals(False)
            await self.search_screen.search(query_param)
        else:
            await self._load_screen(route)

    def _show_login(self) -> None:
        if not self.yt or not self.yt.is_authenticated:
            from pyrolist.ui.dialogs.login_dialog import WebLoginDialog
            dialog = WebLoginDialog(self)
            dialog.login_successful.connect(self._on_web_login_success)
            dialog.exec()
        else:
            self._navigate_to("settings")

    def _on_web_login_success(self, avatar_url: str) -> None:
        self._on_auth_changed(True, avatar_url)
        self._navigate_to("home")

    def _on_auth_changed(self, is_authenticated: bool, avatar_url: str = "") -> None:
        if is_authenticated:
            self.notification_service.start()
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
                    except Exception as e:
                        logger.debug(f"Could not read saved user profile after login: {e}")
            
            self.sidebar.update_auth_state(True, name, avatar_url)
            logger.info(f"Post-login: yt client propagated, name={name}, avatar={avatar_url}")
            
            # Auto-refresh home and library if we just logged in
            self.home_screen.force_reload()
            self._run_async(self.library_screen.load())
        else:
            self.notification_service.stop()
            # Delete user profile file on logout so it's clean
            from pyrolist.config.paths import AppDirs
            profile_file = AppDirs.config / "user_profile.json"
            if profile_file.exists():
                try:
                    profile_file.unlink()
                except Exception as e:
                    logger.warning(f"Could not delete saved user profile on logout: {e}")
            
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
            if "?" in query:
                self._navigate_to(query)
                return
            self._navigate_to(f"search?query={query}")

    def _set_stack_index(self, index: int) -> None:
        current = self.stack.currentIndex()
        if current != index:
            self._nav_history.append(current)
            # Keep history bounded
            if len(self._nav_history) > 30:
                self._nav_history = self._nav_history[-20:]
        if hasattr(self.stack, "setCurrentIndexAnimated"):
            self.stack.setCurrentIndexAnimated(index)
        else:
            self.stack.setCurrentIndex(index)
        # Update mini player expand icon based on whether we're on now_playing
        self._update_expand_icon()

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

        if not queue_items:
            self._run_async(self._fetch_and_populate_auto_queue(video_id))

    async def _fetch_and_populate_auto_queue(self, video_id: str) -> None:
        """Fetch watch playlist and populate the rest of the queue automatically."""
        if not video_id or video_id == "local" or len(video_id) < 5:
            return
        if hasattr(self, 'network_monitor') and not self.network_monitor.is_connected:
            return

        try:
            logger.info(f"Fetching automatic watch playlist for song {video_id}")
            watch = await self.yt.get_watch_playlist(video_id, limit=25)
            tracks = watch.get('tracks', [])
            
            # Verify the current track hasn't changed while we were fetching
            current_item = self.queue.current
            if not current_item or current_item.video_id != video_id:
                logger.info("Song changed during auto queue fetch. Discarding results.")
                return

            new_items = []
            for t in tracks:
                vid = t.get("videoId")
                if not vid or vid == video_id:
                    continue
                
                # Check if this song is already in the queue to avoid duplication
                if any(x.video_id == vid for x in self.queue.items):
                    continue

                # Extract artist names robustly
                artists = t.get("artists", [])
                artist_name = "Unknown Artist"
                if isinstance(artists, list) and artists:
                    names = []
                    for a in artists:
                        if isinstance(a, dict):
                            names.append(a.get("name", ""))
                        else:
                            names.append(str(a))
                    artist_name = ", ".join(filter(None, names)) or artist_name
                elif artists:
                    artist_name = str(artists)
                    
                # Extract thumbnail robustly
                t_thumbnail_url = ""
                thumbnails = t.get("thumbnail") or t.get("thumbnails")
                if isinstance(thumbnails, list) and thumbnails:
                    t_thumbnail_url = thumbnails[0].get("url", "")
                elif isinstance(thumbnails, dict):
                    t_thumbnail_url = thumbnails.get("url", "")
                    
                # Extract album robustly
                album_name = ""
                album_data = t.get("album")
                if isinstance(album_data, dict):
                    album_name = album_data.get("name", "")
                elif album_data:
                    album_name = str(album_data)

                # Duration
                dur_ms = 0
                for key in ('duration_seconds', 'durationSeconds', 'lengthSeconds'):
                    if key in t:
                        try:
                            dur_ms = int(t.get(key)) * 1000
                            break
                        except (TypeError, ValueError):
                            pass

                new_items.append(QueueItem(
                    video_id=vid,
                    title=t.get("title", "Unknown"),
                    artist=artist_name,
                    album=album_name,
                    duration_ms=dur_ms,
                    thumbnail_url=t_thumbnail_url,
                ))

            if new_items:
                logger.info(f"Adding {len(new_items)} related items to the auto-generated queue.")
                for ni in new_items:
                    self.queue.add_to_end(ni)
                self._update_queue_panel()
        except Exception as e:
            logger.warning(f"Failed to generate automatic queue: {e}")

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
        if hasattr(self, "tray") and self.tray:
            self.tray.update_track_info(item.title, item.artist)

        async def _check_liked_state() -> None:
            try:
                from pyrolist.db.repository import SongRepository
                repo = SongRepository()
                song = await repo.get_song(item.video_id)
                liked = song.is_liked if song else False
                self.now_playing_screen.set_liked_state(liked)
            except Exception as e:
                logger.error(f"Error checking liked state in _play_current: {e}")
        self._run_async(_check_liked_state())

        self._current_play_id += 1
        play_id = self._current_play_id
        self._stream_recovery_attempts.discard(item.video_id)
        self._reset_lastfm_scrobble_state(item)

        # Immediate visual feedback for lyrics and related suggestions
        self.now_playing_screen.set_lyrics_loading()
        self.now_playing_screen.set_related([], None)
        self._run_async(self._load_lyrics(item, play_id))
        self._run_async(self._load_related(item, play_id))
        if not item.is_local:
            if hasattr(self, 'network_monitor') and not self.network_monitor.is_connected:
                logger.warning(f"Offline: cannot play non-local song {item.title}")
                from pyrolist.ui.widgets.toast import ToastNotification
                ToastNotification.show(self, f"Sin conexión: '{item.title}' no está descargada.", "error")
                await self.player.stop()
                return

        if item.is_local:
            logger.info(f"Playing local track: {item.title}")
            if self.settings.player.crossfade_enabled and self.player.status.state == PlayerState.PLAYING:
                await self.crossfade_manager.fade_out(self.player, duration_sec=1.2)
            
            success = await self.player.play_url(item.local_path, item.video_id)
            if success:
                self._run_async(self._save_play_history(item))
                if self.settings.player.crossfade_enabled:
                    self._run_async(self.crossfade_manager.fade_in(self.player, self.settings.player.volume, duration_sec=1.2))
                if self.scrobbler:
                    await self.scrobbler.update_now_playing(
                        item.artist, item.title, item.album
                    )
                if self.discord:
                    await self.discord.update(
                        item.title, item.artist, item.album, True, item.thumbnail_url
                    )
                if self.mpris:
                    self.mpris.update_metadata(
                        item.title, item.artist, item.album,
                        item.duration_ms * 1000, item.thumbnail_url, item.video_id
                    )
            else:
                await self._handle_playback_failure(item, "No se pudo reproducir el archivo local.")
            return

        # Check if preloaded stream_url is already valid
        import time
        has_preloaded = False
        if item.stream_url and hasattr(item, 'stream_expires_at') and time.time() < item.stream_expires_at:
            has_preloaded = True

        if has_preloaded:
            logger.info(f"Playing preloaded: {item.title}")
            if item.stream_url:
                if self.settings.player.crossfade_enabled and self.player.status.state == PlayerState.PLAYING:
                    await self.crossfade_manager.fade_out(self.player, duration_sec=1.2)

                success = await self.player.play_url(item.stream_url, item.video_id)
                if success:
                    self._run_async(self._save_play_history(item))
                    if self.settings.player.crossfade_enabled:
                        self._run_async(self.crossfade_manager.fade_in(self.player, self.settings.player.volume, duration_sec=1.2))
                else:
                    logger.error(f"Player failed for preloaded {item.title}, trying alternative format...")
                    alt_url = await self.extractor.get_alternative_stream(item.video_id)
                    if alt_url:
                        logger.info(f"Retrying with alternative format")
                        success = await self.player.play_url(alt_url, item.video_id)
                        if success and self.settings.player.crossfade_enabled:
                            self._run_async(self.crossfade_manager.fade_in(self.player, self.settings.player.volume, duration_sec=1.2))
                    if not success:
                        await self._handle_playback_failure(item, "No se pudo reproducir la pista. Saltando a la siguiente.")
                        return
            else:
                logger.error(f"No stream URL for preloaded {item.title}")
                await self._handle_playback_failure(item, "No se pudo obtener una URL de reproduccion.")
                return

            if getattr(getattr(self.settings, 'network', None), 'preload_next', True):
                self._run_async(self._preload_next())

            if self.scrobbler:
                await self.scrobbler.update_now_playing(
                    item.artist, item.title, item.album
                )
            if self.discord:
                await self.discord.update(
                    item.title, item.artist, item.album, True, item.thumbnail_url
                )
            if self.mpris:
                self.mpris.update_metadata(
                    item.title, item.artist, item.album,
                    item.duration_ms * 1000, item.thumbnail_url, item.video_id
                )
            return

        try:
            logger.info(f"Getting fresh stream for: {item.title}")
            
            import asyncio
            extraction_task = asyncio.create_task(self.extractor.get_stream_info(item.video_id))
            
            # Give immediate feedback by stopping or fading out the old song
            if self.player.status.state == PlayerState.PLAYING:
                if self.settings.player.crossfade_enabled:
                    await self.crossfade_manager.fade_out(self.player, duration_sec=1.2)
                else:
                    await self.player.stop()

            stream_info = await extraction_task
            
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
                    if not success:
                        await self._handle_playback_failure(item, "No se pudo reproducir la pista. Saltando a la siguiente.")
                        return
            else:
                logger.error(f"No stream URL for {item.title}")
                await self._handle_playback_failure(item, "No se pudo obtener una URL de reproduccion.")
                return

            if getattr(getattr(self.settings, 'network', None), 'preload_next', True):
                self._run_async(self._preload_next())

            if self.scrobbler:
                await self.scrobbler.update_now_playing(
                    item.artist, item.title, item.album
                )
            if self.discord:
                await self.discord.update(
                    item.title, item.artist, item.album, True, item.thumbnail_url
                )
            if self.mpris:
                self.mpris.update_metadata(
                    item.title, item.artist, item.album,
                    item.duration_ms * 1000, item.thumbnail_url, item.video_id
                )

        except Exception as e:
            logger.error(f"Failed to play {item.video_id}: {e}")
            await self._handle_playback_failure(item, "Error de reproduccion. Saltando a la siguiente.")

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
                # Check global lyrics cache
                from pyrolist.utils.lyrics_cache import LyricsCache
                lyrics = LyricsCache.get(item.title, item.artist)

            if not lyrics:
                if hasattr(self, 'network_monitor') and not self.network_monitor.is_connected:
                    lyrics = "[Letras no disponibles sin conexión]"
                else:
                    synced = await self.lyrics_client.get_lyrics(
                        item.title, item.artist, item.album
                    )
                    lyrics = synced
                    if lyrics:
                        from pyrolist.utils.lyrics_cache import LyricsCache
                        LyricsCache.save(item.title, item.artist, str(lyrics))
            
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
            if hasattr(self, 'network_monitor') and not self.network_monitor.is_connected:
                if self._current_play_id == play_id:
                    self.now_playing_screen.set_related([], None)
                return
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
        if not next_item:
            return
            
        # 1. Preload artwork
        if next_item.thumbnail_url:
            try:
                from pyrolist.utils.image_cache import ImageCache
                cache = ImageCache()
                await cache.download(next_item.thumbnail_url)
            except Exception as e:
                logger.debug(f"Failed to preload next artwork: {e}")

        # 2. Preload stream URL
        if not next_item.stream_url:
            try:
                import time
                info = await self.extractor.get_stream_info(next_item.video_id)
                next_item.stream_url = info.get("url", "")
                if next_item.stream_url:
                    next_item.stream_expires_at = time.time() + 21600
            except Exception as e:
                logger.debug(f"Failed to preload next stream: {e}")

    async def _advance_queue(self) -> None:
        item = self.queue.advance()
        if item:
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
        except Exception as e:
            logger.debug(f"Could not query VLC playing state: {e}")

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
        if self.mpris:
            self.mpris.emit_seeked(position_ms)
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
        item = self.queue.jump_to(index)
        if item:
            self._update_queue_panel()
            self._run_async(self._play_current())

    def _show_full_player(self) -> None:
        now_playing_index = self.ROUTES.get("now_playing", 8)
        if self.stack.currentIndex() == now_playing_index:
            # Already on NowPlaying — go back
            self._go_back()
        else:
            self._navigate_to("now_playing")

    def _go_back(self) -> None:
        """Navigate back to the previous screen in the history stack."""
        if hasattr(self, '_current_nav_task') and self._current_nav_task and not self._current_nav_task.done():
            self._current_nav_task.cancel()
            
        if self._nav_history:
            prev_index = self._nav_history.pop()
            if hasattr(self.stack, "setCurrentIndexAnimated"):
                self.stack.setCurrentIndexAnimated(prev_index)
            else:
                self.stack.setCurrentIndex(prev_index)
            self._update_expand_icon()
        else:
            # Fallback to home
            self._navigate_to("home")

    def _update_expand_icon(self) -> None:
        """Toggle the mini player expand icon between up/down chevron."""
        from pyrolist.ui.design.icons import Icon
        if hasattr(self, 'mini_player') and hasattr(self.mini_player, 'btn_expand'):
            now_playing_index = self.ROUTES.get("now_playing", 8)
            if self.stack.currentIndex() == now_playing_index:
                self.mini_player.btn_expand.setText(Icon.get("expand_more"))
            else:
                self.mini_player.btn_expand.setText(Icon.get("expand_less"))

    def _on_settings_changed(self, settings: AppSettings) -> None:
        self.settings = settings
        if hasattr(self, 'now_playing_screen'):
            self.now_playing_screen.settings = settings
            self.now_playing_screen.update_lyrics_style()
        from pyrolist.config.paths import AppDirs
        settings.save(AppDirs.settings_file)

        # Update Last.fm scrobbler dynamically
        if settings.integrations.lastfm_enabled and settings.integrations.lastfm_session_key:
            if not getattr(self, 'scrobbler', None) or getattr(self, '_lastfm_session_key', None) != settings.integrations.lastfm_session_key:
                try:
                    self.scrobbler = LastFmScrobbler(
                        settings.integrations.lastfm_api_key,
                        settings.integrations.lastfm_api_secret,
                        settings.integrations.lastfm_session_key,
                    )
                    self._lastfm_session_key = settings.integrations.lastfm_session_key
                    logger.info("Dynamic Last.fm scrobbler initialized/updated")
                except Exception as e:
                    logger.error(f"Failed to initialize dynamic scrobbler: {e}")
        else:
            self.scrobbler = None
            self._lastfm_session_key = None
        
        # Update player volume
        if hasattr(self, 'player'):
            self.player.set_volume(settings.player.volume)
            
        # Update player equalizer
        if settings.equalizer.enabled:
            self.player.apply_equalizer(
                settings.equalizer.preamp,
                settings.equalizer.bands,
            )
        else:
            self.player.reset_equalizer()
        
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
                if self.sleep_timer.is_running:
                    self.sleep_timer.cancel()
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
            self.theme_manager.apply(theme_mode, accent)

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

    def _show_and_activate(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_tray_quit(self) -> None:
        self._force_close = True
        self.close()

    def closeEvent(self, event) -> None:
        self._save_playback_session()
        self._save_window_state()
        if getattr(self.settings.player, "minimize_to_tray", True) and not getattr(self, "_force_close", False) and hasattr(self, "tray") and self.tray.isVisible():
            self.hide()
            event.ignore()
        else:
            active_downloads = getattr(self.download_manager, "active_count", 0)
            if active_downloads > 0:
                result = QMessageBox.question(
                    self,
                    "Descargas activas",
                    f"Hay {active_downloads} descargas en curso o en cola. ¿Salir de todos modos?",
                    QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes,
                    QMessageBox.StandardButton.Cancel,
                )
                if result != QMessageBox.StandardButton.Yes:
                    event.ignore()
                    return
            if self.settings.player.stop_on_close:
                self._run_async(self.player.stop())
            self.player.release()
            if self.discord:
                self._run_async(self.discord.disconnect())
            if hasattr(self, "tray") and self.tray:
                self.tray.hide()
            event.accept()
