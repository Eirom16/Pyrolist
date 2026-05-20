from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QScrollArea, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
import asyncio
from pyrolist.utils.image_cache import ImageCache
from pyrolist.audio.player import PlayerState
from pyrolist.utils.time_utils import format_duration_short
from pyrolist.ui.design.icons import Icon
from pyrolist.ui.design.fonts import AppFont
from pyrolist.ui.widgets.icon_button import IconButton
from pyrolist.ui.widgets.animated_progress import AnimatedProgressBar

_image_cache = ImageCache()

class NowPlayingScreen(QWidget):
    download_requested = Signal(str, str, str, str)
    play_next_requested = Signal(str, str, str, str)
    add_to_queue_requested = Signal(str, str, str, str)
    like_requested = Signal(str, object)
    add_to_playlist_requested = Signal(str, str)
    delete_download_requested = Signal(str)

    def __init__(self, player, queue, yt_client, play_queue_item_cb, settings=None):
        super().__init__()
        self.player = player
        self.queue = queue
        self.yt = yt_client
        self.play_queue_item_cb = play_queue_item_cb
        self.settings = settings
        self._is_playing = False
        self._build_ui()

    def _make_btn(self, icon_name, size=24, color="#FFFFFF", btn_size=40, primary=False):
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
        # Style border and background cleanly without inline color hardcoding
        btn.setStyleSheet("QPushButton { border: none; background: transparent; }")
        return btn

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(40)

        # Left Side (Artwork & Details + Controls)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.artwork = QLabel()
        self.artwork.setFixedSize(360, 360)
        self.artwork.setObjectName("nowPlayingArtwork")
        self.artwork.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.artwork.setText(Icon.get("library_music"))
        self.artwork.setFont(Icon.font(120))
        left_layout.addWidget(self.artwork, alignment=Qt.AlignmentFlag.AlignCenter)

        left_layout.addSpacing(24)

        # ── Song info row ──
        info_layout = QHBoxLayout()
        
        text_info = QVBoxLayout()
        self.title = QLabel("No hay canción")
        self.title.setFont(QFont("Inter", 22, QFont.Weight.Bold))
        self.title.setObjectName("nowPlayingTitle")
        self.title.setWordWrap(True)
        text_info.addWidget(self.title)

        self.artist = QLabel("")
        self.artist.setFont(QFont("Inter", 14))
        self.artist.setObjectName("nowPlayingArtist")
        text_info.addWidget(self.artist)
        
        info_layout.addLayout(text_info)
        info_layout.addStretch()

        # Like button
        self.btn_like = IconButton(size=48, active_color="#F472B6")
        self.btn_like.setText(Icon.get("favorite"))
        self.btn_like.setFont(Icon.font(28, filled=False))
        self.btn_like.setObjectName("nowPlayingLikeBtn")
        self.btn_like.clicked.connect(self._on_like_clicked)
        info_layout.addWidget(self.btn_like)

        left_layout.addLayout(info_layout)
        left_layout.addSpacing(16)

        # ── Progress bar with time labels ──
        progress_row = QHBoxLayout()
        progress_row.setSpacing(10)

        self.time_current = QLabel("0:00")
        self.time_current.setFont(AppFont.mono(11))
        self.time_current.setObjectName("nowPlayingTimeCurrent")
        self.time_current.setFixedWidth(40)
        self.time_current.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        progress_row.addWidget(self.time_current)

        self.progress = AnimatedProgressBar()
        self.progress.setEnabled(False)
        self.progress.on_seek = self._on_seek
        progress_row.addWidget(self.progress, stretch=1)

        self.time_total = QLabel("0:00")
        self.time_total.setFont(AppFont.mono(11))
        self.time_total.setObjectName("nowPlayingTimeTotal")
        self.time_total.setFixedWidth(40)
        self.time_total.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        progress_row.addWidget(self.time_total)

        left_layout.addLayout(progress_row)
        left_layout.addSpacing(12)

        # ── Playback controls ──
        controls = QHBoxLayout()
        controls.setSpacing(16)
        controls.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_shuffle = self._make_btn("shuffle", 22, "#6B6B9B", 40)
        self.btn_shuffle.setObjectName("nowPlayingShuffleBtn")
        self.btn_shuffle.clicked.connect(self._on_shuffle)
        controls.addWidget(self.btn_shuffle)

        self.btn_prev = self._make_btn("skip_previous", 30, "#F1F0FF", 48)
        self.btn_prev.setObjectName("nowPlayingPrevBtn")
        self.btn_prev.clicked.connect(self._on_prev)
        controls.addWidget(self.btn_prev)

        self.btn_play = self._make_btn("play_arrow", 38, "#0A0A14", 60, primary=True)
        self.btn_play.clicked.connect(self._on_play_pause)
        controls.addWidget(self.btn_play)

        self.btn_next = self._make_btn("skip_next", 30, "#F1F0FF", 48)
        self.btn_next.setObjectName("nowPlayingNextBtn")
        self.btn_next.clicked.connect(self._on_next)
        controls.addWidget(self.btn_next)

        self.btn_repeat = self._make_btn("repeat", 22, "#6B6B9B", 40)
        self.btn_repeat.setObjectName("nowPlayingRepeatBtn")
        self.btn_repeat.clicked.connect(self._on_repeat)
        controls.addWidget(self.btn_repeat)

        left_layout.addLayout(controls)
        left_layout.addStretch()

        # Right Side (Tabs: Queue, Lyrics, Related)
        right_panel = QWidget()
        right_panel.setFixedWidth(460)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("nowPlayingTabs")


        # Tab: Queue (A CONTINUACIÓN)
        from pyrolist.ui.widgets.queue_panel import QueuePanel
        self.queue_tab = QueuePanel(self.play_queue_item_cb)
        self.tabs.addTab(self.queue_tab, "A CONTINUACIÓN")

        # Tab: Lyrics (LETRA)
        self.lyrics_scroll = QScrollArea()
        self.lyrics_scroll.setWidgetResizable(True)
        self.lyrics_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lyrics_scroll.setStyleSheet("background: transparent; border: none;")
        
        self.lyrics_container = QWidget()
        self.lyrics_layout = QVBoxLayout(self.lyrics_container)
        self.lyrics_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.lyrics_layout.setContentsMargins(0, 16, 0, 80)
        self.lyrics_scroll.setWidget(self.lyrics_container)
        
        self._lyric_lines = []
        self._current_lyric_index = -1
        
        # Initial message
        msg = QLabel("Reproduce una canción para ver las letras")
        msg.setFont(QFont("Inter", 14))
        from pyrolist.ui.design import tokens
        msg.setStyleSheet(f"color: {tokens.CURRENT.text_disabled};")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lyrics_layout.addWidget(msg)
        
        self.tabs.addTab(self.lyrics_scroll, "LETRA")

        # Tab: Related (SIMILARES)
        self.related_scroll = QScrollArea()
        self.related_scroll.setWidgetResizable(True)
        self.related_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.related_scroll.setStyleSheet("background: transparent; border: none;")
        self.related_container = QWidget()
        self.related_layout = QVBoxLayout(self.related_container)
        self.related_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.related_scroll.setWidget(self.related_container)
        
        self.tabs.addTab(self.related_scroll, "SIMILARES")

        right_layout.addWidget(self.tabs)

        layout.addWidget(left_panel)
        layout.addWidget(right_panel)

    def _on_like_clicked(self):
        """Toggle like for the currently playing song."""
        video_id = self.player.status.current_video_id
        if video_id:
            main = self._find_main_window()
            if main:
                main._on_like_requested(video_id, self.btn_like)

    # ── Playback control handlers ──
    def _on_play_pause(self):
        main = self._find_main_window()
        if main:
            main._on_play_pause()

    def _on_prev(self):
        main = self._find_main_window()
        if main:
            main._on_prev()

    def _on_next(self):
        main = self._find_main_window()
        if main:
            main._on_next()

    def _on_seek(self, pct: float):
        main = self._find_main_window()
        if main and self.player.status.duration_ms > 0:
            ms = int(pct * self.player.status.duration_ms)
            main._on_seek(ms)

    def _on_shuffle(self):
        from pyrolist.ui.design import tokens
        from pyrolist.audio.queue import RepeatMode
        is_shuffled = self.queue.toggle_shuffle()
        color = tokens.CURRENT.accent if is_shuffled else tokens.CURRENT.text_disabled
        self.btn_shuffle.setStyleSheet(f"QPushButton {{ color: {color}; border: none; background: transparent; }}")

    def _on_repeat(self):
        from pyrolist.ui.design import tokens
        from pyrolist.audio.queue import RepeatMode
        mode = self.queue.toggle_repeat()
        if mode == RepeatMode.OFF:
            self.btn_repeat.setText(Icon.get("repeat"))
            self.btn_repeat.setStyleSheet(f"QPushButton {{ color: {tokens.CURRENT.text_disabled}; border: none; background: transparent; }}")
        elif mode == RepeatMode.ALL:
            self.btn_repeat.setText(Icon.get("repeat"))
            self.btn_repeat.setStyleSheet(f"QPushButton {{ color: {tokens.CURRENT.accent}; border: none; background: transparent; }}")
        elif mode == RepeatMode.ONE:
            self.btn_repeat.setText(Icon.get("repeat_one"))
            self.btn_repeat.setStyleSheet(f"QPushButton {{ color: {tokens.CURRENT.accent}; border: none; background: transparent; }}")

    def update_shuffle_repeat_state(self):
        """Sync button visuals with current queue state."""
        from pyrolist.ui.design import tokens
        from pyrolist.audio.queue import RepeatMode
        color = tokens.CURRENT.accent if self.queue.shuffle_enabled else tokens.CURRENT.text_disabled
        self.btn_shuffle.setStyleSheet(f"QPushButton {{ color: {color}; border: none; background: transparent; }}")
        mode = self.queue.repeat_mode
        if mode == RepeatMode.OFF:
            self.btn_repeat.setText(Icon.get("repeat"))
            self.btn_repeat.setStyleSheet(f"QPushButton {{ color: {tokens.CURRENT.text_disabled}; border: none; background: transparent; }}")
        elif mode == RepeatMode.ALL:
            self.btn_repeat.setText(Icon.get("repeat"))
            self.btn_repeat.setStyleSheet(f"QPushButton {{ color: {tokens.CURRENT.accent}; border: none; background: transparent; }}")
        elif mode == RepeatMode.ONE:
            self.btn_repeat.setText(Icon.get("repeat_one"))
            self.btn_repeat.setStyleSheet(f"QPushButton {{ color: {tokens.CURRENT.accent}; border: none; background: transparent; }}")

    def _find_main_window(self):
        w = self.parent()
        while w:
            if hasattr(w, '_on_play_pause'):
                return w
            w = w.parent() if hasattr(w, 'parent') and callable(w.parent) else None
        return None

    def update_track_info(self, title: str, artist: str, thumbnail_url: str):
        self.title.setText(title)
        self.artist.setText(artist)
        self.progress.setEnabled(True)
        
        if thumbnail_url:
            asyncio.ensure_future(self._load_thumbnail(thumbnail_url))
        else:
            self.artwork.setPixmap(QPixmap())
            self.artwork.setText(Icon.get("library_music"))
            self.artwork.setFont(Icon.font(120))
            from pyrolist.ui.design import tokens
            self.artwork.setStyleSheet(f"background: {tokens.CURRENT.bg_high}; color: {tokens.CURRENT.text_disabled}; border-radius: 24px;")

    def update_state(self, status):
        self._is_playing = status.state == PlayerState.PLAYING
        self.btn_play.setText(Icon.get("pause" if self._is_playing else "play_arrow"))

    def update_position(self, position_ms: int, duration_ms: int):
        if duration_ms > 0:
            self.progress.set_value(position_ms / duration_ms)
        self.time_current.setText(format_duration_short(position_ms))
        self.time_total.setText(format_duration_short(duration_ms))
        self._highlight_lyric(position_ms)
        
    def set_lyrics_loading(self):
        self.lyrics_scroll.verticalScrollBar().setValue(0)
        while self.lyrics_layout.count():
            item = self.lyrics_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        self._lyric_lines.clear()
        self._current_lyric_index = -1
        
        loading_lbl = QLabel("Buscando letras...")
        loading_lbl.setFont(QFont("Inter", 14))
        loading_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        from pyrolist.ui.design import tokens
        loading_lbl.setStyleSheet(f"color: {tokens.CURRENT.text_disabled}; margin-top: 32px;")
        self.lyrics_layout.addWidget(loading_lbl)

    def set_lyrics(self, lyrics):
        self.lyrics_scroll.verticalScrollBar().setValue(0)
        while self.lyrics_layout.count():
            item = self.lyrics_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        self._lyric_lines.clear()
        self._current_lyric_index = -1
        
        if not lyrics:
            no_lyrics = QLabel("No hay letras disponibles")
            no_lyrics.setFont(QFont("Inter", 14))
            no_lyrics.setAlignment(Qt.AlignmentFlag.AlignCenter)
            from pyrolist.ui.design import tokens
            no_lyrics.setStyleSheet(f"color: {tokens.CURRENT.text_disabled};")
            self.lyrics_layout.addWidget(no_lyrics)
            return

        import re
        if isinstance(lyrics, str):
            lines = lyrics.strip().split('\n')
        elif isinstance(lyrics, list):
            lines = lyrics
        else:
            lines = [str(lyrics)]
            
        font_size = 18
        alignment = "center"
        line_spacing = 1.5
        if self.settings:
            font_size = self.settings.subtitles.font_size
            alignment = self.settings.subtitles.alignment
            line_spacing = self.settings.subtitles.line_spacing
            
        align_flag = Qt.AlignmentFlag.AlignCenter
        if alignment == "left":
            align_flag = Qt.AlignmentFlag.AlignLeft
        elif alignment == "right":
            align_flag = Qt.AlignmentFlag.AlignRight
            
        padding = int(line_spacing * 4)

        for line_text in lines:
            clean = line_text.strip()
            if not clean:
                spacer = QLabel("")
                spacer.setFixedHeight(16)
                self.lyrics_layout.addWidget(spacer)
                self._lyric_lines.append((-1, spacer))
                continue
            
            timestamp_ms = -1
            match = re.match(r'^\[(\d{2,}):(\d{2}(?:\.\d+)?)\](.*)', clean)
            if match:
                mins = int(match.group(1))
                secs = float(match.group(2))
                timestamp_ms = int((mins * 60 + secs) * 1000)
                clean = match.group(3).strip()
            
            if not clean:
                continue
            
            lbl = QLabel(clean)
            lbl.setFont(QFont("Inter", font_size - 2, QFont.Weight.Bold))
            lbl.setAlignment(align_flag)
            from pyrolist.ui.design import tokens
            lbl.setStyleSheet(f"color: {tokens.CURRENT.text_disabled}; background: transparent; padding: {padding}px 0;")
            lbl.setWordWrap(True)
            self.lyrics_layout.addWidget(lbl)
            self._lyric_lines.append((timestamp_ms, lbl))
            
        self.lyrics_layout.addStretch()

    def _highlight_lyric(self, position_ms: int):
        if not hasattr(self, '_lyric_lines') or not self._lyric_lines:
            return

        adjusted_position = position_ms
        if self.settings:
            adjusted_position += self.settings.subtitles.delay_ms

        active_idx = -1
        for i, (ts, lbl) in enumerate(self._lyric_lines):
            if ts != -1 and adjusted_position >= ts:
                active_idx = i

        if active_idx != -1 and active_idx != self._current_lyric_index:
            from pyrolist.ui.design import tokens
            
            font_size = 18
            line_spacing = 1.5
            glow = True
            auto_scroll = True
            animation_style = "glow"
            if self.settings:
                font_size = self.settings.subtitles.font_size
                line_spacing = self.settings.subtitles.line_spacing
                glow = self.settings.subtitles.glow_effect
                auto_scroll = self.settings.subtitles.auto_scroll
                animation_style = self.settings.subtitles.animation_style
                
            padding = int(line_spacing * 4)

            if self._current_lyric_index != -1:
                old_ts, old_lbl = self._lyric_lines[self._current_lyric_index]
                old_lbl.setStyleSheet(f"color: {tokens.CURRENT.text_disabled}; background: transparent; padding: {padding}px 0;")
                old_lbl.setFont(QFont("Inter", font_size - 2, QFont.Weight.Bold))
                old_lbl.setGraphicsEffect(None)
            
            new_ts, new_lbl = self._lyric_lines[active_idx]
            new_lbl.setStyleSheet(f"color: {tokens.CURRENT.text_primary}; background: transparent; padding: {padding}px 0;")
            new_lbl.setFont(QFont("Inter", font_size, QFont.Weight.Black))
            
            if glow:
                from PySide6.QtWidgets import QGraphicsDropShadowEffect
                from PySide6.QtGui import QColor
                shadow = QGraphicsDropShadowEffect(new_lbl)
                shadow.setBlurRadius(10)
                shadow.setColor(QColor(tokens.CURRENT.accent))
                shadow.setOffset(0, 0)
                new_lbl.setGraphicsEffect(shadow)
            
            self._current_lyric_index = active_idx
            
            if auto_scroll:
                scroll_bar = self.lyrics_scroll.verticalScrollBar()
                target_y = new_lbl.y() - (self.lyrics_scroll.height() / 2) + (new_lbl.height() / 2)
                
                if animation_style == "none":
                    scroll_bar.setValue(int(max(0, target_y)))
                else:
                    from PySide6.QtCore import QPropertyAnimation, QEasingCurve
                    self._scroll_anim = QPropertyAnimation(scroll_bar, b"value")
                    self._scroll_anim.setDuration(400)
                    self._scroll_anim.setStartValue(scroll_bar.value())
                    self._scroll_anim.setEndValue(int(max(0, target_y)))
                    self._scroll_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
                    self._scroll_anim.start()

    def update_lyrics_style(self):
        if not hasattr(self, '_lyric_lines') or not self._lyric_lines:
            return
            
        font_size = 18
        alignment = "center"
        line_spacing = 1.5
        if self.settings:
            font_size = self.settings.subtitles.font_size
            alignment = self.settings.subtitles.alignment
            line_spacing = self.settings.subtitles.line_spacing
            
        align_flag = Qt.AlignmentFlag.AlignCenter
        if alignment == "left":
            align_flag = Qt.AlignmentFlag.AlignLeft
        elif alignment == "right":
            align_flag = Qt.AlignmentFlag.AlignRight
            
        padding = int(line_spacing * 4)
        from pyrolist.ui.design import tokens
        
        for idx, (ts, lbl) in enumerate(self._lyric_lines):
            if ts == -1:
                continue
            lbl.setAlignment(align_flag)
            if idx == self._current_lyric_index:
                lbl.setStyleSheet(f"color: {tokens.CURRENT.text_primary}; background: transparent; padding: {padding}px 0;")
                lbl.setFont(QFont("Inter", font_size, QFont.Weight.Black))
                if self.settings and self.settings.subtitles.glow_effect:
                    from PySide6.QtWidgets import QGraphicsDropShadowEffect
                    from PySide6.QtGui import QColor
                    shadow = QGraphicsDropShadowEffect(lbl)
                    shadow.setBlurRadius(10)
                    shadow.setColor(QColor(tokens.CURRENT.accent))
                    shadow.setOffset(0, 0)
                    lbl.setGraphicsEffect(shadow)
                else:
                    lbl.setGraphicsEffect(None)
            else:
                lbl.setStyleSheet(f"color: {tokens.CURRENT.text_disabled}; background: transparent; padding: {padding}px 0;")
                lbl.setFont(QFont("Inter", font_size - 2, QFont.Weight.Bold))
                lbl.setGraphicsEffect(None)

    async def _load_thumbnail(self, url: str):
        # Request a higher-resolution thumbnail
        high_res_url = url
        if 'w120' in url:
            high_res_url = url.replace('w120', 'w544').replace('h120', 'h544')
        elif 'w226' in url:
            high_res_url = url.replace('w226', 'w544').replace('h226', 'h544')
        
        path = await _image_cache.download(high_res_url)
        if not path:
            path = await _image_cache.download(url)
        if path:
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                size = 360
                radius = 24
                pixmap = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                # Center crop
                x = (pixmap.width() - size) // 2
                y = (pixmap.height() - size) // 2
                pixmap = pixmap.copy(x, y, size, size)
                # Apply rounded rect clip
                from PySide6.QtGui import QPainter, QPainterPath
                from PySide6.QtCore import QRectF
                rounded = QPixmap(size, size)
                rounded.fill(Qt.GlobalColor.transparent)
                painter = QPainter(rounded)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                clip_path = QPainterPath()
                clip_path.addRoundedRect(QRectF(0, 0, size, size), radius, radius)
                painter.setClipPath(clip_path)
                painter.drawPixmap(0, 0, pixmap)
                painter.end()
                self.artwork.setPixmap(rounded)
                self.artwork.setText("")
                self.artwork.setStyleSheet("background: transparent;")

    def set_related(self, tracks, play_callback):
        """Populate the SIMILARES tab with related songs."""
        from functools import partial
        from pyrolist.ui.widgets.song_card import SongCard
        
        self.related_scroll.verticalScrollBar().setValue(0)
        while self.related_layout.count():
            item = self.related_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not tracks:
            msg = QLabel("No hay canciones similares")
            msg.setFont(QFont("Inter", 14))
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            from pyrolist.ui.design import tokens
            msg.setStyleSheet(f"color: {tokens.CURRENT.text_disabled};")
            self.related_layout.addWidget(msg)
            return

        for track in tracks[:12]:
            video_id = track.get('videoId', '')
            title = track.get('title', 'Unknown')
            artists = track.get('artists', [])
            if isinstance(artists, list):
                artist_names = ", ".join(a.get('name', '') for a in artists if isinstance(a, dict)) or 'Unknown'
            else:
                artist_names = str(artists) if artists else 'Unknown'
            
            duration = track.get('duration', track.get('length', ''))
            thumbnails = track.get('thumbnail', track.get('thumbnails', []))
            if isinstance(thumbnails, list):
                thumb_url = thumbnails[-1].get('url', '') if thumbnails else ''
            elif isinstance(thumbnails, dict):
                thumb_url = thumbnails.get('url', '')
            else:
                thumb_url = ''

            if video_id:
                on_play = None
                if play_callback:
                    on_play = partial(play_callback, video_id, title, artist_names, '', 0, thumb_url)
                
                card = SongCard(
                    title=title,
                    artist=artist_names,
                    duration=str(duration) if duration else '',
                    thumbnail_url=thumb_url,
                    on_play=on_play,
                    video_id=video_id,
                )
                card.download_requested.connect(lambda *a: self.download_requested.emit(*a))
                card.play_next_requested.connect(lambda *a: self.play_next_requested.emit(*a))
                card.add_to_queue_requested.connect(lambda *a: self.add_to_queue_requested.emit(*a))
                card.like_requested.connect(lambda *a: self.like_requested.emit(*a))
                card.add_to_playlist_requested.connect(lambda *a: self.add_to_playlist_requested.emit(*a))
                card.delete_download_requested.connect(lambda *a: self.delete_download_requested.emit(*a))
                self.related_layout.addWidget(card)

        self.related_layout.addStretch()
