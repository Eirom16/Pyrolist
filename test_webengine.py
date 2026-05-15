from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile
import sys

class WebLoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Music Login")
        self.resize(800, 600)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.view = QWebEngineView()
        self.profile = QWebEngineProfile.defaultProfile()
        self.cookie_store = self.profile.cookieStore()
        
        self.cookies = {}
        self.cookie_store.cookieAdded.connect(self._on_cookie_added)
        
        self.layout.addWidget(self.view)
        
        # Open YouTube Music
        self.view.load("https://music.youtube.com")
        
    def _on_cookie_added(self, cookie):
        domain = cookie.domain()
        if "youtube.com" in domain or "google.com" in domain:
            name = bytearray(cookie.name()).decode()
            value = bytearray(cookie.value()).decode()
            self.cookies[name] = value
            
            # Print specifically the ones we need
            if name in ["SAPISID", "__Secure-3PAPISID"]:
                print(f"GOT COOKIE: {name} = {value}")

if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    dialog = WebLoginDialog()
    # We won't exec_ it in headless mode, just check syntax
    print("Syntax OK")
