# PROMPT COMPLETO — PYROLIST
## Cliente Python de YouTube Music · PySide6 + Qt · Linux (x86_64 / ARM64)
## Aplicación desde cero con todas las funciones de Metrolist

---

## ROL Y CONTEXTO

Eres un ingeniero Python experto en PySide6, arquitectura de aplicaciones de escritorio, APIs de Google, procesamiento de audio y diseño de interfaces modernas. Tu tarea es construir **desde cero** una aplicación de escritorio completa para escuchar YouTube Music llamada **Pyrolist**, con todas las funcionalidades del cliente Android Metrolist. El entorno de desarrollo y objetivo inicial es **Linux** (Ubuntu/Debian/Arch/Fedora, x86_64 y ARM64).

---

## REGLAS DE IMPLEMENTACIÓN NO NEGOCIABLES

1. **Nunca bloquear el hilo de UI.** Toda operación de red, base de datos o disco se ejecuta con `@asyncSlot` de qasync o en un `QThread` con `QRunnable`. Una UI que se congela es un fallo crítico.
2. **Código puro Python.** Sin archivos `.ui` de Qt Designer. Todo el layout se construye programáticamente.
3. **qasync para asyncio + Qt.** No usar `QtAsyncio` de PySide6 — tiene problemas conocidos con operaciones de red (DNS, sockets). qasync es la solución estándar de producción.
4. **Un módulo = una responsabilidad.** No mezclar lógica de negocio con lógica de UI en el mismo archivo.
5. **Primero Linux, siempre.** No añadir código condicional de Windows hasta que Linux funcione perfectamente.

---

## STACK TECNOLÓGICO COMPLETO

```
# UI y event loop
PySide6>=6.7.0           # Qt6 bindings oficiales (LGPL)
qasync>=0.27.0           # asyncio + Qt event loop integrado
qt-material>=2.14        # Temas Material Design para PySide6

# YouTube Music
ytmusicapi>=1.11.5       # API interna de YouTube Music con OAuth
yt-dlp>=2025.1.1         # Extracción de URLs de stream

# Audio
python-vlc>=3.0.21       # Reproducción vía libvlc

# Base de datos
sqlalchemy[asyncio]>=2.0
aiosqlite>=0.20
alembic>=1.13

# Configuración
pydantic>=2.7
tomli-w>=1.0

# Red
httpx[http2]>=0.27

# Letras
syncedlyrics>=0.7

# Integraciones
pylast>=5.3              # Last.fm scrobbling
pypresence>=4.3          # Discord Rich Presence

# Sistema
dbus-python>=1.3         # MPRIS2 en Linux
pystray>=0.19            # System tray
pillow>=10.0             # Imágenes y artwork
loguru>=0.7              # Logging
```

**Instalación de dependencias del sistema (Linux):**
```bash
# Debian/Ubuntu
sudo apt install vlc libvlc-dev python3-dbus

# Fedora
sudo dnf install vlc vlc-devel python3-dbus

# Arch
sudo pacman -S vlc python-dbus
```

---

## DETECCIÓN DE VLC AL ARRANCAR

**Esta es la primera cosa que ejecuta la app, antes de mostrar cualquier ventana.**

```python
# src/pyrolist/utils/vlc_check.py
import sys
from loguru import logger


def check_vlc_available() -> bool:
    """
    Verifica que libvlc está disponible en el sistema.
    Si no lo está, muestra un diálogo de error con instrucciones
    específicas para la distro detectada y termina la app.
    """
    try:
        import vlc
        instance = vlc.Instance("--quiet")
        if instance is None:
            raise RuntimeError("VLC instance returned None")
        instance.release()
        logger.info("VLC detected successfully")
        return True
    except Exception as e:
        logger.error(f"VLC not available: {e}")
        return False


def get_vlc_install_command() -> str:
    """Detecta la distro y devuelve el comando de instalación correcto."""
    import platform
    import os

    if not platform.system() == "Linux":
        return "Instala VLC desde https://www.videolan.org"

    # Detectar package manager
    if os.path.exists("/usr/bin/apt") or os.path.exists("/usr/bin/apt-get"):
        return "sudo apt install vlc"
    elif os.path.exists("/usr/bin/dnf"):
        return "sudo dnf install vlc"
    elif os.path.exists("/usr/bin/pacman"):
        return "sudo pacman -S vlc"
    elif os.path.exists("/usr/bin/zypper"):
        return "sudo zypper install vlc"
    elif os.path.exists("/usr/bin/emerge"):
        return "sudo emerge media-video/vlc"
    else:
        return "Instala VLC desde tu gestor de paquetes o https://www.videolan.org"


def show_vlc_error_and_exit(app) -> None:
    """Muestra un QMessageBox con las instrucciones y termina."""
    from PySide6.QtWidgets import QMessageBox
    from PySide6.QtGui import QIcon

    cmd = get_vlc_install_command()
    msg = QMessageBox()
    msg.setWindowTitle("VLC no encontrado — Pyrolist")
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setText("Pyrolist necesita VLC para reproducir música.")
    msg.setInformativeText(
        f"VLC (libvlc) no está instalado en tu sistema.\n\n"
        f"Instálalo con el siguiente comando:\n\n"
        f"    {cmd}\n\n"
        f"Luego reinicia Pyrolist."
    )
    msg.setDetailedText(
        "Pyrolist usa libvlc para:\n"
        "• Reproducir streams de audio de YouTube Music\n"
        "• Aplicar el ecualizador paramétrico\n"
        "• Controlar velocidad, tono y volumen\n\n"
        "Sin libvlc, la reproducción de audio es imposible."
    )
    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg.exec()
    sys.exit(1)
```

---

## ESTRUCTURA DE DIRECTORIOS COMPLETA

```
pyrolist/
├── pyproject.toml
├── README.md
├── assets/
│   ├── icon.png               ← 512×512px
│   ├── icon.svg
│   └── placeholder_artwork.png
│
└── src/
    └── pyrolist/
        ├── __init__.py
        ├── main.py             ← QApplication + qasync entry point
        │
        ├── api/
        │   ├── __init__.py
        │   ├── youtube_music.py    ← ytmusicapi async wrapper
        │   ├── stream_extractor.py ← yt-dlp stream URL extraction
        │   ├── lyrics.py           ← syncedlyrics + LRCLib directo
        │   ├── lastfm.py           ← pylast scrobbling
        │   └── discord_rpc.py      ← pypresence rich presence
        │
        ├── audio/
        │   ├── __init__.py
        │   ├── player.py           ← MusicPlayer (python-vlc)
        │   ├── queue.py            ← PlayQueue: normal/shuffle/repeat
        │   ├── equalizer.py        ← EQ 10 bandas + 10 presets
        │   ├── sleep_timer.py      ← temporizador de apagado
        │   └── crossfade.py        ← transición entre canciones
        │
        ├── db/
        │   ├── __init__.py
        │   ├── database.py         ← AsyncEngine SQLAlchemy
        │   ├── models.py           ← Song, Album, Artist, Playlist,
        │   │                          PlayHistory, Download, CachedArtwork
        │   ├── repository.py       ← capa de acceso a datos (async)
        │   └── migrations/         ← scripts Alembic
        │
        ├── config/
        │   ├── __init__.py
        │   ├── settings.py         ← AppSettings con Pydantic
        │   ├── paths.py            ← AppDirs XDG Linux
        │   └── themes.py           ← paletas, colores dinámicos, QSS
        │
        ├── system/
        │   ├── __init__.py
        │   ├── mpris.py            ← MPRIS2 vía dbus-python
        │   ├── tray.py             ← QSystemTrayIcon + menú
        │   ├── media_keys.py       ← teclas multimedia globales
        │   └── network.py          ← monitoreo de conectividad
        │
        ├── ui/
        │   ├── __init__.py
        │   ├── main_window.py      ← QMainWindow principal
        │   ├── stylesheet.py       ← QSS completo de la app
        │   │
        │   ├── widgets/            ← componentes reutilizables
        │   │   ├── __init__.py
        │   │   ├── clickable_label.py
        │   │   ├── artwork_widget.py
        │   │   ├── song_card.py
        │   │   ├── album_card.py
        │   │   ├── artist_card.py
        │   │   ├── playlist_card.py
        │   │   ├── mini_player.py
        │   │   ├── full_player.py
        │   │   ├── lyrics_view.py
        │   │   ├── queue_panel.py
        │   │   ├── nav_sidebar.py
        │   │   ├── search_bar.py
        │   │   ├── scroll_label.py   ← texto con scroll automático
        │   │   ├── loading_spinner.py
        │   │   └── card_grid.py      ← grid responsivo de tarjetas
        │   │
        │   └── screens/
        │       ├── __init__.py
        │       ├── welcome.py        ← pantalla inicial / setup OAuth
        │       ├── home.py
        │       ├── search.py
        │       ├── library.py
        │       ├── album.py
        │       ├── artist.py
        │       ├── playlist.py
        │       ├── history.py
        │       ├── stats.py
        │       ├── downloads.py
        │       └── settings/
        │           ├── __init__.py
        │           ├── appearance.py
        │           ├── player_settings.py
        │           ├── equalizer.py
        │           ├── accounts.py   ← Google OAuth, Last.fm
        │           ├── storage.py
        │           └── about.py
        │
        └── utils/
            ├── __init__.py
            ├── vlc_check.py        ← detección VLC al arrancar
            ├── color_extractor.py  ← color dominante del artwork
            ├── lrc_parser.py       ← parser .lrc sincronizado
            ├── image_cache.py      ← caché de artwork en disco
            ├── time_utils.py
            └── worker.py           ← QThread worker base
```

