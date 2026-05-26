# Monkey-patch to fix PySide6 6.7+ event dispatcher compatibility with qasync
try:
    from PySide6.QtCore import QAbstractEventDispatcher, QEventLoop
    orig_process_events = QAbstractEventDispatcher.processEvents

    def patched_process_events(self, flags):
        if not isinstance(flags, QEventLoop.ProcessEventsFlag):
            try:
                flags = QEventLoop.ProcessEventsFlag(int(flags))
            except Exception:
                pass
        return orig_process_events(self, flags)

    QAbstractEventDispatcher.processEvents = patched_process_events
except Exception:
    pass

import sys
import subprocess

# Prevenir parpadeo de ventanas de consola secundarias en Windows
if sys.platform.startswith('win'):
    _orig_popen_init = subprocess.Popen.__init__
    def _patched_popen_init(self, *args, **kwargs):
        creationflags = kwargs.get('creationflags', 0)
        kwargs['creationflags'] = creationflags | 0x08000000 # CREATE_NO_WINDOW
        _orig_popen_init(self, *args, **kwargs)
    subprocess.Popen.__init__ = _patched_popen_init

import asyncio
import qasync
import warnings
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from loguru import logger
from pyrolist import __version__
from pyrolist.utils.vlc_check import check_vlc_available, show_vlc_error_and_exit, setup_vlc_env
from pyrolist.config.paths import AppDirs
from pyrolist.config.settings import AppSettings
from pyrolist.db.database import init_db

warnings.filterwarnings("ignore")


def setup_logging() -> None:
    log_file = AppDirs.logs / "pyrolist_{time:YYYY-MM-DD}.log"
    logger.add(
        log_file,
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{line} | {message}",
    )


async def main_async(app: QApplication, settings: AppSettings, loop: qasync.QEventLoop) -> None:
    loop.set_exception_handler(lambda loop, ctx: None)
    
    await init_db()
    from pyrolist.ui.main_window import MainWindow
    window = MainWindow(settings, loop)
    window.show()

    quit_future = loop.create_future()

    def cleanup():
        if not quit_future.done():
            quit_future.set_result(None)

    app.aboutToQuit.connect(cleanup)

    try:
        await quit_future
    except Exception:
        pass
    finally:
        from pyrolist.db.database import get_engine
        try:
            engine = get_engine()
            if engine:
                logger.info("Disposing database engine...")
                await engine.dispose()
                logger.info("Database engine successfully disposed.")
        except Exception as e:
            logger.warning(f"Error disposing database engine: {e}")



def main() -> None:
    import os
    # En Linux congelado (AppImage), forzar xcb y renderizado por software
    # para evitar fallos de Wayland EGL y de GLX dentro del sandbox del AppImage
    if sys.platform.startswith('linux') and getattr(sys, 'frozen', False):
        if not os.environ.get("QT_QPA_PLATFORM"):
            os.environ["QT_QPA_PLATFORM"] = "xcb"
        # Forzar renderizado por software para Qt Quick (QQuickWidget)
        # El AppImage no puede resolver los drivers GLX/EGL del host correctamente
        os.environ.setdefault("QT_QUICK_BACKEND", "software")
        # Deshabilitar GPU en QtWebEngine/Chromium embebido
        os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")
            
    app = QApplication(sys.argv)
    app.setApplicationName("Pyrolist")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("pyrolist")
    app.setDesktopFileName("pyrolist")

    setup_vlc_env()
    vlc_ok = check_vlc_available()
    if not vlc_ok:
        logger.warning("VLC no encontrado. La app funcionará pero no podrá reproducir música sin VLC.")

    AppDirs.setup()
    
    from PySide6.QtGui import QIcon, QPixmapCache
    QPixmapCache.setCacheLimit(102400)  # 100 MB cache for covers
    icon_path = AppDirs.root / "assets" / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    from pyrolist.ui.design.fonts import load_fonts, AppFont
    load_fonts()
    app.setFont(AppFont.body())

    settings = AppSettings.load(AppDirs.settings_file)
    setup_logging()

    # Styles are applied immediately within MainWindow during initialization


    with qasync.QEventLoop(app) as loop:
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(main_async(app, settings, loop))
        except RuntimeError as e:
            if "Event loop stopped" not in str(e):
                raise


if __name__ == "__main__":
    main()
