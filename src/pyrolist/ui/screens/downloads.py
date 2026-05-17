import asyncio
from pathlib import Path
from loguru import logger
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame, QPushButton, QProgressBar
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QPixmap

from pyrolist.config.paths import AppDirs
from pyrolist.ui.design.icons import Icon
from pyrolist.ui.widgets.icon_button import IconButton
from pyrolist.services.download_manager import DownloadManager
from pyrolist.db.repository import DownloadRepository


class DownloadItemWidget(QFrame):
    def __init__(self, video_id, title, artist, thumbnail_url, parent_playlist_title=None, on_play_local=None):
        super().__init__()
        self.video_id = video_id
        self.title = title
        self.artist = artist
        self.thumbnail_url = thumbnail_url
        self.parent_playlist_title = parent_playlist_title
        self.on_play_local = on_play_local
        self.file_path = None
        self._build_ui()

    def _build_ui(self):
        self.setObjectName("downloadCard")
        self.setStyleSheet("""
            QFrame#downloadCard {
                background-color: #1E1E2E;
                border-radius: 12px;
            }
            QFrame#downloadCard:hover {
                background-color: #2A2A3E;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        
        self.thumb = QLabel()
        self.thumb.setFixedSize(48, 48)
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setText(Icon.get("music_note"))
        self.thumb.setFont(Icon.font(24))
        self.thumb.setStyleSheet("background-color: #1E1E38; color: #4A4A6A; border-radius: 6px;")
        layout.addWidget(self.thumb)
        
        info = QVBoxLayout()
        title_lbl = QLabel(self.title)
        title_lbl.setStyleSheet("color: #FFFFFF; font-weight: 600; font-size: 14px;")
        
        artist_text = self.artist
        if self.parent_playlist_title:
            artist_text += f" • {self.parent_playlist_title}"
        self.artist_lbl = QLabel(artist_text)
        self.artist_lbl.setStyleSheet("color: #888899; font-size: 12px;")
        
        info.addWidget(title_lbl)
        info.addWidget(self.artist_lbl)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background: #1E1E38; border-radius: 2px; }
            QProgressBar::chunk { background: #A78BFA; border-radius: 2px; }
        """)
        self.progress_bar.hide()
        info.addWidget(self.progress_bar)
        
        layout.addLayout(info)
        layout.addStretch()
        
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #9B9BC0; font-size: 12px;")
        layout.addWidget(self.status_lbl)
        
        self.play_btn = IconButton(size=36)
        self.play_btn.setText(Icon.get("play_arrow"))
        self.play_btn.setFont(Icon.font(20))
        self.play_btn.setFixedSize(36, 36)
        self.play_btn.setStyleSheet("background: transparent; color: #F1F0FF; border: none;")
        self.play_btn.clicked.connect(self._on_play)
        self.play_btn.hide()
        layout.addWidget(self.play_btn)

    def set_downloading(self):
        self.progress_bar.show()
        self.status_lbl.setText("Descargando...")
        self.play_btn.hide()

    def update_progress(self, percent, speed):
        self.progress_bar.setValue(int(percent))
        self.status_lbl.setText(f"{percent}% • {speed}")

    def set_completed(self, filepath):
        self.file_path = filepath
        self.progress_bar.hide()
        self.status_lbl.setText("Completado")
        self.status_lbl.hide()
        self.play_btn.show()

    def set_error(self, msg):
        self.progress_bar.hide()
        self.status_lbl.setText("Error")
        self.status_lbl.setStyleSheet("color: #EF4444; font-size: 12px;")
        self.play_btn.hide()

    def _on_play(self):
        if self.file_path and self.on_play_local:
            metadata = {
                "title": self.title,
                "artist": self.artist,
                "thumbnail_url": self.thumbnail_url
            }
            self.on_play_local(self.file_path, metadata)

