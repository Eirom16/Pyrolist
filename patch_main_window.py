import sys

def patch():
    with open('src/pyrolist/ui/main_window.py', 'r') as f:
        content = f.read()

    # 1. Initialize Notification Service
    old_init = """        self.sidebar.on_login_click.connect(self._show_login)
        self.sidebar.auth_changed.connect(self._on_auth_changed)

        if self.yt.is_authenticated:"""
    new_init = """        self.sidebar.on_login_click.connect(self._show_login)
        self.sidebar.auth_changed.connect(self._on_auth_changed)

        # Initialize Notification Service
        from pyrolist.services.notification_service import NotificationService
        self.notification_service = NotificationService(self.yt)

        if self.yt.is_authenticated:
            self.notification_service.start()"""
    content = content.replace(old_init, new_init)

    # 2. Add notification panel and connections
    old_conn = """        from pyrolist.ui.widgets.global_search import GlobalSearchBar
        self.search_bar = GlobalSearchBar(self.yt, self._play_song_sync)
        self.search_bar.search_submitted.connect(self._on_search_submitted)
        right_layout.addWidget(self.search_bar)

        # Add glassmorphic offline warning banner
        from pyrolist.ui.widgets.offline_banner import OfflineBannerWidget
        self.offline_banner = OfflineBannerWidget(self)
        right_layout.addWidget(self.offline_banner)

        self.stack = FadeStackedWidget()
        self.stack.setObjectName("screenStack")

        from pyrolist.ui.screens.welcome import WelcomeScreen"""
    new_conn = """        from pyrolist.ui.widgets.global_search import GlobalSearchBar
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

        # Connect queue panel artist
        self.queue_panel.artist_clicked.connect(self.resolve_and_navigate_artist)

        # Connect player artists
        self.mini_player.artist_clicked.connect(self.resolve_and_navigate_artist)
        if hasattr(self, 'full_player') and self.full_player:
            self.full_player.artist_clicked.connect(self.resolve_and_navigate_artist)

        from pyrolist.ui.screens.welcome import WelcomeScreen"""
    content = content.replace(old_conn, new_conn)

    # 3. Stack layout addition fix
    content = content.replace("right_layout.addWidget(self.stack)", "right_layout.addLayout(self.main_content_hbox)")

    # 4. Stop service on close
    old_close = """        if self._init_task and not self._init_task.done():
            self._init_task.cancel()
        if self.mpris:"""
    new_close = """        if self._init_task and not self._init_task.done():
            self._init_task.cancel()
        self.notification_service.stop()
        if self.mpris:"""
    content = content.replace(old_close, new_close)

    # 5. Start on auth
    old_auth = """    def _on_auth_changed(self, is_authenticated: bool, avatar_url: str = "") -> None:
        if is_authenticated:
            self.yt = YouTubeMusicClient(self.settings)"""
    new_auth = """    def _on_auth_changed(self, is_authenticated: bool, avatar_url: str = "") -> None:
        if is_authenticated:
            self.notification_service.start()
            self.yt = YouTubeMusicClient(self.settings)"""
    content = content.replace(old_auth, new_auth)

    # 6. Stop on logout
    old_logout = """            self.home_screen.force_reload()
            self._run_async(self.library_screen.load())
        else:
            # Delete user profile file on logout so it's clean"""
    new_logout = """            self.home_screen.force_reload()
            self._run_async(self.library_screen.load())
        else:
            self.notification_service.stop()
            # Delete user profile file on logout so it's clean"""
    content = content.replace(old_logout, new_logout)

    # 7. Add resolve_and_navigate_artist below _navigate_to
    old_nav = """    def _navigate_to(self, path: str) -> None:
        if path == "settings/player":"""
    new_nav = """    def resolve_and_navigate_artist(self, artist_name: str) -> None:
        \"\"\"Dynamically searches for the artist by name and navigates to their profile.\"\"\"
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

    def _navigate_to(self, path: str) -> None:
        if path == "settings/player":"""
    content = content.replace(old_nav, new_nav)

    # 8. Remove search_bar.notif_dropdown
    old_notif = """    def show_notification(self, message: str, kind: str = "info", action_text: str = None, action_callback = None):
        if hasattr(self, "search_bar"):
            self.search_bar.notif_dropdown.add_custom_notification(message, kind)

        from pyrolist.ui.widgets.toast import ToastNotification"""
    new_notif = """    def show_notification(self, message: str, kind: str = "info", action_text: str = None, action_callback = None):
        from pyrolist.ui.widgets.toast import ToastNotification"""
    content = content.replace(old_notif, new_notif)

    with open('src/pyrolist/ui/main_window.py', 'w') as f:
        f.write(content)

patch()
