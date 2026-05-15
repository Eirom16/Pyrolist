from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QWidget
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile
from PySide6.QtCore import Qt, Signal
import json
from loguru import logger
from pyrolist.config.paths import AppDirs
import time

class WebLoginDialog(QDialog):
    login_successful = Signal(str)  # Emits avatar_url

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Iniciar sesión en YouTube Music")
        self.resize(1000, 700)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Header
        header = QWidget()
        header.setStyleSheet("background-color: #1A1A2E; border-bottom: 1px solid #2A2A3E;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        
        title = QLabel("Inicia sesión. La ventana se cerrará automáticamente al terminar.")
        title.setStyleSheet("color: #FFFFFF; font-family: Inter; font-size: 14px; font-weight: 500;")
        header_layout.addWidget(title)
        
        self.btn_close = QPushButton("Cerrar manualmente")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setAutoDefault(False)
        self.btn_close.setDefault(False)
        self.btn_close.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: #3A3A4E;
                color: white;
                border-radius: 6px;
                padding: 6px 16px;
                font-family: Inter;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #4A4A5E;
            }
        """)
        self.btn_close.clicked.connect(self.reject)
        header_layout.addWidget(self.btn_close)
        
        self.layout.addWidget(header)
        
        # Web View
        self.view = QWebEngineView()
        self.profile = QWebEngineProfile.defaultProfile()
        self.cookie_store = self.profile.cookieStore()
        
        self.cookies = {}
        self.cookie_store.cookieAdded.connect(self._on_cookie_added)
        self.view.loadFinished.connect(self._check_login_status)
        
        self.layout.addWidget(self.view)
        
        self.view.load("https://music.youtube.com")
        self._check_timer = None
        
    def _on_cookie_added(self, cookie):
        domain = cookie.domain()
        if "youtube" in domain or "google" in domain:
            name = bytearray(cookie.name()).decode()
            value = bytearray(cookie.value()).decode()
            self.cookies[name] = value

    def _check_login_status(self, ok):
        if not ok: return
        js = "document.querySelector('ytmusic-settings-button img') ? document.querySelector('ytmusic-settings-button img').src : ''"
        self.view.page().runJavaScript(js, self._on_js_result)
        
    def _on_js_result(self, result):
        if result and "SAPISID" in self.cookies:
            self._save_cookies_and_close(avatar_url=result)

    def _save_cookies_and_close(self, avatar_url=""):
        # Build cookie string
        cookie_parts = []
        for name, value in self.cookies.items():
            cookie_parts.append(f"{name}={value}")
        
        cookie_str = "; ".join(cookie_parts)
        
        # We have enough auth info, let's create headers_auth.json
        headers = {
            "cookie": cookie_str,
            "x-goog-authuser": "0",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "accept": "*/*",
            "origin": "https://music.youtube.com",
            "x-origin": "https://music.youtube.com",
            "authorization": "SAPISIDHASH 1" # ytmusicapi 1.12+ needs this to detect AuthType.BROWSER
        }
        
        auth_file = AppDirs.config / "headers_auth.json"
        with open(auth_file, "w") as f:
            json.dump(headers, f, indent=4)
            
        logger.info(f"Browser cookies saved successfully. Avatar: {avatar_url}")
        self.login_successful.emit(avatar_url)
        self.accept()
