"""
Global search bar with suggestions dropdown — YT Music style.

Shows search history, API suggestions, and quick results in a
floating dropdown. Actual search only fires on Enter or clicking
a suggestion/result.
"""

import json
import asyncio
from pathlib import Path
from functools import partial

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea,
    QSizePolicy, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Signal, Qt, QTimer, QPoint
from PySide6.QtGui import QFont, QColor, QPixmap
from loguru import logger

from pyrolist.config.paths import AppDirs
from pyrolist.ui.design.icons import Icon
from pyrolist.ui.widgets.glass_panel import GlassPanel


# ---------------------------------------------------------------------------
# Persistent search history  (simple JSON list, max 20 entries)
# ---------------------------------------------------------------------------
_HISTORY_FILE = AppDirs.data / "search_history.json"
_MAX_HISTORY = 20


def _load_history() -> list[str]:
    try:
        if _HISTORY_FILE.exists():
            return json.loads(_HISTORY_FILE.read_text())[:_MAX_HISTORY]
    except Exception:
        pass
    return []


def _save_history(history: list[str]):
    try:
        AppDirs.data.mkdir(parents=True, exist_ok=True)
        _HISTORY_FILE.write_text(json.dumps(history[:_MAX_HISTORY]))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Suggestion‑row helper widget
