from functools import partial
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QGraphicsOpacityEffect
from qasync import asyncSlot
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Signal
from loguru import logger
from pyrolist.ui.widgets.song_card import SongCard


class HistoryScreen(QWidget):
    download_requested = Signal(str, str, str, str)
    play_next_requested = Signal(str, str, str, str)
    add_to_queue_requested = Signal(str, str, str, str)
    like_requested = Signal(str, object)
    add_to_playlist_requested = Signal(str, str)
    delete_download_requested = Signal(str)

    def __init__(self, yt_client, on_play_song):
        super().__init__()
        self.yt = yt_client
        self.on_play_song = on_play_song
        self._build_ui()

    def _connect_card_signals(self, card):
        card.download_requested.connect(lambda *a: self.download_requested.emit(*a))
        card.play_next_requested.connect(lambda *a: self.play_next_requested.emit(*a))
        card.add_to_queue_requested.connect(lambda *a: self.add_to_queue_requested.emit(*a))
        card.like_requested.connect(lambda *a: self.like_requested.emit(*a))
        card.add_to_playlist_requested.connect(lambda *a: self.add_to_playlist_requested.emit(*a))
        card.delete_download_requested.connect(lambda *a: self.delete_download_requested.emit(*a))

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)

        from pyrolist.ui.design import tokens
        header = QLabel("Historial")
        header.setFont(QFont("Inter", 24, QFont.Weight.Bold))
        header.setStyleSheet(f"")
        layout.addWidget(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        self.content_widget = QWidget()
        self._content_wrapper_layout = QVBoxLayout(self.content_widget)
        self._content_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(16)
        self.content_layout.setContentsMargins(24, 0, 24, 24)
        
        self._content_wrapper_layout.addLayout(self.content_layout)
        self._content_wrapper_layout.addStretch()
        
        self.scroll.setWidget(self.content_widget)
        layout.addWidget(self.scroll)

    def _format_duration(self, ms):
        if not ms:
            return ""
        seconds = ms // 1000
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins}:{secs:02d}"

    def _handle_play(self, video_id, title, artists, thumbnail_url=""):
        try:
            if self.on_play_song:
                self.on_play_song(video_id, title, artists, "", 0, thumbnail_url)
        except Exception as e:
            logger.error(f"Play error: {e}")

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

    async def load(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Show loading skeleton
        from pyrolist.ui.widgets.skeleton_loader import SkeletonListLoader
        skeleton = SkeletonListLoader(row_count=5)
        self.content_layout.addWidget(skeleton)

        header = QLabel("Reproducido recientemente")
        header.setFont(QFont("Inter", 16, QFont.Weight.Bold))

        # Fetch liked video IDs for heart state
        from pyrolist.db.repository import SongRepository
        liked_ids = await SongRepository().get_liked_video_ids()

        # Fetch local play history
        from pyrolist.db.repository import HistoryRepository
        repo = HistoryRepository()
        local_history = await repo.get_history(limit=50)

        # Fetch YouTube Music history if authenticated
        yt_history = []
        if self.yt and self.yt.is_authenticated:
            try:
                yt_history = await self.yt.get_history()
            except Exception as e:
                logger.error(f"Error fetching YouTube history: {e}")

        # Clear skeleton
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.content_layout.addWidget(header)

        # Merge local history and YouTube history, deduplicating by videoId
        seen_video_ids = set()
        combined_history = []

        # 1. Add local history first so it is immediately visible at the top!
        for entry, thumbnail_url in local_history:
            if entry.video_id not in seen_video_ids:
                seen_video_ids.add(entry.video_id)
                combined_history.append({
                    'videoId': entry.video_id,
                    'title': entry.title,
                    'artist': entry.artist,
                    'duration': self._format_duration(entry.duration_ms),
                    'thumbnail_url': thumbnail_url or "",
                })

        # 2. Add YouTube Music history
        for entry in yt_history:
            video_id = entry.get("videoId", "")
            if video_id and video_id not in seen_video_ids:
                seen_video_ids.add(video_id)
                artists_data = entry.get("artists", [])
                artist_names = ", ".join([a.get("name", "") for a in artists_data]) if artists_data else ""
                thumbnails = entry.get("thumbnails", [])
                thumb_url = thumbnails[-1].get("url", "") if thumbnails else ""
                duration_str = entry.get("duration", "")
                
                combined_history.append({
                    'videoId': video_id,
                    'title': entry.get("title", "Desconocido"),
                    'artist': artist_names,
                    'duration': duration_str,
                    'thumbnail_url': thumb_url,
                })

        # Render combined history
        if combined_history:
            for entry in combined_history:
                card = SongCard(
                    title=entry['title'],
                    artist=entry['artist'],
                    duration=entry['duration'],
                    thumbnail_url=entry['thumbnail_url'],
                    on_play=partial(self._handle_play, entry['videoId'], entry['title'], entry['artist'], entry['thumbnail_url']),
                    video_id=entry['videoId'],
                    is_liked=entry['videoId'] in liked_ids,
                )
                self._connect_card_signals(card)
                self.content_layout.addWidget(card)
        else:
            msg = QLabel("Tu historial está vacío\n\nLas canciones que reproduzcas aparecerán aquí")
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg.setObjectName("libraryEmptyMessage")
            self.content_layout.addWidget(msg)

        self.content_layout.addStretch()
        self._fade_in_content()

