# AGENTS.md — Guía para agentes trabajando en Pyrolist

## Contexto del proyecto
Pyrolist es un reproductor de música local + cliente de streaming de YouTube Music.
Stack: Python 3.12+, PySide6 (Qt6), VLC (`python-vlc`), `ytmusicapi`, `yt-dlp`.
Tamaño: ~27k LOC en `src/pyrolist/`.

## ✅ REFACTOR DEL GOD OBJECT — COMPLETADO (no lo reportes como pendiente)
El `main_window.py` original de **2527 líneas / 80+ métodos** ya fue dividido. Hoy
`main_window.py` (~870 líneas) es un **shell de orquestación**: instancia los
controladores, construye la UI (ventana, stack, mini-player, notificaciones, tray,
shortcuts) y mantiene **wrappers finos** que delegan a los controllers. No es un god object.

### Arquitectura actual — `src/pyrolist/ui/controllers/`
- `MainWindow` (shell) crea y posee:
  - `PlaybackController` — `_play_song`, `_play_current`, `_advance_queue`, `_preload_next`,
    auto-queue, play/pause/next/prev/seek, `_update_queue_panel`, `_play_local*`
  - `IntegrationsController` — callbacks VLC, scrobble Last.fm, MPRIS, Discord, conectividad
  - `DownloadController` — `_on_download_*`, `_delete_*`, `_play_local_playlist`
  - `QueueController` — play-next, add-to-queue, add-to-playlist (diálogo), like, queue-move
  - `NavigationController` — routing, offline state, auth/login, búsqueda, sidebar
  - `PlaybackSessionManager` — restore/save sesión, `_initialize`, `_check_updates`
- **Patrón de acoplamiento**: cada controller recibe `main_window` (back-reference) y
  `run_async`. Los métodos que pantallas/señales invocan por nombre (`self._on_play_pause`,
  `self._navigate_to`, `self._on_download_error`, etc.) quedan como **wrappers finos en
  MainWindow** que delegan a `self.<controller>.<método>`. No los borres: las señales de
  `screens/*` y `DownloadManager` se conectan a esos nombres en `__init__`.
- `MainWindow` conserva atributos compartidos que los controllers leen/escriben vía
  `self.main_window.X`: `queue`, `player`, `mpris`, `settings`, `yt`, `stack`, `ROUTES`,
  `ONLINE_ROUTES`, `_current_route`, `_offline_blocked_path`, `offline_banner`, `yt`.

➡️ Si ves wrappers finos o acoplamiento vía `self.main_window`, **NO lo reportes como
hallazgo nuevo** ni propongas "arreglar la arquitectura desde cero". Ya está hecho.
Contribuye en otra área o refina lo existente.

## ✅ Bugs críticos YA RESUELTOS (Fase 1) — no los re-diagnostiques ni "arregles" de nuevo
1. **Race conditions en reproducción** — `MusicPlayer` usa `asyncio.Lock` (`_play_lock`) +
   `asyncio.Event` (`_playback_ready`) para serializar `play/pause/resume/stop/seek`.
2. **RepeatMode.ONE** — `PlayQueue.advance()` mantiene el índice; `next_item` devuelve el
   item actual en modo ONE (no avanza).
3. **Manejo de errores VLC** — `play_url` espera el evento real `MediaPlayerPlaying` con
   timeout 10s (no `sleep` heurístico); `_on_error` setea `_playback_ready` para no colgar.
4. **Validación de archivos locales + fallback** — `_play_local` valida existencia/tamaño/
   permisos y hace fallback a streaming si falla.
5. **Shutdown graceful** — `DownloadManager.async_stop()` + `MainWindow.async_shutdown()`;
   `main.py` lo llama en `finally`.
6. **Bug de duración 10s** — todos los call sites pasan `duration_ms`; se extrajo
   `parse_duration_to_ms` en `utils/time_utils.py` (antes duplicado en `album.py`/`playlist.py`).
   Si ves "0:10" en una duración, ya está resuelto.

## Convenciones
- **Tests**: `pytest` + `pytest-asyncio` (modo STRICT). Fixtures async → `@pytest_asyncio.fixture`.
  Tests de DB: `sqlite+aiosqlite:///:memory:` con monkeypatch de `DATABASE_URL`, `_engine`,
  `_session_factory` antes de `db.init_db()`.
- No agregar comentarios innecesarios al código (salvo TODOs de refactor explícitos).
- MCP servers: `context7` funciona; `sqlite` y `github` requieren config en
  `.opencode/opencode.jsonc` (github necesita `GITHUB_TOKEN` env var).

## Áreas pendientes (Fase 2+, aún NO empezadas)
- **Tests de controllers** — los controllers dependen de `MainWindow` (back-ref) y Qt, por
  lo que son difíciles de testear aislados. Los tests actuales (`tests/test_queue.py`,
  `test_player.py`, `test_repository.py`, `test_time_utils.py`) cubren la lógica pura.
  Añadir tests de integración ligeros si se refactoriza el acoplamiento.
- **SettingsController (opcional)** — `_on_settings_changed` (~70 líneas) aplica equalizer/
  volumen/integradores y aún vive en MainWindow. Extraerlo es polish de bajo riesgo/beneficio.
- **Anomalía conocida (`yt`)** — `MainWindow.yt` se REASIGNA en login/logout
  (`_on_auth_changed` crea un `YouTubeMusicClient` nuevo). Los controllers que leen
  `self.main_window.yt` (Navigation/Queue/Download) ya ven la referencia actualizada;
  pero cualquier controller que INYECTE `yt` en su constructor quedaría con el cliente
  viejo tras login. Mantén el acceso vía `self.main_window.yt` en nuevos controllers.
- **Performance** — revisar ops bloqueantes (solo 1 `subprocess.run` en `theme_manager.py`),
  caching de imágenes/DB, polling del event loop.
- **i18n** — cobertura de traducciones (es es el idioma por defecto).
- **Accesibilidad** — foco, roles ARIA equivalentes en Qt, contraste.
