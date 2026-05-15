# CONTEXTO COMPLETO DEL PROYECTO PYROLIST

## 1. INFORMACIÓN GENERAL DEL PROYECTO

**Nombre del Proyecto:** Pyrolist  
**Descripción:** Cliente de escritorio YouTube Music para Linux  
**Stack Tecnológico:**
- PySide6 (Qt for Python) - Interfaz gráfica
- qasync - Integración de asyncio con Qt
- VLC (libvlc) - Reproducción de audio
- yt-dlp - Extracción de streams
- ytmusicapi - API de YouTube Music
- SQLite (aiosqlite) - Base de datos local

## 2. ESTRUCTURA DEL PROYECTO

```
Pyrolist/
├── src/pyrolist/
│   ├── api/                          # Módulos de API
│   │   ├── youtube_music.py          # Cliente híbrido (yt-dlp + ytmusicapi)
│   │   ├── stream_extractor.py      # Extracción de URLs de stream
│   │   ├── lyrics.py                 # Letras de canciones
│   │   ├── invidious_client.py       # Cliente Invidious (alternativo)
│   │   ├── piped_client.py          # Cliente Piped (alternativo)
│   │   ├── youtube_api.py           # API de YouTube (alternativo)
│   │   ├── lastfm.py                # Scrobbling a Last.fm
│   │   └── discord_rpc.py           # Discord Rich Presence
│   │
│   ├── audio/                        # Módulo de audio
│   │   ├── player.py                # Reproductor de música (VLC)
│   │   ├── queue.py                 # Cola de reproducción
│   │   ├── crossfade.py             # Crossfade entre canciones
│   │   ├── equalizer.py            # Ecualizador
│   │   └── sleep_timer.py           # Temporizador de sueño
│   │
│   ├── db/                           # Base de datos
│   │   ├── database.py              # Inicialización de DB
│   │   ├── models.py                # Modelos de datos
│   │   └── repository.py           # Repositorio de datos
│   │
│   ├── ui/                          # Interfaz de usuario
│   │   ├── main_window.py           # Ventana principal
│   │   ├── stylesheet.py           # Estilos CSS
│   │   ├── screens/                 # Pantallas
│   │   │   ├── home.py             # Pantalla de inicio
│   │   │   ├── search.py           # Búsqueda
│   │   │   ├── library.py          # Biblioteca
│   │   │   ├── history.py          # Historial
│   │   │   ├── downloads.py       # Descargas
│   │   │   ├── playlist.py         # Detalles de playlist
│   │   │   ├── artist.py           # Detalles de artista
│   │   │   ├── album.py            # Detalles de álbum
│   │   │   ├── welcome.py          # Pantalla de bienvenida
│   │   │   └── settings/           # Configuración
│   │   │       ├── __init__.py
│   │   │       ├── accounts.py     # Cuentas
│   │   │       ├── about.py        # Acerca de
│   │   │       ├── storage.py      # Almacenamiento
│   │   │       ├── equalizer.py    # Ecualizador
│   │   │       ├── player_settings.py
│   │   │       └── appearance.py   # Apariencia
│   │   └── widgets/                 # Componentes UI
│   │       ├── nav_sidebar.py      # Barra lateral de navegación
│   │       ├── mini_player.py      # Reproductor mini
│   │       ├── full_player.py      # Reproductor completo
│   │       ├── song_card.py        # Tarjeta de canción
│   │       ├── search_bar.py       # Barra de búsqueda
│   │       ├── lyrics_view.py      # Vista de letras
│   │       └── ...
│   │   └── dialogs/                 # Diálogos
│   │       └── login_dialog.py     # Diálogo de login (WebEngineView)
│   │
│   ├── system/                      # Integraciones del sistema
│   │   ├── mpris.py                # MPRIS2 (Linux media keys)
│   │   ├── tray.py                 # Bandeja del sistema
│   │   ├── media_keys.py          # Media keys
│   │   └── network.py             # Monitor de red
│   │
│   ├── config/                      # Configuración
│   │   ├── settings.py            # Ajustes de la app
│   │   ├── paths.py               # Rutas de archivos
│   │   ├── themes.py              # Temas
│   │   └── __init__.py
│   │
│   ├── utils/                      # Utilidades
│   │   ├── vlc_check.py           # Verificación de VLC
│   │   ├── image_cache.py        # Cache de imágenes
│   │   ├── color_extractor.py    # Extracción de colores
│   │   ├── lrc_parser.py         # Parser de letras
│   │   ├── time_utils.py         # Utilidades de tiempo
│   │   └── worker.py             # Worker asíncrono
│   │
│   └── main.py                    # Punto de entrada
│
├── venv/                           # Entorno virtual
├── pyproject.toml                  # Configuración del proyecto
└── README.md                      # Documentación
```

## 3. ESTADO ACTUAL DEL PROYECTO

### 3.1 Funcionalidades que Funcionan

✅ **Autenticación mediante Cookies del Navegador**
- Se utiliza `QWebEngineView` para capturar cookies de `music.youtube.com`
- Credenciales guardadas en `~/.config/pyrolist/headers_auth.json`
- Proceso automático: al iniciar sesión en el diálogo, la ventana se cierra sola y guarda la sesión

✅ **Barra lateral de navegación**
- Botones: Inicio, Buscar, Biblioteca, Historial, Descargas, Ajustes
- Sección de perfil que muestra el avatar del usuario cuando está autenticado
- Click en perfil no autenticado abre el diálogo de login web

✅ **Reproducción de música**
- Uso de VLC para reproducción (vía `python-vlc`)
- Cola de reproducción centralizada en `MainWindow`
- Controles robustos de Play/Pause con sincronización de estado instantánea

✅ **Búsqueda e Inicio**
- Pantalla de Inicio dinámica: muestra recomendaciones personalizadas si hay sesión, o géneros como fallback
- Búsqueda híbrida usando yt-dlp y ytmusicapi

## 4. SISTEMA DE AUTENTICACIÓN

### 4.1 Método actual: Browser Cookies (headers_auth.json)
La aplicación utiliza un navegador embebido (`QtWebEngine`) para que el usuario inicie sesión directamente en la web de YouTube Music. Al detectar que el usuario se ha logueado con éxito, la aplicación extrae las cookies y genera un archivo `headers_auth.json` compatible con `ytmusicapi`.

Este método ha reemplazado completamente al antiguo flujo OAuth, ya que es más fiable y permite acceder a todas las funciones de la biblioteca del usuario sin restricciones de API Desktop.

### 4.2 Carga de Sesión
```python
# En YouTubeMusicClient._load_auth_session()
def _load_auth_session(self):
    auth_file = AppDirs.config / "headers_auth.json"
    if auth_file.exists():
        self._setup_ytmusicapi(str(auth_file))
```

## 5. REPRODUCCIÓN Y UI

- **Centralización:** Los controles de reproducción (play, pause, next, prev, seek) están centralizados en `MainWindow`.
- **Now Playing:** Pantalla completa con carátula (360px), letras sincronizadas y sección de canciones similares.
- **Favoritos:** Estado de "like" persistente consultando la base de datos local para marcar el corazón rojo incluso en resultados de búsqueda.

## 6. COMMANDOS ÚTILES

### 6.1 Ejecutar la aplicación
```bash
python -m pyrolist.main
```

### 6.2 Cerrar sesión (forzar re-login)
Eliminar el archivo de cabeceras de autenticación:
```bash
rm ~/.config/pyrolist/headers_auth.json
```

---

**Última actualización:** 2026-05-15  
**Estado:** Autenticación por cookies operativa, UI modernizada, Play/Pause estable.