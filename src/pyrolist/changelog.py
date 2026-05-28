from __future__ import annotations

CURRENT_CHANGELOG_VERSION = "1.2.1"
CURRENT_CHANGELOG_SUMMARY = (
    "Esta versión optimiza la latencia de reproducción local, mejora las descargas con "
    "esqueletos y animaciones de carga, y soluciona pequeños bugs visuales y de rendimiento."
)

CURRENT_CHANGELOG: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Novedades",
        (
            "Optimización de latencia en la reproducción de archivos locales, eliminando retrasos innecesarios.",
            "Visualización mejorada en la pantalla de descargas con skeleton loaders interactivos.",
            "Animación de transición suave con efecto 'fade-in' al cargar elementos descargados.",
            "Indicadores de canciones marcadas como 'Me gusta' en la lista de descargas.",
            "Transición de posición más fluida para el panel flotante 'glass' cuando ya está visible.",
        ),
    ),
    (
        "Correcciones",
        (
            "Solucionado un problema en la pantalla de estadísticas que causaba un error al desempaquetar el historial.",
            "Corrección de fugas en el temporizador de sugerencias de la barra de búsqueda global.",
            "Evitada la sobreescritura de sugerencias de búsqueda obsoletas si se cambia la consulta rápidamente.",
        ),
    ),
)
