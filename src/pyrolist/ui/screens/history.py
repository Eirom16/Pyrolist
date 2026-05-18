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
        header.setStyleSheet(f"color: {tokens.CURRENT.text_primary};")
        layout.addWidget(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        
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
        header.setStyleSheet("color: #F1F0FF;")

        has_items = False
        
        # Fetch liked video IDs for heart state
        from pyrolist.db.repository import SongRepository
        liked_ids = await SongRepository().get_liked_video_ids()

        if self.yt and self.yt.is_authenticated:
            history = await self.yt.get_history()
            # Clear skeleton
            while self.content_layout.count():
                item = self.content_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.content_layout.addWidget(header)
            if history:
                has_items = True
                for entry in history:
                    video_id = entry.get("videoId", "")
                    if not video_id:
                        continue
                    
                    title = entry.get("title", "Desconocido")
                    artists_data = entry.get("artists", [])
                    artist_names = ", ".join([a.get("name", "") for a in artists_data]) if artists_data else ""
                    
                    thumbnails = entry.get("thumbnails", [])
                    thumb_url = thumbnails[-1].get("url", "") if thumbnails else ""
                    
                    duration_str = entry.get("duration", "")
                    
                    card = SongCard(
                        title=title,
                        artist=artist_names,
                        duration=duration_str,
                        thumbnail_url=thumb_url,
                        on_play=lambda v=video_id, t=title, a=artist_names, th=thumb_url: self._handle_play(v, t, a, th),
                        video_id=video_id,
                        is_liked=video_id in liked_ids,
                    )
                    self._connect_card_signals(card)
                    self.content_layout.addWidget(card)
        
        if not has_items:
            # Clear skeleton if still showing
            while self.content_layout.count():
                item = self.content_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.content_layout.addWidget(header)
            # Fallback to local history
            from pyrolist.db.repository import HistoryRepository
            repo = HistoryRepository()
            local_history = await repo.get_history(limit=50)

            if local_history:
                has_items = True
                for entry in local_history:
                    card = SongCard(
                        title=entry.title,
                        artist=entry.artist,
                        duration=self._format_duration(entry.duration_ms),
                        on_play=lambda v=entry.video_id, t=entry.title, a=entry.artist: self._handle_play(v, t, a),
                        video_id=entry.video_id,
                        is_liked=entry.video_id in liked_ids,
                    )
                    self._connect_card_signals(card)
                    self.content_layout.addWidget(card)

        if not has_items:
            msg = QLabel("Tu historial esta vacio\n\nLas canciones que reproduzcas apareceran aqui")
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg.setObjectName("libraryEmptyMessage")
            self.content_layout.addWidget(msg)

        self.content_layout.addStretch()
        self._fade_in_content()

    def _update_history_styles(self) -> None:
        from pyrolist.ui.design import tokens
        for label in self.findChildren(QLabel):
            font_size = label.font().pointSize()
            if font_size >= 14:
                label.setStyleSheet(f"color: {tokens.CURRENT.text_primary}; background: transparent;")
            else:
                label.setStyleSheet(f"color: {tokens.CURRENT.text_secondary}; background: transparent;")

    def changeEvent(self, event) -> None:
        from PySide6.QtCore import QEvent
        if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
            if not getattr(self, '_in_style_change', False):
                self._in_style_change = True
                try:
                    self._update_history_styles()
                finally:
                    self._in_style_change = False
        super().changeEvent(event)
