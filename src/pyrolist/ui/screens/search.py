"""
Search results screen with category filter chips (Canciones, Artistas,
Álbumes, Playlists) — inspired by YT Music's results layout.

Receives a query from GlobalSearchBar, fetches *all* result types once,
then lets the user filter by category using the chip bar.
"""

from functools import partial
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QPushButton, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
from qasync import asyncSlot
from loguru import logger
import asyncio

from pyrolist.ui.widgets.song_card import SongCard
from pyrolist.ui.widgets.album_card import AlbumCard
from pyrolist.ui.widgets.artist_card import ArtistCard
from pyrolist.ui.widgets.playlist_card import PlaylistCard
from pyrolist.ui.widgets.ripple_button import RippleButton
from pyrolist.ui.widgets.skeleton_loader import SkeletonListLoader
from pyrolist.ui.design.icons import Icon


# ---------------------------------------------------------------------------
# Filter chip widget
# ---------------------------------------------------------------------------
class _FilterChip(QPushButton):
    """A rounded toggle chip for category filtering."""

    def __init__(self, text: str, category: str):
        super().__init__(text)
        self.category = category
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(34)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self._apply_style()

    def _apply_style(self):
        from pyrolist.ui.design import tokens
        accent = tokens.CURRENT.accent
        self.setStyleSheet(f"""
            QPushButton {{
                background: {tokens.CURRENT.bg_surface};
                color: {tokens.CURRENT.text_secondary};
                border: 1px solid {tokens.CURRENT.border};
                border-radius: 17px;
                padding: 0 20px;
                font-size: 13px;
                font-family: Inter;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {tokens.CURRENT.bg_elevated};
                color: {tokens.CURRENT.text_primary};
            }}
            QPushButton:checked {{
                background: {accent};
                color: {tokens.CURRENT.text_on_accent};
                border: 1px solid {accent};
            }}
        """)

    def changeEvent(self, event):
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.Type.PaletteChange:
            if not getattr(self, '_in_style_change', False):
                self._in_style_change = True
                try:
                    self._apply_style()
                finally:
                    self._in_style_change = False
        super().changeEvent(event)


