import sys

def patch():
    with open('src/pyrolist/ui/main_window.py', 'r') as f:
        content = f.read()

    # Remove the early connections
    bad_conn = """        # Connect queue panel artist
        self.queue_panel.artist_clicked.connect(self.resolve_and_navigate_artist)

        # Connect player artists
        self.mini_player.artist_clicked.connect(self.resolve_and_navigate_artist)
        if hasattr(self, 'full_player') and self.full_player:
            self.full_player.artist_clicked.connect(self.resolve_and_navigate_artist)"""
    content = content.replace(bad_conn, "")

    # Add them after initialization
    good_conn_target = """        if hasattr(self.now_playing_screen, 'queue_tab'):
            self.now_playing_screen.queue_tab.like_requested.connect(self._on_like_requested)"""
            
    good_conn_new = """        if hasattr(self.now_playing_screen, 'queue_tab'):
            self.now_playing_screen.queue_tab.like_requested.connect(self._on_like_requested)
            
        # Connect queue panel artist
        if hasattr(self, 'queue_panel'):
            self.queue_panel.artist_clicked.connect(self.resolve_and_navigate_artist)

        # Connect player artists
        if hasattr(self, 'mini_player'):
            self.mini_player.artist_clicked.connect(self.resolve_and_navigate_artist)
        if hasattr(self, 'full_player') and self.full_player:
            self.full_player.artist_clicked.connect(self.resolve_and_navigate_artist)"""
            
    content = content.replace(good_conn_target, good_conn_new)

    with open('src/pyrolist/ui/main_window.py', 'w') as f:
        f.write(content)

patch()
