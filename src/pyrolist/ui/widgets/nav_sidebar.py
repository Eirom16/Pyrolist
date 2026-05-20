from __future__ import annotations

import asyncio

from PySide6.QtCore import QEasingCurve, QSize, Qt, QPropertyAnimation, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QColor
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from pyrolist.ui.design.fonts import AppFont
from pyrolist.ui.design.icons import Icon
from pyrolist.utils.image_cache import ImageCache

_image_cache = ImageCache()


NAV_ITEMS = [
    ("home", "home", "Inicio"),
    ("library", "library_music", "Biblioteca"),
    ("history", "history", "Historial"),
    ("stats", "bar_chart", "Estadísticas"),
    ("downloads", "download", "Descargas"),
    ("settings", "settings", "Ajustes"),
]


class NavButton(QPushButton):
    def __init__(self, route: str, icon_name: str, label: str, parent=None):
        super().__init__(parent)
        self.route = route
        self.icon_name = icon_name
        self.label = label
        self._collapsed = False
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(label)

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 0, 12, 0)
        row.setSpacing(12)

        self.icon_label = Icon.label(icon_name, 22, "#9B9BC0")
        self.text_label = QLabel(label)
        self.text_label.setFont(AppFont.body(13))
        self.text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        row.addWidget(self.icon_label)
        row.addWidget(self.text_label)
        row.addStretch()

        self._apply_style(False)

    def set_active(self, active: bool) -> None:
        self.setChecked(active)
        self._apply_style(active)

    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        self.text_label.setVisible(not collapsed)

    def _apply_style(self, active: bool) -> None:
        from pyrolist.ui.design import tokens
        from PySide6.QtGui import QColor
        accent = tokens.CURRENT.accent
        c = QColor(accent)
        r, g, b, _ = c.getRgb()

        color = accent if active else "#9B9BC0"
        weight = "700" if active else "500"
        self.icon_label.setStyleSheet(f"color: {color}; background: transparent;")
        self.text_label.setStyleSheet(f"color: {color}; background: transparent; font-weight: {weight};")
        
        bg = f"rgba({r},{g},{b},0.14)" if active else "transparent"
        hover_bg = f"rgba({r},{g},{b},0.09)"
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                border: none;
                border-radius: 12px;
                text-align: left;
                padding: 0;
            }}
            QPushButton:hover {{
                background: {hover_bg};
            }}
        """)

    def changeEvent(self, event) -> None:
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.Type.PaletteChange:
            if hasattr(self, 'icon_label') and self.icon_label:
                if not getattr(self, '_in_style_change', False):
                    self._in_style_change = True
                    try:
                        self._apply_style(self.isChecked())
                    finally:
                        self._in_style_change = False
        super().changeEvent(event)


class NavSidebar(QWidget):
    on_navigate = Signal(str)
    on_login_click = Signal()
    auth_changed = Signal(bool)

    EXPANDED_WIDTH = 220
    COLLAPSED_WIDTH = 64

    def __init__(self, on_navigate):
        super().__init__()
        self._on_navigate = on_navigate
        self._is_function = callable(on_navigate) and not hasattr(on_navigate, "emit")
        self._active = "home"
        self._collapsed = False
        self._is_authenticated = False
        self._user_avatar = ""
        self._user_name = ""
        self._nav_buttons: dict[str, NavButton] = {}
        self._avatar_task: asyncio.Task | None = None

        self.setObjectName("navSidebar")
        self.setFixedWidth(self.EXPANDED_WIDTH)
        self._width_anim = QPropertyAnimation(self, b"minimumWidth", self)
        self._width_anim.setDuration(280)
        self._width_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._max_anim = QPropertyAnimation(self, b"maximumWidth", self)
        self._max_anim.setDuration(280)
        self._max_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 16, 10, 16)
        layout.setSpacing(4)

        self._logo_row = QWidget()
        logo_layout = QHBoxLayout(self._logo_row)
        logo_layout.setContentsMargins(8, 0, 8, 12)
        logo_layout.setSpacing(10)
        from pyrolist.config.paths import AppDirs
        icon_path = AppDirs.root / "assets" / "icon.png"
        if icon_path.exists():
            self._app_icon = QLabel()
            pixmap = QPixmap(str(icon_path))
            self._app_icon.setPixmap(pixmap.scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self._app_icon_is_custom = True
        else:
            self._app_icon = Icon.label("music_note", 26, "#A78BFA")
            self._app_icon_is_custom = False
            
        self._app_title = QLabel("Pyrolist")
        self._app_title.setFont(AppFont.heading(18))
        self._update_header_style()
        logo_layout.addWidget(self._app_icon)
        logo_layout.addWidget(self._app_title)
        logo_layout.addStretch()
        layout.addWidget(self._logo_row)

        for route, icon_name, label in NAV_ITEMS:
            btn = NavButton(route, icon_name, label)
            btn.clicked.connect(lambda checked=False, r=route: self._navigate(r))
            self._nav_buttons[route] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # Profile button — directly in the main layout, no wrapping QFrame
        self._profile_btn = QPushButton()
        self._profile_btn.setFixedHeight(42)
        self._profile_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._profile_btn.clicked.connect(self._on_profile_clicked)
        layout.addWidget(self._profile_btn)

        # Collapse/expand toggle
        self._toggle_btn = QPushButton()
        self._toggle_btn.setFixedHeight(40)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setFont(Icon.font(20))
        self._toggle_btn.clicked.connect(self.toggle_collapse)
        layout.addWidget(self._toggle_btn)

        self._update_sidebar_styles()
        self._update_toggle_icon()
        self._update_profile_ui()
        self._select("home")

    def toggle_collapse(self) -> None:
        self._collapsed = not self._collapsed
        target = self.COLLAPSED_WIDTH if self._collapsed else self.EXPANDED_WIDTH
        self.setProperty("collapsed", "true" if self._collapsed else "false")
        self.style().unpolish(self)
        self.style().polish(self)

        self._width_anim.stop()
        self._width_anim.setStartValue(self.minimumWidth())
        self._width_anim.setEndValue(target)
        self._width_anim.start()
        self._max_anim.stop()
        self._max_anim.setStartValue(self.maximumWidth())
        self._max_anim.setEndValue(target)
        self._max_anim.start()

        for btn in self._nav_buttons.values():
            btn.set_collapsed(self._collapsed)
        self._app_title.setVisible(not self._collapsed)
        self._update_profile_ui()
        self._update_toggle_icon()

    def _update_toggle_icon(self) -> None:
        self._toggle_btn.setText(Icon.get("chevron_right" if self._collapsed else "chevron_left"))

    def _navigate(self, route: str) -> None:
        self._select(route)
        if self._is_function:
            self._on_navigate(route)
        else:
            self._on_navigate.emit(route)
        self.on_navigate.emit(route)

    def _select(self, route: str) -> None:
        self._active = route
        for key, btn in self._nav_buttons.items():
            btn.set_active(key == route)

    def setEnabled(self, enabled: bool) -> None:
        for btn in self.findChildren(QPushButton):
            btn.setEnabled(enabled)

    def _update_profile_ui(self) -> None:
        label = self._user_name or ""
        if self._is_authenticated:
            display_text = label if label else "Mi cuenta"
        else:
            display_text = "Iniciar sesión"

        text = "" if self._collapsed else display_text
        self._profile_btn.setToolTip(display_text)

        # Build the button content with icon + text using a layout
        # Clear any existing icon/text first
        self._profile_btn.setIcon(QIcon())
        self._profile_btn.setIconSize(QSize(24, 24))
        self._profile_btn.setFont(AppFont.body(12))
        from pyrolist.ui.design import tokens
        from PySide6.QtGui import QColor
        accent = tokens.CURRENT.accent
        c = QColor(accent)
        r, g, b, _ = c.getRgb()

        self._profile_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {tokens.CURRENT.text_secondary};
                border: none;
                border-radius: 12px;
                padding: 8px 10px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: rgba({r},{g},{b},0.08);
                color: {tokens.CURRENT.text_primary};
            }}
        """)

        # Cancel any active avatar loading task first
        if self._avatar_task and not self._avatar_task.done():
            self._avatar_task.cancel()
            self._avatar_task = None

        if self._is_authenticated and self._user_avatar:
            async def load_avatar() -> None:
                try:
                    path = await _image_cache.download(self._user_avatar)
                    if path:
                        pixmap = QPixmap(str(path))
                        if not pixmap.isNull():
                            # Scale and crop to circle
                            size = 24
                            scaled = pixmap.scaled(
                                size, size,
                                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                Qt.TransformationMode.SmoothTransformation,
                            )
                            # Center crop
                            x = (scaled.width() - size) // 2
                            y = (scaled.height() - size) // 2
                            cropped = scaled.copy(x, y, size, size)
                            # Clip to circle
                            from PySide6.QtCore import QRectF
                            circular = QPixmap(size, size)
                            circular.fill(Qt.GlobalColor.transparent)
                            painter = QPainter()
                            if painter.begin(circular):
                                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                                path_clip = QPainterPath()
                                path_clip.addEllipse(QRectF(0, 0, size, size))
                                painter.setClipPath(path_clip)
                                painter.drawPixmap(0, 0, cropped)
                                painter.end()
                            self._profile_btn.setIcon(QIcon(circular))
                            self._profile_btn.setText(text)
                            return
                except asyncio.CancelledError:
                    return
                except Exception as e:
                    from loguru import logger
                    logger.error(f"Avatar load failed: {e}")
                # Fallback: use person icon
                self._profile_btn.setIcon(Icon.icon("person", tokens.CURRENT.text_secondary, 20 if not self._collapsed else 22))
                self._profile_btn.setText(text)

            self._avatar_task = asyncio.create_task(load_avatar())
        else:
            # Not authenticated or no avatar — show icon + text
            self._profile_btn.setIcon(Icon.icon("person", tokens.CURRENT.text_secondary, 20 if not self._collapsed else 22))
            self._profile_btn.setText(text)

    def _on_profile_clicked(self) -> None:
        if self._is_authenticated:
            self._navigate("settings")
        else:
            self.on_login_click.emit()

    def _on_login_dialog_success(self, avatar_url: str = "") -> None:
        self._is_authenticated = True
        self._user_name = "YouTube Music"
        self._user_avatar = avatar_url
        self._update_profile_ui()
        self.auth_changed.emit(True)

    def update_auth_state(self, is_authenticated: bool, user_name: str = "", avatar_url: str = "") -> None:
        self._is_authenticated = is_authenticated
        self._user_name = user_name
        self._user_avatar = avatar_url
        self._update_profile_ui()

    def _update_header_style(self) -> None:
        from pyrolist.ui.design import tokens
        accent = tokens.CURRENT.accent
        if hasattr(self, '_app_title') and self._app_title:
            self._app_title.setStyleSheet(f"color: {accent}; background: transparent;")
        if hasattr(self, '_app_icon') and self._app_icon:
            if hasattr(self, '_app_icon_is_custom') and self._app_icon_is_custom:
                return
            if isinstance(self._app_icon, QLabel) and self._app_icon.text():
                self._app_icon.setStyleSheet(f"color: {accent}; background: transparent;")

    def _update_sidebar_styles(self) -> None:
        from pyrolist.ui.design import tokens
        bg_surface = tokens.CURRENT.bg_surface
        border_color = tokens.CURRENT.border
        text_secondary = tokens.CURRENT.text_secondary
        text_primary = tokens.CURRENT.text_primary
        
        self.setStyleSheet(f"""
            #navSidebar {{
                background-color: {bg_surface};
                border-right: 1px solid {border_color};
            }}
        """)
        
        if hasattr(self, '_toggle_btn'):
            self._toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    border-radius: 10px;
                    color: {text_secondary};
                }}
                QPushButton:hover {{
                    background: {tokens.CURRENT.bg_elevated};
                    color: {text_primary};
                }}
            """)
        self._update_header_style()
        self._update_profile_ui()

    def changeEvent(self, event) -> None:
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.Type.PaletteChange:
            if not getattr(self, '_in_style_change', False):
                self._in_style_change = True
                try:
                    self._update_sidebar_styles()
                finally:
                    self._in_style_change = False
        super().changeEvent(event)
