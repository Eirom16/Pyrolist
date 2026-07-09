from __future__ import annotations

CURRENT_CHANGELOG_VERSION = "2.1.0"
CURRENT_CHANGELOG_SUMMARY = (
    "¡Pyrolist v2.1.0 ya está aquí! Esta versión introduce grandes cambios incluyendo la vista de Artistas en la biblioteca, notificaciones del sistema, "
    "mejoras significativas en la interfaz gráfica, y correcciones importantes de sincronización de audio."
)

CURRENT_CHANGELOG: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Novedades",
        (
            "Vista de Artistas: Nueva sección en la Biblioteca para explorar y reproducir por artistas.",
            "Notificaciones de Sistema: Alertas nativas de sistema para cambio de canciones.",
            "Mejoras de Interfaz UI: Múltiples rediseños incluyendo el widget 'Cargar más', la búsqueda global, el panel de cola y ajustes visuales en el mini reproductor.",
            "Roadmap completado: Se ha completado el roadmap de pensamiento lateral.",
        ),
    ),
    (
        "Correcciones",
        (
            "Sincronización de Audio: Se solucionó el bug donde las canciones terminaban antes de tiempo causando desincronización y fallos en la reproducción automática.",
            "Listas de Artistas: Se arregló la carga de listas en Biblioteca > Artistas.",
            "UI Settings: Corrección de comportamiento de los combobox al hacer scroll.",
        ),
    ),
)
