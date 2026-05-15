from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QObject, Slot


class SystemTray(QSystemTrayIcon):

    def __init__(self, parent, on_show, on_play_pause, on_next, on_quit):
        super().__init__(parent)
        self.on_show = on_show
        self.on_play_pause = on_play_pause
        self.on_next = on_next
        self.on_quit = on_quit
        
        self.setIcon(QIcon.fromTheme("media-playback-start"))
        self.setToolTip("Pyrolist")
        
        self._build_menu()

    def _build_menu(self):
        menu = QMenu()
        
        show_action = QAction("Mostrar Pyrolist", menu)
        show_action.triggered.connect(self.on_show)
        menu.addAction(show_action)
        
        menu.addSeparator()
        
        play_pause_action = QAction("Reproducir/Pausar", menu)
        play_pause_action.triggered.connect(self.on_play_pause)
        menu.addAction(play_pause_action)
        
        next_action = QAction("Siguiente", menu)
        next_action.triggered.connect(self.on_next)
        menu.addAction(next_action)
        
        menu.addSeparator()
        
        quit_action = QAction("Salir", menu)
        quit_action.triggered.connect(self.on_quit)
        menu.addAction(quit_action)
        
        self.setContextMenu(menu)

    @Slot()
    def update_play_state(self, is_playing: bool):
        icon_name = "media-playback-pause" if is_playing else "media-playback-start"
        self.setIcon(QIcon.fromTheme(icon_name))