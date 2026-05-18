from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QScrollArea, QFrame, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QPixmap, QColor, QLinearGradient, QPainter, QPaintEvent
from pyrolist.utils.time_utils import format_duration, format_duration_short
import asyncio
from pyrolist.ui.design.icons import Icon
from pyrolist.ui.design.fonts import AppFont
from pyrolist.ui.widgets.animated_progress import AnimatedProgressBar
from pyrolist.ui.widgets.icon_button import IconButton
from pyrolist.ui.widgets.scrolling_label import ScrollingLabel
from pyrolist.utils.image_cache import ImageCache


class FullPlayerDialog(QDialog):
    def __init__(self, player, queue, lyrics_client, parent):
        super().__init__(parent)
        self.player = player
        self.queue = queue
        self.lyrics_client = lyrics_client
        self._is_playing = False
        self._lyric_labels: list[QLabel] = []
        self._current_lyric_index = -1
        self._build_ui()
        self._connect_signals()
        self._fade_in()

    def _fade_in(self):
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(300)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: self.setGraphicsEffect(None))
        anim.start()

    def _build_ui(self):
        self.setWindowTitle("Reproductor Completo")
        self.resize(900, 650)
        self.setObjectName("fullPlayerBg")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Main content area
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(40, 32, 40, 24)
        content_layout.setSpacing(40)

        # ── Left column: artwork + info + controls ──
        left = QVBoxLayout()
        left.setSpacing(20)
        left.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Close button
        close_row = QHBoxLayout()
        close_btn.setObjectName("fullPlayerCloseBtn")
        close_btn.setStyleSheet("QPushButton { border: none; background: transparent; }")
        close_btn.clicked.connect(self._close_animated)
        close_row.addStretch()
        close_row.addWidget(close_btn)
        left.addLayout(close_row)

        # Artwork
        self.artwork = QLabel()
        self.artwork.setFixedSize(300, 300)
        self.artwork.setScaledContents(True)
        self.artwork.setText(Icon.get("music_note"))
        self.artwork.setFont(Icon.font(80))
        self.artwork.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.artwork.setObjectName("fullPlayerArtwork")
        left.addWidget(self.artwork, alignment=Qt.AlignmentFlag.AlignCenter)

        # Title (scrolling for long names)
        self.title = ScrollingLabel("No hay canción")
        self.title.setFont(AppFont.title(18))
        from pyrolist.ui.design import tokens
        self.title.setColor(tokens.CURRENT.text_primary)
        self.title.setFixedWidth(300)
        left.addWidget(self.title, alignment=Qt.AlignmentFlag.AlignCenter)

        # Artist
        self.artist = QLabel("")
        self.artist.setFont(AppFont.label(13))
        self.artist.setObjectName("fullPlayerArtist")
        self.artist.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left.addWidget(self.artist, alignment=Qt.AlignmentFlag.AlignCenter)

        # Progress bar
        self.progress = AnimatedProgressBar()
        self.progress.setFixedWidth(300)
        self.progress.on_seek = self._on_seek
        left.addWidget(self.progress, alignment=Qt.AlignmentFlag.AlignCenter)

        # Time labels
        time_row = QHBoxLayout()
        self.time_current = QLabel("0:00")
        self.time_current.setFont(AppFont.mono(10))
        self.time_current.setObjectName("fullPlayerTimeCurrent")
        self.time_total = QLabel("0:00")
        self.time_total.setFont(AppFont.mono(10))
        self.time_total.setObjectName("fullPlayerTimeTotal")
        time_row.addWidget(self.time_current)
        time_row.addStretch()
        time_row.addWidget(self.time_total)
        time_container = QWidget()
        time_container.setFixedWidth(300)
        time_container.setLayout(time_row)
        left.addWidget(time_container, alignment=Qt.AlignmentFlag.AlignCenter)

        # Playback controls
        controls = QHBoxLayout()
        controls.setSpacing(12)
        controls.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_shuffle = self._make_btn("shuffle", 20, "#6B6B9B", 36)
        self.btn_shuffle.setObjectName("fullPlayerShuffleBtn")
        controls.addWidget(self.btn_shuffle)

        self.btn_prev = self._make_btn("skip_previous", 28, "#F1F0FF", 44)
        self.btn_prev.setObjectName("fullPlayerPrevBtn")
        self.btn_prev.clicked.connect(self._on_prev)
        controls.addWidget(self.btn_prev)

        self.btn_play = self._make_btn("play_arrow", 36, "#0A0A14", 56, primary=True)
        self.btn_play.clicked.connect(self._on_play_pause)
        controls.addWidget(self.btn_play)

        self.btn_next = self._make_btn("skip_next", 28, "#F1F0FF", 44)
        self.btn_next.setObjectName("fullPlayerNextBtn")
        self.btn_next.clicked.connect(self._on_next)
        controls.addWidget(self.btn_next)

        self.btn_repeat = self._make_btn("repeat", 20, "#6B6B9B", 36)
        self.btn_repeat.setObjectName("fullPlayerRepeatBtn")
        controls.addWidget(self.btn_repeat)

        left.addLayout(controls)
        left.addStretch()
        content_layout.addLayout(left)

        # ── Right column: lyrics ──
        right = QVBoxLayout()
        right.setSpacing(12)

        lyrics_header = QLabel("Letra")
        lyrics_header.setFont(AppFont.heading(18))
        lyrics_header.setObjectName("fullPlayerLyricsHeader")
        right.addWidget(lyrics_header)

        self.lyrics_area = QScrollArea()
        self.lyrics_area.setWidgetResizable(True)
        self.lyrics_area.setFrameShape(QFrame.Shape.NoFrame)
        self.lyrics_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.lyrics_content = QWidget()
        self.lyrics_content.setStyleSheet("background: transparent;")
        self.lyrics_content_layout = QVBoxLayout(self.lyrics_content)
        self.lyrics_content_layout.setSpacing(6)
        self.lyrics_content_layout.setContentsMargins(0, 8, 0, 80)

        # Initial "no lyrics" placeholder
        no_lyrics = QLabel(Icon.get("lyrics"))
        no_lyrics.setFont(Icon.font(48))
        no_lyrics.setAlignment(Qt.AlignmentFlag.AlignCenter)
        from pyrolist.ui.design import tokens
        no_lyrics.setStyleSheet(f"color: {tokens.CURRENT.text_disabled}; padding: 40px;")
        self.lyrics_content_layout.addWidget(no_lyrics)

        msg = QLabel("Reproduce una canción para ver las letras")
        msg.setFont(AppFont.body(14))
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet(f"color: {tokens.CURRENT.text_disabled};")
        self.lyrics_content_layout.addWidget(msg)
        self.lyrics_content_layout.addStretch()

        self.lyrics_area.setWidget(self.lyrics_content)
        right.addWidget(self.lyrics_area)

        content_layout.addLayout(right, stretch=1)
        layout.addWidget(content)

    @staticmethod
    def _make_btn(icon_name, size=24, color="#FFFFFF", btn_size=40, primary=False):
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
        btn.setStyleSheet("QPushButton { border: none; background: transparent; }")
        return btn

    def _connect_signals(self):
        self.player.on("state_changed", self._on_state_changed)
        self.player.on("position_changed", self._on_position_changed)
        self.player.on("track_ended", self._on_track_ended)

    def _on_play_pause(self):
        main = self.parent()
        if main and hasattr(main, '_on_play_pause'):
            main._on_play_pause()

    def _on_prev(self):
        main = self.parent()
        if main and hasattr(main, '_on_prev'):
            main._on_prev()

    def _on_next(self):
        main = self.parent()
        if main and hasattr(main, '_on_next'):
            main._on_next()

    def _on_seek(self, value):
        main = self.parent()
        if main and hasattr(main, '_on_seek') and self.player.status.duration_ms > 0:
            ms = int(value * self.player.status.duration_ms)
            main._on_seek(ms)

    def _on_state_changed(self, status):
        from pyrolist.audio.player import PlayerState
        self._is_playing = status.state == PlayerState.PLAYING
        self.btn_play.setText(Icon.get("pause" if self._is_playing else "play_arrow"))

    def _on_position_changed(self, status):
        if self.player.status.duration_ms > 0:
            self.progress.set_value(status.position_ms / status.duration_ms)
        self.time_current.setText(format_duration_short(status.position_ms))
        self.time_total.setText(format_duration_short(status.duration_ms))
        # Highlight current lyric line
        self._highlight_lyric(status.position_ms)

    def _on_track_ended(self, status):
        pass

    def update_track(self, title, artist, thumbnail_url):
        self.title.setText(title)
        self.artist.setText(artist)

    async def show_track(self, item):
        if item:
            self.title.setText(item.title)
            self.artist.setText(item.artist)

            if item.thumbnail_url:
                cache = ImageCache()
                path = await cache.download(item.thumbnail_url)
                if path:
                    pixmap = QPixmap(str(path))
                    if not pixmap.isNull():
                        scaled = pixmap.scaled(
                            300, 300,
                            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                        self.artwork.setPixmap(scaled)
                        self.artwork.setText("")
                        self.artwork.setStyleSheet("background: transparent; border-radius: 20px;")

            asyncio.ensure_future(self._load_lyrics(item.title, item.artist))

    async def _load_lyrics(self, title, artist):
        # Clear existing lyrics
        while self.lyrics_content_layout.count():
            item = self.lyrics_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Show loading state
        loading = QLabel("Buscando letras...")
        loading.setFont(AppFont.body(14))
        loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        from pyrolist.ui.design import tokens
        loading.setStyleSheet(f"color: {tokens.CURRENT.text_secondary}; padding: 40px;")
        self.lyrics_content_layout.addWidget(loading)

        try:
            lyrics = await self.lyrics_client.get_lyrics(title, artist)
            
            # Clear loading indicator
            while self.lyrics_content_layout.count():
                item = self.lyrics_content_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            self._lyric_labels.clear()
            self._current_lyric_index = -1

            if lyrics:
                import re
                
                # Lyrics can be a string or a list of lines
                if isinstance(lyrics, str):
                    lines = lyrics.strip().split('\n')
                elif isinstance(lyrics, list):
                    lines = lyrics
                else:
                    lines = [str(lyrics)]
                
                self._lyric_lines = [] # List of (timestamp_ms, QLabel)
                
                for line_text in lines:
                    clean = line_text.strip()
                    if not clean:
                        spacer = QLabel("")
                        spacer.setFixedHeight(16)
                        self.lyrics_content_layout.addWidget(spacer)
                        self._lyric_lines.append((-1, spacer))
                        continue
                    
                    timestamp_ms = -1
                    # Match LRC timestamp like [00:12.34] or [01:23.456]
                    match = re.match(r'^\[(\d{2,}):(\d{2}(?:\.\d+)?)\](.*)', clean)
                    if match:
                        mins = int(match.group(1))
                        secs = float(match.group(2))
                        timestamp_ms = int((mins * 60 + secs) * 1000)
                        clean = match.group(3).strip()
                    
                    if not clean:
                        continue
                    
                    lbl = QLabel(clean)
                    lbl.setFont(AppFont.title(16)) # Use title font for better readability
                    from pyrolist.ui.design import tokens
                    lbl.setStyleSheet(f"color: {tokens.CURRENT.text_disabled}; background: transparent; padding: 4px 0;")
                    lbl.setWordWrap(True)
                    self.lyrics_content_layout.addWidget(lbl)
                    self._lyric_lines.append((timestamp_ms, lbl))
            else:
                # No lyrics found
                icon_lbl = QLabel(Icon.get("lyrics"))
                icon_lbl.setFont(Icon.font(48))
                icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                from pyrolist.ui.design import tokens
                icon_lbl.setStyleSheet(f"color: {tokens.CURRENT.border}; padding: 30px 0 10px 0;")
                self.lyrics_content_layout.addWidget(icon_lbl)

                no_lyrics = QLabel("No hay letras disponibles")
                no_lyrics.setFont(AppFont.body(14))
                no_lyrics.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_lyrics.setStyleSheet(f"color: {tokens.CURRENT.text_disabled};")
                self.lyrics_content_layout.addWidget(no_lyrics)
        except Exception:
            while self.lyrics_content_layout.count():
                item = self.lyrics_content_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            no_lyrics = QLabel("Error al buscar letras")
            no_lyrics.setFont(AppFont.body(14))
            no_lyrics.setAlignment(Qt.AlignmentFlag.AlignCenter)
            from pyrolist.ui.design import tokens
            no_lyrics.setStyleSheet(f"color: {tokens.CURRENT.error};")
            self.lyrics_content_layout.addWidget(no_lyrics)

        self.lyrics_content_layout.addStretch()

    def _highlight_lyric(self, position_ms: int):
        """Highlight the current lyric line based on playback position."""
        if not hasattr(self, '_lyric_lines') or not self._lyric_lines:
            return

        active_idx = -1
        for i, (ts, lbl) in enumerate(self._lyric_lines):
            if ts != -1 and position_ms >= ts:
                active_idx = i

        if active_idx != -1 and active_idx != self._current_lyric_index:
            from pyrolist.ui.design import tokens
            # Revert old
            if self._current_lyric_index != -1:
                old_ts, old_lbl = self._lyric_lines[self._current_lyric_index]
                old_lbl.setStyleSheet(f"color: {tokens.CURRENT.text_disabled}; background: transparent; padding: 4px 0;")
                old_lbl.setFont(AppFont.title(16))
            
            # Highlight new
            new_ts, new_lbl = self._lyric_lines[active_idx]
            new_lbl.setStyleSheet(f"color: {tokens.CURRENT.text_primary}; background: transparent; padding: 4px 0;")
            new_lbl.setFont(AppFont.heading(18)) # Bigger for active
            
            self._current_lyric_index = active_idx
            
            # Scroll to active line with an animated scroll
            scroll_bar = self.lyrics_area.verticalScrollBar()
            target_y = new_lbl.y() - (self.lyrics_area.height() / 2) + (new_lbl.height() / 2)
            
            # Create property animation for smooth scroll
            from PySide6.QtCore import QPropertyAnimation, QEasingCurve
            self._scroll_anim = QPropertyAnimation(scroll_bar, b"value")
            self._scroll_anim.setDuration(400)
            self._scroll_anim.setStartValue(scroll_bar.value())
            self._scroll_anim.setEndValue(int(max(0, target_y)))
            self._scroll_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
            self._scroll_anim.start()

    def _close_animated(self):
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(200)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)
        anim.finished.connect(self.close)
        anim.start()