---

## MÓDULO CENTRAL: `main.py`

```python
# src/pyrolist/main.py
import sys
import asyncio
import qasync
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from loguru import logger
from pyrolist.utils.vlc_check import check_vlc_available, show_vlc_error_and_exit
from pyrolist.config.paths import AppDirs
from pyrolist.config.settings import AppSettings
from pyrolist.ui.main_window import MainWindow


def setup_logging() -> None:
    from pyrolist.config.paths import AppDirs
    log_file = AppDirs.logs / "pyrolist_{time:YYYY-MM-DD}.log"
    logger.add(
        log_file,
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{line} | {message}",
    )


async def main_async(app: QApplication, settings: AppSettings) -> None:
    window = MainWindow(settings)
    window.show()

    # Mantener el loop corriendo hasta que la ventana se cierre
    close_event = asyncio.Event()
    app.aboutToQuit.connect(close_event.set)
    await close_event.wait()


def main() -> None:
    # Crear QApplication antes de cualquier widget
    app = QApplication(sys.argv)
    app.setApplicationName("Pyrolist")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("pyrolist")

    # Verificar VLC ANTES de mostrar cualquier otra ventana
    if not check_vlc_available():
        show_vlc_error_and_exit(app)

    # Setup
    AppDirs.setup()
    setup_logging()
    settings = AppSettings.load(AppDirs.settings_file)

    # Aplicar tema Material
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

    # Aplicar QSS adicional de Pyrolist sobre qt-material
    from pyrolist.ui.stylesheet import PYROLIST_QSS
    app.setStyleSheet(app.styleSheet() + PYROLIST_QSS)

    # Inicializar qasync y correr
    with qasync.QEventLoop(app) as loop:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main_async(app, settings))


if __name__ == "__main__":
    main()
```

---

## MÓDULO: `config/paths.py`

```python
# src/pyrolist/config/paths.py
import os
from pathlib import Path


class _AppDirs:
    _name = "pyrolist"

    @property
    def config(self) -> Path:
        base = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
        return Path(base) / self._name

    @property
    def data(self) -> Path:
        base = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))
        return Path(base) / self._name

    @property
    def cache(self) -> Path:
        base = os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))
        return Path(base) / self._name

    @property
    def artwork_cache(self) -> Path:
        return self.cache / "artwork"

    @property
    def downloads(self) -> Path:
        return self.data / "downloads"

    @property
    def database(self) -> Path:
        return self.data / "pyrolist.db"

    @property
    def settings_file(self) -> Path:
        return self.config / "settings.toml"

    @property
    def oauth_file(self) -> Path:
        return self.config / "oauth.json"

    @property
    def logs(self) -> Path:
        return self.data / "logs"

    def setup(self) -> None:
        for d in [self.config, self.data, self.cache,
                  self.artwork_cache, self.downloads, self.logs]:
            d.mkdir(parents=True, exist_ok=True)


AppDirs = _AppDirs()
```

---

## MÓDULO: `config/settings.py`

```python
# src/pyrolist/config/settings.py
from __future__ import annotations
from pathlib import Path
from pydantic import BaseModel, Field
import tomllib
import tomli_w


class AppearanceSettings(BaseModel):
    theme_mode: str = "dark"
    accent_color: str = "#7C4DFF"
    use_dynamic_color: bool = True     # cambia el acento según el artwork
    show_artwork_blur_bg: bool = True  # fondo difuminado en el full player
    compact_sidebar: bool = False      # sidebar colapsada a íconos
    font_size: int = 13

class PlayerSettings(BaseModel):
    volume: int = 80
    normalize_audio: bool = True
    skip_silence: bool = False
    crossfade_enabled: bool = True
    crossfade_duration_sec: int = 5
    resume_on_startup: bool = True
    gapless_playback: bool = True
    stop_on_close: bool = False        # True = para al cerrar ventana

class EqualizerSettings(BaseModel):
    enabled: bool = False
    preamp: float = 0.0
    # 10 bandas: 60Hz, 170Hz, 310Hz, 600Hz, 1kHz, 3kHz, 6kHz, 12kHz, 14kHz, 16kHz
    bands: list[float] = Field(default_factory=lambda: [0.0] * 10)
    preset_name: str = "Flat"

class NetworkSettings(BaseModel):
    proxy_url: str | None = None
    stream_quality: str = "best"       # "best", "medium", "low"
    preload_next: bool = True

class IntegrationsSettings(BaseModel):
    lastfm_enabled: bool = False
    lastfm_session_key: str = ""
    lastfm_api_key: str = ""
    lastfm_api_secret: str = ""
    discord_rpc_enabled: bool = False
    mpris_enabled: bool = True         # siempre True en Linux por defecto

class AppSettings(BaseModel):
    google_client_id: str = ""
    google_client_secret: str = ""
    appearance: AppearanceSettings = Field(default_factory=AppearanceSettings)
    player: PlayerSettings = Field(default_factory=PlayerSettings)
    equalizer: EqualizerSettings = Field(default_factory=EqualizerSettings)
    network: NetworkSettings = Field(default_factory=NetworkSettings)
    integrations: IntegrationsSettings = Field(default_factory=IntegrationsSettings)
    language: str = "es"
    last_video_id: str | None = None   # para reanudar al iniciar

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            tomli_w.dump(self.model_dump(), f)

    @classmethod
    def load(cls, path: Path) -> AppSettings:
        if not path.exists():
            return cls()
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
            return cls(**data)
        except Exception:
            return cls()
```

---

## MÓDULO: `api/youtube_music.py`

```python
# src/pyrolist/api/youtube_music.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
from ytmusicapi import YTMusic, OAuthCredentials
from loguru import logger
from pyrolist.config.paths import AppDirs
from pyrolist.config.settings import AppSettings


class YouTubeMusicClient:
    """
    Wrapper async de ytmusicapi.
    ytmusicapi es síncrono — se ejecuta en ThreadPoolExecutor
    para no bloquear nunca el event loop de Qt/asyncio.
    """

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self._client: YTMusic | None = None
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="ytm")

    @property
    def is_authenticated(self) -> bool:
        return self._client is not None

    async def _run(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, lambda: func(*args, **kwargs)
        )

    # ─── AUTENTICACIÓN ────────────────────────────────────────────────

    def load_existing_auth(self) -> bool:
        """Carga sesión OAuth guardada. Devuelve True si tiene éxito."""
        if not AppDirs.oauth_file.exists():
            return False
        if not self.settings.google_client_id:
            return False
        try:
            creds = OAuthCredentials(
                client_id=self.settings.google_client_id,
                client_secret=self.settings.google_client_secret,
            )
            self._client = YTMusic(
                str(AppDirs.oauth_file),
                oauth_credentials=creds,
            )
            logger.info("Loaded existing YouTube Music OAuth session")
            return True
        except Exception as e:
            logger.warning(f"Failed to load existing auth: {e}")
            return False

    async def start_device_flow(self) -> dict:
        """
        Paso 1 del OAuth Device Flow.
        Devuelve: {user_code, verification_url, device_code, expires_in}
        La UI debe mostrar user_code y la URL al usuario.
        """
        creds = OAuthCredentials(
            client_id=self.settings.google_client_id,
            client_secret=self.settings.google_client_secret,
        )
        result = await self._run(creds.get_code)
        logger.info(f"OAuth Device Flow started. Code: {result.get('user_code')}")
        return result

    async def poll_device_token(self, device_code: str) -> bool:
        """
        Paso 2: polling cada 5s hasta que el usuario autorice.
        Devuelve True cuando el token es obtenido y guardado.
        """
        creds = OAuthCredentials(
            client_id=self.settings.google_client_id,
            client_secret=self.settings.google_client_secret,
        )
        try:
            token = await self._run(creds.get_token_from_code, device_code)
            # Guardar token en disco
            from ytmusicapi.auth.oauth import OAuthToken
            OAuthToken(**token).write_to(str(AppDirs.oauth_file))
            # Inicializar cliente
            self._client = YTMusic(
                str(AppDirs.oauth_file),
                oauth_credentials=creds,
            )
            logger.info("OAuth authentication successful")
            return True
        except Exception:
            return False

    def logout(self) -> None:
        self._client = None
        if AppDirs.oauth_file.exists():
            AppDirs.oauth_file.unlink()
        logger.info("Logged out from YouTube Music")

    # ─── BÚSQUEDA Y CATÁLOGO ──────────────────────────────────────────

    async def search(
        self, query: str,
        filter: str | None = None,   # 'songs','albums','artists','playlists','videos'
        limit: int = 20
    ) -> list:
        return await self._run(
            self._client.search, query, filter=filter, limit=limit
        )

    async def search_suggestions(self, query: str) -> list[str]:
        return await self._run(self._client.get_search_suggestions, query)

    async def get_home(self, limit: int = 6) -> list:
        return await self._run(self._client.get_home, limit=limit)

    async def get_song(self, video_id: str) -> dict:
        return await self._run(self._client.get_song, video_id)

    async def get_album(self, browse_id: str) -> dict:
        return await self._run(self._client.get_album, browse_id)

    async def get_album_browse_id(self, album_id: str) -> str:
        return await self._run(self._client.get_album_browse_id, album_id)

    async def get_artist(self, channel_id: str) -> dict:
        return await self._run(self._client.get_artist, channel_id)

    async def get_artist_albums(self, channel_id: str, params: str) -> list:
        return await self._run(self._client.get_artist_albums, channel_id, params)

    async def get_playlist(self, playlist_id: str, limit: int = 100) -> dict:
        return await self._run(
            self._client.get_playlist, playlist_id, limit=limit
        )

    async def get_watch_playlist(self, video_id: str, limit: int = 25) -> dict:
        """Radio/mix generado a partir de una canción (para autoplay)."""
        return await self._run(
            self._client.get_watch_playlist, videoId=video_id, limit=limit
        )

    async def get_charts(self, country: str = "ZZ") -> dict:
        return await self._run(self._client.get_charts, country=country)

    async def get_explore(self) -> dict:
        return await self._run(self._client.get_explore)

    async def get_mood_categories(self) -> dict:
        return await self._run(self._client.get_mood_categories)

    async def get_mood_playlists(self, params: str) -> list:
        return await self._run(self._client.get_mood_playlists, params)

    # ─── BIBLIOTECA DEL USUARIO ───────────────────────────────────────

    async def get_library_songs(self, limit: int = 25) -> dict:
        return await self._run(self._client.get_library_songs, limit=limit)

    async def get_library_albums(self) -> list:
        return await self._run(self._client.get_library_albums)

    async def get_library_artists(self) -> list:
        return await self._run(self._client.get_library_artists)

    async def get_library_playlists(self) -> list:
        return await self._run(self._client.get_library_playlists)

    async def get_liked_songs(self, limit: int = 25) -> dict:
        return await self._run(
            self._client.get_playlist, "LM", limit=limit
        )

    async def get_history(self) -> list:
        return await self._run(self._client.get_history)

    async def rate_song(self, video_id: str, rating: str) -> None:
        """rating: 'LIKE' | 'DISLIKE' | 'INDIFFERENT'"""
        await self._run(self._client.rate_song, video_id, rating)

    async def edit_song_library_status(
        self, feedback_tokens: list[str]
    ) -> None:
        await self._run(
            self._client.edit_song_library_status, feedback_tokens
        )

    async def create_playlist(self, title: str, description: str = "") -> str:
        return await self._run(
            self._client.create_playlist, title, description
        )

    async def add_playlist_items(
        self, playlist_id: str, video_ids: list[str]
    ) -> None:
        await self._run(
            self._client.add_playlist_items, playlist_id, video_ids
        )

    async def remove_playlist_items(
        self, playlist_id: str, videos: list[dict]
    ) -> None:
        await self._run(
            self._client.remove_playlist_items, playlist_id, videos
        )

    async def get_account_info(self) -> dict:
        return await self._run(self._client.get_account_info)

    # ─── PODCASTS ─────────────────────────────────────────────────────

    async def get_podcast(self, playlist_id: str) -> dict:
        return await self._run(self._client.get_podcast, playlist_id)

    async def get_episode(self, video_id: str) -> dict:
        return await self._run(self._client.get_episode, video_id)

    async def get_episodes_playlist(self) -> dict:
        return await self._run(self._client.get_episodes_playlist)
```