class DownloadsScreen(QWidget):
    def __init__(self, extractor, on_play_local):
        super().__init__()
        self.extractor = extractor
        self.on_play_local = on_play_local
        self._current_tab = "songs"
        self._items = {} # video_id -> DownloadItemWidget
        self._repo = DownloadRepository()
        self._build_ui()
        self._connect_manager()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(20)

        header = QLabel("Descargas")
        header.setFont(QFont("Inter", 24, QFont.Weight.Bold))
        header.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(header)

        # Tabs
        self.tabs = QWidget()
        tabs_layout = QHBoxLayout(self.tabs)
        tabs_layout.setSpacing(16)
        
        tab_names = [
            ("songs", "Canciones"),
            ("playlists", "Playlists Completas")
        ]
        
        self.tab_btns = {}
        for key, name in tab_names:
            btn = QPushButton(name)
            btn.setObjectName(f"tab_{key}")
            btn.setStyleSheet(self._tab_style(key == self._current_tab))
            btn.clicked.connect(lambda _, k=key: self._switch_tab(k))
            tabs_layout.addWidget(btn)
            self.tab_btns[key] = btn
        
        tabs_layout.addStretch()
        layout.addWidget(self.tabs)

        self.content_area = QScrollArea()
        self.content_area.setWidgetResizable(True)
        self.content_area.setStyleSheet("background: transparent; border: none;")
        
        self.scroll_content = QWidget()
        self.content_layout = QVBoxLayout(self.scroll_content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        self.content_layout.addStretch()
        
        self.content_area.setWidget(self.scroll_content)
        layout.addWidget(self.content_area)

    def _tab_style(self, active: bool):
        if active:
            return """
                QPushButton {
                    background: #2D1B69;
                    color: #BB86FC;
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-weight: bold;
                }
            """
        return """
            QPushButton {
                background: transparent;
                color: #888899;
                padding: 8px 16px;
                border: none;
                border-radius: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #2A2A3E;
                color: #FFFFFF;
            }
        """

    def _switch_tab(self, key):
        self._current_tab = key
        for k, btn in self.tab_btns.items():
            btn.setStyleSheet(self._tab_style(k == key))
        asyncio.ensure_future(self.load())

    def _connect_manager(self):
        mgr = DownloadManager.get_instance()
        mgr.download_queued.connect(self._on_download_queued)
        mgr.download_started.connect(self._on_download_started)
        mgr.download_progress.connect(self._on_download_progress)
        mgr.download_completed.connect(self._on_download_completed)
        mgr.download_error.connect(self._on_download_error)

    def _on_download_queued(self, task):
        # Add to UI if matches current tab
        is_playlist = task.parent_playlist_id is not None
        if (self._current_tab == "playlists" and is_playlist) or (self._current_tab == "songs" and not is_playlist):
            self._add_item_to_ui(task.video_id, task.title, task.artist, task.thumbnail_url, task.parent_playlist_title)
            self._items[task.video_id].set_downloading()

    def _on_download_started(self, video_id):
        if video_id in self._items:
            self._items[video_id].set_downloading()

    def _on_download_progress(self, video_id, percent, speed):
        if video_id in self._items:
            self._items[video_id].update_progress(percent, speed)

    def _on_download_completed(self, video_id, filepath):
        if video_id in self._items:
            self._items[video_id].set_completed(filepath)

    def _on_download_error(self, video_id, error_msg):
        if video_id in self._items:
            self._items[video_id].set_error(error_msg)

    def _add_item_to_ui(self, vid, title, artist, thumb_url, parent_playlist_title=None):
        if vid in self._items:
            return
        widget = DownloadItemWidget(vid, title, artist, thumb_url, parent_playlist_title, self.on_play_local)
        self.content_layout.insertWidget(0, widget)
        self._items[vid] = widget

    async def load(self):
        while self.content_layout.count() > 1:
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._items.clear()

        downloads = await self._repo.get_downloads()
        
        # Filter based on tab
        filtered = []
        for d in downloads:
            is_playlist = d.parent_playlist_id is not None
            if self._current_tab == "playlists" and is_playlist:
                filtered.append(d)
            elif self._current_tab == "songs" and not is_playlist:
                filtered.append(d)

        if not filtered:
            msg = QLabel("No hay descargas aquí.")
            msg.setStyleSheet("color: #888899; font-size: 16px; padding: 40px;")
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_layout.insertWidget(0, msg)
            
        for d in reversed(filtered):
            self._add_item_to_ui(d.video_id, d.title, d.artist, d.thumbnail_url, d.parent_playlist_title)
            self._items[d.video_id].set_completed(d.file_path)
            
        # Add active downloads from manager
        mgr = DownloadManager.get_instance()
        for vid, task in mgr._tasks.items():
            is_playlist = task.parent_playlist_id is not None
            if (self._current_tab == "playlists" and is_playlist) or (self._current_tab == "songs" and not is_playlist):
                if vid not in self._items:
                    self._add_item_to_ui(task.video_id, task.title, task.artist, task.thumbnail_url, task.parent_playlist_title)
                    if task.status == "downloading":
                        self._items[vid].set_downloading()
                    elif task.status == "error":
                        self._items[vid].set_error("Error")
