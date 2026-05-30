from __future__ import annotations

CURRENT_CHANGELOG_VERSION = "1.3.0"
CURRENT_CHANGELOG_SUMMARY = (
    "Esta versión se enfoca en el rendimiento y optimización extrema: introduce pools de hilos centralizados, "
    "un sistema de caché inteligente de 5 minutos, repintado controlado a 20 FPS y persistencia de sesión HTTP."
)

CURRENT_CHANGELOG: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Novedades",
        (
            "Nuevo pool de hilos centralizado (IO_POOL y CPU_POOL) para optimizar el uso de recursos multinúcleo.",
            "Sistema de caché en memoria de 5 minutos para playlists, álbumes y artistas, logrando una navegación instantánea.",
            "Optimización del fondo fluido (AmbientBackground) limitando su refresco a 20 FPS para reducir el uso de CPU.",
            "Reutilización de sesión HTTP en el gestor de portadas, acelerando drásticamente las descargas sucesivas.",
            "Optimización de carga asíncrona en las pantallas de álbum y playlist mediante cesión de control al event loop (evita congelar la interfaz).",
            "Caché estática de hojas de estilo (stylesheets) en tarjetas rápidas y banners para acelerar la aplicación de temas.",
        ),
    ),
    (
        "Correcciones",
        (
            "Solucionado el reinicio del ecualizador de VLC, aplicando ahora una limpieza nativa completa.",
            "Soporte y corrección automática de identificadores de playlist con prefijo 'VL' provenientes de YouTube Music.",
            "Se corrigieron las descripciones y nombres de autores en las tarjetas de playlists de la pantalla de inicio.",
        ),
    ),
)