---

## MÓDULO: `api/stream_extractor.py`

```python
# src/pyrolist/api/stream_extractor.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
import yt_dlp
from loguru import logger
from pyrolist.config.settings import AppSettings


class StreamExtractor:
    """
    Extrae la URL directa de stream de audio de YouTube Music
    usando yt-dlp sin descargar el archivo.
    Las URLs son válidas ~6 horas; reimpleméntala al recibir error de VLC.
    """

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ytdlp")

    def _build_opts(self, for_download: bool = False) -> dict:
        opts = {
            "format": "bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio",
            "quiet": True,
            "no_warnings": True,
            "skip_download": not for_download,
            "extract_flat": False,
            "noplaylist": True,
        }
        if self.settings.network.proxy_url:
            opts["proxy"] = self.settings.network.proxy_url
        if self.settings.network.stream_quality == "medium":
            opts["format"] = "worstaudio[abr>64]/bestaudio[abr<160]"
        elif self.settings.network.stream_quality == "low":
            opts["format"] = "worstaudio"
        return opts

    async def get_stream_info(self, video_id: str) -> dict:
        """
        Devuelve:
          url: URL de stream directa
          format: ext del stream (webm, m4a)
          quality: bitrate en kbps
          duration: segundos
        """
        url = f"https://music.youtube.com/watch?v={video_id}"
        loop = asyncio.get_running_loop()

        def _extract():
            with yt_dlp.YoutubeDL(self._build_opts()) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    "url": info["url"],
                    "format": info.get("ext", "webm"),
                    "quality": info.get("abr", 0),
                    "duration": info.get("duration", 0),
                }

        result = await loop.run_in_executor(self._executor, _extract)
        logger.debug(
            f"Stream extracted for {video_id}: "
            f"{result['format']} @ {result['quality']}kbps"
        )
        return result

    async def get_download_url_and_info(self, video_id: str) -> dict:
        """Para descargas offline: devuelve la mejor calidad disponible."""
        url = f"https://music.youtube.com/watch?v={video_id}"
        loop = asyncio.get_running_loop()

        def _extract():
            opts = self._build_opts(for_download=False)
            opts["format"] = "bestaudio/best"
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)

        return await loop.run_in_executor(self._executor, _extract)

    async def download_audio(
        self,
        video_id: str,
        output_path: str,
        progress_callback=None
    ) -> str:
        """
        Descarga el audio a disco para uso offline.
        progress_callback(percent: float) se llama durante la descarga.
        Devuelve la ruta del archivo descargado.
        """
        url = f"https://music.youtube.com/watch?v={video_id}"
        loop = asyncio.get_running_loop()

        def _progress_hook(d):
            if d["status"] == "downloading" and progress_callback:
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 1)
                downloaded = d.get("downloaded_bytes", 0)
                asyncio.run_coroutine_threadsafe(
                    progress_callback(downloaded / total * 100), loop
                )

        def _download():
            opts = self._build_opts(for_download=True)
            opts.update({
                "outtmpl": output_path + ".%(ext)s",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "opus",
                    "preferredquality": "0",
                }],
                "progress_hooks": [_progress_hook],
            })
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)

        return await loop.run_in_executor(self._executor, _download)
```

---

## MÓDULO: `audio/player.py`

