from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QWidget
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEngineScript
from PySide6.QtCore import Qt, Signal, QTimer, QUrl
import json
from loguru import logger
from pyrolist.config.paths import AppDirs


class WebLoginDialog(QDialog):
    login_successful = Signal(str)  # Emits avatar_url

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Iniciar sesión en YouTube Music")
        self.resize(1000, 700)
        self.setStyleSheet("background-color: #0F0F1A;")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Minimal header — thin strip with hint + close icon
        header = QWidget()
        header.setFixedHeight(32)
        header.setStyleSheet("background-color: #1A1A2E; border-bottom: 1px solid #2A2A3E;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 8, 0)

        hint = QLabel("Inicia sesión — la ventana se cerrará automáticamente")
        hint.setStyleSheet("color: #6B7280; font-family: Inter; font-size: 11px;")
        header_layout.addWidget(hint)
        header_layout.addStretch()

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setAutoDefault(False)
        self.btn_close.setDefault(False)
        self.btn_close.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #9CA3AF;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                color: #EF4444;
                background-color: rgba(239, 68, 68, 0.1);
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
        self._login_detected = False

        # Inject script to auto-grant Storage Access API (fixes "Permission denied" errors)
        storage_script = QWebEngineScript()
        storage_script.setName("pyrolist_storage_access")
        storage_script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        storage_script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        storage_script.setRunsOnSubFrames(True)
        storage_script.setSourceCode("""
            // Auto-grant Storage Access API to prevent cross-site cookie blocks
            Document.prototype.requestStorageAccess = function() { return Promise.resolve(); };
            Document.prototype.requestStorageAccessFor = function() { return Promise.resolve(); };
        """)
        self.view.page().scripts().insert(storage_script)

        self.cookie_store.cookieAdded.connect(self._on_cookie_added)
        self.view.loadFinished.connect(self._on_load_finished)

        self.layout.addWidget(self.view)

        self.view.load(QUrl("https://music.youtube.com"))

        # Periodic timer to re-check login status every 2 seconds
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(2000)
        self._poll_timer.timeout.connect(self._poll_login)
        self._poll_timer.start()

    def reject(self):
        self._poll_timer.stop()
        super().reject()

    def _on_cookie_added(self, cookie):
        domain = cookie.domain()
        if "youtube" in domain or "google" in domain:
            name = bytearray(cookie.name()).decode()
            value = bytearray(cookie.value()).decode()
            self.cookies[name] = value

    def _on_load_finished(self, ok):
        if ok:
            self._check_login()

    def _poll_login(self):
        if not self._login_detected:
            self._check_login()

    def _check_login(self):
        if self._login_detected:
            return

        js = """
        (() => {
            let img = document.querySelector('ytmusic-settings-button img') ||
                      document.querySelector('#avatar-btn img') ||
                      document.querySelector('img.yt-core-image--loaded[alt]');
            if (!img || !img.src) return '';
            let src = img.src;
            // Reject data: URIs and placeholder images
            if (src.startsWith('data:')) return '';
            if (!src.startsWith('http')) return '';
            return src;
        })()
        """
        self.view.page().runJavaScript(js, self._on_avatar_result)

    def _on_avatar_result(self, avatar_url):
        if self._login_detected:
            return
        if not avatar_url:
            return

        has_session = any(k in self.cookies for k in [
            "SAPISID", "__Secure-3PAPISID", "__Secure-1PAPISID"
        ])

        if has_session:
            self._login_detected = True
            self._poll_timer.stop()
            logger.info(f"Login detected. Avatar: {avatar_url}")
            # Now extract the user name by opening the account menu briefly
            self._detected_avatar = avatar_url
            self._extract_user_name()

    def _extract_user_name(self):
        """Click the settings button to reveal the account menu, read the name, then close it."""
        js = """
        new Promise((resolve) => {
            let btn = document.querySelector('ytmusic-settings-button');
            if (!btn) { resolve(''); return; }
            btn.click();
            setTimeout(() => {
                let nameEl = document.querySelector('ytmusic-active-account-header-renderer #name') ||
                             document.querySelector('#account-name') ||
                             document.querySelector('yt-formatted-string.ytd-active-account-header-renderer');
                let name = nameEl ? nameEl.textContent.trim() : '';
                // Close the menu
                btn.click();
                resolve(name);
            }, 400);
        });
        """
        self.view.page().runJavaScript(js, self._on_name_result)

    def _on_name_result(self, name):
        user_name = name if isinstance(name, str) else ""
        logger.info(f"User name extracted: '{user_name}'")
        self._save_cookies_and_close(avatar_url=self._detected_avatar, name=user_name)

    def _save_cookies_and_close(self, avatar_url="", name=""):
        # Build cookie string
        cookie_parts = []
        for name_key, value in self.cookies.items():
            cookie_parts.append(f"{name_key}={value}")

        cookie_str = "; ".join(cookie_parts)

        headers = {
            "cookie": cookie_str,
            "x-goog-authuser": "0",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "accept": "*/*",
            "origin": "https://music.youtube.com",
            "x-origin": "https://music.youtube.com",
            "authorization": "SAPISIDHASH 1"  # ytmusicapi 1.12+ needs this to detect AuthType.BROWSER
        }

        auth_file = AppDirs.config / "headers_auth.json"
        with open(auth_file, "w") as f:
            json.dump(headers, f, indent=4)

        # Save user profile
        profile_file = AppDirs.config / "user_profile.json"
        try:
            with open(profile_file, "w") as f:
                json.dump({"name": name, "avatar_url": avatar_url}, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save user profile: {e}")

        logger.info(f"Browser cookies saved successfully. Avatar: {avatar_url}")
        self.login_successful.emit(avatar_url)
        self.accept()
