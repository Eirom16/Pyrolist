from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QProgressBar, QFrame
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QFont, QColor

from pyrolist.ui.design import tokens
from pyrolist.ui.design.icons import Icon
from pyrolist.ui.widgets.glass_panel import GlassPanel
from pyrolist.services.download_manager import DownloadManager


class DownloadProgressRow(QWidget):
    cancel_requested = Signal(str)

    def __init__(self, video_id: str, title: str, artist: str, parent=None):
        super().__init__(parent)
        self.video_id = video_id
        self.title = title
        self.artist = artist
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # Header row: Title + Cancel Button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self.title_lbl = QLabel(f"{self.artist} - {self.title}")
        self.title_lbl.setFont(QFont("Inter", 11, QFont.Weight.Medium))
        self.title_lbl.setStyleSheet(f"color: {tokens.CURRENT.text_primary};")
        header_layout.addWidget(self.title_lbl, stretch=1)

        self.cancel_btn = QPushButton()
        self.cancel_btn.setFixedSize(20, 20)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(lambda: self.cancel_requested.emit(self.video_id))
        header_layout.addWidget(self.cancel_btn)

        layout.addLayout(header_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        # Subtext row (percentage + speed)
        self.sub_lbl = QLabel("En cola...")
        self.sub_lbl.setFont(QFont("Inter", 9))
        self.sub_lbl.setStyleSheet(f"color: {tokens.CURRENT.text_secondary};")
        layout.addWidget(self.sub_lbl)

        self._update_styles()

    def set_progress(self, progress: float, speed: str):
        self.progress_bar.setValue(int(progress))
        speed_str = f" • {speed}" if speed else ""
        self.sub_lbl.setText(f"{int(progress)}%{speed_str}")

    def _update_styles(self):
        if not hasattr(self, "title_lbl") or not hasattr(self, "sub_lbl") or not hasattr(self, "cancel_btn") or not hasattr(self, "progress_bar"):
            return
        text_primary = tokens.CURRENT.text_primary
        text_secondary = tokens.CURRENT.text_secondary
        accent = tokens.CURRENT.accent
        bg_high = tokens.CURRENT.bg_high
        c = QColor(text_primary)

        self.title_lbl.setStyleSheet(f"color: {text_primary}; background: transparent;")
        self.sub_lbl.setStyleSheet(f"color: {text_secondary}; background: transparent;")
        
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {text_secondary};
                border: none;
                border-radius: 10px;
                font-family: "{Icon.font().family()}";
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: rgba({c.red()},{c.green()},{c.blue()},0.08);
                color: {tokens.CURRENT.error};
            }}
        """)
        self.cancel_btn.setText(Icon.get("close"))

        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {bg_high};
                border: none;
                border-radius: 2.5px;
            }}
            QProgressBar::chunk {{
                background-color: {accent};
                border-radius: 2.5px;
            }}
        """)

    def changeEvent(self, event):
        from PySide6.QtCore import QEvent
        if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
            if not getattr(self, '_in_style_change', False):
                self._in_style_change = True
                try:
                    self._update_styles()
                finally:
                    self._in_style_change = False
        super().changeEvent(event)


class NotificationHistoryRow(QWidget):
    def __init__(self, message: str, kind: str = "success", parent=None):
        super().__init__(parent)
        self.message = message
        self.kind = kind
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)

        # Kind icon (success, error, info)
        icon_name = "check_circle"
        if self.kind == "error":
            icon_name = "error"
        elif self.kind == "info":
            icon_name = "info"

        self.icon_lbl = QLabel(Icon.get(icon_name))
        self.icon_lbl.setFont(Icon.font(16))
        self.icon_lbl.setFixedSize(20, 20)
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_lbl)

        # Message text
        self.msg_lbl = QLabel(self.message)
        self.msg_lbl.setFont(QFont("Inter", 10))
        self.msg_lbl.setWordWrap(True)
        layout.addWidget(self.msg_lbl, stretch=1)

        self._update_styles()

    def _update_styles(self):
        if not hasattr(self, "icon_lbl") or not hasattr(self, "msg_lbl"):
            return
        text_primary = tokens.CURRENT.text_primary
        color_map = {
            "success": tokens.CURRENT.success,
            "error": tokens.CURRENT.error,
            "info": tokens.CURRENT.info
        }
        accent = color_map.get(self.kind, tokens.CURRENT.accent)
        
        self.icon_lbl.setStyleSheet(f"color: {accent}; background: transparent;")
        self.msg_lbl.setStyleSheet(f"color: {text_primary}; background: transparent;")

    def changeEvent(self, event):
        from PySide6.QtCore import QEvent
        if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
            if not getattr(self, '_in_style_change', False):
                self._in_style_change = True
                try:
                    self._update_styles()
                finally:
                    self._in_style_change = False
        super().changeEvent(event)