```python
# src/pyrolist/audio/player.py
import vlc
import asyncio
from enum import Enum
from dataclasses import dataclass
from typing import Callable
from loguru import logger


class PlayerState(Enum):
    IDLE = "idle"
    LOADING = "loading"
    PLAYING = "playing"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class PlayerStatus:
    state: PlayerState = PlayerState.IDLE
    position_ms: int = 0
    duration_ms: int = 0
    volume: int = 80
    speed: float = 1.0
    current_video_id: str | None = None
    error_msg: str | None = None


class MusicPlayer:
    """Motor de reproducción con python-vlc."""

    def __init__(self):
        self._instance = vlc.Instance(
            "--no-video",
            "--quiet",
            "--audio-resampler=soxr",
            "--network-caching=3000",    # 3s buffer para streams
            "--live-caching=3000",
        )
        self._player: vlc.MediaPlayer = self._instance.media_player_new()
        self._eq: vlc.Equalizer = vlc.Equalizer()
        self.status = PlayerStatus()
        self._callbacks: dict[str, list[Callable]] = {
            "state_changed": [],
            "position_changed": [],
            "track_ended": [],
            "error": [],
            "buffering": [],
        }
        self._poll_task: asyncio.Task | None = None

        em = self._player.event_manager()
        em.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_ended)
        em.event_attach(vlc.EventType.MediaPlayerEncounteredError, self._on_error)
        em.event_attach(vlc.EventType.MediaPlayerPlaying, self._on_playing)
        em.event_attach(vlc.EventType.MediaPlayerPaused, self._on_paused)
        em.event_attach(vlc.EventType.MediaPlayerBuffering, self._on_buffering)

    # ─── REPRODUCCIÓN ─────────────────────────────────────────────────

    async def play_url(self, stream_url: str, video_id: str) -> None:
        """
        Carga y reproduce una URL de stream.
        Si falla (URL expirada), el caller debe obtener una nueva URL
        con StreamExtractor y llamar a play_url de nuevo.
        """
        self.status.state = PlayerState.LOADING
        self.status.current_video_id = video_id
        self._notify("state_changed", self.status)

        media = self._instance.media_new(stream_url)
        media.add_option(
            ":http-user-agent=Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
        self._player.set_media(media)
        self._player.play()

        # Reiniciar polling
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
        self._poll_task = asyncio.create_task(self._poll_position())

    async def pause(self) -> None:
        if self._player.is_playing():
            self._player.pause()

    async def resume(self) -> None:
        state = self._player.get_state()
        if state == vlc.State.Paused:
            self._player.play()

    async def stop(self) -> None:
        self._player.stop()
        self.status.state = PlayerState.IDLE
        self.status.position_ms = 0
        if self._poll_task:
            self._poll_task.cancel()
        self._notify("state_changed", self.status)

    async def seek(self, position_ms: int) -> None:
        if self._player.get_length() > 0:
            self._player.set_time(max(0, position_ms))

    # ─── CONTROLES ────────────────────────────────────────────────────

    def set_volume(self, volume: int) -> None:
        """0-200 (100 = normal, 200 = amplificado 2x)"""
        clamped = max(0, min(200, volume))
        self._player.audio_set_volume(clamped)
        self.status.volume = clamped

    def set_muted(self, muted: bool) -> None:
        self._player.audio_set_mute(muted)

    def set_speed(self, speed: float) -> None:
        """0.25 a 4.0"""
        self._player.set_rate(max(0.25, min(4.0, speed)))
        self.status.speed = speed

    def apply_equalizer(self, preamp: float, bands: list[float]) -> None:
        """
        Aplica perfil de ecualizador.
        preamp: -20.0 a +20.0 dB
        bands: 10 valores de ganancia en dB
        Bandas VLC: 60Hz, 170Hz, 310Hz, 600Hz, 1kHz, 3kHz, 6kHz, 12kHz, 14kHz, 16kHz
        """
        self._eq.set_preamp(preamp)
        for i, gain in enumerate(bands[:10]):
            self._eq.set_amp_at_index(float(gain), i)
        self._player.set_equalizer(self._eq)
        logger.debug(f"EQ applied: preamp={preamp}, bands={bands}")

    def reset_equalizer(self) -> None:
        self._eq.set_preamp(0.0)
        for i in range(10):
            self._eq.set_amp_at_index(0.0, i)
        self._player.set_equalizer(self._eq)

    # ─── CALLBACKS ────────────────────────────────────────────────────

    def on(self, event: str, callback: Callable) -> None:
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def off(self, event: str, callback: Callable) -> None:
        if event in self._callbacks:
            try:
                self._callbacks[event].remove(callback)
            except ValueError:
                pass

    def _notify(self, event: str, data=None) -> None:
        for cb in self._callbacks.get(event, []):
            try:
                cb(data)
            except Exception as e:
                logger.error(f"Player callback error [{event}]: {e}")

    async def _poll_position(self) -> None:
        while True:
            await asyncio.sleep(0.5)
            if self._player.is_playing():
                pos = self._player.get_time()
                dur = self._player.get_length()
                if pos >= 0:
                    self.status.position_ms = pos
                    self.status.duration_ms = dur
                    self._notify("position_changed", self.status)

    # Los callbacks de VLC se ejecutan en hilo VLC, no en Qt/asyncio.
    # Usamos call_soon_threadsafe para enviar al loop correcto.
    def _schedule(self, func, *args):
        try:
            loop = asyncio.get_event_loop()
            loop.call_soon_threadsafe(func, *args)
        except RuntimeError:
            pass

    def _on_ended(self, event):
        def _handle():
            self.status.state = PlayerState.IDLE
            self._notify("track_ended", self.status)
        self._schedule(_handle)

    def _on_error(self, event):
        def _handle():
            self.status.state = PlayerState.ERROR
            self.status.error_msg = "Error de reproducción"
            self._notify("error", self.status)
        self._schedule(_handle)

    def _on_playing(self, event):
        def _handle():
            self.status.state = PlayerState.PLAYING
            self._notify("state_changed", self.status)
        self._schedule(_handle)

    def _on_paused(self, event):
        def _handle():
            self.status.state = PlayerState.PAUSED
            self._notify("state_changed", self.status)
        self._schedule(_handle)

    def _on_buffering(self, event):
        def _handle():
            self._notify("buffering", event.u.new_cache)
        self._schedule(_handle)

    def release(self) -> None:
        if self._poll_task:
            self._poll_task.cancel()
        self._player.release()
        self._instance.release()
```

---

## MÓDULO: `audio/queue.py`

```python
# src/pyrolist/audio/queue.py
import random
from dataclasses import dataclass, field
from enum import Enum


class RepeatMode(Enum):
    OFF = "off"
    ONE = "one"
    ALL = "all"


@dataclass
class QueueItem:
    video_id: str
    title: str
    artist: str
    album: str
    duration_ms: int
    thumbnail_url: str
    stream_url: str | None = None      # lazy-loaded al reproducir
    stream_expires_at: float = 0.0     # timestamp UNIX de expiración
    is_local: bool = False             # archivo descargado offline
    local_path: str | None = None


class PlayQueue:

    def __init__(self):
        self._queue: list[QueueItem] = []
        self._original: list[QueueItem] = []
        self._index: int = -1
        self.repeat_mode: RepeatMode = RepeatMode.OFF
        self.shuffle_enabled: bool = False

    @property
    def current(self) -> QueueItem | None:
        if 0 <= self._index < len(self._queue):
            return self._queue[self._index]
        return None

    @property
    def next_item(self) -> QueueItem | None:
        next_i = self._index + 1
        if next_i < len(self._queue):
            return self._queue[next_i]
        if self.repeat_mode == RepeatMode.ALL and self._queue:
            return self._queue[0]
        return None

    @property
    def items(self) -> list[QueueItem]:
        return self._queue.copy()

    @property
    def current_index(self) -> int:
        return self._index

    def set_queue(self, items: list[QueueItem], start_index: int = 0) -> None:
        self._original = items.copy()
        if self.shuffle_enabled:
            shuffled = items.copy()
            current = shuffled.pop(start_index)
            random.shuffle(shuffled)
            self._queue = [current] + shuffled
            self._index = 0
        else:
            self._queue = items.copy()
            self._index = start_index

    def add_next(self, item: QueueItem) -> None:
        """Inserta como siguiente canción."""
        pos = self._index + 1
        self._queue.insert(pos, item)
        self._original.insert(pos, item)

    def add_to_end(self, item: QueueItem) -> None:
        self._queue.append(item)
        self._original.append(item)

    def remove_at(self, index: int) -> None:
        if 0 <= index < len(self._queue):
            self._queue.pop(index)
            if index <= self._index and self._index > 0:
                self._index -= 1

    def move_item(self, from_index: int, to_index: int) -> None:
        if 0 <= from_index < len(self._queue) and 0 <= to_index < len(self._queue):
            item = self._queue.pop(from_index)
            self._queue.insert(to_index, item)
            if from_index == self._index:
                self._index = to_index

    def advance(self) -> QueueItem | None:
        if self.repeat_mode == RepeatMode.ONE:
            return self.current
        if self._index + 1 < len(self._queue):
            self._index += 1
        elif self.repeat_mode == RepeatMode.ALL and self._queue:
            self._index = 0
        else:
            return None
        return self.current

    def go_back(self) -> QueueItem | None:
        if self._index > 0:
            self._index -= 1
        return self.current

    def toggle_shuffle(self) -> bool:
        self.shuffle_enabled = not self.shuffle_enabled
        current = self.current
        if self.shuffle_enabled:
            remaining = [i for i in self._queue if i is not current]
            random.shuffle(remaining)
            self._queue = ([current] + remaining) if current else remaining
            self._index = 0
        else:
            self._queue = self._original.copy()
            if current:
                try:
                    self._index = next(
                        i for i, item in enumerate(self._queue)
                        if item.video_id == current.video_id
                    )
                except StopIteration:
                    self._index = 0
        return self.shuffle_enabled

    def toggle_repeat(self) -> RepeatMode:
        modes = [RepeatMode.OFF, RepeatMode.ALL, RepeatMode.ONE]
        current_i = modes.index(self.repeat_mode)
        self.repeat_mode = modes[(current_i + 1) % len(modes)]
        return self.repeat_mode

    def clear(self) -> None:
        self._queue.clear()
        self._original.clear()
        self._index = -1
```

---

## MÓDULO: `ui/main_window.py`

