from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from pyrolist.ui.design.fonts import AppFont
from pyrolist.ui.design.icons import Icon
from pyrolist.ui.screens.settings.about import AboutScreen
from pyrolist.ui.screens.settings.accounts import AccountsSettingsScreen
from pyrolist.ui.screens.settings.appearance import AppearanceSettingsScreen
from pyrolist.ui.screens.settings.equalizer import EqualizerSettingsScreen
from pyrolist.ui.screens.settings.player_settings import PlayerSettingsScreen
from pyrolist.ui.screens.settings.storage import StorageSettingsScreen
from pyrolist.ui.widgets.fade_stack import FadeStackedWidget


class SettingsScreen(QWidget):
    CATEGORIES = [
        ("palette", "Apariencia"),
        ("graphic_eq", "Reproductor"),
        ("equalizer", "Ecualizador"),
        ("person", "Cuentas"),
        ("storage", "Almacenamiento"),
        ("info", "Acerca de"),
    ]

    def __init__(self, yt_client, settings, on_settings_changed):
        super().__init__()
        self._yt = yt_client
        self.settings = settings
        self.on_settings_changed = on_settings_changed
        self._cat_buttons: list[QPushButton] = []
        self._build_ui()

    @property
    def yt(self):
        return self._yt

    @yt.setter
    def yt(self, client):
        self._yt = client
        if hasattr(self, "accounts_screen"):
            self.accounts_screen.yt = client

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("""
            QWidget {
                background-color: #10101E;
                border-right: 1px solid rgba(167,139,250,0.08);
            }
        """)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 22, 12, 22)
        side_layout.setSpacing(4)

        title = QLabel("Ajustes")
        title.setFont(AppFont.heading(18))
        title.setStyleSheet("color: #F1F0FF; padding: 0 8px 12px 8px; background: transparent;")
        side_layout.addWidget(title)

        for i, (icon_name, label) in enumerate(self.CATEGORIES):
            button = self._make_cat_button(icon_name, label, i)
            self._cat_buttons.append(button)
            side_layout.addWidget(button)
        side_layout.addStretch()
        root.addWidget(sidebar)

        self.stack = FadeStackedWidget()
        self.stack.setObjectName("settingsStack")
        self.stack.setStyleSheet("#settingsStack { background-color: #0A0A14; }")
        root.addWidget(self.stack)

        self.accounts_screen = AccountsSettingsScreen(self.yt, self.settings, self.on_settings_changed)
        pages = [
            AppearanceSettingsScreen(self.settings, self.on_settings_changed),
            PlayerSettingsScreen(self.settings, self.on_settings_changed),
            EqualizerSettingsScreen(self.settings, self.on_settings_changed),
            self.accounts_screen,
            StorageSettingsScreen(self.settings),
            AboutScreen(),
        ]
        for page in pages:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll.setStyleSheet("QScrollArea { background: #0A0A14; border: none; }")
            wrapper = QWidget()
            wrapper.setStyleSheet("background: #0A0A14;")
            wrapper_layout = QVBoxLayout(wrapper)
            wrapper_layout.setContentsMargins(34, 26, 34, 26)
            wrapper_layout.addWidget(page)
            wrapper_layout.addStretch()
            scroll.setWidget(wrapper)
            self.stack.addWidget(scroll)

        self._select_category(0)

    def _make_cat_button(self, icon_name: str, label: str, index: int) -> QPushButton:
        button = QPushButton()
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedHeight(40)
        row = QHBoxLayout(button)
        row.setContentsMargins(12, 0, 12, 0)
        row.setSpacing(10)
        icon = Icon.label(icon_name, 18, "#9B9BC0")
        text = QLabel(label)
        text.setFont(AppFont.body(13))
        icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        text.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        row.addWidget(icon)
        row.addWidget(text)
        row.addStretch()
        button._icon_label = icon
        button._text_label = text
        button.clicked.connect(lambda checked=False, i=index: self._select_category(i))
        self._style_cat_button(button, False)
        return button

    def _style_cat_button(self, button: QPushButton, active: bool) -> None:
        color = "#A78BFA" if active else "#9B9BC0"
        bg = "rgba(167,139,250,0.15)" if active else "transparent"
        button._icon_label.setStyleSheet(f"color: {color}; background: transparent;")
        button._text_label.setStyleSheet(f"color: {color}; background: transparent; font-weight: {'700' if active else '500'};")
        button.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background: rgba(167,139,250,0.09);
            }}
        """)

    def _select_category(self, index: int) -> None:
        for i, button in enumerate(self._cat_buttons):
            active = i == index
            button.setChecked(active)
            self._style_cat_button(button, active)
        self.stack.setCurrentIndexAnimated(index)

