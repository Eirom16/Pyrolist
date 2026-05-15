from __future__ import annotations

import asyncio

from PySide6.QtCore import QEasingCurve, QSize, Qt, QPropertyAnimation, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from pyrolist.ui.design.fonts import AppFont
from pyrolist.ui.design.icons import Icon


NAV_ITEMS = [
    ("home", "home", "Inicio"),
    ("library", "library_music", "Biblioteca"),
    ("history", "history", "Historial"),
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
        color = "#A78BFA" if active else "#9B9BC0"
        weight = "700" if active else "500"
        self.icon_label.setStyleSheet(f"color: {color}; background: transparent;")
        self.text_label.setStyleSheet(f"color: {color}; background: transparent; font-weight: {weight};")
        bg = "rgba(167,139,250,0.14)" if active else "transparent"
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                border: none;
                border-radius: 12px;
                text-align: left;
                padding: 0;
            }}
            QPushButton:hover {{
                background: rgba(167,139,250,0.09);
            }}
        """)


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
        self.setStyleSheet("""
            #navSidebar {
                background-color: #10101E;
                border-right: 1px solid rgba(167,139,250,0.08);
            }
        """)
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
        else:
            self._app_icon = Icon.label("music_note", 26, "#A78BFA")
            
        self._app_title = QLabel("Pyrolist")
        self._app_title.setFont(AppFont.heading(18))
        self._app_title.setStyleSheet("color: #A78BFA; background: transparent;")
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
        self._toggle_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 10px;
                color: #6B6B9B;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.05);
                color: #F1F0FF;
            }
        """)
        self._toggle_btn.clicked.connect(self.toggle_collapse)
        layout.addWidget(self._toggle_btn)

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
        self._profile_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #9B9BC0;
                border: none;
                border-radius: 12px;
                padding: 8px 10px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: rgba(167,139,250,0.08);
                color: #F1F0FF;
            }
        """)

        if self._is_authenticated and self._user_avatar:
            async def load_avatar() -> None:
                try:
                    from pyrolist.utils.image_cache import ImageCache
                    path = await ImageCache().download(self._user_avatar)
                    if path:
                        pixmap = QPixmap(str(path))
                        if not pixmap.isNull():
                            scaled = pixmap.scaled(
                                24, 24,
                                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                Qt.TransformationMode.SmoothTransformation,
                            )
                            self._profile_btn.setIcon(QIcon(scaled))
                            self._profile_btn.setText(text)
                            return
                except Exception:
                    pass
                # Fallback: use person icon as text
                icon_char = Icon.get("person")
                if text:
                    self._profile_btn.setText(f"  {text}")
                    self._profile_btn.setIcon(QIcon())
                else:
                    self._profile_btn.setText(icon_char)
                    self._profile_btn.setFont(Icon.font(22))

            asyncio.create_task(load_avatar())
        else:
            # Not authenticated or no avatar — show icon + text
            icon_char = Icon.get("person")
            if self._collapsed:
                self._profile_btn.setText(icon_char)
                self._profile_btn.setFont(Icon.font(22))
            else:
                self._profile_btn.setText(f"  {display_text}")
                # Create a pixmap icon from the material font for the person icon
                from PySide6.QtGui import QPainter, QColor, QFont as QFontClass
                pix = QPixmap(24, 24)
                pix.fill(Qt.GlobalColor.transparent)
                painter = QPainter(pix)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setPen(QColor("#9B9BC0"))
                painter.setFont(Icon.font(20))
                painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, icon_char)
                painter.end()
                self._profile_btn.setIcon(QIcon(pix))

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