```python
# src/pyrolist/ui/main_window.py
import asyncio
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QFrame, QStackedWidget, QSplitter
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from qasync import asyncSlot
from loguru import logger
from pyrolist.config.settings import AppSettings
from pyrolist.api.youtube_music import YouTubeMusicClient
from pyrolist.api.stream_extractor import StreamExtractor
from pyrolist.api.lyrics import LyricsClient
from pyrolist.api.lastfm import LastFmScrobbler
from pyrolist.api.discord_rpc import DiscordRPC
from pyrolist.audio.player import MusicPlayer, PlayerState
from pyrolist.audio.queue import PlayQueue, QueueItem
from pyrolist.system.mpris import MprisPlayer
from pyrolist.system.tray import SystemTray
from pyrolist.ui.widgets.nav_sidebar import NavSidebar
from pyrolist.ui.widgets.mini_player import MiniPlayerWidget
from pyrolist.ui.screens.welcome import WelcomeScreen
from pyrolist.ui.screens.home import HomeScreen
from pyrolist.ui.screens.search import SearchScreen
from pyrolist.ui.screens.library import LibraryScreen
from pyrolist.ui.screens.history import HistoryScreen
from pyrolist.ui.screens.downloads import DownloadsScreen
from pyrolist.ui.screens.settings import SettingsScreen


class MainWindow(QMainWindow):
    """
    Layout:
    ┌──────────────────────────────────────────────────┐
    │  NavSidebar (220px) │  QStackedWidget (pantallas) │
    │                     │                             │
    │                     │                             │
    ├─────────────────────┴─────────────────────────────┤
    │              MiniPlayerWidget (80px)               │
    └────────────────────────────────────────────────────┘
    """

    ROUTES = {
        "home": 0,
        "search": 1,
        "library": 2,
        "history": 3,
        "downloads": 4,
        "settings": 5,
    }

    def __init__(self, settings: AppSettings):
        super().__init__()
        self.settings = settings

        # Servicios
        self.yt = YouTubeMusicClient(settings)
        self.extractor = StreamExtractor(settings)
        self.lyrics_client = LyricsClient()
        self.player = MusicPlayer()
        self.queue = PlayQueue()
        self.mpris = MprisPlayer(self.player, self.queue)
        self.scrobbler: LastFmScrobbler | None = None
        self.discord: DiscordRPC | None = None

        self._setup_window()
        self._build_ui()
        self._connect_player_callbacks()
        self._setup_integrations()

        # Inicializar auth en segundo plano
        asyncio.ensure_future(self._initialize())

    def _setup_window(self) -> None:
        self.setWindowTitle("Pyrolist")
        self.setMinimumSize(QSize(960, 640))
        self.resize(1300, 820)
        self.setWindowIcon(QIcon("assets/icon.png"))

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ─── Área principal: sidebar + contenido ───
        content_area = QWidget()
        content_area.setObjectName("contentArea")
        h_layout = QHBoxLayout(content_area)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        # Sidebar de navegación
        self.sidebar = NavSidebar(on_navigate=self._navigate)
        h_layout.addWidget(self.sidebar)

        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setObjectName("sidebarSeparator")
        h_layout.addWidget(separator)

        # Stack de pantallas
        self.stack = QStackedWidget()
        self.stack.setObjectName("screenStack")

        # Pantalla de bienvenida (index 0 temporal, se reemplaza con home)
        self.welcome_screen = WelcomeScreen(
            on_credentials_saved=self._on_credentials_saved
        )
        # Pantallas principales
        self.home_screen = HomeScreen(self.yt, self._play_song)
        self.search_screen = SearchScreen(self.yt, self._play_song)
        self.library_screen = LibraryScreen(self.yt, self._play_song)
        self.history_screen = HistoryScreen(self._play_song)
        self.downloads_screen = DownloadsScreen(self.extractor, self._play_local)
        self.settings_screen = SettingsScreen(
            self.settings,
            on_settings_changed=self._on_settings_changed
        )

        for screen in [
            self.home_screen,       # index 0
            self.search_screen,     # index 1
            self.library_screen,    # index 2
            self.history_screen,    # index 3
            self.downloads_screen,  # index 4
            self.settings_screen,   # index 5
        ]:
            self.stack.addWidget(screen)

        h_layout.addWidget(self.stack)
        root_layout.addWidget(content_area)

        # ─── Mini player fijo en la parte inferior ───
        self.mini_player = MiniPlayerWidget(
            player=self.player,
            queue=self.queue,
            on_expand=self._show_full_player,
            on_prev=self._on_prev,
            on_play_pause=self._on_play_pause,
            on_next=self._on_next,
            on_seek=self._on_seek,
        )
        root_layout.addWidget(self.mini_player)

        # System tray
        self.tray = SystemTray(
            parent=self,
            on_show=self.show,
            on_play_pause=self._on_play_pause,
            on_next=self._on_next,
            on_quit=self.close,
        )

    def _connect_player_callbacks(self) -> None:
        self.player.on("track_ended", self._on_track_ended_callback)
        self.player.on("state_changed", self._on_state_changed_callback)
        self.player.on("position_changed", self._on_position_changed_callback)

    def _on_track_ended_callback(self, status) -> None:
        asyncio.ensure_future(self._advance_queue())

    def _on_state_changed_callback(self, status) -> None:
        self.mini_player.update_state(status)
        if self.mpris:
            self.mpris.update_playback_status(
                status.state.value == "playing"
            )

    def _on_position_changed_callback(self, status) -> None:
        self.mini_player.update_position(
            status.position_ms, status.duration_ms
        )
        if self.mpris:
            self.mpris.update_position(status.position_ms)

    def _setup_integrations(self) -> None:
        if self.settings.integrations.mpris_enabled:
            self.mpris.start()
        if self.settings.integrations.lastfm_enabled:
            self.scrobbler = LastFmScrobbler(
                self.settings.integrations.lastfm_api_key,
                self.settings.integrations.lastfm_api_secret,
                self.settings.integrations.lastfm_session_key,
            )
        if self.settings.integrations.discord_rpc_enabled:
            self.discord = DiscordRPC()
            asyncio.ensure_future(self.discord.connect())

    async def _initialize(self) -> None:
        """Intenta cargar auth existente. Si no hay, muestra pantalla de bienvenida."""
        if not self.settings.google_client_id:
            self._show_welcome()
            return

        if self.yt.load_existing_auth():
            await self.home_screen.load()
            self._navigate("home")
        else:
            self._show_welcome()

    def _show_welcome(self) -> None:
        self.stack.insertWidget(0, self.welcome_screen)
        self.stack.setCurrentWidget(self.welcome_screen)
        self.sidebar.setEnabled(False)

    async def _on_credentials_saved(
        self, client_id: str, client_secret: str
    ) -> None:
        self.settings.google_client_id = client_id
        self.settings.google_client_secret = client_secret
        self.settings.save(self.settings.settings_file)

        # Reinicializar cliente con las nuevas credenciales
        from pyrolist.config.paths import AppDirs
        self.yt = YouTubeMusicClient(self.settings)
        await self._initialize()
        self.sidebar.setEnabled(True)

    def _navigate(self, route: str) -> None:
        index = self.ROUTES.get(route, 0)
        self.stack.setCurrentIndex(index)
        asyncio.ensure_future(self._load_screen(route))

    async def _load_screen(self, route: str) -> None:
        screens = {
            "home": self.home_screen,
            "search": self.search_screen,
            "library": self.library_screen,
            "history": self.history_screen,
        }
        screen = screens.get(route)
        if screen and hasattr(screen, "load"):
            await screen.load()

    async def _play_song(
        self,
        video_id: str,
        title: str,
        artist: str,
        album: str,
        duration_ms: int,
        thumbnail_url: str,
        queue_items: list[QueueItem] | None = None,
        queue_index: int = 0,
    ) -> None:
        """Llamado desde cualquier pantalla para reproducir una canción."""
        if queue_items:
            self.queue.set_queue(queue_items, queue_index)
        else:
            item = QueueItem(
                video_id=video_id, title=title, artist=artist,
                album=album, duration_ms=duration_ms,
                thumbnail_url=thumbnail_url,
            )
            self.queue.set_queue([item], 0)

        await self._play_current()

    async def _play_current(self) -> None:
        item = self.queue.current
        if not item:
            return

        # Actualizar mini player con info de la canción
        self.mini_player.update_track_info(
            item.title, item.artist, item.thumbnail_url
        )

        # Obtener URL de stream
        try:
            stream_info = await self.extractor.get_stream_info(item.video_id)
            item.stream_url = stream_info["url"]
            import time
            item.stream_expires_at = time.time() + 21600  # 6 horas

            await self.player.play_url(item.stream_url, item.video_id)

            # Iniciar carga de letras en paralelo
            asyncio.ensure_future(self._load_lyrics(item))

            # Precargar siguiente
            if self.settings.player.preload_next:
                asyncio.ensure_future(self._preload_next())

            # Scrobble y Discord RPC
            if self.scrobbler:
                await self.scrobbler.update_now_playing(
                    item.artist, item.title, item.album
                )
            if self.discord:
                await self.discord.update(
                    item.title, item.artist, item.album, True
                )
            if self.mpris:
                self.mpris.update_metadata(
                    item.title, item.artist, item.album,
                    item.duration_ms * 1000, item.thumbnail_url
                )

        except Exception as e:
            logger.error(f"Failed to play {item.video_id}: {e}")

    async def _load_lyrics(self, item: QueueItem) -> None:
        lyrics = await self.lyrics_client.get_lyrics(
            item.title, item.artist, item.album
        )
        if lyrics:
            # Si el full player está abierto, pasarle las letras
            pass

    async def _preload_next(self) -> None:
        next_item = self.queue.next_item
        if next_item and not next_item.stream_url:
            try:
                info = await self.extractor.get_stream_info(next_item.video_id)
                next_item.stream_url = info["url"]
            except Exception:
                pass

    async def _advance_queue(self) -> None:
        item = self.queue.advance()
        if item:
            if item.stream_url:
                import time
                if time.time() < item.stream_expires_at:
                    await self.player.play_url(item.stream_url, item.video_id)
                    return
            await self._play_current()
        else:
            # Fin de la cola: cargar autoplay/radio desde YouTube
            current = self.queue.current
            if current:
                try:
                    watch = await self.yt.get_watch_playlist(current.video_id)
                    new_items = [
                        QueueItem(
                            video_id=t["videoId"],
                            title=t.get("title", ""),
                            artist=t.get("artists", [{}])[0].get("name", ""),
                            album="",
                            duration_ms=0,
                            thumbnail_url=(t.get("thumbnail") or [{}])[0].get("url",""),
                        )
                        for t in watch.get("tracks", [])[1:]
                    ]
                    if new_items:
                        for ni in new_items:
                            self.queue.add_to_end(ni)
                        self.queue.advance()
                        await self._play_current()
                except Exception as e:
                    logger.warning(f"Autoplay failed: {e}")

    def _play_local(self, path: str, metadata: dict) -> None:
        asyncio.ensure_future(self.player.play_url(path, "local"))

    def _on_play_pause(self) -> None:
        asyncio.ensure_future(self._toggle_play_pause())

    async def _toggle_play_pause(self) -> None:
        if self.player.status.state == PlayerState.PLAYING:
            await self.player.pause()
        else:
            await self.player.resume()

    def _on_next(self) -> None:
        asyncio.ensure_future(self._advance_queue())

    def _on_prev(self) -> None:
        asyncio.ensure_future(self._go_prev())

    async def _go_prev(self) -> None:
        if self.player.status.position_ms > 3000:
            await self.player.seek(0)
        else:
            item = self.queue.go_back()
            if item:
                await self._play_current()

    def _on_seek(self, position_ms: int) -> None:
        asyncio.ensure_future(self.player.seek(position_ms))

    def _show_full_player(self) -> None:
        # Abre el panel del reproductor completo (QDialog o panel lateral)
        from pyrolist.ui.widgets.full_player import FullPlayerDialog
        dlg = FullPlayerDialog(self.player, self.queue, self.lyrics_client, self)
        dlg.exec()

    def _on_settings_changed(self, settings: AppSettings) -> None:
        self.settings = settings
        settings.save(self.settings.settings_file)
        # Reaplicar EQ si estaba habilitado
        if settings.equalizer.enabled:
            self.player.apply_equalizer(
                settings.equalizer.preamp,
                settings.equalizer.bands,
            )

    def closeEvent(self, event) -> None:
        if self.settings.player.stop_on_close:
            asyncio.ensure_future(self.player.stop())
        self.player.release()
        if self.discord:
            asyncio.ensure_future(self.discord.disconnect())
        self.tray.hide()
        event.accept()
```