# ---------------------------------------------------------------------------
# Top Result card (the prominent first result)
# ---------------------------------------------------------------------------
class _TopResultCard(QWidget):
    """A prominent card shown for the top search result."""
    clicked = Signal()

    def __init__(self, title, artist, result_type, thumbnail_url="", on_play=None):
        super().__init__()
        self._on_play = on_play
        self._has_thumbnail = bool(thumbnail_url)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(120)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 16, 24, 16)
        lay.setSpacing(20)

        # Thumbnail
        self.thumb = QLabel()
        self.thumb.setFixedSize(88, 88)
        self.thumb.setScaledContents(True)
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setText(Icon.get("library_music"))
        self.thumb.setFont(Icon.font(40))
        lay.addWidget(self.thumb)

        if thumbnail_url:
            asyncio.ensure_future(self._load_thumb(thumbnail_url))

        # Info column
        info = QVBoxLayout()
        info.setSpacing(4)
        info.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.type_lbl = QLabel(result_type)
        self.type_lbl.setFont(QFont("Inter", 10, QFont.Weight.Medium))
        info.addWidget(self.type_lbl)

        self.title_lbl = QLabel(title)
        self.title_lbl.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        info.addWidget(self.title_lbl)

        self.artist_lbl = QLabel(artist)
        self.artist_lbl.setFont(QFont("Inter", 12))
        info.addWidget(self.artist_lbl)

        lay.addLayout(info, stretch=1)

        # Play button
        play_btn = RippleButton("Reproducir", "primary")
        play_btn.setFixedHeight(40)
        if on_play:
            play_btn.clicked.connect(on_play)
        lay.addWidget(play_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        self._apply_style()
        self._update_child_styles()

    def _apply_style(self):
        from pyrolist.ui.design import tokens
        accent = tokens.CURRENT.accent
        self.setStyleSheet(f"""
            _TopResultCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {tokens.CURRENT.bg_surface}, stop:1 {tokens.CURRENT.bg_elevated});
                border-radius: 16px;
                border: 1px solid {tokens.CURRENT.border};
            }}
            _TopResultCard:hover {{
                border: 1px solid {accent};
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {tokens.CURRENT.bg_elevated}, stop:1 {tokens.CURRENT.bg_high});
            }}
        """)

    def _update_child_styles(self):
        from pyrolist.ui.design import tokens
        if not self._has_thumbnail:
            self.thumb.setStyleSheet(f"background: {tokens.CURRENT.bg_surface}; color: {tokens.CURRENT.text_disabled}; border-radius: 12px;")
        else:
            self.thumb.setStyleSheet(f"border-radius: 12px; background: transparent;")
        self.type_lbl.setStyleSheet(f"color: {tokens.CURRENT.accent}; background: transparent;")
        self.title_lbl.setStyleSheet(f"color: {tokens.CURRENT.text_primary}; background: transparent;")
        self.artist_lbl.setStyleSheet(f"color: {tokens.CURRENT.text_secondary}; background: transparent;")

    def changeEvent(self, event):
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.Type.PaletteChange:
            if not getattr(self, '_in_style_change', False):
                self._in_style_change = True
                try:
                    self._apply_style()
                    self._update_child_styles()
                finally:
                    self._in_style_change = False
        super().changeEvent(event)

    async def _load_thumb(self, url):
        from pyrolist.utils.image_cache import ImageCache
        cache = ImageCache()
        path = await cache.download(url)
        if path:
            pix = QPixmap(str(path))
            if not pix.isNull():
                self.thumb.setPixmap(pix)
                self.thumb.setText("")
                self._has_thumbnail = True
                self._update_child_styles()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self._on_play:
            self._on_play()
        super().mousePressEvent(e)


# ---------------------------------------------------------------------------
# SearchScreen
# ---------------------------------------------------------------------------
class SearchScreen(QWidget):
    CATEGORIES = [
        ("Canciones", "song"),
        ("Artistas", "artist"),
        ("Álbumes", "album"),
        ("Playlists", "playlist"),
    ]

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
        self._current_query = ""
        self._all_results: list = []       # raw API results
        self._active_category = "song"     # default filter
        self._build_ui()

    def _handle_download(self, vid, title, artist, thumb):
        self.download_requested.emit(vid, title, artist, thumb)

    # ------------------------------------------------------------------
    # Play handler
    # ------------------------------------------------------------------
    def _handle_play(self, video_id, title, artists, thumbnail_url):
        logger.info(f"_handle_play: video_id={repr(video_id)}, title={title[:30]}")
        try:
            if not video_id:
                logger.error("Empty video_id!")
                return
            artist_str = (
                ", ".join([a.get("name", "") for a in artists])
                if isinstance(artists, list)
                else str(artists)
            )
            if self.on_play_song:
                self.on_play_song(video_id, title, artist_str, "", 0, thumbnail_url)
        except Exception as e:
            logger.error(f"Play error: {e}")

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # -- Header area (query label + chip bar) --
        self.header_widget = QWidget()
        header_lay = QVBoxLayout(self.header_widget)
        header_lay.setContentsMargins(24, 16, 24, 12)
        header_lay.setSpacing(12)

        self._query_label = QLabel("")
        self._query_label.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        self._query_label.setVisible(False)
        header_lay.addWidget(self._query_label)

        # Chip row
        chip_row = QHBoxLayout()
        chip_row.setSpacing(8)
        self._chips: dict[str, _FilterChip] = {}

        for label, cat in self.CATEGORIES:
            chip = _FilterChip(label, cat)
            chip.toggled.connect(partial(self._on_chip_toggled, cat))
            chip_row.addWidget(chip)
            self._chips[cat] = chip

        chip_row.addStretch()
        header_lay.addLayout(chip_row)

        root.addWidget(self.header_widget)

        # -- Scrollable results area (must be created BEFORE chips are checked) --
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("background: transparent; border: none;")

        self._results_widget = QWidget()
        self._content_wrapper_layout = QVBoxLayout(self._results_widget)
        self._content_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        
        self._results_layout = QVBoxLayout()
        self._results_layout.setSpacing(16)
        self._results_layout.setContentsMargins(0, 16, 0, 16)
        
        self._content_wrapper_layout.addLayout(self._results_layout)
        self._content_wrapper_layout.addStretch()

        self._scroll.setWidget(self._results_widget)
        root.addWidget(self._scroll)

        # Default check (after results_layout exists)
        self._chips["song"].setChecked(True)
        self._update_search_screen_styles()

    def _update_search_screen_styles(self) -> None:
        from pyrolist.ui.design import tokens
        if hasattr(self, 'header_widget') and self.header_widget:
            self.header_widget.setStyleSheet(f"""
                background-color: {tokens.CURRENT.bg_base};
                border-bottom: 1px solid {tokens.CURRENT.border};
            """)
        if hasattr(self, '_query_label') and self._query_label:
            self._query_label.setStyleSheet(f"color: {tokens.CURRENT.text_primary}; background: transparent;")

    def changeEvent(self, event) -> None:
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.Type.PaletteChange:
            if not getattr(self, '_in_style_change', False):
                self._in_style_change = True
                try:
                    self._update_search_screen_styles()
                finally:
                    self._in_style_change = False
        super().changeEvent(event)

    # ------------------------------------------------------------------
    # Chip toggling
    # ------------------------------------------------------------------
    def _on_chip_toggled(self, category: str, checked: bool):
        if not checked:
            # Don't allow un-checking the only active chip
            self._chips[category].blockSignals(True)
            self._chips[category].setChecked(True)
            self._chips[category].blockSignals(False)
            return

        # Un-check all others
        for cat, chip in self._chips.items():
            if cat != category:
                chip.blockSignals(True)
                chip.setChecked(False)
                chip.blockSignals(False)

        self._active_category = category
        self._render_filtered()

    # ------------------------------------------------------------------
    # Public entry point — called from MainWindow
    # ------------------------------------------------------------------
    async def search(self, query: str):
        """Trigger a search.  Called by MainWindow when user submits."""
        if not query:
            self._clear_results()
            self._query_label.setVisible(False)
            return
        if query == self._current_query:
            return

        self._current_query = query
        self._query_label.setText(f"Resultados para \"{query}\"")
        self._query_label.setVisible(True)
        await self._do_search(query)

    @asyncSlot()
    async def _do_search(self, query: str):
        if not self.yt:
            return
        try:
            self._clear_results()
            self._results_layout.addWidget(SkeletonListLoader(row_count=6))
            
            try:
                from pyrolist.db.repository import DownloadRepository
                dl_repo = DownloadRepository()
                downloads = await dl_repo.get_downloads()
                self.downloaded_playlist_ids = {d.parent_playlist_id for d in downloads if d.parent_playlist_id}
            except Exception as e:
                logger.debug(f"Error fetching downloads: {e}")
                self.downloaded_playlist_ids = set()

            results = await self.yt.search(query, limit=40)
            self._all_results = results
            self._render_filtered()
        except Exception as e:
            logger.error(f"Search error: {e}")

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def _clear_results(self):
        while self._results_layout.count():
            item = self._results_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _render_filtered(self):
        self._clear_results()
        cat = self._active_category

        # Partition results
        filtered = []
        for item in self._all_results:
            rt = item.get("resultType", "")
            if cat == "song" and rt in ("song", "video", ""):
                filtered.append(item)
            elif cat == "album" and rt == "album":
                filtered.append(item)
            elif cat == "artist" and rt == "artist":
                filtered.append(item)
            elif cat == "playlist" and rt == "playlist":
                filtered.append(item)

        if not filtered:
            from pyrolist.ui.design import tokens
            empty = QLabel("No se encontraron resultados en esta categoría")
            empty.setFont(QFont("Inter", 13))
            empty.setStyleSheet(f"color: {tokens.CURRENT.text_secondary}; padding: 32px; background: transparent;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._results_layout.addWidget(empty)
            self._results_layout.addStretch()
            return

        # Top result card (for songs only, first item)
        if cat == "song" and filtered:
            top = filtered[0]
            video_id = top.get("videoId", "")
            title = top.get("title", "Unknown")
            artists = top.get("artists", [])
            artist_str = (
                ", ".join([a.get("name", "") for a in artists])
                if isinstance(artists, list)
                else str(artists)
            )
            thumbnails = top.get("thumbnails", [])
            thumb_url = thumbnails[-1].get("url", "") if thumbnails else ""
            rt = top.get("resultType", "Canción")
            type_label = {"song": "Canción", "video": "Video", "": "Canción"}.get(rt, "Canción")

            top_card = _TopResultCard(
                title=title,
                artist=artist_str,
                result_type=type_label,
                thumbnail_url=thumb_url,
                on_play=lambda: self._handle_play(video_id, title, artists, thumb_url) if video_id else None
            )
            self._results_layout.addWidget(top_card)
            self._results_layout.addSpacing(8)
            remaining = filtered[1:]
        else:
            remaining = filtered

        # Render the rest
        for item in remaining:
            card = self._make_card(item, cat)
            if card:
                self._results_layout.addWidget(card)

        self._results_layout.addStretch()

    def _make_card(self, item: dict, cat: str) -> QWidget | None:
        thumbnails = item.get("thumbnails", [])
        thumb_url = thumbnails[-1].get("url", "") if thumbnails else ""

        if cat == "song":
            video_id = item.get("videoId", "")
            if not video_id:
                return None
            title = item.get("title", "Unknown")
            artists = item.get("artists", [])
            artist_names = (
                ", ".join([a.get("name", "") for a in artists])
                if isinstance(artists, list)
                else str(artists)
            )
            duration = item.get("duration", 0)
            if isinstance(duration, (int, float)) and duration > 0:
                minutes = int(duration) // 60
                seconds = int(duration) % 60
                duration_str = f"{minutes}:{seconds:02d}"
            elif isinstance(duration, str):
                duration_str = duration
            else:
                duration_str = ""

            card = SongCard(
                title=title,
                artist=artist_names,
                duration=duration_str,
                thumbnail_url=thumb_url,
                on_play=lambda: self._handle_play(video_id, title, artists, thumb_url),
                video_id=video_id
            )
            card.download_requested.connect(lambda *a: self.download_requested.emit(*a))
            card.play_next_requested.connect(lambda *a: self.play_next_requested.emit(*a))
            card.add_to_queue_requested.connect(lambda *a: self.add_to_queue_requested.emit(*a))
            card.like_requested.connect(lambda *a: self.like_requested.emit(*a))
            card.add_to_playlist_requested.connect(lambda *a: self.add_to_playlist_requested.emit(*a))
            card.delete_download_requested.connect(lambda *a: self.delete_download_requested.emit(*a))
            return card

        elif cat == "album":
            title = item.get("title", "Unknown")
            artists = item.get("artists", [])
            artist_names = (
                ", ".join([a.get("name", "") for a in artists])
                if isinstance(artists, list)
                else str(artists)
            )
            return AlbumCard(title=title, artist=artist_names, thumbnail_url=thumb_url)

        elif cat == "artist":
            name = item.get("artist", item.get("name", "Unknown"))
            return ArtistCard(name=name, thumbnail_url=thumb_url)

        elif cat == "playlist":
            title = item.get("title", "Unknown")
            playlist_id = item.get("playlistId", "")
            return PlaylistCard(
                title=title,
                thumbnail_url=thumb_url,
                is_downloaded=playlist_id in getattr(self, "downloaded_playlist_ids", set())
            )

        return None

    async def load(self):
        pass
