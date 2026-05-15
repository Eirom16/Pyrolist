from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QSizePolicy, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, Signal, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QFont
from pyrolist.audio.player import PlayerState
from pyrolist.utils.time_utils import format_duration_short
import asyncio
from pyrolist.utils.image_cache import ImageCache
from pyrolist.ui.design.fonts import AppFont
from pyrolist.ui.design.icons import Icon
from pyrolist.ui.widgets.animated_progress import AnimatedProgressBar
from pyrolist.ui.widgets.icon_button import IconButton
from pyrolist.ui.widgets.scrolling_label import ScrollingLabel

_image_cache = ImageCache()


class MiniPlayerWidget(QWidget):
    on_expand = Signal()
    on_prev = Signal()
    on_play_pause = Signal()
    on_next = Signal()
    on_seek = Signal(int)

    def __init__(self, player, queue, on_expand, on_prev, on_play_pause, on_next, on_seek):
        super().__init__()
        self.player = player
        self.queue = queue
        self._is_playing = False
        
        # Connect signals to the passed callbacks
        self.on_expand.connect(on_expand)
        self.on_prev.connect(on_prev)
        self.on_play_pause.connect(on_play_pause)
        self.on_next.connect(on_next)
        self.on_seek.connect(on_seek)
            
        self._build_ui()

    def _build_ui(self):
        self.setObjectName("miniPlayer")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(96)

        self.setStyleSheet("""
            #miniPlayer {
                background: transparent;
            }
        """)

        # Outer layout with margins for floating effect
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 6, 12, 6)
        outer.setSpacing(0)

        # Inner card
        card = QWidget()
        card.setObjectName("playerCard")
        card.setStyleSheet("""
            #playerCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10101E, stop:1 #16162A);
                border-radius: 16px;
                border: 1px solid rgba(167,139,250,0.10);
            }
        """)

        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 16, 10)
        card_layout.setSpacing(14)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # ── Artwork ──
        self.artwork = QLabel()
        self.artwork.setFixedSize(60, 60)
        self.artwork.setScaledContents(True)
        self.artwork.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.artwork.setText(Icon.get("library_music"))
        self.artwork.setFont(Icon.font(28))
        self.artwork.setStyleSheet("""
            background: #1E1E38;
            color: #4A4A6A;
            border-radius: 10px;
        """)
        card_layout.addWidget(self.artwork)

        # ── Song info ──
        info_widget = QWidget()
        info_widget.setFixedWidth(220)
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title = ScrollingLabel("Sin reproduccion")
        self.title.setFont(AppFont.title(13))
        self.title.setColor("#F1F0FF")
        self.title.setFixedWidth(220)
        info_layout.addWidget(self.title)

        self.artist = QLabel("")
        self.artist.setFont(AppFont.label(10))
        self.artist.setStyleSheet("color: #9B9BC0;")
        self.artist.setMaximumWidth(220)
        info_layout.addWidget(self.artist)

        card_layout.addWidget(info_widget)

        # ── Progress section (time + slider + time) ──
        progress_widget = QWidget()
        progress_layout = QHBoxLayout(progress_widget)
        progress_layout.setContentsMargins(4, 0, 4, 0)
        progress_layout.setSpacing(10)
        progress_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.time_current = QLabel("0:00")
        self.time_current.setFont(AppFont.mono(10))
        self.time_current.setStyleSheet("color: #6B6B9B;")
        self.time_current.setFixedWidth(36)
        self.time_current.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        progress_layout.addWidget(self.time_current)

        self.progress = AnimatedProgressBar()
        self.progress.setEnabled(False)
        self.progress.on_seek = self._on_progress_seek
        progress_layout.addWidget(self.progress, stretch=1)

        self.time_total = QLabel("0:00")
        self.time_total.setFont(AppFont.mono(10))
        self.time_total.setStyleSheet("color: #6B6B9B;")
        self.time_total.setFixedWidth(36)
        self.time_total.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        progress_layout.addWidget(self.time_total)

        card_layout.addWidget(progress_widget, stretch=1)

        # ── Playback controls ── (larger icons, better spacing)
        controls = QHBoxLayout()
        controls.setSpacing(4)
        controls.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.btn_prev = self._make_control_btn("skip_previous", size=26, color="#F1F0FF", btn_size=40)
        self.btn_prev.clicked.connect(lambda: self.on_prev.emit())
        controls.addWidget(self.btn_prev)

        self.btn_play = self._make_control_btn("play_arrow", size=34, color="#0A0A14", btn_size=52, primary=True)
        self.btn_play.clicked.connect(lambda: self.on_play_pause.emit())
        controls.addWidget(self.btn_play)

        self.btn_next = self._make_control_btn("skip_next", size=26, color="#F1F0FF", btn_size=40)
        self.btn_next.clicked.connect(lambda: self.on_next.emit())
        controls.addWidget(self.btn_next)

        controls.addSpacing(8)

        self.btn_expand = self._make_control_btn("expand_less", size=22, color="#9B9BC0", btn_size=36)
        self.btn_expand.clicked.connect(lambda: self.on_expand.emit())
        controls.addWidget(self.btn_expand)

        card_layout.addLayout(controls)

        outer.addWidget(card)

    @staticmethod
    def _make_control_btn(icon_name, size=24, color="#FFFFFF", btn_size=40, primary=False):
        from PySide6.QtWidgets import QPushButton
        if primary:
            btn = QPushButton()
            btn.setText(Icon.get(icon_name))
            btn.setFont(Icon.font(size))
            btn.setFixedSize(btn_size, btn_size)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            radius = btn_size // 2
            btn.setObjectName("primaryPlayBtn")
            btn.setStyleSheet(f"QPushButton#primaryPlayBtn {{ border-radius: {radius}px; }}")
            return btn
            
        btn = IconButton(size=btn_size, active_color="rgba(255,255,255,0.2)")
        btn.setText(Icon.get(icon_name))
        btn.setFont(Icon.font(size))
        btn.setFixedSize(btn_size, btn_size)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # We rely on IconButton's paintEvent for the hover background.
        btn.setStyleSheet(f"QPushButton {{ color: {color}; border: none; background: transparent; }}")
        return btn

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def _on_progress_seek(self, pct: float):
        if self.player.status.duration_ms > 0:
            ms = int(pct * self.player.status.duration_ms)
            self.on_seek.emit(ms)

    def update_track_info(self, title: str, artist: str, thumbnail_url: str):
        self.title.setText(title)
        self.artist.setText(artist)
        self.progress.setEnabled(True)

        if thumbnail_url:
            asyncio.ensure_future(self._load_thumbnail(thumbnail_url))
        else:
            self.artwork.setPixmap(QPixmap())
            self.artwork.setText(Icon.get("library_music"))
            self.artwork.setFont(Icon.font(28))
            self.artwork.setStyleSheet("background: #1E1E38; color: #4A4A6A; border-radius: 10px;")

    async def _load_thumbnail(self, url: str):
        path = await _image_cache.download(url)
        if path:
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                # Fade-in transition for the new artwork
                effect = QGraphicsOpacityEffect(self.artwork)
                self.artwork.setGraphicsEffect(effect)
                
                self.artwork.setPixmap(pixmap)
                self.artwork.setText("")
                self.artwork.setStyleSheet("background: transparent; border-radius: 10px;")
                
                fade = QPropertyAnimation(effect, b"opacity", self)
                fade.setDuration(250)
                fade.setStartValue(0.0)
                fade.setEndValue(1.0)
                fade.setEasingCurve(QEasingCurve.Type.OutCubic)
                fade.finished.connect(lambda: self.artwork.setGraphicsEffect(None))
                fade.start()

    def update_state(self, status):
        """Update play/pause icon dynamically based on player state."""
        if status.state == PlayerState.PLAYING:
            self._is_playing = True
            self.btn_play.setText(Icon.get("pause"))
        else:
            self._is_playing = False
            self.btn_play.setText(Icon.get("play_arrow"))

    def update_position(self, position_ms: int, duration_ms: int):
        if duration_ms > 0:
            self.progress.set_value(position_ms / duration_ms)
        self.time_current.setText(format_duration_short(position_ms))
        self.time_total.setText(format_duration_short(duration_ms))