# ---------------------------------------------------------------------------
class _SuggestionRow(QWidget):
    """A single clickable row inside the dropdown."""
    clicked = Signal(str)
    deleted = Signal(str)

    def __init__(self, text: str, icon_name: str = "search",
                 deletable: bool = False, thumbnail_url: str = "",
                 subtitle: str = "", on_click_extra=None):
        super().__init__()
        self._text = text
        self._on_click_extra = on_click_extra
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(54 if subtitle or thumbnail_url else 44)
        self.setStyleSheet("""
            _SuggestionRow { background: transparent; }
            _SuggestionRow:hover { background: rgba(255,255,255,0.04); }
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(14)

        # Left icon / thumbnail
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(32 if thumbnail_url else 24, 32 if thumbnail_url else 24)
        if thumbnail_url:
            self.icon_label.setStyleSheet("background: #2A2A3E; border-radius: 4px;")
            asyncio.ensure_future(self._load_thumb(thumbnail_url))
        else:
            self.icon_label.setText(Icon.get(icon_name))
            self.icon_label.setFont(Icon.font(18))
            self.icon_label.setStyleSheet("color: #9B9BC0; background: transparent;")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.icon_label)

        # Text column
        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        text_col.setContentsMargins(0, 0, 0, 0)

        title_lbl = QLabel(text)
        title_lbl.setFont(QFont("Inter", 13))
        title_lbl.setStyleSheet("color: #FFFFFF;")
        text_col.addWidget(title_lbl)

        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setFont(QFont("Inter", 10))
            sub_lbl.setStyleSheet("color: #888899;")
            text_col.addWidget(sub_lbl)

        lay.addLayout(text_col, stretch=1)

        # Delete button (only for history items)
        if deletable:
            del_btn = QPushButton()
            del_btn.setFixedSize(28, 28)
            del_btn.setText(Icon.get("close"))
            del_btn.setFont(Icon.font(16))
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setStyleSheet("""
                QPushButton { background: transparent; color: #6B6B9B; border: none; border-radius: 14px; }
                QPushButton:hover { background: rgba(255,255,255,0.08); }
            """)
            del_btn.clicked.connect(lambda: self.deleted.emit(self._text))
            lay.addWidget(del_btn)

    # Click anywhere on the row
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._on_click_extra:
                self._on_click_extra()
            else:
                self.clicked.emit(self._text)
        super().mousePressEvent(event)

    async def _load_thumb(self, url):
        from pyrolist.utils.image_cache import ImageCache
        cache = ImageCache()
        path = await cache.download(url)
        if path:
            pix = QPixmap(str(path))
            if not pix.isNull():
                self.icon_label.setPixmap(pix.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))


# ---------------------------------------------------------------------------
# The dropdown panel (floats below the search bar)
# ---------------------------------------------------------------------------
class _SearchDropdown(GlassPanel):
    suggestion_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("searchDropdown")
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_X11DoNotAcceptFocus) # Helpful on Linux
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMaximumHeight(400)
        self.setStyleSheet("""
            #searchDropdown {
                background-color: #1A1A2E;
                border: 1px solid #2A2A3E;
                border-top: none;
                border-radius: 0 0 16px 16px;
            }
        """)

        root_layout = self.layout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._inner = QWidget()
        self._layout = QVBoxLayout(self._inner)
        self._layout.setContentsMargins(0, 8, 0, 8)
        self._layout.setSpacing(0)
        self._layout.addStretch()

        self._scroll.setWidget(self._inner)
        root_layout.addWidget(self._scroll)

    # --- Public helpers ---
    def clear_rows(self):
        # Remove all except the trailing stretch
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def add_separator(self, label: str = ""):
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #2A2A3E; margin: 4px 16px;")
        self._layout.addWidget(sep)
        if label:
            lbl = QLabel(f"  {label}")
            lbl.setFont(QFont("Inter", 11, QFont.Weight.Medium))
            lbl.setStyleSheet("color: #666688; margin: 6px 16px 2px 16px;")
            self._layout.addWidget(lbl)

    def add_row(self, row: _SuggestionRow):
        row.clicked.connect(self.suggestion_selected.emit)
        self._layout.insertWidget(self._layout.count() - 1, row)  # Before stretch


# ---------------------------------------------------------------------------
# GlobalSearchBar  (the main widget placed in the header)
# ---------------------------------------------------------------------------
class GlobalSearchBar(QWidget):
    """
    A search bar with YT‑Music‑style dropdown: history + suggestions.
    Emits *search_submitted* only when the user presses Enter or picks
    a suggestion.  No search‑per‑keystroke.
    """
    search_submitted = Signal(str)

    def __init__(self, yt_client, on_play_song):
        super().__init__()
        self.yt = yt_client
        self.on_play_song = on_play_song
        self._history: list[str] = _load_history()

        self._suggestion_timer = QTimer()
        self._suggestion_timer.setSingleShot(True)
        self._suggestion_timer.setInterval(250)
        self._suggestion_timer.timeout.connect(self._fetch_suggestions)

        self._dropdown: _SearchDropdown | None = None
        self._build_ui()

    # ---- UI construction ----
    def _build_ui(self):
        self.setObjectName("globalSearch")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        bar_widget = QWidget()
        bar_widget.setObjectName("searchBarRow")
        bar_widget.setStyleSheet("""
            #searchBarRow {
                background-color: #0F0F1A;
                border-bottom: 1px solid #2A2A3E;
            }
        """)
        bar_layout = QHBoxLayout(bar_widget)
        bar_layout.setContentsMargins(24, 10, 24, 10)
        bar_layout.setSpacing(12)

        # Search icon
        self._search_icon = QLabel()
        self._search_icon.setFixedSize(28, 28)
        self._search_icon.setText(Icon.get("search"))
        self._search_icon.setFont(Icon.font(20))
        self._search_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bar_layout.addWidget(self._search_icon)

        # Input field
        self.input = QLineEdit()
        self.input.setObjectName("globalSearchInput")
        self.input.setPlaceholderText("¿Qué quieres escuchar hoy?")
        self._update_search_bar_styles()
        self.input.textChanged.connect(self._on_text_changed)
        self.input.returnPressed.connect(self._on_return_pressed)
        bar_layout.addWidget(self.input)

        # Clear button, hidden when empty.
        self._clear_btn = QPushButton()
        self._clear_btn.setFixedSize(32, 32)
        self._clear_btn.setText(Icon.get("close"))
        self._clear_btn.setFont(Icon.font(18))
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #9B9BC0; border: none; border-radius: 16px; }
            QPushButton:hover { background: rgba(255,255,255,0.08); }
        """)
        self._clear_btn.clicked.connect(self._clear_input)
        self._clear_btn.setVisible(False)
        bar_layout.addWidget(self._clear_btn)

        layout.addWidget(bar_widget)

    # ---- Dropdown lifecycle ----
    def _ensure_dropdown(self):
        if self._dropdown is None:
            self._dropdown = _SearchDropdown(self)
            self._dropdown.suggestion_selected.connect(self._on_suggestion_selected)
        return self._dropdown

    def _show_dropdown(self):
        dd = self._ensure_dropdown()

        # Position below the search bar, aligned to the input
        global_pos = self.input.mapToGlobal(QPoint(0, self.input.height()))
        dd_width = min(self.input.width(), 600)
        dd.setFixedWidth(dd_width)
        dd.move(global_pos)
        
        # Calculate dynamic height based on the widgets inside the scroll area layout
        item_count = dd._layout.count() - 1  # Exclude the bottom stretch
        ideal_height = 24  # Margins and paddings
        for i in range(item_count):
            item = dd._layout.itemAt(i)
            if item:
                w = item.widget()
                if w:
                    # Fallback to sizeHint height or standard height if not yet polished by Qt layout
                    ideal_height += w.sizeHint().height() or (54 if "•" in getattr(w, '_subtitle', '') else 44)
        
        # Limit height between 150px and 380px to fit at least 6 items perfectly
        dd.setFixedHeight(min(max(ideal_height, 150), 380))
        
        # On some platforms/WMs, show() might still steal focus despite flags.
        # We ensure the input keeps it.
        dd.popup_at(global_pos)
        self.input.setFocus()
        dd.raise_()

    def _hide_dropdown(self):
        if self._dropdown and self._dropdown.isVisible():
            self._dropdown.hide()

    # ---- Slot: text changed (populate dropdown, but do NOT search) ----
    def _on_text_changed(self, text: str):
        self._clear_btn.setVisible(bool(text))

        if not text.strip():
            self._hide_dropdown()
            return

        # Show dropdown immediately with history, then schedule API suggestions
        self._populate_dropdown_quick(text.strip())
        self._suggestion_timer.start()

    def _populate_dropdown_quick(self, query: str):
        """Show history matches instantly (no network)."""
        dd = self._ensure_dropdown()
        dd.clear_rows()

        # Matching history
        matching = [h for h in self._history if query.lower() in h.lower()]
        if matching:
            for h in matching[:5]:
                row = _SuggestionRow(h, icon_name="history", deletable=True)
                row.deleted.connect(self._delete_history_item)
                dd.add_row(row)

        self._show_dropdown()

    def _fetch_suggestions(self):
        """Fetch API suggestions and update the dropdown."""
        query = self.input.text().strip()
        if not query or not self.yt:
            return
        asyncio.ensure_future(self._fetch_suggestions_async(query))

    async def _fetch_suggestions_async(self, query: str):
        try:
            suggestions = await self.yt.search_suggestions(query)
            self._update_dropdown_suggestions(query, suggestions)
        except Exception as e:
            logger.debug(f"Suggestion error: {e}")

    def _update_dropdown_suggestions(self, query: str, suggestions):
        """Rebuild dropdown with history + rich API suggestions."""
        dd = self._ensure_dropdown()
        dd.clear_rows()

        if not isinstance(suggestions, dict):
            # Fallback for old list format
            matching = [h for h in self._history if query.lower() in h.lower()]
            for h in matching[:3]:
                dd.add_row(_SuggestionRow(h, icon_name="history", deletable=True))
            if suggestions:
                dd.add_separator()
                for s in suggestions[:6]:
                    dd.add_row(_SuggestionRow(str(s)))
            self._show_dropdown()
            return

        # 1. History matches
        matching = [h for h in self._history if query.lower() in h.lower()]
        for h in matching[:3]:
            row = _SuggestionRow(h, icon_name="history", deletable=True)
            row.deleted.connect(self._delete_history_item)
            dd.add_row(row)

        # 2. Rich suggestions (Songs, Artists, Albums)
        has_rich = False
        
        # Artists
        artists = suggestions.get('artists', [])
        if artists:
            dd.add_separator("Artistas")
            for a in artists[:2]:
                name = a.get('name', 'Unknown')
                thumbs = a.get('thumbnails', [])
                url = thumbs[-1].get('url', '') if thumbs else ''
                row = _SuggestionRow(name, thumbnail_url=url, subtitle="Artista", 
                                   on_click_extra=lambda b=a.get('browseId'): self.search_submitted.emit(f"artist?id={b}"))
                dd.add_row(row)
            has_rich = True

        # Albums
        albums = suggestions.get('albums', [])
        if albums:
            dd.add_separator("Álbumes")
            for a in albums[:2]:
                title = a.get('title', 'Unknown')
                artists = a.get('artists', [])
                artist_name = artists[0].get('name', '') if artists else ''
                thumbs = a.get('thumbnails', [])
                url = thumbs[-1].get('url', '') if thumbs else ''
                row = _SuggestionRow(title, thumbnail_url=url, subtitle=f"Álbum • {artist_name}",
                                   on_click_extra=lambda b=a.get('browseId'): self.search_submitted.emit(f"album?id={b}"))
                dd.add_row(row)
            has_rich = True

        # Songs
        songs = suggestions.get('songs', [])
        if songs:
            dd.add_separator("Canciones")
            for s in songs[:3]:
                title = s.get('title', 'Unknown')
                artists = s.get('artists', [])
                artist_name = artists[0].get('name', '') if artists else ''
                thumbs = s.get('thumbnails', [])
                url = thumbs[-1].get('url', '') if thumbs else ''
                
                # For songs, we might want to play directly or just search
                # Let's just search for now to keep it consistent
                row = _SuggestionRow(title, thumbnail_url=url, subtitle=f"Canción • {artist_name}")
                dd.add_row(row)
            has_rich = True

        # 3. Text suggestions
        text_suggs = suggestions.get('text', [])
        if text_suggs:
            if has_rich or matching:
                dd.add_separator("Búsquedas relacionadas")
            for s in text_suggs[:5]:
                text = s.get('text', s) if isinstance(s, dict) else s
                if text.lower() in [h.lower() for h in matching]: continue
                dd.add_row(_SuggestionRow(text))

        self._show_dropdown()

    # ---- Slot: Return / Enter pressed ----
    def _on_return_pressed(self):
        query = self.input.text().strip()
        if query:
            self._commit_search(query)

    # ---- Slot: suggestion selected ----
    def _on_suggestion_selected(self, text: str):
        self.input.blockSignals(True)
        self.input.setText(text)
        self.input.blockSignals(False)
        self._commit_search(text)

    # ---- Commit the search (history + emit) ----
    def _commit_search(self, query: str):
        self._hide_dropdown()

        # Save to history (dedup, push to top)
        q_lower = query.lower()
        self._history = [h for h in self._history if h.lower() != q_lower]
        self._history.insert(0, query)
        self._history = self._history[:_MAX_HISTORY]
        _save_history(self._history)

        self.search_submitted.emit(query)

    # ---- Clear button ----
    def _clear_input(self):
        self.input.clear()
        self.input.setFocus()
        self._hide_dropdown()

    # ---- History management ----
    def _delete_history_item(self, text: str):
        self._history = [h for h in self._history if h != text]
        _save_history(self._history)
        # Refresh dropdown
        current = self.input.text().strip()
        if current:
            self._populate_dropdown_quick(current)
            self._suggestion_timer.start()

    # ---- Public helpers ----
    def focus_search(self):
        self.input.setFocus()
        self.input.selectAll()

    def _update_search_bar_styles(self) -> None:
        from pyrolist.ui.design import tokens
        accent = tokens.CURRENT.accent
        if hasattr(self, '_search_icon') and self._search_icon:
            self._search_icon.setStyleSheet(f"color: {accent}; background: transparent;")
        if hasattr(self, 'input') and self.input:
            self.input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: #1A1A2E;
                    border: 1px solid #2A2A3E;
                    border-radius: 24px;
                    color: #FFFFFF;
                    padding: 12px 24px;
                    font-size: 15px;
                    font-family: Inter;
                    selection-background-color: {accent};
                }}
                QLineEdit:focus {{
                    border: 1px solid {accent};
                    background-color: #1E1E3A;
                }}
                QLineEdit::placeholder {{ color: #666688; }}
            """)

    def changeEvent(self, event) -> None:
        from PySide6.QtCore import QEvent
        if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
            self._update_search_bar_styles()
        super().changeEvent(event)