---

## MÓDULO: `ui/stylesheet.py` — QSS completo

```python
# src/pyrolist/ui/stylesheet.py
"""
QSS personalizado de Pyrolist aplicado sobre qt-material.
Define los estilos específicos de la app: sidebar, mini player,
tarjetas, barra de progreso, etc.
"""

PYROLIST_QSS = """
/* ─── Variables de color ─────────────────────────────────── */
/* Qt no tiene variables nativas; los colores se definen
   directamente. El acento principal es el de qt-material. */

/* ─── Ventana principal ──────────────────────────────────── */
QMainWindow {
    background-color: #0F0F1A;
}

#contentArea {
    background-color: #0F0F1A;
}

/* ─── Sidebar de navegación ──────────────────────────────── */
#navSidebar {
    background-color: #13131F;
    min-width: 220px;
    max-width: 220px;
    border-right: 1px solid #2A2A3E;
}

#navSidebar[collapsed="true"] {
    min-width: 64px;
    max-width: 64px;
}

#appTitle {
    font-size: 20px;
    font-weight: bold;
    color: #BB86FC;
    padding: 20px 16px 12px 16px;
}

.NavButton {
    text-align: left;
    padding: 10px 16px;
    border: none;
    border-radius: 10px;
    font-size: 14px;
    color: #B0B0C0;
    background-color: transparent;
    margin: 2px 8px;
}

.NavButton:hover {
    background-color: #1E1E2E;
    color: #FFFFFF;
}

.NavButton[active="true"] {
    background-color: #2D1B69;
    color: #BB86FC;
    font-weight: 600;
}

#sidebarSeparator {
    color: #2A2A3E;
    max-width: 1px;
}

/* ─── Stack de pantallas ─────────────────────────────────── */
#screenStack {
    background-color: #0F0F1A;
}

/* ─── Mini Player ────────────────────────────────────────── */
#miniPlayer {
    background-color: #13131F;
    border-top: 1px solid #2A2A3E;
    min-height: 80px;
    max-height: 80px;
}

#miniPlayer QLabel#songTitle {
    font-size: 14px;
    font-weight: 600;
    color: #FFFFFF;
}

#miniPlayer QLabel#artistName {
    font-size: 12px;
    color: #888899;
}

#miniPlayer QPushButton {
    background: transparent;
    border: none;
    border-radius: 20px;
    padding: 4px;
}

#miniPlayer QPushButton:hover {
    background-color: #2A2A3E;
}

/* Barra de progreso del mini player */
#progressBar {
    background-color: #2A2A3E;
    border-radius: 2px;
    max-height: 4px;
}

#progressBar::chunk {
    background-color: #BB86FC;
    border-radius: 2px;
}

/* Slider de volumen */
QSlider#volumeSlider::groove:horizontal {
    background: #2A2A3E;
    height: 4px;
    border-radius: 2px;
}

QSlider#volumeSlider::sub-page:horizontal {
    background: #BB86FC;
    height: 4px;
    border-radius: 2px;
}

QSlider#volumeSlider::handle:horizontal {
    background: #FFFFFF;
    width: 12px;
    height: 12px;
    border-radius: 6px;
    margin: -4px 0;
}

/* ─── Tarjetas (SongCard, AlbumCard, etc.) ───────────────── */
.MusicCard {
    background-color: #1A1A2E;
    border-radius: 12px;
    border: 1px solid #2A2A3E;
    padding: 8px;
}

.MusicCard:hover {
    background-color: #1E1E3E;
    border-color: #BB86FC;
}

/* ─── QScrollArea / listas ───────────────────────────────── */
QScrollArea {
    background: transparent;
    border: none;
}

QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #3A3A5E;
    border-radius: 3px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #BB86FC;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}

/* ─── Search bar ─────────────────────────────────────────── */
#searchBar {
    background-color: #1E1E2E;
    border: 1px solid #2A2A3E;
    border-radius: 24px;
    padding: 8px 16px 8px 40px;
    font-size: 14px;
    color: #FFFFFF;
}

#searchBar:focus {
    border-color: #BB86FC;
    background-color: #1E1E3E;
}

/* ─── Letras sincronizadas ───────────────────────────────── */
#lyricsContainer QLabel.lyricLine {
    font-size: 18px;
    color: #666688;
    padding: 6px 0;
    transition: all 0.3s;
}

#lyricsContainer QLabel.lyricLine[active="true"] {
    font-size: 22px;
    font-weight: bold;
    color: #FFFFFF;
}

/* ─── Full Player ────────────────────────────────────────── */
#fullPlayerArtwork {
    border-radius: 16px;
}

/* ─── Sección de encabezados ─────────────────────────────── */
QLabel.sectionHeader {
    font-size: 20px;
    font-weight: bold;
    color: #FFFFFF;
    padding: 16px 0 8px 0;
}

/* ─── Botones de acción ──────────────────────────────────── */
QPushButton.primaryButton {
    background-color: #BB86FC;
    color: #000000;
    border-radius: 20px;
    padding: 10px 24px;
    font-weight: 600;
    font-size: 14px;
    border: none;
}

QPushButton.primaryButton:hover {
    background-color: #CC99FF;
}

QPushButton.secondaryButton {
    background-color: transparent;
    color: #BB86FC;
    border: 1px solid #BB86FC;
    border-radius: 20px;
    padding: 10px 24px;
    font-weight: 600;
    font-size: 14px;
}

QPushButton.secondaryButton:hover {
    background-color: #2D1B69;
}

/* ─── Ecualizador ────────────────────────────────────────── */
QSlider#eqBand::groove:vertical {
    background: #2A2A3E;
    width: 4px;
    border-radius: 2px;
}

QSlider#eqBand::sub-page:vertical {
    background: #BB86FC;
    border-radius: 2px;
}

QSlider#eqBand::handle:vertical {
    background: #FFFFFF;
    width: 14px;
    height: 14px;
    border-radius: 7px;
    margin: 0 -5px;
}

/* ─── Diálogos ───────────────────────────────────────────── */
QDialog {
    background-color: #13131F;
}
"""
```

---

## MÓDULO: `system/mpris.py` — MPRIS2 completo

```python
# src/pyrolist/system/mpris.py
"""
Implementa MPRIS2 (Media Player Remote Interfacing Specification) para Linux.
Permite control desde playerctl, Waybar, KDE, GNOME, dunst, etc.
"""
import platform
from loguru import logger

_DBUS_OK = False
if platform.system() == "Linux":
    try:
        import dbus
        import dbus.service
        import dbus.mainloop.glib
        _DBUS_OK = True
    except ImportError:
        logger.warning("dbus-python not available. MPRIS2 disabled.")

MPRIS2_IFACE = "org.mpris.MediaPlayer2"
PLAYER_IFACE = "org.mpris.MediaPlayer2.Player"
BUS_NAME     = "org.mpris.MediaPlayer2.pyrolist"
OBJECT_PATH  = "/org/mpris/MediaPlayer2"


class MprisPlayer:
    def __init__(self, player, queue):
        self.player = player
        self.queue = queue
        self._bus = None
        self._service = None
        self._active = False

    def start(self) -> None:
        if not _DBUS_OK:
            return
        try:
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            self._bus = dbus.SessionBus()
            self._bus.request_name(BUS_NAME)
            self._active = True
            logger.info(f"MPRIS2 registered as {BUS_NAME}")
        except Exception as e:
            logger.error(f"MPRIS2 registration failed: {e}")
            self._active = False

    def update_metadata(
        self,
        title: str,
        artist: str,
        album: str,
        duration_us: int,
        artwork_url: str,
    ) -> None:
        """Actualiza la metadata visible externamente (playerctl metadata, etc.)"""
        if not self._active or not self._bus:
            return
        try:
            # Emitir PropertiesChanged para que playerctl lo recoja
            props = dbus.Interface(
                self._bus.get_object("org.freedesktop.DBus.Properties", OBJECT_PATH),
                "org.freedesktop.DBus.Properties"
            )
            metadata = dbus.Dictionary({
                "mpris:trackid": dbus.ObjectPath(f"/track/{title[:20].replace(' ','_')}"),
                "mpris:length": dbus.Int64(duration_us),
                "xesam:title": title,
                "xesam:artist": dbus.Array([artist], signature="s"),
                "xesam:album": album,
                "mpris:artUrl": artwork_url,
            }, signature="sv")
            # En implementación completa: señal PropertiesChanged
        except Exception as e:
            logger.debug(f"MPRIS2 metadata update failed: {e}")

    def update_playback_status(self, is_playing: bool) -> None:
        """'Playing' | 'Paused' | 'Stopped'"""
        if not self._active:
            return
        # En implementación completa: señal PropertiesChanged con PlaybackStatus

    def update_position(self, position_ms: int) -> None:
        if not self._active:
            return
        # En implementación completa: señal Seeked con posición en microsegundos
```