class NotificationDropdown(GlassPanel):
    unread_changed = Signal(bool) # Emits has_unread status

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("notificationDropdown")
        self.setFixedWidth(320)
        self.setMaximumHeight(400)
        
        self._tasks_metadata = {} # video_id -> {"title": str, "artist": str}
        self._active_widgets = {} # video_id -> DownloadProgressRow
        self._history_items = []  # List of {"message": str, "kind": str}
        self.has_unread = False

        self._build_ui()
        self._connect_download_manager()

    def _build_ui(self):
        root_layout = self.layout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Header Row
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(16, 12, 16, 8)
        header_layout.setSpacing(8)

        title_lbl = QLabel("Notificaciones")
        title_lbl.setFont(QFont("Inter", 13, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {tokens.CURRENT.text_primary};")
        header_layout.addWidget(title_lbl, stretch=1)

        self.clear_btn = QPushButton("Limpiar")
        self.clear_btn.setFont(QFont("Inter", 10, QFont.Weight.Medium))
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear_history)
        header_layout.addWidget(self.clear_btn)

        root_layout.addWidget(header_widget)

        # Horizontal Separator
        self.sep = QFrame()
        self.sep.setFrameShape(QFrame.Shape.HLine)
        self.sep.setFrameShadow(QFrame.Shadow.Plain)
        self.sep.setFixedHeight(1)
        root_layout.addWidget(self.sep)

        # Scroll Area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._inner = QWidget()
        self._inner.setObjectName("notificationScrollInner")
        self._inner_layout = QVBoxLayout(self._inner)
        self._inner_layout.setContentsMargins(0, 8, 0, 8)
        self._inner_layout.setSpacing(6)

        # Sections inside inner layout
        # A. Empty State
        self.empty_widget = QWidget()
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setContentsMargins(16, 32, 16, 32)
        empty_layout.setSpacing(8)
        empty_icon = QLabel(Icon.get("notifications"))
        empty_icon.setFont(Icon.font(36))
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_icon.setStyleSheet(f"color: {tokens.CURRENT.text_disabled};")
        empty_layout.addWidget(empty_icon)
        empty_lbl = QLabel("No tienes notificaciones")
        empty_lbl.setFont(QFont("Inter", 11))
        empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_lbl.setStyleSheet(f"color: {tokens.CURRENT.text_secondary};")
        empty_layout.addWidget(empty_lbl)
        self._inner_layout.addWidget(self.empty_widget)

        # B. Active downloads group
        self.active_container = QWidget()
        self.active_layout = QVBoxLayout(self.active_container)
        self.active_layout.setContentsMargins(0, 0, 0, 0)
        self.active_layout.setSpacing(4)
        
        self.active_hdr = QLabel("  Descargas en curso")
        self.active_hdr.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        self.active_hdr.setStyleSheet(f"color: {tokens.CURRENT.text_secondary};")
        self.active_layout.addWidget(self.active_hdr)
        self._inner_layout.addWidget(self.active_container)
        self.active_container.hide()

        # C. History group
        self.history_container = QWidget()
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.setContentsMargins(0, 0, 0, 0)
        self.history_layout.setSpacing(4)

        self.history_hdr = QLabel("  Historial")
        self.history_hdr.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        self.history_hdr.setStyleSheet(f"color: {tokens.CURRENT.text_secondary};")
        self.history_layout.addWidget(self.history_hdr)
        self._inner_layout.addWidget(self.history_container)
        self.history_container.hide()

        self._inner_layout.addStretch()
        self._scroll.setWidget(self._inner)
        root_layout.addWidget(self._scroll)

        self._update_styles()

    def _update_styles(self):
        if not hasattr(self, "sep") or not hasattr(self, "clear_btn"):
            return
        text_primary = tokens.CURRENT.text_primary
        text_secondary = tokens.CURRENT.text_secondary
        bg_surface = tokens.CURRENT.bg_surface
        border_color = tokens.CURRENT.border
        accent = tokens.CURRENT.accent
        c = QColor(text_primary)

        self.setStyleSheet(f"""
            #notificationDropdown {{
                background-color: {tokens.CURRENT.bg_surface};
                border: 1px solid {border_color};
                border-radius: 16px;
            }}
            #notificationScrollInner {{
                background: transparent;
            }}
        """)

        self.sep.setStyleSheet(f"background-color: {border_color}; border: none;")

        self.clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {text_secondary};
                border: none;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                color: {accent};
            }}
        """)

    def changeEvent(self, event):
        from PySide6.QtCore import QEvent
        if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
            if not getattr(self, '_in_style_change', False):
                self._in_style_change = True
                try:
                    self._update_styles()
                finally:
                    self._in_style_change = False
        super().changeEvent(event)

    def _connect_download_manager(self):
        mgr = DownloadManager.get_instance()
        mgr.download_queued.connect(self._on_download_queued)
        mgr.download_started.connect(self._on_download_started)
        mgr.download_progress.connect(self._on_download_progress)
        mgr.download_completed.connect(self._on_download_completed)
        mgr.download_error.connect(self._on_download_error)

    # --- Notification Handlers ---
    def popup_at(self, pos):
        # Clear unread status when opening the center
        self.has_unread = False
        self.unread_changed.emit(False)
        super().popup_at(pos)

    def add_custom_notification(self, message: str, kind: str = "info"):
        """Interface for other systems (like playlist download starts) to send notifications."""
        self._history_items.append({"message": message, "kind": kind})
        
        row = NotificationHistoryRow(message, kind)
        self.history_layout.addWidget(row)
        
        # Trigger unread dot if dropdown is not currently open
        if not self.isVisible():
            self.has_unread = True
            self.unread_changed.emit(True)
            
        self._update_visibility()

    def clear_history(self):
        self._history_items.clear()
        # Remove widgets from history layout except index 0 (the header)
        while self.history_layout.count() > 1:
            item = self.history_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        self._update_visibility()

    def _update_visibility(self):
        has_active = len(self._active_widgets) > 0
        has_history = len(self._history_items) > 0

        self.active_container.setVisible(has_active)
        self.history_container.setVisible(has_history)
        self.empty_widget.setVisible(not has_active and not has_history)
        self.clear_btn.setVisible(has_history)

    # --- Slot Listeners ---
    @Slot(object)
    def _on_download_queued(self, task):
        self._tasks_metadata[task.video_id] = {
            "title": task.title,
            "artist": task.artist
        }
        
        row = DownloadProgressRow(task.video_id, task.title, task.artist)
        row.cancel_requested.connect(lambda vid: DownloadManager.get_instance().cancel_download(vid))
        
        self.active_layout.addWidget(row)
        self._active_widgets[task.video_id] = row
        
        if not self.isVisible():
            self.has_unread = True
            self.unread_changed.emit(True)
            
        self._update_visibility()

    @Slot(str)
    def _on_download_started(self, video_id):
        # Optional styling update or just let it update with progress
        pass

    @Slot(str, float, str)
    def _on_download_progress(self, video_id, progress, speed):
        if video_id in self._active_widgets:
            self._active_widgets[video_id].set_progress(progress, speed)

    @Slot(str, str)
    def _on_download_completed(self, video_id, filepath):
        # Move from active to history
        meta = self._tasks_metadata.get(video_id, {"title": video_id, "artist": "Canción"})
        title = meta["title"]
        artist = meta["artist"]

        # Clean active widget
        if video_id in self._active_widgets:
            widget = self._active_widgets.pop(video_id)
            self.active_layout.removeWidget(widget)
            widget.deleteLater()

        # Add history entry
        msg = f"Descarga finalizada: {artist} - {title}"
        self.add_custom_notification(msg, "success")

    @Slot(str, str)
    def _on_download_error(self, video_id, error_msg):
        # Move from active to history
        meta = self._tasks_metadata.get(video_id, {"title": video_id, "artist": "Canción"})
        title = meta["title"]

        # Clean active widget
        if video_id in self._active_widgets:
            widget = self._active_widgets.pop(video_id)
            self.active_layout.removeWidget(widget)
            widget.deleteLater()

        # Add history entry
        msg = f"Error al descargar '{title}': {error_msg}"
        self.add_custom_notification(msg, "error")
