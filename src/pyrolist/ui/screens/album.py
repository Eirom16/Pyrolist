from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QPushButton
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QFont, QPixmap, QPainter, QPen, QColor
from functools import partial
from loguru import logger
import asyncio
from pyrolist.ui.widgets.song_card import SongCard
from pyrolist.ui.widgets.icon_button import IconButton
from pyrolist.ui.design.icons import Icon
from pyrolist.utils.image_cache import ImageCache

_image_cache = ImageCache()


class CircularProgress(QWidget):
    """Tiny circular progress indicator for album download status."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self._progress = 0.0

    def set_progress(self, progress: float):
        self._progress = max(0.0, min(100.0, progress))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg_pen = QPen(QColor(40, 40, 50, 80), 2)
        painter.setPen(bg_pen)
        painter.drawEllipse(2, 2, 20, 20)
        from pyrolist.ui.design import tokens
        accent_color = QColor(tokens.CURRENT.accent)
        fg_pen = QPen(accent_color, 2.5)
        fg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(fg_pen)
        span_angle = -int(self._progress * 3.6 * 16)
        painter.drawArc(2, 2, 20, 20, 90 * 16, span_angle)


class AlbumScreen(QWidget):
    download_requested = Signal(str, str, str, str)
    download_album_requested = Signal(str, str, str)  # browse_id, title, thumbnail_url
    play_next_requested = Signal(str, str, str, str)
    add_to_queue_requested = Signal(str, str, str, str)
    like_requested = Signal(str, object)
    add_to_playlist_requested = Signal(str, str)
    delete_download_requested = Signal(str)

    def __init__(self, yt_client, on_play_song, on_back=None):
        super().__init__()
        self.yt = yt_client
        self.on_play_song = on_play_song
        self.on_back = on_back
        self._browse_id = None
        self._album_data = None
        self._thumbnail_url = ""
        self._build_ui()

        # Wire up DownloadManager signals for real-time progress update
        try:
            from pyrolist.services.download_manager import DownloadManager
            dm = DownloadManager.get_instance()
            dm.download_progress.connect(self._on_download_progress)
            dm.download_completed.connect(self._on_download_completed)
            dm.download_error.connect(self._on_download_error)
        except Exception as e:
            logger.debug(f"Could not connect to DownloadManager signals: {e}")

    def _build_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(24, 24, 24, 24)
        self.content_layout.setSpacing(16)
        
        self.scroll.setWidget(self.content_widget)
        self.layout.addWidget(self.scroll)

    def _clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())

    async def load(self, browse_id: str):
        if not browse_id:
            return
            
        self._browse_id = browse_id
        self._clear_content()
        
        from pyrolist.ui.widgets.skeleton_loader import SkeletonListLoader
        skeleton = SkeletonListLoader(row_count=8)
        self.content_layout.addWidget(skeleton)
        
        try:
            data = await self.yt.get_album(browse_id)
            self._album_data = data

            # Check which tracks are already downloaded
            from pyrolist.db.repository import DownloadRepository
            repo = DownloadRepository()
            downloads = await repo.get_downloads()
            downloaded_vids = {d.video_id for d in downloads}

            tracks = data.get('tracks', [])
            if tracks:
                downloaded_count = sum(1 for t in tracks if t.get('videoId') in downloaded_vids)
                if downloaded_count == len(tracks):
                    data['is_fully_downloaded'] = True
                elif downloaded_count > 0:
                    data['is_partially_downloaded'] = True
                    data['downloaded_count'] = downloaded_count

            self._display_album(data)
        except Exception as e:
            logger.error(f"Error loading album: {e}")
            self._clear_content()
            self.content_layout.addWidget(QLabel("Error cargando álbum"))

    def _display_album(self, data: dict):
        self._clear_content()
        
        if not data:
            self.content_layout.addWidget(QLabel("Álbum no encontrado"))
            return
            
        from pyrolist.ui.design import tokens

        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(24)
        
        thumbnail_url = ""
        thumbnails = data.get('thumbnails', [])
        if thumbnails:
            thumbnail_url = thumbnails[-1].get('url', '')
        self._thumbnail_url = thumbnail_url

        # Back button row
        back_row = QHBoxLayout()
        back_row.setContentsMargins(0, 0, 0, 8)
        btn_back = QPushButton()
        btn_back.setIcon(Icon.icon("arrow_back", tokens.CURRENT.text_secondary, 16))
        btn_back.setText("Volver")
        btn_back.setFont(QFont("Inter", 11, QFont.Weight.Medium))
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {tokens.CURRENT.text_secondary};
                border: none;
                padding: 6px 12px;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background: {tokens.CURRENT.bg_elevated};
                color: {tokens.CURRENT.text_primary};
            }}
        """)
        btn_back.setFixedHeight(36)
        if self.on_back:
            btn_back.clicked.connect(self.on_back)
        back_row.addWidget(btn_back)
        back_row.addStretch()
        self.content_layout.addLayout(back_row)
            
        self.cover = QLabel()
        self.cover.setFixedSize(200, 200)
        self.cover.setStyleSheet(f"background: {tokens.CURRENT.bg_elevated}; border-radius: 8px;")
        header_layout.addWidget(self.cover)
        
        if thumbnail_url:
            asyncio.ensure_future(self._load_cover(thumbnail_url))
            
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)
        
        type_lbl = QLabel(data.get('type', 'ÁLBUM').upper())
        type_lbl.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        type_lbl.setStyleSheet(f"color: {tokens.CURRENT.accent}; background: transparent;")
        info_layout.addWidget(type_lbl)
        
        title_lbl = QLabel(data.get('title', 'Unknown'))
        title_lbl.setFont(QFont("Inter", 32, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {tokens.CURRENT.text_primary}; background: transparent;")
        title_lbl.setWordWrap(True)
        info_layout.addWidget(title_lbl)
        
        artists = data.get('artists', [])
        artist_names = ", ".join([a.get('name', '') for a in artists]) if isinstance(artists, list) else str(artists)
        
        year = data.get('year', '')
        track_count = data.get('trackCount', 0) or len(data.get('tracks', []))
        
        meta_str = f"{artist_names}"
        if year:
            meta_str += f" • {year}"
        if track_count:
            meta_str += f" • {track_count} canciones"
            
        meta_lbl = QLabel(meta_str)
        meta_lbl.setFont(QFont("Inter", 11))
        meta_lbl.setStyleSheet(f"color: {tokens.CURRENT.text_secondary}; background: transparent;")
        info_layout.addWidget(meta_lbl)

        # Download actions row
        dl_layout = QHBoxLayout()
        dl_layout.setSpacing(12)
        dl_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        dl_layout.setContentsMargins(0, 8, 0, 0)

        self.label_offline_status = QLabel("📥 Disponible sin conexión")
        self.label_offline_status.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        self.label_offline_status.setStyleSheet(f"color: {tokens.CURRENT.accent}; background: transparent;")

        self.progress_circle = CircularProgress()
        self.progress_circle.hide()

        # Check active tasks for this album
        from pyrolist.services.download_manager import DownloadManager
        dm = DownloadManager.get_instance()
        active_tasks = [t for t in dm._tasks.values() if t.parent_playlist_id == f"album_{self._browse_id}"]

        if data.get('is_fully_downloaded', False):
            self.label_offline_status.show()
            dl_layout.addWidget(self.label_offline_status)
        else:
            self.label_offline_status.hide()

            btn_label = " Descargar Álbum"
            if data.get('is_partially_downloaded', False):
                btn_label = f" Descargar restantes ({data.get('downloaded_count')}/{track_count} completas)"

            self.btn_dl = QPushButton(btn_label)
            self.btn_dl.setIcon(Icon.icon("download", color="#0A0A14"))
            self._update_dl_button_style()
            self.btn_dl.setCursor(Qt.CursorShape.PointingHandCursor)

            def on_dl_click():
                self.btn_dl.setText(" Descargando... 0%")
                self.btn_dl.setIcon(Icon.icon("hourglass_empty", color="#0A0A14"))
                self.btn_dl.setEnabled(False)
                self.progress_circle.set_progress(0.0)
                self.progress_circle.show()
                self.download_album_requested.emit(
                    self._browse_id,
                    data.get('title', 'Unknown'),
                    thumbnail_url
                )

            self.btn_dl.clicked.connect(on_dl_click)

            dl_layout.addWidget(self.btn_dl)
            dl_layout.addWidget(self.progress_circle)
            dl_layout.addWidget(self.label_offline_status)

            if active_tasks:
                total_progress = sum(t.progress for t in active_tasks)
                overall_pct = total_progress / len(active_tasks)
                self.btn_dl.setText(f" Descargando... {int(overall_pct)}%")
                self.btn_dl.setIcon(Icon.icon("hourglass_empty", color="#0A0A14"))
                self.btn_dl.setEnabled(False)
                self.progress_circle.set_progress(overall_pct)
                self.progress_circle.show()

        info_layout.addLayout(dl_layout)
        info_layout.addStretch()

        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        self.content_layout.addLayout(header_layout)
        
        self.content_layout.addSpacing(24)
        
        # Tracks
        tracks = data.get('tracks', [])
        for i, track in enumerate(tracks):
            title = track.get('title', 'Unknown')
            video_id = track.get('videoId', '')
            
            # Use album artists if track doesn't specify
            track_artists = track.get('artists', [])
            if not track_artists:
                track_artist_names = artist_names
            else:
                track_artist_names = ", ".join([a.get('name', '') for a in track_artists]) if isinstance(track_artists, list) else str(track_artists)
            
            duration = track.get('duration', '')
            
            if video_id:
                card = SongCard(
                    title=title,
                    artist=track_artist_names,
                    duration=duration,
                    thumbnail_url=thumbnail_url,  # Usually same as album
                    on_play=partial(self._handle_play, video_id, title, track_artist_names),
                    video_id=video_id
                )
                card.download_requested.connect(lambda *a: self.download_requested.emit(*a))
                card.play_next_requested.connect(lambda *a: self.play_next_requested.emit(*a))
                card.add_to_queue_requested.connect(lambda *a: self.add_to_queue_requested.emit(*a))
                card.like_requested.connect(lambda *a: self.like_requested.emit(*a))
                card.add_to_playlist_requested.connect(lambda *a: self.add_to_playlist_requested.emit(*a))
                card.delete_download_requested.connect(lambda *a: self.delete_download_requested.emit(*a))
                
                self.content_layout.addWidget(card)
                
        self.content_layout.addStretch()

    async def _load_cover(self, url: str):
        path = await _image_cache.download(url)
        if path:
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                size = 200
                radius = 8
                scaled = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                x = (scaled.width() - size) // 2
                y = (scaled.height() - size) // 2
                cropped = scaled.copy(x, y, size, size)
                from PySide6.QtGui import QPainterPath
                rounded = QPixmap(size, size)
                rounded.fill(Qt.GlobalColor.transparent)
                painter = QPainter(rounded)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                clip = QPainterPath()
                clip.addRoundedRect(QRectF(0, 0, size, size), radius, radius)
                painter.setClipPath(clip)
                painter.drawPixmap(0, 0, cropped)
                painter.end()
                self.cover.setPixmap(rounded)
                self.cover.setStyleSheet("background: transparent;")

    def _handle_play(self, video_id, title, artists):
        if self.on_play_song:
            self.on_play_song(video_id, title, artists, "", 0, self._thumbnail_url)

    def _update_dl_button_style(self) -> None:
        if hasattr(self, 'btn_dl') and isinstance(self.btn_dl, QPushButton):
            from pyrolist.ui.design import tokens
            accent = tokens.CURRENT.accent
            c = QColor(accent)
            bright_hex = c.lighter(125).name()
            self.btn_dl.setStyleSheet(f"""
                QPushButton {{
                    background-color: {accent};
                    color: {tokens.CURRENT.text_on_accent};
                    border: none;
                    border-radius: 16px;
                    padding: 8px 16px;
                    font-weight: bold;
                    margin-top: 12px;
                }}
                QPushButton:hover {{ background-color: {bright_hex}; }}
            """)

    def changeEvent(self, event) -> None:
        from PySide6.QtCore import QEvent
        if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
            if not getattr(self, '_in_style_change', False):
                self._in_style_change = True
                try:
                    self._update_dl_button_style()
                finally:
                    self._in_style_change = False
        super().changeEvent(event)

    # ── Download progress tracking ──
    def _on_download_progress(self, video_id: str, progress: float, speed: str) -> None:
        self._update_album_download_status()

    def _on_download_completed(self, video_id: str, filepath: str) -> None:
        self._update_album_download_status()

    def _on_download_error(self, video_id: str, error_msg: str) -> None:
        self._update_album_download_status()

    def _update_album_download_status(self) -> None:
        if not self._browse_id:
            return

        from pyrolist.services.download_manager import DownloadManager
        dm = DownloadManager.get_instance()

        album_tasks = [t for t in dm._tasks.values() if t.parent_playlist_id == f"album_{self._browse_id}"]
        if not album_tasks:
            return

        total_progress = sum(t.progress for t in album_tasks)
        overall_pct = total_progress / len(album_tasks)

        if hasattr(self, 'btn_dl') and isinstance(self.btn_dl, QPushButton) and self.btn_dl.isVisible():
            self.btn_dl.setText(f" Descargando... {int(overall_pct)}%")
            self.btn_dl.setIcon(Icon.icon("hourglass_empty", color="#0A0A14"))
            self.btn_dl.setEnabled(False)

            if hasattr(self, 'progress_circle'):
                self.progress_circle.set_progress(overall_pct)
                self.progress_circle.show()

            all_done = all(t.status == "completed" for t in album_tasks)
            if all_done:
                self.btn_dl.hide()
                self.progress_circle.hide()
                if hasattr(self, 'label_offline_status'):
                    self.label_offline_status.show()