---

## MÓDULO: `config/themes.py` — Colores dinámicos

```python
# src/pyrolist/config/themes.py
import io
import httpx
from PIL import Image
from loguru import logger

# Presets del ecualizador para la pantalla de EQ
EQ_PRESETS: dict[str, tuple[float, list[float]]] = {
    # nombre: (preamp, [10 bandas])
    "Flat":         (0.0,  [0.0]*10),
    "Bass Boost":   (2.0,  [6.0, 5.0, 4.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
    "Treble Boost": (0.0,  [0.0, 0.0, 0.0, 0.0, 0.0, 2.0, 4.0, 5.0, 6.0, 6.0]),
    "Vocal":        (0.0,  [-2.0,-1.0, 0.0, 2.0, 4.0, 4.0, 3.0, 2.0, 1.0, 0.0]),
    "Classical":    (0.0,  [4.0, 3.0, 2.0, 0.0, 0.0, 0.0, 0.0, 2.0, 3.0, 4.0]),
    "Electronic":   (2.0,  [4.0, 3.0, 0.0, 2.0, 0.0, 0.0, 2.0, 3.0, 4.0, 4.0]),
    "Hip-Hop":      (2.0,  [5.0, 4.0, 2.0, 3.0, 0.0, 0.0, 1.0, 2.0, 3.0, 4.0]),
    "Rock":         (1.0,  [4.0, 3.0, 2.0, 0.0,-1.0,-1.0, 0.0, 2.0, 3.0, 4.0]),
    "Jazz":         (0.0,  [3.0, 2.0, 1.0, 2.0, 0.0, 0.0, 1.0, 2.0, 3.0, 3.0]),
    "Pop":          (0.0,  [-1.0, 0.0, 2.0, 3.0, 4.0, 3.0, 2.0, 0.0,-1.0,-1.0]),
}

# Frecuencias de las 10 bandas de VLC (para etiquetas en la UI)
EQ_BAND_LABELS = [
    "60Hz", "170Hz", "310Hz", "600Hz", "1kHz",
    "3kHz", "6kHz", "12kHz", "14kHz", "16kHz"
]


async def extract_dominant_color(image_url: str) -> str | None:
    """
    Descarga el artwork del álbum y extrae el color más dominante
    de la zona central de la imagen.
    Devuelve un hex string '#rrggbb' o None si falla.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(image_url)
            img = Image.open(io.BytesIO(r.content)).convert("RGB")

        # Redimensionar para procesamiento rápido
        img = img.resize((50, 50), Image.LANCZOS)
        pixels = list(img.getdata())
        w, h = img.size

        # Solo la zona central (25-75% de la imagen)
        center_pixels = [
            pixels[y * w + x]
            for y in range(int(h*0.25), int(h*0.75))
            for x in range(int(w*0.25), int(w*0.75))
        ]

        if not center_pixels:
            return None

        r = sum(p[0] for p in center_pixels) // len(center_pixels)
        g = sum(p[1] for p in center_pixels) // len(center_pixels)
        b = sum(p[2] for p in center_pixels) // len(center_pixels)

        # Aumentar saturación mínima para que sea un acento vivo
        import colorsys
        h_val, s_val, v_val = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        s_val = max(s_val, 0.5)   # saturación mínima 50%
        v_val = max(v_val, 0.6)   # brillo mínimo 60%
        r2, g2, b2 = colorsys.hsv_to_rgb(h_val, s_val, v_val)

        return f"#{int(r2*255):02x}{int(g2*255):02x}{int(b2*255):02x}"

    except Exception as e:
        logger.debug(f"Color extraction failed: {e}")
        return None
```

---

## MÓDULO: `utils/worker.py` — QThread base para tareas pesadas

```python
# src/pyrolist/utils/worker.py
from PySide6.QtCore import QRunnable, QObject, Signal, Slot
import traceback
from typing import Callable, Any


class WorkerSignals(QObject):
    finished = Signal()
    error = Signal(str)
    result = Signal(object)
    progress = Signal(int)


class Worker(QRunnable):
    """
    Worker genérico para QThreadPool.
    Úsalo para cualquier tarea CPU-intensiva o bloqueante que
    NO sea una coroutine (para coroutines usa asyncio.ensure_future).

    Ejemplo:
        worker = Worker(lambda: pesado_calculo())
        worker.signals.result.connect(mi_callback)
        QThreadPool.globalInstance().start(worker)
    """

    def __init__(self, fn: Callable, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as e:
            self.signals.error.emit(
                f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            )
        finally:
            self.signals.finished.emit()
```

---

## PANTALLA: `ui/screens/welcome.py` — Setup OAuth

```python
# src/pyrolist/ui/screens/welcome.py
import asyncio
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFrame, QTextEdit
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QPixmap
from qasync import asyncSlot
from typing import Callable


class WelcomeScreen(QWidget):
    """
    Pantalla de bienvenida que guía al usuario a través de:
    1. Obtener credenciales de Google Cloud Console
    2. Iniciar el Device Flow OAuth (código de 8 dígitos)
    3. Confirmar la autorización
    """

    def __init__(self, on_credentials_saved: Callable):
        super().__init__()
        self.on_credentials_saved = on_credentials_saved
        self._device_code: str | None = None
        self._poll_timer = QTimer()
        self._poll_timer.setInterval(5000)   # polling cada 5s
        self._poll_timer.timeout.connect(self._poll_token)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(80, 40, 80, 40)
        layout.setSpacing(20)

        # Logo y título
        title = QLabel("Pyrolist")
        title.setFont(QFont("Inter", 32, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #BB86FC;")

        subtitle = QLabel("Cliente de YouTube Music para Linux")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #888899; font-size: 14px;")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(20)

        # Paso 1: Credenciales
        self._step1 = self._build_step1()
        # Paso 2: Device code
        self._step2 = self._build_step2()
        self._step2.setVisible(False)

        layout.addWidget(self._step1)
        layout.addWidget(self._step2)
        layout.addStretch()

    def _build_step1(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("setupCard")
        frame.setStyleSheet("""
            #setupCard {
                background-color: #1A1A2E;
                border-radius: 16px;
                border: 1px solid #2A2A3E;
                padding: 24px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setSpacing(12)

        header = QLabel("Paso 1 — Credenciales de Google")
        header.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        header.setStyleSheet("color: #FFFFFF;")

        instructions = QLabel(
            "Para conectar con YouTube Music necesitas crear credenciales OAuth "
            "en Google Cloud Console:\n\n"
            "1. Ve a console.cloud.google.com\n"
            "2. Crea un proyecto nuevo (o usa uno existente)\n"
            "3. Activa la API: YouTube Data API v3\n"
            "4. Ve a Credenciales → Crear credencial → ID de cliente OAuth\n"
            "5. Tipo de aplicación: TVs y dispositivos de entrada limitada\n"
            "6. Copia el Client ID y Client Secret que aparecen"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #B0B0C0; font-size: 13px;")

        self._client_id_input = QLineEdit()
        self._client_id_input.setPlaceholderText("Client ID (*.apps.googleusercontent.com)")
        self._client_id_input.setMinimumHeight(40)

        self._client_secret_input = QLineEdit()
        self._client_secret_input.setPlaceholderText("Client Secret")
        self._client_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._client_secret_input.setMinimumHeight(40)

        self._next_btn = QPushButton("Continuar")
        self._next_btn.setProperty("class", "primaryButton")
        self._next_btn.setMinimumHeight(44)
        self._next_btn.clicked.connect(self._on_next_step1)

        layout.addWidget(header)
        layout.addWidget(instructions)
        layout.addSpacing(8)
        layout.addWidget(QLabel("Client ID:"))
        layout.addWidget(self._client_id_input)
        layout.addWidget(QLabel("Client Secret:"))
        layout.addWidget(self._client_secret_input)
        layout.addSpacing(8)
        layout.addWidget(self._next_btn)
        return frame

    def _build_step2(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("setupCard")
        frame.setStyleSheet("""
            #setupCard {
                background-color: #1A1A2E;
                border-radius: 16px;
                border: 1px solid #2A2A3E;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QLabel("Paso 2 — Autorizar con Google")
        header.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        header.setStyleSheet("color: #FFFFFF;")

        instructions = QLabel(
            "Abre este enlace en tu navegador e introduce el código:"
        )
        instructions.setStyleSheet("color: #B0B0C0;")

        self._verification_url_label = QLabel()
        self._verification_url_label.setStyleSheet(
            "color: #BB86FC; font-size: 14px;"
        )
        self._verification_url_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self._user_code_label = QLabel()
        self._user_code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._user_code_label.setFont(QFont("Monospace", 28, QFont.Weight.Bold))
        self._user_code_label.setStyleSheet(
            "color: #FFFFFF; background: #2D1B69; "
            "border-radius: 12px; padding: 16px;"
        )

        self._status_label = QLabel("Esperando autorización...")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("color: #888899;")

        layout.addWidget(header)
        layout.addWidget(instructions)
        layout.addWidget(self._verification_url_label)
        layout.addSpacing(8)
        layout.addWidget(self._user_code_label)
        layout.addSpacing(8)
        layout.addWidget(self._status_label)
        return frame

    @asyncSlot()
    async def _on_next_step1(self) -> None:
        client_id = self._client_id_input.text().strip()
        client_secret = self._client_secret_input.text().strip()

        if not client_id or not client_secret:
            self._next_btn.setText("⚠ Rellena ambos campos")
            return

        self._next_btn.setText("Conectando...")
        self._next_btn.setEnabled(False)

        # Guardar temporalmente en settings para poder usarlos
        await self.on_credentials_saved(client_id, client_secret)

        # El flujo OAuth lo inicia MainWindow._initialize()
        # que detectará que hay credenciales y llamará a start_device_flow
        # A través de la señal del WelcomeScreen
        self._step1.setVisible(False)
        self._step2.setVisible(True)

    def show_device_code(self, user_code: str, verification_url: str) -> None:
        """Llamado por MainWindow cuando tiene el código del Device Flow."""
        self._user_code_label.setText(user_code)
        self._verification_url_label.setText(verification_url)
        self._device_code_value = user_code
        self._poll_timer.start()

    @asyncSlot()
    async def _poll_token(self) -> None:
        self._status_label.setText("Verificando autorización...")
        # El polling real lo hace MainWindow que tiene acceso al yt_client
        # Este timer solo actualiza la UI

    def on_auth_success(self) -> None:
        self._poll_timer.stop()
        self._status_label.setText("✓ Autorización exitosa. Cargando...")
```

