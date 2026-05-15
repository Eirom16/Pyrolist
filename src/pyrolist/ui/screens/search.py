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
        self.setStyleSheet("""
            QPushButton {
                background: #2A2A3E;
                color: #CCCCDD;
                border: 1px solid #3A3A5E;
                border-radius: 17px;
                padding: 0 20px;
                font-size: 13px;
                font-family: Inter;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #3A3A5E;
                color: #FFFFFF;
            }
            QPushButton:checked {
                background: #7C4DFF;
                color: #FFFFFF;
                border: 1px solid #7C4DFF;
            }
        """)


# ---------------------------------------------------------------------------
# Top Result card (the prominent first result)
# ---------------------------------------------------------------------------
class _TopResultCard(QWidget):
    """A prominent card shown for the top search result."""
    clicked = Signal()

    def __init__(self, title, artist, result_type, thumbnail_url="", on_play=None):
        super().__init__()
        self._on_play = on_play
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(120)
        self.setStyleSheet("""
            _TopResultCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1E1E3A, stop:1 #2A2A3E);
                border-radius: 16px;
                border: 1px solid #3A3A5E;
            }
            _TopResultCard:hover {
                border: 1px solid #7C4DFF;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #252550, stop:1 #2E2E48);
            }
        """)

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
        self.thumb.setStyleSheet("background: #1E1E38; color: #4A4A6A; border-radius: 12px;")
        lay.addWidget(self.thumb)

        if thumbnail_url:
            asyncio.ensure_future(self._load_thumb(thumbnail_url))

        # Info column
        info = QVBoxLayout()
        info.setSpacing(4)
        info.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        type_lbl = QLabel(result_type)
        type_lbl.setFont(QFont("Inter", 10, QFont.Weight.Medium))
        type_lbl.setStyleSheet("color: #7C4DFF;")
        info.addWidget(type_lbl)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #FFFFFF;")
        info.addWidget(title_lbl)

        artist_lbl = QLabel(artist)
        artist_lbl.setFont(QFont("Inter", 12))
        artist_lbl.setStyleSheet("color: #888899;")
        info.addWidget(artist_lbl)

        lay.addLayout(info, stretch=1)

        # Play button
        play_btn = RippleButton("Reproducir", "primary")
        play_btn.setFixedHeight(40)
        if on_play:
            play_btn.clicked.connect(on_play)
        lay.addWidget(play_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

    async def _load_thumb(self, url):
        from pyrolist.utils.image_cache import ImageCache
        cache = ImageCache()
        path = await cache.download(url)
        if path:
            pix = QPixmap(str(path))
            if not pix.isNull():
                self.thumb.setPixmap(pix)
                self.thumb.setText("")
                self.thumb.setStyleSheet("border-radius: 12px;")

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
        header = QWidget()
        header.setStyleSheet("background: #0F0F1A; border-bottom: 1px solid #2A2A3E;")
        header_lay = QVBoxLayout(header)
        header_lay.setContentsMargins(24, 16, 24, 12)
        header_lay.setSpacing(12)

        self._query_label = QLabel("")
        self._query_label.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        self._query_label.setStyleSheet("color: #FFFFFF;")
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

        root.addWidget(header)

        # -- Scrollable results area (must be created BEFORE chips are checked) --
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("background: transparent; border: none;")

        self._results_widget = QWidget()
        self._results_layout = QVBoxLayout(self._results_widget)
        self._results_layout.setContentsMargins(24, 16, 24, 24)
        self._results_layout.setSpacing(12)

        self._scroll.setWidget(self._results_widget)
        root.addWidget(self._scroll)

        # Default check (after results_layout exists)
        self._chips["song"].setChecked(True)

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
    def search(self, query: str):
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
        asyncio.ensure_future(self._do_search(query))

    @asyncSlot()
    async def _do_search(self, query: str):
        if not self.yt:
            return
        try:
            self._clear_results()
            self._results_layout.addWidget(SkeletonListLoader(row_count=6))
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
            empty = QLabel("No se encontraron resultados en esta categoría")
            empty.setFont(QFont("Inter", 13))
            empty.setStyleSheet("color: #666688; padding: 32px;")
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
            return PlaylistCard(title=title, thumbnail_url=thumb_url)

        return None

    async def load(self):
        pass
