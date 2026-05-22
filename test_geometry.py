import sys
import asyncio
from PySide6.QtWidgets import QApplication
from pyrolist.config.settings import AppSettings
from pyrolist.ui.main_window import MainWindow

app = QApplication(sys.argv)
settings = AppSettings()
window = MainWindow(settings, event_loop=asyncio.new_event_loop())

def dump_geometry():
    print("MainWindow size:", window.size())
    print("content_area height:", window.findChild(type(window.centralWidget()), "contentArea").height())
    print("miniPlayer height:", window.mini_player.height())

from PySide6.QtCore import QTimer
QTimer.singleShot(1000, dump_geometry)
QTimer.singleShot(2000, app.quit)

app.exec()
