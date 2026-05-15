import sys
import asyncio
import qasync
import warnings
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from loguru import logger
from pyrolist.utils.vlc_check import check_vlc_available, show_vlc_error_and_exit, setup_vlc_env
from pyrolist.config.paths import AppDirs
from pyrolist.config.settings import AppSettings
from pyrolist.ui.main_window import MainWindow
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


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Pyrolist")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("pyrolist")

    setup_vlc_env()
    vlc_ok = check_vlc_available()
    if not vlc_ok:
        logger.warning("VLC no encontrado. La app funcionará pero no podrá reproducir música sin VLC.")

    AppDirs.setup()
    
    from PySide6.QtGui import QIcon
    icon_path = AppDirs.root / "assets" / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    from pyrolist.ui.design.fonts import load_fonts, AppFont
    load_fonts()
    app.setFont(AppFont.body())

    settings = AppSettings.load(AppDirs.settings_file)
    setup_logging()

    from qt_material import apply_stylesheet
    accent = settings.appearance.accent_color or "#7C4DFF"
    apply_stylesheet(
        app,
        theme="dark_purple.xml",
        extra={
            "primaryColor": accent,
            "primaryLightColor": accent,
            "secondaryColor": "#1E1E2E",
            "secondaryLightColor": "#2A2A3E",
            "secondaryDarkColor": "#13131F",
            "primaryTextColor": "#FFFFFF",
            "secondaryTextColor": "#B0B0C0",
            "density_scale": "-1",
            "pyside6": True,
            "linux": True,
        },
    )

    from pyrolist.ui.stylesheet import PYROLIST_QSS
    app.setStyleSheet(app.styleSheet() + PYROLIST_QSS)

    with qasync.QEventLoop(app) as loop:
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(main_async(app, settings, loop))
        except RuntimeError as e:
            if "Event loop stopped" not in str(e):
                raise


if __name__ == "__main__":
    main()