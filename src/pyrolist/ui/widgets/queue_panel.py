from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PySide6.QtCore import Qt, Signal
from functools import partial
from pyrolist.utils.time_utils import format_duration_short

class QueuePanel(QWidget):
    like_requested = Signal(str, object)  # video_id, btn_like widget

    def __init__(self, on_play_item=None):
        super().__init__()
        self.on_play_item = on_play_item
        self._build_ui()

    def _build_ui(self):
        self.setObjectName("queuePanel")
        self.setStyleSheet("""
            #queuePanel {
                background-color: #13131F;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        header = QLabel("Cola de reproducción")
        header.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        self.queue_list = QWidget()
        self.queue_layout = QVBoxLayout(self.queue_list)
        self.queue_layout.setContentsMargins(0, 0, 0, 0)
        self.queue_layout.setSpacing(8)
        
        self.scroll.setWidget(self.queue_list)
        layout.addWidget(self.scroll)

    def set_queue(self, items, liked_ids=None):
        """Update the queue display. liked_ids is a set of video_ids that are liked."""
        if liked_ids is None:
            liked_ids = set()

        while self.queue_layout.count():
            item = self.queue_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, item in enumerate(items):
            from pyrolist.ui.widgets.song_card import SongCard
            duration_str = format_duration_short(item.duration_ms) if getattr(item, 'duration_ms', 0) else ""
            video_id = getattr(item, 'video_id', '')
            
            card = SongCard(
                title=item.title,
                artist=item.artist,
                duration=duration_str,
                thumbnail_url=getattr(item, 'thumbnail_url', ''),
                video_id=video_id,
                is_liked=video_id in liked_ids,
            )
            
            if self.on_play_item:
                card.clicked.connect(partial(self.on_play_item, i))
            
            # Connect like signal
            card.like_requested.connect(lambda vid, btn: self.like_requested.emit(vid, btn))
                
            self.queue_layout.addWidget(card)
            
        self.queue_layout.addStretch()