---

## `pyproject.toml`

```toml
[project]
name = "pyrolist"
version = "1.0.0"
description = "Cliente de escritorio para YouTube Music - Linux"
requires-python = ">=3.12"
dependencies = [
    "PySide6>=6.7.0",
    "qasync>=0.27.0",
    "qt-material>=2.14",
    "ytmusicapi>=1.11.5",
    "yt-dlp>=2025.1.1",
    "python-vlc>=3.0.21",
    "sqlalchemy[asyncio]>=2.0",
    "aiosqlite>=0.20",
    "alembic>=1.13",
    "pydantic>=2.7",
    "tomli-w>=1.0",
    "httpx[http2]>=0.27",
    "syncedlyrics>=0.7",
    "pylast>=5.3",
    "pypresence>=4.3",
    "pystray>=0.19",
    "pillow>=10.0",
    "loguru>=0.7",
    "dbus-python>=1.3 ; sys_platform == 'linux'",
]

[project.scripts]
pyrolist = "pyrolist.main:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/pyrolist"]
```

---

## FLUJO DE TRABAJO POR FASES

**Fase 1 — Setup y reproducción mínima (2-3 días)**
1. Crear estructura de directorios y `pyproject.toml`, instalar dependencias.
2. Implementar `vlc_check.py`, `paths.py`, `settings.py`.
3. Implementar `YouTubeMusicClient` y `StreamExtractor`.
4. Implementar `MusicPlayer` (python-vlc).
5. Implementar `main.py` con qasync + qt-material básico.
6. **Objetivo verificable:** ventana abre → se detecta VLC → login Google (Device Flow) → buscar canción → reproducir. La UI puede ser placeholder.

**Fase 2 — Layout principal (2 días)**
1. Implementar `NavSidebar` con los 5 destinos.
2. Implementar `MiniPlayerWidget` completo con controles y barra de progreso.
3. Implementar `MainWindow` con el layout de dos paneles.
4. Aplicar `PYROLIST_QSS` completo.

**Fase 3 — Pantallas de contenido (3-4 días)**
1. `HomeScreen` con grillas de álbumes, playlists recientes y mezclas.
2. `SearchScreen` con sugerencias en tiempo real.
3. `LibraryScreen` con canciones, álbumes, artistas, playlists.
4. `AlbumScreen` y `ArtistScreen` como QDialog o pantalla del stack.

**Fase 4 — Reproductor completo (2 días)**
1. `FullPlayerDialog` con artwork grande, letras sincronizadas y cola.
2. `LyricsView` con scroll automático al verso activo.
3. `QueuePanel` con drag & drop para reordenar la cola.
4. Controles avanzados: shuffle, repeat, velocidad, tono.

**Fase 5 — Ecualizador y audio avanzado (1-2 días)**
1. `EqualizerScreen` con 10 sliders verticales + selector de presets.
2. Skip de silencio (detección en el stream).
3. Sleep timer.
4. Crossfade entre canciones.
5. Color dinámico del artwork aplicado al acento de qt-material en runtime.

**Fase 6 — Descargas offline (2 días)**
1. `DownloadsScreen` con lista de canciones descargadas.
2. Cola de descarga con progreso por archivo.
3. Reproducción de archivos locales con `MusicPlayer`.
4. Gestión de almacenamiento (ver uso, limpiar caché).

**Fase 7 — Integraciones (1-2 días)**
1. MPRIS2 completo (playerctl, Waybar, GNOME, KDE).
2. Last.fm scrobbling.
3. Discord Rich Presence.
4. System tray con controles básicos.
5. `HistoryScreen` y `StatsScreen`.

**Fase 8 — Pulido y distribución (2 días)**
1. Exportar como `.deb` con `python3 -m build` + `fpm` o `dpkg-deb`.
2. Generar AppImage con `appimage-builder`.
3. Revisar memory leaks (especialmente en el player y el cache de artwork).

---

## ADVERTENCIAS CRÍTICAS

1. **qasync vs QtAsyncio.** QtAsyncio de PySide6 no tiene implementadas operaciones de red como DNS y sockets, lo que causa errores silenciosos con httpx y ytmusicapi. Usa qasync exclusivamente.

2. **Callbacks de VLC en hilo VLC.** Los eventos de VLC (`MediaPlayerEndReached`, etc.) se disparan en el hilo interno de VLC, no en el hilo de Qt. Usa siempre `loop.call_soon_threadsafe()` para enviar al loop correcto. El código del módulo `player.py` ya implementa esto en `_schedule()`.

3. **URLs de stream expiran en ~6 horas.** Si el usuario pausa la canción por más de 6 horas y luego reanuda, VLC reportará error. El `MainWindow` detecta el error del player y llama a `extractor.get_stream_info()` para obtener una URL fresca antes de reintentar.

4. **ytmusicapi es síncrono.** Absolutamente cada llamada a `self._client.*()` debe ir dentro de `loop.run_in_executor()`. Sin esto, la UI de Qt se congela completamente durante la petición de red.

5. **`qt-material` debe importarse DESPUÉS de PySide6.** Si se importa antes, lanza un `RuntimeError`. El orden correcto está en `main.py`.

6. **`asyncio.ensure_future()` requiere un loop corriendo.** En PySide6 + qasync el loop está corriendo dentro del `with qasync.QEventLoop(app) as loop:` block. Fuera de ese contexto (ej. en `__init__` de un widget), usa `asyncio.get_event_loop().create_task()` con precaución.

7. **Artwork y memoria.** No almacenar imágenes en memoria sin límite. Implementa `image_cache.py` con un LRU de máximo 200 entradas y 50MB en disco bajo `AppDirs.artwork_cache`.

8. **MPRIS2 en Wayland.** El módulo QtAsyncio (y por extensión D-Bus sobre él) requiere configuración adicional en Wayland. Con dbus-python + GLib MainLoop, MPRIS2 funciona en X11 y XWayland sin problemas. Para Wayland nativo puro, verifica que `DBUS_SESSION_BUS_ADDRESS` está definido.

---

## REFERENCIAS

- PySide6 docs: https://doc.qt.io/qtforpython-6/
- qasync: https://github.com/CabbageDevelopment/qasync
- qt-material: https://qt-material.readthedocs.io/
- ytmusicapi OAuth: https://ytmusicapi.readthedocs.io/en/stable/setup/oauth.html
- python-vlc: https://python-vlc.readthedocs.io/
- yt-dlp: https://github.com/yt-dlp/yt-dlp
- syncedlyrics: https://github.com/moehmeni/syncedlyrics
- MPRIS2 spec: https://specifications.freedesktop.org/mpris-spec/latest/
- pylast: https://github.com/pylast/pylast
- pypresence: https://qwertyquerty.github.io/pypresence/

---

*Stack 100% Python. PySide6 + qasync + qt-material + python-vlc + ytmusicapi + yt-dlp.
Todas las funciones de Metrolist: streaming, descarga offline, letras sincronizadas,
ecualizador 10 bandas, Discord RPC, Last.fm, MPRIS2, sleep timer, crossfade,
color dinámico desde artwork, y autenticación OAuth con Google.*
